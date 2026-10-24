"""Independent exact kinetics checks; later inspect saved rollouts without rerunning."""
import ast
import copy
import json
import math
from pathlib import Path
from types import SimpleNamespace as NS
import numpy as np
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h
from diagnostics.repin_v3c3_review_20261001.phase_joint183.endpoint209.prepare import HERE


def units():
    code=h.read(HERE/'exact_function_sources.json')['RouteLaneRegion']
    fn=next(n for n in ast.parse(code).body[0].body if isinstance(n,ast.FunctionDef) and n.name=='_phase_change')
    ns={'math':math};exec(compile(ast.Module(body=[fn],type_ignores=[]),'actual209_method','exec'),ns)
    method=ns['_phase_change'];results=[]
    for n,s,ms,mm,a,b in [(10,3,3,280,.2,.7),(10,0,0,400,.2,.7),(10,10,20,0,.2,.7),
                         (10,3,3,280,0.,.7),(10,3,3,280,.2,0.),(10,3,3,280,0.,0.),
                         (10,3,3,280,.4,.1),(10,3,3,280,1.,1.)]:
        def obj():
            return NS(phase_next={20:[[s,ms,mm]]},next={20:[{'all':n}]},phase0={20:[[s,ms,mm]],21:[[1,0,400]]},
                      phase_start_n={20:[n],21:[12]},lengths={20:.2,21:.2},
                      spec178={'formation_per_sec':a,'release_per_sec':b},phase_balance={20:[[0.]*6]},phase_events=[])
        cfg=NS(network=NS(freeway_segment_params={'FW_E':{20:{'rho_crit':40.},21:{'rho_crit':40.}}},rho_max=150.),
               simulation=NS(T_f_h=1/3600))
        o=obj();o.road='FW_E';result,_=method(o,20,0,NS(time_sec=0),cfg)
        p=o.phase_events[0]['pressure'];alpha,beta=a*p,b*(1-p)
        def f(z):
            ss,x,y,on,off=z
            return np.array([alpha*(n-ss)-beta*ss,-beta*x,-alpha*y+beta*x,alpha*(n-ss),beta*ss])
        z=np.array([s,ms,mm,0.,0.],float);dt=.01
        for _ in range(100):
            k1=f(z);k2=f(z+k1*dt/2);k3=f(z+k2*dt/2);k4=f(z+k3*dt)
            z+=dt*(k1+2*k2+2*k3+k4)/6
        actual=np.array([*result,o.phase_events[0]['onset'],o.phase_events[0]['release']])
        err=float(max(abs(actual-z)))
        assert err<1e-7 and min(actual)>=-1e-10 and 0<=result[0]<=n
        assert result[1]+result[2]<=ms+mm+1e-9
        assert abs(result[0]-s-o.phase_events[0]['onset']+o.phase_events[0]['release'])<1e-10
        results.append(dict(a=a,b=b,pressure=p,error=err,initial_s=s))
    # Eligible trial counts, not all current vehicles, define both likelihood terms.
    rows=h.read(HERE/'fit_samples.json');fit=h.read(HERE/'frozen_fit.json')
    assert all(z['on']<=z['nm'] and z['off']<=z['ns'] and z['nm']+z['ns']<=z['n'] for z in rows)
    assert sum(z['on'] for z in rows)==1014 and sum(z['off'] for z in rows)==1055
    assert sum(z['nm']+z['ns'] for z in rows)==fit['trials']==28348
    assert sum(z['n'] for z in rows)==fit['all_current_population']==45792
    assert fit['projected_gradient']<1e-5 and not fit['bound_hit']
    # Independent probability via a2x2 generator power-series exponential.
    prob_error=0.
    for p in (0.,.1,.5,.9,1.):
        a,b=fit['rates'];Q=np.array([[-a*p,a*p],[b*(1-p),-b*(1-p)]])*5
        P=np.eye(2);term=P.copy()
        for k in range(1,70):term=term@Q/k;P+=term
        r=a*p+b*(1-p)
        expected=np.array([[1-a*p/r*(1-math.exp(-5*r)),a*p/r*(1-math.exp(-5*r))],
                           [b*(1-p)/r*(1-math.exp(-5*r)),1-b*(1-p)/r*(1-math.exp(-5*r))]])
        prob_error=max(prob_error,float(np.max(abs(P-expected))))
    assert prob_error<1e-12
    old=h.read(h.R/'phase_equilibrium181/executed_function_sources.json')['RouteLaneRegion']
    methods=lambda code:{n.name:ast.dump(n,include_attributes=False) for n in ast.parse(code).body[0].body if isinstance(n,ast.FunctionDef)}
    old_methods,new_methods=methods(old),methods(code)
    assert old_methods.keys()==new_methods.keys()
    assert all(v==new_methods[k] for k,v in old_methods.items() if k!='_phase_change')
    result=dict(status='PASS',actual_kinetics_fixtures=results,probability_matrix_error=prob_error,
                eligible_trials=28348,all_current_population=45792,observed_onsets=1014,observed_releases=1055,
                unsupported_onset_events=5,only_reaction_method_changed=True,no_production_changes=True)
    h.save(HERE/'unit.json',result);print(json.dumps(result))


