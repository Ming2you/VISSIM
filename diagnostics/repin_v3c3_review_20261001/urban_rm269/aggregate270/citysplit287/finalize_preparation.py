"""Summarize completed fixed forecasts and canonical preflight, without a run."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = HERE.parent
H = A.parent
ROOT = H.parents[2]
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
PYTHON = 'C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'


def read(path):
    return json.loads(path.read_bytes())


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    result = read(HERE / 'forecast2400/summary.json')
    base = read(A / 'matched280/authority/summary.json')
    prep = read(HERE / 'native_preparation.json')
    protocol_path = Path(prep['protocol'])
    protocol_root = protocol_path.parent
    assert result['status'] == 'complete' and result['forecasts'] == 2
    assert result['application']['state_error'] == 0
    assert read(protocol_root / 'status.json')['stage'] == 'preflight_complete'
    protocol = read(protocol_path)
    assert not protocol['native_started'] and protocol['max_native_runs'] == 1
    assert protocol['arms'] == ['selected'] and protocol['automatic_retries'] == 0
    assert all(x['rm_vsl_held'] for x in protocol['physical_command_check'])
    for source, expected in result['source_pins'].items():
        assert sha(Path(source)) == expected, source
    for source, expected in protocol['command_pins'].items():
        assert sha(Path(source)) == expected, source
    all_results = dict(hold=base['results']['hold'], joint=base['results']['selected'], **result['results'])
    held = all_results['hold']['omega_ttt_veh_h']
    rows = {}
    for name, value in all_results.items():
        assert value['shared_constraints']['feasible']
        assert value['resource_max_exceedance'] < 1e-7
        assert value['writer_three_blocks'] and value['conservation_states'] == 4
        rows[name] = dict(omega_ttt_veh_h=value['omega_ttt_veh_h'],
            delta_from_hold_veh_h=value['omega_ttt_veh_h']-held,
            merge10681_veh=value['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681'])
    interaction = rows['joint']['omega_ttt_veh_h'] - rows['city_only']['omega_ttt_veh_h'] - rows['rm_only']['omega_ttt_veh_h'] + held
    assessment = dict(status='fixed_model_split_complete_native_preflight_passed',
        time_utc=datetime.now(timezone.utc).isoformat(), start_sec=2400, end_sec=2850,
        model_rows=rows, model_interaction_veh_h=interaction,
        additional_forecasts=2, reused_forecasts=2, optimizations=0, fits=0,
        native_dispatches=0, native_complete=False, goal_complete=False,
        physical_constraints_writer_conservation=True, source_pins_unchanged=True,
        initial_state_error=0, future_observation_inputs=False,
        conclusion='Large modeled joint savings mainly arise from city controls. Native city-only evidence is missing; no causal attribution or coefficient adoption.',
        remaining='Existing native joint change is harmful while model predicts benefit. Isolated10681 large component directions and two-state runtime passed; joint gain and VSL native qualification remain incomplete.',
        native_identification='City-only minus held identifies city effect at held RM; joint minus city-only identifies RM effect conditional on selected city. Native interaction requires a separate RM-only arm and is not identified here.',
        queue_gate='Existing coupling268 finite queue must finish normally and all exact owned processes must close. Do not dispatch or freeze now.')
    save(HERE / 'completion.json', assessment)
    post = read(H / 'isolated10681/postprocess_plan.json')
    analyzer = I / 'native_pair1200/analyze_pair.py'
    membership = H.parent / 'urban_area263/approaches_only/membership.json'
    post.update(status='prepared_not_started', analysis_attempts=0, FZP_analysis_passes=0,
        python=PYTHON, argv=[str(analyzer), '--replay-protocol', str(protocol_path),
        '--runs-root', prep['output'], '--output-dir', 'E:/VISSIM_analysis/20261010_urbanrm269_cityonly287',
        '--membership-json', str(membership)],
        source_pins={p:sha(Path(p)) for p in post['source_pins']},
        followup='Match native prefix/execution, then compare city-only to reused hold and completed joint; no interaction claim without RM-only native.',
        complete_sdmpc_wall_benchmark_pending=False)
    post.pop('assessment', None)
    save(HERE / 'postprocess_plan.json', post)
    pins = {str(p):sha(p) for p in [protocol_path, protocol_root/'launch_inputs.json',
        protocol_root/'selected/config_replay.json', protocol_root/'selected/plant_replay.json',
        protocol_root/'selected/replay.vbs', protocol_root/'selected/replay_sgplan.vbs',
        I/'native_pair1200/run_pair.ps1', ROOT/'tools/sdmpc31/freeze_worktree.ps1',
        ROOT/'diagnostics/sdmpc_n31_20260924/tools/freeze_manifest.py', HERE/'postprocess_plan.json']}
    save(HERE / 'launch_plan.json', dict(status='ready_wait_existing_queue_normal_completion',
        protocol=str(protocol_path), results_root=prep['output'], runtime=prep['runtime'],
        maximum_new_native_arms=1, native_dispatches=0, automatic_retries=0,
        preflight_passed=True, frozen_tree=None, source_pins=pins,
        queue_authority='E:/VISSIM_runtime/20261008_coupling268_vsl_three/queue_state.json',
        queue_last_verified=dict(stage='native', condition='off', last_sim_sec=2850,
            pid=4600, birth_utc='2026-10-07T20:38:08.669657Z',
            vissim_pid=41468, vissim_birth_utc='2026-10-09T12:06:54.723367Z'),
        guard='Recheck live identities, all STOPs, no duplicate attempt, disk space and source pins. Require existing finite queue normal closure before freeze/dispatch. No automatic retry.',
        freeze_tool='tools/sdmpc31/freeze_worktree.ps1',
        run_tool='diagnostics/sdmpc_n31_20260924/integration_20260926/native_pair1200/run_pair.ps1',
        run_arguments=['-FrozenTree','<verified new FREEZE_DONE tree>','-ProtocolPath',str(protocol_path),'-ResultsRoot',prep['output']],
        concurrency=[], no_global_kill=True, max_attempts=1, startup_stall_sec=300,
        source_during_freeze_must_remain_unchanged=True))
    for path in (A/'plan.json', H/'plan.json'):
        plan = read(path)
        plan.update(current_stage='citysplit287 complete offline/preflight; native waiting for finite queue',
            current_receipt=str(HERE/'completion.json'),
            latest_stage=str(HERE), current_workers=[],
            clock_current=dict(freeway_sec=5, urban_sec=10, control_sec=150, horizon_sec=450,
                internal_substeps_retained=True, terminal_cost=False,
                full_choice_wall_sec=[284.8641347,321.433798], full_choice_iteration_caps=dict(pfo=2,sdmpc=2),
                full_choice_converged=False, live_native_frozen_tree_unchanged=True),
            next_step='After finite queue normal closure, recheck citysplit287/launch_plan.json; canonical freeze and one city-only2850 replay, reuse closed hold. No more unchanged forecasts/timing/parameter search.',
            latest_goal_turn_audit=dict(outcome='progress', evidence=str(HERE/'completion.json'), goal_complete=False),
            updated_utc=assessment['time_utc'])
        if path == A/'plan.json':
            plan['mainline_5sec_review_historical'] = plan['mainline_5sec_review']
            plan['mainline_5sec_review'] = dict(status='implemented_opt_in_and_two_state_choice_verified',
                evidence='urban_clock277/README.md; selection284; decision285',
                current_mainline_step_sec=5, internal_short_cell_substeps=True, native_changed=False)
            plan['representation']['clock'] = 'Current opt-in FW/ramp5s, urban10s. Short FW and urban CTM retain smaller internal steps; accepted transfers/ownership conserved. Control150s, horizon450s.'
        save(path, plan)
    print('OFFLINE_SPLIT_AND_PREFLIGHT_COMPLETE_NATIVE0', json.dumps(rows), flush=True)


if __name__ == '__main__':
    main()
