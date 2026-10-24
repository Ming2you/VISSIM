"""One bounded joint identification, using the existing component runner."""
import ast
import copy
import itertools
import math
import time
from pathlib import Path
import numpy as np
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h
from diagnostics.repin_v3c3_review_20261001.state_lateral168.run import queue178

HERE=Path(__file__).resolve().parent


def residual(rows):
    groups=[[],[],[]]
    for row in rows:
        a,p=row['actual'],row['predicted']
        groups[0] += [(p[k]-a[k])/s for k,s in [('ttt',5.),('ramp_ttt',1.),('off_ttt',1.),('end_n',40.),('exits',30.)]]
        groups[0] += [(p['merges'][r]-a['merges'][r])/20 for r in sorted(a['merges'])]
        groups[1] += [row['local_rmse'][k]/s for k,s in [('n',8.),('v',20.),('q',800.)]]
    for case in sorted({r['case'] for r in rows}):
        by={r['arm']:r for r in rows if r['case']==case}
        for aa,bb in itertools.combinations(sorted(by),2):
            a,b=by[aa],by[bb]
            for k,s in [('ttt',.5),('ramp_ttt',.5),('end_n',15.),('exits',15.)]:
                real=b['actual'][k]-a['actual'][k]
                groups[2].append((b['predicted'][k]-a['predicted'][k]-real)/max(s,abs(real)))
            for r in sorted(a['actual']['merges']):
                real=b['actual']['merges'][r]-a['actual']['merges'][r]
                groups[2].append((b['predicted']['merges'][r]-a['predicted']['merges'][r]-real)/max(10.,abs(real)))
    vec=np.array([v*math.sqrt(w/len(g)) for w,g in zip((1.,.25,2.),groups) for v in g])
    # All cases used here have either4 or2 arms. Training4 is the fit contract.
    if len({r['case'] for r in rows})==1:
        assert abs(float(vec@vec)-h.losses(rows,[])['objective'])<1e-10
    return vec


def source_for_probe():
    source=copy.deepcopy(h.read(h.R/'merge_priority189/executed_function_sources.json'))
    cls=source['RouteLaneRegion']
    old='        self.priority_rows = []'
    assert cls.count(old)==1
    cls=cls.replace(old,old+"\n        self.shared_flux_fraction = float(spec.get('shared_flux_fraction203',1.))\n        if not 0. <= self.shared_flux_fraction <= 1.:raise ValueError('203 fraction')")
    old='                velocity = min(velocity,(self.outgoing[i][g]+sent)*self.lengths[i]/(dt*n))'
    assert cls.count(old)==1
    cls=cls.replace(old,'''                cap = (self.outgoing[i][g]+sent)*self.lengths[i]/(dt*n)
                weight = 1.
                if i == 20 and g == 0:
                    node = self.junction_rows[-1]
                    assert abs(node['time_s']-state.time_sec)<1e-6
                    # Genuine exit-storage restriction retains the old cap.
                    if node['off_before_veh'] >= node['off_request_veh']-1e-9:
                        weight = self.shared_flux_fraction
                # weight1 executes the exact old operation, including rounding.
                if weight == 1.:velocity = min(velocity,cap)
                else:velocity = velocity-weight*max(0.,velocity-cap)''')
    ast.parse(cls);source['RouteLaneRegion']=cls
    before=ast.parse(h.read(h.R/'merge_priority189/executed_function_sources.json')['RouteLaneRegion']).body[0]
    after=ast.parse(cls).body[0]
    by=lambda c:{n.name:ast.dump(n) for n in c.body if isinstance(n,ast.FunctionDef)}
    a,b=by(before),by(after)
    assert all(v==b[k] for k,v in a.items() if k not in ('__init__','speed'))
    return source


