r"""Compare two SDMPC decision outputs for the same state: before vs after a speed change.

    diff_decisions.py <dir_before> <dir_after> [sim_sec=900]

A decision-neutral change must leave:
  * every command field of action_<sec>.json byte-identical, and
  * every metadata / report value identical except wall-clock timings and receipt
    fields that the change itself adds.
Anything else is listed as a real difference.
"""
import io
import json
import re
import sys
from pathlib import Path

COMMANDS = ('N_P_star', 'N_UF_star', 'ramp_metering', 'vsl', 'green_times', 'offsets',
            'inflow_outflow_allocation')
# Keys that measure time or process identity, never the decision.
TIMING = re.compile(r'(^|_)(sec|secs|seconds|wall|cpu|elapsed|started|finished|time|timestamp|pid)($|_)'
                    r'|wall_sec|cpu_sec|_at$|^created|duration|progress_path|tempdir|temp_dir')
ADDED = {'forward_pruning'}


def walk(a, b, path, out, limit=200):
    if len(out) >= limit:
        return
    key = path.rsplit('/', 1)[-1]
    if TIMING.search(key) or key in ADDED:
        return
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k in ADDED:
                continue
            if k not in a or k not in b:
                if not TIMING.search(k):
                    out.append((path + '/' + k, 'only in ' + ('after' if k not in a else 'before')))
                continue
            walk(a[k], b[k], path + '/' + k, out, limit)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((path, 'length %d vs %d' % (len(a), len(b))))
            return
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, '%s[%d]' % (path, i), out, limit)
    elif a != b and not (isinstance(a, float) and isinstance(b, float) and a != a and b != b):
        out.append((path, '%r -> %r' % (str(a)[:50], str(b)[:50])))


def main():
    before, after = Path(sys.argv[1]), Path(sys.argv[2])
    sec = int(sys.argv[3]) if len(sys.argv) > 3 else 900
    name = 'action_%06d' % sec
    a = json.load(io.open(before / (name + '.json'), encoding='utf-8'))
    b = json.load(io.open(after / (name + '.json'), encoding='utf-8'))

    print('=== commands (must be byte-identical)')
    cmd_ok = True
    for k in COMMANDS:
        same = json.dumps(a.get(k), sort_keys=True) == json.dumps(b.get(k), sort_keys=True)
        cmd_ok &= same
        print('  %-26s %s' % (k, 'identical' if same else 'DIFFERENT'))

    diffs = []
    walk(a.get('metadata', {}), b.get('metadata', {}), 'metadata', diffs)
    ja, jb = (before / (name + '.joint.json')), (after / (name + '.joint.json'))
    if ja.exists() and jb.exists():
        walk(json.load(io.open(ja, encoding='utf-8')), json.load(io.open(jb, encoding='utf-8')), 'report', diffs)

    print('\n=== non-timing differences in metadata and report: %d' % len(diffs))
    for p, what in diffs[:60]:
        print('  %s: %s' % (p, what))

    wa = a.get('metadata', {}).get('decision_wall_sec')
    wb = b.get('metadata', {}).get('decision_wall_sec')
    if wa and wb:
        print('\n  decision_wall_sec  before %.1f  after %.1f  (%+.1f%%)' % (wa, wb, 100 * (wb / wa - 1)))
    print('\nNEUTRAL' if cmd_ok and not diffs else '\nNOT NEUTRAL' if not cmd_ok else '\nCOMMANDS IDENTICAL, review the listed differences')
    return 0 if cmd_ok and not diffs else 1


if __name__ == '__main__':
    raise SystemExit(main())
