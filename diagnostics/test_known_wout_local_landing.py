"""Actual1200/3300 one-step route consumers; no endpoint or optimizer."""
import copy
import json
import pickle
import unittest
from unittest.mock import patch
from diagnostics.probe_known_wout_local_parity import prepared,local_transfers
from diagnostics.probe_model_area_integration import ROOT,adapter
from diagnostics.test_known_wout_routes import option
from diagnostics.known_wout_fixtures import input_path
from diagnostics.prepare_known_wout_local_landing import installed
from evaluation.controllers import link_predictor,urban_flow_accounting as urban


class LocalKnownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases={sec:prepared(sec) for sec in (1200,3300)}

    def test_actual_initial_transfers_match_same_global_limits(self):
        evidence=[]
        for sec in (1200,3300):
            cfg,state,control,demand,follower,tuning=self.cases[sec]
            state=state.copy()
            with installed() as route:
                route.configure_known_legsplit(cfg,option(tuning),state,
                    adapter.load_optional_json(str(input_path(f'state_{sec:06d}.json'))))
                original=pickle.dumps((state,control,demand))
                adapter.install_leg_ramp_split_runtime(cfg)
                coupling=follower._wu._coupling(state,control,demand)
                model=follower._local_freeway_models['FW_E']
                landing=link_predictor.LocalLandingState(follower,model,state)
                self.assertAlmostEqual(coupling['u_on_R_F_E'],landing.replaced_coupling['R_F_E'])
                local=local_transfers(landing,control,{r:state.ramp_queue[r] for r in model.owned_ramps})
                receipts=[];actual=route.known_legsplit_commit
                def capture(s,c,rows,idx):
                    receipts.extend((r or 'free',n) for k,r,n in rows if k=='SC1004_W_out')
                    return actual(s,c,rows,idx)
                global_state=state.copy()
                with patch.object(route,'known_legsplit_commit',side_effect=capture):
                    urban.legsplit_substep_accounted(global_state,control,demand,cfg,
                        urban_step_index=round(sec/cfg.simulation.T_u_sec),ramp_release_veh_h=control.ramp_metering)
                local_values={r['target']:r['vehicles'] for r in local['ramps']};local_values['free']=local['free']
                for target,n in receipts:self.assertAlmostEqual(local_values[target],n,places=10)
                self.assertEqual(original,pickle.dumps((state,control,demand)))
                self.assertLess(landing.ledger['max_abs_residual_veh'],1e-7)
                route._known_check(route.known_local_view(landing),cfg)
                evidence.append({'start_sec':sec,'local':local_values,'global':dict(receipts),
                    'new_frozen_u_on_R_FE_vph':coupling['u_on_R_F_E'],
                    'new_replaced_coupling_R_FE_vph':landing.replaced_coupling['R_F_E'],
                    'same_current_control':True,'candidate_original_unchanged':True,
                    'scope':'W_out sub-transfer equality only. Other urban boundaries are not equal.'})
        (ROOT/'diagnostics/known_wout_local_landing_initial_results.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')

    def test_candidate_copy_pending_direct_land_and_rejection(self):
        cfg,state,control,demand,follower,tuning=self.cases[1200]
        state=state.copy();state.urban_storage_release_buffer['SC1004_W_out']={241:5.}
        with installed() as route:
            route.configure_known_legsplit(cfg,option(tuning),state,
                adapter.load_optional_json(str(input_path('state_001200.json'))))
            model=follower._local_freeway_models['FW_E']
            first=link_predictor.LocalLandingState(follower,model,state)
            second=link_predictor.LocalLandingState(follower,model,state)
            before=pickle.dumps((state,second.__dict__))
            self.assertEqual(first.arrived('SC1004_W_out'),15.)
            closed={r:cfg.network.ramp_queue_cap(r) for r in model.owned_ramps}
            first.external_ramp_q['R_F_W']=cfg.network.ramp_queue_cap('R_F_W')
            transfers=local_transfers(first,control,closed)
            self.assertEqual([r['vehicles'] for r in transfers['ramps']],[0.,0.])
            old_alias=route._known_total(route.known_local_view(first))
            first.land({'OR_F_E':1./(cfg.simulation.T_f_h*first.share['OR_F_E'])},cfg.simulation.T_f_h)
            self.assertAlmostEqual(route._known_total(route.known_local_view(first)),old_alias+1.)
            self.assertEqual(first._known_wout_alias['cohorts'][-1]['due'],241)
            self.assertEqual(first._known_wout_alias['cohorts'][-1]['target'],'free')
            self.assertAlmostEqual(first.arrived('SC1004_W_out'),first.stock['SC1004_W_out'])
            self.assertEqual(before,pickle.dumps((state,second.__dict__)))

    def test_local_landing_off_results_match_original(self):
        cfg,state,control,demand,follower,tuning=self.cases[1200]
        # Public flag OFF, not an invented fixture removal of the aliases.
        with installed() as route:
            route.configure_known_legsplit(cfg,tuning,state,
                adapter.load_optional_json(str(input_path('state_001200.json'))))
        model=follower._local_freeway_models['FW_E']
        original=link_predictor.LocalLandingState(follower,model,state)
        a={r:state.ramp_queue[r] for r in model.owned_ramps}
        original.advance(control,a,cfg.simulation.T_u_h)
        with installed():
            candidate=link_predictor.LocalLandingState(follower,model,state)
            b={r:state.ramp_queue[r] for r in model.owned_ramps}
            candidate.advance(control,b,cfg.simulation.T_u_h)
            self.assertEqual(a,b)
            for name in ('stock','pending','ledger','replaced_coupling','step'):
                self.assertEqual(getattr(original,name),getattr(candidate,name))
            self.assertFalse(hasattr(candidate,'_known_wout_alias'))


if __name__=='__main__':unittest.main()
