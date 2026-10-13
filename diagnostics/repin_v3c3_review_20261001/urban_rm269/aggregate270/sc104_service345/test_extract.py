import unittest
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc104_service345.extract import crossed
class CrossingTest(unittest.TestCase):
    heads={1:96.,2:96.,3:96.,4:96.}
    def row(self,t=1800.1,link=1220061200,lane=1,pos=80.,route=1095):
        return (t,9,link,lane,pos,route,1)
    def test_same_link(self):
        self.assertTrue(crossed(self.row(),self.row(t=1805.1,pos=98.),self.heads))
    def test_connector_skip(self):
        self.assertTrue(crossed(self.row(link=10082),self.row(t=1805.1,link=1220021204),self.heads))
    def test_not_yet_crossed(self):
        self.assertFalse(crossed(self.row(),self.row(t=1805.1,pos=95.),self.heads))
    def test_already_crossed(self):
        self.assertFalse(crossed(self.row(pos=97.),self.row(t=1805.1,link=10125),self.heads))
    def test_gap_or_wrong_route(self):
        self.assertFalse(crossed(self.row(),self.row(t=1810.1,link=10125),self.heads))
        self.assertFalse(crossed(self.row(route=1032),self.row(t=1805.1,link=10125),self.heads))
    def test_left_lane_unqualified(self):
        self.assertFalse(crossed(self.row(lane=5),self.row(t=1805.1,link=10125),self.heads))
if __name__=='__main__':unittest.main()
