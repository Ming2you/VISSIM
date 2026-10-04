"""Saved-state boundary flux screen; no calibration, rollout, or native run."""
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
I=HERE.parent
ROOT=I.parents[2]
OLD=ROOT.parent/'control-full-review/diagnostics'
OUT=HERE/'boundary_flux_audit'
PINS={}


def data(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return b


def load(p):
    b=data(p)
    return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)


def rows(p):
    b=data(p)
    return list(csv.DictReader(io.StringIO((gzip.decompress(b) if p.suffix=='.gz' else b).decode('utf-8-sig'))))


def trap(values):
    a=sorted(values.items())
    return sum((x[1]+y[1])*(y[0]-x[0])/7200 for x,y in zip(a,a[1:]))


def main():
    OUT.mkdir(exist_ok=True)
    assert not list(OUT.iterdir()), 'Preserve existing completed audit'
    manifest=load(OLD/'metanet_net_gain_goal_20260924/mainline_moments/manifest.json')
    ledger=load(HERE/'early_control_flow_ledger/summary.json')
    g=load(I/'selected/port_gain/geometry.json')
    length={r['cell']:r['length_km'] for r in g['cells'] if r['road']=='FW_E'}
    output=[];checks=[]
    for seed in (29,43):
        for arm in ('none','vsl','rm','both'):
            if seed==29:
                folder=OLD/('dsd110_20260923/bottleneck90_rm_20260924/reference_observations/none' if arm=='none' else f'dsd110_20260923/response_recalibration_20260924/observations/{arm}')
            else:
                folder=OLD/('dsd110_20260923/response_recalibration_20260924/gain_response/seed43/none' if arm=='none' else f'metanet_net_gain_goal_20260924/heldout43/observations/{arm}')
            native_cells=rows(folder/'cells_30s.csv')
            native_flow=rows(folder/'flows_30s.csv')
            for file in ('cells_30s.csv','flows_30s.csv'):
                assert PINS[str(folder/file)]==ledger['source_pins'][str(folder/file)]
            spec=next(r for r in manifest['rows'] if r['seed']==seed and r['arm']==arm)
            moment_path=OLD/'metanet_net_gain_goal_20260924/mainline_moments'/spec['output']
            moments=rows(moment_path)
            assert PINS[str(moment_path)]==spec['sha256']
            samples={}
            for r in moments:
                if r['scope']!='cell':continue
                t=round(float(r['time_s']),1);cell=int(r['bin'])
                s=samples.setdefault((cell,t),dict(n=0.,nv=0.))
                s['n']+=float(r['n']);s['nv']+=float(r['speed_sum'])
            times=sorted({t for c,t in samples})
            assert times==[round(2220.1+5*k,1) for k in range(91)]
            # The moment table is sparse: an empty cell has no vehicle row.
            for cell in range(31):
                for t in times:samples.setdefault((cell,t),dict(n=0.,nv=0.))
            native={(int(r['cell']),round(float(r['time_s']),1)):r for r in native_cells if r['road']=='FW_E' and 2220.1-1e-7<=float(r['time_s'])<=2670.1+1e-7}
            assert len(native)==31*16
            for key,r in native.items():
                assert abs(samples[key]['n']-float(r['n_veh']))<1e-8
                if samples[key]['n']:
                    assert abs(samples[key]['nv']/samples[key]['n']-float(r['v_kmh']))<1e-7
            pred=load(HERE/f'component2220_s{seed}_current_v2/{arm}_prediction.json.gz')
            for cell in range(31):
                nv5={t:r['nv']/length[cell] for (c,t),r in samples.items() if c==cell}
                nv30={t:float(r['n_veh'])*float(r['v_kmh'] or 0)/length[cell] for (c,t),r in native.items() if c==cell}
                pred_nv={2220.1:nv30[2220.1]}
                for r in pred['cells']:
                    if r['road']=='FW_E' and r['cell']==cell:
                        pred_nv[round(r['time_s'],1)]=r['n_veh']*r['v_kmh']/length[cell]
                assert len(nv5)==91 and len(nv30)==len(pred_nv)==16
                f=[r for r in native_flow if r['road']=='FW_E' and int(r['cell'])==cell and float(r['window_start_s'])>=2220.1-1e-7 and float(r['window_end_s'])<=2670.1+1e-7]
                pf=[r for r in pred['flows'] if r['road']=='FW_E' and r['cell']==cell]
                assert len(f)==len(pf)==15
                assert all(float(r[k])==0 for r in f for k in ('unexplained_entries','unexplained_losses','native_removals','conservation_residual_veh'))
                output.append(dict(seed=seed,arm=arm,cell=cell,length_km=length[cell],
                    native=dict(spatial_passages_5s=trap(nv5),spatial_passages_30s=trap(nv30),
                        downstream=sum(float(r['downstream_crossings']) for r in f),off=sum(float(r['off_departures']) for r in f),
                        terminal=sum(float(r['terminal_exits_inferred']) for r in f),
                        ttt=trap({t:samples[cell,t]['n'] for t in nv5})),
                    prediction=dict(spatial_passages_30s=trap(pred_nv),
                        downstream=sum(r['downstream_crossings'] for r in pf),off=sum(r['off_departures'] for r in pf),
                        terminal=sum(r['terminal_exits'] for r in pf))))
            checks.append(dict(seed=seed,arm=arm,exact_native_count_speed_snapshots=31*16))
    deltas=[]
    for r in output:
        base=next(b for b in output if b['seed']==r['seed'] and b['cell']==r['cell'] and b['arm']=='none')
        deltas.append(dict(seed=r['seed'],arm=r['arm'],cell=r['cell'],
            **{key:{k:v-base[key][k] for k,v in r[key].items()} for key in ('native','prediction')}))
    result=dict(rows=output,deltas=deltas,checks=checks,source_pins=PINS,new_native=0,new_rollouts=0,
        definition='Spatial equivalent passages = trapezoidal integral of sum(vehicle speed)/cell length; not a boundary flow or model receiving capacity.',
        limits=['Actual5s spatial samples and30s boundaries have distinct discretization.',
                'N*v/L is a spatial mean flow; cell outlet flow may differ with within-cell waves and partial traversals.',
                'Observed future N/v used only to diagnose flux closure, never autonomous prediction.',
                'No fitted coefficient or capacity bonus; a discrepancy alone is not causal proof of missing lane state.'])
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in PINS.items())
    (OUT/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps([r for r in deltas if r['seed']==29 and r['arm'] in ('rm','vsl') and 17<=r['cell']<=24],indent=2))


if __name__=='__main__':main()
