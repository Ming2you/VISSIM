"""obs150 observation (WP-B2, plan 1.6 + B1 core + B7): context, derive, merge, lane observation v2.

One module owns everything the v2 lane plant reads from the 150 s bundle:

- InpxNetwork: the parts of the v2 .inpx the detector table and the context use.
- build_detector_rows: the canonical detector table of plan B1 (the generator
  scripts/build_obs150_detectors.py is its CLI; load_context rebuilds the table
  from the pinned sources and requires the pinned CSV to be byte-identical).
- load_context(document, paths): Obs150Context of a coupled-lane-plant/v2 manifest.
- derive(raw, context): obs150-derived/v1 (CONTRACT 5.1), a pure function of the
  pinned bundle: validate_raw -> rule cross-check -> load_bundle -> evaluate_boundaries
  -> assign_window -> obs150_signal_clock.windows -> obs150_head_window.build
  -> obs150_lane.derive.
- merge_into_state(raw, derived): the four fields of CONTRACT 5.5.
- lane_observation(context, raw): lane-plant-observation/v2 from the merged state.
- PRODUCED_V2 / RETIRED_V2: the local_observation key parity of T10.

Validators raise ObsContractError; nothing is repaired or defaulted.
"""
from __future__ import annotations

from collections import defaultdict
import copy
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.obs150_contract import ObsContractError

ROOT = Path(__file__).resolve().parents[2]

# --------------------------------------------------------------------------
# B1 placement constants
# --------------------------------------------------------------------------
CONNECTOR_STATION_M = 1.0      # connector-start stations: segment [0, 1) (plan B1)
# Origin stations sit at 40 m, not 1 m: a vehicle input places a new vehicle up to
# v*0.1 s past the link start in its first step (probe gt_veh: first positions
# 0.007-1.19 m on link 26 at 30-43 km/h, more at free speed). 40 m is the probe
# station the identity was verified at (V0-6) and the position of the RULE
# measurements 910030-33 / 910045-47 (rule_crosscheck compares them per lane).
SOURCE_STATION_M = 40.0
# The RULE measurements of the v2 network that share a point with a source
# station: {measurement: (link, lane, pos)}, each 1:1 with one point. The runner
# reads their Vehs(Current,k,All) into raw.rule_crosscheck with the same k as the
# table (VBS Obs150ReadDetectors); two points at one position count the same
# vehicles (probe: 910045-47 = 950016-18 in all 8 windows and 3 open intervals,
# 1506 vehicles). build_detector_rows checks this table against the network and
# derive requires equality at every decision (check_rule_crosscheck).
RULE_CROSSCHECK_POINTS = {910030: (74, 1, 40.0), 910031: (74, 2, 40.0), 910032: (74, 3, 40.0),
                          910033: (74, 4, 40.0), 910045: (26, 1, 40.0), 910046: (26, 2, 40.0),
                          910047: (26, 3, 40.0)}
END_OFFSET_M = 0.1             # link-end stations: segment [L-0.1, L]
EXPECTED_ELIGIBLE_HEADS = 210  # NEW-4
EXPECTED_HEAD_GROUPS = 105
EXPECTED_METER_HEADS = 10
HEADFREE_SOURCE_LINK = 403
DETECTOR_BUILD_SCHEMA = 'obs150-detector-build/v1'
DETECTOR_CSV_PATH = 'diagnostics/sdmpc_n31_20260924/obs150/obs150_detectors_v2.csv'
SIDECAR_SUFFIX = '.manifest.json'
SIG_MANIFEST_SCHEMAS = ('sdmpc31-sig-manifest/v1',)
_TOL = 1e-6
_HEX64 = re.compile(r'^[0-9a-f]{64}$')


def _require(condition, message):
    if not condition:
        raise ObsContractError(message)


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _ceil6(value):
    """Smallest 6-decimal value >= value (segment ends must not cut a vehicle at L)."""
    return math.ceil(round(value * 1e6, 3)) / 1e6


