from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import pickle,unittest
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_head326 import candidate as c

HERE=Path(__file__).resolve().parent
def fixture():return pickle.loads((HERE.parent/'citysplit287/forecast2400/initial.pickle').read_bytes())[:2]

class Head(unittest.TestCase):
    def test_state_routes_and_other_capacities_unchanged(self):
        cfg,state=fixture();raw=pickle.dumps(state);routes=deepcopy(cfg.network.control_area_routes)
        old=dict(cfg.network.movement_capacity_by_movement_veh_h);c.install(cfg)
        self.assertEqual(raw,pickle.dumps(state));self.assertEqual(routes,cfg.network.control_area_routes)
        self.assertEqual({m for m,v in old.items() if v!=cfg.network.movement_capacity_by_movement_veh_h[m]},set(c.MEMBERS))

    def test_route_error_rejected_before_mutation(self):
        cfg,_=fixture();caps=dict(cfg.network.movement_capacity_by_movement_veh_h)
        cfg.network.control_area_routes['movement:'+c.T]['physical_turns'][0]['connector']='wrong'
        with self.assertRaisesRegex(ValueError,'Route changed'):c.install(cfg)
        self.assertEqual(caps,cfg.network.movement_capacity_by_movement_veh_h)

    def test_member_and_total_budget_no_duplicate_after_debit(self):
        from evaluation.controllers import head_service_resources as head
        from src.models import urban_queue_model as uqm
        cfg,_=fixture();c.install(cfg);dt=cfg.simulation.T_u_h
        with patch.object(uqm,'_phase_green_fraction',return_value=1.):ctx=head.regular_context(cfg,None,240)
        receivers=cfg.network.regular_alias_pool['groups'][c.GROUP]['receivers']
        requests={receivers[m]:{m:min(100.,c.CAPS[m]*dt)} for m in c.MEMBERS}
        by,none=head.regular_cross_receiver_requests(cfg,requests,{},dict.fromkeys(c.MEMBERS,100.),ctx)
        result={m:v for rows in by.values() for m,v in rows.items()}
        self.assertLessEqual(sum(result.values()),4200.*dt+1e-8)
        self.assertLessEqual(result[c.R],1400.*dt+1e-8)
        # Rejection at the right receiver must not be donated within this batch.
        reserved_through=result[c.T];result[c.R]=0.
        accepted=head.regular_batch(cfg,result,ctx)
        self.assertEqual(accepted[c.T],reserved_through)
        for m,v in accepted.items():head.regular_accepted(m,v,ctx)
        self.assertAlmostEqual(ctx[1][c.GROUP],sum(accepted.values()))

    def test_single_right_cannot_take_three_heads_and_red_blocks(self):
        from evaluation.controllers import head_service_resources as head
        from src.models import urban_queue_model as uqm
        cfg,_=fixture();c.install(cfg);dt=cfg.simulation.T_u_h
        receivers=cfg.network.regular_alias_pool['groups'][c.GROUP]['receivers']
        for green in (0.,1.):
            with patch.object(uqm,'_phase_green_fraction',return_value=green):ctx=head.regular_context(cfg,None,240)
            requests={receivers[m]:{m:(1400.*dt*green if m==c.R else 0.)} for m in c.MEMBERS}
            by,_=head.regular_cross_receiver_requests(cfg,requests,{}, {c.T:0.,c.R:100.},ctx)
            self.assertAlmostEqual(sum(v for rows in by.values() for v in rows.values()),1400.*dt*green)

    def test_local_global_equal_and_context_restored(self):
        from evaluation.controllers import local_signal_service as pool
        from src.controllers.wu_faithful_follower import WuFaithfulFollower
        original=pool._model_view;cfg,_=fixture();f=WuFaithfulFollower(cfg)
        others={k:v for k,v in f._local_models.items() if k!='SC12'}
        with c.enabled():
            c.install(cfg);c.refresh_local(f,cfg)
            self.assertTrue(all(f._local_models[k] is v for k,v in others.items()))
            self.assertEqual({m:f._local_models['SC12'].cap_flow_of[m] for m in c.MEMBERS},c.CAPS)
            f._local_models['SC12'].cap_flow_of[c.R]=4200.
            with self.assertRaisesRegex(ValueError,'Stale'):pool._model_view(f._local_models['SC12'])
        self.assertIs(original,pool._model_view)

    def test_duplicate_rejected(self):
        cfg,_=fixture();c.install(cfg)
        with self.assertRaisesRegex(ValueError,'Duplicate'):c.install(cfg)

if __name__=='__main__':unittest.main()
