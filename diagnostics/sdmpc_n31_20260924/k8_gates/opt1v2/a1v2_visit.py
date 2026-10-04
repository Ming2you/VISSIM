"""K8 OPT1 v2 a1v2: VISIT-BASED recount of the SC1001 EB stop line (link 127) on the v3c3 NC fit-seed FZPs. READ-ONLY.

DECLARATION (fixed before any number below was computed; this docstring is hashed into the output as declaration_sha16):
 Input: x2 ext parquets e_s{31,41,43,47,53}_ext.parquet (v3c3 NC fit FZPs; GB-1 payload == v3c2). s37/_rm/59/61/67 unused.
 Signal clock, green definition, chain position X, head line H = 621.6, cycle windows, theta and the E1 group estimator are
   IDENTICAL to sc1001eb/tools/a1_stopline.py (declaration sha16 77304deded2de68a), except the three changes below.
 Change 1 (visits, not vehicles). Frames of one vehicle NO sorted by SIMSEC are cut into VISITS whenever two consecutive
   frames of that NO in the extracted set are more than 5.0 s apart (the vehicle left the extracted region). Every
   head crossing (frame pair inside one visit, 5 s apart, a on 127 with X<H, b on 127/10118/10368/10695/30/38/39 with
   X>=H) is a separate event. NO de-duplication.
 Change 2 (origin per visit). Origin of a crossing = the link class of the FIRST frame of its visit:
   {26,10491} -> OFF_W, {2,10481} -> OFF_E, {32,10778} -> URB, {129} -> X129, {10777,127} -> X127 (visit already on the
   approach when observation of the region began, e.g. at simulation start). The old vehicle-level rule (ever on 10491 /
   10481 / 129-10778-32 over the whole run) is computed on the same crossing events for comparison only.
 Change 3 (movement per visit). Movement = first element of {10118,30:E; 10368,39:S; 10695,38:N} seen at or after the
   pre-crossing frame INSIDE THE SAME VISIT; '?' if none.
 Re-entry: crossing number k of a vehicle NO (k>=2 = re-entry crossing). Route state at crossing = ROUTDECNO/ROUTENO of the
   last pre-crossing frame: '1117' (consistency 1117:3=E, 1117:1=S, 1117:2=N reported), 'other:<dec>', 'none' (no route).
   Route at visit entry onto 127 (first 127 frame) reported the same way.
 E1 group (SG2 lanes 1-2, SG5 lane 3): a1_stopline E1 rule unchanged on the visit crossing set.
 E1 lane (new, for lane FIFO): for lane l in {1,2,3} with group G(l) (1,2 -> SG2; 3 -> SG5), same cycle start gs and Q0
   frame as G; Q0_l = vehicles with SPEED<5 km/h on 127 lane l at that frame; N_l = visit crossings with lane l in
   [gs, gs+150); lane-saturated cycle: Q0_l >= max(theta_l, N_l + 1), theta_l = 1800*g45_G/3600 (lanes 1,2: 22.5; lane 3: 12).
   s_l(g) = 3600*sum N_l / (g * n_sat_l), g in {g45_G (45/24), g48_G (48/27)}; cycles fully inside [900, 8850); pooled 5
   seeds, per seed, leave-one-seed-out. Fallback if < 10 pooled lane-saturated cycles: drop the N_l+1 term; if still < 10:
   not identifiable. Also reported: lane split on SG2 GROUP-saturated cycles (the old per-lane numbers).
 Lane use: counts by (movement, lane) over crossings with t in [900, 9000); P(lane | movement), P(lane 1 | E, origin).
 Lane-conditional destination upstream of decision 1117 (127 POS < 228.9): for visits with a crossing and known movement,
   frames on 127 before the crossing with POS < 228.9, by (lane, movement), frame-weighted, also split POS [0,100) and
   [100,228.9); and the lane of the first 127 frame of the visit by movement. Lane-3 first position on 127 for N movers by
   origin (median, p10, p90) and share of N-mover pre-1117 frames in lane 3, by origin.
 Post-head census (B8): at frames SIMSEC = T + 0.1 for T = 150k in [900, 8850] (and flagged for the nine FH grid times
   900,1200,1800,2250,2700,3000,3600,4200,4950): vehicles on 127 with POS >= head position of their lane
   (lane 1 621.666240, lane 2 621.568281, lane 3 621.461547; INPX heads 90030836/35/34), split POS < 627.392 / >= 627.392,
   stopped (< 1 km/h) or not, route 1117:x.
 Observed W+ports pair (B2, batch-2 tr:W+ports physical form): at frames T+0.1 and T+150.1, T = 150k in [900, 8850]:
   W = vehicles on 32 (all POS) + 10778 + 129 + 10777 + 127; ports = 10491 + 10481; also 127 stopped (< 5 km/h, G6-7 obs),
   127 all, 129 tail (POS >= 239.384224), 10491, 10481 separately.
 Nothing is fitted; no threshold is tuned on these numbers.
"""
import ctypes, json, hashlib, sys
import numpy as np, pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import k8common as c  # noqa: E402
_ap = c.parser(__doc__)
_ap.add_argument('--data', help='folder of the x2 parquets e_s<seed>_{v1,ext}.parquet (default <out>/opt1v2/data)')
_args = _ap.parse_args()
c.apply(_args)
ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
B = c.OUT / 'opt1v2'
DATA = Path(_args.data) if _args.data else B / 'data'
(B / 'out').mkdir(parents=True, exist_ok=True)
SEEDS = (31, 41, 43, 47, 53)
H = 621.6
OFF = {127: 0.0, 10118: 627.392, 10368: 627.429, 10695: 622.276,
       30: 627.392 + 135.761 - 1.677, 39: 627.429 + 60.115 - 2.414, 38: 622.276 + 65.094 - 2.244}
