"""Verify cached ramp passages and derive the native/model stock comparison."""
import ast
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    result=h.read(HERE/'summary.json');protocol=h.read(HERE/'protocol.json')
    trips=h.read(HERE/'trips.json');old=h.read(h.R/'ramp_posthead186/analysis.json')
    old_source=ast.parse((HERE/'analyzer_before187.py.txt').read_text(encoding='utf8'))
    current=ast.parse((h.R/'flowbudget182/analyze.py').read_text(encoding='utf8'))
    functions=lambda tree:{n.name:ast.dump(n) for n in tree.body if isinstance(n,ast.FunctionDef)}
    before,after=functions(old_source),functions(current)
    assert all(after[k]==v for k,v in before.items())
    assert h.sha(HERE/'analyzer_before187.py.txt')==protocol['source_before']
    checks=0;mechanism=[];pins={str(Path(__file__)):h.sha(__file__)}
    for source in result['sources']:
        case,arm=source['case'],source['arm'];key=f'{case}_{arm}'
        path=Path(source['path']);stat=path.stat()
        assert stat.st_size==source['bytes'] and stat.st_mtime_ns==source['mtime_ns']
        cache=HERE/f'{key}_ramps.json.gz';pins[str(cache)]=h.sha(cache)
        data=h.read(cache);frames={float(t):v for t,v in data['frames'].items()}
        assert data['source']==source and len(frames)==91
        for z in trips['complete_interval_censored']:
            if z['case']!=case or z['arm']!=arm:continue
            vid=z['vehicle'];con=z['connector'];hh=z['head']
            before_row=frames[hh['lower']].get(vid);after_row=frames[hh['upper']].get(vid)
            assert hh['before']==(None if before_row is None else before_row[1:])
            assert hh['after']==(None if after_row is None else after_row[1:])
            a=frames[z['merge_lower']][vid];b=frames[z['merge_upper']].get(vid)
            assert a[0]==con and b is None
            assert a[1]==z['last_ramp_position_m'] and a[2]==z['last_ramp_speed_kmh']
            assert z['travel_lower']==max(0,z['merge_lower']-hh['upper'])
            assert z['travel_upper']==z['merge_upper']-hh['lower']
            assert hh['connector']==con and z['travel_lower']<=z['travel_upper']
            checks+=1
        predpath=h.R/f'queue_dynamics178/forecast/baseline/{key}.json.gz';pred=h.read(predpath);pins[str(predpath)]=h.sha(predpath)
        times=sorted(frames)[:-1]
        for con in ('10639','10681','10490','10484'):
            spec=next(z for z in old['initial'] if z['case']==case and z['connector']==con)
            head,length=spec['head_m'],spec['length_m']
            rows=[z for z in pred['ramps'] if z['start']['connector_id']==con]
            states={round(z['start_sec'],1):z['start'] for z in rows};samples=[]
            for t in times:
                post=[z for z in frames[t].values() if z[0]==con and z[1]>head]
                slow=[z for z in post if z[2]<5]
                samples.append(dict(native_post=len(post),native_slow=len(slow),
                    slow_last15=sum(length-z[1]<=15 for z in slow),slow_last30=sum(length-z[1]<=30 for z in slow),
                    model_trav=states[t]['downstream_travelling_veh'],model_ready=states[t]['merge_ready_veh']))
            means={k:sum(z[k] for z in samples)/len(samples) for k in samples[0]}
            ref=next(z for z in result['rows'] if z['case']==case and z['arm']==arm and z['connector']==con)
            assert abs(means['native_post']-ref['posthead_mean_native5_left'])<1e-10
            assert abs(means['model_trav']+means['model_ready']-ref['posthead_mean_model5_left'])<1e-10
            mechanism.append(dict(case=case,arm=arm,connector=con,**means,
                model_receiving_binding_seconds=sum(z['eligible_merge_veh']>z['receiving_budget_veh']+1e-8 for z in rows),
                model_merge=sum(z['accepted_merge_veh'] for z in rows),model_head=sum(z['head_service_veh'] for z in rows)))
    assert checks==len(trips['complete_interval_censored'])==5329
    assert len(result['rows'])==56
    for key,digest in {**result['input_sha256'],**protocol['protected_sha256'],protocol['STOP']['path']:protocol['STOP']['sha256']}.items():assert h.sha(key)==digest,key
    h.save(HERE/'mechanism.json',dict(rows=mechanism,scope='Observed slow5 posthead by distance to merge; model travelling/merge-ready counts from unchanged receipts. Current samples are labels only; no receiving coefficient is fitted.',input_sha256=pins))
    h.save(HERE/'verification.json',dict(status='verified',paired_passages=checks,groups=56,native_ramps=8,reference_states=4,
        previous_analyzer_functions_unchanged=list(before),native_checks=result['checks'],core_inputs_STOP_unchanged=True,
        forecasts=0,fit=False,adopted=False,qualified=False,full_goal='ACTIVE_NOT_QUALIFIED',summary_sha256=h.sha(HERE/'summary.json'),mechanism_sha256=h.sha(HERE/'mechanism.json')))
    print('VERIFIED187',checks,'paired passages;56 groups;core/STOP preserved')


if __name__=='__main__':main()
