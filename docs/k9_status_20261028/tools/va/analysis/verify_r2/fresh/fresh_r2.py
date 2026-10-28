# VerifyVA r2 independent recompute (fresh code, 2026-10-24).
# Reads raw run files only (FZP, .err, .inpx, action JSON, obs150 jsonl, runlog) for V-A / J1 / NC3, seeds 31 41 43.
# Does NOT import the analysis tools (AV/tools), the pinned verify tools (AV/verify), r1 fresh code, or stage1.
# Definitions re-implemented from amendment 34 sec.8, ANALYSIS_METHOD_VA.md sec.3-4, stage1_uninserted.py docstring.
# Output: <this folder>/out/fresh_r2.json
import hashlib
import json
import math
import os
import re
import sys
import time
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
SEEDS = (31, 41, 43)
RVA = 'D:/VISSIM_runs/20261023_sdmpc31_k92'
RR = 'D:/VISSIM_runs/20261004_sdmpc31_k8'
NCR = 'D:/VISSIM_runs/20261001_v3c3'
J1N = {31: 'sdmpc31_v3c3_k8j1r_s31', 41: 'sdmpc31_v3c3_k8j1_s41', 43: 'sdmpc31_v3c3_k8j1_s43'}
MEMB = 'D:/VISSIM-merge/sim3/diagnostics/control_area_membership.json'
T_GEN = 9000.0
GRID = 0.5
BIN = 150.0
NB = 60
T90 = 2.920
TRACE_HOPS = 6


def run_paths():
    R = {}
    for s in SEEDS:
        R[('nc3', s)] = dict(
            fzp='%s/s%d_v3c3nc/run/vissim_eval/baseline_s%d_v3c3nc_001.fzp' % (NCR, s, s),
            err='%s/s%d_v3c3nc/run/baseline_s%d_v3c3nc_001.err' % (NCR, s, s),
            inpx='%s/s%d_v3c3nc/prepared/network/baseline_s%d_v3c3nc.inpx' % (NCR, s, s), name=None)
        for arm, root, name in (('j1', RR, J1N[s]), ('va', RVA, 'sdmpc31_v3c3_k92va_s%d' % s)):
            R[(arm, s)] = dict(fzp='%s/%s/vissim_eval/sdmpc31_%s_001.fzp' % (root, name, name),
                               err='%s/%s/network/sdmpc31_%s_001.err' % (root, name, name),
                               inpx='%s/%s/network/sdmpc31_%s.inpx' % (root, name, name),
                               dec='%s/%s/decisions_%s' % (root, name, name),
                               runlog='%s/%s/runlog_%s.txt' % (root, name, name), name=name)
    return R


def local(tag):
    return tag.rsplit('}', 1)[-1]


def parse_inpx(path):
    root = ET.parse(path).getroot()
    links = {}
    inputs = {}
    for el in root.iter():
        t = local(el.tag)
        if t == 'link' and el.get('no') is not None:
            no = int(el.get('no'))
            f = t_ = None
            for ch in el:
                if local(ch.tag) == 'fromLinkEndPt':
                    f = int(ch.get('lane').split()[0])
                elif local(ch.tag) == 'toLinkEndPt':
                    t_ = int(ch.get('lane').split()[0])
            links[no] = (f, t_)
        elif t == 'vehicleInput':
            no = int(el.get('no'))
            ivs = []
            for ch in el.iter():
                if local(ch.tag) == 'timeIntervalVehVolume':
                    start = float(ch.get('timeInt').split()[1]) / 1000.0
                    vol = ch.get('volume')
                    ivs.append((start, ch.get('cont') == 'true', float(vol) if vol not in (None, '') else None))
            ivs.sort(key=lambda x: x[0])
            inputs[no] = dict(link=int(el.get('link')), ivs=ivs)
    for no, d in inputs.items():
        sched, prev = [], 0.0
        for i, (st, cont, vol) in enumerate(d['ivs']):
            en = d['ivs'][i + 1][0] if i + 1 < len(d['ivs']) else T_GEN
            en = min(en, T_GEN)
            rate = prev if cont else (vol or 0.0) / 3600.0
            prev = rate
            if en > st:
                sched.append((st, en, rate))
        d['sched'] = sched
    return links, inputs


