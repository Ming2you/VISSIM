# VISSIM 유입 지점과 모델 경계 게이트의 기하 정렬 산출물을 검사로 고정한다.
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from derive_boundary_input_alignment import derive

REAL_INPX = REPO_ROOT / "network" / "real_world_gaepo_modi" / "modi_eval_rw_control.inpx"
REAL_VI = REPO_ROOT / "evaluation" / "real_world_modi_inventory" / "vehicle_input_roles.csv"
REAL_SC = REPO_ROOT / "evaluation" / "real_world_modi_inventory" / "signal_controller_roles.csv"
REAL_ASSIGN = REPO_ROOT / "outputs" / "link_player_assignment_20260805.json"
REAL_CONFIG = (
    REPO_ROOT
    / "evaluation"
    / "configs"
    / "real_world_modi_pstack_distributed_core15n41_20260805.json"
)


def _link(no, points, from_lane=None, to_lane=None):
    poly = "".join(f'<linkPolyPoint x="{x}" y="{y}" zOffset="0" />' for x, y in points)
    ends = ""
    if from_lane and to_lane:
        ends = f'<fromLinkEndPt lane="{from_lane}" pos="0" /><toLinkEndPt lane="{to_lane}" pos="0" />'
    return f'<link no="{no}" name=""><lanes><lane /></lanes>{ends}{poly}</link>'


def _vehicle_input(no, link, name, volumes):
    vols = "".join(
        f'<timeIntervalVehVolume timeInt="1 {start}" vehComp="1" volume="{volume}" />'
        for start, volume in volumes
    )
    return (
        f'<vehicleInput link="{link}" name="{name}" no="{no}">'
        f"<timeIntVehVols>{vols}</timeIntVehVols></vehicleInput>"
    )


class SyntheticFixture:
    """작은 망 하나로 분류 분기를 전부 밟는다.

    SC1 중심 (0,0).  정지선 링크 10(북 접근) / 20(서 접근) / 50(북동 접근).
    SC2 중심 (1000,0) 은 모델 config 에 없다.
    """

    def __init__(self, root: Path):
        self.root = root
        links = [
            _link(10, [(0, 200), (0, 10)]),                      # 남행 -> 접근 leg N
            _link(20, [(-200, 0), (-10, 0)]),                    # 동행 -> 접근 leg W
            _link(30, [(1000, -200), (1000, -10)]),              # 북행 -> 접근 leg S
            _link(40, [(0, 400), (0, 205)]),                     # 링크 10 의 상류 급전
            _link(50, [(200, 200), (10, 10)]),                   # 남서행 -> 접근 leg NE
            _link(41, [(0, 205), (0, 200)], "40 1", "10 1"),     # 커넥터 40 -> 10
        ]
        groups_sc1 = (
            '<signalGroup name="SBT" no="1" />'
            '<signalGroup name="EBT" no="2" />'
            '<signalGroup name="NEB" no="3" />'
        )
        heads = (
            '<signalHead lane="10 1" no="901" pos="185" sg="1 1" />'
            '<signalHead lane="20 1" no="902" pos="185" sg="1 2" />'
            '<signalHead lane="50 1" no="903" pos="260" sg="1 3" />'
            '<signalHead lane="30 1" no="904" pos="185" sg="2 1" />'
        )
        controllers = (
            f'<signalController active="true" name="A" no="1" type="FIXEDTIME">'
            f"<signalGroups>{groups_sc1}</signalGroups></signalController>"
            f'<signalController active="true" name="B" no="2" type="FIXEDTIME">'
            f'<signalGroups><signalGroup name="NBT" no="1" /></signalGroups></signalController>'
        )
        inputs = "".join(
            [
                _vehicle_input(100, 40, "feeder_SB", [(0, 100.0), (900000, 200.0)]),
                _vehicle_input(101, 20, "west_EB", [(0, 50.0), (900000, 60.0)]),
                _vehicle_input(102, 30, "other_NB", [(0, 10.0), (900000, 20.0)]),
                _vehicle_input(103, 20, "Dummy Link 1", [(0, 5.0), (900000, 7.0)]),
                _vehicle_input(104, 50, "", [(0, 30.0), (900000, 40.0)]),
            ]
        )
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<network vissimVersion="2020.00"><netPara northDir="0" />'
            f'<links>{"".join(links)}</links>'
            f"<signalHeads>{heads}</signalHeads>"
            f"<signalControllers>{controllers}</signalControllers>"
            f"<vehicleInputs>{inputs}</vehicleInputs></network>"
        )
        self.network = root / "net.inpx"
        self.network.write_text(xml, encoding="utf-8")

        self.sc_roles = root / "sc_roles.csv"
        self.sc_roles.write_text(
            "no,active,unique_head_links,centroid_xy\n"
            '1,true,"10,20,50","[0.0, 0.0]"\n'
            '2,true,"30","[1000.0, 0.0]"\n',
            encoding="utf-8",
        )

        self.vehicle_inputs = root / "vi_roles.csv"
        self.vehicle_inputs.write_text(
            "no,role,link,first_volume_vph,peak_volume_vph,time_interval_count,name\n"
            "100,urban_input,40,100.0,200.0,2,feeder_SB\n"
            "101,urban_input,20,50.0,60.0,2,west_EB\n"
            "102,urban_input,30,10.0,20.0,2,other_NB\n"
            "103,urban_input,20,5.0,7.0,2,Dummy Link 1\n"
            "104,urban_input,50,30.0,40.0,2,\n",
            encoding="utf-8",
        )

        self.assignment = root / "assignment.json"
        self.assignment.write_text(
            json.dumps(
                {
                    "link_owner": {"10": 1, "20": 1, "40": 1, "50": 1, "30": 2},
                    "link_leg": {"10": "N", "20": "W", "40": "N", "50": "NE", "30": "S"},
                    "link_stop_line": {"10": "10", "20": "20", "40": "10", "50": "50", "30": "30"},
                    "freeway_bound_links": {},
                    "monitor_only_exit_links": [],
                }
            ),
            encoding="utf-8",
        )

        self.config = root / "config.json"
        self.config.write_text(
            json.dumps(
                {
                    "config_overrides": {
                        "network": {
                            "grid_node_legs": {
                                "SC1": {
                                    "W_SC2": {"type": "grid", "node": "SC2"},
                                    "N": {
                                        "type": "boundary",
                                        "in": "in_SC1_N",
                                        "out": "out_SC1_N",
                                        "out_link": "SC1_N_out",
                                    },
                                    "S": {
                                        "type": "boundary",
                                        "in": "in_SC1_S",
                                        "out": "out_SC1_S",
                                        "out_link": "SC1_S_out",
                                    },
                                    "E": {
                                        "type": "boundary",
                                        "in": "in_SC1_E",
                                        "out": "out_SC1_E",
                                        "out_link": "SC1_E_out",
                                    },
                                }
                            },
                            "boundary_in_links": ["in_SC1_N", "in_SC1_S", "in_SC1_E"],
                            "boundary_out_links": ["out_SC1_N", "out_SC1_S", "out_SC1_E"],
                        }
                    }
                }
            ),
            encoding="utf-8",
        )

    def derive(self):
        return derive(
            network_path=self.network,
            vehicle_input_roles_path=self.vehicle_inputs,
            sc_roles_path=self.sc_roles,
            assignment_path=self.assignment,
            config_path=self.config,
        )


class SyntheticSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tempfile

        cls._tmp = tempfile.TemporaryDirectory()
        cls.fixture = SyntheticFixture(Path(cls._tmp.name))
        cls.artifact = cls.fixture.derive()

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def entry(self, no):
        matches = [row for row in self.artifact["vehicle_inputs"] if row["vehicle_input_no"] == no]
        self.assertEqual(len(matches), 1, f"vehicle input {no} not unique")
        return matches[0]

    def test_top_level_schema(self):
        for key in ("schema_version", "generator", "sources", "bearing_convention",
                    "vehicle_inputs", "summary"):
            self.assertIn(key, self.artifact)
        self.assertEqual(self.artifact["schema_version"], 1)

    def test_sources_are_hashed(self):
        for key in ("network", "vehicle_input_roles", "sc_roles", "assignment", "config"):
            self.assertIn(key, self.artifact["sources"])
            self.assertEqual(len(self.artifact["sources"][key]["sha256"]), 64)

    def test_entry_row_schema(self):
        row = self.entry("100")
        for key in ("vehicle_input_no", "link", "name", "role", "entry_class", "volumes_vph",
                    "time_intervals_sec", "downstream_sc", "downstream_hops", "stop_line_link",
                    "leg", "model_node", "model_node_present", "model_node_boundary_gates",
                    "alignment"):
            self.assertIn(key, row)
        for key in ("link_geometry", "link_last_segment", "centroid_to_link_start", "assignment"):
            self.assertIn(key, row["leg"])
        for key in ("link_geometry", "assignment"):
            self.assertIn(key, row["alignment"])
            self.assertIn("status", row["alignment"][key])
            self.assertIn("reason", row["alignment"][key])
            self.assertIn("gate", row["alignment"][key])

    def test_time_interval_volumes_come_from_inpx(self):
        row = self.entry("100")
        self.assertEqual(row["time_intervals_sec"], [0.0, 900.0])
        self.assertEqual(row["volumes_vph"], [100.0, 200.0])

    def test_aligned_entry_names_the_model_gate(self):
        row = self.entry("100")
        self.assertEqual(row["downstream_sc"], "1")
        self.assertEqual(row["downstream_hops"], 2)
        self.assertEqual(row["stop_line_link"], "10")
        self.assertEqual(row["leg"]["link_geometry"], "N")
        self.assertEqual(row["alignment"]["link_geometry"]["status"], "aligned")
        self.assertEqual(row["alignment"]["link_geometry"]["gate"], "in_SC1_N")

    def test_leg_taken_by_grid_neighbour_is_unaligned(self):
        row = self.entry("101")
        self.assertEqual(row["leg"]["link_geometry"], "W")
        self.assertEqual(row["alignment"]["link_geometry"]["status"], "unaligned")
        self.assertEqual(
            row["alignment"]["link_geometry"]["reason"], "leg_occupied_by_grid_neighbour"
        )
        self.assertIsNone(row["alignment"]["link_geometry"]["gate"])

    def test_node_outside_model_is_unaligned(self):
        row = self.entry("102")
        self.assertEqual(row["model_node"], "SC2")
        self.assertFalse(row["model_node_present"])
        self.assertEqual(
            row["alignment"]["link_geometry"]["reason"], "node_absent_from_model"
        )

    def test_diagonal_leg_without_gate_is_unaligned(self):
        row = self.entry("104")
        self.assertEqual(row["entry_class"], "unnamed")
        self.assertEqual(row["leg"]["link_geometry"], "NE")
        self.assertEqual(row["alignment"]["link_geometry"]["reason"], "leg_absent_at_node")

    def test_dummy_entry_class(self):
        self.assertEqual(self.entry("103")["entry_class"], "dummy")
        self.assertEqual(self.entry("100")["entry_class"], "named")

    def test_summary_counts(self):
        summary = self.artifact["summary"]
        self.assertEqual(summary["vehicle_input_count"], 5)
        self.assertEqual(summary["by_entry_class"], {"named": 3, "unnamed": 1, "dummy": 1})
        self.assertEqual(summary["join"], {"resolved": 5, "unresolved": 0})
        urban = summary["urban_entry_points"]
        self.assertEqual(urban["count"], 4)
        self.assertEqual(urban["by_estimator"]["link_geometry"]["aligned"], 1)
        self.assertEqual(urban["by_estimator"]["assignment"]["aligned"], 1)

    def test_unmatched_model_gates_are_counted(self):
        gates = self.artifact["summary"]["model_gates"]
        self.assertEqual(gates["boundary_in_declared"], 3)
        self.assertEqual(gates["gates_with_matched_input_link_geometry"], 1)
        self.assertEqual(gates["gates_without_matched_input_link_geometry"], 2)

    def test_bearing_convention_block_records_the_frame(self):
        block = self.artifact["bearing_convention"]
        self.assertEqual(block["north_dir_attribute"], "0")
        self.assertEqual(block["leg_orientation"], "outward_from_intersection_centre")
        self.assertTrue(block["estimator_scoreboard"])
        for row in block["estimator_scoreboard"]:
            for key in ("estimator", "n", "median_abs_error_deg", "gross_error_gt_45deg"):
                self.assertIn(key, row)

    def test_assignment_leg_is_reproduced_from_geometry(self):
        block = self.artifact["bearing_convention"]["assignment_leg_reproduction"]
        self.assertEqual(block["n"], block["match"])


