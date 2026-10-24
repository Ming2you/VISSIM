"""Short, causal fixed-lane startup feasibility check on saved native states.

This is not a Wiedemann implementation or a production controller adapter.
All packets are initial vehicles; no future arrivals, lane changes or positions
are injected. Future records are consulted ONLY to score these predictions.
"""
from pathlib import Path
from collections import defaultdict,Counter
import sys,copy,math,hashlib,statistics,xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import downstream_wave_audit as d


def native_parameters(path):
    root=ET.parse(path).getroot()
    link=root.find('./links/link[@no="24"]')
    behavior_type=root.find('./linkBehaviorTypes/linkBehaviorType[@no="'+link.get('linkBehavType')+'"]')
    behavior=root.find('./drivingBehaviors/drivingBehavior[@no="'+behavior_type.get('drivBehavDef')+'"]')
    assert behavior.get('carFollowModType')=='WIEDEMANN99'
    dist=root.find('./timeDistributions/timeDistribution[@no="'+behavior.get('w99cc1Distr')+'"]')
    assert dist.get('type')=='NORMAL' and float(dist.get('stdDev'))==0
    geometries={x.get('no'):x for x in root.findall('./models2D3D/model2D3D')}
    distributions={x.get('no'):x for x in root.findall('./model2D3DDistributions/model2D3DDistribution')}
    curves={x.get('no'):[(float(p.get('x')),float(p.get('y'))) for p in x.findall('./accelFuncDataPts/accelerationFunctionDataPoint')]
            for x in root.findall('./desAccelerationFunctions/desAccelerationFunction')}
    by_length={}
    for vt in root.findall('./vehicleTypes/vehicleType'):
        if vt.get('category') not in ('CAR','HGV','BUS'):continue
        for el in distributions[vt.get('model2D3DDistr')].findall('./model2D3DDistrEl/model2D3DDistributionElement'):
            pieces=geometries[el.get('model2D3D')].findall('./model2D3DSegs/model2D3DSegment')
            if len(pieces)!=1:raise ValueError('Unspecified multi-body length')
            length=round(float(pieces[0].get('length')),3)
            definition=dict(category=vt.get('category'),curve=curves[vt.get('desAccelFunc')])
            if length in by_length:assert by_length[length]==definition
            by_length[length]=definition
    return dict(stand_m=float(behavior.get('w99cc0')),headway_s=float(dist.get('mean')),
                vehicle_by_length=by_length,position_convention='FZP Pos is front edge; gap subtracts LEADER length',
                approximation='Mean native desired acceleration curve, not full W99 CC/stochastic/power rules')


def acceleration(v,curve):
    x=3.6*v
    for (a,b),(c,f) in zip(curve,curve[1:]):
        if x<=c:return max(0.,b+(f-b)*max(0.,x-a)/(c-a))
    return max(0.,curve[-1][1])


