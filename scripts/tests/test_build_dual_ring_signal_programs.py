# N4-0 작업1 - 실 .sig 15개를 150 s dual-ring 으로 재작성하는 생산자의 계약 테스트
"""합성 픽스처를 쓰지 않는다. 전부 `modi_eval_rw_control.inpx` 가 `supplyFile2` 로 가리키는
실 `.sig` 15개(SG 136개)에 건다.

## 수치의 출처

목표 표는 구현을 돌려서 얻은 것이 아니라 **실측 배리어에서 손으로 유도한 것**이다.

    eff        = 150 - 3N
    f          = eff / (Bmajor_native + Bminor_native)
    Btarget_b  = B_b x f            (최대잔여법으로 정수화, 합 = eff)
    g_phase    = Btarget_b x mean_phase / sum(mean in b)
                                    (최대잔여법으로 정수화, 합 = Btarget_b)

예 - SC1 은 Bmaj 68 · Bmin 80 · f = 138/148 이므로 배리어가 63/75 로 가고,
major 평균이 34/34 라 63 을 31.5/31.5 로 나눈 뒤 동점이라 앞 현시가 1 을 가져가 32/31 이 된다.
minor 평균 58/22 는 54.375/20.625 라 뒷자리가 커서 minor 좌가 1 을 가져가 54/21 이 된다.

## 이 검사가 드러내는 것

`survey_signal_programs` 가 4현시를 강제했을 때 3 SC 가 위반했다. 현시 수를 유도하면
107·108·109 가 N=3 이 되어 그중 둘이 풀린다. **SC109 만 남는다** — minor 배리어가 native
20 s 뿐이라 170 -> 150 축소에서 17.52 s 가 되고, 그 배리어에 현시가 하나뿐이라 배리어
안에서 green_min 을 맞출 방법이 없다. 그래서 생산자는 기본값으로 **거부**하고,
명시 플래그가 있을 때만 major 배리어에서 2.484 s 를 빌려 쓴 뒤 그 편차를 기록한다.
"""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
if str(REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO / "scripts"))
if str(REPO / "plant") not in sys.path:
    sys.path.insert(0, str(REPO / "plant"))

import build_dual_ring_signal_programs as builder  # noqa: E402
from src.vissim_strict.signal_program import parse_sig  # noqa: E402


NETWORK = REPO / "network" / "real_world_gaepo_modi" / "modi_eval_rw_control.inpx"
MAPPING = (
    REPO
    / "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core15n41_20260805.json"
)

SC_ORDER = [1, 5, 6, 11, 12, 101, 105, 107, 108, 109, 1001, 1002, 1003, 1004, 1005]

# 손으로 유도한 목표 녹색 [s]. 없는 현시는 키가 없다.
EXPECTED_GREEN = {
    1: {"major_through": 32, "major_left": 31, "minor_through": 54, "minor_left": 21},
    5: {"major_through": 47, "major_left": 25, "minor_through": 43, "minor_left": 23},
    6: {"major_through": 52, "major_left": 22, "minor_through": 43, "minor_left": 21},
    11: {"major_through": 34, "major_left": 33, "minor_through": 36, "minor_left": 35},
    12: {"major_through": 32, "major_left": 32, "minor_through": 50, "minor_left": 24},
    101: {"major_through": 39, "major_left": 24, "minor_through": 48, "minor_left": 27},
    105: {"major_through": 35, "major_left": 34, "minor_through": 48, "minor_left": 21},
    107: {"major_through": 78, "major_left": 38, "minor_left": 25},
    108: {"major_through": 88, "major_left": 22, "minor_through": 31},
    109: {"major_through": 90, "major_left": 31, "minor_left": 20},
    1001: {"major_through": 45, "major_left": 24, "minor_through": 46, "minor_left": 23},
    1002: {"major_through": 45, "major_left": 24, "minor_through": 46, "minor_left": 23},
    1003: {"major_through": 45, "major_left": 24, "minor_through": 46, "minor_left": 23},
    1004: {"major_through": 45, "major_left": 24, "minor_through": 46, "minor_left": 23},
    1005: {"major_through": 45, "major_left": 24, "minor_through": 46, "minor_left": 23},
}

