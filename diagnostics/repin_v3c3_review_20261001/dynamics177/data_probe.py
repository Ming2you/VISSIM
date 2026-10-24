"""Finite feature-sufficiency screen, not a conservative traffic simulator.

Current/past native state -> next30s exit flow and lane1 stopped stock.
No policy, seed or future observations are predictor features. No FZP reads.
"""
import csv
import gzip
import hashlib
import json
import time
from pathlib import Path

import numpy as np

HERE=Path(__file__).resolve().parent
R=HERE.parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
F=I/'baseline_reproduction_20260929/cellwise_calibration/freeway_first'
CASE=I/'heldout67_freeway_20260930'
ARMS=['hold','release','hold_vsl90','release_vsl90']
PINS={}
MODELS={
    'aggregate':['demand_all30','dn_density_all','dn_speed_all'],
    'lane':['demand_lane30','dn_density_lane1','dn_speed_lane1'],
    'queue':['demand_lane30','dn_density_lane1','dn_speed_lane1','stopped','dn_stopped'],
    'front':['demand_lane30','dn_density_lane1','dn_speed_lane1','stopped','dn_stopped','ready_exit50'],
    'merge_history':['demand_lane30','dn_density_lane1','dn_speed_lane1','stopped','dn_stopped','merge10490_past30','merge10484_past30'],
    'lateral_history':['demand_lane30','dn_density_lane1','dn_speed_lane1','stopped','dn_stopped','lc_past30','net_lane1_past30'],
}


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    PINS[str(p)]=sha(p)
    with (gzip.open(p,'rt',encoding='utf8') if p.suffix=='.gz' else p.open(encoding='utf-8-sig')) as f:return json.load(f)


def rows(p):
    PINS[str(p)]=sha(p)
    with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))


def save(name,d):
    (HERE/name).write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def mean(v):return sum(v)/len(v) if v else 0.


def fit_predict(train,test,features,target):
    x=np.asarray([[r['x'][k] for k in features] for r in train],dtype=float)
    z=np.asarray([[r['x'][k] for k in features] for r in test],dtype=float)
    center=x.mean(0);scale=x.std(0);scale[scale<1e-9]=1.
    x=(x-center)/scale;z=(z-center)/scale
    y=np.asarray([r['y'][target]-(r['x']['stopped'] if target=='stop_next30' else 0.) for r in train])
    intercept=float(y.mean())
    # A single predeclared ridge strength; no hyperparameter/feature search.
    coef=np.linalg.solve(x.T@x+np.eye(len(features)),x.T@(y-intercept))
    p=intercept+z@coef
    if target=='stop_next30':p+=np.asarray([r['x']['stopped'] for r in test])
    p=np.maximum(0.,p)
    return p.tolist(),dict(features=features,center=center.tolist(),scale=scale.tolist(),
                           standardized_coef=coef.tolist(),intercept=intercept,ridge=1.)


