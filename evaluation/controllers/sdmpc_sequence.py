"""Three independent 150 s controls, with only block zero sent to actuators.

The first ControlAction carries future prediction-only controls in a JSON-safe
diagnostic field. Existing physical command fields always describe block zero.
No future command is executed by this module; every decision starts from the
new observation and the actually applied block-zero command.
"""
from __future__ import annotations

from contextlib import contextmanager
import copy
import hashlib
import pickle

import numpy as np

KEY = 'sdmpc_prediction_sequence'
FIELDS = ('N_P_star', 'N_UF_star', 'ramp_metering', 'vsl', 'green_times',
          'offsets', 'inflow_outflow_allocation', 'infeasibility', 'diagnostics')


def first_action(action):
    result = action.copy()
    result.diagnostics.pop(KEY, None)
    return result


def actions(action, count):
    from src.models.state import ControlAction
    first = first_action(action)
    plan = action.diagnostics.get(KEY)
    if plan is None:
        return [first.copy() for _ in range(count)]
    if (set(plan) != {'schema', 'future'} or plan['schema'] != 'sdmpc-sequence/v1'
            or len(plan['future']) != count-1):
        raise ValueError('SDMPC sequence length/schema differs from the prediction horizon')
    result = [first]
    for row in plan['future']:
        if set(row) != set(FIELDS) or KEY in row['diagnostics']:
            raise ValueError('Nested or incomplete SDMPC future control')
        control = ControlAction(**copy.deepcopy(row))
        # These are one horizon-wide NP cap and actual-merge NUF target.
        control.N_P_star, control.N_UF_star = first.N_P_star, first.N_UF_star
        result.append(control)
    return result


def pack(controls):
    if len(controls) != 3:
        raise ValueError('Three explicit SDMPC control blocks required')
    clean = [first_action(c) for c in controls]
    result = clean[0]
    # Keep payload keys separate from ControlAction's interned instance keys.
    # CPython rebuilds the latter on unpickle; sharing those string identities
    # changes pickle memo references at the native worker's hash boundary.
    result.diagnostics[KEY] = dict(schema='sdmpc-sequence/v1', future=[
        {name.encode('utf-8').decode('utf-8'):copy.deepcopy(getattr(c,name))
         for name in FIELDS} for c in clean[1:]])
    return result


@contextmanager
def prediction_scope(action, cfg, start_sec, horizon):
    """Select controls at existing interval boundaries inside the sole endpoint.

    Preserve installed coupling/ledger hooks and restore them even on failure.
    A complete endpoint must visit each block once; never silently truncate or
    extend a plan, or apply a future block during its predecessor's interval.
    """
    enabled = (getattr(cfg.network, 'sdmpc_options', None) or {}).get('control_blocks', 1)
    if KEY not in action.diagnostics:
        yield None
        return
    if enabled != 3 or horizon != enabled:
        raise ValueError('Future SDMPC controls require the explicit three-block option')
    from src.simulation import coupling
    from src.controllers.rollout_endpoint import ObjectiveSpec
    from evaluation.controllers.area_meter_finalization import for_endpoint
    controls = [for_endpoint(c, (), ObjectiveSpec(cfg, depth_override=horizon,
                                                 box_walk=False, score_mode='raw'))
                for c in actions(action, enabled)]
    original = coupling.run_coupled_interval
    visits = []
    dt = cfg.simulation.T_c_sec
    def run_interval(state, ignored, demand, actual_cfg):
        index = len(visits)
        if (actual_cfg is not cfg or index >= enabled
                or abs(state.time_sec-(start_sec+index*dt)) > 1e-8):
            raise ValueError('SDMPC block/clock mismatch')
        visits.append(index)
        return original(state, controls[index], demand, actual_cfg)
    coupling.run_coupled_interval = run_interval
    try:
        yield visits
        if visits != list(range(enabled)):
            raise ValueError('Incomplete three-block prediction')
    finally:
        coupling.run_coupled_interval = original


def reanchor(box, reference, multiplier=1):
    from evaluation.controllers.joint_owner_neighbors import FixedMoveBox
    entries = tuple((field,key,getattr(reference,field)[key],limit*multiplier,cycle)
                    for field,key,old,limit,cycle in box.entries)
    identity = hashlib.sha256(pickle.dumps(entries,protocol=5)).hexdigest()
    return FixedMoveBox(entries, identity)


