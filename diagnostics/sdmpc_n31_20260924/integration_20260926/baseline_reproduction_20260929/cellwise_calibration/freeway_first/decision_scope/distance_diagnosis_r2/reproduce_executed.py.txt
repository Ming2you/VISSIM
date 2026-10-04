import json,itertools
from pathlib import Path


def distance_diagnosis():
    """Read saved forecasts only; never changes the controller objective."""
    import csv,gzip,hashlib,math,sys
    cw=Path('diagnostics/sdmpc_n31_20260924/integration_20260926/baseline_reproduction_20260929/cellwise_calibration')
    out=cw/'freeway_first/decision_scope/distance_diagnosis_r2'
    out.mkdir(exist_ok=False)
    pins={}
    def raw(p):
        p=Path(p);b=p.read_bytes();pins[str(p.resolve())]=hashlib.sha256(b).hexdigest();return b
    def load(p):
        p=Path(p);b=raw(p)
        return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b.decode('utf-8-sig'))
    def save(name,value):
        (out/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    # Fixed illustrative weights: no fitting or selection after inspecting results.
    betas=[0.,1/220,1/110]
    save('protocol.json',dict(betas_h_per_km=betas,reference_speed_kmh=110,
        scope='East31 mainline only. 30s trapezoid of snapshot N*v; distance proxy, not exact FZP distance or whole Omega.',
        no_new_forecasts=True,no_objective_change=True,no_terminal_cost_implemented=True,
        decision_criterion='Actual mainline TTT of the candidate selected by predicted TTT-beta*D; report regret, no adoption.',
        seed29_training=True,seeds43_53_previously_inspected_checks=True))
    selected=load(cw/'expanded_joint/selection.json')
    assert selected['selected_index']==36
    oldrows=selected['selected']['rows']+load(cw/'expanded_joint/summary.json')['checks']+load(cw/'freeway_first/expanded_seed53/summary.json')['versions']['expanded']['rows']
    additional=load(cw/'additional_admission_s53.json')
    records=load(cw/'data_catalog.json')['checked_records']+additional['records']
    historical_pins=load(cw/'expanded_joint/final_source_pins.json')|additional['pins']
    cases=('s29_early','s29_late','s43_early','s53_late')
    rows=[];initial={};parity_max=0.
    try:
        for case in cases:
            for rec in [r for r in records if r['case']==case]:
                arm=rec['arm'];t0=rec['cutoff'];times=[round(t0+d,6) for d in range(0,451,30)]
                folder=cw/'expanded_joint'/('selected_predictions' if case.startswith('s29') else 'checks')
                predpath=(cw/'freeway_first/expanded_seed53/expanded'/(arm+'_prediction.json.gz') if case=='s53_late' else folder/(case+'_'+arm+'.json.gz'))
                pred=load(predpath);truth=Path(rec['truth']);manifest=load(truth/'manifest.json')
                obsbytes=raw(truth/'cells_30s.csv')
                csvpath=str((truth/'cells_30s.csv').resolve())
                assert hashlib.sha256(obsbytes).hexdigest()==historical_pins[csvpath]
                if 'files' in manifest:
                    assert hashlib.sha256(obsbytes).hexdigest()==manifest['files']['cells_30s.csv']
                obs={};forecast={}
                for row in csv.DictReader(obsbytes.decode('utf-8-sig').splitlines()):
                    t=round(float(row['time_s']),6)
                    if row['road']!='FW_E' or t not in times:continue
                    key=(t,int(row['cell']));assert key not in obs
                    n=float(row['n_veh']);v=float(row['v_kmh']) if row['v_kmh'] else None
                    assert n>=0 and (n==0 or (v is not None and math.isfinite(v) and v>=0))
                    obs[key]=(n,v or 0.)
                for row in pred['cells']:
                    if row['road']!='FW_E':continue
                    key=(round(float(row['time_s']),6),int(row['cell']));assert key not in forecast
                    forecast[key]=(row['n_veh'],row['v_kmh'])
                start=[obs[t0,c] for c in range(31)]
                if case in initial:assert initial[case]==start
                else:initial[case]=start
                for c in range(31):forecast[t0,c]=obs[t0,c]
                required={(t,c) for t in times for c in range(31)}
                assert set(obs)==set(forecast)==required
                old=next(r for r in oldrows if r['case']==case and r['arm']==arm)
                result=dict(case=case,arm=arm,cutoff=t0)
                for label,data in [('actual',obs),('predicted',forecast)]:
                    n={t:math.fsum(data[t,c][0] for c in range(31)) for t in times}
                    nv={t:math.fsum(data[t,c][0]*data[t,c][1] for c in range(31)) for t in times}
                    integrate=lambda x:math.fsum((x[a]+x[b])*(b-a)/7200 for a,b in zip(times,times[1:]))
                    ttt=integrate(n);error=abs(ttt-old[label]['mainline_ttt']);parity_max=max(parity_max,error)
                    assert error<1e-8
                    result[label]=dict(ttt_veh_h=ttt,distance_proxy_veh_km=integrate(nv),end_mainline_n=n[times[-1]],
                        end_component_n=old[label]['end_n'],component_ttt_veh_h=old[label]['ttt'])
                rows.append(result)
        comparisons=[]
        for case in cases:
            rr=[r for r in rows if r['case']==case];assert len(rr)==4
            best=min(rr,key=lambda r:r['actual']['ttt_veh_h'])
            trials=[]
            for beta in betas:
                score=lambda r,label:r[label]['ttt_veh_h']-beta*r[label]['distance_proxy_veh_km']
                choice=min(rr,key=lambda r:score(r,'predicted'))
                trials.append(dict(beta=beta,predicted_choice=choice['arm'],actual_ttt_best=best['arm'],
                    actual_ttt_regret=choice['actual']['ttt_veh_h']-best['actual']['ttt_veh_h'],
                    actual_mixed_score_best=min(rr,key=lambda r:score(r,'actual'))['arm']))
            pairs=[]
            for a,b in itertools.combinations(rr,2):
                deltas={label:{key:b[label][key]-a[label][key] for key in a[label]} for label in ('actual','predicted')}
                ad=deltas['actual']['distance_proxy_veh_km'];pd=deltas['predicted']['distance_proxy_veh_km']
                pairs.append(dict(base=a['arm'],arm=b['arm'],deltas=deltas,distance_direction_correct=ad*pd>0))
            comparisons.append(dict(case=case,trials=trials,pairs=pairs))
        assert len(rows)==16
        for path,digest in pins.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
        save('summary.json',dict(rows=rows,comparisons=comparisons,ttt_parity_max_abs=parity_max,
            source_pins=pins,initial_states_exact=True,new_forecasts=0,new_native=0,new_fzp_reads=0,
            objective_changed=False,terminal_cost_validated=False,whole_omega_validated=False,adopted=False))
        print(json.dumps(dict(ttt_parity_max=parity_max,cases=[dict(case=c['case'],trials=c['trials']) for c in comparisons])))
    except Exception as exc:
        save('failure.json',dict(error=repr(exc),completed_rows=len(rows),source_pins=pins))
        raise


def horizon_diagnosis():
    """Reuse unmodified expanded036 750s trajectories, with exact450s prefixes."""
    import gzip,hashlib,math
    cw=Path('diagnostics/sdmpc_n31_20260924/integration_20260926/baseline_reproduction_20260929/cellwise_calibration')
    out=cw/'freeway_first/decision_scope/distance_diagnosis_r2'
    target=out/'horizon.json';assert not target.exists()
    pins={}
    def load(p):
        b=p.read_bytes();pins[str(p.resolve())]=hashlib.sha256(b).hexdigest()
        return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b.decode('utf-8-sig'))
    earlier=load(out/'summary.json');rows=[]
    for case in ('s29_early','s43_early'):
        pairs={}
        for arm in ('none','vsl'):
            short=next(r for r in earlier['rows'] if r['case']==case and r['arm']==arm)
            stem=cw/'freeway_first/inlet_speed_boundary'/('base_'+case+'_'+arm)
            long=load(stem.with_suffix('.json'));pred=load(stem.with_suffix('.json.gz'))
            original=load(cw/'expanded_joint'/('selected_predictions' if case=='s29_early' else 'checks')/(case+'_'+arm+'.json.gz'))
            end=short['cutoff']+450
            for key,timekey in [('cells','time_s'),('flows','window_end_s'),('ramps','end_sec'),('ports','time_s')]:
                assert [r for r in pred[key] if r[timekey]<=end+1e-6]==original[key],(case,arm,key)
            assert long['horizon']==750 and long['candidate']=='base' and long['changed_speed_equations']==0
            pairs[arm]={label:dict(ttt450=short[label]['ttt_veh_h'],ttt750=long[label]['mainline_ttt'],
                component450=short[label]['component_ttt_veh_h'],component750=long[label]['ttt']) for label in ('actual','predicted')}
        deltas={label:{key:pairs['vsl'][label][key]-pairs['none'][label][key] for key in pairs['none'][label]} for label in ('actual','predicted')}
        for label in deltas:
            deltas[label]['additional300_ttt']=deltas[label]['ttt750']-deltas[label]['ttt450']
            deltas[label]['additional300_component']=deltas[label]['component750']-deltas[label]['component450']
        rows.append(dict(case=case,delta_vsl_minus_none=deltas,levels=pairs))
    for p,h in pins.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
    result=dict(rows=rows,source_pins=pins,prefix450_cells_flows_ports_ramps_exact=True,
        new_forecasts=0,new_native=0,whole_omega=False,terminal_cost_implemented=False,
        continuation='Existing750s fixed-command continuations; VSL and NC each retain their own command. Horizon diagnosis, not fitted terminal value or common post450 control.',
        scope='East31 mainline plus four on/four off connectors as component diagnostic; urban queues excluded.')
    target.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(rows))


