"""SC1001 EB stopline approach: lane FIFO packets over existing stocks (K8-6, option 1 v2).

Binding text: OPT1_V2_SPEC.md (sha 7a2624a7) and OPT1_V2_SPEC_AMENDMENT_1.md r2
(sha 9efd3021), K8 predeclaration amendments 1 r2, 2 (N-A4, N-A5) and 3, user
decision D-K8-1 (judging arm = observed_full storage, geometric = report arm).

No ledger node is added. The three lanes of link 127 are an index over stocks
that already exist: a moving packet is part of `storage:in_SC1001_W` (and of
its paired arrival/release reservation), a ready packet is part of its W
member movement queue. Lane 1 = {E, S}, lane 2 = {E}, lane 3 = {N}.

AD rules (amendment section 5.9, N19)
- Structure (packet creation/deletion, `tags` keys, ledger transfer count and
  route key, ready prefix, head-of-line stop) is decided on primal values only.
- Primal <= 1e-12 values are folded, never dropped: service residuals and city
  shares go to `carry[l][m]`, transfer shares merge into a sibling transfer, an
  untagged moving port share stays in the paired reservation (N-A4).
- Only builtin min/max and math are used on traffic values, so the tangent
  Finder instruments them; float() coercion is not used on traffic values.
- The four fold sites are named functions (hook anchors that survive rebases):
  _fold_service_residual, _fold_city_share, _merge_tiny_transfer,
  _skip_tiny_port_share.  Their *_events counters count site visits (K8
  amendment 14, user decision D-K8-8).

Key absent: nothing here runs and no attribute is created (configure and
initialize return {} before touching cfg or state).

Approved deviations from the spec text (K8 amendment 5 sections 3, 5, 6; the
table is k8_gates/sa/README.md):
- Lane-stock ledger identity at t0 (amendment 5 section 3, replaces spec
  5.8-9 T8 / amendment 1 H-2b): sum_l stock_l = N_127 + N_10777 - |A|
  + N_tail129 (5.8-5 init:port packets) + M_other (5.8-6 ready mass of the W
  members projected on links other than 127 and 10777), +-1e-9.
- `stopline_lane_room` resource rows record the port's per-lane allocation
  alloc_p,l (the two ports share room_l), not room_l (N-3).
- Origin tags of the 5.8-6 other-link mass: 32 / 10778 = init:city, every
  other link (129, 10777, ...) = init:unknown (N-11; the spec names none).
- Post-head branch (a) has no receiver-room refusal of its own: it books the
  vehicle like an accepted departure (_post_service) (N-2; branch (d) no
  longer refuses either, below).  Room shortfall (K8 amendment 7 section 1 rule (A),
  replacing amendment 6 section 2, whose negative receiver storage the
  deployed area ledger refuses): only the share that fits the receiver room
  is booked through _post_service; the rest stays a head ready packet of the
  127 lane the vehicle passed (due t0, its origin tag), inside that lane's
  init_excess when the lane exceeds its cap (spec 5.8).  Mass is kept, no
  urban storage goes negative, and the kept share is reported
  (posthead_receiver_shortfall_veh) and enters the lane-stock identity as
  N_shortfall_kept.  With room >= n nothing changes (bit equal).
- Branch (a) departure step (K8 amendment 11, user decision D-K8-6): a
  post-head vehicle crossed the stop line before the decision, so its booked
  share is an accepted departure of the previous step t0 - 1, the clock that
  runtime_setup leaves in the corridor states before SA.initialize
  (native_input_prehead / native_input_routes / route_choice_corridor /
  sc2001_corridor initialize last_step = t0 - 1, and their accept hooks
  require last_step == step).  _post_service runs at t0 - 1, so receiver
  reservations are t0 - 1 + delay (delay >= 1, never before t0).  Kept
  shares stay head ready packets due t0 (amendments 7/8).  Branch (d) books
  no departure (spec 5.8-4(d): its projection cells move unchanged, T9c), so
  no step enters it.
- Branch (d) posthead connector rehome (K8 amendment 8 section 1, review
  N-r6-1): the same rule (A) replaces the "Posthead rehome overfills"
  refusal.  Branch (a) still takes the receiver room first; of the
  connector's in_SC1001_W share a_c only fit = min(a_c, room) moves to the
  receiver (its projection reservation cells scaled by fit / a_c), the rest
  stays a head ready packet (due t0, init:unknown, ahead of every 127 entry)
  of the 127 lane serving the connector's destination (N: lane 3), inside
  that lane's init_excess over its cap; its provenance stays on the
  connector as the member queue.  Reported in posthead_receiver_shortfall_veh
  together with branch (a) (and alone in posthead_rehome_shortfall_veh), so
  N_shortfall_kept covers both.  With room >= a_c nothing changes.
"""
from __future__ import annotations

import bisect
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

from src.models import urban_queue_model as _uqm
from evaluation.controllers.control_area_objective import emit_transfer, get_ledger

ROOT = Path(__file__).resolve().parents[2]

SCHEMA = 'stopline-approach/v2'
EVIDENCE_SCHEMA = 'stopline-approach-evidence/v2'
APPROACH = 'SC1001_EB'
GEOMETRY_SHA12 = '910bc37a8d69'
TINY = 1e-12          # N19 structure threshold on primal values
MASS_TOL = 1e-9       # I3/I4/I7/I10/I11 tolerance
TAG_TOL = 1e-8        # I1/I2 and G_t <= A_t (PRB-br:303-306)
ACCESS_RISK_FROM_HEAD_M = 83.0   # spec 5.1-4: N access zone ends 83 m upstream of the head
LANES = (1, 2, 3)
DESTS = ('E', 'S', 'N')
LANE_DESTS = {1: ('E', 'S'), 2: ('E',), 3: ('N',)}
DEST_LANES = {'E': (1, 2), 'S': (1,), 'N': (3,)}
SOURCES = ('city', 'init:city', 'init:unknown', 'port:OR_D_W', 'port:OR_D_E', 'init:port')
CITY_SOURCES = ('city', 'init:city', 'init:unknown')
PORTS = ('10491', '10481')                       # LOR order; zipper roles below
PORT_OFF_RAMP = {'10491': 'OR_D_W', '10481': 'OR_D_E'}
ZIPPER = {'10491': 'upstream', '10481': 'merge'}
STORAGE_ARMS = ('observed_full', 'geometric')
TUNING_FIELDS = ('schema', 'evidence', 'approaches', 'lane_model', 'storage', 'merge_rule',
                 'city_admission', 'origin_tags')
TUNING_VALUES = {'schema': (SCHEMA,), 'lane_model': ('lane_fifo',), 'storage': STORAGE_ARMS,
                 'merge_rule': ('zipper',), 'city_admission': ('unconditional',),
                 'origin_tags': ('report',)}
INIT_LINK_SOURCE = {'32': 'init:city', '10778': 'init:city'}   # others init:unknown (N-11 deviation)

# Fixed counter keys (primal floats only, N19). STEP_KEYS is the <=20-key
# per-step diagnostic subset (aggregate_urban_diagnostics keeps the last row,
# so cumulative values give the per-decision totals). np_off_ramp_veh is the
# sum of the two port_release keys and stays in diagnostics(state) only.
COUNTER_KEYS = (
    'lane_budget_binding_steps_1', 'lane_budget_binding_steps_2', 'lane_budget_binding_steps_3',
    'lane_full_steps_1', 'lane_full_steps_2', 'lane_full_steps_3',
    'port_blocked_steps_10491', 'port_blocked_steps_10481',
    'port_release_veh_10491', 'port_release_veh_10481', 'port_full_steps_10491',
    'city_over_room_veh', 'hol_unused_room_veh', 'n_access_risk_steps',
    'inbound_unknown_origin_veh', 'tag_residual_max', 'port_joint_room_binding_steps',
    'fold_carry_veh', 'np_boundary_in_veh', 'internal_crossing_veh', 'np_off_ramp_veh',
    'served_city_veh', 'served_init_city_veh', 'served_init_unknown_veh',
    'served_port_OR_D_W_veh', 'served_port_OR_D_E_veh', 'served_init_port_veh',
    'fold_service_residual_events', 'fold_city_share_events', 'merge_tiny_transfer_events',
    'merge_tiny_transfer_veh', 'untagged_port_share_events', 'untagged_port_share_veh',
)
STEP_KEYS = COUNTER_KEYS[:20]
SERVED_KEY = {'city': 'served_city_veh', 'init:city': 'served_init_city_veh',
              'init:unknown': 'served_init_unknown_veh', 'port:OR_D_W': 'served_port_OR_D_W_veh',
              'port:OR_D_E': 'served_port_OR_D_E_veh', 'init:port': 'served_init_port_veh'}


class StoplineConfigError(ValueError):
    pass


class StoplineInitError(ValueError):
    pass


class StoplineInvariantError(ArithmeticError):
    pass


class StoplineRouteError(ValueError):
    """I10 and the T_m route-table premise of an internal crossing (section 5.6-6)."""


# ---------------------------------------------------------------- primitives

def _p(x):
    """Primal value of a traffic number (Dual or float), for structure only."""
    return getattr(x, '_validation_primal', x)


def _packet_key(packet):
    return (packet[0], packet[1])


def view(cfg):
    """The installed approach (key present) or None (key absent)."""
    return getattr(cfg.network, 'stopline_approach', None)


def _state(state):
    return state.stopline_approach_state


def _count(st, key, value):
    st['counters'][key] = st['counters'][key] + value


def _lane_shares(spec, dest, amount):
    """Section 5.1-1: N -> lane 3, S -> lane 1, E -> lane 1 (p1) / lane 2 (rest)."""
    if dest == 'N':
        return ((3, amount),)
    if dest == 'S':
        return ((1, amount),)
    first = amount * spec['p1']
    return ((1, first), (2, amount - first))


