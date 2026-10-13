"""Partition existing native boundary events by the common initial roster.

This conditions on no future action/outcome. It is diagnostic, not an objective
change or a counterfactual that removes later arrivals and their congestion.
"""
from collections import defaultdict
from pathlib import Path
import gzip,hashlib,json
from evaluation.controllers.control_area_objective import physical_membership_from_ledger

HERE=Path(__file__).resolve().parent;A=HERE.parent;ROOT=HERE.parents[4]
CACHE=Path('E:/VISSIM_analysis/20261010_exit_timing309')
RUNS=dict(hold=Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/decisions_sdmpc31_g_2400_hold_s29'),
          city=Path('E:/VISSIM_runs/20261010_urbanrm269_cityonly289_s29/selected/decisions_sdmpc31_g_2400_selected_s29'))
PINS={}
def raw(p):
    p=Path(p);b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return b
def read(p):return json.loads(raw(p))

def main():
    assert not (HERE/'cohorts.json').exists()
    done=read(CACHE/'completion.json');report=read(HERE/'assessment.json')
    assert done['status']=='complete_closed_exit_timing_cache'
    records={a:read(p/'state_002400.json')['vehicle_records'] for a,p in RUNS.items()}
    assert records['hold']==records['city'];r=records['hold']
    initial={v['veh_no']:v for v in r['records']}
    assert r['complete'] and len(initial)==r['record_count']==r['collection_count_before']==r['collection_count_after']
    assert r['unobservable_count']==r['external_source_count']==0
    tuning=read(A/'flow279/config_10686_free.json')
    inside=physical_membership_from_ledger(read(ROOT/tuning['control_area_objective']['membership_path']))
    assert all(str(v['link_no']) in inside for v in initial.values())
    def category(veh):
        if veh not in initial:return 'absent_initial_roster'
        return 'initial_inside' if inside[str(initial[veh]['link_no'])] else 'initial_outside'
    counts={c:sum(category(v)==c for v in initial) for c in ('initial_inside','initial_outside')}
    cats=('initial_inside','initial_outside','absent_initial_roster')
    kinds=('appeared_or_reappeared_inside','observed_entry','observed_exit','disappeared_inside')
    signs={k:(1 if k in kinds[:2] else -1) for k in kinds}
    arms={};edges={}
    topology=read(A/'exit_timing309/assessment.json')['native_observed_pair_topology']
    for arm in RUNS:
        payload=raw(done['arms'][arm]['cache']);assert hashlib.sha256(payload).hexdigest()==done['arms'][arm]['sha256']
        events=json.loads(gzip.decompress(payload))['events']
        rows={c:{k:dict(count=0,cost=0.) for k in kinds} for c in cats}
        by_edge=defaultdict(lambda:{c:dict(count=0,cost=0.) for c in cats})
        for e in events:
            assert 2395.1<=e['low_sec']<e['high_sec']<=2850 and e['kind'] in signs
            c=category(e['vehicle']);cost=signs[e['kind']]*(2850-e['mid_sec'])/3600
            row=rows[c][e['kind']];row['count']+=1;row['cost']+=cost
            if e['kind']=='observed_exit':
                witness=topology[e['from_link']+'->'+e['to_link']]
                key='->'.join(witness['edge']) if witness['edge'] else 'unresolved_native_topology'
                by_edge[key][c]['count']+=1;by_edge[key][c]['cost']+=cost
        arms[arm]=rows;edges[arm]=dict(by_edge)
        # Cache merges terminal-inferred and unresolved disappearance. Preserve
        # that aggregation here, with the separate totals in assessment.json.
        expected=report['native']['arms'][arm]['events']
        for kind in kinds:
            sources={'appeared_or_reappeared_inside':['appeared_inside_events','reappeared_inside_events'],
                     'observed_entry':['observed_entry_events'],'observed_exit':['observed_exit_events'],
                     'disappeared_inside':['terminal_exit_inferred_events','unresolved_inside_disappearances']}[kind]
            assert sum(rows[c][kind]['count'] for c in cats)==sum(expected[k]['vehicles'] for k in sources)
            assert abs(sum(rows[c][kind]['cost'] for c in cats)-sum(expected[k]['cost'] for k in sources))<1e-7
    deltas={c:{k:{f:arms['city'][c][k][f]-arms['hold'][c][k][f] for f in ('count','cost')} for k in kinds} for c in cats}
    costs={c:sum(v['cost'] for v in row.values()) for c,row in deltas.items()}
    assert abs(sum(costs.values())-report['native']['delta_ttt'])<1e-7
    ranked=[]
    for key in edges['hold'].keys()|edges['city'].keys():
        delta={c:{f:edges['city'].get(key,{}).get(c,{}).get(f,0)-edges['hold'].get(key,{}).get(c,{}).get(f,0) for f in ('count','cost')} for c in cats}
        ranked.append(dict(edge=key,cohort_delta=delta,initial_cost=sum(delta[c]['cost'] for c in cats[:2]),total_cost=sum(delta[c]['cost'] for c in cats)))
    ranked.sort(key=lambda x:-abs(x['initial_cost']))
    result=dict(status='complete_exact_native_roster_partition327',initial_roster_size=len(initial),initial_counts=counts,
        event_accounts=arms,event_delta=deltas,delta_TTT_veh_h_by_initial_cohort=costs,
        total_delta_TTT_veh_h=sum(costs.values()),top_initial_exit_delays=ranked[:12],
        source_pins=PINS,new_forecasts=0,new_native=0,new_fzp=0,
        limitations=['All original future vehicles and congestion remain in the actual runs; cohort accounting does not isolate a no-arrival causal effect.',
                    'IDs absent at2400 are not matched as the same vehicle across divergent arms.',
                    'Unresolved disappearance and terminal inference cannot be separated by cohort from this cache; grouped explicitly.',
                    'This diagnostic does not replace wholeOmega TTT or change the MPC objective.'])
    (HERE/'cohorts.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('ROSTER',len(initial),counts,'TTT_DELTAS',costs,'TOTAL',sum(costs.values()))
    print('TOP_INITIAL_EXIT',json.dumps(ranked[:6],ensure_ascii=False))

if __name__=='__main__':main()
