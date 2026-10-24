"""Check phase ablation conservation, saved formulas and original input pins."""
import ast
import gzip
import json
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent
OUT=h.R/'phase_joint183/restart210'


def main():
    cfg=h.read(HERE/'config.json');jam=cfg['jam'];length=cfg['lengths'];critical=cfg['critical']
    pins=h.read(HERE/'input_pins.json')
    for p,v in pins.items(): assert h.sha(p)==v
    old92=h.read(h.R/'state_information92/protocol.json')['inputs']
    for key in ('29_none','29_vsl','43_none','43_vsl'):
        assert h.sha(h.ROOT/old92[key]['path'])==old92[key]['sha256']
    errors=[];count=0
    for name in ('native','model'):
        rows=h.read(HERE/f'{name}_rows.json.gz')
        for r in rows:
            i=r['cell']
            expected=min(1.,max(0.,(r['n']/length[i]-critical[i])/(jam-critical[i]),
                                  (r['dn']/length[i+1]-critical[i+1])/(jam-critical[i+1]),
                                  r['ds']/r['dn'] if r['dn'] else 0.))
            errors.append(abs(expected-r['p']));count+=1
            if name=='native':
                assert r['slow_visible']+r['slow_missing']==r['s']
                assert r['moving_visible']+r['moving_missing']==r['n']-r['s']
                for state,endpoint in [('slow','restart'),('moving','onset')]:
                    assert 0<=r[endpoint+'_stayers']<=r[state+'_stayers']<=r[state+'_visible']
                    assert r[endpoint+'_stayers']<=r[endpoint+'_visible']<=r[state+'_visible']
    assert max(errors)<1e-10
    checks=0;mass=moment=0.;context=[]
    for label in ('parity','train'):
        status=h.read(OUT/label/'forecast/status.json')
        assert status['status']=='complete' and status['forecasts']==(1 if label=='parity' else 4)
        for path in (OUT/label/'forecast/queue').glob('*_phase.json.gz'):
            d=h.read(path);lookup={(round(r['time_s'],6),r['cell'],r['lane']):r for r in d['rows']}
            for e in d['events']:
                r=lookup[round(e['time_s']+1,6),e['cell'],e['lane']];b=e['balance']
                residual=e['s0']+b[0]-b[1]+b[2]-b[3]+b[4]-b[5]-r['s']
                mass=max(mass,abs(residual));moment=max(moment,abs(r['n']*r['v']-r['slow_moment']-r['moving_moment']))
                assert 0<=r['s']<=r['n']+1e-9 and min(r['slow_moment'],r['moving_moment'])>=0
                checks+=1
            if label=='train':
                rr=[r for r in d['rows'] if r['time_s']>2970.1 and r['cell']==20 and r['lane']==1]
                context.append(dict(case=path.name,cell=20,lane=1,period='2970.1--3120.1 afterstep1s',
                    mean_n=sum(r['n'] for r in rr)/len(rr),mean_s=sum(r['s'] for r in rr)/len(rr),
                    mean_v=sum(r['v'] for r in rr)/len(rr)))
    assert mass<1e-8 and moment<1e-7 and checks==40500
    old=h.read(h.R/'phase_joint183/endpoint209/operator_train/executed_function_sources.json')
    new=h.read(OUT/'train/executed_function_sources.json')
    assert all(v==new[k] for k,v in old.items() if k!='RouteLaneRegion')
    def methods(s): return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(s).body[0].body if isinstance(n,ast.FunctionDef)}
    before,after=methods(old['RouteLaneRegion']),methods(new['RouteLaneRegion'])
    assert before.keys()==after.keys()
    assert [k for k,v in before.items() if v!=after[k]]==['_phase_change']
    assert h.read(OUT/'train/spec.json')==h.read(h.R/'phase_joint183/endpoint209/operator_train/spec.json')
    assessment=h.read(OUT/'train/assessment.json')
    assert assessment['gates']['150']==dict(signs=True,response=True,absolute=True)
    assert assessment['gates']['450']==dict(signs=True,response=False,absolute=False)
    assert not (OUT/'validation/forecast').exists()
    assert h.read(OUT/'validation/not_run.json')['status']=='SKIPPED_TRAINING_MACRO_GATE_FAILED'
    core=h.read(HERE/'protocol.json')['source_sha256'];stop=h.read(HERE/'protocol.json')['STOP']
    assert all(h.sha(h.ROOT/p)==v for p,v in core.items()) and h.sha(stop['path'])==stop['sha256']
    result=dict(status='PASS',pressure_checks=count,max_pressure_error=max(errors),phase_balance_checks=checks,
        max_mass_error=mass,max_moment_error=moment,unmodified_class_methods=len(before)-1,
        other_runtime_functions_unchanged=len(old)-1,physical_spec_unchanged=True,
        core_preserved=len(core),old_STOP_preserved=True,validation_skipped=True,
        meaning='Verification of a rejected diagnostic, not physical gain qualification.')
    h.save(HERE/'verification.json',result);h.save(HERE/'ablation_context.json',context)
    print(json.dumps(result));print(json.dumps(context))


if __name__=='__main__':main()
