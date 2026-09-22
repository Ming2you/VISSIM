"""Exact ramp inventory reuse across phases, lane exchange and AD contexts."""
import copy
import math
from pathlib import Path
import pickle
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import sdmpc_prediction_cache as cache
from evaluation.controllers import physical_ramp_boundary as ramps
from evaluation.controllers import sdmpc_tangent_reverse as ad


def cfg(enabled=True):
    return NS(network=NS(sdmpc_options={'prediction_cache':True,'ramp_stock_cache':enabled}))


def ramp(lanes=False):
    spec=dict(connector_id='test',length_m=100.,head_position_m=50.,lanes=2 if lanes else 1,
        spacing_m=7.,travel_speed_kmh=36.,time_sec=0.,initial_cohorts=[(10.,36.,1),(60.,36.,1)])
    if lanes:
        return ramps.LaneResolvedRampBoundary(**spec,lane_arrival_shares=[.5,.5],
            lane_exchange_rates_per_sec={'prehead':[[0.,.1],[.1,0.]],'posthead':[[0.,.1],[.1,0.]]})
    return ramps.PhysicalRampBoundary(**spec)


def exact_stocks(r):
    x=dict(upstream_travelling_veh=math.fsum(n for _,n in r._upstream),head_ready_veh=r._head_ready,
        downstream_travelling_veh=math.fsum(n for _,n in r._downstream),merge_ready_veh=r._merge_ready)
    x['connector_veh']=math.fsum(x.values())
    return x


class RampStockCacheTests(unittest.TestCase):
    def test_every_mutator_snapshot_and_failure(self):
        histories=[]
        for enabled in (False,True):
            r=ramp();rows=[]
            def check():
                self.assertEqual(r._stocks(),exact_stocks(r))
                rows.append(pickle.dumps(vars(r),protocol=5))
            with cache.scope(cfg(enabled)):
                for i in range(20):
                    check()
                    ready=r.begin_interval(float(i),1.)['eligible_merge_veh'];check()
                    r.commit_merge(min(.2,ready));check()
                    r.apply_head_service(.15,mode='GREEN',green_sec=5.,posthead_capacity_veh=7.);check()
                    r.finish_interval(.1);check()
                    r.current_admission_space();r.admit_current(.05);check()
                r.cumulative_requested_veh+=1.
                with self.assertRaises(ValueError):r.snapshot()
                with self.assertRaises(ValueError):r.admit_current(1e9)
            histories.append(rows)
        self.assertEqual(*histories)

    def test_lane_exchange_receipts_and_all_physical_states_exact(self):
        histories=[]
        for enabled in (False,True):
            r=ramp(True);rows=[]
            with cache.scope(cfg(enabled)):
                for i in range(8):
                    r.snapshot()
                    receipt=r.advance_local_interval(start_sec=float(i),duration_sec=1.,cycle_sec=10.,
                        receiving_budget_veh=.3,service_veh=.2,mode='GREEN',green_sec=5.,
                        request_arrivals_veh=.1,allow_partial_cycle=True)
                    rows.append((receipt,pickle.dumps(vars(r),protocol=5)))
                    for b in r._lane_buffers:self.assertEqual(b._stocks(),exact_stocks(b))
            histories.append(rows)
        self.assertEqual(*histories)

    def test_copy_scope_and_result_isolation(self):
        r=ramp()
        with cache.scope(cfg()) as local:
            expected=r._stocks();r._stocks()['connector_veh']=-10.
            self.assertEqual(r._stocks(),expected)
            other=copy.deepcopy(r)
            self.assertNotIn((other,False),local.ramp_stocks)
            with cache.scope(cfg(False)):
                r.admit_current(.25)
            self.assertEqual(r._stocks(),exact_stocks(r))
            self.assertEqual(other._stocks(),expected)
        self.assertIsNone(cache.active())

    def test_primal_guard_cannot_poison_physical_derivatives(self):
        r=ramp();trace=ad.Trace([.1]);x=ad.Dual(1.,{0:1.},trace)
        r._upstream=[(2.,x)];r._downstream=[]
        with cache.scope(cfg()),patch.object(ramps,'fsum',ad.MathProxy.fsum),patch.object(ramps,'_number',lambda v,*a,**k:v):
            with patch.object(ad,'PRIMAL_GUARD',True):
                self.assertEqual(r._stocks()['connector_veh'].node,0)
            total=r._stocks()['connector_veh']
            self.assertGreater(total.node,0)
            np.testing.assert_array_equal(trace.jacobian([total],1),[[1.]])

    def test_fsum_is_not_replaced_by_an_incremental_total(self):
        r=ramp();r._upstream=[(2.,1e16),(3.,1.),(4.,1.)];r._downstream=[]
        with cache.scope(cfg()):
            self.assertEqual(r._stocks()['connector_veh'],1e16+2.)
            self.assertEqual(r._stocks(),exact_stocks(r))

    def test_option_default_prerequisite_and_boolean(self):
        from evaluation.controllers import sdmpc
        model=pickle.loads((ROOT/'diagnostics/sdmpc_audit_20260922/compact_h3_v4/request.pickle').read_bytes())['owned'][0].cfg
        tuning={'adapter':{'sdmpc':'proxlinear-v1'}}
        self.assertNotIn('ramp_stock_cache',sdmpc.configure(tuning,copy.deepcopy(model)))
        for flag in (True,1):
            tuning['adapter']['sdmpc_ramp_stock_cache']=flag
            with self.assertRaises(ValueError):sdmpc.configure(tuning,copy.deepcopy(model))
        tuning['adapter'].update(sdmpc_prediction_cache=True,sdmpc_ramp_stock_cache=True)
        self.assertTrue(sdmpc.configure(tuning,copy.deepcopy(model))['ramp_stock_cache'])


if __name__=='__main__':unittest.main()
