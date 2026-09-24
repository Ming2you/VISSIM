r"""G1 ground-truth comparator (plan D6): every 150 s obs150 quantity against 0.1 s vehicle truth.

    obs150_verify_gt.py <run_dir | decisions_dir> [--gt-dir DIR] [--windows 750:900,1050:1200]
                        [--network INPX] [--err ERR] [--sig-rule next|previous] [--com-head-delay 0|1]
                        [--out FILE]

PT check_probe.py generalised from 18 probe points to the obs150 detector table, and from
"count per point" to every item of plan section 7 (G1), vehicle by vehicle:

  detectors        per point: Vehs(Current,k,All) = GT crossings of the station; .mer window
                   entries (obs150_contract.assign_window) = GT vehicles; the GT vehicles that
                   crossed in (T-1, T] and are not yet in .mer = the point's tail; every matched
                   .mer entry time lies in its GT 0.1 s step (+-0.006 s rounding)
  boundaries       derived IdentityTerms.cross (station) and lane cross (when lane_exact) = GT
                   crossings of the boundary point x (CONTRACT 3: at -> p, down -> segment start,
                   up -> segment end); down/up lane terms carry the lane at p, so they are judged
                   only where a consumer reads them (LANE_JUDGED_ROLES) and reported elsewhere
  heads            head window v2: crossings, qualified_crossings (GT crossings whose 0.1 s step
                   was GREEN in gt_sig), green_sec (GREEN steps / 10); in a COM-owned second the read
                   back is taken --com-head-delay s earlier (D10, SignalTruth)
  d10              D10 on the vehicles (D10Probe): after each COM GREEN write at u with a lead vehicle
                   standing at the head, it departs at u+0.1 (heads took the write at u: delay 0) or
                   u+1.1 (one update later: delay 1). Any departure contradicting --com-head-delay
                   FAILs; confirming departures PASS it; COM heads in the GT windows without a single
                   usable GREEN write leave the run INCOMPLETE (GT_D10 ... NOT_RECHECKED). Crossings of
                   COM heads in the second after a RED write are reported (legal only with delay 1)
  ledger_10643     (vehicle, lane, destination connector) of every GT crossing of the 10643 end;
                   the destination is the GT route of routing decision 1126 (inpx routes)
  ramp_arrival_shares, off_split (off_entry and through crossings), source admitted_window,
  link_departures_window 403 (headfree 10565 + 10570),
  freeway_exit_count  GT = vehicles on a chain link (RW_FW_*_CHAIN_LINKS) at one step and off
                   the chain (another link, gone, removed) at the next; the unrecorded chain
                   connectors are closed at the window end (ChainMembership)
  lag / boundary_ambiguous (strict run: 0), signal_log fail events, meter heads (GREEN-second
  throughput, D12 audit only), .err realtime (D11: removals of the window already in the T chunk
  vs the final .err), Edie residuals (reported).

Ground truth files (A9): gt_veh.csv, gt_sig.csv, gt_meta.csv, found in --gt-dir, else
<decisions>\obs150_gt\ (where the runner writes them, VBS Obs150GtStepTo), else the run folder or
the decisions folder. Columns are read by header name:
  gt_veh.csv  t10, veh (runner) or no (probe), lane ('<link>-<lane>') or link + lane, pos[, speed]
              [, route_no][, rout_dec_no]
  gt_sig.csv  t10, sc, sg, sig_state
Without a speed column (the runner writes none) the 0.1 s reach of a vehicle is its own
displacement over the previous step on one link, else MAX_SPEED_KMH; both plus REACH_SLACK_M.
A GT sample at t10 is the state after that stop's writes; --sig-rule next (default, PRB g) lets it
govern the step (t10, t10+1], --sig-rule previous the step (t10-1, t10]. Both are reported.

GT crossing of a point x = (link L, position, lanes) between frames a and b = a + 0.1 s:
  A  on L at a and b:  pos_a < x <= pos_b
  B  on L at a only:   pos_a < x and the exit position on L is >= x: the from_pos of the
                       connector it is on at b, the end of L for a connector or a network exit;
                       gone and removed (.err) is no crossing
  C  on L at b only:   pos_b >= x and the entry position on L is <= x: 0 on a connector or an
                       origin link, else to_pos of the connector it came from
  Several candidate exits/entries on both sides of x -> 'ambiguous'; none -> 'unexplained'.
  Both are listed and make the verdict FAIL (the comparator never guesses).
  The crossing lane is lane_a = lane_b (A), lane_a (B), lane_b (C). It is UNKNOWN when the step
  holds a lane change: A with lane_a != lane_b; B/C when the lane the connector's lane mapping
  (inpx fromLinkEndPt/toLinkEndPt "<link> <first lane>") gives for the leaving/entering side
  differs; a short connector traversed inside one step when its two ends give different connector
  lanes. Such an event has lane None and carries the lanes it may have crossed in.
Lane-unknown crossings (PRB f): VISSIM counts a vehicle at the lane-level point of the one lane it
is in, so every lane-unknown crossing of the detector points of one link in one step (all its
candidate points) is attributed by .mer: the points whose window entries hold the vehicle must be
exactly the points of one possible lane. Not in .mer before the last second of the window: explained
only when a possible lane has no point there (it crossed on a lane without a detector), else FAIL.
Not in .mer in the last second: it may be a tail; the rows such crossings touch form a group, and
some choice of one lane per open crossing must give every row of the group its Vehs (heads: its
derived crossings and qualified crossings as well). Heads and 'at' boundaries (one point per lane
at the detector itself) use the same attribution; a lane-unknown event at the station point of
another boundary whose lanes it does not cover leaves that item unjudged.
Verdict: FAIL when a judged item fails; INCOMPLETE when an item that is not report-only
(REPORT_ONLY: signal_log, meter_heads, err_realtime, edie) is not judged (ok None: a boundary point
on a link the GT does not record, gt_sig not covering the steps --sig-rule needs, ...); else PASS.
The run verdict adds the d10 result of all windows (run_d10). Writes <out> (default
<run>/obs150_gt_verdict.json), prints GT_D10 and GT_VERDICT PASS|FAIL|INCOMPLETE and exits 0 | 1 | 3
(2: GT_ERROR).
"""
from __future__ import annotations

import argparse
import csv
import io
import itertools
import json
import math
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from n31_common import ROOT, ToolError, find_decisions_dir, oc, read_json, require, vbs_constants, write_json  # noqa: E402

INF = float('inf')
POS_TOL = 1e-6
END_TOL_M = 0.5            # a connector leaving within this of the link end continues the link
REACH_SLACK_M = 1.0        # front travel per 0.1 s is speed*0.1 plus this slack
MAX_SPEED_KMH = 200.0      # reach bound when gt_veh.csv carries no speed column
MER_STEP_TOL_S = 0.006     # .mer times are rounded to 0.01 s (PRB h: |dt| < 0.006)
ROUTE_DECISION_10643 = oc.ROUTE_DECISION_10643
DESTINATIONS_10643 = tuple(int(c) for c in oc.DESTINATION_CONNECTORS_10643)
SIG_RULES = ('next', 'previous')
REPORT_ONLY = frozenset({'signal_log', 'meter_heads', 'err_realtime', 'edie'})   # ok None by design
# down/up boundaries whose lane terms a consumer reads (CONTRACT 3: ramp arrival shares, the 10643 lane split):
# their lanes are judged; every other boundary's lane terms are reported (only their sum is exact).
LANE_JUDGED_ROLES = ('ramp_arrival', 'x10643_exit')
VERDICT_EXIT = {'PASS': 0, 'FAIL': 1, 'INCOMPLETE': 3}
MAX_LANE_CHOICES = 4096    # lane choices of one group of open lane-unknown crossings (else not judged)
_UNKNOWN = object()        # a lane the connector mapping cannot give


# ---------------------------------------------------------------- network geometry (inpx)
class Link(NamedTuple):
    no: int
    connector: bool
    from_link: int | None
    from_pos: float | None
    to_link: int | None
    to_pos: float | None
    length: float
    from_lane: int | None = None   # connector: the from_link lane its lane 1 leaves (None: not in the source)
    to_lane: int | None = None     # connector: the to_link lane its lane 1 joins
    lanes: int | None = None       # lane count


def _link_lane(text):
    parts = text.split()
    return int(parts[0]), (int(parts[1]) if len(parts) > 1 else None)


class Network:
    def __init__(self, path):
        root = ET.parse(path).getroot()
        self.links, self.out, self.into = {}, defaultdict(list), defaultdict(list)
        for el in root.findall('./links/link'):
            no = int(el.get('no'))
            points = [(float(p.get('x')), float(p.get('y'))) for p in el.findall('./geometry/linkPolyPts/linkPolyPoint')]
            length = math.fsum(math.dist(a, b) for a, b in zip(points, points[1:]))
            lanes = len(el.findall('./lanes/lane')) or None
            fp, tp = el.find('./fromLinkEndPt'), el.find('./toLinkEndPt')
            if fp is not None and tp is not None:
                (from_link, from_lane), (to_link, to_lane) = _link_lane(fp.get('lane')), _link_lane(tp.get('lane'))
                link = Link(no, True, from_link, float(fp.get('pos')), to_link, float(tp.get('pos')), length,
                            from_lane, to_lane, lanes)
                self.out[link.from_link].append(link)
                self.into[link.to_link].append(link)
            else:
                link = Link(no, False, None, None, None, None, length, lanes=lanes)
            self.links[no] = link
        # links with a vehicle input: inserted vehicles enter them at 0 even when a connector also
        # feeds the link further down (link 26: input 1099, and connector 10480 joins at 3625.8 m)
        self.input_links = {int(el.get('link')) for el in root.findall('./vehicleInputs/vehicleInput')}
        self.routes = {}
        for d in root.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic'):
            for r in d.findall('./vehRoutSta/vehicleRouteStatic'):
                self.routes[int(d.get('no')), int(r.get('no'))] = (
                    [int(d.get('link'))] + [int(v.get('key')) for v in r.findall('./linkSeq/intObjectRef')]
                    + [int(r.get('destLink'))])

    @classmethod
    def from_parts(cls, links, routes=None):
        """Test/fixture constructor from Link rows."""
        self = cls.__new__(cls)
        self.links, self.out, self.into = {}, defaultdict(list), defaultdict(list)
        self.input_links = set()
        for link in links:
            self.links[link.no] = link
            if link.connector:
                self.out[link.from_link].append(link)
                self.into[link.to_link].append(link)
        self.routes = dict(routes or {})
        return self

    def destination_10643(self, route):
        path = self.routes.get((ROUTE_DECISION_10643, route))
        if path is None:
            return None
        found = [c for c in path if c in DESTINATIONS_10643]
        return found[0] if found else None


