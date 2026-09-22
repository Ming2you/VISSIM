import unittest
import vsl_strength as s


class CommonFiveSecondCosts(unittest.TestCase):
    def setUp(self):
        groups=sum(map(len,s.c.WIDTHS))
        self.p=dict(lane_groups={'FW_E':[dict(time_s=t,n_veh=2.) for t in range(2401,2851) for _ in range(groups)]},
            ramps=[dict(end_sec=t,road=road,end={'connector_veh':n}) for t in range(2401,2851) for road,n in [('FW_E',3.)]*4+[('FW_W',999.)]],
            ports=[dict(time_s=t,road=road,n_veh=n) for t in range(2401,2851) for road,n in [('FW_E',4.)]*4+[('FW_W',999.)]],
            diagnostics={'roads':[{'road':'FW_E','model_residence_10s_veh_h':9999}]})
        self.expected=dict(mainline=2*groups*450/3600,on=12*450/3600,off=16*450/3600)

    def test_constant_stock_integrates_exactly_without_cached_costs_or_west(self):
        self.assertEqual(s.sampled_costs(self.p),self.expected)

    def test_non_sampled_one_second_records_do_not_change_comparison(self):
        for r in self.p['lane_groups']['FW_E']:
            if r['time_s']%5:r['n_veh']=1234.
        self.assertEqual(s.sampled_costs(self.p),self.expected)

    def test_missing_end_sample_fails(self):
        self.p['ports']=[r for r in self.p['ports'] if r['time_s']!=2850]
        with self.assertRaises(AssertionError):s.sampled_costs(self.p)


if __name__=='__main__':unittest.main()