def _insert(st, lane, due, source, member, amount):
    """(due, seq) bisect insert (amendment B3). The caller updates stock."""
    seq = st['next_seq']
    st['next_seq'] = seq + 1
    packet = [due, seq, source, member, amount]
    bisect.insort(st['lanes'][lane], packet, key=_packet_key)
    return packet


def _due(step, distance_m, sigma, stock_ahead, speed_kmh):
    """Spec 5.4: t + max(1, ceil(max(0, D - sigma*stock) / (v/3.6))); discrete axis on primals."""
    gap = max(0.0, distance_m - sigma * stock_ahead)
    return step + max(1, int(math.ceil(gap / (speed_kmh / 3.6))))


# ------------------------------------------------------ fold sites (anchors)
# Counters live in the compared state, so they read primal values only: the
# scalar witness and the tangent run must hold identical counters (N19). The
# *_events counters count site visits (K8 amendment 14, D-K8-8): every caller
# enters its site on the primal <= 1e-12 predicate, so a visit is the same in
# both runs, whereas primal != 0 is not (0.0 in the scalar witness, 1e-17 in
# the tangent run by arithmetic order). The *_veh sums add |primal| (<= 1e-12
# per visit; adding a zero is skipped, bit equal), inside the state tolerance.
# The tangent-side event counts of G-EB-11 (d) and N-A4 belong to the gate hooks
# that wrap these four named functions (K8-0e), not to the model state.

def _fold_service_residual(st, lane, member, residual):
    """Rule 2 site 1: a deleted packet's residual (primal <= 1e-12) joins carry."""
    st['carry'][lane][member] = st['carry'][lane][member] + residual
    _count(st, 'fold_service_residual_events', 1.0)
    if _p(residual) != 0.0:
        _count(st, 'fold_carry_veh', abs(_p(residual)))


def _fold_city_share(st, lane, member, amount):
    """Rule 2 site 2: a primal <= 1e-12 city/initial ready share joins carry."""
    st['carry'][lane][member] = st['carry'][lane][member] + amount
    st['stock'][lane] = st['stock'][lane] + amount
    _count(st, 'fold_city_share_events', 1.0)
    if _p(amount) != 0.0:
        _count(st, 'fold_carry_veh', abs(_p(amount)))


def _merge_tiny_transfer(st, kept, tiny):
    """Rule 2 site 3: a primal <= 1e-12 transfer share merges into its sibling."""
    _count(st, 'merge_tiny_transfer_events', 1.0)
    if _p(tiny) != 0.0:
        _count(st, 'merge_tiny_transfer_veh', abs(_p(tiny)))
    return kept + tiny


def _skip_tiny_port_share(st, lane, member, amount):
    """N-A4 site 4: no packet for a primal <= 1e-12 moving port share.

    Its mass and tangent stay in the paired in_SC1001_W reservation and
    arrive untagged (gate beta split): redistributed, never discarded.
    """
    _count(st, 'untagged_port_share_events', 1.0)
    if _p(amount) != 0.0:
        _count(st, 'untagged_port_share_veh', abs(_p(amount)))


# --------------------------------------------------------------- configure

def _require(condition, message, error=StoplineConfigError):
    if not condition:
        raise error(message)


def _finite_positive(value, name):
    _require(type(value) in (int, float) and not isinstance(value, bool) and math.isfinite(value)
             and value > 0, name + ' must be a finite positive number')
    return float(value)


def check_section(section):
    """Tuning key `urban.stopline_approach`: eight required fields, no defaults."""
    _require(isinstance(section, dict), 'urban.stopline_approach must be an object')
    _require(set(section) == set(TUNING_FIELDS),
             'urban.stopline_approach fields must be exactly ' + ', '.join(TUNING_FIELDS))
    for key, allowed in TUNING_VALUES.items():
        _require(section[key] in allowed, f'urban.stopline_approach.{key} must be one of {allowed}')
    _require(section['approaches'] == [APPROACH], 'urban.stopline_approach.approaches must be ["SC1001_EB"]')
    pin = section['evidence']
    _require(isinstance(pin, dict) and set(pin) == {'path', 'sha256'},
             'urban.stopline_approach.evidence must be {path, sha256}')
    _require(isinstance(pin['path'], str) and pin['path'] and not Path(pin['path']).is_absolute(),
             'stopline evidence path must be repository-relative')
    digest = pin['sha256']
    _require(isinstance(digest, str) and len(digest) == 64 and all(c in '0123456789abcdef' for c in digest),
             'stopline evidence sha256 must be 64 lowercase hex digits')


def load_evidence(pin):
    path = (ROOT / pin['path']).resolve(strict=True)
    _require(path.is_relative_to(ROOT.resolve()), 'stopline evidence resolves outside the repository')
    content = path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    _require(digest == pin['sha256'], 'stopline evidence sha256 mismatch: ' + str(path))
    return json.loads(content.decode('utf-8')), digest


def _prior(rows, allowed, name):
    _require(isinstance(rows, dict) and set(rows) == {'1', '2', '3'}, name + ' needs lanes 1-3')
    out = {}
    for lane in LANES:
        row = rows[str(lane)]
        _require(isinstance(row, dict) and row and set(row) <= set(allowed[lane]),
                 f'{name} lane {lane} has destinations outside {allowed[lane]}')
        values = {d: float(row[d]) for d in DESTS if d in row}
        _require(all(math.isfinite(v) and v >= 0 for v in values.values())
                 and abs(math.fsum(values.values()) - 1.0) <= 1e-9, f'{name} lane {lane} must sum to 1')
        out[lane] = values
    return out


def build_view(cfg, section, document, evidence_sha256):
    """Validated approach view from the evidence document (spec 3.2 + amendment 3.2)."""
    check_section(section)
    net = cfg.network
    _require(isinstance(document, dict) and document.get('schema') == EVIDENCE_SCHEMA,
             'stopline evidence schema must be ' + EVIDENCE_SCHEMA)
    geometry = ((document.get('inputs') or {}).get('g2_inpx') or {}).get('extract_sha12')
    _require(geometry == GEOMETRY_SHA12, 'stopline evidence geometry sha12 differs from ' + GEOMETRY_SHA12)
    approaches = document.get('approaches')
    _require(isinstance(approaches, dict) and set(approaches) == {APPROACH},
             'stopline evidence must describe exactly SC1001_EB')
    ev = approaches[APPROACH]
    _require(ev.get('signal') == 'SC1001' and ev.get('stopline_link') == '127' and ev.get('receiver') == 'in_SC1001_W',
             'stopline evidence approach identity changed')
    receiver = ev['receiver']
    members = ev.get('members')
    _require(isinstance(members, dict) and set(members) == set(DESTS)
             and len(set(members.values())) == 3 and all(isinstance(v, str) for v in members.values()),
             'stopline evidence members must be E/S/N movement names')
    jam = _finite_positive(ev.get('jam_spacing_m'), 'jam_spacing_m')
    _require(jam == net.urban_avg_vehicle_length_m,
             'stopline jam spacing differs from the urban vehicle spacing (LPR:296-298)')
    rows = ev.get('lanes')
    _require(isinstance(rows, dict) and set(rows) == {'1', '2', '3'}, 'stopline evidence needs lanes 1-3')
    arm = section['storage']
    lanes = {}
    for lane in LANES:
        row = rows[str(lane)]
        _require(row.get('members') == list(LANE_DESTS[lane]), f'lane {lane} members must be {LANE_DESTS[lane]}')
        head = _finite_positive(row.get('head_pos_m'), f'lane {lane} head_pos_m')
        s_lane = _finite_positive(row.get('s_veh_h_lane'), f'lane {lane} s_veh_h_lane')
        _require(1500.0 <= s_lane <= 2200.0, f'lane {lane} saturation flow outside [1500, 2200]')
        storage = row.get('storage_veh')
        _require(isinstance(storage, dict) and set(storage) == set(STORAGE_ARMS), f'lane {lane} storage arms')
        geometric = _finite_positive(storage['geometric'], f'lane {lane} geometric storage')
        _require(abs(geometric - head / jam) <= 1e-9, f'lane {lane} geometric storage != head/jam')
        capacity = _finite_positive(storage[arm], f'lane {lane} {arm} storage')
        phase = row.get('phase')
        _require(isinstance(phase, str) and phase.startswith('SC1001_'), f'lane {lane} phase')
        lanes[lane] = {'dests': LANE_DESTS[lane], 'members': tuple(members[d] for d in LANE_DESTS[lane]),
                       'phase_member': members[LANE_DESTS[lane][0]], 'phase': phase, 's_veh_h': s_lane,
                       'head_pos_m': head, 'S': capacity, 'sigma': head / capacity}
    p1 = _finite_positive(ev.get('p_lane1_given_E'), 'p_lane1_given_E')
    _require(p1 < 1.0, 'p_lane1_given_E must lie in (0, 1)')
    upstream = _prior(ev.get('upstream_lane_prior'), {l: DESTS for l in LANES}, 'upstream_lane_prior')
    posthead = _prior(ev.get('posthead_lane_prior'), {l: DESTS for l in LANES}, 'posthead_lane_prior')
    connectors = ev.get('posthead_connectors')
    _require(isinstance(connectors, dict) and connectors, 'posthead_connectors required')
    for key, row in connectors.items():
        _require(isinstance(row, dict) and set(row) == {'from_lanes', 'receiver'}
                 and isinstance(row['receiver'], str) and row['from_lanes']
                 and set(row['from_lanes']) <= set(LANES), 'posthead connector ' + key)
    rehome = ev.get('posthead_rehome')
    _require(isinstance(rehome, dict) and set(rehome) <= set(connectors)
             and all(connectors[c]['receiver'] == r for c, r in rehome.items()),
             'posthead_rehome must be connectors mapped to their receivers')
    pre = ev.get('pre_stopline_links')
    _require(isinstance(pre, list) and len(pre) >= 3 and pre[-1] == '127' and all(isinstance(x, str) for x in pre),
             'pre_stopline_links must end at the stopline link 127')
    ports_ev = ev.get('ports')
    _require(isinstance(ports_ev, dict) and set(ports_ev) == set(PORTS), 'ports must be 10491 and 10481')
    ports = {}
    for off in PORTS:
        row = ports_ev[off]
        _require(row.get('off_ramp') == PORT_OFF_RAMP[off], f'port {off} off-ramp')
        landing = row.get('landing')
        _require(isinstance(landing, list) and len(landing) == 2 and isinstance(landing[0], str),
                 f'port {off} landing')
        distance = row.get('distance_m')
        _require(isinstance(distance, dict) and set(distance) == {'1', '2', '3'}, f'port {off} distance_m')
        ports[off] = {'off_ramp': PORT_OFF_RAMP[off], 'source': 'port:' + PORT_OFF_RAMP[off],
                      'zipper': ZIPPER[off], 'landing_link': landing[0],
                      'landing_pos_m': _finite_positive(landing[1], f'port {off} landing position'),
                      'distance_m': {l: float(distance[str(l)]) for l in LANES}}
        _require(all(math.isfinite(d) and d >= 0 for d in ports[off]['distance_m'].values()),
                 f'port {off} distances must be finite and nonnegative')
    _require(ports['10481']['landing_link'] == '127' and ports['10491']['landing_link'] == pre[-3],
             'port landings must be the stopline link (10481) and the tail link (10491)')
    connector_link = pre[-2]
    link10777 = _finite_positive(ev.get('link10777_m'), 'link10777_m')
    exits = {lane: ports['10491']['landing_pos_m'] + ports['10491']['distance_m'][lane] - lanes[lane]['head_pos_m']
             for lane in LANES}
    _require(max(exits.values()) - min(exits.values()) <= 1e-6, 'port 10491 distances disagree on the 129 exit')
    route_exit = ev.get('route_exit')
    _require(isinstance(route_exit, dict) and route_exit and set(route_exit.values()) <= set(DESTS)
             and len({k.split(':')[0] for k in route_exit}) == 1, 'route_exit must map one decision to E/S/N')
    origins = ev.get('init_origin_routes')
    _require(isinstance(origins, dict) and set(origins.values()) <= {'port', 'city', 'unknown'},
             'init_origin_routes values must be port/city/unknown')
    progress = ev.get('port_progress_route')
    _require(isinstance(progress, dict) and set(progress.values()) <= set(PORT_OFF_RAMP.values()),
             'port_progress_route values must be off-ramps')
    spec = {
        'schema': SCHEMA, 'evidence_sha256': evidence_sha256, 'storage_arm': arm, 'approach': APPROACH,
        'receiver': receiver, 'stopline_link': '127', 'connector_link': connector_link, 'tail_link': pre[-3],
        'members': tuple(members[d] for d in DESTS), 'member_of': dict(members),
        'dest_of': {name: d for d, name in members.items()}, 'lanes': lanes, 'p1': p1,
        'upstream_lane_prior': upstream, 'posthead_lane_prior': posthead,
        'posthead_connectors': {k: {'from_lanes': tuple(v['from_lanes']), 'receiver': v['receiver']}
                                for k, v in connectors.items()},
        'posthead_rehome': dict(rehome), 'pre_stopline_links': tuple(pre), 'ports': ports,
        'd1117_m': _finite_positive(ev.get('d1117_m'), 'd1117_m'),
        'tail129_from_m': _finite_positive(ev.get('tail129_from_m'), 'tail129_from_m'),
        'link10777_m': link10777, 'exit129_m': exits[1], 'route_exit': dict(route_exit),
        'route_decision': next(iter(route_exit)).split(':')[0], 'init_origin_routes': dict(origins),
        'port_progress_route': dict(progress),
        'speed_floor_kmh': _finite_positive(ev.get('speed_floor_kmh'), 'speed_floor_kmh'),
        'jam_spacing_m': jam, 'zipper': dict(ZIPPER),
    }
    _check_members(cfg, spec)
    return spec


