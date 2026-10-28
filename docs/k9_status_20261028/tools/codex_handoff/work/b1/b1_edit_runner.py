# B1 runner edit (2026-10-26, user decision D-K9-90). Applies exactly two changes to the codex closed-loop runner
# run_closedloop3000.ps1 of the new source tree b1/source (bytes identical to FRZ_B0's runner before the edit):
#   (1) pre-launch VISSIM check: 'refuse if any VISSIM is open' -> 'launch while the PC-wide VISSIM process count is < 4;
#       wait up to 30 s (as before) while it is >= 4, then refuse'  (two condition sites + the refusal text + one comment line)
#   (2) watchdog argument -StallSec 2400 -> 3600
# Each old text must occur exactly once; the input sha must be FRZ_B0's runner sha. Writes a JSON record.
#   python -B b1_edit_runner.py <runner.ps1> <record.json>
import hashlib, json, sys

RUNNER_B0_SHA = '8b2da855da5bdf237d2555fdd08ecb3f41f08dc56b4e8aa0187aa0a1b21bde6e'
EDITS = [
    ("-StallSec 2400 -> 3600",
     b"'-NoGlobalKill','-MaxAttempts','1','-StartupStallSec','300','-StallSec','2400')",
     b"'-NoGlobalKill','-MaxAttempts','1','-StartupStallSec','300','-StallSec','3600')"),
    ("seat check: wait while >= 4",
     b"            for($wait=0; $live.Count -and $wait -lt 30; $wait++) {",
     b"            # D-K9-90 (2026-10-26): launch while the PC-wide VISSIM count is below the 4-seat cap; wait/refuse at 4 or more.\n"
     b"            for($wait=0; $live.Count -ge 4 -and $wait -lt 30; $wait++) {"),
    ("seat check: refuse at >= 4",
     b"            if($live.Count) {throw 'Another VISSIM is open; preserve it and do not launch'}",
     b"            if($live.Count -ge 4) {throw 'PC-wide VISSIM count is at the 4-seat cap; preserve them and do not launch'}"),
]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main(path, rec):
    raw = open(path, 'rb').read()
    before = sha(raw)
    if before != RUNNER_B0_SHA:
        raise SystemExit('EDIT_FAIL input sha %s != FRZ_B0 runner %s' % (before, RUNNER_B0_SHA))
    if b'\r' in raw:
        raise SystemExit('EDIT_FAIL CR found; expected LF-only runner')
    out = raw
    applied = []
    for name, old, new in EDITS:
        n = out.count(old)
        if n != 1:
            raise SystemExit('EDIT_FAIL %r occurs %d times' % (name, n))
        out = out.replace(old, new)
        applied.append({'name': name, 'old': old.decode('utf-8'), 'new': new.decode('utf-8')})
    with open(path, 'wb') as f:
        f.write(out)
    after = sha(open(path, 'rb').read())
    r = {'path': path, 'sha256_before': before, 'sha256_after': after, 'bytes_before': len(raw), 'bytes_after': len(out),
         'lines_before': raw.count(b'\n'), 'lines_after': out.count(b'\n'), 'edits': applied}
    json.dump(r, open(rec, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('EDIT_OK before=%s after=%s lines %d->%d' % (before, after, r['lines_before'], r['lines_after']))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: b1_edit_runner.py <runner.ps1> <record.json>')
    main(sys.argv[1], sys.argv[2])
