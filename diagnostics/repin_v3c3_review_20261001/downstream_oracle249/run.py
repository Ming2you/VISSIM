"""Four conditional forecasts, CURRENT coupled aggregate plant, no calibration.

Future native150s cell22 density is used only in cell21 speed pressure/regime.
This is explicitly an oracle diagnostic, never an autonomous gain candidate.
"""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import copy
from contextlib import contextmanager
import ctypes
from pathlib import Path
import sys
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h
from diagnostics.repin_v3c3_review_20261001.deceleration248 import run as reuse

D=Path(__file__).resolve().parent
ACTIVE=None
AUDIT=[]


def save(name,value):
    if isinstance(value,dict):
        value={**value,'future_observation_inputs':True,
            'scope':'CONDITIONAL cell21 speed equation uses future interpolated actual mean density22; no autonomous qualification.'}
    h.save(D/name,value)


def interpolated(points,time):
    assert points[0][0]<=time<=points[-1][0]
    for (a,x),(b,y) in zip(points,points[1:]):
        if a<=time<=b:return x+(y-x)*(time-a)/(b-a)
    raise AssertionError(time)


@contextmanager
def pressure_scope(ratio,stats):
    assert ratio==1. and ACTIVE is not None
    from evaluation.controllers import area_freeway_accounting as afa
    mn=afa._mn;old=mn.metanet_speed_update_kmh
    ctx=old.__globals__['_FW_SEG_CTX'];calls=[]
    def updated(*args,**kwargs):
        assert not kwargs
        marker=ctx.get('state_response',{}).get('_downstream_oracle249') if ctx['armed'] else None
        if marker is not None:
            assert marker==21 and len(args)==11
            time=2700.+len(calls);assert time<3150
            replaced=interpolated(ACTIVE['points'],time)
            values=list(args);values[3]=replaced
            calls.append(dict(time=time,model_downstream=args[3],actual_interpolated_downstream=replaced,
                local_density=args[2],speed=args[0],new_vs_old_regime=(replaced>=args[2],args[3]>=args[2])))
            return old(*values)
        return old(*args)
    with original_relaxation(ratio,stats):
        mn.metanet_speed_update_kmh=updated
        try:yield
        finally:
            assert mn.metanet_speed_update_kmh is updated
            mn.metanet_speed_update_kmh=old
            AUDIT.append(dict(tag=ACTIVE['tag'],arm=ACTIVE['arm'],points=ACTIVE['points'],calls=calls))
    assert len(calls)==450


original_relaxation=reuse.negative_relaxation


def run_prepared(captured,candidates,coord,output,tag):
    global ACTIVE
    from evaluation.controllers.freeway_fd import cell_state_response
    expected={'release_actual','release_vsl90_actual'};assert set(candidates)==expected
    state=copy.deepcopy(captured['state']);assert state.time_sec==2700
    captured={**captured,'state':state}
    net=state.lane_freeway_runtime.configs['FW_E'].network
    assert net.freeway_segment_lanes['FW_E'][22]==3
    length=net.freeway_segment_params['FW_E'][22]['segment_length_km']
    marker=copy.deepcopy(cell_state_response(net,'FW_E',21));marker['_downstream_oracle249']=21
    net.freeway_state_response['FW_E']['cell_overrides']['21']=marker
    reuse.CAPTURES[tag]=(captured,candidates,coord)
    file=h.R/('s67_full_observation/snapshot_errors76.json' if tag=='s67' else 'replication_s73_95/snapshot_errors95.json')
    labels=h.read(file)
    save('capture_'+tag+'.json',dict(arms=list(candidates),model_start=2700,output=str(output),
        native_labels=str(file),native_labels_sha256=h.sha(file),cell22_length_km=length))
    for arm in ('release_actual','release_vsl90_actual'):
        native=arm.removesuffix('_actual')
        rows=sorted((r for r in labels if r['arm']==native and r['cell']==22),key=lambda r:r['time_sec'])
        assert [r['time_sec'] for r in rows]==[2700,2850,3000,3150]
        points=[(r['time_sec'],r['actual_stock']/(3*length)) for r in rows]
        assert abs(points[0][1]-state.freeway_density['FW_E'][22])<1e-7
        base=h.read(h.R/f'deceleration248/verified/{tag}_base_{arm}.json')
        assert reuse.commands(candidates[arm],captured['cfg'])==base['commands']
        assert state.freeway_speed['FW_E']==base['snapshots'][0]['speed']['FW_E']
        ACTIVE=dict(tag=tag,arm=arm,points=points)
        row=reuse.forecast(tag,arm,1.,'conditional')
        assert row['snapshots'][0]==base['snapshots'][0]
        save('audit.json',dict(records=AUDIT))
    ACTIVE=None


