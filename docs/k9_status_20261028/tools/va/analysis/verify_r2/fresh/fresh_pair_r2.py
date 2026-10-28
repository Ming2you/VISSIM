# VerifyVA r2 follow-up: first divergent frame / entry under the declared pairing definition
# (first frame whose all-link total OR Omega total differs; first differing entry time compared per input).
# fresh_r2.py used a per-link frame comparison and a pooled sorted-entry comparison (a different, stricter definition).
# Reuses only this verifier's own fresh_r2.py helpers. No analysis / pinned verify / stage1 import.
import json
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fresh_r2 as F  # noqa: E402


def one(P, inside, allset):
    links, inputs = F.parse_inpx(P['inpx'])
    df, _, _ = F.read_fzp(P['fzp'])
    tu = np.unique(df['t'].to_numpy())
    fi = np.searchsorted(tu, df['t'].to_numpy())
    lk = df['link'].to_numpy()
    ins = np.isin(lk, np.fromiter(inside, dtype=np.int64))
    alm = np.isin(lk, np.fromiter(allset, dtype=np.int64))
    tot = np.bincount(fi[alm], minlength=len(tu))
    om = np.bincount(fi[ins], minlength=len(tu))
    first = df.drop_duplicates('veh', keep='first')
    entry = (first['t'] - first['tin']).to_numpy()
    flink = first['link'].to_numpy()
    ibl = {d['link']: no for no, d in inputs.items()}
    F.attribute.preds = F.build_preds(links)
    ent = {no: [] for no in inputs}
    cache = {}
    for L, e in zip(flink.tolist(), entry.tolist()):
        if L not in cache:
            cache[L] = F.attribute(L, links, ibl)
        no = cache[L][0]
        if no is None or no == 'ambiguous':
            continue
        ent[no].append(e)
    ent = {no: sorted(v) for no, v in ent.items()}
    return dict(t=tu, tot=tot, om=om, ent=ent)


def main():
    memb = json.load(open(F.MEMB, encoding='utf-8'))
    inside = {int(x) for x in memb['inside_links']}
    allset = inside | {int(x) for x in memb['outside_links']}
    P = F.run_paths()
    out = {}
    for s in F.SEEDS:
        R = {arm: one(P[(arm, s)], inside, allset) for arm in ('nc3', 'j1', 'va')}
        for nm, (a, b) in dict(A=('nc3', 'va'), B=('j1', 'va')).items():
            x, y = R[a], R[b]
            n = min(len(x['t']), len(y['t']))
            same_t = bool(np.array_equal(x['t'][:n], y['t'][:n]))
            dif = np.nonzero((x['tot'][:n] != y['tot'][:n]) | (x['om'][:n] != y['om'][:n]))[0]
            ff = float(x['t'][dif[0]]) if dif.size else None
            fe = None
            for no in x['ent']:
                p, q = x['ent'][no], y['ent'].get(no, [])
                if p == q:
                    continue
                j = next((j for j, (u, v) in enumerate(zip(p, q)) if u != v), min(len(p), len(q)))
                c = min(e for e in (p[j] if j < len(p) else None, q[j] if j < len(q) else None) if e is not None)
                fe = c if fe is None else min(fe, c)
            pre = int(np.sum(x['t'][:n] < 900.0))
            pre_same = bool(np.array_equal(x['tot'][:pre], y['tot'][:pre]) and np.array_equal(x['om'][:pre], y['om'][:pre]))
            out['%s_s%d' % (nm, s)] = dict(same_t=same_t, first_div_frame=ff, first_div_entry=round(fe, 4) if fe is not None else None,
                                           pre900_frames=pre, pre900_same=pre_same)
        print(s, {k: v for k, v in out.items() if k.endswith(str(s))}, flush=True)
    p = os.path.join(HERE, 'out', 'fresh_pair_r2.json')
    json.dump(out, open(p, 'w', encoding='utf-8'), indent=1, sort_keys=True)
    print('WROTE', p, flush=True)


if __name__ == '__main__':
    main()