class SequenceCoordinates:
    """Absolute block controls and linear consecutive-block move constraints."""
    def __init__(self, cfg, reference, move_box, options):
        from evaluation.controllers.sdmpc import Coordinates
        if options.get('control_blocks') != 3 or cfg.mpc.horizon_steps != 3:
            raise ValueError('Sequence coordinates require exactly three intervals')
        self.cfg, self.reference, self.move_box = cfg, first_action(reference), move_box
        self.blocks = [Coordinates(cfg,self.reference,reanchor(move_box,self.reference,k+1),options)
                       for k in range(3)]
        self.width = len(self.blocks[0].axes)
        self.axes, self.green_vectors = [], {}
        self.owners = self.blocks[0].owners
        for k,block in enumerate(self.blocks):
            for j,axis in enumerate(block.axes):
                self.axes.append(dict(axis,block=k))
                if j in block.green_vectors:
                    self.green_vectors[k*self.width+j] = block.green_vectors[j]
        self.lower = np.concatenate([b.lower for b in self.blocks])
        self.upper = np.concatenate([b.upper for b in self.blocks])
        rows, lows, highs = [], [], []
        n = len(self.axes)
        for k,block in enumerate(self.blocks):
            for row,lo,hi in zip(block.G,block.glo,block.ghi):
                full = np.zeros(n); full[k*self.width:(k+1)*self.width] = row
                rows.append(full); lows.append(lo); highs.append(hi)
        base = self.blocks[0]
        vectors = {}
        for j,axis in enumerate(base.axes):
            kind,key,owner,scale = (axis[x] for x in ('kind','key','owner','scale'))
            if kind == 'green':
                for phase,factor in base.green_vectors[j].items():
                    vectors.setdefault(('green_times',owner+'_'+phase),np.zeros(self.width))[j] = factor*scale
            else:
                field,key = (('offsets',key) if kind=='offset' else
                             ('diagnostics','rw_meter_green_'+key) if kind=='meter' else ('vsl',key))
                vectors.setdefault((field,key),np.zeros(self.width))[j] = scale
        for k in (1,2):
            for field,key,ref,limit,cycle in move_box.entries:
                vector = vectors.get((field,key))
                if vector is None:
                    continue  # Fixed addresses or VSL aliases; checked by native validation.
                row = np.zeros(n)
                row[k*self.width:(k+1)*self.width] = vector
                row[(k-1)*self.width:k*self.width] = -vector
                rows.append(row); lows.append(-limit); highs.append(limit)
        self.G = np.asarray(rows)
        self.glo,self.ghi = np.asarray(lows),np.asarray(highs)

    def encode(self, control):
        controls = actions(control,3)
        zs = [block.encode(c) for block,c in zip(self.blocks,controls)]
        # Lift circular offsets along the actual sequence, including wrap at 0.
        for j,axis in enumerate(self.blocks[0].axes):
            if axis['kind'] != 'offset': continue
            key,cycle = axis['key'],axis['scale']
            for k in (1,2):
                delta=(controls[k].offsets[key]-controls[k-1].offsets[key]+cycle/2)%cycle-cycle/2
                zs[k][j]=zs[k-1][j]+delta/cycle
        return np.concatenate(zs)

    def valid(self,z,tolerance=1e-8):
        return (len(z)==len(self.axes) and np.all(np.isfinite(z))
                and np.all(z>=self.lower-tolerance) and np.all(z<=self.upper+tolerance)
                and np.all(self.G@z>=self.glo-tolerance) and np.all(self.G@z<=self.ghi+tolerance))

    def decode(self,z,template):
        if not self.valid(z):
            raise ValueError('SDMPC sequence violates physical or inter-block constraints')
        templates=actions(template,3)
        controls=[]
        previous=self.reference
        for k,block in enumerate(self.blocks):
            control=block.decode(z[k*self.width:(k+1)*self.width],templates[k],previous=previous)
            reanchor(self.move_box,previous).validate(control)
            controls.append(control); previous=control
        result=pack(controls)
        if not self.valid(self.encode(result),tolerance=1e-8):
            raise ValueError('Quantized SDMPC sequence violates its constraints')
        return result

    def validate(self,control):
        from evaluation.controllers import signal_actuation_contract as signals, physical_ramp_branches as ramps
        previous=self.reference
        for c in actions(control,3):
            signals.validate_control(c,self.cfg)
            ramps.prepare_control(c.copy(),self.cfg)
            reanchor(self.move_box,previous).validate(c)
            previous=c
        if not self.valid(self.encode(control)):
            raise ValueError('Invalid SDMPC control sequence')
        return {'blocks':3,'interval_sec':self.cfg.simulation.T_c_sec,
                'applied_block':0,'all_actuator_and_step_constraints_checked':True}

    def stencil(self,z,j):
        raise ValueError('Three-block SDMPC requires direct tangent derivatives')