MOVE = {10118: 'E', 30: 'E', 10368: 'S', 39: 'S', 10695: 'N', 38: 'N'}
GREEN = {'SG2': dict(lanes=(1, 2), g0=0.0, g45=45.0, g48=48.0, q0_phase=0.1, theta=45),
         'SG5': dict(lanes=(3,), g0=48.0, g45=24.0, g48=27.0, q0_phase=45.1, theta=12)}
LANE_G = {1: 'SG2', 2: 'SG2', 3: 'SG5'}
HEAD = {1: 621.666240433568, 2: 621.5682806829368, 3: 621.461546643362}
D1117 = 228.91967281006077
TAIL129 = 239.38422422843928
OFFSET, CYC = 75.0, 150.0
GRID9 = (900, 1200, 1800, 2250, 2700, 3000, 3600, 4200, 4950)
ROUTE_MV = {3: 'E', 1: 'S', 2: 'N'}
DECL_SHA = hashlib.sha256(__doc__.encode()).hexdigest()[:16]
ORIGIN_OF = {26: 'OFF_W', 10491: 'OFF_W', 2: 'OFF_E', 10481: 'OFF_E', 32: 'URB', 10778: 'URB', 129: 'X129', 10777: 'X127', 127: 'X127'}


def phase(t):
    return np.mod(np.asarray(t) - OFFSET, CYC)


def visits(df):
    df = df.sort_values(['NO', 'SIMSEC'], kind='mergesort').reset_index(drop=True)
    new = (df.NO.values[1:] != df.NO.values[:-1]) | (np.diff(df.SIMSEC.values) > 5.0 + 1e-6)
    vid = np.concatenate([[0], np.cumsum(new)])
    df['VID'] = vid
    first = df.groupby('VID').LINK.first()
    df['VORG'] = df.VID.map(first.map(lambda l: ORIGIN_OF.get(int(l), 'X'))).values
    return df


