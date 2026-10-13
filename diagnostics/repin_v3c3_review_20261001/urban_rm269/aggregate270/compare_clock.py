"""Bounded1s/10s aggregate RM response check using canonical saved-state setup.

Two predictions at1s, one at10s; reuse the completed10s protected forecast.
No optimizer, future traffic inputs, parameter fitting or native simulation.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
F = Path('E:/VISSIM_runs/20261008_coupling268_window_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
read = lambda path: json.loads(Path(path).read_bytes())
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dt', type=int, choices=(1, 10), required=True)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    out = args.out.resolve() if args.out else HERE/f'pair2400_dt{args.dt}'
    assert not out.exists(), 'Preserve prior attempt'
    assert not any((p/'STOP').exists() for p in (ROOT, HERE.parent, HERE))
    old = HERE/'forecast2400_dt10'
    assert read(old/'completion.json')['status'] == 'complete'
    assert read(old/'protocol.json')['tuning_sha256'] == sha(HERE/'config_dt10.json')
    for path,digest in read(HERE/'plan.json')['coupled_bridge_source_sha256'].items():
        if path.startswith('evaluation'):
            assert sha(ROOT/path)==digest, 'Cached hold predates a production change: '+path
    configs = [read(HERE/f'config_dt{dt}.json') for dt in (1, 10)]
    for cfg in configs:
        cfg['urban'].pop('known_wout_aggregate_step_sec')
    assert configs[0] == configs[1], 'Clock must be the only tuning difference'
    pins = {str(p):sha(p) for p in [HERE/f'config_dt{args.dt}.json', Path(__file__),
        *(ROOT/'evaluation/controllers'/name for name in ('aggregate_wout.py',
          'sdmpc_aggregate_transport.py', 'route_choice_corridor.py', 'runtime_setup.py',
          'sdmpc_stock_geometry.py'))]}
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[name] = '1'
    sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
    sys.argv = ['verify.py', '--at', '2400', '--out', str(out), '--no-prediction',
                '--cold-prices', '--tuning', str(HERE/f'config_dt{args.dt}.json'), '--decisions', str(F)]
    loader = importlib.util.spec_from_file_location('aggregate_clock_verifier', HERE.parents[1]/'urban260/verify.py')
    v = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(v)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter, sdmpc_pfo, sdmpc
    from evaluation.controllers import physical_ramp_branches as ramps, sdmpc_sequence as seq
    from evaluation.controllers import signal_actuation_contract as signals, area_leader_objective as constraints
    original_main = adapter.main

    def wrapped_main():
        capture = {}
        bound = ramps.configure_operating_bounds
        def capture_bound(state, cfg, reference):
            capture.update(state=state, cfg=cfg)
            return bound(state, cfg, reference)
        ramps.configure_operating_bounds = capture_bound
        initial_audit = sdmpc_pfo.solve
        def audit(reference, coord, policy, options, evaluate, derivative, quantities, check_budget, emit):
            try:
                initial_audit(reference, coord, policy, options, evaluate, derivative, quantities, check_budget, emit)
            except v.Done:
                pass
            assert read(out/'reference.json') == read(old/'reference.json')
            current, previous = read(out/'state.json'), read(old/'state.json')
            for key in ('time_sec', 'urban_link_storage', 'urban_movement_queue', 'ramp_queue'):
                assert current[key] == previous[key], key
            state, cfg = capture['state'], capture['cfg']
            obj = state.known_legsplit_route_state['aggregate_transport']
            storage = cfg.network.known_legsplit_routes['storage']
            initial_stock = cfg.network.urban_link_storage_veh[storage]-state.urban_link_storage[storage]
            assert obj.dt == args.dt and abs(obj.stock()-initial_stock) < 1e-8
            candidate = dict(sdmpc.meter_neighbors(coord, reference))['RM_C10681:release']
            start, end = coord.encode(reference), coord.encode(candidate)
            changes = [axis for a,b,axis in zip(start,end,coord.axes) if abs(a-b)>1e-10]
            assert len(changes) == 3 and all(a['kind']=='meter' and a['key']=='RM_C10681' for a in changes)
            rows = []
            for name, action in (('hold', reference), ('release', candidate)):
                coord.validate(action)
                for block in seq.actions(action, 3):
                    signals.validate_writer(block, cfg, adapter.load_signal_group_actuation_plan(), 'experiment')
                started = time.perf_counter()
                reused = args.dt == 10 and name == 'hold'
                item = read(old/'protected_seed_response.json') if reused else evaluate([action], derivatives=False)[0]
                seconds = time.perf_counter()-started
                assert sdmpc_pfo.model_feasible(item, options['shared_tolerance'])
                assert abs(sum(item['sdmpc_omega_partition']['costs'].values())-item['objective_veh_h']) < 1e-7
                if not reused:
                    v.save(name+'_response.json', item)
                shared = constraints.shared_quantity_constraints(adapter._PHASE_VECTOR_FOLLOWER['ref'], action,
                    item['quantities'], start_sec=2400, horizon_steps=3,
                    np_mode='cap', target_np_veh=action.N_P_star, np_tolerance_veh=options['np_tolerance_veh'],
                    nuf_mode='cap', target_nuf_veh_h=action.N_UF_star, nuf_tolerance_veh_h=options['nuf_tolerance_veh_h'])
                c=item['central_physical']
                physical=dict(zip(c['names'],c['values']))
                rows.append(dict(name=name, reused=reused, seconds=seconds,
                    omega_ttt_veh_h=item['objective_veh_h'], costs=item['sdmpc_omega_partition']['costs'],
                    merge=item['control_area']['predicted_ramp_merge']['accepted_vehicles_by_ramp'],
                    flow_counts=item['control_area']['flow_counts'],
                    wout_stock=[-physical[f'physical/{t}/storage/SC1004_W_out/upper'] for t in (2550,2700,2850)],
                    ramp_greens=[b.diagnostics['rw_meter_green_RM_C10681'] for b in seq.actions(action,3)],
                    shared_constraints=shared, model_feasible=True,
                    max_resource_excess=item['resource_summary']['max_exceedance_veh'],
                    transport_update_count=item['resource_summary']['kinds']['known_wout_connector_to_road']//4))
                assert rows[-1]['transport_update_count'] == 450//args.dt
                v.save('clock_response.json', dict(dt=args.dt, rows=rows, source_pins=pins,
                    native_runs=0, optimizer_calls=0, future_traffic_used=False,
                    scope='Same saved state and fixed non-RM commands; continuous-model response, not native gain'))
                print(args.dt, name, rows[-1]['omega_ttt_veh_h'], seconds, flush=True)
            for path, digest in pins.items():
                assert sha(path) == digest, path
            protocol = read(out/'protocol.json')
            protocol.update(max_predictions=2 if args.dt==1 else 1, reused_predictions=int(args.dt==10))
            v.save('protocol.json', protocol)
            raise v.Done()
        sdmpc_pfo.solve = audit
        return original_main()
    adapter.main = wrapped_main
    v.main()


if __name__ == '__main__':
    main()
