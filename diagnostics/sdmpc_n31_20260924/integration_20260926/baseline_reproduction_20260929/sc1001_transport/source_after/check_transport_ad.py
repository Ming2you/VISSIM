"""Fresh-process AD through the new physical route buffers; no native run.

Verifies derivatives of accepted vehicle counts, not derivatives of discrete
arrival-time branches. The current path speeds stay fixed in this test.
"""
import copy
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'diagnostics/sdmpc_n31_20260924/tests'))
from evaluation.controllers import sdmpc_tangent_runtime
finder=sdmpc_tangent_runtime.install(ROOT,sys.argv[1] if len(sys.argv)>1 else 'forward')
ad=finder.ad
if '--sc1001' not in sys.argv:
    from test_known_wout_transport import fixture, request
from evaluation.controllers import route_choice_corridor as route


def run(amount):
    cfg,state,spec=fixture();storage=spec['storage']
    state.urban_link_storage[storage]-=amount
    route.known_legsplit_receive(state,cfg,amount,999,movement='SC1004_E_SC1005_to_W',entry_step=0)
    due=state.known_legsplit_route_state['cohorts'][0]['due']
    assert request(state,cfg,due)=={}
    route.known_legsplit_commit(state,cfg,[],due)
    east=next(c['due'] for c in state.known_legsplit_route_state['cohorts'] if c['target']=='RM_C10681')
    requested=request(state,cfg,east)['RM_C10681']
    frozen=copy.deepcopy(state)
    accepted=requested*.5
    state.urban_link_storage[storage]+=accepted
    route.known_legsplit_commit(state,cfg,[(storage,'RM_C10681',accepted)],east)
    route._known_check(state,cfg)
    assert frozen.known_legsplit_route_state['plan'] is not None
    return [requested,accepted,route._known_total(state),state.urban_link_storage[storage]]


expected=[.6,.3,.7,-.7]
if '--sc1001' in sys.argv:
    from test_sc1001_destination_travel import DestinationTravelTests
    def run(amount):
        state,cfg,storage=DestinationTravelTests().fixture()
        state.urban_link_storage[storage]-=amount
        route.direct_exit_movement_receive(state,cfg,'m',amount,20)
        requested=route.direct_exit_requests(state,cfg,storage,.001,6.+amount,100)['E']
        accepted=requested*.5
        state.urban_link_storage[storage]+=accepted
        route.direct_exit_commit(state,cfg,[(storage,'E',accepted)],100)
        route._direct_exit_check(state,cfg)
        total=sum(c['vehicles'] for c in state.direct_exit_route_state['cohorts'])
        return [requested,accepted,total,state.urban_link_storage[storage]]
    expected=[.5,.25,.75,-.75]

trace=ad.Trace([.001],track_stencils=False)
value=run(ad.Dual(10.,{0:1.},trace))
scalar=run(10.)
hi,lo=run(10.001),run(9.999)
jac=trace.jacobian(value,1) if finder.backend=='reverse-v1' else None
checks=[]
for i,(v,s) in enumerate(zip(value,scalar)):
    grad=float(jac[i,0]) if jac is not None else ad.derivative(v).get(0,0.)
    fd=(hi[i]-lo[i])/.002
    assert abs(ad.primal(v)-s)<1e-12
    assert abs(grad-fd)<1e-8 and abs(grad-expected[i])<1e-12, (i,grad,fd)
    checks.append(dict(output=i,primal=s,derivative=grad,finite_difference=fd))
print(json.dumps(dict(passed=True,backend=finder.backend,checks=checks,
                     full_rollout_ad_qualified=False,discrete_arrival_derivative_tested=False)))
