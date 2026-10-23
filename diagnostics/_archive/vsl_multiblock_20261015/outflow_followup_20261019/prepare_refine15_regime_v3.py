"""Use the existing native fixed-replay execution proof, not online sentinels."""
from pathlib import Path
import json
A=Path(__file__).resolve().parent
old=A/'run_refine15_regime_fit_v2.py';new=A/'run_refine15_regime_fit_v3.py'
assert not new.exists()
failed=A/'refine15_regime_fit_v2';failed.mkdir(exist_ok=True)
if not (failed/'failure.json').exists():
    (failed/'failure.json').write_text(json.dumps(dict(stage='preflight',error='The fixed native replay does not use online action.json.applied sentinels.',new_forecasts=0,new_native=0,tool_observed_exit_code=1,source=str(old)),indent=2),encoding='utf8')
s=old.read_text(encoding='utf8')
def replace(old,new):
    global s
    assert s.count(old)==1,(old[:70],s.count(old))
    s=s.replace(old,new)
replace("O=A/'refine15_regime_fit_v2'", "O=A/'refine15_regime_fit_v3'")
replace("    # Qualify exact physical replay without substituting coordination budgets.", """    baseline_analysis=Path('E:/VISSIM_analysis/20261011_vsl_response349/causal_off2250_analysis_v2/native_analysis')
    closure=read(baseline_analysis/'runtime_closure.json')
    assert closure['all_owned_processes_closed'] and closure['owner_exit_code']==0 and closure['normal_native_end_sec']==2700
    execution=read(baseline_analysis/'hold/execution.json')
    assert execution['native_execution_passed']
    assert execution['checks']['actual_signal_readbacks']['passed'] and execution['checks']['actual_vsl_apply_readbacks']['passed']
    assert not execution['native_lsa_com_coverage_passed'],'Preserve approved LDP substitute and missing LSA'
    cache_receipt=read(HERE/'native_analysis_repaired_20261016/baseline_cache_receipt.json')
    for p,h in cache_receipt['pins'].items():assert sha(p)==h,p
    # Fixed replay has native execution/LDP/readbacks; online OFF has applied sentinels.
    # Qualify exact physical replay without substituting coordination budgets.""")
replace("            assert Path(str(path)+'.applied').is_file()\n", "            if folder==OBS:assert Path(str(path)+'.applied').is_file()\n")
replace("            assert Path(str(path)+'.applied').is_file(),str(path)", "            if at==2850:assert Path(str(path)+'.applied').is_file(),str(path)")
compile(s,str(new),'exec');new.write_text(s,encoding='utf8');print(new)
