"""F1 a1: SC1001 EB stop line (link 127 heads @621.46-621.67) facts from v3c2 fit-seed FZP (5 s frames). READ-ONLY.

DECLARATION (fixed before any number below was computed; this docstring is hashed into the output):
 Signal clock: SC1001 prog 1 cycle 150 s, program offset 75 s -> cycle phase c = (t - 75) mod 150.
   Two green definitions are carried side by side:
   D45 (repo parser plant/src/vissim_strict/signal_program.py: fixed amber placed BEFORE the red command):
       SG2 EBT green [0,45) amber [45,48); SG5 EBL green [48,72) amber [72,75)   (= plant p3 45 s / p4 24 s)
   D48 (V_VISSIM reading: red command time = green end): SG2 green [0,48); SG5 green [48,75)
   Discrimination test (T-G): crossings per cycle per second in phase bins [40,45) [45,48) [48,51) for SG2 and
   [67,72) [72,75) [75,78) for SG5, plus the share of frames at c=45.1 / 70.1 / 75.1 in which a vehicle within 60 m
   upstream of the head in the group's lanes has InteractTargType 'Signal head'.
 Crossing: consecutive frames (5 s) with chain position x<621.6 on 127 then x>=621.6 (127 or downstream connector/link,
   chain = 127 pos | 627.392+pos on 10118 | 627.429+pos on 10368 | 622.276+pos on 10695 | +connector length on 30/39/38);
   time by linear interpolation; lane = 127 lane of the last pre-crossing frame (1-2 -> SG2, 3 -> SG5);
   movement by first downstream element (10118/30 E, 10368/39 S, 10695/38 N).
 Origin: vehicle ever on 10491 -> OFF_W; ever on 10481 -> OFF_E; else ever on 129/10778/32 -> URB; else X.
 Estimator E1 (saturation flow, per lane, feasible with 5 s frames):
   cycle k of group G starts at the group's green start; Q0 = vehicles with speed<5 km/h in G's lanes on link 127 at the
   frame nearest the green start (SG2: c=0.1, SG5: c=45.1, 2.9 s before its green); N = crossings of G's heads with
   interpolated time in [green start, green start+150).  Saturated cycle: Q0 >= max(theta_G, N + n_G),
   theta_G = n_G*1800*g45_G/3600 (SG2 45, SG5 12).  s_G(g) = 3600*sum N / (n_G*sum g) over saturated cycles,
   g in {D45: 45/24, D48: 48/27}; cycles fully inside [900, 8850) s; pooled 5 seeds, per seed, leave-one-seed-out.
   Fallback if < 10 pooled saturated cycles: drop the N+n_G term; if still < 10: not identifiable, report table only.
 E2 (descriptive only): crossings in [green start+10, green end D45) / (n_G * (g45-10)) on E1-saturated cycles.
 Spillback (frame indicators, 30 s windows with >= 3 of 6 positive frames = event window):
   FW_W: a vehicle on 10491 with pos<=30 & v<15, or on link 26 lane 1 pos in [3550,3651] with route 1132-2 & v<15.
   FW_E: a vehicle on 10481 with pos<=30 & v<15, or on link 2 lane 1 pos in [3950,4092.3] with route 1131-2 & v<15.
   Also the check's definition (30 s mean speed of 10491 vehicles < 30 km/h) for comparability.
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
OFFSET, CYC = 75.0, 150.0
DECL_SHA = hashlib.sha256(__doc__.encode()).hexdigest()[:16]


def phase(t):
    return np.mod(np.asarray(t) - OFFSET, CYC)


def crossings(df):
    eb = df[df.LINK.isin(OFF.keys())].copy()
    eb = eb[~((eb.LINK.isin([30, 38, 39])) & (eb.POS > 119.9))]
    eb['X'] = eb.POS + eb.LINK.map(OFF)
    eb = eb.sort_values(['NO', 'SIMSEC'])
    a = eb.iloc[:-1].reset_index(drop=True)
    b = eb.iloc[1:].reset_index(drop=True)
    m = (a.NO.values == b.NO.values) & (a.LINK.values == 127) & (a.X.values < H) & (b.X.values >= H) & \
        (np.abs(b.SIMSEC.values - a.SIMSEC.values - 5.0) < 1e-6)
    A = a[m]; Bm = b[m]
    t = A.SIMSEC.values + 5.0 * (H - A.X.values) / (Bm.X.values - A.X.values)
    out = pd.DataFrame({'NO': A.NO.values, 't': t, 'ta': A.SIMSEC.values, 'lane': A.LANE.values,
                        'v_a': A.SPEED.values, 'nextlink': Bm.LINK.values})
    # movement: first downstream element seen at/after crossing
    down = eb[eb.LINK.isin(MOVE.keys())].groupby('NO').LINK.first()
    out['mv'] = out.NO.map(down).map(MOVE).fillna('?')
    # vehicles whose last 127 frame is <H and never seen downstream (left extracted set) -> count separately
    last127 = eb[eb.LINK == 127].groupby('NO').X.max()
    lost = last127[(last127 < H) & ~last127.index.isin(out.NO) & ~last127.index.isin(down.index)]
    out = out.drop_duplicates('NO', keep='first')
    return out, len(lost)


def origins(df):
    s = {}
    for no in df.loc[df.LINK == 10491, 'NO'].unique(): s[no] = 'OFF_W'
    for no in df.loc[df.LINK == 10481, 'NO'].unique(): s.setdefault(no, 'OFF_E')
    for no in df.loc[df.LINK.isin([129, 10778, 32]), 'NO'].unique(): s.setdefault(no, 'URB')
    return s


def windows_events(flag_by_frame, frames, t0=900.0, t1=9000.0):
    f = pd.Series(flag_by_frame, index=frames).astype(int)
    w = ((f.index - t0) // 30).astype(int)
    sel = (f.index >= t0) & (f.index < t1)
    g = f[sel].groupby(w[sel]).sum()
    ev = (g >= 3)
    starts = list((g.index[ev] * 30 + t0).astype(float))
    # episodes: runs allowing gap <= 1 window
    eps, cur = [], None
    for k in g.index[ev]:
        if cur and k - cur[1] <= 2:
            cur[1] = k
        else:
            if cur: eps.append(cur)
            cur = [k, k]
    if cur: eps.append(cur)
    eps = [(t0 + a * 30, t0 + (b + 1) * 30) for a, b in eps]
    pk = (g.index * 30 + t0 >= 1800) & (g.index * 30 + t0 < 7200)
    return dict(frac_all=float(ev.mean()), frac_peak=float(ev[pk].mean()), n_event_windows=int(ev.sum()),
                first=starts[0] if starts else None, episodes=[(float(a), float(b)) for a, b in eps],
                total_event_s=int(ev.sum() * 30))


res = dict(declaration_sha16=DECL_SHA, seeds={})
pooled_cyc = []
for seed in SEEDS:
    df = pd.read_parquet(f'{DATA}/e_s{seed}_v1.parquet')
    frames = np.array(sorted(df.SIMSEC.unique()))
    org = origins(df)
    cx, n_lost = crossings(df)
    cx['org'] = cx.NO.map(org).fillna('X')
    cx['ph'] = phase(cx.t)
    cx['sg'] = np.where(cx.lane == 3, 'SG5', 'SG2')
    R = dict(n_cross=int(len(cx)), n_lost_no_downstream=int(n_lost),
             org_counts=cx.org.value_counts().to_dict(),
             lane_by_move=cx.groupby(['mv', 'lane']).size().rename(lambda x: str(x)).to_dict() if False else
             {f'{a}|{b}': int(c) for (a, b), c in cx.groupby(['mv', 'lane']).size().items()})
    # ---- T-G green definition test (cycles fully inside 1800-7200, all crossings)
    pk = cx[(cx.t >= 1800) & (cx.t < 7200)]
    ncyc = 36.0
    tg = {}
    for sg, bins in (('SG2', [(35, 40), (40, 45), (45, 48), (48, 51), (51, 55), (55, 60)]),
                     ('SG5', [(62, 67), (67, 72), (72, 75), (75, 78), (78, 82), (82, 87)])):
        d = pk[pk.sg == sg]
        tg[sg] = {f'{a}-{b}': float(((d.ph >= a) & (d.ph < b)).sum() / ncyc / (b - a)) for a, b in bins}
        tg[sg]['red_crossings_per_cycle'] = float(((d.ph >= (GREEN[sg]['g0'] + 30) % 150) & (d.ph < (GREEN[sg]['g0'] + 140) % 150)).sum() / ncyc) if sg == 'SG2' else \
            float(((d.ph >= 85) & (d.ph < 145)).sum() / ncyc)
    # interaction with signal head at frames phase 40.1 45.1 50.1 (SG2) / 70.1 75.1 (SG5)
    l127 = df[df.LINK == 127]
    sh = {}
    for sg, phs in (('SG2', (40.1, 45.1, 50.1)), ('SG5', (65.1, 70.1, 75.1, 80.1))):
        lanes = GREEN[sg]['lanes']
        for p in phs:
            fr = frames[(np.abs(phase(frames) - p) < 0.01) & (frames >= 1800) & (frames < 7200)]
            x = l127[l127.SIMSEC.isin(fr) & l127.LANE.isin(lanes) & (l127.POS > H - 60) & (l127.POS < H)]
            hit = x[x.INTERACTTARGTYPE.astype(str) == 'Signal head'].groupby('SIMSEC').size()
            sh[f'{sg}@{p}'] = float(len(hit) / max(1, len(fr)))
    tg['signal_head_target_frame_share'] = sh
    R['green_test'] = tg
    # ---- E1 cycles
    stopped = l127[l127.SPEED < 5]
    rows = []
    for sg, G in GREEN.items():
        lanes = G['lanes']; nG = len(lanes)
        cG = cx[cx.lane.isin(lanes)]
        stG = stopped[stopped.LANE.isin(lanes)].groupby('SIMSEC').size()
        k0 = int(np.ceil((900 - OFFSET - G['g0']) / CYC))
        while True:
            gs = OFFSET + G['g0'] + CYC * k0
            if gs + CYC > 8850: break
            if gs >= 900:
                fq = gs - G['g0'] + G['q0_phase'] if sg == 'SG2' else gs - 2.9
                fq = frames[np.argmin(np.abs(frames - fq))]
                Q0 = int(stG.get(fq, 0))
                inw = cG[(cG.t >= gs) & (cG.t < gs + CYC)]
                N = int(len(inw))
                post = inw[(inw.t >= gs + 10) & (inw.t < gs + G['g45'])]
                byo = inw.org.value_counts().to_dict()
                rows.append(dict(seed=seed, sg=sg, gs=gs, Q0=Q0, N=N, N_post10=int(len(post)),
                                 N_l1=int((inw.lane == 1).sum()), N_l2=int((inw.lane == 2).sum()),
                                 OFF_W=int(byo.get('OFF_W', 0)), OFF_E=int(byo.get('OFF_E', 0)), URB=int(byo.get('URB', 0)),
                                 theta=G['theta'], nG=nG))
            k0 += 1
    cyc = pd.DataFrame(rows)
    pooled_cyc.append(cyc)
    # ---- discharge by origin & movement, 900-9000 and peak
    def rate(d, t0, t1):
        return {f'{o}|{m}': float(c * 3600.0 / (t1 - t0)) for (o, m), c in d[(d.t >= t0) & (d.t < t1)].groupby(['org', 'mv']).size().items()}
    R['discharge_vph_900_9000'] = rate(cx, 900, 9000)
    R['discharge_vph_1800_7200'] = rate(cx, 1800, 7200)
    R['total_vph_900_9000'] = float(((cx.t >= 900) & (cx.t < 9000)).sum() * 3600 / 8100)
    R['total_vph_by_sg_900_9000'] = {sg: float(((cx.t >= 900) & (cx.t < 9000) & (cx.sg == sg)).sum() * 3600 / 8100) for sg in ('SG2', 'SG5')}
    # ---- storage counts per frame (1800-7200)
    pkf = frames[(frames >= 1800) & (frames < 7200)]
    def cnt(mask):
        s = df[mask].groupby('SIMSEC').size().reindex(pkf, fill_value=0)
        return dict(p50=float(s.median()), p95=float(s.quantile(.95)), max=int(s.max()), mean=float(s.mean()))
    D = df[df.SIMSEC.isin(pkf)]
    st = {}
    st['10491'] = cnt((df.LINK == 10491) & df.SIMSEC.isin(pkf))
    st['10481'] = cnt((df.LINK == 10481) & df.SIMSEC.isin(pkf))
    st['129_all'] = cnt((df.LINK == 129) & df.SIMSEC.isin(pkf))
    st['129_seg239_302'] = cnt((df.LINK == 129) & (df.POS >= 239.4) & df.SIMSEC.isin(pkf))
    st['127_all'] = cnt((df.LINK == 127) & df.SIMSEC.isin(pkf))
    st['127_lanes12'] = cnt((df.LINK == 127) & df.LANE.isin([1, 2]) & df.SIMSEC.isin(pkf))
    st['127_lane3'] = cnt((df.LINK == 127) & (df.LANE == 3) & df.SIMSEC.isin(pkf))
    # jam spacing: consecutive stopped vehicles in same lane on 127
    sp = []
    s127 = D[(D.LINK == 127) & (D.SPEED < 2)].sort_values(['SIMSEC', 'LANE', 'POS'])
    for (_, _), g in s127.groupby(['SIMSEC', 'LANE']):
        d = np.diff(g.POS.values)
        sp.extend(d[(d > 0) & (d < 15)].tolist())
    st['jam_spacing_m_127'] = dict(median=float(np.median(sp)), p25=float(np.percentile(sp, 25)), p75=float(np.percentile(sp, 75)), n=len(sp))
    sp = []
    s491 = D[(D.LINK == 10491) & (D.SPEED < 2)].sort_values(['SIMSEC', 'POS'])
    for _, g in s491.groupby('SIMSEC'):
        d = np.diff(g.POS.values)
        sp.extend(d[(d > 0) & (d < 15)].tolist())
    st['jam_spacing_m_10491'] = dict(median=float(np.median(sp)) if sp else None, n=len(sp))
    # by origin on W links at frames 150k+0.1
    snap = frames[(np.abs(np.mod(frames, 150.0) - 0.1) < 0.01) & (frames >= 900) & (frames <= 8850)]
    S = df[df.SIMSEC.isin(snap)].copy(); S['org'] = S.NO.map(org).fillna('X')
    tab = S.groupby(['SIMSEC', 'LINK', 'org']).size().unstack(['LINK', 'org'], fill_value=0)
    def col(link, o):
        return tab[(link, o)] if (link, o) in tab.columns else pd.Series(0, index=tab.index)
    u8 = dict(conn_10491=float(col(10491, 'OFF_W').mean()), conn_10481=float(col(10481, 'OFF_E').mean()),
              W129_OFF_W=float(col(129, 'OFF_W').mean()), W127_OFF_W=float(col(127, 'OFF_W').mean()),
              W127_OFF_E=float(col(127, 'OFF_E').mean()), W127_URB=float(col(127, 'URB').mean()), W129_URB=float(col(129, 'URB').mean()),
              n_snap=int(len(tab)))
    u8['offramp_share_of_129_127'] = (u8['W129_OFF_W'] + u8['W127_OFF_W'] + u8['W127_OFF_E']) / max(1e-9, u8['W129_OFF_W'] + u8['W127_OFF_W'] + u8['W127_OFF_E'] + u8['W127_URB'] + u8['W129_URB'])
    st['u8_snapshot_means'] = u8
    # dwell: connector vs W links for crossed off-ramp vehicles
    first = df.groupby(['NO', 'LINK']).SIMSEC.agg(['min', 'max']).reset_index()
    dw = {}
    for o, conn in (('OFF_W', 10491), ('OFF_E', 10481)):
        ids = cx[(cx.org == o) & (cx.t >= 1800) & (cx.t < 7200)].NO.values
        fc = first[(first.LINK == conn) & first.NO.isin(ids)].set_index('NO')
        fw = first[(first.LINK.isin([129, 127])) & first.NO.isin(ids)].groupby('NO')['min'].min()
        tcross = cx.set_index('NO').t
        conn_dw = (fw - fc['min']).dropna()
        w_dw = (tcross.reindex(fw.index) - fw).dropna()
        dw[o] = dict(conn_median=float(conn_dw.median()), conn_p90=float(conn_dw.quantile(.9)), W_median=float(w_dw.median()),
                     W_mean=float(w_dw.mean()), W_p90=float(w_dw.quantile(.9)), n=int(len(w_dw)))
    ids = cx[(cx.org == 'URB') & (cx.t >= 1800) & (cx.t < 7200)].NO.values
    f127 = first[(first.LINK == 127) & first.NO.isin(ids)].set_index('NO')['min']
    dw['URB_on127'] = dict(median=float((cx.set_index('NO').t.reindex(f127.index) - f127).median()))
    st['dwell_s'] = dw
    R['storage'] = st
    # ---- queue extent on 127 & spill indicators
    st127 = df[(df.LINK == 127) & (df.SPEED < 5)].groupby('SIMSEC').POS.min().reindex(frames)
    qlen = (H - st127).fillna(0.0)
    R['q127_extent_frac_1800_7200'] = {f'>={x}m': float((qlen[(frames >= 1800) & (frames < 7200)] >= x).mean()) for x in (300, 392.7, 411.3, 500, 600)}
    spW = df[((df.LINK == 10491) & (df.POS <= 30) & (df.SPEED < 15)) |
             ((df.LINK == 26) & (df.LANE == 1) & (df.POS >= 3550) & (df.POS <= 3651) & (df.ROUTDECNO == 1132) & (df.ROUTENO == 2) & (df.SPEED < 15))].SIMSEC.unique()
    spE = df[((df.LINK == 10481) & (df.POS <= 30) & (df.SPEED < 15)) |
             ((df.LINK == 2) & (df.LANE == 1) & (df.POS >= 3950) & (df.POS <= 4092.3) & (df.ROUTDECNO == 1131) & (df.ROUTENO == 2) & (df.SPEED < 15))].SIMSEC.unique()
    R['spill_FW_W'] = windows_events(np.isin(frames, spW), frames)
    R['spill_FW_E'] = windows_events(np.isin(frames, spE), frames)
    m491 = df[df.LINK == 10491].groupby('SIMSEC').SPEED.mean().reindex(frames)
    w = ((frames - 900) // 30).astype(int)
    ser = pd.Series(m491.values, index=frames)
    sel = (frames >= 1800) & (frames < 7200)
    R['check_def_10491_mean_v_lt30_frac_peak'] = float((ser[sel].groupby(w[sel]).mean() < 30).mean())
    blk129 = df[(df.LINK == 129) & (df.POS >= 239.4) & (df.SPEED < 5)].SIMSEC.unique()
    R['blocked_129_tail_frame_frac_peak'] = float(np.isin(frames[sel], blk129).mean())
    trap10490 = df[(df.LINK == 129) & (df.ROUTDECNO == 1136) & (df.ROUTENO == 3) & (df.SPEED < 5)].groupby('SIMSEC').size().reindex(frames[sel], fill_value=0)
    R['stopped_10490_route_on129_mean_peak'] = float(trap10490.mean())
    blk10481 = df[(df.LINK == 10481) & (df.POS >= 424) & (df.SPEED < 5)].SIMSEC.unique()
    R['blocked_10481_end_frame_frac_peak'] = float(np.isin(frames[sel], blk10481).mean())
    # ---- lane-3 access at SG5 green start (frame c=45.1)
    fr45 = frames[(np.abs(phase(frames) - 45.1) < 0.01) & (frames >= 1800) & (frames < 7200)]
    x = l127[l127.SIMSEC.isin(fr45)]
    nN12 = x[(x.LANE.isin([1, 2])) & (x.ROUTDECNO == 1117) & (x.ROUTENO == 2)].groupby('SIMSEC').size().reindex(fr45, fill_value=0)
    nN3 = x[(x.LANE == 3) & (x.ROUTDECNO == 1117) & (x.ROUTENO == 2)].groupby('SIMSEC').size().reindex(fr45, fill_value=0)
    nst3 = x[(x.LANE == 3) & (x.SPEED < 5)].groupby('SIMSEC').size().reindex(fr45, fill_value=0)
    nU = x[(x.POS < 228.9)].groupby('SIMSEC').size().reindex(fr45, fill_value=0)
    R['lane3_access_at_SG5_start'] = dict(N_in_lanes12_mean=float(nN12.mean()), N_in_lane3_mean=float(nN3.mean()),
                                          stopped_lane3_mean=float(nst3.mean()), stopped_lane3_ge12_frac=float((nst3 >= 12).mean()),
                                          veh_upstream_of_1117_mean=float(nU.mean()))
    res['seeds'][seed] = R
    print(seed, 'cross', len(cx), 'lost', n_lost, json.dumps(R['total_vph_by_sg_900_9000']), flush=True)

C = pd.concat(pooled_cyc, ignore_index=True)
C.to_csv(f'{B}/out/a1_v1rule_cycles_v3c3.csv', index=False)
E1 = {}
for sg in ('SG2', 'SG5'):
    G = GREEN[sg]
    d = C[C.sg == sg]
    sat = d[(d.Q0 >= np.maximum(d.theta, d.N + d.nG))]
    rule = 'Q0>=max(theta,N+nG)'
    if len(sat) < 10:
        sat = d[d.Q0 >= d.theta]; rule = 'fallback Q0>=theta'
    out = dict(rule=rule, n_cycles=int(len(d)), n_sat=int(len(sat)), n_sat_by_seed=sat.seed.value_counts().sort_index().to_dict())
    if len(sat) >= 10:
        nG = G['nG'] if 'nG' in G else len(G['lanes'])
        for gname in ('g45', 'g48'):
            g = G[gname]
            out[f's_{gname}'] = float(3600 * sat.N.sum() / (nG * g * len(sat)))
            out[f's_{gname}_per_seed'] = {int(s): float(3600 * x.N.sum() / (nG * g * len(x))) for s, x in sat.groupby('seed')}
            loso = [float(3600 * sat[sat.seed != s].N.sum() / (nG * g * len(sat[sat.seed != s]))) for s in SEEDS if len(sat[sat.seed != s])]
            out[f's_{gname}_loso_range'] = [min(loso), max(loso)]
        out['N_per_cycle_mean'] = float(sat.N.mean())
        out['E2_post10_rate_per_lane'] = float(3600 * sat.N_post10.sum() / (nG * (G['g45'] - 10) * len(sat)))
        if sg == 'SG2':
            out['lane1_lane2_per_cycle'] = [float(sat.N_l1.mean()), float(sat.N_l2.mean())]
            out['s_g45_lane1'] = float(3600 * sat.N_l1.sum() / (45 * len(sat)))
            out['s_g45_lane2'] = float(3600 * sat.N_l2.sum() / (45 * len(sat)))
        tot = sat[['OFF_W', 'OFF_E', 'URB']].sum()
        out['origin_share_sat'] = (tot / tot.sum()).round(4).to_dict()
    # descriptive table Q0 bins
    d = d.assign(Qb=pd.cut(d.Q0, [-1, 0, 5, 11, 20, 44, 80, 1000]))
    out['by_Q0_bin'] = {str(k): dict(n=int(len(x)), N_mean=float(x.N.mean()) if len(x) else None) for k, x in d.groupby('Qb', observed=False)}
    out['all_cycles_N_mean'] = float(d.N.mean())
    E1[sg] = out
res['E1'] = E1
json.dump(res, open(f'{B}/out/a1_v1rule_v3c3.json', 'w'), indent=1, default=float)
print(json.dumps(E1, indent=1, default=float)[:4000])