def Lcum(sched, t):
    t = np.asarray(t, dtype=float)
    out = np.zeros_like(t)
    for a, b, r in sched:
        out += r * np.clip(t - a, 0.0, b - a)
    return out


def read_fzp(path):
    hdr = None
    with open(path, 'rb') as f:
        for i, line in enumerate(f):
            if line.startswith(b'$VEHICLE:'):
                hdr = i
                cols = line.decode('latin-1').strip().split(':', 1)[1].split(';')
                break
    want = ['SIMSEC', 'NO', 'LANE\\LINK\\NO', 'TMINNETTOT']
    idx = [cols.index(c) for c in want]
    df = pd.read_csv(path, sep=';', skiprows=hdr + 1, header=None, usecols=idx, encoding='latin-1',
                     engine='c', low_memory=False)
    df = df[idx]
    df.columns = ['t', 'veh', 'link', 'tin']
    n_all = len(df)
    early = df['t'] < 5.0
    skipped = {('%.2f' % k): int(v) for k, v in df.loc[early, 't'].value_counts().items()}
    df = df.loc[~early]
    return df, n_all, skipped


def err_parse(path):
    txt = open(path, 'rb').read().decode('latin-1')
    rem = {int(a): int(b) for a, b in re.findall(r'Vehicle input (\d+):[^\n]*?\(remain: (\d+) vehicles\)', txt)}
    rm = re.findall(r'Simulation second ([\d.]+): After [\d.]+ seconds of waiting for lane change the vehicle (\d+)[^\n]*?was removed from link (\d+) at position', txt)
    return rem, [(float(a), int(b), int(c)) for a, b, c in rm]


def attribute(first_link, links, input_by_link):
    """input no for a first-seen link: the link itself, else nearest upstream input link within TRACE_HOPS steps."""
    if first_link in input_by_link:
        return input_by_link[first_link], 0
    preds = attribute.preds
    frontier = {first_link}
    seen = set(frontier)
    for depth in range(1, TRACE_HOPS + 1):
        nxt = set()
        for x in frontier:
            nxt |= preds.get(x, set())
        nxt -= seen
        seen |= nxt
        hits = {input_by_link[x] for x in nxt if x in input_by_link}
        if len(hits) == 1:
            return hits.pop(), depth
        if len(hits) > 1:
            return 'ambiguous', depth
        frontier = nxt
        if not frontier:
            break
    return None, -1


def build_preds(links):
    preds = {}
    for no, (f, t) in links.items():
        if f is not None:  # connector: pred of connector = from link; connector is pred of to link
            preds.setdefault(no, set()).add(f)
            preds.setdefault(t, set()).add(no)
    return preds


def stats(ds):
    a = np.asarray(ds, dtype=float)
    m = float(a.mean())
    sd = float(a.std(ddof=1))
    h = T90 * sd / math.sqrt(len(a))
    return dict(d=[float(x) for x in a], mean=m, sd=sd, ci=[m - h, m + h], ci_excl0=bool(m - h > 0 or m + h < 0),
                neg=int((a < 0).sum()), pos=int((a > 0).sum()))


def label(d3, d4, d4b, drA, drB):
    if not d3 < 0:
        return dict(N='해당 없음(Ω 감소 아님)', W_A='해당 없음(Ω 감소 아님)', W_B='해당 없음(Ω 감소 아님)')
    same = '같은 방향(K8 §5.5 표시 조건 충족, 판정 아님)'
    move = '대기 이전(Ω 밖으로)'
    n_ok = d4 <= 0 and (d4 - d3) <= 0
    return dict(N=same if n_ok else move,
                W_A=same if (n_ok and d4b <= 0 and drA <= 0) else move,
                W_B=same if (n_ok and d4b <= 0 and drB <= 0) else move)


