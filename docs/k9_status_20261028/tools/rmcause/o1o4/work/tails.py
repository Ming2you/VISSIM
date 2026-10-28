# -*- coding: utf-8 -*-
"""Queue-tail / spillback minutes from fwe_scan grids (read-only). 2026-10-24 rmcause/o1o4.

Re-implements the INV_PHYSICS section 3.3 tail metric (that inline script was not saved):
congested bin = 100 m x 60 s cell with mean speed < 60 km/h and density > 15 veh/km/lane
(same as phys/fwe_analyze.py:14,51). For each 60 s window:
  B1 tail = most upstream bin reached by walking upstream from the most upstream congested bin
            whose centre lies in 4,900-5,100 m (10681 merge head), allowing gaps of 1 free bin;
  B2 tail = same from congested bins centred in 7,400-7,700 m (10484 merge head).
  These seed zones and the 1-bin gap reproduce all 56 numbers of the INV_PHYSICS table
  (14 runs x 4 values) - checked by tails_variants2.py (2026-10-24).
  'B1 spill minute' = B1 tail < 4,500 m; 'M spill minute' = B2 tail < 6,800 m.
Validation target: INV_PHYSICS.md:89-100 table (v3c3 NC3 s31/41/43/47/53, 64cf-s29 NC).
Usage: python -B tails.py <scan_json> [...]
"""
import json, sys

VC, KC = 60.0, 15.0


def lanes_at(x):
    return 4 if x < 6841.743 else 3


def grids(d):
    nb, nw = d['nb'], d['nw']
    cong = [[False] * nb for _ in range(nw)]
    for w in range(nw):
        fr = d['frames'][w] or 12
        for b in range(nb):
            n = d['gN'][w][b]
            if not n:
                continue
            v = d['gV'][w][b] / n
            x = (b + 0.5) * d['bin_m']
            k = n / fr / (d['bin_m'] / 1000.0) / lanes_at(x)
            cong[w][b] = v < VC and k > KC
    return cong


def tails(d):
    cong = grids(d)
    nb, nw = d['nb'], d['nw']
    res = {'b1_tail_m': [], 'b2_tail_m': []}
    for w in range(nw):
        row = cong[w]
        for key, (a, e) in (('b1_tail_m', (4900, 5100)), ('b2_tail_m', (7400, 7700))):
            seeds = [b for b in range(nb) if row[b] and a <= (b + 0.5) * 100 < e]
            if not seeds:
                res[key].append(None)
                continue
            b = min(seeds)
            while True:
                if b - 1 >= 0 and row[b - 1]:
                    b -= 1
                elif b - 2 >= 0 and row[b - 2]:
                    b -= 2
                else:
                    break
            res[key].append(b * 100)
    return res


def summary(d):
    t = tails(d)
    b1 = [(w, x) for w, x in enumerate(t['b1_tail_m']) if x is not None]
    b2 = [(w, x) for w, x in enumerate(t['b2_tail_m']) if x is not None]
    b1min = min(b1, key=lambda p: (p[1], p[0])) if b1 else None
    b2min = min(b2, key=lambda p: (p[1], p[0])) if b2 else None
    return {
        'b1_tail_min_m': b1min[1] if b1min else None, 'b1_tail_min_at_s': b1min[0] * 60 if b1min else None,
        'b1_spill_min_lt4500': sum(1 for _, x in b1 if x < 4500),
        'b2_tail_min_m': b2min[1] if b2min else None,
        'm_spill_min_lt6800': sum(1 for _, x in b2 if x < 6800),
        'b1_spill_windows': [w for w, x in b1 if x < 4500],
        'm_spill_windows': [w for w, x in b2 if x < 6800],
        'b1_tail_m': t['b1_tail_m'], 'b2_tail_m': t['b2_tail_m'],
    }


if __name__ == '__main__':
    for p in sys.argv[1:]:
        d = json.load(open(p, encoding='utf-8'))
        s = summary(d)
        print(d['tag'], s['b1_tail_min_m'], s['b1_tail_min_at_s'], s['b1_spill_min_lt4500'], s['b2_tail_min_m'], s['m_spill_min_lt6800'])
