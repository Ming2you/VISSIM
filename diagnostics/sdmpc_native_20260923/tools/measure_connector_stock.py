r"""Measure on-ramp connector occupancy directly from the native FZP.

Counts vehicles whose LANE\LINK\NO is a ramp connector id, per 5s frame.
Compares the no-control run against what the model predicts for the same window.
"""
import sys, json
from pathlib import Path
from collections import defaultdict

RAMPS = {'10480','10482','10484','10490','10639','10644','10646','10681'}
FZP = {
 'none': Path(r'D:\VISSIM_runs\20260922_both_off_half\fw080_urban090_nc9000\run\vissim_eval\baseline_001.fzp'),
 'rm'  : Path(r'D:\VISSIM_runs\20260922_fw080_urban090_controls\rm\run\vissim_eval\baseline_001.fzp'),
}
A,B = 1900.0, 3950.0   # covers the three replay windows

def scan(path):
    per = defaultdict(lambda: defaultdict(int))   # t -> conn -> count
    with path.open('rb') as f:
        for raw in f:
            if not raw[:1].isdigit(): continue
            p = raw.split(b';',4)
            t = float(p[0])
            if t < A: continue
            if t > B: break
            link = p[2].decode('ascii')
            if link in RAMPS: per[t][link] += 1
            elif t not in per: per[t]     # ensure frame exists
    return per

def integrate(series, a, b):
    """veh*h over [a,b] by trapezoid on the 5s grid"""
    ts = sorted(t for t in series if a-1e-9 <= t <= b+1e-9)
    tot = 0.
    for x,y in zip(ts, ts[1:]):
        tot += (series[x]+series[y])/2*(y-x)/3600
    return tot

if __name__ == '__main__':
    out = {}
    for arm, p in FZP.items():
        print(f'scanning {arm} ...', flush=True)
        per = scan(p)
        tot = {t: sum(d.values()) for t,d in per.items()}
        byc = {c: {t: per[t].get(c,0) for t in per} for c in RAMPS}
        out[arm] = dict(total=tot, byconn=byc)
        print(f'  frames={len(per)}  평균 총 커넥터 재차={sum(tot.values())/len(tot):.2f} veh', flush=True)
    res = {}
    for a,b,label in ((1950.1,2400.1,'1950.1'),(2700.1,3150.1,'2700.1'),(3450.1,3900.1,'3450.1')):
        row = {}
        for arm in FZP:
            row[arm] = dict(total=integrate(out[arm]['total'],a,b),
                            byconn={c: integrate(out[arm]['byconn'][c],a,b) for c in RAMPS})
        row['delta_total'] = row['rm']['total']-row['none']['total']
        res[label] = row
        print(f"\n=== {label} ~ +450s : 온램프 커넥터 재차 적분 (veh·h) ===")
        print(f"  none = {row['none']['total']:.4f}   rm = {row['rm']['total']:.4f}   Δ = {row['delta_total']:+.4f}")
        for c in sorted(RAMPS):
            n=row['none']['byconn'][c]; r=row['rm']['byconn'][c]
            print(f"    {c}: none {n:7.4f}  rm {r:7.4f}  Δ {r-n:+7.4f}")
    Path(r'D:\VISSIM-merge\evidence\connector_stock.json').write_text(
        json.dumps(res, indent=2), encoding='utf-8')
