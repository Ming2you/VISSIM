"""T6 runner mechanics (t6_guarded_decision.py) on a fake adapter.

The real T6 needs a G1 state (V3). Here a fake adapter main() calls
configure_runtime exactly as AD:12955-12956 does (import at call time), then
hits a silent fallback that a decision fallback swallows, or the 21-cell
domain builder. The runner must enter the guards after configure_runtime,
record what the adapter swallowed, restore every hook and report by exit code.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

import n31_fixtures as fx
import t6_guarded_decision as t6

FAKE = 'n31_fake_adapter_for_t6'


def fake_main():
    from evaluation.controllers.runtime_setup import configure_runtime
    from evaluation.controllers import joint_owner_neighbors as jon
    from src.models import state as st
    args = sys.argv[1:]
    cfg = types.SimpleNamespace(
        network=types.SimpleNamespace(freeway_segment_params={'FW_E': [{}] * 31, 'FW_W': [{}] * 31},
                                      freeway_segment_lanes={'FW_E': [4.0] * 21, 'FW_W': [3.0] * 21},
                                      lane_plant_enabled=True,
                                      freeway_vsl_zone_head_of_cell={'FW_E': [0] * 5 + [5] * 5 + [10] * 11}),
        freeway_follower=types.SimpleNamespace(vsl_set=[60.0, 80.0, 110.0]))
    if '--no-configure' not in args:
        configure_runtime(None, cfg)
    control = types.SimpleNamespace(vsl={'FW_E': 90.0})
    if '--bad-vsl' in args:
        try:
            st.segment_vsl(control, 'FW_E', 23, cfg)
        except Exception:   # a hold fallback that swallows the error
            pass
    if '--domain' in args:
        try:
            jon.build_current_freeway_domain(None, 'FW_E', None, None, None, None)
        except Exception:
            pass
    if '--fail' in args:
        raise SystemExit(4)


class T6RunnerTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        fx.component()   # the reference-config hooks the guards wrap

    def setUp(self):
        from evaluation.controllers import runtime_setup
        self.dir = Path(tempfile.mkdtemp(prefix='_tmp_', dir=fx.HERE))
        self.addCleanup(shutil.rmtree, self.dir, True)
        module = types.ModuleType(FAKE)
        module.main = fake_main
        sys.modules[FAKE] = module
        self.addCleanup(sys.modules.pop, FAKE, None)
        self.configured = []
        saved = runtime_setup.configure_runtime
        runtime_setup.configure_runtime = lambda adapter, cfg, *a, **k: self.configured.append(cfg) or ('state', {}, {})
        self.addCleanup(setattr, runtime_setup, 'configure_runtime', saved)
        self.stub = runtime_setup.configure_runtime
        from evaluation.controllers import joint_owner_neighbors as jon
        from src.models import metanet as mn
        from src.models import state as st
        self.hooks = (st.segment_vsl, mn._ramp_merge_index, mn.effective_lane_profile, jon.build_current_freeway_domain)

    def run_fake(self, *args):
        path = self.dir / 'record.json'
        code = t6.run(path, list(args), target=FAKE)
        return code, json.loads(path.read_text(encoding='utf-8'))

    def assert_restored(self):
        from evaluation.controllers import runtime_setup
        from evaluation.controllers import joint_owner_neighbors as jon
        from src.models import metanet as mn
        from src.models import state as st
        self.assertIs(runtime_setup.configure_runtime, self.stub)
        now = (st.segment_vsl, mn._ramp_merge_index, mn.effective_lane_profile, jon.build_current_freeway_domain)
        for a, b in zip(now, self.hooks):
            self.assertIs(a, b)

    def test_clean_decision_passes(self):
        code, record = self.run_fake('--state-json', 'x.json')
        self.assertEqual(code, 0)
        self.assertTrue(record['passed'])
        self.assertTrue(record['guards_entered'])
        self.assertEqual(len(self.configured), 1)
        self.assertEqual(record['argv'], ['--state-json', 'x.json'])
        self.assertEqual(record['full_cfg_fd_rows'], {'FW_E': 31, 'FW_W': 31})
        self.assertEqual(record['full_cfg_lane_rows'], {'FW_E': 21, 'FW_W': 21})
        self.assert_restored()

    def test_swallowed_fallback_is_recorded(self):
        code, record = self.run_fake('--bad-vsl')
        self.assertEqual(code, 2)
        self.assertFalse(record['passed'])
        self.assertEqual(record['exit_status'], 0)
        self.assertEqual(len(record['guard_errors']), 1)
        self.assertIn('outside the 21-cell zone table', record['guard_errors'][0])
        self.assert_restored()

    def test_21_cell_domain_call_fails(self):
        code, record = self.run_fake('--domain')
        self.assertEqual(code, 2)
        self.assertEqual(record['build_current_freeway_domain_calls'], 1)
        self.assert_restored()

    def test_adapter_failure(self):
        code, record = self.run_fake('--fail')
        self.assertEqual((code, record['exit_status'], record['passed']), (1, 4, False))
        self.assert_restored()

    def test_guards_never_entered(self):
        code, record = self.run_fake('--no-configure')
        self.assertEqual(code, 2)
        self.assertFalse(record['guards_entered'])
        self.assert_restored()

    def test_usage(self):
        self.assertEqual(t6.main(['record.json', 'no-separator']), 3)


if __name__ == '__main__':
    unittest.main()
