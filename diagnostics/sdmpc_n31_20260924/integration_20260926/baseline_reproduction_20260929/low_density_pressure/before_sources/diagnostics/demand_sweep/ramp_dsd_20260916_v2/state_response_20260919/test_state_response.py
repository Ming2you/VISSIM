"""Regime boundary, configuration isolation and serialization contracts."""
import copy
import pickle
from types import SimpleNamespace as NS
import unittest
from evaluation.controllers.freeway_fd import configure_state_response, state_response_coefficients, cell_state_response, FDParameters

class StateResponseTests(unittest.TestCase):
    def cfg(self):return NS(network=NS(freeway_links=['FW_E','FW_W']),simulation=NS(T_f_h=10/3600))
    def spec(self):return {'FW_E':{'relaxation':{'acceleration_sec':24.,'deceleration_sec':12.},
        'anticipation':{'downstream_ge_local':70.,'downstream_lt_local':12.},'congested_nu_multiplier':2.}}
    def test_disabled_exact_coefficients(self):
        self.assertEqual(state_response_coefficients({},50,60,25,30,27,12/3600,35),(12/3600,35))
    def test_regime_boundaries(self):
        s=self.spec()['FW_E']
        for speed,desired,rho,down,expected in [(50,60,26,30,(24/3600,70)),(60,50,26,25,(12/3600,12)),
            (50,50,27,27,(24/3600,70)),(50,60,28,30,(24/3600,140)),(60,50,28,25,(12/3600,24))]:
            self.assertEqual(state_response_coefficients(s,speed,desired,rho,down,27,1.,35),expected)
    def test_config_and_worker_copy(self):
        c=self.cfg();s=self.spec();before=copy.deepcopy(s)
        configure_state_response(c,{'freeway':{'state_response':s}})
        s['FW_E']['relaxation']['acceleration_sec']=99
        worker=pickle.loads(pickle.dumps(c))
        self.assertEqual(worker.network.freeway_state_response,before)
        self.assertNotIn('FW_W',worker.network.freeway_state_response)
        configure_state_response(c,{})
        self.assertFalse(hasattr(c.network,'freeway_state_response'))
    def test_invalid_config(self):
        bad=[{}, {'bad':{'congested_nu_multiplier':2}}, {'FW_E':{'unknown':2}},
            {'FW_E':{'relaxation':{'acceleration_sec':24}}},
            {'FW_E':{'relaxation':{'acceleration_sec':9,'deceleration_sec':12}}},
            {'FW_E':{'congested_nu_multiplier':True}}, {'FW_E':{'congested_nu_multiplier':float('nan')}},
            {'FW_E':{'anticipation':{'downstream_ge_local':-1,'downstream_lt_local':12}}}]
        for s in bad:
            with self.subTest(spec=s),self.assertRaises(ValueError):configure_state_response(self.cfg(),{'freeway':{'state_response':s}})
    def test_vsl_fd_does_not_add_capacity(self):
        fd=FDParameters(120,20,150)
        caps=[u*fd.critical(u,True) for u in [60,80,100,120]]
        self.assertEqual(caps,sorted(caps))
        self.assertEqual(caps[-1],2400)

    def test_local_coefficients_leave_other_cells_and_direction_unchanged(self):
        c=self.cfg();c.network.freeway_segment_params={'FW_E':[{}, {}, {}]}
        s=self.spec();common=copy.deepcopy(s['FW_E'])
        s['FW_E']['cell_overrides']={'1':{'anticipation':{'downstream_ge_local':35.,'downstream_lt_local':60.}}}
        configure_state_response(c,{'freeway':{'state_response':s}})
        worker=pickle.loads(pickle.dumps(c))
        expected=lambda spec:state_response_coefficients(spec,50,60,28,20,27,1.,1.)
        self.assertEqual(expected(cell_state_response(worker.network,'FW_E',1)),(24/3600,120.))
        for i in (0,2):self.assertEqual(expected(cell_state_response(worker.network,'FW_E',i)),expected(common))
        self.assertEqual(cell_state_response(worker.network,'FW_W',1),{})
        s['FW_E']['cell_overrides']['1']['anticipation']['downstream_lt_local']=999.
        self.assertEqual(expected(cell_state_response(worker.network,'FW_E',1)),(24/3600,120.))

    def test_local_only_configuration_and_disable(self):
        c=self.cfg();c.network.freeway_segment_params={'FW_E':[{},{}]}
        configure_state_response(c,{'freeway':{'state_response':{'FW_E':{'cell_overrides':{'0':{'congested_nu_multiplier':2.}}}}}})
        self.assertEqual(state_response_coefficients(cell_state_response(c.network,'FW_E',1),50,60,28,30,27,.1,35),(.1,35))
        configure_state_response(c,{})
        self.assertEqual(cell_state_response(c.network,'FW_E',0),{})

    def test_invalid_local_cells_fail_before_runtime(self):
        for index in ('-1','01','3',1,True,'1.0','x'):
            c=self.cfg();c.network.freeway_segment_params={'FW_E':[{}, {}, {}]}
            s=self.spec();s['FW_E']['cell_overrides']={index:{'congested_nu_multiplier':2.}}
            with self.subTest(index=index),self.assertRaises(ValueError):configure_state_response(c,{'freeway':{'state_response':s}})
        c=self.cfg();s=self.spec();s['FW_E']['cell_overrides']={'0':{'congested_nu_multiplier':2.}}
        with self.assertRaises(ValueError):configure_state_response(c,{'freeway':{'state_response':s}})

    def test_recovery_changes_relaxation_without_rescaling_pressure(self):
        base=self.spec()['FW_E'];s={**base,'recovery_relaxation':{'acceleration_sec':12.}}
        tau,nu=state_response_coefficients(base,40,70,35,20,27,1.,35)
        rt,rn=state_response_coefficients(s,40,70,35,20,27,1.,35)
        self.assertEqual(rt,12/3600)
        self.assertAlmostEqual(rn/rt,nu/tau)
        # Full unclipped METANET increment: only relaxation changes.
        step=1/3600;length=.5;kappa=17;speed=40;up=50;rho=35;down=20;desired=70
        def update(t,n):
            return speed+step/t*(desired-speed)+step/length*speed*(up-speed)-step*n/(t*length)*(down-rho)/(rho+kappa)
        self.assertAlmostEqual(update(rt,rn)-update(tau,nu),step*(desired-speed)*(1/rt-1/tau))

    def test_recovery_gate_and_equilibrium(self):
        base=self.spec()['FW_E'];s={**base,'recovery_relaxation':{'acceleration_sec':12.}}
        for speed,desired,rho,down in [(70,40,35,20),(50,50,10,5),(40,70,20,25),(40,70,35,27)]:
            self.assertEqual(state_response_coefficients(s,speed,desired,rho,down,27,1.,35),
                             state_response_coefficients(base,speed,desired,rho,down,27,1.,35))
        # Equality at the zero-gradient outlet is eligible only below critical.
        self.assertEqual(state_response_coefficients(s,40,70,20,20,27,1.,35)[0],12/3600)
        same={**base,'recovery_relaxation':{'acceleration_sec':24.}}
        self.assertEqual(state_response_coefficients(same,40,70,35,20,27,1.,35),
                         state_response_coefficients(base,40,70,35,20,27,1.,35))

    def test_local_recovery_config_copy_and_validation(self):
        c=self.cfg();c.network.freeway_segment_params={'FW_E':[{},{}]}
        s=self.spec();s['FW_E']['cell_overrides']={'1':{'recovery_relaxation':{'acceleration_sec':12.}}}
        configure_state_response(c,{'freeway':{'state_response':s}})
        worker=pickle.loads(pickle.dumps(c))
        self.assertNotIn('recovery_relaxation',cell_state_response(worker.network,'FW_E',0))
        self.assertEqual(cell_state_response(worker.network,'FW_E',1)['recovery_relaxation'],{'acceleration_sec':12.})
        for bad in [0,9,float('nan'),True]:
            s['FW_E']['cell_overrides']['1']['recovery_relaxation']['acceleration_sec']=bad
            with self.subTest(bad=bad),self.assertRaises(ValueError):configure_state_response(c,{'freeway':{'state_response':s}})

    def test_recovery_speed_ceiling_excludes_fast_and_boundary_states(self):
        base=self.spec()['FW_E'];s={**base,'recovery_relaxation':{'acceleration_sec':12.,'speed_ceiling_kmh':60.}}
        for speed in (60,70,100):
            self.assertEqual(state_response_coefficients(s,speed,120,25,20,27,1,35),
                             state_response_coefficients(base,speed,120,25,20,27,1,35))
        self.assertEqual(state_response_coefficients(s,59,120,25,20,27,1,35)[0],12/3600)
        c=self.cfg();configure_state_response(c,{'freeway':{'state_response':{'FW_E':s}}})
        for invalid in (0,-1,True,float('nan')):
            s['recovery_relaxation']['speed_ceiling_kmh']=invalid
            with self.assertRaises(ValueError):configure_state_response(c,{'freeway':{'state_response':{'FW_E':s}}})

if __name__=='__main__':unittest.main()