def repo_path(path):
    """Repo-relative forward-slash path when under the worktree, else the absolute path."""
    path = Path(path).resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def resolve_repo(path):
    """A pin path: repo-relative (forward slashes) against the worktree root, or absolute."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


# --------------------------------------------------------------------------
# The v2 .inpx
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class InpxLink:
    no: int
    length_m: float             # 2-D polyline length = VISSIM Length2D (probe b: 318.998327627752)
    lanes: int
    eval_segment_m: float | None
    from_link: int | None
    from_lane: int | None
    from_pos_m: float | None
    to_link: int | None
    to_lane: int | None
    to_pos_m: float | None

    @property
    def is_connector(self):
        return self.from_link is not None


class InpxNetwork:
    """Read-only view of the .inpx parts obs150 uses (no VISSIM)."""

    def __init__(self, path, data=None):
        self.path = Path(path)
        data = self.path.read_bytes() if data is None else data
        self.sha256 = _sha256(data)
        root = ET.fromstring(data)
        self.links = {}
        for node in root.findall('./links/link'):
            points = [(float(p.get('x')), float(p.get('y')))
                      for p in node.findall('./geometry/linkPolyPts/linkPolyPoint')]
            start, end = node.find('./fromLinkEndPt'), node.find('./toLinkEndPt')
            seg = node.get('linkEvalSegLen')
            ends = []
            for edge in (start, end):
                if edge is None:
                    ends.extend((None, None, None))
                else:
                    link, lane = edge.get('lane').split()
                    ends.extend((int(link), int(lane), float(edge.get('pos'))))
            no = int(node.get('no'))
            self.links[no] = InpxLink(no, math.fsum(math.dist(a, b) for a, b in zip(points, points[1:])),
                                      len(node.findall('./lanes/lane')), float(seg) if seg else None, *ends)
        self.heads = []
        for head in root.findall('./signalHeads/signalHead'):
            link, lane = head.get('lane').split()
            sc, sg = head.get('sg').split()
            self.heads.append({'head_id': head.get('no'), 'link': int(link), 'lane': int(lane),
                               'position_m': float(head.get('pos')), 'sc': sc, 'sg': sg,
                               'all_veh_types': head.get('allVehTypes') == 'true'})
        self.dcp_points = {}
        for n in root.findall('./dataCollectionPoints/dataCollectionPoint'):
            link, lane = n.get('lane').split()
            self.dcp_points[int(n.get('no'))] = (int(link), int(lane), float(n.get('pos')))
        self.dcp_keys = set(self.dcp_points)
        self.dcm_points = {int(n.get('no')): tuple(int(r.get('key')) for r in n.findall('./dataCollectionPoints/intObjectRef'))
                           for n in root.findall('./dataCollectionMeasurements/dataCollectionMeasurement')}
        self.dcm_keys = set(self.dcm_points)
        self.controllers = {}
        for node in root.findall('./signalControllers/signalController'):
            supply = node.get('supplyFile2') or ''
            _require(supply == '' or supply.startswith('#data#'), 'Unexpected .sig supply path ' + supply)
            self.controllers[node.get('no')] = {'prog_no': int(node.get('progNo')), 'type': node.get('type'),
                                                'sig_file': supply[len('#data#'):] or None}
        self.route_decisions = {}
        for node in root.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic'):
            routes = {}
            for route in node.findall('./vehRoutSta/vehicleRouteStatic'):
                routes[int(route.get('no'))] = tuple([int(node.get('link'))]
                                                     + [int(r.get('key')) for r in route.findall('./linkSeq/intObjectRef')]
                                                     + [int(route.get('destLink'))])
            self.route_decisions[int(node.get('no'))] = {'link': int(node.get('link')),
                                                         'pos': float(node.get('pos')), 'routes': routes,
                                                         'all_veh_types': node.get('allVehTypes') == 'true'}
        starts = {}
        for node in root.findall('./timeIntervalSets/timeIntervalSet'):
            starts[node.get('no')] = [float(t.get('start')) for t in node.findall('./timeInts/timeInterval')]
        self.input_interval_starts = tuple(starts.get('VEHICLEINPUT', ()))
        self.vehicle_inputs = {}
        for node in root.findall('./vehicleInputs/vehicleInput'):
            volumes = []
            for vol in node.findall('./timeIntVehVols/timeIntervalVehVolume'):
                _, start_ms = vol.get('timeInt').split()
                volumes.append({'start_sec': int(start_ms) / 1000.0, 'vph': float(vol.get('volume')),
                                'cont': vol.get('cont'), 'vol_type': vol.get('volType')})
            self.vehicle_inputs[int(node.get('no'))] = {'link': int(node.get('link')), 'volumes': volumes}

    def out_connectors(self, link):
        return sorted(n for n, x in self.links.items() if x.is_connector and x.from_link == link)

    def in_connectors(self, link):
        return sorted(n for n, x in self.links.items() if x.is_connector and x.to_link == link)

    def attachments(self, link):
        """(connector, 'from'|'to', position) of every connector that leaves or lands on link."""
        out = []
        for n, x in self.links.items():
            if x.is_connector and x.from_link == link:
                out.append((n, 'from', x.from_pos_m))
            if x.is_connector and x.to_link == link:
                out.append((n, 'to', x.to_pos_m))
        return sorted(out)

    def source_schedule(self, link):
        """ScheduleRow tuple of the one vehicle input on link (piecewise constant, last open)."""
        inputs = [v for v in self.vehicle_inputs.values() if v['link'] == link]
        _require(len(inputs) == 1, f'Link {link} needs exactly one vehicle input, found {len(inputs)}')
        volumes = sorted(inputs[0]['volumes'], key=lambda v: v['start_sec'])
        _require([v['start_sec'] for v in volumes] == list(self.input_interval_starts),
                 f'Vehicle input on {link} does not use the VEHICLEINPUT time intervals')
        _require(all(v['cont'] == 'false' for v in volumes), f'Vehicle input on {link} must be piecewise constant')
        rows = []
        for i, v in enumerate(volumes):
            end = volumes[i + 1]['start_sec'] if i + 1 < len(volumes) else None
            rows.append(oc.ScheduleRow(v['start_sec'], end, v['vph']))
        return oc.validate_schedule(rows)


def parse_runner_config(text):
    """RW_FW_*_CHAIN_LINKS and the ramp meter lists of a lane_native runner config."""
    def value(key):
        found = re.findall(r'^' + key + r' = "([^"\r\n]*)"', text, flags=re.MULTILINE)
        _require(len(found) == 1, 'Runner config lacks one ' + key)
        return found[0]

    chains = {road: tuple(int(x) for x in value(f'RW_{road}_CHAIN_LINKS').split(',')) for road in oc.ROADS}
    ids, scs = value('RW_RAMP_METER_IDS').split(','), value('RW_RAMP_METER_SCS').split(',')
    connectors = [int(x) for x in value('RW_RAMP_METER_CONNECTORS').split(',')]
    _require(len(ids) == len(scs) == len(connectors), 'Ramp meter lists differ in length')
    meters = list(zip(ids, scs, connectors))
    _require(len(meters) == len({m[0] for m in meters}) == len({m[1] for m in meters}), 'Ramp meter lists differ')
    return {'chains': chains, 'meters': tuple(meters)}


def sig_manifest_files(document):
    """{file name: sha256} of a sig_manifest.json (WP-E, plan §5).

    Accepted shapes: {"files": {name: sha}} or {"files": [{"name": ..., "sha256": ...}]}.
    """
    _require(isinstance(document, dict) and 'files' in document, 'sig_manifest needs a files entry')
    files = document['files']
    if isinstance(files, dict):
        pairs = list(files.items())
    else:
        _require(isinstance(files, list), 'sig_manifest files must be an object or a list')
        pairs = [(item.get('name'), item.get('sha256')) for item in files if isinstance(item, dict)]
        _require(len(pairs) == len(files), 'sig_manifest file entries must be objects')
    out = {}
    for name, sha in pairs:
        _require(isinstance(name, str) and name.lower().endswith('.sig') and '/' not in name and '\\' not in name,
                 'sig_manifest names are bare .sig file names')
        _require(isinstance(sha, str) and _HEX64.match(sha) is not None, 'sig_manifest sha256 must be lowercase hex')
        _require(name not in out, 'sig_manifest repeats ' + name)
        out[name] = sha
    return out


# --------------------------------------------------------------------------
# B1 core: the detector table
# --------------------------------------------------------------------------
def _chain_offsets(geometry, road):
    return [(int(p['link']), float(p['offset_m']), float(p['length_m'])) for p in geometry['chains'][road]]


def _through_station(net, geometry, road, b):
    """Where the downstream boundary b of an off-ramp's from_cell is counted exactly.

    Inside a link: an exact station at b. At a chain junction (b equals the chain
    offset of the next piece): the chain-internal connector carries every through
    vehicle, so count at its start (down, [0, 1)) or at its end (up, [L-0.1, L])."""
    pieces = _chain_offsets(geometry, road)
    for i in range(1, len(pieces)):
        if abs(pieces[i][1] - b) <= _TOL:
            before, after = net.links[pieces[i - 1][0]], net.links[pieces[i][0]]
            if after.is_connector:
                return 'down', after.no, CONNECTOR_STATION_M
            _require(before.is_connector, f'{road} junction at {b} joins two links without a connector')
            return 'up', before.no, None
    for i, (link, offset, length) in enumerate(pieces):
        nxt = pieces[i + 1][1] if i + 1 < len(pieces) else offset + length
        if offset < b < nxt:
            _require(not net.links[link].is_connector, f'{road} boundary {b} lies inside connector {link}')
            pos = round(b - offset, oc.POS_DECIMALS)
            _require(0 < pos < net.links[link].length_m, f'{road} boundary {b} lies outside link {link}')
            return 'at', link, pos
    raise ObsContractError(f'{road} boundary {b} is not on the chain')


def build_detector_rows(net, geometry, plan, runner):
    """(rows, report): the canonical obs150 detector table of the v2 network (plan B1, 1.7).

    net: InpxNetwork; geometry: the 31-cell metanet geometry of the same network;
    plan: the actuation plan physical_groups uses; runner: parse_runner_config.
    Every plan B1 assertion that needs only these inputs is checked here.
    """
    from evaluation.controllers.signal_head_observation import physical_groups

    checks = []

    def check(condition, what):
        _require(condition, 'Detector table assertion failed: ' + what)
        checks.append(what)

    check(geometry['network']['sha256'] == net.sha256, 'geometry was extracted from this network')
    chains = runner['chains']
    for road in oc.ROADS:
        check([p[0] for p in _chain_offsets(geometry, road)] == list(chains[road]),
              f'{road} runner chain equals the geometry chain')
    chain_all = set().union(*(set(v) for v in chains.values()))
    internal = frozenset(l for l in chain_all if net.links[l].is_connector)
    for road, links in chains.items():
        for i, link in enumerate(links):
            x = net.links[link]
            if x.is_connector:
                check(0 < i < len(links) - 1 and x.from_link == links[i - 1] and x.to_link == links[i + 1],
                      f'{road} internal connector {link} joins its chain neighbours')
    offs = {int(b['connector']): b for b in geometry['boundaries'] if b['kind'] == 'offramp'}
    ramps = {int(b['connector']): b for b in geometry['boundaries'] if b['kind'] == 'ramp'}
    check(len(offs) == oc.EXPECTED_OFFRAMP_COUNT and int(oc.OFFRAMP_10643) in offs, 'eight off-ramps including 10643')
    leaving = {n for l in chain_all for n in net.out_connectors(l)} - internal
    landing = {n for l in chain_all for n in net.in_connectors(l)} - internal
    check(leaving == set(offs), 'chain exits = the 8 off connectors (+ the 2 network ends)')
    check(landing == set(ramps) == {m[2] for m in runner['meters']}, 'chain entries = the 8 metered on-ramps')
    for road, links in chains.items():
        check(not net.in_connectors(links[0]) or all(net.links[c].to_pos_m > SOURCE_STATION_M
                                                     for c in net.in_connectors(links[0])),
              f'{road} origin link has no entry in [0, {SOURCE_STATION_M}]')
    # LPO:218-220: no on-ramp may land between a diverge and the through station (bypass pair).
    offsets = {road: {link: off for link, off, _ in _chain_offsets(geometry, road)} for road in oc.ROADS}

    def chain_pos(road, link, pos):
        return offsets[road][link] + pos

    attach = []
    for road, links in chains.items():
        for link in links:
            for connector, kind, pos in net.attachments(link):
                if connector not in internal and link not in internal:
                    attach.append((road, chain_pos(road, link, pos), connector))
    placement = {}
    for off, b in sorted(offs.items()):
        road = b['road']
        boundary = float(geometry['bounds'][road][int(b['from_cell']) + 1])
        diverge = chain_pos(road, net.links[off].from_link, net.links[off].from_pos_m)
        check(abs(diverge - float(b['chain_pos_m'])) <= 1e-6, f'off {off} chain position equals the geometry')
        # off_split reads the through station at the END of from_cell: the diverge must lie in that cell.
        check(float(geometry['bounds'][road][int(b['from_cell'])]) <= diverge < boundary,
              f'off {off} diverges inside its from_cell {b["from_cell"]}')
        between = [c for r, pos, c in attach if r == road and c != off and diverge < pos <= boundary + _TOL]
        check(not between, f'off {off}: no connector attaches between the diverge and its through boundary')
        bypass = [r for r in ramps.values() if r['road'] == road and int(r['to_cell']) == int(b['from_cell'])
                  and float(r['chain_pos_m']) > float(b['chain_pos_m'])]
        check(not bypass, f'off {off}: no post-branch ramp bypass pair (LPO:218-220)')
        placement[off] = _through_station(net, geometry, road, boundary)

    groups = physical_groups(str(net.path), plan)
    heads = sorted((h for members in groups.values() for h in members), key=lambda h: int(h['head_id']))
    check(len(groups) == EXPECTED_HEAD_GROUPS and len(heads) == EXPECTED_ELIGIBLE_HEADS
          and len({h['head_id'] for h in heads}) == len(heads), '105 head groups with 210 unique eligible heads')
    meter_scs = {m[1]: m for m in runner['meters']}
    meter_heads = sorted((h for h in net.heads if h['sc'] in meter_scs),
                         key=lambda h: (int(h['sc']), h['lane'], int(h['head_id'])))
    check(len(meter_heads) == EXPECTED_METER_HEADS, 'ten ramp meter heads')
    for sc, (name, _, connector) in meter_scs.items():
        on = [h for h in meter_heads if h['sc'] == sc]
        check(on and all(h['link'] == connector for h in on)
              and sorted(h['lane'] for h in on) == list(range(1, net.links[connector].lanes + 1)),
              f'meter {name} heads cover every lane of {connector}')
    check(not {h['sc'] for h in heads} & set(meter_scs), 'no eligible head belongs to a ramp meter')
    decision = net.route_decisions.get(oc.ROUTE_DECISION_10643)
    check(decision is not None and decision['link'] == int(oc.OFFRAMP_10643), 'RD 1126 lies on 10643')
    # The ledger labels and past_p read RD 1126 from every vehicle that crossed 10643.
    check(decision['all_veh_types'], 'RD 1126 applies to all vehicle types')
    destinations = sorted(int(c) for c in oc.DESTINATION_CONNECTORS_10643)
    ends = set()
    for route in decision['routes'].values():
        found = [c for c in route if c in destinations]
        check(len(found) == 1 and route[route.index(found[0]) - 1] == net.links[found[0]].from_link,
              'every RD 1126 route ends through one destination connector')
        ends.add(found[0])
    check(sorted(ends) == destinations, 'RD 1126 reaches exactly 10634/10635/10642')
    check(net.out_connectors(HEADFREE_SOURCE_LINK) == sorted(int(c) for c in oc.HEADFREE_CONNECTORS),
          'link 403 leaves only through 10565 and 10570')

    specs = []

    def geometry_of(link, **extra):
        x = net.links[link]
        return {'link_length_m': x.length_m, 'lane_count': x.lanes, **extra}

    def lanes_of(link):
        return range(1, net.links[link].lanes + 1)

    def down(role, ref, link, pos, **extra):
        for lane in lanes_of(link):
            specs.append((role, ref, link, lane, pos, 'exact', 'down',
                          (oc.SegmentPiece(link, 0.0, pos, (lane,)),), geometry_of(link, **extra)))

    def up_end(role, ref, link):
        length = net.links[link].length_m
        pos = round(length - END_OFFSET_M, oc.POS_DECIMALS)
        for lane in lanes_of(link):
            specs.append((role, ref, link, lane, pos, 'end_minus', 'up',
                          (oc.SegmentPiece(link, pos, _ceil6(length), (lane,)),),
                          geometry_of(link, offset_from_end_m=END_OFFSET_M)))

    for h in heads:
        specs.append(('head', f"{h['head_id']}|{h['sc']}-{h['sg']}", int(h['link']), int(h['lane']),
                      round(float(h['position_m']), oc.POS_DECIMALS), 'exact', 'at', (),
                      geometry_of(int(h['link']), head_position_m=float(h['position_m']))))
    for h in meter_heads:
        specs.append(('meter_head', f"{h['head_id']}|{h['sc']}-{h['sg']}", h['link'], h['lane'],
                      round(h['position_m'], oc.POS_DECIMALS), 'exact', 'at', (),
                      geometry_of(h['link'], head_position_m=h['position_m'])))
    for off in sorted(offs):
        down('off_entry', str(off), off, CONNECTOR_STATION_M, linkeval_segment_m=net.links[off].eval_segment_m)
    for off in sorted(offs):
        kind, link, pos = placement[off]
        if kind == 'at':
            for lane in lanes_of(link):
                specs.append(('through', str(off), link, lane, pos, 'exact', 'at', (), geometry_of(link)))
        elif kind == 'down':
            down('through', str(off), link, pos)
        else:
            up_end('through', str(off), link)
    up_end('x10643_exit', oc.OFFRAMP_10643, int(oc.OFFRAMP_10643))
    for connector in destinations:
        down('destination', str(connector), connector, CONNECTOR_STATION_M)
    for connector in sorted(ramps):
        down('ramp_arrival', 'RM_C%d' % connector, connector, CONNECTOR_STATION_M,
             linkeval_segment_m=net.links[connector].eval_segment_m)
    for road in oc.ROADS:
        down('source', road, chains[road][0], SOURCE_STATION_M)
    for road in oc.ROADS:
        up_end('chain_end', road, chains[road][-1])
    for connector in sorted(int(c) for c in oc.HEADFREE_CONNECTORS):
        down('headfree', str(connector), connector, CONNECTOR_STATION_M,
             linkeval_segment_m=net.links[connector].eval_segment_m)

    lo, hi = oc.DETECTOR_KEY_RANGE
    check(len(specs) <= hi - lo + 1, 'the table fits the key range')
    rows = []
    for i, (role, ref, link, lane, pos, mode, orientation, segment, geo) in enumerate(specs):
        key = lo + i
        check(key not in net.dcp_keys and key not in net.dcm_keys, f'key {key} is unused in the network')
        x = net.links[link]
        check(1 <= lane <= x.lanes and 0 < pos < x.length_m, f'{role} {ref}: lane {lane} and pos {pos} lie on {link}')
        for piece in segment:
            touching = [c for c, _, p in net.attachments(piece.link)
                        if c not in internal and piece.from_m - _TOL <= p <= piece.to_m + _TOL]
            check(not touching, f'{role} {ref}: no connector outside the chain touches segment {piece}')
        rows.append(oc.DetectorRow(key, key, role, ref, link, lane, pos, mode, orientation,
                                   oc.expected_boundary_ref(role, ref), tuple(segment), geo))
    rows = oc.validate_detector_rows(rows)
    for number, point in sorted(RULE_CROSSCHECK_POINTS.items()):
        refs = net.dcm_points.get(number)
        check(refs is not None and len(refs) == 1 and net.dcp_points.get(refs[0]) == point,
              f'RULE measurement {number} is exactly one point at {point}')
    rule_pairs = rule_crosscheck_pairs(rows)
    check(sorted(row.dcm_no for _, row in rule_pairs) == sorted(r.dcm_no for r in rows if r.role == 'source')
          and len(rule_pairs) == len(RULE_CROSSCHECK_POINTS),
          'every source station shares its point with exactly one RULE measurement')
    counts = defaultdict(int)
    for row in rows:
        counts[row.role] += 1
    report = {'network_sha256': net.sha256, 'counts': dict(sorted(counts.items())), 'rows': len(rows),
              'head_groups': len(groups), 'eligible_heads': len(heads),
              'chain_internal_connectors': sorted(internal),
              'rule_crosscheck': {str(row.dcm_no): number for number, row in rule_pairs},
              'through_placement': {str(off): {'kind': kind, 'link': link, 'pos': pos}
                                    for off, (kind, link, pos) in sorted(placement.items())},
              'constants': {'connector_station_m': CONNECTOR_STATION_M, 'source_station_m': SOURCE_STATION_M,
                            'end_offset_m': END_OFFSET_M, 'key_start': lo},
              'assertions': checks}
    return rows, report


def rule_crosscheck_pairs(rows):
    """[(RULE measurement, detector row)] for every table row at a RULE_CROSSCHECK_POINTS point."""
    at = defaultdict(list)
    for row in rows:
        at[(row.link, row.lane, row.pos)].append(row)
    return [(number, row) for number, point in sorted(RULE_CROSSCHECK_POINTS.items()) for row in at.get(point, ())]


def check_rule_crosscheck(obs, rows):
    """Vehs of a table point must equal the RULE measurement at the same point (same k).

    Guards the runner's install (lane, position) and its Vehs read at no cost. A
    table without such points (synthetic tables) has nothing to compare.
    Returns the compared pairs.
    """
    pairs = rule_crosscheck_pairs(rows)
    for number, row in pairs:
        _require(str(number) in obs['rule_crosscheck'],
                 f'raw.rule_crosscheck lacks RULE measurement {number} (shares the point of {row.boundary_ref})')
        rule, own = obs['rule_crosscheck'][str(number)], obs['detectors'][str(row.dcm_no)]
        _require(rule == own, f'{row.boundary_ref} lane {row.lane}: Vehs {own} differs from RULE measurement '
                              f'{number} {rule} at the same point')
    return pairs


def read_sidecar(csv_path, csv_sha256):
    """The generator's verification manifest next to the CSV; it must describe these bytes."""
    path = Path(str(csv_path)[:-len('.csv')] + SIDECAR_SUFFIX) if str(csv_path).endswith('.csv') else None
    _require(path is not None and path.is_file(), 'Detector table lacks its build manifest ' + str(path))
    document = json.loads(path.read_text(encoding='utf-8'))
    _require(document.get('schema') == DETECTOR_BUILD_SCHEMA, 'Unsupported detector build manifest')
    _require(document['output']['sha256'] == csv_sha256, 'Detector build manifest describes another table')
    return document


