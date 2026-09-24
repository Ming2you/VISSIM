"""obs150 contract (WP-0, 2026-09-24): one definition of the 150 s observation.

Every package of the SDMPC-31 x obs150 work codes against this module and
``diagnostics/sdmpc_n31_20260924/CONTRACT.md``. It holds

- the switch (plant manifest v2, tuning rules, runner env, provenance block),
- the time rules (windows, green intervals, the .mer file-order rule, the lag
  rule and the ordinal window assignment),
- the counting identity (station count + stock change + removals),
- the schemas (obs150-raw/v1, capture meta, chunk rows, derived/v1,
  lane-plant-observation/v2, physical-head-window/v2) with strict validators,
- the detector CSV format with its canonical writer/reader,
- Obs150Context and the Python interface signatures of plan section 1.9.

Nothing here touches VISSIM, the adapter or a live run. Functions are pure
except the explicit loaders, which read only files a raw bundle pins by sha256.
Validators raise ObsContractError; they never repair or default a value.
"""
from __future__ import annotations

from collections import defaultdict
import csv
from dataclasses import dataclass
import hashlib
import importlib
import inspect
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping, NamedTuple

ROOT = Path(__file__).resolve().parents[2]


class ObsContractError(ValueError):
    """A bundle, table or derived document violates the obs150 contract."""


class ObsLagError(ObsContractError):
    """The .mer file has not completed the last step before the decision (B3)."""


def _require(condition, message):
    if not condition:
        raise ObsContractError(message)


_HEX64 = re.compile(r'^[0-9a-f]{64}$')
_UINT = re.compile(r'^[1-9][0-9]*$')
_SGKEY = re.compile(r'^([1-9][0-9]*)-([1-9][0-9]*)$')


def _is_int(value):
    return type(value) is int


def _is_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _nonneg_int(value, what):
    _require(_is_int(value) and value >= 0, what + ' must be a non-negative JSON integer')
    return value


def _nonneg_number(value, what):
    _require(_is_number(value) and value >= 0, what + ' must be a finite non-negative number')
    return float(value)


def _sha(value, what):
    _require(isinstance(value, str) and _HEX64.match(value) is not None,
             what + ' must be a lowercase hex sha256')
    return value


def _keys(obj, expected, what):
    _require(isinstance(obj, dict), what + ' must be an object')
    expected = set(expected)
    missing, extra = expected - set(obj), set(obj) - expected
    _require(not missing and not extra,
             f'{what} keys differ: missing {sorted(missing)} extra {sorted(extra)}')


def _uint_key(key, what):
    _require(isinstance(key, str) and _UINT.match(key) is not None,
             what + ' keys must be decimal integer strings')
    return int(key)


