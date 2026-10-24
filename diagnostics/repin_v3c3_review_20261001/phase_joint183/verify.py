"""Independent calibration/selection and preserved-physics audit for183."""
from pathlib import Path
import itertools
import math
import numpy as np
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def changes(a,b,p=()):
    if isinstance(a,dict):
        assert a.keys()==b.keys()
        return [x for k in a for x in changes(a[k],b[k],p+(k,))]
    return [] if a==b else [p]


def main():
    status=h.read(HERE/'status.json');assert status['status']=='complete'
    protocol=h.read(HERE/'protocol.json');evaluation=h.read(HERE/'evaluations.json')
    selected=h.read(HERE/'selection_frozen.json');validation=h.read(HERE/'validation.json')
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    common.setup()
    from evaluation.controllers import lane_plant_runtime as lpr
    frozen=lpr.load_sources(h.R/'lane_state132/eval_01/manifest.json')
    original=h.read(frozen['paths']['reference_config'])
    expected_paths={('freeway','physical_cell_fd','FW_E',str(i),'rho_crit') for i in (20,21)}
    expected_paths|={('freeway','state_response','FW_E','cell_overrides',str(i),'relaxation','acceleration_sec') for i in (20,21)}
    expected_paths|={('freeway','state_response','FW_E','cell_overrides',str(i),'delta_merge') for i in (21,23)}
    count=0;fit_cases=set();valid_cases=set();contrasts=[];phase_checks=0;phase_max_error=0.
    for item in evaluation:
        p=Path(item['folder']);assert h.read(p/'forecast/status.json')['status']=='complete'
        count+=h.read(p/'forecast/status.json')['forecasts']
        assert set(changes(original,h.read(p/'reference_config.json')))<=expected_paths
        assert h.sha(p/'coefficients.json')==h.sha(h.R/'phase_equilibrium181/coefficients.json')
        assert h.sha(p/'executed_function_sources.json')==h.sha(h.R/'phase_equilibrium181/executed_function_sources.json')
        preservation=h.read(p/'forecast/preservation.json');assert preservation['hooks_restored']
        for path,digest in preservation['input_sha256'].items():assert h.sha(path)==digest,path
        cases={r['case'] for r in item['rows']}
        if item['scope'] in ('train','parity'):fit_cases|=cases;assert cases=={'s29_late'}
        else:valid_cases|=cases;assert 's29_late' not in cases
        if item['scope']=='validation' and item['structure']=='queue':
            for row in item['rows']:
                trace=h.read(p/'forecast/queue'/(row['case']+'_'+row['arm']+'_phase.json.gz'))
                by={(round(z['time_s'],6),z['cell'],z['lane']):z for z in trace['rows']}
                for e in trace['events']:
                    z=by[round(e['time_s']+1,6),e['cell'],e['lane']]
                    b=e['balance'];expected=e['s0']+b[0]-b[1]+b[2]-b[3]+b[4]-b[5]
                    error=abs(expected-z['s']);phase_max_error=max(phase_max_error,error);assert error<1e-7
                    assert -1e-7<=z['s']<=z['n']+1e-7
                    assert abs(z['slow_moment']+z['moving_moment']-z['n']*z['v'])<1e-7
                    phase_checks+=1
        loss=h.losses(item['rows'],item['z'])
        for k in ('absolute','local','response','prior','objective'):assert abs(loss[k]-item['loss'][k])<1e-10
        assert all(.8-1e-10<=v<=1.2+1e-10 for v in item['z'])
    assert count==status['forecasts']<=66
    fixed=h.read(h.R/'phase_equilibrium181/forecast/rows.json')
    for structure in ('baseline','queue'):
        proposal=h.read(HERE/(structure+'_proposal.json'));J=np.array(proposal['jacobian']);r=np.array(proposal['residual']);x=np.array(proposal['step'])
        g=J.T@(r+J@x)+.025*x
        assert np.max(np.abs(g-np.array(proposal['gradient'])))<1e-9
        assert all((abs(x[i])<.2-1e-8 and abs(g[i])<1e-7) or (x[i]<=-.2+1e-8 and g[i]>=-1e-7) or (x[i]>=.2-1e-8 and g[i]<=1e-7) for i in range(4))
        base=selected[structure]['fixed_loss']
        trials=[e for e in evaluation if e['structure']==structure and e['tag'] in ('full','half')]
        okay=[e for e in trials if e['loss']['objective']<=.95*base['objective'] and e['loss']['response']<=base['response']+1e-12]
        best=min(okay,key=lambda e:e['loss']['objective']) if okay else None
        assert selected[structure]['train_qualified']==bool(best)
        assert selected[structure]['z']==(best['z'] if best else [1.]*4)
        values=validation[structure]
        current=h.losses(values['rows'],selected[structure]['z'])
        original_base=h.losses([r for r in fixed if r['mode']=='baseline' and r['horizon']==450 and r['case']!='s29_late'],[1.]*4)
        values['against_original_baseline']=dict(response_ratio=current['response']/original_base['response'],
            absolute_ratio=current['absolute']/original_base['absolute'],
            response_pass=current['response']<=.9*original_base['response'],absolute_pass=current['absolute']<=1.1*original_base['absolute'])
        for case in sorted({r['case'] for r in values['rows']}):
            by={r['arm']:r for r in values['rows'] if r['case']==case}
            for aa,bb in [('hold','release'),('release','release_vsl90'),('hold','hold_vsl90'),('none','vsl')]:
                if aa not in by or bb not in by:continue
                contrasts.append(dict(structure=structure,case=case,change=aa+'->'+bb,
                    actual=by[bb]['actual']['ttt']-by[aa]['actual']['ttt'],predicted=by[bb]['predicted']['ttt']-by[aa]['predicted']['ttt']))
    preservation=h.read(HERE/'preservation.json')
    for path,digest in {**preservation['input_sha256'],**protocol['protected_sha256'],protocol['STOP']['path']:protocol['STOP']['sha256']}.items():assert h.sha(path)==digest,path
    result=dict(status='verified',forecasts=count,train_cases=sorted(fit_cases),new_validation_cases=sorted(valid_cases),
        six_config_paths_only=True,constant_hazards_and_physics=True,selection_from_training_only=True,
        kkt_verified=True,protected_and_STOP=True,contrasts=contrasts,
        selected_validation_phase_checks=phase_checks,phase_max_error=phase_max_error,
        comparison={k:{'gates':v['gates'],'against_original_baseline':v['against_original_baseline']} for k,v in validation.items()},
        qualified=all(v['passed'] and v['against_original_baseline']['response_pass'] and v['against_original_baseline']['absolute_pass'] for v in validation.values()),
        adopted=False,wholeOmega_and8ramp_SDPMC_native_qualified=False)
    h.save(HERE/'verification.json',result)
    print(result)


if __name__=='__main__':main()
