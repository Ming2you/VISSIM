from pathlib import Path
HERE=Path(__file__).resolve().parent;H=HERE.parent
text=(H/'connector_stage/assess.py').read_text(encoding='utf8')
text=text.replace("status='complete_one_geometry_candidate'","status='complete_one_connector_lane_composition'").replace('tests=33','tests=45')
anchor="    PINS[str(Path(__file__))]"
extra='''    attribution=read(H/'connector_attribution/assessment.json')
    original=read(HERE/'forecast2400/state.json')['known_legsplit_route_state']['cohorts']
    original=[c for c in original if c['target']=='RM_C10681']
    original_by_order={tuple(c['lane68']['order']):c for c in original}
    assert len(original_by_order)==len(original)==40
    group=lambda c:'initial_RM_lane'+next(iter(c['lane68']['shares']))
    grouped_initial={g:sum(c['vehicles'] for c in original if group(c)==g) for g in {group(c) for c in original}}
    response_groups={}
    for arm,record in candidate.items():
        previous=grouped_initial.copy();bins=[]
        for i,cohorts in enumerate(record['known_endpoint_cohorts']):
            still={g:0. for g in previous}
            for c in cohorts:
                if c['target']!='RM_C10681' or c['source']!='initial_current_route' or 'lane68' not in c:continue
                initial=original_by_order.get(tuple(c['lane68']['order']))
                if initial is not None:still[group(initial)]+=c['vehicles']
            entered={g:previous[g]-still[g] for g in still}
            assert all(n>=-1e-8 for n in entered.values())
            native=attribution['arms'][arm][i]['native']
            total=next(x['arrival10681']['predicted'] for x in comparisons if x['arm']==arm and x['start_sec']==2400+150*i)
            bins.append(dict(start_sec=2400+150*i,native=native['by_initial_group'],predicted_initial_entries=entered,
                predicted_noninitial_entries=total-sum(entered.values()),predicted_initial_remaining=still,
                native_initial_disposition=native['initial_RM_disposition']))
            previous=still
        response_groups[arm]=bins
    result['initial_RM_cohort_attribution']=response_groups
'''
assert text.count(anchor)==1
text=text.replace(anchor,extra+anchor)
(HERE/'assess.py').write_text(text,encoding='utf8')
print('Assessment prepared; same native validation and exact initial-order attribution')
