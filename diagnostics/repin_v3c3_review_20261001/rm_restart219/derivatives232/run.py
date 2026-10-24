"""Bounded integration check of destination-preserving initialization in SDMPC AD."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import sys
import time

D = Path(__file__).resolve().parent
ROOT = D.parents[3]
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
CONFIG = D.parent / 'independent230/replay_v2/candidate_config.json'
OUTPUT = I / 'closedloop_recorded2700_budget_check_derivatives_rm232_destinations'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def save(name, value):
    (D / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')


def main():
    assert not OUTPUT.exists() and not (D / 'protocol.json').exists(), 'Preserve previous results'
    os.chdir(ROOT)
    for name, value in {'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1',
                        'NUMSIM_REPO_ROOT': str(ROOT / 'vendor/NumSim-mine'),
                        'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1',
                        'RW_DECISION_FAIL_FAST': '1', 'RW_MAINLINE_SG_ONLY': '1',
                        'RW_OFFSET_WRITER': 'experiment', 'RW_RAMP_AMBER_SEC': '0'}.items():
        os.environ[name] = value
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.GetCurrentProcess.restype = ctypes.c_void_p
    k.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    assert k.SetPriorityClass(k.GetCurrentProcess(), 0x4000)
    prior = json.loads((D.parent / 'link52_225/protocol.json').read_bytes())
    pins = {p: sha(ROOT / p) for p in prior['source_sha256']}
    pins[str(CONFIG)] = sha(CONFIG)
    pins[str(Path(__file__))] = sha(Path(__file__))
    protocol = dict(schema='recorded-controller-derivatives/v1', start_sec=2700,
        seed=47, horizon_sec=450, anchor_meter_green={},
        purpose='Check destination-preserving225 initialization in the actual SDMPC derivative worker. No fitting or optimization.',
        axes=[dict(kind='meter', key='RM_C10484', block=0, steps=[.001, .0005]),
              dict(kind='green', key='p1', owner='SC1004', block=0, steps=[.001, .0005])],
        max_ad_rollouts=1, max_independent_scalar_rollouts=9,
        primal_abs_tolerance=1e-7, cost_gradient_atol=.0001,
        resource_gradient_atol=.001, gradient_rtol=.001,
        no_optimization=True, no_native=True, no_push=True,
        future_observation_inputs=False, fit=0, source_pins=pins,
        tuning_sha256=sha(CONFIG), priority='BelowNormal',
        scope='One unchanged seed47 state; continuous stencils are derivative diagnostics, not executable commands or a native gain certificate.',
        known_nonsmooth_axis='SC1004 integer timing can kink: retain both one-sided slopes; do not tune coefficients to a derivative mismatch.',
        output=str(OUTPUT))
    save('protocol.json', protocol)
    argv = ['--at=2700', '--closedloop-recorded', '--warm-head-history', '--replay-vsl-history',
        '--fixed-replay-summary=' + str(I / 'native_rm_observation2700_writerfix_v3/analysis/summary.json'),
        '--recording-dir=D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47',
        '--derivative-check', '--derivative-protocol=' + str(D / 'protocol.json'),
        '--probe-label=rm232_destinations', '--tuning-json=' + str(CONFIG)]
    save('launch.json', dict(argv=argv, started_at=time.time(), pid=os.getpid(), output=str(OUTPUT)))
    sys.path.insert(0, str(ROOT))
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
    sys.argv = [str(Path(probe.__file__)), *argv]
    started = time.perf_counter()
    probe.main()
    report = json.loads((OUTPUT / 'summary.json').read_bytes())
    unchanged = all(sha(ROOT / p) == value for p, value in pins.items())
    assert unchanged and report['new_ad_rollouts'] == 1
    assert report['independent_scalar_query']['scalar_rollouts'] == 9
    save('completion.json', dict(status='complete_diagnostic_not_gain_qualified',
        output=str(OUTPUT), wall_sec=time.perf_counter() - started, source_unchanged=unchanged,
        primal_outputs_match=report['primal_outputs_match'],
        all_checked_gradients_match=report['all_checked_gradients_match'],
        ad_rollouts=1, independent_scalar_rollouts=9, fit=0, optimizer=0, native=0, fzp_reads=0))


if __name__ == '__main__':
    main()
