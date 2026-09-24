"""obs150 lane observer (WP-B2, plan B6): the lane-plant quantities of one 150 s decision.

Every count comes from the one counting identity of obs150_contract (station
count + stock change of the short offset segment + removals, plan 1.3),
evaluated once by evaluate_boundaries for the whole detector table:

- off_split          X_off = cross(off_entry:<off>), through = cross(through:<off>),
                     ratio = X_off / (X_off + through) (LPO:221-225, BF:108-114);
- ramp_arrival_shares  per-lane entries of the receiving-node ramps (LPR:348-360
                     meaning "entry lane", now exact); no arrival -> equal shares;
- offramp_10643_lane_shares  per-lane entries onto 10643 (D-C (b));
- ledger_10643       the vehicle-level join 10643 exit lane x destination connector
                     (plan B6, D9). Every vehicle that crossed the end of 10643 in
                     the window is labelled from exactly one of: its frame_T row,
                     its destination-detector record, its .err removal row;
- offramp_10643_history  the local_history shape (LPR:222-247) built from the ledger;
- freeway_exit_count sum X_off + cross(chain_end:FW_E/FW_W) + chain removals (VBS:3645-3667
                     meaning: vehicles leaving chain membership, removed ones included);
- source_boundary    admitted interface of each mainline origin (BF:55-62, 102-105);
- link_departures_window  {403: cross(headfree:10565) + cross(headfree:10570)} (NEW-12);
- edie_residuals     audit only: Edie link-evaluation entries minus the station count.

Nothing here is estimated. A contradiction between the station identity and
the vehicle ledger raises ObsContractError; verification runs (strict) also
fail on an unidentified 10643 tail vehicle (D9), on a late removal row (D11) and
on a removal whose 0.1 m .err position straddles an inner segment end.
"""
from __future__ import annotations

from collections import defaultdict
import math

from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.obs150_contract import ObsContractError

# The SC1004 west approach: the RD 1126 destination connectors leave link 71
# (physical_urban_transport.geometry asserts the same three exits). The 1126
# routes run 10643 -> 126 -> 10641 -> 71 -> destination (inpx); 10700 leaves 126
# as well. RD 1126 sits on 10643 itself, so a vehicle on 126/10641/10700/71 that
# carries it came through 10643 (10776 traffic from link 70 carries RD 1140).
APPROACH_LINK_10643 = 71
_TOL = 1e-9


def _require(condition, message):
    if not condition:
        raise ObsContractError(message)


def _int_or_none(value):
    """COM writes route numbers as doubles; keep only exact integers (LPR:197-198)."""
    if value is None or value == '':
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, float):
        return int(value) if math.isfinite(value) and value.is_integer() else None
    if isinstance(value, int):
        return value
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if math.isfinite(number) and number.is_integer() else None


def _terms(boundaries, ref):
    _require(ref in boundaries, 'No identity terms for ' + ref)
    return boundaries[ref]


def _destinations():
    return {int(c) for c in oc.DESTINATION_CONNECTORS_10643}


# --------------------------------------------------------------------------
# Off-ramp split, arrival shares, lane shares
# --------------------------------------------------------------------------
def off_split(context, boundaries):
    out = {}
    for off in sorted(context.offramps, key=int):
        ref = context.offramps[off]
        exiting = _terms(boundaries, ref.off_entry_ref).cross
        through = _terms(boundaries, ref.through_ref).cross
        eligible = exiting + through
        out[off] = {'downstream_veh': through, 'off_veh': exiting, 'post_branch_ramp_bypass_veh': 0,
                    'eligible_exits_veh': eligible, 'ratio': exiting / eligible if eligible else 0.0}
    return out


def lane_entry_shares(terms, lanes, what):
    """Per-lane entry shares of one station; equal shares when nothing entered (LPR:357-360)."""
    _require(terms.lane_exact, what + ': lane_exact is false (a removal or a negative lane count in the segment)')
    by_lane = {t.lane: t.cross for t in terms.lanes}
    _require(tuple(sorted(by_lane)) == tuple(sorted(lanes)), what + ': detector lanes differ from the connector lanes')
    total = sum(by_lane[lane] for lane in lanes)
    if total == 0:
        return [1.0 / len(lanes)] * len(lanes)
    return [by_lane[lane] / total for lane in lanes]


def ramp_arrival_shares(context, boundaries):
    out = {}
    for name in sorted(context.ramp_arrivals):
        ref = context.ramp_arrivals[name]
        if ref.receiving:
            out[name] = lane_entry_shares(_terms(boundaries, ref.boundary_ref), ref.lanes, name)
    _require(out, 'No receiving-node ramp in the context')
    return out