# 손으로 잰 native 배리어 녹색 [s] = (배리어 안 SG 녹색+황색 합집합 길이) - 현시수 x 3.
EXPECTED_NATIVE_BARRIER = {
    1: (68.0, 80.0),
    5: (77.0, 71.0),
    6: (79.0, 69.0),
    11: (67.0, 71.0),
    12: (59.0, 69.0),
    101: (68.0, 80.0),
    105: (69.0, 69.0),
    107: (133.0, 28.0),
    108: (126.0, 35.0),
    109: (141.0, 20.0),
    1001: (69.0, 69.0),
    1002: (69.0, 69.0),
    1003: (69.0, 69.0),
    1004: (69.0, 69.0),
    1005: (69.0, 69.0),
}

PERMANENT_RED = {
    5: {"9", "11", "12", "13", "15", "16", "17", "18", "19", "21", "22", "23"},
    107: {"4", "8"},
    108: {"3", "7"},
    109: {"1", "3", "4", "8"},
}


def _plan() -> dict:
    if not hasattr(_plan, "cache"):
        _plan.cache = builder.build(NETWORK, MAPPING, allow_green_min_borrow=True)
    return _plan.cache


def _rows() -> dict[int, dict]:
    return {int(row["sc_no"]): row for row in _plan()["controllers"]}


class PhaseCountDerivationTests(unittest.TestCase):
    """현시 수는 하드코딩이 아니라 '녹색을 받는 SG 가 있는가' 로 유도된다."""

    def test_permanent_red_groups_are_twenty_and_land_only_in_four_controllers(self) -> None:
        rows = _rows()
        actual = {
            sc: {g["sg_id"] for g in row["signal_groups"] if g["permanent_red"]}
            for sc, row in rows.items()
        }
        self.assertEqual({sc: ids for sc, ids in actual.items() if ids}, PERMANENT_RED)
        self.assertEqual(sum(len(ids) for ids in actual.values()), 20)

    def test_only_107_108_109_lose_a_phase(self) -> None:
        rows = _rows()
        self.assertEqual(
            {sc: row["phase_count"] for sc, row in rows.items()},
            {sc: (3 if sc in (107, 108, 109) else 4) for sc in SC_ORDER},
        )
        self.assertEqual(rows[107]["absent_phases"], ["minor_through"])
        self.assertEqual(rows[108]["absent_phases"], ["minor_left"])
        self.assertEqual(rows[109]["absent_phases"], ["minor_through"])
        self.assertEqual(rows[1]["absent_phases"], [])

    def test_a_phase_survives_when_only_one_of_its_two_groups_is_alive(self) -> None:
        """SC109 는 WBL·NBL 이 영구적색이어도 EBL·SBL 이 살아 있어 major 좌·minor 좌가 남는다."""
        row = _rows()[109]
        self.assertEqual(row["phases"]["major_left"]["sg_ids"], ["5"])
        self.assertEqual(row["phases"]["minor_left"]["sg_ids"], ["7"])
        self.assertNotIn("minor_through", row["phases"])

    def test_derived_lost_time_and_green_box_follow_from_the_phase_count(self) -> None:
        rows = _rows()
        for sc, row in rows.items():
            n = row["phase_count"]
            self.assertEqual(row["lost_time_sec"], n * 3.0, msg=f"SC{sc}")
            self.assertEqual(row["effective_green_total_sec"], 150.0 - n * 3.0, msg=f"SC{sc}")
            self.assertEqual(row["green_max_sec"], 150.0 - n * 3.0 - (n - 1) * 20.0, msg=f"SC{sc}")
        self.assertEqual(rows[1]["effective_green_total_sec"], 138.0)
        self.assertEqual(rows[1]["green_max_sec"], 78.0)
        self.assertEqual(rows[107]["effective_green_total_sec"], 141.0)
        self.assertEqual(rows[107]["green_max_sec"], 101.0)


class NativeBarrierTests(unittest.TestCase):
    """배리어 회계가 실 프로그램에서 정확히 닫히는지."""

    def test_native_barrier_greens_match_the_hand_measurement(self) -> None:
        rows = _rows()
        self.assertEqual(
            {sc: (row["native_barrier_green_sec"]["major"], row["native_barrier_green_sec"]["minor"])
             for sc, row in rows.items()},
            EXPECTED_NATIVE_BARRIER,
        )

    def test_native_barriers_plus_clearance_close_the_native_cycle_exactly(self) -> None:
        rows = _rows()
        for sc, row in rows.items():
            total = sum(row["native_barrier_green_sec"].values())
            self.assertAlmostEqual(
                total + row["phase_count"] * 3.0,
                row["native_cycle_sec"],
                places=6,
                msg=f"SC{sc}",
            )
        self.assertEqual(rows[109]["native_cycle_sec"], 170.0)
        self.assertEqual(rows[1001]["native_cycle_sec"], 150.0)


