"""Tests for present-state lane exchange, not a bonus for operating a lever."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from evaluation.controllers.physical_lane_groups import StateDependentExchange
import copy
import unittest


def example():
    return {'schema':'state-dependent-exchange/v1',
        'feature_names':['donor_speed','recipient_minus_donor_speed','donor_density','recipient_density'],
        'center':[0.]*4,'scale':[100.]*4,'lower':[0.,-150.,0.,0.],'upper':[150.,150.,150.,150.],
        'coefficients':[0.,1.,0.,-1.],
        'log_intercepts':{'0:0:1':-4.,'0:1:0':-4.},'max_rate_per_sec':.5}


class ExchangeTests(unittest.TestCase):
    def test_faster_neighbor_increases_request_without_changing_inventory(self):
        closure=StateDependentExchange(example(),[[1.,1.]])
        n=[[10.,10.]];before=copy.deepcopy(n)
        equal=closure.rates(n,[[60.,60.]],[.5],[[1.,1.]])[0][0][1]
        faster=closure.rates(n,[[60.,90.]],[.5],[[1.,1.]])[0][0][1]
        self.assertGreater(faster,equal)
        self.assertEqual(n,before)

    def test_dense_receiver_reduces_request(self):
        closure=StateDependentExchange(example(),[[1.,1.]])
        a=closure.rates([[10.,10.]],[[60.,60.]],[.5],[[1.,1.]])[0][0][1]
        b=closure.rates([[10.,50.]],[[60.,60.]],[.5],[[1.,1.]])[0][0][1]
        self.assertLess(b,a)

    def test_no_teleporting_or_nonfinite_rates(self):
        spec=example();spec['log_intercepts'].update({'0:1:2':-4.,'0:2:1':-4.})
        closure=StateDependentExchange(spec,[[1.,1.,2.]])
        rates=closure.rates([[10.,10.,10.]],[[0.,300.,0.]],[.5],[[1.,1.,2.]])
        self.assertEqual(rates[0][0][2],0.)
        self.assertEqual(rates[0][1][1],0.)
        self.assertTrue(all(0<=x<=.5 for row in rates[0] for x in row))
        self.assertGreater(closure.clipped_feature_values,0)

    def test_missing_address_or_wrong_schema_is_rejected(self):
        spec=example();del spec['log_intercepts']['0:1:0']
        with self.assertRaises(ValueError):StateDependentExchange(spec,[[1.,1.]])
        spec=example();spec['schema']='unverified'
        with self.assertRaises(ValueError):StateDependentExchange(spec,[[1.,1.]])

    def test_physical_hazard_matches_fitted_feature_expression(self):
        import json
        import math
        here=Path(__file__).resolve().parent
        model=json.loads((here/'fit_v1/model.json').read_text())
        lane=json.loads((here.parent/'lane_group_response_20260919/observations_v1/s23.json').read_text())
        widths=lane['geometry']['widths']
        stocks=[[20.*w for w in ws] for ws in widths]
        speeds=[[60.+10*g for g in range(len(ws))] for ws in widths]
        lengths=[.5]*len(widths)
        closure=StateDependentExchange(model,widths)
        result=closure.rates(stocks,speeds,lengths,widths)
        raw=[60.,10.,40.,40.]
        bounded=[min(b,max(a,x)) for x,a,b in zip(raw,model['lower'],model['upper'])]
        eta=model['log_intercepts']['7:0:1']+sum(beta*(x-c)/s for beta,x,c,s in
            zip(model['coefficients'],bounded,model['center'],model['scale']))
        self.assertAlmostEqual(result[7][0][1],min(model['max_rate_per_sec'],math.exp(eta)),places=14)


if __name__=='__main__':unittest.main()
