"""A bounded local arithmetic timing; no model forecast or calibration."""
import ctypes,json,time
from pathlib import Path
from types import SimpleNamespace as NS
from evaluation.controllers import route_choice_corridor as rc
from evaluation.controllers import sdmpc_tangent_reverse as ad,sdmpc_tangent_summary as fused
from local68_array_candidate import advance
from test_local68_array_candidate import scalarize,setup

HERE=Path(__file__).resolve().parent;out=HERE/'local68_array_micro.json'
assert not out.exists()
k=ctypes.WinDLL('kernel32');k.GetCurrentProcess.restype=ctypes.c_void_p
k.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
ad.Trace.operation=fused.checked_operation;fused.install_fused_operations()
s,c,p,a,t=setup('ad','blocked',1.);advance(s,c,p,a,10)
def large(mode,count):
    trace=ad.Trace([.01,.01]);cohorts=[]
    def variable(x,axis):return ad.Dual(x,{axis:1.},trace) if mode=='ad' else x
    for j in range(count):
        ramp=j%3==0
        c=dict(target='R' if ramp else 'free',vehicles=variable(.03+j%5*.02,0),due=10,
            lane68=dict(shares={'1':variable(.4,1),'3':variable(.6,1)},exit_step=10,order=(0,j*1.)))
        if not ramp:c.update(local68_queue=True,downstream_steps=5+j%10)
        cohorts.append(c)
    state=NS(known_legsplit_route_state=dict(cohorts=cohorts),urban_storage_release_buffer={})
    spec=dict(storage='W',local_queue_gate=True,entry_lane_receiving=dict(ramp='R',ramp_lanes={'1':0,'2':1}),lateral_access_rate_per_sec=.01)
    return state,NS(network=NS(known_legsplit_routes=spec)),dict(requests={'R':4.}),{'R':variable(2.,0)},trace
rows=[]
for mode in ('scalar','ad'):
    for count in (256,4096):
        baseline=None
        for label,fn in [('existing',rc._known_local_queue_advance),('array',advance)]:
            s,c,p,a,t=large(mode,count);began=time.perf_counter();fn(s,c,p,a,10);seconds=time.perf_counter()-began
            values=scalarize(vars(s))
            if baseline is None:baseline=values
            assert baseline==values
            rows.append(dict(mode=mode,cohorts=count,implementation=label,seconds=seconds,
                             tape_nodes=len(t.p1),same_physical_output=True))
report=dict(status='synthetic_only',measurements=rows,production_installed=False,
    forecasts=0,full_decisions=0,native_runs=0,caveat='One local call per case under competing full-selection/native workload; not a full-decision speedup.')
out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps(report))