def crossings(df):
    eb = df[df.LINK.isin(OFF.keys())].copy()
    eb = eb[~((eb.LINK.isin([30, 38, 39])) & (eb.POS > 119.9))]
    eb['X'] = eb.POS + eb.LINK.map(OFF)
    eb = eb.sort_values(['NO', 'SIMSEC'], kind='mergesort').reset_index(drop=True)
    a = eb.iloc[:-1].reset_index(drop=True); b = eb.iloc[1:].reset_index(drop=True)
    m = ((a.NO.values == b.NO.values) & (a.VID.values == b.VID.values) & (a.LINK.values == 127) & (a.X.values < H)
         & (b.X.values >= H) & (np.abs(b.SIMSEC.values - a.SIMSEC.values - 5.0) < 1e-6))
    A = a[m]; Bm = b[m]
    t = A.SIMSEC.values + 5.0 * (H - A.X.values) / (Bm.X.values - A.X.values)
    out = pd.DataFrame({'NO': A.NO.values, 'VID': A.VID.values, 't': t, 'ta': A.SIMSEC.values, 'lane': A.LANE.values.astype(int),
                        'org': A.VORG.values, 'rdec': A.ROUTDECNO.values, 'rno': A.ROUTENO.values})
    dn = eb[eb.LINK.isin(MOVE.keys())][['VID', 'SIMSEC', 'LINK']]
    dn = dn.merge(out[['VID', 'ta']], on='VID')
    dn = dn[dn.SIMSEC >= dn.ta].sort_values(['VID', 'SIMSEC'])
    mv = dn.groupby('VID').LINK.first().map(MOVE)
    out['mv'] = out.VID.map(mv).fillna('?')
    out = out.sort_values(['NO', 't']).reset_index(drop=True)
    out['k'] = out.groupby('NO').cumcount() + 1
    def rc(r):
        if pd.isna(r.rdec):
            return 'none'
        return '1117' if int(r.rdec) == 1117 else 'other:%d' % int(r.rdec)
    out['rcat'] = [rc(r) for r in out.itertuples()]
    out['rmv'] = [ROUTE_MV.get(int(r.rno)) if (not pd.isna(r.rdec) and int(r.rdec) == 1117 and not pd.isna(r.rno)) else None
                  for r in out.itertuples()]
    return out


def old_origins(df):
    s = {}
    for no in df.loc[df.LINK == 10491, 'NO'].unique(): s[no] = 'OFF_W'
    for no in df.loc[df.LINK == 10481, 'NO'].unique(): s.setdefault(no, 'OFF_E')
    for no in df.loc[df.LINK.isin([129, 10778, 32]), 'NO'].unique(): s.setdefault(no, 'URB')
    return s


def est(sat_N_sum, n_sat, g, n_lanes=1):
    return float(3600.0 * sat_N_sum / (n_lanes * g * n_sat)) if n_sat else None


