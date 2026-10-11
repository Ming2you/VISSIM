"""VISSIM-side reference values for the SA gates (read-only; FZP extracts, EO, R-obs3 decision states).

    python -B sa_vissim_ref.py [--root R] [--out O] [--robs D] [--data DIR] [--eo-root DIR] [--dry-run]
        -> <out>/sa/vissim_ref.json  (schema k8-sa-vissim-ref/v1)

Inputs (all read only; sha256 recorded):
  <out>/opt1v2/data/e_s<seed>_ext.parquet    x2 extract: 127/129/10777/10778/10491/10481/10490/10695/32, 26 tail,
                                              30/38/39 heads (opt1v2/x2_extract.py)
  <out>/sa/fzp/s<seed>_frames.parquet         freeway chains, 10479, 31/124 (sa_fzp_frames.py)
  <out>/opt1v2/out/p4_states_grid9_v3c3.json  VISSIM event / non-event classification (14 / 31 / 0)
  R-obs3 decisions_*/state_<T>.json           s31 = NC3 s31 (GB-6): link counts, freeway_segments
  EO s<seed>_v3c2nc/{cells_30s,boundaries_30s}.csv   (v3c2 EO = v3c3 bytes, PREDECL §0)
Definitions (each names its declared source):
  w_ports       counts on 32, 10778, 129, 10777, 127, 10491, 10481 (G-EB-3 (a) observed side, PREDECL §3.2)
  stop127       127 vehicles with speed < 5 km/h (G6-7, u6 analyze_u6 '127_stop')
  wout          31 + 124 counts (G6-6, u6 fzp_row wout_T150)
  ext127        621.6 - min POS of 127 vehicles with SPEED < 5 (a1_stopline q127 extent); first frame >= T + 0.1
                with ext127 >= 500 m (G-EB-6 (c))
  spill windows FW_W: 30 s windows with >= 3 of 6 frames having a 10491 vehicle at POS <= 30 and v < 15, or a link 26
                lane 1 vehicle at POS 3550-3651 with route 1132-2 and v < 15 (F1 §6 declaration)
  eb discharge  127 head crossings of the station 621.6 m between consecutive 5 s frames (a1_stopline crossing rule:
                chain 127 pos | 627.392 + pos on 10118 | 627.429 + pos on 10368 | 622.276 + pos on 10695 | heads of
                30/39/38), per 150 s block (s31); the crossing frame times themselves (eb_crossing_times) for
                the G-EB-5 period cut at 8970.1 s (amendment 5 section 2-5)
  lane3 full    frames with a stopped (< 5 km/h) 127 lane-3 tail at POS < 30 m (s2_lanefull full_l rule), report (N6)
  10491 flow    EO OR_D_W_signal cumulative crossings differenced per block (G-EB-5 operationalisation)
  FW_W stock    s31: sum of freeway_segments FW_W counts of the R-obs3 state; other seeds: FW_W chain rows of the
                frames parquet at T + 150 k + 0.1
  k8b           K8b-0 (K8_PREDECLARATION_AMENDMENT_16 r2 sections 3.3 / 6 / 7.3), TL3m seeds 31 / 43 / 47:
                states[T] (GRID9): first_appear{32, 10491, 10481, 10118, 10368, 10695} = vehicles whose first frame on
                that link over the whole run lies in (T + 0.1, T + 150.1] (3.3 g, p, w); onW_T150 / onW_T150_slow =
                link 32 rows with NEXTLINK 10482 at T + 150.1 (all / < 5 km/h, R2); wout_dest[k] (k = 1..3) = W_out
                episodes (k8b/wout_episodes.py rule, any class, anomalies excluded) by destination R_D_E / R_D_W /
                free / side_exit whose destination token's first frame lies in (T + 150(k-1) + 0.1, T + 150k + 0.1]
                (R3b; 10484 / 10480 entries); long (s31 starts 900 / 2700 / 4950, blocks k = 1..H): stop127[k]
                (127 rows < 5 km/h at T + 150k + 0.1, R4), onW[k] / onW_slow[k] (R2), wout_dest[k], city127[k] =
                vehicles whose first 127 frame lies in the block and that have a 32 or 10778 frame before it (7.3
                (i-c); a 10491 port vehicle lands on 129 and has neither); inputs w_s<seed>.parquet of
                sa_fzp_frames.py (sha256 recorded)
  k91           K9-1-0 (K8_PREDECLARATION_AMENDMENT_19 r2 section 7 R9 / R10 / R11; the K9-1 probe tool k91_vissim.py
                rule), TL3m seeds 31 / 43 / 47: conn[c][w] = vehicles whose first frame on connector c (10703 side
                street onto 31; 10119 / 10121 / 10698 the W1 connectors) lies in window w = floor((t - 0.1) / 150)
                (from w_s<seed>.parquet, the P-4 extract rule, which keeps those connectors); ew[o][w] = [off, elig]
                of the FW_W exits o in E_W = 10479 / 10491 / 10638 / 10645 counted by the F17b P0-3 rule (the code
                root's k9/f17b_select.py: obs150 detector points applied to the v3c3 NC FZP; read only) -- absent
                (recorded 'missing') when the code root has no k9/f17b_select.py"""
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sa_common as sc  # noqa: E402

