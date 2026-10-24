"""Opt-in cProfile in the adapter and every spawned Python worker.

Timing instrumentation never wraps model functions or changes their arguments.
Function times use the profiler's wall clock. This Python 3.12 build mixes thread
events in cProfile, invalidating caller/time attribution when threads overlap;
see probe_cprofile_thread_attribution.py. Process CPU/lifetime remain independent
measurements. Neither worker lifetime nor cumulative function time is an additive
decomposition of the parent decision's wall time.
"""
import atexit
import cProfile
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def memory_counters():
    if sys.platform != 'win32':
        return {'available': False, 'reason': 'Windows process counters only'}
    import ctypes
    from ctypes import wintypes
    size = ctypes.c_size_t
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                    ('PeakWorkingSetSize', size), ('WorkingSetSize', size),
                    ('QuotaPeakPagedPoolUsage', size), ('QuotaPagedPoolUsage', size),
                    ('QuotaPeakNonPagedPoolUsage', size), ('QuotaNonPagedPoolUsage', size),
                    ('PagefileUsage', size), ('PeakPagefileUsage', size)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    value = Counters()
    value.cb = ctypes.sizeof(value)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(value), value.cb):
        return {'available': False, 'windows_error': ctypes.get_last_error()}
    return {'available': True, 'peak_working_set_bytes': value.PeakWorkingSetSize,
            'working_set_bytes_at_finish': value.WorkingSetSize,
            'peak_commit_bytes': value.PeakPagefileUsage,
            'page_fault_count': value.PageFaultCount}


def install(directory):
    path = Path(directory).resolve()
    if not path.is_relative_to((ROOT / 'diagnostics').resolve()):
        raise ValueError('Diagnostic profiles must stay under workspace diagnostics')
    if sys.getprofile() is not None:
        raise ValueError('Cannot combine cProfile with another Python profiling hook')
    if sys.gettrace() is not None or any(sys.monitoring.get_tool(i) is not None for i in range(6)):
        raise ValueError('Cannot combine cProfile with another trace/monitoring tool')
    path.mkdir(parents=True, exist_ok=True)
    pid = os.getpid()
    stem = path / ('process_' + str(pid))
    metadata = {'schema': 'decision-process-profile/v1', 'pid': pid,
                'parent_pid': os.getppid(), 'initial_argv': list(sys.argv),
                'start_unix_ns': time.time_ns(), 'start_perf_sec': time.perf_counter(),
                'start_process_cpu_sec': time.process_time(),
                'thread_scope': 'cProfile may mix thread events on Python 3.12; process_time includes all threads',
                'python_version': sys.version,
                'function_attribution_requires_thread_audit': True,
                'bootstrap_imports_before_profile': True}
    stem.with_suffix('.started.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    profiler = cProfile.Profile()
    finished = False

    def finish():
        nonlocal finished
        if finished:
            return
        finished = True
        profiler.disable()
        metadata.update(finish_perf_sec=time.perf_counter(), finish_unix_ns=time.time_ns(),
                        finish_process_cpu_sec=time.process_time(), final_argv=list(sys.argv))
        metadata['profiled_lifetime_wall_sec'] = metadata['finish_perf_sec'] - metadata['start_perf_sec']
        metadata['process_cpu_sec'] = metadata['finish_process_cpu_sec'] - metadata['start_process_cpu_sec']
        metadata['memory'] = memory_counters()
        stats = stem.with_suffix('.pstats')
        export_started = time.perf_counter()
        profiler.dump_stats(str(stats))
        metadata['profile_export_wall_sec'] = time.perf_counter() - export_started
        metadata['pstats'] = str(stats.relative_to(ROOT))
        metadata['completed'] = True
        stem.with_suffix('.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')

    # spawn_main exits through sys.exit, so each worker flushes its own profile.
    atexit.register(finish)
    profiler.enable()
    return finish