def _check_members(cfg, spec):
    movements = cfg.network.urban_movements
    receivers = {}
    for dest, name in spec['member_of'].items():
        row = movements.get(name)
        _require(row is not None, 'stopline member is not a model movement: ' + name)
        _require(row.get('kind') == 'boundary_in', 'stopline member kind must be boundary_in: ' + name)
        _require(row.get('origin') == spec['receiver'], 'stopline member origin must be in_SC1001_W: ' + name)
        _require(not row.get('ramp'), 'stopline member cannot be a ramp movement: ' + name)
        for lane in DEST_LANES[dest]:
            _require(row.get('phase') == spec['lanes'][lane]['phase'],
                     f'stopline member phase differs from lane {lane} evidence: ' + name)
        target = row.get('receiving_link')
        hits = [c for c, pc in spec['posthead_connectors'].items() if pc['receiver'] == target]
        _require(len(hits) == 1 and spec['posthead_connectors'][hits[0]]['from_lanes'] == DEST_LANES[dest],
                 'stopline member receiver differs from its posthead connector: ' + name)
        receivers[name] = target
    spec['receiver_of'] = receivers


def configure(cfg, tuning, state_json):
    """RS hook #2 (after LSS/HSR): install cfg.network.stopline_approach, or {} when absent."""
    section = ((tuning or {}).get('urban') or {}).get('stopline_approach')
    if section is None:
        return {}
    check_section(section)
    _require(bool(((tuning or {}).get('freeway') or {}).get('lane_plant')),
             'urban.stopline_approach requires freeway.lane_plant')
    _require((((tuning or {}).get('urban') or {}).get('queue') or {}).get('contiguous') is True,
             'urban.stopline_approach requires urban.queue.contiguous = true')
    _require(view(cfg) is None, 'stopline approach is configured once per decision')
    document, digest = load_evidence(section['evidence'])
    spec = build_view(cfg, section, document, digest)
    cfg.network.stopline_approach = spec
    return {'stopline_approach_schema': SCHEMA, 'stopline_approach_storage_arm': spec['storage_arm'],
            'stopline_approach_evidence_sha256': digest,
            'stopline_approach_storage_veh': {str(l): spec['lanes'][l]['S'] for l in LANES}}


# ----------------------------------------------------------- install check

def _mentions(value, name):
    if isinstance(value, str):
        return value == name
    if isinstance(value, dict):
        return any(_mentions(k, name) or _mentions(v, name) for k, v in value.items())
    if isinstance(value, (list, tuple, set, frozenset)):
        return any(_mentions(v, name) for v in value)
    return False


def _seed_rows(seed_split):
    return {str(k): v for k, v in seed_split.items() if k != 'unattributed'}


def _seed_row(seed_split, link, storage):
    """K8-4 declared row {moving, stopped, due_moving_step, due_stopped_step} or None."""
    row = (_seed_rows(seed_split).get(str(link)) or {}).get(storage)
    if row is None:
        return None
    moving, stopped = float(row['moving']), float(row['stopped'])
    due_m, due_s = row['due_moving_step'], row['due_stopped_step']
    if (not math.isfinite(moving) or not math.isfinite(stopped) or moving < 0 or stopped < 0
            or type(due_m) is not int or type(due_s) is not int):
        raise StoplineInitError(f'Invalid storage seed split row {link}/{storage}')
    return moving, stopped, due_m, due_s


def _unattributed(seed_split, storage):
    row = (seed_split.get('unattributed') or {}).get(storage, 0.0)
    if isinstance(row, dict):
        return float(row.get('moving', 0.0)) + float(row.get('stopped', 0.0))
    return float(row)


def _unattributed_abs(seed_split, storage):
    """|moving| + |stopped| of the K8-4 unattributed row (ce8fe80 `storage_seed_split_unattributed_veh` form), so a
    moving/stopped pair of opposite signs is not read as no unattributed seed by the install refusal."""
    row = (seed_split.get('unattributed') or {}).get(storage, 0.0)
    if isinstance(row, dict):
        return abs(float(row.get('moving', 0.0))) + abs(float(row.get('stopped', 0.0)))
    return abs(float(row))


def seed_split_of(state):
    """K8-4 (ce8fe80) diagnostic `projection_diagnostics.storage_seed_split_by_link` written by
    seed_urban_arrival_buffer: {link: {storage: {moving, stopped, due_moving_step, due_stopped_step (int)}},
    'unattributed': {storage: {moving, stopped}}}; None when the projection seeded nothing (seed off)."""
    summary = getattr(state, 'local_observation_summary', None) or {}
    return (summary.get('projection_diagnostics') or {}).get('storage_seed_split_by_link')