def canonical_json_bytes(obj):
    """The one serialization used for every sha of a JSON value in obs150."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def canonical_sha256(obj):
    return hashlib.sha256(canonical_json_bytes(obj)).hexdigest()


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


# --------------------------------------------------------------------------
# 1.1 The switch
# --------------------------------------------------------------------------
LANE_PLANT_CONFIG_KEY = ('freeway', 'lane_plant')
PLANT_SCHEMA_V1 = 'coupled-lane-plant/v1'
PLANT_SCHEMA_V2 = 'coupled-lane-plant/v2'
PLANT_MODES = {PLANT_SCHEMA_V1: 'v1', PLANT_SCHEMA_V2: 'v2'}
OBSERVATION_CADENCE = 'decision150'
V2_SOURCE_KEYS = ('network', 'geometry', 'refined_partition', 'reference_config', 'parameters',
                  'port_profile', 'reference_protocol', 'runner_config', 'sig_manifest')
V2_MANIFEST_KEYS = ('schema', 'sources', 'membership', 'off_groups', 'observation',
                    'source_boundary', 'lane_groups', 'fw_e_terminal', 'vsl_command_space',
                    'future_observations', 'qualification')
V2_OBSERVATION_KEYS = ('detectors', 'expected_simres', 'vehrec_interval_sec')
SOURCE_BOUNDARY_BLOCK = {'mode': 'calibrated_history_forecast', 'history_sec': 150, 'model_step_sec': 10}
FW_E_TERMINALS = ('component', 'zero_gradient')
VSL_COMMAND_SPACE = 'parent_21'
GT_RUN_NAME_PREFIX = 'sdmpc31_g'

# RW_* values the runner (PS1 Set-HeadObservationTransport) must set for a v2
# manifest. RW_SIGNAL_OBSERVATION_CONFIG_SHA256 keeps its v1 rule and is not
# read in obs150 mode; RW_OBS150_GT is set only for ground-truth dev runs.
RUNNER_ENV_V2 = {
    'RW_SIGNAL_OBSERVATION': '0',
    'RW_LANE_PLANT_OBSERVATION': '1',
    'RW_VEHICLE_OBSERVATION_INTERVAL_SEC': '1',
    'RW_QUEUE_WINDOW': '0',
    'RW_OBSERVATION_CADENCE': OBSERVATION_CADENCE,
    'RW_STATE_LOG': 'decision',
}
PROVENANCE_OBSERVATION_SCHEMA = 'obs150-provenance/v1'
PROVENANCE_OBSERVATION_KEYS = ('schema', 'cadence', 'plant_manifest', 'detectors', 'expected_simres',
                               'vehrec_interval_sec', 'ground_truth_windows', 'freeze')


def _repo_pin(pin, what):
    _keys(pin, ('path', 'sha256'), what)
    path = pin['path']
    _require(isinstance(path, str) and path and '\\' not in path and not PurePosixPath(path).is_absolute()
             and ':' not in path and '..' not in PurePosixPath(path).parts,
             what + '.path must be a repo-relative forward-slash path')
    _sha(pin['sha256'], what + '.sha256')


def plant_mode(document):
    """'v1' or 'v2' from the manifest the ONE key freeway.lane_plant points to."""
    _require(isinstance(document, dict), 'Lane plant manifest must be an object')
    mode = PLANT_MODES.get(document.get('schema'))
    _require(mode is not None, 'Unsupported lane plant declaration schema')
    return mode


def validate_plant_manifest_v2(document):
    """Exact key set of coupled-lane-plant/v2 (plan C8 + WP-0 additions)."""
    _require(plant_mode(document) == 'v2', 'Not a coupled-lane-plant/v2 manifest')
    _keys(document, V2_MANIFEST_KEYS, 'plant manifest v2')
    _keys(document['sources'], V2_SOURCE_KEYS, 'plant manifest v2 sources')
    for key, pin in document['sources'].items():
        _repo_pin(pin, 'sources.' + key)
    _repo_pin(document['membership'], 'membership')
    off_groups = document['off_groups']
    _require(isinstance(off_groups, str) and off_groups and '\\' not in off_groups,
             'off_groups must be a repo-relative forward-slash path')
    observation = document['observation']
    _keys(observation, V2_OBSERVATION_KEYS, 'plant manifest v2 observation')
    _repo_pin(observation['detectors'], 'observation.detectors')
    _require(observation['expected_simres'] == EXPECTED_SIMRES and _is_int(observation['expected_simres']),
             'observation.expected_simres must be 10')
    _require(observation['vehrec_interval_sec'] == VEHREC_INTERVAL_SEC and _is_int(observation['vehrec_interval_sec']),
             'observation.vehrec_interval_sec must be 5')
    _require(document['source_boundary'] == SOURCE_BOUNDARY_BLOCK
             and all(_is_int(document['source_boundary'][k]) for k in ('history_sec', 'model_step_sec')),
             'source_boundary block differs from the contract')
    _require(document['lane_groups'] is False, 'v2 declares lane_groups false')
    _require(document['fw_e_terminal'] in FW_E_TERMINALS, 'Unknown fw_e_terminal')
    _require(document['vsl_command_space'] == VSL_COMMAND_SPACE, 'vsl_command_space must be parent_21')
    _require(document['future_observations'] is False, 'future_observations must be false')
    _require(isinstance(document['qualification'], str) and document['qualification'],
             'qualification must state the honest status')


def validate_tuning_v2(tuning, document):
    """The effective (extends-merged) tuning that selects a v2 manifest."""
    validate_plant_manifest_v2(document)
    _require(isinstance(tuning, dict), 'Tuning must be an object')
    lane_plant = tuning.get('freeway', {}).get('lane_plant')
    _require(isinstance(lane_plant, str) and lane_plant and '\\' not in lane_plant,
             'freeway.lane_plant must be a forward-slash manifest path')
    head = tuning.get('urban', {}).get('capacity', {}).get('head_observation')
    _require(isinstance(head, dict) and head.get('enabled') is True,
             'v2 keeps urban.capacity.head_observation enabled (window v2)')
    _require('sample_interval_sec' not in head, 'v2 rejects head_observation.sample_interval_sec')
    execution = tuning.get('execution', {})
    _require(execution.get('native_signal_record') is False, 'v2 requires execution.native_signal_record false')
    _require(execution.get('signal_vbs_config') == document['sources']['runner_config']['path'],
             'execution.signal_vbs_config must equal the manifest runner_config pin')


def parse_gt_windows(text):
    """RW_OBS150_GT '750:900,1050:1200' -> [[750, 900], [1050, 1200]]; '' -> []."""
    _require(isinstance(text, str), 'Ground-truth windows must be text')
    if text == '':
        return []
    result = []
    for item in text.split(','):
        match = re.fullmatch(r'(0|[1-9][0-9]*):([1-9][0-9]*)', item)
        _require(match is not None, 'Ground-truth window must be start:end integers')
        result.append([int(match[1]), int(match[2])])
    _validate_gt_windows(result)
    return result


def format_gt_windows(windows):
    _validate_gt_windows(windows)
    return ','.join(f'{a}:{b}' for a, b in windows)


def _validate_gt_windows(windows):
    _require(isinstance(windows, list), 'ground_truth_windows must be a list')
    last = -1
    for item in windows:
        _require(isinstance(item, list) and len(item) == 2 and all(_is_int(v) for v in item),
                 'ground_truth window must be [start, end] integers')
        a, b = item
        _require(0 <= a < b and a % DECISION_INTERVAL_SEC == 0 and b % DECISION_INTERVAL_SEC == 0 and a >= last,
                 'ground_truth windows must be sorted, window-aligned and non-overlapping')
        last = b


def expected_runner_env(document, detectors_path):
    """The exact RW_* set PS1 exports for a v2 manifest (SHO v2 compares it)."""
    validate_plant_manifest_v2(document)
    _require(isinstance(detectors_path, str) and detectors_path, 'Absolute detector CSV path required')
    observation = document['observation']
    return {**RUNNER_ENV_V2,
            'RW_OBS150_DETECTORS': detectors_path,
            'RW_OBS150_DETECTORS_SHA256': observation['detectors']['sha256'],
            'RW_OBS150_EXPECTED_SIMRES': str(observation['expected_simres']),
            'RW_OBS150_VEHREC_SEC': str(observation['vehrec_interval_sec'])}


def validate_provenance_observation(block, *, require_freeze=False):
    """The 'observation' block PS1 adds to the run provenance manifest (A8)."""
    _keys(block, PROVENANCE_OBSERVATION_KEYS, 'provenance observation')
    _require(block['schema'] == PROVENANCE_OBSERVATION_SCHEMA, 'Unsupported provenance observation schema')
    _require(block['cadence'] == OBSERVATION_CADENCE, 'provenance cadence must be decision150')
    _keys(block['plant_manifest'], ('path', 'sha256'), 'provenance plant_manifest')
    _sha(block['plant_manifest']['sha256'], 'provenance plant_manifest.sha256')
    _keys(block['detectors'], ('path', 'sha256', 'rows'), 'provenance detectors')
    _sha(block['detectors']['sha256'], 'provenance detectors.sha256')
    _require(_is_int(block['detectors']['rows']) and block['detectors']['rows'] > 0, 'provenance detectors.rows')
    _require(block['expected_simres'] == EXPECTED_SIMRES, 'provenance expected_simres must be 10')
    _require(block['vehrec_interval_sec'] == VEHREC_INTERVAL_SEC, 'provenance vehrec_interval_sec must be 5')
    _validate_gt_windows(block['ground_truth_windows'])
    freeze = block['freeze']
    if freeze is None:
        _require(not require_freeze, 'A launch requires the FREEZE.json pin')
    else:
        _keys(freeze, ('path', 'sha256'), 'provenance freeze')
        _sha(freeze['sha256'], 'provenance freeze.sha256')


# --------------------------------------------------------------------------
# 1.2 Time rules
# --------------------------------------------------------------------------
DECISION_INTERVAL_SEC = 150
FIRST_DECISION_SEC = 1
EXPECTED_SIMRES = 10
VEHREC_INTERVAL_SEC = 5
MER_TIME_DECIMALS = 2
BOUNDARY_EPS_S = 0.005
LAG_MARGIN_S = 1.0
STEP_ORDER_SCAN_S = 0.2
GREEN_STATE = 'GREEN'
# Owned by WP-B1 (obs150_signal_clock.NATIVE_STEP_RULE), fixed by V0-4.
NATIVE_STEP_RULES = ('program_state_at_step_end', 'program_state_at_step_start')
_FUZZ = 1e-9


def is_decision_stop(t):
    return _is_int(t) and (t == FIRST_DECISION_SEC or (t >= DECISION_INTERVAL_SEC and t % DECISION_INTERVAL_SEC == 0))


def window_bounds(k):
    """Window k is (150k-150, 150k]."""
    _require(_is_int(k) and k >= 1, 'Window index must be a positive integer')
    return DECISION_INTERVAL_SEC * (k - 1), DECISION_INTERVAL_SEC * k


def window_index(end_s):
    _require(_is_int(end_s) and end_s >= DECISION_INTERVAL_SEC and end_s % DECISION_INTERVAL_SEC == 0,
             'A window ends at a positive multiple of 150 s')
    return end_s // DECISION_INTERVAL_SEC


def window_of_time(tau):
    """The window holding true time tau > 0 (a passage at exactly 150k is in k)."""
    _require(_is_number(tau) and tau > 0, 'Window membership needs a positive time')
    return math.ceil(tau / DECISION_INTERVAL_SEC - _FUZZ)


def bundle_interval(sim_sec):
    """(start_s, end_s, k) of the interval a bundle at sim_sec closes.

    t=1 closes the open interval (0, 1] of window 1 (k is None there)."""
    _require(is_decision_stop(sim_sec), 'Bundles exist only at t=1 and multiples of 150 s')
    if sim_sec == FIRST_DECISION_SEC:
        return 0, FIRST_DECISION_SEC, None
    k = window_index(sim_sec)
    return sim_sec - DECISION_INTERVAL_SEC, sim_sec, k


def in_green(tau, intervals):
    """Green intervals are integer pairs (a, b): a passage at true time tau is green iff a < tau <= b."""
    return any(a < tau <= b for a, b in intervals)


def tail_in_green(end_s, intervals):
    """Tail passages lie in (T-1, T]; the state is one value there (writes only at integer stops)."""
    return in_green(end_s - 0.5, intervals)


def near_integer(t):
    """The integer s with |t - s| <= 0.005, else None (.mer times are rounded to 0.01 s)."""
    s = round(t)
    return int(s) if abs(t - s) <= BOUNDARY_EPS_S + _FUZZ else None


class MerRow(NamedTuple):
    """One stored .mer row; the chunk JSONL line is this tuple as a JSON array.

    seq: 0-based index of the data row among ALL data rows of the .mer file.
    dcp: data collection point number (first .mer column, PRB h).
    t_entry / t_exit: seconds, None where the .mer column is -1.00.
    ordinal: 1-based per-dcp entry ordinal for entry rows, None for exit-only rows.
    """
    seq: int
    dcp: int
    t_entry: float | None
    t_exit: float | None
    veh: int
    vtype: int
    v_kmh: float | None
    length_m: float | None
    ordinal: int | None

    @property
    def t_file(self):
        """The step the row was written in: its latest event time."""
        return max(t for t in (self.t_entry, self.t_exit) if t is not None)


MER_ROW_FIELDS = MerRow._fields


def boundary_side(rows, index, s):
    """Decide which 0.1 s step a record at |t - s| <= 0.005 belongs to (plan B5, D8).

    Steps are written in order (NEW-5); rows inside one step are in vehicle
    order. An EARLIER row with t >= s + 0.005 proves the record is in the step
    (s, s+0.1]: 'after'. A LATER row with t <= s - 0.005 proves (s-0.1, s]:
    'before'. Neither: 'ambiguous'. Both: the step-order premise is broken.
    rows must be the chunk rows in file (seq) order.
    """
    t = rows[index].t_file
    _require(abs(t - s) <= BOUNDARY_EPS_S + _FUZZ, 'boundary_side needs a record at the boundary')
    after = before = False
    for j in range(index - 1, -1, -1):
        other = rows[j].t_file
        if other >= s + BOUNDARY_EPS_S - _FUZZ:
            after = True
            break
        if other < s - STEP_ORDER_SCAN_S:
            break
    for j in range(index + 1, len(rows)):
        other = rows[j].t_file
        if other <= s - BOUNDARY_EPS_S + _FUZZ:
            before = True
            break
        if other > s + STEP_ORDER_SCAN_S:
            break
    _require(not (after and before), 'Step-order premise violated around ' + str(s))
    return 'after' if after else 'before' if before else 'ambiguous'


def classify_passage(rows, index, intervals):
    """'green' | 'not_green' | 'ambiguous' for the ENTRY event of rows[index]."""
    row = rows[index]
    _require(row.t_entry is not None, 'Only entry events are classified')
    s = near_integer(row.t_entry)
    endpoints = {v for pair in intervals for v in pair}
    if s is None or s not in endpoints:
        return 'green' if in_green(row.t_entry, intervals) else 'not_green'
    side = boundary_side(rows, index, s)
    if side == 'ambiguous':
        return 'ambiguous'
    tau = s if side == 'before' else s + 0.05
    return 'green' if in_green(tau, intervals) else 'not_green'


def lag_ok(max_t_any, end_s, sum_tail):
    """B3: with any tail, the file must already hold a record later than T-1+0.005.

    t=1 closes the open interval (0, 1], which is itself (T-1, T]: every tail
    lies there by definition. The .mer is then often still inside its header
    (max_t_any null) while a source station at 1.0 m already counts a passage.
    """
    if sum_tail == 0 or end_s == FIRST_DECISION_SEC:
        return True
    return max_t_any is not None and max_t_any > end_s - LAG_MARGIN_S + BOUNDARY_EPS_S + _FUZZ


@dataclass(frozen=True)
class WindowAssignment:
    start_s: int
    end_s: int
    k: int | None
    entries: Mapping[int, tuple]      # dcp -> entry MerRows of this interval, seq order
    tails: Mapping[int, int]          # dcp -> C_k - records present (all in (T-1, T])
    sum_tail: int
    max_t_any: float | None
    lag_ok: bool


def assign_window(obs, mer_rows):
    """B3 ordinal assignment for the interval the bundle closes.

    C_k = detectors_cum, C_{k-1} = C_k - detectors (0 at t=1). An entry row
    whose per-dcp ordinal n satisfies C_{k-1} < n <= C_k belongs to this
    interval. tail = C_k - records_cum_by_dcp. Raises ObsLagError when the lag
    rule fails and ObsContractError on any count contradiction.
    """
    start_s, end_s, k = bundle_interval(obs['sim_sec'])
    cum, current = obs['detectors_cum'], obs['detectors']
    records = obs['mer']['records_cum_by_dcp']
    by_dcp = defaultdict(list)
    last_seq = -1
    for row in mer_rows:
        _require(row.seq > last_seq, 'Chunk rows must be in strictly increasing seq order')
        last_seq = row.seq
        _require(str(row.dcp) in cum, 'Chunk row for a point outside the detector table: ' + str(row.dcp))
        if row.ordinal is not None:
            by_dcp[row.dcp].append(row)
    entries, tails = {}, {}
    for key in sorted(cum, key=int):
        dcp = int(key)
        c_now = cum[key]
        c_prev = c_now - current[key]
        present = records[key]
        _require(0 <= c_prev <= present <= c_now,
                 f'dcp {dcp}: need C_prev {c_prev} <= records {present} <= C {c_now}')
        rows = by_dcp.get(dcp, [])
        ordinals = [r.ordinal for r in rows]
        _require(ordinals == list(range(present - len(rows) + 1, present + 1)),
                 f'dcp {dcp}: chunk entry ordinals are not contiguous up to records_cum')
        _require(present - len(rows) <= c_prev, f'dcp {dcp}: rows of this interval are missing from the chunk')
        mine = tuple(r for r in rows if c_prev < r.ordinal <= c_now)
        for r in mine:
            _require(start_s - BOUNDARY_EPS_S - _FUZZ <= r.t_entry <= end_s + BOUNDARY_EPS_S + _FUZZ,
                     f'dcp {dcp}: entry at {r.t_entry} lies outside ({start_s}, {end_s}]')
        entries[dcp] = mine
        tails[dcp] = c_now - present
    sum_tail = sum(tails.values())
    max_t_any = obs['mer']['max_t_any']
    ok = lag_ok(max_t_any, end_s, sum_tail)
    if not ok:
        raise ObsLagError(f'.mer lags at {end_s}: tail {sum_tail} with max_t_any {max_t_any}')
    return WindowAssignment(start_s, end_s, k, entries, tails, sum_tail, max_t_any, ok)


# --------------------------------------------------------------------------
# 1.3 Counting identity
# --------------------------------------------------------------------------
ORIENTATIONS = ('at', 'down', 'up')


@dataclass(frozen=True)
class SegmentPiece:
    """A path piece [from_m, to_m] on one link/connector; lanes None = every lane."""
    link: int
    from_m: float
    to_m: float
    lanes: tuple | None = None

    def as_json(self):
        return {'from_m': float(self.from_m), 'lanes': None if self.lanes is None else list(self.lanes),
                'link': self.link, 'to_m': float(self.to_m)}


def _piece_holds(piece, link, lane, pos, *, open_end, use_lane):
    if link != piece.link:
        return False
    if use_lane and piece.lanes is not None and lane not in piece.lanes:
        return False
    if pos < piece.from_m:
        return False
    return pos < piece.to_m if open_end else pos <= piece.to_m


def segment_contains(segment, orientation, link, lane, pos, *, use_lane=True):
    """Closure: every piece is closed, except that the LAST piece of a 'down'
    segment is open at its end (the station p). A vehicle whose front position
    q satisfies q >= x has crossed x."""
    _require(orientation in ('down', 'up'), 'Only offset stations have a segment')
    last = len(segment) - 1
    return any(_piece_holds(piece, link, lane, pos, open_end=(orientation == 'down' and i == last),
                            use_lane=use_lane)
               for i, piece in enumerate(segment))


def vehicles_in_segment(frame_vehicles, segment, orientation):
    """Vehicle numbers of a lane-plant-frame/v1 vehicle list inside the segment."""
    return {row[0] for row in frame_vehicles
            if segment_contains(segment, orientation, row[1], row[2], row[3])}


def identity_cross(orientation, vehs, n_end, n_start, removed):
    """Plan 1.3, the only formula:

    at   : cross_x = Vehs(x)
    down : in_x  = Vehs(p) + N_[x,p)(T) - N_[x,p)(T-150) + R_[x,p)
    up   : out_x = Vehs(p) + N_[p,x](T-150) - N_[p,x](T) - R_[p,x]
    """
    if orientation == 'at':
        _require(n_end == n_start == removed == 0, 'An exact station has no offset terms')
        return vehs
    if orientation == 'down':
        return vehs + n_end - n_start + removed
    if orientation == 'up':
        return vehs + n_start - n_end - removed
    raise ObsContractError('Unknown orientation ' + repr(orientation))


@dataclass(frozen=True)
class LaneTerms:
    lane: int
    vehs: int
    n_end: int
    n_start: int
    cross: int


@dataclass(frozen=True)
class IdentityTerms:
    boundary_ref: str
    role: str
    orientation: str
    vehs: int
    n_end: int
    n_start: int
    removed: int
    cross: int
    lanes: tuple            # LaneTerms per detector row, lane order
    lane_exact: bool        # per-lane terms are exact: R == 0 and no negative lane cross
    removed_vehicles: tuple  # removal vehicle ids counted in R, err order

    def as_dict(self):
        return {'boundary_ref': self.boundary_ref, 'role': self.role, 'orientation': self.orientation,
                'vehs': self.vehs, 'n_end': self.n_end, 'n_start': self.n_start, 'removed': self.removed,
                'cross': self.cross, 'lane_exact': self.lane_exact,
                'removed_vehicles': list(self.removed_vehicles),
                'lanes': [{'lane': t.lane, 'vehs': t.vehs, 'n_end': t.n_end, 'n_start': t.n_start,
                           'cross': t.cross} for t in self.lanes]}


def window_removals(err_rows, start_s, end_s):
    """lane_change_removal rows with start_s < time_sec <= end_s, err order."""
    return [r for r in err_rows if r.get('kind') == 'lane_change_removal'
            and start_s < r['time_sec'] <= end_s]


def evaluate_boundary(rows, detectors, frame_end, frame_start, removal_rows, start_s, end_s):
    """Identity terms of ONE boundary (all detector rows sharing a boundary_ref).

    detectors: raw 'detectors' ({dcm key: Vehs}); frames: lane-plant-frame/v1
    at end_s and start_s; removal_rows: err rows (any kind; filtered here).
    R has no lane (the .err line carries none), so R is station-level only.
    """
    _require(rows, 'A boundary needs detector rows')
    ref, role, orientation = rows[0].boundary_ref, rows[0].role, rows[0].orientation
    _require(all((r.boundary_ref, r.role, r.orientation) == (ref, role, orientation) for r in rows),
             'Rows of one boundary must share role and orientation')
    vehs = sum(detectors[str(r.dcm_no)] for r in rows)
    if orientation == 'at':
        lanes = tuple(LaneTerms(r.lane, detectors[str(r.dcm_no)], 0, 0, detectors[str(r.dcm_no)])
                      for r in sorted(rows, key=lambda r: r.lane))
        return IdentityTerms(ref, role, orientation, vehs, 0, 0, 0, vehs, lanes, True, ())
    end_vehicles, start_vehicles = frame_end['vehicles'], frame_start['vehicles']
    lanes, end_union, start_union = [], set(), set()
    for r in sorted(rows, key=lambda r: r.lane):
        at_end = vehicles_in_segment(end_vehicles, r.segment, orientation)
        at_start = vehicles_in_segment(start_vehicles, r.segment, orientation)
        end_union |= at_end
        start_union |= at_start
        v = detectors[str(r.dcm_no)]
        lanes.append(LaneTerms(r.lane, v, len(at_end), len(at_start),
                               identity_cross(orientation, v, len(at_end), len(at_start), 0)))
    removed = removals_in_boundary(window_removals(removal_rows, start_s, end_s), rows)
    cross = identity_cross(orientation, vehs, len(end_union), len(start_union), len(removed))
    _require(cross >= 0, f'{ref}: negative crossing count {cross}')
    exact = not removed and all(t.cross >= 0 for t in lanes)
    return IdentityTerms(ref, role, orientation, vehs, len(end_union), len(start_union), len(removed), cross,
                         tuple(lanes), exact, tuple(x['vehicle_id'] for x in removed))


def evaluate_boundaries(obs, detector_rows, frame_end, frame_start, err_rows):
    """IdentityTerms for every boundary_ref of the table, over the bundle's interval."""
    start_s, end_s, _ = bundle_interval(obs['sim_sec'])
    groups = defaultdict(list)
    for row in detector_rows:
        groups[row.boundary_ref].append(row)
    return {ref: evaluate_boundary(rows, obs['detectors'], frame_end, frame_start, err_rows, start_s, end_s)
            for ref, rows in sorted(groups.items())}