def process_run(key, P, inside, allset, net_ref):
    t0 = time.time()
    links, inputs = parse_inpx(P['inpx'])
    df, n_all, skipped = read_fzp(P['fzp'])
    tu = np.unique(df['t'].to_numpy())
    dt = np.diff(tu)
    regular = bool(np.all(np.abs(dt - 5.0) < 1e-6))
    lk = df['link'].to_numpy()
    ul, li = np.unique(lk, return_inverse=True)
    fi = np.searchsorted(tu, df['t'].to_numpy())
    nf, nl = len(tu), len(ul)
    C = np.bincount(fi * nl + li, minlength=nf * nl).reshape(nf, nl).astype(np.int32)
    unknown = sorted(int(x) for x in ul if int(x) not in allset)
    w = np.zeros(nf)
    w[:-1] += dt / 2.0
    w[1:] += dt / 2.0
    link_vh = {int(ul[j]): float(w @ C[:, j]) / 3600.0 for j in range(nl)}
    in_cols = np.array([int(x) in inside for x in ul])
    all_cols = np.array([int(x) in allset for x in ul])
    c_om = C[:, in_cols].sum(1).astype(float)
    c_all = C[:, all_cols].sum(1).astype(float)
    mid = (tu[:-1] + tu[1:]) / 2.0
    sb = np.clip((mid // BIN).astype(int), 0, NB - 1)

    def bins(c):
        return np.bincount(sb, weights=(c[:-1] + c[1:]) / 2.0 * dt / 3600.0, minlength=NB)

    om_bins, all_bins = bins(c_om), bins(c_all)
    j174 = list(ul).index(174) if 174 in set(ul.tolist()) else None
    c174 = C[:, j174] if j174 is not None else np.zeros(nf)
    k174 = int(np.argmax(c174))
    # first record per vehicle
    first = df.drop_duplicates('veh', keep='first')
    entry = (first['t'] - first['tin']).to_numpy()
    lag = first['t'].to_numpy() - entry
    flink = first['link'].to_numpy()
    input_by_link = {}
    multi_input_link = []
    for no, d in inputs.items():
        if d['link'] in input_by_link:
            multi_input_link.append(d['link'])
        input_by_link[d['link']] = no
    attribute.preds = build_preds(links)
    ent = {no: [] for no in inputs}
    n_amb = n_none = 0
    depth_hist = {}
    cache = {}
    for L, e in zip(flink.tolist(), entry.tolist()):
        if L not in cache:
            cache[L] = attribute(L, links, input_by_link)
        no, dep = cache[L]
        if no == 'ambiguous':
            n_amb += 1
            continue
        if no is None:
            n_none += 1
            continue
        depth_hist[dep] = depth_hist.get(dep, 0) + 1
        ent[no].append(e)
    rem, removals = err_parse(P['err'])
    t_first, t_last = float(tu[0]), float(tu[-1])
    grid = np.arange(t_first + GRID / 2.0, t_last, GRID)
    gw = np.full(grid.shape, GRID)
    gw[-1] = t_last - (grid[-1] - GRID / 2.0)
    gb = np.clip((grid // BIN).astype(int), 0, NB - 1)
    inp = {}
    for no, d in inputs.items():
        e = np.sort(np.asarray(ent[no], dtype=float))
        e = e[e <= t_last + 1e-6]
        LT = float(Lcum(d['sched'], [T_GEN])[0])
        seen = int(e.size)
        tail = float(np.sum(e > t_last - 300.0)) / 300.0 * (T_GEN - t_last)
        R = int(rem.get(no, 0))
        N = seen + tail + R
        rec = dict(link=d['link'], LT=LT, seen=seen, tail=tail, remain=R, N=N, N2=round(N, 2))
        if LT > 0:
            Lg = Lcum(d['sched'], grid)
            I = np.searchsorted(e, grid, side='right')
            q = N / LT * Lg - I
            p = Lg / LT
            sd = np.sqrt(np.maximum(N * p * (1 - p), 1.0))
            rec['queued'] = bool(R > 0 or float((q / sd).max()) >= 4.0)
            rec['_Lg'] = Lg
            rec['_I'] = I
        else:
            rec['queued'] = False
        inp[no] = rec
    nets = dict(links=sorted(links), inputs={no: [d['link'], d['sched']] for no, d in inputs.items()})
    same_net = None
    if net_ref is not None:
        same_net = (nets['links'] == net_ref['links'] and
                    {k: [v[0], [list(x) for x in v[1]]] for k, v in nets['inputs'].items()} ==
                    {k: [v[0], [list(x) for x in v[1]]] for k, v in net_ref['inputs'].items()})
    end_in_net = int(C[-1].sum())
    end_omega = int(C[-1, in_cols].sum())
    res = dict(key='%s_s%d' % key, rows=n_all, skipped=skipped, frames=nf, t_first=t_first, t_last=t_last, regular=regular,
               unknown_links=unknown, n_seen=int(first.shape[0]), lag_max=float(lag.max()), lag_gt5=int((lag > 5.0 + 1e-6).sum()),
               n_ambiguous=n_amb, n_unattributed=n_none, depth_hist=depth_hist, multi_input_link=multi_input_link,
               omega=float(c_om @ w) / 3600.0, all_links=float(c_all @ w) / 3600.0,
               om_bins=om_bins, all_bins=all_bins, link_vh=link_vh,
               l174=dict(vh=link_vh.get(174, 0.0), vh_after4350=float(sum(bins(c174.astype(float))[29:])),
                         mean=float(c174.mean()), max=int(c174[k174]), tmax=float(tu[k174])),
               remain=rem, removalsA=len(removals), removalsB=sum(1 for _, _, L in removals if L not in inside),
               removal_links_unknown=sorted({L for _, _, L in removals if L not in allset}),
               end_in_net=end_in_net, end_omega=end_omega, same_net_as_ref=same_net, sec=None)
    res['_C'] = C
    res['_ul'] = ul
    res['_tu'] = tu
    res['_inp'] = inp
    res['_grid'] = (grid, gw, gb)
    res['_firstentry'] = np.sort(entry)
    res['sec'] = round(time.time() - t0, 1)
    return res, nets


def anchored(run, anchorN):
    grid, gw, gb = run['_grid']
    per = {}
    per_bins = {}
    for no, rec in run['_inp'].items():
        if rec['LT'] <= 0:
            per[no] = 0.0
            per_bins[no] = np.zeros(NB)
            continue
        q = anchorN[no] / rec['LT'] * rec['_Lg'] - rec['_I']
        qc = np.maximum(q, 0.0)
        b = np.bincount(gb, weights=qc * gw, minlength=NB) / 3600.0
        per[no] = float(b.sum())
        per_bins[no] = b
    return per, per_bins


def decisions(P):
    d = P['dec']
    acts = {}
    for fn in os.listdir(d):
        m = re.fullmatch(r'action_(\d{6})\.json', fn)
        if m:
            acts[int(m.group(1))] = fn
    out = dict(n_action=len(acts))
    Ts = sorted(acts)
    J = {T: json.load(open(os.path.join(d, acts[T]), encoding='utf-8')) for T in Ts}
    sd = [T for T in Ts if T >= 900]
    p3 = {T: float(J[T]['green_times']['SC109_p3']) for T in sd}
    low = [T for T in sd if p3[T] <= 24.5]
    best = cur = 0
    prev = None
    for T in low:
        cur = cur + 1 if (prev is not None and T - prev == 150) else 1
        best = max(best, cur)
        prev = T
    out['p3'] = dict(n_sdmpc=len(sd), n_le245=len(low), first=low[0] if low else None, longest=best,
                     mean_all=float(np.mean([p3[T] for T in sd])),
                     mean_ge4350=float(np.mean([p3[T] for T in sd if T >= 4350])))
    heads = ['FW_E__seg0', 'FW_E__seg5', 'FW_E__seg10', 'FW_E__seg15']
    wheads = ['FW_W__seg0', 'FW_W__seg5', 'FW_W__seg10', 'FW_W__seg15']
    vE = [T for T in sd if min(float(J[T]['vsl'][h]) for h in heads) < 110]
    vW = [T for T in sd if min(float(J[T]['vsl'][h]) for h in wheads) < 110]
    out['vsl'] = dict(fwe_lt110=len(vE), fwe_first=vE[0] if vE else None, fwe_T=vE, fww_lt110=len(vW))
    kept = []
    holds = []
    for T in sd:
        meta = J[T].get('metadata', {})
        is_hold = os.path.exists(os.path.join(d, 'action_%06d.hold.json' % T)) or ('hold_previous_on_exception' in meta)
        if is_hold:
            holds.append(T)
        if T < 1050 or is_hold or (T - 150) not in J:
            continue
        a = J[T]['green_times'] == J[T - 150]['green_times'] and J[T]['offsets'] == J[T - 150]['offsets']
        b = 'sdmpc_prediction_sequence' not in J[T].get('diagnostics', {})
        jl = meta.get('joint_leader_selection', {}) or {}
        c = repr(jl.get('selected_objective')) == repr(jl.get('held_objective'))
        if a and b and c:
            kept.append(T)
    out['prev_plan_kept'] = kept
    out['holds'] = holds
    out['k92_keys'] = sum(1 for T in Ts if 'k92_w' in J[T].get('metadata', {}) and 'k92_hb' in J[T].get('metadata', {}))
    # S7: obs150 err_<T>.jsonl lane_change_removal, dedup by byte_offset (first T)
    ob = os.path.join(d, 'obs150')
    seen_off = {}
    if os.path.isdir(ob):
        files = sorted((int(m.group(1)), fn) for fn in os.listdir(ob) for m in [re.fullmatch(r'err_(\d+)\.jsonl', fn)] if m)
        for T, fn in files:
            with open(os.path.join(ob, fn), encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    r = json.loads(line)
                    if r.get('kind') == 'lane_change_removal' and r['byte_offset'] not in seen_off:
                        seen_off[r['byte_offset']] = (T, float(r['time_sec']))
    out['s7'] = dict(n=len(seen_off), late=sum(1 for T, ts in seen_off.values() if ts <= T - 150))
    # wall clock
    wall = []
    for line in open(P['runlog'], encoding='utf-8', errors='replace'):
        m = re.match(r'.*CONTROLLER_DECISION sim_sec=(\d+) wall_sec=([\d.]+) result=exit=(-?\d+)', line)
        if m:
            wall.append((int(m.group(1)), float(m.group(2)), int(m.group(3))))
    sw = [w for T, w, e in wall if T >= 900]
    out['wall'] = dict(n=len(wall), exits=sorted({e for _, _, e in wall}), sdmpc_median=float(np.median(sw)),
                       sdmpc_max=float(max(sw)), n_sdmpc=len(sw))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    T0 = time.time()
    memb = json.load(open(MEMB, encoding='utf-8'))
    inside = {int(x) for x in memb['inside_links']}
    allset = inside | {int(x) for x in memb['outside_links']}
    assert len(inside) == 635 and len(allset) == 1236, (len(inside), len(allset))
    P = run_paths()
    res = dict(schema='verify-va-r2-fresh/v1', inside=len(inside), all=len(allset), runs={}, seeds={})
    net_ref = None
    for s in SEEDS:
        R = {}
        for arm in ('nc3', 'j1', 'va'):
            r, nets = process_run((arm, s), P[(arm, s)], inside, allset, net_ref)
            if net_ref is None:
                net_ref = nets
            R[arm] = r
            print('%s_s%d rows=%d frames=%d sec=%.1f' % (arm, s, r['rows'], r['frames'], r['sec']), flush=True)
        for arm in ('j1', 'va'):
            R[arm]['dec'] = decisions(P[(arm, s)])
        anchorN = {no: R['nc3']['_inp'][no]['N2'] for no in R['nc3']['_inp']}
        for arm in ('nc3', 'j1', 'va'):
            per, pb = anchored(R[arm], anchorN)
            R[arm]['unins_per'] = per
            R[arm]['_unins_bins'] = pb
            R[arm]['queued'] = sorted(no for no, rec in R[arm]['_inp'].items() if rec['queued'])
            R[arm]['inp1083'] = dict(seen=R[arm]['_inp'][1083]['seen'], remain=R[arm]['_inp'][1083]['remain'], delay=per[1083])
            R[arm]['inp282'] = dict(seen=R[arm]['_inp'][282]['seen'], remain=R[arm]['_inp'][282]['remain'], delay=per[282])
        # pairing: first differing frame and first differing entry time
        pr = {}
        for a, b in (('nc3', 'va'), ('j1', 'va')):
            Ca, Cb = R[a], R[b]
            la = {int(x): j for j, x in enumerate(Ca['_ul'])}
            lb = {int(x): j for j, x in enumerate(Cb['_ul'])}
            allk = sorted(set(la) | set(lb))
            nf = min(Ca['_C'].shape[0], Cb['_C'].shape[0])
            Ma = np.zeros((nf, len(allk)), np.int32)
            Mb = np.zeros((nf, len(allk)), np.int32)
            for j, k in enumerate(allk):
                if k in la:
                    Ma[:, j] = Ca['_C'][:nf, la[k]]
                if k in lb:
                    Mb[:, j] = Cb['_C'][:nf, lb[k]]
            diff = np.where((Ma != Mb).any(1))[0]
            ea, eb = Ca['_firstentry'], Cb['_firstentry']
            n = min(len(ea), len(eb))
            de = np.where(np.abs(ea[:n] - eb[:n]) > 1e-6)[0]
            pr['%s-%s' % (b, a)] = dict(first_diff_frame=float(Ca['_tu'][diff[0]]) if diff.size else None,
                                       first_diff_entry=float(min(ea[de[0]], eb[de[0]])) if de.size else None)
        res['seeds'][s] = dict(pairing=pr)
        res['runs'][s] = R
    # unions
    U6 = sorted(set().union(*[set(res['runs'][s][a]['queued']) for s in SEEDS for a in ('nc3', 'va')]))
    U9 = sorted(set().union(*[set(res['runs'][s][a]['queued']) for s in SEEDS for a in ('nc3', 'va', 'j1')]))
    U6J = sorted(set().union(*[set(res['runs'][s][a]['queued']) for s in SEEDS for a in ('nc3', 'j1')]))
    res['unions'] = dict(U6VA=U6, U9=U9, U6J1=U6J)
    lev = {}
    for s in SEEDS:
        lev[s] = {}
        for arm in ('nc3', 'j1', 'va'):
            r = res['runs'][s][arm]
            x = dict(om=r['omega'], a4=r['all_links'])
            for un, U in (('U6VA', U6), ('U9', U9), ('U6J1', U6J)):
                b = sum(r['unins_per'][no] for no in U)
                x['b4_' + un] = b
                x['f4_' + un] = r['all_links'] + b
                x['oa_' + un] = r['all_links'] + b - r['omega']
                x['bins3'] = r['om_bins']
                x['bins4_' + un] = r['all_bins'] + sum((r['_unins_bins'][no] for no in U), np.zeros(NB))
            x['ob'] = r['all_links'] - r['omega']
            x['rA'] = r['removalsA']
            x['rB'] = r['removalsB']
            x['u1098_U6VA'] = r['unins_per'][1098]
            x['u1099_U6VA'] = r['unins_per'][1099]
            lev[s][arm] = x
    pairs = {}
    for P_, (a, b, un) in dict(A=('va', 'nc3', 'U6VA'), B=('va', 'j1', 'U9'), Bp=('j1', 'nc3', 'U9'), J1R=('j1', 'nc3', 'U6J1')).items():
        D = {}
        for s in SEEDS:
            A_, B_ = lev[s][a], lev[s][b]
            D[s] = dict(d3=A_['om'] - B_['om'], d4=A_['f4_' + un] - B_['f4_' + un], d4a=A_['a4'] - B_['a4'],
                        d4b=A_['b4_' + un] - B_['b4_' + un], doa=A_['oa_' + un] - B_['oa_' + un], dob=A_['ob'] - B_['ob'],
                        drA=A_['rA'] - B_['rA'], drB=A_['rB'] - B_['rB'],
                        cum3=np.cumsum(A_['bins3'] - B_['bins3']),
                        cum4=np.cumsum(A_['bins4_' + un] - B_['bins4_' + un]))
            D[s]['cumoa'] = D[s]['cum4'] - D[s]['cum3']
        st = {k: stats([D[s][k] for s in SEEDS]) for k in ('d3', 'd4', 'd4a', 'd4b', 'doa', 'dob', 'drA', 'drB')}
        nc_mean = {k: float(np.mean([lev[s]['nc3'][kk] for s in SEEDS])) for k, kk in
                   (('d3', 'om'), ('d4', 'f4_' + un), ('doa', 'oa_' + un))}
        labs = {s: label(D[s]['d3'], D[s]['d4'], D[s]['d4b'], D[s]['drA'], D[s]['drB']) for s in SEEDS}
        labs['mean'] = label(st['d3']['mean'], st['d4']['mean'], st['d4b']['mean'], st['drA']['mean'], st['drB']['mean'])
        marks = [150 * k for k in range(1, NB + 1)]
        cum = {}
        for nm in ('cum3', 'cum4', 'cumoa'):
            cum[nm] = {str(s): {str(T): float(D[s][nm][T // 150 - 1]) for T in (900, 1800, 3600, 5400, 7200, 9000)} for s in SEEDS}
        sign = {}
        for s in SEEDS:
            c3, c4, co = D[s]['cum3'], D[s]['cum4'], D[s]['cumoa']
            sign[str(s)] = dict(
                pre900_maxabs=float(max(np.abs(np.diff(np.concatenate([[0], c3])))[:6].max(),
                                        np.abs(np.diff(np.concatenate([[0], c4])))[:6].max())),
                c3_neg_from_1800=bool(np.all(c3[11:] < 0)), coa_pos_from_1800=bool(np.all(co[11:] > 0)),
                c4_neg_from_5400=bool(np.all(c4[35:] < 0)),
                c3_first_all_neg_after=[marks[i] for i in range(NB) if np.all(c3[i:] < 0)][:1],
                c4_first_all_neg_after=[marks[i] for i in range(NB) if np.all(c4[i:] < 0)][:1])
        pairs[P_] = dict(per_seed={str(s): {k: float(v) for k, v in D[s].items() if not k.startswith('cum')} for s in SEEDS},
                         stats=st, nc_mean=nc_mean,
                         pct={k: 100.0 * st[k]['mean'] / nc_mean[k] for k in nc_mean},
                         labels={str(k): v for k, v in labs.items()}, cum=cum, sign=sign)
    res['pairs'] = pairs
    res['levels'] = {str(s): {arm: {k: float(v) for k, v in lev[s][arm].items() if not k.startswith('bins')} for arm in lev[s]} for s in SEEDS}
    # links
    lk = {}
    for s in SEEDS:
        lk[str(s)] = {arm: {str(L): res['runs'][s][arm]['link_vh'].get(L, 0.0) for L in (21, 174, 1220000704, 1220000803)}
                      for arm in ('nc3', 'j1', 'va')}
    res['links'] = lk
    e704 = {}
    for nm, (a, b) in dict(A=('va', 'nc3'), B=('va', 'j1')).items():
        e704[nm] = stats([lk[str(s)][a]['1220000704'] - lk[str(s)][b]['1220000704'] for s in SEEDS])
        e704[nm + '_803'] = stats([lk[str(s)][a]['1220000803'] - lk[str(s)][b]['1220000803'] for s in SEEDS])
    res['east'] = e704
    # strip private arrays
    runs_out = {}
    for s in SEEDS:
        runs_out[str(s)] = {}
        for arm, r in res['runs'][s].items():
            runs_out[str(s)][arm] = {k: v for k, v in r.items() if not k.startswith('_') and k not in ('om_bins', 'all_bins', 'link_vh')}
            runs_out[str(s)][arm]['unins_per'] = {str(k): v for k, v in r['unins_per'].items()}
    res['runs'] = runs_out
    res['seeds'] = {str(k): v for k, v in res['seeds'].items()}
    res['sec_total'] = round(time.time() - T0, 1)

    def conv(o):
        if isinstance(o, dict):
            return {str(k): conv(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [conv(v) for v in o]
        if isinstance(o, np.ndarray):
            return [conv(v) for v in o.tolist()]
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        return o
    p = os.path.join(OUT, 'fresh_r2.json')
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(conv(res), f, ensure_ascii=False, indent=1, sort_keys=True)
    print('WROTE', p, hashlib.sha256(open(p, 'rb').read()).hexdigest(), 'sec', res['sec_total'], flush=True)


if __name__ == '__main__':
    main()