def install_check(state, cfg, detector_mapping, seed_split, *, tuning=None):
    """Spec 6.3 + amendment 6.3 refusal list; metadata on success.

    `tuning` (the decision's tuning, passed by initialize) adds the N-8 refusal:
    with urban.queue.origin_binding on, a queued 129 tail vehicle would enter
    both the 5.8-6 ready mass and the 5.8-5 moving tail (double count).
    """
    spec = view(cfg)
    _require(spec is not None, 'stopline approach key present but cfg.network.stopline_approach missing',
             StoplineInitError)
    net = cfg.network
    err = StoplineInitError
    queue = (((tuning or {}).get('urban') or {}).get('queue') or {})
    _require(not queue.get('origin_binding'),
             'urban.queue.origin_binding is on: the 129 tail would be counted twice (K8 amendment 5 N-8)', err)
    lor = getattr(state, 'lane_offramp_runtime', None)
    _require(lor is not None, 'stopline approach requires the lane off-ramp runtime', err)
    for off in PORTS:
        row = lor.descriptions.get(off)
        port = spec['ports'][off]
        _require(row is not None and row.get('direct') is False and not row.get('local_upstream')
                 and row.get('group') == port['off_ramp'] and str(row.get('connector')) == off
                 and row.get('storage') == net.off_ramp_storage_link.get(port['off_ramp'])
                 and str(row.get('to_link')) == port['landing_link']
                 and abs(float(row.get('to_pos_m')) - port['landing_pos_m']) <= 1e-6
                 and off in lor.ports, f'off-ramp row {off} is not the signal branch of {port["off_ramp"]}', err)
    from evaluation.controllers.lane_urban_runtime import is_local_movement
    pool = getattr(net, 'local_service_pool', None) or {}
    heads = getattr(net, 'head_service_resources', None) or {}
    head_members = {m for row in (heads.get('extra_pool_groups') or {}).values() for m in row.get('members', ())}
    for name in spec['members']:
        row = net.urban_movements[name]
        _require(name not in (pool.get('group_of') or {}) and name not in head_members,
                 'stopline member is owned by a shared service pool: ' + name, err)
        _require(not _mentions(getattr(net, 'route_choice_corridor', None), name)
                 and not _mentions(getattr(net, 'native_internal_inputs', None), name),
                 'stopline member is owned by a route corridor or native input: ' + name, err)
        _require(not is_local_movement(state, name), 'stopline member is a physical local movement: ' + name, err)
        _require(row.get('kind') == 'boundary_in' and not row.get('ramp')
                 and row.get('receiving_link') == spec['receiver_of'][name]
                 and row.get('receiving_link') in state.urban_link_storage,
                 'stopline member changed after configure: ' + name, err)
    receiver = spec['receiver']
    routing = _uqm.approach_routing(cfg)
    _require(receiver in routing and set(spec['members']) <= {m for m, _ in routing[receiver]},
             'in_SC1001_W must route the three W members', err)
    choice = getattr(net, 'route_choice_corridor', None) or {}
    corridor = getattr(net, 'sc2001_corridor', None) or {}
    local = getattr(state, 'lane_urban_runtime', None)
    _require(receiver not in set(choice.get('capacity_veh', {}) or {}) and corridor.get('storage') != receiver
             and (local is None or local.origin != receiver),
             'in_SC1001_W arrivals are owned by another runtime branch', err)
    city = (getattr(net, 'physical_ramp_branches', None) or {}).get('shared_city_arrival') or {}
    _require(city.get('receiver') != receiver, 'shared city arrival receiver is in_SC1001_W (UFA:363)', err)
    _runtime_guard(cfg, spec)
    origins = (detector_mapping or {}).get('link_to_origins') or {}
    rehome = {c for c, pc in spec['posthead_connectors'].items() if receiver in (origins.get(c) or [])}
    _require(rehome == set(spec['posthead_rehome']),
             f'posthead connectors with in_SC1001_W origin {sorted(rehome)} != posthead_rehome', err)
    for c in rehome:
        rest = [o for o in origins[c] if o != receiver]
        _require(rest == [spec['posthead_rehome'][c]], f'posthead connector {c} other origins {rest}', err)
    origin_links = sorted(k for k, v in origins.items() if receiver in (v or []))
    allowed = set(spec['pre_stopline_links']) | set(PORTS) | set(spec['posthead_rehome'])
    _require(set(origin_links) <= allowed, f'in_SC1001_W origin links outside the approach: '
             f'{sorted(set(origin_links) - allowed)}', err)
    # The stopline link and its 1 m entry connector project to the gate store only (B1 10777).
    for link in (spec['stopline_link'], spec['connector_link']):
        _require(list(origins.get(link) or []) == [receiver], f'link {link} origins must be exactly [{receiver}]', err)
    _require(not ((detector_mapping or {}).get('link_to_movements') or {}).get(spec['connector_link']),
             'link ' + spec['connector_link'] + ' must not project to movements', err)
    # Joint port cap A (N16) is shared by the two approach ports only.
    for off, row in lor.descriptions.items():
        if off in PORTS:
            continue
        targets = {row.get('target')}
        if not row.get('direct') and not row.get('local_upstream'):
            targets |= {net.urban_movements[m].get('receiving_link')
                        for m in net.off_ramp_to_movement.get(row.get('group'), ())}
        _require(receiver not in targets, f'off-ramp row {off} also releases into {receiver}', err)
    _require(seed_split is not None, 'storage_seed_split_by_link (K8-4) is required', err)
    _require(_unattributed_abs(seed_split, receiver) <= MASS_TOL, 'in_SC1001_W has unattributed seeds', err)
    # B1/B7: every in_SC1001_W residual that SA moves (127, 10777, posthead connectors) has its exact seed row.
    provenance = ((getattr(state, 'local_observation_summary', None) or {}).get('projection_diagnostics')
                  or {}).get('physical_stock_assignment_by_link') or {}
    seeded = []
    for link in (spec['stopline_link'], spec['connector_link'], *sorted(spec['posthead_rehome'])):
        residual = (provenance.get(link) or {}).get('storage:' + receiver, 0.0)
        if residual > MASS_TOL:
            _require(_seed_row(seed_split, link, receiver) is not None,
                     f'link {link} holds an in_SC1001_W residual {residual} without its K8-4 seed row', err)
            seeded.append(link)
    return {'stopline_approach_install_check': {
        'members': list(spec['members']), 'posthead_rehome': sorted(rehome), 'origin_links': origin_links,
        'seeded_links': seeded, 'evidence_sha256': spec['evidence_sha256'], 'storage_arm': spec['storage_arm'],
        'passed': True}}


def _runtime_guard(cfg, spec):
    """Known W_out legsplit is configured after RS:253; re-checked at each rollout start."""
    legsplit = getattr(cfg.network, 'known_legsplit_routes', None) or {}
    storage = legsplit.get('storage')
    if storage is not None and (storage == spec['receiver'] or storage in spec['receiver_of'].values()):
        raise StoplineInitError('known legsplit storage overlaps a stopline receiver: ' + str(storage))


def _bind_ports(state, cfg, spec):
    """Port streams from the runtime beta of the eight off-ramp movements (spec 1.5)."""
    net = cfg.network
    lor = state.lane_offramp_runtime
    offramp_movements = []
    for off in PORTS:
        port = spec['ports'][off]
        row = lor.descriptions[off]
        names = list(net.off_ramp_to_movement[port['off_ramp']])
        offramp_movements.extend(names)
        beta, exits = {}, {}
        for name in names:
            mv = net.urban_movements[name]
            share = float(mv.get('beta', 0.0))
            dest = next((d for d, member in spec['member_of'].items()
                         if spec['receiver_of'][member] == mv.get('receiving_link')), None)
            if dest is None:
                _require(share == 0.0, 'off-ramp beta leaves the three stopline receivers: ' + name,
                         StoplineInitError)
                continue
            _require(dest not in exits, 'two off-ramp movements share a stopline receiver: ' + name,
                     StoplineInitError)
            beta[dest], exits[dest] = share, name
        _require(set(exits) == set(DESTS) and math.fsum(beta.values()) > 0,
                 'off-ramp port lacks a stopline destination: ' + off, StoplineInitError)
        total = math.fsum(beta.values())
        tilde = {d: beta[d] / total for d in DESTS}
        p1 = spec['p1']
        port.update({'lanes': row['lanes'], 'storage': row['storage'], 'connector': str(row['connector']),
                     'to_link': str(row['to_link']), 'beta_tilde': tilde, 'exit_movement': exits,
                     'weights': {1: tilde['E'] * p1 + tilde['S'], 2: tilde['E'] * (1.0 - p1), 3: tilde['N']}})
    spec['offramp_movements'] = tuple(offramp_movements)


# ------------------------------------------------------------- initialize

def _new_state(spec):
    return {'lanes': {l: [] for l in LANES}, 'stock': {l: 0.0 for l in LANES},
            'carry': {l: {spec['member_of'][d]: 0.0 for d in LANE_DESTS[l]} for l in LANES},
            'tags': {}, 'next_seq': 0, 'plan': {}, 'speed_kmh': spec['speed_floor_kmh'],
            'counters': {k: 0.0 for k in COUNTER_KEYS}, 'init_excess': {l: 0.0 for l in LANES},
            'city_over': {l: 0.0 for l in LANES}, 'last_step': None}


def _route_key(row):
    if row is None or row.get('route_decision_no') is None:
        return None
    return f"{row['route_decision_no']}:{row['route_no']}"


def _origin_source(spec, route, report):
    kinds = spec['init_origin_routes']
    if route is not None:
        if route in kinds:
            return 'init:' + kinds[route]
        if route.split(':')[0] in kinds:
            return 'init:' + kinds[route.split(':')[0]]
    report['unrouted_veh'] += 1.0
    return 'init:unknown'


def _destinations(spec, route, prior):
    if route is not None and route.split(':')[0] == spec['route_decision']:
        if route not in spec['route_exit']:
            raise StoplineInitError('Unknown stopline route exit: ' + route)
        return [(spec['route_exit'][route], 1.0)]
    return [(d, w) for d, w in prior.items() if w > 0.0]


def _take_seed(buffer, key, due, amount, report):
    """Exact seed removal from one reservation cell; [-1e-9, 0) becomes 0 (counted once per pair)."""
    if amount <= 0.0:
        return
    table = buffer.setdefault(key, {})
    value = table.get(due, 0.0) - amount
    if value < -MASS_TOL:
        raise StoplineInitError(f'Seed subtraction overdraws {key}@{due}: {value}')
    if value < 0.0:
        if report is not None:
            report['seed_residual_veh'] += -value
        value = 0.0
    table[due] = value


def _take_seed_pair(state, key, due, amount, report):
    _take_seed(state.urban_arrival_buffer, key, due, amount, report)
    _take_seed(state.urban_storage_release_buffer, key, due, amount, None)