def results():
    original_rows=h.read(h.R/'phase_equilibrium181/forecast/rows.json')
    old={mode:[r for r in original_rows if r['mode']==mode and r['case']=='s29_late']
         for mode in ('baseline','queue')}
    new={key:h.read(HERE/key/'forecast/rows.json') for key in ('operator_train','refit_train')}
    for key in ('parity',*new):
        status=h.read(HERE/key/'forecast/status.json')
        assert status['status']=='complete' and status['forecasts']==(1 if key=='parity' else 4)
    source=h.R/'phase_equilibrium181/forecast/queue/s29_late_hold.json.gz'
    parity=h.read(HERE/'parity/forecast/queue/s29_late_hold.json.gz');ref=h.read(source)
    assert all(parity[k]==ref[k] for k in ('cells','flows','ports','ramps'))
    scores={};gates={}
    for horizon in (150,450):
        score={label:h.losses([r for r in rows if r['horizon']==horizon],(1,1,1,1))
               for label,rows in {**old,**new}.items()}
        scores[str(horizon)]=score
        for label in new:
            a,b=score['baseline'],score[label]
            gate=dict(signs=all(p['sign_correct'] for p in b['pairs'] if p['meaningful']),
                      response=b['response']<=.9*a['response'],absolute=b['absolute']<=1.1*a['absolute'])
            gates[f'{label}_{horizon}']=gate
    assert not all(gates['refit_train_450'].values()), 'Inspect before expanding to validation'
    # Every model's physical quantities are checked independently of scores.
    max_mass=max_moment=0.;checks=0;context=[]
    for key in ('parity',*new):
        for file in (HERE/key/'forecast/queue').glob('*_phase.json.gz'):
            data=h.read(file);rr={(round(z['time_s'],6),z['cell'],z['lane']):z for z in data['rows']}
            assert len(rr)==8100 and len(data['events'])==8100
            for event in data['events']:
                b=event['balance'];expected=event['s0']+b[0]-b[1]+b[2]-b[3]+b[4]-b[5]
                row=rr[round(event['time_s']+1,6),event['cell'],event['lane']]
                max_mass=max(max_mass,abs(expected-row['s']),abs(event['s_next']-row['s']))
                max_moment=max(max_moment,abs(row['slow_moment']+row['moving_moment']-row['n']*row['v']))
                assert min(row['s'],row['slow_moment'],row['moving_moment'])>=-1e-8
                assert row['s']<=row['n']+1e-8;checks+=1
            for cell in (20,21,24,25):
                ev=[e for e in data['events'] if e['cell']==cell and e['lane']==1 and e['time_s']>=2970.1]
                context.append(dict(mode=key,case=file.name,cell=cell,lane=1,
                    mean_pressure=sum(e['pressure'] for e in ev)/len(ev),
                    mean_n=sum(e['n0'] for e in ev)/len(ev),mean_s=sum(e['s0'] for e in ev)/len(ev),
                    exact_pressure_one_steps=sum(e['pressure']==1 for e in ev)))
    assert max_mass<1e-8 and max_moment<1e-7
    core=h.read(h.R/'recovery_memory206/protocol.json')['source_sha256']
    assert all(h.sha(h.ROOT/p)==v for p,v in core.items())
    prot=h.read(HERE/'protocol.json');assert h.sha(prot['STOP']['path'])==prot['STOP']['sha256']
    frozen=h.read(HERE/'frozen_fit.json')
    for path,digest in frozen['input_sha256'].items():assert h.sha(path)==digest
    for key in ('operator_validation','refit_validation'):
        assert not (HERE/key/'forecast').exists()
        h.save(HERE/key/'not_run.json',dict(status='SKIPPED_TRAINING_MACRO_GATE_FAILED',
            reason='No additional heldout forecast on a candidate already failing training physical response gates.'))
    result=dict(status='COMPLETE_ENDPOINT_REFIT_REJECTED',forecasts=9,fits=1,
        scores=scores,training_gates=gates,phase_balance_checks=checks,max_mass_error=max_mass,
        max_moment_error=max_moment,baseline_parity_exact=True,production_adopted=False,
        validation_executed=False,core_files_preserved=len(core),old_STOP_preserved=True,
        native=0,FZP_reads=0,push=0,goal='ACTIVE_NOT_QUALIFIED')
    h.save(HERE/'results.json',result);h.save(HERE/'phase_context.json',context)
    print(json.dumps({k:v for k,v in result.items() if k!='scores'}))
    print(json.dumps({label:{k:v for k,v in score.items() if k!='pairs'} for label,score in scores['450'].items()}))


if __name__=='__main__':
    import sys
    if '--results' in sys.argv:results()
    else:units()
