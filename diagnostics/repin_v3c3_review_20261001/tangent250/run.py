"""Bounded tangent audit of the actual one-second freeway transition.

Projected density/speed tangent, fixed route/VSL fractions and external port
inputs. NOT the complete network Jacobian or an autonomous stability proof.
"""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import copy
import ctypes
import json
from pathlib import Path
import sys
import time
import numpy as np
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h
from diagnostics.repin_v3c3_review_20261001.deceleration248 import run as reuse

D=Path(__file__).resolve().parent
ROWS=[]
ACTIVE=None
COUNT=0
KERNEL_CALLS=0


def light_copy(state):
    out=copy.copy(state)
    # Other objects are read-only in this pinned single freeway substep.
    for key in ('freeway_density','freeway_speed','freeway_flow','freeway_effective_lanes',
                'mainline_origin_queue','offramp_route_inventory_state','_component_vsl_exposure'):
        if hasattr(state,key):setattr(out,key,copy.deepcopy(getattr(state,key)))
    out._control_area_ledger=None
    return out


def vector(state):
    return np.array(list(state.freeway_density['FW_E'])+list(state.freeway_speed['FW_E']),float)


def project(state,x):
    old=state.freeway_density['FW_E'];assert len(old)==31 and min(old)>0
    assert min(x[:31])>0
    for i,(a,b) in enumerate(zip(old,x[:31])):
        scale=b/a
        inv=state.offramp_route_inventory_state
        assert 'lane_cells' not in inv,'This audit is only for the aggregate production kernel'
        inv['cells']['FW_E'][i]={k:v*scale for k,v in inv['cells']['FW_E'][i].items()}
        exposure=state._component_vsl_exposure['FW_E']
        exposure.cohorts[i]={k:v*scale for k,v in exposure.cohorts[i].items()}
    state.freeway_density['FW_E']=x[:31].tolist()
    state.freeway_speed['FW_E']=x[31:].tolist()


def audit_step(old,state,control,demand,cfg,args,kw,time_sec):
    global KERNEL_CALLS
    scales=np.array([30.]*31+[100.]*31)
    x=vector(state);origin=light_copy(state);base_inventory=copy.deepcopy(state.offramp_route_inventory_state)
    def transition(z):
        global KERNEL_CALLS
        trial=light_copy(origin);project(trial,z)
        _,diag=old(trial,control,demand,cfg,*args,**kw)
        assert diag['density_projection_count']==0
        KERNEL_CALLS+=1
        assert KERNEL_CALLS<=1500
        return vector(trial),diag
    y,diag=transition(x)
    matrices=[];max_one_sided=[]
    for epsilon in (1e-5,5e-6):
        plus=[];minus=[]
        for axis in range(62):
            dx=np.zeros(62);dx[axis]=epsilon*scales[axis]
            yp,_=transition(x+dx);ym,_=transition(x-dx)
            plus.append((yp-y)/scales/epsilon)
            minus.append((y-ym)/scales/epsilon)
        jp=np.column_stack(plus);jm=np.column_stack(minus)
        matrices.append((jp+jm)/2)
        max_one_sided.append(float(np.max(np.abs(jp-jm))))
    J=matrices[-1];eigen=np.linalg.eigvals(J)
    ranked=sorted(eigen,key=abs,reverse=True)
    # The finite-difference error and one-sided discrepancy flag non-smooth
    # active branches; they must be inspected before interpreting eigenvalues.
    lengths=np.array(cfg.network.freeway_segment_length_profile_km['FW_E'])
    row=dict(arm=ACTIVE,time_sec=time_sec,conditional_projected_tangent=True,
        units='rho veh/km/lane, speed km/h; singular values use scales30 and100',
        frozen='Actual accepted ramp rates, off-ramp receiving capacities, urban/off stocks, commands, current route/VSL fractions; their future dynamics are excluded from repeated tangent interpretation.',
        state=x.tolist(),next_state=y.tolist(),scales=scales.tolist(),jacobian=J.tolist(),
        coarse_jacobian=matrices[0].tolist(),
        max_epsilon_difference=float(np.max(np.abs(matrices[0]-matrices[1]))),
        max_one_sided_difference=max_one_sided,
        eigenvalues=[[float(v.real),float(v.imag)] for v in ranked],
        spectral_radius=float(max(abs(eigen))),
        singular_max=float(np.linalg.svd(J,compute_uv=False)[0]),
        euler_inward_but_unit_disk_outside=[ [float(v.real),float(v.imag)] for v in eigen if v.real<1.-1e-6 and abs(v)>1.+1e-6],
        max_advective_courant=float(max(x[31:]*cfg.simulation.T_f_h/lengths)),
        diagnostics=diag,kernel_evaluations=249)
    assert state.offramp_route_inventory_state==base_inventory
    return row