# --------------------------------------------------------------------------
# 1.7 Detector CSV
# --------------------------------------------------------------------------
DETECTOR_CSV_COLUMNS = ('dcp_no', 'dcm_no', 'role', 'ref', 'link', 'lane', 'pos', 'pos_mode', 'orientation',
                        'boundary_ref', 'segment_json', 'geometry_assert')
ROLE_ORIENTATIONS = {
    'head': ('at',), 'meter_head': ('at',),
    'off_entry': ('down',), 'destination': ('down',), 'ramp_arrival': ('down',), 'source': ('down',),
    'headfree': ('down',),
    'x10643_exit': ('up',), 'chain_end': ('up',),
    'through': ('at', 'down', 'up'),
}
ROLES = tuple(ROLE_ORIENTATIONS)
POS_MODES = ('exact', 'end_minus')
DETECTOR_KEY_RANGE = (960001, 969999)
POS_DECIMALS = 6
POS_READBACK_TOL_M = 1e-3
_REF_PATTERNS = {
    'head': r'[1-9][0-9]*\|[1-9][0-9]*-[1-9][0-9]*',
    'meter_head': r'[1-9][0-9]*\|[1-9][0-9]*-[1-9][0-9]*',
    'off_entry': r'[1-9][0-9]*', 'through': r'[1-9][0-9]*', 'destination': r'[1-9][0-9]*',
    'headfree': r'[1-9][0-9]*', 'x10643_exit': r'10643',
    'ramp_arrival': r'RM_C[1-9][0-9]*', 'source': r'FW_[EW]', 'chain_end': r'FW_[EW]',
}


@dataclass(frozen=True)
class DetectorRow:
    dcp_no: int
    dcm_no: int
    role: str
    ref: str
    link: int
    lane: int
    pos: float
    pos_mode: str
    orientation: str
    boundary_ref: str
    segment: tuple            # SegmentPiece, path order; () for 'at'
    geometry_assert: Mapping[str, Any]


def parse_head_ref(ref):
    """'<head_no>|<sc>-<sg>' -> (head_no, sc, sg) as strings."""
    _require(re.fullmatch(_REF_PATTERNS['head'], ref or '') is not None, 'Head ref must be <head>|<sc>-<sg>')
    head, sgkey = ref.split('|')
    sc, sg = sgkey.split('-')
    return head, sc, sg


def expected_boundary_ref(role, ref):
    """'<role>:<key>' where key is the head number for head roles, else ref."""
    _require(role in ROLE_ORIENTATIONS, 'Unknown detector role ' + repr(role))
    _require(isinstance(ref, str) and re.fullmatch(_REF_PATTERNS[role], ref) is not None,
             f'ref {ref!r} does not fit role {role}')
    key = ref.split('|')[0] if role in ('head', 'meter_head') else ref
    return f'{role}:{key}'


def _six(value):
    return _is_number(value) and float(value) == round(float(value), POS_DECIMALS)


def _validate_row(row):
    _require(isinstance(row, DetectorRow), 'Detector rows must be DetectorRow')
    lo, hi = DETECTOR_KEY_RANGE
    _require(_is_int(row.dcp_no) and lo <= row.dcp_no <= hi, f'dcp_no {row.dcp_no} outside {lo}..{hi}')
    _require(row.dcm_no == row.dcp_no, 'Each measurement is its own point (dcm_no == dcp_no)')
    _require(row.role in ROLE_ORIENTATIONS, 'Unknown detector role ' + repr(row.role))
    _require(row.orientation in ROLE_ORIENTATIONS[row.role], f'{row.role} cannot be oriented {row.orientation}')
    _require(row.pos_mode in POS_MODES, 'Unknown pos_mode')
    _require(row.boundary_ref == expected_boundary_ref(row.role, row.ref), 'boundary_ref differs from role/ref')
    _require(_is_int(row.link) and row.link > 0 and _is_int(row.lane) and row.lane >= 1, 'Invalid link/lane')
    _require(_six(row.pos) and row.pos >= 0, 'pos must be finite, >= 0 and rounded to 6 decimals')
    geometry = row.geometry_assert
    _require(isinstance(geometry, dict), 'geometry_assert must be an object')
    length, lanes = geometry.get('link_length_m'), geometry.get('lane_count')
    _require(_is_number(length) and length > 0 and _is_int(lanes) and lanes >= 1,
             'geometry_assert needs link_length_m and lane_count')
    _require(row.lane <= lanes, 'lane exceeds geometry_assert.lane_count')
    _require(row.pos <= length + POS_READBACK_TOL_M, 'pos lies beyond the link length')
    if row.pos_mode == 'end_minus':
        offset = geometry.get('offset_from_end_m')
        _require(_is_number(offset) and offset > 0, 'end_minus needs offset_from_end_m')
        _require(row.pos == round(length - offset, POS_DECIMALS), 'end_minus pos != link_length_m - offset_from_end_m')
    _require(isinstance(row.segment, tuple), 'segment must be a tuple of SegmentPiece')
    if row.orientation == 'at':
        _require(row.segment == (), 'An exact station has an empty segment')
        return
    _require(row.segment, 'An offset station needs its segment')
    for piece in row.segment:
        _require(isinstance(piece, SegmentPiece) and _is_int(piece.link) and piece.link > 0,
                 'Segment pieces must be SegmentPiece with a link')
        _require(_six(piece.from_m) and _six(piece.to_m) and 0 <= piece.from_m <= piece.to_m,
                 'Segment piece needs 0 <= from_m <= to_m rounded to 6 decimals')
        _require(piece.lanes is None or (isinstance(piece.lanes, tuple) and piece.lanes
                                         and all(_is_int(v) and v >= 1 for v in piece.lanes)),
                 'Segment piece lanes must be None or a tuple of lanes')
    if row.orientation == 'down':
        end = row.segment[-1]
        _require(end.link == row.link and end.to_m == row.pos and end.from_m < end.to_m,
                 'A down segment ends (open) at the station p')
    else:
        first = row.segment[0]
        _require(first.link == row.link and first.from_m == row.pos, 'An up segment starts at the station p')


def validate_detector_rows(rows):
    rows = tuple(rows)
    _require(rows, 'Empty detector table')
    for row in rows:
        _validate_row(row)
    keys = [r.dcp_no for r in rows]
    _require(keys == sorted(keys) and len(set(keys)) == len(keys), 'dcp_no must be unique and ascending')
    shape = {}
    for row in rows:
        seen = shape.setdefault(row.boundary_ref, (row.role, row.orientation))
        _require(seen == (row.role, row.orientation), 'Rows of one boundary_ref must share role/orientation')
    lanes = defaultdict(list)
    for row in rows:
        lanes[row.boundary_ref].append(row.lane)
    _require(all(len(v) == len(set(v)) for v in lanes.values()), 'One row per lane and boundary_ref')
    return rows


def _segment_json(segment):
    return json.dumps([p.as_json() for p in segment], sort_keys=True, separators=(',', ':'))


def format_detector_csv(rows):
    """Canonical bytes: ASCII, LF, header, rows by dcp_no, pos '%.6f', compact JSON."""
    rows = validate_detector_rows(rows)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(DETECTOR_CSV_COLUMNS)
    for r in rows:
        writer.writerow([r.dcp_no, r.dcm_no, r.role, r.ref, r.link, r.lane, format(r.pos, '.6f'), r.pos_mode,
                         r.orientation, r.boundary_ref, _segment_json(r.segment),
                         json.dumps(r.geometry_assert, sort_keys=True, separators=(',', ':'), allow_nan=False)])
    return buffer.getvalue().encode('ascii')


def _int_field(text, what):
    _require(re.fullmatch(r'0|[1-9][0-9]*', text) is not None, what + ' must be a plain decimal integer')
    return int(text)


