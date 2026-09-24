"""WP-B1 B2: obs150_capture on synthetic .mer/.err files (failure modes, cursors, CLI contract).

The probe-data checks (V0-1, V0-2, V0-10) are in test_capture_probe.py.
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_fixtures as fx  # noqa: E402
from contract_fixtures import c as oc  # noqa: E402
from evaluation.controllers import obs150_capture as cap  # noqa: E402

ROOT = fx.ROOT
PYTHON = sys.executable
COLUMNS = (b' Measurem.;  t(Entry);   t(Exit);    VehNo; Vehicle type;    Line; v[km/h]; b[m/s2];'
           b'   Occ; Pers; tQueue; VehLength[m];')
STEM = 'net_001'


def table():
    """A head (at), a destination (down) and a chain end (up): three contract rows."""
    geometry = lambda length, lanes, offset=None: {'link_length_m': length, 'lane_count': lanes,
                                                   **({} if offset is None else {'offset_from_end_m': offset})}
    rows = [oc.DetectorRow(960001, 960001, 'head', '11|7-1', 71, 1, 78.980074, 'exact', 'at', 'head:11', (),
                           geometry(82.602857, 5)),
            oc.DetectorRow(960002, 960002, 'destination', '10642', 10642, 1, 1.0, 'exact', 'down',
                           'destination:10642', (oc.SegmentPiece(10642, 0.0, 1.0, (1,)),), geometry(67.9, 1)),
            oc.DetectorRow(960003, 960003, 'chain_end', 'FW_W', 120, 2, 4263.618, 'end_minus', 'up',
                           'chain_end:FW_W', (oc.SegmentPiece(120, 4263.618, 4263.718, (2,)),),
                           geometry(4263.718, 4, 0.1))]
    return oc.validate_detector_rows(rows)


def header(rows, *, extra=(), shift=0.0, columns=True):
    lines = [b'', b'Data Collection (Raw Data)', b'', b'File:     C:\\x\\net.inpx', b'']
    points = [(910001, 5, 1, 12.5)] + [(r.dcp_no, r.link, r.lane, r.pos + shift) for r in rows] + list(extra)
    for dcp, link, lane, pos in points:
        lines.append(b'Data collection point %8d: Link %5d lane %d at %11.3f m.' % (dcp, link, lane, pos))
    lines.append(b'')
    data = b'\r\n'.join(lines) + b'\r\n'
    return data + COLUMNS + b'\n' if columns else data


def row(dcp, t_entry, t_exit, veh, speed=50.0):
    fmt = lambda t: b'%9.2f' % (-1.0 if t is None else t)
    return (b'  %6d; %s; %s; %8d;         100;        0; %6.1f;   0.00;   0.00;    1;   0.0;     4.50;\n'
            % (dcp, fmt(t_entry), fmt(t_exit), veh, speed))


def removal(t, vehicle, link, pos, route=(1126, 1)):
    return ('                  Warning\tSimulation second %.1f: After 45.0 seconds of waiting for lane change the '
            'vehicle %d (on Static Vehicle Route %d - %d) was removed from link %d at position %.1f.\t'
            'Network object type: Vehicle\tNetwork object keys: %d\r\n'
            % (t, vehicle, route[0], route[1], link, pos, vehicle)).encode('cp949')


def route_end(t, vehicle, link, next_link, route=(1126, 2)):
    """ERRP route_next_link_not_found: a vehicle at a link end without the next link of its route."""
    return ('                  Warning\tSimulation second %.1f: Vehicle %d (on Static Vehicle Route %d - %d) arrived at '
            'the end of link %d without having found the next link (%d) of its route.\r\n'
            % (t, vehicle, route[0], route[1], link, next_link)).encode('cp949')


class Workspace:
    def __init__(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='obs150_capture_unit_')
        self.root = Path(self.temporary.name)
        for name in ('vissim_eval', 'network', 'decisions'):
            (self.root / name).mkdir()
        self.mer = self.root / 'vissim_eval' / (STEM + '.mer')
        self.err = self.root / 'network' / (STEM + '.err')
        self.out = self.root / 'decisions' / 'obs150'

    def capture(self, t, mer=None, err=None, rows=None):
        if mer is not None:
            self.mer.write_bytes(mer)
        if err is not None:
            self.err.write_bytes(err)
        return cap.capture(self.root / 'vissim_eval', self.err, self.out, t, table() if rows is None else rows)

    def files(self):
        return sorted(p.name for p in self.out.iterdir()) if self.out.exists() else []

    def chunk(self, meta):
        return oc.load_mer_chunk(self.root / 'decisions' / Path(*meta['mer']['chunk'].split('/')),
                                 meta['mer']['chunk_sha256'])

    def err_chunk(self, meta):
        return oc.load_err_chunk(self.root / 'decisions' / Path(*meta['err']['chunk'].split('/')),
                                 meta['err']['chunk_sha256'])

    def close(self):
        self.temporary.cleanup()


class CaptureCursor(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace()
        self.addCleanup(self.ws.close)

    def test_interface_signature(self):
        self.assertEqual(oc.check_module('evaluation.controllers.obs150_capture'),
                         ['evaluation.controllers.obs150_capture.capture'])

    def test_header_incomplete_at_t1_then_rows_with_seq_ordinals_and_partial_lines(self):
        rows = table()
        head = header(rows)
        # t=1: the column line is not complete yet (PR t1 stopped mid-header)
        meta1 = self.ws.capture(1, head[:-5], b'')
        self.assertEqual((meta1['mer']['max_t_any'], self.ws.chunk(meta1)), (None, []))
        self.assertEqual(meta1['mer']['records_cum_by_dcp'], {'960001': 0, '960002': 0, '960003': 0})
        self.assertLess(meta1['mer']['byte_end'], len(head))
        body = (row(910001, 3.21, None, 5) + row(960001, 140.5, None, 7) + row(910001, None, 3.47, 5)
                + row(960001, None, 141.0, 7) + row(960002, 149.3, 149.4, 9))
        partial = row(960001, 149.9, None, 8)
        meta150 = self.ws.capture(150, head + body + partial[:20], b'')
        chunk = self.ws.chunk(meta150)
        # seq counts every data row, ordinals only entries of generated points, exit-only rows keep null
        self.assertEqual([(r.seq, r.dcp, r.ordinal) for r in chunk],
                         [(1, 960001, 1), (3, 960001, None), (4, 960002, 1)])
        self.assertEqual(meta150['mer']['byte_end'], len(head + body))
        self.assertEqual(meta150['mer']['max_t_any'], 149.4)
        self.assertEqual(meta150['mer']['records_cum_by_dcp'], {'960001': 1, '960002': 1, '960003': 0})
        # the held-back line is read whole by the next capture, seq continues
        meta300 = self.ws.capture(300, head + body + partial + row(960003, 299.0, None, 11), b'')
        self.assertEqual([(r.seq, r.dcp, r.ordinal, r.t_entry) for r in self.ws.chunk(meta300)],
                         [(5, 960001, 2, 149.9), (6, 960003, 1, 299.0)])
        self.assertEqual(meta300['mer']['byte_start'], meta150['mer']['byte_end'])
        self.assertEqual(meta300['mer']['prev_index_sha256'], meta150['mer']['index_sha256'])
        index = oc.validate_mer_index(json.loads((self.ws.out / 'mer_index.json').read_text()))
        self.assertEqual(sorted(index), [1, 150, 300])
        # capture file = the contract bytes; the VBS splices Mid(text, 2, Len-2)
        data = (self.ws.out / 'capture_000300.json').read_bytes()
        self.assertEqual(data, oc.capture_meta_bytes(meta300, 300))
        self.assertTrue(data.decode('ascii')[1:-1].startswith('"mer":{') and b'\n' not in data)

    def test_lag_and_assignment_on_the_captured_chunk(self):
        rows = table()
        head = header(rows)
        self.ws.capture(1, head, b'')
        body = row(960001, 10.0, None, 1) + row(960001, 148.7, None, 2) + row(960002, 148.8, None, 3)
        meta = self.ws.capture(150, head + body, b'')
        obs = {'sim_sec': 150, 'detectors': {'960001': 3, '960002': 1, '960003': 0},
               'detectors_cum': {'960001': 3, '960002': 1, '960003': 0}, 'mer': meta['mer']}
        with self.assertRaises(oc.ObsLagError):   # one 960001 passage missing, file max 148.8 <= 149.005
            oc.assign_window(obs, self.ws.chunk(meta))

    def test_failures_write_nothing_for_the_stop(self):
        rows = table()
        head = header(rows)
        t1_files = ['capture_000001.json', 'err_000001.jsonl', 'mer_000001.jsonl', 'mer_index.json']
        # the header is checked at every stop; data rows are read from T=150 on (t=1 reads the header only)
        cases = {
            'header position differs': (1, header(rows, shift=0.002)),
            'header lacks a point': (1, header(rows[:2])),
            'row width differs': (150, head + b'  960001;    10.00;    -1.00;        1;\n'),
            'time with three decimals': (150, head + row(960001, 10.0, None, 1).replace(b'    10.00', b'   10.001')),
            'blank line in data': (150, head + b'\n' + row(960001, 10.0, None, 1)),
        }
        for name, (t, data) in cases.items():
            with self.subTest(case=name):
                ws = Workspace()
                self.addCleanup(ws.close)
                if t != 1:
                    ws.capture(1, data, b'')           # the same bytes pass at t=1: no row is read there
                with self.assertRaises(oc.ObsContractError):
                    ws.capture(t, data, b'')
                self.assertEqual(ws.files(), [] if t == 1 else t1_files)

    def test_err_failures_write_nothing(self):
        head = header(table())
        bad = b'Warning\tSimulation second 0.9: vehicle 5 was removed from link 7 at position 3.0 for no known reason.\r\n'
        with self.assertRaises(oc.ObsContractError):
            self.ws.capture(1, head, bad)
        self.assertEqual(self.ws.files(), [])
        (self.ws.root / 'network' / (STEM[:-4] + '_002.err')).write_bytes(b'')
        with self.assertRaises(oc.ObsContractError):
            self.ws.capture(1, head, b'')
        self.assertEqual(self.ws.files(), [])

    def test_err_from_after_the_stop_is_refused(self):
        """A stale _001.err of another run would slip its removals into R; its seconds give it away."""
        head = header(table())
        stale = removal(12.3, 5, 10642, 0.4) + removal(1192.6, 6, 10642, 0.5)
        with self.assertRaises(oc.ObsContractError):
            self.ws.capture(1, head, stale)
        self.assertEqual(self.ws.files(), [])
        self.ws.capture(1, head, b'')
        with self.assertRaises(oc.ObsContractError):        # one line past the stop, even an unparsed one
            self.ws.capture(150, None, removal(149.9, 5, 10642, 0.4)
                            + b'                  Warning\tSimulation second 150.1: something new.\r\n')
        meta = self.ws.capture(150, None, removal(149.9, 5, 10642, 0.4) + removal(150.0, 6, 10642, 0.5))
        self.assertEqual((meta['err']['max_sim_sec'], meta['err']['removals']), (150.0, 2))

    def test_refusals_on_replay_and_broken_chain(self):
        head = header(table())
        self.ws.capture(1, head, b'')
        with self.assertRaises(oc.ObsContractError):      # the stop was already captured
            self.ws.capture(1, head, b'')
        with self.assertRaises(oc.ObsContractError):      # skipping a decision stop
            self.ws.capture(300, head, b'')
        with self.assertRaises(oc.ObsContractError):      # not a decision stop
            self.ws.capture(151, head, b'')
        with self.assertRaises(oc.ObsContractError):      # the file shrank
            self.ws.capture(150, head[:100], b'')
        (self.ws.root / 'vissim_eval' / 'other_001.mer').write_bytes(head)
        with self.assertRaises(oc.ObsContractError):      # a second .mer in EvalOutDir
            self.ws.capture(150, head, b'')
        (self.ws.root / 'vissim_eval' / 'other_001.mer').unlink()
        index_path = self.ws.out / 'mer_index.json'
        document = json.loads(index_path.read_text())
        document['entries'][0]['byte_end'] += 1
        index_path.write_bytes(oc.canonical_json_bytes(document) + b'\n')
        with self.assertRaises(oc.ObsContractError):      # tampered index entry
            self.ws.capture(150, head, b'')
        self.assertEqual(self.ws.files(), ['capture_000001.json', 'err_000001.jsonl', 'mer_000001.jsonl',
                                           'mer_index.json'])

    def test_a_changed_file_is_refused(self):
        """The byte before the previous capture end must still end a line, and from T=150 on the
        .mer header must be complete (mid-header is a t=1 state only)."""
        head = header(table())
        self.ws.capture(1, head, removal(0.5, 5, 10642, 0.4))
        t1 = self.ws.files()
        for name, mer, err in (('mer rewritten', b'x' * len(head) + row(960001, 10.0, None, 1), None),
                               ('err rewritten', head, b'x' * len(removal(0.5, 5, 10642, 0.4)))):
            with self.subTest(case=name), self.assertRaises(oc.ObsContractError):
                self.ws.capture(150, mer, err)
            self.assertEqual(self.ws.files(), t1)
        other = Workspace()
        self.addCleanup(other.close)
        other.capture(1, head[:-5], b'')
        with self.assertRaisesRegex(oc.ObsContractError, 'header is still incomplete at 150'):
            other.capture(150, head[:-5], b'')

    @unittest.skipUnless(os.name == 'nt', 'Windows paths ignore case')
    def test_err_path_case_keeps_the_first_spelling(self):
        """The runner names the .err before VISSIM creates it; the file may carry another case."""
        self.ws.mer.write_bytes(header(table()))
        named = self.ws.err.with_name(self.ws.err.name.upper())
        meta1 = cap.capture(self.ws.root / 'vissim_eval', named, self.ws.out, 1, table())
        self.ws.err.write_bytes(removal(100.0, 5, 10642, 0.4))       # created later with the network's case
        meta150 = cap.capture(self.ws.root / 'vissim_eval', named, self.ws.out, 150, table())
        self.assertEqual(meta150['err']['source'], meta1['err']['source'])
        self.assertEqual(meta150['err']['removals'], 1)


class CaptureErr(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace()
        self.addCleanup(self.ws.close)

    def test_absent_err_then_increments_with_partial_tail_and_boundary_totals(self):
        head = header(table())
        meta1 = self.ws.capture(1, head)                    # no .err file yet: an empty file
        self.assertEqual((meta1['err']['byte_end'], meta1['err']['removals'], self.ws.err_chunk(meta1)), (0, 0, []))
        self.assertEqual((self.ws.out / 'err_000001.jsonl').read_bytes(), b'')
        first = removal(120.4, 77, 10642, 0.4) + removal(130.0, 78, 10642, 1.0)
        unknown = '                  Warning\tSimulation second 149.7: something new happened.\r\n'.encode('cp949')
        second = removal(200.0, 79, 120, 4263.7, (1140, 2))
        data = first + unknown + second
        cut = len(first + unknown) + 30
        meta150 = self.ws.capture(150, None, data[:cut])
        err = meta150['err']
        self.assertEqual((err['byte_start'], err['byte_end'], err['partial_tail_bytes']),
                         (0, len(first + unknown), 30))
        self.assertEqual(err['removals'], 2)
        self.assertEqual(err['max_sim_sec'], 149.7)         # an unparsed line still names its second
        # 10642 at 0.4 m is inside [0, 1); at 1.0 m it is the station itself (open end)
        self.assertEqual(err['removals_cum_by_boundary'], {'chain_end:FW_W': 0, 'destination:10642': 1})
        rows = self.ws.err_chunk(meta150)
        self.assertEqual([r['kind'] for r in rows], ['lane_change_removal', 'lane_change_removal', 'unparsed'])
        self.assertEqual([r['byte_offset'] for r in rows], [0, len(removal(120.4, 77, 10642, 0.4)), len(first)])
        self.assertEqual(rows[0]['link'], 10642)
        meta300 = self.ws.capture(300, None, data)
        err = meta300['err']
        self.assertEqual((err['byte_start'], err['byte_end'], err['partial_tail_bytes'], err['removals']),
                         (len(first + unknown), len(data), 0, 1))
        self.assertEqual(err['max_sim_sec'], 200.0)
        self.assertEqual(err['removals_cum_by_boundary'], {'chain_end:FW_W': 1, 'destination:10642': 1})
        self.assertEqual(self.ws.err_chunk(meta300)[0]['byte_offset'], len(first + unknown))

    def test_link_numbers_are_integers_in_every_row_that_names_one(self):
        """CONTRACT 4.2: link -> int; route_next_link_not_found also carries next_link as int (the
        10643 ledger and the removal audit look the connector up by number)."""
        head = header(table())
        self.ws.capture(1, head)
        data = removal(120.4, 77, 10642, 0.4) + route_end(131.5, 4711, 71, 10642)
        meta = self.ws.capture(150, None, data)
        rows = self.ws.err_chunk(meta)
        self.assertEqual([r['kind'] for r in rows], ['lane_change_removal', 'route_next_link_not_found'])
        self.assertEqual((rows[1]['link'], rows[1]['next_link'], rows[1]['vehicle_id']), (71, 10642, 4711))
        self.assertIs(rows[1]['explicitly_says_removed'], False)
        # 'removals' counts lane_change_removal only (CONTRACT 4.4); the route end is a row for B2's ledger
        self.assertEqual(meta['err']['removals'], 1)


class CaptureCli(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace()
        self.addCleanup(self.ws.close)
        self.csv = self.ws.root / 'obs150_detectors_v2.csv'
        self.csv.write_bytes(oc.format_detector_csv(table()))
        self.sha = hashlib.sha256(self.csv.read_bytes()).hexdigest()
        self.ws.mer.write_bytes(header(table()) + row(960001, 0.5, None, 1))

    def run_cli(self, sim_sec, sha=None):
        env = dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1')
        return subprocess.run([PYTHON, '-B', str(ROOT / oc.CAPTURE_CLI), '--eval-dir', str(self.ws.root / 'vissim_eval'),
                               '--err', str(self.ws.err), '--out-dir', str(self.ws.out), '--sim-sec', sim_sec,
                               '--detectors', str(self.csv), '--detectors-sha256', sha or self.sha],
                              capture_output=True, cwd=str(ROOT), env=env, timeout=120)

    def test_success_prints_exactly_one_line(self):
        result = self.run_cli('1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b'')
        digest = hashlib.sha256((self.ws.out / 'capture_000001.json').read_bytes()).hexdigest()
        self.assertEqual(result.stdout.decode('ascii'),
                         '%s meta=obs150/capture_000001.json sha256=%s\n' % (oc.CAPTURE_STDOUT_PREFIX, digest))
        meta = json.loads((self.ws.out / 'capture_000001.json').read_bytes())
        oc.validate_capture_meta(meta, 1)
        # t=1 reads the header only: the 0.5 s row waits for the T=150 chunk
        self.assertEqual((meta['mer']['records_cum_by_dcp']['960001'], meta['mer']['byte_end']),
                         (0, len(header(table()))))
        result = self.run_cli('150')
        self.assertEqual(result.returncode, 0, result.stderr)
        meta = json.loads((self.ws.out / 'capture_000150.json').read_bytes())
        self.assertEqual(meta['mer']['records_cum_by_dcp']['960001'], 1)

    def test_failures_exit_2_with_nothing_on_stdout(self):
        for sim_sec, sha in (('1', 'f' * 64), ('150.5', None), ('149', None)):
            with self.subTest(sim_sec=sim_sec):
                result = self.run_cli(sim_sec, sha)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, b'')
                self.assertTrue(result.stderr.startswith(b'OBS150_CAPTURE_FAIL '), result.stderr)
                self.assertEqual(result.stderr.count(b'\n'), 1)
        self.assertEqual(self.ws.files(), [])

    def test_failure_line_is_cut_in_bytes(self):
        """A non-ASCII message escapes to up to 10 bytes a character; the cut is on the encoded line."""
        spec = importlib.util.spec_from_file_location('obs150_capture_cli', ROOT / oc.CAPTURE_CLI)
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        missing = self.ws.root / ('검지기' * 300) / 'obs150_detectors_v2.csv'
        stderr = types.SimpleNamespace(buffer=io.BytesIO(), flush=lambda: None)
        with mock.patch.object(sys, 'stderr', stderr):
            code = cli.main(['--eval-dir', str(self.ws.root / 'vissim_eval'), '--err', str(self.ws.err),
                             '--out-dir', str(self.ws.out), '--sim-sec', '1', '--detectors', str(missing),
                             '--detectors-sha256', self.sha])
        line = stderr.buffer.getvalue()
        self.assertEqual(code, 2)
        self.assertTrue(line.startswith(b'OBS150_CAPTURE_FAIL ') and line.endswith(b'\n') and line.count(b'\n') == 1)
        self.assertLessEqual(len(line), cli.STDERR_LIMIT)
        self.assertEqual(len(line), cli.STDERR_LIMIT)       # the message was long enough to be cut
        line.decode('ascii')


if __name__ == '__main__':
    unittest.main()
