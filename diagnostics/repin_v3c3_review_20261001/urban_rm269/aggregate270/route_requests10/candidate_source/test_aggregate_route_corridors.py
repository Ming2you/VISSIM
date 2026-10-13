from types import SimpleNamespace as NS
import pytest
from evaluation.controllers import route_choice_corridor as rc, aggregate_route_corridors as ar
from src.models import urban_queue_model as uqm


def fixture(monkeypatch,dt=10,room=20.,typed=False,native=False,request_dt=None):
    spec=dict(decision='x',prefix_storage='p',local_storage='l',capacity_veh={'p':20.,'l':20.},
        branches={'A':dict(mode='free_storage',destination='a',service_group='g',lanes=1,share=.5,branch_position_m=10.),
                  'B':dict(mode='free_storage',destination='b',service_group='g',lanes=1,share=.5,branch_position_m=10.)},
        decision_position_m=0.,per_lane_capacity_veh_h=3600.,turns={},generated_inputs={},local_exits={})
    if typed:
        spec['branches']['A'].update(mode='typed_queue',destination='l')
        spec.update(local_movements={'A':'q'},local_connector='connector',
                    local_travel_segments={'A':{'connector':[dict(start=0.,stop=10.)]}})
    if native:spec['native_fixed_service']=dict(controller='15',signal_group='1',controller_offset_sec=0.,lanes=1)
    rows=[rc._cohort('p','prefix_tagged','A',4.,0,source='observed_current_route',speed=36.),
          rc._cohort('p','prefix_tagged','B',4.,0,source='observed_current_route',speed=36.)]
    if native:rows[1]['native_service_passed']=True
    state=NS(time_sec=0.,urban_link_storage={'p':12.,'l':20.,'a':room,'b':20.},
        urban_movement_queue={},urban_arrival_buffer={},urban_storage_release_buffer={},
        route_choice_corridor_state=dict(cohorts=rows,last_step=-1,service_used_veh={},service_limit_veh={},received_veh=0.,departed_veh=0.))
    cfg=NS(network=NS(route_choice_corridor={**spec,'corridors':[spec],'unknown_policy':'hold'},urban_avg_speed_km_h=36.),
        simulation=NS(T_u_sec=1,T_f_sec=1,T_c_sec=150,T_u_h=1/3600),mpc=NS(horizon_steps=3))
    monkeypatch.setattr(rc,'emit_transfer',lambda *a,**k:None)
    monkeypatch.setattr(rc,'get_ledger',lambda *a:None)
    monkeypatch.setattr(uqm,'_effective_available_space',lambda s,c,t:s.urban_link_storage[t])
    monkeypatch.setattr(uqm,'_link_delay_steps',lambda *a:2)
    tuning={'route_corridor_aggregate_step_sec':dt}
    if request_dt is not None:tuning['route_corridor_request_step_sec']=request_dt
    ar.configure(cfg,{'urban':tuning},state)
    return state,cfg,spec


def test_default_off_does_not_change_state(monkeypatch):
    state=NS();cfg=NS()
    assert ar.configure(cfg,{},state)=={} and vars(state)=={} and vars(cfg)=={}


def test_shared_service_and_target_room_conserve_routes(monkeypatch):
    s,c,spec=fixture(monkeypatch,room=.1)
    rc.advance(s,None,None,c,0)
    # One service unit split between two routes; a blocked share is not reassigned.
    assert s.urban_link_storage['a']==pytest.approx(0.)
    assert s.urban_link_storage['b']==pytest.approx(19.5)
    assert rc._tracked(s.route_choice_corridor_state,'p')==pytest.approx(7.4)
    assert s.route_choice_corridor_state['departed_veh']==pytest.approx(.6)
    assert len(s.route_choice_corridor_state['cohorts'])==0
    rc._check(s,spec)


def test_receipt_keeps_known_route_and_delays_eligibility(monkeypatch):
    s,c,spec=fixture(monkeypatch)
    obj=s.route_choice_corridor_state[ar.KEY]
    rc.advance(s,None,None,c,0)
    n=2.;s.urban_link_storage['p']-=n
    obj.add(rc._cohort('p','prefix_tagged','A',n,3,source='observed_current_route',speed=36.))
    label=obj.label(rc._cohort('p','prefix_tagged','A',n,3,source='observed_current_route',speed=36.))
    index=obj.bins.index[label];assert obj.bins.pending[index]==2.
    for step in range(1,10):rc.advance(s,None,None,c,step)
    assert obj.bins.pending[index]==2.
    rc.advance(s,None,None,c,10);assert obj.bins.pending[index]==0.
    assert obj.updates==2
    obj.bins.verify();rc._check(s,spec)


