"""F17b candidate selection (K8_PREDECLARATION_AMENDMENT_19 r2 section 2.3, P0-3; the K9-1 mini-probe tool
p0_3_f17b_select.py sha 144ee4ed... moved into the repository unchanged in its rule; VISSIM side only: the s41 / s53
v3c3 NC fit FZP, read only, BELOW_NORMAL; no plant output, no judging-state output).  Library of the evidence builder
(build_k9_evidence.py f17b) and of the gate harness (sa_vissim_ref.py seeds[S].k91.ew, R11).

Rule (fixed in the amendment; the operationalization written in the probe tool before it ran):
  exits      E_W = {10479, 10491, 10638, 10645} (P0-4, component.offramps road FW_W).
  stations   the 7e079efb deployed obs150 detector table diagnostics/sdmpc_n31_20260924/obs150/obs150_detectors_v2.csv
             (blob 2cd8340007e83717105d8cc7839afa3bc74f8250, sha256 108debbb...; the file obs150_contract reads for
             off_entry_ref / through_ref): off_entry:<o> = connector o @ 1.0 m (all its lanes); through:<o> = the
             through row (link, pos; all lanes): 10479 -> 26 @3525.599795, 10491 -> 10771 @3.707109, 10638 -> 120
             @2485.050357, 10645 -> 120 @2100.902537.
  counting   off_entry:<o> event = the vehicle's first frame on connector o with POS >= 1.0.  through:<o> event = the
             vehicle's first frame whose FW_W chain position (geometry chains 26 -> 10771 -> 120 of the plant geometry
             s31_v3c3nc_observations/geometry.json: chain_pos = link offset + POS) is >= the station's chain position,
             AFTER an earlier frame of the same vehicle upstream of the station (a chain frame with chain_pos <
             station, or a frame on an FW_W on-ramp connector whose landing chain_pos_m < station) -- a crossing of the
             point; each vehicle counts at most once per point.
  windows    window w = floor((t - 0.1) / 150) covers (150 w, 150 (w + 1)]; off_w, elig_w = off + through events.
  candidates at decision T (window k = (T - 150 (k + 1), T - 150 k], i.e. w = T/150 - 1 - k; empty -> 0.0):
             C0 = off_0 / elig_0; C1 = k = 0..2 pooled; C2 = k = 0..5 pooled; C4 = every window ending in (0, T]
             pooled; C3 = (n s150 + n0 s_prior(j)) / (n + n0), n = elig_0, s150 = C0, j = min(9, floor(T / 900)),
             s_prior(j) = prior seed(s) pooled sum off / sum elig of windows 6 j .. 6 j + 5, elig sum 0 -> the prior's
             all-time pooled value; n0 = numpy.median of the prior's window elig with window end in (900, 9000]
             (pooled prior: the two seeds' windows in one list); n + n0 = 0 -> s150.
  decisions  T in [1050, 8400], T = 0 mod 150, minus GRID9 and DP_T (every seed).
  realized   s_real(T, H) = sum off / sum elig over windows ending in (T, min(T + H, 9000)], H in {450, 1800, 4050};
             (o, T, H) with sum elig = 0 left out; err = |s_hat - s_real|.
  folds      A = (evaluate s53, C3 prior s41), B = (evaluate s41, C3 prior s53).
  loss       L_{c,f} = (1 / |E_W|) sum_o mean over the remaining (T, H) pairs of err (an exit with 0 pairs -> STOP);
             L_c = (L_{c,A} + L_{c,B}) / 2; full float precision.
  selection  candidates allowed by P0-4 (p0/P0_4_TRACE.md sha b3fced27...): C0 C1 C2 C4 C3; L* = min_c L_c; the
             first of (C0, C1, C2, C4, C3) with L_c <= L* + 0.002.
  runtime    the selected id, exits, window / decision interval and the candidate definition; for C3 the pooled
             s41 + s53 prior s_prior(j), j = 0..9, the pooled all-time value and n0 per exit."""
import ctypes
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NC = Path(r'D:/VISSIM_runs/20261001_v3c3')
DET = ROOT / 'diagnostics/sdmpc_n31_20260924/obs150/obs150_detectors_v2.csv'
DET_SHA = '108debbb4b021796b195927ba2140dafab571e1d976734190f5d8f5bd255cfbc'
DET_BLOB = '2cd8340007e83717105d8cc7839afa3bc74f8250'
GEOM = ROOT / ('diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/v3c3_nc_20261001/observations/'
               's31_v3c3nc_observations/geometry.json')
