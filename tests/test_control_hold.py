import copy
import csv
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'vendor/NumSim-mine'))

from evaluation.controllers.control_hold import fixed_vsl_values, fixed_vsl_reference, validate_fixed_vsl, write_hold
from evaluation.controllers.action_csv_schema import ACTION_CSV_FIELDS

HEADS = {k: [0, 2, 5, 10, 13, 15] for k in ('FW_E', 'FW_W')}
POLICY = dict(start_sec=900, base_kmh=110, zone_kmh={'FW_E__seg13': 90})


class ControlHoldTests(unittest.TestCase):
    def test_schedule_only_bottleneck_zone_and_not_entry(self):
        old = {f'{owner}__seg{i}': 110. for owner in HEADS for i in range(21)}
        old.update(FW_E=110., FW_W=110.)
        saved = copy.deepcopy(old)
        self.assertEqual(fixed_vsl_values(old, POLICY, HEADS, 750), old)
        for t in (900, 1050, 9000):
            actual = fixed_vsl_values(old, POLICY, HEADS, t)
            changed = {k for k in actual if actual[k] != old[k]}
            self.assertEqual(changed, {'FW_E', 'FW_E__seg13', 'FW_E__seg14'})
            self.assertTrue(all(actual[k] == 90 for k in changed))
        self.assertEqual(old, saved)

    def test_reject_entry_override_and_nonboundary(self):
        for p in (dict(POLICY, start_sec=901), dict(POLICY, zone_kmh={'FW_E__seg0': 90}),
                  dict(POLICY, base_kmh=120)):
            with self.assertRaises(ValueError): validate_fixed_vsl(p, HEADS)

    def test_window_restores_all_zone_addresses_at_end(self):
        policy = dict(POLICY, start_sec=1800, end_sec=5700)
        old = {f'{owner}__seg{i}': 110. for owner in HEADS for i in range(21)}
        old.update(FW_E=110., FW_W=110.)
        for t, speed in [(1650,110), (1800,90), (5550,90), (5700,110), (9000,110)]:
            old = fixed_vsl_values(old, policy, HEADS, t)
            self.assertEqual(old['FW_E__seg13'], speed)
            self.assertEqual(old['FW_E__seg14'], speed)
            self.assertEqual(old['FW_E'], speed)
            for owner in HEADS:
                self.assertEqual(old[owner+'__seg0'],110)
                self.assertEqual(old[owner+'__seg20'],110)
        for end in (1800, 1650, 5701, None, True, float('nan'), float('inf')):
            with self.subTest(end=end), self.assertRaises(ValueError):
                validate_fixed_vsl(dict(policy,end_sec=end), HEADS)

    def test_prediction_blocks_cross_both_schedule_boundaries(self):
        from evaluation.controllers import vissim_stackelberg_adapter  # canonical vendor bootstrap
        from evaluation.controllers import sdmpc_sequence as seq
        from src.models.state import ControlAction
        ref = ControlAction()
        ref.vsl = {f'{owner}__seg{i}':110. for owner in HEADS for i in range(21)}
        ref.vsl.update(FW_E=110., FW_W=110.)
        policy = dict(POLICY,start_sec=1800,end_sec=5700)
        for t,expected in [(1500,[110,110,90]),(1650,[110,90,90]),
                           (5400,[90,90,110]),(5550,[90,110,110]),(5700,[110,110,110])]:
            with self.subTest(t=t):
                action=fixed_vsl_reference(ref,policy,HEADS,t,150,3)
                self.assertEqual([c.vsl['FW_E__seg13'] for c in seq.actions(action,3)],expected)
                self.assertEqual(action.vsl['FW_E__seg13'],expected[0])
                self.assertEqual(seq.first_action(action).vsl,action.vsl)
        self.assertEqual(ref.vsl['FW_E__seg13'],110.)

    def test_failed_decision_does_not_invent_prices_or_predictions(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            provenance = dict(run_id='owned')
            raw = dict(vsl=dict(FW_E=110., FW_W=110.), green_times={'SC1_p1': 35.},
                offsets={'SC1': 3.}, ramp_metering={'R': 500.},
                diagnostics={'sdmpc_prediction_sequence': {'future': 'unused'}},
                metadata=dict(sim_sec=750., run_provenance=provenance, sdmpc_state={'unapplied': True}),
                run_provenance=provenance, prediction={'false': 'future'})
            previous = folder/'previous.json'
            previous.write_text(json.dumps(raw), encoding='utf-8')
            rows=[]
            for dsd in (63, 64, 65, 66):
                row = dict.fromkeys(ACTION_CSV_FIELDS, '')
                row.update(kind='vsl', id='RW_FW_E_S13', dsd_no=str(dsd), speed_kph='110.0', metadata='ok')
                rows.append(row)
            with previous.with_suffix('.csv').open('w', newline='') as f:
                w=csv.DictWriter(f, fieldnames=ACTION_CSV_FIELDS);w.writeheader();w.writerows(rows)
            state = folder/'state.json'
            state.write_text(json.dumps(dict(sim_sec=900,control_interval_sec=150,run_provenance=provenance)))
            output=folder/'output.json';output.write_text('partial failed artifact')
            args=SimpleNamespace(state_json=str(state),previous_action_json=str(previous),
                out_action_json=str(output),out_action_csv=str(output.with_suffix('.csv')))
            tuning=dict(runtime={'decision_error_policy':'hold_previous'},
                adapter={'sdmpc_fixed_vsl':POLICY},freeway={'vsl_zone_heads':HEADS},
                config_overrides={'network':{'freeway_segments_per_link':21}})
            write_hold(args,tuning)
            held=json.loads(output.read_text(encoding='utf-8'))
            self.assertNotIn('sdmpc_state',held['metadata'])
            self.assertNotIn('prediction',held)
            self.assertNotIn('sdmpc_prediction_sequence',held['diagnostics'])
            for k in ('green_times','offsets','ramp_metering'): self.assertEqual(held[k],raw[k])
            self.assertEqual(held['metadata']['sim_sec'],900.)
            self.assertEqual(output.with_name('output.json.failed_decision').read_text(),'partial failed artifact')
            with output.with_suffix('.csv').open() as f:
                self.assertEqual({float(r['speed_kph']) for r in csv.DictReader(f)}, {90.})
            self.assertEqual(json.loads(previous.read_text()),raw)
            # Failure at the OFF boundary holds RM/signals but still restores VSL110.
            raw['metadata']['sim_sec']=5550.
            raw['vsl']={'FW_E':90.,'FW_W':110.,'FW_E__seg13':90.,'FW_E__seg14':90.}
            previous.write_text(json.dumps(raw),encoding='utf-8')
            for row in rows:row['speed_kph']='90.0'
            with previous.with_suffix('.csv').open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=ACTION_CSV_FIELDS);w.writeheader();w.writerows(rows)
            state.write_text(json.dumps(dict(sim_sec=5700,control_interval_sec=150,run_provenance=provenance)))
            args.out_action_json=str(folder/'off.json');args.out_action_csv=str(folder/'off.csv')
            tuning['adapter']['sdmpc_fixed_vsl']=dict(POLICY,start_sec=1800,end_sec=5700)
            write_hold(args,tuning)
            off=json.loads(Path(args.out_action_json).read_text())
            self.assertEqual(off['vsl']['FW_E__seg13'],110.)
            for field in ('green_times','offsets','ramp_metering'):self.assertEqual(off[field],raw[field])
            with Path(args.out_action_csv).open() as f:
                self.assertEqual({float(r['speed_kph']) for r in csv.DictReader(f)},{110.})
            raw['metadata']['sim_sec']=600
            previous.write_text(json.dumps(raw))
            with self.assertRaises(ValueError): write_hold(args,tuning)


if __name__ == '__main__': unittest.main()