def offramp_10643_lane_shares(context, boundaries):
    ref = context.offramps[oc.OFFRAMP_10643]
    shares = lane_entry_shares(_terms(boundaries, ref.off_entry_ref), ref.lanes, 'off_entry:10643')
    _require(len(shares) == 2, '10643 has two lanes')
    return shares


# --------------------------------------------------------------------------
# 10643 vehicle ledger (plan B6, D9)
# --------------------------------------------------------------------------
def frame_label(row, context):
    """Destination connector a frame row points to; the physical_urban_transport.observe
    intent (planned static RD 1126 route, current next link on 71, conflict -> None)."""
    link, decision, number, kind, next_link = row[1], _int_or_none(row[6]), _int_or_none(row[7]), row[8], _int_or_none(row[9])
    destinations = _destinations()
    if link in destinations:
        return link
    planned = None
    if isinstance(kind, str) and kind.lower() == 'static' and decision == oc.ROUTE_DECISION_10643:
        planned = context.route_destinations_10643.get(number)
    on_approach = link == APPROACH_LINK_10643 and next_link in destinations
    if on_approach and planned is not None and next_link != planned:
        return None
    return next_link if on_approach else planned


def removal_label(row, context):
    if row['route_decision'] != oc.ROUTE_DECISION_10643:
        return None
    return context.route_destinations_10643.get(row['route_index'])