def read_pinned(pin, what):
    path = resolve_repo(pin['path'])
    data = path.read_bytes()
    _require(_sha256(data) == pin['sha256'], what + ' changed: ' + str(path))
    return path, data


# --------------------------------------------------------------------------
# Obs150Context (plan 1.6)
# --------------------------------------------------------------------------
def lane_map_10643(net):
    """{link: {lane: 10643 lane}} along 10643 -> 126 -> 10641/10700 -> 71 (inpx connector lanes)."""
    off = net.links[int(oc.OFFRAMP_10643)]
    out = {off.no: {lane: lane for lane in range(1, off.lanes + 1)}}
    receiving = off.to_link
    out[receiving] = {off.to_lane + i: 1 + i for i in range(off.lanes)}
    from evaluation.controllers.obs150_lane import APPROACH_LINK_10643
    for connector in net.out_connectors(receiving):
        x = net.links[connector]
        _require(x.to_link == APPROACH_LINK_10643, f'{connector} leaves {receiving} away from link 71')
        out[connector] = {}
        for i in range(x.lanes):
            origin = out[receiving].get(x.from_lane + i)
            if origin is not None:
                out[connector][1 + i] = origin
                out.setdefault(APPROACH_LINK_10643, {})
                _require(out[APPROACH_LINK_10643].get(x.to_lane + i, origin) == origin,
                         'Link 71 lane maps to two 10643 lanes')
                out[APPROACH_LINK_10643][x.to_lane + i] = origin
    return {link: dict(sorted(lanes.items())) for link, lanes in out.items()}


