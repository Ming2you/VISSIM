"""Independent endpoint partition and native/model interval checks."""
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

D=Path(__file__).resolve().parent/'verified'
PORTS={'10483':'storage:lane_off_10483','10682':'storage:lane_off_10682',
       '10481':'storage:OR_D_E_storage','10643':'storage:OR_F_E_storage'}


def main():
    assert not (D/'verification.json').exists()
    cells=h.read(D/'cells.json');lanes=h.read(D/'lanes.json');ports=h.read(D/'ports.json')
    witnesses=h.read(D/'witness.json');runtime=h.read(h.R/'entry10643/native_cohorts.json')['route_runtime']
    by={(r['seed'],r['arm'],r['elapsed'],r['cell']):r for r in cells}
    by_lane={(r['seed'],r['arm'],r['elapsed'],r['cell'],r['lane']):r for r in lanes}
    checks=0
    for w in witnesses:
        start=2700 if w['seed']==67 else 2250
        key=(w['seed'],w['arm'],w['time']-start,w['cell']);r=by[key];vv=w['vehicles']
        assert len(vv)==r['n'] and sum(v['v']<5 for v in vv)==r['stopped']
        for lane in {v['lane'] for v in vv}:
            z=[v for v in vv if v['lane']==lane];row=by_lane[key+(lane,)]
            assert row['n']==len(z) and row['stopped']==sum(v['v']<5 for v in z)
            assert abs(row['speed']-sum(v['v'] for v in z)/len(z))<1e-10
            dist=[runtime['bounds']['FW_E'][w['cell']+1]-v['x'] for v in z if v['v']<5]
            assert row['nearest_stopped_to_downstream_m']==(min(dist) if dist else None)
            checks+=1
    events=h.read(h.R/'boundary_time88/events.json')
    old=h.read(h.R/'boundary_time88/assessment.json')['cases']
    totals=0;interval_checks=0;comparisons={}
    for seed in (67,71):
        arms=('release','release_vsl90') if seed==67 else ('nc','rm','vsl','both')
        for arm in arms:
            case=f'67_release/{arm}' if seed==67 else f'71_four/{arm}'
            start=2700 if seed==67 else 2250
            for target in PORTS:
                rr=[r for r in ports if (r['seed'],r['arm'],r['target'])==(seed,arm,target) and r['elapsed']>0]
                es=[e for e in events if e['case']==case and e['ref']=='off_entry:'+target]
                count=sum(r['observed_entry_interval'] for r in rr)
                assert count==old[case]['physical_counts']['off_entry:'+target]==len(es)
                totals+=1
                for r in rr:
                    lo=start+r['elapsed']-150;hi=start+r['elapsed']
                    n=sum(lo<e['time_sec']<=hi for e in es)
                    assert n==r['observed_entry_interval'],(seed,arm,target,lo,n,r['observed_entry_interval'])
                    interval_checks+=1
    timed={arm:h.read(D.parent/f'timing/{arm}_timing.json') for arm in ('rm','both')}
    for target,node in PORTS.items():
        report={}
        for arm in ('rm','both'):
            native=[r['observed_entry_interval'] for r in ports if (r['seed'],r['arm'],r['target'])==(71,arm,target) and r['elapsed']>0]
            model=[sum(r['vehicles'] for r in timed[arm]['intervals'] if r['block']==b and r['target']==node) for b in range(3)]
            moment=sum(e['signed_moment_veh_h'] for e in events if e['case']==f'71_four/{arm}' and e['ref']=='off_entry:'+target)
            report[arm]=dict(native_intervals=native,model_intervals=model,
                native_outflow_signed_moment=moment,model_outflow_signed_moment=-timed[arm]['remaining_time_weighted_outflow'][node])
        report['delta_native_moment']=report['both']['native_outflow_signed_moment']-report['rm']['native_outflow_signed_moment']
        report['delta_model_moment']=report['both']['model_outflow_signed_moment']-report['rm']['model_outflow_signed_moment']
        comparisons[target]=report
    # Final-port time moment is complementary to the off-ramp comparison.
    terminal={}
    for arm in ('rm','both'):
        terminal[arm]=dict(native=sum(e['signed_moment_veh_h'] for e in events if e['case']==f'71_four/{arm}' and e['ref']=='chain_end:FW_E'),
            predicted=-timed[arm]['remaining_time_weighted_outflow']['external:terminal:FW_E'])
    protocol=h.read(D/'protocol.json');pins=h.read(D/'pins.json')
    assert all(h.sha(p)==sha for p,sha in {**pins,**protocol['protected'],protocol['STOP']['path']:protocol['STOP']['sha256']}.items())
    for name in ('cells.json','ports.json','witness.json'):
        assert h.read(D/name)==h.read(D.parent/name),name
    result=dict(status='PASS_DIAGNOSTIC_NOT_QUALIFIED',lane_checks=checks,off_totals=totals,off_intervals=interval_checks,
        exact_initials=True,known_seed_validation_not_blind=True,source_preserved=True,adopted=False,
        off_timing=comparisons,terminal_moments=terminal,
        limitations=['Native1m detector crossing versus model physicalcellport; momentdifference includes location/step approximation.',
                    'Snapshot queues are not continuousqueue duration. No causal attribution by subtracting terms.',
                    'Equal totalflow can coexist with delayedflow. No actualfuturestate as autonomousinput.'])
    h.save(D/'verification.json',result)
    print('PASS',checks,totals,interval_checks)
    print('10483',comparisons['10483'])
    print('terminal',terminal)


if __name__=='__main__':main()
