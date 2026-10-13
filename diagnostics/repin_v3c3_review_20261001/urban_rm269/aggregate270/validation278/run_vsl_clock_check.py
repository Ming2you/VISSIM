"""One VSL-off contrast per clock using frozen2400 operands. No optimizer/native."""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import hashlib
import json
import pickle
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
PREVIOUS = HERE.parent/'urban_clock277'
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, value):
    p.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf8')


def main():
    mode = sys.argv[1]
    assert mode in ('urban1', 'urban10')
    label = 'vsl110_'+mode
    receipt = HERE/(label+'_execution.json')
    assert not receipt.exists(), 'Retain existing attempt; do not duplicate'
    assert not any((p/'STOP').exists() for p in (ROOT, HERE, HERE.parent, HERE.parent.parent, PREVIOUS))
    source = PREVIOUS/('default_v1_request.pickle' if mode == 'urban1' else 'hold_v5_request.pickle')
    request = pickle.loads(source.read_bytes())
    follower, state, reference, forecast = request['owned']
    cfg = follower.cfg
    assert state.time_sec == 2400 and request['horizon'] == 3
    assert cfg.simulation.T_f_sec == 5 and cfg.simulation.T_u_sec == (1 if mode == 'urban1' else 10)
    from evaluation.controllers import sdmpc_sequence as seq
    from evaluation.controllers.control_hold import fixed_vsl_values
    from evaluation.controllers.sdmpc_tangent_surrogate import token
    blocks = seq.actions(request['action'], 3)
    changed = []
    for k, action in enumerate(blocks):
        before = dict(action.vsl)
        policy = dict(start_sec=0, base_kmh=110, zone_kmh={})
        action.vsl = fixed_vsl_values(action.vsl, policy, cfg.network.freeway_vsl_zone_heads, 2400+k*150)
        diff = {key: [before[key], value] for key, value in action.vsl.items() if value != before[key]}
        assert set(diff) == {'FW_E', 'FW_E__seg13', 'FW_E__seg14'} and set(map(tuple, diff.values())) == {(90., 110.)}
        changed.append(diff)
    request['action'] = seq.pack(blocks)
    # The reference, states, demand and historical exposure remain byte-identical.
    original = pickle.loads(source.read_bytes())
    assert pickle.dumps(request['owned'], protocol=5) == pickle.dumps(original['owned'], protocol=5)
    for a, b in zip(seq.actions(request['action'], 3), seq.actions(original['action'], 3)):
        for field in seq.FIELDS:
            if field != 'vsl':
                assert getattr(a, field) == getattr(b, field), field
    pins = {str(p): sha(p) for p in (ROOT/'evaluation/controllers').glob('*.py')}
    for path, digest in request['bootstrap']['runtime_sources'].items():
        if path not in pins:
            assert sha(path) == digest, path
    request['bootstrap']['runtime_sources'].update(pins)
    request['surrogate_evaluation'] = 'scalar'
    request['surrogate_context_sha256'] = token((request['owned'], request['runtime'], request['bootstrap'], request['horizon']))
    src, dst = HERE/(label+'_request.pickle'), HERE/(label+'_result.pickle')
    src.write_bytes(pickle.dumps(request, protocol=5))
    record = dict(status='running', clock=mode, pid=os.getpid(), started_utc=datetime.now(timezone.utc).isoformat(),
        input_sha256=sha(source), source_pins=pins, changed_vsl_by_block=changed,
        full_rollouts=1, full_sdmpc_selections=0, new_native_runs=0)
    save(receipt, record)
    start = time.perf_counter()
    with (HERE/(label+'_stdout.log')).open('w') as out, (HERE/(label+'_stderr.log')).open('w') as err:
        child = subprocess.Popen([sys.executable, '-B', str(ROOT/'evaluation/controllers/sdmpc_tangent_worker.py'),
            str(src), str(dst), sha(src), 'reverse-v1'], cwd=ROOT, stdout=out, stderr=err,
            creationflags=subprocess.BELOW_NORMAL_PRIORITY_CLASS|subprocess.CREATE_NO_WINDOW)
        record['child_pid'] = child.pid
        save(receipt, record)
        code = child.wait()
    record.update(exit_code=code, wall_sec=time.perf_counter()-start,
        status='failed_preserved' if code else 'complete_unreviewed',
        source_pins_unchanged=all(sha(path) == digest for path, digest in pins.items()))
    save(receipt, record)
    print(json.dumps({k: v for k, v in record.items() if k != 'source_pins'}))
    if code:
        failure = pickle.loads(dst.read_bytes()) if dst.exists() else {}
        print(failure.get('error', (HERE/(label+'_stderr.log')).read_text())[-5000:])
    return code


if __name__ == '__main__':
    raise SystemExit(main())
