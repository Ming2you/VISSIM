"""Physical proof reuse must preserve the score's original serialized order."""
import copy
import pickle
import unittest

from diagnostics.test_joint_owner_game_candidate import action, physical_tokens
from evaluation.controllers import joint_owner_game as game


class FinalAuditTokenOrderTests(unittest.TestCase):
    def test_balanced_traversal_preserves_original_physical_mapping_bytes(self):
        own = game.Ownership(('SC1', 'SC5', 'FW_W', 'FW_E'), (
            game.Address('offsets', 'SC1', 'SC1', 'strategy'),
            game.Address('green_times', 'SC5_p1', 'SC5', 'strategy'),
            game.Address('vsl', 'FW_W', 'FW_W', 'strategy'),
            game.Address('ramp_metering', 'RM_E', 'FW_E', 'strategy'),
        ), ())
        incumbent, context = action(own), {}
        expected = physical_tokens(own, incumbent, context)
        for traversal in ('sequential', 'round_robin', 'sequential_balanced', 'round_robin_balanced'):
            with self.subTest(traversal=traversal):
                prepared = game.prepare_final_audit_domains(
                    own, incumbent, context,
                    neighbors=lambda owner, base, ctx: game.Neighborhood(
                        (copy.deepcopy(base),), True, 'synthetic singleton; no production coverage'),
                    context_fingerprint=lambda ctx: 'fixed-context',
                    physical_fingerprint=lambda u, ctx: physical_tokens(own, u, ctx),
                    traversal=traversal, reuse_physical_proofs=True,
                    physical_proof_guard=lambda ctx: None)
                actual = prepared['physical_fingerprint'](incumbent, context)
                self.assertEqual(actual, expected)
                self.assertEqual(tuple(actual), tuple(expected))
                self.assertEqual(pickle.dumps(actual, protocol=5), pickle.dumps(expected, protocol=5))
                actual['SC1'] = 'changed caller copy'
                self.assertEqual(prepared['physical_fingerprint'](incumbent, context), expected)
                self.assertEqual(prepared['evaluation_budget'], len(own.owners))


if __name__ == '__main__':
    unittest.main()