EW = ('10479', '10491', '10638', '10645')
SEEDS = (41, 53)
GRID9 = (900, 1200, 1800, 2250, 2700, 3000, 3600, 4200, 4950)
DP_T = tuple(900 + 450 * k for k in range(17))
TS = [T for T in range(1050, 8401, 150) if T not in GRID9 and T not in DP_T]
HS = (450, 1800, 4050)
ORDER = ('C0', 'C1', 'C2', 'C4', 'C3')
ALLOWED = ('C0', 'C1', 'C2', 'C4', 'C3')
MARGIN = 0.002
COLS = ['SIMSEC', 'NO', 'LINK', 'LANE', 'POS', 'POSLAT', 'SPEED', 'TMINNETTOT', 'DELAYTM', 'DESSPEED', 'LENGTH',
        'ROUTDECNO', 'ROUTENO', 'ROUTDECTYPE', 'NEXTLINK', 'DESTLANE', 'LNCHG', 'INTERACTSTATE', 'INTERACTTARGTYPE',
        'INTERACTTARGNO', 'FX', 'FY', 'RX', 'RY', 'ACCEL']
DEFINITION = {'C0': 'k=0', 'C1': 'k=0..2', 'C2': 'k=0..5', 'C4': 'all windows ending in (0, T]',
              'C3': '(n s150 + n0 s_prior(j)) / (n + n0), j = min(9, floor(T/900))'}


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def below_normal():
    try:
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    except Exception:
        pass


def stations():
    import csv
    if sha(DET) != DET_SHA:
        raise SystemExit('K9_EVIDENCE_STOP f17b: detector table sha differs')
    rows = list(csv.DictReader(open(DET, encoding='utf-8')))
    out = {}
    for o in EW:
        off = [r for r in rows if r['role'] == 'off_entry' and r['ref'] == o]
        thr = [r for r in rows if r['role'] == 'through' and r['ref'] == o]
        if not off or not thr or len({(r['link'], r['pos']) for r in off}) != 1 or len({(r['link'], r['pos'])
                                                                                     for r in thr}) != 1:
            raise SystemExit(f'K9_EVIDENCE_STOP f17b: detector rows of {o} not a single point each')
        out[o] = {'off_link': int(off[0]['link']), 'off_pos': float(off[0]['pos']),
                  'off_lanes': sorted(int(r['lane']) for r in off),
                  'thr_link': int(thr[0]['link']), 'thr_pos': float(thr[0]['pos']),
                  'thr_lanes': sorted(int(r['lane']) for r in thr)}
    return out


def geometry():
    g = json.loads(GEOM.read_text(encoding='utf-8'))
    chain = {int(c['link']): float(c['offset_m']) for c in g['chains']['FW_W']}
    feeders = {int(b['connector']): float(b['chain_pos_m']) for b in g['boundaries']
               if b.get('road') == 'FW_W' and b.get('kind') == 'ramp'}
    return chain, feeders, sha(GEOM)


def load(seed, keep_links, chain):
    import numpy as np
    import pandas as pd
    fzp = NC / f's{seed}_v3c3nc' / 'run' / 'vissim_eval' / f'baseline_s{seed}_v3c3nc_001.fzp'
    parts, n = [], 0
    it = pd.read_csv(fzp, sep=';', skiprows=38, header=None, names=COLS, usecols=['SIMSEC', 'NO', 'LINK', 'POS'],
                     chunksize=1_000_000, encoding='latin-1',
                     dtype={'SIMSEC': np.float64, 'NO': np.int64, 'LINK': np.int64, 'POS': np.float64})
    for ch in it:
        n += len(ch)
        L, P = ch['LINK'], ch['POS']
        m = L.isin(keep_links) & ~L.isin([26, 120])
        m |= (L == 26) & (P >= 2800.0)
        m |= (L == 120) & (P <= 2800.0)
        parts.append(ch.loc[m])
    df = pd.concat(parts, ignore_index=True)
    return df, {'seed': seed, 'fzp': str(fzp), 'fzp_bytes': fzp.stat().st_size, 'rows_in': n, 'kept': int(len(df))}


def events(df, st, chain, feeders):
    """{o: (off event times array, through event times array)}"""
    import numpy as np
    import pandas as pd
    df = df.sort_values(['NO', 'SIMSEC'], kind='mergesort')
    is_chain = df['LINK'].isin(list(chain))
    cp = np.where(is_chain, df['LINK'].map(chain).fillna(0.0).to_numpy() + df['POS'].to_numpy(), np.nan)
    land = df['LINK'].map(feeders).to_numpy(dtype=float)        # NaN when not a feeder frame
    out = {}
    for o, s in st.items():
        offm = (df['LINK'] == s['off_link']) & (df['POS'] >= s['off_pos'])
        off_t = df.loc[offm].groupby('NO')['SIMSEC'].min().to_numpy()
        sc = chain[s['thr_link']] + s['thr_pos']
        up = (is_chain.to_numpy() & (cp < sc)) | (~np.isnan(land) & (land < sc))
        beyond = is_chain.to_numpy() & (cp >= sc)
        d = pd.DataFrame({'NO': df['NO'].to_numpy(), 't': df['SIMSEC'].to_numpy(), 'up': up, 'beyond': beyond})
        first_up = d[d['up']].groupby('NO')['t'].min()
        b = d[d['beyond']].join(first_up.rename('t_up'), on='NO')
        b = b[b['t'] > b['t_up']]
        thr_t = b.groupby('NO')['t'].min().to_numpy()
        out[o] = {'off': np.sort(off_t), 'thr': np.sort(thr_t), 'station_chain_m': sc}
    return out


