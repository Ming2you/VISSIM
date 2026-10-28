# VerifyVA r1 - fresh recomputation of V-A headline numbers from raw run files.
# Written by the verifier on 2026-10-24. Imports NO analysis tool (AV/tools), NO verify tool (AV/verify), NO stage1 module.
# Definitions follow amendment 34 Sec. 8 / ANALYSIS_METHOD_VA.md Sec. 3-4 / stage1_uninserted docstring, re-implemented here.
# Reads only (FZP, .err, .inpx, membership JSON, action JSONs, runlogs). Writes only to <this folder>/out/.
# usage: python -B fresh_va.py [--no-json]   (BELOW_NORMAL set inside)
import ctypes, io, json, math, os, re, sys, time
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd

try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
os.makedirs(OUT, exist_ok=True)
RVA = 'D:/VISSIM_runs/20261023_sdmpc31_k92'
RR = 'D:/VISSIM_runs/20261004_sdmpc31_k8'
NCR = 'D:/VISSIM_runs/20261001_v3c3'
MEMB = 'D:/VISSIM-merge/sim3/diagnostics/control_area_membership.json'
SEEDS = [31, 41, 43]
J1N = {31: 'sdmpc31_v3c3_k8j1r_s31', 41: 'sdmpc31_v3c3_k8j1_s41', 43: 'sdmpc31_v3c3_k8j1_s43'}
VAN = {s: 'sdmpc31_v3c3_k92va_s%d' % s for s in SEEDS}
T_END = 9000.0
DO_JSON = '--no-json' not in sys.argv


def runs():
    R = {}
    for s in SEEDS:
        R[('nc3', s)] = dict(fzp='%s/s%d_v3c3nc/run/vissim_eval/baseline_s%d_v3c3nc_001.fzp' % (NCR, s, s),
                             err='%s/s%d_v3c3nc/run/baseline_s%d_v3c3nc_001.err' % (NCR, s, s),
                             inpx='%s/s%d_v3c3nc/prepared/network/baseline_s%d_v3c3nc.inpx' % (NCR, s, s))
        for arm, root, nm in (('j1', RR, J1N[s]), ('va', RVA, VAN[s])):
            d = '%s/%s' % (root, nm)
            R[(arm, s)] = dict(fzp='%s/vissim_eval/sdmpc31_%s_001.fzp' % (d, nm),
                               err='%s/network/sdmpc31_%s_001.err' % (d, nm),
                               inpx='%s/network/sdmpc31_%s.inpx' % (d, nm),
                               dec='%s/decisions_%s' % (d, nm), runlog='%s/runlog_%s.txt' % (d, nm))
    return R


def net_of(inpx):
    root = ET.parse(inpx).getroot()
    links = {}
    for el in root.find('links'):
        no = int(el.get('no'))
        f = el.find('fromLinkEndPt')
        t = el.find('toLinkEndPt')
        links[no] = (int(f.get('lane').split()[0]), int(t.get('lane').split()[0])) if f is not None else None
    inputs = {}
    for el in root.find('vehicleInputs'):
        rows = []
        for v in el.iter('timeIntervalVehVolume'):
            rows.append((float(v.get('timeInt').split()[1]) / 1000.0, float(v.get('volume')), v.get('cont') == 'true'))
        rows.sort()
        inputs[int(el.get('no'))] = (int(el.get('link')), rows)
    return links, inputs


def sched(rows):
    # piecewise-constant rate (veh/s); last interval closed at T_END; cont = previous rate
    out, prev = [], 0.0
    for k, (a, vph, cont) in enumerate(rows):
        b = rows[k + 1][0] if k + 1 < len(rows) else T_END
        b = min(b, T_END)
        r = prev if cont else vph / 3600.0
        prev = r
        if b > a:
            out.append((a, b, r))
    return out


def cum(sc, x):
    x = np.asarray(x, dtype=float)
    y = np.zeros_like(x)
    for a, b, r in sc:
        y = y + r * np.clip(x - a, 0.0, b - a)
    return y


REM = re.compile(r'Vehicle input (\d+):[^\n]*?remain:\s*(\d+)\s*vehicles')
RMV = re.compile(r'Simulation second ([0-9.]+): After [0-9.]+ seconds of waiting for lane change the vehicle (\d+)[^\n]*?was removed from link (\d+)')