res = dict(declaration_sha16=DECL_SHA, seeds={})
pooled_g, pooled_l = [], []
for seed in SEEDS:
    df = pd.read_parquet(f'{DATA}/e_s{seed}_ext.parquet', columns=['SIMSEC', 'NO', 'LINK', 'LANE', 'POS', 'SPEED', 'ROUTDECNO', 'ROUTENO'])
    df = visits(df)
    frames = np.array(sorted(df.SIMSEC.unique()))
    cx = crossings(df)
    oo = old_origins(df)
    cx['org_old'] = cx.NO.map(oo).fillna('X')
    cx['ph'] = phase(cx.t)
    cx['sg'] = np.where(cx.lane == 3, 'SG5', 'SG2')
    R = {}
    w = cx[(cx.t >= 900) & (cx.t < 9000)]
    R['n_cross_all'] = int(len(cx)); R['n_cross_900_9000'] = int(len(w))
    R['n_vehicles_crossing'] = int(cx.NO.nunique())
    R['n_reentry_cross'] = int((cx.k >= 2).sum()); R['n_reentry_cross_900_9000'] = int((w.k >= 2).sum())
    R['n_vehicles_multi_cross'] = int((cx.groupby('NO').size() >= 2).sum())
    R['reentry_by_origin'] = {str(k): int(v) for k, v in w[w.k >= 2].org.value_counts().items()}
    R['origin_visit_counts'] = {str(k): int(v) for k, v in w.org.value_counts().items()}
    R['origin_old_counts'] = {str(k): int(v) for k, v in w.org_old.value_counts().items()}
    R['origin_visit_vs_old'] = {f'{a}|{b}': int(c) for (a, b), c in w.groupby(['org', 'org_old']).size().items()}
    R['mv_unknown'] = int((w.mv == '?').sum())
    R['route_cat_at_crossing'] = {str(k): int(v) for k, v in w.rcat.value_counts().items()}
    kn = w[w.rmv.notna() & (w.mv != '?')]
    R['route_1117_mv_consistent'] = [int((kn.rmv == kn.mv).sum()), int(len(kn))]
    R['routeless_by_mv'] = {str(k): int(v) for k, v in w[w.rcat == 'none'].mv.value_counts().items()}
    R['routeless_by_origin'] = {str(k): int(v) for k, v in w[w.rcat == 'none'].org.value_counts().items()}
    # route at entry onto 127 (first 127 frame of each crossing visit)
    f127 = df[(df.LINK == 127) & df.VID.isin(w.VID)].sort_values(['VID', 'SIMSEC']).groupby('VID').first()
    ent = f127.ROUTDECNO.map(lambda x: 'none' if pd.isna(x) else str(int(x)))
    R['route_at_127_entry'] = {str(k): int(v) for k, v in ent.value_counts().items()}
    # turn ratios by origin (visit) and old rule
    def turn(d, col):
        out = {}
        for o, x in d[d.mv != '?'].groupby(col):
            vc = x.mv.value_counts(); n = int(vc.sum())
            out[str(o)] = dict(n=n, E=float(vc.get('E', 0) / n), N=float(vc.get('N', 0) / n), S=float(vc.get('S', 0) / n))
        return out
    R['turn_by_origin_visit'] = turn(w, 'org'); R['turn_by_origin_old'] = turn(w, 'org_old')
    vc = w[w.mv != '?'].mv.value_counts(); n = int(vc.sum())
    R['turn_total'] = dict(n=n, E=float(vc.get('E', 0) / n), N=float(vc.get('N', 0) / n), S=float(vc.get('S', 0) / n))
    R['turn_reentry'] = turn(w[w.k >= 2].assign(all='reentry'), 'all')
    R['discharge_vph_900_9000_by_origin'] = {str(k): float(v * 3600 / 8100) for k, v in w.org.value_counts().items()}
    # lane use
    R['lane_by_mv'] = {f'{a}|{b}': int(c) for (a, b), c in w.groupby(['mv', 'lane']).size().items()}
    e = w[w.mv == 'E']
    R['p_lane1_given_E'] = float((e.lane == 1).mean())
    R['p_lane1_given_E_by_origin'] = {str(o): [float((x.lane == 1).mean()), int(len(x))] for o, x in e.groupby('org')}
    R['p_lane_given_mv'] = {m: {int(l): float(c / len(x)) for l, c in x.lane.value_counts().items()} for m, x in w[w.mv != '?'].groupby('mv')}
    # upstream-of-1117 lane/destination table
    cv = w[w.mv != '?'][['VID', 'ta', 'mv', 'org']]
    up = df[(df.LINK == 127) & (df.POS < D1117)].merge(cv, on='VID')
    up = up[up.SIMSEC <= up.ta]
    up['seg'] = np.where(up.POS < 100, '0_100', '100_229')
    R['upstream1117_frames_by_lane_mv'] = {f'{a}|{b}': int(c) for (a, b), c in up.groupby(['LANE', 'mv']).size().items()}
    R['upstream1117_frames_by_seg_lane_mv'] = {f'{s}|{a}|{b}': int(c) for (s, a, b), c in up.groupby(['seg', 'LANE', 'mv']).size().items()}
    first = df[(df.LINK == 127)].merge(cv, on='VID').sort_values(['VID', 'SIMSEC']).groupby('VID').first()
    R['first127_lane_by_mv'] = {f'{a}|{b}': int(c) for (a, b), c in first.groupby(['LANE', 'mv']).size().items()}
    R['first127_lane_by_mv_origin'] = {f'{o}|{a}|{b}': int(c) for (o, a, b), c in first.groupby(['org', 'LANE', 'mv']).size().items()}
    nN = up[up.mv == 'N']
    R['N_upstream_frames_lane3_share_by_origin'] = {str(o): [float((x.LANE == 3).mean()), int(len(x))] for o, x in nN.groupby('org')}
    l3 = df[(df.LINK == 127) & (df.LANE == 3)].merge(cv[cv.mv == 'N'], on='VID')
    l3 = l3[l3.SIMSEC <= l3.ta].sort_values(['VID', 'SIMSEC']).groupby('VID').first()
    R['N_first_lane3_pos_by_origin'] = {str(o): dict(n=int(len(x)), p10=float(x.POS.quantile(.1)), p50=float(x.POS.median()), p90=float(x.POS.quantile(.9)))
                                        for o, x in l3.groupby('org')}
    # travel 127 entry -> crossing for OFF_E by movement (10481 N movers have to reach lane 3 through lanes 1-2)
    tt = first[['SIMSEC', 'mv', 'org']].join(w.set_index('VID').t)
    tt['dt'] = tt.t - tt.SIMSEC
    R['entry127_to_cross_s_by_origin_mv'] = {f'{o}|{m}': dict(n=int(len(x)), p50=float(x.dt.median()), mean=float(x.dt.mean()))
                                             for (o, m), x in tt.groupby(['org', 'mv'])}
    # ---- E1 group + lane
    l127 = df[df.LINK == 127]
    stopped = l127[l127.SPEED < 5]
    rows = []
    for sg, G in GREEN.items():
        k0 = int(np.ceil((900 - OFFSET - G['g0']) / CYC))
        while True:
            gs = OFFSET + G['g0'] + CYC * k0
            if gs + CYC > 8850: break
            if gs >= 900:
                fq = gs - G['g0'] + G['q0_phase'] if sg == 'SG2' else gs - 2.9
                fq = frames[np.argmin(np.abs(frames - fq))]
                st = stopped[stopped.SIMSEC == fq]
                inw = cx[(cx.t >= gs) & (cx.t < gs + CYC) & cx.lane.isin(G['lanes'])]
                byo = inw.org.value_counts().to_dict()
                row = dict(seed=seed, sg=sg, gs=gs, Q0=int(st.LANE.isin(G['lanes']).sum()), N=int(len(inw)), nG=len(G['lanes']),
                           theta=G['theta'], OFF_W=int(byo.get('OFF_W', 0)), OFF_E=int(byo.get('OFF_E', 0)), URB=int(byo.get('URB', 0)),
                           X=int(sum(v for k, v in byo.items() if str(k).startswith('X'))))
                for l in G['lanes']:
                    row[f'Q0_l{l}'] = int((st.LANE == l).sum()); row[f'N_l{l}'] = int((inw.lane == l).sum())
                    il = inw[inw.lane == l]
                    for m in ('E', 'S', 'N'):
                        row[f'N_l{l}_{m}'] = int((il.mv == m).sum())
                    for o in ('OFF_W', 'OFF_E', 'URB'):
                        row[f'N_l{l}_{o}'] = int((il.org == o).sum())
                rows.append(row)
            k0 += 1
    pooled_g.append(pd.DataFrame(rows))
    # ---- post-head census & observed pairs
    snapT = [T for T in range(900, 8851, 150)]
    ph, obs = [], []
    for T in snapT:
        for tt_ in (T, T + 150):
            f = df[np.abs(df.SIMSEC - (tt_ + 0.1)) < 0.01]
            if tt_ == T:
                p = f[(f.LINK == 127)].copy()
                p['headpos'] = p.LANE.map(HEAD)
                p = p[p.POS >= p['headpos']]
                ph.append(dict(T=T, grid9=T in GRID9, n=int(len(p)), n_lt_627392=int((p.POS < 627.392).sum()),
                               n_ge_627392=int((p.POS >= 627.392).sum()), n_stopped=int((p.SPEED < 1.0).sum()),
                               by_lane={int(k): int(v) for k, v in p.LANE.value_counts().items()},
                               route=dict(pd.Series([('none' if pd.isna(r) else str(int(r))) + ':' + ('' if pd.isna(n_) else str(int(n_))) for r, n_ in zip(p.ROUTDECNO, p.ROUTENO)], dtype=object).value_counts().astype(int)) if len(p) else {}))
            row = dict(T=T, at=tt_, W=int(f.LINK.isin([32, 10778, 129, 10777, 127]).sum()), ports=int(f.LINK.isin([10491, 10481]).sum()),
                       l127=int((f.LINK == 127).sum()), l127_stop=int(((f.LINK == 127) & (f.SPEED < 5)).sum()),
                       l129_tail=int(((f.LINK == 129) & (f.POS >= TAIL129)).sum()), c10491=int((f.LINK == 10491).sum()),
                       c10481=int((f.LINK == 10481).sum()), l32=int((f.LINK == 32).sum()), l129=int((f.LINK == 129).sum()))
            obs.append(row)
    R['posthead_census'] = ph
    R['posthead_summary'] = dict(states=len(ph), states_with_any=int(sum(1 for r in ph if r['n'] > 0)), total=int(sum(r['n'] for r in ph)),
                                 max=int(max(r['n'] for r in ph)), grid9_with_any=int(sum(1 for r in ph if r['grid9'] and r['n'] > 0)),
                                 grid9_total=int(sum(r['n'] for r in ph if r['grid9'])),
                                 stopped_total=int(sum(r['n_stopped'] for r in ph)), ge_627392_total=int(sum(r['n_ge_627392'] for r in ph)))
    R['observed_pairs'] = obs
    res['seeds'][seed] = R
    print(seed, 'cross', len(cx), 'reentry', R['n_reentry_cross'], 'posthead', R['posthead_summary'], flush=True)

