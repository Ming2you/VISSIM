"""Reuse completed predictions and native per-link residence; no rollout.

Separate initial chosen RM stock, initial prechoice stock, and later inflow.
Correct the earlier initial-support W_out cost map to its complete path.
"""
from pathlib import Path
import hashlib,json,sys

HERE=Path(__file__).resolve().parent;H=HERE.parent
sys.path.insert(0,str(H))
from qualify_native2400 import validate_scope
PINS={}
def read(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(b)

def main():
    target=HERE/'response_attribution.json'
    assert not target.exists()
    validate_scope(read(H/'native2400_analysis/summary.json'),read(H/'native2400_analysis/observed_input_qualification.json'))
    comparison=read(HERE/'comparison.json')
    attribution=read(H/'connector_attribution/assessment.json')
    initial=read(HERE/'forecast2400/state.json')['known_legsplit_route_state']['cohorts']
    network=read(HERE/'forecast2400/network.json')
    spec=network['known_legsplit_routes'];ramp='RM_C10681'
    prior=spec['future_choice_weights'][ramp]
    initial_prechoice=sum(c['vehicles'] for c in initial if c['target']=='prechoice')
    assert initial_prechoice==35 and abs(prior-.6)<1e-12
    footprint={68,121,10772,10625,10629,10633}
    native={};correction={}
    for arm in ('hold','selected'):
        m=read(H/f'native2400_analysis/{arm}/area_metrics.json')
        links=m['physical_link_residence']
        # A zero-observation link is absent from this sparse map; it contributes
        # zero sampled residence, not a claim of zero traversals.
        for link in footprint|{10681}:
            if str(link) in links:assert links[str(link)]['inside']
        cost=lambda ids:sum(links.get(str(i),{}).get('ttt_veh_h',0.) for i in ids)
        native[arm]={'full_W_out':cost(footprint),'ramp10681':cost({10681})}
        correction[arm]=cost({10772})
    native_delta={k:native['selected'][k]-native['hold'][k] for k in native['hold']}
    models={};groups={}
    for label,folder in [('baseline',H/'sc1_supply'),('connector',H/'connector_stage'),('combined',HERE)]:
        s=read(folder/'forecast2400/summary.json')['results']
        costs={a:{'full_W_out':s[a]['costs_by_stock']['storage:SC1004_W_out'],
                  'ramp10681':s[a]['costs_by_stock']['ramp:RM_C10681']} for a in ('hold','selected')}
        delta={k:costs['selected'][k]-costs['hold'][k] for k in native_delta}
        models[label]=dict(costs_by_arm=costs,delta=delta,delta_error={k:delta[k]-native_delta[k] for k in delta})
        if label!='combined':continue
        for arm in ('hold','selected'):
            previous_pre_entered=0.;rows=[]
            known_by_order={tuple(c['lane68']['order']) for c in initial if c['target']==ramp}
            for i,cs in enumerate(s[arm]['known_endpoint_cohorts']):
                remaining_pre=sum(c['vehicles'] for c in cs if c['source']=='initial_current_route' and c['target']=='prechoice')
                # RM-destined cohorts retain source and order through lane changes
                # and debit. Unlike free/west cohorts they are not coalesced.
                remaining_pre_rm=sum(c['vehicles'] for c in cs if c['source']=='initial_current_route' and c['target']==ramp
                    and tuple(c['lane68']['order']) not in known_by_order)
                generated=(initial_prechoice-remaining_pre)*prior
                cumulative_entered=generated-remaining_pre_rm
                entered_pre=cumulative_entered-previous_pre_entered
                assert entered_pre>=-1e-7 and 0<=generated<=initial_prechoice*prior+1e-7
                old=comparison['initial_RM_cohort_attribution'][arm][i]
                known=sum(old['predicted_initial_entries'].values())
                later=old['predicted_noninitial_entries']-entered_pre
                assert later>=-1e-7
                actual=attribution['arms'][arm][i]['native']['by_initial_group']
                rows.append(dict(start_sec=2400+150*i,
                    predicted_initial_known_RM=known,predicted_initial_prechoice=entered_pre,predicted_later_inflow=later,
                    native_initial_known_RM=sum(v for k,v in actual.items() if k.startswith('initial_RM_lane')),
                    native_initial_other_W_out=actual.get('initial_other_W_out',0),native_later_inflow=actual.get('later_W_out_inflow',0),
                    native_unassigned_tail=actual.get('unassigned_mer_tail',0),
                    predicted_initial_prechoice_remaining=remaining_pre,
                    predicted_initial_prechoice_RM_remaining=remaining_pre_rm))
                previous_pre_entered=cumulative_entered
            groups[arm]=rows
    PINS[str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result=dict(status='complete',new_rollouts=0,new_native=0,new_coefficients=0,
        full_W_out_domain=sorted(footprint),native_delta_veh_h=native_delta,
        native10772_cost_by_arm_veh_h=correction,models=models,arrival_groups=groups,
        limitations=['Same previously used seed29/2400 state, joint city and RM commands; not isolated RM or independent validation.',
        'Native sampled residence5s versus finer model integration. Common2400 prefix cancels for cost differences.',
        'Initial-other native group is observed ownership, not a proof of initial prechoice for every vehicle.',
        'Finalselected one MER tail has no ID and remains unassigned.',
        'Improved local cost is insufficient to qualify whole Omega gain or arrival timing.'],source_pins=PINS)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('native_delta_veh_h','native10772_cost_by_arm_veh_h','models','arrival_groups')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
