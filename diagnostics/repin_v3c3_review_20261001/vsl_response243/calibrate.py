"""Bounded METANET formation-response fit through the existing component runner.

No native run, future boundary inputs, controller objective changes or adoption.
"""
import os
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import ast
import copy
import ctypes
import itertools
import math
import time
from pathlib import Path
import numpy as np
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h
from diagnostics.repin_v3c3_review_20261001.state_lateral168 import run as runner
from diagnostics.repin_v3c3_review_20261001.joint_flux203.calibrate import residual

HERE = Path(__file__).resolve().parent


def packed(rows):
    # Preserve the established scales but include the first control interval.
    return np.concatenate([residual([r for r in rows if r['horizon'] == t])
                           for t in (150, 450)]) / math.sqrt(2.)


def scores(rows):
    return {str(t): h.losses([r for r in rows if r['horizon'] == t], [])
            for t in (150, 450)}


def boxed_step(J, r, radius=.25, ridge=.1):
    A = J.T @ J + ridge * np.eye(2)
    b = -J.T @ r
    options = []
    for codes in itertools.product((-1, 0, 1), repeat=2):
        x = np.asarray(codes, dtype=float) * radius
        free = [i for i, c in enumerate(codes) if c == 0]
        fixed = [i for i, c in enumerate(codes) if c != 0]
        if free:
            x[free] = np.linalg.solve(A[np.ix_(free, free)], b[free] - A[np.ix_(free, fixed)] @ x[fixed])
        if np.max(np.abs(x)) <= radius + 1e-10:
            options.append((float(np.linalg.norm(r + J @ x)**2 + ridge * (x @ x)), x))
    value, x = min(options, key=lambda item: item[0])
    gradient = A @ x - b
    assert all((abs(x[i]) < radius-1e-8 and abs(gradient[i]) < 1e-7)
               or (x[i] <= -radius+1e-8 and gradient[i] >= -1e-7)
               or (x[i] >= radius-1e-8 and gradient[i] <= 1e-7) for i in range(2))
    return x, dict(step=x.tolist(), gradient=gradient.tolist(), linear_objective=value,
                   J=J.tolist(), r=r.tolist(), ridge=ridge, radius=radius)