C = pd.concat(pooled_g, ignore_index=True)
C.to_csv(f'{B}/out/a1v2_cycles.csv', index=False)
E1 = {}
for sg in ('SG2', 'SG5'):
    G = GREEN[sg]; d = C[C.sg == sg]; nG = len(G['lanes'])
    sat = d[d.Q0 >= np.maximum(d.theta, d.N + d.nG)]; rule = 'Q0>=max(theta,N+nG)'
    if len(sat) < 10:
        sat = d[d.Q0 >= d.theta]; rule = 'fallback Q0>=theta'
    o = dict(rule=rule, n_cycles=int(len(d)), n_sat=int(len(sat)), n_sat_by_seed={int(k): int(v) for k, v in sat.seed.value_counts().sort_index().items()})
    for gname in ('g45', 'g48'):
        g = G[gname]
        o[f's_{gname}'] = est(sat.N.sum(), len(sat), g, nG)
        o[f's_{gname}_per_seed'] = {int(s): est(x.N.sum(), len(x), g, nG) for s, x in sat.groupby('seed')}
        lo = [est(sat[sat.seed != s].N.sum(), len(sat[sat.seed != s]), g, nG) for s in SEEDS]
        o[f's_{gname}_loso_range'] = [min(lo), max(lo)]
    tot = sat[['OFF_W', 'OFF_E', 'URB', 'X']].sum()
    o['origin_share_sat'] = {k: float(v / tot.sum()) for k, v in tot.items()}
    o['N_per_cycle_mean_sat'] = float(sat.N.mean())
    if sg == 'SG2':
        for l in (1, 2):
            o[f'grp_sat_s_g45_lane{l}'] = est(sat[f'N_l{l}'].sum(), len(sat), 45.0)
            o[f'grp_sat_lane{l}_mv_share'] = {m: float(sat[f'N_l{l}_{m}'].sum() / max(1, sat[f'N_l{l}'].sum())) for m in ('E', 'S', 'N')}
    E1[sg] = o
