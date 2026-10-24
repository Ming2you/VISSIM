"""Freeze two scoped aggregate-route forecasts from the completed302 runner."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
A=HERE.parent;OLD=A/"sc101_peeloff302"
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    assert not (HERE/"run.py").exists()
    log=(HERE/"tests.log").read_text(encoding="utf8")
    assert "Ran 4 tests" in log and "\nOK" in log and "FAILED" not in log
    cfg=json.loads((OLD/"config.json").read_bytes())
    cfg["diagnostic_source_route_tags"]="past_known_categories_unresolved_baseline_prior"
    cfg["support"]="sc101_route_tags303/support.json"
    (HERE/"config.json").write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    code=(OLD/"run_e.py").read_text(encoding="utf8")
    replace={
        "from candidate import hook, validate_turns, west, east, MOV":"from candidate import hook, validate_turns, west, east, MOV, verify_pending, ATTR",
        "OUT=Path('E:/VISSIM_analysis/20261010_sc101_peeloff302/forecast2400')":"OUT=Path('E:/VISSIM_analysis/20261010_sc101_route_tags303/forecast2400')",
        "HERE/'evidence.json'":"A/'sc101_peeloff302/evidence.json',A/'sc101_peeloff302/candidate.py',HERE/'support.json'",
        "HERE/'preflight_e.json'":"HERE/'preflight.json'",
        "for current in (state,*point.states):get_ledger(current).assert_stocks(model_inventory(current,cfg))":
            "for current in (state,*point.states):\n"
            "                    get_ledger(current).assert_stocks(model_inventory(current,cfg))\n"
            "                    verify_pending(current)\n"
            "                route_tag_states=[getattr(s,ATTR,{}) for s in point.states]\n"
            "                assert all(s.get('receipts',0)>0 for s in route_tag_states)\n"
            "                save(arm+'.route_tags.json',route_tag_states)",
        "'SC101_PEELOFF302'":"'SC101_SOURCE_TAGS303'",
        "sc101_peeloff302=True,":"sc101_peeloff302=True,aggregate_source_tags303=True,"
    }
    for before,after in replace.items():
        assert code.count(before)==1,(before,code.count(before))
        code=code.replace(before,after)
    compile(code,str(HERE/"run.py"),"exec")
    (HERE/"run.py").write_text(code,encoding="utf8")
    files=[HERE/"candidate.py",HERE/"support.json",HERE/"test_candidate.py",HERE/"tests.log",HERE/"config.json",
           HERE/"plan.json",HERE/"run.py",Path(__file__),OLD/"run_e.py"]
    (HERE/"preflight.json").write_text(json.dumps(dict(status="pass",unit_tests=4,
        unresolved_policy="Prior assumption, not observed route probability",
        budget=dict(fixed450=2,new_optimizer=0,new_native=0,new_fzp_scan=0,new_service_fit=0),
        source_pins={str(p):sha(p) for p in files}),indent=2)+"\n",encoding="utf8")
    print("PREPARED303 two autonomous450 predictions; aggregate tags with explicit unresolved mass")

if __name__=="__main__":main()

