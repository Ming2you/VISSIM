"""A single lane cannot spend its service again at each downstream receiver."""
import copy,importlib.util,json,sys,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
H=ROOT/'diagnostics/repin_v3c3_review_20261001/urban_rm269'
spec=importlib.util.spec_from_file_location('sc16_candidate',H/'sc16_supply/candidate.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
from evaluation.controllers import head_service_resources as hs,local_signal_service as pool
from src.models.urban_queue_model import _allocate_receiving_counts
class SharedLaneTest(unittest.TestCase):
    def setUp(self):
        self.cfg=NS(network=NS(**json.loads((H/'sc1_supply/forecast2400/network.json').read_bytes())),simulation=NS(T_u_h=1/3600),urban_follower=NS(receiving_space_rule='proportional'))
        self.before=copy.deepcopy(vars(self.cfg.network));c.install(self.cfg,2400);c.validate_turns(self.cfg.network)
        n=self.cfg.network;n.local_service_pool['groups'][c.GROUP]=copy.deepcopy(n.regular_alias_pool['groups'][c.GROUP]);n.local_service_pool['group_of'].update({m:c.GROUP for m in c.MEMBERS})
        self.members=list(c.MEMBERS);self.ready=dict(zip(self.members,[20.,10.,10.]))
    def global_service(self,space=None,green=1.):
        n=self.cfg.network
        with patch('src.models.urban_queue_model._phase_green_fraction',return_value=green):ctx=hs.regular_context(self.cfg,None,2400)
        budget=c.evidence()*green/3600
        requests={c.MEMBERS[m][2]:{m:min(self.ready[m],budget)} for m in self.members}
        requests,none=hs.regular_cross_receiver_requests(self.cfg,requests,{},self.ready,ctx)
        self.assertEqual(none,{})
        actual={}
        for receiver,rows in requests.items():
            rows=hs.regular_batch(self.cfg,rows,ctx)
            actual.update(_allocate_receiving_counts('proportional',rows,(space or {}).get(receiver,100.)))
        for m,v in actual.items():hs.regular_accepted(m,v,ctx)
        return actual,ctx
    def test_one_budget_across_three_receivers_and_queue_proportions(self):
        actual,ctx=self.global_service();b=c.evidence()/3600
        self.assertAlmostEqual(sum(actual.values()),b)
        self.assertAlmostEqual(actual[self.members[0]],b*.5)
        self.assertAlmostEqual(actual[self.members[1]],b*.25)
        with self.assertRaisesRegex(ValueError,'exceeds'):hs.regular_accepted(self.members[0],.01,ctx)
    def test_blocked_direction_does_not_donate_its_head_share(self):
        actual,_=self.global_service({c.MEMBERS[self.members[0]][2]:0})
        self.assertEqual(actual[self.members[0]],0);self.assertAlmostEqual(sum(actual.values()),c.evidence()/7200)
    def test_red_and_sole_ready(self):
        self.assertEqual(sum(self.global_service(green=0)[0].values()),0)
        self.ready={m:10. if i==1 else 0. for i,m in enumerate(self.members)}
        self.assertAlmostEqual(self.global_service()[0][self.members[1]],c.evidence()/3600)
    def test_existing_single_receiver_path_is_unchanged(self):
        by={'a':{'m':1.}};none={};groups={'old':dict(members=['m'],receiver='a')}
        a,b=pool.limit_multi_receiver_heads(by,none,{'m':100},groups,{'old':.1},{})
        self.assertIs(a,by);self.assertIs(b,none)
    def test_actual_three_turn_debit_roundoff_and_missing_mass(self):
        values=[0.1853185689390492,0.18690832237794738,0.09368219959209433]
        actual=dict(zip(self.members,values));ctx=({c.GROUP:1.},{},dict.fromkeys(self.members,c.GROUP))
        for m,v in actual.items():hs.regular_accepted(m,v,ctx)
        self.assertEqual(hs.regular_evidence(c.GROUP,actual,ctx),{'movement:'+m:v for m,v in actual.items()})
        for defect in (1e-5,float('nan'),float('inf')):
            bad=copy.deepcopy(ctx);bad[1][c.GROUP]+=defect
            with self.assertRaisesRegex(ValueError,'accepted debit'):hs.regular_evidence(c.GROUP,actual,bad)
        missing=dict(actual);missing.pop(self.members[0])
        with self.assertRaisesRegex(ValueError,'accepted debit'):hs.regular_evidence(c.GROUP,missing,ctx)
    def test_incomplete_request_and_receiver_contract_rejected(self):
        with self.assertRaisesRegex(ValueError,'Missing shared-lane request'):pool.limit_multi_receiver_heads({}, {},self.ready,self.cfg.network.regular_alias_pool['groups'],{c.GROUP:1.},{})
        self.cfg.network.urban_movements[self.members[0]]['receiving_link']='wrong'
        with self.assertRaisesRegex(ValueError,'receiver'):self.global_service()
    def test_local_cost_matches_global_departures_with_receiver_blockage(self):
        n=self.cfg.network
        model=NS(cfg=self.cfg,movements=self.members,signal='SC16',has_ramps=False,receiving_of={m:c.MEMBERS[m][2] for m in self.members},phase_of=dict.fromkeys(self.members,'p3'),origin_of=dict.fromkeys(self.members,'in_SC16_E'),cap_flow_of={m:n.movement_capacity_by_movement_veh_h[m] for m in self.members},receiving_space_rule='proportional')
        for g in (0.,.3,1.):
            spaces={v[2]:100. for v in c.MEMBERS.values()};spaces[c.MEMBERS[self.members[0]][2]]=0
            actual,_=self.global_service(spaces,g)
            cost=pool.rollout_shared_plain(model,self.ready,{},dict.fromkeys(self.members,[g]),spaces,1,1/3600)
            self.assertAlmostEqual(cost,(sum(self.ready.values())-sum(actual.values()))/3600)
    def test_rate_uses_only_past_supported_head_not_future_targets(self):
        d=json.loads((H/'sc16_supply/assessment.json').read_bytes());expected=3600*41/88
        self.assertAlmostEqual(c.supported_rate(d),expected);d['arms']={'unknown':'future ignored'}
        self.assertAlmostEqual(c.supported_rate(d),expected)
        d['past']['2400']['SC16_E']['rows'][0]['unverified_sec']=1
        with self.assertRaisesRegex(ValueError,'Unqualified'):c.supported_rate(d)
    def test_only_three_caps_change_and_install_before_routes(self):
        cfg=NS(network=NS(**copy.deepcopy(self.before)));del cfg.network.control_area_routes
        c.install(cfg,3300)
        changed={m for m,v in cfg.network.movement_capacity_by_movement_veh_h.items() if v!=self.before['movement_capacity_by_movement_veh_h'][m]}
        self.assertEqual(changed,set(c.MEMBERS));saved=copy.deepcopy(vars(cfg.network));c.install(cfg,3300);self.assertEqual(saved,vars(cfg.network))
if __name__=='__main__':unittest.main(verbosity=2)
