"""Current-state regime check and one bounded cell22 pressure proposal.

Reuses137 native-state ledgers and138 five1s operator checks. No traffic
rollout, future operational input, new observation extraction or native run.
"""
import math
from collections import defaultdict
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    assert not (HERE/'status.json').exists(), 'No automatic retry'
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    from evaluation.controllers import lane_plant_runtime as lpr
    context,_,_=common.setup()
    parent=h.R/'lane_state132/eval_01'
    cfg=lpr.load_sources(parent/'manifest.json')['component']._config('FW_E',context['parameters']['by_direction']['FW_E'])
    net=cfg.network;p=net.freeway_segment_params['FW_E'];critical=p[22]['rho_crit'];down_critical=p[23]['rho_crit']
    protected=h.read(h.R/'spatial_calibration145/protocol.json')
    paths=[Path(__file__),HERE/'helper_before.py.txt',h.R/'recovery_terms137/rows.json.gz',
           h.R/'temporal_response138/rows.json',parent/'manifest.json',parent/'reference_config.json',
           h.R/'spatial_speed144/audit_repair/executed_function_sources.json',
           h.R/'upstream_worklog/03_codex_review/REVIEW_CHECK.md']
    pins={str(x):h.sha(x) for x in paths}
    h.save(HERE/'protocol.json',dict(previous_goal_turn='NO_PROGRESS: explanation only.145 terminal failed candidate and absent owned python/Vissim process revalidated.',
        reason='137 uniform nu reduction improved state errors but damaged RM benefit.138 nominal-state five1s pressure error is largest when local22 is subcritical and downstream23 is congested.',
        scope='Current native-state conditional ODE check; current density and neighbors fixed for5s. Native following state is a label only. This is not a traffic rollout.',
        training='s67_late release nominal110 only; all3 lanes,30s blocks with>=4 paired5s samples. Previously inspected29 is an other-state check, not blind validation.',
        candidate='Scale only negative cell22 anticipation when rho22<=its effective critical and rho23>its own effective critical. All other states/terms unchanged; regime computed from current predicted state in subsequent rollout.',
        parameter='One multiplier z in[.1,1]. No threshold fitting, no time/control/seed-specific correction.',
        fit='One bounded golden-section minimization of30s block5s-endpoint-rate squared error plus .1*(z-1)^2; maximum32 shrink steps, include both endpoints.',
        critical=dict(local=critical,downstream=down_critical),
        budget=dict(local_fit=1,parity450=1,candidate450=8,independent450=0,new_native=0,new_FZP=0),
        autonomous_gate='Same144 meaningful signs, >=10% response improvement, absolute<=110%, actual regret<=.5vehh; additionally inspect middle150 off10483 and local recovery. No follow-up fit on failure.',
        limits='Current density-regime association does not prove causal driver behavior. Frozen-current ODE cannot replace a conservation forecast. Conditional fit may fail when self-generated states cross regimes.',
        prior_checked=['137 uniform nu rejected','139 speed-gap pressure bound rejected','145 four-coefficient joint fit rejected','Claude REVIEW_CHECK state_response/source binding warning; no matching corrected regime law identified'],
        preparation_note='Exploratory read initially omitted arm in lookup and raised KeyError before any fitting/forecast. Full case+arm+time+cell+lane key below is unique.',
        protected_sha256=protected['protected_sha256'],STOP=protected['STOP'],pins=pins))
    h.save(HERE/'status.json',dict(status='running',phase='cached_regimes'))
    raw=h.read(h.R/'recovery_terms137/rows.json.gz')
    lookup={(r['case'],r['arm'],r['time_s'],r['cell'],r['lane']):r for r in raw};assert len(lookup)==len(raw)
    prior=h.read(h.R/'temporal_response138/rows.json');rows=[];max_error=0.

    def probe(r,z):
        m=r['model'];v=r['v0'];result=[v]
        pressure=m['anticipation']*(z if r['active'] else 1.)
        for _ in range(5):
            v=max(net.v_min,v+(m['desired']-v)/m['tau_sec']
                  +v*(m['upstream_speed']-v)/(p[22]['segment_length_km']*3600)+pressure)
            result.append(v)
        return result

    for old in prior:
        if old['model']!='frozen132':continue
        r=lookup[old['case'],old['arm'],old['time_s'],22,old['lane']]
        m=r['model'];r=dict(r)
        r['regime']=('H' if m['rho']>critical else 'L')+('H' if m['downstream_rho']>down_critical else 'L')
        r['active']=m['downstream_rho']>m['rho'] and r['regime']=='LH'
        trajectory=probe(r,1.)
        max_error=max(max_error,max(abs(a-b) for a,b in zip(trajectory,old['trajectory'])))
        r['baseline_rate']=(trajectory[-1]-r['v0'])/5
        rows.append(r)
    assert max_error<1e-8 and len(rows)==535
    train=[r for r in rows if r['case']=='s67_late' and r['arm']=='release']
    blocks=defaultdict(list)
    for r in train:blocks[r['lane'],int(round((r['time_s']-2670.1)/5))//6].append(r)
    blocks={k:rr for k,rr in blocks.items() if len(rr)>=4}
    assert len(blocks)>=30 and sum(r['active'] for rr in blocks.values() for r in rr)>=40
    evals=[]

    def objective(z):
        errors=[sum((probe(r,z)[-1]-r['v0'])/5-r['observed_rate'] for r in rr)/len(rr) for rr in blocks.values()]
        score=sum(x*x for x in errors)/len(errors)+.1*(z-1.)**2
        evals.append(dict(z=z,score=score))
        return score

    lo,hi=.1,1.;ratio=(math.sqrt(5)-1)/2
    c=hi-ratio*(hi-lo);d=lo+ratio*(hi-lo);fc=objective(c);fd=objective(d)
    for _ in range(32):
        if fc<fd:hi,d,fd=d,c,fc;c=hi-ratio*(hi-lo);fc=objective(c)
        else:lo,c,fc=c,d,fd;d=lo+ratio*(hi-lo);fd=objective(d)
    objective(.1);objective(1.);chosen=min(evals,key=lambda x:x['score']);z=chosen['z']
    groups=defaultdict(list)
    for r in rows:
        r['candidate_rate']=(probe(r,z)[-1]-r['v0'])/5
        for regime in ('all',r['regime']):groups[r['case'],regime].append(r)
        if not r['active']:assert r['candidate_rate']==r['baseline_rate']
    summary=[]
    for (case,regime),rr in sorted(groups.items()):
        summary.append(dict(case=case,regime=regime,samples=len(rr),active=sum(r['active'] for r in rr),
            observed=sum(r['observed_rate'] for r in rr)/len(rr),baseline=sum(r['baseline_rate'] for r in rr)/len(rr),
            candidate=sum(r['candidate_rate'] for r in rr)/len(rr),
            rmse={key:math.sqrt(sum((r[key]-r['observed_rate'])**2 for r in rr)/len(rr)) for key in ('baseline_rate','candidate_rate')}))
    h.save(HERE/'summary.json',summary);h.save(HERE/'fit_evaluations.json',evals)
    h.save(HERE/'proposal.json',dict(z=z,original_nu_ge=20.130921987631222,
        corrected_nu_ge=20.130921987631222*z,critical=dict(local=critical,downstream=down_critical),
        fit=chosen,original=next(x for x in evals if x['z']==1.),blocks=len(blocks),samples=sum(map(len,blocks.values())),
        active_samples=sum(r['active'] for rr in blocks.values() for r in rr),parameter_evaluations=len(evals),input_sha256=pins))
    for path,digest in {**protected['protected_sha256'],**pins}.items():assert h.sha(path)==digest,path
    assert h.sha(protected['STOP']['path'])==protected['STOP']['sha256']
    h.save(HERE/'verification.json',dict(operator_samples=len(rows),baseline138_max_error=max_error,
        unique_join=True,unaffected_states_exact=True,protected=True,STOP=True))
    h.save(HERE/'status.json',dict(status='complete_conditional_proposal',new_forecasts=0,new_native=0,new_FZP=0,selected=z))
    print('PROPOSAL',z,'blocks',len(blocks),'fit',chosen['score'])
    for row in summary:
        if row['regime'] in ('all','LH','HH'):print(row)


if __name__=='__main__':main()
