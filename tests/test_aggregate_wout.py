from copy import deepcopy
from types import SimpleNamespace as NS
import pytest
from evaluation.controllers import aggregate_wout as a, route_choice_corridor as rc
from evaluation.controllers.physical_ramp_boundary import LaneResolvedRampBoundary


def fixture(dt=10):
    ramp='RM_C10681'
    geometry=dict(ramp=ramp,ramp_lanes={'1':0,'2':1},physical_link='68',road_length_m=118.,
        road_capacity_veh={str(i):20. for i in (1,2,3,4)},
        connector_entries={'10629':dict(lanes=[1,2,3],position_m=2.,length_m=60.,capacity_per_lane_veh=10.)},
        incoming={'move':[1,2,3]})
    paths={t:[dict(link='68',start=0.,stop=118.)]+([] if t==ramp else [dict(link='121',start=0.,stop=120.)])
           for t in ('free',ramp,'RM_C10646')}
    spec=dict(storage='W_out',entry_lane_receiving=geometry,connector_queue_gate=True,
              causal_lane_response={'wave_m_s':3.2},lateral_access_rate_per_sec=.008,
              physical_travel={'destinations':paths},choice_position_m=7.,
              future_choice_weights={ramp:.6,'free':.2,'RM_C10646':.2},incoming_movements={'move':'10629'})
    cohorts=[dict(target=ramp,vehicles=10.,due=0,speed_kph=30.,lane68={'shares':{'1':1.},'exit_step':0}),
             dict(target='free',vehicles=5.,due=0,speed_kph=30.,local68_queue=True,lane68={'shares':{'1':1.},'exit_step':0}),
             dict(target='prechoice',vehicles=6.,due=0,speed_kph=30.,connector68={'link':'10629','shares':{'1':1.},'ready_step':0}),
             dict(target='free',vehicles=2.,due=0,speed_kph=30.)]
    buffer=NS(lane_arrival_shares=(.5,.5), _lane_buffers=[NS(current_admission_space=lambda:100.) for _ in range(2)])
    buffer.current_admission_space=lambda:LaneResolvedRampBoundary.current_admission_space(buffer)
    buffer.snapshot=lambda:{'connector_veh':0.}
    state=NS(time_sec=0.,urban_link_storage={'W_out':77.},urban_storage_release_buffer={},ramp_queue={ramp:0.},
             known_legsplit_route_state=dict(cohorts=cohorts,received=0.,departed=0.,plan=None),
             lane_ramp_runtime=NS(buffers={ramp:buffer}))
    cfg=NS(network=NS(known_legsplit_routes=spec,urban_link_storage_veh={'W_out':100.},urban_avg_speed_km_h=50.),
           simulation=NS(T_u_sec=1,T_f_sec=1,T_c_sec=150),mpc=NS(horizon_steps=3))
    return state,cfg,{'urban':{'known_wout_aggregate_step_sec':dt}}


def test_absent_option_preserves_legacy_state_and_configuration():
    state,cfg,_=fixture(); before=deepcopy(state.known_legsplit_route_state)
    assert a.configure(cfg,{},state)=={}
    assert state.known_legsplit_route_state==before
    assert 'aggregate_step_sec' not in cfg.network.known_legsplit_routes


def test_config_rejects_unsupported_distance_reward():
    state,cfg,tuning=fixture();cfg.network.sdmpc_distance_reward={'enabled':True}
    with pytest.raises(ValueError,match='distance accounting'):a.configure(cfg,tuning,state)


def test_source_stock_frees_only_after_actual_receipt():
    state,cfg,tuning=fixture();a.configure(cfg,tuning,state)
    rc.known_connector_advance(state,cfg,0)
    obj=state.known_legsplit_route_state[a.KEY]
    before=obj.stock()
    requests=rc.known_legsplit_requests(state,cfg,'W_out',before,before,0)
    assert requests['RM_C10681']==10.
    # Accepted physical receipt, not the requested quantity, changes the owner.
    state.urban_link_storage['W_out']+=2.
    rc.known_legsplit_commit(state,cfg,[('W_out','RM_C10681',2.)],0)
    assert obj.stock()==before-2.
    assert obj.ready('68','1','RM_C10681')==8.
    assert state.known_legsplit_route_state['departed']==2.


