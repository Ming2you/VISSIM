import copy,json,unittest
from pathlib import Path
from types import SimpleNamespace
import candidate as c
class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.report=c.read(c.HERE/'assessment.json')
        self.network=c.read(c.HERE.parent/'native_beta/forecast2400_checked/network.json')
    def test_past_only_despite_larger_late_observation(self):
        expected=c.paired_support(self.report)
        altered=copy.deepcopy(self.report)
        for row in altered['rows']:
            if row['end_sec']>2400:
                for head in row['groups']['SC101_S']['heads']:head['startup_inclusive_achieved_rate_veh_h']=1e9
        self.assertEqual(c.paired_support(altered),expected)
        self.assertEqual(expected['end_sec'],[1800,1950])
    def test_inconsistent_rate_rejected(self):
        r=copy.deepcopy(self.report)
        next(x for x in r['rows'] if x['end_sec']==1800)['groups']['SC101_S']['heads'][0]['startup_inclusive_achieved_rate_veh_h']+=10
        with self.assertRaisesRegex(ValueError,'Rate calculation'):c.paired_support(r)
    def test_discontinuous_windows_not_paired(self):
        r=copy.deepcopy(self.report);r['rows']=[x for x in r['rows'] if x['end_sec']!=1950]
        with self.assertRaisesRegex(ValueError,'No paired'):c.paired_support(r)
    def test_too_small_prefix_rejected(self):
        r=copy.deepcopy(self.report)
        next(x for x in r['rows'] if x['end_sec']==1800)['groups']['SC101_S']['heads'][0]['queued_prefix_veh']=4
        with self.assertRaisesRegex(ValueError,'Invalid queued'):c.paired_support(r)
    def test_one_rate_only_and_unchanged_at_unused_state(self):
        cfg=SimpleNamespace(network=SimpleNamespace(**copy.deepcopy(self.network)))
        before=copy.deepcopy(vars(cfg.network));receipt=c.install(cfg,2400)
        after=copy.deepcopy(vars(cfg.network))
        self.assertEqual([k for k in after if after[k]!=before[k]],['movement_capacity_by_movement_veh_h'])
        newcap=after.pop('movement_capacity_by_movement_veh_h');oldcap=before.pop('movement_capacity_by_movement_veh_h')
        self.assertEqual([k for k in newcap if newcap[k]!=oldcap[k]],[c.MOVEMENT]);self.assertEqual(before,after)
        cfg2=SimpleNamespace(network=SimpleNamespace(**copy.deepcopy(self.network)))
        self.assertEqual(c.install(cfg2,3300)['after_veh_h'],receipt['after_veh_h'])
    def test_wrong_receiver_rejected(self):
        cfg=SimpleNamespace(network=SimpleNamespace(**copy.deepcopy(self.network)))
        cfg.network.urban_movements[c.MOVEMENT]['receiving_link']='wrong'
        with self.assertRaisesRegex(ValueError,'Movement identity'):c.install(cfg,2400)
    def test_unknown_time_rejected(self):
        with self.assertRaisesRegex(ValueError,'Bounded'):c.install(None,900)
if __name__=='__main__':unittest.main(verbosity=2)

