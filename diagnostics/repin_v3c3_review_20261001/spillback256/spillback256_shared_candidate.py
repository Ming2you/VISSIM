"""Temporary causal diagnostic, before production adoption; no stock owner."""
import xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(r'C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.worktrees/sd31-upstream-20260926')
def configure(state,cfg):
    spec=cfg.network.direct_exit_legsplit
    tree=ET.fromstring((ROOT/spec['network']['path']).read_bytes())
    links={r.get('no'):r for r in tree.findall('./links/link')}
    entry=links['10483'].find('toLinkEndPt');branch=links['10480'].find('fromLinkEndPt')
    assert entry.get('lane')==branch.get('lane')=='124 1'
    distance=float(branch.get('pos'))-float(entry.get('pos'));assert distance>0
    buffer=state.lane_ramp_runtime.buffers['RM_C10480'];assert buffer.lanes==1
    cfg.network.spill256=dict(distance_m=distance,head_m=buffer.head_position_m,spacing_m=buffer.spacing_m,
        limit=(distance+buffer.head_position_m)/buffer.spacing_m)
    return cfg.network.spill256

def room(state,cfg,step):
    spec=cfg.network.spill256
    buffer=state.lane_ramp_runtime.buffers['RM_C10480'];s=buffer.snapshot()
    # Exclude cars already past the signal. Pending admissions are not yet in
    # the physical buffer but already debited from the urban owner.
    queued=s['head_ready_veh']+s['upstream_travelling_veh']
    pending=max(0.,state.ramp_queue['RM_C10480']-s['connector_veh'])
    ready=sum(c['vehicles'] for c in state.direct_exit_route_state['cohorts']
        if c['target']=='RM_C10480' and c['due']<=step)
    return max(0.,spec['limit']-queued-pending-ready)

def install():
    from evaluation.controllers.lane_offramp_runtime import LaneOfframpRuntime
    from src.models import urban_queue_model as uqm
    old=LaneOfframpRuntime.drain;stats=dict(calls=0,constrained=0,zero=0)
    def drain(self,state,control,cfg,step,routing):
        original=uqm._effective_available_space
        def space(s,c,target):
            result=original(s,c,target)
            if target=='SC1001_W_out':
                limit=room(s,c,step);stats['calls']+=1
                stats['constrained']+=limit<result;stats['zero']+=limit==0
                return min(result,limit)
            return result
        uqm._effective_available_space=space
        try:return old(self,state,control,cfg,step,routing)
        finally:uqm._effective_available_space=original
    LaneOfframpRuntime.drain=drain
    return stats