def test_unknown_route_not_redrawn(monkeypatch):
    s,c,spec=fixture(monkeypatch)
    obj=s.route_choice_corridor_state[ar.KEY]
    with pytest.raises(ValueError,match='catalog'):
        obj.add(rc._cohort('p','unknown',None,1.,0,source='new_unverified_source'))


def test_distance_and_wrong_clock_rejected(monkeypatch):
    s,c,spec=fixture(monkeypatch)
    s.route_choice_corridor_state.pop(ar.KEY);c.network.sdmpc_distance_reward={'enabled':True}
    with pytest.raises(ValueError,match='distance'):ar.configure(c,{'urban':{'route_corridor_aggregate_step_sec':10}},s)
    del c.network.sdmpc_distance_reward;c.simulation.T_u_sec=10
    with pytest.raises(ValueError,match='fine physical'):ar.configure(c,{'urban':{'route_corridor_aggregate_step_sec':10}},s)


def test_typed_arrival_has_one_owner_and_no_early_release(monkeypatch):
    s,c,spec=fixture(monkeypatch,typed=True)
    for step in range(10):rc.advance(s,None,None,c,step)
    assert s.urban_movement_queue.get('q',0.)==0.
    assert rc._tracked(s.route_choice_corridor_state,'l')==pytest.approx(4.)
    rc.advance(s,None,None,c,10)
    assert s.urban_movement_queue['q']==pytest.approx(4.)
    assert rc._tracked(s.route_choice_corridor_state,'l')==0.
    assert s.urban_link_storage['l']==20.
    rc._check(s,spec)


def test_passed_native_head_tag_is_retained(monkeypatch):
    s,c,spec=fixture(monkeypatch,native=True)
    from evaluation.controllers import fixed_signal_schedule
    monkeypatch.setattr(rc,'_native_program',lambda *a:None)
    monkeypatch.setattr(fixed_signal_schedule,'_union_green_overlap',lambda *a:0.)
    rc.advance(s,None,None,c,0)
    assert s.urban_link_storage['a']==20.
    assert s.urban_link_storage['b']==pytest.approx(19.5)
    assert s.route_choice_corridor_state['native_service_used_veh']['x']==0.
    rc._check(s,spec)


def test_ten_second_requests_keep_fine_receiving_and_no_unused_service_credit(monkeypatch):
    s,c,spec=fixture(monkeypatch,room=0.,request_dt=10)
    for step in range(5):rc.advance(s,None,None,c,step)
    obj=s.route_choice_corridor_state[ar.KEY]
    assert obj.request_updates==1
    assert s.route_choice_corridor_state['departed_veh']==pytest.approx(2.5)
    # Opening a downstream road cannot release the five past blocked shares.
    s.urban_link_storage['a']=20.
    rc.advance(s,None,None,c,5)
    assert s.urban_link_storage['a']==pytest.approx(19.5)
    assert s.route_choice_corridor_state['departed_veh']==pytest.approx(3.5)
    for step in range(6,10):rc.advance(s,None,None,c,step)
    assert obj.request_updates==1
    assert s.route_choice_corridor_state['departed_veh']==pytest.approx(6.5)
    rc.advance(s,None,None,c,10)
    assert obj.request_updates==2
    rc._check(s,spec);obj.bins.verify()


def test_coarse_request_does_not_release_at_red_or_overdraw_ready_stock(monkeypatch):
    s,c,spec=fixture(monkeypatch,native=True,request_dt=10)
    from evaluation.controllers import fixed_signal_schedule
    monkeypatch.setattr(rc,'_native_program',lambda *a:None)
    monkeypatch.setattr(fixed_signal_schedule,'_union_green_overlap',lambda p,g,a,b,o:float(a>=6))
    for step in range(6):rc.advance(s,None,None,c,step)
    assert s.urban_link_storage['a']==20.
    assert s.urban_link_storage['b']==pytest.approx(17.)
    for step in range(6,10):rc.advance(s,None,None,c,step)
    assert s.urban_link_storage['a']==pytest.approx(18.)
    assert s.urban_link_storage['b']==pytest.approx(16.)
    assert s.route_choice_corridor_state[ar.KEY].request_updates==1
    rc._check(s,spec)


def test_request_clock_requires_a_matching_arrival_clock(monkeypatch):
    with pytest.raises(ValueError,match='request'):
        fixture(monkeypatch,dt=1,request_dt=10)
