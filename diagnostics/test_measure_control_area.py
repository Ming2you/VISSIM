"""Physical accounting regression tests with independent small trajectories."""
from pathlib import Path
import json
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.measure_control_area import Frame, Vehicle, measure_frames, read_fzp_frames, state_frame
from evaluation.controllers.control_area_objective import MembershipError


def v(link,pos=0,speed=36):
    return Vehicle(link,pos,speed)


class AreaMeasurementTests(unittest.TestCase):
    def setUp(self):
        self.membership={'1':True,'2':True,'3':True,'4':False,'24':True}

    def measure(self,frames,end=6,**kw):
        return measure_frames(frames,self.membership,{'24':1000.0},end_sec=end,**kw)

    def test_internal_transfer_has_residence_but_no_exit(self):
        metrics,_=self.measure([Frame(1,{'10':v('1'),'20':v('4')}),Frame(6,{'10':v('2'),'20':v('4')})])
        self.assertAlmostEqual(metrics['ttt_veh_h'],5.5/3600)
        self.assertEqual(metrics['ttd_observed_plus_terminal_events'],0)
        self.assertEqual(metrics['appeared_inside_events'],1)
        self.assertEqual(metrics['closure']['max_abs_residual_veh'],0)

    def test_exit_reentry_exit_counts_events_and_unique_ids_separately(self):
        fs=[Frame(t,{'10':v(link)})for t,link in [(1,'1'),(2,'4'),(3,'2'),(4,'4')]]
        metrics,_=self.measure(fs,end=4)
        self.assertEqual(metrics['ttd_observed_exit_events'],2)
        self.assertEqual(metrics['ttd_counted_unique_vehicle_ids'],1)
        self.assertEqual(metrics['ttd_repeat_exit_events'],1)
        self.assertEqual(metrics['observed_entry_events'],1)

    def test_terminal_missing_requires_near_endpoint(self):
        fs=[Frame(1,{'10':v('24',980),'11':v('24',100),'12':v('1',980)}),Frame(6,{})]
        metrics,_=self.measure(fs)
        self.assertEqual(metrics['ttd_terminal_exit_inferred_events'],1)
        self.assertEqual(metrics['ttd_observed_exit_events'],0)
        self.assertEqual(metrics['unresolved_inside_disappearances'],2)
        self.assertEqual(metrics['unresolved_inside_disappearances_by_link'],{'24':1,'1':1})
        self.assertEqual(metrics['closure']['max_abs_residual_veh'],0)

    def test_ending_file_does_not_remove_last_vehicles(self):
        metrics,rows=self.measure([Frame(1,{'10':v('24',999)}),Frame(6,{'10':v('24',999)})],end=10)
        self.assertEqual(metrics['ttd_observed_plus_terminal_events'],0)
        self.assertEqual(metrics['censored_last_observed_inside_vehicles'],1)
        self.assertEqual(metrics['boundaries']['unobserved_tail_sec'],4)
        self.assertAlmostEqual(metrics['ttt_censored_tail_extrapolation_veh_h'],4/3600)
        self.assertEqual(rows[-1]['source'],'censored_hold_extrapolation')

    def test_terminal_record_can_overshoot_end_by_one_simulation_step(self):
        # Real NC vehicle 121 had Pos-L=36.799 m at 154.9 km/h before
        # disappearing. Also retain a far-upstream stopped disappearance and
        # an impossible 200 m overshoot as unresolved, even with 5 s sampling.
        fs=[Frame(1,{'10':v('24',1036.799,154.9),
                     '11':v('24',1200,154.9),'12':v('24',100,0)}),Frame(6,{})]
        metrics,_=self.measure(fs)
        self.assertEqual(metrics['ttd_terminal_exit_inferred_events'],1)
        self.assertEqual(metrics['ttd_terminal_overshoot_inferred_events'],1)
        self.assertEqual(metrics['unresolved_inside_disappearances'],2)
        self.assertEqual(metrics['closure']['max_abs_residual_veh'],0)
        fine,_=self.measure(fs,simulation_step_sec=.1)
        self.assertEqual(fine['ttd_terminal_exit_inferred_events'],0)

    def test_complete_final_frame_resolves_endpoint_interval(self):
        metrics,_=self.measure([Frame(1,{'10':v('1')}),Frame(6,{'10':v('1')})],end=10,
                               final_frame=Frame(10,{'10':v('4')},'final_state'))
        self.assertEqual(metrics['ttd_observed_exit_events'],1)
        self.assertEqual(metrics['boundaries']['unobserved_tail_sec'],0)
        self.assertTrue(metrics['boundaries']['final_state_used'])

    def test_long_unobserved_tail_has_no_full_run_ttt(self):
        metrics,_=self.measure([Frame(1,{'10':v('1')}),Frame(6,{'10':v('1')})],end=5400)
        self.assertIsNone(metrics['ttt_veh_h'])
        self.assertIsNone(metrics['ttt_censored_tail_extrapolation_veh_h'])
        self.assertEqual(metrics['ttd_observed_plus_terminal_events'],0)

    def test_unresolved_disappearance_and_reappearance_are_visible(self):
        fs=[Frame(1,{'10':v('1')}),Frame(2,{}),Frame(3,{'10':v('1')})]
        metrics,_=self.measure(fs,end=3)
        self.assertEqual(metrics['unresolved_inside_disappearances'],1)
        self.assertEqual(metrics['reappeared_inside_events'],1)
        self.assertEqual(metrics['ttd_observed_plus_terminal_events'],0)

    def test_terminal_inference_is_rejected_if_vehicle_reappears_inside_or_outside(self):
        for target in ('1','4'):
            fs=[Frame(1,{'10':v('24',999)}),Frame(2,{}),Frame(3,{'10':v(target)})]
            with self.subTest(target=target), self.assertRaisesRegex(ValueError,'contradicted'):
                self.measure(fs,end=3)

    def test_unknown_membership_and_timestamp_reordering_fail(self):
        with self.assertRaises(MembershipError):
            self.measure([Frame(1,{'1':v('999')})])
        with self.assertRaises(ValueError):
            self.measure([Frame(2,{}),Frame(1,{})])

    def test_invalid_inference_and_extrapolation_parameters_fail(self):
        for name in ('max_tail_extrap_sec','terminal_margin_m','terminal_acceleration_m_s2','simulation_step_sec'):
            for value in (-1,float('nan'),float('inf')):
                with self.subTest(parameter=name,value=value):
                    with self.assertRaises(ValueError):
                        self.measure([Frame(1,{})],**{name:value})

    def test_final_snapshot_must_be_complete_paused_vehicle_inventory(self):
        raw={'sim_sec':10,'total_vehicles':1,'vehicle_records':{'complete':True,'collection_count_before':1,
             'collection_count_after':1,'record_count':1,'capture_sim_sec_before':10,'capture_sim_sec_after':10,
             'records':[{'veh_no':10,'link_no':1,'position_m':-2.0,'speed_kph':0}]}}
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'final.json'
            p.write_text(json.dumps(raw),encoding='utf-8')
            self.assertEqual(state_frame(p,10).vehicles['10'].link,'1')
            raw['vehicle_records']['collection_count_after']=2
            p.write_text(json.dumps(raw),encoding='utf-8')
            with self.assertRaises(ValueError):
                state_frame(p,10)

    def test_final_snapshot_run_and_manifest_must_match(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'final.json'
            manifest=Path(directory)/'manifest.json'
            raw={'sim_sec':10,'total_vehicles':0,'run_provenance':{'run_id':'expected','manifest_path':str(manifest)},
                 'vehicle_records':{'complete':True,'collection_count_before':0,'collection_count_after':0,
                    'record_count':0,'capture_sim_sec_before':10,'capture_sim_sec_after':10,'records':[]}}
            p.write_text(json.dumps(raw),encoding='utf-8')
            self.assertEqual(state_frame(p,10,expected_run_id='expected',expected_manifest_path=manifest).time_sec,10)
            with self.assertRaisesRegex(ValueError,'different run_id'):
                state_frame(p,10,expected_run_id='wrong')
            with self.assertRaisesRegex(ValueError,'manifest differs'):
                state_frame(p,10,expected_run_id='expected',expected_manifest_path=Path(directory)/'other.json')


class FzpParserTests(unittest.TestCase):
    def parse(self,text):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'sample.fzp'
            path.write_text(text,encoding='utf-8')
            return list(read_fzp_frames(path))

    def test_column_order_and_vehicle_order_are_not_assumed(self):
        rows=self.parse('$VISION\n* comment\n$VEHICLE:SPEED;LANE\\LINK\\NO;NO;SIMSEC;POS;TMINNETTOT\n'
                        '36;1;20;1;2;9999\n36;2;10;1;3;9999\n36;4;20;6;4;9999\n')
        self.assertEqual([x.time_sec for x in rows],[1,6])
        self.assertEqual(set(rows[0].vehicles),{'10','20'})
        self.assertEqual(rows[0].vehicles['10'].link,'2')
        metrics,_=measure_frames(rows,{'1':True,'2':True,'4':False},{},end_sec=6)
        self.assertEqual(metrics['ttd_observed_exit_events'],1)
        self.assertEqual(metrics['unresolved_inside_disappearances'],1)
        self.assertEqual(metrics['ttd_terminal_exit_inferred_events'],0)

    def test_bad_records_fail_instead_of_silent_stock_change(self):
        header='$VEHICLE:SIMSEC;NO;LANE\\LINK\\NO;POS;SPEED\n'
        for text in (header+'1;1;1;0;0\n1;1;1;0;0\n',
                     header+'6;1;1;0;0\n1;1;1;0;0\n',
                     header+'1;1;1;0\n',
                     '$VEHICLE:SIMSEC;NO;POS;SPEED\n1;1;0;0\n'):
            with self.subTest(text=text),self.assertRaises(ValueError):
                self.parse(text)

    def test_vissim_negative_entry_position_is_a_valid_record(self):
        rows=self.parse('$VEHICLE:SIMSEC;NO;LANE\\LINK\\NO;POS;SPEED\n1;1;1;-2.82;0\n')
        self.assertEqual(rows[0].vehicles['1'].position_m,-2.82)


if __name__=='__main__':
    unittest.main()