def window_counts(ev):
    """{o: {w: [off, elig]}} under w = floor((t - 0.1) / 150)."""
    res = {}
    for o, e in ev.items():
        cnt = {}
        for kind, ts in (('off', e['off']), ('thr', e['thr'])):
            for t in ts:
                w = int(math.floor((float(t) - 0.1) / 150.0))
                row = cnt.setdefault(w, [0, 0])
                if kind == 'off':
                    row[0] += 1
                row[1] += 1
        res[o] = cnt
    return res


def seed_window_counts(seed):
    """The E_W window counts of one seed's v3c3 NC FZP (the harness R11 VISSIM side) and the input record."""
    st = stations()
    chain, feeders, _gsha = geometry()
    keep = set(chain) | set(feeders) | {s['off_link'] for s in st.values()} | {s['thr_link'] for s in st.values()}
    df, meta = load(int(seed), keep, chain)
    return window_counts(events(df, st, chain, feeders)), meta


def ratio(off, elig):
    return off / elig if elig else 0.0


def pooled(cnt, ws):
    off = sum(cnt.get(w, [0, 0])[0] for w in ws)
    elig = sum(cnt.get(w, [0, 0])[1] for w in ws)
    return off, elig


def prior_table(cnts):
    """cnts = list of {w: [off, elig]} (one per prior seed).  s_prior(j), all-time value, n0 (numpy.median)."""
    import numpy as np
    tab, allo, alle = {}, 0, 0
    for c in cnts:
        for w, (a, b) in c.items():
            allo += a
            alle += b
    all_v = ratio(allo, alle)
    for j in range(10):
        o_ = e_ = 0
        for c in cnts:
            o2, e2 = pooled(c, range(6 * j, 6 * j + 6))
            o_ += o2
            e_ += e2
        tab[str(j)] = {'off': o_, 'elig': e_, 's': (o_ / e_) if e_ else all_v, 'fallback_all': e_ == 0}
    wl = []
    for c in cnts:
        for w in range(6, 60):                       # window ends 1050 .. 9000 = (900, 9000]
            wl.append(c.get(w, [0, 0])[1])
    n0 = float(np.median(np.asarray(wl, dtype=float)))
    return {'s_prior': tab, 'all': all_v, 'all_off': allo, 'all_elig': alle, 'n0': n0, 'n_windows': len(wl)}


