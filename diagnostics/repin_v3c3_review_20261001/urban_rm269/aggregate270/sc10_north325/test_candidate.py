import copy,pickle,unittest
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_composite308.inputs import inputs
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc10_north325 import candidate as c
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal

class MiddleSignal(unittest.TestCase):
    def setUp(self):
        cfg,state,raw,frame,network,_,lanes=inputs();self.args=(cfg,state,raw,frame,network,lanes)

    def test_initial_conserved_parent_and_known_current_turns(self):
        cfg,old,*_=self.args;oldbytes=pickle.dumps(old);oldcfg=copy.deepcopy(cfg)
        new,r=c.install(*self.args)
        self.assertEqual(pickle.dumps(old),oldbytes)
        self.assertEqual(new.urban_link_storage,old.urban_link_storage)
        self.assertEqual(r['initial_gate_veh'],11)
        self.assertEqual(sum(r['direct_post_calendar'].values()),4)
        self.assertEqual(r['ready_after'],{m:(2. if m.endswith('S_SC16') else 0.) for m in c.MOVS})
        self.assertEqual({k for k,v in vars(cfg.network).items() if k not in vars(oldcfg.network) or not equal(v,vars(oldcfg.network)[k])},{c.ATTR})
        self.assertEqual(len(getattr(cfg.network,c.ATTR)['sources']),3)
        self.assertEqual(getattr(cfg.network,c.ATTR)['rate_veh_h'],4200)
        self.assertEqual(sum(sum(v.values()) for v in new.gate_initial_route_tags[c.TARGET].values()),2.)

    def test_red_then_partial_green_and_late_arrival(self):
        local=dict(pending={},ready={},received=0.,discharged=0.,last_step=239)
        c.register(local,240,3,11.,'known');c.register(local,250,3,2.,None)
        for t in (240,241,242):
            release,row=c.step_gate(local,t,0,4200,10)
            self.assertEqual(row['discharged'],0)
        release,row=c.step_gate(local,243,2,4200,10)
        self.assertAlmostEqual(row['discharged'],4200*2/3600)
        self.assertNotIn((3,None),release)
        release,row=c.step_gate(local,244,10,4200,10)
        self.assertAlmostEqual(local['discharged'],11)
        self.assertAlmostEqual(sum(local['pending'].values()),2)

    def test_known_tag_arrival_is_consumed_once(self):
        from evaluation.controllers.physical_ramp_branches import split_tagged_arrival
        from src.models.urban_queue_model import approach_routing
        cfg,*_=self.args;new,_=c.install(*self.args)
        before=sum(sum(v.values()) for v in new.gate_initial_route_tags[c.TARGET].values())
        received=0.
        for due,n in list(new.urban_arrival_buffer[c.TARGET].items()):
            split=split_tagged_arrival(new,cfg,c.TARGET,due,n,approach_routing(cfg)[c.TARGET])
            # No tagged cohort at this due step delegates to the existing prior.
            received+=n if split is None else sum(dict(split).values())
        self.assertEqual(before,2.)
        self.assertAlmostEqual(received,4.)
        self.assertFalse(new.gate_initial_route_tags[c.TARGET])

    def test_stale_state_does_not_change_config_or_source(self):
        args=list(self.args);args[3]=copy.deepcopy(args[3]);args[3]['time_s']+=10
        cb,sb=pickle.dumps(args[0]),pickle.dumps(args[1])
        with self.assertRaises(ValueError):c.install(*args)
        self.assertEqual(pickle.dumps(args[0]),cb);self.assertEqual(pickle.dumps(args[1]),sb)

    def test_duplicate_install_rejected(self):
        new,_=c.install(*self.args);args=list(self.args);args[1]=new
        with self.assertRaises(ValueError):c.install(*args)

    def test_hook_restores_and_copies_have_independent_gate_queues(self):
        from evaluation.controllers import urban_flow_accounting as ufa,route_choice_corridor as rc
        a,b=ufa._receive_corridor,rc.advance
        with self.assertRaises(RuntimeError):
            with c.enabled():raise RuntimeError('test scoped restoration')
        self.assertIs(a,ufa._receive_corridor);self.assertIs(b,rc.advance)
        new,_=c.install(*self.args);other=copy.deepcopy(new)
        getattr(other,c.ATTR)['pending'].clear()
        self.assertTrue(getattr(new,c.ATTR)['pending'])

if __name__=='__main__':unittest.main()
