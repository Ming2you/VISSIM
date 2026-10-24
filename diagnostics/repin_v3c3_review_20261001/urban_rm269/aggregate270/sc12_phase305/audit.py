"""Audit SC12 north departure phase/route authority from closed cached evidence."""
from collections import Counter,defaultdict
from pathlib import Path
import gzip,hashlib,importlib.util,json,math,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;A=HERE.parent;H=A.parent;ROOT=HERE.parents[4]
from diagnostics.validate_native_signal_record import read_ldp_frames
loader=importlib.util.spec_from_file_location("sc12_heads305",H/"sc12_source/audit.py")
heads=importlib.util.module_from_spec(loader);loader.loader.exec_module(heads)
heads.LINKS={"SC12_W":1220012103}
PINS={}
def pin(p):
    p=Path(p);b=p.read_bytes();PINS[str(p.resolve())]=hashlib.sha256(b).hexdigest();return b
def read(p):return json.loads(pin(p))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf8")

def main():
    assert not (HERE/"assessment.json").exists()
    previous=read(A/"sc101_service304/completion.json")
    assert previous["status"]=="complete_local_discharge_direction_improved_whole_city_gain_unqualified"
    witnesses=read(A/"sourcebalance297/assessment.json")
    network=ROOT/"diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx"
    tree=ET.fromstring(pin(network))
    head_specs={int(h.get("lane").split()[1]):dict(head=h.get("no"),sg=h.get("sg").split()[1],position=float(h.get("pos")))
        for h in tree.findall("./signalHeads/signalHead") if h.get("lane").split()[0]=="1220012103"}
    turns={n.get("no"):dict(source=n.find("fromLinkEndPt").attrib,target=n.find("toLinkEndPt").attrib,lanes=len(n.findall("./lanes/lane")))
        for n in tree.findall("./links/link") if n.find("fromLinkEndPt") is not None and n.find("fromLinkEndPt").get("lane").split()[0]=="1220012103"}
    assert head_specs[2]["sg"]=="5" and float(turns["10242"]["source"]["pos"])>head_specs[2]["position"]
    roots={"hold":Path("E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold"),
           "city":Path("E:/VISSIM_runs/20261010_urbanrm269_cityonly289_s29/selected")}
    results={}
    for arm,root in roots.items():
        label="hold" if arm=="hold" else "selected";stem=f"sdmpc31_g_2400_{label}_s29"
        folder=root/f"decisions_{stem}"
        frames=read_ldp_frames({12:root/"vissim_eval"/f"{stem}_12_001.ldp"},{12:list(range(1,9))},2390,2850)
        PINS.update({p:v["sha256"] for p,v in frames["pins"].items()})
        events=defaultdict(list);blocks=[];raw_counts=[]
        for end in (2400,2550,2700,2850):
            physical,rows=heads.heads_and_entries(folder,end)
            for lane,veh,t in rows["SC12_W"]:events[veh].append(dict(lane=lane,veh=veh,sec=t))
            raw_counts.append(dict(end=end,physical=physical["SC12_W"]))
        matches=[]
        for w in witnesses["native"][arm]["witnesses"]:
            if w["source"]!="west":continue
            possible=[e for e in events[w["vehicle"]] if w["previous_source_time"]-0.2<=e["sec"]<=w["first_north_time"]+0.2]
            rec=dict(witness=w,matched_events=possible)
            for e in possible:
                sec=int(math.floor(e["sec"]))
                e["head"]=head_specs[e["lane"]]["head"]
                e["lane_head_sg"]=head_specs[e["lane"]]["sg"]
                e["signal_at_floor"]={g:frames["frames"][sec][f"12:{g}"] for g in ("2","5")}
                e["signal_neighbors"]={str(t):{g:frames["frames"][t][f"12:{g}"] for g in ("2","5")}
                    for t in range(sec-1,sec+2) if t in frames["frames"]}
            matches.append(rec)
        counts=Counter()
        for rec in matches:
            if len(rec["matched_events"])!=1:counts["unresolved_or_multiple"]+=1
            else:
                e=rec["matched_events"][0];counts[f"lane{e['lane']}:{e['signal_at_floor']['5']}"]+=1
        model=json.loads(gzip.decompress(pin(Path("E:/VISSIM_analysis/20261010_sc101_service304/forecast2400")/(arm+".response.json.gz"))))
        members={"movement:SC12_W_SC11_to_N_SC6","movement:SC12_W_to_N_SC6"}
        model_transfer=[t for t in model["transfers"] if t["source"] in members and t["target"]=="storage:SC12_to_SC6"]
        for start in (2400,2550,2700):
            group=[w for w in matches if start<=w["witness"]["first_north_time"]<start+150]
            blockevents=[e for seq in events.values() for e in seq if start<=e["sec"]<start+150 and e["lane"]==2]
            blocks.append(dict(start=start,downstream_witnesses=len(group),
                matched_by_lane=dict(Counter(e["lane"] for w in group for e in w["matched_events"])),
                lane2_head_known_all_routes=len(blockevents),
                actual_green_sg5=sum(frames["frames"][t]["12:5"]=="GREEN" for t in range(start,start+150)),
                modeled_accepted_north=sum(t["vehicles"] for t in model_transfer if start<=t["start_sec"]<start+150)))
        results[arm]=dict(matches=matches,counts=dict(counts),blocks=blocks,head_rows=raw_counts)
        print(arm,"PHASE_MATCH",dict(counts),"BLOCKS",blocks)
    PINS.update(heads.PINS)
    pin(H.parent/"upstream_worklog/02_urban_b2/diag_c3_r2/U7.md")
    pin(H/"sc12w_service/README.md");pin(H/"sc12w_service/typed_support_v3.json");pin(Path(__file__))
    save(HERE/"assessment.json",dict(status="complete_cached_phase_authority_audit",previous_goal_turn="progress_integrated_SC101_pair",
        geometry=dict(heads=head_specs,connectors=turns),results=results,source_pins=PINS,
        budget=dict(new_native=0,new_forecasts=0,new_fzp_scans=0,new_fits=0),
        limits=["North-road first sightings and head times have different spatial boundaries.",
                "LDP gives one-second state; near-transition crossings must be treated separately.",
                "Known vehicle crossings are a subset when tail IDs are unresolved.",
                "Future records are diagnostic targets only; no predictor consumes them."],
        goal_complete=False))

if __name__=="__main__":main()

