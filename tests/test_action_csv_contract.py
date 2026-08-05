import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ActionCsvContractTests(unittest.TestCase):
    def test_vbs_validates_full_header_and_expected_vsl_id_set(self) -> None:
        runner = (ROOT / "scripts" / "run_real_world_stackelberg_controller.vbs").read_text(
            encoding="utf-8-sig"
        )
        generated = (
            ROOT
            / "evaluation"
            / "generated"
            / "real_world_modi_control_config_distributed_core15n41_20260805.vbs"
        ).read_text(encoding="utf-8-sig")

        self.assertIn("Function ActionCsvHeaderValid(parts)", runner)
        self.assertIn("If actual <> expected(i) Then Exit Function", runner)
        self.assertNotIn('Right(actual, 3) <> "ind"', runner)
        self.assertIn("If UBound(parts) <> 12 Then", runner)
        self.assertIn("seenRamp.CompareMode = 1", runner)
        self.assertIn("Function RampActionValid", runner)
        self.assertIn("Function VslActionKeyValid", runner)
        self.assertIn("Function IsFiniteNumberInRange", runner)
        self.assertIn("Not IsCsvFiniteNumber(parts(6), RW_ALLOWED_VSL_SPEEDS)", runner)
        self.assertIn("Function SetClassSpeedChecked", runner)
        self.assertIn("expectedGreen = Round", runner)
        self.assertIn("majorValue, 5.0, 90.0", runner)
        self.assertIn("For i = 0 To validatedRowCount - 1", runner)
        self.assertEqual(runner.count("fso.OpenTextFile(csvPath, 1, False)"), 1)
        self.assertIn(
            "kind,id,dsd_no,sc_no,link,lane,speed_kph,major_green,minor_green,offset,rate_vph,green_sec,metadata",
            runner,
        )
        self.assertIn("Not VslActionKeyValid(parts(1), parts(2), parts(4), parts(5))", runner)
        self.assertIn("If CStr(numberValue) <> textValue Then Exit Function", runner)

        adapter = (
            ROOT / "evaluation" / "controllers" / "vissim_stackelberg_adapter.py"
        ).read_text(encoding="utf-8-sig")
        self.assertIn('path.open("w", newline="", encoding="utf-8")', adapter)

        match = re.search(r'RW_EXPECTED_VSL_DSD_IDS = "([0-9,]+)"', generated)
        self.assertIsNotNone(match)
        ids = [int(value) for value in match.group(1).split(",")]
        self.assertEqual(len(ids), 71)
        self.assertEqual(len(set(ids)), 71)
        self.assertEqual(ids, list(range(36, 107)))

        self.assertIn("RW_SCHEMA_VERSION = 3", generated)
        key_match = re.search(
            r'RW_EXPECTED_VSL_ACTION_KEYS = "(.*?)"\s*\nRW_ALLOWED_VSL_SPEEDS',
            generated.replace('" & _\n    "', ""),
            re.DOTALL,
        )
        self.assertIsNotNone(key_match)
        actual_keys = key_match.group(1).split(";")
        mapping = json.loads(
            (
                ROOT
                / "evaluation"
                / "real_world_modi_control_distributed_20260728"
                / "control_mapping_distributed_core15n41_20260805.json"
            ).read_text(encoding="utf-8-sig")
        )
        expected_keys = [
            "|".join(
                (
                    str(segment["segment_id"]),
                    str(int(dsd["dsd_no"])),
                    str(int(segment["link"])),
                    str(int(dsd["lane"])),
                )
            )
            for segment in mapping["segments"]
            for dsd in segment["dsds"]
        ]
        self.assertEqual(actual_keys, expected_keys)


if __name__ == "__main__":
    unittest.main()
