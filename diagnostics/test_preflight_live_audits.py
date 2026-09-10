import copy
import unittest

from diagnostics.audit_controlled_head_window import controlled_exposure
from diagnostics.compare_preflight_live_action import head_values


class RecordedAuditTests(unittest.TestCase):
    def rows(self):
        rows = []
        for sec in range(10, 13):
            for stage, time in [('immediate', sec), ('post_step', sec+1)]:
                state = 'GREEN' if sec == 10 else 'RED'
                rows.append(dict(sim_sec=str(time), sc_no='5', sg_no='2', stage=stage,
                                 requested_state=state, readback_state=state, ok='1'))
        # The old command's boundary post-step must not be used as the new hold.
        rows.append(dict(sim_sec='10', sc_no='5', sg_no='2', stage='post_step',
                         requested_state='RED', readback_state='RED', ok='1'))
        return rows

    def test_boundary_left_hold(self):
        self.assertEqual(controlled_exposure(self.rows(), ('5', '2'), 10, 13)[0], 1)

    def test_missing_duplicate_nonfinite_and_failed_trace_rejected(self):
        for mode in ('missing', 'duplicate', 'nonfinite', 'failed', 'noninteger'):
            rows = self.rows()
            if mode == 'missing':
                rows.pop(2)
            elif mode == 'duplicate':
                rows.append(copy.deepcopy(rows[2]))
            elif mode == 'nonfinite':
                rows[2]['sim_sec'] = 'NaN'
            elif mode == 'failed':
                rows[2]['ok'] = '0'
            else:
                rows[2]['sim_sec'] = '11.5'
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                controlled_exposure(rows, ('5', '2'), 10, 13)

    def test_head_hash_normalizes_only_for_comparison_and_keeps_raw_key(self):
        key = 'head_discharge_floor_183_p3_0123456789abcdef'
        values, identities = head_values({key: 600., 'head_provenance_x': 1.})
        self.assertEqual(values, {'head_discharge_floor_183_p3': 600.})
        self.assertEqual(identities['head_discharge_floor_183_p3'], key)

    def test_multiple_contexts_for_one_head_rejected(self):
        with self.assertRaises(ValueError):
            head_values({'head_candidate_rate_183_p3_0123456789abcdef': 600.,
                         'head_candidate_rate_183_p3_1123456789abcdef': 600.})


if __name__ == '__main__':
    unittest.main()
