"""Build bounded fixed-command comparison from completed301 runner."""
import hashlib,json
from pathlib import Path

HERE=Path(__file__).resolve().parent
A=HERE.parent
OLD=A/"sc15_source301"
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert not (HERE/"run.py").exists() and not (HERE/"forecast2400").exists()
    log=(HERE/"tests.log").read_text(encoding="utf8")
    assert "Ran 4 tests" in log and "\nOK" in log and "FAILED" not in log
    cfg=json.loads((OLD/"config.json").read_bytes())
    cfg["diagnostic_sc101_peeloff"]="before_all_source_heads"
    (HERE/"config.json").write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    code=(OLD/"run.py").read_text(encoding="utf8")
    replacements={
        "from candidate import hook, validate_turns, west, east":"from candidate import hook, validate_turns, west, east, MOV",
        "HERE/'calibration.json'":"A/'sc15_source301/calibration.json',A/'sc15_source301/candidate.py',HERE/'evidence.json'",
        "assert cfg.network.urban_movements==oldcfg.network.urban_movements":
            "expected_movements=copy.deepcopy(oldcfg.network.urban_movements)\n"
            "            expected_movements[MOV]['unsignalized']=True\n"
            "            assert cfg.network.urban_movements==expected_movements\n"
            "            assert cfg.network.movement_capacity_by_movement_veh_h[MOV]==oldcfg.network.movement_capacity_by_movement_veh_h[MOV]\n"
            "            for field,key in (('local_service_pool','groups'),('head_service_resources','resources')):\n"
            "                assert not any(MOV in str(group) for group in getattr(cfg.network,field,{}).get(key,{}).values())",
        "sc15_source301=cfg.network.sc15_source301))":
            "sc15_source301=cfg.network.sc15_source301,sc101_peeloff302=cfg.network.sc101_peeloff302))",
        "'SC15_SOURCE_SERVICE'":"'SC101_PEELOFF302'",
        "sc15_source_service=True,":"sc15_source_service=True,sc101_peeloff302=True,",
        "fits=2,":"fits=0,inherited_source_rates=2,"
    }
    for before,after in replacements.items():
        assert code.count(before)==1,(before,code.count(before))
        code=code.replace(before,after)
    compile(code,str(HERE/"run.py"),"exec")
    (HERE/"run.py").write_text(code,encoding="utf8")
    files=[HERE/"candidate.py",HERE/"test_candidate.py",HERE/"tests.log",HERE/"config.json",
           HERE/"evidence.json",HERE/"plan.json",HERE/"run.py",Path(__file__),OLD/"run.py"]
    (HERE/"preflight.json").write_text(json.dumps(dict(status="pass",unit_tests=4,
        bounded_candidate="SC101 false source signal gating only; existing finite service, demand and routing retained",
        budget=dict(fixed450=2,full_optimizer=0,ad=0,native=0,new_fits=0),
        source_pins={str(p):sha(p) for p in files}),indent=2)+"\n",encoding="utf8")
    print("PREPARED302: two fixed450 forecasts; four tests; no new coefficients")


if __name__=="__main__":main()

