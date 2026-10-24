import unittest
from retain_tracks import classify


class ClassificationTest(unittest.TestCase):
    def test_short_connector_can_be_skipped(self):
        result,_=classify({'time':2000},[dict(sec=2005,link='1')],{'right':{'10616','381','10607','1'}})
        self.assertEqual(result,'right')

    def test_signal_does_not_choose_turn(self):
        result,_=classify({'time':2000,'sg':'5','head_lane':5},[dict(sec=2005,link='10023')],{'through':{'10023'},'left':{'10622'}})
        self.assertEqual(result,'through')

    def test_future_is_not_training(self):
        result,_=classify({'time':2390},[dict(sec=2400,link='1')],{'right':{'1'}})
        self.assertEqual(result,'unresolved')

    def test_conflicting_path_stays_ambiguous(self):
        result,_=classify({'time':2000},[dict(sec=2005,link='1'),dict(sec=2010,link='10023')],{'right':{'1'},'through':{'10023'}})
        self.assertEqual(result,'ambiguous')


if __name__=='__main__':unittest.main()