def ledger_10643(context, boundaries, assignment, mer_rows, err_rows, frame_T, frame_prev, *, strict):
    """The vehicles that crossed the end x of 10643 in the interval, with lane and label.

    x10643_exit is an upstream offset station p < x (segment [p, x] per lane), so
    at vehicle level X = (M | Tail | S_start) - S_end - R, the same sets as the
    identity out_x = Vehs(p) + N(T-150) - N(T) - R:
      M       vehicles with an entry record at p in this interval (assign_window),
      Tail    vehicles that crossed p in (T-1, T] without a record yet, found in
              frame_T past p (on 10643 at pos >= p, or carrying RD 1126 on
              126/10641/10700/71/destination) and not past p in frame_{T-150},
      S_start/S_end  vehicles in [p, x] in the two frames, R removals in [p, x].
    Tail lanes come from the connector lane map (1.6); per lane they must equal
    the tails of assign_window (D9). |X| must equal cross(x10643_exit).
    via: 'tail' for Tail; 'mer' for M AND for S_start (a vehicle in [p, x] at
    T-150 whose record at p sits in an earlier chunk). The contract allows only
    these two values (validate_derived).
    Label order: destination record, then .err removal, then frame_T row. A
    destination record wins over a later removal on the destination connector
    or beyond it; a removal upstream of the destination (lane_map_10643 links)
    together with a destination record is a contradiction.
    Returns (ledger, composition): composition[g] = [(connector|None, n)] of lane g+1.
    """
    x_rows = context.boundaries[context.x10643_exit_ref]
    _require(all(r.orientation == 'up' and r.link == int(oc.OFFRAMP_10643) for r in x_rows),
             'x10643_exit must be an upstream offset station on 10643')
    x_terms = _terms(boundaries, context.x10643_exit_ref)
    lanes = tuple(r.lane for r in x_rows)
    _require(lanes == (1, 2), '10643 has two lanes')
    station = {r.lane: r.pos for r in x_rows}
    lane_of_dcp = {r.dcp_no: r.lane for r in x_rows}
    start, end = assignment.start_s, assignment.end_s
    destinations = _destinations()
    region = (set(context.lane_map_10643) - {int(oc.OFFRAMP_10643)}) | destinations

    frame_now = {row[0]: row for row in frame_T['vehicles']}

    def past_p(row):
        veh, link, lane, pos = row[:4]
        if link == int(oc.OFFRAMP_10643):
            return lane in station and pos >= station[lane]      # the segment closure of segment_contains
        return link in region and _int_or_none(row[6]) == oc.ROUTE_DECISION_10643

    def in_segment(frame):
        members = {}
        for r in x_rows:
            for veh in oc.vehicles_in_segment(frame['vehicles'], r.segment, 'up'):
                _require(veh not in members, 'A vehicle lies in two lanes of the 10643 exit segment')
                members[veh] = r.lane
        return members

    recorded = {}
    for r in x_rows:
        for row in assignment.entries.get(r.dcp_no, ()):
            _require(row.veh not in recorded, f'Vehicle {row.veh} recorded twice at the 10643 exit in one interval')
            recorded[row.veh] = r.lane
    recorded_any = {row.veh for row in mer_rows if row.dcp in lane_of_dcp and row.ordinal is not None}
    s_end, s_start = in_segment(frame_T), in_segment(frame_prev)
    window = oc.window_removals(err_rows, start, end)
    removed_seg = {x['vehicle_id'] for x in oc.removals_in_boundary(window, x_rows)}
    before = {row[0] for row in frame_prev['vehicles'] if past_p(row)}

    tail = defaultdict(dict)
    unmapped = []
    for veh, row in frame_now.items():
        if not past_p(row) or veh in recorded_any or veh in before:
            continue
        lane = context.lane_map_10643.get(row[1], {}).get(row[2])
        if lane is None:
            unmapped.append(veh)
        else:
            tail[lane][veh] = row
    expected = {lane_of_dcp[dcp]: n for dcp, n in assignment.tails.items() if dcp in lane_of_dcp}
    _require(set(expected) == set(lanes),
             f'The window assignment lacks a tail of the 10643 exit lanes (has lanes {sorted(expected)})')
    identified =not unmapped and all(len(tail.get(lane, {})) == expected[lane] for lane in lanes) \
        and set(tail) <= set(lanes)
    placeholders = {lane: 0 for lane in lanes}
    if not identified:
        _require(not strict, f'D9: 10643 tail vehicles not identified (expected {expected}, found '
                             f'{ {k: len(v) for k, v in tail.items()} }, unmapped {len(unmapped)})')
        # Operational run: keep only the exact part. Unrecorded vehicles still on
        # 10643 are in [p, x] (not yet crossed x); the rest are unidentified.
        for lane in lanes:
            on_connector = sum(1 for row in tail.get(lane, {}).values() if row[1] == int(oc.OFFRAMP_10643))
            placeholders[lane] = expected[lane] - on_connector
            _require(placeholders[lane] >= 0, 'More unrecorded vehicles in the 10643 exit segment than its tail')
        tail = defaultdict(dict, {lane: {v: r for v, r in rows.items() if r[1] == int(oc.OFFRAMP_10643)}
                                  for lane, rows in tail.items()})

    crossed = {}
    for veh, lane in list(recorded.items()) + list(s_start.items()):
        if veh in s_end or veh in removed_seg:
            continue
        _require(veh not in crossed, f'Vehicle {veh} both recorded in and present before the 10643 interval')
        crossed[veh] = (lane, 'mer')
    for lane, rows in tail.items():
        for veh in rows:
            if veh not in s_end:
                crossed[veh] = (lane, 'tail')
    _require(len(crossed) + sum(placeholders.values()) == x_terms.cross,
             f'10643 vehicle ledger {len(crossed) + sum(placeholders.values())} differs from the station '
             f'identity {x_terms.cross}')

    destination_of = {}
    for connector, ref in context.destination_refs.items():
        for r in context.boundaries[ref]:
            for row in assignment.entries.get(r.dcp_no, ()):
                _require(destination_of.get(row.veh, int(connector)) == int(connector),
                         f'Vehicle {row.veh} recorded at two destination connectors')
                destination_of[row.veh] = int(connector)
    removal_of = {}
    for row in window:
        removal_of.setdefault(row['vehicle_id'], row)
    pre_destination = set(context.lane_map_10643)

    vehicles = []
    for veh, (lane, via) in sorted(crossed.items(), key=lambda item: (item[1][0], item[0])):
        row = frame_now.get(veh)
        if veh in destination_of:
            # A destination record wins over a later removal on the destination
            # connector or beyond it (47/56/67...): a normal trajectory. A removal on
            # 10643 -> 126 -> 10641/10700 -> 71 cannot follow the record.
            removal = removal_of.get(veh)
            _require(removal is None or removal['link'] not in pre_destination,
                     f'Vehicle {veh} has a destination record but was removed upstream of it '
                     f'(link {None if removal is None else removal["link"]})')
            _require(row is None or row[1] not in pre_destination,
                     f'Vehicle {veh} has a destination record but is still upstream at T')
            _require(row is None or row[1] not in destinations or row[1] == destination_of[veh],
                     f'Vehicle {veh} sits on another destination connector than its record')
            connector, source = destination_of[veh], 'destination'
        elif veh in removal_of:
            _require(row is None, f'Removed vehicle {veh} is still in frame_T')
            connector = removal_label(removal_of[veh], context)
            source = 'removal' if connector is not None else 'unidentified'
        elif row is not None and (row[1] in pre_destination or row[1] in destinations):
            connector = frame_label(row, context)
            source = 'frame' if connector is not None else 'unidentified'
        else:
            connector, source = None, 'unidentified'
        _require(not (strict and source == 'unidentified'), f'D9: 10643 vehicle {veh} has no destination label')
        vehicles.append({'veh': veh, 'lane': lane, 'via': via, 'connector': connector, 'label_source': source})
    for lane in lanes:
        vehicles.extend({'veh': None, 'lane': lane, 'via': 'tail', 'connector': None, 'label_source': 'unidentified'}
                        for _ in range(placeholders[lane]))

    by_lane = {str(lane): {} for lane in lanes}
    counts = {lane: defaultdict(int) for lane in lanes}
    for v in vehicles:
        counts[v['lane']][v['connector']] += 1
        if v['connector'] is not None:
            key = str(v['connector'])
            by_lane[str(v['lane'])][key] = by_lane[str(v['lane'])].get(key, 0) + 1
    by_lane = {lane: dict(sorted(v.items())) for lane, v in by_lane.items()}
    ledger = {'vehicles': vehicles, 'by_lane': by_lane,
              'tail_by_lane': {str(lane): expected[lane] for lane in lanes}}
    composition = []
    for lane in lanes:
        lane_counts = dict(counts[lane])
        if not lane_counts:
            # LPR:243-244: an empty lane takes the labels of the vehicles on 10643 now, else None.
            for row in frame_T['vehicles']:
                if row[1] == int(oc.OFFRAMP_10643) and row[2] == lane:
                    label = frame_label(row, context)
                    lane_counts[label] = lane_counts.get(label, 0) + 1
        if not lane_counts:
            lane_counts = {None: 1}
        composition.append(sorted(lane_counts.items(), key=lambda kv: (kv[0] is None, kv[0] or 0)))
    return ledger, composition


