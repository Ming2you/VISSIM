"""Connector queues must enter finite road68 space before route-choice travel."""
from types import SimpleNamespace as NS
import copy
import pytest
from evaluation.controllers import route_choice_corridor as routes


def fixture():
    entries={'A':dict(lanes=[1],position_m=2.,length_m=60.,capacity_per_lane_veh=10.),
             'B':dict(lanes=[1],position_m=2.,length_m=30.,capacity_per_lane_veh=5.)}
    local=dict(ramp='R',physical_link='68',road_length_m=118.,incoming={'a':[1],'alias':[1],'b':[1]},
               ramp_lanes={},capacity_veh={},road_capacity_veh={'1':4.},connector_entries=entries)
    paths={'free':[dict(link='68',start=7.,stop=118.),dict(link='121',start=0.,stop=200.)],
           'R':[dict(link='68',start=7.,stop=118.)]}
    spec=dict(storage='W',entry_lane_receiving=local,connector_queue_gate=True,local_queue_gate=True,
              incoming_movements={'a':'A','alias':'A','b':'B'},choice_position_m=7.,
              physical_travel={'destinations':paths},future_choice_weights={'R':1.})
    cfg=NS(simulation=NS(T_u_sec=1.),network=NS(known_legsplit_routes=spec,
        urban_link_storage_veh={'W':100.},boundary_out_ramp_split={'W':{'free':0.,'ramps':{'R':1.}}}))
    blocked=dict(target='R',vehicles=4.,due=0,lane68=dict(shares={'1':1.},exit_step=0,order=(0,0)))
    incoming=dict(target='prechoice',vehicles=3.,due=1,speed_kph=36.,
                  connector68=dict(link='A',shares={'1':1.},ready_step=1))
    state=NS(known_legsplit_route_state=dict(cohorts=[blocked,incoming],plan=None),
             urban_storage_release_buffer={'W':{1:3.}},urban_link_storage={'W':93.})
    return state,cfg


def test_initial_connector_uses_its_own_tag_not_road_reservation():
    s,c=fixture()
    tag=routes._known_lane68_tag(c,'A',1,40.,36.,0)
    assert 'lane68' not in tag
    assert tag['connector68']==dict(link='A',shares={'1':1.},ready_step=2)


def test_blocked_connector_cannot_draw_a_destination_after_eta():
    s,c=fixture()
    routes.known_connector_advance(s,c,1)
    assert s.known_legsplit_route_state['cohorts'][1]['target']=='prechoice'
    assert s.known_legsplit_route_state['cohorts'][1]['due']==2
    requests=routes.known_legsplit_requests(s,c,'W',4.,4.,1)
    assert requests=={'R':4.}
    assert s.urban_storage_release_buffer=={'W':{2:3.}}
    assert s.urban_link_storage['W']==93.


def test_released_road_room_allows_actual_entry_before_choice():
    s,c=fixture();s.known_legsplit_route_state['cohorts'][0]['vehicles']=2.;s.urban_link_storage['W']=95.
    routes.known_connector_advance(s,c,1)
    rows=s.known_legsplit_route_state['cohorts']
    assert sum(x['vehicles'] for x in rows)==5.
    assert sum(x['vehicles'] for x in rows if 'connector68' in x)==1.
    road=[x for x in rows if x['target']=='prechoice' and 'lane68' in x]
    assert len(road)==1 and road[0]['vehicles']==2. and road[0]['due']==2
    assert s.urban_storage_release_buffer=={'W':{2:3.}}


def test_shared_road_room_does_not_get_granted_to_each_connector():
    s,c=fixture();s.known_legsplit_route_state['cohorts'][0]['vehicles']=2.;s.urban_link_storage['W']=92.
    b=copy.deepcopy(s.known_legsplit_route_state['cohorts'][1]);b['connector68']['link']='B'
    s.known_legsplit_route_state['cohorts'].append(b)
    routes.known_connector_advance(s,c,1)
    rows=s.known_legsplit_route_state['cohorts']
    assert sum(x['vehicles'] for x in rows if 'connector68' not in x)==4.
    assert sum(x['vehicles'] for x in rows)==8.