def parse_detector_csv(data):
    """Parse and validate; the bytes must re-format to themselves (canonical)."""
    _require(isinstance(data, bytes), 'Detector CSV is bytes')
    _require(b'\r' not in data, 'Detector CSV uses LF line endings')
    try:
        text = data.decode('ascii')
    except UnicodeDecodeError as error:
        raise ObsContractError('Detector CSV must be ASCII') from error
    records = list(csv.reader(io.StringIO(text, newline='')))
    _require(records and tuple(records[0]) == DETECTOR_CSV_COLUMNS, 'Detector CSV header differs')
    rows = []
    for record in records[1:]:
        _require(len(record) == len(DETECTOR_CSV_COLUMNS), 'Detector CSV row width differs')
        (dcp, dcm, role, ref, link, lane, pos, pos_mode, orientation, boundary_ref,
         segment_text, geometry_text) = record
        _require(re.fullmatch(r'(0|[1-9][0-9]*)\.[0-9]{6}', pos) is not None, "pos must be written '%.6f'")
        try:
            pieces = json.loads(segment_text)
            geometry = json.loads(geometry_text)
        except json.JSONDecodeError as error:
            raise ObsContractError('Detector CSV JSON column does not parse') from error
        _require(isinstance(pieces, list), 'segment_json must be a JSON list')
        segment = []
        for p in pieces:
            _keys(p, ('from_m', 'lanes', 'link', 'to_m'), 'segment piece')
            lanes = p['lanes']
            _require(lanes is None or isinstance(lanes, list), 'piece lanes must be null or a list')
            segment.append(SegmentPiece(p['link'], p['from_m'], p['to_m'], None if lanes is None else tuple(lanes)))
        rows.append(DetectorRow(_int_field(dcp, 'dcp_no'), _int_field(dcm, 'dcm_no'), role, ref,
                                _int_field(link, 'link'), _int_field(lane, 'lane'), float(pos), pos_mode,
                                orientation, boundary_ref, tuple(segment), geometry))
    rows = validate_detector_rows(rows)
    _require(format_detector_csv(rows) == data, 'Detector CSV is not in canonical form')
    return rows


def read_detector_csv(path, expected_sha256=None):
    data = Path(path).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if expected_sha256 is not None:
        _require(digest == expected_sha256, 'Detector CSV sha256 differs from its pin')
    return parse_detector_csv(data), digest


def offset_boundary_refs(rows):
    """boundary_refs whose identity has offset terms (orientation down/up), sorted."""
    return sorted({r.boundary_ref for r in rows if r.orientation != 'at'})


def removals_in_boundary(removal_rows, rows):
    """Removal rows (any time) whose (link, position) lies in the boundary's segment; lanes ignored."""
    return [x for x in removal_rows if x.get('kind') == 'lane_change_removal'
            and any(segment_contains(r.segment, r.orientation, x['link'], None, x['position_m'], use_lane=False)
                    for r in rows)]


def group_boundaries(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row.boundary_ref].append(row)
    return {ref: tuple(sorted(v, key=lambda r: r.lane)) for ref, v in sorted(groups.items())}


# --------------------------------------------------------------------------
# 1.4 obs150-raw/v1, capture meta, chunks, frames, install record
# --------------------------------------------------------------------------
RAW_SCHEMA = 'obs150-raw/v1'
RAW_STATE_KEY = 'obs150'
RAW_KEYS = ('schema', 'sim_sec', 'k', 'window', 'directory', 'simres_steps_per_sec', 'run_id',
            'ground_truth_windows', 'detector_config', 'install_record', 'detectors', 'detectors_cum',
            'detectors_last_equal', 'rule_crosscheck', 'linkeval_volume_veh_h', 'mer', 'err', 'signal_log',
            'source_cumulative_vehs', 'frames')
RAW_KEYS_FIRST = RAW_KEYS + ('open_interval',)
MER_META_KEYS = ('source', 'chunk', 'chunk_sha256', 'index', 'index_sha256', 'prev_index_sha256',
                 'byte_start', 'byte_end', 'max_t_any', 'records_cum_by_dcp')
ERR_META_KEYS = ('source', 'chunk', 'chunk_sha256', 'byte_start', 'byte_end', 'partial_tail_bytes',
                 'max_sim_sec', 'removals', 'unparsed_removal_lines', 'removals_cum_by_boundary')
SIGNAL_LOG_KEYS = ('scs', 'start', 'events', 'complete')
SIGNAL_EVENT_KINDS = {'write': 5, 'fail': 6, 'own': 5}
ROADS = ('FW_E', 'FW_W')
LANE_META_CADENCE = 'decision_150s'
FRAME_SCHEMA = 'lane-plant-frame/v1'
FRAME_ROW_WIDTH = 15
FRAME_ROW_FIELDS = ('veh', 'link', 'lane', 'pos', 'speed_kmh', 'length_m', 'rout_dec_no', 'route_no',
                    'rout_dec_type', 'next_link', None, None, None, None, None)
MER_INDEX_SCHEMA = 'obs150-mer-index/v1'
MER_INDEX_ENTRY_KEYS = ('sim_sec', 'chunk', 'chunk_sha256', 'byte_start', 'byte_end', 'max_t_any',
                        'records_cum_by_dcp', 'prev_entry_sha256', 'entry_sha256')
INSTALL_SCHEMA = 'obs150-install/v1'
INSTALL_RECORD_PATH = 'obs150/obs150_install.json'
MER_INDEX_PATH = 'obs150/mer_index.json'
INSTALL_EVALUATION = {'DataCollCollectData': True, 'DataCollFromTime': 0, 'DataCollInterval': DECISION_INTERVAL_SEC,
                      'DataCollRawWriteFile': True, 'DataCollRawFromTime': 0}
INSTALL_EVALUATION_TO = ('DataCollToTime', 'DataCollRawToTime')
REMOVAL_KEYS = ('kind', 'message', 'byte_offset', 'raw_line_sha256', 'time_sec', 'wait_sec', 'vehicle_id',
                'route_decision', 'route_index', 'link', 'position_m')


def frame_path(t):
    return f'lane_observations/frame_{t:06d}.json'


def mer_chunk_path(t):
    return f'obs150/mer_{t:06d}.jsonl'


def err_chunk_path(t):
    return f'obs150/err_{t:06d}.jsonl'


def capture_meta_path(t):
    return f'obs150/capture_{t:06d}.json'


def derived_path(t):
    return f'obs150/derived_{t:06d}.json'


def resolve(obs, relative):
    """Relative bundle paths resolve against the bundle's 'directory' (the decision dir)."""
    _require(isinstance(relative, str) and '\\' not in relative and not PurePosixPath(relative).is_absolute(),
             'Bundle paths are forward-slash relative paths')
    return Path(obs['directory']) / Path(*PurePosixPath(relative).parts)


def _validate_mer_meta(mer, sim_sec):
    _keys(mer, MER_META_KEYS, 'raw.mer')
    _require(isinstance(mer['source'], str) and mer['source'].lower().endswith('.mer'), 'mer.source must be the .mer path')
    _require(mer['chunk'] == mer_chunk_path(sim_sec), 'mer.chunk name differs')
    _sha(mer['chunk_sha256'], 'mer.chunk_sha256')
    _require(mer['index'] == MER_INDEX_PATH, 'mer.index path differs')
    _sha(mer['index_sha256'], 'mer.index_sha256')
    if sim_sec == FIRST_DECISION_SEC:
        _require(mer['prev_index_sha256'] is None and mer['byte_start'] == 0, 'The first capture starts the chain')
    else:
        _sha(mer['prev_index_sha256'], 'mer.prev_index_sha256')
    _nonneg_int(mer['byte_start'], 'mer.byte_start')
    _nonneg_int(mer['byte_end'], 'mer.byte_end')
    _require(mer['byte_start'] <= mer['byte_end'], 'mer byte range reversed')
    if mer['max_t_any'] is not None:
        _nonneg_number(mer['max_t_any'], 'mer.max_t_any')
    _require(isinstance(mer['records_cum_by_dcp'], dict), 'mer.records_cum_by_dcp must be an object')
    for key, value in mer['records_cum_by_dcp'].items():
        _uint_key(key, 'mer.records_cum_by_dcp')
        _nonneg_int(value, 'mer.records_cum_by_dcp value')


def _validate_err_meta(err, sim_sec):
    _keys(err, ERR_META_KEYS, 'raw.err')
    _require(isinstance(err['source'], str) and err['source'].lower().endswith('.err'), 'err.source must be the .err path')
    _require(err['chunk'] == err_chunk_path(sim_sec), 'err.chunk name differs')
    _sha(err['chunk_sha256'], 'err.chunk_sha256')
    for key in ('byte_start', 'byte_end', 'partial_tail_bytes', 'removals', 'unparsed_removal_lines'):
        _nonneg_int(err[key], 'err.' + key)
    _require(err['byte_start'] <= err['byte_end'], 'err byte range reversed')
    if sim_sec == FIRST_DECISION_SEC:
        _require(err['byte_start'] == 0, 'The first capture reads the .err from byte 0')
    _require(err['max_sim_sec'] is None or _is_number(err['max_sim_sec']), 'err.max_sim_sec')
    _require(err['unparsed_removal_lines'] == 0, 'A removal line did not parse: the capture must fail')
    _require(isinstance(err['removals_cum_by_boundary'], dict), 'err.removals_cum_by_boundary must be an object')
    for key, value in err['removals_cum_by_boundary'].items():
        _require(isinstance(key, str) and ':' in key, 'removals_cum_by_boundary keys are boundary_refs')
        _nonneg_int(value, 'removals_cum_by_boundary value')


def validate_capture_meta(meta, sim_sec):
    """What obs150_capture.capture returns and the CLI writes to capture_<T>.json."""
    _keys(meta, ('mer', 'err'), 'capture meta')
    _validate_mer_meta(meta['mer'], sim_sec)
    _validate_err_meta(meta['err'], sim_sec)


def capture_meta_bytes(meta, sim_sec):
    """The CLI's file: one line, ASCII, key order mer then err, no newline (VBS splices Mid(text,2,len-2))."""
    validate_capture_meta(meta, sim_sec)
    return json.dumps({'mer': meta['mer'], 'err': meta['err']}, ensure_ascii=True,
                      separators=(',', ':'), allow_nan=False).encode('ascii')


def validate_signal_log(log, start_s, end_s):
    _keys(log, SIGNAL_LOG_KEYS, 'raw.signal_log')
    scs = log['scs']
    _require(isinstance(scs, list) and scs and len(set(scs)) == len(scs), 'signal_log.scs must list unique SCs')
    for sc in scs:
        _require(isinstance(sc, str) and _UINT.match(sc) is not None, 'signal_log.scs holds SC numbers as strings')
    start = log['start']
    _require(isinstance(start, dict) and start, 'signal_log.start must be an object')
    owner, verified = {}, True
    for key, entry in start.items():
        match = _SGKEY.match(key) if isinstance(key, str) else None
        _require(match is not None and match[1] in scs, 'signal_log.start key must be <sc>-<sg> of a listed SC')
        _require(isinstance(entry, dict) and entry.get('owner') in ('native', 'com'), 'start owner native|com')
        if entry['owner'] == 'native':
            _keys(entry, ('owner',), 'native start entry')
        else:
            _keys(entry, ('owner', 'state', 'verified'), 'com start entry')
            _require(isinstance(entry['state'], str) and entry['state'] == entry['state'].upper() and entry['state'],
                     'com start state must be the upper-case SigState')
            _require(type(entry['verified']) is bool, 'com start verified must be boolean')
            verified = verified and entry['verified']
        owner[key] = entry['owner']
    _require({_SGKEY.match(k)[1] for k in start} == set(scs), 'Every listed SC needs its SG start entries')
    last_t, failed = None, False
    events = log['events']
    _require(isinstance(events, list), 'signal_log.events must be a list')
    for event in events:
        _require(isinstance(event, list) and len(event) >= 4, 'Signal event must be a list')
        t, sc, sg, kind = event[:4]
        _require(kind in SIGNAL_EVENT_KINDS and len(event) == SIGNAL_EVENT_KINDS[kind], 'Signal event kind/arity')
        # CONTRACT 2.3: a COM write at the stop t reaches the heads at t+1, so the writes at the
        # window's first stop T-150 are events of this window; those at T belong to the next.
        _require(_is_int(t) and start_s <= t < end_s, f'Signal event time {t} outside [{start_s}, {end_s})')
        _require(last_t is None or t >= last_t, 'Signal events must be time ordered')
        last_t = t
        key = f'{sc}-{sg}'
        _require(isinstance(sc, str) and isinstance(sg, str) and key in start, 'Signal event SG lacks a start entry')
        if kind == 'own':
            _require(type(event[4]) is bool, 'own event carries the ContrByCOM readback boolean')
            owner[key] = 'com' if event[4] else 'native'
            continue
        _require(owner[key] == 'com', f'{kind} on native-owned SG {key}')
        _require(isinstance(event[4], str) and event[4] == event[4].upper() and event[4], 'Signal state upper-case')
        if kind == 'fail':
            _require(isinstance(event[5], str) and event[5], 'fail event detail')
            failed = True
    _require(type(log['complete']) is bool, 'signal_log.complete must be boolean')
    if failed or not verified:
        _require(log['complete'] is False, 'A window with unverified signal time cannot be complete')