# ---------------------------------------------------------------- ground truth readers
class Pos(NamedTuple):
    link: int
    lane: int
    pos: float
    speed: float | None
    route: int | None
    rdec: int | None


COLUMN_ALIASES = {'no': ('no', 'veh'), 'link': ('link', 'link_no'), 'speed': ('speed', 'speed_kmh', 'v_kmh'),
                  'route_no': ('route_no', 'routeno', 'route'), 'rout_dec_no': ('rout_dec_no', 'routdecno', 'routdec')}
GT_SUBDIR = 'obs150_gt'    # <decisions>\obs150_gt: the runner's ground-truth folder (VBS obs150GtDir)


def _columns(header, path):
    names = [h.strip().lower().replace('\\', '_') for h in header]
    index = {n: i for i, n in enumerate(names)}
    for canonical, aliases in COLUMN_ALIASES.items():
        found = [a for a in aliases if a in index]
        require(len(found) <= 1, f'{path}: columns {found} name the same quantity')
        if found:
            index[canonical] = index[found[0]]
    require('t10' in index and 'no' in index and 'pos' in index, f'{path}: needs t10, veh (or no), pos columns')
    require('lane' in index, f'{path}: needs a lane column')
    return index


def _num(text):
    text = text.strip()
    if text == '':
        return None
    return float(text.replace(',', '.'))


def read_gt_frames(path, t10_from, t10_to, recorded=None):
    """Yield (t10, {veh: Pos}) for every t10_from <= t10 <= t10_to; the file is ordered by t10.

    A recorded step without any vehicle on the tracked links has no row, so `recorded` (the
    gt_meta.csv steps) tells an empty frame from a missing one. Without it every step needs rows."""
    def empty(t10):
        require(recorded is not None and t10 in recorded, f'{path}: no ground truth for t10={t10}')
        return {}

    expect = t10_from
    for t10, frame in _gt_rows(path, t10_from, t10_to):       # streamed: one frame in memory
        while expect < t10:
            yield expect, empty(expect)
            expect += 1
        yield t10, frame
        expect = t10 + 1
    while expect <= t10_to:
        yield expect, empty(expect)
        expect += 1


def _gt_rows(path, t10_from, t10_to):
    with open(path, newline='', encoding='latin-1') as handle:
        reader = csv.reader(handle)
        index = _columns(next(reader), path)
        has_link = 'link' in index
        current, frame, last = None, {}, None
        for row in reader:
            if not row:
                continue
            t10 = int(row[index['t10']])
            require(last is None or t10 >= last, f'{path}: rows are not ordered by t10')
            last = t10
            if t10 < t10_from:
                continue
            if t10 > t10_to:
                break
            if t10 != current:
                if current is not None:
                    yield current, frame
                current, frame = t10, {}
            if has_link:
                link, lane = int(row[index['link']]), int(row[index['lane']])
            else:
                text = row[index['lane']].strip()
                require('-' in text, f'{path}: lane must be <link>-<lane> without a link column')
                a, b = text.rsplit('-', 1)
                link, lane = int(a), int(b)
            speed = _num(row[index['speed']]) if 'speed' in index else None
            route = _num(row[index['route_no']]) if 'route_no' in index else None
            rdec = _num(row[index['rout_dec_no']]) if 'rout_dec_no' in index else None
            frame[int(float(row[index['no']]))] = Pos(link, lane, float(row[index['pos']]), speed,
                                                      None if route is None else int(route),
                                                      None if rdec is None else int(rdec))
        if current is not None:
            yield current, frame


def read_gt_signals(path):
    """{('sc','sg'): {t10: STATE}}."""
    out = defaultdict(dict)
    with open(path, newline='', encoding='latin-1') as handle:
        for row in csv.DictReader(handle):
            out[str(int(float(row['sc']))), str(int(float(row['sg'])))][int(row['t10'])] = row['sig_state'].strip().upper()
    return dict(out)


def read_gt_meta_steps(path):
    with open(path, newline='', encoding='latin-1') as handle:
        return {int(row['t10']) for row in csv.DictReader(handle)}


def read_removals(err_path):
    """(removals {veh: [time]}, route ends {veh: [time]}, removal rows) of a final .err."""
    from diagnostics.capture_native_runtime_errors import parse_bytes
    removed, route_end, rows = defaultdict(list), defaultdict(list), []
    if err_path is None or not Path(err_path).is_file():
        return removed, route_end, rows
    parsed = parse_bytes(Path(err_path).read_bytes())
    require(not parsed['unparsed_removal_lines'], 'Final .err has removal lines that do not parse')
    for event in parsed['events']:
        if event['kind'] == 'lane_change_removal':
            removed[event['vehicle_id']].append(event['time_sec'])
            rows.append({**event, 'link': int(event['link'])})
        elif event['kind'] == 'route_next_link_not_found':
            route_end[event['vehicle_id']].append(event['time_sec'])
    return removed, route_end, rows


# ---------------------------------------------------------------- crossing engine
class Point(NamedTuple):
    pid: str
    link: int
    x: float
    lanes: frozenset | None       # None = every lane


class Event(NamedTuple):
    pid: str
    veh: int
    b10: int
    lane: int | None              # None: unknown, the vehicle changed lanes inside the step
    kind: str                     # clean | lane_change | exit | entry | traverse
    lanes: frozenset | None = None   # lane None: the lanes it may have crossed in (None: any lane)


def _covers(point, lanes):
    """The point may see a crossing in one of `lanes` (None: any lane)."""
    return point.lanes is None or lanes is None or bool(point.lanes & lanes)


