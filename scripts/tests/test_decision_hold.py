"""K8-8 helper scripts/decision_hold.py - unit tests on synthetic decision folders (no VISSIM, no adapter).

Declared by K8 amendment 21 section 7.2 (u) (and used by (v)): E1-E10 each refuse (E3: each of the eight P-4
names once as the outer type and once as a middle chain header line; ConnectionAbortedError, outside the list,
is held), determinism (same inputs twice -> the same held JSON and CSV bytes, PYTHONHASHSEED 0 and 2), the CSV
byte copy, the .failed_decision renames, ACTION_CSV_FIELDS = evaluation.controllers.action_csv_schema, and no
'DECISION_FAILED' text in the helper's stdout/stderr.  The helper runs as a child process exactly as the
runner calls it (python <helper> --state-json ... --decision-exit 1).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HELPER = ROOT / 'scripts' / 'decision_hold.py'
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(HELPER.parent) not in sys.path:
    sys.path.insert(0, str(HELPER.parent))

import decision_hold as dh  # noqa: E402

RUN_ID = 'run-k88-unit'
OBS_RUN_ID = 'obs-k88-unit'
FIELDS = dh.ACTION_CSV_FIELDS
EIGHT = ('DecisionDeadline', 'TimeoutError', 'MemoryError', 'KeyboardInterrupt', 'GeneratorExit',
         'BrokenProcessPool', 'BrokenPipeError', 'ConnectionResetError')
WARN = '[경고] leader_hinge 성분은 merge {7,9,13,14} 기하에서 캘리브레이션됨 - 재검증 필요'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def traceback_text(outer='RuntimeError', middle=None, frames=(), root_line=None, extra=''):
    """A decision_failure_report .error.txt: a tangent-worker style chain (outer header, worker traceback in the
    message, root header last)."""
    lines = ['Traceback (most recent call last):',
             '  File "D:\\FRZ\\evaluation\\controllers\\vissim_stackelberg_adapter.py", line 13184, in run_joint_owner_decision',
             '    solved = sdmpc.solve(...)',
             '  File "D:\\FRZ\\evaluation\\controllers\\sdmpc_tangent.py", line 74, in _evaluate_single',
             '    raise RuntimeError(...)']
    for path, func in frames:
        lines += [f'  File "{path}", line 10, in {func}', '    x = 1']
    lines.append(f'{outer}: Tangent prediction failed:')
    lines += ['Traceback (most recent call last):',
              '  File "D:\\FRZ\\evaluation\\controllers\\control_area_objective.py", line 632, in transfer',
              '    raise MembershipError(...)']
    if middle:
        lines.append(f'{middle}: worker pipe')
        lines += ['', 'The above exception was the direct cause of the following exception:', '',
                  'Traceback (most recent call last):',
                  '  File "D:\\FRZ\\evaluation\\controllers\\area_runtime.py", line 331, in evaluate_price_point',
                  '    y = 2']
    if extra:
        lines.append(extra)
    lines.append(root_line or 'evaluation.controllers.control_area_objective.MembershipError: unresolved destination '
                              'of movement:SC5_S_to_N_SC102: (None, None)')
    return '\n'.join(lines) + '\n'


class Fixture:
    """One decision folder: SDMPC action at S = T - 150 (applied), a failed decision at T, state, derived window."""

    def __init__(self, base: Path, T=3900, control_start=900, policy='hold_previous_on_exception'):
        self.base = base
        self.T, self.S, self.cs = T, T - 150, control_start
        self.dir = base / '결정 폴더 k88'
        self.dir.mkdir(parents=True)
        (self.dir / 'obs150').mkdir()
        self.tuning = base / '튜닝 k88.json'
        tun = {'config_overrides': {'x': 1}}
        if policy is not None:
            tun['runtime'] = {'decision_error_policy': policy}
        self.tuning.write_text(json.dumps(tun, indent=2), encoding='utf-8')
        self.write_previous_sdmpc(self.S)
        self.write_state(T)
        self.write_derived(T)
        self.write_failure(T)

    def p(self, sec, suffix):
        return self.dir / f'action_{sec:06d}{suffix}'

    def action(self, sec):
        return {'N_P_star': 697.0 + sec, 'N_UF_star': 12.5,
                'ramp_metering': {'RM_C10480': 1512.0, 'RM_C10681': 2400.0},
                'vsl': {'FW_W__seg0': 110.0, 'FW_E__seg3': 90.0},
                'green_times': {'SC5': {'SC5_p1': 34.0, 'SC5_p2': 20.0}},
                'offsets': {'SC5': 0.0}, 'inflow_outflow_allocation': {'a': [1.0, 2.0]},
                'diagnostics': {'rw_meter_green_RM_C10480': 4.0, 'sdmpc_prediction_sequence': [[1, 2], [3, 4]],
                                'zz_last': '한글 값'},
                'metadata': {'sim_sec': float(sec), 'controller': 'wu-link', 'controller_variant': 'sdmpc-n31',
                             'controller_status': 'ok', 'sdmpc_active': True,
                             'run_provenance': {'run_id': RUN_ID, 'manifest_path': 'm.json'},
                             'far_rate_est_10491': 900.5, 'joint_leader_selection': {'selected_objective': 1.5},
                             'sat_est_SC1001_W': 1800.0, 'far_rate_est_10481': 700.25,
                             'sdmpc_state': {'schema': 'x', 'next_prices_scaled': [0.1, 0.2]},
                             'head_observation_snapshot_sec': float(sec), 'decision_wall_sec': 500.0},
                'prediction': {'wall_sec': 3.0, 'v': [1, 2, 3]},
                'prediction_error': {'source_action_json': 'D:\\run\\action.json'},
                'projection_diagnostics': {'physical_stock_assignment_by_link': {'1': 2}},
                'run_provenance': {'run_id': RUN_ID, 'inputs': {'tuning_json': {'sha256': 'ab' * 32}}}}

    def write_csv(self, sec, rows=2):
        lines = [','.join(FIELDS)]
        lines += [f'vsl,RW_FW_W_S0,{i},,26,1,110.0,,,,,,,,ok' for i in range(rows)]
        lines += ['ramp_meter,RM_C10480,,,,,,,,,,,1512.0,4,ok;group_rate_vph=1512']
        self.p(sec, '.csv').write_bytes(('\r\n'.join(lines) + '\r\n').encode('utf-8'))

    def write_previous_sdmpc(self, sec):
        self.p(sec, '.json').write_text(json.dumps(self.action(sec), ensure_ascii=False, indent=2), encoding='utf-8')
        self.write_csv(sec)
        csv_path = self.p(sec, '.csv')
        receipt = f'{sec}\r\n{csv_path}\r\n{csv_path.stat().st_size}\r\n'
        Path(str(self.p(sec, '.json')) + '.applied').write_bytes(receipt.encode('utf-16'))

    def write_state(self, sec, **override):
        state = {'sim_sec': float(sec), 'control_interval_sec': 150.0,
                 'run_provenance': {'run_id': RUN_ID, 'manifest_path': 'm.json'},
                 'obs150': {'schema': 'obs150-raw/v1', 'sim_sec': sec, 'directory': str(self.dir), 'run_id': OBS_RUN_ID}}
        state.update(override)
        (self.dir / f'state_{sec:06d}.json').write_text(json.dumps(state), encoding='utf-8')

    def write_derived(self, sec, **override):
        doc = {'schema': 'obs150-derived/v1', 'sim_sec': sec, 'run_id': OBS_RUN_ID,
               'window': {'start_s': sec - 150, 'end_s': sec}, 'off_split': {}}
        doc.update(override)
        (self.dir / 'obs150' / f'derived_{sec:06d}.json').write_text(json.dumps(doc), encoding='utf-8')

    def write_failure(self, sec, outer='RuntimeError', middle=None, frames=(), root_line=None, extra='',
                      summary_lines=1, traceback_path=None, stderr_extra=b''):
        error = self.p(sec, '.error.txt')
        error.write_text(traceback_text(outer, middle, frames, root_line, extra), encoding='utf-8')
        root = root_line or ('evaluation.controllers.control_area_objective.MembershipError: unresolved destination '
                             'of movement:SC5_S_to_N_SC102: (None, None)')
        line = (f'DECISION_FAILED type={outer} message=Tangent prediction failed: root_error={root} '
                f'traceback={traceback_path or error}')
        data = (WARN + '\n').encode('utf-8') + stderr_extra + b''.join((line + '\n').encode('utf-8')
                                                                      for _ in range(summary_lines))
        self.p(sec, '.stderr.txt').write_bytes(data)
        self.p(sec, '.stdout.txt').write_bytes(b'')

    def args(self, sec=None, previous=None, control_start=None):
        sec = self.T if sec is None else sec
        prev = (sec - 150) if previous is None else previous
        return ['--state-json', str(self.dir / f'state_{sec:06d}.json'),
                '--failed-action-json', str(self.p(sec, '.json')),
                '--failed-action-csv', str(self.p(sec, '.csv')),
                '--previous-action-json', str(self.p(prev, '.json')),
                '--tuning-json', str(self.tuning),
                '--control-start-sec', str(self.cs if control_start is None else control_start),
                '--decision-exit', '1']

    def snapshot(self):
        return {str(p.relative_to(self.base)): sha(p) for p in sorted(self.base.rglob('*')) if p.is_file()}


def run_helper(args, hashseed='0'):
    env = {k: v for k, v in os.environ.items() if not k.startswith('RW_')}
    env['PYTHONHASHSEED'] = hashseed
    env['PYTHONUTF8'] = '1'
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    done = subprocess.run([sys.executable, '-B', str(HELPER), *args], capture_output=True, env=env, timeout=300)
    return done.returncode, done.stdout, done.stderr


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='k88_hold_'))
        self.fx = Fixture(self.tmp / 'k88 단위 루트')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def assertRefused(self, code, args=None):
        before = self.fx.snapshot()
        rc, out, err = run_helper(args or self.fx.args())
        self.assertEqual(rc, 3, (out, err))
        self.assertEqual(out, b'')
        text = err.decode('utf-8')
        self.assertTrue(text.startswith(f'DECISION_HOLD_REFUSED reason={code} '), text)
        self.assertEqual(len(text.splitlines()), 1)
        self.assertNotIn('DECISION_FAILED', text)
        after = self.fx.snapshot()
        hold_error = str(self.fx.p(self.fx.T, '.hold_error.txt').relative_to(self.fx.base))
        self.assertIn(hold_error, after)
        after.pop(hold_error)
        self.assertEqual(after, before)                     # no existing file changed, nothing else written
        return text

    def assertHeld(self, args=None, hashseed='0'):
        rc, out, err = run_helper(args or self.fx.args(), hashseed)
        self.assertEqual((rc, err), (0, b''), out)
        line = out.decode('utf-8')
        self.assertTrue(line.startswith(f'HOLD_OK sim_sec={self.fx.T} '), line)
        self.assertEqual(len(line.splitlines()), 1)
        self.assertLessEqual(len(out), 1024)
        self.assertNotIn('DECISION_FAILED', line)
        return line


class Eligibility(Base):
    def test_e1_policy_strict_missing_timeout_and_other_values(self):
        for tun in ({}, {'runtime': {'decision_error_policy': 'strict'}},
                    {'runtime': {'decision_error_policy': 'hold_previous'}},
                    {'runtime': {'decision_error_policy': 1}},
                    {'runtime': {'decision_error_policy': 'hold_previous_on_exception', 'decision_timeout_sec': 1800}},
                    {'runtime': 'hold_previous_on_exception'}):
            with self.subTest(tun=tun):
                self.fx.tuning.write_text(json.dumps(tun), encoding='utf-8')
                self.assertRefused('E1')
                self.fx.p(self.fx.T, '.hold_error.txt').unlink()

    def test_e1_extends_chain(self):
        parent = self.fx.base / 'parent.json'
        parent.write_text(json.dumps({'runtime': {'decision_error_policy': 'hold_previous_on_exception'}}),
                          encoding='utf-8')
        self.fx.tuning.write_text(json.dumps({'extends': 'parent.json'}), encoding='utf-8')
        self.assertHeld()
        self.assertEqual(dh.read_policy_chain(self.fx.tuning)[0], 'hold_previous_on_exception')
        parent.write_text(json.dumps({'runtime': {'decision_timeout_sec': 30}}), encoding='utf-8')
        self.fx.tuning.write_text(json.dumps({'extends': 'parent.json',
                                              'runtime': {'decision_error_policy': 'hold_previous_on_exception'}}),
                                  encoding='utf-8')
        with self.assertRaises(ValueError):
            dh.read_policy_chain(self.fx.tuning)

    def test_e2_report_missing_or_not_this_decision(self):
        T = self.fx.T
        self.fx.p(T, '.error.txt').unlink()
        self.assertRefused('E2')
        self.fx.p(T, '.hold_error.txt').unlink()
        for kwargs in ({'summary_lines': 0}, {'summary_lines': 2},
                       {'traceback_path': str(self.fx.p(T - 150, '.error.txt'))}):
            with self.subTest(kwargs=kwargs):
                self.fx.write_failure(T, **kwargs)
                self.assertRefused('E2')
                self.fx.p(T, '.hold_error.txt').unlink()

    def test_e2_path_case_and_separator_and_non_utf8_bytes(self):
        T = self.fx.T
        spelled = str(self.fx.p(T, '.error.txt')).upper().replace('\\', '/')
        self.fx.write_failure(T, traceback_path=spelled, stderr_extra='경고 cp949 줄\n'.encode('cp949') + b'\xff\xfe\n')
        self.assertHeld()                                       # R-15: decoded with errors='replace', no exception

    def test_e3_each_of_the_eight_names_outer_and_middle(self):
        T = self.fx.T
        for name in EIGHT:
            dotted = 'concurrent.futures.process.' + name if name == 'BrokenProcessPool' else name
            for where in ('outer', 'middle'):
                with self.subTest(name=name, where=where):
                    if where == 'outer':
                        self.fx.write_failure(T, outer=dotted, root_line=f'{dotted}: x')
                    else:
                        self.fx.write_failure(T, middle=dotted)
                    text = self.assertRefused('E3')
                    self.assertIn(name, text)
                    self.fx.p(T, '.hold_error.txt').unlink()

    def test_e3_outside_the_list_is_held(self):
        self.fx.write_failure(self.fx.T, middle='ConnectionAbortedError')
        self.assertHeld()
        receipt = json.loads(self.fx.p(self.fx.T, '.hold.json').read_text(encoding='utf-8'))
        self.assertIn('ConnectionAbortedError', receipt['exception']['chain_header_types'])

    def test_e4_contract_pairs_and_message(self):
        T = self.fx.T
        for path, func in dh.CONTRACT_PAIRS:
            with self.subTest(pair=(path, func)):
                self.fx.write_failure(T, frames=[(f'D:\\FRZ\\evaluation\\controllers\\{path}', func)])
                self.assertRefused('E4')
                self.fx.p(T, '.hold_error.txt').unlink()
        self.fx.write_failure(T, extra='ValueError: Invalid applied central multiplier warm start')
        self.assertRefused('E4')

    def test_e4_is_a_pair_not_a_function_name(self):
        self.fx.write_failure(self.fx.T, frames=[('D:\\FRZ\\evaluation\\controllers\\other_module.py', 'configure')])
        self.assertHeld()

    def test_e5_state_and_range(self):
        T = self.fx.T
        for override in ({'sim_sec': float(T + 150)}, {'control_interval_sec': 60.0}):
            with self.subTest(override=override):
                self.fx.write_state(T, **override)
                self.assertRefused('E5')
                self.fx.p(T, '.hold_error.txt').unlink()
        self.fx.write_state(T)
        self.assertRefused('E5', self.fx.args(control_start=T))          # S = T-150 < control start
        self.fx.p(T, '.hold_error.txt').unlink()
        self.assertRefused('E5', self.fx.args(control_start=-1))         # P-3: ControlStartSec >= 0

    def test_e5_first_sdmpc_decision_after_warmup(self):
        fx = Fixture(self.tmp / 'k88 t900', T=900)
        prev = json.loads(fx.p(750, '.json').read_text(encoding='utf-8'))
        prev['metadata']['sdmpc_active'] = False
        prev['metadata']['controller'] = 'no-control'
        fx.p(750, '.json').write_text(json.dumps(prev), encoding='utf-8')
        rc, out, err = run_helper(fx.args())
        self.assertEqual(rc, 3)
        self.assertTrue(err.decode('utf-8').startswith('DECISION_HOLD_REFUSED reason=E5 '))

    def test_e6_previous_not_the_preceding_action_of_this_run(self):
        T, S = self.fx.T, self.fx.S
        good = self.fx.p(S, '.json').read_text(encoding='utf-8')
        for mutate in (lambda d: d['metadata'].__setitem__('sim_sec', float(S - 150)),
                       lambda d: d['run_provenance'].__setitem__('run_id', 'other'),
                       lambda d: d['metadata']['run_provenance'].__setitem__('run_id', 'other')):
            doc = json.loads(good)
            mutate(doc)
            self.fx.p(S, '.json').write_text(json.dumps(doc), encoding='utf-8')
            self.assertRefused('E6')
            self.fx.p(T, '.hold_error.txt').unlink()
        self.fx.p(S, '.json').write_text(good, encoding='utf-8')
        self.fx.write_state(T, run_provenance={'run_id': 'other'})
        self.assertRefused('E6')

    def test_e7_previous_neither_sdmpc_nor_hold(self):
        S = self.fx.S
        doc = json.loads(self.fx.p(S, '.json').read_text(encoding='utf-8'))
        doc['metadata']['sdmpc_active'] = False
        self.fx.p(S, '.json').write_text(json.dumps(doc), encoding='utf-8')
        self.assertRefused('E7')
        self.fx.p(self.fx.T, '.hold_error.txt').unlink()
        doc['metadata']['controller_status'] = 'hold_previous_on_exception'   # a hold record without receipt
        self.fx.p(S, '.json').write_text(json.dumps(doc), encoding='utf-8')
        self.assertRefused('E7')

    def test_e8_previous_not_applied(self):
        T, S = self.fx.T, self.fx.S
        applied = Path(str(self.fx.p(S, '.json')) + '.applied')
        good = applied.read_bytes()
        applied.unlink()
        self.assertRefused('E8')
        self.fx.p(T, '.hold_error.txt').unlink()
        csv_path = self.fx.p(S, '.csv')
        for text in (f'{S - 150}\r\n{csv_path}\r\n{csv_path.stat().st_size}\r\n',
                     f'{S}\r\n{csv_path}\r\n{csv_path.stat().st_size + 1}\r\n',
                     f'{S}\r\n{csv_path}.other\r\n{csv_path.stat().st_size}\r\n'):
            applied.write_bytes(text.encode('utf-16'))
            self.assertRefused('E8')
            self.fx.p(T, '.hold_error.txt').unlink()
        applied.write_bytes(good)
        data = csv_path.read_bytes()
        csv_path.write_bytes(data.replace(b'p4_green', b'p4_greeen', 1))
        self.assertRefused('E8')
        self.fx.p(T, '.hold_error.txt').unlink()
        csv_path.write_bytes((','.join(FIELDS) + '\r\n').encode('utf-8'))
        self.assertRefused('E8')

    def test_e9_window_document(self):
        T = self.fx.T
        derived = self.fx.dir / 'obs150' / f'derived_{T:06d}.json'
        good = derived.read_bytes()
        derived.unlink()
        self.assertRefused('E9')
        self.fx.p(T, '.hold_error.txt').unlink()
        for override in ({'run_id': 'other'}, {'sim_sec': T - 150}, {'schema': 'x'},
                         {'window': {'start_s': T - 300, 'end_s': T}}):
            with self.subTest(override=override):
                self.fx.write_derived(T, **override)
                self.assertRefused('E9')
                self.fx.p(T, '.hold_error.txt').unlink()
        derived.write_bytes(good[:len(good) // 2])                    # truncated JSON
        self.assertRefused('E9')

    def test_e10_failed_decision_target_exists(self):
        T = self.fx.T
        self.fx.p(T, '.json').write_text('{"partial": true}', encoding='utf-8')
        Path(str(self.fx.p(T, '.json')) + '.failed_decision').write_text('{}', encoding='utf-8')
        self.assertRefused('E10')


class HeldOutput(Base):
    def test_csv_bytes_json_shape_and_receipt(self):
        T, S, fx = self.fx.T, self.fx.S, self.fx
        source = json.loads(fx.p(S, '.json').read_text(encoding='utf-8'))
        line = self.assertHeld()
        held_csv, held_json = fx.p(T, '.csv'), fx.p(T, '.json')
        self.assertEqual(held_csv.read_bytes(), fx.p(S, '.csv').read_bytes())            # byte copy (Q-H4)
        held = json.loads(held_json.read_text(encoding='utf-8'))
        for key in dh_control():
            self.assertEqual(held[key], source[key], key)
            self.assertEqual(json.dumps(held[key]), json.dumps(source[key]), key)
        self.assertEqual(list(held), [k for k in source if k not in ('prediction', 'prediction_error',
                                                                    'projection_diagnostics')])
        self.assertEqual(held['diagnostics'], {k: v for k, v in source['diagnostics'].items()
                                               if k != 'sdmpc_prediction_sequence'})
        self.assertEqual(held['run_provenance'], source['run_provenance'])
        md = held['metadata']
        self.assertEqual(list(md), ['sim_sec', 'controller', 'controller_variant', 'controller_status',
                                    'run_provenance', 'far_rate_est_10491', 'sat_est_SC1001_W', 'far_rate_est_10481',
                                    'hold_previous_on_exception'])
        self.assertEqual(md['sim_sec'], float(T))
        self.assertIs(type(md['sim_sec']), float)
        self.assertEqual(md['controller_status'], 'hold_previous_on_exception')
        self.assertNotIn('sdmpc_state', md)
        hold = md['hold_previous_on_exception']
        self.assertEqual(hold['schema'], 'hold-on-exception/v1')
        self.assertEqual((hold['sim_sec'], hold['source_sim_sec'], hold['origin_sim_sec'], hold['chain_length']),
                         (T, S, S, 1))
        self.assertEqual(hold['removed'], ['prediction', 'prediction_error', 'projection_diagnostics',
                                           'diagnostics.sdmpc_prediction_sequence'])
        self.assertEqual(hold['carried_metadata_keys'], sorted(hold['carried_metadata_keys']))
        self.assertEqual(hold['source_action_csv'], {'name': fx.p(S, '.csv').name, 'sha256': sha(fx.p(S, '.csv'))})
        self.assertEqual(hold['price_state'], 'restart')
        self.assertNotIn(json.dumps(str(fx.dir))[1:-1], json.dumps(md))   # no absolute path in the held metadata
        # adapter form: json.dumps(ensure_ascii=False, indent=2) written in text mode
        expected = json.dumps(held, ensure_ascii=False, indent=2).replace('\n', os.linesep).encode('utf-8')
        self.assertEqual(held_json.read_bytes(), expected)
        receipt = json.loads(fx.p(T, '.hold.json').read_text(encoding='utf-8'))
        for key in ('hold_previous_on_exception', 'decision', 'exception', 'eligibility', 'source', 'held_output',
                    'failed_partials', 'evidence', 'inputs', 'wall'):
            self.assertIn(key, receipt)
        self.assertEqual(receipt['hold_previous_on_exception'], hold)
        self.assertEqual(receipt['held_output']['action_csv']['sha256'], sha(held_csv))
        self.assertEqual(receipt['held_output']['action_json']['sha256'], sha(held_json))
        self.assertEqual(receipt['source']['applied']['sha256'], sha(str(fx.p(S, '.json')) + '.applied'))
        self.assertEqual(receipt['exception']['type'], 'RuntimeError')
        self.assertEqual(receipt['exception']['root_type'], 'MembershipError')
        self.assertEqual(receipt['eligibility']['checks'], {f'E{i}': 'pass' for i in range(1, 11)})
        self.assertEqual(receipt['eligibility']['excluded_types'], list(EIGHT))
        self.assertEqual(receipt['evidence'][f'obs150/derived_{T:06d}.json'],
                         sha(fx.dir / 'obs150' / f'derived_{T:06d}.json'))
        self.assertEqual(receipt['evidence'][f'action_{T:06d}.joint.json'], 'absent')
        self.assertIn(f'csv_sha256={sha(held_csv)}', line)
        self.assertIn(f'json_sha256={sha(held_json)}', line)
        self.assertIn('type=RuntimeError root_type=MembershipError', line)
        self.assertFalse(Path(str(held_json) + '.applied').exists())
        self.assertFalse(Path(str(held_json) + '.sdmpc_pending').exists())

    def test_partials_are_renamed_never_applied(self):
        T, fx = self.fx.T, self.fx
        partial = {'.json': b'{"partial": 1}', '.csv': b'kind,id\r\nvsl,x\r\n',
                   '.json.sdmpc_pending': b'Native application required\n', '.joint_written.json': b'{}'}
        for suffix, data in partial.items():
            fx.p(T, suffix).write_bytes(data)
        self.assertHeld()
        receipt = json.loads(fx.p(T, '.hold.json').read_text(encoding='utf-8'))
        names = [p['from'] for p in receipt['failed_partials']]
        self.assertEqual(names, sorted(names))
        self.assertEqual(len(names), 4)
        for suffix, data in partial.items():
            moved = Path(str(fx.p(T, suffix)) + '.failed_decision')
            self.assertEqual(moved.read_bytes(), data)
            self.assertIn({'from': fx.p(T, suffix).name, 'to': moved.name, 'sha256': hashlib.sha256(data).hexdigest()},
                          receipt['failed_partials'])
        self.assertFalse(fx.p(T, '.json.sdmpc_pending').exists())
        self.assertEqual(fx.p(T, '.csv').read_bytes(), fx.p(fx.S, '.csv').read_bytes())

    def test_determinism_hashseed_0_and_2(self):
        a = self.fx
        outputs = [a.p(a.T, '.json'), a.p(a.T, '.csv'), a.p(a.T, '.hold.json')]
        self.assertHeld(a.args(), '0')
        first = {p.name: p.read_bytes() for p in outputs}
        for p in outputs:                       # the same inputs again: the decision folder as before the hold
            p.unlink()
        self.assertHeld(a.args(), '2')
        second = {p.name: p.read_bytes() for p in outputs}
        for suffix in ('.json', '.csv'):
            name = a.p(a.T, suffix).name
            self.assertEqual(first[name], second[name], name)
        ra = json.loads(first[a.p(a.T, '.hold.json').name].decode('utf-8'))
        rb = json.loads(second[a.p(a.T, '.hold.json').name].decode('utf-8'))
        for key in ('hold_previous_on_exception', 'eligibility', 'source', 'held_output'):
            self.assertEqual(ra[key], rb[key], key)
        self.assertEqual({k: v for k, v in ra['exception'].items()}, {k: v for k, v in rb['exception'].items()})
        # another folder (other absolute paths), hash seed 2: the held JSON and CSV bytes are still the same
        b = Fixture(self.tmp / 'k88 두번째 루트')
        rc, out, err = run_helper(b.args(), '2')
        self.assertEqual(rc, 0, err)
        for suffix in ('.json', '.csv'):
            self.assertEqual(first[a.p(a.T, suffix).name], b.p(b.T, suffix).read_bytes(), suffix)

    def test_chained_hold(self):
        fx, T, S = self.fx, self.fx.T, self.fx.S
        self.assertHeld()
        T2 = T + 150
        fx.write_state(T2)
        fx.write_derived(T2)
        fx.write_failure(T2)
        rc, out, err = run_helper(fx.args(sec=T2))
        self.assertEqual(rc, 0, err)
        held2 = json.loads(fx.p(T2, '.json').read_text(encoding='utf-8'))
        hold = held2['metadata']['hold_previous_on_exception']
        self.assertEqual((hold['source_sim_sec'], hold['origin_sim_sec'], hold['chain_length']), (T, S, 2))
        self.assertEqual(fx.p(T2, '.csv').read_bytes(), fx.p(S, '.csv').read_bytes())
        receipt = json.loads(fx.p(T2, '.hold.json').read_text(encoding='utf-8'))
        self.assertEqual(receipt['source']['kind'], 'hold')
        self.assertEqual(receipt['source']['receipt']['sha256'], sha(fx.p(T, '.hold.json')))
        self.assertTrue(out.decode('utf-8').startswith(f'HOLD_OK sim_sec={T2} source_sim_sec={T} origin_sim_sec={S} chain=2 '))
        # a chained source whose receipt no longer pins its CSV is refused (E8)
        T3 = T2 + 150
        fx.write_state(T3)
        fx.write_derived(T3)
        fx.write_failure(T3)
        fx.p(T2, '.csv').write_bytes(fx.p(T2, '.csv').read_bytes() + b'vsl,extra\r\n')
        rc, out, err = run_helper(fx.args(sec=T3))
        self.assertEqual(rc, 3)
        self.assertTrue(err.decode('utf-8').startswith('DECISION_HOLD_REFUSED reason=E8 '))


class Constants(unittest.TestCase):
    def test_action_csv_fields_equal_the_schema(self):
        from evaluation.controllers import action_csv_schema
        self.assertEqual(tuple(dh.ACTION_CSV_FIELDS), tuple(action_csv_schema.ACTION_CSV_FIELDS))

    def test_lists_are_the_declared_ones(self):
        self.assertEqual(dh.EXCLUDED_TYPES, EIGHT)
        self.assertEqual(len(dh.CONTRACT_PAIRS), 9)
        self.assertIn(('area_meter_finalization.py', 'configure'), dh.CONTRACT_PAIRS)
        self.assertEqual(dh.CONTRACT_MESSAGES, ('Invalid applied central multiplier warm start',))

    def test_helper_imports_standard_library_only(self):
        import ast
        tree = ast.parse(HELPER.read_text(encoding='utf-8'))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names |= {a.name.split('.')[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                names.add((node.module or '').split('.')[0])
        self.assertEqual(names, {'__future__', 'argparse', 'csv', 'datetime', 'hashlib', 'json', 'os', 're', 'sys',
                                 'traceback', 'pathlib'})

    def test_helper_exception_path(self):
        tmp = Path(tempfile.mkdtemp(prefix='k88_hold_exc_'))
        try:
            fx = Fixture(tmp / 'root')
            args = fx.args()
            args[args.index('--failed-action-csv') + 1] = str(fx.p(fx.T, '.other.csv'))
            rc, out, err = run_helper(args)
            self.assertEqual(rc, 1)
            text = err.decode('utf-8')
            self.assertTrue(text.startswith('DECISION_HOLD_EXCEPTION type=ValueError'), text)
            self.assertNotIn('DECISION_FAILED', text)
            self.assertTrue(fx.p(fx.T, '.hold_error.txt').is_file())
            self.assertFalse(fx.p(fx.T, '.hold.json').exists())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def dh_control():
    return ('N_P_star', 'N_UF_star', 'ramp_metering', 'vsl', 'green_times', 'offsets', 'inflow_outflow_allocation')


if __name__ == '__main__':
    unittest.main()
