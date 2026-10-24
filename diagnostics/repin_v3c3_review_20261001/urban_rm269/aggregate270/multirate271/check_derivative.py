"""Fresh-process instrumentation of the new5s ramp law, on a smooth branch."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers.sdmpc_tangent_runtime import install
finder=install(ROOT,'forward');ad=finder.ad
from evaluation.controllers.physical_ramp_boundary import LaneResolvedRampBoundary
from evaluation.controllers import known_wout_causal_response as causal


def evaluate(service):
    b=LaneResolvedRampBoundary(connector_id='10681',length_m=72.,head_position_m=60.,
        lanes=2,spacing_m=6.,travel_speed_kmh=36.,time_sec=100.,lane_arrival_shares=(.5,.5),
        initial_cohorts=[(60.,0.,lane) for lane in (1,2) for _ in range(8)])
    for lane in b._lane_buffers:
        causal.attach(lane,3.);lane._causal_receiving_enabled=True
    merged=cost=0.
    for i in range(3):
        r=b.advance_coarse_interval(start_sec=100.+5*i,duration_sec=5.,cycle_sec=10.,
            receiving_budget_veh=10.,mode='OFF',service_veh=service,request_arrivals_veh=0.)
        merged+=r['accepted_merge_veh'];cost+=r['connector_ttt_veh_h']
    stock=b.snapshot()['connector_veh']
    return [merged,cost,stock,stock+merged]


if __name__=='__main__':
    assert not (HERE/'derivative_result.json').exists(),'No duplicate derivative check'
    h=1e-5;anchor=5.;trace=ad.Trace([h])
    dual=evaluate(ad.Dual(anchor,{0:1.},trace))
    base=evaluate(anchor);plus=evaluate(anchor+h);minus=evaluate(anchor-h)
    derivative=[ad.derivative(v).get(0,0.) for v in dual]
    finite=[(p-m)/(2*h) for p,m in zip(plus,minus)]
    assert max(abs(ad.primal(a)-b) for a,b in zip(dual,base))<1e-10
    assert max(abs(a-b) for a,b in zip(derivative,finite))<1e-7
    assert derivative[0]>0 and derivative[1]<0 and abs(derivative[3])<1e-12
    result=dict(status='coarse_boundary_selected_branch_ad_fd_pass',values=base,derivative=derivative,finite_difference=finite,
        quantities=['accepted_merge','ramp_ttt_veh_h','remaining_ramp_stock','conserved_stock_plus_merge'],
        scope='Two-lane causal ramp,3actual5ssteps,one smooth service axis. Not full237/213axis coupled AD or native control validation.',
        sources=finder.source_hashes)
    (HERE/'derivative_result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='sources'}))
