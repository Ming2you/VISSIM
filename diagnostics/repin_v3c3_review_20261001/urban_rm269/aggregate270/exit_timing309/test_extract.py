import unittest
from extract_closed import events_between


class BoundaryTests(unittest.TestCase):
    def test_four_observed_cases_and_mass(self):
        membership={'1':True,'2':False,'3':True}
        before={1:'1',2:'2',3:'1',5:'1'}
        after={1:'2',2:'1',4:'1',5:'3'}
        rows=events_between(before,after,membership,2400.,2405.)
        self.assertEqual({r['vehicle']:r['kind'] for r in rows},
                         {1:'observed_exit',2:'observed_entry',3:'disappeared_inside',4:'appeared_or_reappeared_inside'})
        self.assertEqual({r['mid_sec'] for r in rows},{2402.5})

    def test_missing_vehicle_is_not_exit(self):
        rows=events_between({1:'1'},{},{'1':True},2400,2405)
        self.assertEqual(rows[0]['kind'],'disappeared_inside')
        self.assertIsNone(rows[0]['to_link'])

    def test_undefined_membership_rejected(self):
        with self.assertRaises(AssertionError): events_between({1:'9'},{},{'1':True},0,5)


if __name__=='__main__':unittest.main()
