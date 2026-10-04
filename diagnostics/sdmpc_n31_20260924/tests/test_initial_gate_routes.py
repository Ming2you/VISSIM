"""Pinned current-state destinations and parent-stock conservation; no VISSIM."""
import copy
import json
import math
from pathlib import Path
from types import SimpleNamespace as NS
import sys

import pytest

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'vendor/NumSim-mine'))
from evaluation.controllers import physical_ramp_branches as ramp
from evaluation.controllers.lane_plant_runtime import bind_current_routes

HERE=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
SOURCE='in_SC1001_W'
E='SC1001_W_to_onE'
W='SC1001_W_to_onW'


def geometry_timing_fixture():
    city={'city':.25}
    cfg=NS(network=NS(urban_movements={W:{'beta':.5},E:{'beta':.25}}),
           simulation=NS(T_u_sec=1.))
    paths={'1':[('32',80.)],'3':[('32',100.),('129',100.)],
           '2':[('32',100.),('129',100.)]}
    geometry={k:[dict(link=link,start=0.,stop=end) for link,end in path] for k,path in paths.items()}
    spec=dict(source=SOURCE,movements={'1':W,'3':E},geometry=geometry,
        timings={k:dict(parts=[dict(link=s['link'],speed_kph=36.) for s in ss]) for k,ss in geometry.items()})
    records=[dict(veh_no=1,link_no=32,position_m=0.,speed_kph=36.),
             dict(veh_no=2,link_no=32,position_m=60.,speed_kph=36.),
             dict(veh_no=3,link_no=129,position_m=25.,speed_kph=36.)]
    return NS(time_sec=0.),cfg,{'vehicle_records':{'stopped_threshold_kph':5.}},records,city,spec


def test_geometry_timing_uses_positions_preserves_stock_and_conditional_shares():
    state,cfg,raw,records,city,spec=geometry_timing_fixture()
    before=copy.deepcopy((state,cfg,raw,records))
    paired,tags,proof,retimed=ramp._geometry_gate_initial_tags(state,cfg,raw,records,
        {'32':2.,'129':1.,'127':1.},{'127'},city,{1:4.},4.,spec)
    assert sum(paired.values())==pytest.approx(4.)
    assert retimed==3.
    totals={m:sum(row.get(m,0.) for row in tags.values()) for m in (W,E,'city')}
    assert totals==pytest.approx({W:1.,E:1.,'city':2.})
    assert tags[2][W]==.5 and tags[8][W]==.5
    assert tags[1]=={'city':1.}
    assert sum(x['vehicles'] for x in proof if x.get('vehicle')==3)==1.
    assert not [x for x in proof if x.get('vehicle')==3 and x['route_family']=='1']
    assert (state,cfg,raw,records)==before


def test_geometry_timing_refuses_unidentified_fractional_vehicle_ownership():
    state,cfg,raw,records,city,spec=geometry_timing_fixture()
    with pytest.raises(ValueError,match='exact physical vehicle ownership'):
        ramp._geometry_gate_initial_tags(state,cfg,raw,records,{'32':.5},set(),city,{1:.5},.5,spec)


def test_shared_migration_removes_only_known_city_at_its_original_due_time():
    from evaluation.controllers import lane_offramp_runtime as off
    state,cfg,raw,records,city,spec=geometry_timing_fixture()
    paired,tags,proof,_=ramp._geometry_gate_initial_tags(state,cfg,raw,records,
        {'32':2.,'129':1.,'127':1.},{'127'},city,{8:4.},4.,spec)
    before=copy.deepcopy((paired,tags,proof))
    removal=off._retimed_city_reservations(proof,paired,tags,{'city':1.},1.)
    assert removal=={8:{'city':1.}}
    assert (paired,tags,proof)==before
    remaining=copy.deepcopy(tags)
    for due,row in removal.items():
        for movement,n in row.items():remaining[due][movement]-=n
    # Preserve all three upstream vehicles and their exact destination/due labels.
    assert sum(sum(r.values()) for r in remaining.values())==pytest.approx(3.)
    for due,row in tags.items():
        for movement in (E,W):assert remaining[due].get(movement,0.)==row.get(movement,0.)
    assert remaining[8][W]==.5
    assert remaining[8]['city']==.5  # upstream vehicle3, not the relocated city car