def main():
    assert not (HERE/'results.json').exists()
    started=time.perf_counter()
    parent=read(R/'blocking176/summary.json')
    verification=read(R/'blocking176/verification.json');assert verification['completed']
    geometry=read(F/'route_inventory/mapping31.json')['freeway_model_links']['FW_E']
    bounds=geometry['segment_bounds_m'];L=bounds[21]-bounds[20];Ld=bounds[22]-bounds[21]
    PINS[str(Path(__file__))]=sha(__file__)
    protocol=dict(question='Do lane/queue/spatial/past-merge states predict next30s off10483 discharge and stopped-lane state beyond scalar averages?',
        features=MODELS,primary_cell=20,receiving_cell=21,window=[2700.1,3120.1],step_s=30,
        targets=['exit_next30','stop_next30'],fit_budget=60,ridge=1.,
        folds=['leave-one-policy-out4folds','train2700..2880,one30s embargo,test2940..3090'],
        caveats=['Same seed/common initial state;policy folds are not independent-seed validation.',
          'Observed-state one-step regression only;no conserved autonomous rollout or MPC/gain qualification.',
          'No seed/time/policy command/future state in features. Past arrivals/merges are observed,not forecast interventions.',
          'No parameter or feature search after outcomes;do not interpret fitted regression coefficients as physical causal coefficients.'],
        native_runs=0,FZP_reads=0,plant_predictions=0,production_edits=0)
    save('protocol.json',protocol)
    data=[];transition_summary=[];checks=0
    for arm in ARMS:
        d=read(R/f'blocking176/{arm}_frames.json.gz')
        assert d['fields'][:4]==['cell','speed','x','lane']
        fr={float(t):v for t,v in d['frames'].items()}
        fl=rows(CASE/f'observations/{arm}/flows_30s.csv')
        port=rows(CASE/f'observations/{arm}/ports_30s.csv')
        events=rows(CASE/f'observations/{arm}/port_events.csv')
        for j in range(14):
            t=round(2700.1+30*j,6);tn=round(t+30,6)
            own=[v for v in fr[t].values() if v[0]==20]
            lane=[v for v in own if v[3]==1]
            dn=[v for v in fr[t].values() if v[0]==21]
            dnl=[v for v in dn if v[3]==1]
            ex=[v for v in lane if v[7]=='10483']
            stop=sum(v[1]<5 for v in lane)
            lc=net=0
            for k in range(6):
                ta=round(t-30+5*k,6);tb=round(ta+5,6)
                a,b=fr[ta],fr[tb]
                for vid in a.keys()&b.keys():
                    av,bv=a[vid],b[vid]
                    if av[0]!=bv[0] or not 19<=av[0]<=25 or av[4]!=bv[4]:continue
                    if av[3]!=bv[3]:
                        lc+=1;net+=int(bv[3]==1)-int(av[3]==1)
            pastmerge={cid:sum(e['connector']==cid and e['kind']=='departure' and t-30<float(e['time_s'])<=t+1e-6 for e in events) for cid in ['10490','10484']}
            x=dict(demand_all30=len(ex)*mean([v[1] for v in own])*30/(3.6*L),
                demand_lane30=len(ex)*mean([v[1] for v in lane])*30/(3.6*L),
                dn_density_all=len(dn)/(3*Ld/1000),dn_speed_all=mean([v[1] for v in dn]),
                dn_density_lane1=len(dnl)/(Ld/1000),dn_speed_lane1=mean([v[1] for v in dnl]),
                stopped=stop,dn_stopped=sum(v[1]<5 for v in dnl),
                ready_exit50=sum(v[1]>=5 and bounds[21]-v[2]<=50 for v in ex),
                merge10490_past30=pastmerge['10490'],merge10484_past30=pastmerge['10484'],
                lc_past30=lc,net_lane1_past30=net)
            target=next(r for r in fl if r['road']=='FW_E' and int(r['cell'])==20 and abs(float(r['window_end_s'])-tn)<1e-6)
            porttarget=next(r for r in port if r['connector']=='10483' and abs(float(r['window_end_s'])-tn)<1e-6)
            yexit=float(target['off_departures'])
            assert yexit==float(porttarget['arrivals_veh'])
            assert yexit==sum(e['connector']=='10483' and e['kind']=='arrival' and t<float(e['time_s'])<=tn+1e-6 for e in events)
            yn=sum(v[0]==20 and v[3]==1 and v[1]<5 for v in fr[tn].values())
            # An exact label ledger distinguishes same-vehicle stop/start from turnover.
            a={vid:v for vid,v in fr[t].items() if v[0]==20 and v[3]==1}
            b={vid:v for vid,v in fr[tn].items() if v[0]==20 and v[3]==1}
            persist=a.keys()&b.keys()
            start=sum(a[i][1]>=5 and b[i][1]<5 for i in persist)
            recover=sum(a[i][1]<5 and b[i][1]>=5 for i in persist)
            entrant=sum(b[i][1]<5 for i in b.keys()-a.keys())
            leaver=sum(a[i][1]<5 for i in a.keys()-b.keys())
            assert yn-stop==start-recover+entrant-leaver
            transition_summary.append(dict(arm=arm,t=t,start_stopped=stop,end_stopped=yn,
                persistent_stop_onset=start,persistent_recovery=recover,stopped_entrants=entrant,stopped_leavers=leaver))
            data.append(dict(arm=arm,t=t,latest_feature_time=t,target_time=tn,x=x,
                y=dict(exit_next30=yexit,stop_next30=yn)))
            checks+=1
    save('data.json',data);save('stop_transitions.json',transition_summary)
    records=[];fits=[]
    for target in ['exit_next30','stop_next30']:
        for label,features in MODELS.items():
            for arm in ARMS:
                train=[r for r in data if r['arm']!=arm];test=[r for r in data if r['arm']==arm]
                assert len(train)==42 and len(test)==14
                predictions,fit=fit_predict(train,test,features,target)
                fits.append(dict(model=label,target=target,fold='policy_'+arm,**fit))
                records += [dict(model=label,target=target,fold='policy',heldout=arm,arm=r['arm'],t=r['t'],
                                 actual=r['y'][target],predicted=p) for r,p in zip(test,predictions)]
            train=[r for r in data if r['t']<=2880.1];test=[r for r in data if r['t']>=2940.1]
            assert len(train)==28 and len(test)==24
            assert max(r['target_time'] for r in train)<min(r['t'] for r in test)
            predictions,fit=fit_predict(train,test,features,target)
            fits.append(dict(model=label,target=target,fold='forward',**fit))
            records += [dict(model=label,target=target,fold='forward',arm=r['arm'],t=r['t'],actual=r['y'][target],predicted=p) for r,p in zip(test,predictions)]
    scores=[]
    for target in ['exit_next30','stop_next30']:
        for fold in ['policy','forward']:
            for label in MODELS:
                rs=[r for r in records if r['target']==target and r['fold']==fold and r['model']==label]
                e=np.asarray([r['predicted']-r['actual'] for r in rs])
                scores.append(dict(target=target,fold=fold,model=label,n=len(rs),mae=float(abs(e).mean()),rmse=float(np.sqrt((e*e).mean())),bias=float(e.mean())))
    # Common forward-fitted function applied to all four arms; never compare
    # policy-fold predictions fitted with different coefficient sets as causal deltas.
    responses=[]
    for label in MODELS:
        rs=[r for r in records if r['target']=='exit_next30' and r['fold']=='forward' and r['model']==label]
        for a,b in [('hold','release'),('hold_vsl90','release_vsl90'),('release_vsl90','release'),('hold_vsl90','hold')]:
            aa=[r for r in rs if r['arm']==a];bb=[r for r in rs if r['arm']==b]
            actual=sum(r['actual'] for r in aa)-sum(r['actual'] for r in bb)
            prediction=sum(r['predicted'] for r in aa)-sum(r['predicted'] for r in bb)
            responses.append(dict(model=label,a=a,b=b,window=[2940.1,3120.1],actual_difference=actual,
                prediction_difference=prediction,meaningful=abs(actual)>=10))
    baselines={}
    for target in ['exit_next30','stop_next30']:
        def p(r):return r['x']['demand_lane30'] if target=='exit_next30' else r['x']['stopped']
        baselines[target]={k:float(np.mean([abs(p(r)-r['y'][target]) for r in data if k=='all' or r['t']>=2940.1])) for k in ['all','forward']}
    for p,digest in {**PINS,**parent['protected_sha256'],parent['STOP']['path']:parent['STOP']['sha256']}.items():assert sha(p)==digest,p
    assert len(fits)==60 and len(records)==960
    save('predictions.json',records);save('fits.json',fits)
    save('results.json',dict(scores=scores,forward_responses=responses,physical_persistence_baselines=baselines,
        checks=dict(label_port_event_flow_equal=checks,stop_stock_identities=checks,current_past_features_only=True,
          raw_reads=0,model_rollouts=0,fit_count=len(fits),test_predictions=len(records),protected_and_STOP_preserved=True),
        input_sha256=PINS,elapsed_s=time.perf_counter()-started,adopted=False,
        interpretation='Conditional one-step diagnostic; no independent seed, no autonomous queue law, no TTT/gain qualification.'))
    for s in scores:print(s)
    print('BASELINES',baselines)
    print('RESPONSES',responses)


if __name__=='__main__':main()
