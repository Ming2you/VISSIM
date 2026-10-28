# 검증자 자체 지표 계산 (보충 34 §8.2·§8.3-1·2·3·6·13·§8.4; J1 검증 v_metrics.py 꼴, 9런으로 넓힘)
# 입력: fzp.npz(V-A는 이 프로필 v_fzp.py 출력, J1·NC3은 J1 검증 출력 sha 확인 뒤) + .inpx + .err + obs150 jsonl + 소속·사슬·링크집합
# 사용: python -B v_metrics.py --profile va|selftest  ->  <out>/v_metrics.json
import glob, io, json, math, os, re, statistics
from collections import Counter
import numpy as np
from v_common import (runs, profile, out_dir, npz_dir, parse_inpx, schedule, chains, membership, jl, jd, LINKSETS,
                      below_normal, sha, BIN, NB, T_END, SEEDS, st)

below_normal()
prof = profile()
OUT = out_dir(prof)
RUNS = runs(prof)
TAGS = ['%s_s%d' % (a, s) for s in SEEDS for a in ('nc3', 'j1', 'va')]
res = {'profile': prof, 'notes': []}
nets = {t: parse_inpx(RUNS[t]['inpx']) for t in TAGS}
base = nets['nc3_s31']


def geom(n):
    return {k: (round(v['length'], 3), v['lanes'], v.get('from'), v.get('to')) for k, v in n['links'].items()}


def inps(n):
    return [(i['no'], i['link'], [(r['start'], r['vph'], r['cont']) for r in i['rows']]) for i in n['inputs']]


res['net_equal'] = {t: dict(geom=geom(nets[t]) == geom(base), inputs=inps(nets[t]) == inps(base), dsds=nets[t]['dsds'] == base['dsds'],
                            randSeed=nets[t]['seed']) for t in TAGS}
net = base
links = net['links']
ins, outs, md = membership()
ch = chains()
assert set(links) == ins | outs
region = {}
for l in ch['FW_E']['links']:
    region[l] = 'fw_e_main'
for l in ch['FW_W']['links']:
    region[l] = 'fw_w_main'
for rc in md['ramp_checks']:
    if rc['kind'] != 'on_ramps':
        continue
    c = int(rc['connector'])
    for l in (c, links[c]['from']):
        region[l] = 'onramp:RM_C%d' % c
for rc in md['ramp_checks']:
    if rc['kind'] != 'off_ramps':
        continue
    c = int(rc['connector'])
    region.setdefault(c, 'offramp')
    if links[c]['to'] not in region:
        region[links[c]['to']] = 'offramp'
for l in links:
    if l not in region:
        region[l] = 'urban_omega' if l in ins else 'outside'
ls = jl(LINKSETS)['link_sets']
S1 = [int(x) for x in ch['FW_E']['links']]
S2 = sorted({int(x) for k in ('mainline', 'on_connectors', 'off_connectors', 'on_approaches') for x in ls[k]})
SREC = [int(x) for x in ls['off_receivers_shared']]
res['sets'] = dict(n1=len(S1), n2=len(S2), n_omega=len(ins), n_all=len(links))
data = {}
for t in TAGS:
    d = npz_dir(prof, t)
    z = np.load(os.path.join(d, 'fzp.npz'))
    data[t] = {k: z[k] for k in z.files}
    data[t]['_dir'] = d
LID = data['nc3_s31']['link_ids']
for t in TAGS:
    assert np.array_equal(data[t]['link_ids'], LID), t
col = {int(l): i for i, l in enumerate(LID)}
res['npz_dirs'] = {t: data[t]['_dir'] for t in TAGS}


