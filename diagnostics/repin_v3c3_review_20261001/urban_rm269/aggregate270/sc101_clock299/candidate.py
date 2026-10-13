"""Offline-only SC101 side-entry travel, retaining accepted physical service.

No stock, routing, service, or existing arrival reservation is rewritten.
Only future accepted1099/1100 north-branch transfers receive a source-specific
remaining distance. Shared receiving and branch/SC15 service remain upstream.
"""
from contextlib import contextmanager
import math
from pathlib import Path

from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.combined298.candidate import (
    hook as service_hook, validate_turns, west, east)
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc101_clock299.source_geometry import geometry

MODE='source_path_current_physical_speed'
TARGET='SC1_to_SC101'
ROOT=Path(__file__).resolve().parents[5]


def delay_steps(state,cfg,geom,decision):
    from src.models.urban_queue_model import OBSERVED_SPEED_DELAY_CAP_RATIO
    speed=state.urban_link_speed_kph[TARGET]/geom['lane_factor']
    nominal=cfg.network.urban_avg_speed_km_h
    dt=cfg.simulation.T_u_sec
    distance=geom['sources'][decision]['distance_m']
    if not all(math.isfinite(x) for x in (speed,nominal,dt,distance)) or speed<0 or min(nominal,dt,distance)<=0:
        raise ValueError('Invalid side-entry travel operands')
    speed=max(speed,nominal/OBSERVED_SPEED_DELAY_CAP_RATIO)
    return max(1,math.ceil(distance/speed*3.6/dt))


@contextmanager
def travel_hook(option):
    if option is None:
        yield dict(geometry=None,receipts=[])
        return
    if option!=MODE:
        raise ValueError('Unknown side-entry diagnostic')
    from evaluation.controllers.aggregate_route_corridors import Routes
    from src.models import urban_queue_model as uqm
    original_advance,original_delay=Routes.advance_one,uqm._link_delay_steps
    active=None
    record=dict(geometry=None,receipts=[])
    def advance(self,state,control,cfg,step,spec):
        nonlocal active
        if active is not None:
            raise RuntimeError('Nested aggregate side-entry processing')
        active=(spec,step)
        try:
            return original_advance(self,state,control,cfg,step,spec)
        finally:
            active=None
    def delay(state,cfg,target):
        if active is None or target!=TARGET or active[0]['decision'] not in ('1099','1100'):
            return original_delay(state,cfg,target)
        spec,step=active
        if record['geometry'] is None:
            record['geometry']=geometry(ROOT,cfg)
        geom=record['geometry']
        proof=geom['sources'][spec['decision']]
        branch=spec['branches']['1']
        if branch['destination']!=target or branch['connector']!=proof['connector'] or spec['prefix_storage']!=proof['source']:
            raise ValueError('SC101 source identity changed')
        new=delay_steps(state,cfg,geom,spec['decision'])
        old=original_delay(state,cfg,target)
        record['receipts'].append(dict(source=spec['prefix_storage'],decision=spec['decision'],
            step=step,sec=step*cfg.simulation.T_u_sec,old_delay_sec=old*cfg.simulation.T_u_sec,
            delay_sec=new*cfg.simulation.T_u_sec,remaining_available_space=state.urban_link_storage[target]))
        return new
    Routes.advance_one=advance
    uqm._link_delay_steps=delay
    try:
        yield record
    finally:
        Routes.advance_one=original_advance
        uqm._link_delay_steps=original_delay


@contextmanager
def hook(option):
    with service_hook(),travel_hook(option) as record:
        yield record
