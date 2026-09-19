"""Regime boundary, configuration isolation and serialization contracts."""
import copy
import pickle
from types import SimpleNamespace as NS
import unittest
from evaluation.controllers.freeway_fd import configure_state_response, state_response_coefficients, FDParameters

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

if __name__=='__main__':unittest.main()
