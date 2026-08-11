import hashlib
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

    def test_signal_group_rows_extend_the_schema_without_touching_the_header(self) -> None:
        """N4-5. `signal_sg` 행이 13열 헤더를 바꾸지 않고 SG 단위 타이밍을 싣는다.

        헤더를 늘리지 않은 이유는 하위호환이다. 늘리면 `UBound(parts) <> 12` 계약과
        기존 action CSV 소비자가 함께 깨진다. 대신 계획이 켜졌는데 행이 없거나,
        계획이 꺼졌는데 행이 오면 **전량 거부**한다.
        """
        runner = (ROOT / "scripts" / "run_real_world_stackelberg_controller.vbs").read_text(
            encoding="utf-8-sig"
        )
        # 헤더는 그대로여야 한다.
        self.assertIn("If UBound(parts) <> 12 Then", runner)
        self.assertIn(
            "kind,id,dsd_no,sc_no,link,lane,speed_kph,major_green,minor_green,offset,rate_vph,green_sec,metadata",
            runner,
        )
        self.assertIn('ElseIf kind = "signal_sg" Then', runner)
        self.assertIn("Function SignalSgRowValid", runner)
        self.assertIn("Function SignalGroupPlanExpectedRowCount", runner)
        self.assertIn("Function SignalGroupPlanRejectReason", runner)
        self.assertIn("Function SignalGroupPlanWindowConflictReason", runner)
        self.assertIn("ERROR=ACTION_CSV_SIGNAL_SG_WITHOUT_PLAN_CONFIG", runner)
        # 부분 적용 금지 - 계획 위반은 기존 :874-882 게이트와 같은 조건에 들어간다.
        self.assertIn(
            "signalRows <> expectedSignalRows Or sgRows <> expectedSgRows Or invalidRows > 0 Or planReason <> \"\" Then",
            runner,
        )
        # 이름 규칙은 명시적 폴백으로만 남고 사용 건수를 센다.
        self.assertIn("signalNameRuleFallbacks = signalNameRuleFallbacks + 1", runner)
        self.assertIn('WScript.Echo "SIGNAL_NAME_RULE_FALLBACKS="', runner)
        self.assertIn('WScript.Echo "SIGNAL_COGREEN_BLOCKS="', runner)
        # 계약은 행이 아니라 config 에서 온다.
        self.assertIn("Sub LoadSignalGroupPlanConfig", runner)
        self.assertIn("Sub ValidateSignalGroupPlanCoverage", runner)
        self.assertIn("RW_SIGNAL_SG_EXPECTED", runner)
        self.assertIn("RW_SIGNAL_SG_CONFLICTS", runner)

        adapter = (
            ROOT / "evaluation" / "controllers" / "vissim_stackelberg_adapter.py"
        ).read_text(encoding="utf-8-sig")
        self.assertIn("def signal_group_action_rows(", adapter)
        self.assertIn("signal_group_plan_table=load_signal_group_actuation_plan()", adapter)

    def _assert_sibling_matches_plan(self, config_path: Path, plan_path: Path) -> None:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        text = config_path.read_text(encoding="utf-8")
        joined = text.replace('" & _\n    "', "")
        expected = re.search(r'RW_SIGNAL_SG_EXPECTED = "(.*?)"\n', joined, re.DOTALL)
        conflicts = re.search(r'RW_SIGNAL_SG_CONFLICTS = "(.*?)"\n', joined, re.DOTALL)
        self.assertIsNotNone(expected, config_path)
        self.assertIsNotNone(conflicts, config_path)
        tokens = expected.group(1).split(",")
        self.assertEqual(len(tokens), plan["counts"]["signal_groups"], config_path)
        self.assertEqual(
            sum(int(token.split(":")[2]) for token in tokens),
            plan["counts"]["planned_windows"],
            config_path,
        )
        self.assertEqual(
            len([token for token in conflicts.group(1).split(";") if token]),
            plan["counts"]["conflict_pairs"],
            config_path,
        )
        # 위 셋은 **집계**만 본다. 계획이 바뀌었는데 vbs 를 다시 안 뽑으면 집계가 우연히
        # 같은 한 통과한다(실제로 그렇게 낡은 채로 커밋돼 있었다). 원본 sha 를 직접 대조해
        # "이 vbs 가 지금 그 계획에서 나왔는가"를 고정한다.
        source_sha = re.search(r'RW_SIGNAL_SG_PLAN_SOURCE_SHA256 = "([0-9a-f]{64})"', text)
        self.assertIsNotNone(source_sha, config_path)
        self.assertEqual(
            source_sha.group(1),
            hashlib.sha256(plan_path.read_bytes()).hexdigest(),
            f"{config_path.name} 이 현재 계획 산출물에서 나온 것이 아니다 - --from-plan 으로 재생성하라",
        )

    def test_generated_sg_plan_config_matches_the_plan_artifact(self) -> None:
        plan_path = ROOT / "outputs" / "signal_group_actuation_plan_v3.json"
        siblings = sorted((ROOT / "evaluation" / "generated").glob("*_sgplan.vbs"))
        if not plan_path.is_file() or not siblings:
            self.skipTest("signal group actuation plan artifacts are not built")
        # 한 파일만 보면 나중에 붙는 형제 파일이 낡은 채로 들어와도 통과한다.
        for config_path in siblings:
            with self.subTest(config=config_path.name):
                self._assert_sibling_matches_plan(config_path, plan_path)

    def test_every_run_script_config_ships_a_signal_group_plan_sibling(self) -> None:
        """형제 파일이 없는 config 로 도는 런은 **아무 액션도 적용하지 못한다.**

        어댑터는 계획 산출물(`outputs/signal_group_actuation_plan_v3.json`)이 있으면
        `signal_sg` 행을 **무조건** 싣는다 - `vissim_stackelberg_adapter.py` 의
        `if signal_group_plan_table is not None:` 이 유일한 게이트다.

        러너는 형제 파일이 없으면 `sgPlanEnabled = False` 이고, 그 상태로 온 `signal_sg`
        행을 전부 invalid 로 센다(`ERROR=ACTION_CSV_SIGNAL_SG_WITHOUT_PLAN_CONFIG`).
        `invalidRows > 0` 은 action CSV 전량 거부다. 즉 결과는 "이름 규칙으로 조용히
        도는 런" 이 아니라 **VSL·램프미터·신호를 하나도 못 쓰고 끝에 exit 3 으로 죽는 런**
        이다. 이 짝을 config 목록이 아니라 **실제 실행 스크립트** 에서 끌어와 고정한다.
        """
        plan_path = ROOT / "outputs" / "signal_group_actuation_plan_v3.json"
        if not plan_path.is_file():
            self.skipTest("signal group actuation plan artifact is not built")
        scripts = sorted(
            (ROOT / "scripts").glob("run_real_world_single_watchdog_distributed_core15n41*.ps1")
        )
        self.assertNotEqual(scripts, [], "core15n41 실행 스크립트를 못 찾았다")
        checked = 0
        for script in scripts:
            text = script.read_text(encoding="utf-8-sig")
            match = re.search(
                r'\$VbsConfig = Join-Path \$repo "evaluation\\generated\\([A-Za-z0-9_.]+\.vbs)"',
                text,
            )
            self.assertIsNotNone(match, script.name)
            config = ROOT / "evaluation" / "generated" / match.group(1)
            self.assertTrue(config.is_file(), config)
            sibling = config.with_name(config.stem + "_sgplan.vbs")
            self.assertTrue(
                sibling.is_file(),
                f"{config.name} 에 sgplan 형제 파일이 없다 - 이 config 로 도는 런은 "
                f"모든 action CSV 를 거부한다. --from-plan 으로 {sibling.name} 을 만들어라",
            )
            self._assert_sibling_matches_plan(sibling, plan_path)
            checked += 1
        self.assertGreaterEqual(checked, 3)


if __name__ == "__main__":
    unittest.main()