def route_destinations_10643(net):
    decision = net.route_decisions[oc.ROUTE_DECISION_10643]
    destinations = {int(c) for c in oc.DESTINATION_CONNECTORS_10643}
    out = {}
    for number, route in sorted(decision['routes'].items()):
        found = [c for c in route if c in destinations]
        _require(len(found) == 1, f'RD 1126 route {number} does not end through one destination connector')
        out[number] = found[0]
    return out


def sig_table(net, sig_manifest_path, sig_manifest_bytes):
    """{sc: SigProgram} of every native .sig of the network, read from the pinned byte copies."""
    from evaluation.controllers.obs150_signal_clock import sig_program_from_file
    files = sig_manifest_files(json.loads(sig_manifest_bytes.decode('utf-8-sig')))
    folder = Path(sig_manifest_path).parent
    used = {c['sig_file'] for c in net.controllers.values() if c['sig_file']}
    _require(used == set(files), f'sig_manifest lists {len(files)} files, the network uses {len(used)}')
    out = {}
    for sc, controller in sorted(net.controllers.items(), key=lambda kv: int(kv[0])):
        name = controller['sig_file']
        if name is None:
            continue
        _require(controller['type'] == 'FIXEDTIME', f'SC {sc} is not a fixed-time controller')
        out[sc] = sig_program_from_file(sc, folder / name, controller['prog_no'], sha256=files[name])
    return out


