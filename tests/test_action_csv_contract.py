# action CSV 열 계약(v4, 현시 4값)을 어댑터·러너 양쪽에서 고정한다
"""헤더와 열 인덱스가 어댑터와 러너에서 **같은 한 곳**에서 나오는지 본다.

러너는 헤더를 토큰 단위로 대조하고 열 수가 다르면 그 행을 invalid 로 센다.
`invalidRows > 0` 은 부분 적용이 아니라 **전량 거부**다. 그래서 두 쪽이 갈라지면
런은 조용히 나빠지지 않고 죽는다 - 그 죽음의 조건을 여기서 못박는다.

실제 VBS 를 돌려서 재는 것은
`scripts/tests/test_action_csv_vbs_validators.py` 다(cscript + 되돌림 증명).
이 파일은 정적 대조와 산출물 정합만 본다.
"""

import hashlib
import json
import re
import unittest
from pathlib import Path

from evaluation.controllers import action_csv_schema


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts" / "run_real_world_stackelberg_controller.vbs"
ADAPTER_PATH = ROOT / "evaluation" / "controllers" / "vissim_stackelberg_adapter.py"

HEADER_TEXT = ",".join(action_csv_schema.ACTION_CSV_FIELDS)
LOG_HEADER_TEXT = ",".join(action_csv_schema.ACTION_LOG_FIELDS)
LAST_INDEX = len(action_csv_schema.ACTION_CSV_FIELDS) - 1


class ActionCsvSchemaSourceTests(unittest.TestCase):
    """열 이름이 모델 현시 어휘에서 유도되는가."""

    def test_phase_columns_are_derived_from_the_model_phase_names(self) -> None:
        from evaluation.controllers.signal_group_plan import MODEL_PHASES

        self.assertEqual(
            action_csv_schema.PHASE_GREEN_FIELDS,
            tuple(f"{phase}_green" for phase in MODEL_PHASES),
        )
        self.assertEqual(action_csv_schema.PHASE_GREEN_FIELDS,
                         ("p1_green", "p2_green", "p3_green", "p4_green"))
        self.assertEqual(action_csv_schema.ACTION_CSV_SCHEMA_VERSION, 4)

    def test_the_axis_columns_are_gone_from_the_written_schema(self) -> None:
        for field in action_csv_schema.LEGACY_AXIS_GREEN_FIELDS:
            self.assertNotIn(field, action_csv_schema.ACTION_CSV_FIELDS)

    def test_legacy_rows_stay_readable_without_being_writable(self) -> None:
        """저장소의 옛 action CSV 8천여 개는 다시 쓰지 않는다 - 읽기만 남긴다."""
        v3_signal = {"kind": "signal", "major_green": "57", "minor_green": "63"}
        v4_signal = {
            "kind": "signal", "p1_green": "63", "p2_green": "57",
            "p3_green": "0", "p4_green": "0",
        }
        self.assertFalse(action_csv_schema.row_is_v4(v3_signal))
        self.assertTrue(action_csv_schema.row_is_v4(v4_signal))
        self.assertEqual(action_csv_schema.phase_green_sum_sec(v3_signal), 120.0)
        self.assertEqual(action_csv_schema.phase_green_sum_sec(v4_signal), 120.0)
        # v3 행에는 현시 귀속이 없다. 추측하지 말고 거부한다.
        with self.assertRaises(action_csv_schema.ActionCsvSchemaError):
            action_csv_schema.phase_greens(v3_signal)

    def test_window_bounds_read_both_generations(self) -> None:
        v3_sg = {"kind": "signal_sg", "major_green": "10", "minor_green": "25"}
        v4_sg = {"kind": "signal_sg", "p1_green": "10", "p2_green": "25",
                 "p3_green": "", "p4_green": ""}
        self.assertEqual(action_csv_schema.window_bounds_sec(v3_sg), (10.0, 25.0))
        self.assertEqual(action_csv_schema.window_bounds_sec(v4_sg), (10.0, 25.0))


class ActionCsvContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = RUNNER_PATH.read_text(encoding="utf-8-sig")
        self.adapter = ADAPTER_PATH.read_text(encoding="utf-8-sig")

    def test_runner_and_adapter_agree_on_the_v4_header(self) -> None:
        # 러너 원문의 헤더 리터럴 두 곳(대조용 · 로그 기록용)이 스키마와 같아야 한다.
        self.assertIn(f'Split("{HEADER_TEXT}", ",")', self.runner)
        self.assertIn(f'actionFile.WriteLine "{LOG_HEADER_TEXT}"', self.runner)
        # 어댑터는 리터럴을 갖지 않고 스키마를 읽어야 한다.
        self.assertIn(
            "fields = list(action_csv_schema.ACTION_CSV_FIELDS)", self.adapter
        )
        for field in action_csv_schema.LEGACY_AXIS_GREEN_FIELDS:
            self.assertNotIn(f"{field},", HEADER_TEXT)

    def test_vbs_validates_full_header_and_column_count(self) -> None:
        self.assertIn("Function ActionCsvHeaderValid(parts)", self.runner)
        self.assertIn("If actual <> expected(i) Then Exit Function", self.runner)
        self.assertNotIn('Right(actual, 3) <> "ind"', self.runner)
        self.assertIn(f"If UBound(parts) <> {LAST_INDEX} Then", self.runner)
        self.assertEqual(
            self.runner.count(f"If UBound(parts) <> {LAST_INDEX} Then"), 2,
            "헤더 검사와 행 검사 두 곳이 같은 열 수를 써야 한다",
        )
        self.assertIn("seenRamp.CompareMode = 1", self.runner)
        self.assertIn("Function RampActionValid", self.runner)
        self.assertIn("Function VslActionKeyValid", self.runner)
        self.assertIn("Function IsFiniteNumberInRange", self.runner)
        self.assertIn("Not IsCsvFiniteNumber(parts(6), RW_ALLOWED_VSL_SPEEDS)", self.runner)
        self.assertIn("Function SetClassSpeedChecked", self.runner)
        self.assertIn("expectedGreen = Round", self.runner)
        self.assertIn("For i = 0 To validatedRowCount - 1", self.runner)
        self.assertEqual(self.runner.count("fso.OpenTextFile(csvPath, 1, False)"), 1)
        self.assertIn(
            "Not VslActionKeyValid(parts(1), parts(2), parts(4), parts(5))", self.runner
        )
        self.assertIn("If CStr(numberValue) <> textValue Then Exit Function", self.runner)
        self.assertIn('path.open("w", newline="", encoding="utf-8")', self.adapter)

    def test_the_signal_row_is_validated_as_four_phase_greens(self) -> None:
        self.assertIn("Function SignalActionValuesValid(parts)", self.runner)
        self.assertIn("Function PhaseGreenText(parts)", self.runner)
        self.assertIn("Function LivePhaseCount(phaseText)", self.runner)
        self.assertIn("Function SignalCycleFromPhases(phaseText)", self.runner)
        # 주기 계수는 상수 2 가 아니라 녹색 있는 현시 수다.
        self.assertIn(
            "LivePhaseCount(phaseText) * (AMBER_SEC + ALL_RED_SEC)", self.runner
        )
        self.assertNotIn("(2 * AMBER_SEC) + (2 * ALL_RED_SEC)", self.runner)
        # 현시 녹색 0 은 허용(그 현시를 안 쓴다), 0 이 아니면 쓰기 클램프 안이어야 한다.
        self.assertIn("IsFiniteNumberInRange(values(i), 0.0, 90.0)", self.runner)
        self.assertIn("If value < 5.0 Then Exit Function", self.runner)
        self.assertIn("If liveCount < 2 Then Exit Function", self.runner)

    def test_offset_and_ramp_columns_moved_with_the_new_indices(self) -> None:
        fields = action_csv_schema.ACTION_CSV_FIELDS
        self.assertEqual(fields.index("offset"), 11)
        self.assertEqual(fields.index("rate_vph"), 12)
        self.assertEqual(fields.index("green_sec"), 13)
        self.assertIn("RampActionValid(rowKey, parts(3), parts(12), parts(13))", self.runner)
        self.assertIn("rampGreen(scNo) = CDbl(Trim(CStr(parts(13))))", self.runner)
        self.assertIn("sigOffset(scNo) = CDbl(Trim(CStr(parts(11))))", self.runner)
        self.assertIn("sigPhaseGreen(scNo) = PhaseGreenText(parts)", self.runner)

    def test_a_four_phase_command_without_a_plan_is_refused(self) -> None:
        """이름 규칙(MAJOR/MINOR 두 상태)은 현시 4값을 재생할 수 없다.

        v3 에서는 계획이 없으면 이름 규칙으로 떨어졌다. v4 에서 그렇게 두면 네 현시가
        조용히 두 축으로 접힌다 - 폴백을 주 경로로 쓰는 그 모양이다. 그래서 거부한다.
        """
        self.assertIn("ERROR=ACTION_CSV_SIGNAL_WITHOUT_PLAN_CONFIG", self.runner)
        self.assertIn("ERROR=SIGNAL_PHASE_PLAN_REQUIRED", self.runner)
        # 재생 루프에도 이름 규칙 분기가 남아 있으면 안 된다.
        self.assertNotIn(
            "ApplyRuntimeSignalController CLng(scKey), majorState, minorState", self.runner
        )

    def test_every_runner_that_calls_this_adapter_is_inventoried_by_schema(self) -> None:
        """어댑터를 부르는 러너가 넷인데 v4 로 옮긴 것은 실 러너 하나다.

        나머지 셋은 v3 헤더를 들고 있으므로 **지금 이 어댑터와 같이 돌 수 없다** -
        첫 결정에서 ACTION_CSV_HEADER 로 전량 거부하고 죽는다. 조용히 나빠지지는
        않지만 못 도는 것은 사실이다. 그 사실을 목록으로 못박아, 러너를 옮기거나
        새 러너가 들어오면 이 검사가 깨지게 한다.

        옮기지 않은 이유 - 실 런 경로는 `run_real_world_stackelberg_controller.vbs`
        하나이고(core15n41 실행 스크립트가 그것만 부른다), perf 는 그 러너의 성능
        측정용 스냅샷, 나머지 둘은 8구간 시절 하네스다. 승격 판단이 따로 필요하다.
        """
        v4_runners: set[str] = set()
        v3_runners: set[str] = set()
        for path in sorted((ROOT / "scripts").glob("*.vbs")):
            text = path.read_text(encoding="utf-8-sig")
            if "vissim_stackelberg_adapter.py" not in text:
                continue
            if HEADER_TEXT in text:
                v4_runners.add(path.name)
            elif ",".join(action_csv_schema.LEGACY_ACTION_CSV_FIELDS) in text:
                v3_runners.add(path.name)
            else:
                self.fail(f"{path.name} 이 어느 세대의 헤더도 갖고 있지 않다")
        self.assertEqual(v4_runners, {"run_real_world_stackelberg_controller.vbs"})
        self.assertEqual(
            v3_runners,
            {
                "run_real_world_stackelberg_controller_perf.vbs",
                "run_stackelberg_vissim_controller.vbs",
                "run_stackelberg_vissim_controller_8seg.vbs",
            },
        )

    def test_expected_vsl_ids_are_unchanged_by_the_schema_move(self) -> None:
        generated = (
            ROOT
            / "evaluation"
            / "generated"
            / "real_world_modi_control_config_distributed_core15n41_20260805.vbs"
        ).read_text(encoding="utf-8-sig")
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

    def test_signal_group_rows_reuse_columns_instead_of_widening_the_header(self) -> None:
        """`signal_sg` 는 열을 늘리지 않고 재사용한다. 판별자는 빈 p3/p4 칸이다."""
        self.assertIn('ElseIf kind = "signal_sg" Then', self.runner)
        self.assertIn("Function SignalSgRowValid", self.runner)
        self.assertIn("Function SignalGroupPlanExpectedRowCount", self.runner)
        self.assertIn("Function SignalGroupPlanRejectReason", self.runner)
        self.assertIn("Function SignalGroupPlanWindowConflictReason", self.runner)
        self.assertIn("ERROR=ACTION_CSV_SIGNAL_SG_WITHOUT_PLAN_CONFIG", self.runner)
        self.assertIn('If Trim(CStr(parts(9))) <> "" Then Exit Function', self.runner)
        self.assertIn('If Trim(CStr(parts(10))) <> "" Then Exit Function', self.runner)
        # 부분 적용 금지 - 계획 위반은 기존 게이트와 같은 조건에 들어간다.
        self.assertIn(
            'signalRows <> expectedSignalRows Or sgRows <> expectedSgRows Or invalidRows > 0 Or planReason <> "" Then',
            self.runner,
        )
        self.assertIn('WScript.Echo "SIGNAL_COGREEN_BLOCKS="', self.runner)
        # 계약은 행이 아니라 config 에서 온다.
        self.assertIn("Sub LoadSignalGroupPlanConfig", self.runner)
        self.assertIn("Sub ValidateSignalGroupPlanCoverage", self.runner)
        self.assertIn("RW_SIGNAL_SG_EXPECTED", self.runner)
        self.assertIn("RW_SIGNAL_SG_CONFLICTS", self.runner)
        self.assertIn("def signal_group_action_rows(", self.adapter)
        self.assertIn(
            "signal_group_plan_table=load_signal_group_actuation_plan()", self.adapter
        )

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
        행을 전부 invalid 로 센다. v4 부터는 `signal` 행도 같은 이유로 거부된다
        (현시 4값을 이름 규칙으로 재생할 수 없다). `invalidRows > 0` 은 action CSV
        전량 거부이므로, 결과는 **VSL·램프미터·신호를 하나도 못 쓰고 exit 3 으로 죽는 런**
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
