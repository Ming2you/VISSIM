"""Assert conservative path/head evidence and known counterexamples."""
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class AuthorityEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/'diagnostics/movement_signal_authority_audit.json').read_text(encoding='utf-8'))
        cls.rows=cls.data['movements']

    def test_complete_actual_scope_and_separate_nonwriter_SCs(self):
        self.assertEqual(len(self.rows),366)
        self.assertEqual(sum(self.data['classification_counts'].values()),366)
        self.assertEqual(sum(self.data['writer_scope_counts'].values()),261)
        self.assertEqual(self.data['model_green_gated_bypass_count'],26)

    def test_10528_leaves_lane_before_any_SC101_head(self):
        row=self.rows['SC101_S_SC1_to_E_SC5'];b=row['branches'][0]
        self.assertEqual(row['classification'],'certainly_bypasses_model_signal')
        self.assertEqual(b['first_connector']['id'],'10528')
        self.assertFalse(b['source_heads_before_branch'])
        self.assertGreater(b['source_heads_after_branch'][0]['pos_m']-b['first_connector']['source_pos'],16)
        self.assertEqual([w['route_id'] for w in b['native_route_witnesses']],['1014:3'])

    def test_10366_source_only_bypass_does_not_hide_upstream_SG6(self):
        row=self.rows['SC11_E_SC12_to_N_SC5'];b=row['branches'][0]
        self.assertEqual(row['classification'],'certainly_head_controlled')
        self.assertFalse(b['source_heads_before_branch'])
        self.assertTrue(b['source_heads_after_branch'])
        heads=b['native_route_witnesses'][0]['heads_before_branch_any_lane']
        self.assertEqual({(h['link'],h['SG']) for h in heads},{('1220012001','6')})

    def test_10426_upstream_native_SG10_is_not_MPC_green_authority(self):
        row=self.rows['SC5_W_SC101_to_S_SC11'];b=row['branches'][0]
        self.assertEqual(row['classification'],'certainly_bypasses_model_signal')
        self.assertNotIn('10',row['writer_actuated_SGs'])
        heads=b['native_route_witnesses'][0]['native_same_SC_heads_not_actuated_by_selected_writer']
        self.assertEqual({h['SG'] for h in heads},{'10'})

    def test_no_resolved_bypass_from_missing_witness_or_partial_heads(self):
        for name in self.data['model_green_gated_bypass_movements']:
            row=self.rows[name]
            self.assertTrue(row['writer_controls_SC'])
            self.assertFalse(row['model_spec'].get('unsignalized'))
            for b in row['branches']:
                self.assertTrue(b['native_route_witnesses'])
                self.assertFalse(b['heads_on_movement_continuation'])
                self.assertTrue(all(not w['heads_before_branch_any_lane'] for w in b['native_route_witnesses']))

    def test_disjoint_phase_case_has_actual_traffic_without_claiming_flow(self):
        r=next(r for r in self.data['phase_mismatch_priority_actual_traffic'] if r['movement']=='SC1_E_to_S_SC107')
        self.assertEqual(r['priority'],'P1_disjoint_phase')
        self.assertEqual(r['expected_SGs'],['1','5'])
        self.assertEqual(r['physical_branches'][0]['source_SGs'],['6'])
        self.assertEqual(r['max_snapshot_connector_veh'],2)


if __name__=='__main__':unittest.main()
