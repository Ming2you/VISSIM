import copy,pickle,unittest
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_composite308.inputs import inputs
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.native_routes329 import candidate as c
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal

class FutureRoute(unittest.TestCase):
    def setUp(self):
        self.cfg,s,raw,frame,self.network,_,lanes=inputs()
        self.state,_=c.gate.install(self.cfg,s,raw,frame,self.network,lanes)

    def test_native_weights_paths_eligibility_and_no_current_changes(self):
        before=pickle.dumps(self.state);net=copy.deepcopy(self.cfg.network)
        spec=c.install(self.cfg,self.network)
        self.assertEqual(pickle.dumps(self.state),before)
        self.assertEqual({k for k,v in vars(self.cfg.network).items() if k not in vars(net) or not equal(v,vars(net)[k])},{c.ATTR})
        self.assertAlmostEqual(sum(spec['weights'].values()),1)
        self.assertAlmostEqual(spec['weights']['SC12_N_SC6_to_S_SC16'],477/599)
        self.assertEqual(set(spec['eligible_sources']),{'SC6_N_SC103_to_S_SC12','SC6_W_SC5_to_S_SC12'})
        self.assertFalse(spec['incoming']['SC6_E_SC104_to_S_SC12']['eligible'])
        self.assertIn('10224',spec['routes']['SC12_N_SC6_to_E_SC106']['path'])
        self.assertNotEqual(spec['routes']['SC12_N_SC6_to_E_SC106']['post_m'],spec['routes']['SC12_N_SC6_to_S_SC16']['post_m'])

    def test_new_cohorts_conserve_parent_and_leave_existing_untouched(self):
        spec=c.install(self.cfg,self.network);s=self.state
        old=copy.deepcopy(vars(s));local=getattr(s,c.gate.ATTR)
        pending=dict(local['pending']);n=local['received']
        r=c.register(s,self.cfg,next(iter(spec['eligible_sources'])),599.,240,entry_step=241)
        self.assertAlmostEqual(local['received']-n,599)
        self.assertEqual({k for k,v in vars(s).items() if not equal(v,old[k])},{c.gate.ATTR})
        self.assertAlmostEqual(sum(local['pending'].values())-sum(pending.values()),599)
        for m,w in spec['weights'].items():self.assertAlmostEqual(r['routes'][m]['vehicles'],599*w)
        self.assertGreater(r['gate_due_sec'],2410)

    def test_release_tag_delivers_once_with_unknown_beta_residual(self):
        from evaluation.controllers.physical_ramp_branches import split_tagged_arrival
        from src.models.urban_queue_model import approach_routing
        spec=c.install(self.cfg,self.network);s=self.state;due=999
        for m,w in spec['weights'].items():c.gate.schedule(s,due,599*w,m)
        c.gate.schedule(s,due,10.) # explicitly untagged current/unsupported residual
        routing=dict(approach_routing(self.cfg)[c.gate.TARGET])
        rows=dict(split_tagged_arrival(s,self.cfg,c.gate.TARGET,due,609.,list(routing.items())))
        self.assertAlmostEqual(sum(rows.values()),609)
        for m,w in spec['weights'].items():self.assertAlmostEqual(rows[m],599*w+10*routing[m])
        self.assertNotIn(due,s.gate_initial_route_tags[c.gate.TARGET])

    def test_existing_gate_ready_and_red_green_conservation(self):
        spec=c.install(self.cfg,self.network);s=self.state
        local=getattr(s,c.gate.ATTR);local.update(pending={},ready={},received=0.,discharged=0.,last_step=239)
        r=c.register(s,self.cfg,next(iter(spec['eligible_sources'])),30.,240)
        due=int(r['gate_due_sec']/10)
        for step in range(240,due+1):c.gate.step_gate(local,step,0,4200,10)
        self.assertAlmostEqual(sum(local['ready'].values()),30)
        released={}
        for step in range(due+1,due+5):
            out,row=c.gate.step_gate(local,step,10,4200,10)
            for (post,m),n in out.items():released[m]=released.get(m,0)+n
        self.assertAlmostEqual(sum(released.values()),30)
        for m,w in spec['weights'].items():self.assertAlmostEqual(released[m],30*w)
        self.assertAlmostEqual(local['received'],local['discharged'])

    def test_hook_delegates_unproven_source_and_restores(self):
        from evaluation.controllers import urban_flow_accounting as ufa
        spec=c.install(self.cfg,self.network);old=ufa._receive_corridor;calls=[]
        def sentinel(*a,**kw):calls.append((a,kw));return 'delegate'
        ufa._receive_corridor=sentinel
        try:
            with c.enabled() as records:
                self.assertEqual(ufa._receive_corridor(self.state,self.cfg,'SC6_E_SC104_to_S_SC12',1.,240),'delegate')
                self.assertTrue(ufa._receive_corridor(self.state,self.cfg,next(iter(spec['eligible_sources'])),1.,240))
                self.assertEqual(len(records),1);self.assertEqual(len(calls),1)
            self.assertIs(ufa._receive_corridor,sentinel)
        finally:ufa._receive_corridor=old

    def test_unreviewed_network_duplicate_and_negative_volume_rejected(self):
        cfg=self.cfg;before=pickle.dumps(cfg)
        with self.assertRaises(ValueError):c.install(cfg,self.network+b' ')
        self.assertEqual(pickle.dumps(cfg),before)
        spec=c.install(cfg,self.network)
        with self.assertRaises(ValueError):c.install(cfg,self.network)
        before=pickle.dumps(self.state)
        with self.assertRaises(ValueError):c.register(self.state,cfg,next(iter(spec['eligible_sources'])),-1.,240)
        self.assertEqual(pickle.dumps(self.state),before)

if __name__=='__main__':unittest.main()