@pytest.mark.parametrize('fault', ['missing','amount','tag','nonfinite'])
def test_retimed_shared_migration_rejects_inconsistent_provenance_without_mutation(fault):
    from evaluation.controllers import lane_offramp_runtime as off
    state,cfg,raw,records,city,spec=geometry_timing_fixture()
    paired,tags,proof,_=ramp._geometry_gate_initial_tags(state,cfg,raw,records,
        {'32':2.,'129':1.,'127':1.},{'127'},city,{8:4.},4.,spec)
    amount=1.
    if fault=='missing':proof[0].pop('paired_reservations')
    elif fault=='amount':amount=2.
    elif fault=='tag':tags[8]['city']=.1
    else:proof[0]['paired_reservations'][8]['city']=float('inf')
    before=copy.deepcopy((paired,tags,proof))
    with pytest.raises(ValueError,match='reservation'):
        off._retimed_city_reservations(proof,paired,tags,{'city':1.},amount)
    assert (paired,tags,proof)==before


def test_geometry_timing_excludes_branch_already_passed_within_same_link():
    state,cfg,raw,records,city,spec=geometry_timing_fixture()
    records=[{**records[0],'position_m':90.}]
    paired,tags,proof,retimed=ramp._geometry_gate_initial_tags(
        state,cfg,raw,records,{'32':1.},set(),city,{1:1.},1.,spec)
    assert sum(paired.values())==1. and retimed==1.
    assert all(W not in row for row in tags.values())
    assert sum(row.get(E,0.) for row in tags.values())==.5


def test_geometry_timing_requires_existing_city_lock_and_future_travel():
    for option in (1,True):
        with pytest.raises(ValueError,match='geometry timing requires'):
            ramp.initialize_gate_routes(None,None,{'urban':{'ramp':{'initial_gate_geometry_timing':option}}},None)


def fixture():
    audit=json.loads((HERE/'gate_audit1200/audit.json').read_bytes())
    tuning=json.loads((HERE/'selected/config_n31_v2.json').read_bytes())
    topology=json.loads((ROOT/tuning['urban']['physical_ramp_branches']).read_bytes())
    raw=json.loads((HERE/'selected_init1200_final/state_001200.json').read_bytes())
    frame=json.loads((HERE/'selected_init1200_final/lane_observations/frame_001200.json').read_text(encoding='utf-16'))
    raw=bind_current_routes(raw,{'frames':[frame]})
    cfg=NS(network=NS(physical_ramp_branches=topology,urban_movements=audit['source_specs'],
                     movement_capacity_by_movement_veh_h=audit['capacities'],
                     urban_link_storage_veh={SOURCE:1000.},urban_avg_speed_km_h=40.),
           simulation=NS(T_u_sec=1.))
    prior={int(k):v for k,v in audit['storage_release_buffer'][SOURCE].items()}
    state=NS(time_sec=1200.,local_observation_summary=audit['projection'],
             urban_link_storage={SOURCE:1000.-sum(prior.values())},
             urban_movement_queue=audit['urban_movement_queue'],
             urban_inflow_transit_buffer={},
             urban_arrival_buffer={SOURCE:dict(prior)},
             urban_storage_release_buffer={SOURCE:dict(prior)})
    tuning['urban'].setdefault('ramp',{})['initial_native_gate_routes']=True
    return cfg,state,tuning,raw


def test_disabled_is_inert_and_non_boolean_fails():
    assert ramp.initialize_gate_routes(None,None,{},None)=={}
    with pytest.raises(ValueError,match='boolean'):
        ramp.initialize_gate_routes(None,None,{'urban':{'ramp':{'initial_native_gate_routes':1}}},None)