def main():
    assert not (D/'protocol.json').exists()
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetCurrentProcess.restype=ctypes.c_void_p
    k.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32];assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
    old=h.read(h.R/'deceleration248/verified/protocol.json')
    assert all(h.sha(p)==v for p,v in old['protected_sha256'].items())
    paths=[Path(__file__),Path(reuse.__file__),h.R/'deceleration248/verified/tuning.json',
        h.R/'s67_full_observation/snapshot_errors76.json',h.R/'replication_s73_95/snapshot_errors95.json']
    for tag in ('s67','s73'):
        for arm in ('release_actual','release_vsl90_actual'):
            paths.append(h.R/f'deceleration248/verified/{tag}_base_{arm}.json')
    pins={str(p):h.sha(p) for p in paths}
    save('protocol.json',dict(previous_turn='PROGRESS248: boundedcurrent negative relaxation fit failed, noadoption.',
        prior='ClaudeREVIEW_CHECK K4/K5, U7 notes;81/85/87/88/89/90/91/92/93/94/100/101/133/194/195/196 reread. Original lane_dn67 uses older2670.1 local lane scope; notthis2700 fullOmegaaggregate test.',
        intervention='Only cell21 downstreamrho in canonical velocity function replaced by actualcell22N/(3L), piecewiseLINEAR between recorded2700/2850/3000/3150 states. Also lets existing anticipation regime choose using thatinput. Predicted stocks/flows/receiving notoverwritten.',
        budget=dict(forecasts=4,fit=0,native=0,FZP=0),
        cases='67 and73 release110/90; exact current248 baseline commands/initial states. Baselines reused.',
        decision='If both Omega and terminal response errors shrink20percent, future22pressure merits further causal state-transition diagnosis; NOT a plant adoption gate. Failure cannot rule out5s dynamics, lane-mean mismatch, or othercells.',
        limitations='Future150s interpolation suppresses fastwaves; evaluation diagnostic only. Never importdifferent2670.1 caches as matching2700trial. FullDeltaTTT includesentryeffects andisnot calibrated here.',
        protected_sha256=old['protected_sha256'],STOP=old['STOP'],pins=pins))
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
    from evaluation.controllers import obs150_contract as oc
    original_probe=probe.probe_levers;original_writer=oc.write_derived
    def existing(raw,derived):
        obs=raw[oc.RAW_STATE_KEY];path=oc.resolve(obs,oc.derived_path(obs['sim_sec']))
        assert path.read_bytes()==oc.derived_bytes(derived);return path
    jobs={tag:h.read(h.R/f'deceleration248/verified/capture_{tag}.json')['argv'] for tag in ('s67','s73')}
    reuse.HERE=D;reuse.save=save;reuse.negative_relaxation=pressure_scope
    try:
        oc.write_derived=existing
        for tag,args in jobs.items():
            args=[a for a in args if not a.startswith(('--probe-label=','--output-suffix='))]
            args.extend(['--probe-label=o249_'+tag,'--output-suffix=o249_'+tag])
            def callback(*a,tag=tag):return run_prepared(*a,tag=tag)
            def intercepted(*a,**kw):return original_probe(*a,prepared_probe_callback=callback,**kw)
            probe.probe_levers=intercepted;sys.argv=args;probe.main()
        assert len(reuse.RESULTS)==4 and len(AUDIT)==4
        assert all(h.sha(p)==v for p,v in {**old['protected_sha256'],**pins,old['STOP']['path']:old['STOP']['sha256']}.items())
        save('completion.json',dict(status='COMPLETE_PENDING_ASSESSMENT',forecasts=4,fit_calls=0,
            forecast_seconds=sum(r['seconds'] for r in reuse.RESULTS),production_adopted=False))
    except BaseException as exc:
        save('failure.json',dict(error=repr(exc),completed=len(reuse.RESULTS),preserved=True,automatic_retry=False));raise
    finally:
        probe.probe_levers=original_probe;oc.write_derived=original_writer
        reuse.negative_relaxation=original_relaxation


if __name__=='__main__':main()
