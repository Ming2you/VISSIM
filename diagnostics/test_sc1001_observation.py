"""Causal observation contracts for the experimental shared SC1001 approach."""
import copy
import unittest

from evaluation.controllers.lane_offramp_runtime import update_shared_observation

OPTIONS=dict(enabled=True,min_green_sec=30,min_crossings=5)


def vehicle(key,link,position=50,decision=0):
    return [key,link,1,position,0,5,decision,1,'STATIC']


def observe(at,previous=None,vehicles=(),counts=(25,24,12),valid=True):
    frame=dict(time_s=at,vehicles=list(vehicles))
    window=dict(start_sec=at-150,end_sec=at,clock_complete=valid,unknown_links={},
        heads=[dict(link='127',lane=i+1,head_id=str(i+1),sc='1001',
                    sg='5' if i==2 else '2',green_sec=24 if i==2 else 45,
                    qualified_crossings=count) for i,count in enumerate(counts)])
    return update_shared_observation(previous,frame,window,OPTIONS,239.384)


class SharedObservationTests(unittest.TestCase):
    def test_service_uses_two_disjoint_blocks_not_single_busy_window(self):
        prior=None
        for at in (150,300,450):
            prior=observe(at,prior)
            self.assertTrue(all(s['floor_veh_h']==0 for s in prior['service'].values()))
        prior=observe(600,prior,counts=(1,1,1))
        # Low second block is retained; no cherry-picking the busy windows.
        self.assertAlmostEqual(prior['service']['1']['support_veh_h'],26/90*3600)
        self.assertAlmostEqual(prior['service']['3']['support_veh_h'],13/48*3600)

    def test_short_sg5_green_has_adequate_pooled_exposure(self):
        prior=None
        for at in (150,300,450,600):prior=observe(at,prior)
        self.assertAlmostEqual(prior['service']['3']['floor_veh_h'],1800)
        self.assertEqual(prior['service']['3']['history'][0]['green'],[24])

    def test_source_tracks_current_visit_and_drops_absent_id(self):
        a=observe(150,vehicles=[vehicle(1,32),vehicle(2,10491)])
        b=observe(300,a,[vehicle(1,127,decision=1117),vehicle(2,127,decision=1117),vehicle(3,127)])
        self.assertEqual(b['sources'],{'1':'initial_city','2':'initial_off'})
        self.assertEqual(b['source_unknown_current'],1)
        c=observe(450,b,[vehicle(2,127)])
        d=observe(600,c,[vehicle(1,127),vehicle(2,127)])
        self.assertNotIn('1',d['sources'])
        e=observe(750,d,[vehicle(2,32)])
        self.assertEqual(e['sources']['2'],'initial_city')

    def test_geometry_before_city_merge_and_committed_routes_identify_source(self):
        a=observe(150,vehicles=[vehicle(1,129,200),vehicle(2,129,260),
                               vehicle(3,127,decision=1131),vehicle(4,127,decision=1136)])
        self.assertEqual(a['sources'],{'1':'initial_city','3':'initial_off','4':'initial_city'})

    def test_committed_off_route_on_mainline_survives_short_connector_skip(self):
        a=observe(150,vehicles=[vehicle(1,26,decision=1132)])
        b=observe(300,a,[vehicle(1,127,decision=1117)])
        self.assertEqual(b['sources'],{'1':'initial_off'})
        c=observe(450,b,[vehicle(1,40,decision=1119)])
        d=observe(600,c,[vehicle(1,127,decision=1117)])
        self.assertEqual(d['sources'],{})

    def test_gap_resets_ancestry_and_service_support(self):
        a=None
        for at in (150,300,450,600):a=observe(at,a,[vehicle(1,32)])
        b=observe(900,a,[vehicle(1,127)])
        self.assertEqual(b['sources'],{})
        self.assertEqual(b['service']['1']['floor_veh_h'],0)
        c=observe(750,a,[vehicle(1,127)],valid=False)
        self.assertEqual(c['service'],{})

    def test_future_window_rejected_and_inputs_not_mutated(self):
        a=observe(150,vehicles=[vehicle(1,10481)])
        before=copy.deepcopy(a)
        with self.assertRaisesRegex(ValueError,'current frame'):
            update_shared_observation(a,dict(time_s=300,vehicles=[]),dict(end_sec=450),OPTIONS,239.384)
        self.assertEqual(a,before)


if __name__=='__main__':unittest.main()
