import math
import unittest
from types import SimpleNamespace
from evaluation.controllers.freeway_fd import literature_vsl_parameters as law
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups


class LiteratureVSLTests(unittest.TestCase):
    def test_carlson_equation_11(self):
        self.assertEqual(law(dict(law='carlson',A=.8,E=3.,alpha=0.),120.,30.,2.5,60.,120.),(60.,42.,5.))

    def test_frejo_equation_13(self):
        result=law(dict(law='frejo',A=.4,E=2.5,alpha=.1),120.,30.,2.5,60.,120.)
        for actual,expected in zip(result,(66.,35.4,4.1875)):
            self.assertAlmostEqual(actual,expected)

    def test_nominal_ratio_carlson_identity(self):
        self.assertEqual(law(dict(law='carlson',A=1.,E=3.,alpha=0.),122.,34.,1.3,120.,120.),(122.,34.,1.3))

    def test_frejo_uses_legal_not_free_speed_ratio(self):
        self.assertEqual(law(dict(law='frejo',A=0.,E=1.,alpha=0.),100.,30.,2.,60.,120.),(60.,30.,2.))

    def test_frejo_compliance_saturates(self):
        self.assertEqual(law(dict(law='frejo',A=.8,E=3.,alpha=1.),100.,30.,2.,60.,120.),(100.,30.,2.))

    def test_invalid_values_fail(self):
        for patch in ({'A':-1.},{'E':0.},{'alpha':float('nan')},{'A':True},{'law':'unknown'}):
            with self.assertRaises(ValueError):
                law(dict(dict(law='frejo',A=.4,E=2.5,alpha=0.),**patch),120.,30.,2.,100.,120.)
        with self.assertRaises(ValueError):law(dict(law='carlson',A=.4,E=2.5,alpha=.1),120.,30.,2.,100.,120.)

    def test_disabled_and_inactive_leave_exact_target(self):
        p=object.__new__(PhysicalLaneGroups);p.vsl_fd_response=None
        self.assertEqual(p._literature_target(0,30.,71.234,100.,True,None),71.234)
        p.vsl_fd_response=dict(law='frejo',A=.4,E=2.5,alpha=0.)
        self.assertEqual(p._literature_target(0,30.,71.234,120.,False,None),71.234)

    def test_cell_parameters_consumed_and_storage_guard(self):
        p=object.__new__(PhysicalLaneGroups);p.road='FW_E';p.vsl_fd_response=dict(law='carlson',A=.8,E=3.,alpha=0.)
        net=SimpleNamespace(v_free=100.,rho_crit=20.,metanet_a_m=2.,rho_max=180.,
            freeway_segment_params={'FW_E':[dict(v_free=120.,rho_crit=30.,metanet_a_m=2.5,rho_max=180.)]})
        cfg=SimpleNamespace(network=net,freeway_follower=SimpleNamespace(vsl_set=[60.,120.]))
        self.assertAlmostEqual(p._literature_target(0,42.,90.,60.,True,cfg),60.*math.exp(-.2))
        net.freeway_segment_params['FW_E'][0]['rho_max']=40.
        with self.assertRaises(ValueError):p._literature_target(0,30.,90.,60.,True,cfg)


if __name__=='__main__':unittest.main()
