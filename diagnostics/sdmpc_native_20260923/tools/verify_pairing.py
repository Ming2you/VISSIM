r"""Two checks a paired RM verdict depends on.

1. PAIRED PREMISE. Control starts at 900 s, so within one seed the none and rm arms
   must be IDENTICAL before then. If they are not, the pair is not paired and the
   difference is not attributable to control.
2. CONTROL ACTUALLY ACTED. If the meters never fired, the arms would be identical
   throughout and any difference would be a bug, not an effect.

Compares per-frame Omega vehicle counts, which is what TTT integrates, rather than
whole-file hashes -- the files differ in ways that do not matter (timestamps).
"""
import hashlib
import io
import json
import os
import sys
from collections import Counter

SIM = r'D:\VISSIM-merge\sim3'
BASE = r'D:\VISSIM_runs\20260922_seedvar'
CONTROL_START = 900.0
sys.path.insert(0, SIM)


def inside_links():
    from scripts.measure_control_area import physical_membership_from_ledger
    doc = json.load(io.open(os.path.join(SIM, 'diagnostics', 'control_area_membership.json'),
                            encoding='utf-8-sig'))
    m = physical_membership_from_ledger(doc)
    return {int(k) for k, v in m.items() if v}


def profile(arm, inside):
    """Per-frame Omega count, and a digest of the pre-control prefix."""
    base = os.path.join(BASE, arm, 'run', 'vissim_eval')
    path = os.path.join(base, [f for f in os.listdir(base) if f.endswith('.fzp')][0])
    counts = Counter()
    digest = hashlib.sha256()
    with io.open(path, 'rb') as stream:
        for raw in stream:
            if not raw[:1].isdigit():
                continue
            parts = raw.split(b';', 4)
            t = float(parts[0])
            if t < CONTROL_START:
                digest.update(raw)
            if int(parts[2]) in inside:
                counts[t] += 1
    return counts, digest.hexdigest()


def main():
    inside = inside_links()
    data = {}
    for seed in ('s31', 's37', 's41'):
        for arm in ('none', 'rm'):
            name = seed + '_' + arm
            data[name] = profile(name, inside)
            print('scanned ' + name, flush=True)

    print('\n%-6s %-18s %-10s %s' % ('seed', 'pre-900 identical', 'first diff', 'max |diff| after 900'))
    verdicts = {}
    for seed in ('s31', 's37', 's41'):
        a, ha = data[seed + '_none']
        b, hb = data[seed + '_rm']
        same_prefix = ha == hb
        times = sorted(set(a) | set(b))
        first_diff = next((t for t in times if a[t] != b[t]), None)
        after = [abs(a[t] - b[t]) for t in times if t >= CONTROL_START]
        verdicts[seed] = {
            'pre_control_prefix_identical': same_prefix,
            'pre_control_sha256_none': ha, 'pre_control_sha256_rm': hb,
            'first_differing_frame_sec': first_diff,
            'max_abs_omega_count_diff_after_control': max(after) if after else 0,
            'frames_differing_after_control': sum(1 for t in times if t >= CONTROL_START and a[t] != b[t]),
        }
        print('%-6s %-18s %-10s %d' % (
            seed, 'YES' if same_prefix else 'NO',
            ('%.1f' % first_diff) if first_diff is not None else 'none',
            max(after) if after else 0))

    dest = r'D:\VISSIM-merge\evidence\pairing_check.json'
    io.open(dest, 'w', encoding='utf-8').write(json.dumps(verdicts, ensure_ascii=False, indent=2))
    print('\n-> ' + dest)
    print('\nPaired premise holds only where pre-900 is identical AND the first differing')
    print('frame is at or after 900. A first difference BEFORE 900 invalidates that seed.')


if __name__ == '__main__':
    main()
