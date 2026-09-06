# -*- coding: utf-8 -*-
"""링크별 길이·차로수를 .fzp 로 유도한다 (head window 용).

정지선 연속 walk 는 '행렬의 선두가 정지선 근처에 있어야 정지선 큐'라는 조건이 필요하다.
그 조건 없이 걸으면 **링크 중간에 따로 서 있는 정지 무리**도 큐로 세게 된다 —
arm_qsplit_x18_20260904 실측에서 walk/정지 = 0.820 이 나왔는데 .fzp 참조는 0.569 였고,
그 격차가 이 조건의 부재다.

길이 = 링크에서 관측된 최대 Pos. 하한 추정이지만 5,400초 동안 전 차량을 보므로
실질적으로 정확하다(램프 커넥터 검산: 10482 380.7m x 2차로가 120대 포화 = 6.3 m/veh).
"""
import io,sys,json,collections,pathlib
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
R=pathlib.Path(__file__).resolve().parents[1]
FZP=R/"evaluation/runs/qcread_x18_20260903/vissim_eval/modi_eval_userfix_20260814e_fwsweep_x18_rampbn_qc_001.fzp"
OUT=R/"outputs/urban_link_geometry_20260904.json"
maxpos=collections.defaultdict(float); maxlane=collections.defaultdict(int)
started=False
for raw in io.open(FZP,"rb"):
    if not started:
        if raw.startswith(b"$VEHICLE"): started=True
        continue
    p=raw.split(b";",6)
    if len(p)<5: continue
    lk=p[2].decode()
    try: li=int(p[3]); ps=float(p[4])
    except ValueError: continue
    if ps>maxpos[lk]: maxpos[lk]=ps
    if li>maxlane[lk]: maxlane[lk]=li
out={k: {"length_m": round(v,2), "lanes": maxlane[k]} for k,v in maxpos.items() if v>0}
json.dump({"source":"fzp qcread_x18_20260903 · length = max observed Pos, lanes = max Lane index",
           "note":"head window 판정용. 길이는 하한 추정이나 5400초 전차량 관측이라 실질 정확.",
           "links":out}, io.open(OUT,"w",encoding="utf-8"), ensure_ascii=False, indent=1)
import statistics as stx
L=[v["length_m"] for v in out.values()]
print("링크 %d개 · 길이 중앙 %.1f m · 범위 %.1f~%.1f"%(len(out),stx.median(L),min(L),max(L)))
for k in ("32","66","30","40","420"):
    if k in out: print("   링크 %-6s %8.1f m · %d차로"%(k,out[k]["length_m"],out[k]["lanes"]))
print("-> %s"%OUT)
