"""Compare beneficial/harmful VSL endpoint states using existing obs150 only."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import time
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h
from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
from evaluation.controllers import obs150_contract as oc, offramp_routing as routing

HERE=Path(__file__).resolve().parent/'verified'
PINS={}
TARGETS={'10483':'storage:lane_off_10483','10682':'storage:lane_off_10682',
         '10481':'storage:OR_D_E_storage','10643':'storage:OR_F_E_storage'}


def read(path):
    path=Path(path);data=path.read_bytes();PINS[str(path)]=hashlib.sha256(data).hexdigest()
    return json.loads(data)


def save(name,value):h.save(HERE/name,value)


def metrics(vv):
    n=len(vv)
    return dict(n=n,speed=math.fsum(v['v'] for v in vv)/n if n else None,
                stopped=sum(v['v']<5 for v in vv))


def main():
    HERE.mkdir(exist_ok=False)
    assert not (HERE/'completion.json').exists() and not (HERE/'protocol.json').exists()
    context,_,_=common.setup()
    cfg=context['component']._config('FW_E',context['parameters']['by_direction']['FW_E'])
    assert context['component'].lane_groups_enabled is False
    runtime=read(h.R/'entry10643/native_cohorts.json')['route_runtime']
    assert h.sha(h.ROOT/runtime['network']['path'])==runtime['network']['sha256']
    detectors,digest=oc.read_detector_csv(h.I/'selected/obs150/obs150_detectors_v2.csv')
    groups=oc.group_boundaries(detectors)
    sources={str(p):h.sha(p) for p in (h.ROOT/'evaluation/controllers').glob('*.py')}
    stop=h.read(h.R/'aggregate_recovery247/protocol.json')['STOP']
    save('protocol.json',dict(previous='253completed8fullOmega forecasts; A/Efit improved67butfailed73/71,notadopted.',
        question='Does VSL benefit versus harm correspond to different mainline/offramp stocks and stop locations, rather than uniformly weak VSL FD?',
        cases='67release/release90 at2700..3150;71nc/rm/vsl/both at2250..2700;four150sendpoints each.',
        definition='Stopped<5kmh; actualcurrentstaticroute only, unknown preserved. FullframeSHA verified. Nativeoff-entry detector counters per150s are not all desired-demand; connectorstock is not arrival.',
        scope='Existing completed observed endpoint frames and current248forecast outputs. Postcontrolstates are diagnostic truth ONLY; no autonomous future observation input, no causal coefficient or continuousqueue duration inferred.',
        comparison='Same common initial state within each seed; different seeds/times not common states. Currentaggregate prediction has no lane stopped-state output.',
        budget=dict(fit=0,forecasts=0,native=0,FZP=0),protected=sources,STOP=stop))
    cases=[]
    for arm in ('release','release_vsl90'):
        cases.append((67,arm,2700,Path('D:/VISSIM_runs/20261003_s67_vsl_observation2700')/arm/f'decisions_sdmpc31_g_2700_{arm}_s67',arm+'_actual'))
    for arm in ('nc','rm','vsl','both'):
        cases.append((71,arm,2250,Path('D:/VISSIM_runs/20261003_independent_s71_four84')/arm/f'decisions_sdmpc31_g_2250_{arm}_s71',arm))
    cells=[];lanes=[];ports=[];witness=[];initial={};maxinitial=0.;started=time.perf_counter()
    for seed,arm,start,folder,predarm in cases:
        pred=read(h.R/f'deceleration248/verified/s{seed}_base_{predarm}.json')
        for block,t in enumerate(range(start,start+451,150)):
            raw=read(folder/f'state_{t:06d}.json');obs=raw['obs150'];ref=obs['frames']['current']
            path=oc.resolve(obs,ref['path']);frame=oc.load_frame(path,ref['sha256'],t)
            PINS[str(path)]=ref['sha256']
            assert frame['run_id']==raw['lane_plant_observation']['run_id']
            assert len(frame['vehicles'])==raw['total_vehicles']
            if block==0:
                if seed in initial:assert initial[seed]==frame['vehicles']
                else:initial[seed]=frame['vehicles']
            bycell=defaultdict(list);bylink=defaultdict(list)
            for v in frame['vehicles']:
                item=dict(id=v[0],link=str(v[1]),lane=int(v[2]),pos=v[3],v=v[4])
                bylink[str(v[1])].append(item)
                if str(v[1]) not in runtime['physical']:continue
                road,x,c=routing._position(runtime,v[1],v[3])
                if road!='FW_E':continue
                target='unknown'
                if v[6] is not None:
                    assert str(v[8]).upper()=='STATIC'
                    route=runtime['routes'][f'{int(v[6])}:{int(v[7])}']
                    end=runtime['branches'][route['target']]['source_chain_m'] if route['target'] in runtime['branches'] else route['end'][1]
                    if x<=end+.002:target=route['target'] if route['target'] in runtime['branches'] else 'terminal'
                bycell[c].append(dict(item,x=x,target=target))
            state=pred['snapshots'][block]
            assert state['time']==t
            for c in range(31):
                vv=bycell[c];m=metrics(vv)
                p=cfg.network.freeway_segment_params['FW_E'][c]
                predicted_n=state['density']['FW_E'][c]*p['segment_length_km']*cfg.network.freeway_segment_lanes['FW_E'][c]
                predicted_v=state['speed']['FW_E'][c]
                if block==0:
                    maxinitial=max(maxinitial,abs(predicted_n-m['n']))
                    assert abs(predicted_n-m['n'])<1e-7
                cells.append(dict(seed=seed,arm=arm,elapsed=t-start,cell=c,**m,predicted_n=predicted_n,predicted_speed=predicted_v))
                if c not in range(8,26):continue
                lane_value=cfg.network.freeway_segment_lanes['FW_E'][c]
                nlanes=round(lane_value)
                assert abs(lane_value-nlanes)<1e-8
                assert all(1<=z['lane']<=nlanes for z in vv)
                for lane in range(1,1+nlanes):
                    lv=[z for z in vv if z['lane']==lane]
                    lo,hi=runtime['bounds']['FW_E'][c:c+2]
                    nearest=min((hi-z['x'] for z in lv if z['v']<5),default=None)
                    destinations={k:metrics([z for z in lv if z['target']==k]) for k in sorted({z['target'] for z in lv})}
                    assert sum(z['n'] for z in destinations.values())==len(lv)
                    lanes.append(dict(seed=seed,arm=arm,elapsed=t-start,cell=c,lane=lane,**metrics(lv),
                        nearest_stopped_to_downstream_m=nearest,stopped_last50m=sum(z['v']<5 and hi-z['x']<=50 for z in lv),destinations=destinations))
                witness.append(dict(seed=seed,arm=arm,time=t,cell=c,vehicles=vv))
            for target,stockkey in TARGETS.items():
                vv=bylink[target]
                flow=sum(int(obs['detectors'][str(det.dcp_no)]) for det in groups['off_entry:'+target]) if block else None
                predicted_total=sum(tr['vehicles'] for tr in pred['transfers'] if tr['source']=='freeway:FW_E' and tr['target']==stockkey)
                ports.append(dict(seed=seed,arm=arm,elapsed=t-start,target=target,**metrics(vv),
                    observed_entry_interval=flow,predicted_stock=state['inventory'][stockkey],predicted_entry450=predicted_total))
        # Existing forecast snapshot initial stocks must have actualphysicalcell units.
    assert all(h.sha(p)==sha for p,sha in {**PINS,**sources,stop['path']:stop['sha256']}.items())
    for name,value in [('cells',cells),('lanes',lanes),('ports',ports),('witness',witness),('pins',PINS)]:save(name+'.json',value)
    save('completion.json',dict(status='COMPLETE_DIAGNOSTIC',seconds=time.perf_counter()-started,cases=len(cases),
        frames=24,cells=len(cells),lane_rows=len(lanes),ports=len(ports),initial_stock_error=maxinitial,
        common_initial_fullframes=True,source_and_STOP_preserved=True,fit=0,forecasts=0,native=0,FZP=0,adopted=False))
    print('completed',len(cells),len(lanes),len(ports),'initialerror',maxinitial)


if __name__=='__main__':main()
