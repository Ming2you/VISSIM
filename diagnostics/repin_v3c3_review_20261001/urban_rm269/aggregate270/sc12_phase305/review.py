"""Review one SC12 service candidate without further forecasts or fitting."""
from pathlib import Path
from collections import Counter
import gzip,hashlib,json,pickle
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.matched280.review import model_boundary
HERE=Path(__file__).resolve().parent;A=HERE.parent;H=A.parent
OUT=Path("E:/VISSIM_analysis/20261010_sc12_phase305/forecast2400")
OLD=Path("E:/VISSIM_analysis/20261010_sc101_service304/forecast2400")
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf8")
def main():
    assert not (HERE/"comparison.json").exists()
    new=read(OUT/"summary.json");old=read(OLD/"summary.json");truth=read(A/"cityresponse290/assessment.json")
    assert new["status"]=="complete" and new["forecasts"]==2 and new["initial_state_error"]==0
    for p,h in new["source_pins"].items():assert sha(p)==h,p
    cfg,_,_=pickle.loads((A/"citysplit287/forecast2400/initial.pickle").read_bytes())
    initial=read(A/"matched280/authority/hold.stocks.json")[0]
    arms={};boundaries={};pins={}
    wanted={"movement:SC6_S_SC12_to_N_SC103","movement:SC6_S_SC12_to_E_SC104"}
    west={"movement:SC12_W_SC11_to_N_SC6","movement:SC12_W_to_N_SC6"}
    for version,folder,doc in (("old",OLD,old),("new",OUT,new)):
        boundaries[version]={}
        for arm in ("hold","city"):
            v=doc["results"][arm]
            assert v["writer_three_blocks"] and v["shared_constraints"]["feasible"]
            assert v["resource_max_exceedance"]<1e-7 and v["conservation_states"]==4
            path=folder/(arm+".response.json.gz");pins[str(path)]=sha(path)
            r=json.loads(gzip.decompress(path.read_bytes()))
            assert r["model_constraint_coverage"]["complete"] and r["conditional_model_feasibility_witness"]
            rows=[t for t in r["transfers"] if t["source"] in wanted and t["source"]!=t["target"]]
            counts=[sum(t["vehicles"] for t in rows if s<=t["start_sec"]<s+150) for s in (2400,2550,2700)]
            native=[x["actual"] for x in truth["head_counts"][arm] if x["group"]=="SC6_S" and x["phase"]=="p1"]
            westrows=[t for t in r["transfers"] if t["source"] in west and t["target"]=="storage:SC12_to_SC6"]
            headcost=-sum(t["vehicles"]*(2850-t["start_sec"])/3600 for t in rows)
            final={"stocks":{k:dict(inside=n) for k,n in r["residence"][-1]["inside_veh"].items()}}
            boundary=model_boundary(r,[initial,final],v["omega_ttt_veh_h"],cfg);boundaries[version][arm]=boundary
            west_limits=[x for x in r["resource_allocations"] if "1220012103:10242:p4:typed" in x["resource"]]
            if version=="new":
                assert west_limits,"Missing shared physical service evidence"
                assert all(x["accepted_total_veh"]<=x["available_veh"]+1e-7 for x in west_limits)
            arms.setdefault(arm,{})[version]=dict(omega_ttt=v["omega_ttt_veh_h"],sc6_p1_blocks=counts,
                sc6_native_blocks=native,sc6_mae=sum(abs(a-b) for a,b in zip(counts,native))/3,
                sc6_head_time_cost=headcost,west_discharge=sum(t["vehicles"] for t in westrows),
                west_blocks=[sum(t["vehicles"] for t in westrows if s<=t["start_sec"]<s+150) for s in (2400,2550,2700)],
                final_omega_stock=sum(r["residence"][-1]["inside_veh"].values()),
                shared_west_resource_rows=len(west_limits),model_feasible=True,conservation=True,
                model_boundary_totals={k:sum(v.get(k,0) for v in boundary["routes"].values()) for k in ("entered","departed","generated_inside","entry_cost","departure_cost","generation_cost")},
                endpoint_wall_seconds=v["wall_sec"])
    deltas={mode:arms["city"][mode]["omega_ttt"]-arms["hold"][mode]["omega_ttt"] for mode in ("old","new")}
    head_deltas={mode:arms["city"][mode]["sc6_head_time_cost"]-arms["hold"][mode]["sc6_head_time_cost"] for mode in ("old","new")}
    departures={mode:sum(arms["city"][mode]["sc6_p1_blocks"])-sum(arms["hold"][mode]["sc6_p1_blocks"]) for mode in ("old","new")}
    routes={}
    for version in boundaries:
        bb=boundaries[version]
        routes[version]={}
        for route in bb["city"]["routes"].keys()|bb["hold"]["routes"].keys():
            delta={k:bb["city"]["routes"].get(route,{}).get(k,0)-bb["hold"]["routes"].get(route,{}).get(k,0) for k in ("entry_cost","departure_cost","generation_cost")}
            if max(abs(x) for x in delta.values())>1e-9:routes[version][route]=delta
        assert abs(sum(sum(v.values()) for v in routes[version].values())-deltas[version])<1e-7
    for p in (OUT/"summary.json",OLD/"summary.json",HERE/"assessment.json",HERE/"past_shared_prefix_support.json",
        HERE/"tests.log",Path(__file__),A/"cityresponse290/assessment.json",A/"matched280/review.py",
        A/"matched280/authority/hold.stocks.json",A/"citysplit287/forecast2400/initial.pickle"):
        pins[str(p)]=sha(p)
    result=dict(status="complete_sc12_shared_prefix_pair",goal_complete=False,arms=arms,
        omega_delta_veh_h=deltas,native_omega_delta_veh_h=5.28666666666649,
        sc6_head_time_delta=head_deltas,sc6_cumulative_discharge_delta=departures,
        native_sc6_cumulative_discharge_delta=-34,native_sc6_head_time_delta_bounds=[2.346,2.387667],
        model_boundary_routes=routes,source_pins=pins,
        budget=dict(full450_forecasts=2,new_effective_rate=1,optimizer=0,ad=0,native=0,fzp_scans=0),
        limits=["One historical queued head prefix supports effective north service; not a universal capacity or full lane scheduler.",
                "SC6 head-time cost is not identical to Omega exit contribution.",
                "Fixed actual city commands on one development state; no full controller/native gain qualification.",
                "Preserved initial state, actual receiving, routes, physical service pool, writer and NP/NUF."])
    save(HERE/"comparison.json",result)
    print("OMEGA",deltas,"native",result["native_omega_delta_veh_h"])
    print("SC6_HEAD_DELTA",head_deltas,"cumulative",departures)
    print("ARMS",{a:{v:{k:d[k] for k in ("sc6_p1_blocks","sc6_native_blocks","sc6_mae","west_blocks","shared_west_resource_rows")} for v,d in x.items()} for a,x in arms.items()})
if __name__=="__main__":main()