def initialize(state, cfg, state_json, detector_mapping, seed_split, *, tuning=None, queue_by_lane=None):
    """RS hook #3 (after lane_plant_runtime.initialize, before area configure); {} when absent.

    Spec 5.8 as amended: install check, LOR approach rows, 127/10777 provenance
    reversal, vehicle placement (a) post-head via _post_service at t0 - 1 (K8 amendment 11), (b) ready,
    (c) moving, (d) posthead rehome, 129 tail, other-link ready mass, exact seed
    subtraction (K8-4 interface), speed, invariants, provenance audit.
    """
    spec = view(cfg)
    if spec is None:
        if (((tuning or {}).get('urban') or {}).get('stopline_approach')) is not None:
            raise StoplineInitError('stopline approach key present but not configured')
        return {}
    metadata = install_check(state, cfg, detector_mapping, seed_split, tuning=tuning)
    _bind_ports(state, cfg, spec)
    for off in PORTS:
        state.lane_offramp_runtime.descriptions[off]['approach'] = APPROACH
    from evaluation.controllers.projection_support import complete_records
    from evaluation.controllers.vehicle_routes import complete_vehicle_routes
    from evaluation.controllers.urban_flow_accounting import _post_service
    from evaluation.controllers.observation_projection import audit_projection_provenance
    if queue_by_lane is None:
        from evaluation.controllers.vissim_stackelberg_adapter import _contiguous_stopline_queue_by_lane
        queue_by_lane = _contiguous_stopline_queue_by_lane(state_json)
    net = cfg.network
    receiver = spec['receiver']
    L127, L10777, L129 = spec['stopline_link'], spec['connector_link'], spec['tail_link']
    t0 = _uqm._urban_step_index(state, cfg)
    # K8 amendment 11 (D-K8-6): branch (a) books its post-head vehicles as departures of the previous step, the clock
    # the corridor states hold at initialization (last_step = t0 - 1); receiver reservations follow from t0 - 1.
    t_depart = t0 - 1
    routing = _uqm.approach_routing(cfg)
    records = complete_records(state_json)
    routes = complete_vehicle_routes(state_json, required=True)
    provenance = state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    report = defaultdict(float)
    lanes = spec['lanes']
    st = _new_state(spec)
    seeds = _seed_rows(seed_split)

    # I11 premise: the in_SC1001_W reservations are exactly the K8-4 seed split.
    seed_total = math.fsum(r[receiver]['moving'] + r[receiver]['stopped'] for r in seeds.values() if receiver in r)
    arrival_before = math.fsum(state.urban_arrival_buffer.get(receiver, {}).values())
    if abs(arrival_before - seed_total - _unattributed(seed_split, receiver)) > MASS_TOL:
        raise StoplineInitError(f'in_SC1001_W reservations {arrival_before} differ from the seed split {seed_total}')

    by_link = defaultdict(list)
    for rec in records:
        by_link[str(rec['link_no'])].append(rec)
    # 3. Reverse the 1/14 projection of 127 and the residual of 10777.
    counts = {link: float(len(by_link[link])) for link in (L127, L10777)}
    for link in (L127, L10777):
        row = provenance.get(link, {})
        if abs(math.fsum(row.values()) - counts[link]) > 1e-7:
            raise StoplineInitError('Provenance differs from the observed vehicles of link ' + link)
    for key, n in provenance.get(L127, {}).items():
        kind, name = key.split(':', 1)
        if kind == 'movement':
            state.urban_movement_queue[name] -= n
        elif key == 'storage:' + receiver:
            state.urban_link_storage[receiver] += n
        else:
            raise StoplineInitError('Link 127 holds another stock: ' + key)
    kept10777 = {}
    for key, n in provenance.get(L10777, {}).items():
        if key == 'storage:' + receiver:
            state.urban_link_storage[receiver] += n
        elif key.startswith('movement:') and key[len('movement:'):] in spec['members']:
            kept10777[key] = n
        else:
            raise StoplineInitError('Link 10777 holds another stock: ' + key)
    for name in spec['offramp_movements']:
        q = state.urban_movement_queue.get(name, 0.0)
        if abs(q) > MASS_TOL:
            raise StoplineInitError(f'Off-ramp movement queue {name} is not empty after the 127 reversal: {q}')
        report['offramp_queue_zeroed_veh'] += abs(q)
        state.urban_movement_queue[name] = 0.0
    moving_speeds = [float(r['speed_kph']) for link in (L127, L129) for r in by_link[link]
                     if float(r['speed_kph']) >= 1.0]
    speed = max(math.fsum(moving_speeds) / len(moving_speeds) if moving_speeds else 0.0, spec['speed_floor_kmh'])
    st['speed_kmh'] = speed

    new127 = defaultdict(float)
    new10777 = dict(kept10777)
    entries = {l: [] for l in LANES}

    def place(dest, amount, l_obs, **entry):
        if l_obs is not None and l_obs in DEST_LANES[dest]:
            shares = ((l_obs, amount),)
        else:
            shares = _lane_shares(spec, dest, amount)
            if l_obs is not None:
                report['lane_reassigned_veh'] += amount
        for lane, share in shares:
            # A post-head share kept on 127 (amendment 7 section 1) sorts ahead of every pre-head entry, the most
            # downstream vehicle first; every other entry keeps its distance to the head.
            distance = (-entry['past_head_m'] if 'past_head_m' in entry
                        else max(0.0, entry['offset'] + lanes[lane]['head_pos_m']))
            entries[lane].append(dict(entry, lane=lane, dest=dest, member=spec['member_of'][dest], amount=share,
                                      distance=distance))

    # 4. Vehicles of 127: (a) post-head, (b) ready, (c) moving.
    prehead = []
    for rec in sorted(by_link[L127], key=lambda r: (-float(r['position_m']), r['veh_no'])):
        l_obs = int(rec['lane_no'])
        if l_obs not in LANES:
            raise StoplineInitError('Link 127 vehicle on an undeclared lane')
        pos, kph = float(rec['position_m']), float(rec['speed_kph'])
        route = _route_key(routes.get(rec['veh_no']))
        if pos >= lanes[l_obs]['head_pos_m']:
            source = None
            for dest, w in _destinations(spec, route, spec['posthead_lane_prior'][l_obs]):
                member = spec['member_of'][dest]
                target = spec['receiver_of'][member]
                # Spec 5.8-4(a): booked like an accepted departure of step t0 - 1 (K8 amendment 11, the pre-head
                # clock), no refusal here (N-2; amendment 8 section 1: nor in branch (d)). Amendment 7 section 1
                # rule (A): only the share that fits the receiver room goes to the receiver (_post_service, never
                # below 0); the rest stays a head ready packet of the 127 lane this vehicle passed (due t0, its origin
                # tag; the lane's init_excess below covers a lane over its cap) and is reported. Room >= w: fit is w,
                # nothing else runs.
                fit = min(w, max(0.0, state.urban_link_storage[target]))
                kept = w - fit
                if fit > 0.0:
                    _post_service(state, cfg, member, fit, t_depart, routing, str(target))
                    new127['storage:' + target] += fit
                if kept > 0.0:
                    if source is None:
                        source = _origin_source(spec, route, report)
                    report['posthead_receiver_shortfall_veh'] += kept
                    place(dest, kept, l_obs, offset=-pos, kind='ready', source=source, speed=kph, link=L127,
                          veh=rec['veh_no'], past_head_m=pos - lanes[l_obs]['head_pos_m'])
                report['posthead_veh'] += w
        else:
            prehead.append((rec, l_obs, pos, kph, route))
    ready_ids = set()
    for lane in LANES:
        q_lane = float(queue_by_lane.get((L127, str(lane)), 0.0))
        n_q = int(round(q_lane))
        if abs(q_lane - n_q) > 1e-9:
            raise StoplineInitError('Contiguous stopline queue is not a vehicle count')
        stopped = [x for x in prehead if x[1] == lane and x[3] < 1.0]
        chosen = stopped[:n_q]
        report['queue_shortfall_veh'] += n_q - len(chosen)
        ready_ids.update(x[0]['veh_no'] for x in chosen)
    for rec, l_obs, pos, kph, route in prehead:
        source = _origin_source(spec, route, report)
        kind = 'ready' if rec['veh_no'] in ready_ids else 'moving'
        for dest, w in _destinations(spec, route, spec['upstream_lane_prior'][l_obs]):
            place(dest, w, l_obs, offset=-pos, kind=kind, source=source, speed=kph, link=L127, veh=rec['veh_no'])
    # 10777 (1 m connector onto 127): its residual share moves vehicle by vehicle;
    # a queued (movement) share stays and becomes ready packets in step 6.
    mass10777 = provenance.get(L10777, {}).get('storage:' + receiver, 0.0) / max(counts[L10777], 1.0)
    for rec in sorted(by_link[L10777], key=lambda r: (-float(r['position_m']), r['veh_no'])):
        pos, kph = float(rec['position_m']), float(rec['speed_kph'])
        route = _route_key(routes.get(rec['veh_no']))
        source = _origin_source(spec, route, report)
        l_obs = int(rec['lane_no'])
        if l_obs not in LANES:
            raise StoplineInitError('Link 10777 vehicle on an undeclared lane')
        for dest, w in _destinations(spec, route, spec['upstream_lane_prior'][l_obs]):
            place(dest, w * mass10777, l_obs, offset=spec['link10777_m'] - pos, kind='moving', source=source,
                  speed=kph, link=L10777, veh=rec['veh_no'])
    # 5. 129 tail vehicles still travelling from the OR_D_W landing.
    tail = 0.0
    for rec in by_link[L129]:
        route = _route_key(routes.get(rec['veh_no']))
        pos = float(rec['position_m'])
        if pos < spec['tail129_from_m'] or route not in spec['port_progress_route']:
            continue
        off = next(o for o in PORTS if spec['ports'][o]['off_ramp'] == spec['port_progress_route'][route])
        tilde = spec['ports'][off]['beta_tilde']
        tail += 1.0
        for dest in DESTS:
            if tilde[dest] > 0.0:
                place(dest, tilde[dest], None, offset=spec['exit129_m'] - pos + spec['link10777_m'], kind='moving',
                      source='init:port', speed=float(rec['speed_kph']), link=L129, veh=rec['veh_no'])

    # 7. Exact removal of the seeds that the moved vehicles replace (B7).
    for link in (L127, L10777):
        row = _seed_row(seed_split, link, receiver)
        if row is not None:
            _take_seed_pair(state, receiver, row[2], row[0], report)
            _take_seed_pair(state, receiver, row[3], row[1], report)
    removed = math.fsum(sum(r[:2]) for r in (_seed_row(seed_split, k, receiver) for k in (L127, L10777)) if r)
    tail_sub = 0.0
    if tail > 0.0:
        row = _seed_row(seed_split, L129, receiver)
        if row is None or row[0] + row[1] < tail - MASS_TOL:
            raise StoplineInitError('129 tail exceeds the seeded 129 residual')
        sub_m = tail * row[0] / (row[0] + row[1])
        _take_seed_pair(state, receiver, row[2], sub_m, report)
        _take_seed_pair(state, receiver, row[3], tail - sub_m, report)
        tail_sub = tail
    # 4(d). Posthead connectors keep their projection timing, moved whole (B1).  K8 amendment 8 section 1 (review
    # N-r6-1): rule (A) of branch (a) here too, no receiver-room refusal.  Branch (a) above took the receiver room
    # first; only fit = min(a_c, room) of the connector's in_SC1001_W share goes to the receiver (never below 0) and
    # only that share of its projection reservation cells moves with it.  The rest stays a head ready packet (due t0)
    # of the 127 lane serving the connector's destination (its receiver's member; N -> lane 3), ahead of every 127
    # entry (the connector lies past the end of 127), inside that lane's init_excess over its cap.  Its origin is
    # not observable per vehicle (a projection share): init:unknown, as the other-link mass of D11.  Room >= a_c:
    # fit is a_c, nothing else runs (bit equal).
    for c, target in spec['posthead_rehome'].items():
        row_p = provenance.setdefault(c, {})
        a_c = row_p.pop('storage:' + receiver, 0.0)
        fit = kept = 0.0
        if a_c > 0.0:
            fit = min(a_c, max(0.0, state.urban_link_storage[target]))
            kept = a_c - fit
            state.urban_link_storage[receiver] += a_c
            if fit > 0.0:
                state.urban_link_storage[target] -= fit
                row_p['storage:' + target] = row_p.get('storage:' + target, 0.0) + fit
        if kept > 0.0:
            member = next(m for m, r in spec['receiver_of'].items() if r == target)
            report['posthead_receiver_shortfall_veh'] += kept
            report['posthead_rehome_shortfall_veh'] += kept
            place(spec['dest_of'][member], kept, None, kind='ready', source=INIT_LINK_SOURCE.get(c, 'init:unknown'),
                  speed=0.0, link=c, veh='rehome:' + c, past_head_m=math.inf)
        row = _seed_row(seed_split, c, receiver)
        if row is not None:
            removed += row[0] + row[1]
            for due, amount in ((row[2], row[0]), (row[3], row[1])):
                _take_seed_pair(state, receiver, due, amount, report)
                moved = amount if kept <= 0.0 else amount * fit / a_c
                if target in routing:
                    _uqm._schedule(state.urban_arrival_buffer, target, due, moved)
                _uqm._schedule(state.urban_storage_release_buffer, target, due, moved)
            report['posthead_rehome_seed_gap_veh'] += abs(row[0] + row[1] - a_c)
        report['posthead_rehomed_veh'] += a_c

    # (b)(c) packets, lane by lane downstream -> upstream (N2 due, no overtaking).
    reserved = 0.0
    rebuilt = {L127: new127, L10777: new10777}
    kept_on = defaultdict(lambda: defaultdict(float))    # 4(d) kept shares: their connector's provenance (after 6.)
    for lane in LANES:
        ahead = 0.0
        previous_due = t0 + 1
        for e in sorted(entries[lane], key=lambda e: (e['distance'], e['kind'] != 'ready', str(e['veh']))):
            member, amount = e['member'], e['amount']
            if e['kind'] == 'ready':
                state.urban_movement_queue[member] += amount
                (new127 if e['link'] == L127 else kept_on[e['link']])['movement:' + member] += amount
                if amount > TINY:
                    _insert(st, lane, t0, e['source'], member, amount)
                    st['stock'][lane] += amount
                else:
                    _fold_city_share(st, lane, member, amount)
            else:
                due = _due(t0, e['distance'], lanes[lane]['sigma'], ahead,
                           max(e['speed'], spec['speed_floor_kmh']))
                due = max(due, previous_due)
                previous_due = due
                if e['link'] in rebuilt:
                    state.urban_link_storage[receiver] -= amount
                    row = rebuilt[e['link']]
                    row['storage:' + receiver] = row.get('storage:' + receiver, 0.0) + amount
                if receiver in routing:
                    _uqm._schedule(state.urban_arrival_buffer, receiver, due, amount)
                _uqm._schedule(state.urban_storage_release_buffer, receiver, due, amount)
                reserved += amount
                if amount > TINY:
                    _insert(st, lane, due, e['source'], member, amount)
                    st['stock'][lane] += amount
                    tags = st['tags'].setdefault(due, {})
                    key = (lane, member, e['source'])
                    tags[key] = tags.get(key, 0.0) + amount
                else:
                    report['tiny_moving_veh'] += amount
            ahead += amount
    provenance[L127] = {k: v for k, v in new127.items() if v > 0.0}
    provenance[L10777] = {k: v for k, v in new10777.items() if v > 0.0}

    # 6. W member mass projected on other links: ready packets after 127's.
    order = [L10777, L129] + [k for k in reversed(spec['pre_stopline_links'][:-3])]
    order += sorted(k for k in provenance if k not in order and k != L127)
    for link in order:
        row = provenance.get(link, {})
        for member in spec['members']:
            amount = row.get('movement:' + member, 0.0)
            if amount <= 0.0:
                continue
            source = INIT_LINK_SOURCE.get(link, 'init:unknown')
            if link != L10777:          # 10777's queued share is part of N_10777 (amendment 5 section 3)
                report['other_link_ready_veh'] += amount
            for lane, share in _lane_shares(spec, spec['dest_of'][member], amount):
                if share > TINY:
                    _insert(st, lane, t0, source, member, share)
                    st['stock'][lane] += share
                else:
                    _fold_city_share(st, lane, member, share)
    # Amendment 8 section 1: a 4(d) kept share is its member queue on its connector (the vehicles are there), booked
    # only now so that 6. does not pack it a second time; per-link provenance still sums to the observed vehicles.
    for link, kept_row in kept_on.items():
        row = provenance.setdefault(link, {})
        for key, amount in kept_row.items():
            row[key] = row.get(key, 0.0) + amount

    for lane in LANES:
        excess = max(0.0, st['stock'][lane] - lanes[lane]['S'])
        st['init_excess'][lane] = excess
        report['excess_veh'] += excess
    state.stopline_approach_state = st

    # Invariants at t0 (I1, I3, I7, I8, I9, I11, I5).
    _check_index(state, cfg, spec, st, t0)
    if set(provenance[L127]) - {'storage:' + receiver} - {'movement:' + m for m in spec['members']} \
            - {'storage:' + t for t in spec['receiver_of'].values()}:
        raise StoplineInvariantError('I9: link 127 still projects to another movement')
    for c in spec['posthead_connectors']:
        if 'storage:' + receiver in provenance.get(c, {}):
            raise StoplineInvariantError('I11: posthead connector keeps an in_SC1001_W share: ' + c)
    tagged = math.fsum(v for row in st['tags'].values() for v in row.values())
    expected = seed_total - removed - tail_sub + reserved
    after = math.fsum(state.urban_arrival_buffer.get(receiver, {}).values())
    if abs(after - expected) > MASS_TOL:
        raise StoplineInvariantError(f'I11: in_SC1001_W reservations {after} != {expected}')
    # I11 two-sided (N-1): the new moving reservations are the tags; only the
    # untagged primal <= 1e-12 moving shares (tiny_moving_veh) may differ.
    if abs(reserved - tagged) > MASS_TOL:
        raise StoplineInvariantError(f'I11: new moving reservations {reserved} != tags {tagged}')
    audit_projection_provenance(provenance,
        {k: net.urban_link_storage_veh[k] - state.urban_link_storage[k] for k in net.urban_link_storage_veh},
        state.urban_movement_queue, state.ramp_queue)
    report['speed_kmh'] = speed
    report['packets'] = float(sum(len(st['lanes'][l]) for l in LANES))
    metadata['stopline_approach_initial'] = {
        **{key: float(report[key]) for key in (
            'posthead_veh', 'lane_reassigned_veh', 'excess_veh', 'posthead_rehomed_veh', 'seed_residual_veh',
            'queue_shortfall_veh', 'unrouted_veh', 'offramp_queue_zeroed_veh', 'tiny_moving_veh',
            'posthead_rehome_seed_gap_veh', 'speed_kmh', 'packets', 'other_link_ready_veh',
            'posthead_receiver_shortfall_veh', 'posthead_rehome_shortfall_veh')},
        'step': t0, 'stock_veh': {str(l): st['stock'][l] for l in LANES},
        'tail129_port_veh': tail}
    return metadata


