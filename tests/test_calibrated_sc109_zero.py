import sys,unittest
from pathlib import Path
from types import SimpleNamespace
from evaluation.controllers import calibrated_urban_runtime as urban,vissim_stackelberg_adapter as a
LINKS=urban.module('sc109_initial320.candidate').LINKS

def raw(link='174',front_stopped=False):
    return {'sim_sec':1800,'vehicle_records':{'complete':True,'paused_at_sim_sec':1800,'capture_sim_sec_before':1800,'capture_sim_sec_after':1800,
      'records':[{'link_no':int(link),'lane_no':4,'stopped':x} for x in (front_stopped,True,True)]},
      'local_observation':{'queue_bin_m':7.,'queue_bins':{link+'|4|69':[1,int(front_stopped)],link+'|4|68':[2,2]}}}
class Tests(unittest.TestCase):
    def setUp(self):self.cfg=SimpleNamespace(network=SimpleNamespace())
    def test_zero_is_not_missing_or_all_stopped_for_owned_links(self):
        for link in sorted(LINKS):
            with self.subTest(link=link):
                r=raw(link);urban.configure_queue_projection(self.cfg,r,{})
                old=a._link_lengths_m;a._link_lengths_m=lambda:{link:490.}
                try:
                    self.assertNotIn(link,a._contiguous_stopline_queue(r))
                    self.assertEqual(a._contiguous_stopline_queue(r,zero_links=self.cfg.network.kinematic_queue_zero_links)[link],0.)
                    self.assertEqual(sum(v['stopped'] for v in r['vehicle_records']['records']),2)
                finally:a._link_lengths_m=old
    def test_positive_contiguous_queue_stays_ready(self):
        for link in ('173','174'):
            with self.subTest(link=link):
                r=raw(link,True);urban.configure_queue_projection(self.cfg,r,{})
                old=a._link_lengths_m;a._link_lengths_m=lambda:{link:490.}
                try:self.assertEqual(a._contiguous_stopline_queue(r,zero_links=self.cfg.network.kinematic_queue_zero_links)[link],3.)
                finally:a._link_lengths_m=old
    def test_incomplete_records_rejected(self):
        r=raw();r['vehicle_records']['complete']=False
        with self.assertRaises(ValueError):urban.configure_queue_projection(self.cfg,r,{})
    def test_mismatched_bins_rejected_on_each_approach_link(self):
        for link in ('173','174'):
            with self.subTest(link=link):
                r=raw(link);r['local_observation']['queue_bins'][link+'|4|68']=[1,1]
                with self.assertRaises(ValueError):urban.configure_queue_projection(self.cfg,r,{})
    def test_misaligned_capture_rejected(self):
        r=raw();r['vehicle_records']['capture_sim_sec_after']=1801
        with self.assertRaises(ValueError):urban.configure_queue_projection(self.cfg,r,{})
    def test_disabled_recipe_unchanged(self):
        self.assertEqual(urban.configure_queue_projection(self.cfg,raw(),None),{})
        self.assertFalse(hasattr(self.cfg.network,'kinematic_queue_zero_links'))
    def test_unrelated_origin_keeps_existing_fallback(self):
        r=raw('999');urban.configure_queue_projection(self.cfg,r,{})
        self.assertNotIn('999',self.cfg.network.kinematic_queue_zero_links)
        old=a._link_lengths_m;a._link_lengths_m=lambda:{'999':490.}
        try:self.assertNotIn('999',a._contiguous_stopline_queue(r,zero_links=self.cfg.network.kinematic_queue_zero_links))
        finally:a._link_lengths_m=old
if __name__=='__main__':unittest.main()
