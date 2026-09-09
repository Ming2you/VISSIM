"""Historical real readback and independent zero-offset clock fixtures."""
import unittest
from pathlib import Path
from diagnostics.audit_area_live_actuation import ROOT,parse_commands,read_csv_prefix,trace_audit,audit_interval


class LiveActuationAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run=ROOT/'evaluation/runs/codex_area_beta0_s13_20260910'
        cls.rows,_=read_csv_prefix(run/('decisions_'+run.name)/'signal_readback.csv',1050)
        cls.commands900=(run/('decisions_'+run.name)/'action_000900.csv').read_bytes()
        cls.commands1050=(ROOT/'diagnostics/area_production_preflight/wu-link_t1050_beta0_20260909T194949178671Z/action.csv').read_bytes()

    def test_real_900_complete_interval(self):
        _,signals,ramps=parse_commands(self.commands900,900)
        result=trace_audit(self.rows,signals,ramps,start=900,end=1050)
        self.assertTrue(result['valid'])
        self.assertEqual(result['expected_groups'],130)
        self.assertEqual(sum(result['post_step_rows'].values()),19500)
        complete=audit_interval(ROOT/'evaluation/runs/codex_area_beta0_s13_20260910',900,1050,
            ROOT/'diagnostics/area_production_preflight/wu-link_t900_beta0_20260909T191544832356Z')
        self.assertEqual(complete['status'],'pass')
        self.assertTrue(complete['reference']['csv_byte_identical'])
        self.assertTrue(all(complete['reference']['snapshot_sections_equal'].values()))
        self.assertTrue(complete['next_decision_errors'])

    def test_real_different_1050_command_rejects_stale_900_trace(self):
        self.assertNotEqual(self.commands900,self.commands1050)
        _,signals,ramps=parse_commands(self.commands1050,900)
        result=trace_audit(self.rows,signals,ramps,start=900,end=1050)
        self.assertFalse(result['valid'])
        self.assertGreater(result['command_mismatch_count'],0)

    def test_missing_action_after_recorded_failure_is_not_pending(self):
        result=audit_interval(ROOT/'evaluation/runs/codex_area_beta0_s13_20260910',1050,1200)
        self.assertEqual(result['status'],'fail')
        self.assertTrue(result['interval_errors'])

    @staticmethod
    def zero_offset_fixture():
        controller={'cycle_sec':10.,'offset_sec':0.,'windows':{'1':[(0.,3.)],'2':[(5.,8.)]}}
        # Independent literal VBS aspect sequence, including amber suppression
        # when the other group is green. No use of the audit oracle to generate it.
        aspects={'1':['GREEN']*3+['AMBER']*2+['RED']*5,
                 '2':['RED']*5+['GREEN']*3+['AMBER']*2}
        rows=[dict(sim_sec='10',sc_no='5',sg_no='1',requested_state='INVALID',readback_state='INVALID',ok='0',stage='post_step')]
        for sec in range(10,20):
            for stage,clock in (('immediate',sec),('post_step',sec+1)):
                for sg in ('1','2'):
                    value=aspects[sg][sec%10]
                    rows.append(dict(sim_sec=str(clock),sc_no='5',sg_no=sg,requested_state=value,
                                     readback_state=value,ok='1',stage=stage))
        return rows,{'5':controller}

    def test_zero_offset_is_valid_and_end_poststep_uses_previous_command(self):
        rows,signals=self.zero_offset_fixture()
        result=trace_audit(rows,signals,{},start=10,end=20)
        self.assertTrue(result['valid'])
        self.assertEqual([row['covered_sec'] for row in result['groups']],[10,10])

    def test_missing_final_samples_remain_incomplete(self):
        rows,signals=self.zero_offset_fixture()
        rows=[row for row in rows if not (row['stage']=='post_step' and row['sim_sec']=='20')]
        result=trace_audit(rows,signals,{},start=10,end=20)
        self.assertFalse(result['interval_complete'])
        self.assertEqual(len(result['incomplete_groups']),2)
        self.assertEqual(result['command_mismatch_count'],0)
        self.assertEqual(result['persistence_mismatch_count'],0)


if __name__=='__main__': unittest.main()
