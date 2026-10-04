"""OPT1 state census (read-only, BELOW_NORMAL): VISSIM event / non-event classification of candidate FZP-harness states,
from the F1 extraction parquets (v3c2 fit seeds; v3c3 NC payload identical per GB-1/K7). Definitions = F1 §6 (declared
before F1 ran, a1_stopline.py sha16 77304ded...) plus the options-paper G-EB-6 proxy (10491 connector occupancy >= 20)."""
import ctypes, json, sys, numpy as np, pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import k8common as c  # noqa: E402
_ap = c.parser(__doc__)
_ap.add_argument('--data', help='folder of the x2 parquets e_s<seed>_{v1,ext}.parquet (default <out>/opt1v2/data)')
_args = _ap.parse_args()
c.apply(_args)
ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
D = Path(_args.data) if _args.data else c.OUT / 'opt1v2' / 'data'
GRID = [900, 1200, 1800, 2250, 2700, 3000, 3600, 4200, 4950]   # the nine captured v3c1-s31 template times
out = {'grid': GRID, 'seeds': {}}
for s in (31, 41, 43, 47, 53):
    df = pd.read_parquet(f'{D}/e_s{s}_v1.parquet', columns=['SIMSEC','NO','LINK','LANE','POS','SPEED','ROUTDECNO','ROUTENO'])
    t = np.round(df.SIMSEC.values - 0.1).astype(int)
    df['t'] = t
    # 10491 occupancy per frame
    occ = df[df.LINK == 10491].groupby('t').size()
    # spill frame flag (F1 §6 FW_W)
    a = (df.LINK == 10491) & (df.POS <= 30) & (df.SPEED < 15)
    b = (df.LINK == 26) & (df.LANE == 1) & (df.POS >= 3550) & (df.POS <= 3651) & (df.ROUTDECNO == 1132) & (df.ROUTENO == 2) & (df.SPEED < 15)
    fr = set(df.loc[a | b, 't'].unique())
    frames = np.arange(t.min(), t.max() + 1, 5)
    flag = pd.Series([f in fr for f in frames], index=frames)
    # 30 s windows: >= 3 of 6 frames
    win = {}
    for w0 in range(int(frames.min() // 30 * 30), int(frames.max()), 30):
        fs = [f for f in range(w0, w0 + 30, 5) if f in flag.index]
        win[w0] = sum(flag[f] for f in fs) >= 3
    # 127 lanes 1-2 stopped count per frame (for S_g census)
    st = df[(df.LINK == 127) & (df.SPEED < 5)]
    l12 = st[st.LANE <= 2].groupby('t').size(); l3 = st[st.LANE == 3].groupby('t').size()
    rows = []
    for T in GRID:
        o = occ.reindex(range(T, T + 451, 5)).fillna(0)
        ev = any(win.get(w, False) for w in range(T // 30 * 30, T + 450, 30))
        evb = any(win.get(w, False) for w in range(max(0, (T - 150) // 30 * 30), T + 450, 30))
        o0 = float(occ.get(T, 0))
        rows.append(dict(T=T, occ10491_T=o0, occ10491_max_T_T450=float(o.max()), spill_win_in_T_T450=bool(ev),
                         spill_win_in_Tm150_T450=bool(evb),
                         event_state=bool(ev or o.max() >= 20),
                         nonevent_state=bool((not evb) and o.max() < 20),
                         q127_l12_T=float(l12.get(T, 0)), q127_l3_T=float(l3.get(T, 0))))
    out['seeds'][s] = {'rows': rows, 'n_event': sum(r['event_state'] for r in rows),
                       'n_nonevent': sum(r['nonevent_state'] for r in rows),
                       'n_ambiguous': sum((not r['event_state']) and (not r['nonevent_state']) for r in rows),
                       'stopped127_l12_peak_max': float(l12.loc[1800:7200].max()), 'stopped127_l3_peak_max': float(l3.loc[1800:7200].max())}
    print(s, out['seeds'][s]['n_event'], out['seeds'][s]['n_nonevent'], out['seeds'][s]['n_ambiguous'],
          out['seeds'][s]['stopped127_l12_peak_max'], out['seeds'][s]['stopped127_l3_peak_max'], flush=True)
tot = {k: sum(v[k] for v in out['seeds'].values()) for k in ('n_event','n_nonevent','n_ambiguous')}
out['totals'] = tot
print(tot)
_dest = c.OUT / 'opt1v2' / 'out'
_dest.mkdir(parents=True, exist_ok=True)
json.dump(out, open(_dest / 'p4_states_grid9_v3c3.json', 'w'), indent=1)