if __name__=='__main__':
    import sys
    if '--distance-diagnosis' in sys.argv:
        distance_diagnosis()
        sys.exit(0)
    if '--horizon-diagnosis' in sys.argv:
        horizon_diagnosis()
        sys.exit(0)

cw=Path('diagnostics/sdmpc_n31_20260924/integration_20260926/baseline_reproduction_20260929/cellwise_calibration')
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
rows=load(cw/'expanded_joint/selection.json')['selected']['rows']+load(cw/'expanded_joint/summary.json')['checks']+load(cw/'freeway_first/expanded_seed53/summary.json')['versions']['expanded']['rows']
summary=[]
for case in sorted({r['case'] for r in rows}):
 rr=[r for r in rows if r['case']==case]
 if len(rr)<2:continue
 scope='mainline_ttt'
 obs=min(rr,key=lambda r:r['actual'][scope]); pred=min(rr,key=lambda r:r['predicted'][scope])
 pairs=[]
 for a,b in itertools.combinations(rr,2):
  ad=b['actual'][scope]-a['actual'][scope];pd=b['predicted'][scope]-a['predicted'][scope]
  pairs.append(dict(base=a['arm'],arm=b['arm'],actual=ad,predicted=pd,meaningful=abs(ad)>=.5,same_sign=ad*pd>0))
 summary.append(dict(case=case,actual_best=obs['arm'],predicted_best=pred['arm'],actual_regret=pred['actual'][scope]-obs['actual'][scope],
     actual_main={r['arm']:r['actual'][scope] for r in rr},predicted_main={r['arm']:r['predicted'][scope] for r in rr},pairs=pairs))

import hashlib
out=cw/'freeway_first/decision_scope';out.mkdir(exist_ok=False)
files=[cw/'expanded_joint/selection.json',cw/'expanded_joint/summary.json',cw/'freeway_first/expanded_seed53/summary.json']
pairs=[p for case in summary for p in case['pairs']]
metrics=dict(cases=4,pairs=24,meaningful_pairs=sum(p['meaningful'] for p in pairs),meaningful_sign_correct=sum(p['meaningful'] and p['same_sign'] for p in pairs),
 exact_best=sum(c['actual_best']==c['predicted_best'] for c in summary),maximum_actual_regret=max(c['actual_regret'] for c in summary))
result=dict(cases=summary,metrics=metrics,source_pins={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
  model='expanded_joint/eval_036',threshold_veh_h=.5,threshold_origin='existing cellwise protocol, not chosen after this comparison',
  previously_inspected_checks=True,train_cases=['s29_early','s29_late'],check_cases=['s43_early','s53_late'],
  scope='East31 mainline TTT only, four fixed candidates per common initial state; no independent confidence interval or global optimization claim.',
  adoption=False,new_rollouts=0,goal_qualified=False)
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps(metrics))
