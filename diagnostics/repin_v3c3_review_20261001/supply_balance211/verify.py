"""Check passive instrumentation compatibility and summarize the closed ledger."""
import ast
import contextlib
import io
import json
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent
OUT=h.R/'phase_joint183/supply211'


def funcs(text):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}


def main():
    archive=h.read(HERE/'source_archive.json');checks={}
    for name,changed in [('state_lateral168/run.py','queue178'),('flowbudget182/analyze.py','main')]:
        p=h.R/name;key=str(p.relative_to(h.ROOT)).replace('\\','/')
        item=next(v for k,v in archive.items() if k.replace('\\','/')==key)
        old=h.ROOT/item['archive'];assert h.sha(old)==item['sha256']
        a,b=funcs(old.read_text(encoding='utf8')),funcs(p.read_text(encoding='utf8'))
        assert a.keys()==b.keys()
        assert [k for k,v in a.items() if v!=b[k]]==[changed]
        checks[name+'_other_functions_unchanged']=len(a)-1
    # Exercise the old default analyzer, without overwriting historical output.
    # This is a read of four saved predictions, not four new rollouts.
    from diagnostics.repin_v3c3_review_20261001.flowbudget182 import analyze as module
    oldtext=(HERE/'flowbudget182_analyze.py.before.txt').read_text(encoding='utf8')
    node=next(n for n in ast.parse(oldtext).body if isinstance(n,ast.FunctionDef) and n.name=='main')
    namespace=dict(module.__dict__)
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<recorded182-main>','exec'),namespace)
    captured=[];save=h.save
    def capture(path,value):captured.append((str(path),value))
    try:
        h.save=capture
        with contextlib.redirect_stdout(io.StringIO()):
            namespace['main']();module.main()
    finally:h.save=save
    assert len(captured)==2 and captured[0]==captured[1]
    checks['old_default_analysis_payload_exact']=True
    native=h.read(HERE/'native_totals.json');model_context=[];constraints=[];errors=[]
    totals={}
    for label,mode in [('baseline','baseline'),('ablation','queue')]:
        analysis=h.read(OUT/label/'analysis.json')
        assert analysis['status']=='complete'
        for k,v in analysis['checks'].items():totals[k]=totals.get(k,0)+v
        for arm in ('hold','release','hold_vsl90','release_vsl90'):
            audit=h.read(OUT/label/f'forecast/{mode}/s29_late_{arm}_audit.json.gz')
            assert all(audit['parity'].values())
            lookup={(round(z['time_s'],1),z['cell'],z['lane']):z for z in audit['rows']}
            for cell in (20,21):
                for k in range(3):
                    lo=2670.1+150*k;hi=lo+150
                    rr=[z for z in audit['rows'] if z['cell']==cell and lo-1e-6<=z['time_s']<hi-1e-6]
                    assert len(rr)==450
                    model_context.append(dict(model=label,arm=arm,cell=cell,start=lo,end=hi,
                        lane_mean_n=[sum(z['n'] for z in rr if z['lane']==g)/150 for g in (1,2,3)],
                        final_lane_n=[lookup[round(hi-1,1),cell,g]['end_n'] for g in (1,2,3)]))
        for z in analysis['constraints']:
            if z['arm'] not in ('release','release_vsl90'):continue
            actual=next(r for r in native if r['cell']==20 and r['arm']==z['arm'] and r['start']==z['start'])
            rr=dict(z);rr['model']=label;rr['actual_off']=actual['off_departures'];constraints.append(rr)
        errors.extend(dict(z,model=label) for z in analysis['inventory_budgets'])
    assert totals['unchanged_physical_tables']==32 and totals['actual_constraint']==3600
    core=h.read(h.R/'restart_supply210/protocol.json')['source_sha256'];stop=h.read(HERE/'protocol.json')['STOP']
    assert all(h.sha(h.ROOT/p)==v for p,v in core.items()) and h.sha(stop['path'])==stop['sha256']
    checks.update(totals,core_preserved=len(core),STOP_preserved=True)
    h.save(HERE/'verification.json',dict(status='PASS',checks=checks))
    h.save(HERE/'summary.json',dict(constraints=constraints,inventory_errors=errors,model_lane_context=model_context,
        conclusion='210 changed restart enough to raise late cell20 exit requests, but downstream receiving minus accepted merge restricts both through and shared exit. Rejected phase model is not rescued by hazard adjustment alone.',
        caveats=['Downstream total stock can be underestimated while predicted lane1 is crowded; total-cell density alone cannot validate the lane-specific supply.',
                 'Same downstream law responds correctly with measured states in earlier184; this audit does not justify a capacity bonus.',
                 'No new candidate, no validation state expansion and no wholeOmega claim.']))
    print(json.dumps(checks))
    for r in model_context:
        if r['arm']=='release' and r['start']==2970.1:print(json.dumps(r))


if __name__=='__main__': main()
