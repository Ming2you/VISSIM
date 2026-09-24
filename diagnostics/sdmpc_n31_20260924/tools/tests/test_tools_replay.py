"""WP-D D1/D2: make_replay_state_v2.py (prepare/compare) and replay_decision_n31.ps1 (fake adapter)."""
from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import synthetic_run as sr  # noqa: E402
import make_replay_state_v2 as rs  # noqa: E402
from n31_common import ToolError, file_sha256, oc  # noqa: E402

POWERSHELL = shutil.which('powershell') or r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
T, P = 900, 750


def write_native_decision(syn, t=T, previous=P, objective=393.91612458424544):
    """What the native run leaves: action_T.{json,csv}, progress, the previous action and its receipt."""
    d = syn.decisions
    for sec in (previous, t):
        action = {'N_P_star': 5.0 + sec, 'N_UF_star': 1.0, 'ramp_metering': {'RM_C10480': 1512.0},
                  'vsl': {'FW_W__seg0': 110.0}, 'green_times': {}, 'offsets': {}, 'inflow_outflow_allocation': {},
                  'metadata': {'decision_wall_sec': 1.0, 'sdmpc_state': None if sec == previous else {'x': 1},
                               **({} if sec == previous else {'sdmpc_active': True})}}
        (d / f'action_{sec:06d}.json').write_text(json.dumps(action), encoding='utf-8')
        rows = ['kind,id,dsd_no,sc_no,link,lane,speed_kph,p1_green,p2_green,p3_green,p4_green,offset,rate_vph,green_sec,metadata']
        rows += [f'vsl,RW_FW_W_S0,{i},,26,1,110.0,,,,,,,,ok' for i in range(rs.VSL_ROWS)]
        rows += [f'ramp_meter,RM_C1048{i},,,,,,,,,,,1512.0,,ok' for i in range(rs.METER_ROWS)]
        (d / f'action_{sec:06d}.csv').write_text('\n'.join(rows) + '\n', encoding='utf-8')
    csv_prev = d / f'action_{previous:06d}.csv'
    receipt = f'{float(previous)}\r\n{csv_prev}\r\n{csv_prev.stat().st_size}\r\n'
    (d / f'action_{previous:06d}.json.applied').write_bytes(receipt.encode('utf-16'))
    (d / f'action_{t:06d}.joint.progress.jsonl').write_text(
        json.dumps({'stage': 'sdmpc_completed', 'objective': objective, 'held_objective': 395.5}) + '\n', encoding='utf-8')


