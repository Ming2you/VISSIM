"""Eight fixed 450s responses at V3 t2400; no solver, price fit, COM, or native run."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_suffix('')/'attempt02'
RUN = ROOT/'evaluation/runs/codex_fid_cl9000_s13_v3/decisions_codex_fid_cl9000_s13_v3'
CONFIG = ROOT/'diagnostics/selected_control_demand/codex_fid_cl9000_s13_v3/config.json'
FIELDS = ('N_P_star', 'N_UF_star', 'ramp_metering', 'vsl', 'green_times', 'offsets', 'inflow_outflow_allocation')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
packed_sha = lambda v: hashlib.sha256(pickle.dumps(v, protocol=5)).hexdigest()


def worker():
    os.chdir(ROOT)
    os.environ['RW_OFFSET_WRITER'] = 'experiment'
    sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
    started = time.perf_counter()
    paths = [Path(__file__), CONFIG, RUN/'state_002400.json', RUN/'action_002250.json',
             RUN/'action_002400.json', RUN/'action_002400.joint.json']
    paths += list((ROOT/'evaluation/controllers').glob('*.py'))
    pins = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    report = {'completed': False, 'native_run': False, 'full_solver_runs': 0, 'price_fits': 0,
              'endpoint_limit': 8, 'source_sha256': pins, 'rows': [],
              'scope': 'Same recorded2400 state and450s forecast; original actual-command trust box, recorded prices and targets. Counterfactual model responses only, not native benefits or GNE.'}
    try:
        from diagnostics.probe_model_area_integration import build_projected
        from evaluation.controllers import vissim_stackelberg_adapter as a, area_follower_objective as area
        from evaluation.controllers.area_leader_objective import install_joint_price_field, fixed_joint_price_terms, shared_quantity_constraints
        from evaluation.controllers import joint_owner_game as game
        from src.models.state import ControlAction, segment_vsl
        from src.models.demand import DemandStep

        joint = json.loads((RUN/'action_002400.joint.json').read_text())
        recorded = joint['selected_diagnostics']['joint_shared_response']
        cfg, state, det, tuning, raw, mapping, metadata = build_projected(CONFIG, RUN/'state_002400.json', RUN/'action_002250.json', fixture_inputs=False)
        cal = a.deep_update(dict(a.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))), tuning.get('calibration_override', {}))
        forecast = a.demand_from_state(raw, cfg, DemandStep, 3, cal, det)
        controller = a.build_priced_wu_link_controller(cfg, tuning)
        follower = controller.nash_solver
        historical = a.control_from_json(RUN/'action_002250.json', cfg, ControlAction)
        historical, _ = area.expand_shared_vsl_action(historical, cfg, segment_vsl_func=segment_vsl)
        selected = a.control_from_json(RUN/'action_002400.json', cfg, ControlAction)
        selected, _ = area.expand_shared_vsl_action(selected, cfg, segment_vsl_func=segment_vsl)
        reference = historical.copy()
        reference.N_UF_star = recorded['quantity_constraints']['nuf']['target']
        reference.N_P_star = recorded['quantity_constraints']['np']['target']
        assert reference.N_P_star == 2400.0
        assert reference.N_UF_star == 2996.9313872526645
        assert cfg.mpc.horizon_steps == 3 and cfg.simulation.T_c_sec == 150
        assert joint['selected_price_field']['context']['beta_seconds'] == 0.0
        assert all(getattr(reference, k) == v for k,v in joint['selected_price_field']['reference_levers'].items())
        field = copy.deepcopy(joint['selected_price_field'])
        nodes = {s:node for s,node in cfg.network.signal_actuation_contract['nodes'].items() if node.get('native_clock_basis') is not None}
        # JSON receipts turn cached native tuple fields into lists. Restore only
        # the container types after proving the entire serialized value equal.
        assert json.dumps(field['context']['native_clock_nodes'],sort_keys=True) == json.dumps(nodes,sort_keys=True)
        report['native_clock_context_json_values_exact'] = True
        field['context']['native_clock_nodes'] = copy.deepcopy(nodes)
        report['native_clock_context_tuple_rehydration'] = 'Only JSON list/tuple representation restored from equal current native nodes; no physical value or recorded hash changed.'
        report['price_installation'] = install_joint_price_field(follower, reference, field,
            expected_owners=tuple(cfg.network.signals)+tuple(cfg.network.freeway_links),
            expected_context=field['context'], nuf_mode='equality')
        report['recorded_field_sha256'] = hashlib.sha256(json.dumps(joint['selected_price_field'], sort_keys=True).encode()).hexdigest()
        report['replayed_price_context_note'] = 'Loaded recorded field; exact reference levers and native clock checked by canonical installer. Original process-local frozen_digest is retained provenance, not claimed equal to this new Python object graph.'
        callbacks, context, fingerprint = area._joint_runtime_callbacks(follower, state, forecast, historical,
            reference, mapping, pins, reference=reference, total_budget=None, directional={}, tolerance=40.0)
        controls = {'hold': reference, 'selected': selected}
        families = {}
        for owner in ('FW_W', 'FW_E'):
            neighborhood = callbacks['neighbors'](owner, reference, context)
            assert len(neighborhood.candidates) == 63
            for index, candidate in enumerate(neighborhood.candidates[1:4], start=1):
                changed = game.assert_owner_transition(callbacks['ownership'], owner, reference, candidate)
                family = '+'.join(sorted({field for field,key in changed}))
                name = f'{owner}_neighbor{index}'
                controls[name] = candidate
                families[name] = {'owner': owner, 'index': index, 'family': family, 'changed_addresses': changed}
        assert len(controls) == 8
        report['families'] = families
        policy = {'leader_present': True, 'np_mode': 'cap', 'nuf_mode': 'equality',
                  'inactive_price_addresses': dict.fromkeys(('phase', 'offset', 'vsl', 'meter'), ())}
        fixed = pickle.dumps((follower, state, reference, historical, forecast, policy), protocol=5)
        report['model_inputs_sha256'] = hashlib.sha256(fixed).hexdigest()
        report['forecast_sha256'] = packed_sha(forecast)
        report['state_sha256'] = packed_sha(state)
        report['setup_sec'] = time.perf_counter()-started
        print(json.dumps({'stage':'setup_complete','seconds':report['setup_sec'],'candidates':len(controls)}), flush=True)
        commands = {}
        for name, control in controls.items():
            callbacks['move_box'].validate(control)
            evidence = callbacks['command_evidence'](control)
            commands[name] = evidence['ordered_rows']
            assert len(commands[name]) == 213
        t = time.perf_counter()
        batch = area.evaluate_shared_owner_batch(follower, state, reference, forecast, tuple(controls.values()), horizon_steps=3)
        report['batch_wall_sec'] = time.perf_counter()-t
        report['endpoint_calls'] = batch['endpoint_calls']
        assert batch['endpoint_calls'] == 8
        for (name, control), item in zip(controls.items(), batch['results']):
            assert packed_sha(control) == item['action_token']
            additions = fixed_joint_price_terms(follower, control, item['quantities'], lambda_p=follower._lambda_P,
                lambda_uf=follower._lambda_UF, target_np_veh=2400.0, target_nuf_veh_h=reference.N_UF_star, price_context=policy)
            costs = {owner: item['local_base_costs'][owner]+additions['owners'][owner]['total'] for owner in item['local_base_costs']}
            q = shared_quantity_constraints(follower, control, item['quantities'], start_sec=state.time_sec,
                horizon_steps=3, np_mode='cap', target_np_veh=2400.0, np_tolerance_veh=1e-7,
                nuf_mode='equality', target_nuf_veh_h=reference.N_UF_star, nuf_tolerance_veh_h=40.0)
            witnessed = item['conditional_model_feasibility_witness'] and item['model_constraint_coverage']['complete']
            feasible = witnessed and item['resource_summary']['max_exceedance_veh'] <= 1e-7 and q['feasible']
            row = {'name':name,'objective_veh_h':item['objective_veh_h'],'control_area':item['control_area'],
                'owner_costs':costs,'local_base_costs':item['local_base_costs'],'additive_terms':additions,
                'quantity_constraints':q,'feasible':feasible,'model_constraint_coverage':item['model_constraint_coverage'],
                'resource_summary':item['resource_summary'],'response_token':item['response_token'],
                'model_inputs_token':item['frozen_context_token'],'action_token':item['action_token'],
                'fields':{k:getattr(control,k) for k in FIELDS}, 'command_rows':commands[name],
                'physical_changes_from_hold':[{'before':old,'after':new} for old,new in zip(commands['hold'],commands[name]) if old!=new]}
            report['rows'].append(row)
            print(json.dumps({'name':name,'TTT':item['objective_veh_h'],'feasible':feasible,'NP':q['np']['actual'],'NUF':q['nuf']['actual']}), flush=True)
        assert len({r['model_inputs_token'] for r in report['rows']}) == 1
        assert pickle.dumps((follower,state,reference,historical,forecast,policy),protocol=5) == fixed
        hold, chosen = report['rows'][:2]
        report['replay_checks'] = {
            'same_inputs_after_queries':True,
            'hold_nuf_matches_recorded':abs(hold['quantity_constraints']['nuf']['actual']-reference.N_UF_star)<=1e-7,
            'hold_np_matches_recorded':abs(hold['quantity_constraints']['np']['actual']-316.1265184070456)<=1e-7,
            'selected_objective_matches_recorded':abs(chosen['objective_veh_h']-recorded['objective_veh_h'])<=1e-7,
            'hold_FW_W_own_cost_matches_recorded':abs(hold['owner_costs']['FW_W']-124.8934140223018)<=1e-7,
            'hold_FW_E_own_cost_matches_recorded':abs(hold['owner_costs']['FW_E']-120.83859787978206)<=1e-7}
        report['completed'] = all(report['replay_checks'].values())
        for row in report['rows']:
            row['delta_objective_from_hold_veh_h'] = row['objective_veh_h']-hold['objective_veh_h']
            row['delta_own_cost_from_hold'] = {o:v-hold['owner_costs'][o] for o,v in row['owner_costs'].items()}
    except Exception:
        report['error'] = traceback.format_exc()
        print(report['error'], flush=True)
    finally:
        report['source_changes'] = [p for p,h in pins.items() if sha(ROOT/p)!=h]
        report['completed'] = report['completed'] and not report['source_changes']
        report['wall_sec'] = time.perf_counter()-started
        (OUT/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    return 0 if report['completed'] else 1


def main():
    if sys.argv[1:] == ['--worker']:
        return worker()
    if sys.argv[1:]: raise ValueError('No options except private worker marker')
    OUT.mkdir(exist_ok=False)
    started = time.perf_counter()
    receipt = {'completed':False,'timeout_sec':300,'native_run':False,'owned_process_only':True}
    try:
        with (OUT/'stdout.txt').open('xb') as out, (OUT/'stderr.txt').open('xb') as err:
            p = subprocess.run([sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),'--worker'],
                cwd=ROOT,stdout=out,stderr=err,timeout=300)
        receipt.update(exit_code=p.returncode,completed=p.returncode==0)
    except subprocess.TimeoutExpired:
        receipt['failure']='Owned offline worker exceeded300s; subprocess.run terminated this child only.'
    finally:
        receipt['wall_sec']=time.perf_counter()-started
        (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(receipt),flush=True)
    return 0 if receipt['completed'] else 1


if __name__=='__main__': sys.exit(main())
