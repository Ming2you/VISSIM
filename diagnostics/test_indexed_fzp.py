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


if __name__ == "__main__":
    unittest.main()