@pytest.mark.parametrize('physical,locked', [({'32':111,'127':41,'129':12},41.),
    ({'32':44,'127':14,'129':7,'10695':1},15.),({'32':2,'10695':.5},.5)])
def test_topology_city_lock_without_routes_preserves_paired_stock(physical,locked):
    cfg,state,tuning,raw=fixture()
    tuning['urban']['ramp']={'initial_gate_city_lock':True}
    rows=[]
    for link,count in physical.items():
        for _ in range(math.ceil(count)):
            rows.append(dict(veh_no=len(rows)+1,link_no=int(link),position_m=1.,speed_kph=0.))
    raw.pop('vehicle_routes',None)
    raw['vehicle_records'].update(records=rows,record_count=len(rows),collection_count_before=len(rows),
        collection_count_after=len(rows),full_network_link_counts={k:math.ceil(v) for k,v in physical.items()})
    state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']={
        k:{'storage:'+SOURCE:v} for k,v in physical.items()}
    count=sum(physical.values());state.urban_link_storage[SOURCE]=1000.-count
    state.urban_arrival_buffer[SOURCE]={1201:count*.4,1300:count*.6}
    state.urban_storage_release_buffer=copy.deepcopy(state.urban_arrival_buffer)
    before=copy.deepcopy(state)
    report=ramp.initialize_gate_routes(state,cfg,tuning,raw)
    assert report['gate_initial_city_locked_veh']==locked
    assert report['gate_initial_unresolved_destination_veh']==count-locked
    for key in ('urban_link_storage','urban_arrival_buffer','urban_storage_release_buffer','urban_movement_queue'):
        assert getattr(state,key)==getattr(before,key)
    tags=state.gate_initial_route_tags[SOURCE]
    passed=physical.get('10778',0.)+physical.get('129',0.)
    assert sum(sum(v.values()) for v in tags.values())==pytest.approx(locked+passed)
    assert all(W not in row for row in tags.values())
    assert report['gate_initial_reachability_conditioned_veh']==passed
    routing=[(m,s['beta']) for m,s in cfg.network.urban_movements.items()]
    result={m:0. for m,_ in routing}
    for step,arrived in before.urban_arrival_buffer[SOURCE].items():
        values=ramp.split_tagged_arrival(state,cfg,SOURCE,step,arrived,routing)
        assert sum(v for _,v in values)==pytest.approx(arrived)
        for m,v in values:result[m]+=v
    b_w,b_e=(cfg.network.urban_movements[m]['beta'] for m in (W,E))
    assert result[W]==pytest.approx((count-locked-passed)*b_w)
    assert result[E]==pytest.approx((count-locked-passed)*b_e+passed*b_e/(1-b_w))


def test_city_lock_cannot_silently_replace_strict_native_routes():
    cfg,state,tuning,raw=fixture()
    tuning['urban']['ramp']['initial_gate_city_lock']=True
    before=copy.deepcopy(state.__dict__)
    with pytest.raises(ValueError,match='Choose topology-only'):
        ramp.initialize_gate_routes(state,cfg,tuning,raw)
    assert state.__dict__==before