class TargetGreenTests(unittest.TestCase):
    """재배분 결과를 초 단위로 못박는다."""

    def test_target_greens_match_the_hand_derived_table(self) -> None:
        rows = _rows()
        self.assertEqual(
            {sc: {name: phase["green_sec"] for name, phase in row["phases"].items()}
             for sc, row in rows.items()},
            EXPECTED_GREEN,
        )

    def test_every_existing_phase_clears_green_min_twenty(self) -> None:
        for sc, row in _rows().items():
            for name, phase in row["phases"].items():
                self.assertGreaterEqual(phase["green_sec"], 20.0, msg=f"SC{sc} {name}")

    def test_no_phase_exceeds_the_derived_green_max(self) -> None:
        for sc, row in _rows().items():
            for name, phase in row["phases"].items():
                self.assertLessEqual(phase["green_sec"], row["green_max_sec"], msg=f"SC{sc} {name}")

    def test_greens_plus_clearance_make_exactly_one_hundred_fifty(self) -> None:
        for sc, row in _rows().items():
            total = sum(p["green_sec"] for p in row["phases"].values())
            self.assertEqual(total + row["phase_count"] * 3.0, 150.0, msg=f"SC{sc}")

    def test_barrier_totals_are_preserved_except_in_sc109(self) -> None:
        """비례 축소는 배리어 몫을 보존한다. 못 지키는 곳은 하나뿐이고 이름으로 남는다."""
        rows = _rows()
        deviating = {}
        for sc, row in rows.items():
            factor = row["scale_factor"]
            for barrier, native in row["native_barrier_green_sec"].items():
                target = row["target_barrier_green_sec"][barrier]
                if abs(target - native * factor) > 0.5:
                    deviating.setdefault(sc, {})[barrier] = round(target - native * factor, 3)
        self.assertEqual(
            deviating,
            {109: {"major": -2.484, "minor": 2.484}},
        )

    def test_sc109_records_the_borrow_and_the_default_refuses_to_build_it(self) -> None:
        row = _rows()[109]
        self.assertEqual(row["green_min_borrow_sec"], 2.484)
        self.assertEqual(row["green_min_borrow_from"], "major")
        with self.assertRaises(builder.BuildError) as caught:
            builder.build(NETWORK, MAPPING, allow_green_min_borrow=False)
        self.assertIn("109", str(caught.exception))

    def test_the_seven_native_150_controllers_keep_their_barrier_seconds_absolutely(self) -> None:
        rows = _rows()
        for sc in (11, 105, 1001, 1002, 1003, 1004, 1005):
            self.assertEqual(rows[sc]["scale_factor"], 1.0, msg=f"SC{sc}")
            self.assertEqual(
                rows[sc]["target_barrier_green_sec"],
                {"major": EXPECTED_NATIVE_BARRIER[sc][0], "minor": EXPECTED_NATIVE_BARRIER[sc][1]},
                msg=f"SC{sc}",
            )


class LayoutTests(unittest.TestCase):
    """현시 순서와 clearance 3 s 를 창 좌표로 확인한다."""

    def test_phase_windows_follow_major_through_major_left_minor_through_minor_left(self) -> None:
        for sc, row in _rows().items():
            starts = [(name, p["green_start_sec"]) for name, p in row["phases"].items()]
            self.assertEqual(
                [name for name, _ in sorted(starts, key=lambda item: item[1])],
                [name for name in builder.PHASE_ORDER if name in row["phases"]],
                msg=f"SC{sc}",
            )

    def test_each_phase_is_followed_by_exactly_three_seconds_of_amber(self) -> None:
        for sc, row in _rows().items():
            ordered = [name for name in builder.PHASE_ORDER if name in row["phases"]]
            for index, name in enumerate(ordered):
                phase = row["phases"][name]
                nxt = row["phases"][ordered[(index + 1) % len(ordered)]]
                gap = (nxt["green_start_sec"] - (phase["green_start_sec"] + phase["green_sec"])) % 150.0
                self.assertEqual(gap, 3.0, msg=f"SC{sc} {name}")

    def test_the_first_phase_starts_at_zero_and_the_last_amber_ends_at_the_cycle(self) -> None:
        for sc, row in _rows().items():
            ordered = [name for name in builder.PHASE_ORDER if name in row["phases"]]
            self.assertEqual(row["phases"][ordered[0]]["green_start_sec"], 0.0, msg=f"SC{sc}")
            last = row["phases"][ordered[-1]]
            self.assertEqual(last["green_start_sec"] + last["green_sec"] + 3.0, 150.0, msg=f"SC{sc}")

    def test_sc107_layout_is_the_three_phase_sequence_with_no_minor_through(self) -> None:
        phases = _rows()[107]["phases"]
        self.assertEqual(phases["major_through"]["green_start_sec"], 0.0)
        self.assertEqual(phases["major_left"]["green_start_sec"], 81.0)
        self.assertEqual(phases["minor_left"]["green_start_sec"], 122.0)