def main():
    assert not (HERE/'protocol.json').exists(),'No automatic restart or overwrite'
    started=time.perf_counter();forecasts=0;evaluations=[]
    proto=copy.deepcopy(h.read(h.R/'merge_priority189/protocol.json'))
    proto.update(previous_goal_turn='PROGRESS202 exact prefix and per-lane attribution',
        hypothesis='Jointly identify the ramp/mainline allocation and instantaneous lane-mean flux feedback; each standalone change previously failed.',
        parameters=['10490 ramp priority p','20lane1 shared-flow speed loss fraction alpha'],
        fixed='Exact148 geometry/132 coefficients/171 ramp admission; all physical flow/storage/queue limits and VSL histories unchanged. Genuine exit storage keeps full speed feedback.',
        train='29late four arms only; known historical data, not pristine blind',
        validation='Freeze then67late four,43early two,61late two; no refit from validation',
        budget=dict(parity450=1,train450=24,validation450_max=8,total450_max=33,fit_steps=1,native=0,FZP=0),
        bounds=dict(center=[.75,.5],central_difference=.2,step_box=[-.25,.25],physical_p=[.25,1.],physical_alpha=[0.,1.]),
        method='Center plus4 central-difference vectors,one regularized box-constrained joint step. No second Jacobian, no bounds expansion or retry. Choose among these6 fixed train evaluations.',
        gates='Train objective5%better,response notworse,all meaningful pair signs. Validation response10%better,absolute<=110%,meaningful signs,regret<=.5vehh.',
        scope='East31cells+4on/4off, not wholeOmega qualification.',
        interpretation='alpha is an empirical partial lane-mean response to shared downstream restriction; not an estimated reaction time or a capacity bonus.',
        no_future_observation_inputs=True,production_adopted=False)
    source=source_for_probe();h.save(HERE/'executed_function_sources.json',source)
    pins={str(p):h.sha(p) for p in (Path(__file__),h.R/'state_lateral168/run.py',h.R/'merge_priority189/executed_function_sources.json',h.R/'queue_dynamics178/forecast/rows.json')}
    h.save(HERE/'protocol.json',proto);h.save(HERE/'pins.json',pins)
    fixed=[r for r in h.read(h.R/'queue_dynamics178/forecast/rows.json') if r['horizon']==450 and r['mode']=='baseline']
    training=[r for r in fixed if r['case']=='s29_late'];assert len(training)==4
    fixed_loss=h.losses(training,[])
    # Formula endpoints and range. This verifies the closure, not traffic gain.
    checks=0
    for v,cap,w in itertools.product((0.,5.,40.,100.),(0.,5.,30.,110.),(0.,.3,1.)):
        result=v-w*max(0.,v-cap)
        assert min(v,cap)-1e-12<=result<=v+1e-12
        if w==0:assert result==v
        if w==1:assert abs(result-min(v,cap))<1e-12
        checks+=1
    h.save(HERE/'preflight.json',dict(speed_convex_checks=checks,unrelated_class_methods_preserved=True))

    def evaluate(z,tag,scope='train'):
        nonlocal forecasts
        p,alpha=map(float,z);assert .25<=p<=1. and 0<=alpha<=1.
        folder=HERE/tag;folder.mkdir()
        spec=h.read(h.R/'merge_priority189/spec.json')
        spec.update(merge_priority189={'RM_C10490':p},shared_flux_fraction203=alpha)
        for name,value in [('spec.json',spec),('coefficients.json',dict(p=p,alpha=alpha)),('protocol.json',proto),
                           ('pins.json',pins),('executed_function_sources.json',source),
                           ('setting.json',dict(manifest=str(h.R/'lane_state132/eval_01/manifest.json'),structure='priority',records=scope))]:h.save(folder/name,value)
        expected=1 if scope=='parity' else 4 if scope=='train' else 8
        assert forecasts+expected<=33
        queue178(calibration203=folder);forecasts+=expected
        rows=[r for r in h.read(folder/'forecast/rows.json') if r['horizon']==450]
        if scope=='parity':
            rec=rows[0];key=rec['case']+'_'+rec['arm']+'.json.gz'
            pred=h.read(folder/'forecast/priority'/key);old=h.read(h.R/'queue_dynamics178/forecast/baseline'/key)
            parity={k:pred[k]==old[k] for k in ('cells','flows','ports','ramps')}
            h.save(HERE/'parity.json',parity);assert all(parity.values())
        value=dict(z=list(z),tag=tag,scope=scope,rows=rows,loss=h.losses(rows,[]))
        evaluations.append(value);h.save(HERE/'evaluations.json',evaluations)
        h.save(HERE/'status.json',dict(status='running',tag=tag,forecasts=forecasts))
        print('JOINT203',tag,value['loss']['objective'],value['loss']['response'],flush=True)
        return value

    try:
        evaluate([1.,1.],'parity','parity')
        center=np.array([.75,.5]);base=evaluate(center.tolist(),'center');r0=residual(base['rows']);columns=[]
        for axis in range(2):
            high=center.copy();low=center.copy();high[axis]+=.2;low[axis]-=.2
            a=evaluate(high.tolist(),f'axis{axis}_plus');b=evaluate(low.tolist(),f'axis{axis}_minus')
            columns.append((residual(a['rows'])-residual(b['rows']))/.4)
        J=np.column_stack(columns);ridge=.1
        A=J.T@J+ridge*np.eye(2);b=-J.T@r0;options=[]
        for codes in itertools.product((-1,0,1),repeat=2):
            x=np.array(codes,dtype=float)*.25;free=[i for i,c in enumerate(codes) if not c];bound=[i for i,c in enumerate(codes) if c]
            if free:x[free]=np.linalg.solve(A[np.ix_(free,free)],b[free]-A[np.ix_(free,bound)]@x[bound])
            if max(abs(x))<=.25+1e-10:options.append((float(np.linalg.norm(r0+J@x)**2+ridge*(x@x)),x))
        _,step=min(options,key=lambda z:z[0]);gradient=A@step-b
        assert all((abs(step[i])<.25-1e-8 and abs(gradient[i])<1e-7) or (step[i]<=-.25+1e-8 and gradient[i]>=-1e-7) or (step[i]>=.25-1e-8 and gradient[i]<=1e-7) for i in range(2))
        h.save(HERE/'linear_step.json',dict(J=J.tolist(),r0=r0.tolist(),step=step.tolist(),gradient=gradient.tolist(),ridge=ridge))
        proposal=np.clip(center+step,[.25,0.],[1.,1.]);evaluate(proposal.tolist(),'joint_step')
        choices=[v for v in evaluations if v['scope']=='train' and v['loss']['objective']<=.95*fixed_loss['objective'] and v['loss']['response']<=fixed_loss['response'] and all(p['sign_correct'] for p in v['loss']['pairs'] if p['meaningful'])]
        best=min(choices,key=lambda v:v['loss']['objective']) if choices else None
        h.save(HERE/'selection_frozen.json',dict(train_passed=bool(best),selected_z=best['z'] if best else None,selected_tag=best['tag'] if best else None,fixed_loss=fixed_loss))
        validation=None
        if best:
            trial=evaluate(best['z'],'validation','validation');rows=trial['rows']
            old=h.losses([r for r in fixed if r['case']!='s29_late'],[]);loss=trial['loss'];regrets=[]
            for case in sorted({r['case'] for r in rows}):
                rs=[r for r in rows if r['case']==case];chosen=min(rs,key=lambda r:r['predicted']['ttt'])
                regrets.append(dict(case=case,selected=chosen['arm'],regret=chosen['actual']['ttt']-min(r['actual']['ttt'] for r in rs)))
            gates=dict(response=loss['response']<=.9*old['response'],absolute=loss['absolute']<=1.1*old['absolute'],signs=all(p['sign_correct'] for p in loss['pairs'] if p['meaningful']),regret=all(v['regret']<=.5 for v in regrets))
            validation=dict(gates=gates,passed=all(gates.values()),fixed_loss=old,loss=loss,regrets=regrets)
        h.save(HERE/'validation.json',validation)
        h.save(HERE/'completion.json',dict(status='complete',forecasts450=forecasts,seconds=time.perf_counter()-started,train_passed=bool(best),validation_passed=bool(validation and validation['passed']),production_adopted=False,full_goal='ACTIVE_NOT_QUALIFIED',native=0,FZP_reads=0,optimizer_iterations=0,fit_steps=1))
        h.save(HERE/'status.json',dict(status='complete',forecasts=forecasts))
    except BaseException as e:
        h.save(HERE/'status.json',dict(status='failed',forecasts=forecasts,error=repr(e)));raise
    finally:
        for p,d in {**pins,**proto['protected_sha256'],proto['STOP']['path']:proto['STOP']['sha256']}.items():assert h.sha(p)==d,p
        h.save(HERE/'preservation.json',dict(input_sha256=pins,protected_and_STOP=True))


if __name__=='__main__':main()
