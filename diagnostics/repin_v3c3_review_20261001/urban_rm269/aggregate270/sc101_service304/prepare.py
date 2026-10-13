"""One integrated pair; reuse the past SC101 rate without fitting or a grid."""
import copy,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
A=HERE.parent;H=A.parent
OLD=A/"sc101_route_tags303"
CAP=H/"sc101_recombined"
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+"\n",encoding="utf8")

def main():
    assert not (HERE/"run.py").exists(), "Do not overwrite prepared execution"
    done=read(OLD/"completion.json")
    assert done["status"]=="complete_aggregate_source_route_tags_city_gain_unqualified"
    assert done["budget"]["full450_forecasts"]==2
    evidence=read(CAP/"service_evidence.json")
    for p,h in evidence["source_pins"].items():
        assert sha(p)==h,p
    log=(OLD/"tests.log").read_text(encoding="utf8")
    assert "Ran 4 tests" in log and "\nOK" in log and "FAILED" not in log
    cfg=read(OLD/"config.json")
    cfg["diagnostic_sc101_service"]="reuse_past_queued_prefix_5236.47858772522"
    save(HERE/"config.json",cfg)
    save(HERE/"plan.json",dict(status="prepared_integrated_sc101_service_pair",
        purpose="Combine the existing past-only SC101 discharge support with source supply, unsignalized peeloff and aggregate route tags; judge whole-network feedback.",
        budget=dict(full450_forecasts=2,new_fit=0,parameter_grid=False,full_ad=0,optimizer=0,native=0,fzp_scans=0),
        preserve=["FW5 urban10","450-second horizon","terminal OFF","Omega701 TTT","same initial stocks, reservations and demand","finite receiving and vehicle conservation","existing frozen native queue"],
        goal_complete=False))
    code=(OLD/"run.py").read_text(encoding="utf8")
    edits={
        "from candidate import hook, validate_turns, west, east, MOV, verify_pending, ATTR":
            "from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc101_route_tags303.candidate import hook, validate_turns, west, east, MOV, verify_pending, ATTR\nfrom diagnostics.repin_v3c3_review_20261001.urban_rm269.sc101_recombined import candidate as service",
        "OUT=Path('E:/VISSIM_analysis/20261010_sc101_route_tags303/forecast2400')":
            "OUT=Path('E:/VISSIM_analysis/20261010_sc101_service304/forecast2400')",
        "HERE/'support.json'":"A/'sc101_route_tags303/support.json',A/'sc101_route_tags303/candidate.py',H/'sc101_recombined/candidate.py',H/'sc101_recombined/service_evidence.json'",
        "HERE/'tests.log'":"A/'sc101_route_tags303/tests.log'",
        "changed==set(west.MEMBERS)|set(east.MEMBERS),changed":
            "changed==set(west.MEMBERS)|set(east.MEMBERS),changed\n"
            "            before_service=dict(vars(cfg.network))\n"
            "            application=service.install(cfg,2400)\n"
            "            network_change={k for k,v in vars(cfg.network).items() if v is not before_service[k]}\n"
            "            assert network_change=={'movement_capacity_by_movement_veh_h'},network_change\n"
            "            cap_change={k for k,v in cfg.network.movement_capacity_by_movement_veh_h.items() if v!=before_service['movement_capacity_by_movement_veh_h'][k]}\n"
            "            assert cap_change=={service.MOVEMENT},cap_change\n"
            "            assert application['after_veh_h']==5236.47858772522\n"
            "            assert max(application['support']['end_sec'])<2400\n"
            "            save('candidate_application.json',application)\n"
            "            pins.update(read(H/'sc101_recombined/service_evidence.json')['source_pins'])",
        "'SC101_SOURCE_TAGS303'":"'SC101_SERVICE304'",
        "aggregate_source_tags303=True,":"aggregate_source_tags303=True,sc101_past_service304=True,"
    }
    for before,after in edits.items():
        assert code.count(before)==1,(before,code.count(before))
        code=code.replace(before,after)
    compile(code,str(HERE/"run.py"),"exec")
    (HERE/"run.py").write_text(code,encoding="utf8")
    files=[HERE/"config.json",HERE/"plan.json",HERE/"run.py",Path(__file__),
        OLD/"run.py",OLD/"candidate.py",OLD/"support.json",OLD/"tests.log",OLD/"completion.json",
        CAP/"candidate.py",CAP/"service_evidence.json",CAP/"preflight.json"]
    save(HERE/"preflight.json",dict(status="passed",new_tests=0,
        reused_route_tests=4,reused_service_tests=7,service_source_pins=len(evidence["source_pins"]),
        runtime_gates=["Only SC101 through rate changes beyond303","Right cap unchanged and unsignalized","Initial state and demand unchanged","Actual finite receiving","Three-block writer and NP/NUF","Conservation including route tags"],
        source_pins={str(p):sha(p) for p in files}))
    print("PREPARED304 two full450 forecasts; no refitting, optimizer, native, or FZP scan")

if __name__=="__main__":main()
