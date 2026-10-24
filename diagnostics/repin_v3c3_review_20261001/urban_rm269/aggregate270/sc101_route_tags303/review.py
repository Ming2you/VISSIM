"""Review303 conservation, route response, and remaining SC101 service masking."""
from collections import defaultdict,Counter
from datetime import datetime,timezone
import gzip,hashlib,json
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.source_service300.audit import replay,summary

HERE=Path(__file__).resolve().parent
A=HERE.parent;ROOT=HERE.parents[4]
OUT=Path("E:/VISSIM_analysis/20261010_sc101_route_tags303/forecast2400")
OLD=Path("E:/VISSIM_analysis/20261010_sc101_peeloff302/forecast2400")
M="SC101_S_SC1_to_N_SC2005";SRC="movement:"+M
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf8")

def main():
    assert not (HERE/"comparison.json").exists()
    new=read(OUT/"summary.json");old=read(OLD/"summary.json")
    support=read(HERE/"support.json")
    audit=read(A/"sc101_clock299/assessment.json")
    prior=read(A.parent/"sc101_recombined/forecast2400/candidate_application.json")
    assert max(prior["support"]["end_sec"])<2400
    assert new["status"]=="complete" and new["forecasts"]==2 and new["initial_state_error"]==0
    pins={}
    for report in (new,support):
        for p,h in report["source_pins"].items():assert sha(p)==h,p
        pins.update(report["source_pins"])
    arms={};conditional={}
    for arm in ("hold","city"):
        nr=new["results"][arm]
        assert nr["writer_three_blocks"] and nr["conservation_states"]==4
        assert nr["resource_max_exceedance"]<1e-7 and nr["shared_constraints"]["feasible"]
        responses={}
        for label,folder in (("old",OLD),("new",OUT)):
            p=folder/(arm+".response.json.gz");pins[str(p)]=sha(p)
            responses[label]=json.loads(gzip.decompress(p.read_bytes()))
            assert responses[label]["model_constraint_coverage"]["complete"]
        incoming={}
        for label,r in responses.items():
            incoming[label]=Counter()
            for t in r["transfers"]:
                if t["source"] in ("storage:native_1086_choice","storage:native_1087_choice") and t["target"]=="storage:SC1_to_SC101":
                    incoming[label][t["source"],t["start_sec"]]+=t["vehicles"]
        difference=max(abs(incoming["old"][k]-incoming["new"][k]) for k in incoming["old"].keys()|incoming["new"].keys())
        assert difference<1e-7
        tags=read(OUT/(arm+".route_tags.json"))
        for tag in tags:
            pending={k:sum(r[k] for entries in tag["pending"].values() for r in entries.values()) for k in tag["scheduled"]}
            for k in pending:
                assert abs(tag["scheduled"][k]-tag["matured"][k]-pending[k])<1e-7
        assert abs(sum(incoming["new"].values())-sum(tags[-1]["scheduled"].values()))<1e-7
        movements={}
        for kind,m in support["movements"].items():
            movements[kind]={}
            for label,r in responses.items():
                ts=[t for t in r["transfers"] if t["source"]=="movement:"+m and t["target"]!=t["source"]]
                movements[kind][label]=[sum(t["vehicles"] for t in ts if s<=t["start_sec"]<s+150) for s in (2400,2550,2700)]
        r=responses["new"]
        initial=r["initial_freeway_operands"]["urban_movement_queue"][M]
        resources={(x["start_sec"],x["resource"],x["kind"]):x for x in r["resource_allocations"]
                   if x["resource"] in (M,"storage:SC101_to_SC2005")}
        arrivals=defaultdict(float)
        for t in r["transfers"]:
            if t["target"]==SRC and t["source"]!=SRC:arrivals[t["start_sec"]]+=t["vehicles"]
        greens={t["sec"]:t["green_sec"] for b in audit["model"][arm]["blocks"] for t in b["ticks"]}
        rows=[]
        for t in range(2400,2850,10):
            rec=resources[t,"storage:SC101_to_SC2005","regular_receiving"]
            other=rec["accepted_total_veh"]-rec["accepted_by_source_veh"].get(SRC,0.)
            rows.append(dict(sec=t,arrivals=arrivals[t],green_sec=greens[t],
                receiving_for_this_movement=max(0.,rec["available_veh"]-other)))
        base=replay(rows,initial,prior["before_veh_h"])
        errors=[max(abs(t["ready"]-resources[t["sec"],M,"urban_movement_stock"]["available_veh"]),
                    abs(t["accepted"]-resources[t["sec"],M,"urban_movement_intended_limit"]["accepted_total_veh"])) for t in base]
        assert max(errors)<1e-7
        alt=replay(rows,initial,prior["after_veh_h"])
        native=[b["count"] for b in audit["native"][arm]["blocks"]]
        conditional[arm]=dict(base=summary(base,native),past_supported_capacity=summary(alt,native),
            max_original_reproduction_error=max(errors),past_rate_veh_h=prior["after_veh_h"])
        arms[arm]=dict(old_omega=old["results"][arm]["omega_ttt_veh_h"],new_omega=nr["omega_ttt_veh_h"],
            route_departure=movements,source_flow_max_change=difference,
            tagged_amount_veh=sum(tags[-1]["scheduled"].values()),final_category_totals=tags[-1],
            constraints_feasible=True,resource_max_exceedance=nr["resource_max_exceedance"],
            writer_three_blocks=True,conservation_states=4,endpoint_wall_sec=nr["wall_sec"])
        pins[str(OUT/(arm+".route_tags.json"))]=sha(OUT/(arm+".route_tags.json"))
    cd={mode:conditional["city"][mode]["head_time_cost"]-conditional["hold"][mode]["head_time_cost"]
        for mode in ("base","past_supported_capacity")}
    old_delta=arms["city"]["old_omega"]-arms["hold"]["old_omega"]
    delta=arms["city"]["new_omega"]-arms["hold"]["new_omega"]
    for p in (OUT/"summary.json",OLD/"summary.json",HERE/"support.json",HERE/"tests.log",Path(__file__),
              A/"sc101_clock299/assessment.json",A/"source_service300/audit.py",
              A.parent/"sc101_recombined/forecast2400/candidate_application.json",
              OUT.parent/"citysplit287_migration.json"):
        pins[str(p)]=sha(p)
    report=dict(status="complete_aggregate_source_route_tags_city_gain_unqualified",goal_complete=False,
        arms=arms,old_city_minus_hold_veh_h=old_delta,new_city_minus_hold_veh_h=delta,
        native_city_minus_hold_veh_h=5.28666666666649,
        conditional_service_replay=conditional,conditional_head_time_delta=cd,source_pins=pins,
        budget=dict(full450_forecasts=2,conditional_local_replays=4,optimizer=0,full_ad=0,native=0,fzp_scans=0,new_service_fit=0),
        limits=["Known-route proportions are past empirical support; unresolved mass keeps the existing beta as an explicit prior.",
                "Current/initial stocks and reservations are not re-routed; only new accepted north flow is tagged.",
                "The local replay fixes predicted arrivals and other receiving demand and is not an autonomous full-network result.",
                "Full city gain is still opposite. No independently held-out or full SDMPC/native adoption claim.",
                "Synthetic active-derivative split test passed; this is not a full-AD equivalence certificate."])
    save(HERE/"comparison.json",report)
    print("GAIN303",old_delta,delta,"native",report["native_city_minus_hold_veh_h"])
    print("CONDITIONAL_HEAD_TIMING",cd)
    for arm,data in conditional.items():
        print(arm,"conditional high service",[r["accepted"] for r in data["past_supported_capacity"]["blocks"]],
              "MAE",data["base"]["head_mae"],data["past_supported_capacity"]["head_mae"])
    print("TAGGED",arms["hold"]["tagged_amount_veh"],"source flow changes",[arms[k]["source_flow_max_change"] for k in arms])

if __name__=="__main__":main()

