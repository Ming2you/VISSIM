"""Validate saved physical intervention and cost reconciliation, no model run."""
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name):return json.loads((ROOT/'diagnostics'/name).read_text(encoding='utf-8'))

class Evidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.doc=load('source_meter_shutdown_diagnosis.json')
    def test_first_interval_matches_independent_actual_held_replay(self):
        ref=load('source_interval_1200_1350.json')['model'];first=self.doc['paired']['recorded_closed']['endpoints'][0]
        for key in ('ttt_veh_h','ttd_veh','entered_veh'):self.assertAlmostEqual(first['area_metrics'][key],ref['metrics'][key],places=10)
        self.assertEqual(first['stocks']['ramp_queues_veh'],ref['final']['ramp_queues_veh'])
        self.assertFalse(self.doc['source_changes'])
    def test_intervention_only_reopens_two_groups_with_feasible_realized_budget(self):
        old=self.doc['paired']['recorded_closed'];new=self.doc['paired']['reopen_DW_FE_only']
        self.assertEqual(new['N_UF_star_vph'],sum(new['meters_vph'].values()))
        self.assertLessEqual(new['N_UF_star_vph'],self.doc['cfg']['leader']['N_UF_star_range'][1])
        for r in ('R_F_W','R_D_E'):self.assertEqual(old['meters_vph'][r],new['meters_vph'][r])
        for r in ('R_D_W','R_F_E'):self.assertEqual((old['meters_vph'][r],new['meters_vph'][r]),(0.,1800.))
    def test_density_cost_reverses_pure_area_ranking(self):
        old=self.doc['paired']['recorded_closed']['endpoints'][-1];new=self.doc['paired']['reopen_DW_FE_only']['endpoints'][-1]
        self.assertLess(new['area_metrics']['ttt_veh_h'],old['area_metrics']['ttt_veh_h'])
        for beta in (0,60,150,300):
            score=lambda r:r['area_metrics']['ttt_veh_h']-beta/3600*r['area_metrics']['ttd_veh']
            self.assertLess(score(new),score(old))
        a,b=[r['leader_terms_for_held_control'] for r in (old,new)]
        self.assertGreater(b['leader_total_objective'],a['leader_total_objective'])
        self.assertAlmostEqual(b['leader_total_objective']-a['leader_total_objective'],
            b['leader_objective_base']-a['leader_objective_base']+b['leader_density_penalty']-a['leader_density_penalty'],places=10)
    def test_inadmissible_all_four_request_is_not_an_arm(self):
        rejected=self.doc['separate_inadmissible_quantization']
        self.assertFalse(rejected['candidate_admissible'])
        self.assertGreater(rejected['realized_sum_vph'],7200)
        self.assertEqual(set(self.doc['paired']),{'recorded_closed','reopen_DW_FE_only'})
    def test_canonical_csv_changes_exactly_four_closed_meter_rows(self):
        audit=load('source_meter_shutdown_command_audit.json');self.assertFalse(audit['source_changes'])
        self.assertTrue(audit['arms']['recorded_closed']['canonical_writer_comparison_to_actual1200']['physical_columns_exact'])
        change=audit['arms']['reopen_DW_FE_only']['changed_physical_rows']
        self.assertEqual(len(change),4)
        self.assertTrue(all(r['kind']=='ramp_meter' and float(r['green_sec'])==10 for r in change))

if __name__=='__main__':unittest.main()
