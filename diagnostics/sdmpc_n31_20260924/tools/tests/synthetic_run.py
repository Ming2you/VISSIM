"""A small, internally consistent obs150 run on disk for the WP-D tool tests.

One western road: origin link 26 (2 lanes, 200 m), off connector 10485 leaving 26 at 120 m
toward an untracked link 300, chain connector 10771 leaving 26 at 199 m onto link 120
(2 lanes, 100 m, network exit at its end). Vehicles move at constant speed; one vehicle is
removed by a lane-change timeout on 26 at 150 m (.err). From these trajectories the fixture
writes, exactly as the contract defines them:

  - the 0.1 s ground truth (gt_veh.csv, gt_sig.csv, gt_meta.csv) of (750, 900],
  - the .mer rows of every station crossing (entry time rounded to 0.01 s) as obs150 chunks,
    the sha-chained mer index (1, 150, ..., 900 and a later 1050 entry), the install record,
  - lane_observations frames at every decision time, the .err text and its chunk,
  - state_<T>.json for T in (1, 150, ..., 900) with a contract-valid obs150 raw block,
  - obs150/derived_000900.json built with the contract functions (evaluate_boundaries etc.),
  - an inpx with those links, a runner config with the chain lists, a run provenance.

SyntheticRun(..., lane_change=True) adds (D6 review fix 1/2):
  - a second head 70204|5-4 on lane 2 at 100.004 m (green (800, 850]);
  - vehicle 901 changing lane 1 -> 2 inside the step it crosses the two-lane 'at' station
    through:10485 (130 m), vehicle 902 inside the step it crosses both heads, vehicle 903 the same
    as 901 in the last second (899.62 s: not yet in .mer, a tail), vehicle 904 on the chain
    connector 10771 at 900 s, vehicle 905 crossing the source segment start x = 0 m on lane 1 and
    its detector p = 1 m on lane 2 (the lane terms of source:FW_W then differ from the lanes at x).
    VISSIM records a lane-changing vehicle in the lane it has at the end of the step (recorded_lane).
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
for p in (str(ROOT), str(HERE.parent), str(ROOT / 'diagnostics' / 'obs150_20260924' / 'tests')):
    if p not in sys.path:
        sys.path.insert(0, p)

from evaluation.controllers import obs150_contract as oc  # noqa: E402
import contract_fixtures as cf  # noqa: E402

RUN_ID = 'run1'
T_END = 900
T_START = 750
HEAD_REF = '70203|5-2'
HEAD2_REF = '70204|5-4'                     # lane_change variant: the lane-2 head at the same stop line
GREEN = ((760, 800), (850, 900))           # SC5 SG2 green intervals (a, b] in (750, 900]
GREEN2 = ((800, 850),)                      # SC5 SG4
MERGE_FLUSH_S = 0.5                         # .mer rows later than T - 0.5 are not flushed at T (tails)

# link: (connector?, from_link, from_pos, to_link, to_pos, length, lanes)
LINKS = {26: (False, None, None, None, None, 200.0, 2), 120: (False, None, None, None, None, 100.0, 2),
         300: (False, None, None, None, None, 80.0, 1),
         10485: (True, 26, 120.0, 300, 0.0, 30.0, 1), 10771: (True, 26, 199.0, 120, 0.0, 5.0, 2)}
CONNECTOR_LANES = {10485: (2, 1), 10771: (1, 1)}    # (from_link lane, to_link lane) of the connector's lane 1
REMOVED = (999, 815.0, 150.0)               # vehicle, time, position on 26
# lane_change variant: (veh, created_s, lane, speed_mps, path, (switch position m, new lane))
LANE_CHANGE_VEHICLES = ((901, 770.02, 1, 13.0, 'through', (130.5, 2)),      # 130 m in step 7801
                        (902, 800.05, 1, 14.0, 'through', (100.002, 2)),    # 100.0 / 100.004 m in step 8072
                        (903, 890.334, 1, 14.0, 'through', (130.5, 2)),     # 130 m in step 8997: a tail at 900
                        (904, 885.643, 1, 14.0, 'through', None),           # on 10771 at 900 s
                        (905, 810.0, 1, 13.0, 'through', (0.5, 2)))         # enters at 0 m on lane 1, p=1 m on lane 2


def vehicles(lane_change=False):
    """(veh, created_s, lane, speed_mps, path, switch). Created on 26 at 0 m."""
    out = []
    n = 1
    # 899.6: its source-station entry (899.68) is after the .mer flush at 899.5, i.e. a tail at T=900.
    for i, t0 in enumerate([702.3, 731.7, 748.2, 755.55, 768.0, 781.4, 795.0, 823.3, 846.1, 868.6, 881.2, 890.0,
                            899.6]):
        out.append((n, t0, 1 + (i % 2), 13.0 + (i % 3), 'off' if i % 4 == 1 else 'through', None))
        n += 1
    out.append((REMOVED[0], 800.0, 1, 10.0, 'removed', None))
    if lane_change:
        out.extend(LANE_CHANGE_VEHICLES)
    return out


def lane_at(vehicle, s):
    """The lane at travelled distance s (a switch takes effect at its position)."""
    lane, switch = vehicle[2], vehicle[5]
    return switch[1] if switch is not None and s >= switch[0] else lane


def recorded_lane(vehicle, t):
    """The lane VISSIM records a crossing at true time t in: the lane at the end of that 0.1 s step."""
    b = math.ceil(t * 10 - 1e-9) / 10
    return lane_at(vehicle, (b - vehicle[1]) * vehicle[3])


def position(vehicle, t):
    """(link, lane, pos) at true time t, or None when not on a tracked link."""
    veh, t0, _, v, path, _ = vehicle
    if t < t0:
        return None
    s = (t - t0) * v
    lane = lane_at(vehicle, s)
    if path == 'removed' and t > REMOVED[1]:
        return None
    if path == 'off':
        if s < 120.0:
            return 26, lane, s
        if s < 150.0:
            return 10485, 1, s - 120.0
        return None                                  # untracked 300
    if s < 199.0:
        return 26, lane, s
    if s < 204.0:
        return 10771, lane, s - 199.0
    if s < 304.0:
        return 120, lane, s - 204.0
    return None                                      # network exit at the end of 120


def crossing_time(vehicle, link, x):
    """True time the front passes x on link (exact), or None when the vehicle never passes it."""
    veh, t0, _, v, path, _ = vehicle
    reach = {'off': {26: (0.0, 120.0), 10485: (120.0, 30.0)},
             'removed': {26: (0.0, REMOVED[2])},
             'through': {26: (0.0, 199.0), 10771: (199.0, 5.0), 120: (204.0, 100.0)}}[path]
    if link not in reach or x > reach[link][1]:
        return None
    return t0 + (reach[link][0] + x) / v


def head_greens(lane_change=False):
    """{head ref: green intervals} of the heads of the table."""
    return {HEAD_REF: GREEN, **({HEAD2_REF: GREEN2} if lane_change else {})}


def detector_rows(lane_change=False):
    g26 = {'link_length_m': 200.0, 'lane_count': 2}
    specs = []
    for lane in (1, 2):
        specs.append(('source', 'FW_W', 26, lane, 1.0, 'exact', 'down', (oc.SegmentPiece(26, 0.0, 1.0, (lane,)),), g26))
    specs.append(('head', HEAD_REF, 26, 1, 100.0, 'exact', 'at', (), g26))
    for lane in (1, 2):
        specs.append(('through', '10485', 26, lane, 130.0, 'exact', 'at', (), g26))
    specs.append(('off_entry', '10485', 10485, 1, 1.0, 'exact', 'down', (oc.SegmentPiece(10485, 0.0, 1.0, (1,)),),
                  {'link_length_m': 30.0, 'lane_count': 1}))
    for lane in (1, 2):
        specs.append(('chain_end', 'FW_W', 120, lane, 99.9, 'end_minus', 'up', (oc.SegmentPiece(120, 99.9, 100.0, (lane,)),),
                      {'link_length_m': 100.0, 'lane_count': 2, 'offset_from_end_m': 0.1}))
    if lane_change:
        specs.append(('head', HEAD2_REF, 26, 2, 100.004, 'exact', 'at', (), g26))
    rows = []
    for i, (role, ref, link, lane, pos, mode, orientation, segment, geometry) in enumerate(specs):
        key = oc.DETECTOR_KEY_RANGE[0] + i
        rows.append(oc.DetectorRow(key, key, role, ref, link, lane, pos, mode, orientation,
                                   oc.expected_boundary_ref(role, ref), segment, geometry))
    return oc.validate_detector_rows(rows)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _jsonl(values):
    return b''.join(json.dumps(v, ensure_ascii=True, sort_keys=True, separators=(',', ':')).encode('ascii') + b'\n'
                    for v in values)


def inpx_text():
    parts = ['<?xml version="1.0" encoding="UTF-8"?>\n<network><links>']
    for no, (conn, fl, fp, tl, tp, length, lanes) in LINKS.items():
        parts.append(f'<link no="{no}"><geometry><linkPolyPts><linkPolyPoint x="0" y="{no}" zOffset="0"/>'
                     f'<linkPolyPoint x="{length}" y="{no}" zOffset="0"/></linkPolyPts></geometry><lanes>'
                     + ''.join('<lane width="3.5"/>' for _ in range(lanes)) + '</lanes>')
        if conn:
            from_lane, to_lane = CONNECTOR_LANES[no]
            parts.append(f'<fromLinkEndPt lane="{fl} {from_lane}" pos="{fp}"/><toLinkEndPt lane="{tl} {to_lane}" pos="{tp}"/>')
        parts.append('</link>')
    parts.append('</links><vehicleRoutingDecisionsStatic/></network>\n')
    return ''.join(parts)


def err_text():
    veh, t, pos = REMOVED
    return (f'Simulation second {t:.2f}: After 30.00 seconds of waiting for lane change the vehicle {veh} '
            f'(on Static Vehicle Route 1 - 1) was removed from link 26 at position {pos:.2f}.\r\n')


class SyntheticRun:
    def __init__(self, base, name='sdmpc31_g1', gt_windows=((T_START, T_END),), lane_change=False):
        self.base = Path(base)
        self.name = name
        self.run = self.base / name
        self.decisions = self.run / f'decisions_{name}'
        self.lane_change = lane_change
        self.rows = detector_rows(lane_change)
        self.greens = head_greens(lane_change)
        self.gt_windows = [list(w) for w in gt_windows]
        self.times = [1] + list(range(150, T_END + 1, 150))
        self.vehicles = vehicles(lane_change)
        self.build()

    # ------------------------------------------------------------ helpers
    def frame(self, t):
        rows = []
        for veh in self.vehicles:
            p = position(veh, t)
            if p is not None:
                rows.append([veh[0], p[0], p[1], round(p[2], 6), round(veh[3] * 3.6, 6), 4.5, None, None, None, None,
                             None, None, None, None, None])
        return {'schema': oc.FRAME_SCHEMA, 'complete': True, 'time_s': t, 'run_id': RUN_ID,
                'vehicles': sorted(rows) if t > 0 else []}

    def entries(self):
        """All station entry events: (t_true, dcp, veh, v_kmh), sorted by the .mer write order."""
        out = []
        for row in self.rows:
            for veh in self.vehicles:
                t = crossing_time(veh, row.link, row.pos)
                if t is None or t <= 0 or row.link in (26, 120) and recorded_lane(veh, t) != row.lane:
                    continue
                out.append((t, row.dcp_no, veh[0], veh[3] * 3.6))
        # A step's rows are written together; steps in order (NEW-5): order by step, then vehicle.
        out.sort(key=lambda e: (math.ceil(e[0] * 10 - 1e-9), e[2], e[1]))
        return out

    # ------------------------------------------------------------ build
    def build(self):
        d = self.decisions
        (d / 'lane_observations').mkdir(parents=True)
        (d / 'obs150').mkdir()
        self.network_dir = self.run / 'network'
        self.network_dir.mkdir()
        self.inpx = self.network_dir / f'sdmpc31_{self.name}.inpx'
        self.inpx.write_text(inpx_text(), encoding='utf-8')
        self.err = self.network_dir / f'sdmpc31_{self.name}_001.err'
        err_bytes = err_text().encode('cp949')
        self.err.write_bytes(err_bytes)
        self.csv = self.run / 'obs150_detectors_v2.csv'
        csv_bytes = oc.format_detector_csv(self.rows)
        self.csv.write_bytes(csv_bytes)
        self.csv_sha = _sha(csv_bytes)
        self.runner_config = self.run / 'lane_native_b110.vbs'
        self.runner_config.write_text('RW_FW_E_CHAIN_LINKS = "74,10699,2"\r\nRW_FW_W_CHAIN_LINKS = "26,10771,120"\r\n'
                                      'RW_DETECTOR_MAPPING_PATH = "evaluation\\x\\detector_map.json"\r\n',
                                      encoding='utf-8')
        install = {'schema': oc.INSTALL_SCHEMA, 'run_id': RUN_ID,
                   'detector_config': {'path': str(self.csv), 'sha256': self.csv_sha, 'rows': len(self.rows)},
                   'simres_steps_per_sec': 10,
                   'points': [{'dcp_no': r.dcp_no, 'dcm_no': r.dcm_no, 'link': r.link, 'lane': r.lane, 'pos': r.pos,
                               'readback': {'link': r.link, 'lane': r.lane, 'pos': r.pos}} for r in self.rows],
                   'evaluation': {**oc.INSTALL_EVALUATION, 'DataCollToTime': 1350, 'DataCollRawToTime': 1350}}
        oc.validate_install_record(install, self.rows)
        install_bytes = oc.canonical_json_bytes(install)
        (d / 'obs150' / 'obs150_install.json').write_bytes(install_bytes)
        self.install_sha = _sha(install_bytes)

        frame_sha = {}
        for t in [0] + self.times:
            data = json.dumps(self.frame(t)).encode('utf-8')
            (d / 'lane_observations' / f'frame_{t:06d}.json').write_bytes(data)
            frame_sha[t] = _sha(data)

        from evaluation.controllers.obs150_capture import parse_err_increment
        err_rows_all, _, _ = parse_err_increment(err_bytes, 0)
        entries = self.entries()
        keys = [r.dcp_no for r in self.rows]
        index, previous, seq = [], None, 0
        written = []                      # rows already in earlier chunks
        ordinal = {k: 0 for k in keys}
        stored_all = []
        for e in entries:
            ordinal[e[1]] += 1
            stored_all.append(oc.MerRow(seq, e[1], round(e[0], 2), None, e[2], 100, round(e[3], 2), 4.5, ordinal[e[1]]))
            seq += 1
        self.mer_rows_all = stored_all
        err_start = 0
        states = {}
        cum_at = lambda k_, x: sum(1 for e in entries if e[1] == k_ and e[0] <= x)
        for t in self.times:
            start, end, k = oc.bundle_interval(t)
            flush = end - MERGE_FLUSH_S if t > 1 else end
            chunk = [r for r in stored_all if r.seq >= len(written) and r.t_entry <= flush]
            written.extend(chunk)
            chunk_bytes = _jsonl([list(r) for r in chunk])
            (d / 'obs150' / f'mer_{t:06d}.jsonl').write_bytes(chunk_bytes)
            records = {str(k_): sum(1 for r in written if r.dcp == k_) for k_ in keys}
            cum = {str(k_): cum_at(k_, end) for k_ in keys}
            # t=1: the open interval (0,1]; T>=150: the closed window (T-150, T] (CONTRACT 4.2).
            now = {str(k_): cum[str(k_)] - (0 if t in (1, 150) else cum_at(k_, start)) for k_ in keys}
            # max_t_any is file-wide: rows of every point, generated or not, up to the flush time.
            max_t = flush if written or t > 1 else None
            entry = {'sim_sec': t, 'chunk': oc.mer_chunk_path(t), 'chunk_sha256': _sha(chunk_bytes),
                     'byte_start': 0, 'byte_end': 0, 'max_t_any': max_t, 'records_cum_by_dcp': records,
                     'prev_entry_sha256': previous}
            entry['entry_sha256'] = oc.mer_index_entry_sha256(entry)
            index.append(entry)
            err_chunk_rows = [r for r in err_rows_all if r['time_sec'] <= end and r['time_sec'] > (0 if t == 1 else start)]
            err_bytes_chunk = _jsonl(err_chunk_rows)
            (d / 'obs150' / f'err_{t:06d}.jsonl').write_bytes(err_bytes_chunk)
            removals_cum = {ref: len(oc.removals_in_boundary([r for r in err_rows_all if r['time_sec'] <= end], rs))
                            for ref, rs in oc.group_boundaries(self.rows).items() if rs[0].orientation != 'at'}
            obs = {
                'schema': oc.RAW_SCHEMA, 'sim_sec': t, 'k': k,
                'window': None if k is None else {'start_s': start, 'end_s': end},
                'directory': str(d), 'simres_steps_per_sec': 10, 'run_id': RUN_ID,
                'ground_truth_windows': self.gt_windows,
                'detector_config': {'path': str(self.csv), 'sha256': self.csv_sha, 'rows': len(self.rows)},
                'install_record': {'path': oc.INSTALL_RECORD_PATH, 'sha256': self.install_sha},
                'detectors': now, 'detectors_cum': cum, 'detectors_last_equal': None if k is None else True,
                'rule_crosscheck': {}, 'linkeval_volume_veh_h': {'10485': 100.0},
                'mer': {'source': str(self.run / 'vissim_eval' / f'sdmpc31_{self.name}_001.mer'),
                        'chunk': oc.mer_chunk_path(t), 'chunk_sha256': entry['chunk_sha256'], 'index': oc.MER_INDEX_PATH,
                        'index_sha256': entry['entry_sha256'], 'prev_index_sha256': previous,
                        'byte_start': 0, 'byte_end': 0, 'max_t_any': max_t, 'records_cum_by_dcp': records},
                'err': {'source': str(self.err), 'chunk': oc.err_chunk_path(t), 'chunk_sha256': _sha(err_bytes_chunk),
                        'byte_start': err_start, 'byte_end': err_start, 'partial_tail_bytes': 0,
                        'max_sim_sec': max((r['time_sec'] for r in err_rows_all if r['time_sec'] <= end), default=None),
                        'removals': len([r for r in err_chunk_rows if r['kind'] == 'lane_change_removal']),
                        'unparsed_removal_lines': 0, 'removals_cum_by_boundary': dict(sorted(removals_cum.items()))},
                'signal_log': {'scs': ['5'], 'start': {'-'.join(oc.parse_head_ref(ref)[1:]): {'owner': 'native'}
                                                       for ref in self.greens},
                               'events': [], 'complete': True},
                'source_cumulative_vehs': {'FW_E': 0, 'FW_W': sum(cum[str(r.dcm_no)] for r in self.rows
                                                                  if r.role == 'source')},
                'frames': {'current': {'path': oc.frame_path(end), 'sha256': frame_sha[end],
                                       'vehicles': len(self.frame(end)['vehicles'])},
                           'previous': {'path': oc.frame_path(start), 'sha256': frame_sha[start]}},
            }
            if k is None:
                obs['open_interval'] = {'k': 1, 'end_s': 1}
            oc.validate_raw(obs, self.rows, expected_simres=10)
            state = {'sim_sec': t, 'network_path': str(self.inpx),
                     'run_provenance': {'run_id': RUN_ID, 'manifest_path': str(self.provenance_path)},
                     'lane_plant_observation': {'directory': str(d / 'lane_observations'), 'run_id': RUN_ID,
                                                'time_s': t, 'cadence': oc.LANE_META_CADENCE},
                     'local_observation': {'far_measurement': {'interval_sec': 150, 'freeway_exit_count': None,
                                                               'link_volume_veh_h': {}}},
                     oc.RAW_STATE_KEY: obs}
            (d / f'state_{t:06d}.json').write_text(json.dumps(state), encoding='utf-8')
            states[t] = state
            previous = entry['entry_sha256']
        # A later capture (the run went on): the replay must cut the index back to T.
        later = {'sim_sec': 1050, 'chunk': oc.mer_chunk_path(1050), 'chunk_sha256': _sha(b''), 'byte_start': 0,
                 'byte_end': 0, 'max_t_any': None, 'records_cum_by_dcp': index[-1]['records_cum_by_dcp'],
                 'prev_entry_sha256': previous}
        later['entry_sha256'] = oc.mer_index_entry_sha256(later)
        document = {'schema': oc.MER_INDEX_SCHEMA, 'source': states[T_END][oc.RAW_STATE_KEY]['mer']['source'],
                    'entries': index + [later]}
        (d / 'obs150' / 'mer_index.json').write_bytes(oc.canonical_json_bytes(document) + b'\n')
        self.states = states
        for t in self.times:
            oc.load_bundle(states[t])
        self.write_provenance()
        self.write_derived()
        self.write_ground_truth()

    @property
    def provenance_path(self):
        return self.run / f'run_provenance_{self.name}.json'

    def write_provenance(self, workspace_root=None, env=None):
        doc = {'run_id': RUN_ID, 'name': self.name, 'workspace_root': str(workspace_root or ROOT),
               'env': env or {'RW_PYTHON': sys.executable, 'RW_OBSERVATION_CADENCE': 'decision150'},
               'files': {'generated_vbs_config': {'path': str(self.runner_config)},
                         'tuning': {'path': str(ROOT / 'x_tuning.json')},
                         'control_mapping': {'path': str(ROOT / 'x_mapping.json')},
                         'calibration': {'path': str(ROOT / 'x_calibration.json')}}}
        self.provenance_path.write_text(json.dumps(doc, indent=1), encoding='utf-8')

    # ------------------------------------------------------------ derived (the observation side)
    def green_intervals(self):
        return [list(w) for w in GREEN]

    def write_derived(self, t=T_END):
        state = self.states[t]
        obs = state[oc.RAW_STATE_KEY]
        bundle = oc.load_bundle(state)
        assignment = oc.assign_window(obs, bundle.mer_rows)
        terms = oc.evaluate_boundaries(obs, self.rows, bundle.frame_end, bundle.frame_start, bundle.err_rows)
        rows = list(bundle.mer_rows)
        heads = []
        for head in (r for r in self.rows if r.role == 'head'):
            intervals = self.greens[head.ref]
            head_id, sc, sg = oc.parse_head_ref(head.ref)
            mine = {r.seq for r in assignment.entries[head.dcp_no]}
            qualified = sum(1 for i, r in enumerate(rows)
                            if r.seq in mine and oc.classify_passage(rows, i, intervals) == 'green')
            tail = assignment.tails[head.dcp_no]
            qualified += tail if oc.tail_in_green(t, intervals) else 0
            heads.append({'head_id': head_id, 'link': '26', 'lane': head.lane, 'position_m': head.pos, 'sc': sc, 'sg': sg,
                          'crossings': obs['detectors'][str(head.dcm_no)], 'qualified_crossings': qualified,
                          'green_sec': sum(b - a for a, b in intervals), 'native_sec': 150, 'controlled_sec': 0,
                          'unverified_sec': 0, 'boundary_ambiguous': 0})
        window = {'schema': oc.HEAD_WINDOW_SCHEMA_V2, 'config_sha256': 'a' * 64, 'detector_config_sha256': self.csv_sha,
                  'start_sec': t - 150, 'end_sec': t, 'cadence_sec': 150, 'exposure_method': oc.HEAD_EXPOSURE_METHOD_V2,
                  'clock_complete': True, 'heads': heads, 'bypass_link_exits': {'403': 0}}
        window_removals = oc.window_removals(bundle.err_rows, t - 150, t)
        chain_removals = sum(1 for r in window_removals if r['link'] in (26, 10771, 120))
        off_total = terms['off_entry:10485'].cross
        chain_end = terms['chain_end:FW_W'].cross
        through = terms['through:10485'].cross
        self.derived = {
            'schema': oc.DERIVED_SCHEMA, 'sim_sec': t, 'k': t // 150, 'window': {'start_s': t - 150, 'end_s': t},
            'run_id': RUN_ID, 'strict': True,
            'inputs': {'raw_sha256': oc.canonical_sha256(obs), 'detector_config_sha256': self.csv_sha,
                       'mer_chunk_sha256': obs['mer']['chunk_sha256'], 'mer_index_sha256': obs['mer']['index_sha256'],
                       'err_chunk_sha256': obs['err']['chunk_sha256'],
                       'frame_current_sha256': obs['frames']['current']['sha256'],
                       'frame_previous_sha256': obs['frames']['previous']['sha256']},
            'boundaries': {ref: x.as_dict() for ref, x in terms.items()},
            'lag': {'sum_tail': assignment.sum_tail, 'max_t_any': assignment.max_t_any,
                    'threshold_s': t - 1 + 0.005, 'ok': True, 'err_max_sim_sec': obs['err']['max_sim_sec']},
            'tails': {str(k): v for k, v in assignment.tails.items()}, 'boundary_ambiguous': 0,
            'removals': {'window_total': len(window_removals), 'rows': [
                {'vehicle_id': r['vehicle_id'], 'time_sec': r['time_sec'], 'link': r['link'],
                 'position_m': r['position_m'], 'route_decision': r['route_decision'], 'route_index': r['route_index'],
                 'boundary_refs': [], 'on_chain': r['link'] in (26, 10771, 120)} for r in window_removals]},
            'head_window': window,
            'off_split': {'10485': {'downstream_veh': through, 'off_veh': off_total, 'post_branch_ramp_bypass_veh': 0,
                                    'eligible_exits_veh': through + off_total,
                                    'ratio': off_total / (through + off_total) if through + off_total else 0.0}},
            'ramp_arrival_shares': {}, 'offramp_10643_history': cf.offramp_history(t), 'offramp_10643_lane_shares': [0.5, 0.5],
            'ledger_10643': {'vehicles': [], 'by_lane': {'1': {}, '2': {}}, 'tail_by_lane': {'1': 0, '2': 0}},
            'freeway_exit_count': {'value': off_total + chain_end + chain_removals, 'off_total': off_total,
                                   'chain_end_total': chain_end, 'chain_removals': chain_removals},
            'source_boundary': {'FW_W': {'admitted_window': terms['source:FW_W'].cross}},
            'link_departures_window': {'403': 0}, 'edie_residuals': {'10485': 0.0}}
        # The write_derived format (canonical bytes + LF); validate_derived is WP-B2's, not needed here.
        oc.resolve(obs, oc.derived_path(t)).write_bytes(oc.canonical_json_bytes(self.derived) + b'\n')
        return self.derived

    # ------------------------------------------------------------ ground truth
    def write_ground_truth(self):
        s, e = T_START, T_END
        with open(self.run / 'gt_veh.csv', 'w', encoding='latin-1', newline='') as f:
            f.write('t10,no,lane,pos,speed,route_no\n')
            for t10 in range(10 * s, 10 * e + 1):
                for veh in self.vehicles:
                    p = position(veh, t10 / 10)
                    if p is not None:
                        f.write(f'{t10},{veh[0]},{p[0]}-{p[1]},{p[2]!r},{veh[3] * 3.6!r},1\n')
        with open(self.run / 'gt_sig.csv', 'w', encoding='latin-1', newline='') as f:
            f.write('t10,sc,sg,sig_state,t_sig_state\n')
            for t10 in range(10 * s, 10 * e + 1):
                for sc, sg, green in self.signal_states(t10):
                    f.write(f'{t10},{sc},{sg},{"GREEN" if green else "RED"},0\n')
        with open(self.run / 'gt_meta.csv', 'w', encoding='latin-1', newline='') as f:
            f.write('step,t10,sim_sec\n')
            for i, t10 in enumerate(range(10 * s, 10 * e + 1)):
                f.write(f'{i},{t10},{t10 / 10}\n')

    def signal_states(self, t10):
        """(sc, sg, green) of every head's signal group at the GT sample t10 (green on [10a, 10b))."""
        for ref, intervals in self.greens.items():
            _, sc, sg = oc.parse_head_ref(ref)
            yield sc, sg, any(10 * a <= t10 < 10 * b for a, b in intervals)

    def write_runner_ground_truth(self, links=None):
        """The same truth in the runner's own A9 format (VBS Obs150GtStepTo/Obs150GtWriteVehicles):
        <decisions>/obs150_gt/, CRLF, gt_veh 't10,veh,link,lane,pos,rout_dec_no,route_no' (no speed),
        gt_sig written before each step (t10 = 10s .. 10e-1), gt_meta 't10,sim_sec,veh_rows,...'.
        links: record only these links (the runner records obs150GtLinks: the detector links)."""
        s, e = T_START, T_END
        folder = self.decisions / 'obs150_gt'
        folder.mkdir(exist_ok=True)
        veh_rows = {}
        with open(folder / 'gt_veh.csv', 'w', encoding='latin-1', newline='') as f:
            f.write('t10,veh,link,lane,pos,rout_dec_no,route_no\r\n')
            for t10 in range(10 * s, 10 * e + 1):
                n = 0
                for veh in self.vehicles:
                    p = position(veh, t10 / 10)
                    if p is not None and (links is None or p[0] in links):
                        f.write(f'{t10},{veh[0]},{p[0]},{p[1]},{p[2]!r},,\r\n')
                        n += 1
                veh_rows[t10] = n
        with open(folder / 'gt_sig.csv', 'w', encoding='latin-1', newline='') as f:
            f.write('t10,sc,sg,sig_state\r\n')
            for t10 in range(10 * s, 10 * e):
                for sc, sg, green in self.signal_states(t10):
                    f.write(f'{t10},{sc},{sg},{"GREEN" if green else "RED"}\r\n')
        with open(folder / 'gt_meta.csv', 'w', encoding='latin-1', newline='') as f:
            f.write('t10,sim_sec,veh_rows,sig_rows,step_wall_sec\r\n')
            for t10 in range(10 * s, 10 * e + 1):
                f.write(f'{t10},{t10 / 10},{veh_rows[t10]},{0 if t10 == 10 * s else 1},0.01\r\n')
        return folder

    def truth(self, window=(T_START, T_END)):
        """Crossing counts of the trajectories themselves (independent of the comparator)."""
        s, e = window
        def count(link, x, lane=None, path=None):
            n = 0
            for veh in self.vehicles:
                t = crossing_time(veh, link, x)
                if t is not None and s < t <= e and (lane is None or recorded_lane(veh, t) == lane):
                    n += 1
            return n
        return {'source': count(26, 0.0), 'off': count(10485, 0.0), 'through': count(26, 130.0),
                'chain_end': count(120, 100.0), 'head': count(26, 100.0, lane=1)}
