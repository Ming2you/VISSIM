# -*- coding: utf-8 -*-
"""저류별 길이가중 평균 차로수를 .fzp 로 유도한다 (4단계).

`_storage_effective_lanes` 는 용량/(길이×jam) 항등식으로 차로수를 되찾는데, 증거파일에
길이가 없는 저류가 121/226 이고 그중 **75개가 실제 개포 링크로 저류 점유의 58.29%
(934.82 veh/결정)** 를 들고 있다. 그 저류들은 차로 보정을 못 받아 τ 가 차로수배만큼
과대해진다(보정된 저류의 차로수 중앙 3.00).

docstring 이 원하는 값 그대로 유도한다:

    effective_lanes(storage) = sum_i(len_i * lanes_i) / sum_i(len_i)

len_i = 링크 i 의 max Pos, lanes_i = 링크 i 의 max Lane index (.fzp 실측).
직렬/병렬을 구분할 필요가 없다 — 길이가중 평균이 바로 그 제수다.
"""
import io,sys,json,collections,pathlib
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
R=pathlib.Path(__file__).resolve().parents[1]
FZP=R/"evaluation/runs/qcread_x18_20260903/vissim_eval/modi_eval_userfix_20260814e_fwsweep_x18_rampbn_qc_001.fzp"
DET=R/"evaluation/real_world_modi_control_distributed_20260728/detector_local_mapping_distributed_core17legs4f_20260903_blindfix20260905b.json"
OUT=R/"outputs/storage_effective_lanes_20260904.json"

maxpos=collections.defaultdict(float); maxlane=collections.defaultdict(int)
started=False
for raw in io.open(FZP,"rb"):
    if not started:
        if raw.startswith(b"$VEHICLE"): started=True
        continue
    p=raw.split(b";",6)
    if len(p)<5: continue
    lk=p[2].decode()
    try:
        li=int(p[3]); ps=float(p[4])
    except ValueError: continue
    if ps>maxpos[lk]: maxpos[lk]=ps
    if li>maxlane[lk]: maxlane[lk]=li
print("링크 %d개의 길이·차로수 실측"%len(maxpos))

det=json.load(io.open(DET,encoding="utf-8"))
l2o=det["link_to_origins"]
by_storage=collections.defaultdict(list)
for link,origins in l2o.items():
    for o in (origins if isinstance(origins,list) else [origins]):
        by_storage[str(o)].append(str(link))

out={}
for st,links in by_storage.items():
    num=den=0.0
    for lk in links:
        L=maxpos.get(lk,0.0); n=maxlane.get(lk,0)
        if L<=0.0 or n<=0: continue
        num+=L*n; den+=L
    if den>0.0:
        out[st]=round(num/den,4)
json.dump({"source":"fzp qcread_x18_20260903 · len=max Pos, lanes=max Lane index",
           "formula":"sum(len_i*lanes_i)/sum(len_i) over link_to_origins members",
           "storage_effective_lanes":out},
          io.open(OUT,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
import statistics as stx
v=list(out.values())
print("저류 %d개 유도 · 차로수 중앙 %.2f · 범위 %.2f~%.2f"%(len(out),stx.median(v),min(v),max(v)))
print("-> %s"%OUT)
