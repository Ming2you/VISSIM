"""Prepare one pair changing only SC12W effective shared north service."""
import json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;A=HERE.parent;OLD=A/"sc101_service304"
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
def main():
    assert not (HERE/"run.py").exists()
    log=(HERE/"tests.log").read_text(encoding="utf8")
    assert "Ran 3 tests" in log and "OK" in log and "FAILED" not in log
    cfg=read(OLD/"config.json");cfg["diagnostic_sc12_north_service"]="past_shared_queued_head_prefix"
    save(HERE/"config.json",cfg)
    save(HERE/"plan.json",dict(status="prepared_one_candidate_pair",previous_goal_turn="progress_integrated_SC101_304",
        purpose="Correct use of incomplete mean flow as SC12 north hard service ceiling. One effective bound from past queued head prefix, including competing through/startup time.",
        support="One qualifying9-vehicle queued prefix,8 north and1 through; not a general shared-lane model.",
        budget=dict(fixed450=2,capacity_candidates=1,optimizer=0,ad=0,native=0,fzp=0),
        preserve=["FW5/urban10","450s horizon","terminalOFF","Omega701 TTT","same initial state/routes/lanes/demand/commands","finite receiving","one shared alias budget","live native queue unchanged"],
        goal_complete=False))
    code=(OLD/"run.py").read_text(encoding="utf8")
    changes={
        "from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc101_route_tags303.candidate import hook, validate_turns, west, east, MOV, verify_pending, ATTR":
            "from candidate import hook, validate_turns, west, east, MOV, verify_pending, ATTR",
        "OUT=Path('E:/VISSIM_analysis/20261010_sc101_service304/forecast2400')":
            "OUT=Path('E:/VISSIM_analysis/20261010_sc12_phase305/forecast2400')",
        "pins=dict(old['source_pins'])":
            "pins=dict(old['source_pins'])\n    for support_file in ('past_shared_prefix_support.json','assessment.json','tests.log'):\n        pins[str(HERE/support_file)]=sha(HERE/support_file)\n    pins.update(read(HERE/'past_shared_prefix_support.json')['source_pins'])",
        "validate_turns(cfg.network)":
            "validate_turns(cfg.network)\n"
            "            assert cfg.network.sc12_phase305['rate']==read(HERE/'past_shared_prefix_support.json')['selected_support']['rate']\n"
            "            assert cfg.network.local_service_pool['groups'][west.GROUP]['service_veh_h']==cfg.network.sc12_phase305['rate']\n"
            "            save('sc12_candidate_application.json',cfg.network.sc12_phase305)",
        "'SC101_SERVICE304'":"'SC12_SHARED_PREFIX305'",
        "fits=0,inherited_source_rates=2":"fits=1,inherited_source_rates=2",
        "sc101_past_service304=True,":"sc101_past_service304=True,sc12_shared_prefix305=True,"
    }
    for before,after in changes.items():
        assert code.count(before)==1,(before,code.count(before))
        code=code.replace(before,after)
    compile(code,str(HERE/"run.py"),"exec")
    (HERE/"run.py").write_text(code,encoding="utf8")
    files=[*HERE.glob("*.py"),HERE/"config.json",HERE/"plan.json",HERE/"tests.log",HERE/"assessment.json",
        HERE/"past_shared_prefix_support.json",OLD/"run.py",OLD/"completion.json"]
    save(HERE/"preflight.json",dict(status="pass",unit_tests=3,new_full_forecasts=2,
        warning="One past queue supports effective rate only. Keep diagnostic; do not claim fully identified saturation or shared-through dynamics.",
        source_pins={str(p):sha(p) for p in files}))
    print("PREPARED305 one capacity candidate, two autonomous450 forecasts")
if __name__=="__main__":main()

