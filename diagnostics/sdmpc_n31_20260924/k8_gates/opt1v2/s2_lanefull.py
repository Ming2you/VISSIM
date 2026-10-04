"""K8 OPT1 v2 s2: lane storage at which VISSIM's 127 lanes are 'full' (sensitivity arms for S_l; report-only). READ-ONLY.

DECLARATION (fixed before any number below was computed; docstring hashed into the output as declaration_sha16):
 Input: x2 ext parquets (v3c3 NC fit FZPs 31,41,43,47,53), frames 900 <= SIMSEC < 8850.
 For lane l in {1,2,3} of link 127 and each 5 s frame:
   n_l      = vehicles on 127 lane l (all speeds);
   tail_l   = smallest POS among vehicles on 127 lane l with SPEED < 5 km/h (none -> no tail);
   full_l   = tail_l exists and tail_l < 30.0 m (the stopped queue of lane l reaches the link entry).
 SFULL_l = median of n_l over full_l frames (also p10, p90, number of frames); pooled 5 seeds and per seed.
 Joint lanes 1-2: full_12 = full_1 and full_2; report median/p90 of n_1 + n_2 over full_12 frames.
 Blocking reference: FW_W spill frames of a1_stopline F1 §6 (10491 POS<=30 & v<15, or link 26 lane 1 POS 3550-3651 route
   1132-2 & v<15): median/p90 of n_1 + n_2 and of 129-tail count (POS >= 239.384224) at those frames.
 Geometric reference: head_l / 6.0 (lane 1 621.666240, lane 2 621.568281, lane 3 621.461547) and
   (head_l + 62.541776 + 1.0015) / 6.0 (adding the 129 tail beyond the 10491 landing and connector 10777).
 These values are NOT used to tune anything; they only parameterise the pre-declared sensitivity arms SGOBS2/SFULL.
"""
import ctypes, json, hashlib
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
DECL_SHA = hashlib.sha256(__doc__.encode()).hexdigest()[:16]
HEAD = {1: 621.666240433568, 2: 621.5682806829368, 3: 621.461546643362}
TAIL = 239.38422422843928
res = dict(declaration_sha16=DECL_SHA, geometric={l: dict(head_only=HEAD[l] / 6.0, with_129_tail=(HEAD[l] + 301.926 - TAIL + 1.0015) / 6.0) for l in HEAD}, seeds={})
pool = {k: [] for k in ('1', '2', '3', '12', 'spill12', 'spilltail')}
for s in (31, 41, 43, 47, 53):
    df = pd.read_parquet(f'{DATA}/e_s{s}_ext.parquet', columns=['SIMSEC', 'LINK', 'LANE', 'POS', 'SPEED', 'ROUTDECNO', 'ROUTENO'])
    df = df[(df.SIMSEC >= 900) & (df.SIMSEC < 8850)]
    frames = np.array(sorted(df.SIMSEC.unique()))
    l127 = df[df.LINK == 127]
    n = {l: l127[l127.LANE == l].groupby('SIMSEC').size().reindex(frames, fill_value=0) for l in (1, 2, 3)}
    tail = {l: l127[(l127.LANE == l) & (l127.SPEED < 5)].groupby('SIMSEC').POS.min().reindex(frames) for l in (1, 2, 3)}
    full = {l: (tail[l] < 30.0).fillna(False) for l in (1, 2, 3)}
    R = {}
    for l in (1, 2, 3):
        x = n[l][full[l]]
        pool[str(l)].extend(x.tolist())
        R[f'lane{l}'] = dict(frames=int(len(x)), p10=float(x.quantile(.1)) if len(x) else None, p50=float(x.median()) if len(x) else None,
                             p90=float(x.quantile(.9)) if len(x) else None, all_frames_max=int(n[l].max()))
    f12 = full[1] & full[2]
    x = (n[1] + n[2])[f12]; pool['12'].extend(x.tolist())
    R['lanes12_joint_full'] = dict(frames=int(len(x)), p50=float(x.median()) if len(x) else None, p90=float(x.quantile(.9)) if len(x) else None)
    a = (df.LINK == 10491) & (df.POS <= 30) & (df.SPEED < 15)
    b = (df.LINK == 26) & (df.LANE == 1) & (df.POS >= 3550) & (df.POS <= 3651) & (df.ROUTDECNO == 1132) & (df.ROUTENO == 2) & (df.SPEED < 15)
    sp = np.isin(frames, df.loc[a | b, 'SIMSEC'].unique())
    t129 = df[(df.LINK == 129) & (df.POS >= TAIL)].groupby('SIMSEC').size().reindex(frames, fill_value=0)
    y = (n[1] + n[2])[sp]; z = t129[sp]
    pool['spill12'].extend(y.tolist()); pool['spilltail'].extend(z.tolist())
    R['at_spill_frames'] = dict(frames=int(sp.sum()), n12_p50=float(y.median()) if len(y) else None, n12_p90=float(y.quantile(.9)) if len(y) else None,
                                tail129_p50=float(z.median()) if len(z) else None)
    res['seeds'][s] = R
    print(s, json.dumps(R), flush=True)
q = lambda v, p: float(np.quantile(v, p)) if v else None
res['pooled'] = {k: dict(n=len(v), p10=q(v, .1), p50=q(v, .5), p90=q(v, .9)) for k, v in pool.items()}
json.dump(res, open(f'{B}/out/s2_lanefull.json', 'w'), indent=1, default=float)
print(json.dumps(res['pooled'], indent=1), json.dumps(res['geometric']))