class MidblockSlaveTests(unittest.TestCase):
    """SC5 의 살아 있는 midblock 슬레이브 4개는 여러 현시에 걸쳐 녹색을 유지한다."""

    def test_sc5_has_twelve_live_groups_of_which_four_are_midblock(self) -> None:
        row = _rows()[5]
        live = [g for g in row["signal_groups"] if not g["permanent_red"]]
        self.assertEqual(len(row["signal_groups"]), 24)
        self.assertEqual(len(live), 12)
        self.assertEqual(
            sorted((g["sg_id"] for g in live if g["midblock_parent_sg"]), key=int),
            ["10", "14", "20", "24"],
        )

    def test_midblock_slaves_keep_the_phase_set_they_natively_cover(self) -> None:
        row = _rows()[5]
        spans = {g["sg_id"]: g["phase_span"] for g in row["signal_groups"] if g["midblock_parent_sg"] and not g["permanent_red"]}
        self.assertEqual(spans["10"], ["minor_left", "major_through", "major_left"])
        self.assertEqual(spans["14"], ["minor_left", "major_through", "major_left"])
        self.assertEqual(spans["20"], ["major_left", "minor_through", "minor_left"])
        self.assertEqual(spans["24"], ["major_left", "minor_through", "minor_left"])

    def test_midblock_green_spans_the_intervening_clearances(self) -> None:
        groups = {g["sg_id"]: g for g in _rows()[5]["signal_groups"]}
        # minl 23 + 3 + mt 47 + 3 + ml 25
        self.assertEqual(groups["10"]["target_green_sec"], 101.0)
        # ml 25 + 3 + mint 43 + 3 + minl 23
        self.assertEqual(groups["20"]["target_green_sec"], 97.0)
        self.assertEqual(groups["10"]["native_green_sec"], 102.0)
        self.assertEqual(groups["20"]["native_green_sec"], 104.0)

    def test_a_midblock_slave_always_covers_its_own_parent_phase(self) -> None:
        for sc, row in _rows().items():
            by_id = {g["sg_id"]: g for g in row["signal_groups"]}
            for group in row["signal_groups"]:
                parent = group["midblock_parent_sg"]
                if parent is None or group["permanent_red"]:
                    continue
                self.assertIn(by_id[parent]["phase"], group["phase_span"], msg=f"SC{sc} SG{group['sg_id']}")


class BeforeAfterTableTests(unittest.TestCase):
    """SG 전수 전/후 표가 136행 전부를 덮는지."""

    def test_the_table_covers_every_one_of_the_136_signal_groups(self) -> None:
        plan = _plan()
        self.assertEqual(plan["counts"]["controllers"], 15)
        self.assertEqual(plan["counts"]["signal_groups"], 136)
        self.assertEqual(
            sum(len(row["signal_groups"]) for row in plan["controllers"]), 136
        )
        for row in plan["controllers"]:
            for group in row["signal_groups"]:
                self.assertIn("native_green_sec", group)
                self.assertIn("target_green_sec", group)
                self.assertIn("delta_green_sec", group)
                self.assertEqual(
                    group["delta_green_sec"],
                    group["target_green_sec"] - group["native_green_sec"],
                )

    def test_permanent_red_groups_stay_at_zero_green_before_and_after(self) -> None:
        for row in _plan()["controllers"]:
            for group in row["signal_groups"]:
                if group["permanent_red"]:
                    self.assertEqual(group["native_green_sec"], 0.0)
                    self.assertEqual(group["target_green_sec"], 0.0)