def test_upstream_admission_uses_connector_room_even_when_road_full():
    s,c=fixture()
    assert routes.known_entry_lane_limits(s,c,{'a':6.,'alias':6.,'b':6.,'other':4.},1)=={
        'a':3.5,'alias':3.5,'b':5.,'other':4.}
    assert s.known_legsplit_route_state['entry_lane_shares']['a']=={'1':1.}


def test_disabled_stage_is_exact_noop():
    s,c=fixture();c.network.known_legsplit_routes.pop('connector_queue_gate');before=copy.deepcopy(s)
    routes.known_connector_advance(s,c,1)
    assert vars(s)==vars(before)


def test_admission_gradient_moves_aliases_without_changing_owned_stock(monkeypatch):
    from evaluation.controllers.sdmpc_dual import Dual,Trace,primal,derivative,MathProxy
    monkeypatch.setattr(routes,'math',MathProxy())
    s,c=fixture();n=Dual(2.,{0:1.},Trace([.01]))
    s.known_legsplit_route_state['cohorts'][0]['vehicles']=n;s.urban_link_storage['W']=97.-n
    routes.known_connector_advance(s,c,1)
    rows=s.known_legsplit_route_state['cohorts']
    remain=sum(x['vehicles'] for x in rows if 'connector68' in x)
    assert primal(remain)==1. and derivative(remain)[0]==1.
    admitted=sum(x['vehicles'] for x in rows if x['target']=='prechoice' and 'lane68' in x)
    assert primal(admitted)==2. and derivative(admitted)[0]==-1.


def test_initial_overfull_lane_never_deletes_stock():
    s,c=fixture();s.known_legsplit_route_state['cohorts'][0]['vehicles']=8.;s.urban_link_storage['W']=89.
    routes.known_connector_advance(s,c,1)
    assert sum(x['vehicles'] for x in s.known_legsplit_route_state['cohorts'])==11.
    assert s.known_legsplit_route_state['cohorts'][1]['vehicles']==3.


def test_connector_fifo_preserves_known_target_without_redrawing():
    s,c=fixture();s.known_legsplit_route_state['cohorts'][0]['vehicles']=2.;s.urban_link_storage['W']=94.
    c.network.known_legsplit_routes['physical_travel']['destinations']['free'][0]['start']=0.
    earlier=s.known_legsplit_route_state['cohorts'][1];earlier['vehicles']=1.;earlier['target']='free'
    later=copy.deepcopy(earlier);later['target']='prechoice';later['vehicles']=3.;later['connector68']['ready_step']=2
    s.known_legsplit_route_state['cohorts'].append(later)
    routes.known_connector_advance(s,c,2)
    road=[x for x in s.known_legsplit_route_state['cohorts'] if 'connector68' not in x]
    assert sum(x['vehicles'] for x in road if x['target']=='free')==1.
    assert sum(x['vehicles'] for x in road if x['target']=='prechoice')==1.


def test_empty_road_moves_connector_to_road_then_choices_once():
    s,c=fixture();s.known_legsplit_route_state['cohorts'][0]['vehicles']=0.;s.urban_link_storage['W']=97.
    routes.known_connector_advance(s,c,1)
    assert all(x['target']=='prechoice' for x in s.known_legsplit_route_state['cohorts'])
    routes.known_connector_advance(s,c,2)
    # The fixture avoids runtime distance accounting; physical choice tests
    # elsewhere exercise that integration. Entry itself must not draw a prior.
    assert sum(x['vehicles'] for x in s.known_legsplit_route_state['cohorts'])==3.
    assert all('lane68' in x for x in s.known_legsplit_route_state['cohorts'])


def test_fully_transferred_fractional_lanes_do_not_clone_a_residual():
    s,c=fixture();rows=s.known_legsplit_route_state['cohorts']
    rows[0]['vehicles']=0.;rows[1]['vehicles']=.1
    rows[1]['connector68']['shares']={'1':.3,'2':.7}
    c.network.known_legsplit_routes['entry_lane_receiving']['road_capacity_veh']['2']=4.
    s.urban_link_storage['W']=99.9
    routes.known_connector_advance(s,c,1)
    assert not any('connector68' in x for x in s.known_legsplit_route_state['cohorts'])
    assert sum(x['vehicles'] for x in s.known_legsplit_route_state['cohorts'])==pytest.approx(.1)
