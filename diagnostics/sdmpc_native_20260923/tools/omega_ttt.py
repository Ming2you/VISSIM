r"""Omega TTT for a 5-second FZP, using the canonical membership and integration rule.

WHY NOT diagnostics/summarize_fast_nc.py: that is the canonical accountant and it was
tried first, but summarize_stream asserts `sec == observed + 1` -- it only accepts a
ONE-second FZP. These runs recorded at five seconds
(prepared.json vehicle_record_interval_sec = 5), so the canonical path cannot read them
and re-recording would mean repeating six 9000-second runs.

WHAT IS KEPT IDENTICAL:
  * the membership document, diagnostics/control_area_membership.json, read through the
    same physical_membership_from_ledger(); the same 635 links count as inside Omega.
  * the integration rule, (n_prev + n_now) / 2 * dt / 3600 veh*h per step, which is
    summarize_fast_nc's `(old_counts[road] + counts[road]) / 7200` at dt = 1.

WHAT DIFFERS: dt is 5 s, so within-interval fluctuation is not resolved. The error is
second order in dt and, because every arm is sampled on the same grid, it cancels to
first order in a PAIRED comparison -- which is the only comparison these seeds support
anyway (unpaired, the seed sigma is about 1%).

Usage: omega_ttt.py <arm_dir> [<arm_dir> ...]
"""
import io
import json
import os
import sys
import time
from collections import Counter

SIM = r'D:\VISSIM-merge\sim3'
MEMBERSHIP = os.path.join(SIM, 'diagnostics', 'control_area_membership.json')
sys.path.insert(0, SIM)


def membership_map():
    from scripts.measure_control_area import physical_membership_from_ledger
    document = json.load(io.open(MEMBERSHIP, encoding='utf-8-sig'))
    membership = physical_membership_from_ledger(document)
    inside = {int(k) for k, v in membership.items() if v}
    if len(membership) != 1236 or len(inside) != 635:
        raise SystemExit('Unexpected membership: %d links, %d inside (want 1236 / 635)'
                         % (len(membership), len(inside)))
    return inside


def scan(path, inside):
    """One pass. Returns (ttt_veh_h inside Omega, ttt_veh_h everywhere, frames, dt)."""
    times = []
    inside_n, total_n = Counter(), Counter()
    with io.open(path, 'rb') as stream:
        for raw in stream:
            if not raw[:1].isdigit():
                continue
            parts = raw.split(b';', 4)
            t = float(parts[0])
            link = int(parts[2])
            if not times or times[-1] != t:
                times.append(t)
            total_n[t] += 1
            if link in inside:
                inside_n[t] += 1
    times.sort()
    if len(times) < 2:
        raise SystemExit('Too few frames in ' + path)
    steps = [round(b - a, 6) for a, b in zip(times, times[1:])]
    dt = Counter(steps).most_common(1)[0][0]
    irregular = sum(1 for s in steps if abs(s - dt) > 1e-6)

    def integrate(counts):
        total = 0.0
        for a, b in zip(times, times[1:]):
            step = b - a
            total += (counts[a] + counts[b]) / 2.0 * step / 3600.0
        return total

    return integrate(inside_n), integrate(total_n), len(times), dt, irregular, times[0], times[-1]


def main():
    arms = sys.argv[1:]
    if not arms:
        raise SystemExit(__doc__)
    inside = membership_map()
    print('membership: 635 links inside Omega of 1236\n')
    print('%-10s %14s %14s %8s %6s %10s %10s %6s' %
          ('arm', 'Omega TTT', 'all TTT', 'frames', 'dt', 'first', 'last', 'irreg'))
    out = {}
    for arm in arms:
        path = None
        base = os.path.join(arm, 'run', 'vissim_eval')
        if os.path.isdir(base):
            hits = [f for f in os.listdir(base) if f.endswith('.fzp')]
            if len(hits) == 1:
                path = os.path.join(base, hits[0])
        if path is None:
            print('%-10s  (no single fzp)' % os.path.basename(arm))
            continue
        t0 = time.perf_counter()
        omega, allttt, frames, dt, irregular, first, last = scan(path, inside)
        out[os.path.basename(arm)] = {
            'omega_ttt_veh_h': omega, 'all_ttt_veh_h': allttt, 'frames': frames,
            'dt_sec': dt, 'irregular_steps': irregular, 'first_sec': first, 'last_sec': last,
            'fzp': path, 'fzp_bytes': os.path.getsize(path), 'scan_sec': time.perf_counter() - t0}
        print('%-10s %14.3f %14.3f %8d %6.1f %10.1f %10.1f %6d' %
              (os.path.basename(arm), omega, allttt, frames, dt, first, last, irregular))
    dest = os.path.join(r'D:\VISSIM-merge\evidence', 'omega_ttt.json')
    existing = {}
    if os.path.exists(dest):
        existing = json.load(io.open(dest, encoding='utf-8'))
    existing.update(out)
    io.open(dest, 'w', encoding='utf-8').write(json.dumps(existing, ensure_ascii=False, indent=2))
    print('\n-> ' + dest)


if __name__ == '__main__':
    main()