def rollout(initial,parameters,horizon,bounded=True,step=.2):
    """Finite acceleration with old-state gap response and order.

    The leader's predicted new position enforces body separation; no future
    native leader positions are read. Initial bodies are never repositioned.
    """
    vehicles=copy.deepcopy(initial);states={0:copy.deepcopy(vehicles)};checks=0
    stand,headway=parameters['stand_m'],parameters['headway_s']
    substeps=round(1/step)
    assert abs(substeps*step-1)<1e-9
    for tick in range(1,horizon*substeps+1):
        old=copy.deepcopy(vehicles)
        for lane in (1,2,3):
            order=sorted((i for i,v in old.items() if v['lane']==lane),key=lambda i:old[i]['pos'],reverse=True)
            for j,vid in enumerate(order):
                v=old[vid];speed=v['v']/3.6;desired=v['desired']/3.6
                a=acceleration(speed,parameters['vehicle_by_length'][round(v['length'],3)]['curve'])
                u=min(desired,speed+a*step) if bounded else desired
                if j:
                    lead=old[order[j-1]];gap=lead['pos']-lead['length']-v['pos']
                    if gap < -1e-6:raise ArithmeticError('Initial or predicted same-lane bodies overlap')
                    margin=min(stand,gap)
                    # Native short initial gaps may be below CC0; do not move
                    # vehicles backwards to manufacture the desired spacing.
                    u=min(u,max(0.,(gap-margin)/headway))
                    room=vehicles[order[j-1]]['pos']-lead['length']-margin-v['pos']
                    if .5*speed*step>room+1e-7:raise ArithmeticError('Gap rule requires unmodelled emergency braking')
                    u=min(u,max(0.,2*room/step-speed))
                x=v['pos']+.5*(speed+u)*step
                vehicles[vid].update(pos=x,v=u*3.6)
                assert x>=v['pos'] and u>=0 and math.isfinite(x)
                if bounded:assert u<=speed+a*step+1e-7
                if j:assert vehicles[order[j-1]]['pos']-lead['length']-x>=margin-1e-7
                checks+=1
        assert set(vehicles)==set(initial)
        if tick%substeps==0:states[tick//substeps]=copy.deepcopy(vehicles)
    return states,checks


def release_time(states,vid,limit=5.):
    return next((s for s in sorted(states) if s>0 and vid in states[s] and states[s][vid]['v']>=limit),None)


def cases(frames,parameters,arm):
    records=[];failures=[];checks=0
    for start in range(900,2821,30):
        all_initial={i:copy.deepcopy(v) for i,v in frames[start].items() if v['link']==24}
        targets=[i for i,v in all_initial.items() if v['v']<1 and 800<=v['pos']<=3250]
        if not targets:continue
        # Predict each whole initial lane; neighboring-lane incursions are a
        # scored omission, never replayed from future observations.
        for lane in sorted({all_initial[i]['lane'] for i in targets}):
            initial={i:v for i,v in all_initial.items() if v['lane']==lane}
            by_mode={}
            for mode,bounded in (('gap_only',False),('gap_acceleration',True)):
                try:
                    result,n=rollout(initial,parameters,20,bounded);by_mode[mode]=result;checks+=n
                except (ArithmeticError,KeyError) as exc:
                    failures.append(dict(start_s=start,lane=lane,mode=mode,targets=[i for i in targets if all_initial[i]['lane']==lane],reason=str(exc)))
            if not by_mode:continue
            for vid in targets:
                if initial.get(vid) is None:continue
                obs={dt:{vid:frames[start+dt][vid]} for dt in range(21) if vid in frames[start+dt]}
                if len(obs)!=21:
                    failures.append(dict(start_s=start,vehicle=vid,reason='Scoring window incomplete'));continue
                future_changes=any(obs[dt][vid]['lane']!=lane or obs[dt][vid].get('lane_change')!='None' for dt in range(21))
                initial_order=sorted(initial,key=lambda i:initial[i]['pos']);rank=initial_order.index(vid)
                initial_leader=initial_order[rank+1] if rank+1<len(initial_order) else None
                leader_changes=initial_leader is not None and any(
                    initial_leader not in frames[start+dt] or frames[start+dt][initial_leader]['lane']!=lane or
                    frames[start+dt][initial_leader].get('lane_change')!='None' for dt in range(21))
                actual=release_time(obs,vid)
                record=dict(arm=arm,start_s=start,vehicle=vid,lane=lane,category=parameters['vehicle_by_length'][round(initial[vid]['length'],3)]['category'],
                    initial_speed=initial[vid]['v'],initial_position=initial[vid]['pos'],
                    actual_release_s=actual,own_lane_change_in_scoring_window=future_changes,
                    initial_leader=initial_leader,leader_lane_change_in_scoring_window=leader_changes,
                    future_flags_used_for_prediction=False,predictions={})
                for mode,result in by_mode.items():
                    pred=release_time(result,vid)
                    record['predictions'][mode]=dict(release_s=pred,
                        final_position_error_m=result[20][vid]['pos']-obs[20][vid]['pos'],
                        speed_rmse_kmh=math.sqrt(sum((result[t][vid]['v']-obs[t][vid]['v'])**2 for t in range(1,21))/20),
                        short_residence_seconds=sum(result[t][vid]['pos']<initial[vid]['pos']+100 for t in range(1,21)))
                records.append(record)
    return records,failures,checks


def summarize(records):
    result={}
    for mode in ('gap_only','gap_acceleration'):
        supported=[r for r in records if mode in r['predictions']]
        both=[r for r in supported if r['actual_release_s'] is not None and r['predictions'][mode]['release_s'] is not None]
        result[mode]=dict(n=len(supported),actual_release=sum(r['actual_release_s'] is not None for r in supported),
            predicted_release=sum(r['predictions'][mode]['release_s'] is not None for r in supported),both_release=len(both),
            release_mae_s=statistics.mean(abs(r['actual_release_s']-r['predictions'][mode]['release_s']) for r in both) if both else None,
            speed_rmse_kmh=math.sqrt(statistics.mean(r['predictions'][mode]['speed_rmse_kmh']**2 for r in supported)) if supported else None,
            position_mae_m=statistics.mean(abs(r['predictions'][mode]['final_position_error_m']) for r in supported) if supported else None)
    return result


def main():
    out=d.HERE/'downstream_restart_v3';out.mkdir(exist_ok=False)
    network=d.H/'source_dsd/baseline.inpx';params=native_parameters(network)
    results={};all_records={};receipts={}
    for arm in ('none','vsl'):
        path=d.HERE/f'route_state_native_v1/{arm}_s23/run_retry1/vissim_eval/baseline_001.fzp'
        # Reuse the already checked reader on an explicit longer historical
        # interval. Its module constants are restored before any model call.
        saved_start=d.START
        try:
            d.START=1050 # Reader includes150s before START:900..2850.
            frames,receipts[arm]=d.extract(path,True)
        finally:d.START=saved_start
        assert set(frames)==set(range(900,2851)) and d.START==2400
        records,failures,checks=cases(frames,params,arm)
        all_records[arm]=records
        results[arm]=dict(all=summarize(records),records=records,unsupported=failures,physics_checks=checks,
                         precontrol=summarize([r for r in records if r['start_s']+20<=2400]),
                         postcontrol=summarize([r for r in records if r['start_s']>=2400]),
                         no_own_or_initial_leader_change=summarize([r for r in records if not r['own_lane_change_in_scoring_window'] and not r['leader_lane_change_in_scoring_window']]))
        results[arm]['common_supported']=summarize([r for r in records if len(r['predictions'])==2])
        print(arm,results[arm]['all'],'unsupported',len(failures),'checks',checks,flush=True)
    before=lambda rs:[{k:v for k,v in r.items() if k!='arm'} for r in rs if r['start_s']+20<=2400]
    assert before(all_records['none']), 'No precontrol startup cases: equality would be vacuous'
    assert before(all_records['none'])==before(all_records['vsl'])
    paths=[Path(__file__),Path(d.__file__),network]
    d.e.save(out/'result.json',dict(status='SHORT_LOCAL_PREDICTION_NOT_QUALIFIED',results=results,parameters=params,
        sources=receipts,pins={str(p.relative_to(d.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        future_inputs=False,new_native_runs=0,core_changes=False,qualified=False,
        limitations=['Fixed initial lanes; no new cut-ins, new arrivals or route reassignment.',
            'Unsupported initial overlap/emergency braking cases are explicit failures, not silently projected.',
            'No actual RM length/desire record is invented; this pilot uses NC and VSL20-column recordings.',
            'Native mean desired acceleration is an approximation; CC8/CC9 and random driver dynamics are not reproduced.',
            'Repeated30s cutoffs are correlated; neither20s release nor this inspected seed proves450s gain.'],
        references=['https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/4_BasisdatenSim/FahrverhaltensparameterFolgeverh_Wied99.htm',
                    'https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/5_Netzbearbeiten/Detektoren_Attr.htm']))


if __name__=='__main__':main()
