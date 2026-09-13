"""Synthetic files only; no model, COM, or actual run payload access."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from diagnostics.com_execution_equivalence import verify_pair as v

ACTION_FIELDS = ['kind', 'id', 'dsd_no', 'sc_no', 'link', 'lane', 'speed_kph',
                 'p1_green', 'p2_green', 'p3_green', 'p4_green', 'offset', 'rate_vph', 'green_sec', 'metadata']


def command(kind, **values):
    return {**dict.fromkeys(ACTION_FIELDS, ''), 'kind': kind, 'metadata': 'same', **values}


def save(p, value):
    p.write_text(json.dumps(value), encoding='utf-8')


def table(p, fields, rows):
    with p.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f); writer.writerow(fields)
        for row in rows: writer.writerow([row.get(k, '') for k in fields] if isinstance(row, dict) else row)


class PairTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.a = self.root / 'old'; self.b = self.root / 'fast'
        source = self.root / 'same.txt'; source.write_text('same source/config/network/demand')
        self.sg = {'1:1': {'start': 1, 'end': 3}}
        self.make_run(self.a, source, False); self.make_run(self.b, source, True)

    def tearDown(self): self.tmp.cleanup()

    def make_run(self, run, source, fast):
        run.mkdir(); folder = run / ('decisions_' + run.name); folder.mkdir()
        native = run / 'vissim_eval'; native.mkdir()
        fzp = native / 'run.fzp'
        fzp.write_bytes((b'* different metadata ' + run.name.encode() + b'\n$VEHICLE:SIMSEC;NO;SPEED\n'
                         b'1.00;1;20.00\n2.00;1;21.00\n3.00;1;22.00\n'))
        (native / 'run.lsa').write_bytes(b'Signal Changes Protocol\n1;0;1;1;amber;1;COM;0;\n2;0;1;1;red;1;COM;0;\n')
        sgrows = [(1, 1, 1, 'AMBER', 'AMBER', 1, 'immediate'),
                  (2, 1, 1, 'AMBER', 'AMBER', 1, 'post_step'),
                  (2, 1, 1, 'RED', 'RED', 1, 'immediate'),
                  (3, 1, 1, 'RED', 'RED', 1, 'post_step')]
        if not fast: sgrows[1:1] = [sgrows[0]]
        table(folder / 'signal_readback.csv', v.SG_FIELDS, sgrows)
        table(folder / 'vsl_readback.csv', v.VSL_FIELDS,
              [(t, 7, cls, 120, 120, 1, 'immediate') for t in (1, 3) for cls in (10, 20, 30, 70)])
        ident = {'run_id': run.name + '-uuid', 'manifest_path': str(run / ('run_provenance_' + run.name + '.json'))}
        for t in (1, 3):
            raw = {k: 0 for k in v.STATE_KEYS}
            raw.update(sim_sec=t, sim_period_sec=3, run_provenance=ident,
                       local_observation={'head': {'green_seconds': t}, 'queue': [1, 2]}, vehicle_records=[1, 2])
            save(folder / f'state_{t:06d}.json', raw)
            action = {k: {} for k in v.CONTROL_KEYS}
            action.update(run_provenance=ident, metadata={'wall_sec': 0.1 if fast else 2.0}, prediction={'omitted': run.name})
            save(folder / f'action_{t:06d}.json', action)
            table(folder / f'action_{t:06d}.csv', ACTION_FIELDS,
                  [command('ramp_meter', sc_no=1, green_sec=1, rate_vph=90), command('vsl', dsd_no=7, speed_kph=120)])
        entry = {'path': str(source), 'exists': True, 'sha256': v.sha(source)}
        config = source.with_name('generated.vbs')
        config.write_text('RW_RAMP_METER_SCS = "1"\nRW_RAMP_METER_CAPACITIES_VPH = "900"\n')
        runner = source.with_name('runner.vbs')
        runner.write_text('Const RAMP_CYCLE_SEC = 10\nConst RAMP_AMBER_SEC = 1\nConst AMBER_SEC = 3\n')
        plan = source.with_name('generated_sgplan.vbs')
        plan.write_text('RW_SIGNAL_SG_EXPECTED = "2:1:1,2:" & _\n    "2:0,2:9:0"\n')
        proof = source.with_name('checks.json'); save(proof, {'source_sha256': {str(plan): v.sha(plan)}, 'generated_sha256': {}})
        prov = {'name': run.name, 'run_id': ident['run_id'], 'seed': 13, 'sim_period_sec': 3,
                'control_interval_sec': 3, 'state_log_interval_sec': 1, 'demand_scale': 1,
                'controller': 'diagnostic-signal-profile', 'audit_anchors_sec': '', 'signal_observation': True,
                'files': {k: entry.copy() for k in ('network', 'tuning', 'demand_profile', 'main_vbs_runner')},
                'controller_sources': [entry], 'signal_programs': [entry],
                'env': {'RW_MAINLINE_SG_ONLY': '1', 'RW_SIGNAL_WRITE_ON_CHANGE': '1' if fast else '0', 'RW_SIGNAL_READBACK_SEC': '0' if fast else '1'}}
        prov['files']['generated_vbs_config'] = {'path': str(config), 'exists': True, 'sha256': v.sha(config)}
        prov['files']['main_vbs_runner'] = {'path': str(runner), 'exists': True, 'sha256': v.sha(runner)}
        pp = Path(ident['manifest_path']); save(pp, prov)
        for t in (1, 3):
            action_path = folder / f'action_{t:06d}.json'; action = v.read(action_path)
            state_path = folder / f'state_{t:06d}.json'
            action['run_provenance'] = {'schema_version': 2, 'run_id': ident['run_id'], 'inputs': {
                'run_manifest_json': {'path': str(pp), 'exists': True, 'sha256': v.sha(pp)},
                'state_json': {'path': str(state_path), 'exists': True, 'sha256': v.sha(state_path)}}}
            save(action_path, action)
        log = run / ('runlog_' + run.name + '.txt')
        log.write_text('STAGE=SIM_DONE\nSIM_SEC=3\n' + '\n'.join(k + '=0' for k in v.FAILURE_COUNTERS) + '\n')
        state_csv = run / ('state_' + run.name + '.csv'); table(state_csv, ['sim_sec'], [(1,), (3,)])
        receipt = {'schema': 'selected-control-completion/v1', 'name': run.name, 'run_id': ident['run_id'],
                   'run_directory': str(run), 'completed': True, 'exit_code': 0, 'cscript_exit_code': None,
                   'owned_native_alive': False, 'terminal_sec': 3, 'errors': [], 'provenance_path': str(pp),
                   'provenance_sha256': v.sha(pp), 'runlog_path': str(log), 'state_csv_path': str(state_csv),
                   'preparation_checks': {'path': str(proof), 'sha256': v.sha(proof)}}
        save(run / 'completion_receipt.json', receipt)

    def verify(self):
        return v.verify(self.a, self.b, v.sha(self.a / 'completion_receipt.json'), v.sha(self.b / 'completion_receipt.json'))

    def csv(self, run, name): return run / ('decisions_' + run.name) / name

    def test_complete_pair_metadata_and_duplicate_holds(self):
        out = self.verify()
        self.assertTrue(out['passed'], out)
        self.assertGreater(out['checks']['signals_left']['rows'], out['checks']['signals_right']['rows'])
        self.assertFalse(out['checks']['signals_right']['continuous_hold_coverage_certified'])

    def test_first_ordered_fzp_difference_and_count(self):
        p = self.b / 'vissim_eval/run.fzp'; p.write_bytes(p.read_bytes().replace(b'2.00;1;21.00', b'2.00;1;19.00'))
        out = self.verify()['checks']['fzp']
        self.assertFalse(out['passed']); self.assertEqual(out['different_ordered_rows'], 1)
        self.assertEqual(out['first_difference']['ordered_row_one_based'], 2)
        self.assertEqual(out['first_difference']['left_sec'], '2.00')

    def test_fzp_missing_tail_count(self):
        p = self.b / 'vissim_eval/run.fzp'; p.write_bytes(p.read_bytes().replace(b'3.00;1;22.00\n', b''))
        out = self.verify()['checks']['fzp']
        self.assertFalse(out['passed']); self.assertIsNone(out['first_difference']['right'])

    def test_missing_lsa_com_is_independent_failure(self):
        (self.b / 'vissim_eval/run.lsa').write_bytes(b'1;0;2;2;green;1;Fixed Time;0;\n')
        out = self.verify()
        self.assertTrue(out['actual_execution_equivalent'])
        self.assertFalse(out['native_lsa_com_coverage_passed']); self.assertFalse(out['passed'])
        self.assertEqual(len(out['checks']['native_lsa_right']['missing_com_events']), 2)

    def test_same_state_wrong_prepost_transition_fails(self):
        p = self.csv(self.b, 'signal_readback.csv')
        text = p.read_text().replace('2,1,1,RED,RED,1,immediate', '2,1,1,RED,RED,1,post_step')
        p.write_text(text)
        self.assertFalse(self.verify()['actual_execution_equivalent'])

    def test_reordered_post_after_immediate_rejected(self):
        p = self.csv(self.a, 'signal_readback.csv'); lines = p.read_text().splitlines()
        lines[3], lines[4] = lines[4], lines[3]; p.write_text('\n'.join(lines) + '\n')
        self.assertIn('Reordered', self.verify()['checks']['signals_left']['error'])

    def test_dense_one_second_gap_rejected(self):
        p = self.csv(self.a, 'signal_readback.csv')
        p.write_text(p.read_text().replace('2,1,1,AMBER,AMBER,1,post_step\n', ''))
        self.assertIn('missing one-second', self.verify()['checks']['signals_left']['error'])

    def test_missing_terminal_read_rejected(self):
        p = self.csv(self.b, 'signal_readback.csv')
        p.write_text(p.read_text().replace('3,1,1,RED,RED,1,post_step\n', ''))
        self.assertIn('Terminal', self.verify()['checks']['signals_right']['error'])

    def test_vsl_distribution_reference_not_vehicle_speed(self):
        p = self.csv(self.b, 'vsl_readback.csv')
        p.write_text(p.read_text().replace('1,7,10,120,120', '1,7,10,120,119'))
        self.assertIn('distribution reference', self.verify()['checks']['vsl_right']['error'])

    def test_nan_vsl_rejected(self):
        p = self.csv(self.b, 'vsl_readback.csv')
        p.write_text(p.read_text().replace('1,7,10,120,120', '1,7,10,120,NaN'))
        self.assertIn('Nonfinite', self.verify()['checks']['vsl_right']['error'])

    def test_missing_class_readback_rejected(self):
        p = self.csv(self.b, 'vsl_readback.csv')
        p.write_text(p.read_text().replace('3,7,30,120,120,1,immediate\n', ''))
        self.assertIn('Missing/duplicate VSL', self.verify()['checks']['vsl_right']['error'])

    def test_actual_history_difference_not_hidden_by_metadata_exclusion(self):
        p = self.csv(self.b, 'state_000003.json'); data = v.read(p)
        data['local_observation']['queue'][0] = 9; save(p, data)
        ap = self.csv(self.b, 'action_000003.json'); action = v.read(ap)
        action['run_provenance']['inputs']['state_json']['sha256'] = v.sha(p); save(ap, action)
        out = self.verify()['checks']['commands_and_state_inputs']
        self.assertFalse(out['passed']); self.assertEqual(out['decisions'][-1]['state_changed_keys'], ['local_observation'])

    def test_action_v2_does_not_accept_compact_state_provenance(self):
        p = self.csv(self.b, 'action_000003.json'); data = v.read(p)
        data['run_provenance'] = v.read(self.csv(self.b, 'state_000003.json'))['run_provenance']; save(p, data)
        self.assertIn('Unsupported action provenance', self.verify()['checks']['commands_and_state_inputs']['error'])

    def test_action_v2_run_and_input_identity_tamper_rejected(self):
        p = self.csv(self.b, 'action_000003.json'); original = v.read(p)
        mutations = (
            lambda x: x.update(run_id='foreign-run'),
            lambda x: x['inputs']['run_manifest_json'].update(path=str(self.a / 'run_provenance_old.json')),
            lambda x: x['inputs']['run_manifest_json'].update(sha256='0' * 64),
            lambda x: x['inputs']['state_json'].update(path=str(self.csv(self.b, 'state_000001.json'))),
            lambda x: x['inputs']['state_json'].update(sha256='0' * 64),
            lambda x: x['inputs']['state_json'].update(exists=False),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                data = json.loads(json.dumps(original)); mutate(data['run_provenance']); save(p, data)
                self.assertFalse(self.verify()['checks']['commands_and_state_inputs']['passed'])
        save(p, original)

    def test_state_manifest_still_requires_own_run_path(self):
        p = self.csv(self.b, 'state_000003.json'); data = v.read(p)
        data['run_provenance']['manifest_path'] = str(self.a / 'run_provenance_old.json'); save(p, data)
        self.assertIn('State manifest path differs', self.verify()['checks']['commands_and_state_inputs']['error'])

    def test_nonzero_exit_stops_before_payload_read(self):
        p = self.b / 'completion_receipt.json'; data = v.read(p); data['exit_code'] = 1; save(p, data)
        with patch.object(v, 'fzp_comparison', side_effect=AssertionError('must not read payload')):
            out = self.verify()
        self.assertTrue(out['payload_reads_skipped'])

    def test_live_or_wrong_run_receipt_rejected(self):
        p = self.b / 'completion_receipt.json'; data = v.read(p); data['owned_native_alive'] = True; save(p, data)
        self.assertTrue(self.verify()['payload_reads_skipped'])
        data['owned_native_alive'] = False; data['run_id'] = 'forged'; save(p, data)
        self.assertTrue(self.verify()['payload_reads_skipped'])

    def test_recorded_config_change_no_exception(self):
        p = self.b / ('run_provenance_' + self.b.name + '.json'); data = v.read(p)
        data['files']['tuning']['sha256'] = 'b' * 64; save(p, data)
        rp = self.b / 'completion_receipt.json'; receipt = v.read(rp); receipt['provenance_sha256'] = v.sha(p); save(rp, receipt)
        self.assertIn('files.tuning', self.verify()['checks']['completion_and_provenance']['error'])

    def test_same_intermediate_decision_missing_on_both_arms(self):
        arms = [v.arm_from_run(r, v.sha(r / 'completion_receipt.json'))[0] for r in (self.a, self.b)]
        with self.assertRaisesRegex(ValueError, 'Exact primary decision cadence'):
            v.run_inputs(arms, 3, 1)  # both arms lack the required t=2 decision

    def test_missing_lsa_file_does_not_hide_fzp_readback_pass(self):
        (self.b / 'vissim_eval/run.lsa').unlink()
        out = self.verify()
        self.assertTrue(out['actual_execution_equivalent']); self.assertFalse(out['passed'])
        self.assertIn('error', out['checks']['native_lsa_right'])

    def test_wrong_state_terminal_rejected(self):
        table(self.b / 'state_fast.csv', ['sim_sec'], [(1,), (2,)])
        self.assertTrue(self.verify()['payload_reads_skipped'])

    def test_missing_fast_changed_next_post_rejected(self):
        p = self.csv(self.b, 'signal_readback.csv')
        p.write_text(p.read_text().replace('2,1,1,AMBER,AMBER,1,post_step\n', ''))
        self.assertIn('matching next-step post', self.verify()['checks']['signals_right']['error'])

    def test_sparse_control_boundary_required(self):
        p = self.root / 'sparse.csv'
        rows = [(1, 1, 1, 'GREEN', 'GREEN', 1, 'immediate'), (2, 1, 1, 'GREEN', 'GREEN', 1, 'post_step'),
                (6, 1, 1, 'GREEN', 'GREEN', 1, 'post_step')]
        table(p, v.SG_FIELDS, rows)
        with self.assertRaisesRegex(ValueError, 'control-boundary'):
            v.readbacks(p, v.SG_FIELDS, {'1:1': {'start': 1, 'end': 6}}, command_check=lambda row: None, control_interval=3)

    def test_last_request_same_callback_wins_and_terminal_no_next_step(self):
        p = self.root / 'last.csv'
        table(p, v.SG_FIELDS, [(1, 1, 1, 'GREEN', 'GREEN', 1, 'immediate'),
                              (1, 1, 1, 'RED', 'RED', 1, 'immediate'),
                              (2, 1, 1, 'RED', 'RED', 1, 'post_step'),
                              (2, 1, 1, 'GREEN', 'GREEN', 1, 'immediate')])
        # Coverage-only callback fixture; full verify always constructs CommandClock.
        out = v.readbacks(p, v.SG_FIELDS, {'1:1': {'start': 1, 'end': 2}}, command_check=lambda row: None, control_interval=2)
        self.assertTrue(out['passed'])

    def add_city_commands_and_reads(self):
        for run in (self.a, self.b):
            for t in (1, 3):
                p = self.csv(run, f'action_{t:06d}.csv')
                with p.open(newline='') as f: content = list(csv.reader(f))
                table(p, content[0], [*content[1:],
                    command('signal', sc_no=2, offset=0, p1_green=5, p2_green=0, p3_green=0, p4_green=0),
                    command('signal_sg', dsd_no=1, sc_no=2, offset=0, p1_green=0, p2_green=5, green_sec=8)])
            p = self.csv(run, 'signal_readback.csv')
            frames = [(1, 'immediate', 'AMBER'), (2, 'post_step', 'AMBER'), (2, 'immediate', 'RED'), (3, 'post_step', 'RED')]
            rows = []
            for sec, stage, value in frames:
                rows += [(sec, 1, 1, value, value, 1, stage), (sec, 2, 1, 'GREEN', 'GREEN', 1, stage),
                         (sec, 2, 2, 'RED', 'RED', 1, stage)]
            table(p, v.SG_FIELDS, rows)
            (run / 'vissim_eval/run.lsa').write_bytes(b'1;0;1;1;amber;1;COM;0;\n1;0;2;1;green;1;COM;0;\n1;0;2;2;red;1;COM;0;\n2;0;1;1;red;1;COM;0;\n')

    def test_zero_window_owned_group_included_from_pin_not_csv(self):
        self.add_city_commands_and_reads()
        out = self.verify()
        self.assertTrue(out['passed'], out)
        self.assertEqual(out['checks']['commands_and_state_inputs']['zero_window_owned_groups'], ['2:2'])
        self.assertNotIn('2:9', out['checks']['commands_and_state_inputs']['signal_groups'])

    def test_zero_window_nonred_rejected(self):
        self.add_city_commands_and_reads(); p = self.csv(self.b, 'signal_readback.csv')
        p.write_text(p.read_text().replace('1,2,2,RED,RED', '1,2,2,GREEN,GREEN'))
        self.assertIn('must remain RED', self.verify()['checks']['signals_right']['error'])

    def test_unknown_sg_not_added_from_readback(self):
        self.add_city_commands_and_reads(); p = self.csv(self.b, 'signal_readback.csv')
        p.write_text(p.read_text().replace(',2,2,RED,RED', ',2,3,RED,RED'))
        self.assertIn('Unknown physical', self.verify()['checks']['signals_right']['error'])

    def test_plan_tamper_or_unpinned_rejected(self):
        p = self.root / 'generated_sgplan.vbs'; p.write_text(p.read_text().replace('2:0', '3:0'))
        self.assertIn('Pinned sibling SG plan changed', self.verify()['checks']['commands_and_state_inputs']['error'])

    def test_explicit_missing_optional_same_both_allowed_but_core_rejected(self):
        def change(key):
            for run in (self.a, self.b):
                p = run / ('run_provenance_' + run.name + '.json'); data = v.read(p)
                data['files'][key] = {'path': str(self.root / 'absent.json'), 'exists': False, 'sha256': ''}; save(p, data)
                rp = run / 'completion_receipt.json'; receipt = v.read(rp); receipt['provenance_sha256'] = v.sha(p); save(rp, receipt)
                for t in (1, 3):
                    ap = self.csv(run, f'action_{t:06d}.json'); action = v.read(ap)
                    action['run_provenance']['inputs']['run_manifest_json']['sha256'] = v.sha(p); save(ap, action)
        change('detector_mapping'); self.assertTrue(self.verify()['passed'])
        change('network'); self.assertTrue(self.verify()['payload_reads_skipped'])

    def test_both_readbacks_agree_but_violate_command_clock(self):
        for run in (self.a, self.b):
            p = self.csv(run, 'signal_readback.csv')
            p.write_text(p.read_text().replace('AMBER,AMBER', 'GREEN,GREEN'))
        out = self.verify()
        self.assertFalse(out['actual_execution_equivalent'])
        self.assertIn('Command clock mismatch', out['checks']['signals_left']['error'])
        self.assertIn('Command clock mismatch', out['checks']['signals_right']['error'])

    def test_globally_allowed_vsl_wrong_at_application_time_rejected(self):
        for run in (self.a, self.b):
            p = self.csv(run, 'action_000003.csv')
            with p.open(newline='') as f: rows = list(csv.DictReader(f))
            for row in rows:
                if row['kind'] == 'vsl': row['speed_kph'] = '80'
            table(p, ACTION_FIELDS, rows)
            # Sidecars still request/read120; both values are in the global command map.
        out = self.verify()
        self.assertIn('VSL command/readback mismatch', out['checks']['vsl_left']['error'])
        self.assertFalse(out['actual_execution_equivalent'])

    def test_receipt_clock_uses_zero_only_after_config_transport_native_proof(self):
        from diagnostics.com_execution_equivalence.test_ramp_timing_authority import attach_timing
        pp = self.a / ('run_provenance_' + self.a.name + '.json'); prov = v.read(pp)
        attach_timing(prov, self.root); save(pp, prov)
        receipt_path = self.a/'completion_receipt.json'; receipt = v.read(receipt_path)
        receipt['provenance_sha256'] = v.sha(pp); save(receipt_path, receipt)
        arm, _ = v.arm_from_run(self.a, v.sha(receipt_path))
        batches = {}
        for t in (1, 3):
            with self.csv(self.a, f'action_{t:06d}.csv').open(newline='') as stream:
                batches[t] = list(csv.DictReader(stream))
        clock, proof = v.build_command_clock(arm, batches)
        self.assertEqual(clock.ramp_amber_sec, 0)
        self.assertEqual(clock.expected_meter_state(1, 1), 'RED')
        self.assertEqual(proof['ramp_meter_timing']['amber_sec'], 0)

    def test_command_native_source_pin_tamper_rejected(self):
        p = self.root / 'runner.vbs'; p.write_text(p.read_text().replace('SEC = 3', 'SEC = 4'))
        out = self.verify()
        self.assertIn('native source pin changed', out['checks']['command_clock_left']['error'])
        self.assertFalse(out['actual_execution_equivalent'])


if __name__ == '__main__': unittest.main()
