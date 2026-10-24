"""Frozen post-head candidate on four existing seed53 component captures.

No simulator, fitting or future observations as forecast inputs. One prior-only
FZP scan estimates conflict counts; lane-change brackets are sensitivity cases.
"""
import csv
import gzip
import hashlib
import json
import sys
from pathlib import Path
import time

from evaluation.controllers.lane_plant_runtime import load_sources
from diagnostics.sdmpc_n31_20260924.integration_20260926.replay_congested_component import read_primitive_capture

HERE=Path(__file__).resolve().parent
I=HERE.parents[1]
H=I/'heldout53_response_v2'
ABLATION=sys.argv[1] if len(sys.argv)>1 else None
assert ABLATION in (None,'wave_only','anchor_only')
OUT=HERE/('seed53_'+ABLATION if ABLATION else 'seed53')
T0=2670.1
RID='RM_C10681'
POSITION=2159.868462667
FZP=Path('D:/VISSIM_runs/20260928_release2670_s53_v2/hold/run/vissim_eval/release2670_s53_hold_001.fzp')
load=lambda p:json.loads(Path(p).read_bytes())
def save(path,obj):
    Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def prior_counts():
    """Only2520.1..2670.1, common before commands diverge; no fitted count."""
    old={};frame={};stamp=None;events=[];frames=0;source=FZP.stat()
    digest=hashlib.sha256()
    def flush(t,now):
        nonlocal old,frames
        frames+=1
        for vid,v in now.items():
            if vid in old and old[vid][0]<POSITION<=v[0]:
                p=old[vid]
                events.append(dict(vehicle=vid,lower_sec=t-5,upper_sec=t,
                    from_lane=p[1],to_lane=v[1],from_pos=p[0],to_pos=v[0]))
        old=now
    with FZP.open('rb') as stream:
        for line in stream:
            if line.startswith(b'$VEHICLE:'):
                names=line.decode('ascii').strip().split(':',1)[1].split(';')
                ix={k:names.index(k) for k in ('SIMSEC','NO','LANE\\LINK\\NO','LANE\\INDEX','POS')}
                break
        else:raise ValueError('Missing FZP header')
        for raw in stream:
            digest.update(raw)
            t=float(raw.split(b';',1)[0])
            if t<T0-150-1e-5:continue
            if t>T0+1e-5:break
            if stamp is not None and t!=stamp:
                assert abs(t-stamp-5)<1e-5
                flush(stamp,frame);frame={}
            stamp=t
            x=raw.split(b';')
            if int(x[ix['LANE\\LINK\\NO']])==2:
                frame[int(x[ix['NO']])]=(float(x[ix['POS']]),int(x[ix['LANE\\INDEX']]))
    flush(stamp,frame)
    assert frames==31 and abs(stamp-T0)<1e-6
    assert (source.st_size,source.st_mtime_ns)==(FZP.stat().st_size,FZP.stat().st_mtime_ns)
    # All same-link crossings at this interior station. Check against the
    # previously validated aggregate boundary count without scanning again.
    with (H/'observations/hold/flows_30s.csv').open(encoding='utf-8-sig',newline='') as f:
        total=sum(float(r['downstream_crossings']) for r in csv.DictReader(f)
            if r['road']=='FW_E' and int(r['cell'])==11 and T0-150+1e-5<float(r['window_end_s'])<=T0+1e-5)
    assert total==len(events),(total,len(events))
    counts={key:[sum(e[key]==lane for e in events) for lane in range(1,5)] for key in ('from_lane','to_lane')}
    out=dict(source=str(FZP),source_bytes=source.st_size,source_mtime_ns=source.st_mtime_ns,
        data_prefix_sha256=digest.hexdigest(),window=[T0-150,T0],position_m=POSITION,link=2,
        counts=counts,aggregate_validated_count=total,events=events,
        lane_ambiguous=sum(e['from_lane']!=e['to_lane'] for e in events),
        caveat='Five-second lane brackets, not exact native DCM; both endpoints tested if different.')
    save(OUT/'causal_counts.json',out)
    return out