def callback(captured,candidates,coord,output):
    global ACTIVE,COUNT
    from evaluation.controllers import area_freeway_accounting as afa
    assert set(candidates)=={'release_actual','release_vsl90_actual'}
    reuse.CAPTURES['s67']=(captured,candidates,coord)
    old=afa._freeway_substep_events
    def wrapped(state,control,demand,cfg,*a,**kw):
        global COUNT
        selected=tuple(cfg.network.freeway_links)==('FW_E',)
        row=None
        if selected:
            index=COUNT;COUNT+=1
            if index in (149,299,449):
                row=audit_step(old,state,control,demand,cfg,a,kw,2700+index)
        result=old(state,control,demand,cfg,*a,**kw)
        if row is not None:
            row['canonical_replay_max_difference']=float(max(abs(vector(state)-row['next_state'])))
            assert row['canonical_replay_max_difference']<1e-10
            ROWS.append(row);h.save(D/'tangents.json',ROWS)
            print(json.dumps({k:row[k] for k in ('arm','time_sec','spectral_radius','max_epsilon_difference','max_advective_courant')}),flush=True)
        return result
    afa._freeway_substep_events=wrapped
    try:
        for arm in ('release_actual','release_vsl90_actual'):
            ACTIVE=arm;COUNT=0
            base=h.read(h.R/f'deceleration248/verified/s67_base_{arm}.json')
            assert reuse.commands(candidates[arm],captured['cfg'])==base['commands']
            item=reuse.forecast('s67',arm,1.,'unchanged')
            assert COUNT==450 and abs(item['ttt']-base['ttt'])<1e-10
            assert item['snapshots']==base['snapshots']
    finally:afa._freeway_substep_events=old


def main():
    assert not (D/'protocol.json').exists(),'Preserve previous output; no automatic retry'
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetCurrentProcess.restype=ctypes.c_void_p
    k.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32];assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
    old=h.read(h.R/'deceleration248/verified/protocol.json')
    pins={**old['protected_sha256'],old['STOP']['path']:old['STOP']['sha256']}
    assert all(h.sha(p)==v for p,v in pins.items())
    h.save(D/'protocol.json',dict(scope=__doc__,previous='249PROGRESS conditional pressure failure;231only one smoothspeed pulse. Prior center_distance/Bounded/ARZ failures checked; no repeated candidate.',
        budgets=dict(full450=2,kernel_1s=1494,fit=0,native=0,FZP=0),
        states='Current233/235 seed67release110/90;149/299/449th second of450 prediction; no future native inputs.',
        perturbation='62 rho/v axes, central differences normalized1e-5 and5e-6. Scale existing route/VSL stock cohorts proportionally; fractions fixed. Disable ledger only in disposable one-second copies; complete original forecast ledger remains enabled.',
        interpretation='This projected, frozen-port tangent is not a complete62-state Markov system. Eigenvalues cannot establish autonomous full-network stability. Re(mu)<1,abs(mu)>1 flags a local Euler numerical-risk candidate, not a proven defect. No gain fitting or automatic adoption.',
        pins=pins,source_sha256=h.sha(__file__),future_observation_inputs=False))
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
    from evaluation.controllers import obs150_contract as oc
    original=probe.probe_levers;writer=oc.write_derived
    def existing(raw,derived):
        obs=raw[oc.RAW_STATE_KEY];path=oc.resolve(obs,oc.derived_path(obs['sim_sec']))
        assert path.read_bytes()==oc.derived_bytes(derived);return path
    def intercepted(*a,**kw):return original(*a,prepared_probe_callback=callback,**kw)
    reuse.HERE=D
    args=h.read(h.R/'deceleration248/verified/capture_s67.json')['argv']
    args=[a for a in args if not a.startswith(('--probe-label=','--output-suffix='))]
    args+=['--probe-label=tangent250','--output-suffix=tangent250']
    started=time.perf_counter()
    try:
        probe.probe_levers=intercepted;oc.write_derived=existing;sys.argv=args;probe.main()
        assert len(ROWS)==6 and KERNEL_CALLS==1494 and len(reuse.RESULTS)==2
        assert all(h.sha(p)==v for p,v in pins.items())
        h.save(D/'completion.json',dict(status='COMPLETE_PENDING_ASSESSMENT',maps=6,kernel_calls=KERNEL_CALLS,
            full_forecasts=2,wall_seconds=time.perf_counter()-started,fit=0,production_adopted=False,
            frozen_native_untouched=True,future_observation_inputs=False))
    except BaseException as exc:
        h.save(D/'failure.json',dict(error=repr(exc),maps=len(ROWS),kernel_calls=KERNEL_CALLS,preserved=True));raise
    finally:probe.probe_levers=original;oc.write_derived=writer


if __name__=='__main__':main()