def load_context(document, paths, *, manifest_sha256=None):
    """Obs150Context of a coupled-lane-plant/v2 manifest (built once per decision process).

    paths: LPR load_sources {source key: read_pin result}. manifest_sha256: the
    sha256 of the manifest FILE bytes (the document alone cannot give it; LPR
    has it as context['manifest_sha256']). The pinned detector CSV must equal the
    table build_detector_rows makes from the pinned network, geometry, runner
    config and the actuation plan recorded in the CSV's build manifest.
    """
    oc.validate_plant_manifest_v2(document)
    _require(isinstance(manifest_sha256, str) and _HEX64.match(manifest_sha256) is not None,
             'load_context needs manifest_sha256 (the plant manifest file sha256)')
    sources = document['sources']

    def pinned(key):
        _require(key in paths, 'paths lacks the pinned source ' + key)
        path = Path(paths[key])
        data = path.read_bytes()
        _require(_sha256(data) == sources[key]['sha256'], f'{key} differs from its manifest pin: {path}')
        return path, data

    network_path, network_bytes = pinned('network')
    net = InpxNetwork(network_path, network_bytes)
    geometry = json.loads(pinned('geometry')[1].decode('utf-8-sig'))
    reference = json.loads(pinned('reference_config')[1].decode('utf-8-sig'))
    runner = parse_runner_config(pinned('runner_config')[1].decode('latin-1'))
    sig_path, sig_bytes = pinned('sig_manifest')
    csv_pin = document['observation']['detectors']
    csv_path = resolve_repo(csv_pin['path'])
    rows, csv_sha = oc.read_detector_csv(csv_path, csv_pin['sha256'])
    sidecar = read_sidecar(csv_path, csv_sha)
    _require(sidecar['network']['sha256'] == sources['network']['sha256'],
             'Detector table was built from another network')
    _, plan_bytes = read_pinned(sidecar['sources']['plan'], 'Actuation plan of the detector table')
    plan = json.loads(plan_bytes.decode('utf-8'))
    expected, _ = build_detector_rows(net, geometry, plan, runner)
    _require(oc.format_detector_csv(expected) == oc.format_detector_csv(rows),
             'The pinned detector table differs from the table of the pinned sources')
    from evaluation.controllers.signal_head_observation import physical_groups
    groups = physical_groups(str(network_path), plan)
    chains = runner['chains']
    internal = frozenset(l for links in chains.values() for l in links if net.links[l].is_connector)
    # The receiving-node ramps: the plant's component.ramp_receiving_nodes is this key
    # (metanet_calibration_v1/canonical_harness.py:489). A missing key fails here, not at derive.
    receiving_nodes = (reference.get('freeway') or {}).get('physical_ramp_receiving_nodes')
    _require(isinstance(receiving_nodes, dict) and receiving_nodes,
             'reference_config lacks freeway.physical_ramp_receiving_nodes (the receiving-node ramps)')
    receiving = set(receiving_nodes)
    offramps, ramps = {}, {}
    for b in geometry['boundaries']:
        connector = str(b.get('connector'))
        if b['kind'] == 'offramp':
            offramps[connector] = oc.OfframpRef(connector, b['road'], int(b['from_cell']),
                                                tuple(range(1, net.links[int(connector)].lanes + 1)),
                                                'off_entry:' + connector, 'through:' + connector)
        elif b['kind'] == 'ramp':
            ramps[b['id']] = oc.RampArrivalRef(b['id'], connector, tuple(range(1, net.links[int(connector)].lanes + 1)),
                                               'ramp_arrival:' + b['id'], b['id'] in receiving)
    _require(receiving <= set(ramps), 'A receiving node is not an on-ramp of the geometry')
    schedules = {road: net.source_schedule(chains[road][0]) for road in oc.ROADS}
    for road in oc.ROADS:
        calibrated = sorted((r for r in geometry['desired_source_demand'] if r['road'] == road),
                            key=lambda r: float(r['start_sec']))
        _require([(r.start_sec, r.end_sec, r.vph) for r in schedules[road]]
                 == [(float(r['start_sec']), None if r['end_sec'] is None else float(r['end_sec']),
                      float(r['desired_volume_vph'])) for r in calibrated],
                 road + ': native input schedule differs from the calibration desired_source_demand')
    boundaries = oc.group_boundaries(rows)
    context = oc.Obs150Context(
        manifest_sha256=manifest_sha256, network_sha256=net.sha256, detector_csv_path=str(csv_path),
        detector_csv_sha256=csv_sha, detectors=rows, boundaries=boundaries, chain_links=chains,
        chain_internal_connectors=internal, offramps=offramps, ramp_arrivals=ramps,
        source_refs={road: 'source:' + road for road in oc.ROADS},
        chain_end_refs={road: 'chain_end:' + road for road in oc.ROADS},
        headfree_refs={c: 'headfree:' + c for c in oc.HEADFREE_CONNECTORS},
        x10643_exit_ref='x10643_exit:' + oc.OFFRAMP_10643,
        destination_refs={c: 'destination:' + c for c in oc.DESTINATION_CONNECTORS_10643},
        lane_map_10643=lane_map_10643(net), route_destinations_10643=route_destinations_10643(net),
        head_groups={key: tuple(members) for key, members in groups.items()},
        sig_table=sig_table(net, sig_path, sig_bytes), source_schedule=schedules)
    oc.validate_context(context)
    return context


