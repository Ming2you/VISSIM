"""Held commands must follow both boundaries, without waiving other proof."""
import csv
import unittest
from diagnostics.com_execution_equivalence import verify_pair as v
from diagnostics.com_execution_equivalence.test_recovered_decision import RecoveredDecisionTests
from diagnostics.com_execution_equivalence.test_verify_pair import save,table,ACTION_FIELDS

class HeldVslWindowTests(unittest.TestCase):
    setUp=RecoveredDecisionTests.setUp
    actual=staticmethod(RecoveredDecisionTests.actual)

    def configure(self,start,end,old_speed,new_speed):
        policy=dict(start_sec=start,base_kmh=80,zone_kmh={'FW_E__seg13':90})
        if end is not None:policy['end_sec']=end
        cfg=dict(runtime={'decision_error_policy':'hold_previous'},
            adapter={'sdmpc_fixed_vsl':policy},freeway={'vsl_zone_heads':{'FW_E':[0,13,30]}})
        save(self.tuning,cfg);self.prov['files']['tuning']['sha256']=v.sha(self.tuning)
        for p,speed in ((self.previous,old_speed),(self.action,new_speed)):
            z=v.read(p);z['vsl']['FW_E']=speed;save(p,z)
            with p.with_suffix('.csv').open(newline='',encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
            rows[0]['speed_kph']=str(speed);table(p.with_suffix('.csv'),ACTION_FIELDS,rows)
        z=v.read(self.action)
        z['metadata']['hold_previous'].update(json_sha256=v.sha(self.previous),csv_sha256=v.sha(self.previous.with_suffix('.csv')))
        save(self.action,z)

    def evidence(self):
        return v.decision_recovery_evidence(self.run,'run',self.prov,self.log.read_text().splitlines())

    def test_boundaries_and_legacy_open_ended_schedule(self):
        for start,end,old_speed,new_speed in [(18,24,80,80),(12,18,80,90),(0,18,90,90),
                                                (0,12,90,80),(0,6,80,80),(0,None,90,90)]:
            with self.subTest(start=start,end=end):
                self.configure(start,end,old_speed,new_speed)
                self.assertTrue(self.evidence()['passed'])
                self.assertFalse(self.evidence()['no_calculation_failures'])

    def test_wrong_speed_is_rejected_even_with_matching_json_csv(self):
        for start,end,old_speed,wrong in [(18,24,80,90),(12,18,80,80),(0,12,90,90),(0,6,80,90)]:
            with self.subTest(start=start,end=end):
                self.configure(start,end,old_speed,wrong)
                with self.assertRaisesRegex(ValueError,'Held VSL differs from pinned schedule'):self.evidence()

if __name__=='__main__':unittest.main()
