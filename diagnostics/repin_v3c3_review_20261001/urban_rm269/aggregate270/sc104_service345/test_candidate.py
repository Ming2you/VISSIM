from pathlib import Path
import json,unittest
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc104_service345 import candidate as c
from diagnostics.validate_native_signal_record import read_ldp_frames
class NativeClockTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schedules,e=c.compile_fixed_signal_schedules(c.NET,['SC104'],{'link_to_origins':{'1220061200':['in_SC104_E']}})
        assert not e
        cls.schedule=cls.schedules['SC104']
        cls.spec=dict(origin='in_SC104_E',intersection='SC104',phase='')
        cls.ldp=read_ldp_frames({104:Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/vissim_eval/sdmpc31_g_2400_hold_s29_104_001.ldp')},{104:list(range(1,9))},1800,2400)
    def test_default_exact(self):
        before=[self.schedule.movement_green_fraction(self.spec,t,10) for t in range(1800,2400,10)]
        with c.fixed_clock():after=[self.schedule.movement_green_fraction(self.spec,t,10) for t in range(1800,2400,10)]
        self.assertEqual(before,after)
    def test_past_clock_all_600_seconds(self):
        spec={**self.spec,'sc104_qualified_fixed_clock':True}
        with c.fixed_clock():
            for t in range(1800,2400):
                self.assertEqual(self.schedule.movement_green_fraction(spec,t,1),float(self.ldp['frames'][t+1]['104:6']=='GREEN'))
    def test_coarse_additivity(self):
        spec={**self.spec,'sc104_qualified_fixed_clock':True}
        with c.fixed_clock():
            for t in range(1800,2400,10):
                self.assertAlmostEqual(10*self.schedule.movement_green_fraction(spec,t,10),sum(self.schedule.movement_green_fraction(spec,t+i,1) for i in range(10)))
    def test_wrong_authority_rejected(self):
        with c.fixed_clock(),self.assertRaises(ValueError):
            self.schedule.movement_green_fraction({**self.spec,'origin':'other','sc104_qualified_fixed_clock':True},1800,10)
    def test_conservative_past_rate(self):self.assertAlmostEqual(c.support(),2828.5714285714284)
if __name__=='__main__':unittest.main()
