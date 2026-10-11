"""FH frame extract (read-only FZP pass, one seed at a time, BELOW_NORMAL): the freeway-chain rows the x2 ext parquet
does not hold (opt1v2/x2_extract.py keeps 127/129/10777/10778/10491/10481/10490/10695, 32, and only the tails of 26 and
2).

    python -B sa_fzp_frames.py [--root R] [--out O] [--nc3 D] [--dry-run] [--grid T,...] <seed> [<seed> ...]
        -> <out>/sa/fzp/s<seed>_frames.parquet, s<seed>_frames.json (row counts, frame list, FZP size/mtime, sha256)

Kept rows: LINK in the FW_W chain (26, 10771, 120), the FW_E chain (74, 10699, 2, 10613, 119, 10702, 24), the OR_D_W
connectors 10479 / 10491 and the W_out links 31 / 124, at the frames
    every 5 s frame t = 5k + 0.1 with T - 155 < t <= T + 0.1          (FD3 exit-share window + its predecessor)
    t = T + 150 k + 0.1, k = 1..6                                      (FH VISSIM FW_W stock, W_out at T+150)
for T in the FH grid (900 1200 1800 2250 2700 3000 3600 4200 4950; K9-1-0: --grid T,... replaces it, e.g. the
probe-state FH capture of the K9-1-3 commit gate G3 at 1650).  Columns = x2_extract use_ext.
Seeds: v3c3 NC fit seeds 31 41 43 47 53 only (sealed 37/59/61/67 and *_rm runs are never opened).
K8b-0 (K8_PREDECLARATION_AMENDMENT_16 r2 sections 2.4.2 / 6 R3): the same FZP pass also writes
<out>/sa/fzp/w_s<seed>.parquet = every frame of the W_out neighbourhood (rule of the P-4b extract, k8b_decl/p4b_extract.py
sha 85156269: LINK in WOUT_KEEP_ALL at any POS, or a WOUT_PARTIAL link inside its POS window; columns WOUT_USE), read by
sa_vissim_ref.py for the VISSIM W_out -> 10484 / 10480 / free counts (rule diagnostics/sdmpc_n31_20260924/k8b/
wout_episodes.py) + w_s<seed>.json (rows, sha256)."""
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sa_common as sc  # noqa: E402

c = sc.c
COLS = ['SIMSEC', 'NO', 'LINK', 'LANE', 'POS', 'POSLAT', 'SPEED', 'TMINNETTOT', 'DELAYTM', 'DESSPEED', 'LENGTH',
        'ROUTDECNO', 'ROUTENO', 'ROUTDECTYPE', 'NEXTLINK', 'DESTLANE', 'LNCHG', 'INTERACTSTATE', 'INTERACTTARGTYPE',
        'INTERACTTARGNO', 'FX', 'FY', 'RX', 'RY', 'ACCEL']           # x2_extract.cols (FZP header order)
USE = ['SIMSEC', 'NO', 'LINK', 'LANE', 'POS', 'SPEED', 'LENGTH', 'ROUTDECNO', 'ROUTENO', 'NEXTLINK', 'DESTLANE', 'LNCHG',
       'INTERACTSTATE', 'INTERACTTARGTYPE', 'INTERACTTARGNO', 'ACCEL', 'ROUTDECTYPE']
LINKS = (26, 10771, 120, 74, 10699, 2, 10613, 119, 10702, 24, 10479, 10491, 31, 124)
WOUT_USE = ['SIMSEC', 'NO', 'LINK', 'LANE', 'POS', 'SPEED', 'NEXTLINK']          # K8b-0 (p4b_extract.py USE)
WOUT_KEEP_ALL = (31, 124, 119, 10483, 10774, 10119, 10121, 10698, 10703, 10704, 10484, 10480, 10775, 10702, 10491)
WOUT_PARTIAL = {29: (300.0, 1e9), 37: (250.0, 1e9), 40: (1000.0, 1e9), 78: (250.0, 1e9), 79: (-1.0, 150.0),
                24: (-1.0, 400.0), 26: (3600.0, 4200.0), 125: (-1.0, 150.0)}


def frame_set(grid=sc.GRID9):
    out = set()
    for T in grid:
        k = 0
        while True:
            t = round(T + 0.1 - 5.0 * k, 1)
            if t <= T - 155.0:
                break
            out.add(t)
            k += 1
        for j in range(1, 7):
            out.add(round(T + 150.0 * j + 0.1, 1))
    return out


