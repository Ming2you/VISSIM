"""Bounded diagnostic ablation of own-density restart feedback, not deployment."""
import ast
import copy
import ctypes
import json
import math
from pathlib import Path
import textwrap
import time
from types import SimpleNamespace as NS
import numpy as np
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE = Path(__file__).resolve().parent
OLD = h.R/'phase_joint183/endpoint209/operator_train'
OUT = h.R/'phase_joint183/restart210'


def prepare():
    assert not OUT.exists()
    sources = h.read(OLD/'executed_function_sources.json')
    candidate = copy.deepcopy(sources)
    before = '        alpha,beta=a*pressure,b*(1-pressure)\n'
    after = '''        # 210 DIAGNOSTIC ABLATION: formation retains all pressure terms.
        # Restart responds to current downstream density/slow fraction only.
        # No coefficient change, flow bonus, future observation or deployment.
        release_pressure=min(1.,max(0.,
            (dn/self.lengths[i+1]-fd[i+1]['rho_crit'])/(jam-fd[i+1]['rho_crit']),ds/dn if dn else 0.))
        alpha,beta=a*pressure,b*(1-release_pressure)
'''
    assert sources['RouteLaneRegion'].count(before)==1
    candidate['RouteLaneRegion']=sources['RouteLaneRegion'].replace(before,after)
    protocol=copy.deepcopy(h.read(OLD/'protocol.json'))
    protocol.update(hypothesis='210 saved-state audit: own pressure dominates cell20 release inhibition. Disable only own-density contribution to restart; test endogenous response without adding fitted rates.',
        fit='None: old181 rates fixed; exact209 kinetics retained.',
        equation='alpha=a*max(own_excess,down_excess,down_slow); beta=b*(1-max(down_excess,down_slow)); both pressures clipped0..1.',
        train='Four saved29late450 states, not new likelihood fitting.',
        validation='Only if original baseline train gates pass, run eight43/61/67. Previously inspected data, not blind.',
        budget=dict(parity450=1,train450=4,conditional_validation450=8,max450=13,fits=0,native=0,FZP=0),
        caveat210='Parameter-free ablation tests a feedback mechanism. It does not identify queue-front propagation or justify deploying the two-phase closure.',
        unchanged210=['All longitudinal/sideways transport, FD, merge, shared node, ramp storage and off-ramp dynamics.',
                      'Formation pressure, exact population/moment kinetics, both rate constants, VSL exposure.',
                      'Live197 immutable9000 and101production files.'])
    pins=h.read(OLD/'pins.json')
    for p in (OLD/'executed_function_sources.json',OLD/'spec.json',HERE/'completion.json'):
        pins[str(p)]=h.sha(p)
    for label,records,src in [('parity','parity',sources),('train','train',candidate),('validation','validation',candidate)]:
        folder=OUT/label;folder.mkdir(parents=True)
        for name,value in [('protocol.json',protocol),('pins.json',pins),
                           ('coefficients.json',h.read(OLD/'coefficients.json')),
                           ('spec.json',h.read(OLD/'spec.json')),
                           ('executed_function_sources.json',src),
                           ('setting.json',dict(manifest=str(h.R/'lane_state132/eval_01/manifest.json'),structure='queue',records=records))]:
            h.save(folder/name,value)
    h.save(OUT/'protocol.json',protocol)
    h.save(OUT/'unit.json',units(candidate['RouteLaneRegion']))


