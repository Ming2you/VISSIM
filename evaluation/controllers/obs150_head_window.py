"""obs150 head window (WP-B1, plan B5): physical-head-window/v2 of one decision.

For every eligible head (SHO physical_groups) over the window (T-150, T]:

- crossings            = Vehs(Current,k,All) of the head detector (PRB d: exact);
- qualified_crossings  = the window's .mer entry records whose passage is green
  (classify_passage: green intervals (a, b], the 0.005 s file-order rule at the
  interval endpoints) + the tail when the last second (T-1, T] is green. The tail
  (Vehs minus records in the file) lies wholly in (T-1, T] once the lag rule
  holds (assign_window), and that second has one state. A record at the window
  edge T-150 or T (±0.005) needs no file order: its ordinal already put it in
  (T-150, T], which fixes its step (classify_at_window_edge);
- boundary_ambiguous   = entry records at a green endpoint inside the window the
  file order cannot place (D8). They are not counted as qualified;
- green/native/controlled/unverified seconds from obs150_signal_clock.windows.

bypass_link_exits['403'] is cross(headfree:10565) from the counting identity
(NEW-12). Window assignment, the file-order rule and the identity are the one
implementation in obs150_contract.
"""
from __future__ import annotations

import json
from pathlib import Path

from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.obs150_contract import ObsContractError
from evaluation.controllers.signal_head_observation import serialized_head_position

BYPASS_CONNECTOR = '10565'
# The CSV writes pos with '%.6f' (CONTRACT 7): the head detector sits within half a unit of the head.
HEAD_POSITION_TOL_M = 0.5 * 10 ** -oc.POS_DECIMALS + 1e-9


def _require(condition, message):
    if not condition:
        raise ObsContractError(message)


def eligible_heads(context):
    """(group key, head dict) of every eligible head, group-key then listed order."""
    out = []
    for key in sorted(context.head_groups, key=lambda k: tuple(str(v) for v in k)):
        for head in context.head_groups[key]:
            out.append((key, head))
    return out


def head_detectors(context):
    """head_id -> the one 'head' DetectorRow."""
    rows = {}
    for row in context.detectors:
        if row.role != 'head':
            continue
        head_id = oc.parse_head_ref(row.ref)[0]
        _require(head_id not in rows, f'Two head detectors for head {head_id}')
        rows[head_id] = row
    return rows


def row_positions(mer_rows):
    """seq -> index of the chunk rows (built once per window, shared by every head)."""
    return {row.seq: i for i, row in enumerate(mer_rows)}


def classify_at_window_edge(mer_rows, index, s, window, intervals):
    """'green' | 'not_green' for an entry record at a window edge s (|t - s| <= 0.005).

    assign_window put the record in (start, end] by its ordinal, which already
    fixes the step: (start, start+0.1] at s = start, (end-0.1, end] at s = end.
    A green interval cut at the window edge makes s an endpoint, but this record
    is not ambiguous. The file order may agree or say nothing; the opposite
    step contradicts the ordinal = time order premise (B3) and raises.
    """
    start, end = window
    _require(s in (start, end), f'{s} is not an edge of the window ({start}, {end}]')
    expected = 'after' if s == start else 'before'
    side = oc.boundary_side(mer_rows, index, s)
    _require(side in (expected, 'ambiguous'),
             f'File order puts the record at {s} outside its ordinal window ({start}, {end}]')
    tau = start + 0.05 if s == start else end
    return 'green' if oc.in_green(tau, intervals) else 'not_green'


def classify_entries(mer_rows, entries, intervals, window, *, position=None):
    """Counts {'green', 'not_green', 'ambiguous'} and per-record labels [(MerRow, label)].

    window = (start, end) of the assignment that chose `entries`. A record at a
    window edge is placed by its ordinal (classify_at_window_edge); every other
    record goes through classify_passage. position: row_positions(mer_rows).
    """
    if position is None:
        position = row_positions(mer_rows)
    start, end = window
    counts = {'green': 0, 'not_green': 0, 'ambiguous': 0}
    labels = []
    for row in entries:
        index = position.get(row.seq)
        _require(index is not None and mer_rows[index] == row, 'Window entry is not a chunk row')
        s = oc.near_integer(row.t_entry)
        if s in (start, end):
            label = classify_at_window_edge(mer_rows, index, s, window, intervals)
        else:
            label = oc.classify_passage(mer_rows, index, intervals)
        counts[label] += 1
        labels.append((row, label))
    return counts, labels


def config_sha256_from_provenance(raw):
    """signal_observation.config_chain[0].sha256 of the run provenance manifest (SHO checks the same pin)."""
    manifest = json.loads(Path(raw['run_provenance']['manifest_path']).read_text(encoding='utf-8-sig'))
    _require(manifest.get('run_id') == raw['run_provenance']['run_id'], 'Provenance manifest belongs to another run')
    chain = manifest['signal_observation']['config_chain']
    _require(chain, 'Provenance signal_observation.config_chain is empty')
    return chain[0]['sha256']


