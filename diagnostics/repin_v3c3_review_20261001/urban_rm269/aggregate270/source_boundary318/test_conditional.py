import unittest
from types import SimpleNamespace
from conditional import substitute


class ConditionalSourceTests(unittest.TestCase):
    def forecast(self):
        return [SimpleNamespace(freeway_mainline={'FW_E':7200., 'FW_W':4152.},
                                urban={'source':73.}, ramp_arrival={'10681':17.}) for _ in range(3)]

    def test_units_and_only_source_field(self):
        old=self.forecast()
        new=substitute(old, {'FW_E':[279,311,299], 'FW_W':[179,183,177]})
        self.assertEqual([x.freeway_mainline['FW_E']/24 for x in new], [279,311,299])
        self.assertEqual(sum(x.freeway_mainline['FW_W']/24 for x in new),539)
        self.assertEqual(old[0].freeway_mainline['FW_E'],7200)
        new[0].urban['source']=0
        self.assertEqual(old[0].urban['source'],73)

    def test_reject_partial_boundary(self):
        with self.assertRaises(ValueError):substitute(self.forecast(), {'FW_E':[279,311,299]})

    def test_reject_bad_counts(self):
        for counts in ([1,2], [1,2,-1], [1,2,float('nan')], [1,2,True]):
            with self.subTest(counts=counts), self.assertRaises(ValueError):
                substitute(self.forecast(), {'FW_E':counts, 'FW_W':[179,183,177]})


if __name__=='__main__':unittest.main()
