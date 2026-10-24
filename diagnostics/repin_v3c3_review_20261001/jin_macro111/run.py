"""Bounded Jin effective-density trial in the existing conservative plant."""
import copy
import ctypes
import ctypes.wintypes
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
I = ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
C = I/'baseline_reproduction_20260929/cellwise_calibration'
ROUTE = C/'freeway_first/route_inventory'
MANIFEST = HERE.parent/'retained10638/candidate_manifest.json'
FILES = ['evaluation/controllers/freeway_fd.py', 'evaluation/controllers/area_freeway_accounting.py']


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def save(p, value):
    Path(p).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def setup():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.wintypes.HANDLE
    kernel.SetPriorityClass.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x4000)
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import replay_congested_component as replay
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    context = lpr.load_sources(MANIFEST)
    return context, replay, ObservationData


def records(training=True):
    if training:
        return [r for r in read(C/'data_catalog.json')['checked_records'] if r['case'] in ('s29_early', 's43_early')]
    capture = read(I/'heldout67_freeway_20260930/capture.json')
    return [dict(r, case='s67_late', cutoff=capture['cutoff'],
                 truth=str(I/'heldout67_freeway_20260930/observations'/r['arm'])) for r in capture['records']]


def payload(replay, r, seconds):
    args, kw = copy.deepcopy(replay.read_primitive_capture(r['input'], r['sha256']))
    # Saved captures use the unchanged one-second integrator; shorten only the
    # diagnostic forecast, never the controller period or original inputs.
    assert len(args[1]) == 450 and kw['horizon_sec'] == 450
    args[1][:] = args[1][:seconds]
    kw['horizon_sec'] = seconds
    kw['offramp_inventory'] = dict(contract=read(ROUTE/'contract.json'), raw=read(ROUTE/r['case']/'initial_raw.json'))
    kw['port_dynamics']['entry_capacity_mode'] = 'storage'
    return args, kw


def predict(model, replay, observations, r, seconds):
    args, kw = payload(replay, r, seconds)
    result = model.rollout(*args, **kw)
    measure = replay._cellwise_measure(model, result, r, observations, horizon_sec=seconds)
    return result, measure


def prepare():
    assert not (HERE/'protocol.json').exists(), 'Existing trial must not be overwritten'
    context, replay, Obs = setup()
    backup = HERE/'before'; backup.mkdir()
    pins = {}
    for f in FILES:
        (backup/Path(f).name).write_bytes((ROOT/f).read_bytes()); pins[f] = sha(ROOT/f)
    protocol = dict(
        paper='Jin2010 equations5/6/12, https://arxiv.org/html/math/0503036',
        transfer='Effective density in METANET relaxation target only; actual rho, mass, q=rho*v*lanes, queues and costs conserved.',
        proxy='Current exit-intent stock in fixed cells16..20 / all stock; not actual departures or stopped-count ground truth.',
        geometry='FW_E physical zero-based16..20, from upstream VSL through10483 exit. No cell-specific coefficients.',
        cells=list(range(16,21)), c_seconds=[0.,10.,30.], critical_multipliers=[1.,1.10,1.20],
        training='29/43 early2220.1, all four arms, first150s.43 is used for calibration here, not held out.',
        validation='67 late2670.1 all four arms450s. Previously inspected, not blind; never used for selection.',
        selection='Mean squared normalized absolute and policy-difference TTT/endN/exits/merge errors, equally weighted; no speed RMSE fitting.',
        absolute_scales=dict(ttt=2., end_n=40., exits=30., ramp_ttt=1., merge=20.),
        response_scales=dict(ttt=.5, end_n=15., exits=15., ramp_ttt=.5, merge=10.),
        gate='Training objective>=5% better; validation meaningful |deltaTTT|>=0.5vehh signs preserved and response loss>=10% better, absolute loss<=110%baseline. No adoption from component success alone.',
        budget=dict(grid_candidates=9, training150=72, validation450=8, parity150=1, pre_edit150=1),
        scope='FW_E mainline + four on-ramp and four off-ramp connectors; NOT wholeOmega. Exits are mainline departures, NOT Omega TTD.',
        no_future_truth_inputs=True, new_native_runs=0, automatic_grid_extension=False, before_sha256=pins)
    save(HERE/'protocol.json', protocol)
    r = records()[0]
    pred, measured = predict(context['component'], replay, Obs(r['truth']), r, 150)
    with gzip.open(HERE/'pre_edit150.json.gz','wt',encoding='utf-8') as f: json.dump(pred,f,allow_nan=False)
    save(HERE/'pre_edit150_measure.json', measured)
    print(json.dumps(dict(stage='prepared', predicted=measured['predicted'])), flush=True)


