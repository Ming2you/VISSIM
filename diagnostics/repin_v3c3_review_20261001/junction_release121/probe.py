"""Two conditional450s probes: observed branch blockage, not an autonomous law."""
from pathlib import Path
import copy
import csv
import hashlib
import importlib.util
import json
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'vendor/NumSim-mine'))
R=HERE.parent
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
DISABLED='--disabled' in sys.argv
PREFIX='baseline2_' if DISABLED else 'conditional2_'
SHARED='--shared-lane' in sys.argv
if SHARED:
    assert not DISABLED
    HERE=R/'junction_shared123'
    PREFIX='shared_'


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def save(name,x):
    (HERE/(PREFIX+name)).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    import ctypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=ctypes.c_void_p
    kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000), ctypes.get_last_error()
    assert not (HERE/(PREFIX+'probe_status.json')).exists(), 'Preserve prior attempt; no automatic retry'
    from evaluation.controllers import area_freeway_accounting as accounting
    from evaluation.controllers import offramp_routing as routing
    from evaluation.controllers.control_area_objective import get_ledger
    from src.controllers import rollout_endpoint as endpoint
    from evaluation.controllers.area_runtime import model_inventory
    pins=load(R/'subcell_speed120/attempt3/protocol.json')['pins']
    pins.update(load(R/'cohort_departure89/protocol.json')['input_pins'])
    probe_path=I/'probe_selected_arrival_path.py'
    # Reviewed95 seed73 support and115 read-only derived-observation verifier.
    # Fresh disabled controls below verify the resulting physical baseline.
    pins[str(probe_path)]='b0546a59d94da6b3eaf67294d1e13170097a5a0290cae9edbe82ee312b7ccf9c'
    # Current code and previous evidence must be the same revisions.
    for p,h in pins.items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    stop=Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    stop_sha=hashlib.sha256(stop.read_bytes()).hexdigest()
    assert stop_sha=='91b2163b02b01447242909dee8e7f773d18e76a6594bd9db8de64d2a48246fc3'
    rows=list(csv.DictReader((R/'junction_release121/frames.csv').open(encoding='utf-8-sig')))
    profiles={arm:{round(float(r['time_sec'])-.1):bool(int(r['stopped_body_spans_exit']))
        for r in rows if r['case']==arm} for arm in ('release','release_vsl90')}
    assert all(list(x)==list(range(2700,3150,5)) for x in profiles.values())
    shares=load(HERE/'profiles.json') if SHARED else None
    if SHARED:
        for arm in profiles:
            assert all(shares[arm][str(t)]['blocked']==b for t,b in profiles[arm].items())
    module_path=I/'probe_selected_arrival_path.py'
    spec=importlib.util.spec_from_file_location('junction121_canonical_probe',module_path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    job=next(x for x in load(R/'s67_policy_response81/protocol_path.json')['jobs'] if x['name']=='release')
    argv=[x for x in job['argv'] if not x.startswith('--output-suffix=')]
    label='baseline2_junction121' if DISABLED else 'conditional2_junction121'
    if SHARED:label='conditional_shared123'
    argv=[('--probe-label='+label if x.startswith('--probe-label=') else x) for x in argv]
    output=I/('closedloop_recorded2700_lever450_'+label)
    assert not output.exists(),output
    diagnostic=dict(kind='conditional_observed10483_body_block',autonomous=False,
        future_observation_inputs=True,calibration=False,goal_qualification=False,
        mechanism='Only10483 entry supply set0 while native lane1 stopped body spans the branch; other times retain original storage supply. Original mass/routing/speed update stays coupled.',
        profiles=profiles,phase_alignment_sec=.1,holding_sec=5,
        limitations='Future binary occupancy used ONLY to test coupling; zero-order5s full blockage is an intentionally strong probe, not measured exact open/closed duration or an adopted capacity law.')
    if SHARED:
        diagnostic.update(kind='conditional_observed_shared_lane_block',
            mechanism='10483 entry supply0 plus cell20 through sending multiplied by1-observed_current_through_lane1_population_share while observed body blocks shared lane. Original accepted-flow conservation, speed, ramp/urban wait remain.',
            shared_lane_profiles=shares,
            inference='Fixed existing coefficients; no ceiling on a future dynamics-consistent recalibration. Neither an autonomous law nor a fitted capacity bonus.')
    save('probe_protocol.json',dict(diagnostic=diagnostic,disabled=DISABLED,
        budget=dict(forecasts=2,fresh_disabled_pair=0 if SHARED else 2,combined_forecasts=2 if SHARED else 4,fit=0,native=0),
        core_and_input_pins=pins,STOP_sha=stop_sha,argv=argv,
        decision='Measure the response path at fixed coefficients; do not infer a recalibrated performance ceiling or repeat strength grids. Interpretation_update122 governs the previous branch-only test.'))
    original_step=accounting._freeway_substep_events
    original_sending=routing.sending_requests
    original_probe=module.probe_levers
    active=dict(arm=None)
    records=[];witness=[];stats=dict(calls=0,queries=0,blocked_queries=0)
    sending_records=[]

    def sending(state,cfg,fw,flows,dt):
        main,branch=original_sending(state,cfg,fw,flows,dt)
        if not SHARED or active['arm'] is None or fw!='FW_E':return main,branch
        stamp=get_ledger(state)._response_stamp();t=stamp['start_sec']
        assert stamp['end_sec']-t==1 and 2700<=t<3150 and abs(dt*3600-1)<1e-9
        caller=sys._getframe(1).f_globals['__name__']
        assert caller in ('evaluation.controllers.lane_ramp_runtime','evaluation.controllers.area_freeway_accounting')
        row=shares[active['arm']][str(2700+5*int((t-2700)//5))]
        factor=1-row['through_lane1_share'] if row['blocked'] else 1.
        assert 0<=factor<=1 and cfg.network.offramp_route_inventory['branches']['10483']['source_cell']==20
        changed=list(main);changed[20]*=factor
        assert all(changed[i]==main[i] for i in range(len(main)) if i!=20)
        sending_records.append(dict(arm=active['arm'],time_sec=t,caller=caller,
            blocked=row['blocked'],factor=factor,before_through_vph=main[20],after_through_vph=changed[20]))
        return changed,branch

    def step(state,control,demand,cfg,**kwargs):
        if active['arm'] is None or 'FW_E' not in cfg.network.freeway_links:
            return original_step(state,control,demand,cfg,**kwargs)
        assert list(cfg.network.freeway_links)==['FW_E']
        caps=kwargs['offramp_capacity_veh_h'];dt=cfg.simulation.T_f_h
        stamp=get_ledger(state)._response_stamp()
        t=stamp['start_sec']
        assert abs(dt*3600-1)<1e-9 and stamp['end_sec']-t==1
        assert 2700<=t<3150 and '10483' in caps
        frame=2700+5*int((t-2700)//5)
        blocked=False if DISABLED else profiles[active['arm']][frame]
        modified=dict(caps)
        if blocked:modified['10483']=0.
        assert all(modified[k]==v for k,v in caps.items() if k!='10483')
        assert 0<=modified['10483']<=caps['10483']
        records.append(dict(arm=active['arm'],time_sec=t,blocked=blocked,
            original_cap_vph=caps['10483'],conditional_cap_vph=modified['10483']))
        stats['queries']+=1;stats['blocked_queries']+=int(blocked)
        kwargs['offramp_capacity_veh_h']=modified
        result=original_step(state,control,demand,cfg,**kwargs)
        records[-1]['accepted10483_veh']=result[1]['offramp_flow_branch_10483']*dt
        if blocked:assert records[-1]['accepted10483_veh']==0
        return result

    class MarkJSON:
        def __init__(self,original):self.original=original
        def __getattr__(self,name):return getattr(self.original,name)
        def dumps(self,obj,*a,**kw):
            if not DISABLED and isinstance(obj,dict) and ('ttt_omega_veh_h' in obj or 'results' in obj):
                obj=copy.deepcopy(obj)
                def mark(x):
                    if isinstance(x,dict):
                        for k,v in list(x.items()):
                            if k=='future_observation_inputs':x[k]=True
                            else:mark(v)
                    elif isinstance(x,list):
                        for v in x:mark(v)
                mark(obj);obj['future_observation_inputs']=True;obj['conditional_diagnostic']=diagnostic
            return self.original.dumps(obj,*a,**kw)

    def probe(*a,**kw):
        cfg=a[0]['cfg'];old_evaluate=endpoint.evaluate_price_point;old_json=module.json
        def evaluate(*args,**kwargs):
            assert stats['calls']<2
            active['arm']=('release','release_vsl90')[stats['calls']];stats['calls']+=1
            begin=len(records);initial=model_inventory(args[0],cfg)
            point=old_evaluate(*args,**kwargs)
            assert not point.aborted and len(point.states)==3
            samples=records[begin:]
            assert [x['time_sec'] for x in samples]==list(range(2700,3150))
            assert sum(x['blocked'] for x in samples)==(0 if DISABLED else 5*sum(profiles[active['arm']].values()))
            if SHARED:
                for caller in ('evaluation.controllers.lane_ramp_runtime','evaluation.controllers.area_freeway_accounting'):
                    assert [r['time_sec'] for r in sending_records if r['arm']==active['arm'] and r['caller']==caller]==list(range(2700,3150))
            witness.append(dict(arm=active['arm'],initial_inventory=initial,
                final_inventory=model_inventory(point.states[-1],cfg),
                omega_ttt=point.ttt,queries=len(samples),blocked_queries=sum(x['blocked'] for x in samples)))
            active['arm']=None
            return point
        endpoint.evaluate_price_point=evaluate;module.json=MarkJSON(old_json)
        try:return original_probe(*a,**kw)
        finally:endpoint.evaluate_price_point=old_evaluate;module.json=old_json;active['arm']=None

    old_argv=sys.argv
    started=time.perf_counter()
    save('probe_status.json',dict(phase='running_conditional_not_autonomous',output=str(output)))
    accounting._freeway_substep_events=step;module.probe_levers=probe
    if SHARED:routing.sending_requests=sending
    try:
        sys.argv=argv;module.main()
        assert stats['calls']==2 and stats['queries']==900
        summary=load(output/'summary.json')
        assert summary['future_observation_inputs']==(not DISABLED)
        if not DISABLED:assert not summary['conditional_diagnostic']['autonomous']
        save('probe_witness.json',dict(stats=stats,witness=witness,queries=records))
        if SHARED:save('sending_witness.json',sending_records)
        save('probe_status.json',dict(phase='complete_pending_assessment',output=str(output),stats=stats,wall_sec=time.perf_counter()-started))
    except Exception as exc:
        save('probe_status.json',dict(phase='failed',error=repr(exc),stats=stats,output=str(output)))
        raise
    finally:
        accounting._freeway_substep_events=original_step;module.probe_levers=original_probe;sys.argv=old_argv
        routing.sending_requests=original_sending
        assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in pins.items())
        assert hashlib.sha256(stop.read_bytes()).hexdigest()==stop_sha
        save('restoration.json',dict(core_inputs_STOP_unchanged=True,original_hooks_restored=True))


if __name__=='__main__':
    main()
