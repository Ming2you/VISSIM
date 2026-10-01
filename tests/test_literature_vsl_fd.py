import math
import unittest
from types import SimpleNamespace
from typing import Mapping
from evaluation.controllers.freeway_fd import literature_vsl_parameters as law
from evaluation.controllers.freeway_fd import configure_literature_vsl, literature_desired_speed, VSLExposure
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


# ---------------------------------------------------------------- K4: L2 speed_scale (REPIN_V3C2 plan 3.4, V-1/V-2)
M_V = {'80': 0.7225223093088844, '90': 0.8119772280655296, '100': 0.9006844904146349}   # fit_results 4091d6e1 L2


def l2(**patch):
    spec = dict(law='carlson', A=1.33, E=0.87, alpha=0.,
                speed_scale={'form': 'cubic_lagrange', 'levels': dict(M_V), 'maximum': 110.0})
    spec.update(patch)
    return spec


def old_law(spec, v_free, critical, shape, command, maximum, math=math):
    """freeway_fd.literature_vsl_parameters at 9ed2ef0 (:19-46), verbatim body: the key-absent reference.
    `math` is the module the tangent instrumentation substitutes (sdmpc_dual.MathProxy) in the Dual tests."""
    if (not isinstance(spec, Mapping) or set(spec) != {'law', 'A', 'E', 'alpha'}
            or spec['law'] not in ('carlson', 'frejo')):
        raise ValueError('Explicit Carlson/Frejo FD parameters required')
    values = [spec[k] for k in ('A', 'E', 'alpha')]
    if (any(isinstance(x, bool) or not isinstance(x, (int, float))
            or not math.isfinite(x) for x in values)
            or spec['A'] < 0 or spec['E'] <= 0 or spec['alpha'] < 0
            or (spec['law'] == 'carlson' and spec['alpha'] != 0)):
        raise ValueError('Invalid literature VSL coefficients')
    if (any(not math.isfinite(x) or x <= 0 for x in
            (v_free, critical, shape, command, maximum)) or command > maximum):
        raise ValueError('Invalid VSL FD state/command')
    b = command / maximum
    if spec['law'] == 'carlson':
        speed = v_free * b
    else:
        b = min(b * (1. + spec['alpha']), 1.)
        speed = min(maximum * b, v_free)
    return (speed, critical * (1. + spec['A'] * (1. - b)),
            shape * (spec['E'] - (spec['E'] - 1.) * b))


