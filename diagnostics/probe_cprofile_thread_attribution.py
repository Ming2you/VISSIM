"""Reproduce cross-thread cProfile attribution without running the controller."""
import cProfile
import json
from pathlib import Path
import pstats
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]


def probe():
    go = threading.Event()
    entered = threading.Event()
    release = threading.Event()
    observations = []

    def child_marker():
        observations.append(('child_enter', threading.get_ident(), time.perf_counter()))
        entered.set()
        release.wait(timeout=5)
        observations.append(('child_exit', threading.get_ident(), time.perf_counter()))

    def child_target():
        go.wait(timeout=5)
        child_marker()

    def parent_marker():
        observations.append(('parent_enter', threading.get_ident(), time.perf_counter()))
        go.set()
        assert entered.wait(timeout=5)
        time.sleep(.02)
        observations.append(('parent_exit', threading.get_ident(), time.perf_counter()))

    worker = threading.Thread(target=child_target)
    worker.start()
    profiler = cProfile.Profile()
    profiler.enable()
    parent_marker()
    release.set()
    worker.join(timeout=5)
    assert not worker.is_alive()
    profiler.disable()
    raw = pstats.Stats(profiler).stats
    rows = []
    for key, values in raw.items():
        if key[2] not in ('parent_marker', 'child_marker'):
            continue
        rows.append({'function': key[2], 'primitive_calls': values[0], 'calls': values[1],
                     'self_wall_sec': values[2], 'inclusive_wall_sec': values[3],
                     'callers': [{'function': k[2], 'file': k[0], 'counts_times': list(v)}
                                 for k, v in values[4].items()]})
    child_recorded = any(row['function'] == 'child_marker' for row in rows)
    impossible = [caller for row in rows if row['function'] == 'child_marker'
                  for caller in row['callers'] if caller['function'] != 'child_target']
    return {'python': sys.version, 'observations': observations, 'functions': rows,
            'child_recorded_by_parent_enabled_profiler': child_recorded,
            'impossible_child_callers': impossible,
            'thread_scope_claim_main_only_valid': not child_recorded,
            'scope': 'Local interpreter reproduction; no controller/model changes.'}


if __name__ == '__main__':
    result = probe()
    target = ROOT / 'diagnostics/cprofile_thread_attribution.json'
    target.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
