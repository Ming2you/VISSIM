"""Fresh actual CLI stops before config switches/model imports; no model/native."""
import importlib
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / 'evaluation/controllers/vissim_stackelberg_adapter.py'
CANONICAL = 'evaluation.controllers.vissim_stackelberg_adapter'
ATTRIBUTE = 'vissim_stackelberg_adapter'


def child(case, directory):
    """Exercise actual main and helper, observing just two exact call boundaries."""
    sys.path.insert(0, str(ROOT))
    work = Path(directory)
    enabled = not case.startswith('off_')
    tuning = {'adapter': {'joint_owner_game': {}}} if enabled else {'adapter': {}}
    if case == 'off_none':
        tuning['adapter']['joint_owner_game'] = None
    for name, value in (('state', {}), ('mapping', {}), ('calibration', {}), ('tuning', tuning)):
        (work / (name + '.json')).write_text(json.dumps(value), encoding='utf-8')
    preload = case in ('on_conflict_module', 'on_conflict_package', 'off_preloaded')
    old_module = importlib.import_module(CANONICAL) if preload else None
    package = importlib.import_module('evaluation.controllers')
    if case == 'on_conflict_package':
        # A real imported-module reference can outlive its sys.modules slot.
        del sys.modules[CANONICAL]
    missing = object()
    before_slot = sys.modules.get(CANONICAL, missing)
    before_attr = getattr(package, ATTRIBUTE, missing)
    seen = {'bind': 0, 'checkpoint': 0}

    class BeforeModel(BaseException):
        pass

    def no_models():
        assert not any(name == 'src' or name.startswith('src.') for name in sys.modules), 'Model imported before checkpoint'

    def profile(frame, event, arg):
        if event != 'call' or frame.f_globals.get('__name__') != '__main__':
            return
        name = frame.f_code.co_name
        if name not in ('bind_joint_cli_module', 'install_config_switches'):
            return
        assert Path(frame.f_code.co_filename).resolve() == ADAPTER.resolve()
        current = sys.modules['__main__']
        assert frame.f_globals is vars(current)
        no_models()
        if name == 'bind_joint_cli_module':
            seen['bind'] += 1
            assert seen['bind'] == 1
            assert frame.f_locals['tuning'] == tuning
            if case == 'on_same':
                sys.modules[CANONICAL] = current
                setattr(package, ATTRIBUTE, current)
            return
        seen['checkpoint'] += 1
        assert seen == {'bind': 1, 'checkpoint': 1}, 'Alias helper must precede switches'
        if enabled:
            assert sys.modules[CANONICAL] is current
            assert getattr(package, ATTRIBUTE) is current
            canonical = importlib.import_module(CANONICAL)
            assert canonical is current
            assert canonical.install_config_switches.__globals__ is vars(current)
            assert canonical._PHASE_VECTOR_FOLLOWER is current._PHASE_VECTOR_FOLLOWER
            assert canonical._CFG_SWITCHES is current._CFG_SWITCHES
        else:
            assert sys.modules.get(CANONICAL, missing) is before_slot
            assert getattr(package, ATTRIBUTE, missing) is before_attr
        sys.setprofile(None)
        raise BeforeModel()

    sys.argv = [str(ADAPTER), '--controller', 'wu-link',
        '--state-json', str(work / 'state.json'), '--mapping-json', str(work / 'mapping.json'),
        '--calibration-json', str(work / 'calibration.json'), '--tuning-json', str(work / 'tuning.json'),
        '--out-action-json', str(work / 'action.json'), '--out-action-csv', str(work / 'action.csv')]
    caught = None
    sys.setprofile(profile)
    try:
        runpy.run_path(str(ADAPTER), run_name='__main__')
    except BeforeModel:
        caught = 'checkpoint'
    except ValueError as exc:
        if case not in ('on_conflict_module', 'on_conflict_package'):
            raise
        assert 'module' in str(exc).lower() or 'identity' in str(exc).lower(), str(exc)
        caught = 'conflict'
    finally:
        sys.setprofile(None)
    no_models()
    assert not (work / 'action.json').exists() and not (work / 'action.csv').exists()
    if case in ('on_conflict_module', 'on_conflict_package'):
        assert caught == 'conflict' and seen == {'bind': 1, 'checkpoint': 0}
        assert sys.modules.get(CANONICAL, missing) is before_slot
        assert getattr(package, ATTRIBUTE, missing) is before_attr
        assert old_module is before_attr
    else:
        assert caught == 'checkpoint' and seen == {'bind': 1, 'checkpoint': 1}
    print(json.dumps({'case': case, 'passed': True, 'stop': caught,
                      'model_imported': False, 'action_files_created': False}))


class JointCliIdentityTests(unittest.TestCase):
    def check(self, case):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(Path(__file__).resolve()),
                                     '--child', case, directory], cwd=ROOT,
                                    capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        rows = [json.loads(row) for row in result.stdout.splitlines() if row.startswith('{')]
        self.assertEqual(len(rows), 1, result.stdout)
        self.assertTrue(rows[0]['passed'])
        self.assertFalse(rows[0]['model_imported'])
        self.assertFalse(rows[0]['action_files_created'])

    def test_on_registers_actual_executing_cli_module_before_switches(self):
        self.check('on_absent')

    def test_on_accepts_existing_same_module_in_both_slots(self):
        self.check('on_same')

    def test_on_rejects_preimported_module_or_stale_package_reference(self):
        for case in ('on_conflict_module', 'on_conflict_package'):
            with self.subTest(case=case):
                self.check(case)

    def test_off_preserves_absent_and_existing_canonical_slots(self):
        for case in ('off_absent', 'off_none', 'off_preloaded'):
            with self.subTest(case=case):
                self.check(case)


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--child':
        child(sys.argv[2], sys.argv[3])
    else:
        unittest.main()
