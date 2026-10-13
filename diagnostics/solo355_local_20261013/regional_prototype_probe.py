import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[k]='1'
import argparse, json, pickle, sys, time
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--ad',action='store_true')
p.add_argument('--mode',default='freeway_only')
p.add_argument('--capture',default='D:/VISSIM_analysis/20261013_solo355_local/projected.pkl')
p.add_argument('--output',required=True)
args=p.parse_args()
root=Path('E:/VISSIM_packages/solo355_20261012')
sys.path[:0]=[str(root),str(root/'vendor/NumSim-mine')]
if args.ad:
    from evaluation.controllers.sdmpc_tangent_runtime import install
    finder=install(root,'reverse-v1')
    ad=finder.ad
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers import sdmpc_regional_prototype as regional, sdmpc_continuous
x=pickle.load(open(args.capture,'rb'))
c,s,f,h,m=x['args'];cfg=c.nash_solver.cfg
boundary=regional.boundary_requests(x['obs']['merged']['obs150_derived'],
    args.mode,s.time_sec,cfg.network.ramps,s.lane_freeway_runtime.offramps)
local=regional.project_state(s,cfg,args.mode,boundary)
sdmpc_continuous.install(cfg)
if args.ad:
    trace=ad.Trace([.01,.01],track_stencils=False)
    if args.mode=='freeway_only':
        road='FW_W';head=cfg.network.freeway_vsl_zone_heads[road][cfg.network.freeway_vsl_zone_free[0]]
        for cell,parent in enumerate(cfg.network.freeway_vsl_zone_head_of_cell[road]):
            if parent==head:
                h.vsl[f'{road}__seg{cell}']=ad.Dual(h.vsl[f'{road}__seg{cell}'],{0:1.},trace)
        key='rw_meter_green_RM_C10480'
        h.diagnostics[key]=ad.Dual(h.diagnostics[key],{1:1.},trace)
    else:
        h.offsets['SC1001']=ad.Dual(h.offsets['SC1001'],{0:1.},trace)
        h.offsets['SC1004']=ad.Dual(h.offsets['SC1004'],{1:1.},trace)
t=time.perf_counter()
point=regional.predict(local,cfg,f,h)
elapsed=time.perf_counter()-t
if args.ad:
    value=ad.primal(point.objective)
    deriv=trace.jacobian([point.objective],workers=1).tolist()
else:
    value=float(point.objective);deriv=None
record=dict(stage='prototype_only',production_dispatch=False,native_runs=0,
    region=args.mode,objective_veh_h=value,elapsed_sec=elapsed,
    derivative=deriv,boundary=boundary,initial_stock_keys=list(local._control_area_ledger.stocks),
    own_initial_vehicles=sum(sum(v.values()) for v in local._control_area_ledger.stocks.values()),
    remote_runtime_present=any(hasattr(local,k) for k in (('lane_urban_runtime','lane_offramp_runtime') if args.mode=='freeway_only' else ('lane_freeway_runtime',))),
    note='State cut scalar/AD milestone; cfg/bootstrap isolation and regional feasibility response not qualified.')
Path(args.output).write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps({k:record[k] for k in ('stage','objective_veh_h','elapsed_sec','derivative','remote_runtime_present')}))