def validate_raw(obs, rows=None, *, expected_simres=None):
    """Strict obs150-raw/v1 validation. rows (DetectorRow) enables cross-checks."""
    _require(isinstance(obs, dict) and obs.get('schema') == RAW_SCHEMA, 'Unsupported obs150 raw schema')
    sim_sec = obs.get('sim_sec')
    _require(is_decision_stop(sim_sec), 'raw.sim_sec must be 1 or a multiple of 150')
    start_s, end_s, k = bundle_interval(sim_sec)
    first = sim_sec == FIRST_DECISION_SEC
    _keys(obs, RAW_KEYS_FIRST if first else RAW_KEYS, 'obs150 raw')
    if first:
        _require(obs['k'] is None and obs['window'] is None, 't=1 has no closed window')
        _require(obs['open_interval'] == {'k': 1, 'end_s': 1}, 't=1 carries open_interval {k:1,end_s:1}')
        _require(obs['detectors_last_equal'] is None, 't=1 has no Last interval')
    else:
        _require(obs['k'] == k and _is_int(obs['k']), 'raw.k must be sim_sec/150')
        _require(obs['window'] == {'start_s': start_s, 'end_s': end_s}, 'raw.window must be (T-150, T]')
        _require(obs['detectors_last_equal'] is True, '(Current,Last,All) and (Current,k,All) disagree')
    _require(isinstance(obs['directory'], str) and obs['directory'], 'raw.directory must be the decision dir')
    simres = obs['simres_steps_per_sec']
    _require(_is_int(simres) and simres >= 1, 'raw.simres_steps_per_sec')
    if expected_simres is not None:
        _require(simres == expected_simres, 'raw SimRes differs from the manifest')
    _require(isinstance(obs['run_id'], str) and obs['run_id'], 'raw.run_id')
    _validate_gt_windows(obs['ground_truth_windows'])
    config = obs['detector_config']
    _keys(config, ('path', 'sha256', 'rows'), 'raw.detector_config')
    _sha(config['sha256'], 'detector_config.sha256')
    _require(_is_int(config['rows']) and config['rows'] > 0, 'detector_config.rows')
    _keys(obs['install_record'], ('path', 'sha256'), 'raw.install_record')
    _require(obs['install_record']['path'] == INSTALL_RECORD_PATH, 'install_record path differs')
    _sha(obs['install_record']['sha256'], 'install_record.sha256')
    detectors, cum = obs['detectors'], obs['detectors_cum']
    _require(isinstance(detectors, dict) and isinstance(cum, dict) and set(detectors) == set(cum),
             'detectors and detectors_cum must share keys')
    for key in detectors:
        _uint_key(key, 'raw.detectors')
        _nonneg_int(detectors[key], 'raw.detectors value')
        _nonneg_int(cum[key], 'raw.detectors_cum value')
        _require(cum[key] >= detectors[key], 'detectors_cum below the interval count')
        if first:
            _require(cum[key] == detectors[key], 'At t=1 detectors_cum equals the open-interval count')
    _require(isinstance(obs['rule_crosscheck'], dict) and isinstance(obs['linkeval_volume_veh_h'], dict),
             'rule_crosscheck and linkeval_volume_veh_h must be objects')
    for key, value in obs['rule_crosscheck'].items():
        _uint_key(key, 'raw.rule_crosscheck')
        _nonneg_int(value, 'raw.rule_crosscheck value')
    for key, value in obs['linkeval_volume_veh_h'].items():
        _uint_key(key, 'raw.linkeval_volume_veh_h')
        _require(value is None or (_is_number(value) and value >= 0), 'linkeval volume must be >= 0 or null')
    _validate_mer_meta(obs['mer'], sim_sec)
    _validate_err_meta(obs['err'], sim_sec)
    records = obs['mer']['records_cum_by_dcp']
    _require(set(records) == set(detectors), 'records_cum_by_dcp keys must equal the detector keys')
    for key in detectors:
        _require(cum[key] - detectors[key] <= records[key] <= cum[key],
                 f'dcp {key}: .mer records outside [C_prev, C]')
    validate_signal_log(obs['signal_log'], start_s, end_s)
    sources = obs['source_cumulative_vehs']
    _keys(sources, ROADS, 'raw.source_cumulative_vehs')
    for road in ROADS:
        _nonneg_int(sources[road], 'source_cumulative_vehs.' + road)
    frames = obs['frames']
    _keys(frames, ('current', 'previous'), 'raw.frames')
    _keys(frames['current'], ('path', 'sha256', 'vehicles'), 'raw.frames.current')
    _require(frames['current']['path'] == frame_path(end_s), 'frames.current path differs')
    _sha(frames['current']['sha256'], 'frames.current.sha256')
    _nonneg_int(frames['current']['vehicles'], 'frames.current.vehicles')
    _keys(frames['previous'], ('path', 'sha256'), 'raw.frames.previous')
    _require(frames['previous']['path'] == frame_path(start_s), 'frames.previous must be the interval-start frame')
    _sha(frames['previous']['sha256'], 'frames.previous.sha256')
    if rows is not None:
        rows = tuple(rows)
        _require(config['rows'] == len(rows), 'detector_config.rows differs from the table')
        _require(set(detectors) == {str(r.dcm_no) for r in rows}, 'raw.detectors keys differ from the table')
        _require(set(obs['err']['removals_cum_by_boundary']) == set(offset_boundary_refs(rows)),
                 'removals_cum_by_boundary must list every offset boundary of the table')
        for road in ROADS:
            total = sum(cum[str(r.dcm_no)] for r in rows if r.role == 'source' and r.ref == road)
            _require(sources[road] == total, 'source_cumulative_vehs differs from the source stations')


def validate_lane_meta_v2(meta, raw):
    """state['lane_plant_observation'] in obs150 mode (A7.1)."""
    _keys(meta, ('directory', 'run_id', 'time_s', 'cadence'), 'lane_plant_observation v2 meta')
    _require(meta['cadence'] == LANE_META_CADENCE, 'lane meta cadence must be decision_150s')
    _require(meta['run_id'] == raw['run_provenance']['run_id'] and meta['time_s'] == raw['sim_sec'],
             'lane meta identity differs from the state')


def validate_frame(frame, time_s):
    _require(isinstance(frame, dict), 'Frame must be an object')
    _keys(frame, ('schema', 'complete', 'time_s', 'run_id', 'vehicles'), 'lane frame')
    _require(frame['schema'] == FRAME_SCHEMA and frame['complete'] is True and frame['time_s'] == time_s,
             'Frame schema/time differs')
    seen = set()
    for row in frame['vehicles']:
        _require(isinstance(row, list) and len(row) == FRAME_ROW_WIDTH, 'Frame rows have 15 fields')
        veh, link, lane, pos, speed, length = row[:6]
        _require(all(_is_int(v) and v > 0 for v in (veh, link, lane)), 'Frame vehicle/link/lane identity')
        _require(all(_is_number(v) and v >= 0 for v in (pos, speed, length)) and length > 0,
                 'Frame position/speed/length')
        _require(veh not in seen, 'Duplicate vehicle in frame')
        seen.add(veh)
    if time_s == 0:
        _require(not frame['vehicles'], 'frame_000000 is the empty start state')


def _read_text(path):
    data = Path(path).read_bytes()
    if data.startswith((b'\xff\xfe', b'\xfe\xff')):
        return data, data.decode('utf-16')
    return data, data.decode('utf-8-sig')


def load_frame(path, sha256, time_s):
    data, text = _read_text(path)
    _require(hashlib.sha256(data).hexdigest() == sha256, 'Frame bytes differ from their pin: ' + str(path))
    frame = json.loads(text)
    validate_frame(frame, time_s)
    return frame


def validate_mer_row(value):
    _require(isinstance(value, list) and len(value) == len(MER_ROW_FIELDS), 'mer row is a 9-element array')
    seq, dcp, t_entry, t_exit, veh, vtype, v_kmh, length, ordinal = value
    _require(_is_int(seq) and seq >= 0 and _is_int(dcp) and dcp > 0, 'mer row seq/dcp')
    _require(t_entry is not None or t_exit is not None, 'mer row needs an entry or exit time')
    for t in (t_entry, t_exit):
        _require(t is None or (_is_number(t) and t >= 0 and abs(t * 100 - round(t * 100)) < 1e-6),
                 'mer times are >= 0 and rounded to 0.01 s')
    _require(_is_int(veh) and veh > 0 and _is_int(vtype), 'mer row vehicle/type')
    for v in (v_kmh, length):
        _require(v is None or _is_number(v), 'mer row speed/length')
    _require((ordinal is None) == (t_entry is None) and (ordinal is None or (_is_int(ordinal) and ordinal >= 1)),
             'An entry row carries its ordinal; an exit-only row carries null')
    return MerRow(*[float(x) if i in (2, 3, 6, 7) and x is not None else x for i, x in enumerate(value)])


def validate_err_row(row):
    _require(isinstance(row, dict) and isinstance(row.get('kind'), str), 'err row must carry kind')
    _require('line_number' not in row, 'err rows drop chunk-relative line_number')
    _nonneg_int(row.get('byte_offset'), 'err row byte_offset')
    _sha(row.get('raw_line_sha256'), 'err row raw_line_sha256')
    _require(isinstance(row.get('message'), str), 'err row message')
    if row['kind'] == 'lane_change_removal':
        _keys(row, REMOVAL_KEYS, 'removal row')
        _require(all(_is_int(row[k]) for k in ('vehicle_id', 'route_decision', 'route_index', 'link')),
                 'removal ids are integers (link normalized to int)')
        _require(all(_is_number(row[k]) for k in ('time_sec', 'wait_sec', 'position_m')), 'removal numbers')
    return row


def _load_jsonl(path, sha256):
    data = Path(path).read_bytes()
    _require(hashlib.sha256(data).hexdigest() == sha256, 'Chunk bytes differ from their pin: ' + str(path))
    _require(b'\r' not in data and (not data or data.endswith(b'\n')), 'Chunks are LF-terminated JSONL')
    return [json.loads(line) for line in data.decode('utf-8').splitlines()]


def load_mer_chunk(path, sha256):
    rows = [validate_mer_row(v) for v in _load_jsonl(path, sha256)]
    _require(all(a.seq < b.seq for a, b in zip(rows, rows[1:])), 'mer chunk rows must be in seq order')
    return rows


def load_err_chunk(path, sha256):
    rows = [validate_err_row(v) for v in _load_jsonl(path, sha256)]
    _require(all(a['byte_offset'] < b['byte_offset'] for a, b in zip(rows, rows[1:])),
             'err chunk rows must be in file order')
    return rows


def mer_index_entry_sha256(entry):
    return canonical_sha256({k: v for k, v in entry.items() if k != 'entry_sha256'})


def validate_mer_index(document):
    """{'schema','source','entries':[...]} whose entries form an sha chain."""
    _keys(document, ('schema', 'source', 'entries'), 'mer index')
    _require(document['schema'] == MER_INDEX_SCHEMA, 'Unsupported mer index schema')
    previous = None
    for entry in document['entries']:
        _keys(entry, MER_INDEX_ENTRY_KEYS, 'mer index entry')
        _require(entry['prev_entry_sha256'] == previous, 'mer index chain is broken')
        _require(entry['entry_sha256'] == mer_index_entry_sha256(entry), 'mer index entry hash differs')
        previous = entry['entry_sha256']
    return {e['sim_sec']: e for e in document['entries']}


@dataclass(frozen=True)
class Bundle:
    obs: Mapping[str, Any]
    mer_rows: tuple
    err_rows: tuple
    frame_end: Mapping[str, Any]
    frame_start: Mapping[str, Any]


