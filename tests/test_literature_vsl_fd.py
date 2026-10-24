import math
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from evaluation.controllers.freeway_fd import literature_vsl_parameters as law
from evaluation.controllers.freeway_fd import configure_literature_vsl, literature_desired_speed, VSLExposure
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups


class LiteratureVSLTests(unittest.TestCase):
    def tangent_target(self):
        # Exercise the same source instrumentation used by the isolated AD
        # worker, while leaving the normal imported module unmodified.
        from evaluation.controllers import freeway_fd
        from evaluation.controllers.sdmpc_tangent_runtime import Transform, namespace
        scope = dict(vars(freeway_fd))
        scope.update(namespace())
        tree = Transform().visit(ast.parse(Path(freeway_fd.__file__).read_text(encoding='utf-8')))
        exec(compile(ast.fix_missing_locations(tree), freeway_fd.__file__, 'exec'), scope)
        return scope['literature_desired_speed']

    def test_inactive_ad_preserves_target_without_inventing_command_slope(self):
        from evaluation.controllers.sdmpc_dual import Dual, Trace, derivative
        spec = dict(law='carlson', A=.5, E=2., alpha=0.)
        cfg = SimpleNamespace(network=SimpleNamespace(v_free=110., rho_crit=30.,
            metanet_a_m=2., rho_max=180.), freeway_follower=SimpleNamespace(vsl_set=[90.,100.,110.]))
        trace = Trace([.01,.01])
        target = Dual(75., {0:-1.}, trace)
        command = Dual(110., {1:1.}, trace)
        actual = self.tangent_target()(spec,cfg,'FW_E',0,24.,target,command,False)
        self.assertEqual(derivative(actual), {0:-1.})
        # The scalar predictor is locally flat at the inactive maximum too.
        for value in (109.99,110.,110.01):
            self.assertEqual(literature_desired_speed(spec,cfg,'FW_E',0,24.,75.,value,False),75.)

    def test_active_ad_command_slope_matches_scalar_difference(self):
        from evaluation.controllers.sdmpc_dual import Dual, Trace, derivative, primal
        spec = dict(law='carlson', A=.5, E=2., alpha=0.)
        cfg = SimpleNamespace(network=SimpleNamespace(v_free=110., rho_crit=30.,
            metanet_a_m=2., rho_max=180.), freeway_follower=SimpleNamespace(vsl_set=[90.,100.,110.]))
        target = self.tangent_target()(spec,cfg,'FW_E',0,24.,75.,Dual(100.,{0:1.},Trace([.001])),True)
        def value(command):
            return literature_desired_speed(spec,cfg,'FW_E',0,24.,75.,command,True)
        self.assertAlmostEqual(primal(target),value(100.),places=12)
        self.assertAlmostEqual(derivative(target)[0],(value(100.001)-value(99.999))/.002,places=7)

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

    def test_runtime_direction_and_absence_isolation(self):
        cfg=SimpleNamespace(network=SimpleNamespace(freeway_links=['FW_E','FW_W']))
        tuning={'freeway':{'vsl_fd_response':{'FW_E':dict(law='carlson',A=.5,E=2.,alpha=0.)}}}
        configure_literature_vsl(cfg,tuning)
        self.assertEqual(set(cfg.network.freeway_vsl_fd_response),{'FW_E'})
        tuning['freeway']['vsl_fd_response']['FW_E']['A']=3.
        self.assertEqual(cfg.network.freeway_vsl_fd_response['FW_E']['A'],.5)
        configure_literature_vsl(cfg,{})
        self.assertFalse(hasattr(cfg.network,'freeway_vsl_fd_response'))
        self.assertEqual(literature_desired_speed(None,None,None,0,30.,71.234,90.,True),71.234)

    def test_competing_laws_and_unknown_direction_rejected(self):
        cfg=SimpleNamespace(network=SimpleNamespace(freeway_links=['FW_E'],vsl_fd_two_branch=True))
        tuning={'freeway':{'vsl_fd_response':{'FW_E':dict(law='carlson',A=.5,E=2.,alpha=0.)}}}
        with self.assertRaises(ValueError):configure_literature_vsl(cfg,tuning)
        cfg.network.vsl_fd_two_branch=False
        tuning['freeway']['component_literature']={'family':'hadi'}
        with self.assertRaises(ValueError):configure_literature_vsl(cfg,tuning)
        tuning['freeway'].pop('component_literature')
        tuning['freeway']['vsl_fd_response']['wrong']={}
        with self.assertRaises(ValueError):configure_literature_vsl(cfg,tuning)

    def test_capacity_is_not_automatically_increased(self):
        # Peak exponential-FD flow per lane is vf*critical*exp(-1/shape).
        spec=dict(law='carlson',A=0.,E=1.,alpha=0.)
        vf,rc,a=law(spec,110.,30.,2.,90.,110.)
        self.assertLess(vf*rc*math.exp(-1/a),110.*30.*math.exp(-.5))

    def test_sign_changes_new_arrivals_not_resident_vehicles(self):
        x=VSLExposure([10.,10.],dict(sign_cells=[0],initial_command=110.,ramp_command=110.),110.)
        x.advance([10.,10.],[10.,10.],[2.],[2.,2.],2.,[0.,0.],[90.,90.])
        self.assertEqual(x.cohorts,[{110.:8.,90.:2.},{110.:10.}])
        x.advance([10.,10.],[10.,10.],[2.],[2.,2.],2.,[0.,0.],[90.,90.])
        self.assertAlmostEqual(x.cohorts[1][90.],.4)
        self.assertLess(x.max_residual,1e-10)

    def test_ramp_bypasses_upstream_sign_and_downstream_sign_restores(self):
        x=VSLExposure([10.,10.],dict(sign_cells=[1],initial_command=90.,ramp_command=110.),110.)
        x.advance([10.,10.],[8.,11.],[2.],[2.,2.],0.,[0.,1.],[90.,110.])
        self.assertEqual(x.cohorts[1],{90.:8.,110.:3.})
        with self.assertRaises(ArithmeticError):x.advance([8.,11.],[0.,0.],[9.],[9.,11.],0.,[0.,0.],[90.,110.])

    def test_empty_cell_can_receive_without_a_stale_cohort_key(self):
        x=VSLExposure([0.,2.],dict(sign_cells=[0],initial_command=110.,ramp_command=110.),110.)
        x.advance([0.,2.],[1.,1.],[0.],[0.,1.],1.,[0.,0.],[90.,110.])
        self.assertEqual(x.cohorts,[{90.:1.},{110.:1.}])
        self.assertEqual(x.max_residual,0.)

    def test_tiny_positive_cohort_can_drain(self):
        x=VSLExposure([1e-13],dict(sign_cells=[],initial_command=110.,ramp_command=110.),110.)
        x.advance([1e-13],[0.],[],[1e-13],0.,[0.],[110.])
        self.assertEqual(x.cohorts,[{}])
        self.assertEqual(x.max_residual,0.)


if __name__=='__main__':unittest.main()
