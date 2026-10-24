import copy
import pickle
import unittest
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_composite308.inputs import inputs
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_initial320 import candidate as c


class InitialTiming(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = inputs()

    def apply(self, state=None, raw=None, frame=None):
        cfg,s,r,f,b,inside,q=self.data
        s=copy.deepcopy(s) if state is None else state
        return s,c.install(cfg,s,r if raw is None else raw,f if frame is None else frame,b,q)

    def test_current_cohort_mass_owners_and_only_two_fields_change(self):
        original=copy.deepcopy(self.data[1])
        before={k:pickle.dumps(v,protocol=5) for k,v in vars(original).items()}
        state,report=self.apply(state=original)
        self.assertEqual(report['ready_queue_veh'],10)
        self.assertEqual(report['residual_veh'],43)
        self.assertEqual(sum(state.urban_arrival_buffer[c.TARGET].values()),43)
        self.assertEqual(state.urban_arrival_buffer[c.TARGET],state.urban_storage_release_buffer[c.TARGET])
        for k,v in before.items():
            if k not in report['changed_fields']:
                self.assertEqual(v,pickle.dumps(vars(state)[k],protocol=5),k)
        self.assertGreater(len(report['new_calendar']),2)
        self.assertEqual(sum(x['post_head_retained'] for x in report['vehicles']),1)

    def test_near_vehicle_before_far_vehicle_and_no_early_rounding(self):
        self.assertEqual(c.arrival_step(1,36,20,2400,10),241)
        self.assertEqual(c.arrival_step(101,36,20,2400,10),242)
        self.assertEqual(c.arrival_step(1,0,0,2400,10),241)
        with self.assertRaises(ValueError):c.arrival_step(-1,36,20,2400,10)

    def test_stale_or_incomplete_records_rejected(self):
        raw=copy.deepcopy(self.data[2]);raw['vehicle_records']['complete']=False
        with self.assertRaises(ValueError):self.apply(raw=raw)
        frame=copy.deepcopy(self.data[3]);frame['time_s']+=10
        with self.assertRaises(ValueError):self.apply(frame=frame)

    def test_mismatched_calendar_rejected_before_mutation(self):
        state=copy.deepcopy(self.data[1]);state.urban_storage_release_buffer[c.TARGET][242]-=1
        before=pickle.dumps(state,protocol=5)
        with self.assertRaises(ValueError):self.apply(state=state)
        self.assertEqual(before,pickle.dumps(state,protocol=5))

    def test_known_next_connector_is_not_redrawn_from_lane(self):
        import xml.etree.ElementTree as ET
        links={x.get('no'):x for x in ET.fromstring(self.data[4]).findall('./links/link')}
        v=dict(link_no=174,lane_no=1,position_m=300.)
        distance,path=c.remaining_distance(v,'10281',links,25.745)
        self.assertEqual(path,['174','10281','173'])
        self.assertGreater(distance,200)
        with self.assertRaises(ValueError):c.remaining_distance(v,'9999',links,25.745)

    def test_existing_initial_tags_not_erased(self):
        s=copy.deepcopy(self.data[1]);s.gate_initial_route_tags={c.TARGET:{242:{'unknown':1}}}
        with self.assertRaises(ValueError):self.apply(state=s)


if __name__=='__main__':unittest.main()
