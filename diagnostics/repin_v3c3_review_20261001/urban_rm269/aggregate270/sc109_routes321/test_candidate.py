import copy,pickle,unittest
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_composite308.inputs import inputs
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_initial320.candidate import install as retime
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_routes321 import candidate as c
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal


class CurrentTurns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cfg,state,raw,frame,network,inside,lanes=inputs()
        cls.timing=retime(cfg,state,raw,frame,network,lanes)
        cls.data=cfg,state,raw,frame,network

    def apply(self,data=None,timing=None):return c.install(*(data or self.data),timing or self.timing)

    def test_known_left_ready_and_unknown_prior_preserve_total(self):
        s,r=self.apply()
        self.assertEqual(r['queue_after'],{'SC109_W_SC108_to_E':0.,'SC109_W_SC108_to_N_SC16':10.})
        self.assertEqual(r['known_ready_veh'],10)
        self.assertEqual(r['known_initial_residual_veh'],16)
        self.assertEqual(r['untagged_residual_veh'],27)
        self.assertEqual(s.urban_arrival_buffer,self.data[1].urban_arrival_buffer)
        self.assertEqual(s.urban_storage_release_buffer,self.data[1].urban_storage_release_buffer)
        changed={k for k,v in vars(s).items() if not equal(v,vars(self.data[1])[k])}
        self.assertEqual(changed,{'urban_movement_queue','local_observation_summary','gate_initial_route_tags','_control_area_ledger'})
        for k,v in getattr(self.data[1],'gate_initial_route_tags',{}).items():self.assertEqual(s.gate_initial_route_tags[k],v)

    def test_real_consumer_keeps_known_turns_and_consumes_each_parent_once(self):
        from evaluation.controllers.physical_ramp_branches import split_tagged_arrival
        from src.models.urban_queue_model import approach_routing
        s,r=self.apply();routing=approach_routing(self.data[0])[c.TARGET];out=dict.fromkeys(c.MOVEMENTS,0.)
        for step,n in s.urban_arrival_buffer[c.TARGET].items():
            values=split_tagged_arrival(s,self.data[0],c.TARGET,step,n,routing)
            if values is None:values=[(m,n*b) for m,b in routing]
            self.assertAlmostEqual(sum(v for _,v in values),n)
            for m,v in values:out[m]+=v
        self.assertAlmostEqual(out['SC109_W_SC108_to_E'],9+27*.7621)
        self.assertAlmostEqual(out['SC109_W_SC108_to_N_SC16'],7+27*.2379)
        self.assertEqual(s.gate_initial_route_tags[c.TARGET],{})

    def test_source_state_unmodified_and_repeat_rejected(self):
        before=pickle.dumps(self.data[1],protocol=5);s,r=self.apply()
        self.assertEqual(before,pickle.dumps(self.data[1],protocol=5))
        data=list(self.data);data[1]=s
        with self.assertRaises(ValueError):self.apply(data)

    def test_current_route_conflict_rejected(self):
        data=list(copy.deepcopy(self.data))
        next(r for r in data[3]['vehicles'] if int(r[0])==14789)[9]=10285.
        with self.assertRaises(ValueError):self.apply(data)

    def test_future_or_mismatched_calendar_rejected(self):
        data=list(copy.deepcopy(self.data));data[3]['time_s']+=10
        with self.assertRaises(ValueError):self.apply(data)
        timing=copy.deepcopy(self.timing);timing['new_calendar'][241]-=1
        with self.assertRaises(ValueError):self.apply(timing=timing)


if __name__=='__main__':unittest.main()
