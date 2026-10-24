"""Read-only 10681 audit using the existing saved-state initializer and plant.

Two continuous450 predictions and two discrete900 predictions; no optimizer,
COM, FZP, new native run, coefficient edits, or live command writes.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse, copy, hashlib, importlib.util, inspect, json, pickle, sys, time
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ap = argparse.ArgumentParser()
ap.add_argument('--at', type=int, default=3300)
ap.add_argument('--out', default='four_causes3300')
ap.add_argument('--reuse450', type=Path, help='Reuse completed continuous audit; resume the two horizon diagnostics only')
ap.add_argument('--tuning', type=Path, help='Explicit candidate model; saved objective is a comparator, not a parity assertion')
ap.add_argument('--only450', action='store_true', help='Two fixed-horizon responses; no horizon extension')
ap.add_argument('--meter-derivative', action='store_true', help='One selected-action AD prediction for the three10681 coordinates')
args = ap.parse_args()
reuse450 = args.reuse450
OUT = HERE / args.out
AT = args.at
F = Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
TUNING = args.tuning.resolve() if args.tuning else HERE / 'window1800_5700_config.json'
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
os.environ.update(NUMSIM_REPO_ROOT=str(ROOT/'vendor/NumSim-mine'), PYTHONDONTWRITEBYTECODE='1')
sys.argv = ['verify.py', '--at', str(AT), '--out', str(OUT), '--no-prediction',
            '--decisions', str(F), '--tuning', str(TUNING)]
loader = importlib.util.spec_from_file_location('saved_state_verifier', ROOT/'diagnostics/repin_v3c3_review_20261001/urban260/verify.py')
verify = importlib.util.module_from_spec(loader)
loader.loader.exec_module(verify)
from evaluation.controllers import vissim_stackelberg_adapter as adapter, sdmpc_pfo, sdmpc
from evaluation.controllers import sdmpc_sequence as seq, area_follower_objective as shared
from evaluation.controllers import area_leader_objective as constraints, signal_actuation_contract as signals
from evaluation.controllers.sdmpc_tangent_surrogate import Query
from src.controllers import rollout_endpoint as endpoint
from src.simulation import coupling
from src.models.state import ControlAction

def plain(x):
    if isinstance(x,dict): return {str(k):plain(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)): return [plain(v) for v in x]
    if hasattr(x,'tolist'): return plain(x.tolist())
    if isinstance(x,(str,bool,int,float)) or x is None: return x
    return repr(x)[:300]
def save(name,value):
    (OUT/name).write_text(json.dumps(plain(value),ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')

query_init = Query.__init__
queries = []
def with_costs(self,*a,**kw):
    query_init(self,*a,**kw)
    runner = self.runner
    self.runner = lambda request: runner(dict(request,
        diagnostic_stock_costs=request.get('surrogate_evaluation')!='ad'))
    queries.append(self)
Query.__init__ = with_costs
forecast_original = adapter.demand_from_state
forecast_calls = []
def remember_forecast(*a,**kw):
    forecast_calls.append((a,kw))
    return forecast_original(*a,**kw)
adapter.demand_from_state = remember_forecast
adapter_main = adapter.main

def initialized_main():
    old_audit = sdmpc_pfo.solve
    def audit(reference,coord,policy,options,evaluate,derivative,quantities,check_budget,emit):
        closure = inspect.getclosurevars(old_audit).nonlocals
        try: old_audit(reference,coord,policy,options,evaluate,derivative,quantities,check_budget,emit)
        except verify.Done: pass
        state,cfg = closure['captured']
        follower = adapter._PHASE_VECTOR_FOLLOWER['ref']
        selected_path = F/f'action_{AT:06}.json'
        assert Path(str(selected_path)+'.applied').exists()
        selected = adapter.control_from_json(selected_path,cfg,ControlAction)
        coord.validate(selected)
        alternatives = dict(sdmpc.meter_neighbors(coord,selected))
        relaxed = alternatives['RM_C10681:release']
        actions = {'selected':selected, 'release10681':relaxed}
        for action in actions.values():
            coord.validate(action)
            for a,b in zip(seq.actions(action,3),seq.actions(selected,3)):
                assert a.green_times==b.green_times and a.offsets==b.offsets and a.vsl==b.vsl
                for ramp in cfg.network.ramps:
                    if ramp!='RM_C10681': assert a.diagnostics['rw_meter_green_'+ramp]==b.diagnostics['rw_meter_green_'+ramp]
                signals.validate_writer(a,cfg,adapter.load_signal_group_actuation_plan(),'experiment')
        raw_action = json.loads(selected_path.read_bytes())
        assignment = raw_action['projection_diagnostics']['physical_stock_assignment_by_link']
        selected_keys = {link:list(assignment[link]) for link in ('52','68','10681')}
        stock_support = {key:[link for link,parts in assignment.items() if key in parts]
                         for keys in selected_keys.values() for key in keys}
        initial_stocks = copy.deepcopy(state._control_area_ledger.stocks)
        save('audit_protocol.json',dict(at=AT,max_forecasts=2 if args.only450 else 4,optimized=False,
            tuning=str(TUNING),tuning_sha256=hashlib.sha256(TUNING.read_bytes()).hexdigest(),
            candidate_green={n:[b.diagnostics['rw_meter_green_RM_C10681'] for b in seq.actions(a,3)] for n,a in actions.items()},
            local_stock_keys=selected_keys,initial_stocks=initial_stocks,
            stock_support=stock_support,
            initial_assignment={link:assignment[link] for link in selected_keys},
            horizon_extension='Disabled;450s only' if args.only450 else 'Same450s plan, then hold its last block for450s with forecast generated only from the initial observation; no future-state input.',
            current_goal='Physics, cost/externality and constraint/search checks; no native qualification'))
        joint = json.loads((F/f'action_{AT:06}.joint.json').read_bytes())
        save('saved_selection.json', {k:joint['selection'][k] for k in ('selected_objective','converged','selection_status','final_constraints','meter_neighbor_audit','policy','omega_partition')})
        response_rows=[]
        if reuse450:
            response_rows=json.loads((reuse450/'continuous450.json').read_bytes())
            prior=json.loads((reuse450/'audit_protocol.json').read_bytes())
            assert prior['at']==AT and prior['candidate_green']=={n:[b.diagnostics['rw_meter_green_RM_C10681'] for b in seq.actions(a,3)] for n,a in actions.items()}
            if args.tuning:
                assert prior['tuning_sha256']==hashlib.sha256(TUNING.read_bytes()).hexdigest()
            else:
                assert response_rows[0]['response']['objective_veh_h']==joint['selection']['selected_objective']
            save('continuous450.json',response_rows)
            save('reuse_receipt.json',dict(source=str(reuse450),reused_forecasts=2,
                horizon_sec=450 if args.only450 else 900,
                purpose='Reuse completed fixed-action scalar responses; only requested additional diagnostics run'))
        for name,action in ([] if reuse450 else actions.items()):
            started=time.perf_counter()
            item=evaluate([action],derivatives=False)[0]
            proof=constraints.shared_quantity_constraints(follower,action,item['quantities'],start_sec=AT,horizon_steps=3,
                np_mode='cap',target_np_veh=selected.N_P_star,np_tolerance_veh=options['shared_tolerance'],
                nuf_mode='cap',target_nuf_veh_h=selected.N_UF_star,nuf_tolerance_veh_h=options['shared_tolerance'])
            costs=item['diagnostic_stock_costs_veh_h']
            assert abs(sum(costs.values())-item['objective_veh_h'])<1e-7
            assert abs(sum(item['sdmpc_omega_partition']['costs'].values())-item['objective_veh_h'])<1e-7
            row=dict(name=name,seconds=time.perf_counter()-started,shared_constraints=proof,
                model_feasible=sdmpc_pfo.model_feasible(item,options['shared_tolerance']),response=item)
            if name=='selected':
                row['saved_objective_error']=item['objective_veh_h']-joint['selection']['selected_objective']
                if not args.tuning:
                    assert abs(row['saved_objective_error'])<1e-6, row['saved_objective_error']
            response_rows.append(row)
            save('continuous450.json',response_rows)
            print('continuous',name,item['objective_veh_h'],proof['feasible'],flush=True)
        if args.only450:
            if args.meter_derivative:
                from evaluation.controllers import sdmpc_tangent_surrogate as surrogate
                query=queries[-1]
                request=pickle.loads(query.template)
                columns=[j for j,a in enumerate(request['axes']) if a['kind']=='meter' and a['key']=='RM_C10681']
                assert len(columns)==3
                # Production reverse AD requires one complete tape/catalog.
                # Inspect three meter columns only after that unchanged sweep.
                request.update(action=copy.deepcopy(selected),surrogate_evaluation='ad',
                    surrogate_context_sha256=query.context_token,reverse_worker_limit=2)
                receipt=query.runner(request)
                predicted=receipt['surrogate_prediction']
                surrogate.validate_prediction(predicted,selected,query.context_token)
                assert len(receipt['ad_axes'])==len(request['axes']) and not receipt['fallback_reasons']
                scalar=response_rows[0]['response']
                assert abs(predicted['objective_veh_h']-scalar['objective_veh_h'])<1e-6
                owners=request['costs_order']
                for p,v in zip(owners,receipt['costs']):
                    assert abs(v-scalar['sdmpc_omega_partition']['costs'][p])<1e-6
                jac=receipt['cost_jacobian']
                rows=[]
                for index,j in enumerate(columns):
                    col=j if len(jac[0])==len(request['axes']) else index
                    by_owner={p:jac[k][col] for k,p in enumerate(owners)}
                    axis=request['axes'][j]
                    total=sum(by_owner.values());own=by_owner[axis['owner']]
                    rows.append(dict(axis=axis,own=own,external=total-own,total=total,
                        by_owner=by_owner,resources=[r[col] for r in receipt['resource_jacobian']]))
                save('meter_derivative.json',dict(rows=rows,objective_veh_h=predicted['objective_veh_h'],
                    scalar_objective_veh_h=scalar['objective_veh_h'],scalar_ad_agree=True,
                    derivative_scope=receipt['derivative_scope'],seconds=receipt['wall_sec_including_spawn'],
                    fallback_reasons=receipt['fallback_reasons'],source_pins=receipt['transformed_source_sha256']))
                print('meter_derivative',[(r['axis']['block'],r['total'],r['external']) for r in rows],flush=True)
            save('audit_done.json',dict(status='complete',forecasts=2,model_changes=bool(args.tuning),
                derivative_forecasts=int(args.meter_derivative),reused_scalar=bool(reuse450),
                native_runs=0,horizon_sec=450,future_observations_used_as_input=False))
            raise verify.Done()
        del joint,raw_action
        fa,fk=forecast_calls[-1]
        fa=list(fa); fk=dict(fk)
        if len(fa)>3: fa[3]=6
        else: fk['horizon_steps']=6
        forecast=forecast_original(*fa,**fk)
        assert len(forecast)==6
        save('forecast900.json',[vars(x) for x in forecast])
        # Aggregate time bins are allocated from cfg horizon, not endpoint depth.
        # Expand before initial cohorts enter bins; never extend an existing tail bin.
        assert all('aggregate' not in getattr(state,k) for k in ('native_input_route_state','native_input_prehead_state'))
        cfg.mpc.horizon_steps=6

        @contextmanager
        def plan_scope(action):
            from evaluation.controllers.area_meter_finalization import for_endpoint
            blocks=seq.actions(action,3)
            blocks += [blocks[-1].copy() for _ in range(3)]
            controls=[for_endpoint(b,(),endpoint.ObjectiveSpec(cfg,depth_override=6,box_walk=False,score_mode='raw')) for b in blocks]
            original=coupling.run_coupled_interval
            visits=[]
            def step(s,ignored,demand,actual_cfg):
                index=len(visits)
                assert actual_cfg is cfg and index<6 and abs(s.time_sec-(AT+150*index))<1e-8
                visits.append(index)
                return original(s,controls[index],demand,actual_cfg)
            coupling.run_coupled_interval=step
            try:
                yield
                assert visits==list(range(6))
            finally: coupling.run_coupled_interval=original

        all_points=[]
        for name,action in actions.items():
            started=time.perf_counter()
            with shared.shared_query_runtime_scope(),shared.shared_response_gc_scope(True),plan_scope(action):
                point=endpoint.evaluate_price_point(state,seq.first_action(action),forecast,(),
                    endpoint.ObjectiveSpec(cfg,depth_override=6,box_walk=False,score_mode='raw'),capture_response=True)
            assert not point.aborted and len(point.states)==6
            rows=[]
            for j,s in enumerate(point.states,1):
                cutoff=AT+150*j
                residence=[r for r in point.control_area_response['residence'] if r['end_sec']<=cutoff+1e-7]
                stock_costs=defaultdict(float)
                for r in residence:
                    for stock,count in r['inside_veh'].items(): stock_costs[stock]+=float(r['dt_h'])*float(count)
                ledger=s._control_area_ledger
                rows.append(dict(sim_sec=cutoff,ttt_omega_veh_h=sum(stock_costs.values()),costs=dict(stock_costs),
                    stocks=ledger.stocks,ramps=s.ramp_queue,urban_queue=s.urban_movement_queue,
                    storage=s.urban_link_storage,control_area_summary=dict(ttt_veh_h=ledger.ttt_veh_h,
                        exited_veh=ledger.ttd_veh,entered_veh=ledger.entered_veh,flow_counts=ledger.flow_counts)))
            save(name+'_discrete900.json',dict(seconds=time.perf_counter()-started,rows=rows))
            all_points.append(dict(name=name,rows=rows))
            print('discrete',name,[r['ttt_omega_veh_h'] for r in rows],flush=True)
            del point
        save('native_first150_targets.json', {str(t):json.loads((F/f'state_{t:06}.json').read_bytes())['vehicle_records']['full_network_link_counts'] for t in (AT,AT+150)})
        save('audit_done.json',dict(status='complete',forecasts=4,model_changes=False,native_runs=0,future_observations_used_as_input=False))
        raise verify.Done()
    sdmpc_pfo.solve=audit
    return adapter_main()
adapter.main=initialized_main
verify.main()