def test_fine_receipts_do_not_recompute_macro_transport():
    state,cfg,tuning=fixture();a.configure(cfg,tuning,state)
    obj=state.known_legsplit_route_state[a.KEY]
    for step in range(30):
        rc.known_connector_advance(state,cfg,step)
        rc.known_legsplit_requests(state,cfg,'W_out',0.,0.,step)
        rc.known_legsplit_commit(state,cfg,[],step)
    assert obj.updates==3
    assert rc._known_total(state)==pytest.approx(23.)
    assert obj.bins.future.shape==(40,47)


def test_two_movements_share_connector_capacity_not_each_full_room():
    state,cfg,tuning=fixture();a.configure(cfg,tuning,state)
    spec=cfg.network.known_legsplit_routes
    spec['entry_lane_receiving']['incoming']={'one':[1],'two':[1]}
    spec['incoming_movements'].update(one='10629',two='10629')
    result=rc.known_entry_lane_limits(state,cfg,{'one':4.,'two':4.},0)
    assert result=={'one':2.,'two':2.}


def test_more_actual_ramp_admission_opens_shared_lane_and_upstream_room():
    outcomes=[]
    for admission in (0.,1.):
        state,cfg,tuning=fixture();a.configure(cfg,tuning,state)
        obj=state.known_legsplit_route_state[a.KEY]
        for step in range(30):
            rc.known_connector_advance(state,cfg,step)
            request=rc.known_legsplit_requests(state,cfg,'W_out',0.,0.,step)
            accepted=min(admission,request['RM_C10681'])
            state.urban_link_storage['W_out']+=accepted
            rc.known_legsplit_commit(state,cfg,[('W_out','RM_C10681',accepted)],step)
        outcomes.append((obj.stock('68'),obj.stock('tail'),state.known_legsplit_route_state['departed']))
    assert outcomes[1][0]<outcomes[0][0]
    assert outcomes[1][1]>outcomes[0][1]
    assert outcomes[1][2]>outcomes[0][2]


def test_clone_keeps_independent_aggregate_arrays():
    state,cfg,tuning=fixture();a.configure(cfg,tuning,state)
    other=deepcopy(state)
    rc.known_connector_advance(other,cfg,0)
    assert state.known_legsplit_route_state[a.KEY].updates==0
    assert other.known_legsplit_route_state[a.KEY].updates==1


def test_one_blocked_ramp_lane_does_not_block_a_different_connected_lane():
    state,cfg,tuning=fixture();a.configure(cfg,tuning,state)
    rc.known_connector_advance(state,cfg,0)
    obj=state.known_legsplit_route_state[a.KEY]
    obj.change_ready('68','2','RM_C10681',10.)
    state.urban_link_storage['W_out']-=10.
    buffer=state.lane_ramp_runtime.buffers['RM_C10681']
    buffer._lane_buffers=[NS(current_admission_space=lambda:1.),NS(current_admission_space=lambda:0.)]
    request=rc.known_legsplit_requests(state,cfg,'W_out',obj.stock(),obj.stock(),0)
    accepted=min(request['RM_C10681'],buffer.current_admission_space())
    assert accepted==1.  # Independent1->1 connection can admit while2->2 is full.
    assert buffer.lane_arrival_shares==(1.,0.)
    state.urban_link_storage['W_out']+=accepted
    rc.known_legsplit_commit(state,cfg,[('W_out','RM_C10681',accepted)],0)
    assert obj.ready('68','1','RM_C10681')==9.
    assert obj.ready('68','2','RM_C10681')==10.


def test_lateral_motion_uses_physical_seconds_after_urban_clock_rebase():
    from evaluation.controllers.multirate_urban_clock import UrbanTickBins
    outcomes=[]
    for urban_sec in (1,10):
        state,cfg,tuning=fixture()
        state.known_legsplit_route_state['cohorts'].append(dict(target='RM_C10681',
            vehicles=5.,due=0,speed_kph=30.,lane68={'shares':{'3':1.},'exit_step':0}))
        state.urban_link_storage['W_out']-=5.
        a.configure(cfg,tuning,state)
        obj=state.known_legsplit_route_state[a.KEY]
        if urban_sec==10:
            bins=object.__new__(UrbanTickBins)
            bins.__dict__.update(vars(obj.bins));bins.input_tick_sec=10
            obj.bins=bins;obj.dt=1;cfg.simulation.T_u_sec=10
        obj.advance(state,cfg,0)
        obj.bins.verify()
        outcomes.append((obj.ready('68','2','RM_C10681'),obj.ready('68','3','RM_C10681'),obj.stock()))
    assert outcomes[1]==pytest.approx(outcomes[0])