def offramp_history(composition, cutoff):
    """local_history (LPR:222-247) shape; shares n/total per lane, None last."""
    result = []
    for lane_counts in composition:
        total = sum(n for _, n in lane_counts)
        result.append([[connector, n / total] for connector, n in lane_counts])
    return {'off_composition': result, 'background': {}, 'exchange_rates': [], 'information_cutoff_s': cutoff,
            'history_start_s': max(0, cutoff - oc.DECISION_INTERVAL_SEC), 'endogenous_background': True}


# --------------------------------------------------------------------------
# Chain exits, origin boundary, 403 departures
# --------------------------------------------------------------------------
def freeway_exit_count(context, boundaries, err_rows, start_s, end_s):
    off_total = sum(_terms(boundaries, ref.off_entry_ref).cross for ref in context.offramps.values())
    chain_end_total = sum(_terms(boundaries, context.chain_end_refs[road]).cross for road in oc.ROADS)
    chain = set().union(*(set(links) for links in context.chain_links.values()))
    chain_removals = sum(1 for x in oc.window_removals(err_rows, start_s, end_s) if x['link'] in chain)
    return {'value': off_total + chain_end_total + chain_removals, 'off_total': off_total,
            'chain_end_total': chain_end_total, 'chain_removals': chain_removals}


def source_boundary(obs, context, boundaries):
    """admitted_cum = sum of the interval identity since t=0 (N(0)=0):
    source_cumulative_vehs + N_[0,p)(T) + removals_cum_by_boundary."""
    start, end, k = oc.bundle_interval(obs['sim_sec'])
    interval = end - start
    out = {}
    for road in oc.ROADS:
        ref = context.source_refs[road]
        terms = _terms(boundaries, ref)
        _require(terms.orientation == 'down', ref + ' must be a downstream offset station')
        cumulative = obs['source_cumulative_vehs'][road] + terms.n_end + obs['err']['removals_cum_by_boundary'][ref]
        _require(cumulative >= terms.cross, ref + ': cumulative admitted count below the interval count')
        integral = oc.schedule_integral_veh(context.source_schedule[road], 0.0, float(end))
        out[road] = {'admitted_window': terms.cross, 'admitted_cum': cumulative, 'interval_s': interval,
                     'recent_vph': 3600.0 * terms.cross / interval, 'schedule_integral_veh': integral,
                     'backlog_veh': max(0.0, integral - cumulative)}
    return out


def link_departures(context, boundaries):
    return {oc.BYPASS_SOURCE_LINK: sum(_terms(boundaries, context.headfree_refs[c]).cross
                                       for c in oc.HEADFREE_CONNECTORS)}


