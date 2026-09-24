"""WP-0: obs150-raw/v1, capture meta, chunk rows, the mer index chain, loaders, install record (plan 1.4)."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_fixtures as fx  # noqa: E402
from contract_fixtures import c  # noqa: E402


def mutated(obs, path, value=None, *, delete=False):
    obs = copy.deepcopy(obs)
    target = obs
    for key in path[:-1]:
        target = target[key]
    if delete:
        del target[path[-1]]
    else:
        target[path[-1]] = value
    return obs


class RawSchema(unittest.TestCase):
    def test_fixtures_are_valid(self):
        rows = fx.detector_rows()
        c.validate_raw(fx.raw_obs(900, rows), rows, expected_simres=10)
        c.validate_raw(fx.raw_obs(1, rows), rows, expected_simres=10)
        c.validate_raw(fx.raw_obs(150, rows), rows)

    def test_each_rule_rejects(self):
        rows = fx.detector_rows()
        obs = fx.raw_obs(900, rows)
        key = next(iter(obs['detectors']))
        cases = [
            (('schema',), 'obs150-raw/v2'), (('sim_sec',), 901), (('k',), 5),
            (('window',), {'start_s': 749, 'end_s': 900}), (('detectors_last_equal',), False),
            (('open_interval',), {'k': 1, 'end_s': 1}), (('extra',), 1), (('directory',), ''),
            (('simres_steps_per_sec',), 1), (('ground_truth_windows',), [[700, 900]]),
            (('install_record', 'path'), 'obs150_install.json'), (('detectors', key), 3.0),
            (('detectors_cum', key), 2), (('rule_crosscheck', 'x'), 1), (('linkeval_volume_veh_h', '10643'), -1.0),
            (('mer', 'chunk'), 'obs150/mer_900.jsonl'), (('mer', 'prev_index_sha256'), None),
            (('mer', 'records_cum_by_dcp', key), 21), (('mer', 'records_cum_by_dcp', key), 16),
            (('err', 'unparsed_removal_lines'), 1), (('err', 'byte_start'), 1000),
            (('source_cumulative_vehs', 'FW_E'), 79),
            (('frames', 'previous', 'path'), 'lane_observations/frame_000900.json'),
            (('frames', 'current', 'vehicles'), -1), (('detector_config', 'rows'), 5),
        ]
        for path, value in cases:
            with self.subTest(path=path), self.assertRaises(c.ObsContractError):
                c.validate_raw(mutated(obs, path, value), rows, expected_simres=10)
        for path in (('mer',), ('signal_log',), ('frames',)):
            with self.subTest(path=path), self.assertRaises(c.ObsContractError):
                c.validate_raw(mutated(obs, path, delete=True), rows)

    def test_t1_rules(self):
        rows = fx.detector_rows()
        obs = fx.raw_obs(1, rows)
        key = next(iter(obs['detectors']))
        for path, value in ((('detectors_cum', key), 5), (('mer', 'byte_start'), 10),
                            (('mer', 'prev_index_sha256'), fx.SHA_A), (('open_interval',), {'k': 1, 'end_s': 150}),
                            (('detectors_last_equal',), True),
                            (('frames', 'previous', 'path'), 'lane_observations/frame_000001.json')):
            with self.subTest(path=path), self.assertRaises(c.ObsContractError):
                c.validate_raw(mutated(obs, path, value), rows)
        with self.assertRaises(c.ObsContractError):
            c.validate_raw(mutated(obs, ('open_interval',), delete=True), rows)


class SignalLog(unittest.TestCase):
    def log(self):
        return copy.deepcopy(fx.raw_obs(900)['signal_log'])

    def test_valid_sequences(self):
        log = self.log()
        log['events'] = [[750, '9106', '1', 'write', 'RED'], [800, '1004', '2', 'own', True],
                         [800, '1004', '2', 'write', 'GREEN'], [830, '1004', '2', 'write', 'RED'],
                         [899, '1004', '2', 'own', False]]
        c.validate_signal_log(log, 750, 900)       # the writes at the first stop T-150 are events (CONTRACT 2.3)
        log['events'].append([899, '9106', '1', 'fail', 'RED', 'ERR:readback=GREEN'])
        log['complete'] = False
        c.validate_signal_log(log, 750, 900)

    def test_rejections(self):
        base = self.log()
        cases = []
        for events in ([[900, '9106', '1', 'write', 'RED']], [[749, '9106', '1', 'write', 'RED']],
                       [[800, '1004', '2', 'write', 'RED']], [[820, '9106', '1', 'write', 'RED'],
                                                              [810, '9106', '1', 'write', 'GREEN']],
                       [[800, '9106', '1', 'write', 'red']], [[800, '9106', '1', 'own', 'yes']],
                       [[800, '9106', '1', 'fail', 'RED', 'ERR:x']], [[800, '9106', '1', 'write']],
                       [[800.5, '9106', '1', 'write', 'RED']], [[800, '9106', '2', 'write', 'RED']]):
            log = copy.deepcopy(base)
            log['events'] = events
            cases.append(log)
        unverified = copy.deepcopy(base)
        unverified['start']['9106-1']['verified'] = False
        cases.append(unverified)
        missing_sc = copy.deepcopy(base)
        missing_sc['scs'].append('7')
        cases.append(missing_sc)
        native_state = copy.deepcopy(base)
        native_state['start']['1004-2'] = {'owner': 'native', 'state': 'GREEN'}
        cases.append(native_state)
        for log in cases:
            with self.subTest(log=log['events']), self.assertRaises(c.ObsContractError):
                c.validate_signal_log(log, 750, 900)


def write_bundle(folder, t=900):
    """Materialize a pinned bundle on disk the way the runner and the capture CLI do."""
    rows = fx.detector_rows()
    obs = fx.raw_obs(t, rows)
    obs['directory'] = str(folder)
    start, end, _ = c.bundle_interval(t)
    (folder / 'obs150').mkdir()
    (folder / 'lane_observations').mkdir()
    dcp = rows[0].dcp_no
    mer_rows = [[10, dcp, 760.25, None, 5, 100, 48.2, 4.5, 18], [11, dcp, None, 760.51, 5, 100, 48.0, 4.5, None],
                [12, dcp, 899.12, None, 6, 100, 51.0, 4.5, 19]]
    mer_bytes = ''.join(json.dumps(r) + '\n' for r in mer_rows).encode('utf-8')
    (folder / c.mer_chunk_path(t)).write_bytes(mer_bytes)
    err_rows = [{'kind': 'lane_change_removal', 'message': 'Simulation second 812.0: ... removed', 'byte_offset': 300,
                 'raw_line_sha256': fx.SHA_A, 'time_sec': 812.0, 'wait_sec': 60.0, 'vehicle_id': 77,
                 'route_decision': 1126, 'route_index': 1, 'link': 71, 'position_m': 12.5},
                {'kind': 'unparsed', 'message': 'Error\tSub-attribute not specified', 'byte_offset': 420,
                 'raw_line_sha256': fx.SHA_B}]
    err_bytes = ''.join(json.dumps(r) + '\n' for r in err_rows).encode('utf-8')
    (folder / c.err_chunk_path(t)).write_bytes(err_bytes)
    entries = []
    previous = None
    for sim_sec in (750, t):
        entry = {'sim_sec': sim_sec, 'chunk': c.mer_chunk_path(sim_sec),
                 'chunk_sha256': hashlib.sha256(mer_bytes).hexdigest() if sim_sec == t else fx.SHA_C,
                 'byte_start': 0, 'byte_end': 10, 'max_t_any': 899.42,
                 'records_cum_by_dcp': obs['mer']['records_cum_by_dcp'], 'prev_entry_sha256': previous}
        entry['entry_sha256'] = c.mer_index_entry_sha256(entry)
        previous = entry['entry_sha256']
        entries.append(entry)
    (folder / c.MER_INDEX_PATH).write_text(json.dumps({'schema': c.MER_INDEX_SCHEMA, 'source': 'x.mer',
                                                        'entries': entries}), encoding='utf-8')
    obs['mer'].update(chunk_sha256=hashlib.sha256(mer_bytes).hexdigest(), index_sha256=entries[-1]['entry_sha256'],
                      prev_index_sha256=entries[0]['entry_sha256'])
    obs['err']['chunk_sha256'] = hashlib.sha256(err_bytes).hexdigest()
    for key, sec, vehicles in (('current', end, [(1, 74, 1, 0.4)]), ('previous', start, [])):
        # The VBS writer uses CreateTextFile(..., True): UTF-16 LE with BOM.
        data = json.dumps(fx.frame(sec, vehicles)).encode('utf-16')
        (folder / c.frame_path(sec)).write_bytes(data)
        obs['frames'][key]['sha256'] = hashlib.sha256(data).hexdigest()
    obs['frames']['current']['vehicles'] = 1
    return {'sim_sec': t, c.RAW_STATE_KEY: obs}, rows


class Loaders(unittest.TestCase):
    def test_bundle_loads_and_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw, rows = write_bundle(Path(tmp))
            c.validate_raw(raw['obs150'], rows)
            bundle = c.load_bundle(raw)
            self.assertEqual([r.seq for r in bundle.mer_rows], [10, 11, 12])
            self.assertEqual(bundle.mer_rows[1].t_file, 760.51)
            self.assertEqual(bundle.err_rows[0]['link'], 71)
            self.assertEqual(bundle.frame_end['vehicles'][0][1], 74)
            self.assertEqual(c.window_removals(bundle.err_rows, 750, 900)[0]['vehicle_id'], 77)

    def test_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw, _ = write_bundle(Path(tmp))
            path = Path(tmp) / c.mer_chunk_path(900)
            path.write_bytes(path.read_bytes().replace(b'899.12', b'899.13'))
            with self.assertRaises(c.ObsContractError):
                c.load_bundle(raw)
        with tempfile.TemporaryDirectory() as tmp:
            raw, _ = write_bundle(Path(tmp))
            index = json.loads((Path(tmp) / c.MER_INDEX_PATH).read_text(encoding='utf-8'))
            index['entries'][0]['byte_end'] = 11
            (Path(tmp) / c.MER_INDEX_PATH).write_text(json.dumps(index), encoding='utf-8')
            with self.assertRaises(c.ObsContractError):
                c.load_bundle(raw)

    def test_row_validators(self):
        self.assertEqual(c.validate_mer_row([0, 960001, 1.5, None, 3, 100, 40.0, 4.5, 1]).t_entry, 1.5)
        for bad in ([0, 960001, None, None, 3, 100, 40.0, 4.5, None], [0, 960001, 1.5, None, 3, 100, 40.0, 4.5, None],
                    [0, 960001, None, 1.5, 3, 100, 40.0, 4.5, 2], [0, 960001, 1.505, None, 3, 100, 40.0, 4.5, 1],
                    [0, 960001, 1.5, None, 3, 100, 40.0, 4.5]):
            with self.subTest(bad=bad), self.assertRaises(c.ObsContractError):
                c.validate_mer_row(bad)
        removal = {'kind': 'lane_change_removal', 'message': 'm', 'byte_offset': 1, 'raw_line_sha256': fx.SHA_A,
                   'time_sec': 1.0, 'wait_sec': 60.0, 'vehicle_id': 1, 'route_decision': 1126, 'route_index': 1,
                   'link': 71, 'position_m': 2.0}
        c.validate_err_row(removal)
        for change in ({'link': '71'}, {'line_number': 3}, {'byte_offset': -1}):
            with self.subTest(change=change), self.assertRaises(c.ObsContractError):
                c.validate_err_row({**removal, **change})


class CaptureMeta(unittest.TestCase):
    def test_bytes_splice_into_the_state(self):
        obs = fx.raw_obs(900)
        meta = {'mer': obs['mer'], 'err': obs['err']}
        data = c.capture_meta_bytes(meta, 900)
        self.assertTrue(data.startswith(b'{"mer":{') and data.endswith(b'}') and b'\n' not in data)
        inner = data[1:-1].decode('ascii')
        self.assertEqual(json.loads('{' + inner + '}'), meta)
        with self.assertRaises(c.ObsContractError):
            c.capture_meta_bytes(meta, 1050)
        with self.assertRaises(c.ObsContractError):
            c.validate_capture_meta({**meta, 'extra': 1}, 900)


class InstallRecord(unittest.TestCase):
    def record(self, rows):
        return {'schema': c.INSTALL_SCHEMA, 'run_id': 'run1',
                'detector_config': {'path': 'x.csv', 'sha256': fx.SHA_A, 'rows': len(rows)},
                'simres_steps_per_sec': 10,
                'points': [{'dcp_no': r.dcp_no, 'dcm_no': r.dcm_no, 'link': r.link, 'lane': r.lane, 'pos': r.pos,
                            'readback': {'link': r.link, 'lane': r.lane, 'pos': r.pos + 0.0004}} for r in rows],
                'evaluation': {'DataCollCollectData': True, 'DataCollFromTime': 0, 'DataCollInterval': 150,
                               'DataCollRawWriteFile': True, 'DataCollRawFromTime': 0, 'DataCollToTime': 9000,
                               'DataCollRawToTime': 9000}}

    def test_valid_and_rejections(self):
        rows = fx.detector_rows()
        c.validate_install_record(self.record(rows), rows)
        for change in (lambda r: r['points'][0]['readback'].update(lane=2),
                       lambda r: r['points'][0]['readback'].update(pos=r['points'][0]['pos'] + 0.01),
                       lambda r: r['evaluation'].update(DataCollInterval=300),
                       lambda r: r['evaluation'].update(DataCollCollectData=1),
                       lambda r: r['points'].pop()):
            record = self.record(rows)
            change(record)
            with self.assertRaises(c.ObsContractError):
                c.validate_install_record(record, rows)



class CumulativeRemovals(unittest.TestCase):
    def test_keys_cover_every_offset_boundary(self):
        rows = fx.detector_rows()
        obs = fx.raw_obs(900, rows)
        refs = c.offset_boundary_refs(rows)
        self.assertIn('source:FW_E', refs)
        self.assertNotIn('head:90030883', refs)
        self.assertEqual(set(obs['err']['removals_cum_by_boundary']), set(refs))
        broken = mutated(obs, ('err', 'removals_cum_by_boundary'), {ref: 0 for ref in refs[1:]})
        with self.assertRaises(c.ObsContractError):
            c.validate_raw(broken, rows)
        with self.assertRaises(c.ObsContractError):
            c.validate_raw(mutated(obs, ('err', 'removals_cum_by_boundary', refs[0]), -1), rows)

    def test_membership_ignores_lanes_and_time(self):
        rows = [r for r in fx.detector_rows() if r.boundary_ref == 'source:FW_W']
        removal = {'kind': 'lane_change_removal', 'time_sec': 10.0, 'vehicle_id': 1, 'link': 26, 'position_m': 0.5}
        outside = dict(removal, position_m=1.0, vehicle_id=2)
        other = dict(removal, link=74, vehicle_id=3)
        self.assertEqual([x['vehicle_id'] for x in c.removals_in_boundary([removal, outside, other], rows)], [1])


class DerivedFile(unittest.TestCase):
    def test_write_is_canonical_and_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw, _ = write_bundle(Path(tmp))
            derived = fx.derived(900)
            path = c.write_derived(raw, derived)
            self.assertEqual(path, Path(tmp) / 'obs150' / 'derived_000900.json')
            self.assertEqual(path.read_bytes(), c.canonical_json_bytes(derived) + b'\n')
            self.assertEqual(c.write_derived(raw, derived), path)
            changed = fx.derived(900)
            changed['edie_residuals']['10643'] = 0.05
            with self.assertRaises(c.ObsContractError):
                c.write_derived(raw, changed)
            with self.assertRaises(c.ObsContractError):
                c.write_derived(raw, fx.derived(1050))


if __name__ == '__main__':
    unittest.main()