class SpeedScaleTests(unittest.TestCase):
    def test_key_absent_is_bit_identical(self):
        for spec in (dict(law='carlson', A=.94, E=1.44, alpha=0.), dict(law='frejo', A=.4, E=2.5, alpha=.1)):
            for command in (80., 90., 95.5, 100., 109.999, 110.):
                for args in ((100., 30., 2., command, 110.), (85.97, 27.3, 1.7, command, 110.), (100., 30., 2., 100., 120.)):
                    got, want = law(spec, *args), old_law(spec, *args)
                    self.assertEqual([x.hex() for x in got], [x.hex() for x in want], (spec, args))

    def test_key_absent_adds_no_tangent_operation(self):
        # N1: the tangent trace counts every Dual operation and comparison; the key-absent law must not add one.
        from unittest import mock
        from evaluation.controllers import freeway_fd
        from evaluation.controllers.sdmpc_dual import MathProxy, Trace, derivative, primal
        proxy = MathProxy()     # what sdmpc_tangent_runtime substitutes for `math` in instrumented modules
        for spec in (dict(law='carlson', A=.94, E=1.44, alpha=0.), dict(law='frejo', A=.4, E=2.5, alpha=.1)):
            for command in (90., 110.):
                new, old = Trace([0], track_stencils=False), Trace([0], track_stencils=False)
                with mock.patch.object(freeway_fd, 'math', proxy):
                    a = law(spec, 100., 30., 2., new.scalar(command, {0: 1.}), 110.)
                b = old_law(spec, 100., 30., 2., old.scalar(command, {0: 1.}), 110., math=proxy)
                self.assertEqual((new.operations, new.tangent_entries, dict(new.counts)),
                                 (old.operations, old.tangent_entries, dict(old.counts)))
                self.assertEqual([primal(x).hex() for x in a], [primal(x).hex() for x in b])
                self.assertEqual([derivative(x) for x in a], [derivative(x) for x in b])

    def test_levels_are_exact_and_the_maximum_is_the_nominal_fd(self):
        for key, m in M_V.items():
            vf, rc, a = law(l2(), 100., 30., 2., float(key), 110.)
            self.assertEqual(vf, 100. * m)
            self.assertEqual(rc, 30. * (1. + 1.33 * (1. - m)))
            self.assertEqual(a, 2. * (.87 - (.87 - 1.) * m))
        self.assertEqual(law(l2(), 100., 30., 2., 110., 110.), (100., 30., 2.))

    def test_monotone_between_levels_and_critical_density_below_jam(self):
        last = None
        for i in range(0, 301):
            command = 80. + i * .1
            vf, rc, _ = law(l2(), 100., 30., 2., command, 110.)
            if last is not None:
                self.assertGreater(vf, last[0])
                self.assertLess(rc, last[1])
            last = (vf, rc)
        p = object.__new__(PhysicalLaneGroups); p.road = 'FW_E'; p.vsl_fd_response = l2()
        net = SimpleNamespace(v_free=100., rho_crit=20., metanet_a_m=2., rho_max=180.,
                              freeway_segment_params={'FW_E': [dict(v_free=120., rho_crit=30., metanet_a_m=2.5, rho_max=180.)]})
        cfg = SimpleNamespace(network=net, freeway_follower=SimpleNamespace(vsl_set=[80., 90., 100., 110.]))
        self.assertTrue(math.isfinite(p._literature_target(0, 42., 90., 80., True, cfg)))
        net.freeway_segment_params['FW_E'][0]['rho_max'] = 41.
        with self.assertRaises(ValueError):      # 30 * (1 + 1.33 * 0.2775) = 41.07 >= 41
            p._literature_target(0, 30., 90., 80., True, cfg)

    def test_slopes_and_extrapolation(self):
        from evaluation.controllers.freeway_fd import speed_scale_knots, speed_scale_ratio
        knots = speed_scale_knots(l2()['speed_scale'])
        self.assertEqual(knots[-1], (110., 1.))
        h = 1e-4
        left = (speed_scale_ratio(knots, 110.) - speed_scale_ratio(knots, 110. - h)) / h
        self.assertAlmostEqual(left, 0.01084049344180947, places=6)
        self.assertGreater(left, 1 / 110)
        self.assertLess(speed_scale_ratio(knots, 75.), M_V['80'])
        self.assertAlmostEqual(speed_scale_ratio(knots, 75.), 0.6739657588890473, places=12)

    def test_tangent_equals_the_central_difference(self):
        from unittest import mock
        from evaluation.controllers import freeway_fd
        from evaluation.controllers.sdmpc_dual import MathProxy, Trace, derivative
        patch = mock.patch.object(freeway_fd, 'math', MathProxy())
        patch.start()
        self.addCleanup(patch.stop)
        for command in (80., 90., 100.):
            trace = Trace([0], track_stencils=False)
            got = law(l2(), 100., 30., 2., trace.scalar(command, {0: 1.}), 110.)
            h = 1e-4
            up, down = law(l2(), 100., 30., 2., command + h, 110.), law(l2(), 100., 30., 2., command - h, 110.)
            for value, a, b in zip(got, up, down):
                self.assertAlmostEqual(derivative(value)[0], (a - b) / (2 * h), delta=1e-4 * max(1., abs((a - b) / (2 * h))))
        trace = Trace([0], track_stencils=False)
        got = law(l2(), 100., 30., 2., trace.scalar(110., {0: 1.}), 110.)
        self.assertAlmostEqual(derivative(got[0])[0], 100. * 0.01084049344180947, places=6)

    def test_refusals(self):
        bad = [l2(law='frejo'),
               l2(speed_scale={'form': 'cubic', 'levels': dict(M_V), 'maximum': 110.}),
               l2(speed_scale={'form': 'cubic_lagrange', 'levels': {'80': .72, '90': .81}, 'maximum': 110.}),
               l2(speed_scale={'form': 'cubic_lagrange', 'levels': dict(M_V, **{'100': 1.0}), 'maximum': 110.}),
               l2(speed_scale={'form': 'cubic_lagrange', 'levels': {'80': .72, '90': .81, '110': .9}, 'maximum': 110.}),
               l2(speed_scale={'form': 'cubic_lagrange', 'levels': dict(M_V), 'maximum': 110., 'extra': 1}),
               l2(speed_scale={'form': 'cubic_lagrange', 'levels': dict(M_V), 'maximum': True}),
               l2(extra=1)]
        for spec in bad:
            with self.assertRaises(ValueError, msg=spec):
                law(spec, 100., 30., 2., 90., 110.)
        with self.assertRaises(ValueError):          # the law's maximum must be the scale's last knot
            law(l2(), 100., 30., 2., 90., 120.)
        with self.assertRaises(ValueError):          # undefined above the maximum (primal refusal only)
            law(l2(), 100., 30., 2., 110.5, 110.)

    def test_configure_and_lane_group_validation(self):
        cfg = SimpleNamespace(network=SimpleNamespace(freeway_links=['FW_E', 'FW_W']),
                              freeway_follower=SimpleNamespace(vsl_set=[80., 90., 100., 110.]))
        self.assertEqual(configure_literature_vsl(cfg, {'freeway': {'vsl_fd_response': {'FW_E': l2()}}}),
                         {'freeway_literature_vsl_enabled': 1.0})
        self.assertEqual(cfg.network.freeway_vsl_fd_response['FW_E'], l2())
        # the monotonicity check belongs to the installer (the per-call law parses the structure only)
        bent = l2(speed_scale={'form': 'cubic_lagrange', 'levels': {'80': .9, '90': .5, '100': .95}, 'maximum': 110.})
        law(bent, 100., 30., 2., 90., 110.)
        with self.assertRaisesRegex(ValueError, 'not strictly increasing'):
            configure_literature_vsl(cfg, {'freeway': {'vsl_fd_response': {'FW_E': bent}}})
        for vsl_set in ([80., 90., 110.], [80., 90., 100., 120.], [70., 80., 90., 100., 110.]):
            cfg.freeway_follower.vsl_set = vsl_set
            with self.assertRaises(ValueError, msg=vsl_set):
                configure_literature_vsl(cfg, {'freeway': {'vsl_fd_response': {'FW_E': l2()}}})
        # key absent never reads the vsl_set (the old configure did not either)
        bare = SimpleNamespace(network=SimpleNamespace(freeway_links=['FW_E']))
        configure_literature_vsl(bare, {'freeway': {'vsl_fd_response': {'FW_E': dict(law='carlson', A=.94, E=1.44, alpha=0.)}}})
        from evaluation.controllers.freeway_fd import literature_validation_maximum
        self.assertEqual(literature_validation_maximum(dict(law='carlson', A=.94, E=1.44, alpha=0.), 120.), 120.)
        self.assertEqual(literature_validation_maximum(l2(), 120.), 110.)


if __name__=='__main__':unittest.main()