# --------------------------------------------------------------------------
# .err position resolution (strict runs)
# --------------------------------------------------------------------------
# The .err writes the front position rounded to 0.1 m (probe: 3689 at 76.238 m is
# "76.2"; all 12 probe removals carry one decimal), so a removal row places the
# vehicle only within +-0.05 m. The segment ends are 6-decimal positions.
ERR_POSITION_HALF_STEP_M = 0.05


def ambiguous_removals(context, err_rows, start_s, end_s):
    """[(vehicle_id, boundary_ref, end_m)] of window removals whose rounded .err position
    may lie on either side of an inner end of an offset segment.

    removals_in_boundary (R of the identity, the 10643 ledger) decides membership
    from the rounded position, so such a row may be counted in the wrong segment.
    A segment end at the link start (0) or at/after the link end of the row's own
    link is not inner: every position on the link lies on one side of it.
    """
    out = set()
    for removal in oc.window_removals(err_rows, start_s, end_s):
        for ref, rows in context.boundaries.items():
            for row in rows:
                length = row.geometry_assert.get('link_length_m')
                for piece in row.segment:
                    if piece.link != removal['link']:
                        continue
                    for end_m in (piece.from_m, piece.to_m):
                        outer = end_m <= 0.0 or (piece.link == row.link and length is not None
                                                 and end_m >= float(length) - _TOL)
                        if not outer and abs(removal['position_m'] - end_m) <= ERR_POSITION_HALF_STEP_M + _TOL:
                            out.add((removal['vehicle_id'], ref, end_m))
    return sorted(out)