@pytest.mark.parametrize('link', ['10778','129'])
def test_initial_downstream_stock_cannot_choose_the_passed_10482_exit(link):
    cfg,state,tuning,raw=fixture()
    tuning['urban']['ramp']={'initial_gate_city_lock':True}
    raw.pop('vehicle_routes',None)
    rows=[dict(veh_no=i+1,link_no=int(link),position_m=1.,speed_kph=20.) for i in range(10)]
    raw['vehicle_records'].update(records=rows,record_count=10,collection_count_before=10,
        collection_count_after=10,full_network_link_counts={link:10})
    state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']={
        link:{'storage:'+SOURCE:10.}}
    state.urban_link_storage[SOURCE]=990.
    state.urban_arrival_buffer={SOURCE:{1201:4.,1300:6.}}
    state.urban_storage_release_buffer=copy.deepcopy(state.urban_arrival_buffer)
    before=copy.deepcopy(state)
    ramp.initialize_gate_routes(state,cfg,tuning,raw)
    assert state.urban_link_storage==before.urban_link_storage
    assert state.urban_arrival_buffer==state.urban_storage_release_buffer==before.urban_arrival_buffer
    routing=[(m,s['beta']) for m,s in cfg.network.urban_movements.items()]
    result={m:0. for m,_ in routing}
    for step,amount in before.urban_arrival_buffer[SOURCE].items():
        split=ramp.split_tagged_arrival(state,cfg,SOURCE,step,amount,routing)
        assert sum(v for _,v in split)==pytest.approx(amount)
        for m,v in split:result[m]+=v
    assert result[W]==0., '10482 branches from32 before10778/129; it is no longer reachable'
    feasible_total=sum(beta for m,beta in routing if m!=W)
    for m,beta in routing:
        if m!=W:assert result[m]==pytest.approx(10*beta/feasible_total)


def test_existing_routes_and_parent_stock_are_preserved():
    cfg,state,tuning,raw=fixture()
    before=copy.deepcopy(state)
    report=ramp.initialize_gate_routes(state,cfg,tuning,raw)
    assert report['gate_initial_route_tagged_veh']==163.
    assert state.urban_link_storage==before.urban_link_storage
    assert state.urban_movement_queue==before.urban_movement_queue
    assert state.local_observation_summary==before.local_observation_summary
    assert state.urban_arrival_buffer==state.urban_storage_release_buffer
    assert sum(state.urban_arrival_buffer[SOURCE].values())==pytest.approx(163.)
    tags=state.gate_initial_route_tags[SOURCE]
    totals={m:sum(v.get(m,0.) for v in tags.values()) for m in cfg.network.urban_movements}
    assert totals[W]==pytest.approx(88.)
    assert totals[E]==pytest.approx(40.+2./3.)
    assert sum(v for m,v in totals.items() if m not in (E,W))==pytest.approx(34.+1./3.)
    # All current129 vehicles with a freeway off-ramp route remain city-bound.
    off_ids={r['veh_no'] for r in raw['vehicle_routes']['records'] if r['route_decision_no']==1132}
    proofs=state.gate_initial_route_evidence
    assert any(r['vehicle'] in off_ids and r.get('link')=='129' for r in proofs)
    assert all(r['route_family']=='2' for r in proofs if r['vehicle'] in off_ids)
    assert report['gate_initial_future_generation_changed'] is False
    assert report['gate_initial_new_stock_veh']==0.
    with pytest.raises(ValueError,match='already initialized'):
        ramp.initialize_gate_routes(state,cfg,tuning,raw)


def test_timing_ends_at_connector_entry_and_retains_legacy_city_timing():
    cfg,state,tuning,raw=fixture()
    ramp.initialize_gate_routes(state,cfg,tuning,raw)
    records={r['veh_no']:r for r in raw['vehicle_records']['records']}
    for row in state.gate_initial_route_evidence:
        if row['vehicle'] is None:
            assert row['vehicles']==19.
            assert row['timing'].startswith('retained_legacy_city_schedule')
        elif row['route_family']=='1':
            # Native entry at1028.62075, not the528.87m ramp's exit plane.
            assert row['remaining_m']==pytest.approx(1028.62075298-records[row['vehicle']]['position_m'],abs=1e-5)
            assert row['due_sec']>1200.


def test_missing_past_ramp_choice_is_rejected_without_state_mutation():
    cfg,state,tuning,raw=fixture()
    target=next(r['veh_no'] for r in raw['vehicle_records']['records']
                if r['link_no']==32 and r['position_m']>100.)
    for row in raw['vehicle_routes']['records']:
        if row['veh_no']==target:
            row.update(route_decision_no=None,route_no=None,route_decision_type=None)
    before=copy.deepcopy(state.__dict__)
    with pytest.raises(ValueError,match='Missing committed'):
        ramp.initialize_gate_routes(state,cfg,tuning,raw)
    assert state.__dict__==before


