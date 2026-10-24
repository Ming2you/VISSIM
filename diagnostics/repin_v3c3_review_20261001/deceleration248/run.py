"""Bounded negative-relaxation calibration in the current coupled plant.

Uses the existing recorded-command initializer and scalar rollout endpoint.
Runtime sources and the live frozen native experiment are never edited.
"""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
import copy
from contextlib import contextmanager
import ctypes
import json
import math
from pathlib import Path
import sys
import time
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent/'verified'
CAPTURES={}
RESULTS=[]


def save(name,value):h.save(HERE/name,value)


@contextmanager
def negative_relaxation(ratio,stats):
    from evaluation.controllers import freeway_fd as fd
    old=fd.state_response_coefficients
    def changed(spec,speed,desired,rho,downstream,critical,tau_h,nu):
        tau,value=old(spec,speed,desired,rho,downstream,critical,tau_h,nu)
        cell=spec.get('_deceleration248_cell')
        if cell is not None:
            assert cell in (24,25)
            record=stats.setdefault(str(cell),dict(calls=0,changed=0,base_relaxation_sum=0.,new_relaxation_sum=0.,pressure_ratio_max_error=0.))
            record['calls']+=1
            if desired<speed:
                record['changed']+=1
                record['base_relaxation_sum']+=(desired-speed)/(tau*3600)
                record['new_relaxation_sum']+=ratio*(desired-speed)/(tau*3600)
                record['pressure_ratio_max_error']=max(record['pressure_ratio_max_error'],abs((value/ratio)/(tau/ratio)-value/tau))
                # Preserve anticipation nu/tau; only the negative relaxation
                # contribution changes. No new target, capacity or reward.
                if ratio!=1.:return tau/ratio,value/ratio
        return tau,value
    fd.state_response_coefficients=changed
    try:yield
    finally:
        assert fd.state_response_coefficients is changed
        fd.state_response_coefficients=old


def commands(action,cfg):
    from evaluation.controllers import sdmpc_sequence as seq
    return [dict(vsl=a.vsl,green_times=a.green_times,offsets=a.offsets,
        meters={r:a.diagnostics['rw_meter_green_'+r] for r in cfg.network.ramps}) for a in seq.actions(action,3)]


