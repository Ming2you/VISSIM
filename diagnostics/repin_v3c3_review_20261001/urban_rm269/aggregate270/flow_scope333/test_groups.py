import unittest
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.flow_scope333.groups import family_keys, stock_total, boundary_ledger, crossing_edges


class GroupTests(unittest.TestCase):
    def test_initially_empty_alias_is_still_included(self):
        keys = family_keys({'a': {'origin': 'first'}, 'b': {'origin': 'second'},
                            'c': {'origin': 'unrelated'}}, ('first', 'second'))
        self.assertEqual(keys, {'storage:first', 'storage:second', 'movement:a', 'movement:b'})
        self.assertEqual(stock_total({'stocks': {'movement:b': {'inside': 4, 'outside': 0},
                                                 'movement:c': {'inside': 8, 'outside': 0}}}, keys), 4)

    def test_internal_handoffs_do_not_count_as_arrivals(self):
        rows = [dict(start_sec=0, end_sec=10, source=s, target=t, vehicles=n)
                for s, t, n in [('outside', 'store', 7), ('store', 'queue', 5), ('queue', 'next', 3)]]
        ledger = boundary_ledger(rows, {'store', 'queue'}, 0, 10)
        self.assertEqual((ledger['incoming'], ledger['outgoing']), (7, 3))

    def test_geometry_boundary_preserves_alternative_internal_paths(self):
        self.assertEqual(crossing_edges({(1, 2), (2, 3), (2, 4), (3, 5), (4, 5), (5, 6)}, {2, 3, 4, 5}),
                         ([(1, 2)], [(5, 6)]))


if __name__ == '__main__':
    unittest.main()