def link_vh(t):
    d = data[t]
    tt, Mm = d['t'], d['M'].astype(np.float64)
    dt = np.diff(tt)
    mid = (tt[:-1] + tt[1:]) / 2.0
    b = np.clip((mid // BIN).astype(int), 0, NB - 1)
    S = (Mm[:-1] + Mm[1:]) * (dt / 7200.0)[:, None]
    B = np.zeros((len(b), NB))
    B[np.arange(len(b)), b] = 1.0
    return S.T @ B


LV = {t: link_vh(t) for t in TAGS}
res['frames'] = {t: dict(n=len(data[t]['t']), first=float(data[t]['t'][0]), last=float(data[t]['t'][-1])) for t in TAGS}


def setbins(t, ids):
    return LV[t][[col[i] for i in ids], :].sum(axis=0)


INS = sorted(ins)
ALL = sorted(links)
REG = {r: sorted(l for l in links if region[l] == r) for r in set(region.values())}
ONR = sorted(l for l in links if region[l].startswith('onramp:'))
REM_RE = re.compile(r'Vehicle input (\d+):.*?remain:\s*(\d+)\s*vehicles')
RMV_RE = re.compile(r'Simulation second ([\d.]+): After [\d.]+ seconds of waiting for lane change the vehicle (\d+) .*?was removed from link (\d+) at position ([\d.]+)')
ERR = {}
for t in TAGS:
    txt = open(RUNS[t]['err'], 'rb').read().decode('cp949', errors='replace')
    rem = {int(m.group(1)): int(m.group(2)) for m in REM_RE.finditer(txt)}
    lsr = [int(m.group(3)) for m in RMV_RE.finditer(txt)]
    ERR[t] = dict(remains=rem, removals=len(lsr), outside=sum(l not in ins for l in lsr), inside=sum(l in ins for l in lsr))
input_by_link = {}
for i in net['inputs']:
    input_by_link.setdefault(i['link'], []).append(i['no'])
preds = {}
for l, r in links.items():
    if r['conn']:
        preds.setdefault(l, []).append(r['from'])
        preds.setdefault(r['to'], []).append(l)


def trace(l, depth=6):
    fr, vis = [l], {l}
    for _ in range(depth):
        hits = sorted({i for x in fr for i in input_by_link.get(x, [])})
        if hits:
            return hits
        nx = []
        for x in fr:
            for q in preds.get(x, []):
                if q not in vis:
                    vis.add(q)
                    nx.append(q)
        fr = nx
        if not fr:
            break
    return []


INSERT = {}
for t in TAGS:
    d = data[t]
    ent = {i['no']: [] for i in net['inputs']}
    cache = {}
    for tf, lk, tm in zip(d['seen_t'].tolist(), d['seen_lk'].tolist(), d['seen_tm'].tolist()):
        e = round(tf - tm, 1) if tm == tm else tf
        if lk in input_by_link:
            hits = input_by_link[lk]
        else:
            if lk not in cache:
                cache[lk] = trace(lk)
            hits = cache[lk]
        if len(hits) == 1:
            ent[hits[0]].append(e)
    for k in ent:
        ent[k].sort()
    INSERT[t] = ent
GRID = 0.5


def cumL(sch, x):
    x = np.asarray(x, dtype=float)
    o = np.zeros_like(x)
    for a, b, r in sch:
        o += r * np.clip(x - a, 0.0, b - a)
    return o


def recon(t):
    d = data[t]
    t0, t1 = float(d['t'][0]), float(d['t'][-1])
    grid = np.arange(t0 + GRID / 2.0, t1, GRID)
    gw = np.full(grid.shape, GRID)
    gw[-1] = t1 - (grid[-1] - GRID / 2.0)
    out = {}
    for i in net['inputs']:
        no = i['no']
        sch = schedule(i)
        LT = float(cumL(sch, [T_END])[0])
        e = np.asarray(INSERT[t][no], dtype=float)
        e = e[e <= t1 + 1e-6]
        recent = int(np.sum(e > t1 - 300.0))
        tail = recent / 300.0 * (T_END - t1)
        Rr = int(ERR[t]['remains'].get(no, 0))
        N = int(e.size) + tail + Rr
        rec = dict(LT=LT, N=N, R=Rr)
        if LT > 0:
            Lg = cumL(sch, grid)
            q = N / LT * Lg - np.searchsorted(e, grid, side='right')
            p = Lg / LT
            sd = np.sqrt(np.maximum(N * p * (1 - p), 1.0))
            rec['queued'] = bool(Rr > 0 or float((q / sd).max()) >= 4.0)
        else:
            rec['queued'] = False
        out[no] = rec
    return out, grid, gw


RC = {t: recon(t) for t in TAGS}
UNIONS = {'U6VA': ('va', 'nc3'), 'U9': ('va', 'j1', 'nc3'), 'U6J1': ('j1', 'nc3')}
union, union_src = {}, {}
for u, arms in UNIONS.items():
    tg = [t for t in TAGS if t.split('_')[0] in arms]
    union[u] = sorted({no for t in tg for no, r in RC[t][0].items() if r['queued'] or r['R'] > 0})
    union_src[u] = {no: [t for t in tg if RC[t][0][no]['queued'] or RC[t][0][no]['R'] > 0] for no in union[u]}
anchors = {s: {i['no']: round(RC['nc3_s%d' % s][0][i['no']]['N'], 2) for i in net['inputs']} for s in SEEDS}


def clipped(t, no, anchor):
    i = next(x for x in net['inputs'] if x['no'] == no)
    sch = schedule(i)
    LT = float(cumL(sch, [T_END])[0])
    grid, gw = RC[t][1], RC[t][2]
    e = np.asarray(INSERT[t][no], dtype=float)
    q = anchor / LT * cumL(sch, grid) - np.searchsorted(e, grid, side='right')
    gb = np.clip((grid // BIN).astype(int), 0, NB - 1)
    bins = np.bincount(gb, weights=np.maximum(q, 0.0) * gw, minlength=NB) / 3600.0
    ft = data[t]['t']
    qf = anchor / LT * cumL(sch, ft) - np.searchsorted(e, ft, side='right')
    return bins, qf


allno = sorted(set(n for u in union.values() for n in u) | {1083})
UN = {t: {no: clipped(t, no, anchors[int(t[-2:])][no]) for no in allno} for t in TAGS}
KEYS = ['M1', 'M2', 'M3', 'M3u', 'M4', 'M4a', 'M4b', 'OUTa', 'OUTb', 'U1098', 'U1099', 'Uother', 'REC']
MET = {}
for u in UNIONS:
    for t in TAGS:
        m = {}
        m['M1'] = setbins(t, S1); m['M2'] = setbins(t, S2); m['M3'] = setbins(t, INS)
        m['M3u'] = setbins(t, REG['urban_omega']); m['M4a'] = setbins(t, ALL)
        m['M4b'] = sum((UN[t][no][0] for no in union[u]), np.zeros(NB))
        m['M4'] = m['M4a'] + m['M4b']; m['OUTa'] = m['M4'] - m['M3']; m['OUTb'] = m['M4a'] - m['M3']
        m['U1098'] = UN[t][1098][0] if 1098 in union[u] else np.zeros(NB)
        m['U1099'] = UN[t][1099][0] if 1099 in union[u] else np.zeros(NB)
        m['Uother'] = sum((UN[t][no][0] for no in union[u] if no not in (1098, 1099)), np.zeros(NB))
        m['REC'] = setbins(t, SREC)
        for r in ('fw_e_main', 'fw_w_main', 'offramp', 'urban_omega'):
            m['om_' + r] = setbins(t, [l for l in REG.get(r, []) if l in ins]) if REG.get(r) else np.zeros(NB)
        m['om_onramp'] = setbins(t, [l for l in ONR if l in ins])
        MET[(u, t)] = m
lev = {}
for (u, t), m in MET.items():
    x = {k: float(v.sum()) for k, v in m.items()}
    x['REM'] = float(ERR[t]['removals']); x['REM_B'] = float(ERR[t]['outside'])
    lev['%s|%s' % (u, t)] = x
res['levels'] = lev
PAIRS = {'A': ('va', 'nc3', 'U6VA'), 'B': ('va', 'j1', 'U9'), 'Bp': ('j1', 'nc3', 'U9'), 'J1R': ('j1', 'nc3', 'U6J1')}
LKEYS = KEYS + ['REM', 'REM_B', 'om_fw_e_main', 'om_fw_w_main', 'om_onramp', 'om_offramp', 'om_urban_omega']
pairs = {}
for pk, (a, b, u) in PAIRS.items():
    P = {}
    for k in LKEYS:
        dv = [lev['%s|%s_s%d' % (u, a, s)][k] - lev['%s|%s_s%d' % (u, b, s)][k] for s in SEEDS]
        P[k] = st(dv, [lev['%s|nc3_s%d' % (u, s)][k] for s in SEEDS])
    lab = {}
    for s in [str(x) for x in SEEDS] + ['mean']:
        g = (lambda k: P[k]['mean']) if s == 'mean' else (lambda k, s=s: P[k]['d'][SEEDS.index(int(s))])
        d3, d4, dout, d4b, ra, rb = g('M3'), g('M4'), g('OUTa'), g('M4b'), g('REM'), g('REM_B')
        if not d3 < 0:
            N = WA = WB = '해당 없음'
        else:
            N = '같은 방향' if (d4 <= 0 and dout <= 0) else '대기 이전'
            WA = '같은 방향' if (d4 <= 0 and dout <= 0 and d4b <= 0 and ra <= 0) else '대기 이전'
            WB = '같은 방향' if (d4 <= 0 and dout <= 0 and d4b <= 0 and rb <= 0) else '대기 이전'
        lab[s] = dict(N=N, W_A=WA, W_B=WB)
    pre = {}
    for s in SEEDS:
        ma, mb = MET[(u, '%s_s%d' % (a, s))], MET[(u, '%s_s%d' % (b, s))]
        pre[str(s)] = max(abs(float(ma[k][:6].sum() - mb[k][:6].sum())) for k in KEYS)
    cum = {}
    for k in ('M1', 'M3', 'M4', 'OUTa'):
        cum[k] = {str(s): [float(x) for x in np.cumsum(MET[(u, '%s_s%d' % (a, s))][k] - MET[(u, '%s_s%d' % (b, s))][k])[[5, 11, 23, 35, 47, 59]]]
                  for s in SEEDS}
    pairs[pk] = dict(union=u, stats=P, labels=lab, pre900_maxabs=pre, cum=cum)
res['pairs'] = pairs
res['union'] = union
res['union_src'] = {u: {str(k): v for k, v in x.items()} for u, x in union_src.items()}
res['end'] = {t: dict(in_net=int(data[t]['M'][-1].sum()), omega=int(data[t]['M'][-1][[col[l] for l in INS]].sum()),
                      seen=int(len(data[t]['seen_no'])), removals=ERR[t]['removals'], rem_outside=ERR[t]['outside'],
                      rem_inside=ERR[t]['inside'], remains=ERR[t]['remains']) for t in TAGS}
uin = {}
for u in ('U6VA', 'U9'):
    uin[u] = {str(no): {t: dict(total=float(UN[t][no][0].sum()), remain=ERR[t]['remains'].get(no, 0))
                        for t in TAGS if t.split('_')[0] in UNIONS[u]} for no in union[u]}
res['uninserted_by_input'] = uin
# 입력 1083 (§8.3-3)
f1083 = {}
for s in SEEDS:
    for arm in ('nc3', 'j1', 'va'):
        t = '%s_s%d' % (arm, s)
        e = INSERT[t][1083]
        qf = np.maximum(UN[t][1083][1], 0)
        k = int(np.argmax(qf))
        f1083[t] = dict(remain=ERR[t]['remains'].get(1083, 0), inserted=len(e), delay=float(UN[t][1083][0].sum()),
                        maxq_frame=float(qf[k]), maxq_frame_t=float(data[t]['t'][k]),
                        per_bin=np.bincount(np.clip((np.asarray(e) // BIN).astype(int), 0, NB - 1), minlength=NB).tolist())
    for pk, bse in (('A', 'nc3'), ('B', 'j1')):
        ft = data['va_s%d' % s]['t']
        sel = np.arange(29, len(ft), 30)
        dq = np.maximum(UN['va_s%d' % s][1083][1], 0)[sel] - np.maximum(UN['%s_s%d' % (bse, s)][1083][1], 0)[sel]
        over = np.nonzero(dq > 10)[0]
        db = np.array(f1083['va_s%d' % s]['per_bin']) - np.array(f1083['%s_s%d' % (bse, s)]['per_bin'])
        u = 'U6VA' if pk == 'A' else 'U9'
        share = (f1083['va_s%d' % s]['delay'] - f1083['%s_s%d' % (bse, s)]['delay']) if 1083 in union[u] else 0.0
        f1083['%s_s%d' % (pk, s)] = dict(first_gt10=float(ft[sel][over[0]]) if over.size else None,
                                         bindiff_from28=db[28:].tolist(), share=share)
res['input_1083'] = f1083
chainl = {}
for l in (21, 10112, 174, 10280, 10281, 173):
    chainl[str(l)] = dict(length=links[l]['length'], lanes=links[l]['lanes'], region=region[l], inside=l in ins,
                          ttt={t: [float(LV[t][col[l]].sum()), float(LV[t][col[l]][29:].sum())] for t in TAGS},
                          frames={t: dict(mean=float(data[t]['M'][:, col[l]].mean()), max=float(data[t]['M'][:, col[l]].max()),
                                          max_t=float(data[t]['t'][int(np.argmax(data[t]['M'][:, col[l]]))])) for t in TAGS})
res['link174_chain'] = chainl
east = {}
for l in (1220000704, 1220000803):
    tt = {t: data[t]['t'] for t in TAGS}
    east[str(l)] = dict(inside=l in ins, ttt={t: [float(LV[t][col[l]].sum()), float(LV[t][col[l]][12:48].sum())] for t in TAGS},
                        frames={t: dict(F_mean=float(data[t]['M'][:, col[l]].mean()), F_max=float(data[t]['M'][:, col[l]].max()),
                                        P_mean=float(data[t]['M'][(tt[t] >= 1800) & (tt[t] < 7200), col[l]].mean()),
                                        P_max=float(data[t]['M'][(tt[t] >= 1800) & (tt[t] < 7200), col[l]].max())) for t in TAGS})
    for pk, bse in (('A', 'nc3'), ('B', 'j1')):
        for wi, wn in ((0, 'full'), (1, 'P_1800_7200')):
            east[str(l)]['%s_%s' % (pk, wn)] = st([east[str(l)]['ttt']['va_s%d' % s][wi] - east[str(l)]['ttt']['%s_s%d' % (bse, s)][wi] for s in SEEDS],
                                                   [east[str(l)]['ttt']['nc3_s%d' % s][wi] for s in SEEDS])
res['sc109_east'] = east
pair = {}
for pk, (a, b, u) in PAIRS.items():
    for s in SEEDS:
        ta, tb = '%s_s%d' % (b, s), '%s_s%d' % (a, s)
        n = min(len(data[ta]['t']), len(data[tb]['t']))
        same = bool(np.array_equal(data[ta]['t'][:n], data[tb]['t'][:n]))
        alla, allb = data[ta]['M'].sum(axis=1), data[tb]['M'].sum(axis=1)
        ic = [col[l] for l in INS]
        oma, omb = data[ta]['M'][:, ic].sum(axis=1), data[tb]['M'][:, ic].sum(axis=1)
        dif = np.nonzero((alla[:n] != allb[:n]) | (oma[:n] != omb[:n]))[0]
        ff = float(data[ta]['t'][dif[0]]) if dif.size else None
        fe = None
        for no in INSERT[ta]:
            x, y = INSERT[ta][no], INSERT[tb][no]
            if x == y:
                continue
            j = next((j for j, (p, q) in enumerate(zip(x, y)) if p != q), min(len(x), len(y)))
            c = min(e for e in (x[j] if j < len(x) else None, y[j] if j < len(y) else None) if e is not None)
            fe = c if fe is None else min(fe, c)
        pair['%s_s%d' % (pk, s)] = dict(same_t=same, first_div_frame=ff, first_div_entry=fe,
                                        ok=bool(same and (ff is None or ff >= 900) and (fe is None or fe >= 900)))
res['pairing'] = pair
s7 = {}
for s in SEEDS:
    for arm in ('j1', 'va'):
        t = '%s_s%d' % (arm, s)
        dd = RUNS[t]['dir'] + '/decisions_' + RUNS[t]['name'] + '/obs150'
        seenoff = {}
        for fpath in sorted(glob.glob(dd + '/err_*.jsonl')):
            T = int(os.path.basename(fpath)[4:10])
            for line in io.open(fpath, encoding='utf-8'):
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                if r.get('kind') != 'lane_change_removal' or r['byte_offset'] in seenoff:
                    continue
                seenoff[r['byte_offset']] = (T, r['time_sec'])
        s7[t] = dict(n_jsonl=len(seenoff), n_late=sum(1 for T, ts in seenoff.values() if ts <= T - 150), err_removals=ERR[t]['removals'])
res['s7'] = s7


def conv(o):
    if isinstance(o, dict):
        return {str(k): conv(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [conv(v) for v in o]
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return o


jd(conv(res), os.path.join(OUT, 'v_metrics.json'))
print('ok', {u: len(v) for u, v in union.items()})
