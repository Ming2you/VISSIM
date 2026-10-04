"""Physical route timing, destination preservation and accepted-flow conservation."""
from types import SimpleNamespace as NS
from pathlib import Path
import copy
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'vendor/NumSim-mine'))

import pytest
from evaluation.controllers import route_choice_corridor as route
from test_known_wout_native_prior import inputs, NAMES


def fixture():
    tree,proof=inputs()
    travel=route._known_travel_geometry(tree,proof,NAMES)
    storage=proof['storage']
    spec=dict(storage=storage,physical_travel=travel,choice_position_m=proof['choice_position_m'],
        incoming_movements=proof['incoming_movements'],future_choice_weights={'free':.2,'RM_C10646':.2,'RM_C10681':.6})
    movements={m:dict(receiving_link=storage,origin='source') for m in proof['incoming_movements']}
    cfg=NS(simulation=NS(T_u_sec=1.), network=NS(known_legsplit_routes=spec,urban_avg_speed_km_h=36.,
        urban_movements=movements,urban_link_storage_veh={storage:100.},
        boundary_out_ramp_split={storage:dict(free=.2,ramps=dict(RM_C10646=.2,RM_C10681=.6))}))
    state=NS(urban_link_storage={storage:100.},urban_storage_release_buffer={},
        urban_link_speed_kph={'source':36.,storage:36.},
        known_legsplit_route_state=dict(cohorts=[],plan=None,received=0.,departed=0.))
    return cfg,state,spec


def request(state,cfg,step):
    spec=cfg.network.known_legsplit_routes
    pending=sum(v for d,v in state.urban_storage_release_buffer.get(spec['storage'],{}).items() if d>step)
    arrived=route._known_total(state)-pending
    # A legacy coarse travel multiplier must not further retard physical arrivals.
    return route.known_legsplit_requests(state,cfg,spec['storage'],arrived/100.,arrived,step)


def test_routes_end_at_their_own_entry_plane_not_the_long_free_tail():
    cfg,state,spec=fixture()
    paths=spec['physical_travel']['destinations']
    d={k:route._known_remaining(v,'68',spec['choice_position_m']) for k,v in paths.items()}
    assert 109.<d['RM_C10681']<111.
    assert 341.<d['free']<346.
    assert d['RM_C10681']<d['RM_C10646']
    assert all('123' not in [r['link'] for r in p] for p in paths.values())
    # Position farther along an unchanged path reduces remaining travel.
    assert route._known_remaining(paths['free'],'121',200.)<35.
    with pytest.raises(ValueError):route._known_remaining(paths['RM_C10681'],'121',10.)


def test_future_choice_waits_for_two_physical_legs_and_receiver_rejection_keeps_stock():
    cfg,state,spec=fixture();storage=spec['storage']
    state.urban_link_storage[storage]-=10.
    assert route.known_legsplit_receive(state,cfg,10.,999,movement='SC1004_E_SC1005_to_W',entry_step=0)
    c=state.known_legsplit_route_state['cohorts'][0]
    choice=c['due']; assert 6<=choice<=9
    assert request(state,cfg,choice-1)=={}
    route.known_legsplit_commit(state,cfg,[],choice-1)
    assert request(state,cfg,choice)=={}
    route.known_legsplit_commit(state,cfg,[],choice)
    chosen={r['target']:r for r in state.known_legsplit_route_state['cohorts']}
    east=chosen['RM_C10681']['due']
    assert east==choice+11
    assert chosen['RM_C10646']['due']>east
    assert request(state,cfg,east)=={'RM_C10681':6.}
    frozen=copy.deepcopy(state)
    route.known_legsplit_commit(state,cfg,[],east)
    assert route._known_total(state)==10.
    assert state.urban_link_storage[storage]==90.
    # Draw is permanent even when a receiver stays blocked and priors change.
    spec['future_choice_weights']={'free':1.,'RM_C10646':0.,'RM_C10681':0.}
    assert request(state,cfg,east+1)=={'RM_C10681':6.}
    state.urban_link_storage[storage]+=2.
    route.known_legsplit_commit(state,cfg,[(storage,'RM_C10681',2.)],east+1)
    assert route._known_total(state)==8.
    assert frozen.known_legsplit_route_state['cohorts'][2]['vehicles']==6.
    route._known_check(state,cfg)


def test_direct_offramp_receipt_can_only_continue_to_free_tail():
    cfg,state,spec=fixture();storage=spec['storage']
    state.urban_link_storage[storage]-=5.
    assert route.known_legsplit_receive(state,cfg,5.,999,off_ramp='OR_F_E',entry_step=20)
    cohort=state.known_legsplit_route_state['cohorts'][0]
    assert cohort['target']=='free'
    assert 20<cohort['due']<45
    req=request(state,cfg,cohort['due'])
    assert req=={'free':5.}
    state.urban_link_storage[storage]+=5.
    route.known_legsplit_commit(state,cfg,[(storage,None,5.)],cohort['due'])
    assert route._known_total(state)==0.


def test_physical_mode_requires_native_priors_and_timestamped_receipts():
    cfg,state,spec=fixture()
    with pytest.raises(ValueError):
        route.configure_known_legsplit(cfg,{'urban':{'known_wout_physical_travel':True}},state,{})
    with pytest.raises(ValueError):
        route.known_legsplit_receive(state,cfg,1.,20,movement='SC1004_E_SC1005_to_W')


def test_physical_travel_rejects_a_new_signal_on_the_travel_path():
    tree,proof=inputs()
    ET.SubElement(tree.find('./signalHeads'),'signalHead',lane='68 1',pos='50')
    with pytest.raises(ValueError,match='unmodelled signal'):
        route._known_travel_geometry(tree,proof,NAMES)


def test_initial_timing_uses_current_positions_without_adding_or_rerouting_stock(monkeypatch):
    cfg,state,spec=fixture();_,proof=inputs();storage=spec['storage']
    spec.update(routes={k:{**v,**({'target':NAMES.get(v['target'],v['target'])} if 'target' in v else {})}
                        for k,v in proof['native_routes'].items()},prechoice_connectors=proof['prechoice_connectors'])
    records=[dict(veh_no=i,link_no=link,position_m=pos,speed_kph=36.)
             for i,link,pos in [(1,68,20.),(2,10629,60.),(3,68,30.)]]
    routes={i:dict(route_decision_type='STATIC',route_decision_no=d,route_no=r)
            for i,d,r in [(1,1135,4),(2,1123,2),(3,0,0)]}
    monkeypatch.setattr(route,'complete_records',lambda raw:records)
    monkeypatch.setattr(route,'complete_vehicle_routes',lambda raw,required:routes)
    state.time_sec=0.
    state.urban_link_storage[storage]=97.
    state.urban_arrival_buffer={}
    state.urban_storage_release_buffer={storage:{999:2.}}
    state.local_observation_summary={'projection_diagnostics':{'physical_stock_assignment_by_link':{
        '68':{'storage:'+storage:2.},'10629':{'storage:'+storage:1.}}}}
    del state.known_legsplit_route_state
    route.initialize_known_legsplit(state,cfg,{})
    cohorts=state.known_legsplit_route_state['cohorts']
    assert [c['target'] for c in cohorts]==['RM_C10681','prechoice','unknown']
    assert cohorts[0]['due']==10 and cohorts[1]['due']==2 and cohorts[2]['due']==0
    assert state.urban_link_storage[storage]==97.
    assert sum(state.urban_storage_release_buffer[storage].values())==2.
    assert 999 not in state.urban_storage_release_buffer[storage]
    route._known_check(state,cfg)
