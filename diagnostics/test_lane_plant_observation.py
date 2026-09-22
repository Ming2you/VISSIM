"""Live observation contracts needed before native SDMPC lane-plant use."""
import copy
import unittest
import json
import tempfile
from pathlib import Path

from evaluation.controllers.lane_plant_observation import LanePlantObserver, load_causal_snapshot


def vehicle(no=1, link=10, lane=1, position=600., speed=20.):
    return [no, link, lane, position, speed, 4.5, None, None, None,
            None, None, None, None, None, None]


def frame(sec, rows=()):
    return {'time_s': sec, 'complete': True, 'vehicles': list(rows)}


def observer(history=3, interval=1):
    geometry = {'addresses': {'10': ['FW_E', 0.]}, 'bounds': {'FW_E': [0., 1000.]},
        'boundaries': [dict(kind='ramp', connector=500, id='RM_C500', road='FW_E', to_cell=0,chain_pos_m=500.),
                       dict(kind='offramp', connector=600, road='FW_E', from_cell=0,chain_pos_m=400.)]}
    lane = {'schema': 'physical-mainline-lane-groups/v1', 'road': 'FW_E',
        'widths': [[1., 1., 1.]], 'matrices': [],
        'ramp_access': {'RM_C500': {'cell': 0, 'weights': [1., 0., 0.]}},
        'off_access': {'600': {'cell': 0, 'weights': [1., 0., 0.]}}}
    return LanePlantObserver(geometry, {'FW_E': lane}, {}, history_sec=history,sample_interval_sec=interval)


