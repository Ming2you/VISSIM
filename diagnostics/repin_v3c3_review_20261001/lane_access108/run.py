"""Three bounded, process-local route-alignment checks using existing rollout."""
import copy
import ctypes
import ctypes.wintypes
import gzip
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
I = ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
F = I/'baseline_reproduction_20260929/cellwise_calibration/freeway_first'
PREVIOUS = HERE.parent/'lane_receiving107'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def change(source, old, new):
    assert source.count(old)==1, (old[:70],source.count(old))
    return source.replace(old,new)


def main():
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=ctypes.wintypes.HANDLE
    kernel.SetPriorityClass.argtypes=[ctypes.wintypes.HANDLE,ctypes.wintypes.DWORD]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    assert not (HERE/'prediction_status.json').exists(), 'No automatic repeat'
    evidence=read(HERE/'assessment.json')['results']
    for arm in ('release','release_vsl90'):
        e=evidence[arm]['exits']
        assert e['vehicles_changed119']==0 and e['first119_lanes']=={'1':e['n']}
    protocol=read(HERE/'protocol.json')
    for path,digest in protocol['protected_sha256'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
    out=HERE/'prediction';out.mkdir(exist_ok=False)
    prior_completion=read(PREVIOUS/'completion.json')
    source_path=PREVIOUS/'dynamic/executed_function_sources.json'
    assert hashlib.sha256(source_path.read_bytes()).hexdigest()==prior_completion['artifact_sha256']['dynamic/executed_function_sources.json']
    sources=read(source_path)
    s=sources['RouteLaneRegion']
    s=change(s,'        self.rows = []\n','        self.rows = []\n        self.keep_aligned_exit = bool(spec.get("keep_aligned_exit", False))\n        self.alignment_rows = []\n')
    # A single change: exit-bound stock already in its physical exit lane is
    # excluded from generic destination-blind discretionary lateral exchange.
    # Other stock, including off-bound stock not yet aligned, keeps old rates.
    anchor='            matrix = []\n'
    s=change(s,anchor,'''            eligible = []
            for g,row in enumerate(old):
                available = {}
                locked = 0.
                for key,n in row.items():
                    target = key.rsplit('|',1)[-1]
                    aligned = (target in self.off_access and self.off_access[target] == g
                               and i <= runtime['branches'][target]['source_cell'])
                    if self.keep_aligned_exit and aligned:
                        locked += n
                    else:
                        available[key] = n
                eligible.append(available)
                if self.keep_aligned_exit and locked:
                    self.alignment_rows.append(dict(time_s=state.time_sec,cell=i,lane=g+1,locked_exit_veh=locked))
            movable = [sum(row.values()) for row in eligible]
            matrix = []
''')
    s=change(s,'matrix.append([ns[g]*(1.-math.exp(-hazard*dt*3600))*r/hazard if hazard else 0. for r in rates])',
             'matrix.append([movable[g]*(1.-math.exp(-hazard*dt*3600))*r/hazard if hazard else 0. for r in rates])')
    s=change(s,'classes = {key:n*amount/ns[g] for key,n in old[g].items()}',
             'classes = {key:n*amount/movable[g] for key,n in eligible[g].items()}')
    sources['RouteLaneRegion']=s
    sources['rollout']=change(sources['rollout'],"receiving_rows=joint_lanes.receiving_rows,", "receiving_rows=joint_lanes.receiving_rows, alignment_rows=joint_lanes.alignment_rows,")
    save(out/'executed_function_sources.json',sources)
    save(out/'protocol.json',dict(
        question='Does preventing destination-blind scattering of already aligned off-ramp traffic improve the same-state VSL response?',
        change='keep_aligned_exit only in19/20 approaching10483; all other lane rates, FD, merge and objective unchanged. Receiving107 addition OFF.',
        reason='All136/150 observed10483 departures first seen on119lane1, zero observed net lane changes in approach; all65 ex-ante known exit vehicles also aligned.',
        inputs='Same archived2670.1 seed67 component captures and initial current route inventory as107; no future observations in rollout.',
        maximum450_calls=3, cases=['lane baseline disabled exact parity','aligned exit release','aligned exit release_vsl90'],
        fits=0, new_native=0, new_FZP=0,
        continuation_gate='Mainline meaningful VSL gain sign correct; response error reduces>=20% vs lane-only107; no state RMSE>10% worsening; conservation valid. This is necessary, not wholeOmega sufficiency.',
        limits=['Observed5s net changes can miss change-and-return within5s.',
                'Locking is a tested approximation, not a universal VISSIM rule.',
                'Lane-only baseline already rejected; success against it does not suffice for production adoption.',
                'Seed67 repeatedly inspected; passing requires other states and largeRM validation later.']))
    from evaluation.controllers import lane_plant_runtime as lpr
    context=lpr.load_sources(ROOT/read(PREVIOUS/'protocol.json')['manifest'])
    from evaluation.controllers import physical_lane_groups as lanes, offramp_routing as route, area_freeway_accounting as area
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import replay_congested_component as replay
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    model=context['component'];cls=type(model)
    spec=read(F/'joint_lane_25/protocol.json')['candidate']
    assert not spec.get('congested_receiving_cells')
    capture=read(I/'heldout67_freeway_20260930/capture.json')
    inputs={}
    for arm in ('release','release_vsl90'):
        rec=next(r for r in capture['records'] if r['arm']==arm)
        args,kw=replay.read_primitive_capture(rec['input'],rec['sha256'])
        assert args[2]==context['parameters']
        kw['offramp_inventory']=dict(contract=read(F/'route_inventory/contract.json'),raw=read(F/'route_inventory/s67_late/initial_raw.json'))
        kw['port_dynamics']['entry_capacity_mode']='storage'
        inputs[arm]=(args,kw,dict(rec,case='s67_late',cutoff=2670.1))
    originals=[];results=[];completed=0;started=time.perf_counter()
    save(HERE/'prediction_status.json',dict(status='running',completed=0,max_calls=3))
    try:
        assert not hasattr(lanes,'RouteLaneRegion')
        ns={};exec(compile(sources['RouteLaneRegion'],str(out/'class'),'exec'),lanes.__dict__,ns)
        lanes.RouteLaneRegion=ns['RouteLaneRegion'];originals.append((lanes,'RouteLaneRegion',None))
        for target,name in ((route,'initialize_inventory'),(route,'advance_inventory'),(area,'_freeway_substep_events'),(cls,'rollout')):
            old=getattr(target,name);ns={}
            exec(compile(sources[name],str(out/name),'exec'),old.__globals__,ns)
            originals.append((target,name,old));setattr(target,name,ns[name])
        for label,arm,enabled in (('disabled','release',False),('aligned_release','release',True),('aligned_release_vsl90','release_vsl90',True)):
            args,kw,rec=inputs[arm];args=copy.deepcopy(args);kw=copy.deepcopy(kw)
            current_spec=copy.deepcopy(spec);current_spec['keep_aligned_exit']=enabled
            kw['route_lane_regions']={'FW_E':current_spec}
            pred=model.rollout(*args,**kw);completed+=1
            with gzip.open(out/(label+'.json.gz'),'wt',encoding='utf-8') as f:json.dump(pred,f,allow_nan=False)
            if not enabled:
                with gzip.open(PREVIOUS/'dynamic/lanes_release.json.gz','rt',encoding='utf-8') as f:old=json.load(f)
                parity={k:json.loads(json.dumps(old[k]))==json.loads(json.dumps(pred[k])) for k in ('cells','flows','ports','ramps')}
                save(out/'disabled_parity.json',parity);assert all(parity.values())
            score=replay._cellwise_measure(model,pred,rec,ObservationData(I/'heldout67_freeway_20260930/observations'/arm),horizon_sec=450)
            detail=pred['diagnostics']['roads'][0]['joint_lane_region']
            assert detail['route_marginal_max_error']<1e-7 and not score['score']['invalid']
            score['version']=label;score['alignment_records']=len(detail['alignment_rows'])
            results.append(score);save(out/'partial.json',dict(completed=completed,rows=results))
            print(json.dumps(dict(label=label,predicted=score['predicted'],alignment_records=score['alignment_records'])),flush=True)
        save(out/'summary.json',dict(completed=completed,rows=results,elapsed_seconds=time.perf_counter()-started))
        save(HERE/'prediction_status.json',dict(status='complete_pending_assessment',completed=completed))
    except BaseException as exc:
        save(out/'failure.json',dict(error=repr(exc),completed=completed));save(HERE/'prediction_status.json',dict(status='failed',completed=completed,error=repr(exc)))
        raise
    finally:
        for target,name,old in reversed(originals):
            if old is None:delattr(target,name)
            else:setattr(target,name,old)
        for path,digest in protocol['protected_sha256'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
        assert hashlib.sha256(Path(protocol['STOP']['path']).read_bytes()).hexdigest()==protocol['STOP']['sha256']
        save(out/'restoration.json',dict(hooks_restored=True,core_unchanged=True,STOP_unchanged=True))


if __name__=='__main__':
    main()
