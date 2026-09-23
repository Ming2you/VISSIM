import sys, traceback, json, importlib.util
from pathlib import Path
ROOT=Path(r'D:\VISSIM-merge\sim3')
CAL=ROOT/'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1'
RD=ROOT/'diagnostics/demand_sweep/ramp_dsd_20260916_v2'
BASE=CAL/'res10_20260922/boundary_literature_v1'
sys.path[:0]=[str(CAL),str(RD),str(ROOT/'.review-deps'),str(ROOT)]
from canonical_harness import load_base_model
import evaluate_response as er
def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
spec=importlib.util.spec_from_file_location('h',ROOT/'diagnostics/offramp_dynamic_20260922/study.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
data,corr=m.corrected_data()
print('data.phase_sec =',getattr(data,'phase_sec','(없음)'))
print('data.cells 키 샘플 =',sorted(data.cells)[:4])
model=load_base_model(data.geometry,BASE/'boundary_config.json')
print('model.component_residence =',model.component_residence)
print('model.port_origin_split   =',model.port_origin_split)
params=load(BASE/'family_parameters.json')['boundary']
profile=load(RD/'controller_response_4500_v1/model_v3/port_profile.json')
policy=load(Path(r'D:\VISSIM_runs\20260922_fw080_urban090_controls/rules/prepared_rm/rule_policy.json'))
sec=1800.1
def command(t):
    return {}, {d:120. for z,v in policy['zone_dsds'].items() for d in v}
try:
    w=er.window(data,model,sec,'history_forecast',profile,command)
    print('window OK, boundary_steps =',len(w['boundary_steps']))
    pred=er.simulate(model,w,params)
    print('simulate OK')
    parts=er.component(data,model,sec,pred)
    print('component OK',parts)
except Exception:
    traceback.print_exc()
