r"""K8-9 (amendment 22 sections 4 and 6.2, D-K9-16, D-K9-20): read-only check of the phantom route alias table.

    python -B diagnostics/sdmpc_n31_20260924/k9/phantom_route_alias.py --root <tree> [--out <json>] [--check]

The ledger (evaluation/controllers/control_area_objective.py, ModelAreaLedger.transfer) raises MembershipError
"unresolved destination" when a phantom movement (route contract status no_match, both membership probabilities
null) leaves with stock.  K8-9 lends such a phantom the route of its real sibling, only at that failure site and
only for the three SC5_S phantoms of D-K9-20 (constant PHANTOM_ROUTE_ALIAS).  This tool rebuilds that table from
the data of a tree by the declared rule and prints the evidence.  It changes nothing.

Inputs (tree-relative): the route contract, the deployed tuning, the detector mapping and the network .inpx.

1. Enumeration (section 4.4-1): every route-contract key starting with 'movement:' whose status is 'no_match',
   sorted; count and sha256 of json.dumps(<list>, separators=(',', ':')).  The three table keys must be in it.
2. Sibling rule (section 4.1), applied literally to the three phantoms P:
   - real movement Q: route contract movement:Q has status 'unique', non-empty physical_turns, and both
     probabilities numbers (not bool) in [0, 1];
   - same signal: tuning config_overrides.network.urban_movements[Q].signal = that of P;
   - same exit: 'exit' and 'receiving_link' both equal;
   - same stop line: every physical_turns[].from_link of Q equals S(P), where
     (i) the source links of P = the route contract input:gate:<origin>.physical_sources links when that list is
         not empty, else the detector mapping link_to_origins links that list P's origin;
     (ii) S(P) = the first "stop line of P's signal" met when following the .inpx link/connector graph from a
         source link (itself included); a stop line of P's signal = a physical_turns[].from_link of a real
         movement of the same signal in the route contract.  A path reaching a link with a head of another
         modeled signal is dropped.  Depth 12.  No path, or more than one S(P) -> STOP.
   - cross checks: (1) among the real stop lines of P's signal grouped by approach leg, S(P) belongs to exactly
     one leg and that leg has P's compass (first letter of the approach); (2) phase of P = phase of Q.
   Exactly one sibling -> alias.  None or more than one -> STOP (D-K9-16 clause, kept for these three by D-K9-20).
3. --check: also read PHANTOM_ROUTE_ALIAS from <tree>/evaluation/controllers/control_area_objective.py and
   require it to equal the rebuilt table.

Last line: 'PHANTOM_ALIAS_OK n=3 table_sha256=<sha256>' and exit 0, or
           'PHANTOM_ALIAS_STOP phantom=<key> reason=<...>' and exit 3.
Standard library only.  No traffic or performance value is read or printed.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROUTE_CONTRACT = 'diagnostics/control_area_route_contract_physical_routes.json'
TUNING = 'diagnostics/sdmpc_n31_20260924/config_n31_v2.json'
DETECTOR_MAPPING = 'evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json'
NETWORK = 'diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx'
CAO = 'evaluation/controllers/control_area_objective.py'
INPUTS = (ROUTE_CONTRACT, TUNING, DETECTOR_MAPPING, NETWORK)
# D-K9-20: exactly these three phantoms get an alias.
PHANTOMS = ('movement:SC5_S_to_E_SC6', 'movement:SC5_S_to_N_SC102', 'movement:SC5_S_to_W_SC101')
MAX_DEPTH = 12


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def in01(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0.0 <= float(value) <= 1.0


def table_sha256(table):
    return sha256_bytes(json.dumps(table, sort_keys=True, separators=(',', ':')).encode('utf-8'))


class Network:
    """Successors of links and connectors, and signal heads per link, from the .inpx."""

    def __init__(self, path):
        root = ET.parse(path).getroot()
        self.succ = collections.defaultdict(list)
        for link in root.findall('./links/link'):
            start, end = link.find('fromLinkEndPt'), link.find('toLinkEndPt')
            if start is not None and end is not None:
                source, target = start.get('lane').split()[0], end.get('lane').split()[0]
                self.succ[source].append(link.get('no'))
                self.succ[link.get('no')].append(target)
        self.heads = collections.defaultdict(set)
        for head in root.findall('.//signalHead'):
            if head.get('lane') and head.get('sg'):
                controller, group = head.get('sg').split()[:2]
                self.heads[head.get('lane').split()[0]].add((controller, group))


def build(root):
    root = Path(root)
    rc = read_json(root / ROUTE_CONTRACT)
    tuning = read_json(root / TUNING)
    mapping = read_json(root / DETECTOR_MAPPING)
    net = Network(root / NETWORK)
    um = tuning['config_overrides']['network']['urban_movements']
    modeled = {str(spec.get('signal', '')).removeprefix('SC') for spec in um.values()}

    def real(name):
        route = rc.get('movement:' + name, {})
        return (route.get('status') == 'unique' and bool(route.get('physical_turns'))
                and in01(route.get('inside_to_inside')) and in01(route.get('outside_to_inside')))

    def from_links(name):
        return sorted({str(turn.get('from_link')) for turn in rc['movement:' + name]['physical_turns']})

    report = {'schema': 'phantom-route-alias/v1', 'root': str(root),
              'inputs': {rel: {'sha256': sha256_bytes((root / rel).read_bytes()),
                               'size': (root / rel).stat().st_size} for rel in INPUTS}}
    no_match = sorted(key for key, route in rc.items()
                      if key.startswith('movement:') and isinstance(route, dict) and route.get('status') == 'no_match')
    report['no_match_movements'] = {
        'count': len(no_match), 'sha256': sha256_bytes(json.dumps(no_match, separators=(',', ':')).encode('utf-8')),
        'keys': no_match}
    report['table_keys_in_enumeration'] = {key: key in no_match for key in PHANTOMS}
    phantoms, table, stop = {}, {}, None
    for key in PHANTOMS:
        name = key[len('movement:'):]
        row = {'verdict': 'STOP'}
        phantoms[key] = row
        if key not in no_match:
            stop = stop or (key, 'not_a_no_match_movement')
            continue
        spec = um.get(name)
        if not isinstance(spec, dict):
            stop = stop or (key, 'no_tuning_spec')
            continue
        signal = spec.get('signal')
        own = str(signal).removeprefix('SC')
        row.update({field: spec.get(field) for field in
                    ('signal', 'approach', 'exit', 'receiving_link', 'origin', 'phase', 'kind')})
        gate = rc.get('input:gate:' + str(spec.get('origin')), {})
        gate_links = sorted({str(source.get('link')) for source in (gate.get('physical_sources') or [])
                             if isinstance(source, dict) and source.get('link') is not None})
        if gate_links:
            sources, source_rule = gate_links, 'route_contract_physical_sources'
        else:
            sources = sorted(str(link) for link, origins in mapping['link_to_origins'].items()
                             if spec.get('origin') in origins)
            source_rule = 'detector_link_to_origins'
        row.update(source_links=sources, source_rule=source_rule)
        same_signal_real = [q for q, s in um.items() if s.get('signal') == signal and real(q)]
        stoplines = sorted({link for q in same_signal_real for link in from_links(q)})
        row['own_signal_stoplines'] = stoplines
        found, paths, dropped = set(), [], []
        frontier = [[source] for source in sources]
        for _ in range(MAX_DEPTH):
            following = []
            for path in frontier:
                current = path[-1]
                if current in stoplines:
                    found.add(current)
                    paths.append(path)
                    continue
                if {controller for controller, _group in net.heads[current]} & (modeled - {own}):
                    dropped.append(path)
                    continue
                for nxt in net.succ[current]:
                    if nxt not in path:
                        following.append(path + [nxt])
            frontier = following
            if not frontier:
                break
        row.update({'S(P)': sorted(found), 'paths': paths, 'dropped': dropped, 'open_after_depth': len(frontier),
                    'heads_on_S(P)': {link: sorted('%s/%s' % h for h in net.heads[link]) for link in sorted(found)}})
        if not sources:
            stop = stop or (key, 'no_source_link')
            continue
        if len(found) != 1:
            stop = stop or (key, 'stop_line_count_%d' % len(found))
            continue
        stopline = next(iter(found))
        candidates = {q: from_links(q) for q in same_signal_real
                      if q != name and um[q].get('exit') == spec.get('exit')
                      and um[q].get('receiving_link') == spec.get('receiving_link')}
        siblings = sorted(q for q, links in candidates.items() if links == [stopline])
        row.update(candidates=candidates, siblings=siblings)
        by_leg = collections.defaultdict(set)
        for q in same_signal_real:
            by_leg[str(um[q].get('approach'))].update(from_links(q))
        legs = sorted(leg for leg, links in by_leg.items() if stopline in links)
        check1 = len(legs) == 1 and legs[0][:1] == str(spec.get('approach'))[:1]
        row['cross_check_1'] = {'legs_holding_S(P)': legs, 'ok': check1,
                                'stoplines_by_leg': {leg: sorted(links) for leg, links in sorted(by_leg.items())}}
        if len(siblings) != 1:
            stop = stop or (key, 'sibling_count_%d' % len(siblings))
            continue
        sibling = siblings[0]
        check2 = um[sibling].get('phase') == spec.get('phase')
        row['cross_check_2'] = {'phantom_phase': spec.get('phase'), 'sibling_phase': um[sibling].get('phase'),
                                'ok': check2}
        if not check1:
            stop = stop or (key, 'cross_check_1')
            continue
        if not check2:
            stop = stop or (key, 'cross_check_2')
            continue
        row['verdict'] = 'UNIQUE'
        row['sibling'] = 'movement:' + sibling
        table[key] = 'movement:' + sibling
    report['phantoms'] = phantoms
    report['table'] = dict(sorted(table.items()))
    report['table_sha256'] = table_sha256(report['table'])
    return report, stop


def cao_table(root):
    """PHANTOM_ROUTE_ALIAS as written in the tree's control_area_objective.py (a JSON-compatible dict literal)."""
    lines = (Path(root) / CAO).read_text(encoding='utf-8').splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith('PHANTOM_ROUTE_ALIAS = {')]
    if len(starts) != 1:
        raise ValueError('PHANTOM_ROUTE_ALIAS assignment not found exactly once')
    end = next(i for i in range(starts[0], len(lines)) if lines[i].rstrip().endswith('}'))
    text = '\n'.join(lines[starts[0]:end + 1])
    return json.loads(text[text.index('{'):])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--root', required=True, help='tree root (repository or frozen copy)')
    parser.add_argument('--out', help='write the JSON report here')
    parser.add_argument('--check', action='store_true', help='also require the CAO constant to equal the table')
    args = parser.parse_args(argv)
    report, stop = build(args.root)
    if stop is None and len(report['table']) != len(PHANTOMS):
        stop = ('*', 'table_size_%d' % len(report['table']))
    if stop is None and not all(report['table_keys_in_enumeration'].values()):
        stop = ('*', 'table_key_outside_enumeration')
    if args.check:
        try:
            constant = cao_table(args.root)
        except (OSError, ValueError, StopIteration) as error:
            constant = None
            report['cao_check'] = {'ok': False, 'error': str(error)}
        else:
            report['cao_check'] = {'ok': constant == report['table'], 'cao_table_sha256': table_sha256(constant)}
        if stop is None and not report['cao_check']['ok']:
            differing = sorted(set(report['table']) ^ set(constant or {}) |
                               {k for k in report['table'] if (constant or {}).get(k) != report['table'][k]})
            stop = (differing[0] if differing else '*', 'cao_constant_differs')
    report['verdict'] = 'OK' if stop is None else 'STOP'
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    for key, row in report['phantoms'].items():
        print('%s %s S(P)=%s sibling=%s' % (key, row['verdict'], ','.join(row.get('S(P)', [])), row.get('sibling', '-')))
    print('NO_MATCH_MOVEMENTS n=%d sha256=%s' % (report['no_match_movements']['count'],
                                                report['no_match_movements']['sha256']))
    for rel, pin in report['inputs'].items():
        print('INPUT %s sha256=%s' % (rel, pin['sha256']))
    if stop is not None:
        print('PHANTOM_ALIAS_STOP phantom=%s reason=%s' % stop)
        return 3
    print('PHANTOM_ALIAS_OK n=%d table_sha256=%s' % (len(report['table']), report['table_sha256']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