def load_bundle(raw):
    """Load and sha-verify everything raw['obs150'] pins (chunks, index entry, frames)."""
    obs = raw[RAW_STATE_KEY]
    start_s, end_s, _ = bundle_interval(obs['sim_sec'])
    mer, err, frames = obs['mer'], obs['err'], obs['frames']
    index = validate_mer_index(json.loads(resolve(obs, mer['index']).read_text(encoding='utf-8')))
    entry = index.get(obs['sim_sec'])
    _require(entry is not None and entry['entry_sha256'] == mer['index_sha256']
             and entry['prev_entry_sha256'] == mer['prev_index_sha256']
             and entry['chunk_sha256'] == mer['chunk_sha256']
             and entry['records_cum_by_dcp'] == mer['records_cum_by_dcp'],
             'mer index entry differs from the raw bundle')
    return Bundle(obs,
                  tuple(load_mer_chunk(resolve(obs, mer['chunk']), mer['chunk_sha256'])),
                  tuple(load_err_chunk(resolve(obs, err['chunk']), err['chunk_sha256'])),
                  load_frame(resolve(obs, frames['current']['path']), frames['current']['sha256'], end_s),
                  load_frame(resolve(obs, frames['previous']['path']), frames['previous']['sha256'], start_s))


def validate_install_record(record, rows):
    _keys(record, ('schema', 'run_id', 'detector_config', 'simres_steps_per_sec', 'points', 'evaluation'),
          'install record')
    _require(record['schema'] == INSTALL_SCHEMA, 'Unsupported install record schema')
    rows = tuple(rows)
    _keys(record['detector_config'], ('path', 'sha256', 'rows'), 'install detector_config')
    _require(record['detector_config']['rows'] == len(rows), 'install rows differ from the table')
    _require(record['simres_steps_per_sec'] == EXPECTED_SIMRES, 'install SimRes must be 10')
    points = record['points']
    _require(isinstance(points, list) and len(points) == len(rows), 'One install point per table row')
    for point, row in zip(points, rows):
        _keys(point, ('dcp_no', 'dcm_no', 'link', 'lane', 'pos', 'readback'), 'install point')
        _require((point['dcp_no'], point['dcm_no'], point['link'], point['lane']) ==
                 (row.dcp_no, row.dcm_no, row.link, row.lane)
                 and _is_number(point['pos']) and abs(point['pos'] - row.pos) <= 1e-9,
                 f'install point {point.get("dcp_no")} differs from the table')
        back = point['readback']
        _keys(back, ('link', 'lane', 'pos'), 'install readback')
        _require(back['link'] == row.link and back['lane'] == row.lane
                 and _is_number(back['pos']) and abs(back['pos'] - row.pos) <= POS_READBACK_TOL_M,
                 f'install readback of {row.dcp_no} differs')
    evaluation = record['evaluation']
    _keys(evaluation, tuple(INSTALL_EVALUATION) + INSTALL_EVALUATION_TO, 'install evaluation')
    for key, value in INSTALL_EVALUATION.items():
        _require(evaluation[key] == value and type(evaluation[key]) is type(value), 'install evaluation ' + key)
    for key in INSTALL_EVALUATION_TO:
        _require(_is_int(evaluation[key]) and evaluation[key] > 0, 'install evaluation ' + key)


# --------------------------------------------------------------------------
# 1.5 Derived schemas
# --------------------------------------------------------------------------
DERIVED_SCHEMA = 'obs150-derived/v1'
LANE_OBS_SCHEMA_V2 = 'lane-plant-observation/v2'
HEAD_WINDOW_SCHEMA_V2 = 'physical-head-window/v2'
HEAD_EXPOSURE_METHOD_V2 = 'runner_write_log+sig_program'
FREEWAY_EXIT_PROVENANCE = 'conservation_v2'
MERGED_DERIVED_KEY = 'obs150_derived'
BYPASS_SOURCE_LINK = '403'
HEADFREE_CONNECTORS = ('10565', '10570')
OFFRAMP_10643 = '10643'
ROUTE_DECISION_10643 = 1126
DESTINATION_CONNECTORS_10643 = ('10634', '10635', '10642')
EXPECTED_OFFRAMP_COUNT = 8
SHARE_TOL = 1e-12
LANE_PART_KEYS = ('off_split', 'ramp_arrival_shares', 'offramp_10643_history', 'offramp_10643_lane_shares',
                  'ledger_10643', 'freeway_exit_count', 'source_boundary', 'link_departures_window',
                  'edie_residuals')
DERIVED_KEYS = ('schema', 'sim_sec', 'k', 'window', 'run_id', 'strict', 'inputs', 'boundaries', 'lag', 'tails',
                'boundary_ambiguous', 'removals', 'head_window') + LANE_PART_KEYS
DERIVED_INPUT_KEYS = ('raw_sha256', 'detector_config_sha256', 'mer_chunk_sha256', 'mer_index_sha256',
                      'err_chunk_sha256', 'frame_current_sha256', 'frame_previous_sha256')
LANE_OBS_V2_KEYS = ('schema', 'information_cutoff_s', 'history_start_s', 'future_traffic_inputs',
                    'lane_group_dynamics', 'current_exit_labels', 'off_split_ratio', 'off_split_history', 'frames',
                    'ramp_arrival_shares', 'offramp_10643_history', 'offramp_10643_lane_shares',
                    'freeway_exit_count', 'source_boundary', 'source')
LANE_OBS_SOURCE_KEYS = ('run_id', 'manifest_sha256', 'derived_sha256') + DERIVED_INPUT_KEYS
OFF_SPLIT_HISTORY_KEYS = ('downstream_veh', 'off_veh', 'post_branch_ramp_bypass_veh', 'eligible_exits_veh')
SOURCE_BOUNDARY_KEYS = ('admitted_window', 'admitted_cum', 'interval_s', 'recent_vph', 'schedule_integral_veh',
                        'backlog_veh')
HEAD_WINDOW_V2_KEYS = ('schema', 'config_sha256', 'detector_config_sha256', 'start_sec', 'end_sec', 'cadence_sec',
                       'exposure_method', 'clock_complete', 'heads', 'bypass_link_exits')
HEAD_IDENTITY_KEYS = ('head_id', 'link', 'lane', 'position_m', 'sc', 'sg')
HEAD_COUNT_KEYS = ('crossings', 'qualified_crossings', 'green_sec', 'native_sec', 'controlled_sec',
                   'unverified_sec', 'boundary_ambiguous')
CLOCK_KEYS = ('green', 'native_sec', 'controlled_sec', 'unverified_sec', 'complete')
IDENTITY_TERM_KEYS = ('boundary_ref', 'role', 'orientation', 'vehs', 'n_end', 'n_start', 'removed', 'cross',
                      'lane_exact', 'removed_vehicles', 'lanes')
LEDGER_SOURCES = ('frame', 'destination', 'removal', 'unidentified')


def validate_clocks(clocks, window):
    """obs150_signal_clock.windows output: {'<sc>-<sg>': clock} over window (T-150, T]."""
    start_s, end_s = window['start_s'], window['end_s']
    length = end_s - start_s
    _require(isinstance(clocks, dict), 'clocks must be an object')
    for key, clock in clocks.items():
        _require(isinstance(key, str) and _SGKEY.match(key) is not None, 'clock keys are <sc>-<sg>')
        _keys(clock, CLOCK_KEYS, 'clock ' + key)
        last = None
        green = 0
        for pair in clock['green']:
            _require(isinstance(pair, (list, tuple)) and len(pair) == 2 and all(_is_int(v) for v in pair),
                     'green intervals are integer pairs (a, b]')
            a, b = pair
            _require(start_s <= a < b <= end_s, f'green interval {pair} outside the window')
            _require(last is None or last < a, 'green intervals are sorted, disjoint and merged')
            last = b
            green += b - a
        for name in ('native_sec', 'controlled_sec', 'unverified_sec'):
            _nonneg_int(clock[name], key + '.' + name)
        _require(clock['native_sec'] + clock['controlled_sec'] + clock['unverified_sec'] == length,
                 key + ': owned seconds must cover the window')
        _require(green <= clock['native_sec'] + clock['controlled_sec'], key + ': green inside unverified time')
        _require(type(clock['complete']) is bool, key + '.complete')
        if clock['unverified_sec']:
            _require(clock['complete'] is False, key + ': unverified time makes the clock incomplete')


def validate_head_window_v2(window, *, end_sec=None, detector_config_sha256=None):
    _keys(window, HEAD_WINDOW_V2_KEYS, 'physical-head-window/v2')
    _require(window['schema'] == HEAD_WINDOW_SCHEMA_V2, 'Unsupported head window schema')
    _sha(window['config_sha256'], 'head window config_sha256')
    _sha(window['detector_config_sha256'], 'head window detector_config_sha256')
    if detector_config_sha256 is not None:
        _require(window['detector_config_sha256'] == detector_config_sha256, 'Head window detector table differs')
    start, end = window['start_sec'], window['end_sec']
    _require(_is_int(start) and _is_int(end) and end - start == DECISION_INTERVAL_SEC
             and window['cadence_sec'] == DECISION_INTERVAL_SEC, 'Head window is one 150 s window')
    if end_sec is not None:
        _require(end == end_sec, 'Head window must end at the state time')
    _require(window['exposure_method'] == HEAD_EXPOSURE_METHOD_V2, 'Head window exposure method differs')
    _require(type(window['clock_complete']) is bool, 'clock_complete must be boolean')
    seen, unverified = set(), 0
    _require(isinstance(window['heads'], list) and window['heads'], 'Head window needs its head rows')
    for row in window['heads']:
        _keys(row, HEAD_IDENTITY_KEYS + HEAD_COUNT_KEYS, 'head row')
        _require(all(isinstance(row[k], str) for k in ('head_id', 'link', 'sc', 'sg'))
                 and _is_int(row['lane']) and _is_number(row['position_m']), 'head identity types')
        _require(row['head_id'] not in seen, 'Duplicate head row')
        seen.add(row['head_id'])
        for key in HEAD_COUNT_KEYS:
            _nonneg_int(row[key], 'head ' + key)
        _require(row['qualified_crossings'] <= row['crossings'], 'qualified_crossings exceeds crossings')
        _require(row['native_sec'] + row['controlled_sec'] + row['unverified_sec'] == DECISION_INTERVAL_SEC,
                 'Head exposure must cover the window')
        _require(row['green_sec'] <= row['native_sec'] + row['controlled_sec'], 'Head green exceeds verified time')
        unverified += row['unverified_sec']
    if unverified:
        _require(window['clock_complete'] is False, 'Unverified head time makes the window incomplete')
    bypass = window['bypass_link_exits']
    _require(isinstance(bypass, dict), 'bypass_link_exits must be an object')
    for key, value in bypass.items():
        _uint_key(key, 'bypass_link_exits')
        _nonneg_int(value, 'bypass_link_exits value')


def _validate_shares(values, what, n=None):
    _require(isinstance(values, list) and values and (n is None or len(values) == n), what + ' length')
    _require(all(_is_number(v) and v >= 0 for v in values), what + ' must be non-negative')
    _require(abs(math.fsum(values) - 1) <= SHARE_TOL, what + ' must sum to 1')


def _validate_source_boundary(block):
    _keys(block, ROADS, 'source_boundary')
    for road in ROADS:
        row = block[road]
        _keys(row, SOURCE_BOUNDARY_KEYS, 'source_boundary.' + road)
        _nonneg_int(row['admitted_window'], road + '.admitted_window')
        _nonneg_int(row['admitted_cum'], road + '.admitted_cum')
        _require(row['interval_s'] in (FIRST_DECISION_SEC, DECISION_INTERVAL_SEC), road + '.interval_s')
        recent = _nonneg_number(row['recent_vph'], road + '.recent_vph')
        _require(abs(recent - 3600.0 * row['admitted_window'] / row['interval_s']) <= 1e-9 * max(1.0, recent),
                 road + ': recent_vph must be 3600*admitted_window/interval_s')
        integral = _nonneg_number(row['schedule_integral_veh'], road + '.schedule_integral_veh')
        backlog = _nonneg_number(row['backlog_veh'], road + '.backlog_veh')
        _require(abs(backlog - max(0.0, integral - row['admitted_cum'])) <= 1e-9 * max(1.0, integral),
                 road + ': backlog must be max(0, schedule integral - admitted_cum)')


