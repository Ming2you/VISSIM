"""Compare retained local states to saved native snapshots; no prediction run."""
import ast
import json
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

from assess import HERE, ROOT, REVIEW, I, PINS, read


def main():
    assert not (HERE/'local_state_audit.json').exists()
    native = read(REVIEW/'local10643_receiver/native_audit.json')
    heads = read(REVIEW/'local10643_receiver/head_audit.json')
    manifest = read(REVIEW/'retained10638/candidate_manifest.json')
    path = ROOT/manifest['sources']['network']['path']
    import hashlib
    PINS[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    assert PINS[str(path)] == manifest['sources']['network']['sha256']
    network = ET.parse(path).getroot()
    links = {int(x.get('no')):x for x in network.findall('./links/link')}
    scenarios = [
        ('47hold','closedloop_recorded2700_select_check_trace10681_entry10643','held_actual'),
        ('47selected','closedloop_recorded2700_select_check_trace10681_entry10643','selected'),
        ('43nc','closedloop_recorded2250_lever450_trace10681_retained43','held_actual')]
    cases = {}
    for name,folder,key in scenarios:
        trace = read(I/folder/(key+'_RM_C10681_trace.json.gz'))
        local = trace['local_receiver_diagnostics']
        observed = {s['time_sec']:s for s in native['cases'][name]}
        snapshots = []
        for state in local['states']:
            grouped = defaultdict(Counter)
            for cell in state['cells']:
                for packet in cell['packets']:
                    grouped[tuple(cell['cell'][:2])][str(packet['label'][0])] += packet['vehicles']
            rows = []
            sample = observed[state['time_sec']]
            for (road,lane),counts in sorted(grouped.items()):
                actual = sample['roads'][str(road)]['lanes'].get(str(lane),0)
                rows.append(dict(road=road,lane=lane,native_stock=actual,
                    model_stock=sum(counts.values()),model_by_destination=dict(counts)))
            snapshots.append(dict(time_sec=state['time_sec'],lanes=rows))
        actual_heads = defaultdict(Counter)
        for window in heads['cases'][name]:
            for h in window['heads']:
                if h['link']!='71':continue
                actual_heads[h['lane']].update(green_crossings=h['qualified_crossings'],
                    crossings=h['crossings'],green_sec=h['green_sec'],ambiguous=h['boundary_ambiguous'])
        model_exit = Counter()
        for row in local['resources']:
            if row['kind']!='lane_urban_sending':continue
            source = ast.literal_eval(row['resource'])
            if source[0]!=71:continue
            for target,n in row['accepted_by_source_veh'].items():
                event = ast.literal_eval(target)
                if event[0]=='exit':model_exit[source[1],event[1]] += n
        cases[name] = dict(snapshots=snapshots,head_comparison=[dict(lane=g,**actual_heads[g],
                modeled_connector=10634 if g<=3 else 10635,
                model_corresponding_connector_outflow=model_exit[g,10634 if g<=3 else 10635],
                model_earlier_side_exit10642=model_exit[g,10642]) for g in (1,2,3,4,5)])
    cache = read(REVIEW/'lane10643_native/rows.json.gz')
    previous, changes = {}, []
    for row in cache['rows']:
        old=previous.get(row[1]);previous[row[1]]=row
        if old and row[0]-old[0]<5.0001 and row[2]==old[2]==126 and row[3]!=old[3]:
            changes.append(dict(vehicle=row[1],from_sec=old[0],to_sec=row[0],
                before_position=old[4],after_position=row[4],from_lane=old[3],to_lane=row[3],
                route_decision=row[6],route_number=row[7],
                available_before_cutoff=row[0]<=2700.))
    result=dict(status='completed_saved_local_state_audit',cases=cases,
        native_126_lane_changes=changes,source_pins=PINS,
        source_network_sha256=manifest['sources']['network']['sha256'],
        link_behaviour_types={str(n):links[n].get('linkBehavType') for n in (126,71,10643)},
        new_forecasts=0,new_native=0,new_fzp_scan=0,fit=0,
        limitations=['Native heads at about78.9m and modeled connector endpoints near81m are different planes.',
            'The earlier10642 side exit is reported separately; it is not included in the corresponding model head outflow.',
            'Five-second lane observations can omit intermediate changes; after-cutoff events are evaluation evidence only.',
            'A missing class of local lane redistribution is a hypothesis, not proof that one rate parameter solves it.'])
    (HERE/'local_state_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for name,row in cases.items():
        lane=next(r for r in row['snapshots'][-1]['lanes'] if r['road']==126 and r['lane']==2)
        print(name,'final126lane2',lane)
        print('HEADS',row['head_comparison'])
    print('CHANGES',len(changes),'past',sum(c['available_before_cutoff'] for c in changes))


if __name__=='__main__':
    main()