class WrittenProgramRoundTripTests(unittest.TestCase):
    """쓴 파일을 정본 파서로 다시 읽어 왕복이 성립하는지."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls._tmp.name)
        cls.written = builder.write_programs(_plan(), cls.out)
        cls.by_name = {row["output_sig_name"]: int(row["sc_no"]) for row in _plan()["controllers"]}

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_fifteen_files_are_written_with_new_names(self) -> None:
        self.assertEqual(len(self.written), 15)
        self.assertEqual(len(self.by_name), 15)
        for path in self.written:
            self.assertTrue(path.exists())
            self.assertIn(builder.OUTPUT_SUFFIX, path.name)
            self.assertIn(path.name, self.by_name)

    def test_every_written_program_reparses_at_a_cycle_of_150(self) -> None:
        rows = _rows()
        for path in self.written:
            program = parse_sig(path, 1)
            sc_no = self.by_name[path.name]
            self.assertEqual(program.cycle_length_sec, 150.0, msg=str(path.name))
            self.assertEqual(len(program.sg_timelines), len(rows[sc_no]["signal_groups"]))

    def test_every_signal_group_green_matches_the_plan_after_reparsing(self) -> None:
        rows = _rows()
        checked = 0
        for path in self.written:
            sc_no = self.by_name[path.name]
            program = parse_sig(path, 1)
            for group in rows[sc_no]["signal_groups"]:
                timeline = program.sg_timelines[group["sg_id"]]
                green = sum(
                    i.end_sec - i.start_sec for i in timeline.intervals if i.state == "GREEN"
                )
                self.assertEqual(green, group["target_green_sec"], msg=f"SC{sc_no} SG{group['sg_id']}")
                self.assertEqual(timeline.permanent_red, group["permanent_red"])
                checked += 1
        self.assertEqual(checked, 136)

    def test_every_amber_in_every_written_program_is_exactly_three_seconds(self) -> None:
        durations = set()
        for path in self.written:
            program = parse_sig(path, 1)
            for timeline in program.sg_timelines.values():
                for interval in timeline.intervals:
                    if interval.state == "AMBER":
                        durations.add(round(interval.end_sec - interval.start_sec, 6))
        self.assertEqual(durations, {3.0})

    def test_the_written_files_do_not_touch_the_originals(self) -> None:
        plan = _plan()
        for row in plan["controllers"]:
            source = Path(row["source_sig_path"])
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            self.assertEqual(digest, row["source_sig_sha256"], msg=str(source))
            self.assertNotIn(builder.OUTPUT_SUFFIX, source.name)

    def test_signal_group_declarations_and_sequences_survive_the_rewrite(self) -> None:
        """`sgs` 선언·signalsequence·intergreenmatrices 는 건드리지 않는다."""
        import xml.etree.ElementTree as ET

        plan = _plan()
        by_sc = {int(row["sc_no"]): row for row in plan["controllers"]}
        for path in self.written:
            sc_no = self.by_name[path.name]
            source = ET.parse(Path(by_sc[sc_no]["source_sig_path"])).getroot()
            written = ET.parse(path).getroot()
            for tag in ("signaldisplays", "signalsequences", "sgs", "intergreenmatrices"):
                self.assertEqual(
                    ET.tostring(source.find(tag), encoding="unicode"),
                    ET.tostring(written.find(tag), encoding="unicode"),
                    msg=f"{path.name}:{tag}",
                )

    def test_the_inactive_programs_are_left_at_their_native_cycles(self) -> None:
        """활성 프로그램만 다시 쓴다. prog 2·3 은 원본 그대로다."""
        import xml.etree.ElementTree as ET

        by_sc = {int(row["sc_no"]): row for row in _plan()["controllers"]}
        for path in self.written:
            sc_no = self.by_name[path.name]
            source = {
                p.get("id"): ET.tostring(p, encoding="unicode")
                for p in ET.parse(Path(by_sc[sc_no]["source_sig_path"])).getroot().findall("./progs/prog")
            }
            written = {
                p.get("id"): ET.tostring(p, encoding="unicode")
                for p in ET.parse(path).getroot().findall("./progs/prog")
            }
            self.assertEqual(sorted(source), sorted(written), msg=path.name)
            for prog_id in source:
                if prog_id == "1":
                    self.assertNotEqual(source[prog_id], written[prog_id], msg=path.name)
                else:
                    self.assertEqual(source[prog_id], written[prog_id], msg=f"{path.name}:{prog_id}")


class CommittedArtifactTests(unittest.TestCase):
    """저장소에 있는 새 `.sig` 15개가 지금 다시 빌드한 것과 바이트 동일한지."""

    def test_committed_programs_are_byte_identical_to_a_fresh_build(self) -> None:
        target_dir = NETWORK.parent
        with tempfile.TemporaryDirectory() as tmp:
            fresh = builder.write_programs(_plan(), Path(tmp))
            for path in fresh:
                committed = target_dir / path.name
                self.assertTrue(committed.exists(), msg=f"missing {committed.name}")
                self.assertEqual(
                    hashlib.sha256(committed.read_bytes()).hexdigest(),
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    msg=committed.name,
                )


if __name__ == "__main__":
    unittest.main()
