"""Two city/RM fixed-action decompositions through the canonical adapter.

2400: selected city with held RM, selected RM with held city;450s each.
No optimization, future observation input, parameter fit or native launch.
"""
import os
for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '1'
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
H = HERE.parent
F = Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
read = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
ap = argparse.ArgumentParser()
ap.add_argument('--at', type=int, choices=[2400], required=True)
ap.add_argument('--variant', choices=['action_split'], default='action_split')
args = ap.parse_args()
assert args.at in (2400,3300)
OUT = HERE / 'forecast2400_checked'
tuning = H / 'native_beta/config.json'


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False, default=lambda v: repr(v)[:600]) + '\n', encoding='utf8')


def main():
    assert not OUT.exists(), 'Do not overwrite or retry existing predictions'
    for p, h in read(HERE / 'plan.json')['source_pins'].items():
        assert sha(Path(p)) == h, p
    sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
    os.environ.update(NUMSIM_REPO_ROOT=str(ROOT / 'vendor/NumSim-mine'), PYTHONDONTWRITEBYTECODE='1')
    sys.argv = ['verify.py', '--at', str(args.at), '--out', str(OUT), '--no-prediction', '--tuning', str(tuning), '--decisions', str(F)]
    loader = importlib.util.spec_from_file_location('sc6_canonical_verifier', H.parent / 'urban260/verify.py')
    v = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(v)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter, sdmpc_pfo, sdmpc_sequence as seq
    from evaluation.controllers import physical_ramp_branches as ramps, signal_actuation_contract as signals
    from evaluation.controllers import area_leader_objective as constraints, area_meter_finalization as meters
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.area_runtime import model_inventory
    from src.controllers import rollout_endpoint as endpoint
    from src.models.state import ControlAction
    original_main = adapter.main

    def wrapped_main():
        captured = {}
        original_bounds, original_forecast = ramps.configure_operating_bounds, adapter.demand_from_state

        def bounds(state, cfg, reference):
            captured.update(state=state, cfg=cfg)
            return original_bounds(state, cfg, reference)

        def forecast(*a, **kw):
            result = original_forecast(*a, **kw)
            captured['forecast'] = result
            return result

        ramps.configure_operating_bounds, adapter.demand_from_state = bounds, forecast

        def audit(reference, coord, policy, options, evaluate, derivative, quantities, check_budget, emit):
            state, cfg = captured['state'], captured['cfg']
            save('network.json', vars(cfg.network))
            save('state.json', vars(state))
            save('reference.json', vars(reference))
            # Historical opaque runtime reprs include memory addresses. Compare
            # all serialized values, normalizing only those addresses; the same
            # pinned initializer constructs the nonserialized runtime objects.
            import re
            def normalized(x):
                if isinstance(x, str):return re.sub(r' at 0x[0-9A-Fa-f]+', ' at <address>', x)
                if isinstance(x, dict):return {k:normalized(v) for k,v in x.items()}
                if isinstance(x, list):return [normalized(v) for v in x]
                return x
            for file in ('state.json','network.json'):
                a=normalized(read(H/'native_beta/forecast2400_checked'/file));b=normalized(read(OUT/file))
                changed=[k for k in a.keys()|b.keys() if a.get(k)!=b.get(k)]
                assert not changed,(file,changed)
            assert cfg.network.head_service_resources['schema']=='physical-head-resource-join/v11'
            save('initialization_equivalence.json',dict(status='passed',scope='All serialized state/network values, memory addresses normalized; unchanged pinned initializer, v11 contract.'))
            pins = {str(p): sha(p) for p in (Path(__file__), tuning, ROOT / 'evaluation/controllers/head_service_resources.py',
                                            H.parent / 'urban260/verify.py', F / f'state_{args.at:06}.json')}
            depth=3
            source={}
            for name in ('hold','selected'):
                source[name]=[]
                for at in (2400,2550,2700):
                    p=H/'selection2400_discrete'/name/f'action_{at:06}.json'
                    pins[str(p)]=sha(p);pins[str(p.with_suffix('.csv'))]=sha(p.with_suffix('.csv'))
                    source[name].append(seq.first_action(adapter.control_from_json(p,cfg,ControlAction)))
            commands=[]
            proofs={}
            for name,meter_source,city_source in (('city_only','hold','selected'),('rm_only','selected','hold')):
                blocks=[];proof=[]
                for j in range(3):
                    hold,selected=source['hold'][j],source['selected'][j]
                    for field in ('N_P_star','N_UF_star','vsl','inflow_outflow_allocation'):
                        assert getattr(hold,field)==getattr(selected,field),(j,field)
                    meter,city=source[meter_source][j],source[city_source][j]
                    block=copy.deepcopy(meter)
                    block.green_times=copy.deepcopy(city.green_times)
                    block.offsets=copy.deepcopy(city.offsets)
                    # Reader consumes CSV ramp rows only. No city command is
                    # inherited from the retained meter-record provenance.
                    assert block.diagnostics==meter.diagnostics
                    assert ramps.physical_commands(block,cfg)==ramps.physical_commands(meter,cfg)
                    signals.validate_writer(block,cfg,adapter.load_signal_group_actuation_plan(),'experiment')
                    ramps.candidate_from_greens(block,blocks[-1] if blocks else source['hold'][0],cfg,
                        {k:block.diagnostics['rw_meter_green_'+k] for k in block.ramp_metering})
                    blocks.append(block)
                    proof.append(dict(at=2400+150*j,city_source=city_source,meter_source=meter_source,
                        green_times=block.green_times,offsets=block.offsets,meter_commands=ramps.physical_commands(block,cfg)))
                action=seq.pack(blocks)
                # Validate joint coordinates (storage/phase/green-change/VSL
                # constraints), not merely each copied field in isolation.
                coordinate_proof=coord.validate(action)
                proofs[name]=dict(blocks=proof,coordinate_proof=coordinate_proof)
                save(name+'.action.json',vars(action))
                commands.append((name,action))
            save('action_contract.json',proofs)
            groups = {k: [m for m in cfg.network.urban_movements if m.startswith(prefix)]
                      for k, prefix in [('SC6_S', 'SC6_S_SC12_'), ('SC6_E', 'SC6_E_SC104_'), ('SC12_S','SC12_S_SC16_'), ('SC16_S','SC16_S_SC109_')]}
            origins = {'SC6_S': 'SC12_to_SC6', 'SC6_E': 'SC104_to_SC6', 'SC12_S':'SC16_to_SC12', 'SC16_S':'SC109_to_SC16'}
            group_keys = {g: {'storage:' + origins[g], *('movement:' + m for m in moves)} for g, moves in groups.items()}

            def stock(s, g):
                return dict(queue={m: s.urban_movement_queue[m] for m in groups[g]},
                            occupied_storage=cfg.network.urban_link_storage_veh[origins[g]] - s.urban_link_storage[origins[g]])

            results = {}
            for name, action in commands:
                for b in seq.actions(action, depth):
                    signals.validate_writer(b, cfg, adapter.load_signal_group_actuation_plan(), 'experiment')
                started = time.perf_counter()
                with seq.prediction_scope(action, cfg, args.at, depth) as visits:
                    point = endpoint.evaluate_price_point(state, action, copy.deepcopy(captured['forecast'][:depth]), (),
                        endpoint.ObjectiveSpec(cfg, depth_override=depth, box_walk=False, score_mode='raw'), capture_response=True)
                save(name+'.rollout_status.json', dict(aborted=point.aborted, states=len(point.states), expected_depth=depth, visits=visits))
                assert not point.aborted and len(point.states) == depth
                assert visits == list(range(depth)) if depth == 3 else visits is None
                response = point.control_area_response
                import gzip
                with gzip.open(OUT/(name+'.response.json.gz'),'wt',encoding='utf8') as f:
                    json.dump(response,f,allow_nan=False)
                assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
                exceed = max((r['exceedance_veh'] for r in response['resource_allocations']), default=0.)
                assert exceed <= 1e-7
                for s in (state, *point.states):
                    get_ledger(s).assert_stocks(model_inventory(s, cfg))
                costs = {}
                for row in response['residence']:
                    for k, n in row['inside_veh'].items():
                        costs[k] = costs.get(k, 0.) + n * row['dt_h']
                assert abs(sum(costs.values()) - point.ttt) < 1e-7
                local = {}
                for g, moves in groups.items():
                    bins = []
                    for j in range(depth):
                        start = args.at + 150*j
                        transfers = [t for t in response['transfers'] if start <= t['start_sec'] < start+150]
                        incoming = sum(t['vehicles'] for t in transfers if t['target'] in group_keys[g] and t['source'] not in group_keys[g])
                        outgoing = sum(t['vehicles'] for t in transfers if t['source'] in group_keys[g] and t['target'] not in group_keys[g])
                        n0, n1 = stock((state, *point.states)[j], g), stock(point.states[j], g)
                        total = lambda d: sum(d['queue'].values()) + d['occupied_storage']
                        residual = total(n0) + incoming - outgoing - total(n1)
                        assert abs(residual) < 1e-7, (g, start, residual)
                        bins.append(dict(start_sec=start, initial=n0, final=n1, incoming_veh=incoming, outgoing_veh=outgoing,
                            local_balance_error_veh=residual, by_movement={m: sum(t['vehicles'] for t in transfers if t['source'] == 'movement:'+m) for m in moves}))
                    local[g] = dict(bins=bins, cost_veh_h=sum(costs.get(k, 0.) for k in group_keys[g]))
                shared = None
                if depth == 3:
                    follower = adapter._PHASE_VECTOR_FOLLOWER['ref']
                    quantities = constraints.shared_urban_quantities(follower, response, start_sec=args.at, horizon_steps=3)
                    shared = constraints.shared_quantity_constraints(follower, action, quantities, start_sec=args.at, horizon_steps=3,
                        np_mode='cap', target_np_veh=action.N_P_star, np_tolerance_veh=options['shared_tolerance'],
                        nuf_mode='cap', target_nuf_veh_h=action.N_UF_star, nuf_tolerance_veh_h=options['shared_tolerance'])
                results[name] = dict(omega_ttt_veh_h=point.ttt, costs_by_stock=costs, local=local,
                    predicted_merge=point.control_area['predicted_ramp_merge'], resource_max_exceedance=exceed,
                    shared_constraints=shared, wall_sec=time.perf_counter()-started,
                    conservation_states=depth+1, writer_validated=True)
                save(name+'.json', results[name])
                print(name, round(point.ttt, 6), 'SC6_left_rate', cfg.network.movement_capacity_by_movement_veh_h['SC6_S_SC12_to_W_SC5'], flush=True)
            save('summary.json', dict(status='complete', at=args.at, depth=depth, variant=args.variant, source_pins=pins,
                forecasts=len(commands), native_runs=0, optimizer_calls=0, future_observation_inputs=False,
                results=results, scope='Model-only factorial city/RM decomposition at same2400state. Previously computed held/joint endpoints reused; no independent native city-only/RM-only observations.'))
            raise v.Done()

        sdmpc_pfo.solve = audit
        return original_main()

    adapter.main = wrapped_main
    v.main()


if __name__ == '__main__':
    main()
