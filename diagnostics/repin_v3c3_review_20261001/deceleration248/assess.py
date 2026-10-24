"""Read saved248 forecasts only; independent bookkeeping and frozen gates."""
import itertools
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

D=Path(__file__).resolve().parent/'verified'


def compare(actual,predicted):
    material=abs(actual)>=.5
    error=predicted-actual
    allowed=max(.5,.5*abs(actual))
    return dict(actual=actual,predicted=predicted,error=error,material=material,
        allowed_error=allowed,passed=(actual*predicted>0 and abs(error)<=allowed) if material else None)


def main():
    assert not (D/'assessment.json').exists()
    done=h.read(D/'completion.json');assert done['status']=='COMPLETE_PENDING_ASSESSMENT'
    protocol=h.read(D/'protocol.json');selection=h.read(D/'selection_frozen.json')
    rows=[h.read(p) for p in sorted(D.glob('s*_*.json')) if '_base_' in p.name or '_probe_' in p.name or '_chosen_' in p.name]
    assert len(rows)==done['forecasts']<=18
    maxbalance=0.;costerror=0.;checks=0
    by={}
    for row in rows:
        by[row['tag'],row['label'],row['arm']]=row
        inventory0=row['snapshots'][0]['inventory'];inventory1=row['snapshots'][-1]['inventory']
        # Transit identities can be created and filled after the first step.
        # Check both endpoint inventories; an absent key has zero vehicles.
        net={k:0. for k in inventory0.keys()|inventory1.keys()}
        for t in row['transfers']:
            assert math.isfinite(t['vehicles']) and t['vehicles']>=0
            if t['source'] in net:net[t['source']]-=t['vehicles']
            if t['target'] in net:net[t['target']]+=t['vehicles']
        for k in net:
            e=inventory0.get(k,0.)+net[k]-inventory1.get(k,0.)
            maxbalance=max(maxbalance,abs(e));checks+=1
            assert abs(e)<1e-6,(row['tag'],row['arm'],k,e)
        for stock in ['freeway:FW_E','freeway:FW_W',*('ramp:'+r for r in row['ramps'])]:
            duration=sum(r['dt_h']*3600 for r in row['residence'] if stock in r['stock_keys'])
            assert abs(duration-450)<1e-7,(stock,duration)
        for field,total in [('inside_total',row['ttt']),('east',row['east_ttt']),('ramps',row['ramps_ttt'])]:
            e=sum(r['dt_h']*r[field] for r in row['residence'])-total
            costerror=max(costerror,abs(e));assert abs(e)<1e-7
        assert len(row['ramps'])==8 and row['resource_max']<1e-7
        for rr in row['ramps'].values():
            assert abs(rr['initial']+rr['arrival']-rr['merge']-rr['final'])<1e-7
        for c,s in row['relaxation'].items():
            assert c in ('24','25') and s['calls']>=450
            assert abs(s['new_relaxation_sum']-row['ratio']*s['base_relaxation_sum'])<1e-7
            assert s['pressure_ratio_max_error']<1e-7
        base=next(v for v in rows if v['tag']==row['tag'] and v['label']=='base' and v['arm']==row['arm'])
        assert row['commands']==base['commands'] and row['snapshots'][0]==base['snapshots'][0]
    def chosen(tag,arm):
        label='base' if selection['ratio']==1. else 'probe' if tag=='s67' and abs(selection['ratio']-.5)<1e-12 else 'chosen'
        return by[tag,label,arm]
    reports={}
    for tag,name in [('s67','s67_full_observation/response_assessment76.json'),('s73','replication_s73_95/response_assessment95.json')]:
        actual=h.read(h.R/name);entries={}
        for label,select in [('base',lambda arm:by[tag,'base',arm]),('chosen',lambda arm:chosen(tag,arm))]:
            a,b=[select(x) for x in ('release_actual','release_vsl90_actual')]
            entry=dict(omega=compare(actual['actual_delta_omega_veh_h'],b['ttt']-a['ttt']),
                east=compare(actual['component_delta_veh_h']['FW_E']['actual'],b['east_ttt']-a['east_ttt']),
                ramp=compare(actual['component_delta_veh_h']['ramps']['actual'],b['ramps_ttt']-a['ramps_ttt']),
                outside_delta=b['tracked_outside']-a['tracked_outside'],
                actual_arms_from_common_prefix=True,absolute_native_full_run_cost_not_compared=True,
                arms={})
            for key,row in [('release',a),('release_vsl90',b)]:
                truth=actual['arms'][key]['mainline']['FW_E']['actual']
                entry['arms'][key]=dict(terminal_actual=truth['terminal'],terminal_predicted=row['east_terminal'],
                    final_actual=truth['final_stock'],final_predicted=row['east_final'],
                    ramp_merge_predicted={r:s['merge'] for r,s in row['ramps'].items()},
                    ramp_cost=row['ramps_ttt'])
            predicted_best='release' if a['ttt']<=b['ttt'] else 'release_vsl90'
            actualcost={'release':0.,'release_vsl90':actual['actual_delta_omega_veh_h']}
            entry['predicted_choice']=predicted_best
            entry['regret']=actualcost[predicted_best]-min(actualcost.values())
            entries[label]=entry
        for field in ('terminal','final'):
            err=lambda label:sum(abs(x[field+'_predicted']-x[field+'_actual']) for x in entries[label]['arms'].values())
            entries[field+'_absolute_error']=dict(base=err('base'),chosen=err('chosen'),passed=err('chosen')<=1.1*err('base')+1e-7)
        reports[tag]=entries
    truth71=h.read(h.R/'rm_restart219/independent230/replay_v2/assessment.json')['arms']
    entries={}
    for label,select in [('base',lambda arm:by['s71','base',arm]),('chosen',lambda arm:chosen('s71',arm))]:
        arms={arm:select(arm) for arm in ('nc','rm','vsl','both')}
        contrasts={}
        for a,b in itertools.combinations(arms,2):
            actual=truth71[b]['native_window_omega_veh_h']-truth71[a]['native_window_omega_veh_h']
            contrasts[b+' minus '+a]=compare(actual,arms[b]['ttt']-arms[a]['ttt'])
        pick=min(arms,key=lambda x:arms[x]['ttt']);best=min(truth71,key=lambda x:truth71[x]['native_window_omega_veh_h'])
        entries[label]=dict(contrasts=contrasts,predicted_choice=pick,actual_choice=best,
            regret=truth71[pick]['native_window_omega_veh_h']-truth71[best]['native_window_omega_veh_h'],
            outside_deltas={arm:row['tracked_outside']-arms['nc']['tracked_outside'] for arm,row in arms.items()})
    reports['s71']=entries
    training=h.read(D/'training.json')
    # Record the actual perturbed pair even when the frozen fit selects no change.
    pa,pb=[by['s67','probe',arm] for arm in ('release_actual','release_vsl90_actual')]
    training['half_negative_relaxation_probe']=dict(omega_delta=pb['ttt']-pa['ttt'],
        east_delta=pb['east_ttt']-pa['east_ttt'],ramp_delta=pb['ramps_ttt']-pa['ramps_ttt'],
        cost_changes_by_arm={arm:by['s67','probe',arm]['ttt']-by['s67','base',arm]['ttt']
            for arm in ('release_actual','release_vsl90_actual')})
    gates=dict(training_loss_improvement=training['chosen_loss']<=.9*training['base_loss'],
        material_response=all(reports[tag]['chosen']['omega']['passed'] for tag in ('s67','s73'))
            and all(c['passed'] is not False for c in reports['s71']['chosen']['contrasts'].values()),
        ranking=all(reports[tag]['chosen']['regret']<=.5 for tag in reports),
        east_absolute=all(reports[tag][field+'_absolute_error']['passed'] for tag in ('s67','s73') for field in ('terminal','final')))
    pins={**protocol['protected_sha256'],**protocol['input_pins'],protocol['STOP']['path']:protocol['STOP']['sha256']}
    assert all(h.sha(p)==sha for p,sha in pins.items())
    result=dict(status='GATES_PASS_NEEDS_FURTHER_VALIDATION' if all(gates.values()) else 'NOT_ADOPTED_RESPONSE_GATE_FAILED',
        ratio=selection['ratio'],forecasts=len(rows),earlier_forecast_with_reporting_failure=1,
        total_completed_physics_forecasts=len(rows)+1,gates=gates,training=training,reports=reports,
        verification=dict(inventory_balances=checks,max_balance_error=maxbalance,max_integral_error=costerror,
            commands_and_initial_states_unchanged=True,full8ramps=True,protected_sources_preserved=True),
        production_adopted=False,full_goal_qualified=False,native_runs=0,FZP_reads=0,
        limitations=['Known historical validation states, not a blind test.',
            '450s conditional-on-executed-command prediction, not a newly optimized policy.',
            'Process-local scalar candidate, no AD or writer adoption.',
            'A failure of this bounded one-parameter family is not impossibility of VSL benefit.'])
    h.save(D/'assessment.json',result)
    print(result['status'],result['ratio'],gates)
    for tag in reports:
        print(tag,reports[tag]['chosen'].get('omega',reports[tag]['chosen'].get('contrasts')),reports[tag]['chosen']['regret'])


if __name__=='__main__':main()