def bypass_crossings(obs, context, bundle, boundaries):
    ref = context.headfree_refs[BYPASS_CONNECTOR]
    if boundaries is not None:
        _require(ref in boundaries, 'Precomputed boundaries lack ' + ref)
        terms = boundaries[ref]
        return terms['cross'] if isinstance(terms, dict) else terms.cross
    rows = context.boundaries[ref]
    start, end, _ = oc.bundle_interval(obs['sim_sec'])
    return oc.evaluate_boundary(rows, obs['detectors'], bundle.frame_end, bundle.frame_start,
                                bundle.err_rows, start, end).cross


# --------------------------------------------------------------------------
# Contract interface (plan 1.9)
# --------------------------------------------------------------------------
def build(raw, context, clocks, mer_rows, *, bundle=None, boundaries=None, config_sha256=None):
    """physical-head-window/v2 of the state raw (None at t=1).

    raw: the state (top-level 'obs150' bundle, 'run_provenance'); context:
    Obs150Context; clocks: obs150_signal_clock.windows output; mer_rows: the T
    chunk's MerRows in file order. Keywords let the caller pass what it already
    has: bundle (load_bundle(raw)), boundaries (evaluate_boundaries result, used
    for bypass_link_exits) and config_sha256 (else read from the provenance).
    """
    obs = raw[oc.RAW_STATE_KEY]
    start, end, k = oc.bundle_interval(obs['sim_sec'])
    if k is None:
        return None
    _require(obs['detector_config']['sha256'] == context.detector_csv_sha256,
             'The bundle was captured with another detector table')
    # validate_clocks keeps every green interval inside [start, end]; a clock of
    # another window without green in this one still passes it.
    oc.validate_clocks(clocks, {'start_s': start, 'end_s': end})
    mer_rows = list(mer_rows)
    assignment = oc.assign_window(obs, mer_rows)
    if boundaries is None and bundle is None:
        bundle = oc.load_bundle(raw)
    if bundle is not None:
        _require(tuple(bundle.mer_rows) == tuple(mer_rows), 'mer_rows differ from the pinned chunk')
    detectors = head_detectors(context)
    position = row_positions(mer_rows)
    heads, complete = [], True
    for _, head in eligible_heads(context):
        head_id = str(head['head_id'])
        row = detectors.get(head_id)
        _require(row is not None, f'Eligible head {head_id} has no head detector')
        _, sc, sg = oc.parse_head_ref(row.ref)
        _require((sc, sg) == (str(head['sc']), str(head['sg'])) and (row.link, row.lane) == (int(head['link']), int(head['lane']))
                 and abs(row.pos - float(head['position_m'])) <= HEAD_POSITION_TOL_M,
                 f'Head detector {row.ref} differs from eligible head {head_id}')
        clock = clocks.get(f'{sc}-{sg}')
        _require(clock is not None, f'No signal clock for {sc}-{sg} (head {head_id})')
        intervals = [tuple(pair) for pair in clock['green']]
        counts, _ = classify_entries(mer_rows, assignment.entries.get(row.dcp_no, ()), intervals, (start, end),
                                     position=position)
        tail = assignment.tails[row.dcp_no]
        crossings = obs['detectors'][str(row.dcm_no)]
        qualified = counts['green'] + (tail if oc.tail_in_green(end, intervals) else 0)
        complete = complete and clock['complete'] is True
        heads.append({'head_id': head_id, 'link': str(head['link']), 'lane': int(head['lane']),
                      'position_m': serialized_head_position(head['position_m']), 'sc': sc, 'sg': sg,
                      'crossings': crossings, 'qualified_crossings': qualified,
                      'green_sec': sum(b - a for a, b in intervals), 'native_sec': clock['native_sec'],
                      'controlled_sec': clock['controlled_sec'], 'unverified_sec': clock['unverified_sec'],
                      'boundary_ambiguous': counts['ambiguous']})
    window = {'schema': oc.HEAD_WINDOW_SCHEMA_V2,
              'config_sha256': config_sha256 if config_sha256 is not None else config_sha256_from_provenance(raw),
              'detector_config_sha256': obs['detector_config']['sha256'], 'start_sec': start, 'end_sec': end,
              'cadence_sec': oc.DECISION_INTERVAL_SEC, 'exposure_method': oc.HEAD_EXPOSURE_METHOD_V2,
              'clock_complete': complete, 'heads': heads,
              'bypass_link_exits': {oc.BYPASS_SOURCE_LINK: bypass_crossings(obs, context, bundle, boundaries)}}
    oc.validate_head_window_v2(window, end_sec=end, detector_config_sha256=obs['detector_config']['sha256'])
    return window
