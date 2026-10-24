import copy,unittest
import full_calibration as f
from test_hadiuzzaman import ConservedReceiving
from run import apply_physical_coefficients


class CalibrationContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):ConservedReceiving.setUpClass()

    def test_all_physical_values_reach_scalar_and_rows_without_geometry_change(self):
        _,_,cfg=ConservedReceiving().fixture();before=copy.deepcopy(cfg.network.freeway_segment_params['FW_E'])
        values=dict(v_free=111.,rho_crit=29.,rho_max=175.,metanet_a_m=1.8,metanet_kappa_veh_km_lane=44.,
            metanet_delta_merge=.6,freeway_lane_drop_phi=2.)
        apply_physical_coefficients(cfg,'FW_E',values)
        for key,value in values.items():self.assertEqual(getattr(cfg.network,key),value)
        for a,b in zip(before,cfg.network.freeway_segment_params['FW_E']):
            expected={**a,**{k:v for k,v in values.items() if k not in ('metanet_delta_merge','freeway_lane_drop_phi')}}
            self.assertEqual(b,expected)

    def test_unknown_and_inconsistent_inputs_fail(self):
        for values in ({'typo':2},{'rho_crit':200},{'v_free':float('nan')},{'rho_max':-1}):
            _,_,cfg=ConservedReceiving().fixture()
            with self.assertRaises(ValueError):apply_physical_coefficients(cfg,'FW_E',values)

    def test_optimizer_residual_exactly_matches_existing_loss(self):
        p=f.c.load(f.B/'refined_guard1_none.json');r=f.residual(p)
        self.assertEqual(len(r),1003)
        self.assertAlmostEqual(float(r@r),f.c.score(p)['objective'],places=10)

    def test_wang_wave_is_derived_not_an_extra_free_coefficient(self):
        values={k:v[2] for k,v in f.BOUNDS.items()}
        a=f.specification('a',values,'wang');values['wave']=28.
        b=f.specification('b',values,'wang')
        self.assertEqual(a['hadiuzzaman'],b['hadiuzzaman'])
        self.assertEqual(a['hadiuzzaman']['relaxation_cells'],b['hadiuzzaman']['relaxation_cells'])


if __name__=='__main__':unittest.main()
