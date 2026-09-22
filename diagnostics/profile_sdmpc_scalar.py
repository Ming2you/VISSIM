"""Profile the pinned continuous scalar trajectory, without VISSIM."""
from pathlib import Path
import cProfile
import hashlib
import json
import pickle
import pstats
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]


def main():
    from evaluation.controllers.sdmpc_tangent_runtime import install
    finder = install(ROOT, 'reverse-v1')
    from evaluation.controllers.sdmpc_tangent_worker import run
    source, out = map(Path, sys.argv[1:3])
    out.mkdir(parents=True, exist_ok=False)
    request = pickle.loads((source/'request.pickle').read_bytes())
    request.pop('diagnostic_checkpoint', None)
    request['scalar_only'] = True
    for name in request['bootstrap']['runtime_sources']:
        request['bootstrap']['runtime_sources'][name] = hashlib.sha256(Path(name).read_bytes()).hexdigest()
    profile = cProfile.Profile()
    try:
        result = profile.runcall(run, request, finder, {})
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    finally:
        profile.dump_stats(str(out/'profile.pstats'))
        with (out/'profile.txt').open('w', encoding='utf-8') as stream:
            stats = pstats.Stats(profile, stream=stream)
            stats.sort_stats('cumulative').print_stats(65)
            stats.sort_stats('tottime').print_stats(40)


if __name__ == '__main__':
    main()