E1L = {}
for l in (1, 2, 3):
    sg = LANE_G[l]; G = GREEN[sg]; d = C[C.sg == sg]
    th = 1800.0 * G['g45'] / 3600.0
    sat = d[d[f'Q0_l{l}'] >= np.maximum(th, d[f'N_l{l}'] + 1)]; rule = 'Q0_l>=max(theta_l,N_l+1)'
    if len(sat) < 10:
        sat = d[d[f'Q0_l{l}'] >= th]; rule = 'fallback Q0_l>=theta_l'
    o = dict(rule=rule, theta_l=th, n_cycles=int(len(d)), n_sat=int(len(sat)),
             n_sat_by_seed={int(k): int(v) for k, v in sat.seed.value_counts().sort_index().items()})
    if len(sat) >= 10:
        for gname in ('g45', 'g48'):
            g = G[gname]
            o[f's_{gname}'] = est(sat[f'N_l{l}'].sum(), len(sat), g)
            o[f's_{gname}_per_seed'] = {int(s): est(x[f'N_l{l}'].sum(), len(x), g) for s, x in sat.groupby('seed')}
            lo = [est(sat[sat.seed != s][f'N_l{l}'].sum(), len(sat[sat.seed != s]), g) for s in SEEDS]
            o[f's_{gname}_loso_range'] = [min(lo), max(lo)]
        o['N_per_cycle_mean_sat'] = float(sat[f'N_l{l}'].mean())
        o['mv_share_sat'] = {m: float(sat[f'N_l{l}_{m}'].sum() / max(1, sat[f'N_l{l}'].sum())) for m in ('E', 'S', 'N')}
        o['origin_share_sat'] = {x: float(sat[f'N_l{l}_{x}'].sum() / max(1, sat[f'N_l{l}'].sum())) for x in ('OFF_W', 'OFF_E', 'URB')}
    E1L[f'lane{l}'] = o
res['E1_group'] = E1; res['E1_lane'] = E1L
json.dump(res, open(f'{B}/out/a1v2_visit.json', 'w'), indent=1, default=float)
print(json.dumps({'E1_group': {k: {kk: vv for kk, vv in v.items() if not kk.endswith('per_seed')} for k, v in E1.items()}, 'E1_lane': E1L}, indent=1, default=float)[:6000])
