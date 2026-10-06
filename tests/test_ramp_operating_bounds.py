"""Storage protection constrains commands; it never invents discharge/space."""
import copy
import sys
from pathlib import Path
from types import SimpleNamespace as NS
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'vendor/NumSim-mine'))
from src.models.state import ControlAction
from evaluation.controllers import physical_ramp_branches as ramps, sdmpc, sdmpc_sequence as seq
from evaluation.controllers.joint_owner_neighbors import FixedMoveBox

class Buffer:
    head_position_m=300.;spacing_m=6.;lanes=1
    def __init__(self,ready=0.,travel=0.,post=0.):self.ready,self.travel,self.post=ready,travel,post
    def snapshot(self):return dict(head_ready_veh=self.ready,upstream_travelling_veh=self.travel,connector_veh=self.ready+self.travel+self.post)

def fixture(green=2,fill=0.,allow_zero=False,guard=True):
    ids=[f'R{i}' for i in range(8)]
    catalog={r:dict(sc_no=9101+i,sg_no=1,capacity_vph=900.,cycle_sec=10.,
             service_by_green_veh_h={str(g):180.*g for g in [0,*range(2,11)]}) for i,r in enumerate(ids)}
    spec=dict(ramps=catalog,legacy_groups=[],writer_mapping=[],cycle_sec=10.,minimum_green_sec=2.,
              max_green_change_sec=2.,allow_zero_green=allow_zero,
              storage_release_guard={'enabled':guard,'trigger_fraction':.9})
    cfg=NS(network=NS(physical_ramp_branches=spec,ramps=ids,signals=[],freeway_links=[],
        ramp_to_freeway={r:'E' if i<4 else 'W' for i,r in enumerate(ids)}),mpc=NS(horizon_steps=3),simulation=NS(T_c_sec=150.))
    a=ControlAction(ramp_metering={r:green*180. for r in ids},diagnostics={'rw_meter_green_'+r:float(green) for r in ids})
    state=NS(lane_ramp_runtime=NS(buffers={r:Buffer(fill*50) for r in ids}))
    box=FixedMoveBox(tuple(('diagnostics','rw_meter_green_'+r,float(green),2.,None) for r in ids),'test')
    policy=dict(control_blocks=3,fd_meter_green_sec=1.)
    return cfg,state,a,box,policy

def coordinates(cfg,state,a,box,policy):
    proof=ramps.configure_operating_bounds(state,cfg,a)
    return seq.SequenceCoordinates(cfg,a,box,policy),proof

def test_minimum_applies_to_all_blocks_candidates_and_writer_values():
    cfg,s,a,b,p=fixture()
    coord,proof=coordinates(cfg,s,a,b,p)
    assert all(min(x['allowed'])==2 for x in coord.axes)
    for name,c in sdmpc.meter_neighbors(coord,a):
        coord.validate(c)
        for block in seq.actions(c,3):
            rows=ramps.physical_commands(block,cfg)
            assert len(rows)==8 and all(2<=r['green_sec']<=10 and r['rate_vph']==r['green_sec']*90 for r in rows.values())
    with pytest.raises(ValueError,match='operating minimum'):
        ramps.candidate_from_greens(a,a,cfg,{r:0 for r in cfg.network.ramps})

@pytest.mark.parametrize('old,new',[(0,2),(2,4),(8,10),(9,10),(10,10)])
def test_full_ramp_recovers_within_actual_change_limit(old,new):
    cfg,s,a,b,p=fixture(old,1.)
    before=copy.deepcopy(vars(s.lane_ramp_runtime.buffers['R0']))
    coord,proof=coordinates(cfg,s,a,b,p)
    assert all(row['minimum_green_sec']==new for row in proof['ramps'].values())
    seed=coord.decode(np.clip(coord.encode(a),coord.lower,coord.upper),a)
    coord.validate(seed)
    assert all(c.diagnostics['rw_meter_green_R0']==new for c in seq.actions(seed,3))
    assert a.diagnostics['rw_meter_green_R0']==old and vars(s.lane_ramp_runtime.buffers['R0'])==before
    assert all(x['capacity_veh']==50 for x in proof['ramps']['R0']['lanes'])

def test_one_full_lane_is_not_hidden_by_an_empty_lane_or_posthead_stock():
    cfg,s,a,b,p=fixture()
    s.lane_ramp_runtime.buffers['R0']=NS(_lane_buffers=[Buffer(45),Buffer(0)])
    s.lane_ramp_runtime.buffers['R1']=Buffer(0,0,500)
    proof=ramps.configure_operating_bounds(s,cfg,a)
    assert proof['ramps']['R0']['triggered'] and proof['ramps']['R0']['minimum_green_sec']==4
    assert not proof['ramps']['R1']['triggered'] and proof['ramps']['R1']['minimum_green_sec']==2

def test_moving_prehead_stock_uses_space_but_is_not_called_stopped_queue():
    cfg,s,a,b,p=fixture();s.lane_ramp_runtime.buffers['R0']=Buffer(25,20)
    proof=ramps.configure_operating_bounds(s,cfg,a)
    assert proof['ramps']['R0']['lanes'][0]['prehead_veh']==45
    assert proof['ramps']['R0']['minimum_green_sec']==4

def test_protection_releases_when_occupancy_falls_and_old_policy_replays():
    cfg,s,a,b,p=fixture(4,.8)
    coord,proof=coordinates(cfg,s,a,b,p)
    assert all(x['minimum_green_sec']==2 for x in proof['ramps'].values())
    cfg,s,a,b,p=fixture(2,1.,allow_zero=True,guard=False)
    coord,proof=coordinates(cfg,s,a,b,p)
    assert 0 in coord.axes[0]['allowed']
    ramps.prepare_control(a,cfg)

def test_missing_geometry_fails_explicitly():
    cfg,s,a,b,p=fixture();del s.lane_ramp_runtime
    with pytest.raises(ValueError,match='actual physical ramp'):
        ramps.configure_operating_bounds(s,cfg,a)
