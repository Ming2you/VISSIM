"""Compare full old/new validators on preserved prediction evidence."""
from pathlib import Path
import json
import hashlib
import pickle
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]


def main():
    from evaluation.controllers.sdmpc_tangent_worker import state_error as old
    from evaluation.controllers.sdmpc_tangent_state import state_error as new
    source, output = map(Path, sys.argv[1:3])
    if output.exists():
        raise ValueError('Do not replace earlier validation evidence')
    started = time.perf_counter()
    with source.open('rb') as stream:
        data = pickle.load(stream)
    load_sec = time.perf_counter()-started
    print('loaded', load_sec, flush=True)
    times, errors = {}, {}
    methods = [('legacy', old), ('fast', new)]
    if '--recorded-legacy' in sys.argv:
        recorded = json.loads((source.parent/'result.json').read_text())
        if not recorded['complete_primal_state_match']:
            raise ValueError('Missing legacy full-state qualification')
        errors['legacy'] = recorded['max_primal_state_error']
        methods = [('fast', new)]
    for name, fn in methods:
        started = time.perf_counter()
        errors[name] = fn(data['scalar_states'], data['tangent_states'])
        times[name] = time.perf_counter()-started
        print(name, errors[name], times[name], flush=True)
    report = dict(source=str(source), source_sha256=hashlib.file_digest(source.open('rb'), 'sha256').hexdigest(),
                  legacy_reused='--recorded-legacy' in sys.argv,
                  comparator_sha256=hashlib.sha256((ROOT/'evaluation/controllers/sdmpc_tangent_state.py').read_bytes()).hexdigest(),
                  load_sec=load_sec, errors=errors, seconds=times,
                  pass_all=errors['legacy'] == errors['fast'])
    output.write_text(json.dumps(report, indent=2)+'\n')
    return 0 if report['pass_all'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