def test_tag_consumption_is_once_and_future_untagged_arrivals_keep_old_choice():
    cfg,state,tuning,raw=fixture()
    ramp.initialize_gate_routes(state,cfg,tuning,raw)
    copied=copy.deepcopy(state)
    step=min(state.gate_initial_route_tags[SOURCE])
    named=dict(state.gate_initial_route_tags[SOURCE][step]);count=sum(named.values())
    routing=[(m,s['beta']) for m,s in cfg.network.urban_movements.items()]
    allocated=dict(ramp.split_tagged_arrival(state,cfg,SOURCE,step,count+4.,routing))
    assert sum(allocated.values())==pytest.approx(count+4.)
    for movement,beta in routing:
        assert allocated[movement]==pytest.approx(named.get(movement,0.)+4.*beta)
    assert step in copied.gate_initial_route_tags[SOURCE]
    assert ramp.split_tagged_arrival(state,cfg,SOURCE,step,4.,routing) is None
    assert ramp.split_tagged_arrival(state,cfg,'unrelated',step,4.,routing) is None


def test_parent_underflow_is_rejected_before_tag_consumption():
    cfg,state,tuning,raw=fixture()
    ramp.initialize_gate_routes(state,cfg,tuning,raw)
    step=min(state.gate_initial_route_tags[SOURCE]);named=state.gate_initial_route_tags[SOURCE][step]
    routing=[(m,s['beta']) for m,s in cfg.network.urban_movements.items()]
    with pytest.raises(ValueError,match='exceed'):
        ramp.split_tagged_arrival(state,cfg,SOURCE,step,sum(named.values())-.1,routing)
    assert state.gate_initial_route_tags[SOURCE][step]==named


def test_existing_shared_city_tags_still_split_and_consume_once():
    cfg=NS(network=NS(physical_ramp_branches={'shared_city_arrival':{
        'receiver':'another_source','conditional_shares':{'city_a':.75,'city_b':.25}}}))
    state=NS(shared_approach_state={'city_arrival_tags':{42:8.}})
    routing=[('ramp',.5),('city_a',.3),('city_b',.2)]
    actual=dict(ramp.split_tagged_arrival(state,cfg,'another_source',42,10.,routing))
    assert actual==pytest.approx({'ramp':1.,'city_a':6.6,'city_b':2.4})
    assert ramp.split_tagged_arrival(state,cfg,'another_source',42,2.,routing) is None


def future_fixture():
    cfg,state,tuning,raw=fixture()
    tuning['urban']['ramp']['native_gate_travel']=True
    ramp.initialize_gate_routes(state,cfg,tuning,raw)
    return cfg,state


def test_future_geometry_and_native_prior_are_physical():
    cfg,state=future_fixture();spec=cfg.network.physical_gate_travel
    assert spec['priors']==pytest.approx({'1':6/9,'2':1/9,'3':2/9})
    assert sum(p['distance_m'] for p in spec['timings']['1']['parts'])==pytest.approx(1028.62075298,abs=1e-5)
    assert spec['timings']['3']['delay_steps']>spec['timings']['1']['delay_steps']>150
    assert spec['timings']['2']['delay_steps']>spec['timings']['3']['delay_steps']
    assert spec['admission'].startswith('Aggregate physical approach space only')


def test_new_gate_arrival_is_not_instant_and_has_a_fixed_native_destination():
    cfg,state=future_fixture();spec=cfg.network.physical_gate_travel
    before=copy.deepcopy(state.urban_movement_queue)
    report=ramp.advance_gate(state,cfg,SOURCE,1200,9.)
    assert report==dict(desired_veh=9.,admitted_veh=9.,arrived_veh=0.,outside_wait_veh=0.)
    assert state.urban_movement_queue==before
    # Changing observed beta after generation cannot reroute an accepted cohort.
    cfg.network.urban_movements[E]['beta']=0.
    last=1200+max(s['delay_steps'] for s in spec['timings'].values())
    for step in range(1201,last+1):ramp.advance_gate(state,cfg,SOURCE,step,0.)
    assert state.urban_movement_queue[W]-before[W]==pytest.approx(6.)
    assert state.urban_movement_queue[E]-before[E]==pytest.approx(2.)
    assert sum(state.urban_movement_queue.values())-sum(before.values())==pytest.approx(9.)
    assert not state.urban_inflow_transit_buffer['gate:'+SOURCE]
    assert not state.gate_future_route_tags


