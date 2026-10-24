"""Propose probability-preserving route trees from XML; no INPX writes/runs."""
from __future__ import annotations
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NETWORK = ROOT / 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'
RAMPS = ('10480', '10482', '10646', '10644', '10639', '10681', '10490', '10484')
DOWNSTREAM = ('1134', '1135', '1136', '1137')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    before = sha(NETWORK)
    root = ET.fromstring(NETWORK.read_bytes())
    links = {x.get('no'): x for x in root.findall('./links/link')}
    decisions = {x.get('no'): x for x in root.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')}
    starts = [x.get('start') for x in root.findall("./timeIntervalSets/timeIntervalSet[@no='VEHICLEROUTESTATIC']/timeInts/timeInterval")]
    if starts != ['0']:
        raise ValueError('This proposal requires the observed single static-route interval')

    def frac(f):
        return {'exact': str(f), 'value': float(f)}

    def route_path(d, v):
        return [d.get('link')] + [x.get('key') for x in v.findall('./linkSeq/intObjectRef')] + [v.get('destLink')]

    def weight(v):
        raw = v.get('relFlow', '').strip()
        if not raw:
            return Fraction(1)
        m = re.fullmatch(r'2 0:([0-9]+(?:\.[0-9]+)?)', raw)
        if not m:
            raise ValueError(f'Unrecognized time-relative-flow {raw}')
        return Fraction(m[1])

    def routes(d):
        return d.findall('./vehRoutSta/vehicleRouteStatic')

    def total(d):
        return sum((weight(v) for v in routes(d)), Fraction())

    def ep(x, name):
        e = x.find(name)
        if e is None:
            return None
        road, lane = e.get('lane').split()
        return {'link': road, 'position_m': float(e.get('pos')),
                'lanes': list(range(int(lane), int(lane) + len(x.findall('./lanes/lane'))))}

    def validate_path(path, start, end):
        errors = []
        for i, no in enumerate(path):
            x = links[no]
            f, t = ep(x, 'fromLinkEndPt'), ep(x, 'toLinkEndPt')
            if f is not None:
                if i and f['link'] != path[i - 1]:
                    errors.append(f'{no}: from mismatch')
                if i + 1 < len(path) and t['link'] != path[i + 1]:
                    errors.append(f'{no}: to mismatch')
            else:
                entry = start if i == 0 else ep(links[path[i - 1]], 'toLinkEndPt')['position_m']
                leave = end if i == len(path) - 1 else ep(links[path[i + 1]], 'fromLinkEndPt')['position_m']
                if entry > leave:
                    errors.append(f'{no}: backwards {entry}>{leave}')
        return errors

    stem_rows, ramp_rows = [], []
    for dn in DOWNSTREAM:
        d = decisions[dn]
        stem, position = d.get('link'), float(d.get('pos'))
        incoming = []
        for no, x in links.items():
            t = ep(x, 'toLinkEndPt')
            if t and t['link'] == stem:
                incoming.append({'connector': no, 'from': ep(x, 'fromLinkEndPt'), 'to': t,
                                 'before_decision': t['position_m'] < position})
        parents = []
        for upstream in decisions.values():
            if upstream is d:
                continue
            for v in routes(upstream):
                if v.get('destLink') == stem:
                    parents.append({'decision': upstream.get('no'), 'source_link': upstream.get('link'),
                                    'source_position_m': float(upstream.get('pos')), 'route': v.get('no'),
                                    'route_end_position_m': float(v.get('destPos')),
                                    'end_before_decision': float(v.get('destPos')) < position,
                                    'upstream_weight': frac(weight(v)), 'upstream_total': frac(total(upstream)),
                                    'upstream_turn_probability': frac(weight(v) / total(upstream)),
                                    'path': route_path(upstream, v)})
        inputs = [{'attributes': dict(v.attrib),
                   'volume_schedule': [dict(t.attrib) for t in v.findall('./timeIntVehVols/timeIntervalVehVolume')]}
                  for v in root.findall('./vehicleInputs/vehicleInput') if v.get('link') == stem]
        branches = []
        for v in routes(d):
            p = route_path(d, v)
            branches.append({'route': dict(v.attrib), 'path': p, 'weight': frac(weight(v)),
                             'probability': frac(weight(v) / total(d)),
                             'empty_relFlow_default_one': not bool(v.get('relFlow', '').strip())})
            for ramp in RAMPS:
                if ramp in p:
                    ramp_rows.append({'physical_ramp': ramp, 'from': ep(links[ramp], 'fromLinkEndPt'),
                                      'to': ep(links[ramp], 'toLinkEndPt'), 'downstream_decision': dn,
                                      'decision_source': stem, 'decision_position_m': position,
                                      'route_no': v.get('no'), 'ordered_path': p,
                                      'q_given_decision': frac(weight(v) / total(d)),
                                      'upstream_parents': parents, 'source_input_ids': [x['attributes']['no'] for x in inputs]})
        stem_rows.append({'decision': dict(d.attrib), 'route_weight_sum': frac(total(d)),
                          'branches': branches, 'incoming': incoming, 'upstream_parents': parents,
                          'native_inputs': inputs})

    # Exact product expansion of the three upstream legs feeding1135.
    d = decisions['1135']
    expansions = []
    for upno, oldno in [('1123', '2'), ('1124', '1'), ('1125', '1')]:
        up = decisions[upno]
        old = next(v for v in routes(up) if v.get('no') == oldno)
        oldpath, W, Q = route_path(up, old), weight(old), total(d)
        children = []
        for branch in routes(d):
            downstream_path = route_path(d, branch)
            path = oldpath + downstream_path[1:]
            w = W * weight(branch) / Q
            incoming = ep(links[oldpath[-2]], 'toLinkEndPt')
            leaving = ep(links[downstream_path[1]], 'fromLinkEndPt')
            child = {'symbolic_id': f'{upno}:{oldno}x1135:{branch.get("no")}',
                     'old_route': oldno, 'downstream_route': branch.get('no'),
                     'relative_weight_replacing_old_W': frac(w),
                     'unconditional_probability_at_upstream': frac(w / total(up)),
                     'path': path, 'destination': {'link': branch.get('destLink'), 'pos': branch.get('destPos')},
                     'initial_stem_lanes': incoming['lanes'], 'next_branch_lanes': leaving['lanes'],
                     'direct_lane_overlap': sorted(set(incoming['lanes']) & set(leaving['lanes'])),
                     'path_errors': validate_path(path, float(up.get('pos')), float(branch.get('destPos')))}
            children.append(child)
        unchanged = [v for v in routes(up) if v is not old]
        child_total = sum((W * weight(v) / Q for v in routes(d)), Fraction())
        expansions.append({'upstream_decision': dict(up.attrib), 'replace_only_route': dict(old.attrib),
                           'keep_routes': [dict(v.attrib) for v in unchanged], 'children': children,
                           'checks': {'child_weight_sum_equals_old': child_total == W,
                                      'total_weight_unchanged': child_total + sum((weight(v) for v in unchanged), Fraction()) == total(up),
                                      'unique_child_paths': len({tuple(v['path']) for v in children}) == len(children),
                                      'all_paths_ordered_connected': not any(v['path_errors'] for v in children)}})
    all_children = [c for x in expansions for c in x['children']]
    target_incoming = next(x for x in stem_rows if x['decision']['no'] == '1135')['incoming']
    covered_incoming = {x['children'][0]['path'][1] for x in expansions}
    behavior = root.find("./drivingBehaviors/drivingBehavior[@no='1']")
    out = {'schema': 'onramp-early-route-tree-proposal/v1', 'network': {'path': str(NETWORK.relative_to(ROOT)), 'sha256': before},
           'producer_sha256': sha(Path(__file__)), 'production_modified': False, 'model_execution': False, 'com_access': False,
           'static_route_interval': {'starts_sec': starts, 'end': 'simulation end', 'time_key': '2 0'},
           'relative_flow_semantics': {'empty_string': 'Implicit default1, same interpretation as canonical offramp_routing.derive_prior; preserve raw and require native RelFlow(1) readback before any deletion',
                                       'not_realized_passage_ratio': True, 'all_ratios_conditional_on_reaching_eligible_decision': True},
           'driving_behavior1': dict(behavior.attrib), 'ramps': ramp_rows, 'stems': stem_rows,
           'E8_10681_replacement_trees': expansions,
           'E8_10681_coverage': {'incoming_connectors': sorted(x['connector'] for x in target_incoming),
                                'covered_by_exact_upstream_routes': sorted(covered_incoming),
                                'missing_incoming': sorted({x['connector'] for x in target_incoming} - covered_incoming),
                                'new_children': len(all_children), 'path_errors': [e for c in all_children for e in c['path_errors']],
                                'native_input_on68': False,
                                'runtime_eligibility_limit': 'Structural coverage is not proof that every live vehicle has an eligible upstream route; inspect route-bearing vehicle records before deleting1135.'},
           'E8_10639_scope': {'native_decision': '1134', 'route': '3', 'probability': '12/65',
                              'native_input': '1101', 'source': '69', 'source_incoming_connectors': [],
                              'existing_upstream_leg_decision': None,
                              'proposal': 'Keep1134 four-way tree; it already fixes10639 destination at69@48.857m. Any earlier source-choice experiment must replace all four routes on69 and preserve input1101, not delete the decision without coverage.'},
           'separate_city_case': {'vehicle': '4725', 'native_route': '1126:1', 'destination_connector': '10635',
                                 'destination': '47', 'is_onramp': False},
           'required_pre_edit_guards': ['Read back blank RelFlow defaults and effective Combine/LooKAhead values in actual engine',
                                       'Verify complete live upstream route coverage including all vehicle classes',
                                       'Preserve unchanged turn probabilities, input schedules, destinations, lane maps, signal plans and1s records',
                                       'No second downstream draw for an expanded route; keep/delete decisions only after coverage proof',
                                       'Compare fixed actual controls; probability preservation does not imply identical same-seed vehicle choices or improved lane access'],
           'source_changes': [] if sha(NETWORK) == before else ['network']}
    target = ROOT / 'diagnostics/onramp_early_route_tree_audit.json'
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'ramps': len(ramp_rows), 'E8_children': len(all_children),
                      'coverage': out['E8_10681_coverage'], 'checks': [x['checks'] for x in expansions],
                      'source_changes': out['source_changes']}))


if __name__ == '__main__':
    main()
