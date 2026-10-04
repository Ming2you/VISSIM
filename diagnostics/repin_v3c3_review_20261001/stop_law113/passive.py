"""Four frozen autonomous forecasts, with two passive stopped-stock tracers.

No tracer feeds back to physics. Accepted transfers are reused and source/ramp
admissions are labelled moving. This deliberately small transport closure is
tested, not assumed to reproduce stopped-vehicle discharge.
"""
import copy
import gzip
import importlib.util
import json
import math
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def save(name, value):
    (HERE/name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def load_gz(path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        return json.load(stream)


def main():
    assert not (HERE/'passive_protocol.json').exists(), 'No duplicate autonomous check'
    spec = importlib.util.spec_from_file_location('jin_reuse', HERE.parent/'jin_macro111/run.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    context, replay, Obs = helper.setup()
    from evaluation.controllers import area_freeway_accounting as afa, freeway_fd as fd
    original_step, original_advance = afa._freeway_substep_events, fd.VSLExposure.advance
    old_protocol = read(HERE/'protocol.json')
    fit = read(HERE/'macro_results.json')
    theta = {r['model']:r['coefficients'] for r in fit['fits']}
    assert fit['decision'] == 'CONDITIONAL_PASS_ONLY'
    geometry = read(helper.I/'selected/port_gain/geometry.json')
    lane_km = {r['cell']:r['lane_km'] for r in geometry['cells'] if r['road']=='FW_E'}
    critical = {int(k):v for k,v in old_protocol['critical'].items()}
    free = {int(k):v for k,v in old_protocol['v_free'].items()}
    rho_max = old_protocol['rho_max']
    records = [r for r in helper.records(True) if r['case']=='s43_early' and r['arm'] in ('none','vsl')]
    records += [r for r in helper.records(False) if r['arm'] in ('release','release_vsl90')]
    assert len(records) == 4
    # Stronger paired state67 first;43 remains a replication, never a refit.
    records = records[2:]+records[:2]
    save('passive_protocol.json', dict(
        budget_forecasts=4, horizon=450, new_fits=0, parameters=theta,
        initialize='Only native stopped labels at the common initial timestamp. No future observation into rollout.',
        rates='Same fixed features/coefficients; current autonomous rho/speed and predicted downstream stopped fraction.',
        transport='Apply exact CTMC reaction for1s, then mix stopped labels proportionally with already accepted conservative flows.',
        sources='Origin and accepted on-ramp admissions enter as moving. Outside16..23 no reaction; initial labels may advect. This is an explicit unvalidated closure.',
        feedback_to_physics=False,
        gate='150s mean-region stopped-stock RMSE>=20% better than constant law for BOTH43 and67; meaningful observed paired changes>=5veh have correct sign and >=20% magnitude. Passing is only state forecast evidence, not TTT/gain qualification.',
        physical_parity='67 four physical tables exact vs111;43 block metrics exact vs111 three_blocks baseline.',
        scope='FW_E zero-based16..23; stopped<5km/h. First450s of cached43 and67; no seed29 fitting.',
        core_pins=old_protocol['core_pins'], input_pins=old_protocol['input_pins']))
    for p,h in old_protocol['core_pins'].items():
        assert helper.sha(p)==h
    current = None
    step_context = None
    results = []
    started = time.perf_counter()

    def step(state, control, demand, cfg, *args, **kwargs):
        nonlocal step_context
        assert cfg.network.freeway_links == ['FW_E'], cfg.network.freeway_links
        step_context = dict(speed=list(state.freeway_speed['FW_E']), dt=cfg.simulation.T_f_h*3600)
        before = current['steps']
        value = original_step(state, control, demand, cfg, *args, **kwargs)
        assert current['steps'] == before+1, 'Exactly one physical tracer advance per step'
        return value

    def advance(self, old_n, new_n, internal, total_out, entry, ramps, commands):
        assert len(old_n)==31 and len(internal)==30
        dt=step_context['dt']; v=step_context['speed']
        assert abs(dt-1.)<1e-10
        if current['steps']==0:
            mismatch=max(abs(n-m) for n,m in zip(old_n,current['initial_n']))
            current['initial_count_mismatch']=mismatch
            assert mismatch<1e-6, ('Initial native/plant stock mismatch',mismatch)
        for model in ('constant','state'):
            b=current['stock'][model]
            after=list(b)
            for i in range(16,24):
                if model=='constant':
                    a,z=theta[model]
                else:
                    rd=old_n[i+1]/lane_km[i+1]
                    down_fraction=b[i+1]/old_n[i+1] if old_n[i+1]>0 else 0.
                    pressure=(old_n[i]/lane_km[i]/critical[i])*(down_fraction+max(v[i]-v[i+1],0.)/free[i]+rd/rho_max)
                    room=max(v[i+1],0.)/free[i+1]*max(1-rd/rho_max,0.)
                    a,z=theta[model][0]*pressure,theta[model][1]*room
                factor=-math.expm1(-(a+z)*dt)/(a+z) if a+z else dt
                after[i]=b[i]+(old_n[i]-b[i])*a*factor-b[i]*z*factor
            fraction=[bi/ni if ni>0 else 0. for bi,ni in zip(after,old_n)]
            nxt=[after[i]-total_out[i]*fraction[i]+(internal[i-1]*fraction[i-1] if i else 0.) for i in range(31)]
            external=sum((total_out[i]-(internal[i] if i<30 else 0.))*fraction[i] for i in range(31))
            residual=abs(sum(nxt)-(sum(after)-external))
            current['max_tag_balance']=max(current['max_tag_balance'],residual)
            assert residual<1e-7
            assert all(-1e-8<=bi<=ni+1e-8 for bi,ni in zip(nxt,new_n)), 'Passive stopped tags must remain within real stock'
            current['stock'][model]=nxt
        current['steps']+=1
        if current['steps']%5==0:
            current['traces'].append(dict(elapsed=current['steps'], stock=copy.deepcopy(current['stock'])))
        # Original cohort bookkeeping executes once with unmodified arguments.
        return original_advance(self, old_n, new_n, internal, total_out, entry, ramps, commands)

    afa._freeway_substep_events=step
    fd.VSLExposure.advance=advance
    try:
        for r in records:
            case=('67_' if r['case']=='s67_late' else '43_')+r['arm']
            spec=old_protocol['input_pins'][case]
            assert helper.sha(ROOT/spec['path'])==spec['sha256']
            native=load_gz(ROOT/spec['path'])
            frames={round(float(t),1):row for t,row in native['frames'].items()}
            initial=frames[round(r['cutoff'],1)]
            n=[sum(row[0]==i for row in initial.values()) for i in range(31)]
            b=[sum(row[0]==i and row[1]<5 for row in initial.values()) for i in range(31)]
            current=dict(case=case,steps=0,initial_n=n,stock={name:list(b) for name in theta},
                         traces=[dict(elapsed=0,stock={name:list(b) for name in theta})],max_tag_balance=0.)
            save('passive_status.json',dict(status='running',case=case,completed=len(results)))
            pred,measure=helper.predict(context['component'],replay,Obs(r['truth']),r,450)
            assert current['steps']==450
            if r['case']=='s67_late':
                archived=load_gz(HERE.parent/'jin_macro111'/('baseline_'+r['arm']+'.json.gz'))
                parity={k:json.loads(json.dumps(pred[k]))==archived[k] for k in ('cells','flows','ports','ramps')}
            else:
                old=read(HERE.parent/'jin_macro111/three_blocks/grid.json')[0]['rows']
                blocks=helper.block_measures(context['component'],replay,Obs(r['truth']),r,pred)
                parity={x['case']:x==next(y for y in old if y['case']==x['case'] and y['arm']==x['arm']) for x in blocks}
            assert all(parity.values()), ('Physics changed',case,parity)
            rows=[]
            for trace in current['traces']:
                actual=frames[round(r['cutoff']+trace['elapsed'],1)]
                rows.append(dict(elapsed=trace['elapsed'],actual=sum(row[0] in range(16,24) and row[1]<5 for row in actual.values()),
                                 **{name:sum(trace['stock'][name][16:24]) for name in theta}))
            windows=[]
            for start in (0,150,300):
                selected=[x for x in rows if start<=x['elapsed']<start+150]
                assert len(selected)==30
                windows.append(dict(start=start,**{k:sum(x[k] for x in selected)/30 for k in ('actual','constant','state')}))
            result=dict(case=case,steps=current['steps'],max_tag_balance=current['max_tag_balance'],
                        initial_count_mismatch=current['initial_count_mismatch'],physical_parity=parity,windows=windows,rows=rows)
            results.append(result)
            save('passive_partial.json',results)
            print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)
        gates=[]
        for seed in ('43','67'):
            chosen=[r for r in results if r['case'].startswith(seed+'_')]
            rmse={k:math.sqrt(sum((w[k]-w['actual'])**2 for r in chosen for w in r['windows'])/6) for k in theta}
            plain=next(r for r in chosen if r['case']==seed+('_none' if seed=='43' else '_release'))
            controlled=next(r for r in chosen if r is not plain)
            delta=[{k:b[k]-a[k] for k in ('actual','constant','state')} for a,b in zip(plain['windows'],controlled['windows'])]
            direction=all(abs(d['actual'])<5 or (d['actual']*d['state']>0 and abs(d['state'])>=.2*abs(d['actual'])) for d in delta)
            gates.append(dict(seed=seed,rmse=rmse,improvement=1-rmse['state']/rmse['constant'],delta=delta,
                              passed=direction and rmse['state']<=.8*rmse['constant']))
        save('passive_results.json',dict(results=results,gates=gates,decision='STATE_ONLY_PASS' if all(g['passed'] for g in gates) else 'DO_NOT_CONNECT',
                                         elapsed_seconds=time.perf_counter()-started,forecasts=4,gain_qualified=False))
        save('passive_status.json',dict(status='complete',completed=4))
    except BaseException as exc:
        save('passive_status.json',dict(status='failed',completed=len(results),case=current['case'] if current else None,error=repr(exc)))
        raise
    finally:
        afa._freeway_substep_events=original_step
        fd.VSLExposure.advance=original_advance
        assert all(helper.sha(p)==h for p,h in old_protocol['core_pins'].items())


if __name__=='__main__':
    main()
