"""Source-pinned physical peeloff evidence; read small caches, no FZP scan."""
import gzip,hashlib,json,pickle
from collections import defaultdict,Counter
from pathlib import Path
import xml.etree.ElementTree as ET
from evaluation.controllers.physical_movement_routes import load_evidence
from diagnostics.validate_native_signal_record import read_ldp_frames

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4];A=HERE.parent
MOV="SC101_S_SC1_to_E_SC5"
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert not (HERE/"evidence.json").exists()
    cfg,state,_=pickle.loads((A/"citysplit287/forecast2400/initial.pickle").read_bytes())
    tuning=read(A/"flow279/config_10686_free.json")
    authority=tuning["urban"]["movements"]["physical_phase_authority"]
    doc,routes,edges=load_evidence(authority)
    network=ROOT/doc["network"]["path"]
    tree=ET.parse(network).getroot()
    links={x.get("no"):x for x in tree.findall("./links/link")}
    expected_spec=cfg.network.urban_movements[MOV]
    assert not expected_spec.get("unsignalized")
    path=["1220011503","10528","336"]
    assert all(e in edges for e in zip(path,path[1:]))
    conn=links["10528"]
    start,end=conn.find("fromLinkEndPt"),conn.find("toLinkEndPt")
    connector=dict(id="10528",source_lane=int(start.get("lane").split()[1]),
        source_pos=float(start.get("pos")),target_lane=int(end.get("lane").split()[1]),
        target_pos=float(end.get("pos")),lanes=len(conn.findall("./lanes/lane")))
    heads=[]
    for h in tree.findall("./signalHeads/signalHead"):
        link=h.get("lane").split()[0]
        assert link not in path[1:],"Unsupported head on peeloff"
        if link!=path[0]:continue
        heads.append(dict(head=h.get("no"),link=link,lane=int(h.get("lane").split()[1]),
            pos_m=float(h.get("pos")),SC="SC"+h.get("sg").split()[0],SG=h.get("sg").split()[1],
            all_vehicle_types=h.get("allVehTypes")=="true",compliance=float(h.get("complRate",1))))
    assert len(heads)==5 and all(h["pos_m"]>connector["source_pos"] for h in heads)
    assert all(h["SC"]=="SC101" and h["all_vehicle_types"] and h["compliance"]==1 for h in heads)
    matching={}
    for key,route in routes.items():
        for i in range(len(route["path"])-2):
            if route["path"][i:i+3]!=path:continue
            entry=float(route["decision"]["pos"]) if i==0 else float(links[route["path"][i-1]].find("toLinkEndPt").get("pos"))
            assert 0<=entry<=connector["source_pos"]
            assert route["decision"]["allVehTypes"]=="true" and route["decision"]["routeChoiceMeth"]=="STATIC"
            matching[key]=dict(path=route["path"],decision=route["decision"],entry_position_m=entry)
    assert matching
    support=cfg.network.control_area_routes["movement:"+MOV]
    assert support["status"]=="unique" and support["physical_turns"][0]["connector"]=="10528"
    assert support["physical_turns"][0]["destination_support_paths"]==[["336","10529","1210014303"]]
    conflicts={x.get("no"):{k:x.get(k) for k in ("link1","link2","status")} for x in tree.findall("./conflictAreas/conflictArea")
               if x.get("link1") in ("10528","336","10529") or x.get("link2") in ("10528","336","10529")}
    assert conflicts["1393"]["status"]=="TWOYIELDSONE"
    cache_done=read("E:/VISSIM_analysis/20261010_sc15_source301_past/completion.json")
    cache_path=Path(cache_done["cache"]);assert sha(cache_path)==cache_done["cache_sha256"]
    cache=json.loads(gzip.decompress(cache_path.read_bytes()))
    ldp_path=Path(cache["source"]).parent/"sdmpc31_g_2400_hold_s29_101_001.ldp"
    ldp=read_ldp_frames({101:ldp_path},{101:list(range(1,9))},900,2396)
    tracks=defaultdict(list)
    for f in cache["frames"]:
        for r in f["rows"]:tracks[r[0]].append((f["sec"],r))
    witness=[]
    for veh,track in tracks.items():
        for (t0,r0),(t1,r1) in zip(track,track[1:]):
            if r0[1]!=1220011503 or r0[3]>connector["source_pos"] or r1[1] not in (10528,336) or t1-t0>5.01:continue
            # Whole bracket, not just endpoint colour.
            colours=sorted({ldp["frames"][sec]["101:8"] for sec in range(int(t0),int(t1)+1)})
            witness.append(dict(veh=veh,lower_sec=t0,upper_sec=t1,sg8_colours=colours,
                before=dict(link=r0[1],lane=r0[2],pos_m=r0[3]),after=dict(link=r1[1],lane=r1[2],pos_m=r1[3])))
            break
    counts=Counter(tuple(x["sg8_colours"]) for x in witness)
    assert counts[("RED",)]>0,"Geometry proof lacks expected saved RED witness"
    plan_path=ROOT/doc["selected_plan"]["path"]
    assert sha(plan_path)==doc["selected_plan"]["sha256"]
    selected=read(plan_path)
    assert "8" in selected["controllers"]["101"]["phase_signal_groups"]["p1"]
    paths=[network,plan_path,ROOT/authority,cache_path,ldp_path,HERE/"plan.json",Path(__file__),
           A/"citysplit287/forecast2400/initial.pickle",A/"sc15_source301/completion.json",
           A.parent.parent/"upstream_worklog/02_urban_b2/impl/STAGE3.md",
           A.parent.parent/"upstream_worklog/02_urban_b2/diag_c3_r2/U7.md"]
    evidence=dict(schema="sc101-prehead-peeloff302/v1",status="physical_authority_confirmed",
        network=doc["network"],selected_plan=doc["selected_plan"],base_authority=authority,
        movement=MOV,expected_spec=expected_spec,path=path,connector=connector,
        source_heads=heads,native_routes=matching,receiver_support=support,
        existing_capacity_veh_h=cfg.network.movement_capacity_by_movement_veh_h[MOV],
        conflicts=conflicts,native_past_witnesses=witness,
        native_past_bracket_counts={",".join(k):v for k,v in counts.items()},
        source_pins={str(p):sha(p) for p in paths},goal_complete=False,
        limits=["Remove source signal gating only; downstream10529 yields and finite receiving still matter.",
                "Do not promote absence of a signal head into unlimited service or a new fitted capacity.",
                "Past native witnesses support signal authority, not whole-control causal gains."])
    (HERE/"evidence.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("PEELOFF302",matching.keys(),connector["source_pos"],"heads",[h["pos_m"] for h in heads])
    print("PAST_SC101_SG8_CROSSING_BRACKETS",dict(counts),"rate unchanged",evidence["existing_capacity_veh_h"])


if __name__=="__main__":main()
