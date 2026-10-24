from pathlib import Path
import json,unittest
from diagnostics.probe_joint_offratio_sensitivity import ROOT,native_joint


class JointPriorTests(unittest.TestCase):
    def test_pinned_native_joint_is_coherent_and_counts_destination_connector(self):
        rows=native_joint()
        expected={'OR_F_E':(1.6,4.,8.),'OR_D_E':(4.,3.,8.),'OR_D_W':(3.,3.,10.),'OR_F_W':(1.,3.,8.)}
        for off,(signal,direct,through) in expected.items():
            row=rows[off];total=signal+direct+through
            self.assertAlmostEqual(row['total_off']*(1-row['direct_given_off']),signal/total)
            self.assertAlmostEqual(row['total_off']*row['direct_given_off'],direct/total)
        fe=next(r for r in rows['OR_F_E']['routes'] if r['branch']=='signal')
        self.assertEqual(fe['path'][-1],'10643')
        fw=next(r for r in rows['OR_F_W']['routes'] if r['branch']=='signal')
        self.assertEqual(fw['raw_relflow'],'');self.assertEqual(fw['weight'],1.)

    def test_recorded_endpoints_have_exact_landing_and_horizon_prefix_closure(self):
        report=json.loads((ROOT/'diagnostics/joint_offratio_sensitivity.json').read_text(encoding='utf-8'))
        trace=json.loads((ROOT/'diagnostics/joint_offratio_sensitivity_trace.json').read_text(encoding='utf-8'))
        self.assertTrue(report['inputs_unchanged']);self.assertEqual(report['source_changes'],[])
        self.assertEqual(len(report['results']),6)
        for r in report['results']:
            self.assertTrue(r['stock_closure_valid']);self.assertTrue(r['held_control_equal_every_substep'])
            self.assertAlmostEqual(r['controlled_freeway_cell_ttt_veh_h']+r['area_non_freeway_cell_ttt_veh_h'],r['area']['ttt_veh_h'])
            for flow in r['off_flows'].values():
                self.assertAlmostEqual(flow['requested_veh'],flow['accepted_veh']+flow['blocked_veh'])
                self.assertAlmostEqual(flow['accepted_veh'],flow['accepted_signal_veh']+flow['accepted_direct_veh'])
            key=r['name']+'_'+str(r['horizon_sec'])
            if r['horizon_sec']==450:self.assertEqual(trace[key][:15],trace[r['name']+'_150'])


if __name__=='__main__':unittest.main()
