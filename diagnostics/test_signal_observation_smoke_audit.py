"""Small read-only audit tests; no simulator, controller or large fixture."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import json
from diagnostics.audit_signal_observation_smoke import prefix_payload, action_evidence
from diagnostics import audit_signal_observation_smoke as audit


class SmokeAuditTests(unittest.TestCase):
    def payload(self, rows, end=2, complete=False):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'sample.fzp'
            path.write_bytes(b'* metadata\r\n$VEHICLE:SIMSEC;NO\r\n'+rows)
            return prefix_payload(path,end,completed_eof=complete)

    def test_same_ordered_prefix_ignores_later_frames(self):
        first=self.payload(b'1;9\r\n1;8\r\n2;4\r\n3;7\r\n')
        second=self.payload(b'1;9\r\n1;8\r\n2;4\r\n3;999\r\n4;333\r\n')
        self.assertEqual(first['payload_sha256'],second['payload_sha256'])
        self.assertEqual(first['rows'],3)
        reordered=self.payload(b'1;8\r\n1;9\r\n2;4\r\n3;7\r\n')
        self.assertNotEqual(first['payload_sha256'],reordered['payload_sha256'])

    def test_final_frame_requires_complete_eof_or_later_complete_row(self):
        with self.assertRaisesRegex(ValueError,'Final frame'):
            self.payload(b'1;1\r\n2;2\r\n')
        self.assertEqual(self.payload(b'1;1\r\n2;2\r\n',complete=True)['frames'],2)
        with self.assertRaisesRegex(ValueError,'Partial'):
            self.payload(b'1;1\r\n2;2\r\n3;7')

    def test_gap_noninteger_nonfinite_and_time_reversal_reject(self):
        for rows in (b'1;1\n3;3\n',b'1;1\n1.5;2\n3;3\n',
                     b'1;1\nnan;2\n',b'1;1\n2;2\n1;3\n3;4\n'):
            with self.subTest(rows=rows),self.assertRaises(ValueError):self.payload(rows)

    def test_trajectory_only_accepts_off_run_without_head_snapshots(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in ('on','off'):
                run=root/'evaluation/runs'/name;(run/'vissim_eval').mkdir(parents=True)
                (run/f'runlog_{name}.txt').write_text('STAGE=SIM_DONE\n')
                (run/f'run_provenance_{name}.json').write_text(json.dumps({
                    'run_id':name,'controller':'no-control','seed':13,'sim_period_sec':2}))
                (run/'vissim_eval/sample.fzp').write_bytes(b'$VEHICLE:SIMSEC;NO\n1;4\n2;4\n')
            with patch.object(audit,'ROOT',root):
                result=audit.compare_trajectory_prefixes('off','on',2)
            self.assertTrue(result['ordered_payload_exact'])
            self.assertEqual(result['payloads'][0]['frames'],2)

    def test_recorded_floor_needs_adjacent_candidates_then_monotone_carry(self):
        def action(end):
            return {'run_provenance':{'run_id':'run'},'metadata':{
                'sim_sec':end,'head_observation_snapshot_sec':end,
                'head_provenance_identity':1,'head_candidate_rate_link_p1':400,
                'head_candidate_end_link_p1':end}}
        previous=action(150);current=action(300)
        current['metadata']['head_discharge_floor_link_p1']=620
        row=action_evidence(current,previous,'identity','run',150,300)
        self.assertEqual(row['new_floor_count'],1)
        later=action(450);later['metadata']['head_discharge_floor_link_p1']=620
        self.assertEqual(action_evidence(later,current,'identity','run',300,450)['prior_floor_count'],1)
        for tamper in ('provenance','overlap','lost','decreased'):
            bad=deepcopy(later)
            prior=deepcopy(current)
            if tamper=='provenance':bad['run_provenance']['run_id']='foreign'
            if tamper=='overlap':
                prior=previous;prior['metadata']['head_candidate_end_link_p1']=299
            if tamper=='lost':del bad['metadata']['head_discharge_floor_link_p1']
            if tamper=='decreased':bad['metadata']['head_discharge_floor_link_p1']=619
            with self.subTest(tamper=tamper),self.assertRaises(ValueError):
                action_evidence(bad,prior,'identity','run',300,450)


if __name__=='__main__':unittest.main()
