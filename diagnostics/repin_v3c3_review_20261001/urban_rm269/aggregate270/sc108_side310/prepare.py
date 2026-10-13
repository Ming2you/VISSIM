"""Reuse the qualified308 harness, adding only a single physical rate."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
source=HERE.parent/'sc109_composite308/run_v2.py'
text=source.read_text(encoding='utf8')
assert not (HERE/'run.py').exists()
text=text.replace('from candidate import install as install_sc109', 'from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_composite308.candidate import install as install_sc109\nfrom candidate import install as install_side')
text=text.replace('from inputs import inputs','from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_composite308.inputs import inputs')
text=text.replace('20261010_sc109_composite308/forecast2400_v2','20261010_sc108_side310/forecast2400')
text=text.replace("CASE/'tests_v2.log'","CASE/'tests.log'")
needle='            baseline_state=pickle.dumps(state,protocol=5)'
assert text.count(needle)==1
text=text.replace(needle,"            side_application=install_side(cfg,state.time_sec)\n            pins.update(side_application['source_pins'])\n            save('sc108_side_application.json',side_application)\n"+needle)
text=text.replace("sc109_application=sc109_application,changed_initial_fields", "sc109_application=sc109_application,sc108_side_application=side_application,changed_initial_fields")
text=text.replace("native_runs=0,fits=0,inherited_source_rates=3", "native_runs=0,fits=1,inherited_source_rates=3")
text=text.replace('SC109_COMPOSITE308','SC108_SIDE310')
(HERE/'run.py').write_text(text,encoding='utf8')
plan=dict(status='prepared',baseline='sc109_composite308',candidate='SC108_side_past_achieved_service_floor',
    preserved=['FW5/urban10','450s horizon','terminalOFF','sameOmega701','sameinitial/demand/threecommands','receiving/conservation'],
    budget=dict(parameter_sets=1,full450=2,ad=0,optimizer=0,native=0,fzp_scans=0),
    output='E:/VISSIM_analysis/20261010_sc108_side310/forecast2400',
    inherited_harness=dict(path=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest()),
    future_observation_inputs=False,production_adopted=False,
    next_gate='Compare same native head/wholeOmega responses; do not infer whole gain from absolute count improvement.')
(HERE/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('PREPARED')
