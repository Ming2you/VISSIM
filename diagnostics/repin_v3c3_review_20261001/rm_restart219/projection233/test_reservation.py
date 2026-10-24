import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest

from evaluation.controllers.lane_plant_runtime import (
    prepare_offramp_projection, restore_offramp_projection_capacity)


class MigrationReservation(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        groups=Path(self.temp.name)/'groups.json'
        groups.write_text(json.dumps({'groups':{'east':{'direct_connector':'10483'}}}))
        self.context={'document':{'off_groups':str(groups)},
                      'component':NS(offramps={'10483':{'storage_capacity_veh':70.}})}
        self.cfg=NS(network=NS(urban_link_storage_veh={'SC1001_W_out':220.}))
        self.obs={'information_cutoff_s':4500,
                  'frames':[{'time_s':4500,'vehicles':[[i,10483] for i in range(46)]}]}
        self.det={'link_to_origins':{'10483':['SC1001_W_out']},'link_to_movements':{}}

    def test_measured_port_stock_migrates_without_increasing_prediction_capacity(self):
        # Failure fixture: 179 urban +46 connector vehicles were clipped to220.
        prepare_offramp_projection(self.context,self.obs,self.cfg,self.det)
        capacity=self.cfg.network.urban_link_storage_veh['SC1001_W_out']
        self.assertEqual(capacity,266.)
        self.assertLessEqual(179+46,capacity)
        state=NS(urban_link_storage={'SC1001_W_out':capacity-179})
        restore_offramp_projection_capacity(self.context,self.cfg,state)
        self.assertEqual(self.cfg.network.urban_link_storage_veh['SC1001_W_out'],220.)
        self.assertEqual(state.urban_link_storage['SC1001_W_out'],41.)
        self.assertTrue(self.context['offramp_projection_reservations']['SC1001_W_out']['restored'])

    def test_actual_urban_overcapacity_still_fails(self):
        prepare_offramp_projection(self.context,self.obs,self.cfg,self.det)
        state=NS(urban_link_storage={'SC1001_W_out':266.-221.})
        with self.assertRaisesRegex(ValueError,'Remaining urban stock exceeds'):
            restore_offramp_projection_capacity(self.context,self.cfg,state)

    def test_actual_port_overcapacity_still_fails_without_widening(self):
        self.context['component'].offramps['10483']['storage_capacity_veh']=45.
        with self.assertRaisesRegex(ValueError,'physical capacity'):
            prepare_offramp_projection(self.context,self.obs,self.cfg,self.det)
        self.assertEqual(self.cfg.network.urban_link_storage_veh['SC1001_W_out'],220.)

    def test_explicit_observed_floor_preserves_excess_with_zero_free_space(self):
        self.context['projection_capacity_policy']='observed_lower_bound'
        prepare_offramp_projection(self.context,self.obs,self.cfg,self.det)
        state=NS(urban_link_storage={'SC1001_W_out':266.-221.})
        restore_offramp_projection_capacity(self.context,self.cfg,state)
        self.assertEqual(self.cfg.network.urban_link_storage_veh['SC1001_W_out'],221.)
        self.assertEqual(state.urban_link_storage['SC1001_W_out'],0.)
        self.assertEqual(self.context['offramp_projection_reservations']['SC1001_W_out']['observed_floor_added_veh'],1.)

    def test_ambiguous_stock_owner_still_fails(self):
        self.det['link_to_movements']['10483']=['movement']
        with self.assertRaisesRegex(ValueError,'ambiguous owner'):
            prepare_offramp_projection(self.context,self.obs,self.cfg,self.det)

    def test_dedicated_branch_is_unchanged(self):
        self.det['physical_storage_projection']={'link_to_storage':{'10483':'direct_port'}}
        result=prepare_offramp_projection(self.context,self.obs,self.cfg,self.det)
        self.assertEqual(result['offramp_projection_temporary_reservations'],{})
        self.assertEqual(self.cfg.network.urban_link_storage_veh['SC1001_W_out'],220.)

    def test_empty_link_is_unchanged(self):
        self.obs['frames'][0]['vehicles']=[]
        result=prepare_offramp_projection(self.context,self.obs,self.cfg,self.det)
        self.assertEqual(result['offramp_projection_temporary_reservations'],{})


if __name__=='__main__':unittest.main()
