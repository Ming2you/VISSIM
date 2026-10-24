from copy import deepcopy
import json,pickle,unittest
from unittest.mock import patch
from . import candidate as c
from evaluation.controllers import head_service_resources as h,vissim_stackelberg_adapter as adapter
from ..transfer331.inputs import load

class PhysicalAttribution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg,_,_=pickle.loads((c.A/'transfer331/build2400_v2/initial.pickle').read_bytes())
        cls.folder=json.loads((c.A/'transfer331/build2400_v2/summary.json').read_bytes())['source']
        cls.pre_cfg,_,cls.raw,cls.plan=pickle.loads((c.HERE/'configure_fixture/fixture.pickle').read_bytes())
        cls.document=json.loads((c.HERE/'head_resources.json').read_bytes())
        cls.tuning=json.loads((c.A/'flow279/config_10686_free.json').read_bytes())
        cls.tuning['urban']['capacity']['head_resource_contract']=(c.HERE/'head_resources.json').relative_to(c.ROOT).as_posix()

    def configure(self,doc=None):
        cfg=deepcopy(self.pre_cfg)
        if doc is None:h.configure(cfg,self.tuning,self.raw,self.plan)
        else:
            old=h.json.loads
            def read(blob,*a,**kw):
                result=old(blob,*a,**kw)
                return doc if isinstance(result,dict) and result.get('schema')=='physical-head-resource-join/v13' else result
            with patch.object(h.json,'loads',read):h.configure(cfg,self.tuning,self.raw,self.plan)
        return cfg

    def test_real_prehead_continuation_and_receiver_verified(self):
        cfg=self.configure()
        self.assertIn('10200',cfg.network.head_service_resources['resources'])
        self.assertEqual(cfg.network.movement_capacity_by_movement_veh_h,self.pre_cfg.network.movement_capacity_by_movement_veh_h)

    def test_wrong_route_continuation_rejected(self):
        doc=deepcopy(self.document)
        doc['resources']['10200']['disjoint_consumers'][c.RIGHT]['native_route_path'][-1]='68'
        with self.assertRaisesRegex(ValueError,'Excluded consumer'):self.configure(doc)

    def test_shared_lane_without_upstream_proof_rejected(self):
        doc=deepcopy(self.document)
        doc['resources']['10200']['disjoint_consumers'][c.RIGHT]['upstream_of_head']=False
        with self.assertRaisesRegex(ValueError,'Excluded consumer'):self.configure(doc)

    def test_physical_observer_does_not_beta_split(self):
        cfg=self.configure();seen={}
        def legacy(_cfg,_groups,est,target):
            if ('1220021201','p3') in est:
                rate=est[('1220021201','p3')]
                target.update({c.THROUGH:rate*.67,c.RIGHT:rate*.33})
                return 2
            return 0
        def original(cfg,raw,previous,caps,plan,distribute,options):
            distribute(cfg,[],{('1220021201','p3'):3000.},seen)
            return {'head_provenance_test':1.}
        h.observe(original,cfg,self.raw,None,deepcopy(cfg.network.movement_capacity_by_movement_veh_h),self.plan,legacy,{})
        self.assertEqual(seen,{c.THROUGH:3000.})

    def test_causal_support_changes_one_rate_only(self):
        cfg=deepcopy(self.cfg);before=deepcopy(cfg.network.movement_capacity_by_movement_veh_h)
        report=c.install(cfg,self.raw,self.plan,self.folder,2400)
        self.assertAlmostEqual(report['new_through'],2936.842105263158)
        self.assertEqual([k for k in before if before[k]!=cfg.network.movement_capacity_by_movement_veh_h[k]],[c.THROUGH])
        self.assertLessEqual(max(p['end'] for p in report['physical_pair_support']),2400)

    def test_future_or_foreign_support_rejected(self):
        from pathlib import Path
        d=json.loads((Path(self.folder)/'action_001650.json').read_bytes())
        with self.assertRaisesRegex(ValueError,'future or foreign'):c.support([d],1500,d['run_provenance']['run_id'])
        with self.assertRaisesRegex(ValueError,'future or foreign'):c.support([d],1800,'other-run')

if __name__=='__main__':unittest.main()
