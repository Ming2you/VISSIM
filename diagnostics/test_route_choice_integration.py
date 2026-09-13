"""Counterfactual route-envelope regression through the real shared runtime.

These route2/3 labels are explicit synthetic fixtures, not observed beta-run
destinations. Physical1350 records and current action remain the actual ones.
"""
from pathlib import Path
import json,os,pickle,tempfile,unittest
from diagnostics.test_route_choice_corridor import ROOT,current_routes
from diagnostics.probe_model_area_integration import build_projected


class IntegrationTests(unittest.TestCase):
    def test_current_route_schema_reaches_canonical450_endpoint_without_redraw(self):
        from evaluation.controllers import vissim_stackelberg_adapter as adapter,area_runtime,route_choice_corridor
        from src.models.state import ControlAction
        from src.models.demand import DemandStep
        run=ROOT/'evaluation/runs/codex_area_beta0_retry_s13_20260910/decisions_codex_area_beta0_retry_s13_20260910'
        raw=json.loads((run/'state_001350.json').read_text(encoding='utf-8-sig'))
        tuning=json.loads((ROOT/'diagnostics/route_choice_integration_config.json').read_text(encoding='utf-8-sig'))
        tuning['urban']['route_choice_corridor']['unknown_policy']='error'
        outputs={}
        os.environ['RW_MAINLINE_SG_ONLY']='1';os.environ['RW_OFFSET_WRITER']='experiment'
        with tempfile.TemporaryDirectory(prefix='choice_synthetic_route_',dir=ROOT/'diagnostics') as folder:
            directory=Path(folder).resolve()
            self.assertTrue(directory.is_relative_to((ROOT/'diagnostics').resolve()))
            config=directory/'config.json';config.write_text(json.dumps(tuning),encoding='utf-8')
            for route in (2,3):
                candidate_raw=dict(raw,vehicle_routes=current_routes(raw,{4834:route}))
                state_path=directory/f'state_1350_synthetic_route{route}.json'
                state_path.write_text(json.dumps(candidate_raw),encoding='utf-8')
                cfg,state,detectors,_,observed,_,metadata=build_projected(config,state_path,run/'action_001200.json',fixture_inputs=False)
                choice=route_choice_corridor.diagnostics(state,cfg)
                self.assertEqual(choice['route_choice_held_unknown_route_veh'],0.)
                local=[c for c in state.route_choice_corridor_state['cohorts'] if c['storage']=='SC1004_to_SC1005']
                self.assertEqual([c['route'] for c in local],[str(route)])
                self.assertEqual([c['source'] for c in local],['observed_current_route'])
                action=adapter.control_from_json(run/'action_001200.json',cfg,ControlAction)
                forecast=adapter.demand_from_state(observed,cfg,DemandStep,3)
                from src.controllers.rollout_endpoint import ObjectiveSpec,evaluate_price_point
                frozen=pickle.dumps(state)
                point=evaluate_price_point(state,action,forecast,[],ObjectiveSpec(cfg,depth_override=3,score_mode='raw'))
                self.assertEqual(frozen,pickle.dumps(state))
                for future in point.states:
                    future._control_area_ledger.assert_stocks(area_runtime.model_inventory(future,cfg))
                    self.assertEqual(route_choice_corridor.diagnostics(future,cfg)['route_choice_held_unknown_route_veh'],0.)
                outputs[str(route)]={'objective':point.objective,'area':point.control_area,
                                     'initial_choice':choice,'final_choice':route_choice_corridor.diagnostics(point.states[-1],cfg)}
        (ROOT/'diagnostics/route_choice_synthetic_current_route_450.json').write_text(json.dumps({
            'kind':'synthetic current-route schema integration, not measured destination evidence',
            'physical_snapshot':'beta0_retry1350','synthetic_vehicle_id':4834,'seconds':450,'cases':outputs},indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':unittest.main()
