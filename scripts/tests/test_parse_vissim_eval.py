# VISSIM eval 산출물(.rsr / .att) 파서의 동작을 고정하는 테스트

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import parse_vissim_eval as parser


# 실 산출물 .att 헤더에 들어 있는 한글 경로. CP949 로 인코딩하면 UTF-8 로는 못 읽는다.
KOREAN_INPX_PATH = (
    r"C:\Users\alsrj\Desktop\학술\찐찐막\Claude\VISSIM"
    r"\network\real_world_gaepo_modi\modi_eval_rw_control.inpx"
)

# 실 산출물 .rsr 헤더는 VISSIM 이 한글을 물음표로 이미 뭉갠 상태로 적는다.
MANGLED_INPX_PATH = (
    r"C:\Users\alsrj\Desktop\??\???\Claude\VISSIM"
    r"\network\real_world_gaepo_modi\modi_eval_rw_control.inpx"
)

# 실 산출물 modi_eval_rw_control_001.rsr 앞부분.
RSR_FIXTURE = "\r\n".join(
    [
        "",
        "Table of Travel Times",
        "",
        f"File:     {MANGLED_INPX_PATH}",
        "Comment:  ",
        "Date:     2026-08-09 6:00:19",
        "PTV Vissim 2020.00-14 (64 bit) [95957]",
        "",
        "  Time;   No.;   Veh;VehType; Trav.;Delay.;  Dist;",
        "1800.9;   724;  9575;   100;  44.1;   3.0; 486.9;",
        "1800.8;   816;  9302;   150;  11.5;   0.5; 127.7;",
        "1800.9;  1204;  9575;   100;  30.4;   0.0; 360.1;",
        "1800.6;  1908;  7515;   100;  35.1;  23.9; 209.3;",
        "1800.1;  2002; 10118;   100;  59.6;   6.2;1900.5;",
        "",
    ]
)

# 로케일이 다른 장비에서는 .rsr 헤더에도 CP949 한글이 그대로 남을 수 있다.
RSR_FIXTURE_KOREAN_HEADER = RSR_FIXTURE.replace(MANGLED_INPX_PATH, KOREAN_INPX_PATH)

# 실 산출물 modi_eval_rw_control_Queue Results_001.att 앞부분.
QUEUE_ATT_FIXTURE = "\r\n".join(
    [
        "$VISION",
        f"* File:\t\t{KOREAN_INPX_PATH}",
        "* Comment:\t",
        "* Date:\t\t2026-08-09 6:06:26",
        "* PTV Vissim:\t2020.00 [14]",
        "* ",
        "* Table: Queue Results",
        "* ",
        "* SIMRUN: SimRun, Simulation run (Number of simulation run)",
        "* QLEN: QLen, Queue length (Average queue length) [m]",
        "*",
        "$QUEUECOUNTEREVALUATION:SIMRUN;TIMEINT;QUEUECOUNTER;QLEN;QLENMAX;QSTOPS",
        "1;600-760;1;16.18;48.77;11",
        "1;600-760;2;5.26;19.09;4",
        "1;600-760;31;0.00;0.00;0",
        "1;3480-3601;200242;0.00;0.00;0",
        "",
    ]
)

# 실 산출물 modi_eval_rw_control_Vehicle Travel Time Results_001.att 앞부분.
# 측정 101/102 는 값이 있고, 107 은 통과 차량이 0 대라 TravTm/DistTrav 셀이 비어 있다.
TRAVEL_TIME_ATT_FIXTURE = "\r\n".join(
    [
        "$VISION",
        f"* File:\t\t{KOREAN_INPX_PATH}",
        "* Comment:\t",
        "* Date:\t\t2026-08-09 6:06:26",
        "* PTV Vissim:\t2020.00 [14]",
        "* ",
        "* Table: Vehicle Travel Time Results",
        "*",
        "$VEHICLETRAVELTIMEMEASUREMENTEVALUATION:SIMRUN;TIMEINT;"
        "VEHICLETRAVELTIMEMEASUREMENT;VEHS(ALL);TRAVTM(ALL);DISTTRAV(ALL)",
        "1;600-760;101;3;72.39;555.31",
        "1;600-760;102;8;125.29;878.83",
        "1;600-760;107;0;;",
        "1;3480-3601;900317;6;169.80;1006.41",
        "",
    ]
)


class ParseVissimEvalTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

    def write(self, name: str, text: str, encoding: str = "cp949") -> Path:
        path = self.directory / name
        path.write_bytes(text.encode(encoding))
        return path

    # -- .rsr ---------------------------------------------------------------

    def test_parse_rsr_reads_vehicle_records(self) -> None:
        path = self.write("run_001.rsr", RSR_FIXTURE)

        records = parser.parse_rsr(path)

        self.assertEqual(len(records), 5)
        first = records[0]
        self.assertEqual(
            tuple(first), (1800.9, 724, 9575, 100, 44.1, 3.0, 486.9)
        )
        self.assertEqual(first.time_sec, 1800.9)
        self.assertEqual(first.measurement_no, 724)
        self.assertEqual(first.veh_no, 9575)
        self.assertEqual(first.veh_type, 100)
        self.assertEqual(first.trav_sec, 44.1)
        self.assertEqual(first.delay_sec, 3.0)
        self.assertEqual(first.dist_m, 486.9)
        self.assertIsInstance(first.measurement_no, int)
        self.assertIsInstance(first.veh_type, int)
        self.assertIsInstance(first.time_sec, float)
        # 마지막 행까지 읽고, 붙은 세미콜론 때문에 빈 열이 생기지 않아야 한다.
        self.assertEqual(
            tuple(records[-1]), (1800.1, 2002, 10118, 100, 59.6, 6.2, 1900.5)
        )

    def test_parse_rsr_survives_cp949_header_that_breaks_utf8(self) -> None:
        path = self.write(
            "run_cp949_001.rsr", RSR_FIXTURE_KOREAN_HEADER, encoding="cp949"
        )

        # 픽스처가 실제로 UTF-8 함정을 담고 있는지 먼저 증명한다.
        with self.assertRaises(UnicodeDecodeError):
            path.read_text(encoding="utf-8")

        records = parser.parse_rsr(path)

        self.assertEqual(len(records), 5)
        self.assertEqual(records[0].measurement_no, 724)

    def test_parse_rsr_rejects_file_without_column_header(self) -> None:
        path = self.write("broken.rsr", "Table of Travel Times\r\n\r\n")

        with self.assertRaises(ValueError):
            parser.parse_rsr(path)

    # -- Queue Results .att -------------------------------------------------

    def test_parse_queue_att_reads_records(self) -> None:
        path = self.write("Queue Results_001.att", QUEUE_ATT_FIXTURE)

        records = parser.parse_queue_att(path)

        self.assertEqual(len(records), 4)
        first = records[0]
        self.assertEqual(tuple(first), (1, "600-760", 1, 16.18, 48.77, 11))
        self.assertEqual(first.simrun, 1)
        self.assertEqual(first.timeint, "600-760")
        self.assertEqual(first.queue_counter, 1)
        self.assertEqual(first.qlen_m, 16.18)
        self.assertEqual(first.qlenmax_m, 48.77)
        self.assertEqual(first.qstops, 11)
        self.assertIsInstance(first.qstops, int)
        self.assertEqual(records[-1].timeint, "3480-3601")
        self.assertEqual(records[-1].queue_counter, 200242)

    def test_parse_queue_att_survives_cp949_header_that_breaks_utf8(self) -> None:
        path = self.write(
            "Queue Results_cp949.att", QUEUE_ATT_FIXTURE, encoding="cp949"
        )

        with self.assertRaises(UnicodeDecodeError):
            path.read_text(encoding="utf-8")

        records = parser.parse_queue_att(path)

        self.assertEqual(len(records), 4)
        self.assertEqual(records[0].qlen_m, 16.18)

    def test_parse_queue_att_rejects_missing_required_column(self) -> None:
        text = QUEUE_ATT_FIXTURE.replace(";QLENMAX", ";QLENMAXIMUM")
        path = self.write("Queue Results_bad.att", text)

        with self.assertRaises(ValueError):
            parser.parse_queue_att(path)

    # -- Vehicle Travel Time Results .att -----------------------------------

    def test_parse_travel_time_att_reads_records(self) -> None:
        path = self.write("Travel Time_001.att", TRAVEL_TIME_ATT_FIXTURE)

        records = parser.parse_travel_time_att(path)

        self.assertEqual(len(records), 4)
        first = records[0]
        self.assertEqual(tuple(first), (1, "600-760", 101, 3, 72.39, 555.31))
        self.assertEqual(first.simrun, 1)
        self.assertEqual(first.timeint, "600-760")
        self.assertEqual(first.measurement, 101)
        self.assertEqual(first.vehs, 3)
        self.assertEqual(first.travtm_s, 72.39)
        self.assertEqual(first.dist_m, 555.31)
        self.assertIsInstance(first.vehs, int)

    def test_parse_travel_time_att_maps_empty_cells_to_none(self) -> None:
        path = self.write("Travel Time_001.att", TRAVEL_TIME_ATT_FIXTURE)

        records = parser.parse_travel_time_att(path)
        empty = [r for r in records if r.measurement == 107][0]

        self.assertEqual(empty.vehs, 0)
        self.assertIsNone(empty.travtm_s)
        self.assertIsNone(empty.dist_m)

    def test_parse_travel_time_att_binds_columns_by_name_not_position(self) -> None:
        text = TRAVEL_TIME_ATT_FIXTURE.replace(
            "VEHS(ALL);TRAVTM(ALL);DISTTRAV(ALL)",
            "VEHS(ALL);DISTTRAV(ALL);TRAVTM(ALL)",
        ).replace("101;3;72.39;555.31", "101;3;555.31;72.39")
        path = self.write("Travel Time_swapped.att", text)

        records = parser.parse_travel_time_att(path)

        self.assertEqual(records[0].travtm_s, 72.39)
        self.assertEqual(records[0].dist_m, 555.31)


if __name__ == "__main__":
    unittest.main()