def fzp_path(seed):
    return c.NC3 / f's{seed}_v3c3nc' / 'run' / 'vissim_eval' / f'baseline_s{seed}_v3c3nc_001.fzp'


def main():
    ap = c.add_nc3(c.parser(__doc__))
    ap.add_argument('seeds', nargs='+', type=int)
    ap.add_argument('--dry-run', action='store_true', help='print inputs/outputs only (reads nothing big)')
    ap.add_argument('--grid', help='K9-1-0: comma list of T replacing the FH grid GRID9')
    args = ap.parse_args()
    c.apply(args)
    for s in args.seeds:
        sc.guard_seed(s)
    frames = frame_set(tuple(int(x) for x in args.grid.split(',')) if args.grid else sc.GRID9)
    out_dir = sc.sa_out() / 'fzp'
    if args.dry_run:
        for s in args.seeds:
            p = fzp_path(s)
            print(f'DRY s{s} fzp={p} exists={p.is_file()} -> {out_dir / f"s{s}_frames.parquet"} frames={len(frames)}')
        return 0
    c.lower_priority()
    import numpy as np
    import pandas as pd
    out_dir.mkdir(parents=True, exist_ok=True)
    keys = np.array(sorted(frames))
    for s in args.seeds:
        p = fzp_path(s)
        st = p.stat()
        t0 = time.time()
        parts, nrows = [], 0
        wparts = []
        it = pd.read_csv(p, sep=';', skiprows=38, header=None, names=COLS, usecols=USE, chunksize=1_000_000,
                         encoding='latin-1',
                         dtype={'SIMSEC': np.float64, 'NO': np.int64, 'LINK': np.int64, 'LANE': np.int16,
                                'POS': np.float64, 'SPEED': np.float64, 'LENGTH': np.float64, 'ROUTDECNO': 'Int32',
                                'ROUTENO': 'Int32', 'NEXTLINK': 'Int64', 'DESTLANE': 'Int16', 'LNCHG': 'category',
                                'INTERACTSTATE': 'category', 'INTERACTTARGTYPE': 'category',
                                'INTERACTTARGNO': 'string', 'ACCEL': np.float64, 'ROUTDECTYPE': 'category'})
        for ch in it:
            nrows += len(ch)
            t = ch['SIMSEC'].round(1)
            m = ch['LINK'].isin(LINKS) & t.isin(keys)
            if m.any():
                parts.append(ch.loc[m, USE].copy())
            L, P_ = ch['LINK'], ch['POS']                       # K8b-0 W_out neighbourhood, every frame
            wm = L.isin(WOUT_KEEP_ALL)
            for link, (lo, hi) in WOUT_PARTIAL.items():
                wm |= (L == link) & (P_ >= lo) & (P_ <= hi)
            if wm.any():
                wparts.append(ch.loc[wm, WOUT_USE].copy())
        df = pd.concat(parts, ignore_index=True)
        for col in ('LNCHG', 'INTERACTSTATE', 'INTERACTTARGTYPE', 'ROUTDECTYPE'):
            df[col] = df[col].astype(str).astype('category')
        dest = out_dir / f's{s}_frames.parquet'
        df.to_parquet(dest, index=False)
        meta = {'schema': 'k8-sa-fzp-frames/v1', 'seed': s, 'fzp': str(p), 'fzp_size': st.st_size,
                'fzp_mtime': st.st_mtime, 'rows_in': nrows, 'rows_kept': int(len(df)), 'links': list(LINKS),
                'frames': sorted(frames), 'parquet_sha256': sc.sha256_file(dest), 'sec': round(time.time() - t0, 1)}
        sc.write_json(out_dir / f's{s}_frames.json', meta)
        wdf = pd.concat(wparts, ignore_index=True)
        wdf['NEXTLINK'] = wdf['NEXTLINK'].astype('Int64')
        wdest = out_dir / f'w_s{s}.parquet'
        wdf.to_parquet(wdest, index=False)
        sc.write_json(out_dir / f'w_s{s}.json', {'schema': 'k8b-wout-extract/v1', 'seed': s, 'fzp': str(p),
                                                  'rows_in': nrows, 'rows_kept': int(len(wdf)),
                                                  'keep_all': list(WOUT_KEEP_ALL),
                                                  'partial': {str(k): list(v) for k, v in WOUT_PARTIAL.items()},
                                                  'parquet_sha256': sc.sha256_file(wdest)})
        print(f'SA_FZP_FRAMES s{s} kept={len(df)} rows_in={nrows} sha256={meta["parquet_sha256"][:16]} '
              f'sec={meta["sec"]}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