# --------------------------------------------------------------- dynamics

def _context(state, cfg, step):
    spec = view(cfg)
    st = _state(state)
    plan = st['plan']
    if plan:
        if plan['step'] != step:
            raise StoplineInvariantError('A stopline plan of another step is still open')
        return spec, st, plan
    last = st['last_step']
    if last is None:
        _runtime_guard(cfg, spec)
    elif step != last + 1:
        raise StoplineInvariantError('Noncontiguous stopline approach step')
    st['plan'] = plan = {'step': step}
    return spec, st, plan


def _admit(st, spec, step, member, amount, source):
    """City/initial ready admission (amendment 5.5): carry folds into the new packet."""
    for lane, share in _lane_shares(spec, spec['dest_of'][member], amount):
        before = _p(st['stock'][lane])
        if _p(share) > TINY:
            carry = st['carry'][lane][member]
            st['carry'][lane][member] = 0.0
            _insert(st, lane, step, source, member, share + carry)
            st['stock'][lane] = st['stock'][lane] + share
        else:
            _fold_city_share(st, lane, member, share)
        capacity = spec['lanes'][lane]['S']
        over = max(0.0, _p(st['stock'][lane]) - capacity) - max(0.0, before - capacity)
        if over > 0.0:
            st['city_over'][lane] += over
            _count(st, 'city_over_room_veh', over)


