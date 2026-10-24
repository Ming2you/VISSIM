import copy
import pickle
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace as N

import candidate as c


class SideEntryTest(unittest.TestCase):
    def test_real_geometry_and_current_clock(self):
        cfg,state,_=pickle.loads((Path(__file__).parent.parent/'citysplit287/forecast2400/initial.pickle').read_bytes())
        geom=c.geometry(c.ROOT,cfg)
        self.assertEqual(set(geom['sources']),{'1099','1100'})
        for decision in geom['sources']:
            self.assertEqual(c.delay_steps(state,cfg,geom,decision),7)
        self.assertEqual(cfg.simulation.T_u_sec,10)

    def test_actual_hook_is_scoped_and_restores_on_failure(self):
        from evaluation.controllers.aggregate_route_corridors import Routes
        from src.models import urban_queue_model as uqm
        geom=dict(lane_factor=3.,sources={'1099':dict(distance_m=600.,connector='x',source='near')})
        cfg=N(network=N(urban_avg_speed_km_h=40.),simulation=N(T_u_sec=10))
        state=N(urban_link_speed_kph={c.TARGET:120.},urban_link_storage={c.TARGET:650.},
            urban_arrival_buffer={c.TARGET:{251:4.}},urban_storage_release_buffer={c.TARGET:{251:4.}})
        spec=dict(decision='1099',prefix_storage='near',branches={'1':dict(destination=c.TARGET,connector='x')})
        initial=copy.deepcopy(vars(state))
        def original_delay(state,cfg,target):return 12
        def original_advance(self,state,control,cfg,step,spec):
            self.answers=(uqm._link_delay_steps(state,cfg,c.TARGET),uqm._link_delay_steps(state,cfg,'other'))
            raise LookupError('simulated exception after scheduling calculation')
        obj=N()
        with patch.object(Routes,'advance_one',original_advance),patch.object(uqm,'_link_delay_steps',original_delay),patch.object(c,'geometry',return_value=geom):
            with self.assertRaises(LookupError):
                with c.travel_hook(c.MODE) as report:
                    self.assertEqual(uqm._link_delay_steps(state,cfg,c.TARGET),12)
                    Routes.advance_one(obj,state,None,cfg,240,spec)
            self.assertEqual(obj.answers,(6,12))
            self.assertIs(Routes.advance_one,original_advance)
            self.assertIs(uqm._link_delay_steps,original_delay)
            self.assertEqual(report['receipts'][0]['old_delay_sec'],120)
        self.assertEqual(vars(state),initial)

    def test_disabled_and_invalid_options(self):
        from evaluation.controllers.aggregate_route_corridors import Routes
        before=Routes.advance_one
        with c.travel_hook(None) as report:self.assertEqual(report['receipts'],[])
        self.assertIs(Routes.advance_one,before)
        with self.assertRaises(ValueError):
            with c.travel_hook('unreviewed'):pass
        self.assertIs(Routes.advance_one,before)


if __name__=='__main__':unittest.main()
