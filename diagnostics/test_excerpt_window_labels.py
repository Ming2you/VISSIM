"""Small command/LSA fixtures only; no FZP, model or native process access."""
import contextlib
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from diagnostics.control_improvement.r03_u030_first_window import extract as m


class ExcerptWindows(unittest.TestCase):
    def test_seed_comes_from_provenance_with_optional_receipt_consistency(self):
        for seed in (13, 17):
            self.assertEqual(m.provenance_seed({'seed':seed}), seed)
            self.assertEqual(m.provenance_seed({'seed':seed}, {'completed':True}), seed)
            self.assertEqual(m.provenance_seed({'seed':seed}, {'seed':seed}), seed)
        for seed in (None, 0, -1, True, 17.0, '17', float('nan')):
            with self.subTest(seed=seed), self.assertRaisesRegex(ValueError, 'positive integer seed'):
                m.provenance_seed({'seed':seed})
        for receipt_seed in (13, None, True, 17.0, '17'):
            with self.subTest(receipt_seed=receipt_seed), self.assertRaisesRegex(ValueError, 'seed mismatch'):
                m.provenance_seed({'seed':17}, {'seed':receipt_seed})

    def test_dense_window_budget_retains_selected_extent_and_deadline(self):
        # In-memory size fixture only: no native FZP is opened or constructed.
        size = 500*1024*1024
        limits = m.window_read_limits(size, 2400, 2850)
        self.assertEqual(limits['max_bytes'], size+1024*1024)
        self.assertGreater(limits['max_bytes'], 96*1024*1024)
        self.assertEqual(limits['window_sec'], [2400,2850])
        self.assertEqual(limits['expected_frames'], 451)
        self.assertEqual(limits['deadline_sec'], 45)
        self.assertEqual(m.window_read_limits(size, 900, 1350)['expected_frames'], 451)
        for invalid_size in (0, -1, True):
            with self.subTest(size=invalid_size), self.assertRaisesRegex(ValueError, 'nonempty'):
                m.window_read_limits(invalid_size, 2400, 2850)

    def test_default_and_explicit_window_arguments(self):
        default = m.parse_args([])
        self.assertEqual((default.start, default.end), (900, 1050))
        self.assertEqual(m.parse_args(['--end', '1350']).start, 900)
        args = m.parse_args(['--start', '2400', '--end', '2850', '--output', 'fresh'])
        self.assertEqual((args.start, args.end, args.out), (2400, 2850, Path('fresh')))
        self.assertEqual(m.parse_args(['--out', 'fresh']).out, args.out)
        for argv in (['--start', '0'], ['--start', '2401', '--end', '2850'],
                     ['--start', '2400', '--end', '2400'], ['--end', '1351']):
            with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    m.parse_args(argv)

    def fixture(self, base, start, *, signals=True):
        run = base / 'fixture_run'
        decisions = run / ('decisions_'+run.name)
        decisions.mkdir(parents=True)
        output = base / 'output'
        output.mkdir()
        fields = ('kind', 'id', 'dsd_no', 'sc_no', 'sg_no', 'speed_kph', 'rate_vph', 'green_sec')
        for sec in (start-150, start):
            rows = [dict(kind='vsl', id='v1', dsd_no='1', sc_no='', speed_kph=80 if sec<start else 70),
                    dict(kind='ramp_meter', id='r1', dsd_no='', sc_no='9101', rate_vph=600,
                         green_sec=10 if sec<start else 12)]
            if signals:
                rows.append(dict(kind='signal', id='s1', dsd_no='', sc_no='1004', sg_no='6'))
            with (decisions/f'action_{sec:06d}.csv').open('w', newline='', encoding='utf-8') as stream:
                writer = csv.DictWriter(stream, fields)
                writer.writeheader(); writer.writerows(rows)
            (decisions/f'action_{sec:06d}.json').write_text(json.dumps(
                {'ramp_metering': {'r1': sec}, 'N_UF_star': sec+1}), encoding='utf-8')
        native_dir = run/'vissim_eval'
        native_dir.mkdir()
        # Distinct pre-window, in-window and right-boundary events verify the
        # durations use the requested interval, rather than merely its labels.
        events = [(start-160,1004,6,'GREEN'), (start-140,1004,6,'RED'),
                  (start-100,1004,3,'GREEN'), (start-100,1004,6,'GREEN'),
                  (start-90,1005,1,'GREEN'), (start,1004,6,'RED'),
                  (start+1,1004,6,'GREEN')]
        (native_dir/'fixture.lsa').write_text(''.join(
            f'{sec};0;{sc};{sg};{state}\n' for sec,sc,sg,state in events), encoding='utf-8')
        return run, output, fields

    def test_actual_interval_and_legacy_names(self):
        for start in (900, 2400):
            with self.subTest(start=start), tempfile.TemporaryDirectory(prefix='excerpt_fixture_') as tmp:
                run, output, fields = self.fixture(Path(tmp), start)
                sources = {}
                with patch.object(m, 'OUT', output):
                    summary = m.command_evidence(run, start, sources)
                prior = start-150
                self.assertEqual(set(summary['command_counts']), {str(prior),str(start)})
                self.assertEqual(summary[f'meter_group_rates_{start}'], {'r1':start})
                self.assertEqual(summary[f'NUF_{start}'], start+1)
                self.assertEqual(summary['vsl_changed_rows'], 1)
                self.assertEqual(summary['meter_changed_physical_greens'], 1)
                self.assertEqual(summary['command_observation_window']['recorded_lsa_duration_window_sec'], [prior,start])
                self.assertEqual(summary['command_observation_window']['recorded_lsa_prefix_end_sec'], start)
                self.assertEqual(len(sources), 5)
                self.assertEqual({p.name for p in output.iterdir()}, set(m.command_artifact_names(start)))
                with (output/f'native_{prior}_{start}_observed_sg.csv').open(newline='') as stream:
                    rows = {r['sc_sg']:r for r in csv.DictReader(stream)}
                self.assertEqual(set(rows), {'1004:6','1004:3'})
                self.assertEqual(float(rows['1004:6'][f'native_green_sec_{prior}_{start}']), 110)
                self.assertEqual(float(rows['1004:3'][f'native_unknown_sec_{prior}_{start}']), 50)
                with (output/f'action{start}_urban_written.csv').open(newline='') as stream:
                    reader = csv.DictReader(stream)
                    self.assertEqual(reader.fieldnames, list(fields))
                    self.assertEqual(len(list(reader)), 1)

    def test_nc_without_signal_commands_has_truthful_header_only_tables(self):
        with tempfile.TemporaryDirectory(prefix='excerpt_fixture_') as tmp:
            run, output, fields = self.fixture(Path(tmp), 2400, signals=False)
            with patch.object(m, 'OUT', output):
                summary = m.command_evidence(run, 2400, {})
            self.assertEqual(summary['command_observation_window']['selected_scs'], [])
            self.assertEqual(summary['command_observation_window']['selected_sg_rows'], 0)
            self.assertGreater(summary['native_clock_prefix']['raw_event_rows'], 0)
            self.assertIn('not missing native signals', summary['native_signal_scope'])
            for name in ('action2400_urban_written.csv','native_2250_2400_observed_sg.csv'):
                with (output/name).open(newline='') as stream:
                    reader = csv.DictReader(stream)
                    self.assertEqual(list(reader), [])
                    self.assertTrue(reader.fieldnames)


if __name__ == '__main__':
    unittest.main()