class Prepare(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='n31_replay_'))
        cls.syn = sr.SyntheticRun(cls.tmp)
        write_native_decision(cls.syn)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_prepare_isolates_and_pins(self):
        out = self.tmp / 'r_ok'
        manifest = rs.prepare(self.syn.decisions, T, out)
        state = json.loads((out / f'state_{T:06d}.json').read_text(encoding='utf-8'))
        source = json.loads((self.syn.decisions / f'state_{T:06d}.json').read_text(encoding='utf-8'))
        self.assertEqual(state[oc.RAW_STATE_KEY]['directory'], str(out))
        self.assertEqual(state['lane_plant_observation']['directory'], str(out / 'lane_observations'))
        # only the two directories differ
        a, b = copy.deepcopy(state), copy.deepcopy(source)
        for doc in (a, b):
            doc[oc.RAW_STATE_KEY].pop('directory')
            doc['lane_plant_observation'].pop('directory')
        self.assertEqual(a, b)
        oc.load_bundle(state)                                     # every pin verifies inside out
        index = json.loads((out / 'obs150' / 'mer_index.json').read_text(encoding='utf-8'))
        self.assertEqual(index['entries'][-1]['sim_sec'], T)      # the later 1050 entry is cut
        self.assertEqual(manifest['mer_index'], {'entries_kept': 7, 'entries_in_run_index': 8,
                                                 'sha256': file_sha256(out / 'obs150' / 'mer_index.json')})
        self.assertEqual(manifest['previous_sec'], P)
        self.assertEqual(Path(manifest['previous_action']['read_from']), self.syn.decisions / f'action_{P:06d}.json')
        self.assertIn('.json.applied', manifest['evidence']['previous'])
        self.assertFalse((out / 'obs150' / oc.derived_path(T).split('/')[-1]).exists())   # the replay writes it
        self.assertTrue((out / 'original' / 'obs150' / f'derived_{T:06d}.json').is_file())
        for link in manifest['links']:
            self.assertEqual(file_sha256(out / Path(*link['rel'].split('/'))), link['sha256'])
        self.assertEqual({l['method'] for l in manifest['links']}, {'hardlink'})

    def test_prepare_refuses(self):
        out = self.tmp / 'r_twice'
        rs.prepare(self.syn.decisions, T, out)
        with self.assertRaises(ToolError):
            rs.prepare(self.syn.decisions, T, out)                 # never reused
        with self.assertRaises(ToolError):
            rs.prepare(self.syn.decisions, 450 + 1, self.tmp / 'r_bad')   # no such state
        state = self.syn.decisions / f'state_{T:06d}.json'
        original = state.read_bytes()
        try:
            doc = json.loads(original)
            doc[oc.RAW_STATE_KEY]['frames']['current']['sha256'] = 'f' * 64
            state.write_text(json.dumps(doc), encoding='utf-8')
            with self.assertRaises(oc.ObsContractError):
                rs.prepare(self.syn.decisions, T, self.tmp / 'r_pin')
        finally:
            state.write_bytes(original)

    def fake_replay(self, out, *, derived_change=None, csv_change=False, objective=393.91612458424544,
                    write_derived=True, write_progress=True, sdmpc_active=True):
        """What a correct adapter run in the replay folder writes."""
        state = json.loads((out / f'state_{T:06d}.json').read_text(encoding='utf-8'))
        derived = copy.deepcopy(self.syn.derived)
        derived['inputs']['raw_sha256'] = oc.canonical_sha256(state[oc.RAW_STATE_KEY])
        if derived_change:
            derived_change(derived)
        if write_derived:
            oc.resolve(state[oc.RAW_STATE_KEY], oc.derived_path(T)).write_bytes(oc.canonical_json_bytes(derived) + b'\n')
        replay = out / rs.REPLAY_SUBDIR
        replay.mkdir()
        for suffix in ('.json', '.csv'):
            shutil.copyfile(self.syn.decisions / f'action_{T:06d}{suffix}', replay / f'action_{T:06d}{suffix}')
        if not sdmpc_active:
            action = json.loads((replay / f'action_{T:06d}.json').read_text(encoding='utf-8'))
            action['metadata'].pop('sdmpc_active')
            (replay / f'action_{T:06d}.json').write_text(json.dumps(action), encoding='utf-8')
        if csv_change:
            with open(replay / f'action_{T:06d}.csv', 'a', encoding='utf-8') as f:
                f.write('signal,x\n')
        if write_progress:
            (replay / f'action_{T:06d}.joint.progress.jsonl').write_text(
                json.dumps({'stage': 'sdmpc_completed', 'objective': objective, 'held_objective': 395.5}) + '\n',
                encoding='utf-8')

    @staticmethod
    def as_warmup_original(out):
        """original/ as a decision without SDMPC: no progress log, no metadata.sdmpc_active. The files
        are hard links into the run folder, so each is unlinked before it is replaced."""
        original = out / 'original'
        os.remove(original / f'action_{T:06d}.joint.progress.jsonl')
        action = json.loads((original / f'action_{T:06d}.json').read_text(encoding='utf-8'))
        action['metadata'].pop('sdmpc_active')
        os.remove(original / f'action_{T:06d}.json')
        (original / f'action_{T:06d}.json').write_text(json.dumps(action), encoding='utf-8')

    def test_compare_identical_and_each_difference(self):
        out = self.tmp / 'r_cmp'
        rs.prepare(self.syn.decisions, T, out)
        self.fake_replay(out)
        report = rs.compare(out, 110.0)
        self.assertEqual(report['verdict'], 'IDENTICAL', report)
        self.assertTrue(report['checks']['derived']['raw_sha256_bound'])
        for name, kwargs in {'derived': {'derived_change': lambda d: d['off_split']['10485'].update(off_veh=99)},
                             'action_csv': {'csv_change': True},
                             'objective': {'objective': 393.9161245842455}}.items():      # last digits differ
            case = self.tmp / f'r_cmp_{name}'
            rs.prepare(self.syn.decisions, T, case)
            self.fake_replay(case, **kwargs)
            report = rs.compare(case, 110.0)
            self.assertEqual(report['verdict'], 'DIFFERENT', name)
            self.assertIs(report['checks'][name]['ok'], False, name)
        case = self.tmp / 'r_cmp_vsl'
        rs.prepare(self.syn.decisions, T, case)
        self.fake_replay(case)
        self.assertEqual(rs.compare(case, 120.0)['checks']['action_contract']['ok'], False)

    def test_missing_on_both_sides_is_never_identical(self):
        """Review fix 3: 'neither side has it' is not a pass for the SDMPC objective or the derived file."""
        run_progress = self.syn.decisions / f'action_{T:06d}.joint.progress.jsonl'
        case = self.tmp / 'r_none_objective'
        rs.prepare(self.syn.decisions, T, case)
        os.remove(case / 'original' / run_progress.name)          # only the hard link in original/
        self.fake_replay(case, write_progress=False)
        report = rs.compare(case, 110.0)
        self.assertEqual(report['verdict'], 'DIFFERENT')
        self.assertIs(report['checks']['objective']['ok'], False)
        self.assertTrue(report['checks']['objective']['required'])
        self.assertTrue(run_progress.is_file())                    # the run folder is untouched
        # the replay derived nothing (it used to raise) / the native run derived nothing (it used to pass)
        case = self.tmp / 'r_no_replay_derived'
        rs.prepare(self.syn.decisions, T, case)
        self.fake_replay(case, write_derived=False)
        report = rs.compare(case, 110.0)
        self.assertEqual((report['verdict'], report['checks']['derived']['ok']), ('DIFFERENT', False))
        self.assertEqual(report['checks']['derived']['replay_present'], False)
        case = self.tmp / 'r_no_original_derived'
        rs.prepare(self.syn.decisions, T, case)
        os.remove(case / 'original' / 'obs150' / f'derived_{T:06d}.json')
        self.fake_replay(case)
        report = rs.compare(case, 110.0)
        self.assertEqual((report['verdict'], report['checks']['derived']['ok']), ('DIFFERENT', False))
        self.assertEqual(report['checks']['derived']['original_present'], False)

    def test_warmup_decision_has_no_objective(self):
        case = self.tmp / 'r_warmup'
        rs.prepare(self.syn.decisions, T, case)
        self.as_warmup_original(case)
        self.fake_replay(case, write_progress=False, sdmpc_active=False)
        report = rs.compare(case, 110.0)
        self.assertEqual(report['verdict'], 'IDENTICAL', report)
        self.assertIsNone(report['checks']['objective']['ok'])
        self.assertFalse(report['checks']['objective']['required'])
        # ... but a replay that ran SDMPC where the original did not must show its objective on both sides
        case = self.tmp / 'r_warmup_vs_sdmpc'
        rs.prepare(self.syn.decisions, T, case)
        self.as_warmup_original(case)
        self.fake_replay(case)
        self.assertIs(rs.compare(case, 110.0)['checks']['objective']['ok'], False)
        self.assertTrue((self.syn.decisions / f'action_{T:06d}.joint.progress.jsonl').is_file())
        self.assertTrue(json.loads((self.syn.decisions / f'action_{T:06d}.json').read_text(encoding='utf-8'))
                        ['metadata']['sdmpc_active'])


