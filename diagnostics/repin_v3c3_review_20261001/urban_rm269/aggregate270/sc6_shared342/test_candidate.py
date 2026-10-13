import unittest
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc6_shared342.candidate import access_limit

class Access(unittest.TestCase):
    def test_red_clear_pocket_allows_prehead_turn(self):
        # Old green-only formula gives zero although a downstream red head
        # has no authority over an accessible upstream right branch.
        self.assertEqual(access_limit(8,1,2,3,4,0),(3,0,0))
    def test_red_queue_reaching_branch_blocks(self):
        self.assertEqual(access_limit(8,3,2,3,4,0),(0,1,0))
    def test_partial_coverage_and_actual_through_receiving(self):
        self.assertEqual(access_limit(8,2.5,2,3,4,2),(2.25,.5,.5))
        self.assertEqual(access_limit(8,3,2,3,4,2),(1.5,1,.5))
        self.assertEqual(access_limit(8,3,2,3,4,4),(3,1,1))
    def test_stock_bound(self):
        self.assertEqual(access_limit(.4,0,2,3,4,4)[0],.4)
    def test_bad_service_fails(self):
        with self.assertRaises(ValueError):access_limit(8,3,2,3,4,5)

if __name__=='__main__':unittest.main()