c = sc.c
CHAIN = {10118: 627.392, 10368: 627.429, 10695: 622.276}
DOWN_HEADS = {30: 10118, 39: 10368, 38: 10695}


def parse():
    ap = c.parser(__doc__)
    ap.add_argument('--data', help='x2 ext parquet folder (default <out>/opt1v2/data)')
    ap.add_argument('--eo-root', default=r'D:\VISSIM_runs\20260930_v3c2\reports\nc_analysis\eo')
    ap.add_argument('--wout-data', help='K8b-0: W_out extracts folder (default <out>/sa/fzp, sa_fzp_frames.py)')
    ap.add_argument('--dry-run', action='store_true')
    return ap.parse_args()


K8B_FIRST_LINKS = (32, 10491, 10481, 10118, 10368, 10695)
K8B_WOUT_DESTS = ('R_D_E', 'R_D_W', 'free', 'side_exit')


def _wout_rule():
    path = c.R / 'diagnostics' / 'sdmpc_n31_20260924' / 'k8b'
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
    import wout_episodes
    return wout_episodes


def _block_counts(times, T, H):
    """{k: n} of event times t in (T + 150(k-1) + 0.1, T + 150k + 0.1], k = 1..H (5 s frames end on .1)."""
    out = {str(k): 0 for k in range(1, H + 1)}
    for t in times:
        k = int(-(-(t - T - 0.1 - 1e-6) // 150.0))
        if 1 <= k <= H:
            out[str(k)] += 1
    return out


def k8b_entry(ext, wdf, seed):
    """K8b-0 VISSIM-side values of one TL3m seed (definitions in the module docstring)."""
    rule = _wout_rule()
    first = {L: ext[ext.LINK == L].groupby('NO').SIMSEC.min() for L in K8B_FIRST_LINKS}
    eps = [r for r in rule.seed_rows(wdf[['SIMSEC', 'NO', 'LINK', 'POS']], seed) if not r[5] and r[6] is not None]
    dest_times = {d: sorted(r[6] for r in eps if r[3] == d) for d in K8B_WOUT_DESTS}
    onw = ext[(ext.LINK == 32) & (ext.NEXTLINK == 10482)]
    onw_all = onw.groupby('SIMSEC').size()
    onw_slow = onw[onw.SPEED < 5].groupby('SIMSEC').size()
    stop127 = ext[(ext.LINK == 127) & (ext.SPEED < 5)].groupby('SIMSEC').size()
    first127 = ext[ext.LINK == 127].groupby('NO').SIMSEC.min()
    city_first = ext[ext.LINK.isin([32, 10778])].groupby('NO').SIMSEC.min()
    city127 = sorted(float(t) for no, t in first127.items() if no in city_first.index and city_first[no] < t)
    frames = sorted(set(float(t) for t in ext.SIMSEC.unique()))

    def at(series, t):
        f = nearest_frame(frames, t)
        return int(series.get(f, 0)) if f is not None else None
    out = {'states': {}, 'n_wout_episodes': len(eps)}
    for T in sc.GRID9:
        t0, t1 = T + 0.1, T + 150.1
        row = {'first_appear': {str(L): int(((s > t0 + 1e-6) & (s <= t1 + 1e-6)).sum()) for L, s in first.items()},
               'onW_T150': at(onw_all, t1), 'onW_T150_slow': at(onw_slow, t1),
               'wout_dest': {d: _block_counts(dest_times[d], T, 3) for d in K8B_WOUT_DESTS}}
        out['states'][str(T)] = row
    if int(seed) == sc.ROBS_SEED:
        out['long'] = {}
        for T, H in sc.LONG_H.items():
            ends = [T + 150.0 * k + 0.1 for k in range(1, H + 1)]
            out['long'][str(T)] = {
                'H': H,
                'stop127': {str(k + 1): at(stop127, t) for k, t in enumerate(ends)},
                'onW': {str(k + 1): at(onw_all, t) for k, t in enumerate(ends)},
                'onW_slow': {str(k + 1): at(onw_slow, t) for k, t in enumerate(ends)},
                'wout_dest': {d: _block_counts(dest_times[d], T, H) for d in K8B_WOUT_DESTS},
                'city127': _block_counts(city127, T, H)}
    return out


K91_CONNECTORS = (10703, 10119, 10121, 10698)


def k91_entry(wdf, seed):
    """K9-1-0 VISSIM-side values of one TL3m seed (definitions in the module docstring, 'k91')."""
    conn = {}
    for cn in K91_CONNECTORS:
        first = wdf[wdf.LINK == cn].groupby('NO').SIMSEC.min()
        w = ((first - 0.1) // 150).astype(int).value_counts().to_dict()
        conn[str(cn)] = {str(k): int(v) for k, v in sorted(w.items())}
    out = {'conn': conn}
    path = c.R / 'diagnostics' / 'sdmpc_n31_20260924' / 'k9' / 'f17b_select.py'
    if not path.is_file():
        out['ew'] = {'missing': str(path)}
        return out
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    import f17b_select as F
    counts, meta = F.seed_window_counts(int(seed))
    out['ew'] = {o: {str(w): list(v) for w, v in sorted(cnt.items())} for o, cnt in counts.items()}
    out['ew_inputs'] = meta
    return out


def counts_at(df, t, links):
    sub = df[(df.SIMSEC == t)]
    out = {str(k): int((sub.LINK == int(k)).sum()) for k in links}
    out['total'] = sum(out.values())
    return out


def nearest_frame(frames, t):
    f = min(frames, key=lambda x: abs(x - t))
    return f if abs(f - t) < 1e-6 else None


def spill_windows(df):
    a = (df.LINK == 10491) & (df.POS <= 30) & (df.SPEED < 15)
    b = ((df.LINK == 26) & (df.LANE == 1) & (df.POS >= 3550) & (df.POS <= 3651) & (df.ROUTDECNO == 1132)
         & (df.ROUTENO == 2) & (df.SPEED < 15))
    pos = set(round(float(t) - 0.1) for t in df.loc[a | b, 'SIMSEC'].unique())
    frames = sorted(set(round(float(t) - 0.1) for t in df.SIMSEC.unique()))
    if not frames:
        return []
    out = []
    for w0 in range(int(frames[0] // 30 * 30), int(frames[-1]) + 1, 30):
        fs = [f for f in range(w0, w0 + 30, 5)]
        if sum(1 for f in fs if f in pos) >= 3:
            out.append([w0, w0 + 30])
    return out


def ext127_series(df):
    st = df[(df.LINK == 127) & (df.SPEED < 5)].groupby('SIMSEC').POS.min()
    return {float(t): sc.STOPLINE_X_M - float(p) for t, p in st.items()}


def lane3_full_frames(df):
    st = df[(df.LINK == 127) & (df.LANE == 3) & (df.SPEED < 5)].groupby('SIMSEC').POS.min()
    return sorted(float(t) for t, p in st.items() if float(p) < 30.0)


def eb_crossings(df):
    """a1_stopline crossing rule on consecutive 5 s frames; returns sorted crossing frame times."""
    def x_of(link, pos):
        if link == 127:
            return pos
        if link in CHAIN:
            return CHAIN[link] + pos
        if link in DOWN_HEADS:
            return 700.0 + pos          # any downstream head is past the station
        return None
    rows = df[df.LINK.isin([127, 10118, 10368, 10695, 30, 39, 38])].sort_values(['NO', 'SIMSEC'])
    out = []
    prev_no, prev_t, prev_x = None, None, None
    for r in rows.itertuples(index=False):
        x = x_of(int(r.LINK), float(r.POS))
        no, t = int(r.NO), float(r.SIMSEC)
        if no == prev_no and prev_x is not None and x is not None and t - prev_t <= 5.0 + 1e-6:
            if prev_x < sc.STOPLINE_X_M <= x:
                out.append(t)
        prev_no, prev_t, prev_x = no, t, x
    return sorted(out)


def eo_tables(eo_dir):
    import csv
    cells = defaultdict(dict)        # t -> cell -> (v, eligible)
    with open(Path(eo_dir) / 'cells_30s.csv', newline='', encoding='utf-8') as h:
        for row in csv.DictReader(h):
            if row['road'] != 'FW_W':
                continue
            v = row['v_kmh']
            cells[round(float(row['time_s']), 1)][int(row['cell'])] = (
                float(v) if v not in ('', None) else None, row['speed_eligible_n_ge5'] == 'True')
    cum = {}
    with open(Path(eo_dir) / 'boundaries_30s.csv', newline='', encoding='utf-8') as h:
        for row in csv.DictReader(h):
            if row['id'] == 'OR_D_W_signal':
                cum[round(float(row['window_end_s']), 1)] = float(row['cumulative_crossings'])
    return ({str(t): {str(k): list(v) for k, v in row.items()} for t, row in cells.items()},
            {str(t): v for t, v in cum.items()})


def robs3_rows():
    out = {}
    for T in sc.ROBS61_T:
        p = c.DEC / f'state_{T:06d}.json'
        if not p.is_file():
            continue
        d = json.loads(p.read_text(encoding='utf-8-sig'))
        vr = d['vehicle_records']
        full = {str(k): int(v) for k, v in vr['full_network_link_counts'].items()}
        recs = vr['records']
        stop127 = sum(1 for r in recs if str(r['link_no']) == '127' and float(r['speed_kph']) < 5.0)
        w = {k: full.get(k, 0) for k in sc.OBS_W_LINKS}
        w['total'] = sum(w.values())
        out[str(T)] = dict(w_ports=w, stop127=stop127, wout=sum(full.get(k, 0) for k in sc.W_OUT_LINKS),
                           fw_w_stock=sum(int(c_['count']) for c_ in d['freeway_segments']['FW_W']),
                           port10491=full.get('10491', 0), port10481=full.get('10481', 0))
    return out


def main():
    args = parse()
    c.apply(args)
    data = Path(args.data) if args.data else c.OUT / 'opt1v2' / 'data'
    p4 = c.OUT / 'opt1v2' / 'out' / 'p4_states_grid9_v3c3.json'
    inputs = {'p4': p4, 'robs_decisions': c.DEC}
    wdata = Path(args.wout_data) if args.wout_data else sc.sa_out() / 'fzp'
    for s in sc.FH_SEEDS:
        inputs[f'ext_s{s}'] = data / f'e_s{s}_ext.parquet'
        inputs[f'frames_s{s}'] = sc.sa_out() / 'fzp' / f's{s}_frames.parquet'
        inputs[f'eo_s{s}'] = Path(args.eo_root) / f's{s}_v3c2nc'
        if s in sc.TL3M_SEEDS:
            inputs[f'wout_s{s}'] = wdata / f'w_s{s}.parquet'          # K8b-0
    if args.dry_run:
        for k, v in inputs.items():
            print(f'DRY {k:12s} {"ok " if Path(v).exists() else "MISSING"} {v}')
        print('DRY ->', sc.sa_out() / 'vissim_ref.json')
        return 0
    c.lower_priority()
    import pandas as pd
    p4d = json.loads(p4.read_text(encoding='utf-8'))
    ref = {'schema': 'k8-sa-vissim-ref/v1', 'rules': __doc__.split('Definitions', 1)[1],
           'inputs': {k: {'path': str(v), 'sha256': sc.sha256_file(v)} for k, v in inputs.items()
                      if Path(v).is_file()}, 'seeds': {}}
    for s in sc.FH_SEEDS:
        sc.guard_seed(s)
        ext = pd.read_parquet(inputs[f'ext_s{s}'])
        frm = pd.read_parquet(inputs[f'frames_s{s}'])
        fr_ext = sorted(set(float(t) for t in ext.SIMSEC.unique()))
        fr_frm = sorted(set(float(t) for t in frm.SIMSEC.unique()))
        ext127 = ext127_series(ext)
        lane3 = lane3_full_frames(ext)
        cls = {int(r['T']): r for r in p4d['seeds'][str(s)]['rows']}
        states = {}
        for T in sc.GRID9:
            t0, t1 = nearest_frame(fr_ext, T + 0.1), nearest_frame(fr_ext, T + 150.1)
            row = dict(event_state=bool(cls[T]['event_state']), nonevent_state=bool(cls[T]['nonevent_state']),
                       w_ports_T=counts_at(ext, t0, sc.OBS_W_LINKS) if t0 else None,
                       w_ports_T150=counts_at(ext, t1, sc.OBS_W_LINKS) if t1 else None)
            sub = ext[(ext.SIMSEC == t1) & (ext.LINK == 127)] if t1 else None
            row['stop127_T150'] = int((sub.SPEED < 5).sum()) if sub is not None else None
            f1 = nearest_frame(fr_frm, T + 150.1)
            row['wout_T150'] = (int(frm[(frm.SIMSEC == f1) & frm.LINK.isin([31, 124])].shape[0]) if f1 else None)
            first = [t for t, e in sorted(ext127.items()) if T + 0.1 - 1e-6 <= t <= T + 900.1 + 1e-6 and e >= sc.G6_EXTENT_M]
            row['ext127_first500'] = first[0] - 0.1 if first else None
            row['fw_w_stock'] = {}
            for k in range(1, 7):
                f = nearest_frame(fr_frm, T + 150 * k + 0.1)
                row['fw_w_stock'][str(T + 150 * k)] = (int(frm[(frm.SIMSEC == f) & frm.LINK.isin([26, 10771, 120])].shape[0])
                                                      if f else None)
            row['lane3_full_frames_T_T450'] = sum(1 for t in lane3 if T + 0.1 - 1e-6 <= t <= T + 450.1 + 1e-6)
            states[str(T)] = row
        entry = {'states': states, 'spill_windows_W': spill_windows(ext)}
        if s == 31:
            entry['robs3'] = robs3_rows()
            cross = eb_crossings(ext)
            entry['eb_crossings_by_block'] = {str(b): sum(1 for t in cross if b < t - 0.1 <= b + 150)
                                              for b in range(0, 9000, 150)}
            entry['eb_crossing_times'] = [float(t) for t in cross]
            cells, cum = eo_tables(inputs['eo_s31'])
            entry['eo_cells30_FW_W'] = cells
            entry['eo_or_d_w_signal_cum'] = cum
        if s in sc.TL3M_SEEDS:                                     # K8b-0 (amendment 16 r2 sections 3.3 / 6 / 7.3)
            wpath = inputs[f'wout_s{s}']
            wdf = pd.read_parquet(wpath) if Path(wpath).is_file() else None
            entry['k8b'] = k8b_entry(ext, wdf, s) if wdf is not None else {'missing': str(wpath)}
            entry['k91'] = k91_entry(wdf, s) if wdf is not None else {'missing': str(wpath)}   # K9-1-0
        ref['seeds'][str(s)] = entry
        print(f'SA_VISSIM_REF s{s} states={len(states)} spill_windows={len(entry["spill_windows_W"])}', flush=True)
    sc.write_json(sc.sa_out() / 'vissim_ref.json', ref)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