def forecast(tag,arm,ratio,label):
    from evaluation.controllers import sdmpc_sequence as seq
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.freeway_fd import cell_state_response
    from src.controllers import rollout_endpoint as endpoint
    captured,candidates,coord=CAPTURES[tag]
    original=captured['state'];state=copy.deepcopy(original);cfg=captured['cfg'];action=candidates[arm]
    validation=coord.validate(action)
    kernel=state.lane_freeway_runtime.configs['FW_E'];net=kernel.network
    before=copy.deepcopy(net.freeway_state_response)
    spec=net.freeway_state_response['FW_E']
    for cell in (24,25):
        local=copy.deepcopy(cell_state_response(net,'FW_E',cell))
        local['_deceleration248_cell']=cell
        spec.setdefault('cell_overrides',{})[str(cell)]=local
    for cell in range(31):
        actual=cell_state_response(net,'FW_E',cell)
        previous=before['FW_E'].get('cell_overrides',{}).get(str(cell),before['FW_E'])
        assert {k:v for k,v in actual.items() if k!='_deceleration248_cell'}==previous
    initial=model_inventory(state,cfg);get_ledger(state).assert_stocks(initial)
    stats={};started=time.perf_counter()
    with negative_relaxation(ratio,stats),seq.prediction_scope(action,cfg,state.time_sec,3) as visits:
        point=endpoint.evaluate_price_point(state,action,copy.deepcopy(captured['forecast']),(),
            endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
    assert visits==[0,1,2] and not point.aborted and len(point.states)==3
    assert set(stats)=={'24','25'} and all(s['calls']>=450 for s in stats.values())
    assert all(s['pressure_ratio_max_error']<1e-7 for s in stats.values())
    response=point.control_area_response;costs={};outside={};residence=[];durations={}
    for r in response['residence']:
        for key,n in r['inside_veh'].items():
            durations[key]=durations.get(key,0.)+r['dt_h']*3600
            costs[key]=costs.get(key,0.)+r['dt_h']*n
            out=r['model_stock_veh'][key]-n;assert out>=-1e-7
            outside[key]=outside.get(key,0.)+r['dt_h']*max(0.,out)
        residence.append(dict(time=r['end_sec'],dt_h=r['dt_h'],inside_total=sum(r['inside_veh'].values()),
            stock_keys=list(r['inside_veh']),
            east=r['inside_veh'].get('freeway:FW_E',0.),west=r['inside_veh'].get('freeway:FW_W',0.),
            ramps=sum(v for k,v in r['inside_veh'].items() if k.startswith('ramp:'))))
    assert abs(sum(costs.values())-point.ttt)<1e-7
    transfers={}
    for t in response['transfers']:
        key=(t['source'],t['target']);transfers[key]=transfers.get(key,0.)+t['vehicles']
    ramps={}
    for ramp in cfg.network.ramps:
        arrival=sum(v for (s,t),v in transfers.items() if t=='ramp:'+ramp)
        merged=transfers.get(('ramp:'+ramp,'merge_pending:'+ramp),0.)
        end=point.states[-1].ramp_queue[ramp]
        error=state.ramp_queue[ramp]+arrival-merged-end;assert abs(error)<1e-7
        ramps[ramp]=dict(initial=state.ramp_queue[ramp],arrival=arrival,merge=merged,final=end,residual=error)
    snapshots=[]
    for s in (state,*point.states):
        inv=model_inventory(s,cfg);get_ledger(s).assert_stocks(inv)
        snapshots.append(dict(time=s.time_sec,inventory=inv,speed={r:list(v) for r,v in s.freeway_speed.items()},
            density={r:list(v) for r,v in s.freeway_density.items()}))
    maximum=max((r['exceedance_veh'] for r in response['resource_allocations']),default=0.)
    assert maximum<1e-7
    assert model_inventory(original,cfg)==initial
    assert original.freeway_speed==state.freeway_speed
    assert original.lane_freeway_runtime.configs['FW_E'].network.freeway_state_response==before
    item=dict(tag=tag,arm=arm,label=label,ratio=ratio,seconds=time.perf_counter()-started,ttt=point.ttt,
        cost_by_stock=costs,tracked_outside=sum(outside.values()),outside_by_stock=outside,
        east_ttt=costs['freeway:FW_E'],ramps_ttt=sum(v for k,v in costs.items() if k.startswith('ramp:')),
        east_terminal=transfers.get(('freeway:FW_E','external:terminal:FW_E'),0.),
        east_final=snapshots[-1]['inventory']['freeway:FW_E'],ramps=ramps,snapshots=snapshots,
        commands=commands(action,cfg),validation=validation,resource_max=maximum,relaxation=stats,
        residence=residence,residence_duration_sec=durations,
        transfers=[dict(source=s,target=t,vehicles=v) for (s,t),v in transfers.items()])
    assert len(RESULTS)<18
    RESULTS.append(item);save(f'{tag}_{label}_{arm}.json',item)
    save('progress.json',dict(stage='forecast_complete',count=len(RESULTS),tag=tag,arm=arm,label=label,ratio=ratio))
    print(json.dumps({k:item[k] for k in ('tag','arm','label','ratio','ttt','seconds')}),flush=True)
    return item


def pair(tag,ratio,label):
    return [forecast(tag,a,ratio,label) for a in ('release_actual','release_vsl90_actual')]


def actual67():
    d=h.read(h.R/'s67_full_observation/response_assessment76.json')
    a=d['arms']['release']['mainline']['FW_E']['actual'];b=d['arms']['release_vsl90']['mainline']['FW_E']['actual']
    target=[d['actual_delta_omega_veh_h']/2,d['component_delta_veh_h']['FW_E']['actual']/2,
            d['component_delta_veh_h']['ramps']['actual'],a['terminal']/50,b['terminal']/50,a['final_stock']/50,b['final_stock']/50]
    return target


def vector(pair):
    a,b=pair
    return [(b['ttt']-a['ttt'])/2,(b['east_ttt']-a['east_ttt'])/2,b['ramps_ttt']-a['ramps_ttt'],
            a['east_terminal']/50,b['east_terminal']/50,a['east_final']/50,b['east_final']/50]


def prepare_inputs():
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
    from evaluation.controllers import obs150_contract as oc
    original_probe=probe.probe_levers;original_writer=oc.write_derived
    def existing(raw,derived):
        obs=raw[oc.RAW_STATE_KEY];path=oc.resolve(obs,oc.derived_path(obs['sim_sec']))
        assert path.read_bytes()==oc.derived_bytes(derived)
        return path
    jobs={}
    args=h.read(h.R/'s67_full_observation/prediction_run76_actuator_equivalent.json')['argv'][2:]
    jobs['s67']=[str(x) for x in args]
    jobs['s73']=h.read(h.R/'replication_s73_95/postprocess_plan.json')['commands']['forecast']
    proof=h.I/'native_rm_observation2700_s71_four84/analysis/observation_reuse.json'
    receipt=h.read(proof)
    jobs['s71']=[str(Path(probe.__file__)),'--closedloop-recorded','--at=2250','--warm-head-history','--replay-vsl-history',
        '--recording-dir='+receipt['recording_dir'],'--four-arm-receipt='+str(proof)]
    try:
        oc.write_derived=existing
        for tag,args in jobs.items():
            args=[a for a in args if not a.startswith(('--tuning-json=','--probe-label=','--output-suffix='))]
            args.extend(['--tuning-json='+str(HERE/'tuning.json'),'--probe-label=d248c_'+tag,'--output-suffix=d248c_'+tag])
            def capture(captured,candidates,coord,output,tag=tag):
                assert tag not in CAPTURES
                if tag=='s71':
                    assert set(candidates)=={'held_actual','rm','vsl','both'}
                    candidates={('nc' if k=='held_actual' else k):v for k,v in candidates.items()}
                CAPTURES[tag]=(captured,candidates,coord)
                save('capture_'+tag+'.json',dict(start=captured['state'].time_sec,arms=list(candidates),output=str(output),argv=args,
                    commands={k:commands(v,captured['cfg']) for k,v in candidates.items()},
                    source_and_forecast='Canonical initializer; only pre-state observed history and captured demand forecast. No future observations.'))
            def intercepted(*a,**kw):return original_probe(*a,prepared_probe_callback=capture,**kw)
            probe.probe_levers=intercepted;sys.argv=args;probe.main()
            assert tag in CAPTURES
            expected={'nc','rm','vsl','both'} if tag=='s71' else {'release_actual','release_vsl90_actual'}
            assert set(CAPTURES[tag][1])==expected,(tag,list(CAPTURES[tag][1]))
    finally:
        probe.probe_levers=original_probe;oc.write_derived=original_writer


def main():
    HERE.mkdir(exist_ok=True)
    assert not (HERE/'protocol.json').exists(),'Never overwrite/retry a completed or failed experiment'
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetCurrentProcess.restype=ctypes.c_void_p
    k.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32];assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
    protected={str(p):h.sha(p) for p in (h.ROOT/'evaluation/controllers').glob('*.py')}
    stop=h.read(h.R/'aggregate_recovery247/protocol.json')['STOP']
    tuning=h.read(h.R/'rm_restart219/budget235/config.json');tuning['adapter'].pop('sdmpc_fixed_vsl')
    save('tuning.json',tuning)
    evidence=[h.R/'s67_full_observation/response_assessment76.json',h.R/'replication_s73_95/response_assessment95.json',
              h.R/'rm_restart219/independent230/replay_v2/assessment.json',Path(__file__),HERE/'tuning.json',
              h.I/'probe_selected_arrival_path.py']
    pins={str(p):h.sha(p) for p in evidence}
    save('protocol.json',dict(previous_goal_turn='PROGRESS247: current/frozen-reference audit established negative relaxation in observed recovery states.',
        scope='Current233/235 coupled expanded036, wholeOmega and8ramps. Frozen native run untouched.',
        change='Only FW_E physical24/25 when desired<speed: multiply negative relaxation by sharedlambda in[.25,1]. tau andnu both divided bylambda, preserving anticipationnu/tau. Positive relaxation, FDtarget, convection,merge,lane drop,receiving,queues,offstorage andVSLhistory unchanged.',
        calibration='Knownseed67 same2700 state release110/90. Evaluate lambda1,.5, then at mostone bounded linear least-squares proposal withridge.1 aboutlambda1. No line search/grid/bound expansion.',
        fit_vector='DeltaOmegaTTT/2,DeltaeastTTT/2,DeltarampTTT/1; eacharm actual eastterminal/50 andendstock/50. Prefixsame so native full-run cost differences equal450 differences.',
        validation='Freeze coefficient before knowns71 NC/RM/VSL/both ands73release pair; no coefficient change after validation. These have historical exposure,notblind.',
        budget=dict(forecasts_max=18,coefficient_fits=1,optimizer=0,native=0,FZP=0),
        acceptance='Materialcost abs>=.5: sign anderror<=max(.5,.5*abs(actual)); regret<=.5. Requiretrainingfitloss improve10%; absolute eastterminal/endstock errors notworsen10%. Mechanical checks and improved speed alone insufficient.',
        tuning_exception='Remove only fixedVSL actuator policy in offline comparison to replay actually executed110/90 commands. Physicalcode/controller period/demand/network unchanged.',
        protected_sha256=protected,STOP=stop,input_pins=pins))
    try:
        prepare_inputs()
        base=pair('s67',1.,'base');probe=pair('s67',.5,'probe')
        target=actual67();center=vector(base);edge=vector(probe)
        derivative=[(b-a)/(-.5) for a,b in zip(center,edge)]
        residual=[a-b for a,b in zip(center,target)]
        numerator=sum(d*r for d,r in zip(derivative,residual));denominator=sum(d*d for d in derivative)+.1
        ratio=min(1.,max(.25,1.-numerator/denominator))
        frozen=dict(ratio=ratio,derivative=derivative,center_residual=residual,target=target,ridge=.1,
                    fit_calls=1,training_seed=67,validation_used=False)
        save('selection_frozen.json',frozen)
        chosen=base if ratio==1. else probe if abs(ratio-.5)<1e-12 else pair('s67',ratio,'chosen')
        train_loss=lambda pp:sum((a-b)**2 for a,b in zip(vector(pp),target))
        save('training.json',dict(base_loss=train_loss(base),chosen_loss=train_loss(chosen),ratio=ratio,
            actual_delta=target[0]*2,base_delta=base[1]['ttt']-base[0]['ttt'],chosen_delta=chosen[1]['ttt']-chosen[0]['ttt']))
        # Complete the promised RM/VSL four-condition comparison even if this
        # single candidate fails training; it guards against an overbroad claim.
        for tag in ('s71','s73'):
            arms=('nc','rm','vsl','both') if tag=='s71' else ('release_actual','release_vsl90_actual')
            for arm in arms:
                forecast(tag,arm,1.,'base')
                if ratio!=1.:forecast(tag,arm,ratio,'chosen')
        assert all(h.sha(p)==v for p,v in {**protected,**pins,stop['path']:stop['sha256']}.items())
        save('completion.json',dict(status='COMPLETE_PENDING_ASSESSMENT',forecasts=len(RESULTS),fit_calls=1,
            ratio=ratio,forecast_seconds=sum(r['seconds'] for r in RESULTS),production_adopted=False,source_preserved=True))
    except BaseException as exc:
        save('failure.json',dict(error=repr(exc),forecasts_completed=len(RESULTS),preserved=True,automatic_retry=False))
        raise


if __name__=='__main__':main()
