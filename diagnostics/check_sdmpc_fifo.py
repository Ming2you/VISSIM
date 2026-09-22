"""Repeat a frozen continuous prediction with indexed lateral departures."""
from pathlib import Path
import hashlib
import json
import pickle
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]


def main():
    source, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=False)
    with (source/'request.pickle').open('rb') as stream:
        request = pickle.load(stream)
    request['owned'][0].cfg.network.sdmpc_options['fifo_batch'] = True
    request['diagnostic_checkpoint'] = str((out/'prediction.pickle').resolve())
    data = pickle.dumps(request, protocol=5)
    req = out/'request.pickle'
    req.write_bytes(data)
    result = out/'result.pickle'
    started = time.perf_counter()
    child = subprocess.run([sys.executable, '-B', str(ROOT/'evaluation/controllers/sdmpc_tangent_worker.py'),
                            str(req.resolve()), str(result.resolve()), hashlib.sha256(data).hexdigest()])
    receipt = pickle.loads(result.read_bytes())
    receipt['wall_sec_including_spawn'] = time.perf_counter()-started
    (out/'result.json').write_text(json.dumps(receipt, indent=2)+'\n')
    if child.returncode:
        print(receipt.get('error'), flush=True)
        return child.returncode
    import numpy as np
    from evaluation.controllers.sdmpc_tangent_worker import state_error
    baseline = json.loads((source/'result_attempt01.json').read_text())
    comparisons = {key:float(np.max(np.abs(np.asarray(receipt[key])-np.asarray(baseline[key]))))
                   for key in ('costs','resources','cost_jacobian','resource_jacobian')}
    with (source/'prediction.pickle').open('rb') as stream:
        before=pickle.load(stream)
    with (out/'prediction.pickle').open('rb') as stream:
        after=pickle.load(stream)
    for key in ('scalar_states','tangent_states'):
        comparisons[key+'_max_primal_error']=state_error(before[key],after[key])
    report=dict(comparisons=comparisons, baseline=str(source.resolve()),
                scalar_sec=receipt['scalar_sec'], tangent_sec=receipt['tangent_sec'],
                pass_all=max(comparisons.values()) <= 1e-8)
    (out/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    return 0 if report['pass_all'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
