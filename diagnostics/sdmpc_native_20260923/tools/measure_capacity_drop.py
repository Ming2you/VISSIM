r"""Measure the capacity drop phi directly from the no-control FZP.

phi = (queue discharge rate after breakdown) / (max sustained pre-breakdown flow)
at the active bottleneck. Flow is counted as trajectory crossings of a fixed
road-offset between consecutive 5s frames; breakdown is detected from the speed
of the vehicles just upstream of that offset.
"""
import sys, json, importlib.util
from collections import defaultdict
from pathlib import Path
ROOT=Path(r'D:\VISSIM-merge\sim3')
CAL=ROOT/'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1'
sys.path[:0]=[str(CAL),str(ROOT/'.review-deps'),str(ROOT)]
NONE=Path(r'D:\VISSIM_runs\20260922_both_off_half\fw080_urban090_nc9000\run\vissim_eval\baseline_001.fzp')
ROAD='FW_E'
# probe offsets: downstream of the queue region (cells 14..20 span 5262..7241)
PROBES=[5262.,5789.,6315.,6490.,6841.,7041.,7241.,7498.,7827.]
UP=300.   # speed sampled within this distance upstream of the probe

def main():
    spec=importlib.util.spec_from_file_location('h',ROOT/'diagnostics/offramp_dynamic_20260922/study.py')
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    data,_=m.corrected_data()
    link={}
    for road,rs in data.geometry['chains'].items():
        for r in rs: link[str(r['link'])]=(road,float(r['offset_m']))
    prev={}; cross=defaultdict(lambda: defaultdict(int)); spd=defaultdict(lambda: defaultdict(list))
    lastt=None
    with NONE.open('rb') as f:
        cur={}
        for raw in f:
            if not raw[:1].isdigit(): continue
            p=raw.split(b';',7); t=float(p[0])
            if t!=lastt:
                if lastt is not None:
                    for vid,(x,v) in cur.items():
                        if vid in prev:
                            x0=prev[vid]
                            for X in PROBES:
                                if x0 < X <= x: cross[lastt][X]+=1
                        for X in PROBES:
                            if X-UP <= x < X: spd[lastt][X].append(v)
                    prev={vid:x for vid,(x,v) in cur.items()}
                lastt=t; cur={}
            lk=p[2].decode('ascii')
            if lk not in link: continue
            road,off=link[lk]
            if road!=ROAD: continue
            cur[p[1].decode('ascii')]=(off+float(p[4]), float(p[6]))
    ts=sorted(cross)
    print(f"프레임 {len(ts)}개, {ts[0]}~{ts[-1]}초\n")
    print(f"{'위치m':>7} {'자유류 최대유량':>16} {'대기열 방류율':>15} {'phi':>7} {'붕괴시각':>9} {'붕괴후 표본':>10}")
    out={}
    for X in PROBES:
        rows=[(t,cross[t].get(X,0)*720., (sum(spd[t][X])/len(spd[t][X]) if spd[t].get(X) else None)) for t in ts]
        rows=[r for r in rows if r[2] is not None]
        if len(rows)<100: print(f"{X:>7.0f}  표본부족"); continue
        # breakdown: first time the 5-frame mean upstream speed drops below 50 km/h and stays
        bt=None
        for i in range(len(rows)-5):
            w=[r[2] for r in rows[i:i+5]]
            if sum(w)/5 < 50.: bt=rows[i][0]; break
        pre=[r[1] for r in rows if r[0] < (bt or rows[-1][0]) and r[2] >= 70.]
        post=[r[1] for r in rows if bt is not None and r[0] >= bt and r[2] < 50.]
        if not pre or len(post)<20: print(f"{X:>7.0f}  붕괴 미검출 또는 표본부족  (붕괴={bt})"); continue
        pre.sort()
        cap=sum(pre[-max(6,len(pre)//20):])/len(pre[-max(6,len(pre)//20):])   # top 5% sustained
        dis=sum(post)/len(post)
        out[X]=dict(capacity_vph=cap,discharge_vph=dis,phi=dis/cap,breakdown_s=bt,post_n=len(post))
        print(f"{X:>7.0f} {cap:>16.1f} {dis:>15.1f} {dis/cap:>7.3f} {bt:>9.1f} {len(post):>10}")
    Path(r'D:\VISSIM-merge\evidence\capacity_drop.json').write_text(
        json.dumps(out,indent=2),encoding='utf-8')
    if out:
        ph=[v['phi'] for v in out.values()]
        ph.sort()
        print(f"\n  phi 중앙값 = {ph[len(ph)//2]:.3f}   범위 {min(ph):.3f}~{max(ph):.3f}   (n={len(ph)})")

main()
