"""Boundary and literature equations; synthetic conservation, no VISSIM."""
import copy
import json
import unittest
from pathlib import Path

from canonical_harness import load_base_model, TrafficState, ControlAction, DemandStep, accounting

B = Path(__file__).parent / 'res10_20260922'


class BoundaryLiterature(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        geometry = json.loads((B/'p100_observations/geometry.json').read_text())
        cls.model = load_base_model(geometry, B/'fit_config.json')

    def advance(self, *, source=False, terminal=False, density=20., literature=None):
        cfg = self.model._config('FW_E', {})
        net = cfg.network
        if source: net.freeway_source_capacity_veh_h = {'FW_E': None}
        if terminal: net.freeway_terminal_capacity_veh_h = {'FW_E': None}
        if literature: net.freeway_hadiuzzaman = {'FW_E': literature}
        count = len(net.freeway_segment_lanes['FW_E'])
        net.freeway_segments_per_link = count
        state = TrafficState.initial(cfg)
        state.freeway_effective_lanes['FW_E'] = list(net.freeway_segment_lanes['FW_E'])
        state.freeway_density['FW_E'] = [density]*count
        state.freeway_speed['FW_E'] = [120.]*count
        state.mainline_origin_queue['FW_E'] = 0.
        state.urban_link_storage = dict(net.urban_link_storage_veh)
        initial = sum(accounting.continuity_vehicle_counts(state,cfg)['FW_E'])
        _, diag = accounting._freeway_substep_events(state,ControlAction.uncontrolled(cfg),
            DemandStep({'FW_E':8000.},{},{}),cfg,offramp_capacity_veh_h={o:0. for o in net.off_ramps},
            ramp_release_veh_h={r:0. for r in net.ramps},
            ramp_release_diagnostics={'total_no_meter_flow':0.,'mean_ramp_receiving_factor':1.},
            update_ramp_queues=False,include_ramp_queue_ttt=False)
        admitted = 8000./3600-state.mainline_origin_queue['FW_E']
        final = sum(accounting.continuity_vehicle_counts(state,cfg)['FW_E'])
        self.assertAlmostEqual(final-initial,admitted-diag['mainline_exit_flow_total']/3600,places=9)
        self.assertEqual(diag['density_projection_count'],0)
        return admitted*3600,diag,state

    def test_admitted_interface_removes_only_extra_source_gate(self):
        self.assertAlmostEqual(self.advance()[0],6937.)
        self.assertAlmostEqual(self.advance(source=True)[0],8000.)

    def test_open_exit_does_not_reuse_origin_capacity(self):
        self.assertAlmostEqual(self.advance()[1]['mainline_exit_flow_total'],6937.*3/4)
        self.assertAlmostEqual(self.advance(terminal=True)[1]['mainline_exit_flow_total'],7200.)

    def test_no_source_override_can_inject_into_full_storage(self):
        admitted,_,state = self.advance(source=True,density=self.model.base.network.rho_max)
        self.assertAlmostEqual(admitted,0.)
        self.assertGreater(state.mainline_origin_queue['FW_E'],0.)

    def test_hadi_wang_receiving_and_command_are_used(self):
        cells=[dict(capacity_vphpl=2400.,wave_kmh=15.,rho_critical=30.,theta=.15)]*31
        h=dict(ctm=True,relaxation='command',cells=cells,relaxation_cells=list(range(31)),congested_branch='fixed_wave')
        _,a,_=self.advance(source=True,terminal=True,density=40.,literature=h)
        h=copy.deepcopy(h);h['congested_branch']='capacity_critical'
        _,b,_=self.advance(source=True,terminal=True,density=40.,literature=h)
        self.assertGreater(a['literature_receiving_limited_cells'],0)
        self.assertGreater(a['literature_command_cells'],0)
        self.assertNotEqual(a['literature_receiving_total_vph'],b['literature_receiving_total_vph'])

    def test_source_mismatch_is_scored_separately_from_cell_outflow(self):
        from boundary_factory import ObservationData, build_window
        from scoring import score_rollout
        data=ObservationData(B/'p100_observations')
        w=build_window(data,2700.1,'conditioned_diagnostic',model_step_sec=1)
        result=self.model.rollout(w['initial_cells'],w['boundary_steps'],roads=('FW_E',))
        old=score_rollout(data,2700.1,result,'FW_E')
        new=score_rollout(data,2700.1,result,'FW_E',include_source_boundary=True)
        self.assertGreater(new['source_flow_vph']['rmse'],0.)
        self.assertAlmostEqual(new['objective']-old['objective'],(new['source_flow_vph']['rmse']/1000.)**2)
        for key in ('speed','density','flow_vph'):
            self.assertEqual(old[key],new[key])


if __name__ == '__main__': unittest.main()
