"""The two stages must share physical space without using the same hole twice."""
from types import SimpleNamespace as NS
from evaluation.controllers import route_choice_corridor as r


def test_ramp_release_then_lateral_access_then_connector_entry_share_space():
    spec=dict(storage='W',connector_queue_gate=True,local_queue_gate=True,lateral_access_rate_per_sec=2.,
        choice_position_m=7.,entry_lane_receiving=dict(ramp='R',physical_link='68',road_length_m=118.,
        ramp_lanes={'1':0,'2':1},road_capacity_veh={'1':4.,'2':4.,'3':4.,'4':4.},
        connector_entries={'A':dict(lanes=[3],position_m=2.,length_m=60.,capacity_per_lane_veh=10.)}))
    cfg=NS(simulation=NS(T_u_sec=1.),network=NS(known_legsplit_routes=spec,urban_link_storage_veh={'W':100.}))
    c2=dict(target='R',vehicles=4.,due=0,lane68=dict(shares={'2':1.},exit_step=0,order=(0,0)))
    c3=dict(target='R',vehicles=4.,due=0,lane68=dict(shares={'3':1.},exit_step=0,order=(0,1)))
    queued=dict(target='prechoice',vehicles=3.,due=1,speed_kph=36.,connector68=dict(link='A',shares={'3':1.},ready_step=1))
    state=NS(known_legsplit_route_state={'cohorts':[c2,c3,queued]},urban_storage_release_buffer={'W':{1:3.}},urban_link_storage={'W':89.})
    r.known_connector_advance(state,cfg,1);r._known_lateral_advance(state,cfg,1)
    assert queued['vehicles']==3. and c3['lane68']['shares']=={'3':1.}
    # Two accepted native ramp admissions open lane2; neither stage invents
    # an extra vehicle or takes space still occupied at its own snapshot.
    r._known_ramp_lane_debit(cfg,c2,2.);state.urban_link_storage['W']+=2.
    r.known_connector_advance(state,cfg,2);r._known_lateral_advance(state,cfg,2)
    assert queued['vehicles']==3. and c3['lane68']['shares']=={'3':.5,'2':.5}
    r.known_connector_advance(state,cfg,3)
    assert queued['vehicles']==1.
    assert r._known_lane_occupancy(state,spec,3)['3']==4.
    assert sum(c['vehicles'] for c in state.known_legsplit_route_state['cohorts'])==9.
