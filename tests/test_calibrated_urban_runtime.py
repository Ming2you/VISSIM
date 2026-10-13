"""Native bridge regression: model copies must retain calibrated transport."""
import copy
from types import SimpleNamespace as NS
from unittest.mock import patch
from evaluation.controllers import calibrated_urban_runtime as runtime
from evaluation.controllers.aggregate_route_corridors import Routes
from src.models import urban_queue_model as uqm

def fixture():
    data=dict(document_sha256='fixture',source_route_support={'sources':{'1099':{'category_shares':{
        'straight':.5,'right':.2,'left':.2,'unresolved':.1}}}},
        side_geometry=dict(lane_factor=1.,sources={'1099':dict(distance_m=200.,connector='c',source='s')}),
        prehead_geometry=dict(distance_m=200.))
    cfg=NS(network=NS(urban_avg_speed_km_h=36.,calibrated_urban_native348=data),simulation=NS(T_u_sec=10))
    state=NS(urban_link_speed_kph={'SC1_to_SC101':36.,'in_SC108_W':36.},urban_arrival_buffer={})
    spec=dict(decision='1099',prefix_storage='s',branches={'1':dict(destination='SC1_to_SC101',connector='c')})
    return cfg,state,spec,data

def test_side_clock_survives_configuration_copy_and_tags_same_stock():
    cfg,state,spec,data=fixture();private=copy.deepcopy(cfg)
    def advance(self,state,control,current,step,spec):
        due=step+uqm._link_delay_steps(state,current,'SC1_to_SC101')
        uqm._schedule(state.urban_arrival_buffer,'SC1_to_SC101',due,10.)
        return due
    with patch.object(Routes,'advance_one',advance),patch.object(uqm,'_link_delay_steps',return_value=77):
        with runtime.side_runtime(cfg,data):
            due=Routes.advance_one(None,state,None,private,0,spec)
    assert due==2
    assert state.urban_arrival_buffer=={'SC1_to_SC101':{2:10.}}
    tags=state._sc101_route_tags303
    assert sum(tags['pending'][2]['1099'].values())==10.
    assert sum(tags['scheduled'].values())==10.

def test_side_clock_does_not_affect_unconfigured_model():
    cfg,state,spec,data=fixture();private=copy.deepcopy(cfg);del private.network.calibrated_urban_native348
    def advance(self,state,control,current,step,spec):return uqm._link_delay_steps(state,current,'SC1_to_SC101')
    with patch.object(Routes,'advance_one',advance),patch.object(uqm,'_link_delay_steps',return_value=77):
        with runtime.side_runtime(cfg,data):assert Routes.advance_one(None,state,None,private,0,spec)==77
    assert not hasattr(state,'_sc101_route_tags303')

def test_prehead_clock_survives_copy_and_keeps_other_links_unchanged():
    cfg,state,spec,data=fixture();private=copy.deepcopy(cfg)
    with patch.object(uqm,'_link_delay_steps',return_value=77):
        with runtime.prehead_runtime(data):
            assert uqm._link_delay_steps(state,private,'in_SC108_W')==2
            assert uqm._link_delay_steps(state,private,'another')==77
        assert uqm._link_delay_steps(state,private,'in_SC108_W')==77

def test_absent_option_is_noop():
    assert runtime.load({}) is None
    cfg,state,spec,data=fixture()
    result,metadata=runtime.initialize(cfg,state,None,None,None)
    assert result is state and metadata=={}

def test_empty_current_link_retains_other_stock_and_nonempty_is_not_skipped():
    from unittest.mock import Mock
    component=NS(LINK='123',project=Mock(return_value=('checked',{})))
    state=NS(time_sec=7500,local_observation_summary={'projection_diagnostics':{'physical_stock_assignment_by_link':{}}})
    raw={'vehicle_records':{'complete':True,'records':[]}}
    result,receipt=runtime.project_current_link(component,state,None,raw,None,None,True,{})
    assert result is state and receipt['empty_current_cohort']
    component.project.assert_not_called()
    raw['vehicle_records']['records']=[{'link_no':123}]
    assert runtime.project_current_link(component,state,None,raw,None,None,True,{})[0]=='checked'
    component.project.assert_called_once()
