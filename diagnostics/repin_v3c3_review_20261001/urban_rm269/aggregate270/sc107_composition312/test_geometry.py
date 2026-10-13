import unittest,xml.etree.ElementTree as ET
from audit import connector_support,reachable


class GeometryTest(unittest.TestCase):
    def test_four_lanes_starting_at_two_include_five(self):
        node=ET.fromstring('<link><fromLinkEndPt lane="100 2" pos="85"/><lanes><lane/><lane/><lane/><lane/></lanes></link>')
        self.assertEqual(connector_support(node)['lanes'],[2,3,4,5])

    def test_passed_branch_cannot_receive_current_queue(self):
        geo={'right':dict(lanes=[1],pos=8), 'through':dict(lanes=[2,3,4,5],pos=85)}
        self.assertEqual(reachable(dict(lane_no=1,position_m=74),geo),[])
        self.assertEqual(reachable(dict(lane_no=1,position_m=4),geo),['right'])
        self.assertEqual(reachable(dict(lane_no=5,position_m=74),geo),['through'])


if __name__=='__main__':unittest.main()