def test_full_approach_keeps_uninserted_demand_and_admits_after_space_returns():
    cfg,state=future_fixture()
    state.urban_link_storage[SOURCE]=0.
    r=ramp.advance_gate(state,cfg,SOURCE,1200,9.)
    assert r['admitted_veh']==0. and r['outside_wait_veh']==9.
    assert state.urban_inflow_transit_buffer['gate_wait:'+SOURCE]=={0:9.}
    assert not state.urban_inflow_transit_buffer['gate:'+SOURCE]
    state.urban_link_storage[SOURCE]=4.+sum(state.urban_movement_queue.values())
    r=ramp.advance_gate(state,cfg,SOURCE,1201,0.)
    assert r['admitted_veh']==4. and r['outside_wait_veh']==5.
    # Accepted transit reserves those four places until it becomes a queue.
    assert ramp.advance_gate(state,cfg,SOURCE,1202,0.)['admitted_veh']==0.
    assert sum(state.urban_inflow_transit_buffer['gate:'+SOURCE].values())==pytest.approx(4.)
    assert state.gate_future_accounting['desired_veh']==9.


def test_future_mode_cannot_reinterpret_an_unknown_existing_gate_buffer():
    cfg,state,tuning,raw=fixture()
    tuning['urban']['ramp']['native_gate_travel']=True
    state.urban_inflow_transit_buffer['gate:'+SOURCE]={1234:1.}
    before=copy.deepcopy(state.__dict__)
    with pytest.raises(ValueError,match='untagged transit'):
        ramp.initialize_gate_routes(state,cfg,tuning,raw)
    assert state.__dict__==before


def test_future_routes_do_not_require_observed_routes_of_current_vehicles():
    cfg,state,tuning,raw=fixture()
    tuning['urban']['ramp']={'initial_gate_city_lock':True,'native_gate_travel':True}
    raw.pop('vehicle_routes',None)
    before=copy.deepcopy(state)
    ramp.initialize_gate_routes(state,cfg,tuning,raw)
    assert state.urban_arrival_buffer==before.urban_arrival_buffer
    assert state.urban_storage_release_buffer==before.urban_storage_release_buffer
    # Future vehicles have not chosen a route yet. Their native distribution
    # and physical travel path do not depend on a guessed past choice.
    expected_cfg,_=future_fixture()
    assert cfg.network.physical_gate_travel==expected_cfg.network.physical_gate_travel
    assert sum(sum(row.values()) for row in state.gate_initial_route_tags[SOURCE].values())<=163.
    assert ramp.advance_gate(state,cfg,SOURCE,1200,9.)['arrived_veh']==0.
    assert sum(state.urban_inflow_transit_buffer['gate:'+SOURCE].values())==9.


def test_future_city_mode_failure_preserves_all_initial_state():
    cfg,state,tuning,raw=fixture()
    tuning['urban']['ramp']={'initial_gate_city_lock':True,'native_gate_travel':True}
    raw.pop('vehicle_routes',None)
    state.urban_inflow_transit_buffer['gate:'+SOURCE]={1234:1.}
    before=copy.deepcopy(state.__dict__)
    with pytest.raises(ValueError,match='untagged transit'):
        ramp.initialize_gate_routes(state,cfg,tuning,raw)
    assert state.__dict__==before
    assert not hasattr(cfg.network,'physical_gate_travel')