def read_err(p):
    txt = open(p, 'rb').read().decode('cp949', errors='replace')
    rem = {}
    for m in REM.finditer(txt):
        rem[int(m.group(1))] = int(m.group(2))
    rmv = [int(m.group(3)) for m in RMV.finditer(txt)]
    return rem, rmv


def read_fzp(p):
    off, cols = 0, None
    with open(p, 'rb') as f:
        for raw in f:
            off += len(raw)
            if raw.startswith(b'$VEHICLE:'):
                cols = raw[9:].strip().decode('ascii').split(';')
                break
    ci = [cols.index(c) for c in ('SIMSEC', 'NO', 'LANE\\LINK\\NO', 'TMINNETTOT')]
    with open(p, 'rb') as f:
        f.seek(off)
        df = pd.read_csv(f, sep=';', header=None, usecols=ci, engine='c', low_memory=False,
                         dtype={ci[0]: np.float64, ci[1]: np.int64, ci[2]: np.int64, ci[3]: np.float64})
    df.columns = ['t', 'no', 'lk', 'tm']
    n_all = len(df)
    df = df[df['t'] >= 5.0]  # 0.10 s row skipped (same rule as the analysis shim)
    return df, n_all - len(df)


def longest_run(ts, step=150):
    best = cur = 0
    prev = None
    for t in ts:
        cur = cur + 1 if (prev is not None and t - prev == step) else 1
        best = max(best, cur)
        prev = t
    return best


