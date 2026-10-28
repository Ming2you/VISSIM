# Assemble A1_LAUNCH_ENV.json (read-only toward run files). Usage: python -B a1_env_record.py <out.json> [run]
# Without 'run': declared env + the preflight2 wrapper dump (same WMI path the run uses).
# With 'run': also the run wrapper dump and its differences from the preflight2 dump.
import datetime, hashlib, json, os, sys
RES = 'D:/VISSIM_runs/20261025_codex_a1_s29'
REC = RES + '/a1_launch'
LAUNCH = 'D:/VISSIM_runtime/20261025_codex_a1/launch'


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def load(p):
    return json.load(open(p, encoding='utf-8-sig'))


pf_env = load(REC + '/wrapper_preflight2_env.json')
pf_py = load(REC + '/wrapper_preflight2_python.json')
pf_start = load(REC + '/wrapper_preflight2_started.json')
prov = load(RES + '/sdmpc/preflight/run_provenance_sdmpc31_sdmpc8100_s29.json')
out = {
    'what': 'A1 (64cf-s29 joint 8100 s) launch environment. run_provenance /env records RW_* only (PRE_A1 r2 section 1), so every other variable is recorded here.',
    'written_at': datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
    'decisions': {'U1': '(b) env_hsw', 'U6': '(b) S1 not used (no PYTHONPYCACHEPREFIX, no NUMBA_NUM_THREADS)', 'U10': '(b) PYTHONHASHSEED=0',
                  'source': 'NOTES D-K9-85 (sha 67dcc32b...), PRE_A1 r2 (sha 2d9aa15a...)'},
    'set_by_wrapper': pf_env['set'],
    'removed_by_wrapper': pf_env['removed'] + ['RW_* (all names)'],
    'set_by_runner_read_from_code': {
        'source': 'run_closedloop3000.ps1:109-117 (sha 8e95423b...), run as-is',
        'removes': 'every RW_* (SetEnvironmentVariable(name, $null) under pwsh 7 leaves an empty value; the wrapper already removed them so none is inherited)',
        'RW_PYTHON': '<-PythonExe>', 'RW_MAINLINE_SG_ONLY': '1', 'RW_OFFSET_WRITER': 'experiment', 'RW_RAMP_AMBER_SEC': '0',
        'RW_DECISION_FAIL_FAST': '1', 'RW_QUEUE_COUNTER': '1', 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1',
        'PYTHONPATH': '<-DependenciesPath>;<frozen tree>', 'NUMSIM_REPO_ROOT': '<frozen tree>/vendor/NumSim-mine',
        'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'},
    'rw_env_written_by_watchdog_preflight2': prov['env'],
    'python': {'exe': pf_py['python_exe'], 'version_vv': pf_py['python_vv'], 'probe_under_wrapper_env_plus_deps_pythonpath': pf_py['probe'],
               'why_this_interpreter': 'Same interpreter as the A0/A0b replays (U9 reading needs the same conditions); PRE_A1 U1 says either interpreter; Python 3.12.14 was bit-identical in A0 (T=4950).'},
    'dependencies_path': pf_py['deps'],
    'powershell': {'exe': pf_py['pwsh'], 'version': pf_start['ps_version'],
                   'note': 'codex record ran the runner under the codex-runtime pwsh (its version is not in the raw record); PRE_A1 does not fix it.'},
    'launch': {'method': 'WMI Win32_Process.Create (detached), PriorityClass 32 = Normal (PRE_A1 U5 (b)), runner without -Detached',
               'launcher': LAUNCH + '/a1_launch_wmi.ps1', 'launcher_sha256': sha(LAUNCH + '/a1_launch_wmi.ps1'),
               'wrapper': LAUNCH + '/a1_wrapper.ps1', 'wrapper_sha256': sha(LAUNCH + '/a1_wrapper.ps1')},
    'process_env_preflight2': {'file': REC + '/wrapper_preflight2_env.json', 'sha256': sha(REC + '/wrapper_preflight2_env.json'),
                               'note': 'Whole environment the runner inherits, captured inside the WMI-created wrapper after its changes (secret-looking names redacted).',
                               'process_env': pf_env['process_env']},
}
if len(sys.argv) > 2 and sys.argv[2] == 'run':
    rn = load(REC + '/wrapper_run_env.json')
    rp = load(REC + '/wrapper_run_python.json')
    a, b = pf_env['process_env'], rn['process_env']
    out['process_env_run'] = {'file': REC + '/wrapper_run_env.json', 'sha256': sha(REC + '/wrapper_run_env.json'), 'process_env': b,
                              'diff_vs_preflight2': {'only_run': sorted(set(b) - set(a)), 'only_preflight2': sorted(set(a) - set(b)),
                                                     'value_changed': sorted(k for k in set(a) & set(b) if a[k] != b[k])}}
    out['python_run'] = {'version_vv': rp['python_vv'], 'probe': rp['probe']}
json.dump(out, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('written', sys.argv[1], sha(sys.argv[1]))
