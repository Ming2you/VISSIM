"""Exit-only process counters for normal benchmarks; no call/line profiling."""
import atexit
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def install(directory):
    path = Path(directory).resolve()
    if not path.is_relative_to(ROOT / 'diagnostics'):
        raise ValueError('Resource counter output must stay under diagnostics')
    path.mkdir(parents=True, exist_ok=True)
    stem = path / ('resource_' + str(os.getpid()))
    metadata = {'schema': 'normal-decision-process-counters/v1', 'pid': os.getpid(),
                'parent_pid': os.getppid(), 'start_perf_sec': time.perf_counter(),
                'start_process_cpu_sec': time.process_time(), 'initial_argv': list(sys.argv),
                'python_version': sys.version, 'function_instrumentation': False}
    stem.with_suffix('.started.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    finished = False

    def finish():
        nonlocal finished
        if finished:
            return
        finished = True
        metadata['finish_perf_sec'] = time.perf_counter()
        metadata['finish_process_cpu_sec'] = time.process_time()
        metadata['observed_lifetime_wall_sec'] = metadata['finish_perf_sec'] - metadata['start_perf_sec']
        metadata['observed_process_cpu_sec'] = metadata['finish_process_cpu_sec'] - metadata['start_process_cpu_sec']
        from diagnostics.decision_profile import memory_counters
        metadata['memory'] = memory_counters()
        module = sys.modules.get('evaluation.controllers.signal_actuation_contract')
        info = getattr(module, 'clock_cache_info', None)
        metadata['signal_clock_cache'] = info() if info is not None else None
        if module is not None:
            metadata['phase_window_cache'] = module._phase_windows.cache_info()._asdict()
        metadata['completed'] = True
        metadata['scope'] = ('Exit-only counter overhead applies equally to baseline and optimized benchmarks. '
                             'Worker CPU is additive work; worker lifetime and peak memory are not additive elapsed/peak totals.')
        stem.with_suffix('.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')

    atexit.register(finish)
    return finish