class Engine:
    def __init__(self, network, points, tracked, removed=None, route_end=None):
        self.net = network
        self.by_link = defaultdict(list)
        for p in points:
            self.by_link[p.link].append(p)
        self.tracked = set(tracked)
        self.removed = removed or {}
        self.route_end = route_end or {}
        self.anomalies = []
        self.observed_kmh = {}        # veh -> speed from its last same-link 0.1 s displacement (no speed column)

    def by_link_points(self):
        return [p for points in self.by_link.values() for p in points]

    def _reach(self, p, veh=None):
        """Front travel bound over one 0.1 s step: the GT speed, else the vehicle's own last same-link
        displacement, else MAX_SPEED_KMH; plus REACH_SLACK_M (far above a 0.1 s speed change)."""
        if p.speed is not None:
            speed = max(p.speed, 0.0)
        else:
            speed = self.observed_kmh.get(veh, MAX_SPEED_KMH)
        return speed / 3.6 * 0.1 + REACH_SLACK_M

    def _observe_speeds(self, fa, fb):
        for veh, pb in fb.items():
            pa = fa.get(veh)
            if pa is not None and pa.link == pb.link:
                self.observed_kmh[veh] = max(pb.pos - pa.pos, 0.0) * 36.0

    def _gone(self, table, veh, a10, b10):
        return any(a10 / 10 - 0.1 - 1e-9 < t <= b10 / 10 + 0.1 + 1e-9 for t in table.get(veh, ()))

    def exit_positions(self, link, pa, pb, veh=None):
        """Candidate positions on `link` where a vehicle at pa (on link) left it before b."""
        g = self.net.links.get(link)
        if g is None:
            return None
        if g.connector:                               # a connector is left only at its end
            return [INF] if pb is None or pb.link == g.to_link or pb.link in {c.no for c in self.net.out[g.to_link]} \
                else None
        out = self.net.out[link]
        if pb is not None:
            cands = [c.from_pos for c in out if c.no == pb.link or c.to_link == pb.link]
        else:
            cands = [c.from_pos for c in out if c.no not in self.tracked]
            if not any(c.from_pos >= g.length - END_TOL_M for c in out):
                cands.append(g.length)                # network exit at the link end
        reach = self._reach(pa, veh)
        cands = [INF if c >= g.length - END_TOL_M else c for c in cands
                 if pa.pos - POS_TOL <= c <= pa.pos + reach or c >= g.length - END_TOL_M and g.length <= pa.pos + reach]
        return cands or None

    def entry_positions(self, link, pa, pb, veh=None):
        g = self.net.links.get(link)
        if g is None:
            return None
        if g.connector:
            return [0.0]
        into = self.net.into[link]
        if pa is not None:
            cands = [c.to_pos for c in into if c.no == pa.link or c.from_link == pa.link]
        else:
            cands = [c.to_pos for c in into if c.no not in self.tracked]
            if not into or link in getattr(self.net, 'input_links', ()):
                cands.append(0.0)                     # an origin or input link: inputs start at 0
        reach = self._reach(pb, veh)
        cands = [c for c in cands if pb.pos - reach <= c <= pb.pos + POS_TOL]
        return cands or None

    @staticmethod
    def _event(point, veh, b10, lanes, kind):
        """One crossing: lane-level when `lanes` holds one lane, else lane-unknown with its possible lanes."""
        if lanes is not None and len(lanes) == 1:
            return Event(point.pid, veh, b10, next(iter(lanes)), kind)
        return Event(point.pid, veh, b10, None, 'lane_change' if kind == 'clean' else kind, lanes)

    def _decide(self, point, cands, passed, veh, b10, lanes, kind):
        """passed(c) -> bool per candidate; one event only when all candidates agree."""
        if cands is None:
            self.anomalies.append({'pid': point.pid, 'veh': veh, 'b10': b10, 'kind': 'unexplained_' + kind})
            return None
        votes = {passed(c) for c in cands}
        if votes == {True}:
            return self._event(point, veh, b10, lanes, kind)
        if votes == {True, False}:
            self.anomalies.append({'pid': point.pid, 'veh': veh, 'b10': b10, 'kind': 'ambiguous_' + kind,
                                   'candidates': sorted(cands)})
        return None

    # A connector's lane i leaves from_link lane (from_lane + i - 1) and joins to_link lane (to_lane + i - 1).
    @staticmethod
    def _connector_lane(connector, lane):
        return lane if connector.lanes is None or 1 <= lane <= connector.lanes else _UNKNOWN

    def _left_lane(self, link, pb):
        """The lane of `link` a vehicle at pb one step later left it from; None when the network holds
        no lane mapping (the lane at a is then taken), _UNKNOWN when the mapping cannot tell."""
        g = self.net.links.get(link)
        if g is None:
            return None
        if g.connector:
            if pb.link != g.to_link or g.to_lane is None:
                return None
            return self._connector_lane(g, pb.lane - g.to_lane + 1)
        c = self.net.links.get(pb.link)
        if c is not None and c.connector and c.from_link == link:
            return None if c.from_lane is None else c.from_lane + pb.lane - 1
        between = [c for c in self.net.out.get(link, ()) if c.to_link == pb.link]
        if len(between) != 1 or between[0].from_lane is None or between[0].to_lane is None:
            return None
        c = between[0]
        lane = self._connector_lane(c, pb.lane - c.to_lane + 1)
        return lane if lane is _UNKNOWN else c.from_lane + lane - 1

    def _entered_lane(self, link, pa):
        """The lane of `link` a vehicle at pa one step earlier entered it in (None/_UNKNOWN as _left_lane)."""
        g = self.net.links.get(link)
        if g is None:
            return None
        if g.connector:
            if pa.link != g.from_link or g.from_lane is None:
                return None
            return self._connector_lane(g, pa.lane - g.from_lane + 1)
        c = self.net.links.get(pa.link)
        if c is not None and c.connector and c.to_link == link:
            return None if c.to_lane is None else c.to_lane + pa.lane - 1
        between = [c for c in self.net.into.get(link, ()) if c.from_link == pa.link]
        if len(between) != 1 or between[0].from_lane is None or between[0].to_lane is None:
            return None
        c = between[0]
        lane = self._connector_lane(c, pa.lane - c.from_lane + 1)
        return lane if lane is _UNKNOWN else c.to_lane + lane - 1

    def _all_lanes(self, link):
        """Every lane of `link` (None: its lane count is unknown, i.e. any lane)."""
        g = self.net.links.get(link)
        return None if g is None or g.lanes is None else frozenset(range(1, g.lanes + 1))

    def _lanes(self, link, own, mapped):
        """Possible crossing lanes on `link`: the vehicle's own lane at a (B) or b (C), plus the lane the
        connector mapping gives for the other end of the step; every lane when the mapping cannot tell."""
        if mapped is _UNKNOWN:
            return self._all_lanes(link)
        return frozenset({own} if mapped is None else {own, mapped})

    def _traversed(self, veh, pa, pb, b10, events):
        """A short connector crossed entirely inside one step: every point on it is crossed, in the
        connector lane both ends give (two lanes when they differ; every lane when an end cannot tell)."""
        between = [c for c in self.net.out.get(pa.link, ()) if c.to_link == pb.link and self.by_link.get(c.no)]
        if len(between) == 1:
            c = between[0]
            ends = [None if c.from_lane is None else self._connector_lane(c, pa.lane - c.from_lane + 1),
                    None if c.to_lane is None else self._connector_lane(c, pb.lane - c.to_lane + 1)]
            lanes = (self._all_lanes(c.no) if any(x is None or x is _UNKNOWN for x in ends)
                     else frozenset(ends))
            for point in self.by_link[c.no]:
                if _covers(point, lanes):
                    events.append(self._event(point, veh, b10, lanes, 'traverse'))
        elif len(between) > 1:
            self.anomalies.append({'pid': ','.join(str(c.no) for c in between), 'veh': veh, 'b10': b10,
                                   'kind': 'ambiguous_traverse'})

    def step(self, a10, fa, b10, fb):
        events = []
        for veh in fa.keys() | fb.keys():
            pa, pb = fa.get(veh), fb.get(veh)
            if pa is not None and pb is not None and pa.link != pb.link:
                self._traversed(veh, pa, pb, b10, events)
            links = {p.link for p in (pa, pb) if p is not None}
            for link in links:
                for point in self.by_link.get(link, ()):
                    if pa is not None and pb is not None and pa.link == link == pb.link:
                        lanes = frozenset((pa.lane, pb.lane))
                        if pa.pos < point.x <= pb.pos and _covers(point, lanes):   # front q >= x crossed x (CONTRACT 3.2)
                            events.append(self._event(point, veh, b10, lanes, 'clean'))
                    elif pa is not None and pa.link == link:          # B: left the link
                        lanes = (frozenset((pa.lane,)) if pb is None
                                 else self._lanes(link, pa.lane, self._left_lane(link, pb)))
                        if pa.pos >= point.x or not _covers(point, lanes):
                            continue
                        if pb is None and self._gone(self.removed, veh, a10, b10):
                            continue
                        if pb is None and self._gone(self.route_end, veh, a10, b10):
                            cands = [INF]
                        else:
                            cands = self.exit_positions(link, pa, pb, veh)
                        event = self._decide(point, cands, lambda c: c >= point.x - POS_TOL, veh, b10, lanes, 'exit')
                        if event:
                            events.append(event)
                    elif pb is not None and pb.link == link:          # C: entered the link
                        lanes = (frozenset((pb.lane,)) if pa is None
                                 else self._lanes(link, pb.lane, self._entered_lane(link, pa)))
                        if pb.pos < point.x or not _covers(point, lanes):
                            continue
                        cands = self.entry_positions(link, pa, pb, veh)
                        event = self._decide(point, cands, lambda c: c <= point.x + POS_TOL, veh, b10, lanes, 'entry')
                        if event:
                            events.append(event)
        self._observe_speeds(fa, fb)
        return events


class ChainMembership:
    """freeway_exit_count truth: vehicles that leave the chain (another link, network exit, removal).

    GT records only the links of the detector table (and every link it shows a vehicle on), so the
    chain connectors 10699 and 10702 are unrecorded. A vehicle that vanishes where such a connector
    starts is 'pending'; when an unrecorded way off the chain is also in reach (another connector,
    the network end: 119 runs on 4.2 m past the start of 10702) it is pending 'ambiguous'. A
    pending vehicle that reappears on a chain link never left. A connector has no branch: the only
    way off it is its to_link (a chain link) or a removal (.err). close() settles the rest
    deterministically: a lane_change_removal on an unrecorded chain link inside the window is the
    exit at its time (also for a vehicle that was already there when the window began); every other
    pending vehicle is looked up in VISSIM's complete frame at the window end (frame_end, the obs150
    frame_T): on a chain link -> never left; absent or off the chain after an ambiguous vanish ->
    it left at the vanish step. Without that frame a 'chain' vanish is still on the chain and an
    'ambiguous' one stays 'ambiguous_chain_exit'. A vanish nothing explains, or a 'chain' vanish the
    frame contradicts, is 'unexplained_chain_vanish'. Anomalies make the verdict FAIL."""

    def __init__(self, network, chain, tracked, engine):
        self.net, self.chain, self.tracked, self.engine = network, set(chain), set(tracked), engine
        self.exits, self.pending, self.resolved, self.anomalies = [], {}, [], []
        self.booked = set()           # vehicles whose vanish (or removal) is already booked as an exit

    def _vanished_into(self, p, reach):
        """(unrecorded chain successors, unrecorded ways off the chain) of a vehicle at p that is gone one step later."""
        g = self.net.links.get(p.link)
        if g is None:
            return [], []
        if g.connector:                                    # a connector ends in its to_link only
            if g.to_link in self.tracked:
                return [], []
            return ([g.to_link], []) if g.to_link in self.chain else ([], [g.to_link])
        out = self.net.out.get(p.link, ())
        near = [c for c in out if c.no not in self.tracked and p.pos - POS_TOL <= c.from_pos <= p.pos + reach]
        chain = [c.no for c in near if c.no in self.chain]
        off = [c.no for c in near if c.no not in self.chain]
        if not any(c.from_pos >= g.length - END_TOL_M for c in out) and g.length <= p.pos + reach:
            off.append('network_end')
        return chain, off

    def step(self, a10, fa, b10, fb):
        self.tracked |= {p.link for p in fb.values()}
        for veh in [v for v in self.pending if v in fb and fb[v].link in self.chain]:
            self.resolved.append({**self.pending.pop(veh), 'veh': veh, 'outcome': 'reappeared', 'b10': b10,
                                  'link': fb[veh].link})
        for veh, p in fa.items():
            if p.link not in self.chain:
                continue
            q = fb.get(veh)
            if q is not None:
                if q.link not in self.chain:
                    self.exits.append((veh, b10))
                    self.booked.add(veh)
                continue
            if self.engine._gone(self.engine.removed, veh, a10, b10) or self.engine._gone(self.engine.route_end, veh, a10, b10):
                self.exits.append((veh, b10))
                self.booked.add(veh)
                continue
            chain, off = self._vanished_into(p, self.engine._reach(p, veh))
            if chain:
                self.pending[veh] = {'vanished_b10': b10, 'from_link': p.link, 'pos': p.pos,
                                     'kind': 'ambiguous' if off else 'chain', 'candidates': [str(x) for x in chain + off]}
            elif off:
                self.exits.append((veh, b10))
                self.booked.add(veh)
            else:
                self.anomalies.append({'pid': 'chain', 'veh': veh, 'b10': b10, 'kind': 'unexplained_chain_vanish',
                                       'link': p.link, 'pos': p.pos})

    def close(self, window, removal_rows=(), frame_end=None):
        """Window end (see the class doc). frame_end: {veh: link} of VISSIM's complete frame at e."""
        s, e = window
        for row in removal_rows or ():
            veh, t, link = row['vehicle_id'], row['time_sec'], int(row['link'])
            if not (s < t <= e) or link not in self.chain or link in self.tracked or veh in self.booked:
                continue
            self.exits.append((veh, math.ceil(t * 10 - 1e-6)))
            self.booked.add(veh)
            self.resolved.append({**self.pending.pop(veh, {}), 'veh': veh, 'outcome': 'removed', 'link': link,
                                  'time_sec': t})
        for veh, info in sorted(self.pending.items()):
            b10 = info['vanished_b10']
            link = None if frame_end is None else frame_end.get(veh)
            if frame_end is not None and link in self.chain:
                self.resolved.append({**info, 'veh': veh, 'outcome': 'on_chain_at_window_end', 'link': link})
            elif frame_end is None and info['kind'] == 'chain':
                self.resolved.append({**info, 'veh': veh, 'outcome': 'on_chain_at_window_end', 'link': None})
            elif frame_end is not None and info['kind'] == 'ambiguous':
                self.exits.append((veh, b10))           # it took the way off the chain when it vanished
                self.booked.add(veh)
                self.resolved.append({**info, 'veh': veh, 'outcome': 'left_at_vanish', 'link': link})
            else:
                self.anomalies.append({'pid': 'chain', 'veh': veh, 'b10': b10,
                                       'kind': 'ambiguous_chain_exit' if info['kind'] == 'ambiguous'
                                       else 'unexplained_chain_vanish', 'link': info['from_link'], 'pos': info['pos'],
                                       'candidates': info['candidates'], 'frame_end_link': link})
        self.pending = {}


