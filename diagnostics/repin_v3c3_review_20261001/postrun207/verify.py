"""Small provenance/summary checks only. Never starts or analyzes a native run."""
import ast
import json
from pathlib import Path

from diagnostics.sdmpc_n31_20260924.integration_20260926.native_pair1200 import analyze_pair as a

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
R = HERE.parent
I = ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
RUN = Path('D:/VISSIM_runs/20261004_sdmpc_fixed90_s29_9000')
NC = Path('D:/VISSIM_runs/20260927_sd31_wiring9000/nc')
NAMES = ('sdmpc31_nc9000_s29', 'sdmpc31_sdmpc9000_s29')


def main():
    # Same finalized first two decisions; no optimization or large trajectory reads.
    old_tree = ast.parse((HERE/'analyze_pair_before207.py.txt').read_text(encoding='utf-8-sig'))
    old_fn = next(n for n in old_tree.body if isinstance(n, ast.FunctionDef) and n.name == 'decision_summary')
    namespace = dict(vars(a))
    exec(compile(ast.Module(body=[old_fn], type_ignores=[]), 'pre207_decision_summary', 'exec'), namespace)
    decisions = RUN/'sdmpc'/('decisions_'+NAMES[1])
    old = namespace['decision_summary'](decisions, 900, 1200)
    new = a.decision_summary(decisions, 900, 1200)
    assert all(new[k] == v for k, v in old.items())
    assert new['optimized_decisions'] == 2 and new['held_error_decisions'] == 0

    sources = [NC/('run_provenance_'+NAMES[0]+'.json'),
               RUN/'sdmpc'/('run_provenance_'+NAMES[1]+'.json')]
    nc, control = [a.load(p) for p in sources]
    equal_values = {}
    for key in ('seed', 'sim_period_sec', 'control_interval_sec', 'demand_scale'):
        assert nc[key] == control[key], key
        equal_values[key] = nc[key]
    assert (nc['seed'], nc['sim_period_sec']) == (29, 9000)
    matched = {}
    for key in ('network', 'control_mapping', 'vehicle_input_roles', 'demand_profile',
                'urban_input_gate_map', 'generated_vbs_config', 'signal_group_plan'):
        assert nc['files'][key]['sha256'] == control['files'][key]['sha256'], key
        for prov in (nc, control):
            assert a.sha256(Path(prov['files'][key]['path'])) == prov['files'][key]['sha256'], key
        matched[key] = nc['files'][key]['sha256']
    env = {}
    for key in ('RW_MAINLINE_SG_ONLY', 'RW_OBS150_EXPECTED_SIMRES', 'RW_OBS150_VEHREC_SEC',
                'RW_OFFSET_WRITER', 'RW_RAMP_AMBER_SEC'):
        assert nc['env'][key] == control['env'][key], key
        env[key] = nc['env'][key]
    log = NC/('runlog_'+NAMES[0]+'.txt')
    lines = log.read_bytes().splitlines()
    assert lines.count(b'STAGE=SIM_DONE') == lines.count(b'SIM_SEC=9000') == 1
    summary_path = I/'expanded036_9000_20260930/analysis/summary.json'
    prior = a.load(summary_path)
    assert prior['arms']['nc']['native_execution_passed'] is True
    assert Path(prior['reused_nc_run']).resolve() == NC.resolve()
    fzp, = (NC/'vissim_eval').glob('*.fzp')
    stat = fzp.stat()  # Inventory only; do not reopen the completed large FZP.
    reference = dict(status='MATCHED_METADATA_NATIVE_COMPARISON_PENDING',
        values=equal_values, files=matched, env=env,
        provenance=[{'path': str(p), 'sha256': a.sha256(p)} for p in sources],
        nc_terminal_log={'path': str(log), 'sha256': a.sha256(log)},
        existing_nc_analysis={'path': str(summary_path), 'sha256': a.sha256(summary_path),
                              'prefix': prior['prefixes']['nc']},
        nc_fzp_inventory={'path': str(fzp), 'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns,
                          'read_or_rehashed_this_turn': False},
        limitations=['Matched source settings are not native physical equivalence proof.',
                     'Control/NC pre900 trajectory prefix still must match after the control run closes.',
                     'No existing R2 traffic result was recomputed.'])
    a.save(HERE/'matched_nc.json', reference)

    pins = a.load(R/'recovery_memory206/protocol.json')['source_sha256']
    assert all(a.sha256(ROOT/p) == digest for p, digest in pins.items())
    stop = Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    assert a.sha256(stop) == '91b2163b02b01447242909dee8e7f773d18e76a6594bd9db8de64d2a48246fc3'
    # All unrelated historical analyzer/verifier functions stay exactly the same.
    unchanged = {}
    for before, after, allowed in (
        ('analyze_pair_before207.py.txt', Path(a.__file__), {'main', 'decision_summary'}),
        ('verify_pair_before207.py.txt', ROOT/'diagnostics/com_execution_equivalence/verify_pair.py',
         {'verify_native_execution'})):
        def functions(p):
            return {n.name: ast.dump(n, include_attributes=False)
                    for n in ast.parse(p.read_text(encoding='utf-8-sig')).body
                    if isinstance(n, ast.FunctionDef)}
        prior_functions, current_functions = functions(HERE/before), functions(after)
        assert all(current_functions[k] == v for k, v in prior_functions.items() if k not in allowed)
        unchanged[str(after)] = len(set(prior_functions)-allowed)
    result = dict(status='PASS', existing_actual_normal_decisions_exact=2,
        native_calculation_performed=False, FZP_reads=0, fits=0, forecasts=0,
        unchanged_other_functions=unchanged, preserved_core_files=len(pins),
        old_stop_preserved=True, run_mutated=False, gain_qualified=False,
        matched_nc_sha256=a.sha256(HERE/'matched_nc.json'))
    a.save(HERE/'verification.json', result)
    python = Path('C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')
    analysis_output = R/'fixedvsl9000_197/analysis'
    a.save(HERE/'postprocess_plan.json', dict(
        status='PREPARED_WAIT_FOR_NATIVE_CLOSURE_NOT_STARTED', runs_root=str(RUN),
        output=str(analysis_output), native_status=str(RUN/'native_status.json'),
        run_id=control['run_id'], task_name='Codex-VISSIM-sd31-run-20261004202026583',
        owned_handles=[{'pid':25232,'start_time':'2026-10-04T20:20:27.1270234+09:00'},
                       {'pid':47760,'start_time':'2026-10-04T20:25:02.5723515+09:00'},
                       {'pid':37916,'original_start_time':'2026-10-04T20:25:04.473841+09:00',
                        'latest_start_time_unreadable':True}],
        prerequisites=[
            'Read current native_status and detached receipt; do not infer completion from this plan.',
            'Require SIM_DONE and SIM_SEC=9000 exactly once; actual wrapper status must be complete.',
            'Confirm this task/owned processes closed with exit0; PID birth must match, never terminate another process.',
            'Respect STOP. No automatic retries or new native run.',
            'Do not run if analysis summary already exists; preserve any failed output before considering repair.',
            'Verify pinned analyzer and verifier; native LDP, VSL readbacks, command holds, FZP prefix must pass.',
        ],
        command=[str(python),'-B','-m',
            'diagnostics.sdmpc_n31_20260924.integration_20260926.native_pair1200.analyze_pair',
            '--closed-loop-9000','--runs-root',str(RUN),'--nc-run-dir',str(NC),
            '--output-dir',str(analysis_output),'--status-json',str(RUN/'native_status.json')],
        cwd=str(ROOT),
        environment={'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1',
                     'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1',
                     'NUMSIM_REPO_ROOT':str(ROOT/'vendor/NumSim-mine')},
        source_sha256={str(p):a.sha256(p) for p in [Path(a.__file__),
            ROOT/'diagnostics/com_execution_equivalence/verify_pair.py']},
        matched_nc_proof={'path':str(HERE/'matched_nc.json'),'sha256':a.sha256(HERE/'matched_nc.json')},
        analysis_scope='Same Omega TTT and normal exit events, outside residence/uninserted/removals/residual; no calibration.',
        limitations=['Existing analyzer reads completed NC/control FZP only after closure; no live rescan.',
                     'LSA failure stays visible; user-approved LDP substitution must pass.',
                     'A held-error cycle may have verified native execution but no valid new prediction.',
                     'This finite run does not qualify general RM/VSL gain prediction.']))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
