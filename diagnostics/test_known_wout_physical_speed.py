"""Known-route metre geometry must not consume lane-scaled delay speed."""
import copy
from types import SimpleNamespace as NS
import unittest

from diagnostics.probe_model_area_integration import ROOT
from evaluation.controllers import route_choice_corridor as rc


class PhysicalSpeedTests(unittest.TestCase):
    def case(self, physical=True):
        storage='SC1004_W_out'
        travel=dict(prefix={'10629':[dict(link='10629',start=0.,stop=100.)]},
                    destinations={'free':[dict(link='68',start=0.,stop=100.)]},
                    direct_entry=dict(link='68',position_m=0.))
        if physical:travel['speed_source']='physical_observation'
        spec=dict(storage=storage,incoming_movements={'turn':'10629'},physical_travel=travel,
                  future_choice_weights={'free':1.},choice_position_m=0.)
        cfg=NS(simulation=NS(T_u_sec=1.),network=NS(urban_avg_speed_km_h=50.,
            urban_link_storage_veh={storage:100.},known_legsplit_routes=spec,
            urban_movements={'turn':dict(receiving_link=storage,origin='approach')},
            boundary_out_ramp_split={storage:dict(free=1.,ramps={})}))
        state=NS(urban_link_storage={storage:99.},
            urban_link_speed_kph={'approach':144.,storage:144.},
            local_observation_summary={'urban_link_speed_kph':{'approach':36.,storage:36.}},
            urban_storage_release_buffer={},
            known_legsplit_route_state=dict(cohorts=[],plan=None,received=0.,departed=0.))
        return state,cfg

    def test_metres_use_physical_speed_on_both_legs_without_new_mass(self):
        state,cfg=self.case()
        self.assertTrue(rc.known_legsplit_receive(state,cfg,1.,999,movement='turn',entry_step=900))
        row=state.known_legsplit_route_state['cohorts'][0]
        self.assertEqual((row['due'],row['speed_kph']),(910,36.))
        requests=rc.known_legsplit_requests(state,cfg,'SC1004_W_out',1.,1.,910)
        self.assertEqual(requests,{})
        row=state.known_legsplit_route_state['cohorts'][0]
        self.assertEqual((row['target'],row['due'],row['vehicles']),('free',920,1.))
        self.assertEqual(state.urban_link_storage['SC1004_W_out'],99.)
        self.assertEqual(state.urban_storage_release_buffer['SC1004_W_out'][920],1.)

    def test_legacy_source_unchanged_when_not_enabled(self):
        state,cfg=self.case(False)
        rc.known_legsplit_receive(state,cfg,1.,999,movement='turn',entry_step=900)
        row=state.known_legsplit_route_state['cohorts'][0]
        self.assertEqual((row['due'],row['speed_kph']),(903,144.))

    def test_direct_offramp_preserves_free_destination_and_mass(self):
        state,cfg=self.case()
        rc.known_legsplit_receive(state,cfg,1.,999,off_ramp='OR_F_E',entry_step=900)
        row=state.known_legsplit_route_state['cohorts'][0]
        self.assertEqual((row['target'],row['due'],row['vehicles']),('free',910,1.))
        self.assertEqual(state.urban_link_storage['SC1004_W_out'],99.)

    def test_missing_observation_provenance_fails_without_creating_cohort(self):
        state,cfg=self.case();state.local_observation_summary={}
        before=copy.deepcopy(state.__dict__)
        with self.assertRaisesRegex(ValueError,'observation provenance'):
            rc.known_legsplit_receive(state,cfg,1.,999,movement='turn',entry_step=900)
        self.assertEqual(state.__dict__,before)

    def test_option_requires_physical_geometry_and_boolean(self):
        state,cfg=self.case()
        for value in ('true',True):
            with self.assertRaisesRegex(ValueError,'known_wout_physical_speed'):
                rc.configure_known_legsplit(cfg,{'urban':{'known_wout_physical_speed':value}},state,{})

    def test_existing_sc1001_physical_source_is_identical(self):
        state,cfg=self.case()
        cfg.network.direct_exit_legsplit={'travel':{'speed_source':'physical_observation'}}
        self.assertEqual(rc._direct_travel_speed(state,cfg,'approach'),36.)
        self.assertEqual(state.urban_link_speed_kph['approach'],144.)


if __name__=='__main__':unittest.main()