# ---------------------------------------------------------------- points of the detector table
def boundary_x(row):
    """(link, x, lanes) of the boundary point a row measures (CONTRACT 3.2)."""
    if row.orientation == 'at':
        return row.link, row.pos, (row.lane,)
    piece = row.segment[0] if row.orientation == 'down' else row.segment[-1]
    x = piece.from_m if row.orientation == 'down' else piece.to_m
    return piece.link, x, piece.lanes


def build_points(rows):
    """Station points per detector row, lane-level x per row, and station-level x per boundary."""
    points, station_x = [], defaultdict(set)
    for row in rows:
        points.append(Point(f'dcp:{row.dcp_no}', row.link, row.pos, frozenset((row.lane,))))
        link, x, lanes = boundary_x(row)
        points.append(Point(f'xl:{row.dcp_no}', link, x, None if lanes is None else frozenset(lanes)))
        station_x[row.boundary_ref].add((link, x, None if lanes is None else frozenset(lanes)))
    for ref, xs in station_x.items():
        grouped = defaultdict(set)
        unbounded = set()
        for link, x, lanes in xs:
            if lanes is None:
                unbounded.add((link, x))
            else:
                grouped[link, x] |= lanes
        for i, (link, x) in enumerate(sorted(set(grouped) | unbounded)):
            lanes = None if (link, x) in unbounded else frozenset(grouped[link, x])
            points.append(Point(f'x:{ref}:{i}', link, x, lanes))
    return points


# ---------------------------------------------------------------- one window
def collect(gt_veh, network, rows, window, tracked, removed, route_end, chain, meta_steps=None, *, removal_rows=(),
            frame_end=None, d10_probe=None):
    """All GT events of one window (s, e]: frames 10s..10e, steps (a, b] with b in (10s, 10e].
    removal_rows (the final .err lane_change_removal rows) and frame_end ({veh: link} of the obs150
    frame at e) close the unrecorded chain connectors (ChainMembership.close). d10_probe (D10Probe)
    sees every frame and is returned as 'd10_probe'."""
    s, e = window
    points = build_points(rows)
    engine = Engine(network, points, tracked, removed, route_end)
    membership = ChainMembership(network, chain, tracked, engine)
    exit_pids = {p.pid for p in engine.by_link_points() if p.pid.startswith(f'x:x10643_exit:{oc.OFFRAMP_10643}:')}
    events, routes_at_exit, seen_links, frames_seen, previous = [], {}, set(), set(), None
    for t10, frame in read_gt_frames(gt_veh, 10 * s, 10 * e, meta_steps):
        frames_seen.add(t10)
        seen_links |= {p.link for p in frame.values()}
        if d10_probe is not None:
            d10_probe.feed(t10, frame)
        if previous is not None:
            a10, fa = previous
            require(t10 == a10 + 1, f'GT frames skip from t10={a10} to {t10}')
            step_events = engine.step(a10, fa, t10, frame)
            events.extend(step_events)
            membership.step(a10, fa, t10, frame)
            for ev in step_events:
                if ev.pid in exit_pids and ev.veh in fa:
                    routes_at_exit[ev.veh, ev.b10] = (fa[ev.veh].route, fa[ev.veh].rdec)
        previous = (t10, frame)
    require(frames_seen == set(range(10 * s, 10 * e + 1)),
            f'GT frames do not cover ({s}, {e}]: {len(frames_seen)} of {10 * (e - s) + 1} steps')
    if meta_steps is not None:
        require(set(range(10 * s, 10 * e + 1)) <= meta_steps, f'gt_meta lacks steps of ({s}, {e}]')
    membership.close((s, e), [r for r in removal_rows if r.get('kind', 'lane_change_removal') == 'lane_change_removal'],
                     frame_end)
    by_pid = defaultdict(list)
    for ev in events:
        by_pid[ev.pid].append(ev)
    return {'by_pid': by_pid, 'exits': membership.exits, 'anomalies': engine.anomalies + membership.anomalies,
            'chain_anomalies': membership.anomalies, 'chain_resolved': membership.resolved,
            'routes_at_exit': routes_at_exit, 'recorded_links': set(tracked) | seen_links,
            'points': {p.pid: p for p in points}, 'd10_probe': d10_probe}


def _station(by_pid, ref, n_points):
    vehicles = {}
    for i in range(n_points):
        for ev in by_pid.get(f'x:{ref}:{i}', ()):
            vehicles.setdefault(ev.veh, ev)
    return vehicles


def _station_unresolved(by_pid, points, ref, n_points):
    """Lane-unknown GT events at a station point whose lanes do not cover every lane the vehicle may have
    crossed in: whether the station saw it is unknown (the item is then not judged)."""
    out = []
    for i in range(n_points):
        pid = f'x:{ref}:{i}'
        point = points.get(pid)
        for ev in by_pid.get(pid, ()):
            if (ev.lane is None and point is not None and point.lanes is not None
                    and (ev.lanes is None or not ev.lanes <= point.lanes)):
                out.append({'pid': pid, 'veh': ev.veh, 'b10': ev.b10,
                            'lanes': None if ev.lanes is None else sorted(ev.lanes)})
    return out


def _green_state(signals, key, t10, rule):
    table = signals.get(key)
    if table is None:
        return None
    return table.get(t10 - 1 if rule == 'next' else t10)


# ---------------------------------------------------------------- COM head delay (D10)
LEAD_GAP_M = 3.0           # a lead vehicle waiting at its head stands within this of the head (probe: < 1.5 m)
STILL_M = 1e-5             # a standing front keeps its position exactly; the first 0.1 s of a start moves ~1 mm
D10_LOOKAHEAD_S = 3        # a lead vehicle that has not moved 3 s after the GREEN write is 'no_move'
STAND_STEPS = 5            # it stands still over the last 0.5 s before the write (probe 3596 stopped at 849.1)
D10_ITEM = 'd10'


def com_head_delay_default():
    """The D10 value the observation side uses (WP-B1 obs150_signal_clock.COM_HEAD_DELAY_S)."""
    from evaluation.controllers import obs150_signal_clock
    return obs150_signal_clock.COM_HEAD_DELAY_S


