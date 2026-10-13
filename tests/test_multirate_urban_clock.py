from copy import deepcopy
from types import SimpleNamespace as NS
from collections import Counter
import pickle
import pytest
from src.models.state import SimulationConfig
from evaluation.controllers.multirate_urban_clock import rebase_projection,UrbanTickBins
from evaluation.controllers.sdmpc_aggregate_transport import IntervalBins


def fixture():
    cfg=NS(simulation=SimulationConfig(T_u=1,T_f=5,control_interval=150),network=NS())
    state=NS(time_sec=100,urban_arrival_buffer={'A':{101:2.,109:3.,110:4.,120:5.}},
        urban_storage_release_buffer={'A':{101:2.,109:3.,110:4.,120:5.}},
        urban_inflow_transit_buffer={},offramp_transit_buffer={},
        gate_initial_route_tags={'A':{101:{'left':2.},109:{'straight':3.},110:{'left':4.},120:{'right':5.}}},
        gate_future_route_tags={},
        native_input_prehead_state=dict(last_step=99,finished_step=99,cohorts=[dict(due=103,vehicles=1.,stage='decision',route=None)]),
        urban_movement_queue={'held':7.},urban_link_storage={'A':20.},ramp_queue={'RM_C10681':74.})
    return cfg,state


def test_rounded_arrivals_and_route_subsets_remain_paired_without_early_service():
    cfg,state=fixture();stocks=deepcopy((state.urban_movement_queue,state.urban_link_storage,state.ramp_queue))
    before=deepcopy(state.urban_arrival_buffer['A'])
    result=rebase_projection(cfg,state)
    assert state.urban_arrival_buffer['A']=={11:9.,12:5.}
    assert state.urban_storage_release_buffer==state.urban_arrival_buffer
    assert state.gate_initial_route_tags['A']=={11:{'left':6.,'straight':3.},12:{'right':5.}}
    for end in range(100,131,10):
        assert sum(n for due,n in before.items() if due<=end)==sum(n for due,n in state.urban_arrival_buffer['A'].items() if due*10<=end)
    assert (state.urban_movement_queue,state.urban_link_storage,state.ramp_queue)==stocks
    assert cfg.simulation.T_u_sec==10 and result['max_delay_sec']==9
    assert state.native_input_prehead_state['last_step']==9
    assert state.native_input_prehead_state['finished_step']==9
    assert state.native_input_prehead_state['cohorts']==[dict(due=11,vehicles=1.,stage='decision',route=None)]


def test_absolute_port_times_and_counter_labels_are_not_rescaled():
    cfg,state=fixture();port=NS(urban=NS(time=100),lanes=[NS(time=100,start=100)])
    tags={101:Counter({('turnA',False):2.}),109:Counter({('turnA',False):3.,(None,False):1.})}
    state.lane_urban_runtime=NS(last_step=99,port=port,arrival_tags=tags)
    state.lane_offramp_runtime=NS(last_drain=None,local_port=port)
    state.sc1001_approach=NS(time=100,queues={'1':[[107,'off','N',2.]]})
    rebase_projection(cfg,state)
    assert state.lane_urban_runtime.port is state.lane_offramp_runtime.local_port is port
    assert port.urban.time==100 and port.lanes[0].time==100
    assert state.sc1001_approach.queues['1']==[[107,'off','N',2.]]
    assert state.lane_urban_runtime.arrival_tags=={11:Counter({('turnA',False):5.,(None,False):1.})}
    assert state.lane_urban_runtime.last_step==9


def test_aggregate_bins_keep_absolute_eta_and_future_column_mass():
    cfg,state=fixture();bins=IntervalBins([('68','2','RM_C10681')],100,450,10)
    bins.add(('68','2','RM_C10681'),107,2.)
    state.known_legsplit_route_state=dict(cohorts=[],plan=None,
        aggregate_transport=NS(start=100,dt=10,last_macro=None,bins=bins))
    rebase_projection(cfg,state)
    obj=state.known_legsplit_route_state['aggregate_transport']
    assert isinstance(obj.bins,UrbanTickBins) and obj.start==10 and obj.dt==1
    assert obj.bins.origin_sec==100 and obj.bins.step_sec==10
    obj.bins.advance(10);assert obj.bins.waiting[0]==0.
    obj.bins.add(('68','2','RM_C10681'),12,3.)
    obj.bins.advance(11);assert obj.bins.waiting[0]==2.
    obj.bins.advance(12);assert obj.bins.waiting[0]==5.
    obj.bins.verify()


def test_late_validation_failure_is_atomic_for_all_calendars_and_cfg():
    cfg,state=fixture();state.lane_offramp_runtime=NS(last_drain=99)
    before=pickle.dumps((cfg,state),protocol=5)
    with pytest.raises(ValueError,match='already advanced'):rebase_projection(cfg,state)
    assert pickle.dumps((cfg,state),protocol=5)==before


def test_no_rebase_after_advance_or_existing_coarse_state():
    cfg,state=fixture();state.native_input_prehead_state['last_step']=100
    with pytest.raises(ValueError,match='unadvanced'):rebase_projection(cfg,state)
    cfg,state=fixture();rebase_projection(cfg,state)
    with pytest.raises(ValueError,match='fresh1s'):rebase_projection(cfg,state)


def test_already_queued_cohort_stays_ready_with_all_nonclock_fields():
    cfg,state=fixture()
    state.native_input_prehead_state['cohorts']=[dict(due=87,ready=99,vehicles=2.,stage='queue',route='W',passed_first=True)]
    rebase_projection(cfg,state)
    assert state.native_input_prehead_state['cohorts']==[dict(due=9,ready=10,vehicles=2.,stage='queue',route='W',passed_first=True)]


def test_stale_arrival_entry_rejected_instead_of_dropped_or_reinjected():
    cfg,state=fixture();state.urban_arrival_buffer['A'][99]=2.
    before=pickle.dumps((cfg,state),protocol=5)
    with pytest.raises(ValueError,match='stale'):rebase_projection(cfg,state)
    assert pickle.dumps((cfg,state),protocol=5)==before


@pytest.mark.parametrize('duration',[True,0,5,11])
def test_unsupported_clock_rejected(duration):
    cfg,state=fixture()
    with pytest.raises(ValueError):rebase_projection(cfg,state,duration)


def test_default1s_is_noop():
    cfg,state=fixture();before=pickle.dumps((cfg,state),protocol=5)
    assert rebase_projection(cfg,state,1)=={'urban_clock_rebased':False}
    assert pickle.dumps((cfg,state),protocol=5)==before


def test_new_gate_arrivals_and_queued_downstream_travel_preserve_seconds():
    cfg,state=fixture()
    original={'source':'A','timings':{'west':{'delay_steps':37},'east':{'delay_steps':80}}}
    cfg.network.physical_gate_travel=original
    state.known_legsplit_route_state={'cohorts':[dict(due=100,downstream_steps=31,vehicles=2.,target='free')],'plan':None}
    rebase_projection(cfg,state)
    assert cfg.network.physical_gate_travel['timings']=={'west':{'delay_steps':4},'east':{'delay_steps':8}}
    assert original['timings']['west']['delay_steps']==37
    assert state.known_legsplit_route_state['cohorts'][0]==dict(due=10,downstream_steps=4,vehicles=2.,target='free')
