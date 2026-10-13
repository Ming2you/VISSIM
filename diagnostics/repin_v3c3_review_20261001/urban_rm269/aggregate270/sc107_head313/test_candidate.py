from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json,pickle,unittest
from candidate import install,partition,register_owner,THROUGH,SG5,UNKNOWN,RIGHT,ORIGIN

HERE=Path(__file__).resolve().parent;A=HERE.parent


def fixture():
    cfg,state,_=pickle.loads((A/'citysplit287/forecast2400/initial.pickle').read_bytes())
    evidence=json.loads((A/'sc107_composition312/assessment.json').read_bytes())
    raw_path=Path(next(p for p in evidence['source_pins'] if p.endswith('state_002400.json')))
    raw=json.loads(raw_path.read_bytes());frame=json.loads((raw_path.parent/raw['obs150']['frames']['current']['path']).read_bytes())
    network=Path(next(p for p in evidence['source_pins'] if p.endswith('.inpx'))).read_bytes()
    return cfg,state,raw,frame,network


class HeadCohortTest(unittest.TestCase):
    def test_position_prevents_backtracking(self):
        with self.assertRaisesRegex(ValueError,'after right'):
            partition([dict(veh_no=1,lane_no=2,position_m=1,stopped=True)],dict(right_pos=8,through_pos=85))

    def test_current_stock_and_pending_are_conserved(self):
        from evaluation.controllers.area_runtime import model_inventory
        from evaluation.controllers.control_area_objective import get_ledger
        cfg,s,raw,frame,network=fixture()
        inv=model_inventory(s,cfg);arr=deepcopy(s.urban_arrival_buffer);release=deepcopy(s.urban_storage_release_buffer)
        route={m:r['beta'] for m,r in cfg.network.urban_movements.items()}
        r=install(cfg,s,raw,frame,network)
        self.assertEqual(r['queue_after'][THROUGH],14)
        self.assertEqual(r['queue_after'][SG5],11)
        self.assertEqual(r['queue_after'][RIGHT],0)
        self.assertEqual(r['queue_after'][UNKNOWN],1)
        self.assertAlmostEqual(sum(inv.values()),sum(model_inventory(s,cfg).values()),places=9)
        self.assertEqual(arr,s.urban_arrival_buffer);self.assertEqual(release,s.urban_storage_release_buffer)
        self.assertTrue(all(cfg.network.urban_movements[m]['beta']==b for m,b in route.items()))
        self.assertEqual(s.gate_initial_route_tags[ORIGIN],{242:{THROUGH:3.}})
        get_ledger(s).assert_stocks(model_inventory(s,cfg))

    def test_sg5_responds_to_p4_not_p3_and_unknown_cannot_disappear(self):
        from src.models import urban_queue_model as uqm
        cfg,s,raw,frame,network=fixture();install(cfg,s,raw,frame,network)
        action=SimpleNamespace(green_times={'SC107_p3':100.,'SC107_p4':0.},offsets={},inflow_outflow_allocation={})
        self.assertEqual(uqm._phase_green_fraction(action,cfg,cfg.network.urban_movements[SG5]),0)
        action.green_times.update(SC107_p3=0.,SC107_p4=100.)
        self.assertGreater(uqm._phase_green_fraction(action,cfg,cfg.network.urban_movements[SG5]),0)
        self.assertEqual(uqm._phase_green_fraction(action,cfg,cfg.network.urban_movements[THROUGH]),0)
        self.assertEqual(uqm._movement_capacity_flow(action,cfg,UNKNOWN,cfg.network.urban_movements[UNKNOWN]),0)

    def test_known_current_route_is_not_imputed(self):
        cfg,s,raw,frame,network=fixture()
        row=next(r for r in frame['vehicles'] if str(r[1])=='1220000201');row[6]=1061
        with self.assertRaisesRegex(ValueError,'known route'):
            install(cfg,s,raw,frame,network)

    def test_new_head_uses_existing_physical_omega_path(self):
        from evaluation.controllers.control_area_objective import emit_transfer,get_ledger
        from evaluation.controllers.area_runtime import model_inventory
        cfg,s,raw,frame,network=fixture();install(cfg,s,raw,frame,network)
        self.assertEqual(cfg.network.control_area_routes['movement:'+SG5],cfg.network.control_area_routes['movement:'+THROUGH])
        n=.5;target='SC107_to_SC108'
        emit_transfer(s,cfg,'movement:'+SG5,'storage:'+target,n,route_key='movement:'+SG5)
        s.urban_movement_queue[SG5]-=n;s.urban_link_storage[target]-=n
        get_ledger(s).assert_stocks(model_inventory(s,cfg))

    def test_positive_left_demand_rejects_unqualified_service_reuse(self):
        cfg,s,raw,frame,network=fixture();cfg.network.urban_movements['SC107_W_SC1005_to_N_SC1']['beta']=.1
        with self.assertRaisesRegex(ValueError,'Positive left intent'):
            install(cfg,s,raw,frame,network)

    def test_new_head_has_one_owner_without_new_controls(self):
        from src.controllers.wu_faithful_follower import WuFaithfulFollower
        from evaluation.controllers.area_leader_objective import _joint_catalog
        cfg,s,raw,frame,network=fixture();follower=WuFaithfulFollower(cfg)
        initial={k:v for k,v in follower._local_models.items() if k!='SC107'}
        install(cfg,s,raw,frame,network)
        with self.assertRaisesRegex(ValueError,'exactly its configured'):_joint_catalog(follower)
        receipt=register_owner(follower,cfg)
        self.assertTrue(receipt['unique_owner_verified']);self.assertEqual(receipt['new_control_axes'],0)
        self.assertTrue(all(follower._local_models[k] is v for k,v in initial.items()))


if __name__=='__main__':unittest.main()