def split_arrival(state, cfg, step, arrived, targets):
    """UFA hook #6: tagged arrivals to their members, the rest by gate beta (amendment 5.5)."""
    spec, st, plan = _context(state, cfg, step)
    tags = st['tags'].pop(step, None)
    if not tags and _p(arrived) <= 0.0:
        return []
    tagged = {}
    if tags:
        total = sum(tags.values())
        if _p(total) > _p(arrived) + TAG_TOL:
            raise StoplineInvariantError(f'Tagged stopline arrivals exceed the parent arrival: {_p(total)}')
        folded = set()
        for (lane, member, _source), amount in tags.items():
            tagged[member] = tagged.get(member, 0.0) + amount
            if (lane, member) in folded:
                continue
            folded.add((lane, member))
            packet = next((p for p in st['lanes'][lane] if p[0] == step and p[3] == member), None)
            if packet is None:
                raise StoplineInvariantError('A stopline tag lost its moving packet')
            packet[4] = packet[4] + st['carry'][lane][member]
            st['carry'][lane][member] = 0.0
        untagged = max(0.0, arrived - total)
    else:
        untagged = arrived
    values = {}
    members = set(spec['members'])
    for movement, beta in targets:
        share = beta * untagged
        values[movement] = share
        if movement in members:
            _admit(st, spec, step, movement, share, 'city')
    for member, amount in tagged.items():
        if member not in values:
            raise StoplineInvariantError('Tagged stopline member is not routed from in_SC1001_W')
        values[member] = values[member] + amount
    return list(values.items())


def enqueue_city(state, cfg, movement, amount, step):
    """UFA hook #7: gate landing share of a W member (queue already credited by UFA:391)."""
    spec, st, _plan = _context(state, cfg, step)
    _admit(st, spec, step, movement, amount, 'city')


def _joint_ports(state, cfg, spec, st, step):
    """Amendment 5.3: zipper per lane, connector FIFO, joint in_SC1001_W cap A (N16)."""
    lor = state.lane_offramp_runtime
    room = {l: max(0.0, spec['lanes'][l]['S'] - st['stock'][l]) for l in LANES}
    service, request = {}, {}
    for off in PORTS:
        port = lor.ports[off]
        service[off] = cfg.network.movement_capacity_veh_h * spec['ports'][off]['lanes'] / 3600.
        ready = port.ready + math.fsum(n for t, n in port.pending if t <= step + 1)
        request[off] = min(service[off], ready)
    west, east = [o for o in PORTS if ZIPPER[o] == 'upstream'][0], [o for o in PORTS if ZIPPER[o] == 'merge'][0]
    alloc = {west: {}, east: {}}
    for lane in LANES:
        r_w = spec['ports'][west]['weights'][lane] * request[west]
        r_e = spec['ports'][east]['weights'][lane] * request[east]
        a_e = min(r_e, max(room[lane] / 2, room[lane] - r_w))
        alloc[east][lane] = a_e
        alloc[west][lane] = min(r_w, room[lane] - a_e)
    fifo, first = {}, {}
    for off in PORTS:
        weights = spec['ports'][off]['weights']
        fifo[off] = min(alloc[off][l] / weights[l] for l in LANES if _p(weights[l]) > 0.0)
        first[off] = min(service[off], fifo[off])
    available = _uqm._effective_available_space(state, cfg, spec['receiver'])
    limit = {east: min(first[east], max(available / 2, available - first[west]))}
    limit[west] = min(first[west], available - limit[east])
    out = {}
    for off in PORTS:
        out[off] = {'limit': limit[off], 'service': service[off], 'room': min(available, fifo[off]),
                    'request': request[off], 'alloc': alloc[off], 'fifo': fifo[off], 'released': 0.0}
        if _p(limit[off]) < _p(request[off]) - TINY:
            _count(st, 'port_blocked_steps_' + off, 1.0)
    out['available'] = available
    if _p(first[west]) + _p(first[east]) > _p(available) + TINY:
        _count(st, 'port_joint_room_binding_steps', 1.0)
    for lane in LANES:
        if _p(room[lane]) <= TINY:
            _count(st, 'lane_full_steps_' + str(lane), 1.0)
    port = lor.ports['10491']
    if _p(port.stock) >= port.capacity - 1.0:
        _count(st, 'port_full_steps_10491', 1.0)
    return out


def allocate(state, cfg, step, off, port=None):
    """LOR hook #4: (None, receiver, L_p, c_p*dt, room) with both ports computed once per step."""
    spec, st, plan = _context(state, cfg, step)
    if 'ports' not in plan:
        plan['ports'] = _joint_ports(state, cfg, spec, st, step)
    row = plan['ports'][off]
    return (None, spec['receiver'], row['limit'], row['service'], row['room'])


def land_release(state, cfg, step, off, n, routing):
    """LOR hook #5: lane packets, tags, per-lane paired reservations (N-A5), ledger (B2)."""
    spec, st, plan = _context(state, cfg, step)
    if 'ports' not in plan:
        raise StoplineInvariantError('Port release without its stopline allocation')
    port = spec['ports'][off]
    receiver = spec['receiver']
    tilde = port['beta_tilde']
    by_dest = {'E': n * tilde['E'], 'S': n * tilde['S']}
    by_dest['N'] = n - by_dest['E'] - by_dest['S']
    share = {lane: [] for lane in LANES}
    for dest in DESTS:
        for lane, amount in _lane_shares(spec, dest, by_dest[dest]):
            share[lane].append((spec['member_of'][dest], amount))
    source = port['source']
    lane_total = {}
    for lane in LANES:
        lanes = spec['lanes'][lane]
        due = _due(step, port['distance_m'][lane], lanes['sigma'], _p(st['stock'][lane]), st['speed_kmh'])
        total = 0.0
        for member, amount in share[lane]:
            total = total + amount
            if _p(amount) > TINY:
                _insert(st, lane, due, source, member, amount)
                st['stock'][lane] = st['stock'][lane] + amount
                tags = st['tags'].setdefault(due, {})
                key = (lane, member, source)
                tags[key] = tags.get(key, 0.0) + amount
            else:
                _skip_tiny_port_share(st, lane, member, amount)
        lane_total[lane] = total
        if receiver in routing:
            _uqm._schedule(state.urban_arrival_buffer, receiver, due, total)
        _uqm._schedule(state.urban_storage_release_buffer, receiver, due, total)
    # Ledger (B2): one transfer per destination, counted and keyed on primals.
    big = [d for d in DESTS if _p(by_dest[d]) > TINY]
    if big:
        amounts = {d: by_dest[d] for d in big}
        for d in DESTS:
            if d not in amounts:
                amounts[big[0]] = _merge_tiny_transfer(st, amounts[big[0]], by_dest[d])
    else:
        big, amounts = ['E'], {'E': n}
    lor = state.lane_offramp_runtime
    for d in big:
        emit_transfer(state, cfg, 'storage:' + port['storage'], 'storage:' + receiver, amounts[d],
                      route_key='movement:' + port['exit_movement'][d],
                      source_inside=lor.membership[port['connector']],
                      target_inside=lor.membership[port['to_link']])
    ledger = get_ledger(state)
    if ledger is not None and ledger.captures_response:
        # N-3 (approved deviation): the recorded resource is this port's lane allocation alloc_p,l (the two
        # ports share room_l), not room_l itself. New kind `stopline_lane_room` -> GB-7' A_K8 rule 1.
        alloc = plan['ports'][off]['alloc']
        for lane in LANES:
            if _p(port['weights'][lane]) > 0.0:
                ledger.record_resource_allocation('stopline_lane_room', off + ':' + str(lane), alloc[lane],
                                                  {off + ':' + str(lane): lane_total[lane]})
    plan['ports'][off]['released'] = plan['ports'][off]['released'] + n
    _count(st, 'port_release_veh_' + off, _p(n))
    _count(st, 'np_off_ramp_veh', _p(n))


def intended(state, control, cfg, step):
    """UFA hook #8: ready prefix of each lane up to B_l = s_l*T_u_h*phi_l (amendment 5.2, N7)."""
    spec, st, plan = _context(state, cfg, step)
    if 'intended' in plan:
        return plan['intended']
    specs = _uqm.movement_specs(cfg)
    lists, budgets = {}, {}
    result = {m: 0.0 for m in spec['members']}
    for lane in LANES:
        row = spec['lanes'][lane]
        # Module attribute looked up at call time: adapter patches and wrap_clock apply (N7).
        phi = _uqm._phase_green_fraction(control, cfg, specs[row['phase_member']], urban_step_index=step)
        budget = row['s_veh_h'] * cfg.simulation.T_u_h * phi
        walked, cumulative, ready_total = [], 0.0, 0.0
        stopped = False
        for packet in st['lanes'][lane]:
            if packet[0] > step:
                break
            ready_total += _p(packet[4])
            if stopped:
                continue
            remaining = budget - cumulative
            if _p(remaining) <= 0.0:
                stopped = True
                continue
            if _p(packet[4]) < _p(remaining):
                take = packet[4]
            else:
                take = remaining
                stopped = True
            walked.append((packet, packet[3], take))
            cumulative = cumulative + take
            result[packet[3]] = result[packet[3]] + take
        if ready_total > _p(budget) + TINY:
            _count(st, 'lane_budget_binding_steps_' + str(lane), 1.0)
        lists[lane] = walked
        budgets[lane] = budget
    plan.update(lists=lists, budget=budgets, intended=result)
    return result


