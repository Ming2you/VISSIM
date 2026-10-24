"""Physical alias sharing: preserve the envelope, stocks and receiver constraints."""
import copy,json,sys,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import regular_alias_service as alias
from evaluation.controllers import head_service_resources as hs,local_signal_service as pool
from src.models.urban_queue_model import _allocate_receiving_counts
H=ROOT/'diagnostics/repin_v3c3_review_20261001/urban_rm269'
class AliasPoolTest(unittest.TestCase):
    def setUp(self):
        net=json.loads((H/'native_beta/forecast2400_checked/network.json').read_bytes())
        self.cfg=NS(network=NS(**net),simulation=NS(T_u_h=1/3600),urban_follower=NS(receiving_space_rule='proportional'))
        self.tuning=json.loads((H/'sc1_supply/config.json').read_bytes());self.tuning['execution']['native_signal_record']=False
        self.raw={'network_path':str(ROOT/json.loads((H/'sc1_supply/contract.json').read_bytes())['network']['path'])}
        self.old=copy.deepcopy(self.cfg.network.movement_capacity_by_movement_veh_h)
    def configure(self):return alias.configure(self.cfg,self.tuning,self.raw)
    def context(self,green=1):
        with patch('src.models.urban_queue_model._phase_green_fraction',return_value=green):
            return hs.regular_context(self.cfg,None,2400)
    def test_preserve_aggregate_and_other_rates(self):
        self.configure();new=self.cfg.network.movement_capacity_by_movement_veh_h
        total=sum(self.old[m] for m in alias.MEMBERS)
        self.assertEqual([m for m in new if new[m]!=self.old[m]],list(alias.MEMBERS))
        for m in alias.MEMBERS:self.assertEqual(new[m],total)
        self.assertEqual(alias.view(self.cfg)['service_veh_h'],total)
    def test_idempotent_and_disable_restores_owned_rates(self):
        self.configure();first=copy.deepcopy(vars(self.cfg.network));self.configure()
        self.assertEqual(vars(self.cfg.network),first)
        t=copy.deepcopy(self.tuning);del t['urban']['capacity']['regular_alias_pool']
        alias.configure(self.cfg,t,self.raw)
        self.assertIsNone(alias.view(self.cfg));self.assertEqual(self.cfg.network.movement_capacity_by_movement_veh_h,self.old)
    def test_wrong_phase_rejected(self):
        self.cfg.network.urban_movements[alias.MEMBERS[1]]['phase']='SC1_p2'
        with self.assertRaisesRegex(ValueError,'source, phase'):self.configure()
    def test_extra_same_connector_consumer_rejected(self):
        self.cfg.network.urban_movements['unknown']=copy.deepcopy(self.cfg.network.urban_movements[alias.MEMBERS[0]])
        with self.assertRaisesRegex(ValueError,'Unknown'):self.configure()
    def test_wrong_network_rejected(self):
        self.raw['network_path']=str(H/'sc1_supply/contract.json')
        with self.assertRaisesRegex(ValueError,'networks differ'):self.configure()
    def test_missing_receiver_rejected(self):
        del self.cfg.network.urban_link_storage_veh['SC1_to_SC101']
        with self.assertRaisesRegex(ValueError,'finite receiver'):self.configure()
    def test_both_ready_cannot_double_capacity(self):
        self.configure();ctx=self.context();requests=dict.fromkeys(alias.MEMBERS,9.)
        result=hs.regular_batch(self.cfg,requests,ctx);budget=ctx[0][alias.GROUP]
        self.assertAlmostEqual(sum(result.values()),budget)
        for m,v in result.items():hs.regular_accepted(m,v,ctx)
        self.assertAlmostEqual(ctx[1][alias.GROUP],budget)
        with self.assertRaisesRegex(ValueError,'exceeds'):hs.regular_accepted(alias.MEMBERS[0],.1,ctx)
    def test_single_ready_alias_uses_spare_head_capacity(self):
        self.configure();ctx=self.context()
        values=hs.regular_batch(self.cfg,{alias.MEMBERS[0]:0.,alias.MEMBERS[1]:10.},ctx)
        self.assertEqual(values[alias.MEMBERS[0]],0.)
        self.assertAlmostEqual(values[alias.MEMBERS[1]],sum(self.old[m] for m in alias.MEMBERS)/3600)
    def test_red_and_empty_cannot_create_service(self):
        self.configure()
        for green,q in ((0.,10.),(1.,0.)):
            ctx=self.context(green);v=hs.regular_batch(self.cfg,dict.fromkeys(alias.MEMBERS,q),ctx)
            self.assertEqual(sum(v.values()),0.)
    def test_receiver_remains_a_second_limit(self):
        self.configure();ctx=self.context()
        req=hs.regular_batch(self.cfg,dict.fromkeys(alias.MEMBERS,8.),ctx)
        actual=_allocate_receiving_counts('proportional',req,.2)
        self.assertAlmostEqual(sum(actual.values()),.2)
        for m,v in actual.items():hs.regular_accepted(m,v,ctx)
        self.assertAlmostEqual(ctx[1][alias.GROUP],.2)
    def model(self):
        self.configure();net=self.cfg.network
        alias.extend_local_pool(self.cfg)
        return NS(cfg=self.cfg,movements=list(alias.MEMBERS),signal='SC1',has_ramps=False,
            receiving_of=dict.fromkeys(alias.MEMBERS,'SC1_to_SC101'),
            phase_of=dict.fromkeys(alias.MEMBERS,'p1'),origin_of={m:net.urban_movements[m]['origin'] for m in alias.MEMBERS},
            cap_flow_of={m:net.movement_capacity_by_movement_veh_h[m] for m in alias.MEMBERS},receiving_space_rule='proportional')
    def test_local_plain_and_global_share_same_resource(self):
        model=self.model();dt=1/3600;q=dict.fromkeys(alias.MEMBERS,10.)
        ctx=self.context();req=hs.regular_batch(self.cfg,{m:min(q[m],model.cap_flow_of[m]*dt) for m in model.movements},ctx)
        expected=(sum(q.values())-sum(req.values()))*dt
        actual=pool.rollout_shared_plain(model,q,{},dict.fromkeys(model.movements,[1.]),{'SC1_to_SC101':100.},1,dt)
        self.assertAlmostEqual(actual,expected)
        average=pool.rollout_shared_average(model,q,{}, {'SC1_to_SC101':100.},{'p1':model.cfg.network.cycle_length},1,dt)
        self.assertAlmostEqual(average,expected)
    def test_local_receiver_held_profile_and_arrival_conservation(self):
        model=self.model();dt=1/3600;q=dict.fromkeys(alias.MEMBERS,0.)
        q[alias.MEMBERS[1]]=10.
        arrivals=dict.fromkeys(model.movements,[360.]);green=dict.fromkeys(model.movements,[1.])
        cost=pool.rollout_shared_plain(model,q,arrivals,green,{'SC1_to_SC101':100.},1,dt,{'SC1_to_SC101':[.05]})
        self.assertAlmostEqual(cost,(10.+.2-.05)*dt)
    def test_model_scope_excludes_other_signals_but_rejects_partial_pool(self):
        model=self.model()
        self.assertEqual(set(pool._model_view(model)['groups']),{alias.GROUP})
        model.movements=[alias.MEMBERS[0]]
        with self.assertRaisesRegex(ValueError,'complete physical pool'):pool._model_view(model)
    def test_actual_local_and_follower_entrypoints(self):
        from src.controllers import local_signal_plant as local,wu_faithful_follower as follower
        model=self.model();pool.install(self.cfg)
        q={alias.MEMBERS[0]:0.,alias.MEMBERS[1]:10.};green=dict.fromkeys(model.movements,[1.])
        expected=pool.rollout_shared_plain(model,q,{},green,{'SC1_to_SC101':100.},1,1/3600)
        for module in (local,follower):
            self.assertEqual(module.rollout_local_tts_phased(model,q,{},green,{'SC1_to_SC101':100.},1,1/3600),expected)
            self.assertEqual(module.rollout_local_tts(model,q,{}, {'SC1_to_SC101':100.},{'p1':model.cfg.network.cycle_length},1,1/3600),expected)
    def test_unpooled_entrypoint_keeps_original_result(self):
        from src.controllers import local_signal_plant as local
        model=self.model();pool.install(self.cfg)
        model.cfg.network.local_service_pool=None
        arguments=(model,dict.fromkeys(model.movements,10.),{},dict.fromkeys(model.movements,[1.]),{'SC1_to_SC101':100.},1,1/3600)
        self.assertEqual(local.rollout_local_tts_phased(*arguments),local.rollout_local_tts_phased.__wrapped__(*arguments))
if __name__=='__main__':unittest.main(verbosity=2)
