"""Synthetic, contract-valid obs150 documents for unit tests (WP-0).

Every builder returns a fresh object that passes its validator; a test then
mutates one field and expects ObsContractError. Numbers are small and chosen
so every cross-field rule (identity, sums, shares) holds exactly.
Other packages may import these builders for their own tests.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.controllers import obs150_contract as c  # noqa: E402

SHA_A, SHA_B, SHA_C = 'a' * 64, 'b' * 64, 'c' * 64
OFFS = {'10481': ('FW_E', 3, (1,)), '10483': ('FW_E', 8, (1,)), '10643': ('FW_E', 13, (1, 2)),
        '10682': ('FW_E', 20, (1,)), '10479': ('FW_W', 4, (1,)), '10485': ('FW_W', 9, (1,)),
        '10648': ('FW_W', 15, (1,)), '10650': ('FW_W', 22, (1,))}
HEADS = [('90030883', '71', 1, 78.980074, '1004', '2'), ('90030880', '71', 4, 78.869329, '1004', '5'),
         ('70203', '5', 2, 120.5, '5', '2')]
METER_HEADS = [('90030898', '10681', 1, 290.720031, '9106', '1'), ('90030899', '10681', 2, 290.720031, '9106', '1')]


def _geometry(length, lanes, offset=None):
    g = {'link_length_m': length, 'lane_count': lanes}
    if offset is not None:
        g['offset_from_end_m'] = offset
    return g


def detector_rows():
    specs = []
    for head, link, lane, pos, sc, sg in HEADS:
        specs.append(('head', f'{head}|{sc}-{sg}', int(link), lane, pos, 'exact', 'at', (), _geometry(200.0, 4)))
    for head, link, lane, pos, sc, sg in METER_HEADS:
        specs.append(('meter_head', f'{head}|{sc}-{sg}', int(link), lane, pos, 'exact', 'at', (),
                      _geometry(437.517152, 2)))
    for off, (road, cell, lanes) in OFFS.items():
        for lane in lanes:
            specs.append(('off_entry', off, int(off), lane, 1.0, 'exact', 'down',
                          (c.SegmentPiece(int(off), 0.0, 1.0, (lane,)),), _geometry(50.0, len(lanes))))
        specs.append(('through', off, 2 if road == 'FW_E' else 26, 1, 400.0 * cell, 'exact', 'at', (),
                      _geometry(10784.0, 4)))
    for lane in (1, 2):
        specs.append(('x10643_exit', '10643', 10643, lane, 1651.7, 'end_minus', 'up',
                      (c.SegmentPiece(10643, 1651.7, 1651.8, (lane,)),), _geometry(1651.8, 2, 0.1)))
    for connector, lanes in (('10634', (1,)), ('10635', (1, 2)), ('10642', (1,))):
        for lane in lanes:
            specs.append(('destination', connector, int(connector), lane, 1.0, 'exact', 'down',
                          (c.SegmentPiece(int(connector), 0.0, 1.0, (lane,)),), _geometry(20.0, len(lanes))))
    for ramp, connector, lanes in (('RM_C10681', 10681, (1, 2)), ('RM_C10484', 10484, (1,))):
        for lane in lanes:
            specs.append(('ramp_arrival', ramp, connector, lane, 1.0, 'exact', 'down',
                          (c.SegmentPiece(connector, 0.0, 1.0, (lane,)),), _geometry(437.517152, len(lanes))))
    for road, link, lanes in (('FW_E', 74, 4), ('FW_W', 26, 3)):
        for lane in range(1, lanes + 1):
            specs.append(('source', road, link, lane, 1.0, 'exact', 'down',
                          (c.SegmentPiece(link, 0.0, 1.0, (lane,)),), _geometry(2701.577, lanes)))
    for road, link, lanes in (('FW_E', 24, 4), ('FW_W', 120, 3)):
        for lane in range(1, lanes + 1):
            specs.append(('chain_end', road, link, lane, 499.9, 'end_minus', 'up',
                          (c.SegmentPiece(link, 499.9, 500.0, (lane,)),), _geometry(500.0, lanes, 0.1)))
    for connector, lanes in (('10565', (1,)), ('10570', (1, 2))):
        for lane in lanes:
            specs.append(('headfree', connector, int(connector), lane, 1.0, 'exact', 'down',
                          (c.SegmentPiece(int(connector), 0.0, 1.0, (lane,)),), _geometry(30.0, len(lanes))))
    rows = []
    for i, (role, ref, link, lane, pos, mode, orientation, segment, geometry) in enumerate(specs):
        key = c.DETECTOR_KEY_RANGE[0] + i
        rows.append(c.DetectorRow(key, key, role, ref, link, lane, pos, mode, orientation,
                                  c.expected_boundary_ref(role, ref), segment, geometry))
    return tuple(rows)


def frame(t, vehicles=()):
    """lane-plant-frame/v1; vehicles are (veh, link, lane, pos[, speed])."""
    rows = []
    for v in vehicles:
        veh, link, lane, pos = v[:4]
        speed = v[4] if len(v) > 4 else 50.0
        rows.append([veh, link, lane, float(pos), float(speed), 4.5, None, None, None, None,
                     None, None, None, None, None])
    return {'schema': c.FRAME_SCHEMA, 'complete': True, 'time_s': t, 'run_id': 'run1', 'vehicles': rows}


def raw_obs(t=900, rows=None):
    rows = detector_rows() if rows is None else rows
    start, end, k = c.bundle_interval(t)
    first = k is None
    detectors = {str(r.dcm_no): (1 if first else 3) for r in rows}
    cum = {key: (value if first else 20) for key, value in detectors.items()}
    records = {key: (0 if first else 19) for key in detectors}
    sources = {road: sum(cum[str(r.dcm_no)] for r in rows if r.role == 'source' and r.ref == road)
               for road in c.ROADS}
    events = [] if first else [[start + 62, '9106', '1', 'write', 'RED'], [start + 110, '9106', '1', 'write', 'GREEN']]
    obs = {
        'schema': c.RAW_SCHEMA, 'sim_sec': t, 'k': k,
        'window': None if first else {'start_s': start, 'end_s': end},
        'directory': 'C:\\runs\\x\\decisions', 'simres_steps_per_sec': 10, 'run_id': 'run1',
        'ground_truth_windows': [[750, 900]],
        'detector_config': {'path': 'C:\\w\\obs150_detectors_v2.csv', 'sha256': SHA_A, 'rows': len(rows)},
        'install_record': {'path': c.INSTALL_RECORD_PATH, 'sha256': SHA_B},
        'detectors': detectors, 'detectors_cum': cum,
        'detectors_last_equal': None if first else True,
        'rule_crosscheck': {'910030': 12}, 'linkeval_volume_veh_h': {'10643': 812.4, '10565': None},
        'mer': {'source': 'C:\\runs\\x\\vissim_eval\\x_001.mer', 'chunk': c.mer_chunk_path(t),
                'chunk_sha256': SHA_A, 'index': c.MER_INDEX_PATH, 'index_sha256': SHA_B,
                'prev_index_sha256': None if first else SHA_C, 'byte_start': 0 if first else 1000,
                'byte_end': 5000, 'max_t_any': None if first else 899.42, 'records_cum_by_dcp': records},
        'err': {'source': 'C:\\runs\\x\\network\\x_001.err', 'chunk': c.err_chunk_path(t), 'chunk_sha256': SHA_C,
                'byte_start': 0 if first else 300, 'byte_end': 900, 'partial_tail_bytes': 0,
                'max_sim_sec': None if first else 898.7, 'removals': 0 if first else 2,
                'unparsed_removal_lines': 0,
                'removals_cum_by_boundary': {ref: 0 for ref in c.offset_boundary_refs(rows)}},
        'signal_log': {'scs': ['1004', '5', '9106'],
                       'start': {'1004-2': {'owner': 'native'}, '1004-5': {'owner': 'native'},
                                 '5-2': {'owner': 'native'},
                                 '9106-1': {'owner': 'com', 'state': 'GREEN', 'verified': True}},
                       'events': events, 'complete': True},
        'source_cumulative_vehs': sources,
        'frames': {'current': {'path': c.frame_path(end), 'sha256': SHA_A, 'vehicles': 3},
                   'previous': {'path': c.frame_path(start), 'sha256': SHA_B}},
    }
    if first:
        obs['open_interval'] = {'k': 1, 'end_s': 1}
    return obs


def head_window(t=900):
    heads = []
    for head, link, lane, pos, sc, sg in HEADS:
        heads.append({'head_id': head, 'link': link, 'lane': lane, 'position_m': pos, 'sc': sc, 'sg': sg,
                      'crossings': 40, 'qualified_crossings': 38, 'green_sec': 60, 'native_sec': 150,
                      'controlled_sec': 0, 'unverified_sec': 0, 'boundary_ambiguous': 0})
    return {'schema': c.HEAD_WINDOW_SCHEMA_V2, 'config_sha256': SHA_A, 'detector_config_sha256': SHA_B,
            'start_sec': t - 150, 'end_sec': t, 'cadence_sec': 150, 'exposure_method': c.HEAD_EXPOSURE_METHOD_V2,
            'clock_complete': True, 'heads': heads, 'bypass_link_exits': {'403': 7}}


def _splits():
    history, ratio = {}, {}
    for i, off in enumerate(OFFS):
        row = {'downstream_veh': 100 + i, 'off_veh': 10 + i, 'post_branch_ramp_bypass_veh': 0,
               'eligible_exits_veh': 110 + 2 * i}
        history[off] = row
        ratio[off] = row['off_veh'] / row['eligible_exits_veh']
    return ratio, history


def source_boundary(t=900):
    interval = 1 if t == 1 else 150
    return {'FW_E': {'admitted_window': 150, 'admitted_cum': 900, 'interval_s': interval,
                     'recent_vph': 3600.0 * 150 / interval, 'schedule_integral_veh': 950.0, 'backlog_veh': 50.0},
            'FW_W': {'admitted_window': 100, 'admitted_cum': 700, 'interval_s': interval,
                     'recent_vph': 3600.0 * 100 / interval, 'schedule_integral_veh': 650.0, 'backlog_veh': 0.0}}


def offramp_history(t=900):
    return {'off_composition': [[[10642, 0.75], [10634, 0.25]], [[10635, 0.5], [10634, 0.5]]],
            'background': {}, 'exchange_rates': [], 'information_cutoff_s': t,
            'history_start_s': max(0, t - 150), 'endogenous_background': True}


def lane_observation(t=900):
    ratio, history = _splits()
    return {'schema': c.LANE_OBS_SCHEMA_V2, 'information_cutoff_s': t, 'history_start_s': max(0, t - 150),
            'future_traffic_inputs': False, 'lane_group_dynamics': {}, 'current_exit_labels': {},
            'off_split_ratio': ratio, 'off_split_history': history,
            'frames': [frame(t, [(1, 2, 1, 100.0), (2, 2, 2, 150.0), (3, 26, 1, 10.0)])],
            'ramp_arrival_shares': {'RM_C10681': [0.25, 0.75], 'RM_C10484': [1.0]},
            'offramp_10643_history': offramp_history(t), 'offramp_10643_lane_shares': [0.4, 0.6],
            'freeway_exit_count': 321, 'source_boundary': source_boundary(t),
            'source': {'run_id': 'run1', 'manifest_sha256': SHA_A, 'derived_sha256': SHA_B,
                       **{key: SHA_C for key in c.DERIVED_INPUT_KEYS}}}


def derived(t=900):
    start, end, k = c.bundle_interval(t)
    ratio, history = _splits()
    terms = c.IdentityTerms('source:FW_E', 'source', 'down', 150, 2, 1, 0, 151,
                            (c.LaneTerms(1, 150, 2, 1, 151),), True, ())
    window = head_window(t) if k is not None else None
    return {'schema': c.DERIVED_SCHEMA, 'sim_sec': t, 'k': k,
            'window': None if k is None else {'start_s': start, 'end_s': end}, 'run_id': 'run1', 'strict': True,
            'inputs': {**{key: SHA_A for key in c.DERIVED_INPUT_KEYS}, 'detector_config_sha256': SHA_B},
            'boundaries': {'source:FW_E': terms.as_dict()},
            'lag': {'sum_tail': 2, 'max_t_any': end - 0.5, 'threshold_s': end - 1 + 0.005, 'ok': True,
                    'err_max_sim_sec': end - 1.3},
            'tails': {'960001': 1, '960002': 1}, 'boundary_ambiguous': 0,
            'removals': {'window_total': 1, 'rows': [{'vehicle_id': 77, 'time_sec': (start + end) / 2, 'link': 71,
                                                      'position_m': 12.0, 'route_decision': 1126, 'route_index': 1,
                                                      'boundary_refs': [], 'on_chain': False}]},
            'head_window': window,
            'off_split': {off: {**history[off], 'ratio': ratio[off]} for off in OFFS},
            'ramp_arrival_shares': {'RM_C10681': [0.25, 0.75], 'RM_C10484': [1.0]},
            'offramp_10643_history': offramp_history(t), 'offramp_10643_lane_shares': [0.4, 0.6],
            'ledger_10643': {'vehicles': [{'veh': 5, 'lane': 1, 'via': 'mer', 'connector': 10642,
                                           'label_source': 'destination'}],
                             'by_lane': {'1': {'10642': 1}, '2': {}}, 'tail_by_lane': {'1': 0, '2': 0}},
            'freeway_exit_count': {'value': 321, 'off_total': 300, 'chain_end_total': 20, 'chain_removals': 1},
            'source_boundary': source_boundary(t),
            'link_departures_window': {'403': 0 if k is None else 9},
            'edie_residuals': {'10643': 0.04}}


def state(t=900):
    """A state JSON as the v2 runner writes it (before merge)."""
    return {'sim_sec': t, 'run_provenance': {'run_id': 'run1', 'manifest_path': 'C:\\runs\\x\\provenance.json'},
            'lane_plant_observation': {'directory': 'C:\\runs\\x\\decisions\\lane_observations', 'run_id': 'run1',
                                       'time_s': t, 'cadence': c.LANE_META_CADENCE},
            'local_observation': {'scan_ok': True, 'link_counts': {'71': 4},
                                  'far_measurement': {'interval_sec': 150, 'freeway_exit_count': None,
                                                      'link_volume_veh_h': {'10681': 25.9}}},
            c.RAW_STATE_KEY: raw_obs(t)}


def merged(t=900):
    before = state(t)
    d = derived(t)
    after = copy.deepcopy(before)
    local = after['local_observation']
    local['signal_observation_window'] = copy.deepcopy(d['head_window'])
    local['link_departures_window'] = dict(d['link_departures_window'])
    local['far_measurement']['freeway_exit_count'] = d['freeway_exit_count']['value']
    local['far_measurement']['freeway_exit_count_provenance'] = c.FREEWAY_EXIT_PROVENANCE
    after[c.MERGED_DERIVED_KEY] = d
    return before, after


def manifest_v2():
    pin = lambda path, sha=SHA_A: {'path': path, 'sha256': sha}
    base = 'diagnostics/sdmpc_n31_20260924/'
    return {'schema': c.PLANT_SCHEMA_V2,
            'sources': {'network': pin(base + 'network/baseline_s31_v2nc.inpx'),
                        'geometry': pin(base + 'b110/geometry.json'),
                        'refined_partition': pin(base + 'b110/geometry_200_branch_guard.json'),
                        'reference_config': pin(base + 'reference_config_n31_v2.json'),
                        'parameters': pin(base + 'b110/parameters.json'),
                        'port_profile': pin(base + 'port_profile_v2/port_profile.json'),
                        'reference_protocol': pin('diagnostics/x/protocol.json'),
                        'runner_config': pin(base + 'scenario/lane_native_b110.vbs'),
                        'sig_manifest': pin(base + 'network/sig_manifest.json')},
            'membership': pin(base + 'scenario/control_area_membership_x.json'),
            'off_groups': 'diagnostics/control_improvement/x/offramp_route_inventory_v1.json',
            'observation': {'detectors': pin(base + 'obs150/obs150_detectors_v2.csv', SHA_B),
                            'expected_simres': 10, 'vehrec_interval_sec': 5},
            'source_boundary': dict(c.SOURCE_BOUNDARY_BLOCK), 'lane_groups': False, 'fw_e_terminal': 'component',
            'vsl_command_space': 'parent_21', 'future_observations': False,
            'qualification': 'integration in progress; no native9000 launch approval claimed'}


def tuning_v2(document=None):
    document = manifest_v2() if document is None else document
    return {'freeway': {'lane_plant': 'diagnostics/sdmpc_n31_20260924/plant_n31_v2.json'},
            'urban': {'capacity': {'measured': True, 'head_observation': {'enabled': True, 'min_green_sec': 30,
                                                                         'min_crossings': 10}}},
            'execution': {'native_signal_record': False,
                          'signal_vbs_config': document['sources']['runner_config']['path']}}


def context(rows=None):
    rows = detector_rows() if rows is None else rows
    boundaries = c.group_boundaries(rows)
    groups = {}
    for head, link, lane, pos, sc, sg in HEADS:
        groups.setdefault((link, sc + '_p1'), []).append(
            {'head_id': head, 'link': link, 'lane': lane, 'position_m': pos, 'sc': sc, 'sg': sg})
    offramps = {off: c.OfframpRef(off, road, cell, lanes, 'off_entry:' + off, 'through:' + off)
                for off, (road, cell, lanes) in OFFS.items()}
    ramps = {'RM_C10681': c.RampArrivalRef('RM_C10681', '10681', (1, 2), 'ramp_arrival:RM_C10681', True),
             'RM_C10484': c.RampArrivalRef('RM_C10484', '10484', (1,), 'ramp_arrival:RM_C10484', True)}
    schedule = (c.ScheduleRow(0.0, 900.0, 3000.0), c.ScheduleRow(900.0, None, 3600.0))
    return c.Obs150Context(
        manifest_sha256=SHA_A, network_sha256=SHA_B, detector_csv_path='C:\\w\\obs150_detectors_v2.csv',
        detector_csv_sha256=SHA_C, detectors=rows, boundaries=boundaries,
        chain_links={'FW_E': (74, 10699, 2, 10613, 119, 10702, 24), 'FW_W': (26, 10771, 120)},
        chain_internal_connectors=frozenset({10699, 10613, 10702, 10771}), offramps=offramps,
        ramp_arrivals=ramps, source_refs={'FW_E': 'source:FW_E', 'FW_W': 'source:FW_W'},
        chain_end_refs={'FW_E': 'chain_end:FW_E', 'FW_W': 'chain_end:FW_W'},
        headfree_refs={'10565': 'headfree:10565', '10570': 'headfree:10570'},
        x10643_exit_ref='x10643_exit:10643',
        destination_refs={x: 'destination:' + x for x in ('10634', '10635', '10642')},
        lane_map_10643={10643: {1: 1, 2: 2}, 126: {1: 1, 2: 2}, 10641: {1: 1}, 10700: {1: 1}, 71: {1: 2, 2: 1}},
        route_destinations_10643={1: 10635, 2: 10634, 3: 10642},
        head_groups={key: tuple(v) for key, v in groups.items()},
        sig_table={'1004': c.SigProgram('1004', 'C:\\n\\1004.sig', SHA_A, 1, 75, 150, {'2': ((0, 40),), '5': ((50, 90),)})},
        source_schedule={'FW_E': schedule, 'FW_W': schedule})
