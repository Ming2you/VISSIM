"""Independent saved-result balance and response checks for the bounded FD fit."""
import itertools
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h
from diagnostics.repin_v3c3_review_20261001.deceleration248.assess import compare

D=Path(__file__).resolve().parent/'verified'
OLD=h.R/'deceleration248/verified'


def off(row):
    return sum(t['vehicles'] for t in row['transfers']
               if t['source']=='freeway:FW_E' and t['target'].startswith('storage:'))


def main():
    assert not (D/'assessment.json').exists()
    done=h.read(D/'completion.json');assert done['status']=='COMPLETE_PENDING_ASSESSMENT'
    protocol=h.read(D/'protocol.json');sel=h.read(D/'selection_frozen.json')
    rows=[h.read(p) for p in D.glob('s*_*.json') if 'snapshots' in h.read(p)]
    assert len(rows)==done['forecasts']<=9
    maxbalance=costerror=0.;checks=0
    for row in rows:
        begin=row['snapshots'][0]['inventory'];end=row['snapshots'][-1]['inventory']
        net={k:0. for k in begin.keys()|end.keys()}
        for t in row['transfers']:
            assert math.isfinite(t['vehicles']) and t['vehicles']>=0
            if t['source'] in net:net[t['source']]-=t['vehicles']
            if t['target'] in net:net[t['target']]+=t['vehicles']
        for key in net:
            e=begin.get(key,0)+net[key]-end.get(key,0)
            checks+=1;maxbalance=max(maxbalance,abs(e));assert abs(e)<1e-6
        assert len(row['ramps'])==8 and row['resource_max']<1e-7
        for r in row['ramps'].values():assert abs(r['initial']+r['arrival']-r['merge']-r['final'])<1e-7
        for field,value in [('inside_total',row['ttt']),('east',row['east_ttt']),('ramps',row['ramps_ttt'])]:
            e=sum(r['dt_h']*r[field] for r in row['residence'])-value
            costerror=max(costerror,abs(e));assert abs(e)<1e-7
        base=h.read(OLD/f"{row['tag']}_base_{row['arm']}.json")
        assert row['commands']==base['commands'] and row['snapshots'][0]==base['snapshots'][0]
        # The inherited reporting hook is lambda=1, never a second physical fit.
        assert row['ratio']==1.
        assert all(abs(s['base_relaxation_sum']-s['new_relaxation_sum'])<1e-7 for s in row['relaxation'].values())
    by={(r['tag'],r['label'],r['arm']):r for r in rows}
    validation={(r['tag'],r['arm']):r for r in h.read(D/'validation.json')}
    def base(tag,arm):return h.read(OLD/f'{tag}_base_{arm}.json')
    def chosen(tag,arm):
        if tag=='s67' and arm=='release_vsl90_actual':
            return base(tag,arm) if sel['label']=='base' else by[tag,sel['label'],arm]
        return validation.get((tag,arm),base(tag,arm))
    reports={}
    for tag,name in [('s67','s67_full_observation/response_assessment76.json'),('s73','replication_s73_95/response_assessment95.json')]:
        truth=h.read(h.R/name);entry={}
        for label,select in [('base',base),('chosen',chosen)]:
            a,b=(select(tag,arm) for arm in ('release_actual','release_vsl90_actual'))
            targets=[truth['arms'][arm]['mainline']['FW_E']['actual'] for arm in ('release','release_vsl90')]
            entry[label]=dict(omega=compare(truth['actual_delta_omega_veh_h'],b['ttt']-a['ttt']),
                east=compare(truth['component_delta_veh_h']['FW_E']['actual'],b['east_ttt']-a['east_ttt']),
                ramp_delta=b['ramps_ttt']-a['ramps_ttt'],outside_delta=b['tracked_outside']-a['tracked_outside'],
                terminal_delta=b['east_terminal']-a['east_terminal'],off_delta=off(b)-off(a),
                terminal_error=sum(abs(r['east_terminal']-t['terminal']) for r,t in zip((a,b),targets)),
                off_error=sum(abs(off(r)-t['off']) for r,t in zip((a,b),targets)))
            pick=0 if a['ttt']<=b['ttt'] else 1
            costs=[0.,truth['actual_delta_omega_veh_h']]
            entry[label]['regret']=costs[pick]-min(costs)
        reports[tag]=entry
    truth=h.read(h.R/'rm_restart219/independent230/replay_v2/assessment.json')['arms']
    entry={}
    for label,select in [('base',base),('chosen',chosen)]:
        arms={arm:select('s71',arm) for arm in ('nc','rm','vsl','both')}
        costs={arm:r['native_window_omega_veh_h'] for arm,r in truth.items()}
        pick=min(arms,key=lambda a:arms[a]['ttt'])
        entry[label]=dict(predicted_choice=pick,actual_choice=min(costs,key=costs.get),regret=costs[pick]-min(costs.values()),
            contrasts={b+' minus '+a:compare(costs[b]-costs[a],arms[b]['ttt']-arms[a]['ttt']) for a,b in itertools.combinations(arms,2)})
    reports['s71']=entry
    losses={r['label']:r['loss'] for r in sel['candidates']}
    gates=dict(training_flux=losses[sel['label']]<=.9*losses['base'],
        material=all(reports[t]['chosen']['omega']['passed'] for t in ('s67','s73')) and all(r['passed'] is not False for r in entry['chosen']['contrasts'].values()),
        ranking=all(r['chosen']['regret']<=.5 for r in reports.values()),
        absolute_flux=all(r['chosen'][key]<=1.1*r['base'][key]+1e-7 for tag,r in reports.items() if tag!='s71' for key in ('off_error','terminal_error')))
    pins={**protocol['protected'],**protocol['pins'],protocol['STOP']['path']:protocol['STOP']['sha256']}
    assert all(h.sha(p)==sha for p,sha in pins.items())
    result=dict(status='REQUIRES_AD_AND_FURTHER_VALIDATION' if all(gates.values()) else 'NOT_ADOPTED',
        A=sel['A'],E=sel['E'],gates=gates,reports=reports,
        verification=dict(balances=checks,max_balance=maxbalance,max_cost_error=costerror,initial_and_commands_same=True,protected=True),
        forecasts=len(rows),fits=1,native=0,FZP=0,adopted=False,qualified=False)
    h.save(D/'assessment.json',result)
    print(result['status'],result['A'],result['E'],gates)
    print({t:r['chosen'].get('omega',r['chosen'].get('contrasts')) for t,r in reports.items()})


if __name__=='__main__':main()
