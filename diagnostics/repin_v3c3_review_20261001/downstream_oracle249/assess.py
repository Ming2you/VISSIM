"""Assess saved conditional forecasts; no fitting or native file access."""
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

D=Path(__file__).resolve().parent


def main():
    assert not (D/'assessment.json').exists()
    p=h.read(D/'protocol.json');c=h.read(D/'completion.json')
    assert c['forecasts']==4 and c['future_observation_inputs']
    a=h.read(D/'audit.json');assert a['future_observation_inputs'] and len(a['records'])==4
    cases={};maximum=0.;checks=0;pressure_error=0.
    for tag,truth_path in [('s67','s67_full_observation/response_assessment76.json'),('s73','replication_s73_95/response_assessment95.json')]:
        truth=h.read(h.R/truth_path);trial={};base={}
        for arm in ('release_actual','release_vsl90_actual'):
            trial[arm]=h.read(D/f'{tag}_conditional_{arm}.json')
            base[arm]=h.read(h.R/f'deceleration248/verified/{tag}_base_{arm}.json')
            row=trial[arm];assert row['future_observation_inputs']
            assert row['commands']==base[arm]['commands'] and row['snapshots'][0]==base[arm]['snapshots'][0]
            first,last=row['snapshots'][0]['inventory'],row['snapshots'][-1]['inventory']
            net={k:0. for k in first.keys()|last.keys()}
            for flow in row['transfers']:
                if flow['source'] in net:net[flow['source']]-=flow['vehicles']
                if flow['target'] in net:net[flow['target']]+=flow['vehicles']
            for key in net:
                err=first.get(key,0.)+net[key]-last.get(key,0.)
                maximum=max(maximum,abs(err));checks+=1;assert abs(err)<1e-6
            assert len(row['ramps'])==8 and row['resource_max']<1e-7
            cost=sum(x['dt_h']*x['inside_total'] for x in row['residence'])
            assert abs(cost-row['ttt'])<1e-7
            audit=next(x for x in a['records'] if x['tag']==tag and x['arm']==arm)
            assert [x['time'] for x in audit['calls']]==list(range(2700,3150))
            for rec in audit['calls']:
                interval=min(2,int((rec['time']-2700)//150))
                (t0,d0),(t1,d1)=audit['points'][interval:interval+2]
                expected=((t1-rec['time'])*d0+(rec['time']-t0)*d1)/150
                err=abs(rec['actual_interpolated_downstream']-expected)
                pressure_error=max(pressure_error,err);assert err<1e-10
                assert rec['new_vs_old_regime']==[expected>=rec['local_density'],rec['model_downstream']>=rec['local_density']]
        actual=dict(omega=truth['actual_delta_omega_veh_h'],terminal=truth['arms']['release_vsl90']['mainline']['FW_E']['actual']['terminal']-truth['arms']['release']['mainline']['FW_E']['actual']['terminal'])
        comparisons={}
        for label,rows in [('base',base),('conditional',trial)]:
            left,right=rows['release_actual'],rows['release_vsl90_actual']
            comparisons[label]=dict(omega=right['ttt']-left['ttt'],terminal=right['east_terminal']-left['east_terminal'],
                east=right['east_ttt']-left['east_ttt'],ramp=right['ramps_ttt']-left['ramps_ttt'],
                tracked_outside=right['tracked_outside']-left['tracked_outside'],end_stock=right['east_final']-left['east_final'])
        reductions={key:1-abs(comparisons['conditional'][key]-value)/abs(comparisons['base'][key]-value) for key,value in actual.items()}
        cases[tag]=dict(actual=actual,**comparisons,error_reductions=reductions,
            both_errors_improve20percent=all(x>=.2 for x in reductions.values()),
            changed_regimes={arm:sum(new!=old for row in a['records'] if row['tag']==tag and row['arm']==arm
                for new,old in (x['new_vs_old_regime'] for x in row['calls'])) for arm in trial})
    pins={**p['protected_sha256'],**p['pins'],p['STOP']['path']:p['STOP']['sha256']}
    assert all(h.sha(path)==sha for path,sha in pins.items())
    out=dict(status='CONDITIONAL_DIAGNOSIS_COMPLETE_NOT_AUTONOMOUS',future_observation_inputs=True,
        cases=cases,forecasts=4,fit_calls=0,verification=dict(stock_checks=checks,max_balance=maximum,
            pressure_calls=1800,max_interpolation_error=pressure_error,commands_initial_states_preserved=True,
            protected_sources_and_STOP_preserved=True),production_adopted=False,full_goal_qualified=False,
        limitations=['150s interpolation is not observed second-by-second pressure; no general impossibility inference.',
            'Only aggregate cell22 input into cell21 equation; neither other cells nor lane imbalance are controlled.',
            'Native source/admission differences remain; these cost contrasts are not pure capacity effects.'])
    h.save(D/'assessment.json',out)
    print(out['status'])
    for tag,result in cases.items():print(tag,result)


if __name__=='__main__':main()
