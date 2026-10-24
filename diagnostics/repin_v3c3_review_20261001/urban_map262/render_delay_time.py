"""Local delay increments from native DelayTm; do not map upstream accumulated delay."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize, LinearSegmentedColormap
import numpy as np

HERE = Path(__file__).resolve().parent
BASE = HERE / 'to8550'
OUT = BASE / 'delay_time'
OUT.mkdir(exist_ok=True)
START, END = 7950., 8550.
SOURCES = {
    'nc': Path('D:/VISSIM_runs/20260927_sd31_wiring9000/nc/vissim_eval/sdmpc31_nc9000_s29_001.fzp'),
    'sdmpc': Path('D:/VISSIM_runs/20261006_min2_storage90_fixed90_s29_9000/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s29_001.fzp'),
}


def frames(path):
    """Read the bounded window plus one snapshot on each side; no live COM."""
    now, vehicles, columns = None, {}, None
    with path.open(encoding='utf-8-sig', errors='replace') as stream:
        for line in stream:
            if line.startswith('$VEHICLE:'):
                columns = [s.strip().upper() for s in line.split(':',1)[1].split(';')]
                assert columns[0] == 'SIMSEC'
                ix = [columns.index(k) for k in ('NO','LANE\\LINK\\NO','DELAYTM')]
                continue
            if line.startswith(('*','$')) or not line.strip():
                continue
            assert columns is not None
            t = float(line.split(';',1)[0])
            if t < START-5:
                continue
            if now is not None and t != now:
                assert t > now
                yield now, vehicles
                vehicles = {}
            if t > END+0.11:
                return
            now = t
            row = line.split(';')
            assert len(row) == len(columns)
            no, link, delay = int(row[ix[0]]), int(row[ix[1]]), float(row[ix[2]])
            assert no not in vehicles and np.isfinite(delay)
            vehicles[no] = (link, delay)
    if now is not None:
        yield now, vehicles


def extract(arm):
    path = SOURCES[arm]
    cache = OUT / f'{arm}_delay.json'
    if cache.exists():
        result = json.loads(cache.read_bytes())
        assert result['source'] == str(path) and result['source_bytes'] == path.stat().st_size
        return result
    local = Counter()
    observed = defaultdict(set)
    same_link_vehicles = defaultdict(set)
    exposure = Counter()
    transition_delay = Counter()
    previous, previous_t = None, None
    stats = Counter()
    samples = []
    for t, current in frames(path):
        samples.append(t)
        if START <= t <= END:
            for no,(link,delay) in current.items():
                observed[link].add(no)
        if previous is None:
            previous_t, previous = t, current
            continue
        dt = t-previous_t
        assert abs(dt-5) < 1e-7
        overlap = max(0., min(t,END)-max(previous_t,START))
        if overlap:
            for no in previous.keys() & current.keys():
                old_link, old_delay = previous[no]
                link, delay = current[no]
                change = delay-old_delay
                stats['matched_pairs'] += 1
                if change < -0.021:
                    stats['negative_increment_pairs'] += 1
                    stats['negative_increment_seconds'] += change*overlap/dt
                    stats['minimum_increment_seconds'] = min(stats['minimum_increment_seconds'],change)
                if change > dt+0.021:
                    stats['increment_over_dt_pairs'] += 1
                    raise ValueError(f'DelayTm increment exceeds elapsed time: {change} vs {dt}')
                increment = change*overlap/dt
                if old_link == link:
                    local[link] += increment
                    exposure[link] += overlap
                    observed[link].add(no)
                    same_link_vehicles[link].add(no)
                    stats['same_link_pairs'] += 1
                else:
                    transition_delay[f'{old_link}->{link}'] += increment
                    stats['transition_pairs_excluded'] += 1
            stats['unmatched_previous_observations'] += len(previous.keys()-current.keys())
            stats['unmatched_current_observations'] += len(current.keys()-previous.keys())
        previous_t, previous = t, current
    assert abs(samples[0]-7945.1)<1e-7 and abs(samples[-1]-8550.1)<1e-7
    result = {
        'source':str(path),'source_bytes':path.stat().st_size,'window_sec':[START,END],
        'sampling_sec':5,'first_frame_sec':samples[0],'last_frame_sec':samples[-1],
        'definition':'Sum of signed native cumulative DelayTm increments for consecutive same-link observations, clipped by time overlap, divided by distinct observed vehicles on that link during the window. Native negative increments are preserved.',
        'unit':'seconds per observed vehicle; partial local delay accumulated within this600s window',
        'limitations':['Not completed-trip delay or full-link traversal delay. Vehicles still queuing are included.',
                       'Delay during link-changing intervals and unobserved entry/exit intervals is unallocated; the mapped local delay is a partial estimate.',
                       'The two partial5s time-boundary increments are prorated by overlap; within-frame timing is not observed.',
                       'Native delay uses Vissim ideal-driving conditions. It is distinct from stopped time and from Omega TTT.',
                       'Native negative delay increments are retained numerically; colors below zero use the minimum color.'],
        'checks':dict(stats),'links':{},'unallocated_transition_delay_sec':float(sum(transition_delay.values())),
        'unallocated_transition_by_pair_sec':dict(transition_delay),
    }
    for link, ids in observed.items():
        result['links'][str(link)] = dict(observed_vehicles=len(ids),same_link_vehicles=len(same_link_vehicles[link]),
            local_delay_sec=float(local[link]),mean_local_delay_sec=float(local[link]/len(ids)),
            same_link_exposure_veh_sec=float(exposure[link]))
    cache.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result


def main():
    data = {}
    for arm in SOURCES:
        data[arm] = extract(arm)
        print(arm+': '+json.dumps(data[arm]['checks']),flush=True)
    original = json.loads((BASE/'summary.json').read_bytes())
    network = next(Path(p) for p,h in original['source_sha256'].items()
                   if p.lower().endswith('.inpx') and h==original['network_sha256'])
    raw = network.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==original['network_sha256']
    net = ET.fromstring(raw)
    with (BASE/'link_window_metrics.csv').open(encoding='utf-8-sig',newline='') as f:
        meta={int(r['link']):r for r in csv.DictReader(f) if r['arm']=='nc' and int(r['from_sec'])==START}
    ids = sorted(meta)
    bg = next(b for b in net.findall('./backgroundImages/backgroundImage') if b.get('no')=='4')
    origin=np.array([float(bg.find('coordBL').get(k)) for k in ('x','y')])
    poly={int(l.get('no')):np.array([[float(p.get('x')),float(p.get('y'))]
          for p in l.findall('./geometry/linkPolyPts/linkPolyPoint')]) for l in net.findall('./links/link')}
    geom=[(poly[i]-origin)/1000 for i in ids]
    urban=np.array([meta[i]['category']=='urban_and_other_inside' for i in ids])
    outside=np.array([meta[i]['category']=='outside' for i in ids])
    ramps=np.array([meta[i]['category'] in ('on_ramp_connector','off_ramp_connector') for i in ids])
    freeway=np.array([meta[i]['category'].startswith('FW_') for i in ids])
    major=np.array([float(meta[i]['length_m'])>=60 for i in ids])
    pts=np.vstack([geom[j] for j in np.where(urban)[0]])
    bounds=[pts[:,0].min()-.18,pts[:,0].max()+.18,pts[:,1].min()-.18,pts[:,1].max()+.18]
    cmap=LinearSegmentedColormap.from_list('local_delay',['#719db4','#ecddae','#efa45b','#d6543b','#851b34'])
    norm=Normalize(0,600)
    plot_values={}
    for arm in data:
        plot_values[arm]=np.array([data[arm]['links'].get(str(i),{}).get('mean_local_delay_sec',np.nan) for i in ids])

    def background(ax):
        ax.add_collection(LineCollection(geom,colors='#d7dce1',linewidths=.55,zorder=1))
        ax.add_collection(LineCollection([geom[j] for j in np.where(freeway)[0]],colors='#6d4ca0',linewidths=1.25,zorder=2))
        ax.add_collection(LineCollection([geom[j] for j in np.where(ramps)[0]],colors='#495f76',linewidths=1,zorder=2))
        ax.set(xlim=bounds[:2],ylim=bounds[2:],aspect='equal')
        ax.set_xticks([]);ax.set_yticks([])
        for spine in ax.spines.values():spine.set_edgecolor('#d0d6dd')

    fig,axes=plt.subplots(1,2,figsize=(17,7.4))
    fig.subplots_adjust(left=.006,right=.946,bottom=.015,top=.985,wspace=.035)
    for ax,arm in zip(axes,('nc','sdmpc')):
        background(ax)
        values=plot_values[arm]
        for mask,style,width in ((outside,'dashed',1.45),(urban,'solid',2.2)):
            js=np.where(mask & major & np.isfinite(values))[0]
            ax.add_collection(LineCollection([geom[j] for j in js],array=values[js],cmap=cmap,norm=norm,
                linewidths=width,linestyles=style,zorder=3))
    cax=fig.add_axes([.964,.16,.014,.68])
    cb=fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cmap),cax=cax,extend='max')
    cb.set_ticks([])
    fig.canvas.draw()
    assert all(not t.get_text() for t in fig.findobj(matplotlib.text.Text))
    for ext in ('png','svg'):
        fig.savefig(OUT/f'urban_delay_no_text.{ext}',dpi=200,facecolor='white')
    plt.close(fig)
    selected=[]
    for i in (40,52,68,66,127,38):
        selected.append({'link':i,**{a:data[a]['links'].get(str(i)) for a in data}})
    with (OUT/'link_delay.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(['link','category','nc_partial_delay_s_per_observed_vehicle','control_partial_delay_s_per_observed_vehicle','control_minus_nc'])
        for j,i in enumerate(ids):
            a,b=plot_values['nc'][j],plot_values['sdmpc'][j]
            writer.writerow([i,meta[i]['category'],a if np.isfinite(a) else '',b if np.isfinite(b) else '',b-a if np.isfinite(a+b) else ''])
    report={'source_map':str(BASE/'urban_stopped_density_latest.png'),'same_original_run':True,
        'window_sec':[START,END],'color_scale_sec_per_observed_vehicle':[0,600],
        'metric':data['nc']['definition'],'text_removed':True,'grey':'No usable vehicle observations',
        'reference':'https://cgi.ptvgroup.com/vision-help/VISSIM_11_ENG/Content/11_Auswertungen/AuswertungFahrzeugprotokoll.htm',
        'limitations':data['nc']['limitations'],'focus_links':selected,
        'unallocated_transition_delay_sec':{a:data[a]['unallocated_transition_delay_sec'] for a in data}}
    (OUT/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'focus_links':selected,'output':str(OUT)},ensure_ascii=True),flush=True)


if __name__=='__main__':
    main()
