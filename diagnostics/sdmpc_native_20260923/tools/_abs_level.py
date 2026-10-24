import json,os,sys,importlib.util
from pathlib import Path
ROOT=Path(r'D:\VISSIM-merge\sim3')
CAL=ROOT/'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1'
RD=ROOT/'diagnostics/demand_sweep/ramp_dsd_20260916_v2'
BASE=CAL/'res10_20260922/boundary_literature_v1'
Q=Path(r'D:\VISSIM_runs\20260922_fw080_urban090_controls')
sys.path[:0]=[str(CAL),str(RD),str(ROOT/'.review-deps'),str(ROOT)]
from canonical_harness import load_base_model
import evaluate_response as er
def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
spec=importlib.util.spec_from_file_location('h',ROOT/'diagnostics/offramp_dynamic_20260922/study.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
data,_=m.corrected_data()
model=load_base_model(data.geometry,BASE/'boundary_config.json')
params=load(BASE/'family_parameters.json')['boundary']
prof0=load(RD/'controller_response_4500_v1/model_v3/port_profile.json')
policy=load(Q/'rules/prepared_rm/rule_policy.json')
ids={d:120. for z,v in policy['zone_dsds'].items() for d in v}
nat=json.load(open(r'D:\VISSIM-merge\evidence\connector_stock.json',encoding='utf-8'))
print(f"{'cutoff':>9} {'모드':<14} {'모형 ramp_ttt':>14} {'native 커넥터':>14} {'비율':>8}")
for cut,key in ((1950.1,'1950.1'),(2700.1,'2700.1'),(3450.1,'3450.1')):
    for label,win in (('상수(<=900)',None),('직전150초 실측',150.)):
        prof=dict(prof0, **({'online_window_sec':win} if win else {}))
        w=er.window(data,model,cut,'history_forecast',prof,lambda t:({},ids))
        pred=er.simulate(model,w,params)
        parts=er.component(data,model,cut,pred)
        n=nat[key]['none']['total']
        r=parts['ramp_ttt_veh_h']
        print(f"{cut:>9} {label:<14} {r:>14.4f} {n:>14.4f} {r/n:>8.2f}")