def losses(rows, protocol):
    def error(p, a, scales):
        terms = [((p[k]-a[k])/scales[k])**2 for k in ('ttt','end_n','exits','ramp_ttt')]
        terms.append(sum(((p['merges'][r]-a['merges'][r])/scales['merge'])**2 for r in a['merges'])/len(a['merges']))
        return sum(terms)/len(terms)
    absolute = sum(error(r['predicted'],r['actual'],protocol['absolute_scales']) for r in rows)/len(rows)
    pairs = []
    for case in sorted({r['case'] for r in rows}):
        group = [r for r in rows if r['case']==case]
        base = next(r for r in group if r['arm'] in ('none','hold'))
        comparisons = [(base,r) for r in group if r is not base]
        by = {r['arm']:r for r in group}
        for a,b in (('rm','both'),('release','release_vsl90')):
            if a in by and b in by: comparisons.append((by[a],by[b]))
        for first, second in comparisons:
            deltas = {}
            for kind in ('actual','predicted'):
                p,a = second[kind],first[kind]
                deltas[kind] = {k:p[k]-a[k] for k in ('ttt','end_n','exits','ramp_ttt')}
                deltas[kind]['merges'] = {r:p['merges'][r]-a['merges'][r] for r in a['merges']}
            pairs.append(dict(case=case,pair=first['arm']+'->'+second['arm'],**deltas))
    response = sum(error(p['predicted'],p['actual'],protocol['response_scales']) for p in pairs)/len(pairs)
    return dict(absolute=absolute,response=response,objective=(absolute+response)/2,pairs=pairs)


def block_measures(model, replay, observations, record, pred):
    """150s block costs without resetting predicted stocks to future truth."""
    previous=None; result=[]
    for horizon in (150,300,450):
        end=record['cutoff']+horizon; cropped=dict(pred)
        for name,key in (('cells','time_s'),('flows','window_end_s'),('ports','time_s'),('ramps','end_sec')):
            cropped[name]=[x for x in pred[name] if x[key]<=end+1e-6]
        cumulative=replay._cellwise_measure(model,cropped,record,observations,horizon_sec=horizon)
        block=copy.deepcopy(cumulative);block['case']+='_'+str(horizon)
        if previous is not None:
            for kind in ('actual','predicted'):
                for key in ('ttt','mainline_ttt','ramp_ttt','off_ttt','exits'):
                    block[kind][key]-=previous[kind][key]
                for r in block[kind]['merges']:block[kind]['merges'][r]-=previous[kind]['merges'][r]
        previous=cumulative;result.append(block)
    return result