FAKE_ADAPTER = textwrap.dedent(r'''
    """Test double of vissim_stackelberg_adapter.py: records argv/env, writes what a correct run writes."""
    import argparse, json, os, shutil, sys
    from pathlib import Path
    sys.path.insert(0, os.environ['N31_TEST_ROOT'])
    from evaluation.controllers import obs150_contract as oc
    p = argparse.ArgumentParser()
    for a in ('--state-json', '--out-action-json', '--out-action-csv', '--mapping-json', '--controller',
              '--detector-mapping-json', '--calibration-json', '--tuning-json', '--previous-action-json', '--mode'):
        p.add_argument(a, default=None)
    args = p.parse_args()
    state = json.loads(Path(args.state_json).read_text(encoding='utf-8'))
    obs = state[oc.RAW_STATE_KEY]
    run = Path(os.environ['N31_TEST_DECISIONS'])
    derived = json.loads((run / 'obs150' / f'derived_{obs["sim_sec"]:06d}.json').read_text(encoding='utf-8'))
    derived['inputs']['raw_sha256'] = oc.canonical_sha256(obs)
    oc.resolve(obs, oc.derived_path(obs['sim_sec'])).write_bytes(oc.canonical_json_bytes(derived) + b'\n')
    t = obs['sim_sec']
    shutil.copyfile(run / f'action_{t:06d}.json', args.out_action_json)
    shutil.copyfile(run / f'action_{t:06d}.csv', args.out_action_csv)
    shutil.copyfile(run / f'action_{t:06d}.joint.progress.jsonl', args.out_action_json[:-5] + '.joint.progress.jsonl')
    Path(args.out_action_json).with_name('argv.json').write_text(json.dumps({
        'args': vars(args), 'cwd': os.getcwd(),
        'rw_env': {k: v for k, v in os.environ.items() if k.startswith('RW_')}}), encoding='utf-8')
''')