def observed_full_lane(count=20.):
    state,cfg,tuning=fixture()
    cfg.network.known_legsplit_routes['entry_lane_receiving']['road_capacity_veh']['2']=19.319508088249663
    state.known_legsplit_route_state['cohorts']=[
        dict(target='RM_C10681',vehicles=count,due=0,speed_kph=0.,
             lane68={'shares':{'2':1.},'exit_step':0}),
        dict(target='prechoice',vehicles=3.,due=0,speed_kph=30.,
             connector68={'link':'10629','shares':{'2':1.},'ready_step':0})]
    state.urban_link_storage['W_out']=100.-count-3.
    return state,cfg,tuning


def test_observed_integer_lane_count_survives_fractional_storage_limit():
    # Actual4650 frame:20 on lane2; conservative length/6m limit19.3195.
    state,cfg,tuning=observed_full_lane()
    a.configure(cfg,tuning,state)
    obj=state.known_legsplit_route_state[a.KEY]
    assert obj.stock('68','2')==20.
    assert obj.stock()==23.
    assert cfg.network.known_legsplit_routes['entry_lane_receiving']['road_capacity_veh']['2']==19.319508088249663
    obj.advance(state,cfg,0)
    # Preserving observed vehicles does not grant extra receiving room.
    assert obj.stock('68','2')==20.
    assert obj.stock('10629','2')==3.
    obj.change_ready('68','2','RM_C10681',.01)
    with pytest.raises(ArithmeticError,match='lane capacity'):obj.check_capacity(cfg)


def test_observed_excess_cannot_be_reused_after_it_drains():
    state,cfg,tuning=observed_full_lane()
    a.configure(cfg,tuning,state)
    obj=state.known_legsplit_route_state[a.KEY]
    obj.bins.advance(0)
    obj.change_ready('68','2','RM_C10681',-.3)
    obj.check_capacity(cfg)
    obj.change_ready('68','2','RM_C10681',.1)
    with pytest.raises(ArithmeticError,match='lane capacity'):obj.check_capacity(cfg)
    obj.change_ready('68','2','RM_C10681',-1.)
    obj.check_capacity(cfg)
    obj.change_ready('68','2','RM_C10681',.6)
    with pytest.raises(ArithmeticError,match='lane capacity'):obj.check_capacity(cfg)


@pytest.mark.parametrize('count',[21.,19.5])
def test_initial_storage_exception_is_only_one_integer_count(count):
    state,cfg,tuning=observed_full_lane(count)
    with pytest.raises(ArithmeticError,match='lane capacity'):a.configure(cfg,tuning,state)


def test_observed_connector_excess_does_not_admit_new_upstream_stock():
    state,cfg,tuning=fixture()
    cfg.network.known_legsplit_routes['entry_lane_receiving']['connector_entries']['10629']['capacity_per_lane_veh']=5.8
    a.configure(cfg,tuning,state)
    obj=state.known_legsplit_route_state[a.KEY]
    assert obj.stock('10629','1')==6.
    spec=cfg.network.known_legsplit_routes
    spec['entry_lane_receiving']['incoming']={'one':[1]}
    spec['incoming_movements']['one']='10629'
    assert rc.known_entry_lane_limits(state,cfg,{'one':4.},0)=={'one':0.}
    obj.bins.advance(0)
    obj.change_ready('10629','1','prechoice',-.3)
    obj.check_capacity(cfg)
    obj.change_ready('10629','1','prechoice',.2)
    with pytest.raises(ArithmeticError,match='connector'):obj.check_capacity(cfg)


def test_drained_lane_reopens_only_its_nominal_available_space():
    state,cfg,tuning=observed_full_lane()
    metadata=a.configure(cfg,tuning,state)
    cap=cfg.network.known_legsplit_routes['entry_lane_receiving']['road_capacity_veh']['2']
    assert metadata['known_wout_initial_storage_excess_veh']==pytest.approx(20.-cap)
    obj=state.known_legsplit_route_state[a.KEY]
    obj.advance(state,cfg,0)
    obj.change_ready('68','2','RM_C10681',-1.5)
    state.urban_link_storage['W_out']+=1.5
    obj.check_capacity(cfg)
    obj.advance(state,cfg,10)
    assert obj.stock('68','2')==pytest.approx(cap)
    assert obj.stock('10629','2')==pytest.approx(3.-(cap-18.5))
    assert obj.stock()==pytest.approx(21.5)
