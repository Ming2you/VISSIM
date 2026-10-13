"""Physical local steps and downstream travel must use distinct clocks."""
from types import SimpleNamespace as NS
import pytest
from src.models.state import SimulationConfig
from evaluation.controllers.lane_urban_runtime import LaneUrbanRuntime
from evaluation.controllers import urban_flow_accounting as flows


def test_local_substeps_keep_one_service_tick_and_endpoint_arrivals(monkeypatch):
    runtime=object.__new__(LaneUrbanRuntime)
    runtime.last_step=9;runtime.port=NS(urban=NS(time=100))
    runtime.local_storage={71:'local71'};runtime.off_storage='off'
    runtime.exits_by_movement={'m':10634};runtime.origin='origin'
    cfg=NS(simulation=SimulationConfig(T_u=10,T_f=5,control_interval=150),
           network=NS(multirate_urban_clock_sec=10))
    state=NS(urban_link_storage={'local71':3.,'off':4.,'origin':5.},urban_movement_queue={'m':2.})
    calls=[]
    def advance(s,c,cfg,sec,**kw):
        calls.append((sec,kw['service_step'],kw['arrival_step'],kw['signal_cfg'].simulation.T_u_sec))
        assert cfg.simulation.T_u_sec==10
        runtime.port.urban.time+=1
        return {'lane_urban_exit_veh':.5,'lane_urban_stock_veh':8.}
    monkeypatch.setattr(runtime,'_advance_physical',advance,raising=False)
    monkeypatch.setattr(flows,'get_ledger',lambda s:None)
    result=runtime.advance(state,None,cfg,10)
    assert calls==[(t,10,11,1) for t in range(100,110)]
    assert runtime.last_step==10 and runtime.port.urban.time==110
    assert result['lane_urban_exit_veh']==5.
    assert result['lane_urban_stock_veh']==8.
    assert cfg.simulation.T_u_sec==10


def test_endpoint_receipt_uses_current_service_and_later_travel(monkeypatch):
    from evaluation.controllers import route_choice_corridor as rc
    cfg=NS(network=NS(route_choice_corridor=True))
    calls=[]
    monkeypatch.setattr(rc,'receive_accepted',lambda s,c,m,n,k,**kw:calls.append((k,kw)) or True)
    assert flows._receive_corridor(None,cfg,'m',2.,10,entry_step=11)
    assert calls==[(10,{'entry_step':11})]


def test_earlier_receipt_is_rejected_before_handler(monkeypatch):
    with pytest.raises(ValueError,match='entry'):
        flows._receive_corridor(None,NS(network=NS()),'m',2.,10,entry_step=9)


def test_route_receipts_keep_one_service_budget_and_start_travel_at_end(monkeypatch):
    from evaluation.controllers import route_choice_corridor as rc
    turn={'connector':'c','service_veh_h':1440.,'signal_controlled':False}
    spec={'prefix_storage':'p','capacity_veh':{'p':20.},'turns':{'m':turn},
          'prefix_travel_segments':{'c':[{'start':0.,'stop':70.}]}}
    cfg=NS(simulation=SimulationConfig(T_u=10,T_f=5,control_interval=150),
           network=NS(urban_avg_speed_km_h=36.))
    state=NS(urban_link_storage={'p':20.},urban_link_speed_kph={'p':36.},
        route_choice_corridor_state={'last_step':10,'cohorts':[],
            'service_limit_veh':{},'service_used_veh':{},'received_veh':0.})
    monkeypatch.setattr(rc,'_movement_spec',lambda c,m:spec)
    for _ in range(2):
        assert rc.intended_departure(state,None,cfg,'m',2.,10)==2.
        state.urban_link_storage['p']-=2.
        assert rc.receive_accepted(state,cfg,'m',2.,10,entry_step=11)
    local=state.route_choice_corridor_state
    assert local['service_used_veh']['c']==4.
    assert rc.intended_departure(state,None,cfg,'m',2.,10)==0.
    assert all(c['due']==12 and c['source']=='m' for c in local['cohorts'])
    assert sum(c['vehicles'] for c in local['cohorts'])==4.


def test_local_wrong_absolute_clock_rejected_before_physical_step(monkeypatch):
    runtime=object.__new__(LaneUrbanRuntime)
    runtime.last_step=9;runtime.port=NS(urban=NS(time=101))
    cfg=NS(simulation=SimulationConfig(T_u=10,T_f=5,control_interval=150))
    with pytest.raises(ValueError,match='Noncontiguous'):
        runtime.advance(None,None,cfg,10)
    assert runtime.port.urban.time==101 and runtime.last_step==9
