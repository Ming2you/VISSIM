"""Focused current-route subset proposal tests, no full optimizer/VISSIM."""
import copy
from collections import Counter
import hashlib
import json
import pickle
import subprocess
import sys
import unittest
from diagnostics.probe_model_area_integration import ROOT, build_projected
from diagnostics.prepare_known_wout_routes import installed
from diagnostics.known_wout_fixtures import input_path


def actual_case(sec):
    return build_projected(ROOT/'diagnostics/area_candidate_configs/n7_area_beta0.json',
        input_path(f'state_{sec:06d}.json'),input_path(f'action_{sec-150:06d}.json'),fixture_inputs=False)


def option(tuning):
    tuning=copy.deepcopy(tuning)
    path=ROOT/'diagnostics/known_wout_routes_ver2_proposal.json'
    tuning['urban']['preserve_known_wout_routes']=True
    tuning['urban']['known_wout_route_evidence']={'path':str(path.relative_to(ROOT)),
        'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    return tuning


class KnownWoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases={sec:actual_case(sec) for sec in (1200,3300)}

    def setUp(self):
        from evaluation.controllers import urban_flow_accounting as urban
        self.original_legsplit=urban.legsplit_substep_accounted
        self.ctx=installed(); self.route=self.ctx.__enter__()
        self.addCleanup(self.ctx.__exit__,None,None,None)

    def prepared(self,sec):
        cfg,state,detectors,tuning,raw,mapping,metadata=copy.deepcopy(self.cases[sec])
        n_before=pickle.dumps((state.urban_link_storage,state.urban_storage_release_buffer,state._control_area_ledger))
        self.route.configure_known_legsplit(cfg,option(tuning),state,raw)
        self.assertEqual(n_before,pickle.dumps((state.urban_link_storage,state.urban_storage_release_buffer,state._control_area_ledger)))
        return cfg,state,raw

    def test_initial_route_subsets_are_exclusive_and_preserve_stock(self):
        for sec,expected in [(1200,{'free':12.,'R_F_W':4.,'prechoice':4.}),
                             (3300,{'free':34.,'R_F_W':61.,'R_F_E':1.,'prechoice':9.})]:
            cfg,state,_=self.prepared(sec)
            counts=Counter()
            for c in state.known_legsplit_route_state['cohorts']:counts[c['target']]+=c['vehicles']
            self.assertEqual(dict(counts),expected)
            self.assertEqual(sum(counts.values()),cfg.network.urban_link_storage_veh['SC1004_W_out']-state.urban_link_storage['SC1004_W_out'])

    def test_known_receipts_do_not_redraw_after_receiver_rejection(self):
        cfg,state,_=self.prepared(1200)
        spec=cfg.network.known_legsplit_routes; step=240; storage=spec['storage']
        requests=self.route.known_legsplit_requests(state,cfg,storage,20.,20.,step)
        self.assertAlmostEqual(requests['free'],12.+4*.3333)
        self.assertAlmostEqual(requests['R_F_E'],4*.1667)
        self.assertAlmostEqual(requests['R_F_W'],4.+4*.5)
        # Actual stock owner accepts only one free vehicle; all other requests
        # are rejected. The helper alone cannot withdraw any physical vehicle.
        state.urban_link_storage[storage]+=1.
        self.route.known_legsplit_commit(state,cfg,[(storage,None,1.)],step)
        again=self.route.known_legsplit_requests(state,cfg,storage,19.,19.,step+1)
        self.assertEqual(again['R_F_E'],requests['R_F_E'])
        self.assertEqual(again['R_F_W'],requests['R_F_W'])
        self.assertAlmostEqual(again['free'],requests['free']-1.)

    def test_candidate_copy_and_rejected_attempt_leave_original_unchanged(self):
        cfg,state,_=self.prepared(3300); before=pickle.dumps(state)
        candidate=state.copy(); storage='SC1004_W_out'
        req=self.route.known_legsplit_requests(candidate,cfg,storage,5.,105.,660)
        candidate.urban_link_storage[storage]+=.5
        self.route.known_legsplit_commit(candidate,cfg,[(storage,None,.5)],660)
        self.assertEqual(before,pickle.dumps(state))
        self.assertAlmostEqual(self.route._known_total(candidate),104.5)
        self.assertGreater(req['free'],.5)

    def test_postchoice_missing_route_is_held_not_given_prior(self):
        cfg,state,raw=self.prepared(1200)
        record={'link_no':121,'position_m':2.}
        empty={'route_decision_type':None,'route_decision_no':None,'route_no':None}
        self.assertEqual(self.route._known_classify(record,empty,cfg.network.known_legsplit_routes),'unknown')
        record={'link_no':68,'position_m':3.}
        self.assertEqual(self.route._known_classify(record,empty,cfg.network.known_legsplit_routes),'prechoice')

    def test_future_direct_and_urban_receipts_keep_existing_ready_timing(self):
        cfg,state,_=self.prepared(1200); storage='SC1004_W_out'
        state.urban_link_storage[storage]-=1.
        self.route.known_legsplit_receive(state,cfg,1.,242,off_ramp='OR_F_E')
        state.urban_link_storage[storage]-=2.
        self.route.known_legsplit_receive(state,cfg,2.,247,movement='SC1004_N_SC1003_to_W')
        # The original owner separately writes the same generic release buffer.
        state.urban_storage_release_buffer[storage]={247:2.}
        req=self.route.known_legsplit_requests(state,cfg,storage,21.,21.,242)
        self.assertAlmostEqual(req['free'],13.+4*.3333)
        self.assertEqual(sum(c['vehicles'] for c in state.known_legsplit_route_state['cohorts'] if c['due']>242),2.)

    def test_off_is_exact_noop_and_nonboolean_rejected(self):
        cfg,state,detectors,tuning,raw,mapping,metadata=copy.deepcopy(self.cases[1200])
        before=pickle.dumps((cfg,state,raw))
        self.assertEqual(self.route.configure_known_legsplit(cfg,tuning,state,raw),{})
        self.assertIsNone(self.route.known_legsplit_requests(state,cfg,'SC1004_W_out',1.,20.,240))
        self.route.known_legsplit_commit(state,cfg,[],240)
        self.assertEqual(before,pickle.dumps((cfg,state,raw)))
        bad=copy.deepcopy(tuning);bad['urban']['preserve_known_wout_routes']='true'
        with self.assertRaises(ValueError):self.route.configure_known_legsplit(cfg,bad,state,raw)
        bad=option(tuning);cfg.network.boundary_out_ramp_split['SC1004_W_out']['free']=.5
        with self.assertRaisesRegex(ValueError,'normalized'):
            self.route.configure_known_legsplit(cfg,bad,state,raw)

    def test_bad_receipt_cannot_partially_debit_tags(self):
        cfg,state,_=self.prepared(1200)
        self.route.known_legsplit_requests(state,cfg,'SC1004_W_out',20.,20.,240)
        before=pickle.dumps(state.known_legsplit_route_state)
        with self.assertRaisesRegex(ValueError,'source owner'):
            self.route.known_legsplit_commit(state,cfg,[('SC1004_W_out',None,1.)],240)
        self.assertEqual(before,pickle.dumps(state.known_legsplit_route_state))
        with self.assertRaisesRegex(ValueError,'more than'):
            self.route.known_legsplit_commit(state,cfg,[('SC1004_W_out','R_F_E',100.)],240)
        self.assertEqual(before,pickle.dumps(state.known_legsplit_route_state))

    def test_unknown_ready_stock_is_held_without_extra_known_budget(self):
        cfg,state,_=self.prepared(1200)
        local=state.known_legsplit_route_state
        local['cohorts']=[{'target':'unknown','vehicles':10.,'due':240,'source':'synthetic'},
                          {'target':'free','vehicles':10.,'due':240,'source':'synthetic'}]
        req=self.route.known_legsplit_requests(state,cfg,'SC1004_W_out',10.,20.,240)
        self.assertEqual(req,{'free':5.})
        state.urban_link_storage['SC1004_W_out']+=5.
        self.route.known_legsplit_commit(state,cfg,[('SC1004_W_out',None,5.)],240)
        self.assertEqual(sum(c['vehicles'] for c in local['cohorts'] if c['target']=='unknown'),10.)
        reported=self.route.diagnostics(state,cfg)
        self.assertEqual(reported['known_wout_held_unknown_route_veh'],10.)
        self.assertEqual(reported['known_wout_prediction_route_complete'],0.)
        self.assertEqual(reported['route_choice_prediction_route_complete'],0.)

    def test_enabled_rejects_unaccounted_scheduler_before_alias_mutation(self):
        cfg,state,detectors,tuning,raw,mapping,metadata=copy.deepcopy(self.cases[1200])
        cfg.network.control_area_enabled=False
        before=pickle.dumps((cfg,state))
        with self.assertRaisesRegex(ValueError,'accounted area scheduler'):
            self.route.configure_known_legsplit(cfg,option(tuning),state,raw)
        self.assertEqual(before,pickle.dumps((cfg,state)))

    def test_initial_pending_keeps_ready_boundary_and_total_residence_stock(self):
        cfg,state,detectors,tuning,raw,mapping,metadata=copy.deepcopy(self.cases[1200])
        state.urban_storage_release_buffer['SC1004_W_out']={241:5.}
        self.route.configure_known_legsplit(cfg,option(tuning),state,raw)
        self.assertEqual(self.route._known_total(state),20.)
        first=self.route.known_legsplit_requests(state,cfg,'SC1004_W_out',15.,15.,240)
        self.assertAlmostEqual(sum(first.values()),15.)
        self.route.known_legsplit_commit(state,cfg,[],240)
        second=self.route.known_legsplit_requests(state,cfg,'SC1004_W_out',20.,20.,241)
        self.assertAlmostEqual(sum(second.values()),20.)
        self.assertEqual(self.route._known_total(state),20.)

    def test_actual_legsplit_body_off_is_identical(self):
        from diagnostics.probe_model_area_integration import adapter
        from evaluation.controllers import urban_flow_accounting as urban
        from src.models.state import ControlAction
        from src.models.demand import DemandStep
        cfg,state,detectors,tuning,raw,mapping,metadata=copy.deepcopy(self.cases[1200])
        control=adapter.control_from_json(input_path('action_001200.json'),cfg,ControlAction)
        calibration=adapter.deep_update(dict(adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))),tuning.get('calibration_override',{}))
        demand=adapter.demand_from_state(raw,cfg,DemandStep,1,calibration,detectors)[0]
        proposed=urban.legsplit_substep_accounted
        original=self.original_legsplit
        a=state.copy();b=state.copy()
        left=original(a,control,demand,cfg,urban_step_index=240,ramp_release_veh_h=control.ramp_metering)
        right=proposed(b,control,demand,cfg,urban_step_index=240,ramp_release_veh_h=control.ramp_metering)
        self.assertEqual(left,right)
        self.assertEqual(pickle.dumps(a),pickle.dumps(b))

    def test_fresh_runtime_worker_preserves_plain_aliases_and_ready(self):
        cfg,state,raw=self.prepared(3300)
        expected=self.route.known_legsplit_requests(state.copy(),cfg,'SC1004_W_out',10.,105.,660)
        detectors=self.cases[3300][2]
        code='''import json,pickle,sys
from diagnostics.probe_model_area_integration import adapter
from diagnostics.prepare_known_wout_routes import installed
from evaluation.controllers.runtime_setup import install_worker_runtime
cfg,state,raw,detectors=pickle.loads(sys.stdin.buffer.read())
with installed() as route:
    install_worker_runtime(adapter,cfg,raw,detectors)
    before=pickle.dumps(state)
    candidate=state.copy()
    requests=route.known_legsplit_requests(candidate,cfg,'SC1004_W_out',10.,105.,660)
    assert before==pickle.dumps(state)
    print(json.dumps(requests,sort_keys=True))
'''
        result=subprocess.run([sys.executable,'-X','utf8','-c',code],
            input=pickle.dumps((cfg,state,raw,detectors)),capture_output=True,cwd=ROOT,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr.decode('utf-8',errors='replace'))
        self.assertEqual(json.loads(result.stdout),expected)

if __name__=='__main__':unittest.main()
