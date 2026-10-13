import copy,pickle,unittest
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_composite308.inputs import inputs
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc16_aggregate323 import candidate as c
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal

class AggregateSC16(unittest.TestCase):
    def setUp(self):
        cfg,state,raw,frame,network,_,lanes=inputs()
        self.args=cfg,state,raw,frame,network,lanes

    def test_current_lane_prior_service_and_preserved_physics(self):
        cfg,state,*_=self.args;old=copy.deepcopy(cfg);new,r=c.install(*self.args)
        self.assertEqual(new.urban_movement_queue[c.LEFT],1.)
        self.assertEqual(sum(new.urban_movement_queue[m] for m in c.MOVEMENTS),1.)
        self.assertEqual(new.urban_arrival_buffer,state.urban_arrival_buffer)
        self.assertEqual(new.urban_storage_release_buffer,state.urban_storage_release_buffer)
        self.assertEqual(cfg.network.movement_capacity_by_movement_veh_h[c.LEFT],1440.)
        self.assertEqual(cfg.network.urban_movements[c.LEFT]['beta'],33/124)
        self.assertEqual({k for k,v in vars(cfg.network).items() if not equal(v,vars(old.network)[k])},
                         {'urban_movements','movement_capacity_by_movement_veh_h'})
        self.assertEqual({k for k,v in vars(new).items() if not equal(v,vars(state)[k])},
                         {'urban_movement_queue','local_observation_summary','gate_initial_route_tags','_control_area_ledger'})
        self.assertEqual(r['current_projection']['tagged_residual'].get(c.LEFT,0.),0.)

    def test_arrival_tags_preserve_current_lane_and_consume_once(self):
        from evaluation.controllers.physical_ramp_branches import split_tagged_arrival
        from src.models.urban_queue_model import approach_routing
        new,r=c.install(*self.args);cfg=self.args[0]
        step=r['current_projection']['due_step'];parent=r['current_projection']['parent_veh']
        got=dict(split_tagged_arrival(new,cfg,c.SOURCE,step,parent,approach_routing(cfg)[c.SOURCE]))
        self.assertAlmostEqual(sum(got.values()),parent)
        self.assertAlmostEqual(got[c.LEFT],(parent-2)*33/124)
        self.assertEqual(new.gate_initial_route_tags[c.SOURCE],{})

    def test_source_state_unchanged_and_repeated_install_rejected(self):
        before=pickle.dumps(self.args[1]);new,_=c.install(*self.args)
        self.assertEqual(pickle.dumps(self.args[1]),before)
        with self.assertRaises(ValueError):c.install(*self.args)

    def test_stale_observation_rejected_before_configuration_change(self):
        args=list(self.args);args[3]=copy.deepcopy(args[3]);args[3]['time_s']+=10
        before=pickle.dumps(args[0])
        with self.assertRaises(ValueError):c.install(*args)
        self.assertEqual(pickle.dumps(args[0]),before)

    def test_future_support_rejected(self):
        self.args[1].time_sec=2250
        with self.assertRaises(ValueError):c.install(*self.args)

if __name__=='__main__':unittest.main()
