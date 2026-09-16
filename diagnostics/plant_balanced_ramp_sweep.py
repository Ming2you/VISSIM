"""Offline native-demand scenarios using the canonical coupled plant (no COM).

The empty initial envelope is synthetic. Historical source pins establish the
unchanged geometry/service setup, never observations of these new scenarios.
"""
import argparse
import copy
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
from diagnostics.probe_model_area_integration import build_projected
from evaluation.controllers import area_runtime, vissim_stackelberg_adapter as adapter
from src.models.demand import DemandStep
from src.models.state import ControlAction

BASE = ROOT/'diagnostics/selected_control_demand/rule100_none3000_s13_v1/config.json'
DEC = ROOT/'evaluation/runs/rule100_none3000_s13_v1/decisions_rule100_none3000_s13_v1'


def save(path, value):
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)


def empty_envelope():
    raw = json.loads((DEC/'state_000001.json').read_text(encoding='utf-8-sig'))
    raw['diagnostic_synthetic_initial_state'] = {
        'kind': 'empty-network-at-zero',
        'source_template': str(DEC/'state_000001.json'),
        'not_native_observation': True,
    }
    raw['sim_sec'] = 0.
    raw['sim_period_sec'] = 9000.
    for key in ('total_vehicles', 'urban_vehicles', 'freeway_vehicles', 'ramp_vehicles',
                'boundary_vehicles', 'other_vehicles', 'stopped_vehicles'):
        raw[key] = 0
    raw['mean_speed_kph'] = raw['freeway_mean_speed_kph'] = 100.
    raw['ramp_counts'] = {k: 0 for k in raw['ramp_counts']}
    for section in ('vehicle_records', 'vehicle_routes'):
        obj = raw[section]
        for key in ('paused_at_sim_sec', 'capture_sim_sec_before', 'capture_sim_sec_after',
                    'sim_sec_before', 'sim_sec_after', 'collection_count_before',
                    'collection_count_after', 'record_count', 'unobservable_count',
                    'external_source_count'):
            if key in obj: obj[key] = 0
        obj['records'] = []
    for key in ('full_network_link_counts', 'full_network_link_stopped_counts'):
        raw['vehicle_records'][key] = {}
    for rows in raw['freeway_segments'].values():
        for row in rows: row.update(count=0, speed_sum=0.)
    obs = raw['local_observation']
    for key in ('observed_vehicle_count', 'unobservable_vehicle_count', 'queue_window_samples'):
        obs[key] = 0
    for key in ('link_counts', 'link_stopped_counts', 'link_stopped_counts_window_mean',
                'link_stopped_counts_window_max', 'link_counts_window_mean',
                'link_departures_window'):
        obs[key] = {k: 0. for k in obs[key]}
    obs['link_queue_tail_pos_m'] = {}
    obs['queue_bins'] = {}
    obs['queue_counters'] = {}
    window = obs['signal_observation_window']
    window['start_sec'] = window['end_sec'] = 0
    for key in ('unknown_links', 'bypass_link_exits'): window[key] = {}
    assert window['transition_count'] == 0
    assert all(row['crossings'] == row['green_sec'] == 0 for row in window['heads'])
    # Empty one-second template has no measured flow history; preserve service
    # calibration inputs independently of synthetic demand/stock.
    raw['rule_observation']['sim_sec'] = 0
    return raw


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    raw = empty_envelope()
    save(out/'empty_initial_state.json', raw)
    cfg,state,det,tuning,raw,mapping,meta = build_projected(
        BASE, out/'empty_initial_state.json', DEC/'action_000001.json', fixture_inputs=False)
    inventory = area_runtime.model_inventory(state,cfg)
    assert math.fsum(inventory.values()) < 1e-8, {k:v for k,v in inventory.items() if v}
    assert math.fsum(v['inside']+v['outside'] for v in state._control_area_ledger.stocks.values()) < 1e-8
    save(out/'initialized.json', {
        'time_sec':state.time_sec, 'initial_total':sum(inventory.values()),
        'state_attribute_types':{k:type(v).__name__ for k,v in vars(state).items()},
        'source_specs':{k:getattr(cfg.network,k,None) for k in (
            'shared_approach','sc2001_corridor','boundary_out_ramp_split',
            'leg_ramp_split','native_input_schedule','native_internal_inputs')},
        'ramp_movements': {m:v for m,v in cfg.network.urban_movements.items() if v.get('ramp')},
    })
    print('EMPTY INITIALIZATION PASS', flush=True)


if __name__ == '__main__':
    main()