def resolve(state, cfg, accepted):
    """UFA hook #9: per-lane head-of-line walk of the accepted service."""
    st = _state(state)
    plan = st['plan']
    if 'lists' not in plan:
        return {}
    rate, acc = {}, {}
    for member, wanted in plan['intended'].items():
        got = accepted.get(member, 0.0)
        acc[member] = got
        rate[member] = 1.0 if (_p(wanted) <= 0.0 or _p(got) >= _p(wanted)) else got / wanted
    realized = {m: 0.0 for m in plan['intended']}
    items = {m: [] for m in plan['intended']}
    lane_realized = {}
    for lane in LANES:
        total = 0.0
        for packet, member, amount in plan['lists'][lane]:
            r = rate[member]
            blocked = _p(r) < 1.0 - TINY
            x = amount * r if blocked else amount
            items[member].append((lane, packet, x))
            realized[member] = realized[member] + x
            total = total + x
            if blocked:
                break
        lane_realized[lane] = total
    unused = math.fsum(max(0.0, _p(acc[m]) - _p(realized[m])) for m in realized)
    if unused > 0.0:
        _count(st, 'hol_unused_room_veh', unused)
    plan.update(accepted=acc, realized=realized, items=items, lane_realized=lane_realized, dequeued={})
    return dict(realized)


def dequeue(state, cfg, movement, actual, step):
    """FIFO removal of the resolved plan; fixed six-source split (amendment 5.2)."""
    spec, st, plan = _context(state, cfg, step)
    if 'items' not in plan or movement in plan['dequeued']:
        raise StoplineInvariantError('Stopline dequeue without its resolve plan: ' + movement)
    items = plan['items'][movement]
    planned = plan['realized'][movement]
    if abs(_p(actual) - _p(planned)) > MASS_TOL or not items:
        raise StoplineInvariantError(f'Stopline departure {movement} differs from its plan')
    delta = actual - planned
    out = {k: 0.0 for k in SOURCES}
    for index, (lane, packet, x) in enumerate(items):
        take = x + delta if index == len(items) - 1 else x
        packet[4] = packet[4] - take
        out[packet[2]] = out[packet[2]] + take
        st['stock'][lane] = st['stock'][lane] - take
        _count(st, SERVED_KEY[packet[2]], _p(take))
        residual = _p(packet[4])
        if residual <= TINY:
            if residual < -MASS_TOL:
                raise StoplineInvariantError('Stopline packet overdrawn')
            queue = st['lanes'][lane]
            del queue[next(i for i, p in enumerate(queue) if p is packet)]
            _fold_service_residual(st, lane, movement, packet[4])
    plan['dequeued'][movement] = actual
    return out


def _route_side(cfg, member):
    routes = getattr(cfg.network, 'control_area_routes', None) or {}
    route = routes.get('movement:' + member)
    if route is None or type(route.get('target_inside')) is not bool:
        raise StoplineRouteError('Internal stopline crossing needs a boolean target_inside: ' + member)
    if route.get('inside_to_inside') != route.get('outside_to_inside'):
        raise StoplineRouteError('Internal stopline crossing route has p_in != p_out: ' + member)
    return route['target_inside']


def depart(state, cfg, movement, actual, step, receiving_key):
    """UFA hook #10 (before UFA:597): dequeue and the N_P-aware ledger transfers (amendment 5.6).

    Returns the city-side amount that UFA:617-619 counts as inbound / gate inflow.
    """
    src = dequeue(state, cfg, movement, actual, step)
    st = _state(state)
    city = src['city'] + src['init:city'] + src['init:unknown']
    port = actual - city
    target = 'storage:' + receiving_key if receiving_key in state.urban_link_storage else None
    ledger = get_ledger(state)
    if _p(city) > TINY and _p(port) > TINY:
        emit_transfer(state, cfg, 'movement:' + movement, target, city, route_key='movement:' + movement)
        _internal(state, cfg, ledger, movement, target, port)
        counted = city
    elif _p(port) <= TINY:
        _merge_tiny_transfer(st, city, port)       # counted only; `actual` is emitted as is
        emit_transfer(state, cfg, 'movement:' + movement, target, actual, route_key='movement:' + movement)
        counted = actual
    else:
        _merge_tiny_transfer(st, port, city)
        _internal(state, cfg, ledger, movement, target, actual)
        counted = 0.0
    _count(st, 'np_boundary_in_veh', _p(counted))
    _count(st, 'internal_crossing_veh', _p(actual) - _p(counted))
    _count(st, 'inbound_unknown_origin_veh', _p(src['init:unknown']))
    return counted


def _internal(state, cfg, ledger, movement, target, amount):
    if ledger is None:
        return          # CAO:702-704: no ledger, no transfer and no I10 premise
    side = _route_side(cfg, movement)
    outside = _p(ledger.stocks.get('movement:' + movement, {}).get('outside', 0.0))
    if outside > MASS_TOL:
        raise StoplineRouteError(f'I10: {movement} carries an outside cohort {outside}')
    emit_transfer(state, cfg, 'movement:' + movement, target, amount,
                  route_key='stopline_internal:' + movement, target_inside=side)


def _check_index(state, cfg, spec, st, step):
    """I1, I3, I5, I7, I8 on the current index (also used at t0)."""
    receiver = spec['receiver']
    arrivals = state.urban_arrival_buffer.get(receiver, {})
    worst = 0.0
    for due, row in st['tags'].items():
        if due <= step:
            raise StoplineInvariantError(f'I1: unconsumed stopline tag at {due}')
        total = math.fsum(_p(v) for v in row.values())
        worst = max(worst, total - _p(arrivals.get(due, 0.0)))
    if worst > TAG_TOL:
        raise StoplineInvariantError(f'I1: tags exceed their arrival reservation by {worst}')
    tagged = math.fsum(_p(v) for row in st['tags'].values() for v in row.values())
    occupancy = cfg.network.urban_link_storage_veh[receiver] - _p(state.urban_link_storage[receiver])
    if tagged > occupancy + TAG_TOL:
        raise StoplineInvariantError('I2: tagged packets exceed the in_SC1001_W occupancy')
    ready = defaultdict(float)
    for lane in LANES:
        packets = st['lanes'][lane]
        keys = [_packet_key(p) for p in packets]
        if any(a >= b for a, b in zip(keys, keys[1:])):
            raise StoplineInvariantError(f'I8: lane {lane} is not strictly (due, seq) ordered')
        mass = 0.0
        for p in packets:
            if _p(p[4]) <= TINY:
                raise StoplineInvariantError('I3: a packet with primal amount <= 1e-12 survived')
            mass += _p(p[4])
            if p[0] <= step:
                ready[p[3]] += _p(p[4])
        carry = st['carry'][lane]
        mass += math.fsum(_p(v) for v in carry.values())
        for member, value in carry.items():
            ready[member] += _p(value)
        stock = _p(st['stock'][lane])
        if abs(stock - mass) > MASS_TOL:
            raise StoplineInvariantError(f'I3: lane {lane} stock {stock} != index {mass}')
        bound = spec['lanes'][lane]['S'] + st['city_over'][lane] + st['init_excess'][lane]
        if stock > bound + MASS_TOL:
            raise StoplineInvariantError(f'I3: lane {lane} stock {stock} exceeds {bound}')
    for member in spec['members']:
        q = _p(state.urban_movement_queue.get(member, 0.0))
        if abs(ready[member] - q) > MASS_TOL:
            raise StoplineInvariantError(f'I7: {member} index {ready[member]} != queue {q}')
    for name in spec.get('offramp_movements', ()):
        if _p(state.urban_movement_queue.get(name, 0.0)) != 0.0:
            raise StoplineInvariantError('I5: off-ramp movement queue is not zero: ' + name)
    return worst


def end_step(state, cfg, step):
    """UFA hook #10b: close the step plan, check I1-I5/I7/I8, per-step diagnostics (<= 20 keys)."""
    spec, st, plan = _context(state, cfg, step)
    for off in PORTS:
        row = plan.get('ports', {}).get(off)
        if row is not None and _p(row['released']) > _p(row['limit']) + MASS_TOL:
            raise StoplineInvariantError('I4: port release exceeds its limit ' + off)
    if 'ports' in plan:
        joint = _p(plan['ports']['10491']['limit']) + _p(plan['ports']['10481']['limit'])
        if joint > _p(plan['ports']['available']) + MASS_TOL:
            raise StoplineInvariantError('I4: joint port release exceeds in_SC1001_W room')
    if 'lane_realized' in plan:
        for lane in LANES:
            if _p(plan['lane_realized'][lane]) > _p(plan['budget'][lane]) + MASS_TOL:
                raise StoplineInvariantError(f'I4: lane {lane} realized service exceeds its budget')
        for member, value in plan['realized'].items():
            if _p(value) > _p(plan['accepted'][member]) + MASS_TOL:
                raise StoplineInvariantError('I4: member realized service exceeds acceptance ' + member)
    worst = _check_index(state, cfg, spec, st, step)
    counters = st['counters']
    counters['tag_residual_max'] = max(counters['tag_residual_max'], max(0.0, worst))
    risk = any(_p(st['stock'][lane]) > (spec['lanes'][lane]['head_pos_m'] - ACCESS_RISK_FROM_HEAD_M)
               / spec['lanes'][lane]['sigma'] for lane in (1, 2))
    if risk:
        _count(st, 'n_access_risk_steps', 1.0)
    st['plan'] = {}
    st['last_step'] = step
    return {'stopline_' + key: counters[key] for key in STEP_KEYS}


def diagnostics(state):
    """All cumulative counters plus the reported origin shares (spec 9)."""
    st = _state(state)
    out = {'stopline_' + k: v for k, v in st['counters'].items()}
    served = math.fsum(st['counters'][SERVED_KEY[s]] for s in SOURCES)
    for tag, key in (('OFF_W', 'served_port_OR_D_W_veh'), ('OFF_E', 'served_port_OR_D_E_veh')):
        out['stopline_origin_share_' + tag] = st['counters'][key] / served if served > 0.0 else 0.0
    return out
