from types import SimpleNamespace as NS
import math
import numpy as np
import pytest
from evaluation.controllers import route_choice_corridor as rc
from evaluation.controllers import sdmpc_tangent_reverse as ad
from evaluation.controllers import sdmpc_tangent_summary as fused
from local68_array_candidate import advance

def setup(mode,kind,scale):
    trace=ad.Trace([.01,.01])
    amount=ad.Dual(2.,{0:1.},trace) if mode=='ad' else 2.
    shares={'1':.4,'3':.6}
    if mode=='ad':shares={'1':ad.Dual(.4,{1:1.},trace),'3':ad.Dual(.6,{1:-1.},trace)}
    ramp=dict(target='R',vehicles=4.,due=10,lane68=dict(shares={'3':1.},exit_step=10,order=(0,10.)))
    local=dict(target='free',vehicles=3.*scale,due=10,local68_queue=True,downstream_steps=5,
               lane68=dict(shares=shares,exit_step=10,order=(0,30.)))
    if kind=='ahead':ramp['lane68']['order']=(0,50.)
    if kind=='later':ramp['due']=11
    if kind=='tiny_blocker':ramp['vehicles']=1e-10
    if kind=='tie':ramp['vehicles']=1.
    if kind=='no_admission':amount=0.
    spec=dict(storage='W',local_queue_gate=True,entry_lane_receiving=dict(ramp='R'))
    if kind=='restricted':
        spec.update(lateral_access_rate_per_sec=.01);spec['entry_lane_receiving']['ramp_lanes']={'1':0,'2':1}
    cfg=NS(network=NS(known_legsplit_routes=spec))
    state=NS(known_legsplit_route_state={'cohorts':[ramp,local]},urban_storage_release_buffer={})
    return state,cfg,{'requests':{'R':4.}},{'R':amount},trace

def scalarize(v):
    if isinstance(v,ad.Dual):return v.value
    if isinstance(v,dict):return {k:scalarize(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [scalarize(x) for x in v]
    return v

def outputs(s):
    result=[]
    for c in s.known_legsplit_route_state['cohorts']:
        result.append(c['vehicles']);result.extend(c.get('lane68',{}).get('shares',{}).values())
    result.extend(s.urban_storage_release_buffer.get('W',{}).values())
    result.append(s.known_legsplit_route_state['local68_passed_veh'])
    return result

@pytest.mark.parametrize('kind',['blocked','ahead','later','tiny_blocker','tie','no_admission','restricted'])
@pytest.mark.parametrize('scale',[1.,1e-180])
@pytest.mark.parametrize('mode',['scalar','ad'])
def test_same_mass_lane_clock_and_sensitivity(kind,scale,mode,monkeypatch):
    monkeypatch.setattr(ad.Trace,'operation',fused.checked_operation)
    states=[];gradients=[];events=[]
    for fn in (rc._known_local_queue_advance,advance):
        s,c,p,a,t=setup(mode,kind,scale);fn(s,c,p,a,10)
        states.append(scalarize(vars(s)))
        if mode=='ad':gradients.append(t.jacobian(outputs(s),workers=1));events.append(t.result())
    assert states[0]==states[1]
    if mode=='ad':
        np.testing.assert_allclose(gradients[0],gradients[1],rtol=1e-12,atol=1e-12)
        for field in ('event_counts','exact_tie_axes','discrete_dependent_axes'):assert events[0][field]==events[1][field]
