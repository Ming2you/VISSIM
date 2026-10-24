"""Offline source21 pre-head geometry; queues and receiving remain explicit."""
from contextlib import contextmanager
import copy
import math

TARGET='in_SC108_W'


def geometry(cfg):
    from evaluation.controllers.native_internal_input import _signal_authority
    _,proof=_signal_authority(cfg,'1083')
    assert proof['physical_source']=='21' and proof['pre_head_storage']==TARGET
    assert proof['post_head_storage']=='SC108_to_SC109' and proof['kept_movement']=='SC108_W_to_E_SC109'
    positions=proof['head_position_by_lane_m']
    assert set(positions)=={'1','2'}
    assert cfg.network.native_internal_inputs['inputs']['1083']['approach_path']==['21']
    spacing=cfg.network.urban_avg_vehicle_length_m
    assert spacing>0
    return dict(head_positions_m=positions,distance_m=max(positions.values()),
        capacity_veh=sum(positions.values())/spacing,spacing_m=spacing,
        source_lanes=len(positions),scope='Source start to the two selected heads only; past-head21/10112 remains downstream.')


def install(cfg,state):
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    geom=geometry(cfg)
    before=cfg.network.urban_link_storage_veh[TARGET]
    occupied=before-state.urban_link_storage[TARGET]
    q=sum(state.urban_movement_queue.get(k,0.) for k,v in cfg.network.urban_movements.items() if v['origin']==TARGET)
    if min(occupied,q)<-1e-8 or occupied+q>geom['capacity_veh']+1e-8:
        raise ValueError('Observed stock exceeds proposed pre-head physical capacity; retain evidence, do not clip vehicles')
    initial_inventory=model_inventory(state,cfg)
    buffers=(copy.deepcopy(state.urban_arrival_buffer),copy.deepcopy(state.urban_storage_release_buffer))
    cfg.network.urban_link_storage_veh=copy.copy(cfg.network.urban_link_storage_veh)
    cfg.network.urban_link_storage_veh[TARGET]=geom['capacity_veh']
    state.urban_link_storage[TARGET]=geom['capacity_veh']-occupied
    after_inventory=model_inventory(state,cfg)
    assert initial_inventory.keys()==after_inventory.keys()
    assert max(abs(initial_inventory[k]-after_inventory[k]) for k in initial_inventory)<1e-8
    get_ledger(state).assert_stocks(after_inventory)
    assert buffers==(state.urban_arrival_buffer,state.urban_storage_release_buffer)
    return dict(geometry=geom,old_capacity_veh=before,new_capacity_veh=geom['capacity_veh'],
                occupied_veh=occupied,queue_veh=q,initial_stock_and_due_times_preserved=True)


def delay_steps(state,cfg,geom):
    from src.models.urban_queue_model import OBSERVED_SPEED_DELAY_CAP_RATIO
    nominal=cfg.network.urban_avg_speed_km_h
    speed=max(float(state.urban_link_speed_kph.get(TARGET,nominal)),nominal/OBSERVED_SPEED_DELAY_CAP_RATIO)
    dt=cfg.simulation.T_u_sec
    if not all(math.isfinite(x) and x>0 for x in (speed,dt,geom['distance_m'])):
        raise ValueError('Invalid physical pre-head clock')
    return max(1,math.ceil(geom['distance_m']/(speed/3.6)/dt))


@contextmanager
def clock(cfg):
    from src.models import urban_queue_model as uqm
    geom=geometry(cfg);original=uqm._link_delay_steps;receipts=[]
    def corrected(state,current_cfg,target):
        if current_cfg is not cfg or target!=TARGET:
            return original(state,current_cfg,target)
        answer=delay_steps(state,cfg,geom)
        receipts.append(dict(sec=state.time_sec,step_sec=cfg.simulation.T_u_sec,
            geometry_distance_m=geom['distance_m'],delay_sec=answer*cfg.simulation.T_u_sec,
            generic_after_capacity_fix_sec=original(state,cfg,target)*cfg.simulation.T_u_sec))
        return answer
    uqm._link_delay_steps=corrected
    try:yield receipts
    finally:uqm._link_delay_steps=original
