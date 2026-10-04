"""Current-state lane/route initialization, not a physical forecast."""
import ast
import copy
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest
from evaluation.controllers import offramp_routing as routing
from evaluation.controllers.lane_plant_runtime import bind_current_routes
from evaluation.controllers.projection_support import complete_records

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PINS={}
def read(p):
    raw=p.read_bytes();PINS[str(p)]=hashlib.sha256(raw).hexdigest();return json.loads(raw)

class Partition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        before=HERE/'offramp_routing.py.before'
        cls.old={'__name__':'saved_offramp_routing','__file__':str(ROOT/'evaluation/controllers/offramp_routing.py')}
        exec(compile(before.read_text(encoding='utf8'),str(before),'exec'),cls.old)
        cls.runtime=read(HERE.parent/'entry10643/native_cohorts.json')['route_runtime']
        cls.fixtures=[]
        for seed,t,folder in [(43,2250,'D:/VISSIM_runs/20260929_seed43_observation2700/nc/decisions_sdmpc31_nc2700_s43'),
                              (43,2700,'D:/VISSIM_runs/20260929_seed43_observation2700/nc/decisions_sdmpc31_nc2700_s43'),
                              (47,2700,'D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47'),
                              (47,3150,'D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47')]:
            raw=read(Path(folder)/f'state_{t:06d}.json')
            frame=read(Path(raw['lane_plant_observation']['directory'])/f'frame_{t:06d}.json')
            raw=bind_current_routes(raw,{'frames':[frame]})
            dims={road:[3 if road=='FW_E' and 9<=i<=12 else 1 for i in range(len(bounds)-1)]
                  for road,bounds in cls.runtime['bounds'].items()}
            ids={};counts={road:[0. for _ in rows] for road,rows in dims.items()};native={}
            for v in complete_records(raw):
                if str(v['link_no']) not in cls.runtime['physical']:continue
                road,pos,cell=routing._position(cls.runtime,v['link_no'],v['position_m'])
                g=min(v['lane_no']-1,2) if dims[road][cell]==3 else 0
                ids[v['veh_no']]=g;counts[road][cell]+=1
                native.setdefault((road,cell,g),[]).append(v)
            partition=dict(groups_per_cell=dims,vehicle_group=ids)
            state=SimpleNamespace(time_sec=t,mainline_origin_queue={r:0. for r in dims})
            cfg=SimpleNamespace(network=SimpleNamespace(offramp_route_inventory=cls.runtime,freeway_links=list(dims)))
            cls.fixtures.append(dict(seed=seed,time=t,raw=raw,state=state,cfg=cfg,partition=partition,counts=counts,native=native))
        cls.receipts=[]

    def initialize(self,f,partition=None,old=False):
        state=copy.deepcopy(f['state'])
        function=self.old['initialize_inventory'] if old else routing.initialize_inventory
        kwargs={} if old else {'lane_partition':partition}
        with patch('evaluation.controllers.area_freeway_accounting.continuity_vehicle_counts',return_value=f['counts']):
            metadata=function(state,f['cfg'],f['raw'],**kwargs)
        return state,metadata

    def test_default_initializer_exact_before_on_four_observed_states(self):
        for f in self.fixtures:
            old,om=self.initialize(f,old=True);new,nm=self.initialize(f)
            self.assertEqual(om,nm);self.assertEqual(old.offramp_route_inventory_state,new.offramp_route_inventory_state)

    def test_lane_initialization_preserves_each_class_and_native_lane_mass(self):
        for f in self.fixtures:
            base,metadata=self.initialize(f)
            state,lane_metadata=self.initialize(f,f['partition'])
            inv=copy.deepcopy(state.offramp_route_inventory_state)
            groups=inv.pop('lane_cells')
            self.assertEqual(inv,base.offramp_route_inventory_state)
            self.assertEqual(metadata,lane_metadata)
            rows=[]
            for road,cells in groups.items():
                for i,gs in enumerate(cells):
                    for g,classes in enumerate(gs):
                        native=f['native'].get((road,i,g),[])
                        self.assertAlmostEqual(math.fsum(classes.values()),len(native))
                        if road=='FW_E' and 9<=i<=12:
                            rows.append(dict(cell=i,group=g,vehicles=len(native),
                                speed_kmh=math.fsum(v['speed_kph'] for v in native)/len(native) if native else None,
                                target10682=sum(n for k,n in classes.items() if k.endswith('|10682')),classes=classes))
            self.receipts.append(dict(seed=f['seed'],time_sec=f['time'],rows=rows,
                total=sum(map(sum,f['counts'].values())),groups=sum(sum(map(len,cells)) for cells in groups.values())))

    def test_incomplete_or_out_of_range_partition_rejected(self):
        f=self.fixtures[0];p=f['partition'];vid=next(iter(p['vehicle_group']))
        bad=[]
        b=copy.deepcopy(p);b['vehicle_group'].pop(vid);bad.append(b)
        b=copy.deepcopy(p);b['vehicle_group'][vid]=True;bad.append(b)
        b=copy.deepcopy(p);b['vehicle_group'][vid]=-1;bad.append(b)
        b=copy.deepcopy(p);b['vehicle_group'][vid]=99;bad.append(b)
        b=copy.deepcopy(p);b['groups_per_cell']['FW_E'].pop();bad.append(b)
        b=copy.deepcopy(p);b['groups_per_cell']['FW_E'][0]=0;bad.append(b)
        for b in bad:
            with self.assertRaises(ValueError):self.initialize(f,b)

    def test_class_change_without_mass_change_is_detected(self):
        f=self.fixtures[0];state,_=self.initialize(f,f['partition'])
        group=next(g for rows in state.offramp_route_inventory_state['lane_cells'].values() for cell in rows for g in cell if g)
        key=next(iter(group));n=group.pop(key);group['invented_terminal|terminal']=n
        with self.assertRaisesRegex(ValueError,'classes differ'):routing.assert_inventory(state,f['cfg'],f['counts'])

    def test_future_or_stale_current_snapshot_rejected(self):
        for shift in (-5,5):
            f=copy.deepcopy(self.fixtures[0]);f['state'].time_sec+=shift
            with self.assertRaisesRegex(ValueError,'current state snapshot'):self.initialize(f,f['partition'])

    def test_negative_lane_mass_rejected(self):
        f=self.fixtures[0];state,_=self.initialize(f,f['partition'])
        group=next(g for rows in state.offramp_route_inventory_state['lane_cells'].values() for cell in rows for g in cell if g)
        group[next(iter(group))]=-1.
        with self.assertRaisesRegex(ValueError,'Invalid lane'):routing.assert_inventory(state,f['cfg'],f['counts'])

    def test_unintegrated_transport_fails_without_mutating_stock(self):
        f=self.fixtures[0];state,_=self.initialize(f,f['partition']);saved=copy.deepcopy(state.offramp_route_inventory_state)
        with self.assertRaisesRegex(ValueError,'not yet integrated'):
            routing.advance_inventory(state,f['cfg'],'FW_E',mainline=[],terminal=0,offramps={},entry=0,generated=0,merges={},duration_h=1/3600)
        self.assertEqual(saved,state.offramp_route_inventory_state)

    def test_default_accepted_flow_transport_120steps_exact(self):
        f=self.fixtures[0];old,_=self.initialize(f,old=True);new,_=self.initialize(f)
        for step in range(120):
            for road,rows in new.offramp_route_inventory_state['cells'].items():
                flows=[math.fsum(row.values())*36. for row in rows]
                main,off=routing.sending_requests(new,f['cfg'],road,flows,1/3600)
                args=dict(mainline=main[:-1],terminal=main[-1],offramps=off,entry=720.,generated=720.,merges={},duration_h=1/3600)
                self.old['advance_inventory'](old,f['cfg'],road,**args)
                routing.advance_inventory(new,f['cfg'],road,**args)
                self.assertEqual(old.offramp_route_inventory_state,new.offramp_route_inventory_state)
            old.time_sec+=1;new.time_sec+=1

if __name__=='__main__':
    import sys
    if sys.argv[1:] not in ([],['--temporal-guard-check']):raise SystemExit('Unknown verification mode')
    target=HERE/('initialization_temporal_guard.json' if sys.argv[1:] else 'initialization.json');assert not target.exists()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Partition))
    if result.wasSuccessful():
        before=ast.parse((HERE/'offramp_routing.py.before').read_text(encoding='utf8'))
        after=ast.parse((ROOT/'evaluation/controllers/offramp_routing.py').read_text(encoding='utf8'))
        old={n.name:ast.dump(n) for n in before.body if isinstance(n,ast.FunctionDef)}
        new={n.name:ast.dump(n) for n in after.body if isinstance(n,ast.FunctionDef)}
        changed=[k for k,v in old.items() if new[k]!=v]
        assert changed==['initialize_inventory','assert_inventory','advance_inventory'],changed
        target.write_text(json.dumps(dict(status='initialization_only_verified',cases=Partition.receipts,tests=result.testsRun,
            changed_functions=changed,existing_other_functions_exact=len(old)-len(changed),source_pins=PINS,
            no_physical_forecasts=True,lane_transport_integrated=False,not_controller_ready=True),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    raise SystemExit(not result.wasSuccessful())
