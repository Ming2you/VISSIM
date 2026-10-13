"""Compare completed integrated304 with303; no further predictions."""
import gzip,hashlib,json
from pathlib import Path
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent
A=HERE.parent
OUT=Path("E:/VISSIM_analysis/20261010_sc101_service304/forecast2400")
OLD=Path("E:/VISSIM_analysis/20261010_sc101_route_tags303/forecast2400")
M="SC101_S_SC1_to_N_SC2005";SRC="movement:"+M
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf8")

def main():
    assert not (HERE/"comparison.json").exists(), "Preserve completed review"
    new=read(OUT/"summary.json");old=read(OLD/"summary.json")
    assert new["status"]=="complete" and new["forecasts"]==2 and new["initial_state_error"]==0
    for p,h in new["source_pins"].items():assert sha(p)==h,p
    application=read(OUT/"candidate_application.json")
    assert max(application["support"]["end_sec"])<2400
    assert application["before_veh_h"]==2969.5492252308654
    assert application["after_veh_h"]==5236.47858772522
    native=read(A/"sc101_clock299/assessment.json")["native"]
    arms={};responses={}
    for label,folder,doc in (("old",OLD,old),("new",OUT,new)):
        responses[label]={}
        for arm in ("hold","city"):
            result=doc["results"][arm]
            assert result["writer_three_blocks"] and result["conservation_states"]==4
            assert result["shared_constraints"]["feasible"] and result["resource_max_exceedance"]<1e-7
            r=json.loads(gzip.decompress((folder/(arm+".response.json.gz")).read_bytes()))
            assert r["model_constraint_coverage"]["complete"] and r["conditional_model_feasibility_witness"]
            out=[t for t in r["transfers"] if t["source"]==SRC and t["target"]!=SRC]
            blocks=[sum(t["vehicles"] for t in out if s<=t["start_sec"]<s+150) for s in (2400,2550,2700)]
            cost=result["costs_by_stock"]
            components={prefix:sum(v for k,v in cost.items() if k.startswith(prefix+":"))
                for prefix in ("freeway","ramp","movement","storage","transit","origin","merge_pending")}
            assert abs(sum(components.values())-result["omega_ttt_veh_h"])<1e-7
            queue=r["residence"][-1]["model_stock_veh"][SRC]
            incoming=sum(t["vehicles"] for t in r["transfers"] if t["target"]==SRC and t["source"]!=SRC)
            initial=r["initial_freeway_operands"]["urban_movement_queue"][M]
            assert abs(initial+incoming-sum(blocks)-queue)<1e-7
            responses[label][arm]=r
            arms.setdefault(arm,{})[label]=dict(
                omega_ttt_veh_h=result["omega_ttt_veh_h"],cost_by_stock_class=components,
                sc101_discharge_blocks=blocks,sc101_discharge=sum(blocks),
                sc101_initial_queue=initial,sc101_arrivals=incoming,sc101_end_queue=queue,
                omega_inside_stock_at2850=sum(r["residence"][-1]["inside_veh"].values()),
                ramp_accepted_merges=result["predicted_merge"]["accepted_vehicles_by_ramp"],
                model_feasible=True,writer_three_blocks=True,resource_max_exceedance=result["resource_max_exceedance"],
                endpoint_seconds=result["wall_sec"])
        for arm in arms:
            arms[arm]["native_sc101_blocks"]=[b["count"] for b in native[arm]["blocks"]]
    native_delta=5.28666666666649
    delta={mode:arms["city"][mode]["omega_ttt_veh_h"]-arms["hold"][mode]["omega_ttt_veh_h"] for mode in ("old","new")}
    discharge_delta={mode:arms["city"][mode]["sc101_discharge"]-arms["hold"][mode]["sc101_discharge"] for mode in ("old","new")}
    component_delta={mode:{k:arms["city"][mode]["cost_by_stock_class"][k]-arms["hold"][mode]["cost_by_stock_class"][k] for k in arms["hold"][mode]["cost_by_stock_class"]} for mode in ("old","new")}
    stock_change=[]
    for k in set(new["results"]["hold"]["costs_by_stock"])|set(new["results"]["city"]["costs_by_stock"]):
        val=lambda doc,arm:doc["results"][arm]["costs_by_stock"].get(k,0.)
        nd=val(new,"city")-val(new,"hold");od=val(old,"city")-val(old,"hold")
        if abs(nd-od)>1e-9:stock_change.append(dict(stock=k,previous_delta=od,current_delta=nd,increment=nd-od))
    stock_change.sort(key=lambda x:abs(x["increment"]),reverse=True)
    pins={str(p):sha(p) for p in [OUT/"summary.json",OLD/"summary.json",OUT/"candidate_application.json",Path(__file__),A/"sc101_clock299/assessment.json"]}
    pins.update({str(folder/(arm+".response.json.gz")):sha(folder/(arm+".response.json.gz")) for folder in (OLD,OUT) for arm in ("hold","city")})
    report=dict(status="complete_integrated_service_pair",goal_complete=False,arms=arms,
        city_minus_hold_omega_veh_h=delta,native_city_minus_hold_omega_veh_h=native_delta,
        direction_matched=delta["new"]>0,absolute_gain_error_old=abs(delta["old"]-native_delta),
        absolute_gain_error_new=abs(delta["new"]-native_delta),
        sc101_cumulative_discharge_city_minus_hold=discharge_delta,
        native_sc101_cumulative_discharge_city_minus_hold=-9,
        component_delta=component_delta,largest_delta_changes=stock_change[:20],
        future_observation_inputs=False,initial_state_error=0,source_pins=pins,
        budget=dict(full450_forecasts=2,new_fit=0,full_ad=0,optimizer=0,native=0,fzp_scans=0),
        limits=["Past achieved head rate is support, not a universal saturation guarantee.",
                "Native head crossings can include later turns; not an exact final-route census.",
                "Two autonomous fixed-command forecasts at one development state; not full SDMPC or independent validation.",
                "Endpoint timings exclude setup, file reads and optimization.",
                "City-only actual command pair; this is not an isolated RM treatment."])
    save(HERE/"comparison.json",report)
    print("GAIN304",delta,"native",native_delta)
    print("SC101 cumulative discharge delta",discharge_delta,"native",-9)
    print("ERROR",report["absolute_gain_error_old"],report["absolute_gain_error_new"])
    for arm,data in arms.items():
        print(arm,"discharge",data["new"]["sc101_discharge_blocks"],"end queue",data["new"]["sc101_end_queue"],"final Omega",data["new"]["omega_inside_stock_at2850"])
    print("COMPONENT_DELTA",component_delta)

if __name__=="__main__":main()