# --------------------------------------------------------------------------
# Edie audit (PRB e, V0-7)
# --------------------------------------------------------------------------
def edie_weight(position_m, length_m, segment_m):
    """Share of the link-evaluation segment average a vehicle at position still has to drive.

    VISSIM averages the Edie flow of the segments [0, s), [s, 2s), ... (last one
    shorter). For a link without intermediate entries or exits this gives
    entries = E + sum_T w(y) - sum_{T-150} w(x), E = AVG volume * interval / 3600.
    """
    nseg = max(1, math.ceil(length_m / segment_m - _TOL))
    p = min(max(position_m, 0.0), length_m)
    j = min(int(p // segment_m), nseg - 1)
    lo, hi = j * segment_m, min((j + 1) * segment_m, length_m)
    fraction = (p - lo) / (hi - lo) if hi > lo else 1.0
    return (nseg - j - fraction) / nseg


def edie_entries(volume_veh_h, interval_s, length_m, segment_m, positions_end, positions_start):
    return (volume_veh_h * interval_s / 3600.0
            + math.fsum(edie_weight(y, length_m, segment_m) for y in positions_end)
            - math.fsum(edie_weight(x, length_m, segment_m) for x in positions_start))


def _entry_boundaries(context):
    """link -> boundary_ref of the entry station at the start of that connector."""
    out = {}
    for ref in context.offramps.values():
        out[int(ref.connector)] = ref.off_entry_ref
    for ref in context.ramp_arrivals.values():
        out[int(ref.connector)] = ref.boundary_ref
    for connector, ref in context.headfree_refs.items():
        out[int(connector)] = ref
    return out


def edie_residuals(raw, context, boundaries, frame_T, frame_prev):
    """{link: Edie entries - station entries} for every evaluated connector with an entry station.

    Volumes: obs150 linkeval_volume_veh_h (off connectors, 10565/10570) and the far
    link_volume of the state (on-ramps; D-D (a) keeps its Edie meaning). Audit only.
    """
    obs = raw[oc.RAW_STATE_KEY]
    start, end, k = oc.bundle_interval(obs['sim_sec'])
    if k is None:
        return {}
    volumes = {}
    far = ((raw.get('local_observation') or {}).get('far_measurement') or {}).get('link_volume_veh_h') or {}
    for key, value in far.items():
        volumes[str(key)] = value
    for key, value in obs['linkeval_volume_veh_h'].items():
        volumes[str(key)] = value
    entries = _entry_boundaries(context)
    out = {}
    for key in sorted(volumes, key=lambda s: int(s) if s.isdigit() else -1):
        value = volumes[key]
        if not key.isdigit() or int(key) not in entries or value is None:
            continue
        ref = entries[int(key)]
        rows = context.boundaries[ref]
        geometry = rows[0].geometry_assert
        segment = geometry.get('linkeval_segment_m')
        if segment is None:
            continue
        link = int(key)
        at_end = [row[3] for row in frame_T['vehicles'] if row[1] == link]
        at_start = [row[3] for row in frame_prev['vehicles'] if row[1] == link]
        estimate = edie_entries(float(value), end - start, float(geometry['link_length_m']), float(segment),
                                at_end, at_start)
        out[key] = estimate - _terms(boundaries, ref).cross
    return out


# --------------------------------------------------------------------------
# Contract interface (plan 1.9)
# --------------------------------------------------------------------------
def derive(raw, context, mer_rows, err_rows, frame_T, frame_prev, *, boundaries=None, assignment=None):
    """LANE_PART_KEYS of the bundle raw['obs150'] (CONTRACT 5.1).

    raw: the state (top-level obs150 bundle; local_observation for the far volumes);
    mer_rows/err_rows: the T chunks (file order); frame_T/frame_prev: the frames at
    T and T-150 (frame_000000 at T=150, empty). Keywords take the evaluate_boundaries
    and assign_window results the caller already has.
    """
    obs = raw[oc.RAW_STATE_KEY]
    start, end, k = oc.bundle_interval(obs['sim_sec'])
    _require(frame_T['time_s'] == end and frame_prev['time_s'] == start,
             f'Frames must be at {start} and {end}, got {frame_prev["time_s"]} and {frame_T["time_s"]}')
    _require(obs['detector_config']['sha256'] == context.detector_csv_sha256,
             'The bundle was captured with another detector table')
    mer_rows, err_rows = list(mer_rows), list(err_rows)
    if boundaries is None:
        boundaries = oc.evaluate_boundaries(obs, context.detectors, frame_T, frame_prev, err_rows)
    if assignment is None:
        assignment = oc.assign_window(obs, mer_rows)
    _require((assignment.start_s, assignment.end_s) == (start, end), 'Window assignment of another interval')
    strict = bool(obs['ground_truth_windows'])
    if strict:
        # D11 (open until G1): a removal row with time <= T-150 in the T chunk reached
        # the .err after the previous capture. window_removals keeps it out of both
        # windows' R, so a count of the earlier window was silently off. Verification
        # runs stop here; the derived schema has no slot to carry it in operational runs.
        late = [r for r in err_rows if r.get('kind') == 'lane_change_removal' and r['time_sec'] <= start]
        _require(not late, f'D11: {len(late)} removal row(s) of an earlier window reached the .err only in the '
                           f'{end} s chunk (first: vehicle {late[0]["vehicle_id"] if late else None} at '
                           f'{late[0]["time_sec"] if late else None} s on link {late[0]["link"] if late else None})')
        # Exact counts only: a removal within the .err rounding of an inner segment end
        # has no decidable segment. Operational runs count it by the rounded position.
        ambiguous = ambiguous_removals(context, err_rows, start, end)
        _require(not ambiguous, f'{len(ambiguous)} removal(s) lie within {ERR_POSITION_HALF_STEP_M} m of an inner '
                                f'offset segment end (vehicle, boundary, end): {ambiguous[:3]}')
    if k is None:
        # t=1 closure (plan B6): nothing can have reached an off-ramp or a chain end in (0, 1].
        for ref in [r.off_entry_ref for r in context.offramps.values()] + list(context.chain_end_refs.values()):
            _require(all(obs['detectors'][str(row.dcm_no)] == 0 for row in context.boundaries[ref]),
                     't=1: open-interval Vehs of ' + ref + ' must be 0')
    split = off_split(context, boundaries)
    ledger, composition = ledger_10643(context, boundaries, assignment, mer_rows, err_rows, frame_T, frame_prev,
                                       strict=strict)
    departures = link_departures(context, boundaries)
    exits = freeway_exit_count(context, boundaries, err_rows, start, end)
    if k is None:
        _require(departures[oc.BYPASS_SOURCE_LINK] == 0 and exits['value'] == 0,
                 't=1 closes departures and the freeway exit count at 0')
    return {'off_split': split,
            'ramp_arrival_shares': ramp_arrival_shares(context, boundaries),
            'offramp_10643_history': offramp_history(composition, end),
            'offramp_10643_lane_shares': offramp_10643_lane_shares(context, boundaries),
            'ledger_10643': ledger,
            'freeway_exit_count': exits,
            'source_boundary': source_boundary(obs, context, boundaries),
            'link_departures_window': departures,
            'edie_residuals': edie_residuals(raw, context, boundaries, frame_T, frame_prev)}
