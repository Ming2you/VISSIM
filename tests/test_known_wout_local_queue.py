"""A blocked local lane cannot disappear at a travel ETA or duplicate stock."""
from types import SimpleNamespace as NS
import copy
import pytest
from evaluation.controllers.route_choice_corridor import (
    _known_local_queue_prepare,_known_local_queue_advance,known_legsplit_commit)


def fixture():
    r=dict(target='R',vehicles=4.,due=10,lane68=dict(shares={'3':1.},exit_step=10,order=(0,10.)))
    f=dict(target='free',vehicles=3.,due=10,local68_queue=True,downstream_steps=5,
           lane68=dict(shares={'3':1.},exit_step=10,order=(0,30.)))
    spec=dict(storage='W',local_queue_gate=True,entry_lane_receiving=dict(ramp='R',road_length_m=100.))
    cfg=NS(network=NS(known_legsplit_routes=spec,urban_link_storage_veh={'W':100.}))
    plan=dict(step=10,requests={'R':4.},rows=[(r,4.)])
    state=NS(known_legsplit_route_state=dict(cohorts=[r,f],plan=plan,departed=0.),
             urban_storage_release_buffer={},urban_link_storage={'W':93.})
    return state,cfg,plan,r,f


def test_zero_admission_retains_local_count_after_expired_eta():
    s,c,p,r,f=fixture();_known_local_queue_advance(s,c,p,{},10)
    assert f['vehicles']==3. and len(s.known_legsplit_route_state['cohorts'])==2
    assert not s.urban_storage_release_buffer


def test_actual_admission_releases_proportional_travel_not_network_exit():
    s,c,p,r,f=fixture();before=sum(v['vehicles'] for v in s.known_legsplit_route_state['cohorts'])
    _known_local_queue_advance(s,c,p,{'R':2.},10)
    assert f['vehicles']==1.5
    post=s.known_legsplit_route_state['cohorts'][-1]
    assert post==dict(target='free',vehicles=1.5,due=15,source='local68_passed')
    assert sum(v['vehicles'] for v in s.known_legsplit_route_state['cohorts'])==before
    assert s.urban_link_storage['W']==93. and s.known_legsplit_route_state['departed']==0.
    assert s.urban_storage_release_buffer=={'W':{15:1.5}}


@pytest.mark.parametrize('kind',['different_lane','behind','still_moving'])
def test_unrelated_or_not_yet_queued_ramp_does_not_stop_free_path(kind):
    s,c,p,r,f=fixture()
    if kind=='different_lane':r['lane68']['shares']={'1':1.}
    elif kind=='behind':r['lane68']['order']=(0,50.)
    else:r['due']=11
    _known_local_queue_advance(s,c,p,{},10)
    assert f['vehicles']==0.
    assert s.urban_storage_release_buffer['W'][15]==3.


def test_mass_commit_only_counts_actual_ramp_admission_as_owner_departure():
    s,c,p,r,f=fixture();s.urban_link_storage['W']+=2.
    known_legsplit_commit(s,c,[('W','R',2.)],10)
    assert sum(x['vehicles'] for x in s.known_legsplit_route_state['cohorts'])==5.
    assert s.known_legsplit_route_state['departed']==2.
    assert s.known_legsplit_route_state['plan'] is None


def test_partial_lane_release_updates_remaining_shares_conservatively():
    s,c,p,r,f=fixture();f['lane68']['shares']={'3':.5,'4':.5}
    _known_local_queue_advance(s,c,p,{},10)
    assert f['vehicles']==1.5 and f['lane68']['shares']=={'3':1.}


def test_new_local_stage_preserves_downstream_physical_travel():
    s,c,p,r,f=fixture();c.simulation=NS(T_u_sec=1.)
    c.network.known_legsplit_routes['physical_travel']={'destinations':{
        'free':[dict(link='68',start=0.,stop=100.),dict(link='121',start=0.,stop=200.)]}}
    f.pop('local68_queue');f['speed_kph']=36.;f['due']=50
    _known_local_queue_prepare(c,f)
    assert f['due']==10 and f['downstream_steps']==20
    assert f['vehicles']==3.


def test_disabled_is_exact_noop():
    s,c,p,r,f=fixture();c.network.known_legsplit_routes['local_queue_gate']=False
    before=copy.deepcopy(s)
    _known_local_queue_prepare(c,f);_known_local_queue_advance(s,c,p,{'R':2.},10)
    assert vars(s)==vars(before)


def test_admission_sensitivity_reaches_waiting_and_travelling_stock():
    from evaluation.controllers.sdmpc_dual import Dual,Trace,derivative,primal
    s,c,p,r,f=fixture();accepted=Dual(2.,{0:1.},Trace([.01]))
    _known_local_queue_advance(s,c,p,{'R':accepted},10)
    post=s.known_legsplit_route_state['cohorts'][-1]
    assert primal(f['vehicles'])==1.5 and derivative(f['vehicles'])[0]==-.75
    assert primal(post['vehicles'])==1.5 and derivative(post['vehicles'])[0]==.75


def test_vanishing_residual_keeps_mass_without_normalizing_by_tiny_stock():
    from evaluation.controllers.sdmpc_dual import Dual,Trace,derivative,primal
    s,c,p,r,f=fixture();f['vehicles']=1e-180
    accepted=Dual(2.,{0:1.},Trace([.01]))
    _known_local_queue_advance(s,c,p,{'R':accepted},10)
    post=s.known_legsplit_route_state['cohorts'][-1]
    assert primal(f['vehicles'])==5e-181
    assert primal(f['vehicles']+post['vehicles'])==1e-180
    assert f['lane68']['shares']=={'3':1.}
    assert derivative(f['vehicles'])[0]<0
    assert derivative(post['vehicles'])[0]>0


def test_whole_fractional_lane_release_leaves_no_roundoff_queue():
    s,c,p,r,f=fixture();f['vehicles']=.1
    f['lane68']['shares']={'3':.3,'4':.7};r['lane68']['shares']={'1':1.}
    _known_local_queue_advance(s,c,p,{},10)
    assert f['vehicles']==0.
    assert s.urban_storage_release_buffer['W'][15]==pytest.approx(.1)
