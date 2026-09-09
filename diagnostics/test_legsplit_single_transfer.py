"""Both real full-search failures must conserve with one accepted W_out transfer."""
import ast
import copy
import json
from pathlib import Path
import pickle
import sys
from types import FunctionType
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'diagnostics'), str(ROOT / 'vendor/NumSim-mine')]


class SingleTransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from evaluation.controllers import runtime_setup, vissim_stackelberg_adapter as adapter
        cls.endpoint = pickle.loads((ROOT / 'diagnostics/area_main_preflight/failed_endpoint_25540.pkl').read_bytes())
        cfg = cls.endpoint['objective_spec'].cfg
        from evaluation.controllers import area_meter_finalization
        from diagnostics.review_fixtures import fixture_path
        decisions = ROOT/'evaluation/runs/codex_n7_pure_s13_20260910/decisions_codex_n7_pure_s13_20260910'
        raw = json.loads(fixture_path(decisions/'state_003300.json').read_text(encoding='utf-8'))
        previous_path = fixture_path(decisions/'action_003150.json')
        tuning = json.loads((ROOT/'diagnostics/fixtures/area_baseline_before_route_choice_beta300.json').read_text(encoding='utf-8'))
        mapping = json.loads((ROOT/tuning['mapping_json']).read_text(encoding='utf-8'))
        calibration = adapter.deep_update(json.loads((ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json').read_text(encoding='utf-8')),
                                          tuning.get('calibration_override', {}))
        area_meter_finalization.configure(adapter,cfg,tuning,mapping,raw,previous_path,cls.endpoint['state'],calibration)
        runtime_setup.install_worker_runtime(adapter, cfg, {'network_path': str(ROOT / 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx')}, {})

    def test_actual_3300_full_candidate_closes_all_stocks(self):
        from src.controllers.rollout_endpoint import evaluate_price_point
        from evaluation.controllers.area_runtime import model_inventory
        p = copy.deepcopy(self.endpoint)
        result = evaluate_price_point(*(p[key] for key in ('state', 'previous', 'forecast', 'action_schedule', 'objective_spec')))
        result.states[-1]._control_area_ledger.assert_stocks(model_inventory(result.states[-1], p['objective_spec'].cfg))
        self.assertFalse(result.aborted)

    def test_actual_1200_ramp_competition_conserves_source_and_receiver(self):
        p = pickle.loads((ROOT / 'diagnostics/area_main_preflight/first_ramp_clip_50548.pkl').read_bytes())
        from evaluation.controllers import urban_flow_accounting as urban
        from evaluation.controllers.area_runtime import model_inventory
        urban.legsplit_substep_accounted(p['state'], p['control'], p['demand'], p['cfg'], *p['args'], **p['kwargs'])
        inventory = model_inventory(p['state'], p['cfg'])
        for key, row in p['state']._control_area_ledger.stocks.items():
            if not key.startswith('merge_pending:'):
                self.assertAlmostEqual(sum(row.values()), inventory.get(key, 0), places=6, msg=key)

    def test_default_body_does_not_defer_without_explicit_wrapper_argument(self):
        from evaluation.controllers import urban_flow_accounting as urban
        from fixed_source_reference import source as fixed_source
        source = fixed_source('evaluation/controllers/urban_flow_accounting.py')
        node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'urban_substep_accounted')
        namespace = dict(vars(urban))
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<pre-single-transfer body>', 'exec'), namespace)
        ref = namespace[node.name]
        reference = FunctionType(ref.__code__, vars(urban), node.name, ref.__defaults__, ref.__closure__)
        p = pickle.loads((ROOT / 'diagnostics/area_main_preflight/first_ramp_clip_50548.pkl').read_bytes())
        # Compare the unchanged default body with corridor physics disabled;
        # that opt-in subsystem did not exist in the fixed reference.
        if hasattr(p['cfg'].network, 'sc2001_corridor'):
            del p['cfg'].network.sc2001_corridor
        a, b = p['state'].copy(), p['state'].copy()
        ra = reference(a, p['control'], p['demand'], p['cfg'], *p['args'], **p['kwargs'])
        rb = urban.urban_substep_accounted(b, p['control'], p['demand'], p['cfg'], *p['args'], **p['kwargs'])
        self.assertEqual(ra, rb)
        self.assertEqual({k:v for k,v in vars(a).items() if k != '_control_area_ledger'},
                         {k:v for k,v in vars(b).items() if k != '_control_area_ledger'})
        self.assertEqual(vars(a._control_area_ledger), vars(b._control_area_ledger))


if __name__ == '__main__':
    unittest.main(verbosity=2)
