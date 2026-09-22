from pathlib import Path
from types import SimpleNamespace as NS
import copy
import pickle
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import sdmpc_prediction_cache as cache
from evaluation.controllers import sdmpc_tangent_reverse as ad


def config(enabled=True):
    return NS(network=NS(sdmpc_options=dict(prediction_cache=True,flow_update_cache=enabled)))


class FlowUpdateTests(unittest.TestCase):
    def test_only_the_mutated_ramp_dictionary_is_copied(self):
        trace=ad.Trace([1.]);rate=ad.Dual(2.,{0:1.},trace)
        control=NS(ramp_metering={'r':rate},variable_speed_limits={'road':80.},
                   diagnostics={'future':[{'green':30.}]})
        with cache.scope(config()):
            query=cache.ramp_query_control(control)
            self.assertIsNot(query,control)
            self.assertIsNot(query.ramp_metering,control.ramp_metering)
            self.assertIs(query.ramp_metering['r'],rate)
            self.assertIs(query.variable_speed_limits,control.variable_speed_limits)
            self.assertIs(query.diagnostics,control.diagnostics)
            query.ramp_metering['r']=10.
            self.assertIs(control.ramp_metering['r'],rate)
        self.assertEqual(trace.jacobian([rate],1)[0,0],1.)
        for enabled in (False,True):
            scope=cache.scope(config(False)) if not enabled else __import__('contextlib').nullcontext()
            with scope:
                independent=cache.ramp_query_control(control)
            self.assertIsNot(independent.diagnostics,control.diagnostics)

    def test_real_release_query_is_unchanged_and_does_not_modify_shared_inputs(self):
        from src.models import metanet
        request=pickle.loads((ROOT/'diagnostics/sdmpc_trial_20260922/trial_h3_v1/request.pickle').read_bytes())
        follower,state,reference,forecast=request['owned']
        control=request['action']
        before=pickle.dumps(control,protocol=5)
        # The actual read-only consumer is evaluated with both copy strategies.
        demand=forecast.steps[0] if hasattr(forecast,'steps') else forecast[0]
        cfg=follower.cfg
        results=[]
        for enabled in (False,True):
            with cache.scope(config(enabled)):
                query=cache.ramp_query_control(control)
            query.ramp_metering.update(cfg.network.ramp_capacity_veh_h)
            results.append(metanet.compute_ramp_release_flows(state,query,demand,cfg,include_current_arrivals=False))
        self.assertEqual(results[0],results[1])
        self.assertEqual(pickle.dumps(control,protocol=5),before)

    def test_option_is_explicit_and_requires_query_scope(self):
        from evaluation.controllers import sdmpc
        cfg=pickle.loads((ROOT/'diagnostics/sdmpc_trial_20260922/trial_h3_v1/request.pickle').read_bytes())['owned'][0].cfg
        tuning={'adapter':{'sdmpc':'proxlinear-v1'}}
        self.assertNotIn('flow_update_cache',sdmpc.configure(tuning,copy.deepcopy(cfg)))
        tuning['adapter']['sdmpc_flow_update_cache']=True
        with self.assertRaises(ValueError):sdmpc.configure(tuning,copy.deepcopy(cfg))
        tuning['adapter']['sdmpc_prediction_cache']=True
        self.assertTrue(sdmpc.configure(tuning,copy.deepcopy(cfg))['flow_update_cache'])
        tuning['adapter']['sdmpc_flow_update_cache']=1
        with self.assertRaises(ValueError):sdmpc.configure(tuning,copy.deepcopy(cfg))


if __name__=='__main__':unittest.main()