def _validate_offramp_history(history, cutoff):
    _keys(history, ('off_composition', 'background', 'exchange_rates', 'information_cutoff_s', 'history_start_s',
                    'endogenous_background'), 'offramp_10643_history')
    _require(history['background'] == {} and history['exchange_rates'] == []
             and history['endogenous_background'] is True, 'offramp_10643_history closure fields')
    _require(history['information_cutoff_s'] == cutoff and history['history_start_s'] == max(0, cutoff - 150),
             'offramp_10643_history time fields')
    composition = history['off_composition']
    _require(isinstance(composition, list) and len(composition) == 2, 'off_composition has the two 10643 lanes')
    for lane in composition:
        _require(isinstance(lane, list) and lane, 'off_composition lane must be a non-empty list')
        for pair in lane:
            _require(isinstance(pair, list) and len(pair) == 2 and (pair[0] is None or _is_int(pair[0])),
                     'off_composition entries are [connector|null, share]')
        _validate_shares([p[1] for p in lane], 'off_composition shares')


def _validate_lane_shares_and_splits(off_split_ratio, history, ramp_shares, lane_shares):
    _require(isinstance(off_split_ratio, dict) and set(off_split_ratio) == set(history), 'off split keys differ')
    _require(len(off_split_ratio) == EXPECTED_OFFRAMP_COUNT and OFFRAMP_10643 in off_split_ratio,
             'Eight off-ramp splits including 10643')
    for off, ratio in off_split_ratio.items():
        _uint_key(off, 'off_split')
        row = history[off]
        _keys(row, OFF_SPLIT_HISTORY_KEYS, 'off_split_history.' + off)
        for key in OFF_SPLIT_HISTORY_KEYS:
            _nonneg_int(row[key], off + '.' + key)
        _require(row['post_branch_ramp_bypass_veh'] == 0, '31-cell geometry has no bypass pairs')
        _require(row['eligible_exits_veh'] == row['off_veh'] + row['downstream_veh'], off + ': eligible exits')
        expected = row['off_veh'] / row['eligible_exits_veh'] if row['eligible_exits_veh'] else 0.0
        _require(_is_number(ratio) and ratio == expected, off + ': split must be off/(off+through)')
    _require(isinstance(ramp_shares, dict) and ramp_shares, 'ramp_arrival_shares must be an object')
    for name, shares in ramp_shares.items():
        _validate_shares(shares, 'ramp_arrival_shares.' + name)
    _validate_shares(lane_shares, 'offramp_10643_lane_shares', 2)


def validate_lane_observation_v2(observation):
    _keys(observation, LANE_OBS_V2_KEYS, 'lane-plant-observation/v2')
    _require(observation['schema'] == LANE_OBS_SCHEMA_V2, 'Unsupported lane observation schema')
    cutoff = observation['information_cutoff_s']
    _require(is_decision_stop(cutoff), 'information_cutoff_s must be a decision time')
    _require(observation['history_start_s'] == max(0, cutoff - DECISION_INTERVAL_SEC), 'history_start_s')
    _require(observation['future_traffic_inputs'] is False, 'future_traffic_inputs must be false')
    _require(observation['lane_group_dynamics'] == {} and observation['current_exit_labels'] == {},
             'v2 carries no lane-group dynamics or exit labels')
    frames = observation['frames']
    _require(isinstance(frames, list) and len(frames) == 1, 'v2 carries exactly frame_T')
    validate_frame(frames[0], cutoff)
    history = observation['off_split_history']
    _require(isinstance(history, dict), 'off_split_history must be an object')
    _validate_lane_shares_and_splits(observation['off_split_ratio'], history, observation['ramp_arrival_shares'],
                                     observation['offramp_10643_lane_shares'])
    _validate_offramp_history(observation['offramp_10643_history'], cutoff)
    _nonneg_int(observation['freeway_exit_count'], 'freeway_exit_count')
    _validate_source_boundary(observation['source_boundary'])
    _keys(observation['source'], LANE_OBS_SOURCE_KEYS, 'lane observation source')
    for key in LANE_OBS_SOURCE_KEYS:
        if key != 'run_id':
            _sha(observation['source'][key], 'source.' + key)


def validate_derived(derived):
    _keys(derived, DERIVED_KEYS, 'obs150-derived/v1')
    _require(derived['schema'] == DERIVED_SCHEMA, 'Unsupported derived schema')
    sim_sec = derived['sim_sec']
    start_s, end_s, k = bundle_interval(sim_sec)
    _require(derived['k'] == k and derived['window'] == (None if k is None else {'start_s': start_s, 'end_s': end_s}),
             'derived k/window differ from sim_sec')
    _require(isinstance(derived['run_id'], str) and derived['run_id'], 'derived run_id')
    _require(type(derived['strict']) is bool, 'derived strict must be boolean')
    _keys(derived['inputs'], DERIVED_INPUT_KEYS, 'derived inputs')
    for key in DERIVED_INPUT_KEYS:
        _sha(derived['inputs'][key], 'inputs.' + key)
    _require(isinstance(derived['boundaries'], dict) and derived['boundaries'], 'derived boundaries')
    for ref, terms in derived['boundaries'].items():
        _keys(terms, IDENTITY_TERM_KEYS, 'boundary terms ' + str(ref))
        _require(terms['boundary_ref'] == ref, 'boundary terms keyed by ref')
        _require(terms['cross'] == identity_cross(terms['orientation'], terms['vehs'], terms['n_end'],
                                                  terms['n_start'], terms['removed']),
                 ref + ': cross differs from the identity')
    lag = derived['lag']
    _keys(lag, ('sum_tail', 'max_t_any', 'threshold_s', 'ok', 'err_max_sim_sec'), 'derived lag')
    _require(lag['ok'] is True, 'A derived document exists only when the lag rule held')
    tails = derived['tails']
    _require(isinstance(tails, dict), 'derived tails must be an object')
    for key, value in tails.items():
        _uint_key(key, 'derived tails')
        _nonneg_int(value, 'derived tail')
    _require(sum(tails.values()) == lag['sum_tail'], 'tails must sum to sum_tail')
    _nonneg_int(derived['boundary_ambiguous'], 'boundary_ambiguous')
    if derived['strict']:
        _require(derived['boundary_ambiguous'] == 0, 'Verification runs fail on boundary-ambiguous records (D8)')
    removals = derived['removals']
    _keys(removals, ('window_total', 'rows'), 'derived removals')
    _require(removals['window_total'] == len(removals['rows']), 'removal total differs from rows')
    for row in removals['rows']:
        _keys(row, ('vehicle_id', 'time_sec', 'link', 'position_m', 'route_decision', 'route_index',
                    'boundary_refs', 'on_chain'), 'removal assignment')
        _require(start_s < row['time_sec'] <= end_s, 'Assigned removal lies outside the interval')
    ledger = derived['ledger_10643']
    _keys(ledger, ('vehicles', 'by_lane', 'tail_by_lane'), 'ledger_10643')
    for vehicle in ledger['vehicles']:
        _keys(vehicle, ('veh', 'lane', 'via', 'connector', 'label_source'), 'ledger vehicle')
        _require(vehicle['via'] in ('mer', 'tail') and vehicle['label_source'] in LEDGER_SOURCES,
                 'ledger vehicle via/label_source')
        if derived['strict']:
            _require(vehicle['label_source'] != 'unidentified', 'Verification runs fail on unidentified 10643 labels (D9)')
    exit_count = derived['freeway_exit_count']
    _keys(exit_count, ('value', 'off_total', 'chain_end_total', 'chain_removals'), 'freeway_exit_count')
    for key in ('value', 'off_total', 'chain_end_total', 'chain_removals'):
        _nonneg_int(exit_count[key], 'freeway_exit_count.' + key)
    _require(exit_count['value'] == exit_count['off_total'] + exit_count['chain_end_total'] + exit_count['chain_removals'],
             'freeway_exit_count = off + chain end + chain removals')
    split = derived['off_split']
    _require(isinstance(split, dict), 'off_split must be an object')
    for row in split.values():
        _keys(row, OFF_SPLIT_HISTORY_KEYS + ('ratio',), 'off_split row')
    _validate_lane_shares_and_splits({o: r['ratio'] for o, r in split.items()},
                                     {o: {k: r[k] for k in OFF_SPLIT_HISTORY_KEYS} for o, r in split.items()},
                                     derived['ramp_arrival_shares'], derived['offramp_10643_lane_shares'])
    _validate_offramp_history(derived['offramp_10643_history'], sim_sec)
    _validate_source_boundary(derived['source_boundary'])
    _keys(derived['link_departures_window'], (BYPASS_SOURCE_LINK,), 'link_departures_window')
    _nonneg_int(derived['link_departures_window'][BYPASS_SOURCE_LINK], 'link_departures_window.403')
    for key, value in derived['edie_residuals'].items():
        _uint_key(key, 'edie_residuals')
        _require(_is_number(value), 'edie residual must be finite')
    if k is None:
        _require(derived['head_window'] is None, 't=1 has no head window')
        _require(derived['link_departures_window'][BYPASS_SOURCE_LINK] == 0, 't=1 closes departures at 0')
    else:
        validate_head_window_v2(derived['head_window'], end_sec=end_s,
                                detector_config_sha256=derived['inputs']['detector_config_sha256'])
        _require(derived['boundary_ambiguous'] == sum(h['boundary_ambiguous'] for h in derived['head_window']['heads']),
                 'boundary_ambiguous is the head window total')


def derived_bytes(derived):
    """Bytes of obs150/derived_<T>.json: canonical JSON plus one LF."""
    validate_derived(derived)
    return canonical_json_bytes(derived) + b'\n'


def write_derived(raw, derived):
    """Write obs150/derived_<T>.json under the bundle directory; identical bytes may already exist."""
    obs = raw[RAW_STATE_KEY]
    _require(derived['sim_sec'] == obs['sim_sec'] and derived['run_id'] == obs['run_id'],
             'Derived document belongs to another bundle')
    path = resolve(obs, derived_path(obs['sim_sec']))
    data = derived_bytes(derived)
    if path.exists():
        _require(path.read_bytes() == data, 'A different derived document already exists: ' + str(path))
        return path
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_bytes(data)
    temporary.replace(path)
    return path


def validate_merged_state(before, after):
    """merge_into_state changes exactly four fields and adds obs150_derived."""
    _require(isinstance(before, dict) and isinstance(after, dict), 'States must be objects')
    derived = after.get(MERGED_DERIVED_KEY)
    validate_derived(derived)
    _require(MERGED_DERIVED_KEY not in before, 'The raw state already carries derived values')
    local_before, local_after = before['local_observation'], after['local_observation']
    far_before, far_after = local_before['far_measurement'], local_after['far_measurement']
    _require(isinstance(far_before, dict) and far_before.get('freeway_exit_count') is None,
             'v2 runner leaves far freeway_exit_count null for the merge')
    _require(far_after.get('freeway_exit_count') == derived['freeway_exit_count']['value']
             and far_after.get('freeway_exit_count_provenance') == FREEWAY_EXIT_PROVENANCE,
             'far freeway_exit_count must be the conservation value')
    _require(local_after['link_departures_window'] == derived['link_departures_window'],
             'link_departures_window must come from the derived counts')
    _require('signal_observation_window' in local_after
             and local_after['signal_observation_window'] == derived['head_window'],
             'signal_observation_window must be the derived head window (null at t=1)')
    strip_far = lambda far: {k: v for k, v in far.items() if k not in ('freeway_exit_count', 'freeway_exit_count_provenance')}
    strip_local = lambda local: {k: (strip_far(v) if k == 'far_measurement' else v) for k, v in local.items()
                                 if k not in ('signal_observation_window', 'link_departures_window')}
    _require(strip_local(local_before) == strip_local(local_after), 'merge changed another local observation field')
    rest = lambda state: {k: v for k, v in state.items() if k not in ('local_observation', MERGED_DERIVED_KEY)}
    _require(rest(before) == rest(after), 'merge changed a field outside local_observation')


# --------------------------------------------------------------------------
# 1.6 Obs150Context and the source schedule
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class ScheduleRow:
    """Piecewise-constant desired source demand: vph on [start_sec, end_sec); end None = open."""
    start_sec: float
    end_sec: float | None
    vph: float


