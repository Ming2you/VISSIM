"""Two recorded VSL interventions at a verified common native initial state.

Explicit legacy urban projection; current freeway and FW5/U10 coupling. Not a
native348 full-plant validation or an autonomous policy/cap selection test.
"""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,copy,csv,gzip,hashlib,importlib.util,json,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
R=ROOT/'diagnostics/repin_v3c3_review_20261001'
TUNING=HERE/'legacy_urban_diagnostic_config.json'
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,choices=(67,71),required=True)
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    assert not a.out.exists() and not (HERE/'STOP').exists()
    start=2700 if a.seed==67 else 2250
    native=R/'s67_full_observation/analysis/summary.json' if a.seed==67 else I/'native_rm_observation2700_s71_four84/analysis/summary.json'
    folder=Path('D:/VISSIM_runs/20261003_s67_vsl_observation2700/release/decisions_sdmpc31_g_2700_release_s67') if a.seed==67 else Path('D:/VISSIM_runs/20261003_independent_s71_four84/nc/decisions_sdmpc31_g_2250_nc_s71')
    arms=('release','release_vsl90') if a.seed==67 else ('rm','both')
    alignment=R/'s67_full_observation/recording_start_alignment76.json' if a.seed==67 else None
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    sys.argv=['verify.py','--at',str(start),'--out',str(a.out),'--no-prediction','--cold-prices','--tuning',str(TUNING),'--decisions',str(folder)]
    spec=importlib.util.spec_from_file_location('matched349_bootstrap',R/'urban260/verify.py')
    verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_pfo,sdmpc_sequence as seq
    from evaluation.controllers import physical_ramp_branches as ramps,signal_actuation_contract as signals
    from evaluation.controllers.area_freeway_accounting import continuity_vehicle_counts
    from evaluation.controllers.control_area_objective import get_ledger,physical_membership_from_ledger
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.area_follower_objective import expand_shared_vsl_action,shared_query_runtime_scope
    from src.controllers import rollout_endpoint as endpoint
    from src.models.state import ControlAction
    def save(name,x):(a.out/name).write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    original_main=adapter.main
    def wrapped_main():
        from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
        from evaluation.controllers import obs150_contract as oc
        receipt=probe.prepare_fixed_replay_history(native,folder,TUNING,a.out,recording_alignment=alignment)
        derived=Path(receipt['derived_directory'])
        head,vsl=probe.replay_head_history,probe.replay_vsl_history
        probe.replay_head_history=lambda *args,**kw:head(*args,**dict(kw,derived_directory=derived))
        probe.replay_vsl_history=lambda *args,**kw:vsl(*args,**dict(kw,derived_directory=derived,compare_online=False))
        def readonly(raw,document):
            path=derived/f"derived_{document['sim_sec']:06d}.json"
            assert path.read_bytes()==oc.derived_bytes(document);return path
        oc.write_derived=readonly
        previous=probe.bind_fixed_replay_reference(receipt,folder,a.out)
        sys.argv[sys.argv.index('--previous-action-json')+1]=str(previous)
        captured={};bound=ramps.configure_operating_bounds;forecast=adapter.demand_from_state
        from evaluation.controllers import runtime_setup
        configure=runtime_setup.configure_runtime
        def capture_runtime(*args,**kwargs):
            result=configure(*args,**kwargs)
            captured.update(mapping=args[3],calibration=args[7],tuning=args[2])
            return result
        runtime_setup.configure_runtime=capture_runtime
        def capture_bound(state,cfg,reference):
            captured.update(state=state,cfg=cfg);return bound(state,cfg,reference)
        def capture_forecast(*args,**kw):
            result=forecast(*args,**kw);captured['forecast']=result;return result
        ramps.configure_operating_bounds=capture_bound;adapter.demand_from_state=capture_forecast
        def run(*unused,**kw):
            state,cfg=captured['state'],captured['cfg'];assert state.time_sec==start
            assert cfg.simulation.T_f_sec==5 and cfg.simulation.T_u_sec==10
            initial=copy.deepcopy(get_ledger(state).stocks);initial_n=continuity_vehicle_counts(state,cfg)
            physical=physical_membership_from_ledger(read(ROOT/read(TUNING)['control_area_objective']['membership_path']))
            raw=read(folder/f'state_{start:06}.json')
            assert sum(physical.values())==701
            observed=sum(physical[str(v['link_no'])] for v in raw['vehicle_records']['records'])
            assert abs(observed-sum(v['inside'] for v in initial.values()))<1e-7
            pins={str(TUNING):sha(TUNING),str(Path(__file__)):sha(__file__)};commands={}
            segment_vsl=adapter.repo_imports(ROOT/'vendor/NumSim-mine')[-1]
            for arm in arms:
                blocks=[]
                for index,path in enumerate(receipt['candidate_actions'][arm]):
                    pins[path]=sha(path);command=seq.first_action(adapter.control_from_json(Path(path),cfg,ControlAction))
                    # Historical root aliases differ from their segment minimum.
                    # Preserve effective zone speeds and prove actual DSD equality
                    # using the canonical writer before strict alias expansion.
                    with shared_query_runtime_scope():
                        before={road:[float(segment_vsl(command,road,i,cfg))
                            for i in range(len(cfg.network.freeway_vsl_zone_head_of_cell[road]))]
                            for road in cfg.network.freeway_links}
                        for road,values in before.items():
                            command.vsl[road]=min(values)
                            for i,value in enumerate(values):command.vsl[f'{road}__seg{i}']=value
                        assert before=={road:[float(segment_vsl(command,road,i,cfg))
                            for i in range(len(values))] for road,values in before.items()}
                    rewritten=a.out/f'{arm}_block{index}_vsl_binding.csv'
                    adapter.write_action_csv(rewritten,command,cfg,captured['mapping'],segment_vsl,
                        read(path)['metadata'],adapter.adapter_actuation_settings(captured['calibration'],captured['tuning']),
                        signal_group_plan_table=adapter.load_signal_group_actuation_plan(),offset_writer='experiment')
                    def signs(source):
                        with source.open(encoding='utf-8-sig',newline='') as stream:
                            return sorted((int(row['dsd_no']),float(row['speed_kph']))
                                for row in csv.DictReader(stream) if row['kind']=='vsl')
                    assert signs(rewritten)==signs(Path(path).with_suffix('.csv'))
                    command,_=expand_shared_vsl_action(command,cfg,segment_vsl_func=segment_vsl)
                    signals.validate_writer(command,cfg,adapter.load_signal_group_actuation_plan(),'experiment');blocks.append(command)
                commands[arm]=blocks
            for left,right in zip(commands[arms[0]],commands[arms[1]]):
                assert left.green_times==right.green_times and left.offsets==right.offsets
                assert left.ramp_metering==right.ramp_metering
                assert {k:v for k,v in left.diagnostics.items() if k.startswith('rw_meter_green_')}=={k:v for k,v in right.diagnostics.items() if k.startswith('rw_meter_green_')}
            save('protocol.json',dict(seed=a.seed,start=start,end=start+450,arms=arms,scope=__doc__,pins=pins,
                same_city_rm_commands=True,initial_omega_vehicles=observed,initial_stocks=initial,
                future_observation_inputs=False,recorded_future_commands_are_conditions=True))
            results={}
            for arm in arms:
                action=seq.pack(commands[arm]);tick=time.perf_counter()
                with seq.prediction_scope(action,cfg,start,3) as visits:
                    point=endpoint.evaluate_price_point(state,action,copy.deepcopy(captured['forecast'][:3]),(),
                        endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
                elapsed=time.perf_counter()-tick;assert visits==[0,1,2] and not point.aborted and len(point.states)==3
                response=point.control_area_response
                assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
                snapshots=[]
                for current in (state,*point.states):
                    ledger=get_ledger(current);ledger.assert_stocks(model_inventory(current,cfg))
                    snapshots.append(dict(time_sec=current.time_sec,stocks=ledger.stocks,n=continuity_vehicle_counts(current,cfg),speed=current.freeway_speed))
                assert initial==get_ledger(state).stocks and initial_n==continuity_vehicle_counts(state,cfg)
                costs={};outside={}
                for row in response['residence']:
                    for key,value in row['inside_veh'].items():
                        costs[key]=costs.get(key,0.)+value*row['dt_h']
                        outside[key]=outside.get(key,0.)+(row['model_stock_veh'][key]-value)*row['dt_h']
                assert abs(sum(costs.values())-point.ttt)<1e-7
                (a.out/(arm+'_response.json.gz')).write_bytes(gzip.compress(json.dumps(response,allow_nan=False).encode('utf8')))
                save(arm+'_snapshots.json',snapshots);save(arm+'_control_area.json',point.control_area)
                results[arm]=dict(ttt=point.ttt,costs_by_stock=costs,outside_costs_by_stock=outside,seconds=elapsed,
                    physical_constraints=True,writer=True,sdmpc_cap_or_selection_claimed=False)
                save('prediction_progress.json',results);print('PREDICTION',a.seed,arm,point.ttt,elapsed,flush=True)
            save('summary.json',dict(status='complete_conditional_pair',seed=a.seed,start=start,end=start+450,
                results=results,model_delta_omega=results[arms[1]]['ttt']-results[arms[0]]['ttt'],
                new_predictions=2,latest_full_native348_validation=False,native_runs=0,fits=0,
                native_receipt=str(a.out/'fixed_replay_receipt.json'),source_pins=pins))
            raise verifier.Done()
        sdmpc_pfo.solve=run
        return original_main()
    adapter.main=wrapped_main;verifier.main()

if __name__=='__main__':main()
