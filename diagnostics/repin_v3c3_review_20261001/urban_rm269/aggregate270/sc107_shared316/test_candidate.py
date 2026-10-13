from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import pickle,unittest
from candidate import install,refresh_local,MEMBERS,GROUP

HERE=Path(__file__).resolve().parent


def fixture():
    return pickle.loads((HERE.parent/'citysplit287/forecast2400/initial.pickle').read_bytes())[:2]


class SharedHead(unittest.TestCase):
    def test_total_capacity_and_initial_state_preserved(self):
        cfg,state=fixture();before=pickle.dumps(state);caps=dict(cfg.network.movement_capacity_by_movement_veh_h)
        movements=deepcopy(cfg.network.urban_movements);routes=deepcopy(cfg.network.control_area_routes)
        result=install(cfg)
        self.assertEqual(result['service_veh_h'],sum(caps[m] for m in MEMBERS))
        self.assertEqual({m for m,v in caps.items() if cfg.network.movement_capacity_by_movement_veh_h[m]!=v},set(MEMBERS))
        self.assertEqual(movements,cfg.network.urban_movements);self.assertEqual(routes,cfg.network.control_area_routes)
        self.assertEqual(before,pickle.dumps(state))

    def test_route_mismatch_rejected_before_mutation(self):
        cfg,_=fixture();caps=dict(cfg.network.movement_capacity_by_movement_veh_h)
        cfg.network.control_area_routes['movement:'+MEMBERS[0]]['physical_turns'][0]['path']=['wrong']
        with self.assertRaisesRegex(ValueError,'share one'):install(cfg)
        self.assertEqual(caps,cfg.network.movement_capacity_by_movement_veh_h)

    def test_sources_borrow_idle_service_but_cannot_double_total(self):
        from evaluation.controllers import head_service_resources as head
        from src.models import urban_queue_model as uqm
        cfg,_=fixture();old=cfg.network.movement_capacity_by_movement_veh_h[MEMBERS[0]];install(cfg)
        with patch.object(uqm,'_phase_green_fraction',return_value=1.):context=head.regular_context(cfg,None,240)
        limit=context[0][GROUP]
        solo=head.regular_batch(cfg,{MEMBERS[0]:100.,MEMBERS[1]:0.},context)
        self.assertAlmostEqual(solo[MEMBERS[0]],limit)
        self.assertGreater(solo[MEMBERS[0]],old*cfg.simulation.T_u_h)
        both=head.regular_batch(cfg,{MEMBERS[0]:100.,MEMBERS[1]:100.},context)
        self.assertAlmostEqual(sum(both.values()),limit)
        for m,v in both.items():head.regular_accepted(m,v,context)
        self.assertAlmostEqual(context[1][GROUP],limit)
        self.assertEqual(sum(head.regular_batch(cfg,{m:10. for m in MEMBERS},context).values()),0.)

    def test_red_allows_no_service(self):
        from evaluation.controllers import head_service_resources as head
        from src.models import urban_queue_model as uqm
        cfg,_=fixture();install(cfg)
        with patch.object(uqm,'_phase_green_fraction',return_value=0.):context=head.regular_context(cfg,None,240)
        self.assertEqual(sum(head.regular_batch(cfg,{m:10. for m in MEMBERS},context).values()),0.)

    def test_local_global_same_pool_without_changing_other_owners(self):
        from src.controllers.wu_faithful_follower import WuFaithfulFollower
        cfg,_=fixture();follower=WuFaithfulFollower(cfg)
        before={k:v for k,v in follower._local_models.items() if k!='SC107'}
        install(cfg);result=refresh_local(follower,cfg)
        self.assertTrue(result['local_global_budget_equal'])
        self.assertTrue(all(follower._local_models[k] is v for k,v in before.items()))

    def test_duplicate_install_rejected(self):
        cfg,_=fixture();install(cfg)
        with self.assertRaisesRegex(ValueError,'Duplicate'):install(cfg)


if __name__=='__main__':unittest.main()
