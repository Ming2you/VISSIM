"""Local travel-clock derivative witness; no complete rollout AD claim."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace as NS

ROOT=Path.cwd()
from evaluation.controllers import sdmpc_tangent_runtime
backend=sys.argv[1]
finder=sdmpc_tangent_runtime.install(ROOT,backend)
from evaluation.controllers.physical_ramp_boundary import PhysicalRampBoundary, ramp_posthead_speed_kmh

cfg=NS(network=NS(ramp_to_freeway={'r':'E'},ramp_merge_segment_index={'r':1}))

def eta(speed):
    state=NS(freeway_speed={'E':[99.,speed]})
    b=PhysicalRampBoundary(connector_id='r',length_m=100.,head_position_m=50.,lanes=1,
        spacing_m=5.,travel_speed_kmh=36.,posthead_travel_speed_kmh=36.,time_sec=0.,
        initial_cohorts=[(60.,0.,1)])
    cap=ramp_posthead_speed_kmh(state,cfg,'r',36.)
    b.begin_interval(0.,1.,posthead_speed_kmh=cap)
    return b._downstream[0][0]

ad=finder.ad;rows=[]
for speed,expected in ((18.,-1./36.),(70.,0.)):
    trace=ad.Trace([.001],track_stencils=False)
    val=eta(ad.Dual(speed,{0:1.},trace))
    grad=float(trace.jacobian([val],1)[0,0]) if backend=='reverse-v1' else ad.derivative(val).get(0,0.)
    fd=(eta(speed+.001)-eta(speed-.001))/.002
    assert abs(grad-expected)<1e-10 and abs(fd-grad)<1e-8
    assert ad.primal(val)==eta(speed)
    rows.append(dict(speed=speed,eta=ad.primal(val),gradient=grad,finite_difference=fd))
print(json.dumps(dict(passed=True,backend=backend,rows=rows,full_rollout_ad_qualified=False)))
