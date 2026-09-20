"""Diagnostic future upstream boundary isolation; never a causal forecast."""
from pathlib import Path
import copy
import hashlib
import json
import math
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import downstream_spatial_rollout as s
K=Path(__file__).resolve().parent
ROOT=K.parents[3]


def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def boundaries(frames,start,mode,initial,kind):
    groups=len(initial['n'][0]);result=[];events=[]
    for t in range(start+1,start+151):
        before=frames[t-1];after=frames[t]
        up=[[] for _ in range(groups)];entry=[[] for _ in range(groups)]
        for r in before.values():
            if r['cell']==14:up[0 if groups==1 else r['lane']-1].append(r['v'])
        assert all(up),(t,'unobserved upstream lane')
        for vid,r in after.items():
            if r['cell']<15:continue
            a=before.get(vid)
            assert a is not None,(t,vid,'unexplained region entry')
            if a['cell']==14:
                g=0 if groups==1 else r['lane']-1
                entry[g].append(a['v'])
                events.append(dict(time_s=t,vehicle=vid,lane=r['lane'],previous_speed_kmh=a['v']))
        velocities=[sum(vs)/len(vs) for vs in up]
        speeds=[sum(vs)/len(vs) if vs else velocities[g] for g,vs in enumerate(entry)]
        if kind=='observed_count_only':velocities=initial['upstream'];speeds=initial['upstream']
        result.append(dict(arrivals=[len(vs) for vs in entry],upstream=velocities,entry_speed=speeds))
    return result,events


def main():
    out=K/'downstream_boundary_probe_v1';out.mkdir(exist_ok=False)
    gp=s.d.H/'controller_response_s23_v1/none/geometry.json';geometry=load(gp)
    config=K/'transport_step1_exchange_off_v2/config.json';pp=K/'port_travel_fit_v1/selected_parameters.json'
    model=s.d.e.load_base_model(geometry,config);cfg=model._config('FW_E',load(pp)['parameters']['by_direction']['FW_E'])
    inputs_path=K/'downstream_spatial_rollout_v1/inputs.json';inputs=load(inputs_path)
    obs_path=K/'compact_lane_state_v1/states.json';observations=load(obs_path)
    runs=[];prefixes=0;entry_checks=0;receipts={};saved_boundaries={}
    for arm in ('none','rm_ramp'):
        path=K/'route_state_native_v1'/('none_s23/run_retry1' if arm=='none' else 'rm_ramp_s23/run')/'vissim_eval/baseline_001.fzp'
        raw,receipts[arm]=s.d.extract(path,True);frames=s.locate(raw,geometry);del raw
        for start in (2400,2550,2700):
            for mode in ('coarse','lane_100m'):
                key=f'{arm}_{start}_{mode}';initial=copy.deepcopy(inputs[key]['inputs'])
                initial['rates']={int(k):v for k,v in initial['rates'].items()}
                for kind in ('history','observed_count_only','observed_boundary'):
                    sequence=None
                    if kind!='history':
                        sequence,events=boundaries(frames,start,mode,initial,kind)
                        for j,b in enumerate(sequence):
                            assert sum(b['arrivals'])==observations[arm]['entry'][str(start+j+1)]
                            entry_checks+=1
                        saved_boundaries[key+'_'+kind]=dict(sequence=sequence,events=events)
                    trace,checks=s.rollout(initial,cfg,150,momentum_advection=mode=='lane_100m',boundary_steps=sequence)
                    trace=json.loads(json.dumps(trace))
                    if kind=='history':
                        assert trace==load(K/'downstream_spatial_horizon_v1'/(key+'.json'));prefixes+=1
                    # If an oracle vehicle waits outside, retaining just its
                    # mean incoming velocity needs a queue moment/FIFO state.
                    # Fail that unimplemented case, rather than call it exact.
                    if kind=='observed_boundary':assert max(r['queue'] for r in trace)<1e-9
                    se=[];ne=[];ttt=actual=0.
                    for r in trace:
                        obs=observations[arm]['states'][str(start+r['step'])]
                        for c,value in r['cells'].items():
                            se.append(value['v']-obs[c]['v']);ne.append(value['n']-obs[c]['n'])
                            ttt+=value['n']/3600;actual+=obs[c]['n']/3600
                    row=dict(arm=arm,start=start,mode=mode,kind=kind,
                        speed_rmse=math.sqrt(sum(x*x for x in se)/len(se)),speed_bias=sum(se)/len(se),
                        stock_mae=sum(abs(x) for x in ne)/len(ne),predicted_ttt=ttt,actual_ttt=actual,
                        max_queue=max(r['queue'] for r in trace),checks=checks)
                    runs.append(row)
                    if kind!='history':s.d.e.save(out/(key+'_'+kind+'.json'),trace)
                    print(arm,start,mode,kind,round(row['speed_rmse'],4),flush=True)
    response=[]
    for start in (2400,2550,2700):
        for mode in ('coarse','lane_100m'):
            for kind in ('history','observed_count_only','observed_boundary'):
                a=next(r for r in runs if (r['arm'],r['start'],r['mode'],r['kind'])==('none',start,mode,kind))
                b=next(r for r in runs if (r['arm'],r['start'],r['mode'],r['kind'])==('rm_ramp',start,mode,kind))
                response.append(dict(start=start,mode=mode,kind=kind,predicted_delta_ttt=b['predicted_ttt']-a['predicted_ttt'],
                    actual_delta_ttt=b['actual_ttt']-a['actual_ttt']))
    s.d.e.save(out/'boundaries.json',saved_boundaries)
    files=[Path(__file__),Path(s.__file__),gp,config,pp,inputs_path,obs_path]
    s.d.e.save(out/'result.json',dict(qualified=False,status='FUTURE_BOUNDARY_ISOLATION_ONLY',
        runs=runs,response=response,history_traces_exact=prefixes,observed_entry_counts_checked=entry_checks,
        new_native_runs=0,production_changes=0,source_receipts=receipts,
        source_pins={p.relative_to(ROOT).as_posix():sha(p) for p in files},
        limitations=['Future observed boundary counts/speeds are diagnostic inputs, not available causal controller forecasts.',
            'Interior states and terminal exits are predicted, not reset to future observations.',
            'Lateral rates still fixed from cutoff history; no future route/target/lane-change inputs.',
            'No full450s, VSL or fresh-seed qualification.']))


if __name__=='__main__':main()
