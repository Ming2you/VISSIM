"""Native eastbound speed comparison; one extraction, cached plotting thereafter."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / 'speed_heatmap900_8100'
OUT.mkdir(exist_ok=True)
REF = json.loads((HERE / 'warmup_excluded900_8100_no_west.json').read_bytes())
GEOPATH = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json'
GEO = json.loads(GEOPATH.read_bytes())
assert hashlib.sha256(GEOPATH.read_bytes()).hexdigest() == REF['source_sha256'][str(GEOPATH)]
CHAIN = {str(r['link']): r['offset_m'] for r in GEO['chains']['FW_E']}
LENGTH = max(r['offset_m'] + r['length_m'] for r in GEO['chains']['FW_E'])
X_EDGES = np.r_[np.arange(0, LENGTH, 100.), LENGTH]
T_EDGES = np.arange(900., 8100.1, 15.)


def extract(arm):
    source = Path(REF['arms'][arm]['fzp_source'])
    assert source.stat().st_size == REF['arms'][arm]['fzp_size']
    cache = OUT / f'{arm}_native_speed.npz'
    if cache.exists():
        with np.load(cache) as data:
            assert str(data['source']) == str(source)
            assert int(data['source_bytes']) == source.stat().st_size
            assert np.array_equal(data['time_edges'], T_EDGES)
            assert np.array_equal(data['distance_edges'], X_EDGES)
            return data['sum_speed'].copy(), data['samples'].copy(), json.loads(str(data['audit']))
    sums = np.zeros((len(X_EDGES)-1, len(T_EDGES)-1))
    counts = np.zeros_like(sums, dtype=np.int64)
    # Per-frame freeway inventories independently reconcile with the previous TTT.
    ts, ns = [0.], [0]
    stamp, inventory = None, 0
    total_rows = clamped = 0
    min_pos, max_pos = float('inf'), -float('inf')
    with source.open(encoding='utf-8-sig', errors='replace') as stream:
        columns = None
        for line in stream:
            if line.startswith('$VEHICLE:'):
                columns = [x.strip().upper() for x in line.split(':', 1)[1].split(';')]
                ti, li, pi, vi = [columns.index(k) for k in ('SIMSEC', 'LANE\\LINK\\NO', 'POS', 'SPEED')]
                continue
            if line.startswith(('*', '$')) or not line.strip():
                continue
            assert columns is not None
            row = line.split(';')
            assert len(row) == len(columns)
            t = float(row[ti])
            if stamp is not None and t != stamp:
                assert t > stamp
                ts.append(stamp); ns.append(inventory)
                inventory = 0
            if t >= 8100:
                break
            stamp = t
            total_rows += 1
            link = row[li].strip()
            if link not in CHAIN:
                continue
            inventory += 1
            if t < 900:
                continue
            position = CHAIN[link] + float(row[pi])
            speed = float(row[vi])
            assert np.isfinite(speed) and speed >= 0
            min_pos, max_pos = min(min_pos, position), max(max_pos, position)
            if position < 0 or position >= LENGTH:
                clamped += 1
            # Native terminal-link positions may overshoot by one simulation step.
            xi = min(max(int(position // 100), 0), counts.shape[0]-1)
            ti_bin = int((t-900) // 15)
            sums[xi, ti_bin] += speed
            counts[xi, ti_bin] += 1
    assert abs(ts[-1] - 8095.1) < 1e-7
    metrics = json.loads((HERE / 'current_native_analysis_to8100' / arm / 'area_metrics.json').read_bytes())
    assert total_rows == metrics['sampling']['fzp_rows']
    assert len(ts)-1 == metrics['sampling']['fzp_snapshots']
    ts.append(8100.); ns.append(ns[-1])
    t, n = np.array(ts), np.array(ns)
    ct = np.r_[900., t[t > 900]]
    cn = np.r_[np.interp(900., t, n), n[t > 900]]
    ttt = float(np.sum((cn[:-1]+cn[1:])*np.diff(ct)/7200))
    assert abs(ttt - REF['arms'][arm]['domain']['FW_E']) < 1e-7
    details = dict(source=str(source), source_bytes=source.stat().st_size, native_rows=total_rows,
                   speed_samples=int(counts.sum()), time_bin_sec=15, distance_bin_m=100,
                   last_native_sec=8095.1, endpoint_clamped_samples=clamped,
                   observed_distance_range_m=[min_pos,max_pos],
                   freeway_ttt_reconciliation_veh_h=ttt,
                   missing_bins=int((counts==0).sum()),
                   values_above120_bins=int(np.sum(sums>120*counts)))
    np.savez_compressed(cache, sum_speed=sums, samples=counts, source=str(source),
                        source_bytes=source.stat().st_size, time_edges=T_EDGES,
                        distance_edges=X_EDGES, audit=json.dumps(details))
    return sums, counts, details


def plot(data, zoom):
    plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':12, 'svg.fonttype':'none'})
    fig, axs = plt.subplots(2, 1, figsize=(13,7.6), sharex=True, sharey=True)
    fig.subplots_adjust(left=.095, right=.865, top=.85, bottom=.15, hspace=.18)
    fig.text(.095, .955, 'Eastbound freeway speed', fontsize=21, weight='bold', color='#20252B')
    fig.text(.095, .902, '900–8100 s  |  Seed 29  |  Native vehicle records: 15 s × 100 m', fontsize=12, color='#5B6168')
    palette = plt.get_cmap('RdYlBu').copy()
    palette.set_bad('#E5E7EB')
    marker_ids={10643,10639,10681,10481,10490,10484}
    ramps=[r for r in GEO['boundaries'] if r['road']=='FW_E' and r.get('connector') in marker_ids]
    labels={'nc':'(a) No Control', 'sdmpc':'(b) SDMPC + fixed VSL90'}
    for ax, arm in zip(axs, ('nc','sdmpc')):
        sums, counts, audit=data[arm]
        speed=np.divide(sums,counts,out=np.full_like(sums,np.nan),where=counts>0)
        mesh=ax.pcolormesh(T_EDGES,X_EDGES/1000,np.ma.masked_invalid(speed),cmap=palette,
                           vmin=0,vmax=120,shading='flat',rasterized=True)
        for ramp in ramps:
            ax.axhline(ramp['chain_pos_m']/1000,color='#444444',lw=.65,ls=(0,(4,4)),alpha=.5)
        ax.set_title(labels[arm],loc='left',fontsize=13,pad=8)
        ax.set_ylabel('Distance [km]')
        ax.set_xlim(900,8100)
        ax.set_ylim((3.3,9.) if zoom else (0,LENGTH/1000))
        ax.set_yticks(np.arange(4,10) if zoom else np.arange(0,11,2))
        ax.tick_params(labelsize=11)
    axs[-1].set_xlabel('Simulation time [s]')
    axs[-1].set_xticks(np.arange(900,8101,900))
    cax=fig.add_axes([.89,.15,.023,.70])
    colorbar=fig.colorbar(mesh,cax=cax,extend='max',ticks=np.arange(0,121,20))
    colorbar.set_label('Vehicle-weighted mean speed [km/h]',labelpad=12)
    fig.text(.095,.070,'Distance measured from the eastbound entrance; downstream is upward. Dashed lines mark ramp junctions.',fontsize=9.2,color='#5B6168')
    fig.text(.095,.042,'Mainline lanes and connecting mainline links only; ramps excluded. Grey = no vehicle observations. No temporal interpolation.',fontsize=9.2,color='#5B6168')
    name='east_speed_comparison_zoom' if zoom else 'east_speed_comparison_full'
    fig.savefig(OUT/(name+'.png'),dpi=200,facecolor='white')
    fig.savefig(OUT/(name+'.svg'),facecolor='white')
    plt.close(fig)


def main():
    data={}
    for arm in ('nc','sdmpc'):
        data[arm]=extract(arm)
        print(arm+': '+json.dumps(data[arm][2]),flush=True)
    plot(data,True)
    plot(data,False)
    summary={'window_sec':[900,8100],'mainline':'FW_E','color_range_kph':[0,120],
             'aggregation':'Sum of observed native speeds / vehicle-record count within each15s x100m bin; empty bins masked',
             'time_interpolation':False,'native_sample_interval_sec':5,
             'ramp_speeds_included':False,'zoom_extent_km':[3.3,9.],
             'full_extent_km':[0,LENGTH/1000],
             'geometry_sha256':hashlib.sha256(GEOPATH.read_bytes()).hexdigest(),
             'arms':{a:r[2] for a,r in data.items()}}
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('HEATMAP_DONE '+str(OUT),flush=True)


if __name__=='__main__':
    main()
