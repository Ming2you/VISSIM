"""K8-6 SA evidence builder: stopline-approach-evidence/v2 for SC1001 EB (OPT1_V2_SPEC 3.2 + amendment 1 r2 3.2).

    python -B diagnostics/sdmpc_n31_20260924/stopline/build_sc1001eb_evidence.py [--check]
        [--inputs <dir>] [--loso <s2_loso_out.json>] [--out <evidence json>]

Default inputs are the byte copies in stopline/inputs/ (K8 amendment 5 section 6: copied from the session scratch
<K8>/opt1v2/out and <K8>/amend1/tools so G-EB-0 reproduces after Temp cleanup; the pins below are unchanged).
Reads only sha-pinned files (a mismatch is a SystemExit, nothing is written):
  a1v2_visit.json   d6e4a0bc...  visit estimator, declaration sha16 211a48c6b3e3f450 (spec 1.2-1.6)
  s2_lanefull.json  f9ec730a...  lane-full counts, declaration sha16 5864d5b1d518c34e (spec 1.8)
  g2_inpx_v3c3.json 69d4a5b5...  v3c3 INPX geometry, extract sha12 910bc37a8d69 on all five fit seeds
  s2_loso_out.json  f98d422d...  LOSO report, declaration sha16 2d7a85d124ae2f3d (recorded, not checked)
  the deployed detector mapping and physical projection support table (repository files, pinned)
No runtime module is imported; the build is a pure JSON computation.

Declared rules (each value is then compared with the OPT1_V2_SPEC 1.9 table as amended; any difference at the
precision the spec prints is a SystemExit -> STOP, user):
  s_veh_h_lane[l]        E1_lane.lane<l>.s_g45 (visit units, saturated-lane cycles, 45 s green)
  head_pos_m[l]          g2 signal head on lane "127 <l>"
  lane members           posthead connectors (fromLink 127): lane l serves the destination of every connector
                         whose from-lanes contain l (10118 lanes 1-2 E, 10368 lane 1 S, 10695 lane 3 N)
  p_lane1_given_E        sum over seeds lane_by_mv E|1 / (E|1 + E|2)
  upstream_lane_prior    sum over seeds upstream1117_frames_by_lane_mv, row-normalised per lane
  posthead_lane_prior    sum over seeds lane_by_mv restricted to the destinations served by the lane's signal group
                         (SG2 lanes 1-2: E, S; SG5 lane 3: N), row-normalised
  storage_veh            geometric = head/6.0 (jam spacing); observed_full = pooled p50 for lanes 1-2 (81, 63) and
                         geometric for lane 3 (no lane-full frame); judging arm = observed_full (D-K8-1)
  posthead_connectors    every INPX connector leaving link 127 -> {from_lanes, receiver = mapping origin of its to-link}
  posthead_rehome        posthead connectors whose mapping origins still hold in_SC1001_W after the support table
  pre_stopline_links     in_SC1001_W origin links minus ports and posthead connectors, ordered upstream -> 127
  ports                  OR_D_W 10491 lands on 129 at its to-pos, travels (10777 from-pos on 129 - landing) + head_l
                         (the 1 m 10777 connector excluded, U8C convention); OR_D_E 10481 lands on 127, head_l - to-pos
  d1117_m, tail129_from_m, link10777_m   route decision 1117 position, 10491 to-pos on 129, 10777 length
  route_exit             decision 1117 routes -> destination of their first connector
  init_origin_routes     routes ending on 127 through a port connector = port, otherwise city; decision 1117 = unknown
  port_progress_route    routes ending on 127 through 10491 and 129 -> OR_D_W (the 129 tail of spec 5.8-5)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCHEMA = 'stopline-approach-evidence/v2'
OUT_REL = 'diagnostics/sdmpc_n31_20260924/stopline/sc1001eb_evidence_v3c3_20261004.json'
BUILDER_REL = 'diagnostics/sdmpc_n31_20260924/stopline/build_sc1001eb_evidence.py'
INPUTS_REL = 'diagnostics/sdmpc_n31_20260924/stopline/inputs'
DEFAULT_INPUTS = ROOT / INPUTS_REL                      # sha-pinned byte copies (amendment 5 section 6)
DEFAULT_LOSO = DEFAULT_INPUTS / 's2_loso_out.json'

PINS = {
    'a1v2_visit': ('a1v2_visit.json', 'd6e4a0bc5d295f0df9244da14e213fb8938d7081b6464c7879e31ce0c9fdf8e0',
                   '211a48c6b3e3f450'),
    's2_lanefull': ('s2_lanefull.json', 'f9ec730a425ea4ba48a3ba1ff467f323f3159d1e541f016f084c1ce439c03a76',
                    '5864d5b1d518c34e'),
    'g2_inpx': ('g2_inpx_v3c3.json', '69d4a5b5b1ecb6908898d0292ceae3571e6d4d690adc4445731ee6e69281bab0', None),
    's2_loso': ('s2_loso_out.json', 'f98d422db3ee1ade32fdab2b1ada16440abe0f547cf131d32c96ea9cc082da58',
                '2d7a85d124ae2f3d'),
}
MAPPING = ('evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json',
           'f8c90e5769c7c92e8c698134dbf61b5f35f2205bf634841f4562f37967e72b3e')
SUPPORT = ('diagnostics/sdmpc_n31_20260924/scenario/physical_projection_support_635_proposal_ec2393.json',
           '8d02ed64d43461236ef15f657aeab553440cc981540fbc390fa01c2d0eea7d50')
NETWORK = ('diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx',
           '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e')     # recorded only (N12)
GEOMETRY_SHA12 = '910bc37a8d69'
SEEDS = ('31', '41', '43', '47', '53')
LANES = ('1', '2', '3')
DESTS = ('E', 'S', 'N')
MEMBERS = {'E': 'SC1001_W_to_E_SC1002', 'S': 'SC1001_W_to_S_SC1003', 'N': 'SC1001_W_to_N_SC2002'}
MEMBER_RECEIVER = {'E': 'SC1001_to_SC1002', 'S': 'SC1001_to_SC1003', 'N': 'SC1001_to_SC2002'}
RECEIVER = 'in_SC1001_W'
STOPLINE_LINK = '127'
# Declared constants (spec 1.9 / plan): SG2 heads on lanes 1-2 = plan phase p3, SG5 on lane 3 = p4; v1 speed floor;
# the urban vehicle spacing that geometric storage divides by (LPR:296-298).
LANE_PHASE = {'1': 'SC1001_p3', '2': 'SC1001_p3', '3': 'SC1001_p4'}
LANE_SIGNAL_GROUP = {'1': '1001 2', '2': '1001 2', '3': '1001 5'}
SPEED_FLOOR_KMH = 20.0
JAM_SPACING_M = 6.0
PORT_OFF_RAMP = {'10491': 'OR_D_W', '10481': 'OR_D_E'}
ROUTE_DECISION = '1117'
OBSERVED_FULL_LANES = ('1', '2')          # lane 3 has no lane-full frame (spec 1.8)

# OPT1_V2_SPEC 1.9 (amended) as printed: exact where the spec prints full precision, else (value, digits).
SPEC_19 = {
    's_veh_h_lane': {'1': 2030.9375, '2': 1581.7040358744396, '3': 2101.923076923077},
    'head_pos_m': {'1': 621.666240433568, '2': 621.5682806829368, '3': 621.461546643362},
    'lane_members': {'1': ['E', 'S'], '2': ['E'], '3': ['N']},
    'p_lane1_given_E': (0.524, 3),
    'upstream_lane_prior': ({'1': {'E': 0.6252, 'N': 0.0039, 'S': 0.3708},
                             '2': {'E': 0.9925, 'N': 0.0073, 'S': 0.0002},
                             '3': {'E': 0.1548, 'N': 0.8304, 'S': 0.0149}}, 4),
    'upstream_frames': {'1': 130861, '2': 111413, '3': 8064},
    'posthead_lane_prior': ({'1': {'E': 0.842, 'S': 0.158}, '2': {'E': 0.992, 'S': 0.008}, '3': {'N': 1.0}}, 3),
    'storage_geometric': ({'1': 103.61104, '2': 103.59471, '3': 103.57692}, 5),
    'storage_observed_full': ({'1': 81.0, '2': 63.0, '3': 103.57692}, 5),
    'port_10491_offset_m': (62.5418, 4),
    'exit129_m': (301.926, 3),
    'landing_10491_m': (239.3842, 4),
    'landing_10481_m': (210.2714, 4),
    'd1117_m': (228.9197, 4),
    'tail129_from_m': (239.3842, 4),
    'speed_floor_kmh': 20.0,
    'origin_prior': ({'OFF_W': 0.6048, 'OFF_E': 0.2017, 'URB': 0.1935}, 4),
    'posthead_connectors': {'10118': {'from_lanes': [1, 2], 'receiver': 'SC1001_to_SC1002'},
                            '10368': {'from_lanes': [1], 'receiver': 'SC1001_to_SC1003'},
                            '10695': {'from_lanes': [3], 'receiver': 'SC1001_to_SC2002'}},
    'posthead_rehome': {'10695': 'SC1001_to_SC2002'},
    'pre_stopline_links': ['32', '10778', '129', '10777', '127'],
    'ports': ['10491', '10481'],
}


class EvidenceError(SystemExit):
    pass


def _fail(message):
    raise EvidenceError('stopline evidence: ' + message)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_pinned(path, digest):
    data = Path(path).read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != digest:
        _fail(f'{path} sha256 {actual} != pinned {digest}')
    return json.loads(data.decode('utf-8'))


def load_inputs(inputs=DEFAULT_INPUTS, loso=DEFAULT_LOSO, root=ROOT):
    inputs, root = Path(inputs), Path(root)
    docs = {}
    for key, (name, digest, declaration) in PINS.items():
        path = Path(loso) if key == 's2_loso' else inputs / name
        doc = _load_pinned(path, digest)
        if declaration is not None and doc.get('declaration_sha16') != declaration:
            _fail(f'{name} declaration sha16 {doc.get("declaration_sha16")} != {declaration}')
        docs[key] = doc
    extract = docs['g2_inpx'].get('extract_sha') or {}
    if set(extract) != set(SEEDS) or set(extract.values()) != {GEOMETRY_SHA12}:
        _fail('g2 geometry extract is not ' + GEOMETRY_SHA12 + ' on all five fit seeds')
    docs['mapping'] = _load_pinned(root / MAPPING[0], MAPPING[1])
    docs['support'] = _load_pinned(root / SUPPORT[0], SUPPORT[1])
    return docs


def _close(value, expected, digits):
    return round(value, digits) == expected


def _ratio_rows(counts_by_seed, key_of, allowed):
    """Pool integer counts over the five seeds, then normalise each lane row over its allowed destinations."""
    pooled = {lane: {d: 0 for d in allowed[lane]} for lane in LANES}
    for seed in SEEDS:
        for key, count in counts_by_seed[seed].items():
            lane, dest = key_of(key)
            if lane in pooled and dest in pooled[lane]:
                pooled[lane][dest] += int(count)
    out, totals = {}, {}
    for lane in LANES:
        total = sum(pooled[lane].values())
        if total <= 0:
            _fail('empty prior row for lane ' + lane)
        totals[lane] = total
        out[lane] = {d: pooled[lane][d] / total for d in allowed[lane] if pooled[lane][d] > 0}
    return out, totals, pooled


def _geometry(g2):
    seed = g2['seed31']
    links = {str(k): v for k, v in seed['links'].items()}
    heads = {}
    for head in seed['heads']:
        link, lane = head['lane'].split()
        if link == STOPLINE_LINK:
            heads[lane] = (float(head['pos']), head['sg'])
    if set(heads) != set(LANES):
        _fail('link 127 must carry one signal head per lane')
    return seed, links, heads


def _route_decisions(seed):
    return {str(rd['no']): rd for rd in seed['rds']}


def build(inputs=DEFAULT_INPUTS, loso=DEFAULT_LOSO, root=ROOT):
    docs = load_inputs(inputs, loso, root)
    visit, lanefull, loso_doc = docs['a1v2_visit'], docs['s2_lanefull'], docs['s2_loso']
    seed, links, heads = _geometry(docs['g2_inpx'])
    origins = docs['mapping']['link_to_origins']
    support = docs['support']['link_to_storage']

    # Posthead connectors and lane members.
    connectors = {}
    for key in sorted(links, key=int):
        row = links[key]
        if row.get('frm') is None or row['frm'][0].split()[0] != STOPLINE_LINK:
            continue
        first = int(row['frm'][0].split()[1])
        to_link = row['to'][0].split()[0]
        receivers = origins.get(to_link) or []
        if len(receivers) != 1:
            _fail(f'connector {key} lands on {to_link} with origins {receivers}')
        connectors[key] = {'from_lanes': list(range(first, first + int(row['nlanes']))), 'receiver': receivers[0]}
    dest_of_receiver = {}
    for dest, receiver in MEMBER_RECEIVER.items():
        hits = [c for c, row in connectors.items() if row['receiver'] == receiver]
        if len(hits) != 1:
            _fail('member ' + MEMBERS[dest] + ' has no unique posthead connector')
        dest_of_receiver[receiver] = dest
    lane_members = {lane: [dest_of_receiver[row['receiver']] for c, row in connectors.items()
                           if int(lane) in row['from_lanes']] for lane in LANES}
    lane_members = {lane: [d for d in DESTS if d in members] for lane, members in lane_members.items()}
    rehome = {c: row['receiver'] for c, row in connectors.items()
              if RECEIVER in (origins.get(c) or []) and c not in support}

    # Ports (mapping off-ramp connectors) and the pre-stopline chain walked upstream from 127.
    port_group = {}
    for group, rows in docs['mapping']['off_ramp_connectors'].items():
        for row in rows:
            if str(row['connector']) in PORT_OFF_RAMP:
                port_group[str(row['connector'])] = group
    if port_group != PORT_OFF_RAMP:
        _fail(f'port connectors {port_group} != {PORT_OFF_RAMP}')
    origin_links = sorted((k for k, v in origins.items() if RECEIVER in (v or [])), key=int)
    candidates = set(origin_links) - set(PORT_OFF_RAMP) - set(connectors)
    chain = [STOPLINE_LINK]
    while True:
        head_link = links.get(chain[0], {})
        if head_link.get('frm') is not None:          # a connector: its predecessor is its from-link
            feeders = [head_link['frm'][0].split()[0]]
        else:                                         # a link: the connector(s) landing on it
            feeders = [k for k in candidates if links.get(k, {}).get('to')
                       and links[k]['to'][0].split()[0] == chain[0]]
        feeders = [k for k in feeders if k in candidates and k not in chain]
        if not feeders:
            break
        if len(feeders) != 1:
            _fail(f'ambiguous feeder of {chain[0]}: {feeders}')
        chain.insert(0, feeders[0])
    if set(chain) != candidates:
        _fail(f'pre-stopline chain {chain} does not cover the in_SC1001_W origin links {sorted(candidates)}')
    connector_link, tail_link = chain[-2], chain[-3]
    exit129 = float(links[connector_link]['frm'][1])
    if links[connector_link]['frm'][0].split()[0] != tail_link:
        _fail('the 127 entry connector does not start on the tail link')
    landing = {}
    for port in PORT_OFF_RAMP:
        to_lane, to_pos = links[port]['to']
        landing[port] = [to_lane.split()[0], float(to_pos)]
    if landing['10491'][0] != tail_link or landing['10481'][0] != STOPLINE_LINK:
        _fail(f'port landings {landing} differ from the tail link / stopline link')
    head = {lane: heads[lane][0] for lane in LANES}
    distance = {'10491': {lane: (exit129 - landing['10491'][1]) + head[lane] for lane in LANES},
                '10481': {lane: head[lane] - landing['10481'][1] for lane in LANES}}

    # Routes.
    decisions = _route_decisions(seed)
    rd1117 = decisions[ROUTE_DECISION]
    if str(rd1117['link']) != STOPLINE_LINK:
        _fail('route decision 1117 is not on link 127')
    receiver_of_connector = {c: row['receiver'] for c, row in connectors.items()}
    route_exit = {}
    for route in rd1117['routes']:
        first = str(route['seq'][0])
        route_exit[f"{ROUTE_DECISION}:{route['no']}"] = dest_of_receiver[receiver_of_connector[first]]
    init_routes, progress = {}, {}
    for no, rd in sorted(decisions.items(), key=lambda kv: int(kv[0])):
        for route in rd['routes']:
            if str(route['destLink']) != STOPLINE_LINK:
                continue
            seq = [str(x) for x in route['seq']]
            ports = [p for p in PORT_OFF_RAMP if p in seq]
            key = f"{no}:{route['no']}"
            init_routes[key] = 'port' if ports else 'city'
            if ports == ['10491'] and tail_link in seq:
                progress[key] = PORT_OFF_RAMP['10491']
    init_routes[ROUTE_DECISION] = 'unknown'

    # Lane service, priors, storage.
    s_lane = {lane: visit['E1_lane']['lane' + lane]['s_g45'] for lane in LANES}
    lane_by_mv = {s: visit['seeds'][s]['lane_by_mv'] for s in SEEDS}
    e1 = sum(lane_by_mv[s].get('E|1', 0) for s in SEEDS)
    e2 = sum(lane_by_mv[s].get('E|2', 0) for s in SEEDS)
    p1 = e1 / (e1 + e2)
    upstream, upstream_frames, _ = _ratio_rows({s: visit['seeds'][s]['upstream1117_frames_by_lane_mv'] for s in SEEDS},
                                               lambda k: tuple(k.split('|')), {lane: DESTS for lane in LANES})
    group_dests = {}
    for lane in LANES:
        group_dests.setdefault(heads[lane][1], set()).update(lane_members[lane])
    posthead_allowed = {lane: [d for d in DESTS if d in group_dests[heads[lane][1]]] for lane in LANES}
    posthead, _, _ = _ratio_rows(lane_by_mv, lambda k: tuple(reversed(k.split('|'))), posthead_allowed)
    geometric = {lane: head[lane] / JAM_SPACING_M for lane in LANES}
    for lane in LANES:
        if lanefull['geometric'][lane]['head_only'] != geometric[lane]:
            _fail('s2 geometric storage differs from head/6.0 on lane ' + lane)
    observed = {lane: (float(lanefull['pooled'][lane]['p50']) if lane in OBSERVED_FULL_LANES else geometric[lane])
                for lane in LANES}
    if lanefull['pooled']['3']['n'] != 0:
        _fail('lane 3 has lane-full frames; the observed_full rule assumed none')

    approach = {
        'signal': 'SC1001', 'stopline_link': STOPLINE_LINK, 'receiver': RECEIVER, 'members': dict(MEMBERS),
        'lanes': {lane: {'members': lane_members[lane], 'phase': LANE_PHASE[lane],
                         'signal_group': heads[lane][1], 'head_pos_m': head[lane], 's_veh_h_lane': s_lane[lane],
                         'storage_veh': {'geometric': geometric[lane], 'observed_full': observed[lane]}}
                  for lane in LANES},
        'judging_storage_arm': 'observed_full',
        'p_lane1_given_E': p1,
        'upstream_lane_prior': upstream,
        'upstream_lane_frames': upstream_frames,
        'posthead_lane_prior': posthead,
        'posthead_connectors': connectors,
        'posthead_rehome': rehome,
        'pre_stopline_links': chain,
        'ports': {port: {'off_ramp': PORT_OFF_RAMP[port], 'landing': landing[port], 'distance_m': distance[port]}
                  for port in PORT_OFF_RAMP},
        'd1117_m': float(rd1117['pos']),
        'tail129_from_m': landing['10491'][1],
        'link10777_m': float(links[connector_link]['length_poly']),
        'port_progress_route': progress,
        'route_exit': route_exit,
        'init_origin_routes': init_routes,
        'speed_floor_kmh': SPEED_FLOOR_KMH,
        'jam_spacing_m': JAM_SPACING_M,
    }
    sg2 = visit['E1_group']['SG2']
    report = {
        'origin_prior_sg2': {k: sg2['origin_share_sat'][k] for k in ('OFF_W', 'OFF_E', 'URB')},
        'e1_group_s_g45': {'SG2': sg2['s_g45'], 'SG5': visit['E1_group']['SG5']['s_g45']},
        'e1_lane_loso_range': {lane: visit['E1_lane']['lane' + lane]['s_g45_loso_range'] for lane in LANES},
        'lane_full_pooled': {lane: lanefull['pooled'][lane] for lane in ('1', '2', '12', 'spill12')},
        'loso_p50': {lane: {s: loso_doc['loso'][lane][s]['p50'] for s in SEEDS} for lane in OBSERVED_FULL_LANES},
        'loso_flags': loso_doc['flags'],
        'x_10490_m': float(links['10490']['frm'][1]),
        'exit129_m': exit129,
    }
    doc = {
        'schema': SCHEMA,
        'builder': {'path': BUILDER_REL, 'sha256': sha256(Path(root) / BUILDER_REL)},
        'inputs': {
            'a1v2_visit': {'file': PINS['a1v2_visit'][0], 'sha256': PINS['a1v2_visit'][1],
                           'declaration_sha16': PINS['a1v2_visit'][2]},
            's2_lanefull': {'file': PINS['s2_lanefull'][0], 'sha256': PINS['s2_lanefull'][1],
                            'declaration_sha16': PINS['s2_lanefull'][2]},
            'g2_inpx': {'file': PINS['g2_inpx'][0], 'sha256': PINS['g2_inpx'][1], 'extract_sha12': GEOMETRY_SHA12},
            's2_loso': {'file': PINS['s2_loso'][0], 'sha256': PINS['s2_loso'][1],
                        'declaration_sha16': PINS['s2_loso'][2], 'checked': False},
            'mapping': {'path': MAPPING[0], 'sha256': MAPPING[1]},
            'support': {'path': SUPPORT[0], 'sha256': SUPPORT[1]},
            'network': {'label': 'v3c3 s31', 'path': NETWORK[0], 'sha256': NETWORK[1], 'checked': False},
        },
        'approaches': {'SC1001_EB': approach},
        'report': report,
    }
    check_spec(doc)
    return doc


def check_spec(doc):
    """OPT1_V2_SPEC 1.9 (amended) reproduction: exact where printed in full, else at the printed digits."""
    a = doc['approaches']['SC1001_EB']
    r = doc['report']
    problems = []

    def need(ok, what):
        if not ok:
            problems.append(what)

    for lane in LANES:
        row = a['lanes'][lane]
        need(row['s_veh_h_lane'] == SPEC_19['s_veh_h_lane'][lane], 's_veh_h_lane ' + lane)
        need(row['head_pos_m'] == SPEC_19['head_pos_m'][lane], 'head_pos_m ' + lane)
        need(row['members'] == SPEC_19['lane_members'][lane], 'lane_members ' + lane)
        need(row['storage_veh']['geometric'] == row['head_pos_m'] / JAM_SPACING_M, 'geometric = head/6 ' + lane)
        for arm, key in (('geometric', 'storage_geometric'), ('observed_full', 'storage_observed_full')):
            expected, digits = SPEC_19[key]
            need(_close(row['storage_veh'][arm], expected[lane], digits), f'storage {arm} {lane}')
        need(a['upstream_lane_frames'][lane] == SPEC_19['upstream_frames'][lane], 'upstream frames ' + lane)
        expected, digits = SPEC_19['upstream_lane_prior']
        need(set(a['upstream_lane_prior'][lane]) == set(expected[lane])
             and all(_close(a['upstream_lane_prior'][lane][d], v, digits) for d, v in expected[lane].items()),
             'upstream_lane_prior ' + lane)
        expected, digits = SPEC_19['posthead_lane_prior']
        need(set(a['posthead_lane_prior'][lane]) == set(expected[lane])
             and all(_close(a['posthead_lane_prior'][lane][d], v, digits) for d, v in expected[lane].items()),
             'posthead_lane_prior ' + lane)
        need(_close(a['ports']['10491']['distance_m'][lane] - a['lanes'][lane]['head_pos_m'],
                    *SPEC_19['port_10491_offset_m']), '10491 distance ' + lane)
        need(a['ports']['10481']['distance_m'][lane] == a['lanes'][lane]['head_pos_m'] - a['ports']['10481']['landing'][1],
             '10481 distance ' + lane)
    need(_close(a['p_lane1_given_E'], *SPEC_19['p_lane1_given_E']), 'p_lane1_given_E')
    need(_close(r['exit129_m'], *SPEC_19['exit129_m']), 'exit129')
    need(_close(a['ports']['10491']['landing'][1], *SPEC_19['landing_10491_m']), '10491 landing')
    need(_close(a['ports']['10481']['landing'][1], *SPEC_19['landing_10481_m']), '10481 landing')
    need(_close(a['d1117_m'], *SPEC_19['d1117_m']), 'd1117_m')
    need(_close(a['tail129_from_m'], *SPEC_19['tail129_from_m']), 'tail129_from_m')
    need(a['speed_floor_kmh'] == SPEC_19['speed_floor_kmh'], 'speed_floor_kmh')
    expected, digits = SPEC_19['origin_prior']
    need(all(_close(r['origin_prior_sg2'][k], v, digits) for k, v in expected.items()), 'origin_prior')
    need(a['posthead_connectors'] == SPEC_19['posthead_connectors'], 'posthead_connectors')
    need(a['posthead_rehome'] == SPEC_19['posthead_rehome'], 'posthead_rehome')
    need(a['pre_stopline_links'] == SPEC_19['pre_stopline_links'], 'pre_stopline_links')
    need(list(a['ports']) == SPEC_19['ports'], 'ports')
    need(a['route_exit'] == {'1117:3': 'E', '1117:1': 'S', '1117:2': 'N'}, 'route_exit')
    need(a['init_origin_routes'] == {'1131:2': 'port', '1132:2': 'port', '1136:2': 'city', '1117': 'unknown'},
         'init_origin_routes')
    need(a['port_progress_route'] == {'1132:2': 'OR_D_W'}, 'port_progress_route')
    if problems:
        _fail('differs from OPT1_V2_SPEC 1.9: ' + ', '.join(problems))


def dumps(doc):
    return (json.dumps(doc, indent=1, ensure_ascii=False) + '\n').encode('utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--inputs', default=str(DEFAULT_INPUTS), help='a1v2, s2, g2 directory (default stopline/inputs)')
    parser.add_argument('--loso', default=str(DEFAULT_LOSO), help='s2_loso_out.json (default stopline/inputs)')
    parser.add_argument('--out', default=str(ROOT / OUT_REL))
    parser.add_argument('--check', action='store_true', help='rebuild and compare with --out byte for byte')
    args = parser.parse_args(argv)
    data = dumps(build(args.inputs, args.loso, ROOT))
    out = Path(args.out)
    if args.check:
        if not out.is_file() or out.read_bytes() != data:
            raise SystemExit(f'{out} differs from its builder')
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    print('STOPLINE_EVIDENCE_OK sha256=' + hashlib.sha256(data).hexdigest())


if __name__ == '__main__':
    main(sys.argv[1:])
