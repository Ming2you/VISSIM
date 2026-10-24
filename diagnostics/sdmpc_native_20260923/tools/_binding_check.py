import json,sys,importlib.util
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
profile=load(RD/'controller_response_4500_v1/model_v3/port_profile.json')
policy=load(Q/'rules/prepared_rm/rule_policy.json'); zd=policy['zone_dsds']
CUT=1950.1; BL=(1950,2100,2250)
plan={t:(dict(load(Q/f'rm/run/decision_{t}.json')['history']['greens']),
         dict(load(Q/f'rm/run/decision_{t}.json')['history']['states'])) for t in BL}
ids={d:120. for z,v in zd.items() for d in v}
def mk(rep):
    def c(t):
        if not rep: return {},ids
        g,s=plan[BL[min(2,int((t-CUT)//150))]]
        return {k:v for k,v in g.items() if v<10 or k in s}, ids
    return c
out={}
for rep in (False,True):
    w=er.window(data,model,CUT,'history_forecast',profile,mk(rep))
    pred=er.simulate(model,w,params)
    # 실제로 요구된 도착 · 미터 서비스 · 방출
    svc={}; arr={}
    for s in w['boundary_steps']:
        for mid,v in s.get('ramp_head_service',{}).items():
            svc.setdefault(mid,[]).append((v.get('mode'),v.get('green_sec'),v.get('service_veh')))
        for mid,v in s.get('ramp_arrival_vph',{}).items(): arr.setdefault(mid,[]).append(v)
    end={x['ramp']:x['end'] for x in pred['ramps'] if abs(x['end_sec']-(CUT+450))<1e-6}
    out['replay' if rep else 'hold']=dict(
        merge={k:v['cumulative_merge_veh'] for k,v in end.items()},
        head={k:v['cumulative_head_service_veh'] for k,v in end.items()},
        arrivals={k:sum(vs)/len(vs) for k,vs in arr.items()},
        svc_sample={k:vs[0] for k,vs in svc.items()})
print("=== 램프별: 평균 도착(vph) / hold 방출(veh) / replay 방출(veh) / 차이 ===")
for mid in sorted(out['hold']['merge']):
    a=out['hold']['arrivals'].get(mid,0)
    h=out['hold']['head'][mid]; r=out['replay']['head'][mid]
    tag=''
    for t in BL:
        g=plan[t][0].get(mid,10)
        if g<10: tag+=f' g{t}={g}'
    print(f"  {mid:<12} 도착{a:8.1f}vph  hold{h:9.3f}  replay{r:9.3f}  Δ{r-h:+8.4f}{tag}")
print()
print("=== 제한된 3개 램프의 서비스 용량 대비 도착 ===")
for mid in ('RM_C10639','RM_C10490','RM_C10484'):
    a=out['hold']['arrivals'].get(mid,0)
    print(f"  {mid}: 도착 {a:.1f} vph")
    for t in BL:
        g=plan[t][0].get(mid,10)
        # per_lane table 에서 용량 환산
        print(f"    t={t} green={g}")
