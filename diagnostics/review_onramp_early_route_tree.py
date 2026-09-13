"""Independent XML-only checks; does not import or rerun the audited producer."""
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NETWORK = ROOT / 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'


def main():
    paths = [NETWORK] + [ROOT / ('diagnostics/onramp_early_route_tree_audit.' + ext)
                         for ext in ('py', 'json', 'md')]
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {str(p.relative_to(ROOT)): digest(p) for p in paths}
    root = ET.fromstring(NETWORK.read_bytes())
    links = {x.get('no'): x for x in root.findall('./links/link')}
    decisions = {x.get('no'): x for x in root.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')}
    audited = json.loads(paths[2].read_text(encoding='utf-8'))
    assert before[str(NETWORK.relative_to(ROOT))] == audited['network']['sha256']
    assert digest(paths[1]) == audited['producer_sha256']
    starts = [x.get('start') for x in root.findall("./timeIntervalSets/timeIntervalSet[@no='VEHICLEROUTESTATIC']/timeInts/timeInterval")]
    assert starts == ['0']

    def routes(d):
        return {v.get('no'): v for v in d.findall('./vehRoutSta/vehicleRouteStatic')}

    def weight(v):
        raw = v.get('relFlow')
        if raw == '':
            return Fraction(1)  # Default evidenced separately; not a native readback.
        assert raw.startswith('2 0:')
        return Fraction(raw[4:])

    def path(d, v):
        return [d.get('link')] + [z.get('key') for z in v.findall('./linkSeq/intObjectRef')] + [v.get('destLink')]

    def incoming(road):
        return [{'connector': no, 'from': dict(x.find('fromLinkEndPt').attrib),
                 'to': dict(x.find('toLinkEndPt').attrib)} for no, x in links.items()
                if x.find('toLinkEndPt') is not None and x.find('toLinkEndPt').get('lane').split()[0] == road]

    def polyline_length(no):
        points = links[no].findall('./geometry/linkPolyPts/linkPolyPoint')
        return sum(math.hypot(float(b.get('x')) - float(a.get('x')),
                              float(b.get('y')) - float(a.get('y'))) for a, b in zip(points, points[1:]))

    downstream = decisions['1135']
    child_routes = routes(downstream)
    rows, classifications = [], []
    for parent, original in [('1123', '2'), ('1124', '1'), ('1125', '1')]:
        d = decisions[parent]
        rr = routes(d)
        total = sum(map(weight, rr.values()))
        saved = next(v for v in audited['E8_10681_replacement_trees'] if v['upstream_decision']['no'] == parent)
        assert d.attrib == saved['upstream_decision']
        assert rr[original].attrib == saved['replace_only_route']
        assert [v.attrib for n, v in rr.items() if n != original] == saved['keep_routes']
        weights = []
        for childno, child in child_routes.items():
            joint = weight(rr[original]) * weight(child) / sum(map(weight, child_routes.values()))
            joined = path(d, rr[original]) + path(downstream, child)[1:]
            row = next(v for v in saved['children'] if v['downstream_route'] == childno)
            assert joined == row['path']
            assert Fraction(row['relative_weight_replacing_old_W']['exact']) == joint
            assert Fraction(row['unconditional_probability_at_upstream']['exact']) == joint / total
            assert row['destination'] == {'link': child.get('destLink'), 'pos': child.get('destPos')}
            for i in range(1, len(joined), 2):
                conn = links[joined[i]]
                assert conn.find('fromLinkEndPt').get('lane').split()[0] == joined[i - 1]
                assert conn.find('toLinkEndPt').get('lane').split()[0] == joined[i + 1]
                for endpoint in ('fromLinkEndPt', 'toLinkEndPt'):
                    road, firstlane = conn.find(endpoint).get('lane').split()
                    assert 1 <= int(firstlane) <= len(links[road].findall('./lanes/lane'))
                    assert int(firstlane) + len(conn.findall('./lanes/lane')) - 1 <= len(links[road].findall('./lanes/lane'))
            for i in range(0, len(joined), 2):
                entry = float(d.get('pos')) if i == 0 else float(links[joined[i - 1]].find('toLinkEndPt').get('pos'))
                leave = float(child.get('destPos')) if i == len(joined) - 1 else float(links[joined[i + 1]].find('fromLinkEndPt').get('pos'))
                assert 0 <= entry <= leave <= polyline_length(joined[i]) + 0.001
            weights.append(joint)
            rows.append({'parent': parent, 'old_route': original, 'child1135': childno,
                         'weight': str(joint), 'parent_probability': str(joint / total),
                         'path': joined, 'destination': row['destination']})
        assert sum(weights) == weight(rr[original])
        assert float(rr[original].get('destPos')) < float(downstream.get('pos'))

    relevant = sorted({no for row in rows for no in row['path']} | {'69'})
    behaviors = {x.get('no'): x for x in root.findall('./drivingBehaviors/drivingBehavior')}
    types = {x.get('no'): x for x in root.findall('./linkBehaviorTypes/linkBehaviorType')}
    for no in relevant:
        x = links[no]
        bt = types[x.get('linkBehavType')]
        applied = {bt.get('drivBehavDef')} | {v.get('drivBehav') for v in bt.findall('./vehClassDrivBehav/vehClassDrivingBehavior')}
        assert all(behaviors[b].get('vehRoutDecLookAhead') == 'true' for b in applied)
        assert x.get('direction') == 'ALL'
        # Current XML has no lane subtrees expressing vehicle-class exclusions here.
        assert all(not list(lane) for lane in x.findall('./lanes/lane'))
        classifications.append({'link': no, 'behavior_type': bt.get('no'), 'behaviors': sorted(applied),
                                'lookahead': True, 'consNextTurn': {b: behaviors[b].get('consNextTurn') for b in sorted(applied)}})
    for no in ('1123', '1124', '1125', '1134', '1135'):
        d = decisions[no]
        assert (d.get('allVehTypes'), d.get('routeChoiceMeth'), d.get('combineStaRoutDec')) == ('true', 'STATIC', 'true')
        assert all(v.get('formula') == '' for v in routes(d).values())
    inc68, inc69 = incoming('68'), incoming('69')
    assert {r['connector'] for r in inc68} == {'10625', '10629', '10633'}
    assert all(float(r['to']['pos']) < float(downstream.get('pos')) for r in inc68)
    assert not inc69
    native = {no: [dict(v.attrib) for v in root.findall('./vehicleInputs/vehicleInput') if v.get('link') == no] for no in ('68', '69')}
    assert native['68'] == [] and [r['no'] for r in native['69']] == ['1101']
    upstream_entries = {no: incoming(decisions[no].get('link')) for no in ('1123', '1124', '1125')}
    assert all(float(x['to']['pos']) < float(decisions[no].get('pos')) for no, entries in upstream_entries.items() for x in entries)
    q69 = {no: str(weight(v) / sum(map(weight, routes(decisions['1134']).values()))) for no, v in routes(decisions['1134']).items()}
    out = {'schema': 'onramp-early-route-tree-peer-review/v1', 'reviewed_at_utc': datetime.now(timezone.utc).isoformat(),
           'status': 'XML algebra and topology checks pass; live equivalence and incremental lookahead benefit not established',
           'sources_sha256': before, 'reviewer_source_sha256': digest(Path(__file__)), 'nine_expansions': rows,
           'static_route_interval_starts_sec': starts, 'decisions_all_types_static_combine_true': ['1123', '1124', '1125', '1134', '1135'],
           'formulas_empty': True, 'physical_behavior_join': classifications,
           'incoming68': inc68, 'incoming69': inc69, 'upstream_entries_before_decisions': upstream_entries,
           'native_inputs': native, 'retain1134_probabilities': q69,
           'length_check': 'XML XY polyline, 1mm rounding tolerance; not a COM length measurement',
           'limitations': ['p*q preserves a local routing-destination probability conditional on eligible parent choice; not realized full-trip OD',
                           'Same seed does not prove correspondence of random draws after route-tree restructuring; engine stream details not assumed',
                           'Existing Combine and LookAhead make newly earlier route knowledge an unproven mechanism',
                           'Complete live-route coverage, route default readback, and per-vehicle destination coupling not tested'],
           'execution': {'model': 0, 'COM': 0, 'VISSIM': 0, 'FZP_scan': 0, 'production_writes': 0},
           'source_changes': [p for p, h in before.items() if digest(ROOT / p) != h]}
    assert not out['source_changes']
    (ROOT / 'diagnostics/onramp_early_route_tree_peer_review.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'pass': True, 'children': len(rows), 'behavior_links': len(classifications), 'source_changes': out['source_changes']}))


if __name__ == '__main__':
    main()
