"""Same saved twenty cases, numerical repair only; no fitting or VISSIM."""
import gzip
import json
import math
from pathlib import Path
import sys
import time

D=Path(__file__).resolve().parent; I=D.parent; ROOT=I.parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import lane_plant_runtime as lpr
from evaluation.controllers.freeway_fd import positive_lane_reduction
from diagnostics.sdmpc_n31_20260924.integration_20260926.replay_congested_component import read_primitive_capture

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))

assert not (D/'roundoff_validation.json').exists()
ctx=lpr.load_sources(I/'closedloop9000_d4e2_analysis/local_merge_cell23/candidate_manifest.json')
model=ctx['component']
records=read(I/'decision_response/capture.json')['records']
records += [dict(r,case='s53_late') for r in read(I/'heldout53_response_v2/capture.json')['records']]
rows=[]; started=time.perf_counter()
for record in records:
    name=record['case']+'_'+record['arm']
    args,kwargs=read_primitive_capture(record['input'],record['sha256'])
    prediction=json.loads(json.dumps(model.rollout(*args,**kwargs),allow_nan=False))
    with gzip.open(D/'local_v2'/(name+'.json.gz'),'rt',encoding='utf-8') as f:old=json.load(f)
    errors=[]
    def check(a,b,path):
        if isinstance(a,dict):
            assert a.keys()==b.keys(),path
            for k in a:check(a[k],b[k],path+'/'+str(k))
        elif isinstance(a,list):
            assert len(a)==len(b),path
            for i,(x,y) in enumerate(zip(a,b)):check(x,y,path+'/'+str(i))
        elif isinstance(a,(float,int)) and not isinstance(a,bool):
            assert math.isfinite(a) and math.isfinite(b),path
            if a!=b:errors.append((abs(a-b),path))
        else:assert a==b,path
    for field in ('cells','flows','ports','ramps'):check(prediction[field],old[field],field)
    worst=max(errors,default=(0.,'')); assert worst[0]<1e-9,(name,worst)
    residual=max(abs(r['conservation_residual_veh']) for r in prediction['ports']+prediction['ramps'])
    assert residual<1e-7
    times=sorted({r['time_s'] for r in old['cells']})
    def series(pred):
        return {t:sum(r['n_veh'] for r in pred['cells'] if r['time_s']==t)
                 +sum(r['n_veh'] for r in pred['ports'] if r['time_s']==t)
                 +sum(r['end']['connector_veh'] for r in pred['ramps'] if r['end_sec']==t) for t in times}
    a,b=series(prediction),series(old)
    # Identical initial state: integrate differences, initial delta exactly zero.
    delta={round(times[0]-30,6):0.,**{t:a[t]-b[t] for t in times}}
    stamps=sorted(delta)
    cost_delta=sum((delta[t]+delta[u])*(u-t)/7200 for t,u in zip(stamps,stamps[1:]))
    rows.append(dict(case=record['case'],arm=record['arm'],numeric_leaves_changed=len(errors),
        max_abs_difference=worst[0],worst_path=worst[1],cost_delta_veh_h=cost_delta,conservation_max=residual))
geometry=ctx['geometry']; lane_rows={}
for road in ('FW_E','FW_W'):
    cells=sorted((r for r in geometry['cells'] if r['road']==road),key=lambda r:r['cell'])
    lanes=[r['lane_km']/r['length_km'] for r in cells]
    lane_rows[road]=dict(before=[i for i,(a,b) in enumerate(zip(lanes,lanes[1:])) if a>b],
        after=[i for i,(a,b) in enumerate(zip(lanes,lanes[1:])) if positive_lane_reduction(a,b)>0])
summary=dict(rows=rows,static_lane_drop_boundaries=lane_rows,rollouts=len(rows),wall_sec=time.perf_counter()-started,
    max_numeric_difference=max(r['max_abs_difference'] for r in rows),
    max_abs_cost_change=max(abs(r['cost_delta_veh_h']) for r in rows),native_runs=0)
(D/'roundoff_validation.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='rows'}),flush=True)