class ObservationTests(unittest.TestCase):
    def test_five_second_samples_use_elapsed_seconds_not_frame_count(self):
        obs=observer(15,5)
        obs.push(frame(0));obs.push(frame(1,[vehicle(lane=1)]))
        obs.push(frame(5,[vehicle(lane=1)]));obs.push(frame(10,[vehicle(lane=2)]));obs.push(frame(15,[vehicle(lane=2)]))
        snap=obs.snapshot(15)
        self.assertEqual(snap['sample_interval_sec'],5)
        self.assertEqual(snap['lane_group_dynamics']['FW_E']['exchange_rates_per_sec'][0][0][1],.2)
        self.assertEqual([f['time_s'] for f in snap['frames']],[0,1,5,10,15])
        with self.assertRaisesRegex(ValueError,'cadence'):obs.push(frame(16))
        obs.push(frame(20,[vehicle()]))
        self.assertEqual([f['time_s'] for f in obs.snapshot(20)['frames']],[5,10,15,20])

    def test_five_second_checkpoint_no_interpolated_history_or_cadence_reuse(self):
        from evaluation.controllers.lane_plant_observation import sample_times
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            for sec in sample_times(0,30,5):
                rows=[] if sec==0 else [vehicle(link=500,position=10.)] if sec==1 else [vehicle()]
                data=dict(frame(sec,rows),schema='lane-plant-frame/v1',run_id='test',sample_interval_sec=5)
                (folder/f'frame_{sec:06d}.json').write_text(json.dumps(data),encoding='utf-16')
            load_causal_snapshot(folder,observer(15,5),15,run_id='test',configuration_sha256='cfg')
            resumed=load_causal_snapshot(folder,observer(15,5),30,run_id='test',configuration_sha256='cfg')
            replay=load_causal_snapshot(folder,observer(15,5),30,run_id='test',configuration_sha256='cfg',use_checkpoint=False)
            self.assertEqual(resumed,replay)
            self.assertEqual(resumed['ramp_origin_tags'],{1:'RM_C500'})
            with self.assertRaisesRegex(ValueError,'identity'):
                load_causal_snapshot(folder,observer(15,1),30,run_id='test',configuration_sha256='cfg')

    def test_com_integral_route_numbers_join_without_rounding(self):
        from diagnostics.test_vehicle_routes import physical
        from evaluation.controllers.lane_plant_runtime import bind_current_routes
        from evaluation.controllers.vehicle_routes import complete_vehicle_routes
        raw=physical(None)
        rows=[[n,56,1,300.,40.,4.5,1129.,2.,'STATIC',None,None,None,None,None,None] for n in (9,20)]
        observation={'frames':[{'vehicles':rows}]}
        joined=bind_current_routes(raw,observation)
        routes=complete_vehicle_routes(joined,required=True)
        self.assertEqual(routes[9]['route_decision_no'],1129)
        self.assertIs(type(routes[9]['route_no']),int)
        self.assertIsNone(raw['vehicle_routes'])
        rows[0][7]=2.5
        with self.assertRaisesRegex(ValueError,'Invalid current-route'):
            bind_current_routes(raw,observation)

    def test_checkpoint_resume_keeps_origin_beyond_window_and_rejects_changed_source(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            for sec in range(11):
                rows = [] if sec == 0 else [vehicle(link=500,position=10.)] if sec == 1 else [vehicle()]
                data = dict(frame(sec,rows),schema='lane-plant-frame/v1',run_id='test')
                (folder/f'frame_{sec:06d}.json').write_text(json.dumps(data),encoding='utf-16')
            first = load_causal_snapshot(folder,observer(),4,run_id='test',configuration_sha256='cfg')
            resumed = load_causal_snapshot(folder,observer(),10,run_id='test',configuration_sha256='cfg')
            self.assertEqual(first['ramp_origin_tags'],resumed['ramp_origin_tags'])
            self.assertEqual(resumed['ramp_origin_tags'],{1:'RM_C500'})
            same = load_causal_snapshot(folder,observer(),10,run_id='test',configuration_sha256='cfg')
            self.assertEqual(same,resumed)
            with self.assertRaisesRegex(ValueError,'future'):
                load_causal_snapshot(folder,observer(),9,run_id='test',configuration_sha256='cfg')
            checkpoint=(folder/'observer_checkpoint.json').read_bytes()
            replay=load_causal_snapshot(folder,observer(),4,run_id='test',configuration_sha256='cfg',use_checkpoint=False)
            self.assertEqual(replay,first)
            self.assertEqual((folder/'observer_checkpoint.json').read_bytes(),checkpoint)
            p=folder/'frame_000010.json'
            p.write_text(p.read_text(encoding='utf-16')+' ',encoding='utf-16')
            with self.assertRaisesRegex(ValueError,'source changed'):
                load_causal_snapshot(folder,observer(),10,run_id='test',configuration_sha256='cfg')

    def test_origin_survives_wait_longer_than_history_then_clears_on_exit(self):
        obs = observer()
        obs.push(frame(0)); obs.push(frame(1, [vehicle(link=500, position=10.)]))
        for sec in range(2, 11):
            obs.push(frame(sec, [vehicle()]))
        snap = obs.snapshot(10)
        lane = snap['lane_group_dynamics']['FW_E']
        self.assertEqual(snap['ramp_origin_tags'], {1: 'RM_C500'})
        self.assertEqual(lane['initial_ramp_origin']['RM_C500'], [1., 0., 0.])
        self.assertEqual(lane['initial_off_eligible']['600'], [0., 0., 0.])
        # Continue into an observed downstream cell rather than disappearing
        # onto an unmodelled link (which must fail boundary conservation).
        obs.bounds['FW_E'] = [0.,1000.,2000.]
        obs.lane_geometry['FW_E']['widths'].append([3.])
        obs.addresses[20] = ('FW_E',1000.)
        obs.push(frame(11, [vehicle(link=20)]))
        self.assertEqual(obs.snapshot(11)['ramp_origin_tags'], {})

    def test_pre_post_partition_preserves_stock_and_velocity_moment(self):
        obs = observer(); obs.push(frame(0))
        rows = [vehicle(1, position=200., speed=10.), vehicle(2, position=800., speed=30.)]
        for sec in range(1, 4): obs.push(frame(sec, rows))
        lane = obs.snapshot(3)['lane_group_dynamics']['FW_E']
        self.assertEqual(lane['initial_groups'][0][0], {'n_veh': 2., 'v_kmh': 20.})
        self.assertEqual(lane['branch_partition_initial']['600']['pre'][0], {'n_veh': 1., 'v_kmh': 10.})
        self.assertEqual(lane['branch_partition_initial']['600']['post'][0], {'n_veh': 1., 'v_kmh': 30.})

    def test_lane_exchange_uses_same_link_and_earlier_history_only(self):
        obs = observer(); obs.push(frame(0))
        obs.push(frame(1, [vehicle(lane=1)]))
        obs.push(frame(2, [vehicle(lane=2)]))
        obs.push(frame(3, [vehicle(lane=2)]))
        rates = obs.snapshot(3)['lane_group_dynamics']['FW_E']['exchange_rates_per_sec'][0]
        self.assertEqual(rates[0][1], 1.)
        self.assertEqual(rates[1][0], 0.)
        with self.assertRaisesRegex(ValueError, 'cutoff'): obs.snapshot(4)

    def test_returned_history_does_not_mutate_observer_or_other_candidates(self):
        obs = observer(); obs.push(frame(0))
        for sec in range(1, 4): obs.push(frame(sec, [vehicle()]))
        snap = obs.snapshot(3)
        snap['frames'][-1]['vehicles'][0][4] = 999.
        snap['lane_group_dynamics']['FW_E']['initial_groups'][0][0]['n_veh'] = 99.
        actual = obs.snapshot(3)
        self.assertEqual(actual['frames'][-1]['vehicles'][0][4], 20.)
        self.assertEqual(actual['lane_group_dynamics']['FW_E']['initial_groups'][0][0]['n_veh'], 1.)

    def test_missing_cadence_incomplete_or_duplicate_capture_fails(self):
        obs = observer(); obs.push(frame(0))
        for bad in (frame(2), {**frame(1), 'complete': False}, frame(1, [vehicle(), vehicle()])):
            with self.assertRaises(ValueError): obs.push(bad)
        self.assertEqual(obs.time_sec, 0)
        obs.push(frame(1, [vehicle()]))
        # Native warmup has only the actual past since the empty start.
        warmup=obs.snapshot(1)
        self.assertEqual(warmup['history_start_s'],0)
        self.assertEqual([f['time_s'] for f in warmup['frames']],[0,1])


if __name__ == '__main__':
    unittest.main()