class RealNetworkSealTests(unittest.TestCase):
    """실 망 수치를 봉인한다. 값은 관측 후 고정한 회귀 핀이다."""

    @classmethod
    def setUpClass(cls):
        required = (REAL_INPX, REAL_VI, REAL_SC, REAL_ASSIGN, REAL_CONFIG)
        if not all(path.is_file() for path in required):
            raise unittest.SkipTest("real network inputs unavailable")
        cls.artifact = derive(
            network_path=REAL_INPX,
            vehicle_input_roles_path=REAL_VI,
            sc_roles_path=REAL_SC,
            assignment_path=REAL_ASSIGN,
            config_path=REAL_CONFIG,
        )

    def test_every_vehicle_input_joins_to_a_downstream_controller(self):
        self.assertEqual(self.artifact["summary"]["vehicle_input_count"], 34)
        self.assertEqual(self.artifact["summary"]["join"], {"resolved": 34, "unresolved": 0})

    def test_entry_classes(self):
        self.assertEqual(
            self.artifact["summary"]["by_entry_class"],
            {"named": 14, "unnamed": 8, "dummy": 10, "freeway": 2},
        )

    def test_urban_entry_points_are_the_named_plus_unnamed(self):
        urban = self.artifact["summary"]["urban_entry_points"]
        self.assertEqual(urban["count"], 22)

    def test_alignment_verdict_depends_on_the_bearing_estimator(self):
        by = self.artifact["summary"]["urban_entry_points"]["by_estimator"]
        self.assertEqual(by["assignment"]["aligned"], 5)
        self.assertEqual(by["link_geometry"]["aligned"], 11)

    def test_unaligned_reasons_and_leg_shape(self):
        by = self.artifact["summary"]["urban_entry_points"]["by_estimator"]
        self.assertEqual(by["link_geometry"]["unaligned"], 11)
        self.assertEqual(by["link_geometry"]["cardinal_leg"], 11)
        self.assertEqual(by["link_geometry"]["diagonal_leg"], 11)
        self.assertEqual(
            by["link_geometry"]["unaligned_reasons"],
            {"leg_absent_at_node": 10, "leg_occupied_by_grid_neighbour": 1},
        )
        # `link_leg` 추정기로는 대각선이 16개, 방위 미정 1개(freeway_bound 링크 69)다.
        self.assertEqual(by["assignment"]["unaligned"], 17)
        self.assertEqual(by["assignment"]["cardinal_leg"], 5)
        self.assertEqual(by["assignment"]["diagonal_leg"], 16)
        self.assertEqual(by["assignment"]["undetermined_leg"], 1)

    def test_aligned_volume_share(self):
        by = self.artifact["summary"]["urban_entry_points"]["by_estimator"]
        self.assertAlmostEqual(
            by["link_geometry"]["aligned_volume"]["peak_volume_vph"], 8104.88, places=2
        )
        self.assertAlmostEqual(
            by["link_geometry"]["unaligned_volume"]["peak_volume_vph"], 8789.48, places=2
        )
        self.assertAlmostEqual(
            by["assignment"]["aligned_volume"]["peak_volume_vph"], 4031.72, places=2
        )

    def test_most_model_gates_have_no_vissim_input_behind_them(self):
        gates = self.artifact["summary"]["model_gates"]
        self.assertEqual(gates["gates_with_matched_input_link_geometry"], 11)
        self.assertEqual(gates["gates_without_matched_input_link_geometry"], 106)
        self.assertEqual(gates["gates_with_matched_input_assignment"], 5)
        self.assertEqual(gates["gates_without_matched_input_assignment"], 112)

    def test_dummy_inputs_are_reported_separately(self):
        dummy = self.artifact["summary"]["dummy_inputs"]
        self.assertEqual(dummy["count"], 10)
        self.assertAlmostEqual(dummy["peak_volume_vph"], 2226.0, places=3)
        self.assertAlmostEqual(dummy["first_volume_vph"], 1484.0, places=3)

    def test_urban_entry_point_volumes_split_named_and_unnamed(self):
        urban = self.artifact["summary"]["urban_entry_points"]
        self.assertAlmostEqual(urban["peak_volume_vph"], 16894.36, places=2)
        self.assertAlmostEqual(urban["by_entry_class"]["named"]["peak_volume_vph"], 10361.40, places=2)
        self.assertAlmostEqual(urban["by_entry_class"]["unnamed"]["peak_volume_vph"], 6532.96, places=2)

    def test_model_gate_supply_is_far_larger_than_the_input_count(self):
        gates = self.artifact["summary"]["model_gates"]
        self.assertEqual(gates["node_count"], 41)
        self.assertEqual(gates["boundary_leg_count"], 119)
        self.assertEqual(gates["boundary_in_declared"], 117)

    def test_assignment_leg_is_reproduced_on_the_real_network(self):
        block = self.artifact["bearing_convention"]["assignment_leg_reproduction"]
        self.assertGreater(block["n"], 900)
        self.assertEqual(block["n"], block["match"])

    def test_link_leg_estimator_is_the_worst_scoring_one(self):
        board = {row["estimator"]: row for row in
                 self.artifact["bearing_convention"]["estimator_scoreboard"]}
        self.assertEqual(board["centroid_to_link_start"]["n"], 170)
        self.assertEqual(board["centroid_to_link_start"]["gross_error_gt_45deg"], 38)
        self.assertEqual(board["link_last_segment_reversed"]["gross_error_gt_45deg"], 13)
        self.assertEqual(board["link_chord_reversed"]["gross_error_gt_45deg"], 11)


if __name__ == "__main__":
    unittest.main()
