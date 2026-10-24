"""Entry speed must reach the ODE after transport/exchange without losing mass."""
from pathlib import Path
import copy
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import test_branch_partition as partition
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.lane_group_response_20260919 import test_lane_groups as base
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups


class RampEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base.LaneGroupTests.setUpClass()
        partition.BranchPartitionTests.setUpClass()

    def advance(self,p,state,cfg,ramp,speeds=None):
        rates={r:0. for r in cfg.network.ramps};rates[ramp]=360.
        n0=sum(map(sum,p.n));amount=rates[ramp]*p.dt
        ledger=base.ch.ModelAreaLedger({'freeway:FW_E':{'inside':n0},'origin:FW_E':{'outside':0.},
            **{'merge_pending:'+r:{'outside':q*p.dt} for r,q in rates.items()}},capture_response=True)
        ledger.begin_response_step('freeway',state.time_sec,state.time_sec+p.sec)
        ledger.expect_constraint_coverage('freeway_allocator');state._control_area_ledger=ledger
        cfg.network.metanet_delta_merge=0.
        with patch.object(base.ch.accounting._mn,'metanet_speed_update_kmh',lambda v,*args:v):
            p.advance(state,base.ch.ControlAction.uncontrolled(cfg),base.ch.DemandStep({'FW_E':0.},{},{}),cfg,
                offramp_capacity_veh_h={o:0. for o in p.off},ramp_release_veh_h=rates,
                **({'ramp_entry_speed_kmh':speeds} if speeds is not None else {}))
        self.assertAlmostEqual(sum(map(sum,p.n)),n0+amount)
        return amount

    def plain(self,lateral=False):
        spec=copy.deepcopy(base.LaneGroupTests.spec)
        for rows in spec['initial_groups']:
            for r in rows:r.update(n_veh=0.,v_kmh=60.)
        spec['initial_groups'][13][0]['n_veh']=10.
        for matrix in spec['exchange_rates_per_sec']:
            for row in matrix:
                for k in range(len(row)):row[k]=0.
        if lateral:spec['exchange_rates_per_sec'][13][0][1]=.02
        spec,state,cfg=base.LaneGroupTests().fixture(spec)
        cfg.network.off_ramp_split_ratio={o:0. for o in cfg.network.off_ramps}
        return PhysicalLaneGroups(spec,state,cfg,base.ch.accounting),state,cfg

    def test_entry_speed_survives_lateral_carrier_assignment(self):
        for lateral in (False,True):
            p,state,cfg=self.plain(lateral)
            speeds={r:30. for r in cfg.network.ramps}
            amount=self.advance(p,state,cfg,'RM_C10490',speeds)
            n=sum(p.n[13]);moment=sum(n*v for n,v in zip(p.n[13],p.v[13]))
            self.assertAlmostEqual(moment,(n-amount)*60.+amount*30.)
            self.assertLess(moment/n,60.)
            if lateral:self.assertGreater(p.n[13][1],0.)

    def test_equal_speed_does_not_create_a_loss(self):
        p,state,cfg=self.plain()
        self.advance(p,state,cfg,'RM_C10490',{r:60. for r in cfg.network.ramps})
        self.assertAlmostEqual(p.v[13][0],60.)

    def test_partition_uses_post_merge_moment_once(self):
        p,state,cfg=partition.BranchPartitionTests().setup_partition()
        amount=self.advance(p,state,cfg,'RM_C10639',{r:30. for r in cfg.network.ramps})
        self.assertAlmostEqual(p.partitions[8]['post_n'][0],amount)
        self.assertAlmostEqual(p.partitions[8]['post_v'][0],30.)
        self.assertEqual(p.partitions[8]['pre_n'][0],0.)

    def test_missing_or_nonfinite_speed_fails(self):
        for bad in (None,float('nan'),-1.,True):
            p,state,cfg=self.plain()
            values={} if bad is None else {r:(bad if r=='RM_C10490' else 30.) for r in cfg.network.ramps}
            with self.assertRaises(ValueError):self.advance(p,state,cfg,'RM_C10490',values)


if __name__=='__main__':unittest.main()
