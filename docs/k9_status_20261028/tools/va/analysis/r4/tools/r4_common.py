r"""V-A report r4 correction (D-K9-87): shared definitions for the r4 tools.

First-observation difference (VERIFY_HANDOFF_RESULTS sec.2, work/vhr/vhr_unins.py): two runs of one seed share the
arrival stream A(t), so U_a(t) - U_b(t) = I_b(t) - I_a(t), I = vehicles whose FIRST FZP frame is <= t.
Here the integral is taken on the r3 window [t0, t1] = [first frame, last frame] = [5.1, 8995.1] with the stage-1 0.5 s
midpoint grid and 150 s bins by midpoint (stage1_uninserted.py), so that d(4) = d(4a) + d(4b) uses one window.
Nothing here writes outside AV/r4."""
import io
import json
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
R4 = os.path.dirname(HERE)
AV = os.path.dirname(R4)
AVT = os.path.join(AV, 'tools')
if AVT not in sys.path:
    sys.path.insert(0, AVT)
import va_common as V  # noqa: E402  (pinned r3 common, imported read-only)

OUT = os.path.join(R4, 'out')
GRID = 0.5
BIN = 150.0
NB = 60
T0, T1 = 5.1, 8995.1
SEEDS = V.SEEDS
ARMS = ('va', 'j1', 'nc3')
TAGS = ['%s_s%d' % (a, s) for s in SEEDS for a in ARMS]
PAIRS = {'A': ('va', 'nc3', 'U6VA'), 'B': ('va', 'j1', 'U9'), 'Bp': ('j1', 'nc3', 'U9'), 'J1R': ('j1', 'nc3', 'U6J1')}
ROWS = ('M4b', 'M4', 'OUT_a', 'unins_1098', 'unins_1099', 'unins_other')
CPS = (900, 1800, 3600, 5400, 7200, 9000)
VA_METRICS = os.path.join(AV, 'out', 'va_metrics.json')
VA_REPORT = os.path.join(AV, 'VA_REPORT.md')
VA_REPORT_SHA = 'b57022e651adeefcaf1484993c20fd940b2e13012f0437e3a5b6c5ad6a20fc1b'
VHR_SCAN = os.path.join(V.SP, 'codex_handoff', 'work', 'vhr', 'scan_out')
O701_FILE = r'D:\VISSIM_handoff\20261024\derived\omega_membership_exact.json'
# VERIFY_HANDOFF_RESULTS sec.2.2 "우리 꼴 0-9000" row 4b (published 2026-10-25, corr_tables.md): reproduction targets
VHR_EXPECT_0_9000 = {('va', 'nc3', 31): -174.3, ('va', 'nc3', 41): -105.6, ('va', 'nc3', 43): -62.0,
                     ('j1', 'nc3', 31): -264.3, ('j1', 'nc3', 41): -134.5, ('j1', 'nc3', 43): -9.6,
                     ('va', 'j1', 31): +90.0, ('va', 'j1', 41): +28.9, ('va', 'j1', 43): -52.4}


def fzp_of(tag):
    arm, s = tag.split('_s')
    s = int(s)
    if arm == 'va':
        return V.runner_run(V.RVA, V.VA_NAMES[s])['fzp']
    if arm == 'j1':
        return V.j1_run(s)['fzp']
    if arm == 'nc3':
        return V.nc3_run(s)['fzp']
    raise SystemExit('bad tag ' + tag)


def grid_bins(first_times, t0=T0, t1=T1, nb=NB, bs=BIN):
    """150 s bins of integral_{[t0,t1]} I(t) dt / 3600, I(t) = #{first_times <= t}; 0.5 s midpoint grid exactly as
    stage1_uninserted.reconstruct_from_scan (last partial cell kept)."""
    e = np.sort(np.asarray(first_times, dtype=float))
    grid = np.arange(t0 + GRID / 2.0, t1, GRID)
    w = np.full(grid.shape, GRID)
    w[-1] = t1 - (grid[-1] - GRID / 2.0)
    gb = np.clip((grid // bs).astype(int), 0, nb - 1)
    cnt = np.searchsorted(e, grid, side='right').astype(float)
    return np.bincount(gb, weights=cnt * w, minlength=nb) / 3600.0


def closed_form(first_times, t1=T1):
    """sum over first_times <= t1 of (t1 - t) / 3600 (= the same integral when every t >= t0)."""
    return float(sum(t1 - t for t in first_times if t <= t1 + 1e-9)) / 3600.0


def f(x, nd=1, sign=False):
    """va_tables.f (display format of the r3 tables)."""
    if x is None:
        return '–'
    if isinstance(x, bool):
        return str(x)
    return ('%+.*f' % (nd, x)) if sign else ('%.*f' % (nd, x))


def sgn(x):
    return 0 if x == 0 else (1 if x > 0 else -1)


def jload(p):
    with io.open(p, encoding='utf-8-sig') as h:
        return json.load(h)


def jdump(o, p):
    tmp = p + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8', newline='\n') as h:
        json.dump(o, h, indent=1, ensure_ascii=False, default=V._default)
    os.replace(tmp, p)
