# -*- coding: utf-8 -*-
"""fwe_meter_ldp.py - ramp-meter LDP -> GREEN seconds per 10 s cycle (PRE_FWE section 7.4, R3-a). 2026-10-27 KST.

Rule (CW/rawcheck/rm_exec.py:14-23, sha 27f64022...): the LDP line '<sim sec> <cycle sec><state>' gives the signal
state of second (t-1, t]; cycle [c, c+10) uses the states at t = c+1.0 ... c+10.0; GREEN = state 'I' only
(amber/red/blank are not green). Cycles start at 900 s (900, 910, ...) and end before the window end.
Read-only on the LDP files. Light job (LDP files are ~0.1 MB).
"""
import re

LINE = re.compile(r'^\s*(\d+\.\d)\s+(\d+\.\d)(.*)$')
METERS = {9101: 'RM_C10480', 9102: 'RM_C10482', 9103: 'RM_C10646', 9104: 'RM_C10644',
          9105: 'RM_C10639', 9106: 'RM_C10681', 9107: 'RM_C10490', 9108: 'RM_C10484'}
FWE_SC = (9105, 9106, 9107, 9108)
FWW_SC = (9101, 9102, 9103, 9104)


def ldp_states(path):
    """{sim second (float): first state char} from one LDP file."""
    g = {}
    with open(path, 'rb') as f:
        for raw in f:
            s = raw.decode('latin-1').rstrip('\r\n')
            m = LINE.match(s)
            if m:
                g[float(m.group(1))] = m.group(3)[:1]
    return g


def cycles_from_states(g, c0=900, c1=9000, period=10):
    """list of (cycle_start, green_seconds, missing_seconds)."""
    out = []
    for c in range(c0, c1, period):
        secs = [g.get(float(c + k + 1)) for k in range(period)]
        out.append((c, sum(1 for x in secs if x == 'I'), sum(1 for x in secs if x is None)))
    return out


def blank_per_cycle(g, c0=900, c1=9000, period=10):
    """[(cycle_start, blank_seconds)]: seconds whose state is blank (' ' or empty) = no SG state recorded.
    Added 2026-10-27 after data (R3): LNC / VSL / vsl_repro LDPs are blank in every second. GREEN rule unchanged."""
    out = []
    for c in range(c0, c1, period):
        secs = [g.get(float(c + k + 1)) for k in range(period)]
        out.append((c, sum(1 for x in secs if x in (' ', ''))))
    return out


def ldp_cycles(path, c0=900, c1=9000):
    return cycles_from_states(ldp_states(path), c0, c1)


if __name__ == '__main__':
    import sys, json
    p, c1 = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 9000
    cy = ldp_cycles(p, 900, c1)
    print(json.dumps({'n': len(cy), 'green_hist': {g: sum(1 for c in cy if c[1] == g) for g in range(11)},
                      'missing': sum(c[2] for c in cy)}))