def metrics(pred):
    times=[round(T0+t,6) for t in range(0,451,30)]
    main={t:sum(x['n_veh'] for x in pred['cells'] if abs(x['time_s']-t)<1e-6) for t in times[1:]}
    port={t:sum(x['n_veh'] for x in pred['ports'] if abs(x['time_s']-t)<1e-6)
        +sum(x['end']['connector_veh'] for x in pred['ramps'] if abs(x['end_sec']-t)<1e-6) for t in times[1:]}
    # All arms have the same microscopic initial frame; use the saved result
    # to recover its common initial stock from the first receipt / first port.
    main[T0]=sum(x['n_veh'] for x in args_initial if x['road']=='FW_E')
    port[T0]=sum(len(v) for k,v in initial_ports.items() if k in ('10481','10483','10643','10682'))
    port[T0]+=sum(len(v['initial_cohorts']) for k,v in initial_ramps.items() if k in east_ramps)
    integrate=lambda d:sum((d[a]+d[b])*(b-a)/7200 for a,b in zip(times,times[1:]))
    residual=max(abs(x['conservation_residual_veh']) for x in pred['ports']+pred['ramps'])
    assert residual<1e-7
    return dict(main=integrate(main),ports=integrate(port),component=integrate(main)+integrate(port),
        merges={r:sum(x['accepted_merge_veh'] for x in pred['ramps'] if x['ramp']==r) for r in east_ramps},
        conservation_max=residual)


if __name__=='__main__':
    OUT.mkdir(exist_ok=False)
    counts=load(HERE/'seed53/causal_counts.json') if ABLATION else prior_counts()
    ctx=load_sources(H/'candidate_manifest.json');model=ctx['component']
    wave=load(HERE/'candidate_config.json')['freeway']['ramp_posthead_receiving'][RID]['wave_speed_kmh']
    capture=load(H/'capture.json');actual=load(H/'prediction_summary.json')
    records=[];regression=[]
    modes=['from_lane']+(['to_lane'] if not ABLATION and counts['counts']['from_lane']!=counts['counts']['to_lane'] else [])
    for record in capture['records']:
        arm=record['arm'];args,kwargs=read_primitive_capture(record['input'],record['sha256'])
        # Both the total discharge and retained state must stay identical with
        # the option disabled, not merely a similar aggregate TTT.
        if not ABLATION:
            pred=model.rollout(*args,**kwargs)
            with gzip.open(H/f'candidate/{arm}_prediction.json.gz','rt',encoding='utf-8') as f:old=json.load(f)
            pred=json.loads(json.dumps(pred))
            parity={k:pred[k]==old[k] for k in ('cells','flows','ports','ramps')}
            assert all(parity.values()),(arm,parity)
            regression.append(dict(arm=arm,arrays_exact=parity))
        args_initial=args[0];initial_ports=kwargs['port_dynamics']['initial_cohorts'];initial_ramps=kwargs['ramp_dynamics']['ramps']
        east_ramps={r for r,v in model.ramps.items() if v['road']=='FW_E'}
        cfg=model._config('FW_E',args[2]['by_direction'].get('FW_E',{}));net=cfg.network
        upstream=net.ramp_merge_segment_index[RID]-1;assert upstream==11
        row=next(r for r in args[0] if r['road']=='FW_E' and r['cell']==upstream)
        split=sum(args[1][0]['off_split_ratio'][o] for o in net.off_ramps if net.off_ramp_segment_index[o]==upstream)
        reference=row['n_veh']/model.geometry_cells['FW_E',upstream]['lane_km']*row['v_kmh']*(1-split)
        assert reference>0
        if ABLATION!='anchor_only':kwargs['ramp_dynamics']['ramps'][RID]['posthead_wave_speed_kmh']=wave
        for mode in modes:
            factors=[n*24/reference for n in counts['counts'][mode][:2]]
            if ABLATION!='wave_only':kwargs['ramp_conflict_factors']={RID:factors}
            begin=time.perf_counter();pred=model.rollout(*args,**kwargs);wall=time.perf_counter()-begin
            with gzip.open(OUT/f'{arm}_{mode}.json.gz','wt',encoding='utf-8') as f:json.dump(pred,f,allow_nan=False)
            m=metrics(pred);truth=next(r for r in actual['rows'] if r['family']=='candidate' and r['arm']==arm)
            m.update(arm=arm,mode=mode,wall_sec=wall,factors=factors,reference_vph=reference,
                actual_component=truth['actual_component'],actual_merges=truth['actual_merges'],
                previous_component=truth['predicted_component'],previous_merges=truth['predicted_merges'])
            records.append(m);print(json.dumps(m),flush=True)
    for mode in modes:
        held=next(r for r in records if r['mode']==mode and r['arm']=='hold')
        for r in records:
            if r['mode']==mode:r.update(predicted_delta=r['component']-held['component'],
                actual_delta=r['actual_component']-held['actual_component'],previous_delta=r['previous_component']-held['previous_component'])
    save(OUT/'summary.json',dict(records=records,default_off_regression=regression,seed=53,wave_speed_kmh=wave,
        ablation=ABLATION,refit=False,new_native=0,future_input=False,production_adopted=False,
        scope='East31cells+4on/4off connectors, matching earlier component scoring; not complete Omega or outside waiting.',
        counts='causal_counts.json',script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
