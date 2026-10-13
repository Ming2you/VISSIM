"""Aggregate route metadata conservation, initial-label coexistence and tangent."""
from copy import deepcopy
import pickle,unittest
from types import SimpleNamespace
from pathlib import Path
import candidate
from evaluation.controllers.physical_ramp_branches import split_tagged_arrival as original

HERE=Path(__file__).resolve().parent

class RouteTagTests(unittest.TestCase):
    def setUp(self):
        self.cfg,self.initial,_=pickle.loads((HERE.parent/"citysplit287/forecast2400/initial.pickle").read_bytes())
        self.d=candidate.document()
        self.routing=[(m,self.cfg.network.urban_movements[m]["beta"]) for m in self.d["movements"].values()]
        self.state=SimpleNamespace(urban_arrival_buffer={candidate.TARGET:{250:20.}},
            gate_initial_route_tags={},shared_approach_state={})

    def test_two_sources_keep_categories_and_parent_count(self):
        parent=deepcopy(self.state.urban_arrival_buffer)
        candidate.add_tag(self.state,"1099",250,6.,self.d)
        candidate.add_tag(self.state,"1100",250,10.,self.d)
        candidate.verify_pending(self.state)
        self.assertEqual(parent,self.state.urban_arrival_buffer)
        got=dict(candidate.split(self.state,self.cfg,candidate.TARGET,250,20.,self.routing,self.d,original))
        self.assertAlmostEqual(sum(got.values()),20.)
        for kind,m in self.d["movements"].items():
            expected=4*self.d["base_beta"][kind]+sum(n*self.d["sources"][src]["effective_route_shares_if_prior_used"][kind] for src,n in (("1099",6),("1100",10)))
            self.assertAlmostEqual(got[m],expected)
        self.state.urban_arrival_buffer[candidate.TARGET].pop(250)
        candidate.verify_pending(self.state)
        self.assertFalse(getattr(self.state,candidate.ATTR)["pending"])

    def test_existing_initial_tags_are_not_redistributed(self):
        left=self.d["movements"]["left"]
        self.state.gate_initial_route_tags={candidate.TARGET:{250:{left:4.}}}
        candidate.add_tag(self.state,"1100",250,16.,self.d)
        got=dict(candidate.split(self.state,self.cfg,candidate.TARGET,250,20.,self.routing,self.d,original))
        self.assertAlmostEqual(got[left],4+16*self.d["sources"]["1100"]["effective_route_shares_if_prior_used"]["left"])
        self.assertEqual(self.state.gate_initial_route_tags[candidate.TARGET],{})

    def test_rejects_oversized_tags_and_future_support(self):
        candidate.add_tag(self.state,"1100",250,21.,self.d)
        with self.assertRaisesRegex(ValueError,"exceed"):candidate.verify_pending(self.state)
        before=pickle.dumps(self.initial,protocol=5)
        with self.assertRaisesRegex(ValueError,"precede"):candidate.validate(self.cfg,2300,self.d)
        self.assertEqual(before,pickle.dumps(self.initial,protocol=5))

    def test_route_split_preserves_active_derivative(self):
        from evaluation.controllers.sdmpc_dual import Trace,derivative,primal
        trace=Trace([1.],track_stencils=False)
        n=trace.scalar(10.,{0:1.})
        self.state.urban_arrival_buffer={candidate.TARGET:{250:n}}
        candidate.add_tag(self.state,"1100",250,n,self.d)
        got=dict(candidate.split(self.state,self.cfg,candidate.TARGET,250,n,self.routing,self.d,original))
        self.assertAlmostEqual(primal(sum(got.values())),10.)
        self.assertAlmostEqual(derivative(sum(got.values()))[0],1.)
        for kind,m in self.d["movements"].items():
            self.assertAlmostEqual(derivative(got[m])[0],self.d["sources"]["1100"]["effective_route_shares_if_prior_used"][kind])

if __name__=="__main__":unittest.main()

