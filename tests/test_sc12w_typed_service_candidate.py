"""Past evidence and single physical budget for the bounded SC12W candidate."""
import copy,importlib.util,json,sys,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
H=ROOT/'diagnostics/repin_v3c3_review_20261001/urban_rm269'
spec=importlib.util.spec_from_file_location('sc12w_candidate',H/'sc12w_service/candidate.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
from evaluation.controllers import head_service_resources as hs,local_signal_service as pool
from src.models.urban_queue_model import _allocate_receiving_counts

class TypedServiceTest(unittest.TestCase):
    def setUp(self):
        self.cfg=NS(network=NS(**json.loads((H/'sc1_supply/forecast2400/network.json').read_bytes())),
            simulation=NS(T_u_h=1/3600),urban_follower=NS(receiving_space_rule='proportional'))
        self.old=copy.deepcopy(self.cfg.network.movement_capacity_by_movement_veh_h)
        self.doc=json.loads((H/'sc12w_service/typed_support_v3.json').read_bytes())
    def context(self,green=1):
        with patch('src.models.urban_queue_model._phase_green_fraction',return_value=green):
            return hs.regular_context(self.cfg,None,2400)
    def test_fixed_past_estimator_and_future_transition_rejection(self):
        self.assertEqual(c.supported_rate(self.doc),960.)
        w=next(w for r in self.doc['rows'] for w in r['typed_witnesses'] if w['proof']=='observed_adjacent_source_to_connector_frames')
        w['post_connector']['time_sec']=2400.1
        with self.assertRaisesRegex(ValueError,'transition'):c.supported_rate(self.doc)
    def test_unknown_destination_not_promoted(self):
        w=next(w for r in self.doc['rows'] for w in r['typed_witnesses'] if w['proof']=='active_static_route_and_next_link')
        w['prior']['next_link']='10241'
        with self.assertRaisesRegex(ValueError,'route'):c.supported_rate(self.doc)
    def test_only_reviewed_aliases_change_and_idempotence(self):
        c.install(self.cfg,2400);new=self.cfg.network.movement_capacity_by_movement_veh_h
        self.assertEqual({m for m in new if new[m]!=self.old[m]},set(c.MEMBERS))
        saved=copy.deepcopy(vars(self.cfg.network));c.install(self.cfg,2400)
        self.assertEqual(saved,vars(self.cfg.network))
    def test_both_ready_share_one_budget(self):
        c.install(self.cfg,2400);ctx=self.context();out=hs.regular_batch(self.cfg,dict.fromkeys(c.MEMBERS,20.),ctx)
        self.assertAlmostEqual(sum(out.values()),960/3600)
        for m,v in out.items():hs.regular_accepted(m,v,ctx)
        with self.assertRaisesRegex(ValueError,'exceeds'):hs.regular_accepted(c.MEMBERS[0],.01,ctx)
    def test_sole_ready_can_borrow_but_red_cannot_serve(self):
        c.install(self.cfg,2400)
        for g,expected in ((1,960/3600),(0,0)):
            out=hs.regular_batch(self.cfg,{c.MEMBERS[0]:8.,c.MEMBERS[1]:0.},self.context(g))
            self.assertAlmostEqual(sum(out.values()),expected)
    def test_receiver_full_cannot_be_overridden(self):
        c.install(self.cfg,2400);ctx=self.context();req=hs.regular_batch(self.cfg,dict.fromkeys(c.MEMBERS,20.),ctx)
        for space in (0.,.1):
            out=_allocate_receiving_counts('proportional',req,space)
            self.assertAlmostEqual(sum(out.values()),space)
    def test_wrong_phase_and_missing_receiver_rejected(self):
        self.cfg.network.urban_movements[c.MEMBERS[0]]['phase']='SC12_p3'
        with self.assertRaisesRegex(ValueError,'binding'):c.install(self.cfg,2400)
        self.cfg.network.urban_movements[c.MEMBERS[0]]['phase']='SC12_p4'
        del self.cfg.network.urban_link_storage_veh['SC12_to_SC6']
        with self.assertRaisesRegex(ValueError,'receiver'):c.install(self.cfg,2400)
    def test_local_and_global_budget_match(self):
        c.install(self.cfg,2400);net=self.cfg.network
        net.local_service_pool['groups'][c.GROUP]=copy.deepcopy(net.regular_alias_pool['groups'][c.GROUP])
        net.local_service_pool['group_of'].update({m:c.GROUP for m in c.MEMBERS})
        model=NS(cfg=self.cfg,movements=list(c.MEMBERS),signal='SC12',has_ramps=False,
            receiving_of=dict.fromkeys(c.MEMBERS,'SC12_to_SC6'),phase_of=dict.fromkeys(c.MEMBERS,'p4'),
            origin_of={m:net.urban_movements[m]['origin'] for m in c.MEMBERS},
            cap_flow_of={m:net.movement_capacity_by_movement_veh_h[m] for m in c.MEMBERS},receiving_space_rule='proportional')
        q={c.MEMBERS[0]:10.,c.MEMBERS[1]:0.};dt=1/3600
        value=pool.rollout_shared_plain(model,q,{},dict.fromkeys(c.MEMBERS,[1.]),{'SC12_to_SC6':100},1,dt)
        self.assertAlmostEqual(value,(10-960*dt)*dt)
    def test_install_before_late_routes_then_validate_canonical_turns(self):
        routes=self.cfg.network.control_area_routes
        del self.cfg.network.control_area_routes
        c.install(self.cfg,2400)
        self.cfg.network.control_area_routes=routes
        c.validate_turns(self.cfg.network)
        routes['movement:'+c.MEMBERS[0]]['physical_turns'][0]['connector']='10241'
        with self.assertRaisesRegex(ValueError,'Canonical turn'):c.validate_turns(self.cfg.network)

if __name__=='__main__':unittest.main(verbosity=2)
