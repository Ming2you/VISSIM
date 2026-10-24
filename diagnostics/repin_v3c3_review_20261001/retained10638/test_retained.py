import copy
import importlib.machinery
import importlib.util
import json
import math
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from evaluation.controllers import offramp_routing as routing
from evaluation.controllers.lane_urban_runtime import LaneUrbanRuntime

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

class RetainedRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc=json.loads((HERE.parent/'unrouted10646/route_contract.json').read_bytes())
        cls.mapping=json.loads((ROOT/cls.doc['mapping']['path']).read_bytes())
        cls.runtime=routing.compile_inventory(cls.doc,cls.mapping)

    def test_active_and_finished_routes_have_different_downstream_rights(self):
        r=self.runtime
        self.assertEqual(routing._route_distribution(r,r['routes']['1133:2'],'FW_W',6200.,retain_route=True),
                         {'route:1133:2|10638':1.})
        self.assertEqual(r['merges']['RM_C10646']['route_weights'],{'unrouted|10638':1.})
        self.assertEqual(routing._future_distribution(r,'FW_W',4000.,retain_route=True).get('route:1133:2|10638'),
                         routing._future_distribution(r,'FW_W',4000.).get('10638'))

    def test_route_tags_preserve_every_source_destination_marginal(self):
        loader=importlib.machinery.SourceFileLoader('routing_previous',str(HERE/'offramp_routing.py.before'))
        spec=importlib.util.spec_from_loader(loader.name,loader);old=importlib.util.module_from_spec(spec)
        loader.exec_module(old);old.ROOT=ROOT
        prior=old.compile_inventory(self.doc,self.mapping)
        for name in ('inputs','merges'):
            for key,row in self.runtime[name].items():
                self.assertEqual(row['weights'],prior[name][key]['weights'])
                marginal={}
                for tag,value in row['route_weights'].items():
                    off=tag.rsplit('|',1)[-1];marginal[off]=marginal.get(off,0.)+value
                self.assertEqual(marginal,row['weights'])

    def test_accepted_flow_receipt_preserves_class_and_mass(self):
        runtime=self.runtime;road='FW_W';n=len(runtime['bounds'][road])-1
        cell=runtime['branches']['10638']['source_cell']
        rows=[{} for _ in range(n)]
        rows[cell]={'observed_route:1133:2|route:1133:2|10638':3.,'expected_merge:RM_C10646|unrouted|10638':1.}
        state=NS(time_sec=100.,offramp_route_inventory_state={'cells':{road:rows},'origins':{road:{}}})
        cfg=NS(network=NS(offramp_route_inventory=runtime))
        routing.advance_inventory(state,cfg,road,mainline=[0.]*n,terminal=0.,offramps={'10638':7200.},
                                  entry=0.,generated=0.,merges={},duration_h=1/3600.)
        inv=state.offramp_route_inventory_state;receipt=inv['last_offramp_receipts'][road]
        self.assertEqual(receipt['end_sec'],101.)
        self.assertEqual(list(receipt['ports']['10638'].values()),[1.5,.5])
        self.assertAlmostEqual(math.fsum(inv['cells'][road][cell].values()),2.)
        self.assertAlmostEqual(math.fsum(receipt['ports']['10638'].values())+math.fsum(inv['cells'][road][cell].values()),4.)

    def make_local(self):
        movements={10634:'SC1004_W_to_E_SC1005',10635:'SC1004_W_to_N_SC1003',10642:'SC1004_W_to_S'}
        cfg=NS(network=NS(off_ramp_storage_link={'OR_F_E':'OR_F_E_storage'},
            urban_movements={m:{'origin':'in_SC1004_W'} for m in movements.values()}))
        port=NS(urban=NS(edges={126:[]},time=0.,continuation=True,speed=10.))
        local=LaneUrbanRuntime(port,cfg,movement_by_exit=movements)
        local.entry_paths={'off10638':10.};local.future_shares={'off10638':{m:1/3 for m in movements.values()}}
        state=NS(urban_arrival_buffer={},urban_storage_release_buffer={},
                 urban_movement_queue={m:0. for m in movements.values()},urban_link_storage={local.origin:96.})
        return local,state,cfg

    def test_unassigned_travel_does_not_free_storage_or_create_turn(self):
        local,state,cfg=self.make_local()
        due=local.schedule_upstream(state,cfg,0,4.,entry='off10638',shares={None:1.})
        self.assertEqual(sum(state.urban_storage_release_buffer.get(local.origin,{}).values()),0.)
        local.consume_upstream(state,cfg,due,4.)
        self.assertEqual(state.urban_link_storage[local.origin],96.)
        self.assertEqual(sum(state.urban_movement_queue.values()),0.)
        self.assertEqual(sum(q.stock for q in local.unrouted_pending.values()),4.)
        self.assertEqual([q.counts() for q in local.unrouted_pending.values()],
                         [{(None,'unrouted'):2.},{(None,'unrouted'):2.}])

    def test_finished_route_uses_existing_turn_distribution(self):
        local,state,cfg=self.make_local()
        local.schedule_upstream(state,cfg,0,3.,entry='off10638')
        self.assertEqual(sum(state.urban_storage_release_buffer[local.origin].values()),3.)
        self.assertEqual(set(local.arrival_tags[1]),{(m,False) for m in local.exits_by_movement})

    def test_unreviewed_unassigned_city_entry_fails(self):
        local,state,cfg=self.make_local();local.entry_paths['city']=10.
        with self.assertRaises(ValueError):local.schedule_upstream(state,cfg,0,1.,entry='city',shares={None:1.})

if __name__=='__main__':unittest.main()