def main():
    t00 = time.time()
    R = runs()
    memb = json.load(io.open(MEMB, encoding='utf-8-sig'))
    INS = {int(x) for x in memb['inside_links']}
    OUTS = {int(x) for x in memb['outside_links']}
    assert len(INS) == 635 and len(INS | OUTS) == 1236 and not (INS & OUTS)
    base_links, base_inputs = net_of(R[('nc3', 31)]['inpx'])
    assert set(base_links) == INS | OUTS
    res = {'per_run': {}, 'net_same_as_nc3_s31': {}, 'notes': []}
    input_by_link = {}
    for no, (lk, rows) in base_inputs.items():
        input_by_link.setdefault(lk, []).append(no)
    preds = {}
    for lk, ft in base_links.items():
        if ft is not None:
            preds.setdefault(lk, []).append(ft[0])
            preds.setdefault(ft[1], []).append(lk)

    def upstream_inputs(lk):
        front, seen = [lk], {lk}
        for _ in range(6):
            h = sorted({i for x in front for i in input_by_link.get(x, [])})
            if h:
                return h
            nxt = []
            for x in front:
                for q in preds.get(x, []):
                    if q not in seen:
                        seen.add(q)
                        nxt.append(q)
            front = nxt
            if not front:
                break
        return []

    SCH = {no: sched(rows) for no, (lk, rows) in base_inputs.items()}
    LT = {no: float(cum(SCH[no], [T_END])[0]) for no in SCH}
    ENT, N, RUNINFO = {}, {}, {}
    for key in [(a, s) for s in SEEDS for a in ('nc3', 'j1', 'va')]:
        tag = '%s_s%d' % key
        r = R[key]
        t1 = time.time()
        lk_i, in_i = net_of(r['inpx'])
        res['net_same_as_nc3_s31'][tag] = (lk_i == base_links and in_i == base_inputs)
        df, skipped = read_fzp(r['fzp'])
        tt, fi = np.unique(df['t'].to_numpy(), return_inverse=True)
        lids, li = np.unique(df['lk'].to_numpy(), return_inverse=True)
        NF, NL = len(tt), len(lids)
        Cm = np.bincount(fi * NL + li, minlength=NF * NL).reshape(NF, NL).astype(np.float64)
        dt = np.diff(tt)
        w = np.zeros(NF)
        w[:-1] += dt / 2.0
        w[1:] += dt / 2.0
        link_vh = dict(zip(lids.tolist(), (w @ Cm / 3600.0).tolist()))
        unknown = sorted(set(lids.tolist()) - set(base_links))
        omega = sum(v for l, v in link_vh.items() if l in INS)
        allv = sum(link_vh.values())
        # 150 s bins by step midpoint (for cumulative checks)
        mid = (tt[:-1] + tt[1:]) / 2.0
        bi = np.clip((mid // 150).astype(int), 0, 59)
        ins_mask = np.isin(lids, list(INS))
        fo = Cm[:, ins_mask].sum(axis=1)
        fa = Cm.sum(axis=1)
        om_bins = np.bincount(bi, weights=(fo[:-1] + fo[1:]) / 2.0 * dt / 3600.0, minlength=60)
        all_bins = np.bincount(bi, weights=(fa[:-1] + fa[1:]) / 2.0 * dt / 3600.0, minlength=60)
        j174 = int(np.where(lids == 174)[0][0])
        c174 = Cm[:, j174]
        k = int(np.argmax(c174))
        first = df.drop_duplicates(subset='no', keep='first')
        tf = first['t'].to_numpy()
        tm = first['tm'].to_numpy()
        flk = first['lk'].to_numpy()
        entry = np.where(np.isnan(tm), tf, np.round(tf - tm, 1))
        ent = {no: [] for no in base_inputs}
        cache, unatt, amb = {}, 0, 0
        for e, l in zip(entry.tolist(), flk.tolist()):
            if l in input_by_link:
                h = input_by_link[l]
            else:
                if l not in cache:
                    cache[l] = upstream_inputs(l)
                h = cache[l]
            if len(h) == 1:
                ent[h[0]].append(e)
            elif len(h) > 1:
                amb += 1
            else:
                unatt += 1
        for no in ent:
            ent[no] = np.sort(np.asarray(ent[no], dtype=float))
        rem, rmv = read_err(r['err'])
        t_first, t_last = float(tt[0]), float(tt[-1])
        # own anchor N and queued flag per input
        grid = np.arange(t_first + 0.25, t_last, 0.5)
        gw = np.full(grid.shape, 0.5)
        gw[-1] = t_last - (grid[-1] - 0.25)
        Nrun, queued = {}, {}
        for no in base_inputs:
            e = ent[no][ent[no] <= t_last + 1e-6]
            tail = int(np.sum(e > t_last - 300.0)) / 300.0 * (T_END - t_last)
            Rr = int(rem.get(no, 0))
            n = e.size + tail + Rr
            Nrun[no] = n
            if LT[no] > 0:
                Lg = cum(SCH[no], grid)
                q = n / LT[no] * Lg - np.searchsorted(e, grid, side='right')
                p = Lg / LT[no]
                sd = np.sqrt(np.maximum(n * p * (1 - p), 1.0))
                queued[no] = bool(Rr > 0 or float((q / sd).max()) >= 4.0)
            else:
                queued[no] = False
        ENT[key] = ent
        N[key] = Nrun
        RUNINFO[key] = dict(grid=grid, gw=gw, rem=rem, queued=queued, t_first=t_first, t_last=t_last)
        res['per_run'][tag] = dict(
            frames=NF, first=t_first, last=t_last, skipped_rows_lt5=int(skipped), unknown_links=unknown,
            vehicles_seen=int(len(first)), omega_ttt=omega, all_ttt=allv, om_bins=om_bins.tolist(), all_bins=all_bins.tolist(),
            link174_ttt=link_vh.get(174, 0.0), link174_ttt_after4350=None,
            link174_frame_mean=float(c174.mean()), link174_frame_max=int(c174.max()), link174_frame_max_t=float(tt[k]),
            link1220000704_ttt=link_vh.get(1220000704, 0.0), link1220000803_ttt=link_vh.get(1220000803, 0.0),
            link21_ttt=link_vh.get(21, 0.0),
            removals_A=len(rmv), removals_B_outside=sum(1 for l in rmv if l not in INS),
            remains={str(k2): v for k2, v in sorted(rem.items())}, inserted_1083=int(ent[1083].size),
            queued_inputs=sorted(no for no, qd in queued.items() if qd or rem.get(no, 0) > 0),
            unattributed=unatt, ambiguous=amb, sec=round(time.time() - t1, 1))
        # link 174 after 4350 s (bins 29..59): steps with midpoint >= 4350
        m2 = bi >= 29
        res['per_run'][tag]['link174_ttt_after4350'] = float(np.sum(((c174[:-1] + c174[1:]) / 2.0 * dt / 3600.0)[m2]))
        print(tag, 'frames', NF, 'omega %.2f all %.2f l174 %.2f sec %.1f' % (omega, allv, link_vh.get(174, 0.0), time.time() - t1), flush=True)
        del df, Cm, first

    def clipped(key, no, anchor, bins=False):
        ri = RUNINFO[key]
        grid, gw = ri['grid'], ri['gw']
        e = ENT[key][no]
        q = anchor / LT[no] * cum(SCH[no], grid) - np.searchsorted(e, grid, side='right')
        qc = np.maximum(q, 0.0) * gw / 3600.0
        if bins:
            return np.bincount(np.clip((grid // 150).astype(int), 0, 59), weights=qc, minlength=60)
        return float(qc.sum())

    unions = {'U6VA': ('va', 'nc3'), 'U9': ('va', 'j1', 'nc3'), 'U6J1': ('j1', 'nc3')}
    U = {}
    for u, arms in unions.items():
        s_ = set()
        for s in SEEDS:
            for a in arms:
                s_ |= set(res['per_run']['%s_s%d' % (a, s)]['queued_inputs'])
        U[u] = sorted(s_)
    res['unions'] = U
    anchor = {s: {no: round(N[('nc3', s)][no], 2) for no in base_inputs} for s in SEEDS}
    lev = {}
    for u in U:
        for s in SEEDS:
            for a in unions[u]:
                key = (a, s)
                pr = res['per_run']['%s_s%d' % key]
                b4 = 0.0
                byin = {}
                b4bins = np.zeros(60)
                for no in U[u]:
                    v = clipped(key, no, anchor[s][no])
                    byin[str(no)] = v
                    b4 += v
                    b4bins += clipped(key, no, anchor[s][no], bins=True)
                M3, M4a = pr['omega_ttt'], pr['all_ttt']
                lev['%s|%s_s%d' % (u, a, s)] = dict(M3=M3, M4a=M4a, M4b=b4, M4=M4a + b4, OUTa=M4a + b4 - M3, OUTb=M4a - M3,
                                                     unins_by_input=byin,
                                                     cum_M3=np.cumsum(pr['om_bins']).tolist(),
                                                     cum_M4=np.cumsum(np.asarray(pr['all_bins']) + b4bins).tolist())
    res['levels'] = lev
    # 1083 delay with NC3 anchor (any union)
    res['unins_1083_nc3anchor'] = {'%s_s%d' % (a, s): clipped((a, s), 1083, anchor[s][1083]) for s in SEEDS for a in ('nc3', 'j1', 'va')}

    def stats(v):
        m = sum(v) / 3.0
        sd = math.sqrt(sum((x - m) ** 2 for x in v) / 2.0)
        h = 2.920 * sd / math.sqrt(3.0)
        return dict(d=v, mean=m, sd=sd, ci=[m - h, m + h], ci_excl0=(m - h > 0 or m + h < 0))

    def lab(d3, d4, d4b, dra, drb):
        if d3 >= 0:
            return dict(N='해당 없음', W_A='해당 없음', W_B='해당 없음')
        nn = 'same' if (d4 <= 0 and d4 - d3 <= 0) else 'shift'
        return dict(N=nn, W_A='same' if (nn == 'same' and d4b <= 0 and dra <= 0) else 'shift',
                    W_B='same' if (nn == 'same' and d4b <= 0 and drb <= 0) else 'shift')

    pairs = {'A': ('va', 'nc3', 'U6VA'), 'B': ('va', 'j1', 'U9'), 'Bp': ('j1', 'nc3', 'U9'), 'J1R': ('j1', 'nc3', 'U6J1')}
    P = {}
    for pk, (x, y, u) in pairs.items():
        dd = {}
        for m in ('M3', 'M4a', 'M4b', 'M4', 'OUTa', 'OUTb'):
            dd[m] = stats([lev['%s|%s_s%d' % (u, x, s)][m] - lev['%s|%s_s%d' % (u, y, s)][m] for s in SEEDS])
        for m, fld in (('remA', 'removals_A'), ('remB', 'removals_B_outside'), ('l174', 'link174_ttt'),
                       ('l704', 'link1220000704_ttt'), ('l803', 'link1220000803_ttt')):
            dd[m] = stats([res['per_run']['%s_s%d' % (x, s)][fld] - res['per_run']['%s_s%d' % (y, s)][fld] for s in SEEDS])
        labels = {}
        for i, s in enumerate(SEEDS):
            labels[str(s)] = lab(dd['M3']['d'][i], dd['M4']['d'][i], dd['M4b']['d'][i], dd['remA']['d'][i], dd['remB']['d'][i])
        labels['mean'] = lab(dd['M3']['mean'], dd['M4']['mean'], dd['M4b']['mean'], dd['remA']['mean'], dd['remB']['mean'])
        cumd = {}
        for s in SEEDS:
            a3 = np.asarray(lev['%s|%s_s%d' % (u, x, s)]['cum_M3']) - np.asarray(lev['%s|%s_s%d' % (u, y, s)]['cum_M3'])
            a4 = np.asarray(lev['%s|%s_s%d' % (u, x, s)]['cum_M4']) - np.asarray(lev['%s|%s_s%d' % (u, y, s)]['cum_M4'])
            cumd[str(s)] = dict(d3=a3.tolist(), d4=a4.tolist(), dout=(a4 - a3).tolist())
        P[pk] = dict(stats=dd, labels=labels, cum=cumd)
    res['pairs'] = P

    # control side from action JSONs and runlogs (V-A and J1)
    CW = re.compile(r'CONTROLLER_DECISION sim_sec=(\d+) wall_sec=([0-9.]+)')
    ctl = {}
    for s in SEEDS:
        for a in ('j1', 'va'):
            r = R[(a, s)]
            tag = '%s_s%d' % (a, s)
            txt = open(r['runlog'], 'rb').read().decode('utf-8', errors='replace')
            wall = {}
            for m in CW.finditer(txt):
                wall[int(m.group(1))] = float(m.group(2))
            sd_w = sorted(v for t_, v in wall.items() if t_ >= 900)
            rec = dict(n_wall=len(wall), sdmpc_wall_median=float(np.median(sd_w)) if sd_w else None)
            if DO_JSON:
                files = sorted(f for f in os.listdir(r['dec']) if re.fullmatch(r'action_\d{6}\.json', f))
                p3, vsl_lt, k92w, k92hb, prev_keep = [], [], 0, 0, []
                c_a = c_b = c_c = 0
                prev = None
                for f in files:
                    T = int(f[7:13])
                    d = json.load(io.open(os.path.join(r['dec'], f), encoding='utf-8-sig'))
                    md = d.get('metadata', {})
                    k92w += 'k92_w' in md
                    k92hb += 'k92_hb' in md
                    cur = (d['green_times'], d['offsets'])
                    if T >= 900:
                        g3 = d['green_times'].get('SC109_p3')
                        p3.append((T, g3))
                        heads = [d['vsl'].get('FW_E__seg%d' % z) for z in (0, 5, 10, 15)]
                        if any(h is not None and h < 110 for h in heads):
                            vsl_lt.append((T, heads))
                        if T >= 1050:
                            ga = prev is not None and cur[0] == prev[0] and cur[1] == prev[1]
                            gb = 'sdmpc_prediction_sequence' not in d.get('diagnostics', {})
                            jl = md.get('joint_leader_selection', {})
                            gc = repr(jl.get('selected_objective')) == repr(jl.get('held_objective'))
                            c_a += ga
                            c_b += gb
                            c_c += gc
                            if ga and gb and gc:
                                prev_keep.append(T)
                    prev = cur
                    del d
                lo = [t_ for t_, g in p3 if g is not None and g <= 24.5]
                rec.update(n_action=len(files), n_sdmpc=len(p3), p3_le_245=len(lo), p3_first_T=(lo[0] if lo else None),
                           p3_longest=longest_run(lo), vsl_fwe_lt110=len(vsl_lt), vsl_fwe_lt110_T=[t_ for t_, _ in vsl_lt],
                           vsl_fwe_lt110_heads=sorted({json.dumps(h) for _, h in vsl_lt}),
                           k92_w=k92w, k92_hb=k92hb, prev_plan_a=c_a, prev_plan_b=c_b, prev_plan_c=c_c, prev_plan_all=prev_keep)
            ctl[tag] = rec
            print(tag, 'control', json.dumps({k: v for k, v in rec.items() if k not in ('vsl_fwe_lt110_T',)}), flush=True)
    res['control'] = ctl
    res['wall_ratio'] = {str(s): (ctl['va_s%d' % s]['sdmpc_wall_median'] / ctl['j1_s%d' % s]['sdmpc_wall_median']) for s in SEEDS}
    res['sec'] = round(time.time() - t00, 1)
    with io.open(os.path.join(OUT, 'fresh_va.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=float)
    print('FRESH_DONE sec=%.1f' % res['sec'], flush=True)


if __name__ == '__main__':
    main()
