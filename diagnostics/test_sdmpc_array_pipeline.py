"""Whole local transport comparisons to the preserved object implementation."""
import copy
from collections import Counter
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
import numpy as np
from diagnostics.test_sdmpc_persistent_fifo import load, flatten
from evaluation.controllers import sdmpc_tangent_reverse as ad
from evaluation.controllers.sdmpc_prediction_cache import scope, reverse_arrays

ROOT=Path(__file__).resolve().parents[1]
OLD=load(ROOT/'diagnostics/sdmpc_array_pipeline_20260922/before_sources/physical_urban_transport.py')
NEW=load(ROOT/'evaluation/controllers/physical_urban_transport.py')


class ArrayPipelineTests(unittest.TestCase):
    def setUp(self):
        self.flags=ad.DIRECT_SUM_NODES,ad.FAST_PRIMITIVES
        ad.DIRECT_SUM_NODES=True;ad.FAST_PRIMITIVES=True

    def tearDown(self):ad.DIRECT_SUM_NODES,ad.FAST_PRIMITIVES=self.flags

    def case(self,enabled,dual,mode):
        ns=NEW if enabled else OLD;trace=ad.Trace([1.]*4)
        def value(n,axis):return ad.Dual(n,{axis:1.},trace) if dual else n
        cfg=NS(network=NS(sdmpc_options=dict(prediction_cache=True,array_urban_pipeline=enabled)))
        with reverse_arrays(),scope(cfg):
            p=object.__new__(ns['UrbanTransport'])
            fraction=value(.7,1)
            p.program=NS(state_at=lambda *a,**kw:'GREEN' if mode!=4 else 'RED',
                         service_fraction_at=lambda *a,**kw:fraction)
            p.offset=0.;p.time=0;p.speed=10.;p.wave=3.;p.spacing=6.
            p.capacity_rate=10.*3./(6.*13.)
            p.lateral_access=mode!=3;p.continuation=True;p.compact_equal_behavior=True
            p.exits={10634:dict(lanes=[1,2,3],position_m=96.),10635:dict(lanes=[4,5],position_m=95.),10642:dict(lanes=[1],position_m=48.)}
            p.edges={71:[0.,24.,48.,72.,96.]}
            p.unrouted_labels={(None,'unrouted')};p.fallback_exits={10634,10635,10642}
            p.exchange_rates={(71,1,2,10634):.08,(71,3,2,None):.03}
            p.cells={(71,lane,cell):ns['FIFO']() for lane in range(1,6) for cell in range(4)}
            p.cap={key:4. for key in p.cells};p.dx={key:24. for key in p.cells}
            for key,rows in {
                (71,1,0):[((10634,1),1.),((10634,2),.2),((10634,1),.3)],
                (71,3,0):[((10635,3),.8),((None,4),.4)],
                (71,2,1):[((10642,5),.9)],(71,2,2):[((10642,6),.4)],
                (71,1,3):[((10634,7),.8),((None,8),.6)],
                (71,4,3):[((10635,9),.7)],(71,1,1):[((None,'unrouted'),.3)]}.items():
                for label,n in rows:p.cells[key].append(label,value(n,0))
            if mode==5:p.defer_mandatory_while_forward_open=True
            if mode==6:p.prefer_more_receiving_space=True
            if mode==7:p.lateral_start_footprints={None:6.}
            if mode==9:
                p.cells[71,1,3].append((10634.,None),value(.13,0))
                p.cells[71,2,3].append((10634,None),value(.17,0))
                p.cells[71,3,3].append((10634.,None),value(.11,0))
                p.cells[71,3,3].append((10634,None),value(.12,0))
            p.initial=p.counts();p.admitted=Counter();p.departed=Counter()
            p.movements=Counter();p.blocked_seconds=Counter();p.vehicle_seconds=0.;p.checks=0
            pending=ns['FIFO']([((10635,11),value(.6,3)),((None,12),.3)])
            output=[];structure=[]
            saved=None
            for step in range(8):
                room=None if mode==1 else {10634:value(.12,2) if mode!=2 else 0.,10635:.16,10642:.06}
                name='background2' if mode==11 and step>=4 else 'background'
                external={} if mode==11 and step==5 else {name:((71,5,0),pending)}
                if mode==10 and step==4:
                    extra=value(.12,3);label=(10634.,90)
                    p.cells[71,1,0].append(label,extra);p.admitted[label]+=extra
                    pending.append((10635,91),value(.2,2))
                accepted=p.step(external,exit_receiving=room,indexed_lateral=mode!=8)
                if mode>=10:
                    if step==3:saved=copy.deepcopy(p)
                    if step<7:continue
                # Sort only dictionary presentation, never the physical FIFO.
                payload=[list(q.q) for q in p.cells.values()]+[list(pending.q),p.vehicle_seconds]
                for obj in (p.admitted,p.departed,p.movements,p.blocked_seconds,p.last_sending_limits,p.last_receiving_limits):
                    payload.append([obj[k] for k in sorted(obj,key=str)])
                    structure.append(tuple(sorted(obj,key=str)))
                structure.append(tuple((str(s),str(t),tuple(repr(label) for label,n in rows)) for s,t,rows in p.last_transfers))
                structure.append(tuple(tuple(repr(label) for label,n in q.q) for q in p.cells.values()))
                payload.append(accepted)
                if saved is not None:
                    payload.extend([saved.vehicle_seconds,*[list(q.q) for q in saved.cells.values()]])
                output.extend(flatten(payload))
            snapshot=copy.deepcopy(p)
            self.assertEqual(snapshot.time,8)
            self.assertIs(type(snapshot),ns['UrbanTransport'])
        self.assertIs(type(p),ns['UrbanTransport'])
        return trace,output,structure

    def test_values_routes_controls_and_jacobians(self):
        for dual in (False,True):
            for mode in range(12):
                with self.subTest(dual=dual,mode=mode):
                    ta,a,sa=self.case(False,dual,mode);tb,b,sb=self.case(True,dual,mode)
                    self.assertEqual(sa,sb)
                    np.testing.assert_array_equal([ad.primal(x) for x in a],[ad.primal(x) for x in b])
                    if dual:
                        np.testing.assert_allclose(ta.jacobian(a,workers=1),tb.jacobian(b,workers=1),rtol=0.,atol=1e-12)

    def test_invalid_receiving_fails(self):
        from diagnostics.test_lane_plant_coupling import UrbanReceivingTests
        for enabled in (False,True):
            with reverse_arrays(),scope(NS(network=NS(sdmpc_options=dict(prediction_cache=True,array_urban_pipeline=enabled)))):
                p=UrbanReceivingTests.urban()
                with self.assertRaises(ValueError):p.step({},exit_receiving={10634:1.})
                with self.assertRaises(ValueError):p.step({},exit_receiving={10634:-1.,10635:0.,10642:0.})


if __name__=='__main__':unittest.main()
