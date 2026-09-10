"""Small native-warning classification and bounded-frame regressions."""
from pathlib import Path
import tempfile
import unittest
from diagnostics.capture_native_runtime_errors import parse_bytes, check_removals, interval_check_candidates, dll_program_messages


def removal(vehicle=590, suffix="", wait=45):
    return (f"Warning\tSimulation second 467.0: After {wait}.0 seconds of waiting for lane change the vehicle {vehicle} "
            f"(on Static Vehicle Route 1159 - 1{suffix}) was removed from link 310 at position 93.3.\r\r\n")


class NativeErrorTests(unittest.TestCase):
    def test_end_input_backlog_is_not_vehicle_deletion(self):
        data=('Warning\tVehicle input 1098: 경부_EB could not be finished completely (remain: 1932 vehicles).\n'
              'Warning\tVehicle input 1105 could not be finished completely (remain: 71 vehicles).\n').encode('cp949')
        parsed=parse_bytes(data)
        self.assertEqual(parsed['counts'],{'unfinished_vehicle_input':2})
        self.assertEqual([(x['input_no'],x['remaining_vehicles']) for x in parsed['events']],[(1098,1932),(1105,71)])
        self.assertTrue(all(not x['explicitly_says_removed'] for x in parsed['events']))

    def test_dll_complete_punctuated_message_can_lack_final_newline(self):
        data=b'SC 9101\nThe signal controller 9101 has no signal program.SC 9102\nThe signal controller 9102 has no signal program.'
        self.assertEqual(dll_program_messages(data),[9101,9102])
        self.assertEqual(dll_program_messages(data[:-1]),[9101])

    def test_start_warning_is_retained_for_next_sample_disappearance(self):
        events=[{"time_sec":t} for t in (898,899,900,1050,1051)]
        self.assertEqual([x["time_sec"] for x in interval_check_candidates(events,900,1050)],
                         [899,900,1050])

    def test_route_names_and_non45_wait_are_not_lost(self):
        data=(removal()+removal(1,": 좌",60)+removal(2,": 우",45)).encode("cp949")
        parsed=parse_bytes(data)
        self.assertEqual(parsed["counts"],{"lane_change_removal":3})
        self.assertEqual([x["wait_sec"] for x in parsed["events"]],[45.,60.,45.])
        self.assertEqual([x["vehicle_id"] for x in parsed["events"]],[590,1,2])
        self.assertEqual(parsed["unparsed_removal_lines"],[])

    def test_partial_tail_never_becomes_an_event(self):
        complete=removal().encode();tail=removal(2).encode()[:-2]
        parsed=parse_bytes(complete+tail)
        self.assertEqual(len(parsed["events"]),1)
        self.assertEqual(parsed["complete_line_prefix_bytes"],len(complete))
        self.assertEqual(parsed["partial_tail_bytes"],len(tail))

    def test_route_end_warning_is_not_asserted_to_be_removal(self):
        line=("Warning\tSimulation second 1974.0: Vehicle 10371 (on Static Vehicle Route 1130 - 3) "
              "arrived at the end of link 2 without having found the next link (10682) of its route.\r\r\n")
        parsed=parse_bytes(line.encode())
        self.assertEqual(parsed["counts"],{"route_next_link_not_found":1})
        self.assertFalse(parsed["events"][0]["explicitly_says_removed"])

    def test_other_warning_categories_are_separate(self):
        lines=("Warning\tSimulation second 1.0: Vehicle 2 ignores the static routing decision 3 because it has left link 4 at position 5.0 in the same time step.\n"
               "Warning\tSimulation second 2.0: Vehicle 3 ignores the desired speed decision 4 because it has left link 5 at position 6.0 in the same time step.\n"
               "Warning\tSimulation second 3.0: vehicle 2 already passed start of travel time section 8 at simulation second 0.5\n")
        self.assertEqual(parse_bytes(lines.encode())["counts"],
            {"ignored_static_routing":1,"ignored_desired_speed":1,"duplicate_travel_time_section_start":1})

    def test_local_disappearance_only_does_not_blacklist_prior_crossing(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"test.fzp"
            path.write_bytes(b"$VEHICLE:SIMSEC;NO;LANE\\LINK\\NO;LANE\\INDEX;POS;SPEED\n"
                b"1;7;10;1;5;0\n1;99;9;1;1;20\n"
                b"2;7;10;1;5;0\n2;99;9;1;2;20\n"
                b"3;99;9;1;3;20\n4;99;9;1;4;20\n")
            event={"time_sec":2.,"vehicle_id":7,"link":"10","position_m":5.}
            result=check_removals(path,[event],{"10"},{"24","120"},max_bytes=4096)
            row=result["checks"][0]
            self.assertEqual(row["disappearances"][0]["upper_sec"],3)
            self.assertTrue(row["last_link_inside"])
            self.assertFalse(row["last_link_is_terminal"])
            self.assertLess(result["bytes_read"],4096)
            self.assertNotIn("excluded_vehicle_ids",result)
            self.assertNotIn("ttd",result)


if __name__=="__main__":unittest.main()
