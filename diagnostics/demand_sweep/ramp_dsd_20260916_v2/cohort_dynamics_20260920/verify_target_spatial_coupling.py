"""Saved-record validation of spatial representation and rejected rollouts."""
from pathlib import Path
import ast
import hashlib
import json
import math
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import target_acceleration_coupling as c
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import target_spatial_representation as p

K,e,s=c.K,c.e,c.s


def close(a,b):
    assert math.isfinite(a) and math.isfinite(b) and abs(a-b)<1e-8,(a,b)


def main():
    pins=archived=traces=balances=0
    spatial=e.load(p.OUT/'result.json')
    memory=e.load(c.OUT/'result.json')
    scale=e.load(K/'physical_response_scale_v1/result.json')
    for result in (spatial,memory,scale):
        assert not result['qualified'] and not result['production_adopted'] and result['new_native_runs']==0
        for name,digest in result['source_pins'].items():
            path=s.d.ROOT/name
            if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
                assert path.name=='downstream_spatial_rollout.py'
                assert hashlib.sha256((c.OUT/'source_before_response_scale.py').read_bytes()).hexdigest()==digest
                archived+=1
            pins+=1
    old=e.load(K/'target_history_audit_v1/result.json')
    for period,modes in spatial['scores'].items():
        for key in ('existing','target_history_bin'):
            for h,row in modes[key].items():assert row==old['scores'][period][h][key]
    rows=e.load(c.OUT/'training_rows.json');fit=e.load(c.OUT/'fit.json')
    assert sorted({r['t'] for r in rows})==list(range(930,2091))
    assert fit['skipped_training_snapshots']=={}
    refit=c.fit(rows)
    for variant in ('base','self_only','coupled'):
        for key in ('self_weight','forward_weight','training_mse'):close(refit[variant][key],fit[variant][key])
    obs=e.load(K/'compact_lane_state_v1/states.json');bank=e.load(c.OUT/'initials.json')
    worse_memory=worse_scale30=worse_scale150=0
    for result,folder in ((memory,c.OUT),(scale,K/'physical_response_scale_v1')):
        for row in result['runs']:
            arm,start=row['arm'],row['start_s'];variant=row.get('variant',row.get('response'))
            assert row.get('status','completed')=='completed'
            trace=e.load(folder/f'{arm}_{start}_{variant}.json');initial=bank[arm][str(start)]['inputs']
            n0=sum(map(sum,initial['n']));rate=sum(initial['arrivals'])
            for j,frame in enumerate(trace,1):
                assert frame['step']==j
                close(sum(v['n'] for v in frame['cells'].values())+frame['queue']+frame['exits'],n0+j*rate)
                assert all(v['n']>=-1e-9 and math.isfinite(v['v']) and v['v']>=0 for v in frame['cells'].values())
                balances+=1
            for length,expected in ((30,row),) if result is memory else ((30,row['prefix30']),(150,row['full150'])):
                actual=c.score(trace[:length],obs,arm,start)
                for key in ('speed_rmse','stock_mae','local_ttt','actual_ttt'):close(actual[key],expected[key])
            if result is memory and variant=='coupled':
                base=next(r for r in result['runs'] if r['arm']==arm and r['start_s']==start and r['variant']=='base')
                worse_memory+=row['speed_rmse']>base['speed_rmse']
            elif result is scale and variant=='physical_cell':
                base=next(r for r in result['runs'] if r['arm']==arm and r['start_s']==start and r['response']=='transport')
                worse_scale30+=row['prefix30']['speed_rmse']>base['prefix30']['speed_rmse']
                worse_scale150+=row['full150']['speed_rmse']>base['full150']['speed_rmse']
                baseline=e.load(folder/f'{arm}_{start}_transport.json')
                for key in ('queue','exits'):close(trace[0][key],baseline[0][key])
                for cell,v in trace[0]['cells'].items():close(v['n'],baseline[0]['cells'][cell]['n'])
            traces+=1
    # Pure-current geometry and forward exposure contracts, without native IDs
    # in the forward-field operator and without future input dependencies.
    assert s.forward_acceleration([[1.],[3.],[7.]],[[2.],[0.],[1.]])==[[4.],[7.],[None]]
    geometry=dict(chains={'FW_E':[dict(link=119,offset_m=0.)]},cells=[dict(road='FW_E',cell=0,start_m=0.,end_m=200.,length_km=.2)])
    geo,bins=p.grid(geometry)
    now={1:dict(link=119,lane=1,pos=20.,v=100.,target=2),2:dict(link=119,lane=1,pos=60.,v=90.,target=3),3:dict(link=119,lane=1,pos=130.,v=80.,target=None)}
    prev={1:dict(v=99.),2:dict(v=95.),3:dict(v=78.)}
    records=[dict(time_s=900,vehicle=1,cell=0),dict(time_s=900,vehicle=2,cell=0)]
    p.attach(records,{899:prev,900:now},geometry,geo,bins)
    assert [r['forward_lane100m_bin'] for r in records]==[1,3]
    canary=[dict(time_s=900,vehicle=1,cell=0),dict(time_s=900,vehicle=2,cell=0)]
    p.attach(canary,{899:prev,900:now,901:{1:dict(v=99999.)}},geometry,geo,bins)
    assert canary==records
    core=['evaluation/controllers/physical_lane_groups.py','evaluation/controllers/physical_ramp_boundary.py',
        'evaluation/controllers/vissim_stackelberg_adapter.py',
        'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py']
    for name in core:assert subprocess.check_output(['git','show','fbdbeed:'+name],cwd=s.d.ROOT)==(s.d.ROOT/name).read_bytes()
    for path in (Path(__file__),Path(c.__file__),Path(p.__file__),Path(s.__file__),K/'check_response_scale.py'):
        ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
    result=dict(passed=True,qualified=False,source_pins=pins,archived_sources_resolved=archived,
        frozen_conditional_scores_exact=spatial['old_scores_exact'],training_rows_refit=len(rows),
        training_timestamps=1161,saved_traces_checked=traces,mass_balances=balances,
        coupled_worse_cases=worse_memory,physical_scale_worse_30s=worse_scale30,physical_scale_worse_150s=worse_scale150,
        original_default_traces_exact=memory['default_traces_exact'],zero_weight_traces_exact=memory['zero_weight_traces_exact'],
        physical_scale_default_prefixes_exact=scale['default30s_traces_exact'],core_unchanged_from='fbdbeed',
        native_started=False,forecasts_recomputed=False,
        previous_goal_turn='progress: duration rejected and current target acceleration dependence identified',
        current_goal_turn='progress: spatial representation verified, autonomous coupling and force-scale candidates rejected',
        completed_owned_sessions={'64859':'exit0 representation','7972':'exit0 coupling'},goal_status='active; NOT_QUALIFIED',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    destination=K/'physical_response_scale_v1/verification.json'
    if destination.exists():assert e.load(destination)==result
    else:e.save(destination,result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