def forecast(c, cnt, T, prior):
    w0 = T // 150 - 1
    if c == 'C0':
        return ratio(*pooled(cnt, [w0]))
    if c in ('C1', 'C2', 'C4'):
        k = {'C1': 3, 'C2': 6, 'C4': w0 + 1}[c]
        ws = [w0 - i for i in range(k) if w0 - i >= 0]
        return ratio(*pooled(cnt, ws))
    if c == 'C3':
        off0, n = pooled(cnt, [w0])
        s150 = ratio(off0, n)
        j = min(9, T // 900)
        n0 = prior['n0']
        if n + n0 == 0:
            return s150
        return (n * s150 + n0 * prior['s_prior'][str(j)]['s']) / (n + n0)
    raise ValueError(c)


def realized(cnt, T, H):
    end = min(T + H, 9000)
    ws = [w for w in range(T // 150, end // 150)]      # windows ending in (T, end]
    off, elig = pooled(cnt, ws)
    return (off / elig) if elig else None


def fold_table(cnt_eval, prior):
    """{c: {o: {'pairs': n, 'mean_err': x, 'by_H': {H: mean}}}, 'L': {c: L}}"""
    tab, L = {}, {}
    for c in ORDER:
        tab[c] = {}
        per_exit = []
        for o in EW:
            errs, byH = [], {H: [] for H in HS}
            for T in TS:
                sh = forecast(c, cnt_eval[o], T, prior[o] if prior else None)
                for H in HS:
                    sr = realized(cnt_eval[o], T, H)
                    if sr is None:
                        continue
                    e = abs(sh - sr)
                    errs.append(e)
                    byH[H].append(e)
            if not errs:
                raise SystemExit(f'K9_EVIDENCE_STOP f17b: exit {o} has no (T, H) pair left (candidate {c})')
            m = sum(errs) / len(errs)
            tab[c][o] = {'pairs': len(errs), 'mean_err': m,
                         'by_H': {str(H): (sum(v) / len(v) if v else None) for H, v in byH.items()}}
            per_exit.append(m)
        L[c] = sum(per_exit) / len(EW)
    return tab, L


def select(log=print):
    """The P0-3 selection document (the fields of the probe's p0/f17b_selection.json; JSON-normalised)."""
    st = stations()
    chain, feeders, gsha = geometry()
    keep = set(chain) | set(feeders) | {s['off_link'] for s in st.values()} | {s['thr_link'] for s in st.values()}
    cnts, inputs, evs = {}, [], {}
    for seed in SEEDS:
        df, meta = load(seed, keep, chain)
        ev = events(df, st, chain, feeders)
        cnts[seed] = window_counts(ev)
        evs[seed] = {o: {'off_events': int(len(e['off'])), 'thr_events': int(len(e['thr'])),
                         'station_chain_m': e['station_chain_m']} for o, e in ev.items()}
        inputs.append(meta)
        log('f17b seed', seed, meta['kept'])
    priors = {seed: {o: prior_table([cnts[seed][o]]) for o in EW} for seed in SEEDS}
    pooled_prior = {o: prior_table([cnts[s][o] for s in SEEDS]) for o in EW}
    folds = {}
    for name, ev_seed, pr_seed in (('A', 53, 41), ('B', 41, 53)):
        tab, L = fold_table(cnts[ev_seed], priors[pr_seed])
        folds[name] = {'eval_seed': ev_seed, 'prior_seed': pr_seed, 'table': tab, 'L': L,
                       'rank1': min(L, key=lambda c: (L[c], ORDER.index(c)))}
    Lc = {c: (folds['A']['L'][c] + folds['B']['L'][c]) / 2.0 for c in ORDER}
    allowed = [c for c in ORDER if c in ALLOWED]
    Lstar = min(Lc[c] for c in allowed)
    selected = next(c for c in allowed if Lc[c] <= Lstar + MARGIN)
    runtime = {'candidate': selected, 'exits': list(EW), 'window_sec': 150, 'decision_interval_sec': 150,
               'definition': DEFINITION[selected]}
    if selected == 'C3':
        runtime['prior'] = {o: {'s_prior': {j: r['s'] for j, r in pooled_prior[o]['s_prior'].items()},
                                'all': pooled_prior[o]['all'], 'n0': pooled_prior[o]['n0']} for o in EW}
        runtime['prior_seeds'] = list(SEEDS)
    doc = {'schema': 'k91-p0-3-f17b-selection/v1', 'rule': 'k9/f17b_select.py docstring (amendment 19 r2 2.3)',
           'detector_table': {'path': str(DET), 'sha256': DET_SHA, 'blob_7e079efb': DET_BLOB},
           'geometry': {'path': str(GEOM), 'sha256': gsha, 'chain_FW_W': chain, 'feeders_FW_W': feeders},
           'stations': st, 'inputs': inputs, 'events': evs, 'decisions_T': TS, 'H': list(HS),
           'window_counts': {str(s): {o: {str(w): v for w, v in sorted(c.items())} for o, c in cnts[s].items()}
                             for s in SEEDS},
           'priors_single': {str(s): priors[s] for s in SEEDS}, 'prior_pooled': pooled_prior,
           'folds': folds, 'L': Lc, 'L_star': Lstar, 'margin': MARGIN, 'allowed': allowed, 'order': list(ORDER),
           'selected': selected, 'question_C0': selected == 'C0', 'runtime_values': runtime}
    return json.loads(json.dumps(doc, default=float))


# The fields of a selection document that carry the rule's result (meta -- script sha, file paths, rule text -- excluded)
RESULT_FIELDS = ('stations', 'events', 'decisions_T', 'H', 'window_counts', 'priors_single', 'prior_pooled', 'folds',
                 'L', 'L_star', 'margin', 'allowed', 'order', 'selected', 'question_C0', 'runtime_values')


def result_of(doc):
    out = {k: doc.get(k) for k in RESULT_FIELDS}
    out['detector_sha256'] = (doc.get('detector_table') or {}).get('sha256')
    g = doc.get('geometry') or {}
    out['geometry_chain'] = g.get('chain_FW_W')
    out['geometry_feeders'] = g.get('feeders_FW_W')
    out['inputs'] = [{k: r.get(k) for k in ('seed', 'fzp_bytes', 'rows_in', 'kept')} for r in doc.get('inputs') or []]
    return out
