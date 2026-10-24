import importlib.util
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from evaluation.controllers import physical_urban_transport as model

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
MANIFEST=json.loads((HERE/'candidate_manifest.json').read_bytes())
NETWORK=ROOT/MANIFEST['sources']['network']['path']
PROTOCOL=json.loads((HERE/'local_protocol.json').read_bytes())


class Program:
    def state_at(self,t,sg,*,controller_offset_sec):return 'GREEN' if sg==2 else 'RED'


def fixture(module=model,enabled=True):
    m=module.UrbanTransport(dict(time_s=3100.1,vehicles=[]),NETWORK,Program(),0,
        PROTOCOL['urban_free_speed_m_s'],6.,PROTOCOL['wave_m_s'],lateral_access=True,continuation=True)
    m.mandatory_lateral_completion=enabled
    m.cells[(71,3,0)]=module.FIFO([((10635,'turn'),1.)])
    k=(71,4,0)
    m.cells[k]=module.FIFO([((10635,'queue'),m.cap[k]-.1)])
    m.initial=m.counts();m.check()
    return m


class Completion(unittest.TestCase):
    def test_started_lateral_remainder_does_not_run_ahead_in_original_lane(self):
        m=fixture();m.step({})
        self.assertGreater(sum(n for s,t,ps in m.last_transfers if s==(71,3,0) and t==(71,4,0) for _,n in ps),0.)
        self.assertFalse(any(s==(71,3,0) and t==(71,3,1) for s,t,ps in m.last_transfers))
        self.assertGreater(m.cells[(71,3,0)].counts()[(10635,'turn')],0.)

    def test_rejected_lateral_request_does_not_commit(self):
        m=fixture();m.cells[(71,4,0)]=model.FIFO([((10635,'queue'),m.cap[(71,4,0)])]);m.initial=m.counts()
        m.step({})
        self.assertTrue(any(s==(71,3,0) and t==(71,3,1) for s,t,ps in m.last_transfers))
        self.assertNotIn(((71,3,0),(10635,'turn')),m.lateral_commitments)

    def test_intermediate_lane_does_not_start_forward_before_next_lateral(self):
        m=fixture();m.cells[(71,3,0)]=model.FIFO();m.cells[(71,4,0)]=model.FIFO()
        m.cells[(71,2,0)]=model.FIFO([((10635,'turn'),1.)]);m.initial=m.counts();m.step({})
        self.assertIn(((71,3,0),(10635,'turn')),m.lateral_commitments)
        self.assertEqual(m.route((71,3,0),(10635,'turn'),{}),(None,'lane_change_completion'))

    def test_existing_whole_blocking_vehicle_still_blocks_green_lane(self):
        m=fixture();m.cells={k:model.FIFO() for k in m.cells};last=len(m.edges[71])-2
        m.cells[(71,3,last)]=model.FIFO([((10635,'blocked'),1.),((10634,'through'),1.)])
        m.cells[(71,4,last)]=model.FIFO([((10635,'red_queue'),m.cap[(71,4,last)])]);m.initial=m.counts()
        m.step({});self.assertEqual(sum(m.departed.values()),0.)
        self.assertEqual(m.counts()[(10635,'blocked')],1.)

    def test_mass_and_completed_commitments(self):
        m=fixture();m.program=SimpleNamespace(state_at=lambda *a,**kw:'GREEN')
        for _ in range(120):m.step({});m.check()
        self.assertLess(abs(sum(m.initial.values())-sum(m.counts().values())-sum(m.departed.values())),1e-8)
        self.assertTrue(all(m.cells[k].counts().get(label,0)>model.EPS for k,label in m.lateral_commitments))
        self.assertGreater(m.departed[(10635,'turn')],.999)

    def test_disabled_mode_is_exact_for120_steps(self):
        loader=SourceFileLoader('before_urban_transport',str(HERE/'physical_urban_transport.py.before'))
        spec=importlib.util.spec_from_loader(loader.name,loader);old=importlib.util.module_from_spec(spec);loader.exec_module(old)
        a=fixture(model,False);b=fixture(old,False)
        for _ in range(120):
            self.assertEqual(a.step({}),b.step({}))
            self.assertEqual(a.counts(),b.counts());self.assertEqual(a.departed,b.departed)
            self.assertEqual(a.last_transfers,b.last_transfers)

    def test_unverified_compiled_path_fails_before_state_changes(self):
        m=fixture();before=m.counts()
        with patch.object(model.prediction_cache,'active',return_value=SimpleNamespace(urban_pipeline_enabled=True)):
            with self.assertRaisesRegex(NotImplementedError,'completion'):m.step({})
        self.assertEqual(m.counts(),before)

    def test_compaction_does_not_move_uncommitted_mass_across_committed_head(self):
        m=fixture();key=(71,3,0);a=(10635,'committed');b=(10635,'free')
        m.cells[key]=model.FIFO([(b,.5),(a,.1),(b,.5)])
        m.cells[(71,4,0)]=model.FIFO([((10635,'queue'),m.cap[(71,4,0)])])
        m.initial=m.counts();m.lateral_commitments.add((key,a))
        m.prefer_more_receiving_space=True;m.compact_equal_behavior=True
        m.step({})
        self.assertEqual([label for label,n in m.cells[key].q],[b,a,b])


if __name__=='__main__':
    import sys
    name=sys.argv[1];target=HERE/(name+'.json');assert not target.exists()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Completion))
    target.write_text(json.dumps(dict(tests=result.testsRun,passed=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors)),indent=2)+'\n')
    raise SystemExit(not result.wasSuccessful())