class ReplayScript(unittest.TestCase):
    """replay_decision_n31.ps1 end to end with a fake adapter (no VISSIM, no SDMPC)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='n31_replay_ps_'))
        cls.syn = sr.SyntheticRun(cls.tmp)
        write_native_decision(cls.syn)
        cls.root_a = cls.tmp / 'frz_a'                  # the tree the run used (provenance workspace_root)
        cls.root_b = cls.tmp / 'w_b'                    # a code-change tree
        for root in (cls.root_a, cls.root_b):
            (root / 'evaluation' / 'controllers').mkdir(parents=True)
            (root / 'evaluation' / 'controllers' / 'vissim_stackelberg_adapter.py').write_text(FAKE_ADAPTER, encoding='utf-8')
            for name in ('x_tuning.json', 'x_mapping.json', 'x_calibration.json'):
                (root / name).write_text('{"config_overrides": {"freeway_follower": {"vsl_set": [60, 80, 110]}}}',
                                         encoding='utf-8')
        env = {'RW_PYTHON': sys.executable, 'RW_OBSERVATION_CADENCE': 'decision150', 'RW_OFFSET_WRITER': 'experiment'}
        doc = {'run_id': 'run1', 'name': cls.syn.name, 'workspace_root': str(cls.root_a), 'env': env,
               'files': {'generated_vbs_config': {'path': str(cls.syn.runner_config)},
                         'tuning': {'path': str(cls.root_a / 'x_tuning.json')},
                         'control_mapping': {'path': str(cls.root_a / 'x_mapping.json')},
                         'calibration': {'path': str(cls.root_a / 'x_calibration.json')}}}
        cls.syn.provenance_path.write_text(json.dumps(doc), encoding='utf-8')
        (cls.syn.run / 'launch_plan.json').write_text(json.dumps(
            {'controller': 'wu-link', 'warmup_controller': 'no-control', 'control_start_sec': 900}), encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def replay(self, replay_dir, *extra):
        env = {**os.environ, 'N31_TEST_ROOT': str(sr.ROOT), 'N31_TEST_DECISIONS': str(self.syn.decisions),
               'RW_LEAK': 'must-not-survive', 'PYTHONDONTWRITEBYTECODE': '1'}
        return subprocess.run([POWERSHELL, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                               str(HERE.parent / 'replay_decision_n31.ps1'), '-ReplayDir', str(replay_dir), *extra],
                              capture_output=True, text=True, env=env, timeout=600)

    def test_replay_in_run_tree(self):
        out = self.tmp / 'ra'
        rs.prepare(self.syn.decisions, T, out)
        done = self.replay(out)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn('ROOT_NOT_FROZEN', done.stdout)
        self.assertIn('REPLAY_COMPARE verdict=IDENTICAL', done.stdout)
        argv = json.loads((out / 'replay' / 'argv.json').read_text(encoding='utf-8'))
        a = argv['args']
        self.assertEqual(a['controller'], 'wu-link')
        self.assertEqual(Path(a['previous_action_json']), self.syn.decisions / f'action_{P:06d}.json')
        self.assertEqual(Path(a['state_json']), out / f'state_{T:06d}.json')
        self.assertEqual(a['detector_mapping_json'], r'evaluation\x\detector_map.json')
        self.assertEqual(Path(a['tuning_json']), self.root_a / 'x_tuning.json')
        self.assertIsNone(a['mode'])
        self.assertEqual(Path(argv['cwd']), self.root_a)
        self.assertEqual(argv['rw_env'], {'RW_PYTHON': sys.executable, 'RW_OBSERVATION_CADENCE': 'decision150',
                                          'RW_OFFSET_WRITER': 'experiment'})

    def test_code_change_root_rebases_and_warmup_controller(self):
        out = self.tmp / 'rb'
        rs.prepare(self.syn.decisions, T, out)
        done = self.replay(out, '-Root', str(self.root_b), '-Controller', 'no-control')
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn('REBASE', done.stdout)
        a = json.loads((out / 'replay' / 'argv.json').read_text(encoding='utf-8'))['args']
        self.assertEqual(Path(a['tuning_json']), self.root_b / 'x_tuning.json')
        self.assertEqual(Path(a['mapping_json']), self.root_b / 'x_mapping.json')
        self.assertEqual(a['controller'], 'no-control')

    def test_frozen_root_is_reverified(self):
        import freeze_manifest as fm
        root = self.tmp / 'frz_c'
        shutil.copytree(self.root_a, root)
        tools = root / 'diagnostics' / 'sdmpc_n31_20260924' / 'tools'
        tools.mkdir(parents=True)
        for name in ('n31_common.py', 'freeze_manifest.py'):
            shutil.copyfile(HERE.parent / name, tools / name)
        shutil.copyfile(sr.ROOT / 'evaluation' / 'controllers' / 'obs150_contract.py',
                        root / 'evaluation' / 'controllers' / 'obs150_contract.py')
        table, total = fm.hash_tree(root)
        fm.write_json(root / 'FREEZE.json', {'schema': 'sdmpc31-freeze/v1', 'frozen': str(root), 'git': {'head': 'f' * 40},
                                             'files': table, 'tree_sha256': fm.tree_sha256(table)}, indent=None)
        out = self.tmp / 'rd'
        rs.prepare(self.syn.decisions, T, out)
        done = self.replay(out, '-Root', str(root))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn('FREEZE_VERIFIED', done.stdout)
        (root / 'x_tuning.json').write_text('{"edited": true}', encoding='utf-8')
        out = self.tmp / 're'
        rs.prepare(self.syn.decisions, T, out)
        done = self.replay(out, '-Root', str(root))
        self.assertEqual(done.returncode, 3, done.stdout)
        self.assertIn('FREEZE.json verification failed', done.stdout)

    def test_refuses_changed_previous_action(self):
        out = self.tmp / 'rc'
        rs.prepare(self.syn.decisions, T, out)
        receipt = self.syn.decisions / f'action_{P:06d}.json.applied'
        original = receipt.read_bytes()
        try:
            os.remove(receipt)                    # break the hard link, then write different bytes
            receipt.write_bytes(original + b'x\x00')
            done = self.replay(out)
            self.assertEqual(done.returncode, 3, done.stdout)
            self.assertIn('previous action file changed since prepare', done.stdout)
        finally:
            os.remove(receipt)
            receipt.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
