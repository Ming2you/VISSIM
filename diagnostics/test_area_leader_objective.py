"""Canonical cost/consumer tests; no endpoint rollout, search or proposal loading."""
from __future__ import annotations
import contextlib,copy,json,pickle,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import area_leader_objective as objective
from diagnostics.probe_signal_feasibility import setup
from evaluation.controllers import vissim_stackelberg_adapter as adapter,area_runtime,urban_flow_accounting,area_freeway_accounting,area_follower_objective
from src.controllers.leader import Leader,LeaderAction
from src.controllers import stackelberg_mpc as mpc,rollout_endpoint
from src.controllers import stackelberg_wu_metered as metered
from src.controllers.stackelberg_wu_metered import StackelbergWuMeteredController
from src.controllers.wu_faithful_follower import WuFaithfulFollower
from src.models.state import ControlAction
BASE=Leader.objective_terms
BASE_PROXY=StackelbergWuMeteredController._proxy_score_candidate
BASE_MPC_PROXY=mpc.StackelbergMPCController._proxy_score_candidate
BASE_EVAL=mpc.StackelbergMPCController._leader_evaluation_base
BASE_FALLBACK=mpc.StackelbergMPCController._make_fallback_evaluation

class AreaLeaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.cfg,cls.state,*_=setup()
    def setUp(self):
        self.stack=contextlib.ExitStack()
        for cls,name,original in ((Leader,'objective_terms',BASE),(StackelbergWuMeteredController,'_proxy_score_candidate',BASE_PROXY),
                                  (mpc.StackelbergMPCController,'_proxy_score_candidate',BASE_MPC_PROXY),
                                  (mpc.StackelbergMPCController,'_leader_evaluation_base',BASE_EVAL),
                                  (mpc.StackelbergMPCController,'_make_fallback_evaluation',BASE_FALLBACK)):
            self.stack.enter_context(patch.object(cls,name,original))
    def tearDown(self):self.stack.close()
    def fixture(self,area):
        cfg=copy.deepcopy(self.cfg);state=self.state.copy()
        cfg.network.control_area_enabled=area;cfg.leader.objective_mode='follower_ttt'
        cfg.leader.mfd_penalty_mode='combined';cfg.leader.N_P_crit_veh=0.
        cfg.leader.w_P=2.;cfg.leader.w_F=3.;cfg.leader.w_ramp_queue=4.;cfg.leader.w_boundary_in=5.
        cfg.leader.mfd_storage_weight=1.;cfg.leader.mfd_storage_threshold_ratio=.5
        state.freeway_density[next(iter(state.freeway_density))][0]=100.
        state.ramp_queue[next(iter(state.ramp_queue))]=50.
        movement=next(m for m,s in cfg.network.urban_movements.items() if s.get('kind')=='boundary_in')
        state.urban_movement_queue[movement]=1000.
        control=ControlAction.fixed(cfg);control.N_P_star=0.;control.N_UF_star=1440.
        return cfg,state,control
    def test_off_exact_original_terms_and_no_weight_mutation(self):
        cfg,state,control=self.fixture(False);leader=Leader(cfg)
        expected=BASE(leader,[state],control,control,-20.,False,.2,.3)
        weights=pickle.dumps(cfg.leader)
        with patch.object(Leader,'objective_terms',BASE):
            cfg.network.control_area_enabled=True;objective.install_runtime(cfg)
            cfg.network.control_area_enabled=False
            self.assertEqual(leader.objective_terms([state],control,control,-20.,False,.2,.3),expected)
            cfg.leader.objective_mode='state_accumulation'
            expected=BASE(leader,[state],control,control,42.,True)
            self.assertEqual(leader.objective_terms([state],control,control,42.,True),expected)
            cfg.leader.objective_mode='follower_ttt'
        self.assertEqual(pickle.dumps(cfg.leader),weights)
    def test_on_excludes_all_positive_legacy_terms_preserves_quantities_and_inputs(self):
        cfg,state,control=self.fixture(True);leader=Leader(cfg)
        old=BASE(leader,[state],control,control,-20.,True)
        for key in objective.APPLIED_LEGACY_COSTS[:-1]:self.assertGreater(old[key],0.,key)
        immutable=pickle.dumps((cfg,state,control))
        with patch.object(Leader,'objective_terms',BASE):
            objective.install_runtime(cfg);once=Leader.objective_terms
            objective.install_runtime(cfg);self.assertIs(Leader.objective_terms,once)
            actual=leader.objective_terms([state],control,control,-20.,True)
            self.assertEqual(leader.objective([state],control,control,-20.,True),-20.)
        self.assertEqual(pickle.dumps((cfg,state,control)),immutable)
        self.assertEqual(actual['leader_total_objective'],-20.)
        for key in objective.APPLIED_LEGACY_COSTS[:-1]:
            self.assertEqual(actual[key],0.)
            self.assertEqual(actual['leader_excluded_'+key.removeprefix('leader_')],old[key])
        for key in ('leader_density_excess','leader_mfd_storage_excess_veh','leader_ramp_queue_veh'):
            self.assertEqual(actual[key],old[key])
        self.assertEqual(objective.canonicalize_terms(cfg,actual,-20.),actual)
    def test_terminal_installer_before_or_after_class_hook_cannot_readd_cost(self):
        install=adapter.install_vissim_terminal_cost_objective
        with tempfile.TemporaryDirectory(dir=ROOT/'diagnostics') as tmp:
            fit=Path(tmp)/'fit.json';fit.write_text(json.dumps({'raw_coefficients':{'ramp_vehicles':2.},'features':['ramp_vehicles']}))
            tuning={'adapter':{'terminal_cost':{'enabled':True,'fit_json':str(fit),'weight':3.}}}
            for terminal_first in (False,True):
                with self.subTest(terminal_first=terminal_first),patch.object(Leader,'objective_terms',BASE):
                    cfg,state,control=self.fixture(True);leader=Leader(cfg);controller=SimpleNamespace(leader=leader)
                    if terminal_first:install(controller,cfg,tuning)
                    objective.install_runtime(cfg)
                    if not terminal_first:install(controller,cfg,tuning)
                    actual=leader.objective_terms([state],control,control,-20.,True)
                    self.assertEqual(actual['leader_total_objective'],-20.)
                    self.assertGreater(actual['leader_excluded_vissim_terminal_cost_penalty'],0.)
                    self.assertGreater(actual['leader_excluded_density_penalty'],0.)
                    self.assertEqual(actual['leader_vissim_terminal_cost_active'],0.)
                    self.assertEqual(actual['leader_vissim_terminal_cost_penalty'],0.)
                    self.assertEqual(leader.objective_terms([],control,control,-20.,True)['leader_total_objective'],-20.)
                    cfg.network.control_area_enabled=False
                    off=leader.objective_terms([state],control,control,-20.,True)
                    plain=SimpleNamespace(leader=Leader(cfg))
                    with patch.object(Leader,'objective_terms',BASE):
                        adapter.install_vissim_terminal_cost_objective(plain,cfg,tuning)
                        self.assertEqual(off,plain.leader.objective_terms([state],control,control,-20.,True))
    def test_full_and_wu_proxy_use_same_endpoint_score_base_fallback_rejected(self):
        cfg,state,control=self.fixture(True);score=-20.
        controller=object.__new__(StackelbergWuMeteredController);controller.cfg=cfg;controller.leader=Leader(cfg)
        follower=object.__new__(WuFaithfulFollower)
        nash=SimpleNamespace(control=control.copy(),diagnostics={},objective_value=score,converged=True,residual_objective=0.,residual_control=0.)
        follower.solve=lambda *a,**k:nash
        follower._local_freeway_models={link:SimpleNamespace(owned_ramps=[r for r in cfg.network.ramps if cfg.network.ramp_to_freeway[r]==link]) for link in cfg.network.freeway_links}
        follower._wu=SimpleNamespace(_omega_f={link:.5 for link in cfg.network.freeway_links})
        controller.nash_solver=follower;controller.candidate_dedupe_enabled=True;controller._nuf_solve_cache={};controller._dedupe_hits=0
        controller._project_action_to_follower_feasible_np=lambda action,*a,**k:(action,{})
        controller._leader_evaluation_base=lambda *a,**k:([state],score,True)
        controller._close_nash_response_leader_action=lambda action,*a,**k:(action,{})
        controller._predict=lambda *a,**k:([state],30.)  # Historical _predict returns TTT, not negative J.
        forecast=[object()];action=LeaderAction(0.,1440.)
        with patch.object(Leader,'objective_terms',BASE),patch.object(rollout_endpoint,'evaluate_price_point',return_value=SimpleNamespace(states=[state],ttt=30.,objective=score)):
            objective.install_runtime(cfg)
            full=controller._evaluate_full_candidate(0,action,state,forecast,control,stage='test',incumbent_obj=float('inf'))
            proxy=controller._proxy_score_candidate(0,action,state,forecast,control)
            self.assertEqual(BASE_PROXY(controller,0,action,state,forecast,control)['objective'],30.)
            with self.assertRaisesRegex(ValueError,'base fallback'):
                controller._make_fallback_evaluation(1,'fallback',nash,control,state,forecast)
        for value in (full.objective,proxy['objective']):self.assertEqual(value,score)
        self.assertEqual(full.objective_terms['leader_control_area_objective_only'],1.)
    def test_actual_wu_pfo_method_uses_endpoint_once_and_preserves_complete_terms(self):
        cfg,state,previous=self.fixture(True);cfg.mpc.stackelberg_enable_pfo_incumbent=True
        controller=object.__new__(StackelbergWuMeteredController);controller.cfg=cfg;controller.leader=Leader(cfg)
        nash=SimpleNamespace(control=previous.copy(),diagnostics={},objective_value=99.,converged=True,residual_objective=0.,residual_control=0.)
        solved=[];events=[];forecast=[object()]
        def response(copied_state,leader,supplied_forecast,pfo_previous):
            self.assertIsNone(leader);self.assertIs(supplied_forecast,forecast)
            self.assertIsNot(copied_state,state);self.assertEqual(pickle.dumps(copied_state),pickle.dumps(state))
            self.assertEqual((pfo_previous.N_P_star,pfo_previous.N_UF_star),(0.,0.))
            self.assertEqual(pfo_previous.inflow_outflow_allocation,{})
            solved.append(pfo_previous)
            return nash
        controller.nash_solver=SimpleNamespace(solve=response)
        # Preserve the actual equivalent-action method, isolate only its bounds
        # query. This regression exercises score composition, not a new solve.
        controller.leader._candidate_bounds=lambda *a,**k:SimpleNamespace(np_lower=0.,np_upper=10000.,nuf_lower=0.,nuf_upper=10000.)
        controller._append_progress_event=lambda **kw:events.append(kw)
        immutable=pickle.dumps((state,previous))
        point=SimpleNamespace(states=[state],ttt=30.,objective=-20.)
        with patch.object(rollout_endpoint,'evaluate_price_point',return_value=point) as endpoint:
            objective.install_runtime(cfg)
            with patch.object(controller,'_make_fallback_evaluation',side_effect=AssertionError('Wu PFO must not use base fallback')):
                rows=controller._evaluate_fallback_candidates(state,forecast,previous,7)
        self.assertEqual(endpoint.call_count,1);self.assertEqual(len(solved),1)
        self.assertIs(endpoint.call_args.args[1],nash.control)
        self.assertIs(endpoint.call_args.args[4].walk_previous,solved[0])
        self.assertEqual(endpoint.call_args.args[4].score_mode,'raw')
        self.assertEqual(len(rows),1);row=rows[0]
        self.assertEqual((row.index,row.stage,row.objective,row.rollout_used),(7,'fallback_pfo',-20.,True))
        self.assertEqual(row.objective_terms['leader_control_area_objective_only'],1.)
        self.assertGreater(row.objective_terms['leader_excluded_density_penalty'],0.)
        self.assertEqual(row.metadata['leader_pfo_incumbent_objective'],-20.)
        self.assertIs(controller._pfo_incumbent_eval,row)
        self.assertEqual(events[0]['best_objective'],-20.)
        self.assertEqual(immutable,pickle.dumps((state,previous)))
    def test_unverified_base_proxy_rejected_before_any_score_or_endpoint(self):
        cfg,state,previous=self.fixture(True)
        owner=object.__new__(mpc.StackelbergMPCController);owner.cfg=cfg;owner.leader=Leader(cfg)
        owner.nash_solver=SimpleNamespace()
        owner._project_action_to_follower_feasible_np=lambda action,*a,**k:(action,{})
        action=LeaderAction(0.,0.);forecast=[object()]
        objective.install_runtime(cfg)
        with patch.object(rollout_endpoint,'evaluate_price_point',side_effect=AssertionError('Unsupported path must not start another endpoint')):
            with self.assertRaisesRegex(ValueError,'base/DistributedCoordinator'):
                owner._proxy_score_candidate(0,action,state,forecast,previous)
            cfg.network.control_area_enabled=False
            self.assertEqual(owner._proxy_score_candidate(0,action,state,forecast,previous),
                             BASE_MPC_PROXY(owner,0,action,state,forecast,previous))
    def test_actual_full_base_uses_endpoint_objective_even_without_old_far_gate(self):
        cfg,state,control=self.fixture(True);cfg.mpc.leader_value_depth=0;cfg.mpc.leader_mfd_far_at_d0=False
        owner=object.__new__(mpc.StackelbergMPCController);owner.cfg=cfg
        nash=SimpleNamespace(control=control,objective_value=99.)
        point=SimpleNamespace(states=[state],ttt=30.,objective=-20.)
        with patch.object(rollout_endpoint,'evaluate_price_point',return_value=point),patch.object(mpc,'evaluate_price_point',return_value=point):
            objective.install_runtime(cfg)
            self.assertEqual(owner._leader_evaluation_base(state,nash,[])[1],-20.)
            cfg.network.control_area_enabled=False
            self.assertEqual(owner._leader_evaluation_base(state,nash,[])[1],99.)
    def test_installed_proxy_and_fallback_off_exact_original(self):
        cfg,state,control=self.fixture(False)
        owner=object.__new__(StackelbergWuMeteredController);owner.cfg=cfg;owner.leader=Leader(cfg)
        owner._project_action_to_follower_feasible_np=lambda action,*a,**k:(action,{})
        owner._predict=lambda *a,**k:([state],30.)
        action=LeaderAction(0.,0.);nash=SimpleNamespace(control=control,diagnostics={},objective_value=30.,converged=True,residual_objective=0.,residual_control=0.)
        before_proxy=BASE_PROXY(owner,0,action,state,[object()],control)
        before_fallback=BASE_FALLBACK(owner,0,'fallback',nash,control,state,[object()])
        cfg.network.control_area_enabled=True;objective.install_runtime(cfg);cfg.network.control_area_enabled=False
        with patch.object(rollout_endpoint,'evaluate_price_point',side_effect=AssertionError('OFF must not use the new endpoint path')):
            self.assertEqual(owner._proxy_score_candidate(0,action,state,[object()],control),before_proxy)
            result=owner._make_fallback_evaluation(0,'fallback',nash,control,state,[object()])
        self.assertEqual(vars(result),vars(before_fallback))
    def test_fresh_worker_restore_and_imported_class_alias(self):
        cfg,state,control=self.fixture(True)
        with tempfile.TemporaryDirectory(dir=ROOT/'diagnostics') as tmp:
            payload=Path(tmp)/'payload.pkl';payload.write_bytes(pickle.dumps((cfg,state,control)))
            code="""import json,pickle,sys
from pathlib import Path
root=Path.cwd();sys.path[:0]=[str(root),str(root/'vendor/NumSim-mine')]
from src.controllers.leader import Leader as Alias
import importlib
p=importlib.import_module(sys.argv[2])
cfg,state,control=pickle.loads(Path(sys.argv[1]).read_bytes());weights=pickle.dumps(cfg.leader)
p.install_runtime(cfg);a=Alias(cfg).objective_terms([state],control,control,-20.,True)
assert a['leader_total_objective']==-20. and a['leader_excluded_density_penalty']>0
assert weights==pickle.dumps(cfg.leader)
print(json.dumps({'total':a['leader_total_objective'],'alias':bool(Alias.objective_terms._control_area_leader_objective)}))
"""
            result=subprocess.run([sys.executable,'-X','utf8','-c',code,str(payload),objective.__name__],cwd=ROOT,capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout),{'total':-20.,'alias':True})
    def test_common_runtime_installs_before_already_installed_endpoint_shortcut(self):
        cfg,_,_=self.fixture(True)
        install=area_runtime.install
        def endpoint(*args):raise AssertionError('No rollout should run')
        endpoint._control_area_objective=True
        with patch.object(Leader,'objective_terms',BASE),patch.object(urban_flow_accounting,'install',return_value={}),patch.object(area_freeway_accounting,'install',return_value={}),patch.object(area_follower_objective,'install_runtime',return_value={}),patch.object(rollout_endpoint,'evaluate_price_point',endpoint):
            metadata=install(adapter,cfg)
            self.assertEqual(metadata['control_area_leader_objective_only_installed'],1.)
            self.assertTrue(Leader.objective_terms._control_area_leader_objective)
    def test_actual1200_saved_comparator_and_all_beta_units(self):
        data=json.loads((ROOT/'diagnostics/source_meter_shutdown_diagnosis.json').read_text(encoding='utf-8'))
        cfg,_,_=self.fixture(True)
        states=[data['paired'][key]['endpoints'][-1] for key in ('recorded_closed','reopen_DW_FE_only')]
        self.assertGreater(states[1]['leader_terms_for_held_control']['leader_total_objective'],states[0]['leader_terms_for_held_control']['leader_total_objective'])
        for beta in (0,60,150,300):
            normalized=[]
            for row in states:
                old=copy.deepcopy(row['leader_terms_for_held_control']);base=row['area_metrics']['ttt_veh_h']-beta/3600*row['area_metrics']['ttd_veh']
                old['leader_total_objective']+=base-old['leader_objective_base'];old['leader_objective_base']=base
                normalized.append(objective.canonicalize_terms(cfg,old,base))
            self.assertLess(normalized[1]['leader_total_objective'],normalized[0]['leader_total_objective'])
            self.assertEqual(normalized[0]['leader_excluded_density_penalty'],59.80759763234019)
    def test_reject_unknown_cost_nonfinite_and_unsupported_direct_far(self):
        cfg,_,_=self.fixture(True)
        with self.assertRaisesRegex(ValueError,'Unrecognized'):objective.canonicalize_terms(cfg,{'leader_total_objective':2.},1.)
        with self.assertRaisesRegex(ValueError,'finite'):objective.canonicalize_terms(cfg,{'leader_total_objective':float('nan')},float('nan'))
        cfg.mpc.leader_proxy_near_far=True
        with self.assertRaisesRegex(ValueError,'direct proxy far'):objective.install_runtime(cfg)
        cfg.network.control_area_enabled=False;self.assertEqual(objective.install_runtime(cfg),{})
    def test_actual_endpoint_removes_objective_surrogates_not_feasibility(self):
        source=(ROOT/'evaluation/controllers/area_runtime.py').read_text(encoding='utf-8')
        self.assertIn('price_hinge=False, leader_hinge=False, protected_queue=False',source)
        self.assertIn('closing.assert_stocks(model_inventory(result.states[-1], cfg))',source)
        self.assertIn('area_leader_objective.require_pure_endpoint_base(result.objective, result.ttt)',source)
        self.assertIn('result.objective = weight.score(metrics)\n',source)
        self.assertIn("'additional_cost_veh_h': 0.0,",source)
        self.assertNotIn('score(metrics) + other',source)
    def test_endpoint_base_is_exact_ttt_and_unknown_extras_fail(self):
        for ttt in (0.,30.,1e6):
            self.assertIsNone(objective.require_pure_endpoint_base(ttt,ttt))
        for score,ttt in ((31.,30.),(29.,30.),(30.+1e-10,30.),(float('nan'),30.),(float('inf'),float('inf')),(-1.,-1.)):
            with self.subTest(objective=score,ttt=ttt),self.assertRaisesRegex(ValueError,'endpoint cost'):
                objective.require_pure_endpoint_base(score,ttt)

if __name__=='__main__':unittest.main()