# --------------------------------------------------------------------------
# derive / merge / lane observation (plan B7)
# --------------------------------------------------------------------------
def _removal_assignments(context, err_rows, start_s, end_s):
    chain = set().union(*(set(v) for v in context.chain_links.values()))
    offset_refs = [ref for ref, rows in context.boundaries.items() if rows[0].orientation != 'at']
    out = []
    for row in oc.window_removals(err_rows, start_s, end_s):
        refs = [ref for ref in offset_refs if oc.removals_in_boundary([row], context.boundaries[ref])]
        out.append({'vehicle_id': row['vehicle_id'], 'time_sec': row['time_sec'], 'link': row['link'],
                    'position_m': row['position_m'], 'route_decision': row['route_decision'],
                    'route_index': row['route_index'], 'boundary_refs': refs, 'on_chain': row['link'] in chain})
    return {'window_total': len(out), 'rows': out}


def derive(raw, context):
    """obs150-derived/v1 of the state raw (top-level 'obs150'); a pure function of the pinned bundle."""
    from evaluation.controllers import obs150_head_window, obs150_lane, obs150_signal_clock

    obs = raw[oc.RAW_STATE_KEY]
    oc.validate_raw(obs, context.detectors, expected_simres=oc.EXPECTED_SIMRES)
    _require(obs['detector_config']['sha256'] == context.detector_csv_sha256,
             'The bundle was captured with another detector table')
    check_rule_crosscheck(obs, context.detectors)
    # CONTRACT 6: B4 re-checks the run network folder's .sig copies of every natively
    # used SC against sig_table. The runner writes network_path in every state
    # (VBS:2817); without it that check would be skipped, so it is required.
    network_path = raw.get('network_path')
    _require(isinstance(network_path, str) and network_path and Path(network_path).is_absolute(),
             'The state lacks an absolute network_path (the run .sig copies cannot be re-checked)')
    start, end, k = oc.bundle_interval(obs['sim_sec'])
    bundle = oc.load_bundle(raw)
    mer_rows, err_rows = list(bundle.mer_rows), list(bundle.err_rows)
    boundaries = oc.evaluate_boundaries(obs, context.detectors, bundle.frame_end, bundle.frame_start, err_rows)
    assignment = oc.assign_window(obs, mer_rows)
    clocks = obs150_signal_clock.windows(obs['signal_log'], context.sig_table, obs['window'],
                                         network_dir=Path(network_path).parent)
    head_window = obs150_head_window.build(raw, context, clocks, mer_rows, bundle=bundle, boundaries=boundaries)
    lane = obs150_lane.derive(raw, context, mer_rows, err_rows, bundle.frame_end, bundle.frame_start,
                              boundaries=boundaries, assignment=assignment)
    mer, err, frames = obs['mer'], obs['err'], obs['frames']
    derived = {'schema': oc.DERIVED_SCHEMA, 'sim_sec': obs['sim_sec'], 'k': k,
               'window': None if k is None else {'start_s': start, 'end_s': end}, 'run_id': obs['run_id'],
               'strict': bool(obs['ground_truth_windows']),
               'inputs': {'raw_sha256': oc.canonical_sha256(obs),
                          'detector_config_sha256': obs['detector_config']['sha256'],
                          'mer_chunk_sha256': mer['chunk_sha256'], 'mer_index_sha256': mer['index_sha256'],
                          'err_chunk_sha256': err['chunk_sha256'],
                          'frame_current_sha256': frames['current']['sha256'],
                          'frame_previous_sha256': frames['previous']['sha256']},
               'boundaries': {ref: terms.as_dict() for ref, terms in boundaries.items()},
               'lag': {'sum_tail': assignment.sum_tail, 'max_t_any': assignment.max_t_any,
                       'threshold_s': end - oc.LAG_MARGIN_S + oc.BOUNDARY_EPS_S, 'ok': assignment.lag_ok,
                       'err_max_sim_sec': err['max_sim_sec']},
               'tails': {str(dcp): n for dcp, n in sorted(assignment.tails.items())},
               'boundary_ambiguous': 0 if head_window is None else sum(h['boundary_ambiguous']
                                                                       for h in head_window['heads']),
               'removals': _removal_assignments(context, err_rows, start, end),
               'head_window': head_window, **lane}
    oc.validate_derived(derived)
    return derived


