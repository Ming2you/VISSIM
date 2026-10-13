from types import SimpleNamespace as NS
import pytest
from evaluation.controllers import multirate_freeway as macro


class Clock:
    T_f=5.
    @property
    def T_f_sec(self):return self.T_f


def fixture(monkeypatch):
    from evaluation.controllers import control_area_objective as area
    visits=[];stamps=[];calls=[]
    ledger=NS(begin_response_step=lambda *x:stamps.append(x),
              complete_constraint_coverage=lambda x:visits.append(x))
    monkeypatch.setattr(area,'get_ledger',lambda state:ledger)
    monkeypatch.setattr(macro,'time_limit',lambda runtime,state:2.)
    cfg=NS(simulation=Clock())
    runtime=NS(lanes={},configs={'FW':cfg},roads=('FW',),ramps={'r':{}},offramps={'o':{}},time_sec=100.)
    state=NS(time_sec=100.)
    def advance(state,control,demand,**kw):
        dt=runtime.configs['FW'].simulation.T_f_sec
        calls.append(dict(time=state.time_sec,dt=dt,**kw));runtime.time_sec+=dt
        return 10*dt/3600.,{'o':kw['off_capacities']['o']/2.},{'FW':{'density_projection_count':0.,'rate':120.}}
    runtime.advance=advance
    return runtime,state,cfg,calls,visits,stamps


def test_shared_substeps_spend_ramp_packet_and_exit_budget_once(monkeypatch):
    runtime,state,cfg,calls,visits,stamps=fixture(monkeypatch)
    cost,off,rows=macro.advance(runtime,state,None,None,ramp_releases={'r':720.},off_capacities={'o':360.})
    assert len(calls)==3 and sum(c['dt'] for c in calls)==pytest.approx(5.)
    assert sum(c['ramp_releases']['r']*c['dt']/3600. for c in calls)==pytest.approx(1.)
    assert [c['complete_ramp_packets'] for c in calls]==[False,False,True]
    assert all(not c['complete_allocator_scope'] for c in calls)
    assert off=={'o':180.} and cost==pytest.approx(50/3600.)
    assert rows['FW']['rate']==pytest.approx(120.)
    assert runtime.time_sec==105. and state.time_sec==100.
    assert runtime.configs['FW'] is cfg and cfg.simulation.T_f==5.
    assert visits==['freeway_allocator'] and stamps[-1]==('freeway',100.,105.)


def test_long_cell_can_use_one_real_five_second_step(monkeypatch):
    runtime,state,cfg,calls,_,_=fixture(monkeypatch)
    monkeypatch.setattr(macro,'time_limit',lambda *args:5.)
    macro.advance(runtime,state,None,None,ramp_releases={'r':0.},off_capacities={'o':0.})
    assert len(calls)==1 and calls[0]['dt']==5. and calls[0]['complete_ramp_packets']


def test_macro_preserves_every_accepted_exit_route_class(monkeypatch):
    runtime,state,_,calls,_,_=fixture(monkeypatch)
    state.offramp_route_inventory_state={'last_offramp_receipts':{}}
    original=runtime.advance
    def advance(*a,**kw):
        cost,flows,rows=original(*a,**kw)
        state.offramp_route_inventory_state['last_offramp_receipts']['FW']={
            'end_sec':runtime.time_sec,'ports':{'o':{'route'+str(len(calls)):flows['o']*calls[-1]['dt']/3600.}}}
        return cost,flows,rows
    runtime.advance=advance
    _,flows,_=macro.advance(runtime,state,None,None,ramp_releases={'r':0.},off_capacities={'o':360.})
    receipt=state.offramp_route_inventory_state['last_offramp_receipts']['FW']
    assert receipt['end_sec']==105. and len(receipt['ports']['o'])==3
    assert sum(receipt['ports']['o'].values())==pytest.approx(flows['o']*5/3600.)


@pytest.mark.parametrize('change',('lane_model','wrong_clock','invalid_supply'))
def test_reject_unsupported_or_invalid_macro_before_mutation(monkeypatch,change):
    runtime,state,cfg,calls,_,_=fixture(monkeypatch)
    q=1.
    if change=='lane_model':runtime.lanes={'FW':object()}
    if change=='wrong_clock':cfg.simulation.T_f=1.
    if change=='invalid_supply':q=-1.
    with pytest.raises(ValueError):macro.advance(runtime,state,None,None,ramp_releases={'r':q},off_capacities={'o':1.})
    assert calls==[] and runtime.time_sec==state.time_sec==100.


def test_failed_step_does_not_leave_temporary_clock_or_configs(monkeypatch):
    runtime,state,cfg,_,_,_=fixture(monkeypatch)
    def fail(*a,**kw):raise ArithmeticError('example physical failure')
    runtime.advance=fail
    with pytest.raises(ArithmeticError):macro.advance(runtime,state,None,None,ramp_releases={'r':0.},off_capacities={'o':0.})
    assert runtime.configs['FW'] is cfg and cfg.simulation.T_f==5. and state.time_sec==100.


def test_screen_uses_actual_speed_not_posted_limit(monkeypatch):
    from evaluation.controllers import freeway_geometry as geometry
    monkeypatch.setattr(geometry,'cell_lengths_km',lambda *a:[.076])
    net=NS(metanet_tau_h=12/3600.,freeway_segment_params={})
    runtime=NS(configs={'FW':NS(network=net)})
    state=NS(freeway_speed={'FW':[150.]})
    assert macro.time_limit(runtime,state)==pytest.approx(.9*3600.*.076/150.)


def test_clock_option_is_noop_by_default_and_only_changes_prediction():
    from src.models.state import SimulationConfig
    sim=SimulationConfig(T_f=1,T_u=1,control_interval=150)
    road=NS(simulation=SimulationConfig(T_f=1,T_u=1))
    cfg=NS(simulation=sim,network=NS())
    state=NS(time_sec=900.,lane_freeway_runtime=NS(time_sec=900.,lanes={},configs={'FW':road}),
        lane_ramp_runtime=NS(buffers={}))
    assert macro.configure(cfg,{},state)=={} and sim.T_f_sec==1
    result=macro.configure(cfg,{'freeway':{'multirate_exchange_sec':5}},state)
    assert sim.T_f_sec==road.simulation.T_f_sec==5 and sim.T_u_sec==1 and sim.T_c_sec==150
    assert result['native_simulation_clock_changed'] is False
    assert sim.derived_time_ratios==dict(K_fu=5,K_cf=30,K_cu=150)
    with pytest.raises(ValueError,match='freshly'):macro.configure(cfg,{'freeway':{'multirate_exchange_sec':5}},state)


@pytest.mark.parametrize('fw,urban,enabled,road_clock,lanes,accepted',[
    (1,1,False,1,{},True),
    (5,1,True,5,{},True),
    (5,1,False,5,{},False),
    (5,1,True,1,{},False),
    (5,1,True,5,{'FW':object()},False),
    (10,1,True,10,{},False),
    (5,10,True,5,{},False),
])
def test_joint_clock_admits_only_wired_supported_mode(fw,urban,enabled,road_clock,lanes,accepted):
    cfg=NS(simulation=NS(T_f_sec=fw,T_u_sec=urban),
           network=NS(multirate_freeway_exchange_enabled=enabled))
    state=NS(lane_freeway_runtime=NS(lanes=lanes,
             configs={'FW':NS(simulation=NS(T_f_sec=road_clock))}))
    assert macro.supports_joint_clock(cfg,state) is accepted
