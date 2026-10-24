"""Verify bounded timestamp lookup retains every row of a selected block."""
from pathlib import Path
import tempfile
import unittest
from diagnostics.probe_e8_lane_receiving import IndexedFzp


class IndexedFzpTests(unittest.TestCase):
    def test_binary_lookup_returns_exact_full_blocks_and_skips_other_times(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.fzp"
            with path.open("w") as stream:
                stream.write("$VEHICLE:SIMSEC;NO;LANE\\LINK\\NO;LANE\\INDEX;POS;SPEED\n")
                for time in range(101):
                    for veh in range(200):
                        stream.write(f"{time};{veh};2;{1 + veh % 4};{veh * 1.5};12.5\n")
            reader = IndexedFzp(path)
            for time in (0, 1, 33, 50, 99, 100):
                values = reader.snapshot(time)
                self.assertEqual(set(values), set(range(200)))
                self.assertEqual(values[199], (2, 4, 298.5, 12.5))
            self.assertLess(reader.bytes_read, reader.size // 2)
            reader.handle.close()


    def test_explicit_extra_columns_preserve_blanks_and_original_default(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'extras.fzp'
            path.write_text('$VEHICLE:SIMSEC;NO;LANE\\LINK\\NO;LANE\\INDEX;POS;SPEED;DESTLANE;LNCHG\n'
                            '5.1;9;119;1;230;16;;None\n5.1;10;119;2;231;20;1;Right\n',encoding='utf-8')
            reader = IndexedFzp(path)
            try:
                base = reader.snapshot(5.1)
                full = reader.snapshot(5.1, extra_columns=('DESTLANE','LNCHG'))
                self.assertEqual({k:v[:4] for k,v in full.items()},base)
                self.assertEqual(full[9][4],{'DESTLANE':'','LNCHG':'None'})
                self.assertEqual(full[10][4],{'DESTLANE':'1','LNCHG':'Right'})
                with self.assertRaises(ValueError):reader.snapshot(5.1,extra_columns=('NOT_RECORDED',))
                with self.assertRaises(ValueError):reader.snapshot(5.1,extra_columns=('LNCHG','LNCHG'))
            finally:reader.handle.close()


if __name__ == "__main__":
    unittest.main()