def run(horizon_sec=150):
    assert not (HERE/'fit_status.json').exists(), 'No automatic retries or duplicate fit'
    from evaluation.controllers import freeway_fd
    assert hasattr(freeway_fd, 'jin_lane_intensity'), 'Rejected candidate is archived; apply reviewed candidate.patch only in an isolated copy'
    protocol = read(HERE/'protocol.json')
    context, replay, Obs = setup(); model = context['component']
    started = time.perf_counter(); completed = 0; current = None
    source_config = model._config
    def configured(road, parameters):
        cfg = source_config(road, parameters)
        if current is not None and road=='FW_E':
            c,scale = current
            cfg.network.freeway_jin_lane_intensity = {'FW_E':dict(cells=protocol['cells'],duration_sec=c)}
            for cell in protocol['cells']:
                cfg.network.freeway_segment_params[road][cell]['rho_crit'] *= scale
        return cfg
    model._config = configured
    save(HERE/'fit_status.json',dict(status='running',completed=0))
    train = records(); truth = {(r['case'],r['arm']):Obs(r['truth']) for r in train}
    try:
        if horizon_sec==150:
            pred, measured = predict(model,replay,truth[(train[0]['case'],train[0]['arm'])],train[0],150)
            with gzip.open(HERE/'pre_edit150.json.gz','rt',encoding='utf-8') as f: old=json.load(f)
            parity={k:json.loads(json.dumps(pred[k]))==old[k] for k in ('cells','flows','ports','ramps')}
            save(HERE/'disabled_parity.json',parity); assert all(parity.values())
        else:
            assert all(read(HERE.parent/'disabled_parity.json').values())
        grid=[]
        for c in protocol['c_seconds']:
            for scale in protocol['critical_multipliers']:
                current=(c,scale); rows=[]
                for r in train:
                    observations=truth[(r['case'],r['arm'])]
                    pred,measure=predict(model,replay,observations,r,horizon_sec)
                    rows.extend(block_measures(model,replay,observations,r,pred) if horizon_sec==450 else [measure]);completed+=1
                    save(HERE/'fit_status.json',dict(status='running',completed=completed,current=current,case=r['case'],arm=r['arm']))
                result=dict(c_seconds=c,critical_multiplier=scale,rows=rows,loss=losses(rows,protocol))
                grid.append(result);save(HERE/'grid.json',grid)
                print(json.dumps(dict(completed=completed,c=c,scale=scale,loss={k:v for k,v in result['loss'].items() if k!='pairs'})),flush=True)
        best=min(grid,key=lambda r:r['loss']['objective']);baseline=grid[0]
        selection=dict(c_seconds=best['c_seconds'],critical_multiplier=best['critical_multiplier'],
                       training_improvement=1-best['loss']['objective']/baseline['loss']['objective'],
                       selected_before_validation=True,selected_ordinal=grid.index(best))
        save(HERE/'selection.json',selection)
        held=[]
        reuse=[]
        for label,current in [('baseline',(0.,1.)),('selected',(best['c_seconds'],best['critical_multiplier']))]:
            for r in records(False):
                reuse_label=None
                if horizon_sec==450:
                    previous=read(HERE.parent/'selection.json')
                    if current==(0.,1.):reuse_label='baseline'
                    elif current==(previous['c_seconds'],previous['critical_multiplier']):reuse_label='selected'
                if reuse_label:
                    source=HERE.parent/(reuse_label+'_'+r['arm']+'.json.gz')
                    with gzip.open(source,'rt',encoding='utf-8') as f:pred=json.load(f)
                    measure=replay._cellwise_measure(model,pred,r,Obs(r['truth']),horizon_sec=450)
                    reuse.append(dict(version=label,arm=r['arm'],source=str(source),sha256=sha(source)))
                    (HERE/(label+'_'+r['arm']+'.json.gz')).write_bytes(source.read_bytes())
                else:
                    pred,measure=predict(model,replay,Obs(r['truth']),r,450);completed+=1
                    with gzip.open(HERE/(label+'_'+r['arm']+'.json.gz'),'wt',encoding='utf-8') as f: json.dump(pred,f,allow_nan=False)
                held.append(dict(version=label,**measure));save(HERE/'validation.json',held)
                save(HERE/'fit_status.json',dict(status='validating',completed=completed,version=label,arm=r['arm']))
                print(json.dumps(dict(version=label,arm=r['arm'],predicted=measure['predicted'])),flush=True)
        save(HERE/'reused_predictions.json',reuse)
        save(HERE/'fit_status.json',dict(status='complete_pending_assessment',completed=completed,elapsed_seconds=time.perf_counter()-started))
    except BaseException as exc:
        save(HERE/'fit_status.json',dict(status='failed',completed=completed,current=current,error=repr(exc)))
        raise
    finally:
        model._config=source_config


if __name__=='__main__':
    {'prepare':prepare,'run':run}[sys.argv[1]]()
