"""Profile one canonical aggregate450s scalar worker, without optimization or native runs."""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import ctypes
import hashlib
import importlib.util
import json
import pickle
import pstats
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
H = HERE.parent
ROOT = H.parents[2]
OUT = HERE / 'profile_scalar'
CONFIG = HERE / 'config_dt10.json'
DECISIONS = Path('E:/VISSIM_runs/20261008_coupling268_window_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')

def save(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf8')

def main():
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    assert not OUT.exists(), 'Preserve previous profile; no duplicate attempt'
    assert not any((p/'STOP').exists() for p in (ROOT,H,HERE))
    for p,d in json.loads((HERE/'profile_plan.json').read_bytes())['source_pins'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==d,p
    sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
    os.environ.update(NUMSIM_REPO_ROOT=str(ROOT/'vendor/NumSim-mine'), PYTHONDONTWRITEBYTECODE='1')
    sys.argv = ['verify.py', '--at', '2400', '--out', str(OUT), '--no-prediction', '--cold-prices',
                '--tuning', str(CONFIG), '--decisions', str(DECISIONS)]
    spec = importlib.util.spec_from_file_location('profile_verifier', H.parent/'urban260/verify.py')
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter, sdmpc_pfo
    from evaluation.controllers.sdmpc_tangent_surrogate import Query
    original = adapter.main

    def wrapped():
        def audit(reference, coord, policy, options, evaluate, derivative, quantities, check_budget, emit):
            query = derivative.__self__
            assert isinstance(query, Query) and query.stats()['total_rollouts'] == 0
            request = pickle.loads(query.template)
            assert request['horizon'] == 3
            request.update(action=reference, surrogate_evaluation='scalar',
                           surrogate_context_sha256=query.context_token)
            request_bytes = pickle.dumps(request, protocol=5)
            request_path, result_path = OUT/'request.pickle', OUT/'result.pickle'
            request_path.write_bytes(request_bytes)
            digest = hashlib.sha256(request_bytes).hexdigest()
            worker = ROOT/'evaluation/controllers/sdmpc_tangent_worker.py'
            command = [sys.executable, '-B', '-m', 'cProfile', '-o', str(OUT/'worker.prof'),
                       str(worker), str(request_path), str(result_path), digest, 'reverse-v1']
            save('receipt.json', dict(status='running_one_profile', command=command,
                horizon_sec=450, optimizer_calls=0, native_runs=0, maximum_ad_rollouts=0, maximum_scalar_rollouts=1,
                config_sha256=hashlib.sha256(CONFIG.read_bytes()).hexdigest()))
            started = time.perf_counter()
            with (OUT/'worker.stdout.log').open('w', encoding='utf8') as stdout, (OUT/'worker.stderr.log').open('w', encoding='utf8') as stderr:
                done = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr)
            result = pickle.loads(result_path.read_bytes())
            assert done.returncode == 0 and 'error' not in result, result.get('error')
            assert result['scalar_rollouts'] == 1
            retained=pickle.loads((HERE/'ad2400_lane_offer/scalar.pickle').read_bytes())
            assert max(abs(a-b) for k in ('costs','resources') for a,b in zip(result[k],retained[k]))<1e-7
            stats = pstats.Stats(str(OUT/'worker.prof'))
            rows = [dict(file=f[0], line=f[1], function=f[2], calls=v[1], self_sec=v[2], cumulative_sec=v[3])
                    for f,v in stats.stats.items()]
            save('profile_summary.json', dict(status='complete', wall_sec=time.perf_counter()-started,
                timing_scope='cProfile overhead included; not an end-to-end decision benchmark',
                axes=len(coord.axes), costs=result['costs'], resources=result['resources'],
                scalar_sec=result['scalar_sec'],
                by_self=sorted(rows, key=lambda r:r['self_sec'], reverse=True)[:40],
                by_cumulative=sorted(rows, key=lambda r:r['cumulative_sec'], reverse=True)[:40]))
            protocol = json.loads((OUT/'protocol.json').read_bytes())
            protocol.update(actual_ad_rollouts=0, actual_scalar_rollouts=1, profiling_only=True,
                            full_sdmpc_selection=False, native_runs=0)
            save('protocol.json', protocol)
            for p,d in json.loads((HERE/'profile_plan.json').read_bytes())['source_pins'].items():
                assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==d,p
            print('PROFILE_DONE', time.perf_counter()-started, flush=True)
            raise verifier.Done()
        sdmpc_pfo.solve = audit
        return original()
    adapter.main = wrapped
    verifier.main()

if __name__ == '__main__':
    main()