def test_uninserted_cost_stays_outside_omega_until_admission_without_ttd():
    from evaluation.controllers.control_area_objective import ModelAreaLedger
    cfg,state=future_fixture()
    ledger=ModelAreaLedger({})
    state._control_area_ledger=ledger
    state.urban_link_storage[SOURCE]=0.
    ramp.advance_gate(state,cfg,SOURCE,1200,9.)
    wait='transit:gate_wait:'+SOURCE;travel='transit:gate:'+SOURCE
    assert ledger.stocks[wait]=={'inside':0.,'outside':9.}
    ledger.residence([wait],1/3600)
    assert ledger.metrics.ttt_veh_h==0.
    state.urban_link_storage[SOURCE]=4.+sum(state.urban_movement_queue.values())
    ramp.advance_gate(state,cfg,SOURCE,1201,0.)
    assert ledger.stocks[wait]=={'inside':0.,'outside':5.}
    assert ledger.stocks[travel]=={'inside':4.,'outside':0.}
    ledger.residence([wait,travel],1/3600)
    assert ledger.metrics.ttt_veh_h==pytest.approx(4/3600)
    assert ledger.metrics.ttd_veh==0.


def test_entry_lane_count_is_independent_of_the_meter_command_service():
    cfg,state,tuning,raw=fixture()
    before=copy.deepcopy(cfg.network.movement_capacity_by_movement_veh_h)
    tuning['urban']['ramp']['gate_entry_capacity_per_lane_veh_h']=1800.
    ramp.initialize_gate_routes(state,cfg,tuning,raw)
    assert cfg.network.movement_capacity_by_movement_veh_h[W]==3600.
    assert cfg.network.movement_capacity_by_movement_veh_h[E]==1800.
    assert all(v==cfg.network.movement_capacity_by_movement_veh_h[m] for m,v in before.items() if m not in (E,W))
    assert not hasattr(cfg.network,'ramp_capacity_veh_h')  # No meter capacity mutation.


def test_entry_geometry_does_not_require_individual_vehicle_routes():
    cfg,state,tuning,raw=fixture()
    tuning['urban']['ramp']={'initial_gate_city_lock':True}
    raw.pop('vehicle_routes',None)
    reference=copy.deepcopy(state)
    ramp.initialize_gate_routes(reference,copy.deepcopy(cfg),tuning,raw)
    original_caps=copy.deepcopy(cfg.network.movement_capacity_by_movement_veh_h)
    tuning['urban']['ramp']['gate_entry_capacity_per_lane_veh_h']=1800.
    report=ramp.initialize_gate_routes(state,cfg,tuning,raw)
    assert state.__dict__==reference.__dict__
    assert report['gate_entry_capacity_veh_h']=={W:3600.,E:1800.}
    assert cfg.network.movement_capacity_by_movement_veh_h=={**original_caps,W:3600.,E:1800.}
    assert not hasattr(cfg.network,'physical_gate_travel')
    assert not hasattr(cfg.network,'ramp_capacity_veh_h')


@pytest.mark.parametrize('bad', ['receiver','lane'])
def test_city_gate_capacity_checks_geometry_before_mutating_stock(monkeypatch,bad):
    cfg,state,tuning,raw=fixture()
    tuning['urban']['ramp']={'initial_gate_city_lock':True,'gate_entry_capacity_per_lane_veh_h':1800.}
    raw.pop('vehicle_routes',None)
    if bad=='receiver':
        cfg.network.urban_movements[W]['ramp']='RM_C10490'
    else:
        import xml.etree.ElementTree as ET
        tree=ET.fromstring(ramp._read(cfg.network.physical_ramp_branches['network']))
        tree.find("./links/link[@no='10482']/fromLinkEndPt").set('lane','32 99')
        monkeypatch.setattr(ramp,'_read',lambda pin:ET.tostring(tree))
    before_state=copy.deepcopy(state.__dict__)
    before_cfg=copy.deepcopy(cfg.network.__dict__)
    with pytest.raises(ValueError,match='Gate entry'):
        ramp.initialize_gate_routes(state,cfg,tuning,raw)
    assert state.__dict__==before_state
    assert cfg.network.__dict__==before_cfg