class SignalTruth:
    """The GT signal state the vehicles see in the 0.1 s step (b10-1, b10] of the window (s, e].

    gt_sig holds the SigState read back at t10 after that stop's writes. A native SG read at t10 is the
    state of the step (t10, t10+1] (--sig-rule next, V0-4) or (t10-1, t10] (previous). A COM write at the
    stop u reads back at once but reaches the heads one update later (D10, CONTRACT 2.3,
    obs150_signal_clock.COM_HEAD_DELAY_S = delay), so in a COM-owned second the read back is taken 10*delay
    samples earlier. Ownership comes from the runner's signal log of the window (start owner + own events,
    moved by the same delay as obs150_signal_clock.windows). Before the first GT sample of the window the read
    back of a COM SG is its logged start state (the state after the writes up to the stop T-151), when the
    runner verified it. In the delay seconds after an own(true) the heads are still native while the read back
    shows the COM write: those seconds have no GT state (None: the head is then not judged). The shift is the
    D10 hypothesis; the d10 item checks it on the vehicles."""

    def __init__(self, signals, signal_log, window, delay):
        self.signals, self.delay = signals, delay
        self.s, self.e = window
        self.com, self.pre, self.unknown = {}, {}, {}
        if not signal_log:
            return
        events = defaultdict(lambda: defaultdict(list))
        for event in signal_log.get('events', ()):
            events[str(event[1]), str(event[2])][int(event[0])].append(event)
        for sgkey, entry in signal_log.get('start', {}).items():
            key = tuple(sgkey.split('-'))
            owner = entry['owner']
            if owner == 'com' and entry.get('verified') is True:
                self.pre[key] = entry['state']
            slots, unknown = set(), set()
            for t in range(self.s, self.e):
                for event in events[key].get(t - delay, ()):
                    if event[3] == 'own':
                        owner = 'com' if event[4] else 'native'
                if owner == 'com':
                    slots.add(t)
                elif any(event[3] == 'own' and event[4] for w in range(t - delay + 1, t + 1)
                         for event in events[key].get(w, ())):
                    # still native for the heads, but the read back already shows the COM write: no GT state
                    unknown.add(t)
            self.com[key], self.unknown[key] = slots, unknown

    def is_com(self, key, t):
        return t in self.com.get(key, ())

    def state(self, key, b10, rule):
        table = self.signals.get(key)
        if table is None or (b10 - 1) // 10 in self.unknown.get(key, ()):
            return None
        index = b10 - 1 if rule == 'next' else b10
        if self.is_com(key, (b10 - 1) // 10):
            index -= 10 * self.delay
            if index < 10 * self.s and index not in table:
                return self.pre.get(key)
        return table.get(index)


class D10Probe:
    """Vehicle evidence of D10: the lead vehicle standing at a COM head when GREEN is written at the stop u.

    A GREEN write at u (read back GREEN at 10u, not GREEN over the 2 s before, the SG COM-owned from u-1 to
    u+3) whose head has a vehicle standing within LEAD_GAP_M before it through [u-0.5, u]: its first GT step
    of motion m tells when the head turned GREEN for the vehicles. m = 10u+1 (departs at u+0.1): the heads
    took the write at u (D10 = 0); m = 10u+11 (u+1.1): one update later (D10 = 1; probe: 851.1 after 850).
    Any other m (a blocked or slow start) is reported only. collect() feeds the GT frames (feed)."""

    def __init__(self, rows, truth):
        self.truth = truth
        s, e = truth.s, truth.e
        heads = defaultdict(list)
        for row in rows:
            if row.role in ('head', 'meter_head'):
                head, sc, sg = oc.parse_head_ref(row.ref)
                heads[sc, sg].append((head, row))
        self.com_sgs = sorted(f'{sc}-{sg}' for sc, sg in heads if truth.com.get((sc, sg)))
        self.targets, writes = [], set()
        for key, members in sorted(heads.items()):
            table = truth.signals.get(key)
            if not table or not truth.com.get(key):
                continue
            for u in range(s + 2, e - D10_LOOKAHEAD_S):
                if (table.get(10 * u) != oc.GREEN_STATE
                        or not all(truth.is_com(key, t) for t in range(u - 1, u + D10_LOOKAHEAD_S + 1))
                        or any(table.get(j) in (None, oc.GREEN_STATE) for j in range(10 * u - 20, 10 * u))):
                    continue
                writes.add((key, u))
                for head, row in members:
                    self.targets.append({'sg': '-'.join(key), 'head': head, 'role': row.role, 'link': row.link,
                                         'lane': row.lane, 'x': row.pos, 'u': u})
        self.green_writes = len(writes)
        self.by_t10 = defaultdict(list)
        for i, target in enumerate(self.targets):
            for t10 in range(10 * target['u'] - 10, 10 * (target['u'] + D10_LOOKAHEAD_S) + 1):
                self.by_t10[t10].append(i)
        self.seen = [defaultdict(dict) for _ in self.targets]     # target -> t10 -> {veh: pos} near its head

    def feed(self, t10, frame):
        mine = self.by_t10.get(t10)
        if not mine:
            return
        lanes = defaultdict(list)
        for veh, p in frame.items():
            lanes[p.link, p.lane].append((veh, p.pos))
        for i in mine:
            target = self.targets[i]
            x = target['x']
            self.seen[i][t10] = {veh: pos for veh, pos in lanes.get((target['link'], target['lane']), ())
                                 if x - 30.0 <= pos <= x + 0.5}

    def item(self, delay):
        samples = []
        for target, seen in zip(self.targets, self.seen):
            u, x = target['u'], target['x']
            at = [(pos, veh) for veh, pos in seen.get(10 * u, {}).items() if pos <= x + POS_TOL]
            if not at:
                continue
            pos, veh = max(at)
            if x - pos > LEAD_GAP_M:
                continue
            standing = [seen.get(t10, {}).get(veh) for t10 in range(10 * u - STAND_STEPS, 10 * u + 1)]
            if any(p is None or abs(p - pos) > STILL_M for p in standing):
                continue
            moved = next((t10 for t10 in range(10 * u + 1, 10 * (u + D10_LOOKAHEAD_S) + 1)
                          if (p := seen.get(t10, {}).get(veh)) is None or abs(p - pos) > STILL_M), None)
            lag = None if moved is None else moved - 10 * u - 1
            kind = ('no_move' if lag is None else 'match' if lag == 10 * delay
                    else 'contradiction' if lag in (0, 10) else 'other')
            samples.append({**target, 'veh': veh, 'gap_m': round(x - pos, 3), 'first_move_t10': moved,
                            'departure_after_write_s': None if moved is None else round(moved / 10 - u, 1),
                            'kind': kind})
        counts = Counter(s_['kind'] for s_ in samples)
        ok = False if counts['contradiction'] else True if counts['match'] else None
        return {'ok': ok, 'configured_delay_s': delay, 'probed': True, 'com_head_sgs': self.com_sgs,
                'green_writes': self.green_writes, 'lead_samples': len(samples), 'by_kind': dict(counts),
                'departures_after_write_s': dict(Counter(s_['departure_after_write_s'] for s_ in samples)),
                'samples': samples[:40],
                # every contradiction, uncapped: a FAIL must keep all of its evidence in the verdict JSON
                'contradiction_samples': [s_ for s_ in samples if s_['kind'] == 'contradiction']}


def _in_step(b10, t_entry):
    """A .mer entry time lies in its GT 0.1 s step (b10 - 1, b10] (rounded to 0.01 s)."""
    return b10 / 10 - 0.1 - MER_STEP_TOL_S <= t_entry <= b10 / 10 + MER_STEP_TOL_S


def _tri(values):
    """False if any is False, None if any is None (not judged), else True."""
    values = list(values)
    if any(v is False for v in values):
        return False
    if any(v is None for v in values):
        return None
    return True


class LaneResolution(NamedTuple):
    attributed: dict      # dcp -> {veh: Event}: lane-unknown GT crossings .mer holds at this point
    unknown_at: dict      # dcp -> {veh}: vehicles with a lane-unknown GT event at this point
    open: list            # last-second crossings .mer does not (fully) hold yet: may be tails
    uncounted: list       # explained: crossed on a possible lane that has no point (never recorded)
    failures: list        # .mer contradicts every possible lane


def resolve_unknown_lanes(rows, by_pid, mer, window):
    """Attribute every lane-unknown GT crossing of the lane-level detector points (PRB f).

    One crossing = one vehicle, one step, one link: its candidate points are the points of that link
    with a lane-unknown event of the vehicle at that step. VISSIM counts it at the points of the one
    lane it was in, so the options are {points of lane L} for every possible lane L (the empty set
    for a lane without a point; also always when the possible lanes are unknown). mer = {dcp: {veh:
    MerRow}} (the window entries). .mer must hold the vehicle at exactly one option; in the last
    second the not yet written rest of an option may be a tail (the crossing stays open)."""
    s, e = window
    row_of = {r.dcp_no: r for r in rows}
    crossings, unknown_at = defaultdict(dict), defaultdict(set)
    for r in rows:
        for ev in by_pid.get(f'dcp:{r.dcp_no}', ()):
            if ev.lane is None:
                crossings[ev.veh, ev.b10, r.link][r.dcp_no] = ev
                unknown_at[r.dcp_no].add(ev.veh)
    attributed, open_, uncounted, failures = defaultdict(dict), [], [], []
    for (veh, b10, link), at in sorted(crossings.items(), key=lambda item: item[0]):
        spans = [ev.lanes for ev in at.values()]
        any_lane = any(x is None for x in spans)
        lanes = frozenset(row_of[d].lane for d in at) if any_lane else frozenset().union(*spans)
        options = {frozenset(d for d in at if row_of[d].lane == lane) for lane in lanes}
        if any_lane:
            options.add(frozenset())
        recorded = frozenset(d for d in at if veh in mer.get(d, {}))
        entry = {'veh': veh, 'b10': b10, 'link': link, 'points': sorted(at),
                 'lanes': None if any_lane else sorted(lanes), 'recorded': sorted(recorded)}
        if b10 > 10 * (e - 1):
            rest = {opt - recorded for opt in options if recorded <= opt}
            if not rest:
                failures.append({**entry, 'kind': 'recorded_at_points_of_no_single_lane'})
                continue
            for d in recorded:
                attributed[d][veh] = at[d]
            if rest != {frozenset()}:
                open_.append({**entry, 'options': sorted(rest, key=sorted)})
        elif recorded in options:
            for d in recorded:
                attributed[d][veh] = at[d]
            if not recorded:
                uncounted.append(entry)
        else:
            failures.append({**entry, 'kind': 'not_recorded' if not recorded else 'recorded_at_points_of_no_single_lane'})
    return LaneResolution(dict(attributed), dict(unknown_at), open_, uncounted, failures)


def _open_groups(open_):
    """Rows tied together by open crossings (each crossing ties the points of all its options)."""
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            x = parent[x]
        return x

    for c in open_:
        dcps = sorted(set().union(*c['options']))
        for d in dcps:
            parent[find(d)] = find(dcps[0])
    groups = {}
    for c in open_:
        group = groups.setdefault(find(min(set().union(*c['options']))), {'rows': set(), 'crossings': []})
        group['crossings'].append(c)
        group['rows'] |= set().union(*c['options'])
    return list(groups.values())


def _lane_choices(crossings):
    """Every choice of one option per crossing, or None when there are more than MAX_LANE_CHOICES."""
    if math.prod(len(c['options']) for c in crossings) > MAX_LANE_CHOICES:
        return None
    return list(itertools.product(*[c['options'] for c in crossings]))


def _public(crossing):
    return {**crossing, 'options': [sorted(o) for o in crossing['options']]} if 'options' in crossing else crossing


def verify_window(window, state, derived, rows, network, gt, removal_rows, sig_rule):
    s, e = window
    by_pid, exits, anomalies = gt['by_pid'], gt['exits'], gt['anomalies']
    points = gt.get('points') or {p.pid: p for p in build_points(rows)}
    obs = state[oc.RAW_STATE_KEY]
    delay = gt.get('com_head_delay')
    delay = com_head_delay_default() if delay is None else delay
    sig_truth = SignalTruth(gt['signals'], obs.get('signal_log'), window, delay)

    def sig_state(key, b10, rule):
        return sig_truth.state(key, b10, rule)

    items = {}
    groups = oc.group_boundaries(rows)
    n_points = {ref: len({(boundary_x(r)[0], boundary_x(r)[1]) for r in rs}) for ref, rs in groups.items()}
    recorded = gt.get('recorded_links')

    def uncovered(*refs):
        """Links of the boundary points x the GT does not record: such an item is reported, not judged."""
        if recorded is None:
            return []
        return sorted({boundary_x(r)[0] for ref in refs for r in groups.get(ref, ()) if boundary_x(r)[0] not in recorded})

    def judged(entry, ok, *refs, station=True):
        missing = uncovered(*refs)
        unresolved = [u for ref in refs for u in _station_unresolved(by_pid, points, ref, n_points.get(ref, 0))] \
            if station else []
        if missing:
            entry['ok'], entry['not_recorded_links'] = None, missing
        elif unresolved:
            entry['ok'], entry['unresolved_lane_change'] = None, unresolved[:20]
        else:
            entry['ok'] = ok
        return entry

    # detectors ---------------------------------------------------------
    bundle = oc.load_bundle(state)
    assignment = oc.assign_window(obs, bundle.mer_rows)
    mer = {row.dcp_no: {m.veh: m for m in assignment.entries.get(row.dcp_no, ())} for row in rows}
    resolution = resolve_unknown_lanes(rows, by_pid, mer, window)
    failed_at = defaultdict(list)
    for failure in resolution.failures:
        for d in failure['points']:
            failed_at[d].append(failure)
    expected, det_rows, base_ok = {}, {}, {}
    for row in rows:
        d = row.dcp_no
        clean = {ev.veh: ev for ev in by_pid.get(f'dcp:{d}', []) if ev.lane is not None}
        exp = {**clean, **resolution.attributed.get(d, {})}
        expected[d] = exp
        m = mer[d]
        vehs = obs['detectors'][str(row.dcm_no)]
        tail = assignment.tails.get(d, 0)
        mer_only = sorted(set(m) - set(clean) - resolution.unknown_at.get(d, set()))
        gt_only = sorted(set(exp) - set(m))
        early = [v for v in gt_only if exp[v].b10 <= 10 * (e - 1)]
        outside = [v for v in m if v in exp and not _in_step(exp[v].b10, m[v].t_entry)]
        excess = vehs - len(exp)          # counted by VISSIM beyond the attributed GT: open crossings only
        base_ok[d] = not mer_only and not early and not outside and not failed_at[d] and excess == tail - len(gt_only)
        det_rows[d] = {'dcp': d, 'role': row.role, 'boundary_ref': row.boundary_ref, 'lane': row.lane,
                       'vehs': vehs, 'mer_entries': len(m), 'tail': tail, 'gt': len(clean),
                       'gt_lane_change': sorted(resolution.unknown_at.get(d, ())),
                       'attributed_lane_change': sorted(resolution.attributed.get(d, ())),
                       'mer_only': mer_only[:20], 'gt_only': gt_only[:20], 'gt_only_before_last_second': early[:20],
                       'mer_outside_gt_step': outside[:20], 'excess': excess,
                       'lane_change_failures': len(failed_at[d]), 'ok': base_ok[d] and excess == 0}
    # Open lane-unknown crossings of the last second: rows judged together (some lane choice gives every Vehs).
    lane_groups, group_of, group_docs = [], {}, []
    for gi, group in enumerate(_open_groups(resolution.open)):
        choices = _lane_choices(group['crossings'])
        fits = None if choices is None else [
            ch for ch in choices if all(sum(d in opt for opt in ch) == det_rows[d]['excess'] for d in group['rows'])]
        ok = None if fits is None else bool(fits) and all(base_ok[d] for d in group['rows'])
        lane_groups.append((group, fits))
        for d in group['rows']:
            group_of[d] = gi
            det_rows[d]['lane_change_group'] = gi
            det_rows[d]['ok'] = ok
        group_docs.append({'group': gi, 'rows': sorted(group['rows']), 'ok': ok,
                           'open_crossings': [_public(c) for c in group['crossings']],
                           'lane_choices': None if choices is None else len(choices),
                           'lane_choices_fitting': None if fits is None else len(fits)})
    items['detectors'] = {'ok': _tri(d['ok'] for d in det_rows.values()), 'rows': list(det_rows.values()),
                          'lane_change': {'attributed': sum(len(v) for v in resolution.attributed.values()),
                                          'explained_uncounted': resolution.uncounted[:20],
                                          'failures': resolution.failures[:20], 'open_groups': group_docs}}

    def detector_values(dcps):
        """Possible GT counts summed over detector points (their 'at' boundary), given the lane choices
        that fit VISSIM's Vehs; None when a group has too many choices to enumerate."""
        dcps = set(dcps)
        values = {sum(len(expected[d]) for d in dcps)}
        for gi in sorted({group_of[d] for d in dcps if d in group_of}):
            fits = lane_groups[gi][1]
            if fits is None:
                return None
            adds = {sum(len(opt & dcps) for opt in ch) for ch in fits}
            values = {v + a for v in values for a in adds}
        return sorted(values)

    if derived is None:
        items['derived'] = {'ok': False, 'note': 'obs150/derived file missing: the decision did not derive'}
        return items

    # boundaries --------------------------------------------------------
    bounds = {}
    for ref, rs in groups.items():
        terms = derived['boundaries'].get(ref)
        derived_cross = None if terms is None else terms['cross']
        if rs[0].orientation == 'at':
            # The boundary point is the detector point itself: the same attribution as the detectors.
            values = detector_values(r.dcp_no for r in rs)
            entry = {'derived_cross': derived_cross, 'gt': values[0] if values and len(values) == 1 else None}
            if values is not None and len(values) != 1:
                entry['gt_possible'] = values
            ok = None if values is None else terms is not None and terms['cross'] in values
            if ok is not None and terms is not None and terms['lane_exact']:
                lanes = []
                for lane_terms in terms['lanes']:
                    row = next(r for r in rs if r.lane == lane_terms['lane'])
                    lane_values = detector_values([row.dcp_no])
                    lanes.append({'lane': lane_terms['lane'], 'derived': lane_terms['cross'], 'gt': lane_values,
                                  'ok': lane_values is not None and lane_terms['cross'] in lane_values})
                entry['lanes'] = lanes
                ok = ok and all(x['ok'] for x in lanes)
            bounds[ref] = judged(entry, ok, ref, station=False)
            continue
        station = _station(by_pid, ref, n_points[ref])
        entry = {'derived_cross': derived_cross, 'gt': len(station)}
        ok = terms is not None and terms['cross'] == len(station)
        if terms is not None and terms['lane_exact']:
            lanes = []
            for lane_terms in terms['lanes']:
                row = next(r for r in rs if r.lane == lane_terms['lane'])
                gt_lane = by_pid.get(f'xl:{row.dcp_no}', [])
                known = [ev for ev in gt_lane if ev.lane is not None]
                changed = len(gt_lane) - len(known)
                # A lane-unknown crossing belongs to exactly one lane of the station (the station sum is exact).
                lanes.append({'lane': lane_terms['lane'], 'derived': lane_terms['cross'], 'gt': len(known),
                              'gt_lane_change': changed,
                              'ok': len(known) <= lane_terms['cross'] <= len(known) + changed})
            entry['lanes'] = lanes
            # CONTRACT 3 (lane_exact): the lane terms carry the lane at p, so a lane change inside [x, p) moves a
            # crossing between lanes; only their sum (+R) is the station cross. They are judged where a lane
            # value is consumed (LANE_JUDGED_ROLES), else reported.
            if rs[0].role in LANE_JUDGED_ROLES:
                ok = ok and all(x['ok'] for x in lanes)
            else:
                entry['lanes_report_only'] = True
        bounds[ref] = judged(entry, ok, ref)
    items['boundaries'] = {'ok': _tri(v['ok'] for v in bounds.values()), 'by_ref': bounds}

    # heads -------------------------------------------------------------
    window_doc = derived.get('head_window') or {}
    heads_doc = {str(h['head_id']): h for h in window_doc.get('heads', [])}
    heads, head_of = {}, {}
    steps = range(10 * s + 1, 10 * e + 1)
    for row in rows:
        if row.role != 'head':
            continue
        head, sc, sg = oc.parse_head_ref(row.ref)
        d = row.dcp_no
        exp = expected[d]
        per_rule = {}
        for rule in SIG_RULES:
            states = [sig_state((sc, sg), b10, rule) for b10 in steps]
            per_rule[rule] = {'covered': all(v is not None for v in states),
                              'green_sec': sum(v == oc.GREEN_STATE for v in states) / 10,
                              'qualified': sum(sig_state((sc, sg), ev.b10, rule) == oc.GREEN_STATE
                                               for ev in exp.values())}
        doc = heads_doc.get(head)
        truth = per_rule[sig_rule]
        entry = {'sc': sc, 'sg': sg, 'crossings': None if doc is None else doc['crossings'], 'gt_crossings': len(exp),
                 'qualified_crossings': None if doc is None else doc['qualified_crossings'],
                 'green_sec': None if doc is None else doc['green_sec'], 'gt': per_rule,
                 'gt_lane_change': len(resolution.unknown_at.get(d, ())),
                 'gt_com_sec': len(sig_truth.com.get((sc, sg), ()))}   # read back shifted by the COM head delay
        if not truth['covered']:
            entry['ok'] = None
        else:
            green_ok = doc is not None and abs(doc['green_sec'] - truth['green_sec']) < 1e-9
            entry['ok'] = (green_ok and not failed_at[d] and doc['crossings'] == len(exp)
                           and doc['qualified_crossings'] == truth['qualified'])
            head_of[d] = (head, sc, sg, doc, truth, green_ok)
        heads[head] = entry
    # Heads tied by open lane-unknown crossings: one lane choice must give each head its crossings and
    # qualified crossings (the GT state of the head the choice puts the crossing at).
    for gi, (group, fits) in enumerate(lane_groups):
        mine = [d for d in sorted(group['rows']) if d in head_of]
        if not mine:
            continue

        def fits_heads(choice):
            for d in mine:
                head, sc, sg, doc, truth, _ = head_of[d]
                add = sum(d in opt for opt in choice)
                add_q = sum(d in opt and sig_state((sc, sg), c['b10'], sig_rule) == oc.GREEN_STATE
                            for opt, c in zip(choice, group['crossings']))
                if doc is None or (doc['crossings'], doc['qualified_crossings']) != (len(expected[d]) + add,
                                                                                    truth['qualified'] + add_q):
                    return False
            return True

        ok = None if fits is None else any(fits_heads(ch) for ch in fits)
        for d in mine:
            head, _, _, _, _, green_ok = head_of[d]
            heads[head]['lane_change_group'] = gi
            heads[head]['ok'] = None if ok is None else ok and green_ok and not failed_at[d]
    items['heads'] = {'ok': _tri(h['ok'] for h in heads.values()), 'sig_rule': sig_rule, 'by_head': heads}

    # ledger 10643 --------------------------------------------------------
    ref = f'x10643_exit:{oc.OFFRAMP_10643}'
    if ref in groups:
        station = _station(by_pid, ref, n_points[ref])
        gt_map = {}
        for veh, ev in station.items():
            route = gt['routes_at_exit'].get((veh, ev.b10))
            label = network.destination_10643(route[0]) if route and route[1] in (None, ROUTE_DECISION_10643) else None
            gt_map[veh] = (ev.lane, label, ev.lanes)
        derived_map = {v['veh']: (v['lane'], v['connector']) for v in derived['ledger_10643']['vehicles']}

        def same(veh):
            lane, label, lanes = gt_map[veh]
            d_lane, d_label = derived_map[veh]
            lane_ok = d_lane == lane if lane is not None else (lanes is None or d_lane in lanes)
            return lane_ok and d_label == label

        mismatched = sorted(v for v in set(gt_map) & set(derived_map) if not same(v))
        items['ledger_10643'] = judged({
            'gt': len(gt_map), 'derived': len(derived_map),
            'missing': sorted(set(gt_map) - set(derived_map))[:20], 'extra': sorted(set(derived_map) - set(gt_map))[:20],
            'mismatched': [{'veh': v, 'gt': gt_map[v][:2], 'derived': derived_map[v]} for v in mismatched[:20]],
            'gt_lane_unknown': sorted(v for v, x in gt_map.items() if x[0] is None)[:20],
            'gt_by_lane': {str(l): dict(Counter(str(c) for (ll, c, _) in gt_map.values() if ll == l))
                           for l in sorted({l for l, _, _ in gt_map.values() if l is not None})}},
            not mismatched and set(gt_map) == set(derived_map), ref, station=False)

    # ramp arrival shares, off split, source, 403 --------------------------
    ramps = {}
    for ramp, shares in derived['ramp_arrival_shares'].items():
        rs = groups.get(f'ramp_arrival:{ramp}', ())
        counts = [len([x for x in by_pid.get(f'xl:{r.dcp_no}', []) if x.lane is not None]) for r in rs]
        # A lane-unknown arrival adds one to one of its possible lanes of this ramp.
        unknown = {}
        for i, r in enumerate(rs):
            for x in by_pid.get(f'xl:{r.dcp_no}', []):
                if x.lane is None:
                    unknown.setdefault((x.veh, x.b10), set()).add(i)
        lane_sets = [sorted(v) for v in unknown.values()]
        if math.prod(len(v) for v in lane_sets) > MAX_LANE_CHOICES:
            possible = None
        else:
            possible = []
            for choice in itertools.product(*lane_sets):
                c = list(counts)
                for i in choice:
                    c[i] += 1
                total = sum(c)
                possible.append([x / total for x in c] if total else [1.0 / len(c)] * len(c) if c else [])
        entry = {'derived': shares, 'gt_counts': counts, 'gt_lane_change': len(lane_sets),
                 'gt_shares': possible[0] if possible and len(possible) == 1 else None}
        if possible is not None and len(possible) != 1:
            entry['gt_shares_possible'] = possible[:20]
        ok = None if possible is None else any(
            len(truth) == len(shares) and all(abs(a - b) <= oc.SHARE_TOL for a, b in zip(truth, shares))
            for truth in possible)
        ramps[ramp] = judged(entry, ok, f'ramp_arrival:{ramp}', station=False) if ok is not None else \
            {**entry, 'ok': None, 'note': 'too many lane choices'}
    items['ramp_arrival_shares'] = {'ok': _tri(r['ok'] for r in ramps.values()), 'by_ramp': ramps}

    splits = {}
    for off, row in derived['off_split'].items():
        gt_off = len(_station(by_pid, f'off_entry:{off}', n_points.get(f'off_entry:{off}', 0)))
        gt_through = len(_station(by_pid, f'through:{off}', n_points.get(f'through:{off}', 0)))
        splits[off] = judged({'derived_off': row['off_veh'], 'gt_off': gt_off, 'derived_through': row['downstream_veh'],
                              'gt_through': gt_through},
                             row['off_veh'] == gt_off and row['downstream_veh'] == gt_through,
                             f'off_entry:{off}', f'through:{off}')
    items['off_split'] = {'ok': _tri(v['ok'] for v in splits.values()), 'by_off': splits}

    sources = {}
    for road, block in derived['source_boundary'].items():
        gt_n = len(_station(by_pid, f'source:{road}', n_points.get(f'source:{road}', 0)))
        sources[road] = judged({'derived_admitted_window': block['admitted_window'], 'gt': gt_n},
                               block['admitted_window'] == gt_n, f'source:{road}')
    items['source'] = {'ok': _tri(v['ok'] for v in sources.values()), 'by_road': sources}

    refs403 = [f'headfree:{c}' for c in oc.HEADFREE_CONNECTORS]
    gt403 = sum(len(_station(by_pid, ref, n_points.get(ref, 0))) for ref in refs403)
    value403 = derived['link_departures_window'].get(oc.BYPASS_SOURCE_LINK)
    items['link_403'] = judged({'derived': value403, 'gt': gt403}, value403 == gt403, *refs403)

    # freeway exit count --------------------------------------------------
    value = derived['freeway_exit_count']['value']
    in_window = [veh for veh, b10 in exits if 10 * s < b10 <= 10 * e]
    chain_anomalies = [a for a in gt.get('chain_anomalies', ()) if 10 * s < a['b10'] <= 10 * e]
    hidden = gt.get('chain_resolved', [])
    items['freeway_exit_count'] = {'derived': value, 'gt': len(in_window), 'terms': derived['freeway_exit_count'],
                                   'unrecorded_connector': {'count': len(hidden),
                                                            'by_outcome': dict(Counter(h['outcome'] for h in hidden)),
                                                            'examples': hidden[:20]},
                                   'anomalies': chain_anomalies[:20],
                                   'ok': not chain_anomalies and value == len(in_window)}

    # lag, ambiguity, signal log, meter heads, .err realtime, Edie ------------
    strict = bool(derived.get('strict'))
    items['lag'] = {'lag': derived['lag'], 'boundary_ambiguous': derived['boundary_ambiguous'],
                    'ok': derived['lag']['ok'] is True and (not strict or derived['boundary_ambiguous'] == 0)}
    log = obs['signal_log']
    items['signal_log'] = {'ok': None, 'complete': log['complete'],
                           'fail_events': [e_ for e_ in log['events'] if e_[3] == 'fail'],
                           'own_events': [e_ for e_ in log['events'] if e_[3] == 'own']}
    meters = {}
    for row in rows:
        if row.role != 'meter_head':
            continue
        head, sc, sg = oc.parse_head_ref(row.ref)
        n = len(expected[row.dcp_no])
        states = [sig_state((sc, sg), b10, sig_rule) for b10 in range(10 * s + 1, 10 * e + 1)]
        green = sum(v == oc.GREEN_STATE for v in states) / 10 if all(v is not None for v in states) else None
        meters[f'{head}:{row.lane}'] = {'vehs': obs['detectors'][str(row.dcm_no)], 'gt': n, 'gt_green_sec': green,
                                        'veh_per_green_sec': (n / green) if green else None}
    items['meter_heads'] = {'ok': None, 'by_head_lane': meters}
    # D10 on the vehicles: lead departures after COM GREEN writes (D10Probe, fed by collect); crossings of COM
    # heads in the second after a RED write are reported (with D10 = 1 the heads still show GREEN then).
    probe = gt.get('d10_probe')
    d10 = probe.item(delay) if probe is not None else {'ok': None, 'configured_delay_s': delay, 'probed': False}
    after_red = []
    for row in rows:
        if row.role not in ('head', 'meter_head'):
            continue
        _, sc, sg = oc.parse_head_ref(row.ref)
        table = sig_truth.signals.get((sc, sg)) or {}
        for u in range(s + 1, e):
            if (sig_truth.is_com((sc, sg), u) and table.get(10 * u) not in (None, oc.GREEN_STATE)
                    and table.get(10 * u - 1) == oc.GREEN_STATE):
                n = sum(1 for ev in expected[row.dcp_no].values() if 10 * u < ev.b10 <= 10 * u + 10)
                after_red.append({'sg': f'{sc}-{sg}', 'dcp': row.dcp_no, 'write_s': u, 'crossings_next_second': n})
    d10['red_writes'] = len(after_red)
    d10['crossings_in_second_after_red_write'] = sum(r['crossings_next_second'] for r in after_red)
    d10['red_write_examples'] = [r for r in after_red if r['crossings_next_second']][:20]
    items[D10_ITEM] = d10
    chunk =[r for r in bundle.err_rows if r.get('kind') == 'lane_change_removal' and s < r['time_sec'] <= e]
    final = [r for r in removal_rows if s < r['time_sec'] <= e]
    seen = {(r['vehicle_id'], r['time_sec']) for r in chunk}
    items['err_realtime'] = {'ok': None, 'chunk_removals_in_window': len(chunk), 'final_removals_in_window': len(final),
                             'not_yet_in_chunk': [{'veh': r['vehicle_id'], 'time_sec': r['time_sec']}
                                                  for r in final if (r['vehicle_id'], r['time_sec']) not in seen][:20],
                             'err_max_sim_sec': obs['err']['max_sim_sec'],
                             'lag_s': None if obs['err']['max_sim_sec'] is None else e - obs['err']['max_sim_sec']}
    items['edie'] = {'ok': None, 'residuals': derived.get('edie_residuals')}
    items['gt_anomalies'] = {'ok': not anomalies, 'count': len(anomalies),
                             'by_kind': dict(Counter(a['kind'] for a in anomalies)), 'examples': anomalies[:20]}
    return items


def window_verdict(items):
    """(verdict, failed items, not judged items): report-only items never decide."""
    judged = {k: v.get('ok') for k, v in items.items() if k not in REPORT_ONLY}
    failed = sorted(k for k, v in judged.items() if v is False)
    # d10 without evidence in this window is not incomplete here: the run needs it once (verify, run_d10).
    incomplete = sorted(k for k, v in judged.items() if v is None and k != D10_ITEM)
    return ('FAIL' if failed else 'INCOMPLETE' if incomplete else 'PASS'), failed, incomplete


# ---------------------------------------------------------------- run level
def gt_folder(gt_dir, run_dir, decisions):
    """The one folder holding gt_veh.csv (and its gt_sig.csv): --gt-dir only when given, else the
    runner's <decisions>\\obs150_gt, the run folder, the decisions folder. Files are never mixed."""
    folders = [Path(gt_dir)] if gt_dir is not None else [decisions / GT_SUBDIR, run_dir, decisions]
    for folder in folders:
        if (folder / 'gt_veh.csv').is_file():
            require((folder / 'gt_sig.csv').is_file(), f'{folder} has gt_veh.csv but no gt_sig.csv')
            return folder
    raise ToolError(f'gt_veh.csv not found in {", ".join(str(f) for f in folders)}')


def run_d10(windows):
    """Run-level D10 verdict from the windows' d10 items: False if any window contradicts the configured
    COM head delay, True if some window confirms it, None (not re-checked) when COM heads were in the GT
    windows but no GREEN write found a standing lead vehicle, 'not_applicable' without COM-owned heads."""
    items = [w['items'].get(D10_ITEM) or {} for w in windows]
    oks = [d.get('ok') for d in items]
    applicable = any(d.get('com_head_sgs') for d in items)
    ok = False if False in oks else True if True in oks else None if applicable else 'not_applicable'
    kinds = Counter()
    for d in items:
        kinds.update(d.get('by_kind', {}))
    return {'ok': ok, 'configured_delay_s': items[0].get('configured_delay_s') if items else None,
            'lead_samples': sum(d.get('lead_samples', 0) for d in items), 'by_kind': dict(kinds),
            'green_writes': sum(d.get('green_writes', 0) for d in items),
            'crossings_in_second_after_red_write': sum(d.get('crossings_in_second_after_red_write', 0) for d in items)}


def verify(target, *, gt_dir=None, windows=None, network_path=None, err_path=None, sig_rule='next', out=None,
           com_head_delay=None):
    require(sig_rule in SIG_RULES, f'--sig-rule must be one of {SIG_RULES}')
    delay = com_head_delay_default() if com_head_delay is None else com_head_delay
    decisions = find_decisions_dir(target)
    run_dir, name = decisions.parent, decisions.name[len('decisions_'):]
    states = {}

    def state(t):
        if t not in states:
            path = decisions / f'state_{t:06d}.json'
            require(path.is_file(), f'State missing: {path}')
            with io.open(path, encoding='utf-8-sig') as handle:
                states[t] = json.load(handle)
        return states[t]

    if windows is None:
        latest = sorted(decisions.glob('state_*.json'))
        require(latest, f'No state files in {decisions}')
        with io.open(latest[-1], encoding='utf-8-sig') as handle:
            windows = json.load(handle)[oc.RAW_STATE_KEY]['ground_truth_windows']
    require(windows, 'No ground-truth windows (RW_OBS150_GT) to verify')
    first = state(windows[0][1])
    obs = first[oc.RAW_STATE_KEY]
    rows, _ = oc.read_detector_csv(obs['detector_config']['path'], obs['detector_config']['sha256'])
    network = Network(network_path or first['network_path'])
    # An explicit --err must exist; the run's own .err may be absent only if no capture ever read a byte of it.
    require(err_path is None or Path(err_path).is_file(), f'--err {err_path} is not a file')
    err_path = err_path or obs['err']['source']
    require(Path(err_path).is_file() or all(state(e)[oc.RAW_STATE_KEY]['err']['byte_end'] == 0 for _, e in windows),
            f'The final .err {err_path} is missing although the captures read it')
    removed, route_end, removal_rows = read_removals(err_path)
    folder = gt_folder(gt_dir, run_dir, decisions)
    gt_veh, gt_sig = folder / 'gt_veh.csv', folder / 'gt_sig.csv'
    gt_meta = folder / 'gt_meta.csv' if (folder / 'gt_meta.csv').is_file() else None
    signals = read_gt_signals(gt_sig)
    provenance = read_json(run_dir / f'run_provenance_{name}.json')
    constants = vbs_constants(provenance['files']['generated_vbs_config']['path'])
    chain = {int(x) for road in ('E', 'W') for x in constants[f'RW_FW_{road}_CHAIN_LINKS'].split(',')}
    tracked = {r.link for r in rows}
    results = {'schema': 'obs150-gt-verdict/v1', 'run_dir': str(run_dir), 'sig_rule': sig_rule,
               'com_head_delay_s': delay,
               'files': {'gt_veh': str(gt_veh), 'gt_sig': str(gt_sig), 'gt_meta': str(gt_meta) if gt_meta else None,
                         'network': str(network_path or first['network_path']), 'err': str(err_path)},
               'windows': []}
    meta_steps = read_gt_meta_steps(gt_meta) if gt_meta else None
    for s, e in windows:
        t_state = state(e)
        derived_path = oc.resolve(t_state[oc.RAW_STATE_KEY], oc.derived_path(e))
        derived = json.loads(derived_path.read_text(encoding='utf-8')) if derived_path.is_file() else None
        frame_end = {int(v[0]): int(v[1]) for v in oc.load_bundle(t_state).frame_end['vehicles']}
        probe = D10Probe(rows, SignalTruth(signals, t_state[oc.RAW_STATE_KEY].get('signal_log'), (s, e), delay))
        gt = collect(gt_veh, network, rows, (s, e), tracked, removed, route_end, chain, meta_steps,
                     removal_rows=removal_rows, frame_end=frame_end, d10_probe=probe)
        gt['signals'] = signals
        gt['com_head_delay'] = delay
        items = verify_window((s, e), t_state, derived, rows, network, gt, removal_rows, sig_rule)
        verdict, failed, incomplete = window_verdict(items)
        results['windows'].append({'window': [s, e], 'verdict': verdict,
                                   'ok': {'PASS': True, 'FAIL': False, 'INCOMPLETE': None}[verdict],
                                   'failed': failed, 'not_judged': incomplete, 'items': items})
    verdicts = {w['verdict'] for w in results['windows']}
    results['d10'] = run_d10(results['windows'])
    d10_ok = results['d10']['ok']
    results['verdict'] = ('FAIL' if 'FAIL' in verdicts or d10_ok is False else
                          'INCOMPLETE' if 'INCOMPLETE' in verdicts or d10_ok is None else 'PASS')
    out = Path(out) if out else run_dir / 'obs150_gt_verdict.json'
    write_json(out, results)
    for w in results['windows']:
        for key, item in w['items'].items():
            print(f'GT_CHECK window={w["window"][0]}:{w["window"][1]} {key} ok={item.get("ok")}'
                  + (' report_only' if key in REPORT_ONLY else ''))
    for w in results['windows']:
        if w['verdict'] != 'PASS':
            print(f'GT_WINDOW {w["window"][0]}:{w["window"][1]} {w["verdict"]} failed={",".join(w["failed"]) or "-"} '
                  f'not_judged={",".join(w["not_judged"]) or "-"}')
    d10 = results['d10']
    print(f'GT_D10 ok={d10_ok} delay={d10["configured_delay_s"]} green_writes={d10["green_writes"]} '
          f'lead_samples={d10["lead_samples"]} by_kind={json.dumps(d10["by_kind"], sort_keys=True)} '
          f'crossings_after_red_write={d10["crossings_in_second_after_red_write"]}'
          + (' NOT_RECHECKED' if d10_ok is None else ''))
    print(f'GT_VERDICT {results["verdict"]} out={out}')
    return results


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('target')
    parser.add_argument('--gt-dir', default=None)
    parser.add_argument('--windows', default=None, help="e.g. 750:900,1050:1200 (default: the run's RW_OBS150_GT)")
    parser.add_argument('--network', default=None)
    parser.add_argument('--err', default=None)
    parser.add_argument('--sig-rule', default='next', choices=SIG_RULES)
    parser.add_argument('--out', default=None)
    parser.add_argument('--com-head-delay', type=int, choices=(0, 1), default=None,
                        help='D10 hypothesis for COM-owned heads (default: obs150_signal_clock.COM_HEAD_DELAY_S)')
    args = parser.parse_args(argv)
    windows = oc.parse_gt_windows(args.windows) if args.windows else None
    result = verify(args.target, gt_dir=args.gt_dir, windows=windows, network_path=args.network, err_path=args.err,
                    sig_rule=args.sig_rule, out=args.out, com_head_delay=args.com_head_delay)
    return VERDICT_EXIT[result['verdict']]


if __name__ == '__main__':
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        sys.exit(main(sys.argv[1:]))
    except (ToolError, oc.ObsContractError) as error:
        print(f'GT_ERROR {error}')
        sys.exit(2)
