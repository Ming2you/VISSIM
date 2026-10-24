"""Two unchanged exact forecasts with passive ramp-stage receipts."""
import copy
import ctypes
import ctypes.wintypes
import gzip
import hashlib
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
R=HERE.parent
ROOT=HERE.parents[2]
EAST=("RM_C10639","RM_C10681","RM_C10490","RM_C10484")
DEC=Path("D:/VISSIM_runs/20261004_sdmpc_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29")
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,obj):
    raw=json.dumps(obj,allow_nan=False,indent=None if name.endswith(".gz") else 2).encode()
    (HERE/name).write_bytes(gzip.compress(raw) if name.endswith(".gz") else raw)

def trace(captured,reference,coord,options,evaluate,selected_path,output,**unused):
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_sequence as seq
    from evaluation.controllers.lane_ramp_runtime import LaneRampRuntime
    from src.models.state import ControlAction
    from src.controllers import rollout_endpoint as endpoint
    state,cfg=captured["state"],captured["cfg"]
    assert state.time_sec==4500
    selected=adapter.control_from_json(selected_path,cfg,ControlAction)
    if seq.KEY not in selected.diagnostics:selected=seq.pack(seq.actions(selected,3))
    z=coord.encode(selected)
    for j,a in enumerate(coord.axes):
        if a["kind"]=="meter" and a["key"] in EAST:
            value=8-2*a["block"];assert value in a["allowed"]
            z[j]=(value-a["reference_value"])/a["scale"]
    candidates={"selected":selected,"east_progressive":coord.decode(z,selected)}
    advance=LaneRampRuntime.advance
    results={}
    for name,action in candidates.items():
        coord.validate(action)
        rows=[]
        def observed(runtime,*args,**kwargs):
            result=advance(runtime,*args,**kwargs)
            rows.extend(dict(ramp=r,receipt=copy.deepcopy(result[2][r])) for r in EAST)
            return result
        start=time.perf_counter()
        with patch.object(LaneRampRuntime,"advance",observed),seq.prediction_scope(action,cfg,state.time_sec,3) as visits:
            point=endpoint.evaluate_price_point(state,action,copy.deepcopy(captured["forecast"]),(),
                endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode="raw"),capture_response=True)
        elapsed=time.perf_counter()-start
        assert visits==[0,1,2] and len(point.states)==3 and not point.aborted
        old=json.loads((R/"rm_selection216"/(name+".json")).read_bytes())["execution"]
        assert abs(point.ttt-old["ttt"])<1e-9,(name,point.ttt,old["ttt"])
        costs={}
        for row in point.control_area_response["residence"]:
            for k,n in row["inside_veh"].items():costs[k]=costs.get(k,0.)+row["dt_h"]*n
        assert costs==old["costs"]
        assert len(rows)==450*4
        buckets={}
        for row in rows:
            r,x=row["ramp"],row["receipt"]
            assert x["duration_sec"]==1 and x["start_sec"] in range(4500,4950)
            block=int((x["start_sec"]-4500)//150)
            for lane,v in enumerate(x.get("lane_receipts",[x]),1):
                key=(r,lane,block)
                b=buckets.setdefault(key,dict(seconds=0,head_service=0.,merge=0.,eligible=0.,receiving=0.,
                    green_seconds=0,red_seconds=0,service_limited=0,head_ready_limited=0,posthead_space_limited=0,
                    merge_ready_limited=0,receiving_limited=0,head_wait_sum=0.,merge_wait_sum=0.,posttravel_sum=0.,
                    max_head_min_error=0.,max_merge_min_error=0.))
                served=v["head_service_veh"];end=v["end"]
                head_ready=end["head_ready_veh"]+served
                post=end["downstream_travelling_veh"]+end["merge_ready_veh"]-served
                free=max(0.,v["nominal_posthead_storage_veh"]-post)
                limit=v["head_service_limit_veh"];eligible=v["eligible_merge_veh"];receiving=v["receiving_budget_veh"]
                err=abs(served-min(limit,head_ready,free))
                merr=abs(v["accepted_merge_veh"]-min(eligible,receiving))
                assert err<1e-7 and merr<1e-7,(r,lane,err,merr)
                b["max_head_min_error"]=max(b["max_head_min_error"],err)
                b["max_merge_min_error"]=max(b["max_merge_min_error"],merr)
                b["seconds"]+=1;b["head_service"]+=served;b["merge"]+=v["accepted_merge_veh"]
                b["eligible"]+=eligible;b["receiving"]+=receiving
                if limit>0:
                    b["green_seconds"]+=1
                    b["service_limited"]+=int(limit<=head_ready+1e-9 and limit<=free+1e-9)
                    b["head_ready_limited"]+=int(head_ready<=limit+1e-9 and head_ready<=free+1e-9)
                    b["posthead_space_limited"]+=int(free<=limit+1e-9 and free<=head_ready+1e-9)
                else:b["red_seconds"]+=1
                b["merge_ready_limited"]+=int(eligible<=receiving+1e-9)
                b["receiving_limited"]+=int(receiving<=eligible+1e-9)
                b["head_wait_sum"]+=end["head_ready_veh"];b["merge_wait_sum"]+=end["merge_ready_veh"]
                b["posttravel_sum"]+=end["downstream_travelling_veh"]
        summary=[dict(ramp=k[0],lane=k[1],block=k[2],**v) for k,v in buckets.items()]
        assert all(v["seconds"]==150 for v in summary)
        item=dict(ttt=point.ttt,seconds=elapsed,exact_cost_parity=True,stages=summary,
            initial={r:dict(metadata=state.lane_ramp_runtime.buffers[r].metadata(),
                stock=state.lane_ramp_runtime.buffers[r].snapshot(),
                head_service=cfg.network.physical_ramp_branches["ramps"][r]["service_by_green_veh_h"]) for r in EAST})
        save(name+".json",item);save(name+".receipts.json.gz",rows)
        results[name]=item
        print(json.dumps(dict(case=name,seconds=elapsed,ttt=point.ttt,rows=len(rows))),flush=True)
    save("summary.json",dict(results=results,forecasts450=2,optimizer_iterations=0,native=0,fit=0,
        scope="Passive exact RM gate accounting, not native counterfactual proof",future_observations_used=False))
def main():
    assert not (HERE/"protocol.json").exists()
    k=ctypes.WinDLL("kernel32",use_last_error=True)
    k.GetCurrentProcess.restype=ctypes.wintypes.HANDLE
    k.SetPriorityClass.argtypes=[ctypes.wintypes.HANDLE,ctypes.wintypes.DWORD]
    assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
    prior=json.loads((R/"rm_selection216/protocol.json").read_bytes())
    assert all(sha(ROOT/p)==v for p,v in prior["source_sha256"].items())
    assert sha(Path(prior["STOP"]["path"]))==prior["STOP"]["sha256"]
    save("protocol.json",dict(budget=dict(exact_forecasts450=2,scalar=0,fit=0,optimizer=0,native=0,FZP=0),
        baseline=str(R/"rm_selection216"),source_sha256=prior["source_sha256"],STOP=prior["STOP"],
        driver_sha256=sha(Path(__file__)),scope="Passive existing gate receipts; no physics edits"))
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
    original=probe.probe_selected_meter;probe.probe_selected_meter=trace
    sys.argv=[str(probe.__file__),"--closedloop-recorded","--at=4500","--selected-meter-check",
        "--recorded-selection-check","--warm-head-history","--replay-vsl-history","--probe-label=rmflow218",
        "--recording-dir="+str(DEC),"--tuning-json="+str(R/"fixedvsl9000_197/config.json")]
    try:probe.main()
    finally:probe.probe_selected_meter=original
    assert all(sha(ROOT/p)==v for p,v in prior["source_sha256"].items())
    assert sha(Path(prior["STOP"]["path"]))==prior["STOP"]["sha256"]
    save("completion.json",dict(status="COMPLETE",core101_unchanged=True,STOP_unchanged=True))
if __name__=="__main__":main()