def merge_into_state(raw, derived):
    """raw' = raw with exactly the four fields of CONTRACT 5.5 and the in-memory obs150_derived."""
    oc.validate_derived(derived)
    obs = raw[oc.RAW_STATE_KEY]
    _require(derived['sim_sec'] == obs['sim_sec'] and derived['run_id'] == obs['run_id']
             and derived['inputs']['raw_sha256'] == oc.canonical_sha256(obs), 'Derived document of another bundle')
    _require(oc.MERGED_DERIVED_KEY not in raw, 'The state is already merged')
    far = (raw.get('local_observation') or {}).get('far_measurement')
    _require(isinstance(far, dict) and 'freeway_exit_count' in far and far['freeway_exit_count'] is None,
             'The v2 runner leaves far_measurement.freeway_exit_count null for the merge')
    merged = copy.deepcopy(raw)
    local = merged['local_observation']
    local['signal_observation_window'] = copy.deepcopy(derived['head_window'])
    local['link_departures_window'] = dict(derived['link_departures_window'])
    local['far_measurement']['freeway_exit_count'] = derived['freeway_exit_count']['value']
    local['far_measurement']['freeway_exit_count_provenance'] = oc.FREEWAY_EXIT_PROVENANCE
    merged[oc.MERGED_DERIVED_KEY] = copy.deepcopy(derived)
    oc.validate_merged_state(raw, merged)
    return merged


