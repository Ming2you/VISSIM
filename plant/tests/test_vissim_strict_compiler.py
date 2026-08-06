from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import textwrap
import unittest

from src.vissim_strict.compiler import compile_network
from src.vissim_strict.topology import canonical_json_sha256


REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_NETWORK = (
    REPO_ROOT
    / "network"
    / "real_world_gaepo_modi"
    / "modi_eval_rw_control.inpx"
)


def _write_compiler_fixture(
    root: Path, *, include_head: bool = True, active_prog_no: int = 1, daily: bool = False
) -> Path:
    head = '<signalHead no="501" lane="1 1" pos="40" sg="10 1"/>' if include_head else ""
    inpx = f"""
    <network version="702" vissimVersion="test">
      <links><link no="1" name="approach">
        <geometry><linkPolyPts>
          <linkPolyPoint x="0" y="0" zOffset="0"/>
          <linkPolyPoint x="100" y="0" zOffset="0"/>
        </linkPolyPts></geometry>
        <lanes><lane width="3.5"/></lanes>
      </link></links>
      <signalControllers><signalController no="10" name="SC10" active="true"
        type="FIXEDTIME" supplyFile2="#data#test.sig" progNo="{active_prog_no}" offset="0">
        <sgs><signalGroup no="1" name="through" amber="3" minGreen="5"
          minRed="1" redAmber="0"/></sgs>
      </signalController></signalControllers>
      <signalHeads>{head}</signalHeads>
      <simulation startTm="3600" simPeriod="7200"/>
    </network>
    """
    programs = "".join(
        f"""
        <prog id="{program_no}" cycletime="90000" switchpoint="0" offset="0"
          name="program-{program_no}"><sgs><sg sg_id="1" signal_sequence="7">
          <cmds><cmd display="3" begin="10000"/><cmd display="1" begin="40000"/></cmds>
          <fixedstates><fixedstate display="4" duration="3000"/></fixedstates>
        </sg></sgs></prog>
        """
        for program_no in (1, 2, 3)
    )
    daily_lists = (
        """
        <dailyProgLists><dailyProgList id="1000" name="weekday">
          <dailyProgListItem time="0" prog_id="1"/>
          <dailyProgListItem time="3000000" prog_id="2"/>
          <dailyProgListItem time="7200000" prog_id="3"/>
        </dailyProgList></dailyProgLists>
        """
        if daily
        else "<dailyProgLists/>"
    )
    sig = f"""
    <sc version="201602" id="10" name="SC10">
      <signaldisplays>
        <display id="1" name="Red" state="RED"/>
        <display id="3" name="Green" state="GREEN"/>
        <display id="4" name="Amber" state="AMBER"/>
      </signaldisplays>
      <signalsequences><signalsequence id="7" name="Red-Green-Amber">
        <state display="1" isFixedDuration="false" isClosed="true" defaultDuration="1000"/>
        <state display="3" isFixedDuration="false" isClosed="false" defaultDuration="5000"/>
        <state display="4" isFixedDuration="true" isClosed="true" defaultDuration="3000"/>
      </signalsequence></signalsequences>
      <sgs><sg id="1" name="through" defaultSignalSequence="7"/></sgs>
      <progs>{programs}</progs>
      {daily_lists}
    </sc>
    """
    inpx_path = root / "fixture.inpx"
    inpx_path.write_text(textwrap.dedent(inpx), encoding="utf-8")
    (root / "test.sig").write_text(textwrap.dedent(sig), encoding="utf-8")
    return inpx_path


class CanonicalSignalCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifests = [compile_network(REAL_NETWORK) for _ in range(3)]
        cls.manifest = cls.manifests[0]

    def test_real_network_controller_roles_and_program_counts(self) -> None:
        report = self.manifest["validation_report"]
        reference = self.manifest["signal_reference"]

        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["selected_model_controllers"], 41)
        self.assertEqual(report["compiled_signal_programs"], 41)
        self.assertEqual(report["compiled_all_programs"], 123)
        self.assertEqual(report["auxiliary_signal_controllers"], 8)
        self.assertEqual(report["excluded_signal_controllers"], 1)
        self.assertEqual(
            reference["auxiliary_controller_nos"],
            [str(value) for value in range(9101, 9109)],
        )
        self.assertEqual(reference["selected_controller_nos"], [
            item["controller_no"]
            for item in reference["controller_classifications"]
            if item["classification"] == "model_selected"
        ])
        self.assertEqual(
            [item["controller_no"] for item in reference["excluded_controllers"]],
            ["9004"],
        )
        self.assertEqual(
            reference["excluded_controllers"][0]["reason"],
            "explicit_sc9004_exclusion_no_signal_head_references",
        )
        self.assertEqual(reference["active_program_schedule_status"], "absent_in_inpx")
        self.assertEqual(
            reference["active_program_runtime_readback_status"], "NOT_EVALUATED"
        )
        self.assertFalse(
            any(
                error["code"] == "missing_signal_program"
                and error["entity_id"] in {f"sc:{value}" for value in range(9101, 9109)}
                for error in report["errors"]
            )
        )

    def test_selected_controllers_include_exact_heads_hash_and_all_timelines(self) -> None:
        schedules = self.manifest["schedules"]["fixed"]
        self.assertEqual(len(schedules), 41)

        for schedule in schedules:
            self.assertEqual(schedule["program_nos"], [1, 2, 3])
            self.assertEqual(len(schedule["programs"]), 3)
            self.assertEqual(
                schedule["source_sha256"],
                hashlib.sha256(
                    (REAL_NETWORK.parent / schedule["source_path"]).read_bytes()
                ).hexdigest(),
            )
            self.assertEqual(
                schedule["active_program"]["provenance"], "static_inpx_progNo"
            )
            self.assertEqual(
                schedule["active_program"]["daily_program_schedule_status"],
                "absent_in_inpx",
            )
            self.assertEqual(
                schedule["active_program"]["sig_daily_program_list_status"],
                "empty_in_sig",
            )
            self.assertEqual(
                schedule["active_program"]["runtime_readback"]["status"],
                "NOT_EVALUATED",
            )
            self.assertEqual(schedule["active_program"]["compile_time_status"], "PASS")
            self.assertFalse(schedule["active_program"]["fallback_used"])
            self.assertTrue(schedule["signal_heads"])
            self.assertTrue(
                all(
                    head["link_no"] is not None
                    and head["lane_no"] is not None
                    and head["position_m"] is not None
                    and head["sg_no"] is not None
                    for head in schedule["signal_heads"]
                )
            )

            for program in schedule["programs"]:
                self.assertIsInstance(program["cycle_length_ms"], int)
                self.assertIsInstance(program["switchpoint_ms"], int)
                self.assertIsInstance(program["program_offset_ms"], int)
                self.assertEqual(
                    program["cycle_length_sec"], program["cycle_length_ms"] / 1000.0
                )
                for timeline in program["sg_timelines"].values():
                    intervals = timeline["intervals"]
                    self.assertEqual(intervals[0]["start_ms"], 0)
                    self.assertEqual(intervals[-1]["end_ms"], timeline["cycle_length_ms"])
                    self.assertEqual(
                        [item["end_ms"] for item in intervals[:-1]],
                        [item["start_ms"] for item in intervals[1:]],
                    )
                    self.assertTrue(
                        all(isinstance(item["begin_ms"], int) for item in timeline["commands"])
                    )

    def test_three_compilations_have_identical_canonical_hashes(self) -> None:
        hashes = [canonical_json_sha256(item) for item in self.manifests]
        self.assertEqual(len(set(hashes)), 1)
        self.assertEqual(len({item["topology_hash"] for item in self.manifests}), 1)

    def test_headless_non_exception_controller_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = compile_network(
                _write_compiler_fixture(Path(directory), include_head=False)
            )

        classifications = manifest["signal_reference"]["controller_classifications"]
        self.assertEqual(classifications[0]["classification"], "invalid")
        self.assertEqual(classifications[0]["reason"], "missing_signal_head_provenance")
        self.assertEqual(manifest["signal_reference"]["excluded_controllers"], [])
        self.assertFalse(manifest["validation_report"]["valid"])
        self.assertIn(
            "missing_signal_head_provenance",
            {item["code"] for item in manifest["validation_report"]["errors"]},
        )

    def test_daily_program_list_expands_at_inpx_runtime_start_without_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = compile_network(
                _write_compiler_fixture(
                    Path(directory), active_prog_no=1000, daily=True
                )
            )

        self.assertTrue(
            manifest["validation_report"]["valid"],
            manifest["validation_report"]["errors"],
        )
        schedule = manifest["schedules"]["fixed"][0]
        active = schedule["active_program"]
        self.assertEqual(active["mode"], "daily_program_list")
        self.assertEqual(active["configured_prog_no"], 1000)
        self.assertEqual(active["effective_program_at_start"], 2)
        self.assertEqual(active["program_no"], 2)
        self.assertEqual(active["provenance"], "inpx_progNo_selects_sig_dailyProgList")
        self.assertEqual(active["simulation_start"]["time_of_day_ms"], 3_600_000)
        self.assertEqual(
            [
                (item["start_time_of_day_ms"], item["end_time_of_day_ms"], item["program_no"])
                for item in active["time_indexed_schedule"]
            ],
            [
                (0, 3_000_000, 1),
                (3_000_000, 7_200_000, 2),
                (7_200_000, 86_400_000, 3),
            ],
        )
        self.assertEqual(schedule["program"]["active_prog_no"], 2)
        self.assertFalse(active["fallback_used"])
        self.assertEqual(active["runtime_readback"]["status"], "NOT_EVALUATED")


if __name__ == "__main__":
    unittest.main()
