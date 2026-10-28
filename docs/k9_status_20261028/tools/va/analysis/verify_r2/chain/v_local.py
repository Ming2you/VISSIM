# 검증자 자체: SC1001 EB 국소(§8.3-10, 짝 A·B), DESSPEED 두 읽는 법(§8.3-12, V-A만; J1 검증 v_local.py 꼴)
# 사용: python -B v_local.py --profile va|selftest   (v_fzp.py 출력과 v_control.json 의 vsl_by_T 를 읽음)
import json, os
import numpy as np
from v_common import runs, profile, out_dir, npz_dir, jl, jd, below_normal, SEEDS, st

below_normal()
prof = profile()
OUT = out_dir(prof)
TAGS = ['%s_s%d' % (a, s) for s in SEEDS for a in ('nc3', 'j1', 'va')]
res = {'profile': prof}
data = {t: dict(np.load(os.path.join(npz_dir(prof, t), 'fzp.npz'))) for t in TAGS}
LID = data['nc3_s31']['link_ids']
col = {int(l): i for i, l in enumerate(LID)}


def win(flag, t, t0=900.0, t1=9000.0):
    sel = (t >= t0) & (t < t1)
    w = ((t[sel] - t0) // 30).astype(int)
    g = np.bincount(w, weights=flag[sel].astype(float))
    present = np.bincount(w) > 0
    ks = np.nonzero(present)[0]
    ev = g[ks] >= 3
    starts = ks * 30 + t0
    pk = (starts >= 1800) & (starts < 7200)
    return dict(frac_all=float(ev.mean()), frac_peak=float(ev[pk].mean()), n_ev=int(ev.sum()),
                first=float(starts[ev][0]) if ev.any() else None)


loc = {}
for t in TAGS:
    d = data[t]
    tt = d['t']
    n491 = d['M'][:, col[10491]].astype(float)
    n127 = d['n127_12'].astype(float)
    P = (tt >= 1800) & (tt < 7200)
    loc[t] = dict(n491_P_mean=float(n491[P].mean()), n491_P_max=float(n491[P].max()), n491_F_mean=float(n491.mean()),
                  n491_F_max=float(n491.max()), n127_P_mean=float(n127[P].mean()), n127_P_max=float(n127[P].max()),
                  n127_F_mean=float(n127.mean()), n127_F_max=float(n127.max()), W=win(d['spW'], tt), E=win(d['spE'], tt))
res['local'] = loc
ls = {}
for pk, b in (('A', 'nc3'), ('B', 'j1')):
    for k in ('n491_P_mean', 'n491_P_max', 'n491_F_mean', 'n491_F_max', 'n127_P_mean', 'n127_P_max', 'n127_F_mean', 'n127_F_max'):
        ls['%s_%s' % (pk, k)] = st([loc['va_s%d' % s][k] - loc['%s_s%d' % (b, s)][k] for s in SEEDS], [loc['nc3_s%d' % s][k] for s in SEEDS])
    for side in ('W', 'E'):
        for k in ('frac_peak', 'frac_all'):
            ls['%s_%s_%s' % (pk, side, k)] = st([loc['va_s%d' % s][side][k] - loc['%s_s%d' % (b, s)][side][k] for s in SEEDS],
                                                [loc['nc3_s%d' % s][side][k] for s in SEEDS])
res['local_stats'] = ls
ctl = jl(os.path.join(OUT, 'v_control.json'))
MAPM = {80: 81, 90: 91, 100: 101}
zn = ['FW_E__seg0', 'FW_E__seg5', 'FW_E__seg10', 'FW_E__seg15']
ds = {}
for s in SEEDS:
    t = 'va_s%d' % s
    dr = np.load(os.path.join(npz_dir(prof, t), 'drec_round.npy'))
    cmds = ctl['runs'][t]['vsl_by_T']
    cells = {}
    for Ts, zc in cmds.items():
        T = int(Ts)
        if T < 900 or T > 8850:
            continue
        for zi, z in enumerate(zn):
            c = zc.get(z)
            c = int(round(c if c is not None else 110))
            m = (dr[:, 1] == zi) & (dr[:, 2] > T) & (dr[:, 2] <= T + 150)
            for passed in (1, 0):
                mm = m & (dr[:, 4] == passed)
                v = dr[mm, 3]
                a = cells.setdefault('%d|%s|%s' % (c, z, 'pass' if passed else 'noup'), [0, 0, 0])
                a[0] += int(mm.sum())
                if c < 110:
                    a[1] += int(np.sum((v >= c - 1) & (v <= c + 1)))
                    a[2] += int(np.sum((v >= MAPM[c] - 1) & (v <= MAPM[c] + 1)))
                else:
                    x = int(np.sum((v >= 98) & (v <= 140)))
                    a[1] += x
                    a[2] += x
    ds[t] = {k: dict(n=a[0], in_C=a[1], in_M=a[2]) for k, a in sorted(cells.items())}
res['desspeed'] = ds
jd(res, os.path.join(OUT, 'v_local.json'))
print('ok')
