"""Check phase mass/moments, prefix accounting, and fixed adoption gates."""
import collections
import gzip
import json
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    out=HERE/'forecast';status=h.read(out/'status.json');assert status['status']=='complete'
    rows=h.read(out/'rows.json');coeff=h.read(HERE/'coefficients.json')
    protocol=h.read(HERE/'protocol.json');checks=collections.Counter();maxerr=collections.defaultdict(float)
    for p,digest in {**h.read(out/'preservation.json')['input_sha256'],**protocol['protected_sha256'],protocol['STOP']['path']:protocol['STOP']['sha256']}.items():assert h.sha(p)==digest,p
    selected=[];slow_summary=[];block_summary=[]
    for row in rows:
        case,arm,mode,H=row['case'],row['arm'],row['mode'],row['horizon']
        pred=h.read(out/mode/(case+'_'+arm+'.json.gz'))
        t0=min(z['window_start_s'] for z in pred['flows']);end=t0+H
        exits=sum(z['off_departures']+z['terminal_exits'] for z in pred['flows'] if z['window_end_s']<=end+1e-6)
        assert abs(exits-row['predicted']['exits'])<1e-9;checks['prefix_flow']+=1
        for ramp,value in row['predicted']['merges'].items():
            actual=sum(z['accepted_merge_veh'] for z in pred['ramps'] if z['ramp']==ramp and z['end_sec']<=end+1e-6)
            assert abs(actual-value)<1e-9;checks['prefix_merge']+=1
        if H!=450:continue
        for lo in (0,150,300):
            sub=[z for z in pred['flows'] if t0+lo<z['window_end_s']<=t0+lo+150+1e-6 and z['cell']==20]
            block_summary.append(dict(case=case,arm=arm,mode=mode,start=lo,off10483=sum(z['off_departures'] for z in sub)))
        if mode!='queue':continue
        trace=h.read(out/mode/(case+'_'+arm+'_phase.json.gz'))
        by={(round(z['time_s'],6),z['cell'],z['lane']):z for z in trace['rows']}
        for e in trace['events']:
            key=(round(e['time_s']+1,6),e['cell'],e['lane']);z=by[key]
            b=e['balance'];s=e['s0']+b[0]-b[1]+b[2]-b[3]+b[4]-b[5]
            err=abs(s-z['s']);maxerr['slow_mass']=max(maxerr['slow_mass'],err);assert err<1e-7
            assert -1e-7<=z['s']<=z['n']+1e-7
            assert -1e-7<=z['slow_moment']<=5*z['s']+1e-7
            err=abs(z['slow_moment']+z['moving_moment']-z['n']*z['v'])
            maxerr['moment']=max(maxerr['moment'],err);assert err<1e-7
            onset=(e['n_next']-e['transport_s'])*(-math.expm1(-coeff['formation_per_sec']*e['pressure']))
            release=e['transport_s']*(-math.expm1(-coeff['release_per_sec']*(1-e['pressure'])))
            assert abs(onset-e['onset'])<1e-9 and abs(release-e['release'])<1e-9
            checks['phase_balances']+=1
        for z in pred['cells']:
            if z['cell'] not in range(20,26):continue
            groups=[by[(round(z['time_s'],6),z['cell'],g)] for g in (1,2,3)]
            n=sum(r['n'] for r in groups);moment=sum(r['slow_moment']+r['moving_moment'] for r in groups)
            assert abs(n-z['n_veh'])<1e-7 and (not n or abs(moment/n-z['v_kmh'])<1e-7)
            checks['aggregate_matches']+=1
        # Cold-phase count and speed-threshold count are not automatically
        # equal: a moving-phase vehicle can still be below5 during startup.
        for cell in (20,21,24,25):
            a=[z for z in trace['rows'] if z['cell']==cell and z['lane']==1]
            low=[]
            for z in a:
                m=z['n']-z['s'];u=z['moving_moment']/m if m>1e-9 else 0.
                low.append(z['s']+(m if u<5 else 0.))
            slow_summary.append(dict(case=case,arm=arm,cell=cell,
                mean_phase_s=sum(z['s'] for z in a)/len(a),mean_speed_threshold_low=sum(low)/len(low)))
    contrasts=[];regrets=[]
    for H in (150,450):
        for case in sorted({r['case'] for r in rows}):
            by={(r['mode'],r['arm']):r for r in rows if r['case']==case and r['horizon']==H}
            for a,b in [('hold','release'),('release','release_vsl90'),('hold','hold_vsl90'),('none','vsl')]:
                if ('baseline',a) not in by or ('baseline',b) not in by:continue
                real=by['baseline',b]['actual']['ttt']-by['baseline',a]['actual']['ttt']
                z=dict(case=case,horizon=H,change=a+'->'+b,actual=real,meaningful=abs(real)>=.5)
                for mode in ('baseline','queue'):
                    z[mode]=by[mode,b]['predicted']['ttt']-by[mode,a]['predicted']['ttt']
                contrasts.append(z)
            for mode in ('baseline','queue'):
                rs=[r for r in rows if r['case']==case and r['horizon']==H and r['mode']==mode]
                chosen=min(rs,key=lambda r:r['predicted']['ttt'])
                regrets.append(dict(case=case,horizon=H,mode=mode,chosen=chosen['arm'],
                    regret=chosen['actual']['ttt']-min(r['actual']['ttt'] for r in rs)))
    assessment=h.read(out/'assessment.json')['losses']['450']
    base,cand=assessment['baseline'],assessment['queue']
    gate=dict(meaningful_signs=all(z['actual']*z['queue']>0 for z in contrasts if z['horizon']==450 and z['meaningful']),
        response=cand['response']<=.9*base['response'],absolute=cand['absolute']<=1.1*base['absolute'],
        regret=all(x['regret']<=.5 for x in regrets if x['mode']=='queue' and x['horizon']==450))
    result=dict(status='verified',forecasts=status['forecasts'],checks=dict(checks),max_errors=dict(maxerr),
        gate=gate,passed=all(gate.values()),adopted=False,contrasts=contrasts,regrets=regrets,
        protected_and_STOP_preserved=True)
    h.save(HERE/'verification.json',result);h.save(HERE/'slow_summary.json',slow_summary);h.save(HERE/'block_summary.json',block_summary)
    print('GATE',gate,'BASE/CAND',base['absolute'],cand['absolute'],base['response'],cand['response'])
    for z in contrasts:print(z)


if __name__=='__main__':main()