def lane_observation(context, raw):
    """lane-plant-observation/v2 (CONTRACT 5.2) from the MERGED state raw'."""
    derived = raw.get(oc.MERGED_DERIVED_KEY)
    _require(derived is not None, 'lane_observation reads the merged state (merge_into_state)')
    oc.validate_derived(derived)
    obs = raw[oc.RAW_STATE_KEY]
    _require(derived['sim_sec'] == obs['sim_sec'] and derived['run_id'] == obs['run_id']
             and derived['inputs']['raw_sha256'] == oc.canonical_sha256(obs), 'Derived document of another bundle')
    _require(derived['inputs']['detector_config_sha256'] == context.detector_csv_sha256,
             'Derived document of another detector table')
    local = raw.get('local_observation') or {}
    far = local.get('far_measurement') or {}
    _require(far.get('freeway_exit_count') == derived['freeway_exit_count']['value']
             and far.get('freeway_exit_count_provenance') == oc.FREEWAY_EXIT_PROVENANCE
             and local.get('link_departures_window') == derived['link_departures_window']
             and 'signal_observation_window' in local
             and local['signal_observation_window'] == derived['head_window'],
             'The merged local_observation differs from its derived document')
    end = obs['sim_sec']
    current = obs['frames']['current']
    frame = oc.load_frame(oc.resolve(obs, current['path']), current['sha256'], end)
    split = derived['off_split']
    observation = {
        'schema': oc.LANE_OBS_SCHEMA_V2, 'information_cutoff_s': end,
        'history_start_s': max(0, end - oc.DECISION_INTERVAL_SEC), 'future_traffic_inputs': False,
        'lane_group_dynamics': {}, 'current_exit_labels': {},
        'off_split_ratio': {off: row['ratio'] for off, row in split.items()},
        'off_split_history': {off: {key: row[key] for key in oc.OFF_SPLIT_HISTORY_KEYS} for off, row in split.items()},
        'frames': [frame],
        'ramp_arrival_shares': copy.deepcopy(derived['ramp_arrival_shares']),
        'offramp_10643_history': copy.deepcopy(derived['offramp_10643_history']),
        'offramp_10643_lane_shares': list(derived['offramp_10643_lane_shares']),
        'freeway_exit_count': derived['freeway_exit_count']['value'],
        'source_boundary': copy.deepcopy(derived['source_boundary']),
        'source': {'run_id': obs['run_id'], 'manifest_sha256': context.manifest_sha256,
                   'derived_sha256': oc.canonical_sha256(derived),
                   **{key: derived['inputs'][key] for key in oc.DERIVED_INPUT_KEYS}}}
    oc.validate_lane_observation_v2(observation)
    return observation


# --------------------------------------------------------------------------
# T10: local_observation key parity (v1 run sdmpc_lp_9000c state_000900.json)
# --------------------------------------------------------------------------
# Written by the v2 runner exactly as in v1 (VBS WriteStateJson local_observation block).
RUNNER_V2_KEYS = ('schema_version', 'mode', 'source', 'detector_mapping_json', 'global_vehicle_scan_masked',
                  'scan_ok', 'observed_vehicle_count', 'unobservable_vehicle_count', 'link_counts',
                  'link_speeds_kph', 'link_stopped_counts', 'link_queue_tail_pos_m', 'queue_bins', 'queue_bin_m',
                  'queue_counters', 'far_measurement')
# Filled by merge_into_state from the derived document (CONTRACT 5.5).
MERGED_V2_KEYS = ('signal_observation_window', 'link_departures_window')
PRODUCED_V2 = RUNNER_V2_KEYS + MERGED_V2_KEYS
# (key, consumer, reason). RW_QUEUE_WINDOW=0 in obs150 mode (expected_runner_env), so
# the VBS QueueWindowEnabled() block (VBS:2741-2748) writes none of these.
RETIRED_V2 = (
    ('link_counts_window_mean', 'AD:1143-1148 (_link_counts_from_local_observation)',
     'read only when urban.queue.window_stat is mean|max; it is "" in the n31 tuning (OBS1), so the '
     'instantaneous link_counts are used either way'),
    ('link_stopped_counts_window_mean', 'AD:5774-5782 (_observed_stopped_counts)',
     'read only when urban.queue.window_stat is mean; "" in the n31 tuning'),
    ('link_stopped_counts_window_max', 'AD:5774-5782 (_observed_stopped_counts)',
     'read only when urban.queue.window_stat is max; "" in the n31 tuning'),
    ('queue_window_samples', 'AD:1146, AD:5780',
     'sample count of the retired 5 s queue window; only read together with the window keys above'),
)
# A produced key whose v2 content is narrower than v1 (not retired, but different).
NARROWED_V2 = (
    ('link_departures_window', 'SHO:400 (head-free service)',
     'v2 holds only {"403": cross(10565)+cross(10570)}; with head observation on, AD:4276-4281 returns before '
     'any other link departure is read (NEW-12)'),
    ('signal_observation_window', 'SHO:114-251, HSR:95-158', 'physical-head-window/v2 (plan B5)'),
    ('far_measurement', 'AD:8053-8081', 'freeway_exit_count = conservation_v2 (merge); link_volume_veh_h is '
     'read (Current,k,All), same Edie meaning (D-D (a))'),
)