def main():
    assert not (HERE/'protocol.json').exists(), 'Preserve completed and failed attempts'
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x4000)
    started = time.perf_counter()
    old_ast = ast.parse((HERE/'runner_before.py.txt').read_text(encoding='utf-8-sig'))
    new_ast = ast.parse(Path(runner.__file__).read_text(encoding='utf-8-sig'))
    funcs = lambda tree: {n.name: ast.dump(n) for n in tree.body if isinstance(n, ast.FunctionDef)}
    old, new = funcs(old_ast), funcs(new_ast)
    assert all(v == new[k] for k, v in old.items() if k != 'queue178')
    context, _, _ = runner.common.setup()
    from evaluation.controllers import lane_plant_runtime as lpr
    from evaluation.controllers.freeway_fd import cell_state_response
    base_manifest = h.R/'lane_state132/eval_01/manifest.json'
    frozen = lpr.load_sources(base_manifest)
    document = h.read(base_manifest)
    original = h.read(frozen['paths']['reference_config'])
    oldcfg = frozen['component']._config('FW_E', frozen['parameters']['by_direction']['FW_E'])
    source = h.read(h.R/'spatial_context148/forecast/executed_function_sources.json')
    spec = h.read(h.R/'queue_dynamics178/spec.json')
    spec.pop('queue178')
    production = {str(p): h.sha(p) for p in (h.ROOT/'evaluation/controllers').glob('*.py')}
    stop = h.read(h.R/'joint_flux203/protocol.json')['STOP']
    assert h.sha(stop['path']) == stop['sha256']
    proto = dict(hypothesis='Joint local deceleration and rising-density anticipation calibration; earlier151/153/191 focused acceleration or recovery branches.',
        source='Frozen148 lane/route dynamics,132 prior and171 storage admission. This is an unadopted component model, not the running production plant.',
        parameters=['19--21 deceleration relaxation time common multiplier', '19--21 downstream>=local anticipation common multiplier'],
        train='seed67 late RM hold/release x VSL110/90. Previously inspected and used by132; never call it new blind evidence.',
        validation='seed29 late4,43 early2,61 late2 excluded from this parameter selection. Known historical records, not new blind trials.',
        budget=dict(parity=1,training=28,validation=8,total450=37,fit_steps=1,native=0,FZP_reads=0),
        bounds=[.75,1.25],central_difference=.1,fit='One central Jacobian; boxed ridge step and half step only. No retries, expanded bounds or subsequent refit.',
        score='Existing125 absolute/flow/wait/response residual, equally weighted150 and450s; controller Omega objective unchanged.',
        gates='Frozen candidate: >=10% response reduction, absolute<=110%, all meaningful pair signs correct, regret<=0.5vehh; both150/450 reported. No forced positive benefit.',
        scope='East31 physical cells+4on/4off connectors; not fullOmega qualification.',
        preserved='FD/capacity, acceleration/recovery branch, actual merge, dynamic off storage/drain/FIFO, ramp wait, VSL history, stock conservation.',
        protected_sha256=production,STOP=stop,production_adopted=False,future_measurement_inputs=False,
        previous_native='Current233/235 frozen9000 remains unchanged; user explicitly requested simultaneous offline VSL work.',
        prior_review='Reviewed201/202/203/208/211/213/151/153/191/231 and Claude bd39205 worklog; no claim prior single-candidate failure proves impossibility.')
    pins={str(p):h.sha(p) for p in (Path(__file__),Path(runner.__file__),base_manifest,Path(frozen['paths']['reference_config']),h.R/'queue_dynamics178/forecast/rows.json')}
    h.save(HERE/'protocol.json',proto);h.save(HERE/'pins.json',pins)
    evaluations=[]; bindings=[]; forecasts=0

    def evaluate(z, tag, scope='train'):
        nonlocal forecasts
        z=list(map(float,z));assert len(z)==2 and all(.75<=v<=1.25 for v in z)
        folder=HERE/tag;folder.mkdir()
        config=copy.deepcopy(original)
        for i in (19,20,21):
            row=config['freeway']['state_response']['FW_E']['cell_overrides'][str(i)]
            row['relaxation']['deceleration_sec']*=z[0]
            row['anticipation']['downstream_ge_local']*=z[1]
        path=folder/'reference_config.json';h.save(path,config)
        manifest=copy.deepcopy(document)
        manifest['sources']['reference_config']=dict(path=path.relative_to(h.ROOT).as_posix(),sha256=h.sha(path))
        manifest['qualification']='Unqualified243 component diagnostic; not deployed and requires original148 process-local source hooks.'
        h.save(folder/'manifest.json',manifest)
        loaded=lpr.load_sources(folder/'manifest.json')
        cfg=loaded['component']._config('FW_E',loaded['parameters']['by_direction']['FW_E'])
        assert loaded['parameters']==frozen['parameters']==context['parameters']
        assert cfg.network.freeway_segment_params==oldcfg.network.freeway_segment_params
        for i in range(31):
            actual=cell_state_response(cfg.network,'FW_E',i)
            expected=copy.deepcopy(cell_state_response(oldcfg.network,'FW_E',i))
            if i in (19,20,21):
                expected['relaxation']['deceleration_sec']*=z[0]
                expected['anticipation']['downstream_ge_local']*=z[1]
            assert actual==expected,(i,actual,expected)
        bindings.append(dict(tag=tag,z=z,cell_bindings_verified=True,FD_unchanged=True))
        h.save(HERE/'bindings.json',bindings)
        setting=dict(manifest=str(folder/'manifest.json'),structure='response243',records=scope)
        for name,value in [('setting.json',setting),('spec.json',spec),('coefficients.json',dict(multipliers=z)),('protocol.json',proto),('pins.json',pins),('executed_function_sources.json',source)]:
            h.save(folder/name,value)
        expected=1 if scope=='parity' else 4 if scope=='train' else 8
        assert forecasts+expected<=37
        runner.queue178(calibration243=folder)
        status=h.read(folder/'forecast/status.json');assert status['forecasts']==expected
        forecasts+=expected
        rows=h.read(folder/'forecast/rows.json')
        if scope=='parity':
            rec=rows[0];key=rec['case']+'_'+rec['arm']+'.json.gz'
            pred=h.read(folder/'forecast/response243'/key)
            ref=h.read(h.R/'queue_dynamics178/forecast/baseline'/key)
            parity={k:pred[k]==ref[k] for k in ('cells','flows','ports','ramps')}
            h.save(HERE/'disabled_parity.json',parity);assert all(parity.values()),parity
        row=dict(tag=tag,z=z,scope=scope,rows=rows,scores=scores(rows))
        row['objective']=float(packed(rows)@packed(rows)) if scope!='parity' else None
        evaluations.append(row);h.save(HERE/'evaluations.json',evaluations)
        h.save(HERE/'status.json',dict(status='running',forecasts=forecasts,tag=tag))
        print('VSL243',tag,forecasts,row['objective'],flush=True)
        return row

    try:
        evaluate([1.,1.],'parity','parity')
        center=evaluate([1.,1.],'center'); r0=packed(center['rows']); columns=[]
        for axis in range(2):
            hi=np.ones(2);lo=np.ones(2);hi[axis]+=.1;lo[axis]-=.1
            a=evaluate(hi,f'axis{axis}_plus');b=evaluate(lo,f'axis{axis}_minus')
            columns.append((packed(a['rows'])-packed(b['rows']))/.2)
        step,linear=boxed_step(np.column_stack(columns),r0)
        h.save(HERE/'linear_step.json',linear)
        full=evaluate(np.ones(2)+step,'full_step')
        half=evaluate(np.ones(2)+.5*step,'half_step')
        best=min((full,half),key=lambda r:r['objective'])
        h.save(HERE/'selection_frozen.json',dict(tag=best['tag'],z=best['z'],objective=best['objective'],baseline_objective=center['objective'],selection_before_validation=True))
        val=evaluate(best['z'],'validation','validation')
        baseline=h.read(h.R/'queue_dynamics178/forecast/rows.json')
        baseline=[r for r in baseline if r['mode']=='baseline' and r['case']!='s67_late']
        reference=scores(baseline); gates={};regrets=[]
        for horizon in ('150','450'):
            loss=val['scores'][horizon];old=reference[horizon]
            chosen=[]
            for case in sorted({r['case'] for r in val['rows']}):
                rs=[r for r in val['rows'] if r['case']==case and r['horizon']==int(horizon)]
                selected=min(rs,key=lambda r:r['predicted']['ttt'])
                chosen.append(dict(case=case,horizon=int(horizon),arm=selected['arm'],regret=selected['actual']['ttt']-min(r['actual']['ttt'] for r in rs)))
            regrets+=chosen
            gates[horizon]=dict(response=loss['response']<=.9*old['response'],absolute=loss['absolute']<=1.1*old['absolute'],signs=all(p['sign_correct'] for p in loss['pairs'] if p['meaningful']),regret=all(r['regret']<=.5 for r in chosen))
        training_gates={t:dict(response=best['scores'][t]['response']<=.9*center['scores'][t]['response'],absolute=best['scores'][t]['absolute']<=1.1*center['scores'][t]['absolute'],signs=all(p['sign_correct'] for p in best['scores'][t]['pairs'] if p['meaningful'])) for t in ('150','450')}
        h.save(HERE/'validation.json',dict(gates=gates,training_gates=training_gates,baseline=reference,selected=val['scores'],regrets=regrets))
        passed=all(v for group in (*gates.values(),*training_gates.values()) for v in group.values())
        result=dict(status='complete',forecasts450=forecasts,wall_sec=time.perf_counter()-started,component_gate_passed=passed,production_adopted=False,goal='ACTIVE_NOT_QUALIFIED',native_runs=0,FZP_reads=0)
        h.save(HERE/'completion.json',result);h.save(HERE/'status.json',result)
        print('COMPLETED243',result,flush=True)
    except BaseException as exc:
        h.save(HERE/'status.json',dict(status='failed',forecasts450=forecasts,error=repr(exc)));raise
    finally:
        for path,digest in {**pins,**production,stop['path']:stop['sha256']}.items():assert h.sha(path)==digest,path
        h.save(HERE/'preservation.json',dict(production_sources_unchanged=True,input_and_STOP_hashes_unchanged=True))


if __name__=='__main__':
    main()
