"""Build isolated byte-preserving XML experiment arms; stdlib, no model/COM.

Route expansion is a prepared hypothesis, never run-ready before native
RelFlow/Combine/vehicle-eligibility checks. Existing networks are never written.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NETWORK = ROOT / 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'
NETWORK_SHA = '085a10c71874e897083c97097af8fa3f1f08da1ef7416fef2f7cfbedabdfc317'
DEFAULT_OUTPUT = ROOT / 'diagnostics/fixed_beta300v3_network_arms_v1'
PARENTS = {'1123': '2', '1124': '1', '1125': '1'}
CHILD_IDS = {'2': '4', '3': '5', '4': '6'}
PIN_PATHS = (
    'diagnostics/onramp_early_route_tree_audit.json',
    'diagnostics/onramp_early_route_tree_peer_review.json',
    'diagnostics/fixed_beta300v3_route_experiment_design.md',
    'diagnostics/fixed_beta300v3_900_signal_profile/config.json',
    'diagnostics/fixed_beta300v3_900_signal_profile/frozen_greens.json',
    'diagnostics/fixed_beta300v3_900_signal_profile/manifest.json',
    'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1',
    'scripts/run_real_world_stackelberg_controller.vbs',
    'evaluation/controllers/vissim_stackelberg_adapter.py',
    'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json',
    'outputs/signal_group_actuation_plan_mainline_20260825.json',
)
ACTION_DIR = ('evaluation/runs/codex_contract_beta300_s13_1050_v3_20260910/'
              'decisions_codex_contract_beta300_s13_1050_v3_20260910/')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def element_span(raw, tag, no):
    pattern = (rb'<' + tag.encode() + rb'\b(?=[^>]*\bno="' + no.encode()
               + rb'")[^>]*>.*?</' + tag.encode() + rb'>')
    matches = list(re.finditer(pattern, raw, re.S))
    require(len(matches) == 1, f'Expected one {tag}:{no}, found {len(matches)}')
    return matches[0]


def attribute(raw, name, before, after):
    pattern = rb'\b' + name.encode() + rb'="' + re.escape(before.encode()) + rb'"'
    updated, count = re.subn(pattern, lambda _: name.encode() + b'="' + after.encode() + b'"', raw)
    require(count == 1, f'Attribute contract changed: {name}={before}')
    return updated


def splice(raw, edits):
    """Copy every unedited source byte; retain exact edit and outside hashes."""
    pieces, records, outside = [], [], []
    old_cursor = new_cursor = 0
    for start, end, replacement, label in sorted(edits):
        require(old_cursor <= start < end <= len(raw), 'Overlapping/out-of-range edit')
        unchanged = raw[old_cursor:start]
        pieces.append(unchanged)
        outside.append({'source_range': [old_cursor, start],
                        'output_range': [new_cursor, new_cursor + len(unchanged)],
                        'size': len(unchanged), 'sha256': sha(unchanged)})
        new_cursor += len(unchanged)
        records.append({'label': label, 'source_range': [start, end],
                        'output_range': [new_cursor, new_cursor + len(replacement)],
                        'before_sha256': sha(raw[start:end]), 'after_sha256': sha(replacement),
                        'before_utf8': raw[start:end].decode('utf-8'),
                        'after_utf8': replacement.decode('utf-8')})
        pieces.append(replacement)
        new_cursor += len(replacement)
        old_cursor = end
    last = raw[old_cursor:]
    outside.append({'source_range': [old_cursor, len(raw)],
                    'output_range': [new_cursor, new_cursor + len(last)],
                    'size': len(last), 'sha256': sha(last)})
    pieces.append(last)
    result = b''.join(pieces)
    for row in outside:
        a, b = row['source_range']; c, d = row['output_range']
        require(raw[a:b] == result[c:d], 'Unedited byte range changed')
    return result, {'edits': records, 'outside_ranges': outside,
                    'all_outside_rawbytes_exact': True}


def tree_value(node):
    # Whitespace formatting is separately checked byte-for-byte outside edits.
    return (node.tag, tuple(sorted(node.attrib.items())), (node.text or '').strip(),
            tuple(tree_value(child) for child in node))


def routes(decision):
    return decision.findall('./vehRoutSta/vehicleRouteStatic')


def weight(route):
    raw = route.get('relFlow', '')
    if raw == '':
        return Fraction(1)  # Recorded default interpretation; COM still pending.
    match = re.fullmatch(r'2 0:([0-9]+(?:\.[0-9]+)?)', raw)
    require(match is not None, f'Unknown static interval/RelFlow: {raw!r}')
    return Fraction(match[1])


def exact_decimal(value):
    text = format(Decimal(value.numerator) / Decimal(value.denominator), 'f')
    require(Fraction(text) == value, 'Weight lacks an exact finite decimal representation')
    return text.rstrip('0').rstrip('.') if '.' in text else text


def route_path(decision, route):
    return [decision.get('link')] + [n.get('key') for n in route.findall('./linkSeq/intObjectRef')] + [route.get('destLink')]


def endpoint(link, which):
    point = link.find(which)
    require(point is not None, f'{link.get("no")} has no {which}')
    road, lane = point.get('lane').split()
    return road, int(lane), float(point.get('pos'))


def length(link):
    points = [tuple(float(p.get(k, '0')) for k in ('x', 'y', 'zOffset'))
              for p in link.findall('./geometry/linkPolyPts/linkPolyPoint')]
    require(len(points) >= 2, f'No polyline: {link.get("no")}')
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


def validate_route(decision, route, links):
    path = route_path(decision, route)
    transitions, lane_moves = [], []
    for i, no in enumerate(path):
        require(no in links, f'Unknown route link {no}')
        link = links[no]
        require(link.get('direction') == 'ALL', f'Unreviewed direction restriction: {no}')
        lanes = link.findall('./lanes/lane')
        require(lanes and all(not list(lane) and set(lane.attrib) <= {'width'} for lane in lanes),
                f'Unreviewed lane/class restriction: {no}')
        if link.find('fromLinkEndPt') is not None:
            require(0 < i < len(path) - 1, 'Connector cannot be route source/destination here')
            fr, fl, fp = endpoint(link, 'fromLinkEndPt')
            to, tl, tp = endpoint(link, 'toLinkEndPt')
            require((fr, to) == (path[i-1], path[i+1]), f'Disconnected route at {no}')
            require(1 <= fl and fl + len(lanes)-1 <= len(links[fr].findall('./lanes/lane')),
                    f'From-lane range invalid at {no}')
            require(1 <= tl and tl + len(lanes)-1 <= len(links[to].findall('./lanes/lane')),
                    f'To-lane range invalid at {no}')
            require(0 <= fp <= length(links[fr]) + .001 and 0 <= tp <= length(links[to]) + .001,
                    f'Connector endpoint outside road polyline at {no}')
            transitions.append({'connector': no, 'from_link': fr, 'from_pos': fp,
                                'to_link': to, 'to_pos': tp,
                                'lane_pairs': [[fl+j, tl+j] for j in range(len(lanes))]})
        else:
            entry = float(decision.get('pos')) if i == 0 else endpoint(links[path[i-1]], 'toLinkEndPt')[2]
            leave = float(route.get('destPos')) if i == len(path)-1 else endpoint(links[path[i+1]], 'fromLinkEndPt')[2]
            require(0 <= entry <= leave + 1e-9 and leave <= length(link) + .001,
                    f'Backwards/out-of-range road traversal at {no}')
            if 0 < i < len(path)-1:
                prev, nxt = links[path[i-1]], links[path[i+1]]
                in_lane = endpoint(prev, 'toLinkEndPt')[1]
                out_lane = endpoint(nxt, 'fromLinkEndPt')[1]
                incoming = set(range(in_lane, in_lane + len(prev.findall('./lanes/lane'))))
                outgoing = set(range(out_lane, out_lane + len(nxt.findall('./lanes/lane'))))
                lane_moves.append({'road': no, 'entry_lanes': sorted(incoming), 'exit_lanes': sorted(outgoing),
                                   'same_lane_overlap': sorted(incoming & outgoing),
                                   'available_distance_m': leave-entry,
                                   'lane_change_required': not bool(incoming & outgoing)})
    return {'path': path, 'connector_lane_maps': transitions, 'road_lane_transitions': lane_moves,
            'geometry_connected_ordered_lane_ranges_valid': True,
            'lane_change_feasibility_or_success_proven': False}


def expand_routes(original):
    before = ET.fromstring(original)
    decisions = {d.get('no'): d for d in before.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')}
    links = {n.get('no'): n for n in before.findall('./links/link')}
    down = decisions['1135']; branches = routes(down)
    require([r.get('no') for r in branches] == list(CHILD_IDS), 'Downstream route set/order changed')
    intervals = before.findall("./timeIntervalSets/timeIntervalSet[@no='VEHICLEROUTESTATIC']/timeInts/timeInterval")
    require([x.attrib for x in intervals] == [{'start': '0'}], 'Static-route interval changed')
    for no in (*PARENTS, '1135'):
        d = decisions[no]
        require(d.get('allVehTypes') == 'true' and d.get('routeChoiceMeth') == 'STATIC'
                and d.get('combineStaRoutDec') == 'true' and [c.tag for c in d] == ['vehRoutSta'],
                f'Unreviewed class/choice/Combine contract at {no}')
    incoming = {n for n, x in links.items() if x.find('toLinkEndPt') is not None
                and endpoint(x, 'toLinkEndPt')[0] == '68'}
    require(incoming == {'10625','10629','10633'}, 'Source68 incoming coverage changed')
    require(not any(x.get('link') == '68' for x in before.findall('./vehicleInputs/vehicleInput')),
            'Source68 has an unreviewed native input')
    Q = sum(map(weight, branches), Fraction())
    require([weight(b) for b in branches] == [3,1,1], 'Expected 1135 weights 3:1:1')
    edits, mapping = [], []
    for upno, oldno in PARENTS.items():
        up = decisions[upno]; old = next(x for x in routes(up) if x.get('no') == oldno)
        require(not (set(CHILD_IDS.values()) & {r.get('no') for r in routes(up)}), 'New route ID collision')
        require(old.get('destLink') == '68' and float(old.get('destPos')) < float(down.get('pos')),
                'Parent route does not end before1135')
        W = weight(old); total = sum(map(weight, routes(up)), Fraction())
        outer = element_span(original, 'vehicleRoutingDecisionStatic', upno)
        inner = element_span(outer.group(), 'vehicleRouteStatic', oldno)
        children = []
        for branch in branches:
            require(old.get('formula') == branch.get('formula') == '', 'Formula routing is unsupported')
            bid = branch.get('no'); w = W * weight(branch) / Q
            child = inner.group()
            for name, value in {'no': CHILD_IDS[bid], 'destLink': branch.get('destLink'),
                                'destPos': branch.get('destPos'), 'relFlow': '2 0:' + exact_decimal(w)}.items():
                child = attribute(child, name, old.get(name), value)
            keys = route_path(up, old)[1:] + route_path(down, branch)[1:-1]
            content = b'\r\n' + b''.join(b'\t'*6 + b'<intObjectRef key="' + k.encode() + b'"/>\r\n' for k in keys) + b'\t'*5
            child, n = re.subn(rb'(?<=<linkSeq>).*?(?=</linkSeq>)', lambda _: content, child, flags=re.S)
            require(n == 1, 'Expected one linkSeq block')
            parsed = ET.fromstring(child)
            require({k:v for k,v in parsed.attrib.items() if k not in ('no','destLink','destPos','relFlow')}
                    == {k:v for k,v in old.attrib.items() if k not in ('no','destLink','destPos','relFlow')},
                    'Unexpected child route attribute edit')
            validation = validate_route(up, parsed, links)
            require(validation['path'] == route_path(up, old) + route_path(down, branch)[1:], 'Route concatenation changed')
            mapping.append({'parent_decision': upno, 'old_parent_route': oldno,
                            'old_downstream_decision': '1135', 'old_downstream_route': bid,
                            'new_route': CHILD_IDS[bid], 'parent_weight': str(W),
                            'conditional_branch_probability': str(weight(branch)/Q),
                            'new_relative_weight': str(w), 'written_relFlow': parsed.get('relFlow'),
                            'upstream_probability_before_product': str((W/total)*(weight(branch)/Q)),
                            'upstream_probability_after': str(weight(parsed)/total),
                            'destination': {'link': parsed.get('destLink'), 'pos_raw': parsed.get('destPos')},
                            **validation})
            children.append(child)
        start, end = outer.start()+inner.start(), outer.start()+inner.end()
        edits.append((start, end, b'\r\n\t\t\t\t'.join(children), f'expand {upno}:{oldno} to4/5/6'))
    removed = element_span(original, 'vehicleRoutingDecisionStatic', '1135')
    edits.append((removed.start(), removed.end(), b'', 'remove downstream decision1135'))
    result, byte_audit = splice(original, edits)
    after = ET.fromstring(result)
    after_dec = {d.get('no'): d for d in after.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')}
    require(set(after_dec) == set(decisions)-{'1135'}, 'Unexpected decision addition/removal')
    for upno, oldno in PARENTS.items():
        old, new = decisions[upno], after_dec[upno]
        require(old.attrib == new.attrib, 'Parent decision attributes changed')
        require(sum(map(weight, routes(old)), Fraction()) == sum(map(weight, routes(new)), Fraction()), 'Parent mass changed')
        retained = [r for r in routes(old) if r.get('no') != oldno]
        require({r.get('no') for r in routes(new)} == {r.get('no') for r in retained} | set(CHILD_IDS.values()), 'Route IDs changed')
        for oldroute in retained:
            oldbytes = element_span(element_span(original,'vehicleRoutingDecisionStatic',upno).group(),'vehicleRouteStatic',oldroute.get('no')).group()
            newbytes = element_span(element_span(result,'vehicleRoutingDecisionStatic',upno).group(),'vehicleRouteStatic',oldroute.get('no')).group()
            require(oldbytes == newbytes, 'Sibling raw bytes changed')
        # Remove only the whitelisted route subtrees for an independent XML diff.
        old.find('vehRoutSta').remove(next(r for r in routes(old) if r.get('no') == oldno))
        for r in list(routes(new)):
            if r.get('no') in CHILD_IDS.values(): new.find('vehRoutSta').remove(r)
    before.find('vehicleRoutingDecisionsStatic').remove(decisions['1135'])
    require(tree_value(before) == tree_value(after), 'XML diff exceeds the declared route edits')
    require(all(r['upstream_probability_before_product'] == r['upstream_probability_after'] for r in mapping), 'Product probability mismatch')
    return result, {'byte_preservation': byte_audit, 'route_mapping': mapping,
                    'xml_allowed_diff_pass': True, 'parent_probability_mass_preserved': True,
                    'retained_sibling_routes_raw_exact': 6, 'new_child_routes': 9,
                    'all_vehicle_types': True, 'static_interval_start_sec': [0],
                    'combineStaRoutDec_unchanged_true': True,
                    'relFlow_blank_default_interpretation': '1; native COM readback still required',
                    'structural_incoming_coverage68': sorted(incoming),
                    'live_vehicle_eligibility_coverage_verified': False}


def distance_arm(original):
    match = element_span(original, 'link', '10635')
    # Only the quoted numeric payload changes, not even the rest of the tag.
    attr = re.search(rb'\blnChgDist="(1000)"', match.group())
    require(attr is not None, '10635 lnChgDist is not1000')
    start, end = match.start()+attr.start(1), match.start()+attr.end(1)
    result, audit = splice(original, [(start,end,b'2000','link10635 lnChgDist1000→2000')])
    a, b = ET.fromstring(original), ET.fromstring(result)
    node = b.find("./links/link[@no='10635']")
    require(node.get('lnChgDist') == '2000' and node.get('lnChgDistIsPerLn') == 'false', 'Distance contract changed')
    node.set('lnChgDist','1000')
    require(tree_value(a) == tree_value(b), 'Distance arm has another XML change')
    return result, {'byte_preservation':audit,'xml_allowed_diff_pass':True,
                    'all_routes_classes_intervals_destinations_exact':True,
                    'DiffusTm_EmergStopDist_driver_parameters_exact':True,
                    'scope':'City connector10635 to47; distinct from on-ramp route expansion'}


def output_path(value):
    path = Path(value)
    path = (path if path.is_absolute() else ROOT/path).resolve()
    diagnostics = (ROOT/'diagnostics').resolve()
    require(path != diagnostics and path.is_relative_to(diagnostics), 'Output must be a separate subtree of diagnostics')
    return path


def build():
    original = NETWORK.read_bytes()
    require(sha(original) == NETWORK_SHA, 'Original INPX differs from the reviewed byte pin')
    root = ET.fromstring(original)
    inputs = {str(NETWORK.relative_to(ROOT)): {'sha256':sha(original),'size':len(original)}}
    for relative in (*PIN_PATHS, ACTION_DIR+'action_000900.json', ACTION_DIR+'action_000900.csv', ACTION_DIR+'action_000750.csv'):
        raw = (ROOT/relative).read_bytes(); inputs[relative] = {'sha256':sha(raw),'size':len(raw)}
    inputs[str(Path(__file__).resolve().relative_to(ROOT))] = {'sha256':sha(Path(__file__).read_bytes()),'size':Path(__file__).stat().st_size}
    assets = {}
    sig_refs = []
    for controller in root.findall('./signalControllers/signalController'):
        for key, value in controller.attrib.items():
            if key.startswith('supplyFile') and value.lower().endswith('.sig'):
                name = value.removeprefix('#data#')
                require(name and not any(c in name for c in '/\\:') and not name.startswith('#'), 'Unsafe/nonrelative SIG reference')
                raw = (NETWORK.parent/name).read_bytes(); assets[name] = raw
                rel = str((NETWORK.parent/name).relative_to(ROOT))
                inputs[rel] = {'sha256':sha(raw),'size':len(raw)}
                sig_refs.append({'controller':controller.get('no'),'attribute':key,'raw_reference':value,
                                 'copied_relative_path':name,'sha256':sha(raw)})
    require(len(assets) == 42, 'Referenced SIG set changed')
    distance, da = distance_arm(original); expanded, ea = expand_routes(original)
    definitions = [('baseline',original,{'original_network_bytes_exact':True}),
                   ('lcd10635_2000',distance,da),('upstream1135',expanded,ea)]
    files, arms = {}, {}
    for name, raw, audit in definitions:
        for tag, no in (('link','69'),('link','10703'),('vehicleRoutingDecisionStatic','1134')):
            require(element_span(original,tag,no).group() == element_span(raw,tag,no).group(), f'{tag}:{no} changed')
        audit.update({'source69_decision1134_late_join10703_raw_exact':True,
                      'run_ready':False, 'static_build_verified':True,
                      'model_execution':False,'COM_readback':False})
        network_name = name+'/'+NETWORK.name
        files[network_name] = raw
        files[name+'/validation.json'] = json_bytes(audit)
        for filename, content in assets.items(): files[name+'/'+filename] = content
        arms[name] = {'network':network_name,'network_sha256':sha(raw),'network_size':len(raw),
                      'validation':name+'/validation.json','run_ready':False,
                      'pending':['Baseline fixed-command writer/native-load smoke not executed'] +
                        (['Native RelFlow(1), Combine/LookAhead and actual eligible vehicle coverage not verified'] if name=='upstream1135' else [])}
    manifest = {'schema':'fixed-command-route-network-arms/v1','source_network_sha256':NETWORK_SHA,
                'inputs':inputs,'arms':arms,'relative_sig_references':sig_refs,
                'sig_files_per_arm':len(assets),'run_ready':False,
                'route_id_mapping':ea['route_mapping'],
                'no_original_or_runtime_mutation':True,
                'not_copied':{'background_images':'Visual-only #data# image references remain unchanged; the95MB background image is not packaged.',
                              'engine_assets':'#exe#/#3dmodels#, bare VISSIG DLLs and existing absolute visual assets remain the original host dependencies.'},
                'limitations':['Conditional local destination probabilities, not same-seed realized vehicle OD, are preserved.',
                               'Combine and route look-ahead already enabled; improved lane access is unproven.',
                               '66→10633 lands on68lane4, while10681 requires lane1/2: route extension does not remove that lane change.',
                               'Original model/evidence SHA contracts must not be repinned to these experimental networks.'],
                'outputs':{name:{'sha256':sha(raw),'size':len(raw)} for name,raw in sorted(files.items())}}
    files['manifest.json'] = json_bytes(manifest)
    return files, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=str(DEFAULT_OUTPUT))
    parser.add_argument('--verify', action='store_true', help='Read-only verify an already generated directory; never overwrite')
    args = parser.parse_args(); target = output_path(args.output)
    files, manifest = build()
    if args.verify:
        require(target.is_dir(), 'Prepared directory is absent')
        actual = {p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()}
        require(actual == set(files), 'Prepared file set differs')
        for name, raw in files.items(): require((target/name).read_bytes() == raw, 'Prepared bytes changed: '+name)
    else:
        require(not target.exists(), 'Output exists; use --verify or a new directory, never overwrite')
        target.mkdir(parents=True, exist_ok=False)
        for name, raw in files.items():
            path = (target/name).resolve(); require(path.is_relative_to(target), 'Output escaped directory')
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream: stream.write(raw)
            require(path.read_bytes() == raw, 'Artifact readback mismatch')
    for name, row in manifest['inputs'].items(): require(sha((ROOT/name).read_bytes()) == row['sha256'], 'Input changed during prepare: '+name)
    print(json.dumps({'output':str(target),'verified':args.verify,'files':len(files),
                      'manifest_sha256':sha(files['manifest.json']),
                      'network_sha256':{name:arm['network_sha256'] for name,arm in manifest['arms'].items()},
                      'run_ready':False,'source_changes':[]}))


if __name__ == '__main__':
    main()
