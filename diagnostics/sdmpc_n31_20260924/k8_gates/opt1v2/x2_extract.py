"""K8 OPT1 v2 x2: read-only FZP filter around SC1001 EB from the v3c3 NC fit-seed FZPs (31,41,43,47,53).
Two outputs per seed (one FZP pass):
  e_s{seed}_v1.parquet  : EXACTLY the x1 filter/columns (sc1001eb/tools/x1_extract.py sha256 564256ee...) -> compare with
                          the v3c2 parquets (GB-1 says v3c3 NC payload == v3c2 payload).
  e_s{seed}_ext.parquet : x1 filter + link 32 at ALL positions + 10482 (onW ramp connector) + column ROUTDECTYPE.
                          Needed for the visit-based recount (visit origin) and the G-EB-3 observed W+ports pair (B2).
BELOW_NORMAL, one seed at a time. Never touches s37 or *_rm. Usage: python -B x2_extract.py 31 41 43 47 53"""
import sys, time, ctypes, hashlib
import pandas as pd, numpy as np
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import k8common as c  # noqa: E402
_ap = c.add_nc3(c.parser(__doc__))
_ap.add_argument('seeds', nargs='+', type=int, help='NC fit seeds (31 41 43 47 53 only)')
_ap.add_argument('--data', help='parquet output folder (default <out>/opt1v2/data)')
_args = _ap.parse_args()
c.apply(_args)
ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)  # BELOW_NORMAL
D = Path(_args.data) if _args.data else c.OUT / 'opt1v2' / 'data'
D.mkdir(parents=True, exist_ok=True)
cols = ['SIMSEC', 'NO', 'LINK', 'LANE', 'POS', 'POSLAT', 'SPEED', 'TMINNETTOT', 'DELAYTM', 'DESSPEED', 'LENGTH', 'ROUTDECNO', 'ROUTENO',
        'ROUTDECTYPE', 'NEXTLINK', 'DESTLANE', 'LNCHG', 'INTERACTSTATE', 'INTERACTTARGTYPE', 'INTERACTTARGNO', 'FX', 'FY', 'RX', 'RY', 'ACCEL']
use = ['SIMSEC', 'NO', 'LINK', 'LANE', 'POS', 'SPEED', 'LENGTH', 'ROUTDECNO', 'ROUTENO', 'NEXTLINK', 'DESTLANE', 'LNCHG',
       'INTERACTSTATE', 'INTERACTTARGTYPE', 'INTERACTTARGNO', 'ACCEL']
use_ext = use + ['ROUTDECTYPE']
FULL = {127, 10118, 10368, 10695, 129, 10777, 10778, 10491, 10481, 10490}
DOWN = {30, 38, 39}


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


for seed in _args.seeds:
    assert seed in (31, 41, 43, 47, 53)
    FZP = str(c.NC3 / f's{seed}_v3c3nc' / 'run' / 'vissim_eval' / f'baseline_s{seed}_v3c3nc_001.fzp')
    t0 = time.time(); p1 = []; p2 = []; nrows = 0
    it = pd.read_csv(FZP, sep=';', skiprows=38, header=None, names=cols, usecols=use_ext, chunksize=1_000_000, encoding='latin-1',
                     dtype={'SIMSEC': np.float64, 'NO': np.int64, 'LINK': np.int64, 'LANE': np.int16, 'POS': np.float64, 'SPEED': np.float64,
                            'LENGTH': np.float64, 'ROUTDECNO': 'Int32', 'ROUTENO': 'Int32', 'NEXTLINK': 'Int64',
                            'DESTLANE': 'Int16', 'LNCHG': 'category', 'INTERACTSTATE': 'category', 'INTERACTTARGTYPE': 'category',
                            'INTERACTTARGNO': 'string', 'ACCEL': np.float64, 'ROUTDECTYPE': 'category'})
    for ch in it:
        nrows += len(ch)
        L = ch['LINK']; P = ch['POS']
        m1 = L.isin(FULL) | (L.isin(DOWN) & (P < 120)) | ((L == 32) & (P >= 700)) | ((L == 26) & (P >= 3300)) | ((L == 2) & (P >= 3700))
        m2 = m1 | (L == 32) | (L == 10482)
        p1.append(ch.loc[m1, use].copy())
        p2.append(ch.loc[m2, use_ext].copy())
    for parts, name, cats in ((p1, 'v1', ('LNCHG', 'INTERACTSTATE', 'INTERACTTARGTYPE')),
                              (p2, 'ext', ('LNCHG', 'INTERACTSTATE', 'INTERACTTARGTYPE', 'ROUTDECTYPE'))):
        df = pd.concat(parts, ignore_index=True)
        for c in cats:
            df[c] = df[c].astype(str).astype('category') if name == 'ext' else df[c].astype('category')
        out = str(D / f'e_s{seed}_{name}.parquet')
        df.to_parquet(out, index=False)
        print(f's{seed} {name}: rows_in {nrows:,} kept {len(df):,} sha256 {sha(out)}', flush=True)
    print(f's{seed} t={time.time()-t0:.0f}s', flush=True)
