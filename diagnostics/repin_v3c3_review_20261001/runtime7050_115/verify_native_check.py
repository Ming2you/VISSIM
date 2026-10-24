"""Verify completed logging-only native trials; no FZP rescan of full runs."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

out = HERE / 'native_check_v3'
arms = {}
for name in ('baseline', 'barrier'):
    directory = out / name
    log = (out / (name + '.log')).read_text(encoding='utf-8-sig')
    assert 'COMPLETE151' in log and 'FAIL=' not in log
    files = list((directory / 'eval').glob('*.fzp'))
    assert len(files) == 1
    lines = files[0].read_bytes().splitlines()
    header = next(i for i, line in enumerate(lines) if line.startswith(b'$VEHICLE:'))
    rows = [line for line in lines[header + 1:] if line.strip()]
    assert len(rows) > 0, 'An empty traffic run cannot establish trajectory parity'
    payload = b'\n'.join(rows)
    arms[name] = dict(rows=len(rows), all_columns_sha256=hashlib.sha256(payload).hexdigest(),
                      vehicles=len({line.split(b';')[1] for line in rows}),
                      final_record_sec=float(rows[-1].split(b';')[0]))
assert arms['baseline'] == arms['barrier'], arms

snapshots = {}
for second in (1, 150):
    snapshot = out / 'barrier' / ('err_at_' + str(second) + '.snapshot')
    # This verifies the exact live marker, not the post-Exit fully flushed file.
    data = snapshot.read_bytes()
    complete = data[:data.rfind(b'\n')+1]
    expected = ('Note\tOBS150_ERR_BARRIER_native115_' + str(second)).encode('ascii')
    assert sum(line.strip() == expected for line in complete.splitlines()) == 1
    snapshots[str(second)] = dict(bytes=snapshot.stat().st_size, complete_current_marker=True)
result = dict(status='PASS', arms=arms, live_err_snapshots=snapshots,
              shipping_flush_procedure=True, sim_clock_unchanged=True,
              limitations='151s diagnostic fixed inputs; not a restarted SDMPC run, deletion-heavy or full9000 validation')
(out / 'verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, indent=2))
