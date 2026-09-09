"""Exercise the exact main exception handler with strict/legacy configurations."""
import ast
import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'diagnostics')]
from fixed_source_reference import source as fixed_source
from evaluation.controllers.control_area_objective import MembershipError
PATH = ROOT / 'evaluation/controllers/vissim_stackelberg_adapter.py'


def handler(source):
    main = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    return next(n for n in ast.walk(main) if isinstance(n, ast.ExceptHandler) and n.name == 'exc'
                and any(isinstance(x, ast.Constant) and x.value == 'fallback_fixed' for x in ast.walk(n)))


def execute(source, flag, error):
    network = SimpleNamespace()
    if flag is not None:
        network.control_area_enabled = flag
    namespace = {'args': SimpleNamespace(controller='wu-link'), 'cfg': SimpleNamespace(network=network),
        'diagnostic_profile': SimpleNamespace(CONTROLLERS=('diagnostic-x',)),
        'diagnostic_signal_profile': SimpleNamespace(CONTROLLER='diagnostic-signal'),
        'metadata': {}, 'ControlAction': SimpleNamespace(fixed=lambda cfg: 'fixed'),
        'fail': lambda: (_ for _ in ()).throw(error)}
    tree = ast.Module(body=[ast.Try(body=[ast.Expr(value=ast.Call(func=ast.Name(id='fail', ctx=ast.Load()), args=[], keywords=[]))],
        handlers=[copy.deepcopy(handler(source))], orelse=[], finalbody=[])], type_ignores=[])
    exec(compile(ast.fix_missing_locations(tree), '<exact reviewed main error handler>', 'exec'), namespace)
    return namespace['control'], namespace['metadata']


class AreaFailfastTests(unittest.TestCase):
    def test_strict_membership_and_other_errors_propagate_unchanged(self):
        source = PATH.read_text(encoding='utf-8')
        for error in (MembershipError('positive unresolved crossing'), RuntimeError('worker bootstrap failed')):
            with self.assertRaises(type(error)) as raised:
                execute(source, True, error)
            self.assertIs(raised.exception, error)

    def test_absent_and_false_keep_legacy_fallback_identical(self):
        source = PATH.read_text(encoding='utf-8')
        for flag in (None, False):
            error = MembershipError('fixture failure')
            self.assertEqual(execute(source, flag, error), execute(fixed_source('evaluation/controllers/vissim_stackelberg_adapter.py'), flag, error))


if __name__ == '__main__':
    unittest.main(verbosity=2)
