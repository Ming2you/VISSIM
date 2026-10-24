"""Small synthetic checks; never opens native evidence or launches a process."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

spec=importlib.util.spec_from_file_location('four_arm_analysis',Path(__file__).with_name('analyze_four_arms.py'))
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def geometry():
    return {'addresses':{1:['FW_E',0.],2:['FW_W',0.]},
        'chains':{'FW_E':[{'link':1}],'FW_W':[{'link':2}]},
        'boundaries':[{'connector':10490,'kind':'ramp','id':'RM_C10490'},
                      {'connector':10,'kind':'offramp','id':'off10'}]}


class SyntheticAccounting(unittest.TestCase):
    def test_cutoff_stock_integrals_do_not_assume_empty_window_start(self):
        signals={t:{'9107:1':'OFF'} for t in range(1,2251)}
        sample=m.Measurements(geometry(),signals,None,None,[])
        for t in range(1,2251):
            sample.advance(t,{1:(1,1,1.,10.)} if t in (1350,1800,2250) else {})
        self.assertAlmostEqual(sample.ttt[1350,1800,'freeway_all']*3600,1.)
        self.assertAlmostEqual(sample.ttt[1800,2250,'freeway_all']*3600,1.)
        self.assertAlmostEqual(sample.ttt[1350,2250,'freeway_all']*3600,2.)
        self.assertEqual(sample.cutoff_counts[1350]['model_component'],1)
        self.assertEqual(sample.ttt[1350,2250,'component'],sample.ttt[1350,2250,'freeway_all'])

    def test_head_crossing_and_later_merge_are_distinct_events(self):
        signals={1:{'9107:1':'OFF'},2:{'9107:1':'GREEN'},3:{'9107:1':'GREEN'}}
        sample=m.Measurements(geometry(),signals,None,None,[])
        sample.advance(1,{7:(10490,1,270.,10.)})
        sample.advance(2,{7:(10490,1,274.,10.)})
        sample.advance(3,{7:(119,1,306.,10.)})
        self.assertEqual([r['upper_s'] for r in sample.head_events],[2])
        self.assertEqual([r['upper_s'] for r in sample.merge_events],[3])
        self.assertTrue(sample.merge_events[0]['already_downstream_of_head_at_lower'])
        self.assertEqual(sample.meter_states[1]['upstream_n'],0)
        self.assertEqual(sample.meter_states[1]['downstream_n'],1)

    def test_short_posthead_section_crossing_is_not_lost(self):
        sample=m.Measurements(geometry(),{1:{'9107:1':'OFF'},2:{'9107:1':'OFF'}},None,None,[])
        sample.advance(1,{7:(10490,1,270.,50.)})
        sample.advance(2,{7:(119,1,306.,50.)})
        self.assertEqual(len(sample.head_events),1)
        self.assertEqual(sample.head_events[0]['evidence'],'connector_to_verified_mainline_bracket')
        self.assertEqual(sample.head_events[0]['ldp_interval_end_state'],'OFF')
        self.assertEqual(len(sample.merge_events),1)

    def test_congestion_requires_five_eligible_contiguous_samples(self):
        rows=[{'time_s':30*t,'n_veh':10,'v_kmh':20.,'zone':'z'} for t in range(1,5)]
        self.assertEqual(m.congestion(rows,lambda r:r['zone']),[])
        rows.append({'time_s':150,'n_veh':10,'v_kmh':20.,'zone':'z'})
        self.assertEqual(m.congestion(rows,lambda r:r['zone'])[0]['span_s'],120)
        rows[2]['n_veh']=4
        self.assertEqual(m.congestion(rows,lambda r:r['zone']),[])


if __name__=='__main__':
    unittest.main(verbosity=2)