def validate_schedule(rows):
    rows = tuple(rows)
    _require(rows and rows[0].start_sec == 0 and rows[-1].end_sec is None, 'Schedule covers [0, inf)')
    for a, b in zip(rows, rows[1:]):
        _require(a.end_sec == b.start_sec, 'Schedule rows must be contiguous and ordered')
    for row in rows:
        _require(_is_number(row.vph) and row.vph >= 0, 'Schedule vph must be >= 0')
        _require(row.end_sec is None or row.end_sec > row.start_sec, 'Schedule rows need positive length')
    return rows


def schedule_rate_at(schedule, t):
    """BF demand_vph: the unique row with start <= t < end."""
    rows = [r for r in schedule if r.start_sec <= t and (r.end_sec is None or t < r.end_sec)]
    _require(len(rows) == 1, f'Schedule has {len(rows)} rows at {t}')
    return float(rows[0].vph)


def schedule_integral_veh(schedule, t0, t1):
    """Integral of the schedule over [t0, t1] in vehicles (BF desired_before with t0=0)."""
    _require(t0 <= t1, 'Integral bounds reversed')
    total = []
    for row in schedule:
        end = t1 if row.end_sec is None else min(t1, row.end_sec)
        total.append(max(0.0, end - max(t0, row.start_sec)) * float(row.vph) / 3600.0)
    return math.fsum(total)


@dataclass(frozen=True)
class OfframpRef:
    connector: str
    road: str
    from_cell: int              # 31-cell index of the diverge cell (geometry boundaries)
    lanes: tuple                # connector lanes
    off_entry_ref: str          # boundary_ref 'off_entry:<connector>'
    through_ref: str            # boundary_ref 'through:<connector>'


@dataclass(frozen=True)
class RampArrivalRef:
    ramp_id: str
    connector: str
    lanes: tuple
    boundary_ref: str           # 'ramp_arrival:<ramp_id>'
    receiving: bool             # in component.ramp_receiving_nodes


@dataclass(frozen=True)
class SigProgram:
    """One native .sig program (NEW-9). All times integer seconds."""
    sc: str
    path: str
    sha256: str
    prog_no: int
    offset_s: int
    cycle_s: int
    green_s: Mapping[str, tuple]   # sg -> ((start, end), ...) program seconds, 0 <= start < end <= cycle


@dataclass(frozen=True)
class Obs150Context:
    """Built once per run by obs150_observation.load_context(document, paths)."""
    manifest_sha256: str
    network_sha256: str
    detector_csv_path: str
    detector_csv_sha256: str
    detectors: tuple                               # DetectorRow, dcp order
    boundaries: Mapping[str, tuple]                # boundary_ref -> DetectorRow (lane order); segments = 1.3
    chain_links: Mapping[str, tuple]               # road -> RW_FW_*_CHAIN_LINKS (source link first, exit last)
    chain_internal_connectors: frozenset           # connectors inside the chains (10699/10613/10702/10771)
    offramps: Mapping[str, OfframpRef]             # 8 off connectors
    ramp_arrivals: Mapping[str, RampArrivalRef]    # ramp id -> ref
    source_refs: Mapping[str, str]                 # road -> 'source:<road>'
    chain_end_refs: Mapping[str, str]              # road -> 'chain_end:<road>'
    headfree_refs: Mapping[str, str]               # '10565'/'10570' -> 'headfree:<c>'
    x10643_exit_ref: str                           # 'x10643_exit:10643'
    destination_refs: Mapping[str, str]           # '10634'/'10635'/'10642' -> 'destination:<c>'
    lane_map_10643: Mapping[int, Mapping[int, int]]  # link (10643/126/10641/10700/71) -> lane -> 10643 lane
    route_destinations_10643: Mapping[int, int]    # RD 1126 route no -> destination connector
    head_groups: Mapping[tuple, tuple]             # SHO.physical_groups: (link, phase) -> head dicts
    sig_table: Mapping[str, SigProgram]            # sc -> native program
    source_schedule: Mapping[str, tuple]           # road -> ScheduleRow

    def rows_by_role(self, role):
        return tuple(r for r in self.detectors if r.role == role)


def validate_context(context):
    _require(isinstance(context, Obs150Context), 'Obs150Context required')
    _sha(context.manifest_sha256, 'context.manifest_sha256')
    _sha(context.network_sha256, 'context.network_sha256')
    _sha(context.detector_csv_sha256, 'context.detector_csv_sha256')
    rows = validate_detector_rows(context.detectors)
    _require(dict(context.boundaries) == group_boundaries(rows), 'context.boundaries must group the table')

    def ref_of(ref, role):
        _require(ref in context.boundaries and context.boundaries[ref][0].role == role,
                 f'context ref {ref} missing or not a {role} boundary')

    _require(set(context.chain_links) == set(ROADS), 'Both roads need their chain')
    chain_all = set()
    for road, links in context.chain_links.items():
        _require(isinstance(links, tuple) and len(links) >= 2 and len(set(links)) == len(links)
                 and all(_is_int(v) for v in links), road + ' chain must be unique integer links')
        chain_all |= set(links)
    _require(set(context.chain_internal_connectors) <= chain_all, 'Chain connectors lie on the chains')
    _require(len(context.offramps) == EXPECTED_OFFRAMP_COUNT and OFFRAMP_10643 in context.offramps,
             'Eight off-ramps including 10643')
    for off, ref in context.offramps.items():
        _require(isinstance(ref, OfframpRef) and ref.connector == off and ref.road in ROADS
                 and _is_int(ref.from_cell) and ref.from_cell >= 0, 'OfframpRef ' + off)
        ref_of(ref.off_entry_ref, 'off_entry')
        ref_of(ref.through_ref, 'through')
        _require(tuple(t.lane for t in context.boundaries[ref.off_entry_ref]) == tuple(ref.lanes),
                 off + ': off_entry rows must cover each connector lane once')
    _require(context.ramp_arrivals and any(r.receiving for r in context.ramp_arrivals.values()),
             'At least one receiving ramp')
    for name, ref in context.ramp_arrivals.items():
        _require(isinstance(ref, RampArrivalRef) and ref.ramp_id == name, 'RampArrivalRef ' + name)
        ref_of(ref.boundary_ref, 'ramp_arrival')
        _require(tuple(t.lane for t in context.boundaries[ref.boundary_ref]) == tuple(ref.lanes),
                 name + ': ramp_arrival rows must cover each ramp lane once')
    for table, role, keys in ((context.source_refs, 'source', ROADS), (context.chain_end_refs, 'chain_end', ROADS),
                              (context.headfree_refs, 'headfree', HEADFREE_CONNECTORS),
                              (context.destination_refs, 'destination', DESTINATION_CONNECTORS_10643)):
        _require(set(table) == set(keys), role + ' refs keys differ')
        for ref in table.values():
            ref_of(ref, role)
    ref_of(context.x10643_exit_ref, 'x10643_exit')
    _require({10643, 126} <= set(context.lane_map_10643), 'lane_map_10643 needs 10643 and 126')
    _require(set(context.route_destinations_10643.values()) <= {int(c) for c in DESTINATION_CONNECTORS_10643},
             'RD 1126 routes must end at the three destination connectors')
    heads = {r.ref.split('|')[0]: r for r in rows if r.role == 'head'}
    _require(context.head_groups, 'Head groups must not be empty')
    eligible = {str(h['head_id']) for members in context.head_groups.values() for h in members}
    _require(eligible == set(heads), 'Head detectors must equal the eligible physical_groups heads')
    for members in context.head_groups.values():
        for head in members:
            row = heads.get(str(head['head_id']))
            _require(row is not None, f'Eligible head {head["head_id"]} has no head detector')
            _require(parse_head_ref(row.ref)[1:] == (str(head['sc']), str(head['sg']))
                     and (row.link, row.lane) == (int(head['link']), int(head['lane'])),
                     f'Head detector {row.ref} differs from its eligible head')
    for sc, program in context.sig_table.items():
        _require(isinstance(program, SigProgram) and program.sc == sc, 'SigProgram ' + sc)
        _sha(program.sha256, sc + '.sha256')
        _require(all(_is_int(v) for v in (program.prog_no, program.offset_s, program.cycle_s))
                 and program.cycle_s > 0, sc + ': program times must be integer seconds')
        for sg, intervals in program.green_s.items():
            for a, b in intervals:
                _require(_is_int(a) and _is_int(b) and 0 <= a < b <= program.cycle_s, f'{sc}-{sg} green interval')
    _require(set(context.source_schedule) == set(ROADS), 'Both roads need a source schedule')
    for schedule in context.source_schedule.values():
        validate_schedule(schedule)


# --------------------------------------------------------------------------
# 1.9 Python interfaces (signatures fixed here; bodies live in their owners)
# --------------------------------------------------------------------------
REQUIRED = inspect.Parameter.empty
INTERFACES = {
    # WP-B1
    'evaluation.controllers.obs150_capture.capture':
        (('eval_dir', REQUIRED), ('err_path', REQUIRED), ('out_dir', REQUIRED), ('sim_sec', REQUIRED),
         ('detector_table', REQUIRED)),
    'evaluation.controllers.obs150_signal_clock.windows':
        (('signal_log', REQUIRED), ('sig_table', REQUIRED), ('window', REQUIRED)),
    'evaluation.controllers.obs150_head_window.build':
        (('raw', REQUIRED), ('context', REQUIRED), ('clocks', REQUIRED), ('mer_rows', REQUIRED)),
    # WP-B2
    'evaluation.controllers.obs150_lane.derive':
        (('raw', REQUIRED), ('context', REQUIRED), ('mer_rows', REQUIRED), ('err_rows', REQUIRED),
         ('frame_T', REQUIRED), ('frame_prev', REQUIRED)),
    'evaluation.controllers.obs150_observation.load_context': (('document', REQUIRED), ('paths', REQUIRED)),
    'evaluation.controllers.obs150_observation.derive': (('raw', REQUIRED), ('context', REQUIRED)),
    'evaluation.controllers.obs150_observation.merge_into_state': (('raw', REQUIRED), ('derived', REQUIRED)),
    'evaluation.controllers.obs150_observation.lane_observation': (('context', REQUIRED), ('raw', REQUIRED)),
    # WP-C
    'evaluation.controllers.source_boundary.forecast':
        (('recent_vph', REQUIRED), ('backlog_veh', REQUIRED), ('schedule', REQUIRED), ('start_s', REQUIRED),
         ('block_s', REQUIRED), ('n_blocks', REQUIRED), ('step_s', 10)),
}
CAPTURE_CLI = 'scripts/obs150_capture.py'
CAPTURE_CLI_ARGS = ('--eval-dir', '--err', '--out-dir', '--sim-sec', '--detectors', '--detectors-sha256')
CAPTURE_STDOUT_PREFIX = 'OBS150_CAPTURE_OK'


def assert_implements(qualified_name, function):
    """The function's leading parameters match the contract exactly.

    Extra parameters are allowed only as keyword-only with defaults.
    """
    _require(qualified_name in INTERFACES, 'Not a contract interface: ' + qualified_name)
    parameters = list(inspect.signature(function).parameters.values())
    expected = INTERFACES[qualified_name]
    _require(len(parameters) >= len(expected), qualified_name + ': too few parameters')
    for parameter, (name, default) in zip(parameters, expected):
        _require(parameter.name == name and parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
                 and parameter.default == default,
                 f'{qualified_name}: parameter {parameter.name!r} differs from contract {name!r}')
    for parameter in parameters[len(expected):]:
        _require(parameter.kind is inspect.Parameter.KEYWORD_ONLY and parameter.default is not REQUIRED,
                 f'{qualified_name}: extra parameter {parameter.name!r} must be keyword-only with a default')


def check_module(module_name):
    """Import an owner module and check every contract interface it must provide."""
    module = importlib.import_module(module_name)
    names = [n for n in INTERFACES if n.rsplit('.', 1)[0] == module_name]
    _require(names, 'No contract interfaces live in ' + module_name)
    for name in names:
        assert_implements(name, getattr(module, name.rsplit('.', 1)[1]))
    return names
