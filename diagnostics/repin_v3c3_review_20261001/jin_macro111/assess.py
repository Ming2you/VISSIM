"""Evaluate the completed bounded trial; no forecasts or native file scans."""
import gzip
import json
from pathlib import Path
import sys
from run import HERE, ROOT, FILES, read, save, sha, setup, records, payload, losses


def main():
    status=read(HERE/'fit_status.json')
    reused=read(HERE/'reused_predictions.json') if (HERE/'reused_predictions.json').exists() else []
    assert status['status']=='complete_pending_assessment' and status['completed']+len(reused)==80
    context,replay,Obs=setup();model=context['component']
    protocol=read(HERE/'protocol.json');selection=read(HERE/'selection.json')
    rows=read(HERE/'validation.json')
    stats={v:losses([r for r in rows if r['version']==v],protocol) for v in ('baseline','selected')}
    horizon_rows=[];initial_checks=[];mass_errors=[]
    for training in (True,False):
        groups={}
        for r in records(training):
            args,kw=payload(replay,r,150 if training else 450)
            initial=dict(cells=args[0],origin=args[3],ports=kw['port_dynamics']['initial_cohorts'],
                         ramps=kw['ramp_dynamics']['ramps'],routes=kw['offramp_inventory']['raw'])
            # Ramp maps include initial stock/geometric metadata, no policies;
            # policies are in boundary_steps and intentionally differ.
            groups.setdefault(r['case'],[]).append(initial)
        for case,values in groups.items():
            initial_checks.append(dict(case=case,all_four_initial_states_identical=all(x==values[0] for x in values)))
    assert all(c['all_four_initial_states_identical'] for c in initial_checks)
    for version in ('baseline','selected'):
        for r in records(False):
            with gzip.open(HERE/(version+'_'+r['arm']+'.json.gz'),'rt',encoding='utf-8') as f:pred=json.load(f)
            truth=Obs(r['truth']);args,_=payload(replay,r,450)
            previous=sum(c['n_veh'] for c in args[0] if c['road']=='FW_E')
            for t in sorted({c['time_s'] for c in pred['cells']}):
                end=sum(c['n_veh'] for c in pred['cells'] if c['time_s']==t)
                flows=[f for f in pred['flows'] if f['window_end_s']==t]
                expected=previous+sum(f['source_admissions']+f['ramp_merges']-f['off_departures']-f['terminal_exits'] for f in flows)
                mass_errors.append(abs(end-expected));previous=end
            for horizon in (150,300,450):
                end=r['cutoff']+horizon
                cropped=dict(pred)
                for name,key in (('cells','time_s'),('flows','window_end_s'),('ports','time_s'),('ramps','end_sec')):
                    cropped[name]=[x for x in pred[name] if x[key]<=end+1e-6]
                row=replay._cellwise_measure(model,cropped,r,truth,horizon_sec=horizon)
                horizon_rows.append(dict(version=version,horizon_sec=horizon,**row))
    assert max(mass_errors)<1e-7
    sign_failures=[p for p in stats['selected']['pairs'] if abs(p['actual']['ttt'])>=.5 and p['actual']['ttt']*p['predicted']['ttt']<=0]
    gates=dict(training=selection['training_improvement']>=.05,
               validation_response=stats['selected']['response']<=.90*stats['baseline']['response'],
               validation_absolute=stats['selected']['absolute']<=1.10*stats['baseline']['absolute'],
               meaningful_signs=not sign_failures)
    assessment=dict(decision='REJECTED' if not all(gates.values()) else 'COMPONENT_PASS_ONLY',
                    gates=gates,selection=selection,validation=stats,
                    validation_response_error_change=stats['selected']['response']/stats['baseline']['response']-1,
                    validation_absolute_error_change=stats['selected']['absolute']/stats['baseline']['absolute']-1,
                    conservation_max=max(mass_errors),same_initial_states=initial_checks,
                    scope=protocol['scope'],future_truth_used_as_input=False,
                    new_native_runs=0,fullOmega_gain_qualification=False)
    save(HERE/'assessment.json',assessment);save(HERE/'horizon_results.json',horizon_rows)
    # Exact tested sources remain reviewable if the failed opt-in code is removed.
    directory=HERE/'tested_sources';directory.mkdir(exist_ok=False)
    for f in FILES:(directory/Path(f).name).write_bytes((ROOT/f).read_bytes())
    (directory/'test_jin_lane_intensity.py.txt').write_bytes((ROOT/'tests/test_jin_lane_intensity.py').read_bytes())
    print(json.dumps({k:v for k,v in assessment.items() if k!='validation'},ensure_ascii=False))
    for h in (150,300,450):
        for v in ('baseline','selected'):
            s=losses([r for r in horizon_rows if r['version']==v and r['horizon_sec']==h],protocol)
            p=next(p for p in s['pairs'] if p['pair']=='release->release_vsl90')
            print(json.dumps(dict(horizon=h,version=v,actual_delta=p['actual'],predicted_delta=p['predicted'])))


if __name__=='__main__':
    if len(sys.argv)>1:
        assert sys.argv[1]=='three_blocks'
        HERE=HERE/'three_blocks'
    main()
