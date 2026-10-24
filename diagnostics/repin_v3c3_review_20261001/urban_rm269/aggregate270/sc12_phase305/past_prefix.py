"""Estimate past queued-prefix service; no validation outcomes in the estimator."""
import importlib.util,json,math,hashlib
from pathlib import Path
from collections import defaultdict
from diagnostics.validate_native_signal_record import read_ldp_frames
HERE=Path(__file__).resolve().parent;A=HERE.parent;H=A.parent
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    assert not (HERE/"past_prefix_support.json").exists()
    old=read(H/"sc12w_service/typed_support_v3.json")
    for p,h in old["source_pins"].items():assert sha(p)==h,p
    cache=read(H/"sc12w_service/past_fzp_slice.json")
    rows=cache["kept_rows"];bytime=defaultdict(dict);byveh=defaultdict(list)
    for r in rows:bytime[r["time_sec"]][r["vehicle_id"]]=r;byveh[r["vehicle_id"]].append(r)
    times=sorted(bytime)
    root=Path("E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold")
    folder=root/"decisions_sdmpc31_g_2400_hold_s29"
    loader=importlib.util.spec_from_file_location("headspast305",H/"sc12_source/audit.py")
    heads=importlib.util.module_from_spec(loader);loader.loader.exec_module(heads);heads.LINKS={"SC12_W":1220012103}
    ev=[]
    for end in (1950,2100,2250,2400):
        _,events=heads.heads_and_entries(folder,end)
        ev+=sorted((v,t) for lane,v,t in events["SC12_W"] if lane==2)
    ldp_path=root/"vissim_eval/sdmpc31_g_2400_hold_s29_12_001.ldp"
    ldp=read_ldp_frames({12:ldp_path},{12:list(range(1,9))},1790,2400)["frames"]
    intervals=[];start=None
    for t in range(1790,2401):
        green=t<2400 and ldp[t]["12:5"]=="GREEN"
        if green and start is None:start=t
        if not green and start is not None:
            if start>=1800:intervals.append((start,t))
            start=None
    evidence=[]
    for start,end in intervals:
        t0=max(t for t in times if t<start);tprev=max(t for t in times if t<t0)
        assert start-t0<=5.1 and abs(t0-tprev-5)<1e-6
        stopped=[]
        for v,r in bytime[t0].items():
            p=bytime[tprev].get(v)
            if r["link"]!=1220012103 or r["lane"]!=2 or r["position_m"]>107.36635894390177 or not p:continue
            if p["link"]!=r["link"] or p["lane"]!=2:continue
            if abs(r["position_m"]-p["position_m"])>1:continue
            stopped.append((r["position_m"],v))
        stopped.sort(reverse=True)
        queue=[];front=107.36635894390177
        for pos,v in stopped:
            if front-pos>15:break
            queue.append(v);front=pos
        prefix=[];events=sorted((t,v) for v,t in ev if start<t<end)
        for t,v in events:
            if v not in queue:break
            previous=[r for r in byveh[v] if r["time_sec"]<=t and r["link"]==1220012103]
            p=previous[-1] if previous else None
            current_north=bool(p and t-p["time_sec"]<=5.1 and p["next_link"]=="10242")
            connector=next((r for r in byveh[v] if t<r["time_sec"]<2400 and r["link"]==10242 and r["time_sec"]-t<=5.1),None)
            if not (current_north or connector):break
            prefix.append(dict(vehicle=v,time=t,route_proof="current_next_link" if current_north else "observed_connector_after_head"))
        n=len(prefix)
        evidence.append(dict(start=start,end=end,queue_frame=t0,stable_prefix_queue=queue,
            head_events=len(events),prefix=prefix,eligible=n>=3,
            startup_inclusive_rate_veh_h=3600*n/(prefix[-1]["time"]-start) if n else None))
    eligible=[r for r in evidence if r["eligible"]]
    pairs=[dict(starts=[a["start"],b["start"]],rate=min(a["startup_inclusive_rate_veh_h"],b["startup_inclusive_rate_veh_h"]))
        for a,b in zip(eligible,eligible[1:])]
    support=max(pairs,key=lambda x:x["rate"]) if pairs else None
    pins={str(p):sha(p) for p in (Path(__file__),H/"sc12w_service/past_fzp_slice.json",H/"sc12w_service/typed_support_v3.json",ldp_path)}
    pins.update(heads.PINS)
    output=dict(status="past_prefix_support_evaluated",window=[1800,2400],cutoff_exclusive=True,
        algorithm="Max of adjacent qualified green-pair minima, same startup-inclusive support estimator as SC101. >=3 route-typed consecutive head crossers in the stable pre-green queue; no speed coefficient fit.",
        stability="same lane/link over preceding5s, displacement<=1m; queue gap<=15m from head backwards",
        rows=evidence,selected_support=support,previous_partial_green_average=960,
        source_pins=pins,validation_inputs_used=False,new_fzp_scans=0,new_native=0,
        limits=["5s stopped-queue and connector sampling can censor prefixes.",
                "Achieved startup-inclusive support remains a lower-bound capacity witness, not a universal upper bound.",
                "The shared lane also permits straight traffic; route proof is required for every prefix vehicle."])
    (HERE/"past_prefix_support.json").write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("PAST_PREFIX",[(r["start"],len(r["stable_prefix_queue"]),len(r["prefix"]),r["startup_inclusive_rate_veh_h"]) for r in evidence])
    print("SUPPORTED",support)
if __name__=="__main__":main()