def units(source):
    node=next(n for n in ast.parse(source).body[0].body if isinstance(n,ast.FunctionDef) and n.name=='_phase_change')
    scope={'math':math};exec(textwrap.dedent(ast.get_source_segment(source,node)),scope)
    fn=scope['_phase_change'];rates=h.read(OLD/'coefficients.json')
    a,b=rates['formation_per_sec'],rates['release_per_sec'];mx=0.;rows=[]
    for n,s,dn,ds in [(36,30,0,0),(36,36,36,36),(10,0,10,0),(10,4,10,8),
                       (36,0,0,0),(10,10,0,0),(30,15,20,8),(10,3,36,0)]:
        cfg=NS(network=NS(freeway_segment_params={'FW_E':[dict(rho_crit=30.)]*3},rho_max=180.),
               simulation=NS(T_f_h=1/3600))
        obj=NS(road='FW_E',lengths=[.2]*3,phase_next={0:[[float(s),float(s),float((n-s)*30)]]},
            next={0:[{'all':n}]},phase0={0:[[s,s,(n-s)*30]],1:[[ds,ds,(dn-ds)*30]]},
            phase_start_n={0:[n],1:[dn]},phase_balance={0:[[0.]*6]},phase_events=[],spec178=rates)
        result,count=fn(obj,0,0,NS(time_sec=0),cfg)
        pp=max(0.,(n/.2-30)/150,(dn/.2-30)/150,ds/dn if dn else 0.)
        pd=max(0.,(dn/.2-30)/150,ds/dn if dn else 0.)
        alpha,beta=a*min(1.,pp),b*(1-min(1.,pd))
        y=np.array([s,s,(n-s)*30.],float);dt=.001
        def rhs(x):return np.array([alpha*(n-x[0])-beta*x[0],-beta*x[1],-alpha*x[2]+beta*x[1]])
        for _ in range(1000):
            k1=rhs(y);k2=rhs(y+dt*k1/2);k3=rhs(y+dt*k2/2);k4=rhs(y+dt*k3)
            y+=dt*(k1+2*k2+2*k3+k4)/6
        mx=max(mx,float(max(abs(y-result))))
        assert count==n and 0<=result[0]<=n and min(result)>=0
        rows.append(dict(n=n,s=s,down_n=dn,down_s=ds,pressure=pp,release_pressure=pd,result=result))
    assert mx<1e-8
    return dict(actual_method_RK4_fixtures=len(rows),maximum_error=mx,fixtures=rows)


def assess(label):
    rows=h.read(OUT/label/'forecast/rows.json')
    references=h.read(h.R/'phase_equilibrium181/forecast/rows.json')
    references=[r for r in references if r['mode']=='baseline' and (r['case']=='s29_late')==(label=='train')]
    scores={};gates={}
    for horizon in (150,450):
        base=h.losses([r for r in references if r['horizon']==horizon],(1,1,1,1))
        new=h.losses([r for r in rows if r['horizon']==horizon],(1,1,1,1))
        scores[str(horizon)]=dict(baseline=base,ablation=new)
        gates[str(horizon)]=dict(signs=all(p['sign_correct'] for p in new['pairs'] if p['meaningful']),
                                 response=new['response']<=.9*base['response'],
                                 absolute=new['absolute']<=1.1*base['absolute'])
    result=dict(scores=scores,gates=gates,passed450=all(gates['450'].values()))
    h.save(OUT/label/'assessment.json',result)
    return result


def run():
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    from diagnostics.repin_v3c3_review_20261001.state_lateral168.run import queue178
    start=time.perf_counter();assert not (OUT/'completion.json').exists()
    queue178(calibration183=OUT/'parity')
    p='forecast/queue/s29_late_hold.json.gz'
    lhs,rhs=h.read(OUT/'parity'/p),h.read(OLD/p)
    assert all(lhs[k]==rhs[k] for k in ('cells','flows','ports','ramps'))
    queue178(calibration183=OUT/'train')
    result=assess('train');validation=False
    if result['passed450']:
        queue178(calibration183=OUT/'validation');assess('validation');validation=True
    else:
        h.save(OUT/'validation/not_run.json',dict(status='SKIPPED_TRAINING_MACRO_GATE_FAILED'))
    core=h.read(HERE/'protocol.json')['source_sha256'];stop=h.read(HERE/'protocol.json')['STOP']
    assert all(h.sha(h.ROOT/p)==v for p,v in core.items()) and h.sha(stop['path'])==stop['sha256']
    completion=dict(status='COMPLETE_ABLATION',forecasts=13 if validation else 5,fits=0,
        training_pass=result['passed450'],validation_run=validation,production_adopted=False,
        parity_four_tables_exact=True,core_preserved=len(core),old_STOP_preserved=True,
        elapsed_s=time.perf_counter()-start,goal='ACTIVE_NOT_QUALIFIED')
    h.save(OUT/'completion.json',completion)
    print(json.dumps(completion))
    print(json.dumps(result))


if __name__=='__main__':
    import sys
    if '--prepare' in sys.argv:prepare()
    else:run()
