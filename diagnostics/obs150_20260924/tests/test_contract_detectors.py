"""WP-0: detector CSV format (plan 1.7) - canonical bytes and every row rule."""
from __future__ import annotations

import dataclasses
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_fixtures as fx  # noqa: E402
from contract_fixtures import c  # noqa: E402


def _replace(rows, index, **changes):
    rows = list(rows)
    rows[index] = dataclasses.replace(rows[index], **changes)
    return tuple(rows)


def _index(rows, role, ref=None):
    return next(i for i, r in enumerate(rows) if r.role == role and (ref is None or r.ref == ref))


class DetectorCsvRoundTrip(unittest.TestCase):
    def test_format_parse_is_byte_stable(self):
        rows = fx.detector_rows()
        data = c.format_detector_csv(rows)
        self.assertTrue(data.startswith(b'dcp_no,dcm_no,role,ref,link,lane,pos,pos_mode,orientation,'
                                        b'boundary_ref,segment_json,geometry_assert\n'))
        self.assertNotIn(b'\r', data)
        parsed = c.parse_detector_csv(data)
        self.assertEqual(c.format_detector_csv(parsed), data)
        self.assertEqual([r.dcp_no for r in parsed], [r.dcp_no for r in rows])
        self.assertEqual(parsed[_index(parsed, 'off_entry', '10643')].segment,
                         (c.SegmentPiece(10643, 0.0, 1.0, (1,)),))

    def test_first_ten_fields_split_plainly_for_vbs(self):
        # VBS reads Split(line, ",", 11): the first 10 fields carry no comma/quote.
        for line in c.format_detector_csv(fx.detector_rows()).decode('ascii').splitlines()[1:]:
            fields = line.split(',', 10)
            self.assertEqual(len(fields), 11)
            self.assertTrue(all('"' not in f for f in fields[:10]))
            self.assertTrue(fields[10].startswith(('[],', '"[')))

    def test_read_checks_the_pin(self):
        data = c.format_detector_csv(fx.detector_rows())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'd.csv'
            path.write_bytes(data)
            rows, digest = c.read_detector_csv(path, hashlib.sha256(data).hexdigest())
            self.assertEqual(digest, hashlib.sha256(data).hexdigest())
            self.assertEqual(len(rows), len(fx.detector_rows()))
            with self.assertRaises(c.ObsContractError):
                c.read_detector_csv(path, 'f' * 64)

    def test_parse_rejects_non_canonical_bytes(self):
        data = c.format_detector_csv(fx.detector_rows())
        for bad in (data.replace(b'\n', b'\r\n'),
                    data.replace(b',1.000000,', b',1.0,', 1),
                    data.replace(b'dcp_no,', b'dcp,', 1),
                    data.replace(b'"[', b'" [', 1)):
            with self.assertRaises(c.ObsContractError):
                c.parse_detector_csv(bad)


class DetectorRowRules(unittest.TestCase):
    def assertRejected(self, rows):
        with self.assertRaises(c.ObsContractError):
            c.validate_detector_rows(rows)

    def test_fixture_is_valid(self):
        c.validate_detector_rows(fx.detector_rows())

    def test_keys(self):
        rows = fx.detector_rows()
        self.assertRejected(_replace(rows, 0, dcm_no=rows[0].dcp_no + 1000))
        self.assertRejected(_replace(rows, 0, dcp_no=910045, dcm_no=910045))
        self.assertRejected(_replace(rows, 1, dcp_no=rows[0].dcp_no, dcm_no=rows[0].dcp_no))
        self.assertRejected(tuple(reversed(rows)))

    def test_role_orientation_and_boundary_ref(self):
        rows = fx.detector_rows()
        i = _index(rows, 'source')
        self.assertRejected(_replace(rows, i, orientation='up'))
        self.assertRejected(_replace(rows, i, boundary_ref='source:FW_W'))
        self.assertRejected(_replace(rows, i, role='sources'))
        h = _index(rows, 'head')
        self.assertRejected(_replace(rows, h, ref='90030883'))

    def test_segments(self):
        rows = fx.detector_rows()
        h = _index(rows, 'head')
        self.assertRejected(_replace(rows, h, segment=(c.SegmentPiece(71, 0.0, 1.0),)))
        d = _index(rows, 'off_entry')
        self.assertRejected(_replace(rows, d, segment=()))
        self.assertRejected(_replace(rows, d, segment=(c.SegmentPiece(rows[d].link, 0.0, 2.0, (1,)),)))
        self.assertRejected(_replace(rows, d, segment=(c.SegmentPiece(rows[d].link, 1.0, 1.0, (1,)),)))
        u = _index(rows, 'chain_end')
        self.assertRejected(_replace(rows, u, segment=(c.SegmentPiece(rows[u].link, 499.8, 500.0, (1,)),)))

    def test_positions_and_geometry(self):
        rows = fx.detector_rows()
        d = _index(rows, 'off_entry')
        self.assertRejected(_replace(rows, d, pos=1.0000001))
        u = _index(rows, 'chain_end')
        self.assertRejected(_replace(rows, u, pos=499.8, segment=(c.SegmentPiece(rows[u].link, 499.8, 500.0, (1,)),)))
        self.assertRejected(_replace(rows, u, geometry_assert={'link_length_m': 500.0, 'lane_count': 4}))
        self.assertRejected(_replace(rows, d, lane=9))
        t = _index(rows, 'through')
        self.assertRejected(_replace(rows, t, pos=20000.0))

    def test_one_row_per_lane_and_boundary(self):
        rows = fx.detector_rows()
        i = _index(rows, 'source', 'FW_E')
        self.assertRejected(_replace(rows, i + 1, lane=rows[i].lane,
                                     segment=(c.SegmentPiece(74, 0.0, 1.0, (rows[i].lane,)),)))

    def test_head_ref(self):
        self.assertEqual(c.parse_head_ref('90030883|1004-2'), ('90030883', '1004', '2'))
        self.assertEqual(c.expected_boundary_ref('meter_head', '90030898|9106-1'), 'meter_head:90030898')
        self.assertEqual(c.expected_boundary_ref('ramp_arrival', 'RM_C10681'), 'ramp_arrival:RM_C10681')
        with self.assertRaises(c.ObsContractError):
            c.expected_boundary_ref('x10643_exit', '10642')


if __name__ == '__main__':
    unittest.main()
