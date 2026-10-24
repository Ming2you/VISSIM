"""WP-D D3: watch_sdmpc.py - one line per decision with the obs150 audit, failures, resume, end."""
from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import synthetic_run as sr  # noqa: E402
import watch_sdmpc as w  # noqa: E402
from test_tools_replay import write_native_decision  # noqa: E402


class Watch(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='n31_watch_'))
        self.syn = sr.SyntheticRun(self.tmp)
        write_native_decision(self.syn)
        d = self.syn.decisions
        (d / 'action_000900.decision_budget.json').write_text('{}', encoding='utf-8')
        action = json.loads((d / 'action_000900.json').read_text(encoding='utf-8'))
        action['ramp_metering'] = {'RM_C10480': 900.0, 'RM_C10681': 3024.0}
        action['vsl'] = {'FW_W__seg0': 110.0, 'FW_W__seg1': 80.0}
        action['metadata']['decision_wall_sec'] = 505.4
        (d / 'action_000900.json').write_text(json.dumps(action), encoding='utf-8')
        tuning = self.tmp / 'tuning.json'
        tuning.write_text(json.dumps({'config_overrides': {'freeway_follower': {'vsl_set': [60.0, 80.0, 110.0]}}}),
                          encoding='utf-8')
        prov = json.loads(self.syn.provenance_path.read_text(encoding='utf-8'))
        prov['files']['tuning'] = {'path': str(tuning)}
        self.syn.provenance_path.write_text(json.dumps(prov), encoding='utf-8')
        (self.syn.run / 'launch_plan.json').write_text(json.dumps({'control_start_sec': 900}), encoding='utf-8')
        self.log = self.syn.run / 'launch.log'
        self.summary = self.syn.run / 'summary.log'

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def watch(self, target=None):
        out = io.StringIO()
        with redirect_stdout(out):
            w.Watch(target or self.syn.run, str(self.log), str(self.summary), 40).run(once=True)
        return out.getvalue()

    def test_decision_line_with_obs150_audit(self):
        text = self.watch()
        lines = text.splitlines()
        at = next(i for i, l in enumerate(lines) if l.startswith('sim_sec=900'))
        line, obs = lines[at], lines[at + 1]
        self.assertIn('wall=505', line)
        self.assertIn('meters_restricting=1/2', line)
        self.assertIn('vsl_below_max=1(110)', line)
        self.assertIn('obj=393.916', line)
        self.assertIn('gain=1.584', line)
        self.assertTrue(obs.strip().startswith('obs150 '))
        derived = self.syn.derived
        for part in ('lag_ok=True', f'sum_tail={derived["lag"]["sum_tail"]}', 'amb=0', 'removals=1',
                     f'exit={derived["freeway_exit_count"]["value"]}', 'cons=0', 'lane_inexact=', 'edie_max=0'):
            self.assertIn(part, obs)
        self.assertIn(f'dets={len(self.syn.rows)}/', obs)
        self.assertIn('err_lag=85.0', obs)                      # T 900 - .err max 815.0
        # warmup decision 750 has no budget file but is below control_start: reported too
        self.assertIn('sim_sec=750', text)

    def test_resume_failures_and_end(self):
        self.watch(self.syn.decisions)
        (self.syn.run / f'runlog_{self.syn.name}.txt').write_text(
            'CONTROLLER_DECISION sim_sec=1050 wall_sec=3 result=exit=1\n'
            'ERROR=DECISION_EXIT_NONZERO sim_sec=1050 exit=1 stderr=ObsLagError\nDECISIONS_OK=7\nDECISIONS_FAILED=1\n',
            encoding='utf-8')
        text = self.watch()
        self.assertNotIn('sim_sec=900 ', text)                  # resume: never repeated
        self.assertIn('DECISION FAILED sim_sec=1050', text)
        self.assertNotIn('RUN ENDED', text)
        self.log.write_text('2026-09-24 12:00:00  EXIT sdmpc31_g1 code=0\n', encoding='utf-8')
        text = self.watch()
        self.assertNotIn('DECISION FAILED', text)               # reported once
        self.assertIn('RUN ENDED', text)
        self.assertIn('DECISIONS_OK=7 DECISIONS_FAILED=1', text)
        summary = self.summary.read_text(encoding='utf-8')
        self.assertEqual(summary.count('sim_sec=900 '), 1)
        self.assertEqual(summary.count('DECISION FAILED sim_sec=1050'), 1)

    def test_meter_ceiling_is_the_no_control_rate(self):
        d = self.syn.decisions
        warm = json.loads((d / 'action_000750.json').read_text(encoding='utf-8'))
        warm['ramp_metering'] = {'RM_C10480': 1512.0, 'RM_C10681': 3600.0}
        (d / 'action_000750.json').write_text(json.dumps(warm), encoding='utf-8')
        line = next(l for l in self.watch().splitlines() if l.startswith('sim_sec=900'))
        self.assertIn('meters_restricting=2/2', line)          # 3024 < the open 3600 of this network
        self.assertIn('10681:3024', line)

    def test_conservation_residual_sees_each_wrong_term(self):
        raw = self.syn.states[900][sr.oc.RAW_STATE_KEY]
        chain = w.chain_links_of(json.loads(self.syn.provenance_path.read_text(encoding='utf-8')))
        self.assertEqual(chain, {74, 10699, 2, 26, 10771, 120})
        derived = json.loads(json.dumps(self.syn.derived))
        self.assertEqual(w.conservation_residual(raw, derived, chain), 0)
        self.assertGreater(derived['boundaries']['source:FW_W']['cross'], 0)
        self.assertGreater(derived['boundaries']['off_entry:10485']['cross'], 0)
        for ref, sign in (('source:FW_W', -1), ('off_entry:10485', +1), ('chain_end:FW_W', +1)):
            bad = json.loads(json.dumps(derived))
            bad['boundaries'][ref]['cross'] += 1
            self.assertEqual(w.conservation_residual(raw, bad, chain), sign, ref)
        bad = json.loads(json.dumps(derived))
        bad['removals']['rows'] = []                              # the removal on 26 at 815 s
        self.assertEqual(w.conservation_residual(raw, bad, chain), -1)
        self.assertEqual(w.conservation_residual(raw, derived, chain - {10771}), -1 * sum(
            1 for row in sr.oc.load_bundle(self.syn.states[900]).frame_end['vehicles'] if row[1] == 10771)
            + sum(1 for row in sr.oc.load_bundle(self.syn.states[900]).frame_start['vehicles'] if row[1] == 10771))

    def test_only_the_launchers_own_exit_line_ends_the_watch(self):
        self.log.write_text('2026-09-24 12:00:00  WD 09-24 12:00:00  EXIT sdmpc31_g1 code=1\n'
                            '2026-09-24 12:00:01  WATCHDOG_EXIT code=0 wall_sec=10\n', encoding='utf-8')
        self.assertNotIn('RUN ENDED', self.watch())
        with open(self.log, 'a', encoding='utf-8') as handle:
            handle.write('2026-09-24 12:00:02  EXIT sdmpc31_g1 code=7\n')
        self.assertIn('RUN ENDED', self.watch())

    def test_missing_derived_is_visible(self):
        (self.syn.decisions / 'obs150' / 'derived_000900.json').unlink()
        self.assertIn('obs150 derived=missing', self.watch())


if __name__ == '__main__':
    unittest.main()
