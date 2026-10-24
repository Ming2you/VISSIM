"""Two actuator forecasts and one matched native replay, using canonical code."""
import copy
import csv
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import time
from types import SimpleNamespace as NS

D=Path(__file__).resolve().parent
ROOT=D.parents[3]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
O=I/'native_rm10681_reopen4650_238'
F=Path('D:/VISSIM_runs/20261005_rm219_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
FIELDS=('N_P_star','N_UF_star','ramp_metering','vsl','green_times','offsets','inflow_outflow_allocation')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())


def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def rows(path):
    def normalize(value):
        try:return float(value)
        except ValueError:return value
    with path.open(encoding='utf-8-sig',newline='') as stream:
        return [{k:normalize(v) for k,v in r.items() if k!='metadata'} for r in csv.DictReader(stream)]


def prepare(captured,reference,coord,options):
    from evaluation.controllers import sdmpc,sdmpc_sequence as sequence
    from evaluation.controllers import area_leader_objective as constraints
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    from src.controllers import rollout_endpoint as endpoint
    cfg,state=captured['cfg'],captured['state']
    assert state.time_sec==4650 and not O.exists(), 'Preserve prepared/native attempts'
    neighbors=dict(sdmpc.meter_neighbors(coord,reference))
    cases={'hold':reference,'selected':neighbors['RM_C10681:release']}
    local={s:NS(signal=s,movements=[m for m,v in cfg.network.urban_movements.items() if v['signal']==s],
                kind_of={m:v['kind'] for m,v in cfg.network.urban_movements.items() if v['signal']==s})
           for s in cfg.network.signals}
    fw={road:NS(link=road,owned_ramps=[r for r in cfg.network.ramps if cfg.network.ramp_to_freeway[r]==road])
        for road in cfg.network.freeway_links}
    follower=NS(cfg=cfg,_local_models=local,_local_freeway_models=fw)
    results={}
    for name,action in cases.items():
        coord.validate(action)
        old=read(D.parent/'posthold237'/('hold_action.json' if name=='hold' else 'release10681_action.json'))
        assert all(getattr(action,k)==old[k] for k in FIELDS)
        assert action.diagnostics.get(sequence.KEY)==old['diagnostics'].get(sequence.KEY)
        started=time.perf_counter()
        with sequence.prediction_scope(action,cfg,state.time_sec,3) as visits:
            point=endpoint.evaluate_price_point(state,action,copy.deepcopy(captured['forecast']),(),
                endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
        assert not point.aborted and len(point.states)==3 and visits in (None,[0,1,2])
        response=point.control_area_response
        assert response['model_constraint_coverage']['complete']
        assert response['conditional_model_feasibility_witness']
        exceed=max((r['exceedance_veh'] for r in response['resource_allocations']),default=0.)
        assert exceed<=1e-7
        for saved in (state,*point.states):get_ledger(saved).assert_stocks(model_inventory(saved,cfg))
        raw=constraints.shared_urban_quantities(follower,response,start_sec=4650,horizon_steps=3)
        q=constraints.shared_quantity_constraints(follower,action,raw,start_sec=4650,horizon_steps=3,
            np_mode='cap',target_np_veh=action.N_P_star,np_tolerance_veh=1e-7,
            nuf_mode='cap',target_nuf_veh_h=action.N_UF_star,nuf_tolerance_veh_h=1e-7)
        outside=sum(r['dt_h']*sum(max(0.,r['model_stock_veh'][key]-n) for key,n in r['inside_veh'].items())
                    for r in response['residence'])
        result=dict(omega_ttt_veh_h=point.ttt,tracked_outside_residence_veh_h=outside,
            inherited_constraints=q,model_constraint_coverage=response['model_constraint_coverage'],
            resource_max_exceedance_veh=exceed,ledger_checks=4,wall_sec=time.perf_counter()-started,
            commands=[{r:a.diagnostics['rw_meter_green_'+r] for r in cfg.network.ramps}
                      for a in sequence.actions(action,3)])
        results[name]=result
        save(D/(name+'_prediction.json'),result)
        with gzip.open(D/(name+'_response.json.gz'),'wt',encoding='utf-8') as stream:json.dump(response,stream)
        print('ACTUATOR_PREDICTION',name,round(point.ttt,6),flush=True)
    results['delta_omega_ttt_veh_h']=results['selected']['omega_ttt_veh_h']-results['hold']['omega_ttt_veh_h']
    results['delta_tracked_outside_veh_h']=results['selected']['tracked_outside_residence_veh_h']-results['hold']['tracked_outside_residence_veh_h']
    results['scope']='Two fixed-command actuator forecasts; inherited caps diagnostic only; no SDMPC optimum or native result.'
    save(D/'prediction_summary.json',results)

    plan=read(D.parent/'posthold237/next_native_plan.json')
    pins={str(p):sha(p) for p in (Path(__file__),D/'prediction_summary.json',D.parent/'posthold237/next_native_plan.json')}
    for key in ('baseline_summary','baseline_execution'):
        p=Path(plan[key]['path']);assert sha(p)==plan[key]['sha256'];pins[str(p)]=sha(p)
    dest=O/'selected/commands';dest.mkdir(parents=True)
    prefix=[]
    for sec in (1,*range(150,4650,150)):
        record=dict(sim_sec=sec)
        for suffix in ('.json','.csv'):
            src=F/f'action_{sec:06d}{suffix}';target=dest/src.name
            shutil.copy2(src,target);assert sha(src)==sha(target)
            pins[str(src)]=sha(src);pins[str(target)]=sha(target)
            record[suffix[1:]]=dict(source=str(src),destination=str(target),sha256=sha(src))
        prefix.append(record)
    actuation=adapter.adapter_actuation_settings(captured['calibration'],captured['tuning'])
    segment=adapter.repo_imports(ROOT/'vendor/NumSim-mine')[-1]
    signal_plan=adapter.load_signal_group_actuation_plan()
    metadata=read(F/'action_004350.json')['metadata']
    written=[]
    for name,action in cases.items():
        folder=dest if name=='selected' else D/'held_writer'
        folder.mkdir(exist_ok=True)
        blocks=sequence.actions(action,3)
        for k,sec in enumerate((4650,4800,4950,5100)):
            current=blocks[min(k,2)]
            meta=copy.deepcopy(metadata)
            for stale in ('sdmpc_state','run_provenance','hold_previous'):meta.pop(stale,None)
            meta.update(sim_sec=sec,controller_status='diagnostic_fixed_sequence',
                diagnostic_scope='10681 reopen causal actuator check; inherited NUF cap may fail; not an optimized decision')
            stem=folder/f'action_{sec:06d}'
            adapter.write_action_csv(stem.with_suffix('.csv'),current,cfg,captured['mapping'],segment,meta,actuation,
                signal_group_plan_table=signal_plan,offset_writer='experiment')
            save(stem.with_suffix('.json'),adapter.control_to_json_dict(current,meta))
            actual=rows(stem.with_suffix('.csv'))
            base=rows(F/f'action_{sec:06d}.csv')
            assert len(actual)==len(base)
            changed=[]
            for a,b in zip(actual,base):
                if a!=b:
                    assert name=='selected' and a['kind']==b['kind']=='ramp_meter' and a['id']==b['id']=='RM_C10681'
                    assert {key for key in a if a[key]!=b[key]}<={'green_sec','rate_vph'}
                    assert a['green_sec']==[2.,4.,6.][min(k,2)]
                    changed.append(a['id'])
            assert changed==(['RM_C10681'] if name=='selected' else [])
            written.append(dict(arm=name,sec=sec,rows=len(actual),changed_ids=changed,csv_sha256=sha(stem.with_suffix('.csv'))))
            for suffix in ('.json','.csv'):pins[str(stem.with_suffix(suffix))]=sha(stem.with_suffix(suffix))
    network=I/'selected/network/native_seed29.inpx'
    assert sha(network)==plan['network_sha256']
    execution=Path(plan['baseline_execution']['path'])
    provenance=F.parent/'run_provenance_sdmpc31_sdmpc9000_s29.json'
    pins[str(provenance)]=sha(provenance)
    protocol=dict(start_sec=4650,end_sec=5100,seed=29,arms=['selected'],control_start_sec=900,controller='wu-link',
        network=str(network),network_sha256=sha(network),command_pins=pins,
        reuse_native_baseline=dict(run=str(F.parent),summary=plan['baseline_summary']['path'],sha256=plan['baseline_summary']['sha256']),
        controlled_prefix=dict(execution=str(execution),execution_sha256=sha(execution),
            provenance=str(provenance),provenance_sha256=sha(provenance),control_start_sec=900,commands=prefix),
        native_authorization_pending=False,native_authorization='User authorized necessary VISSIM runs',
        max_native_runs=1,automatic_retries=0,sim_resolution=10,vehicle_record_interval_sec=5,
        observation_interval_sec=150,future_observation_inputs=False,controller_optimization=False,
        physical_command_check=written,prediction_summary=str(D/'prediction_summary.json'),
        scope='Exact actual219 prefix through4500; only10681 g2/4/6 from4650. Inherited planning cap fails; causal actuator diagnostic, not fresh SDMPC feasible selection.',
        qualification_requires_exact_native_prefix=True,native_started=False)
    save(O/'protocol.json',protocol)
    save(D/'preparation.json',dict(status='prepared_not_launched',protocol=str(O/'protocol.json'),protocol_sha256=sha(O/'protocol.json'),
        written=written,prefix_files=2*len(prefix),native_runs=0,fit=0,scalar_predictions=0,actuator_predictions=2,
        delta_omega_ttt_veh_h=results['delta_omega_ttt_veh_h']))
    print('NATIVE_COMMANDS_PREPARED',str(O),flush=True)
