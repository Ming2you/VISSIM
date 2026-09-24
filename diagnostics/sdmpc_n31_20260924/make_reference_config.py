"""C7: reference_config_n31_v2.json = b110 boundary config + five transport keys.

Start: the b110 boundary_literature_v1 boundary_config.json (C1 copy).
Add from transport_step1_exchange_off_v2/config.json exactly these five
freeway keys (plan C7 / N31 E6): physical_component_residence,
physical_offramp_interval_service, physical_ramp_capacity_vph (3600 for
RM_C10482/RM_C10681; else canonical_harness:354-361 defaults them to 1800),
physical_ramp_head_service_veh_per_cycle, physical_ramp_receiving_nodes.
Omit the twelve lane-group keys; canonical_harness:384-448 rejects them when
lane groups are off. component_boundary {admitted_interface, open_exit},
vsl_set [60,80,110] and v_free 110 come from the boundary config unchanged.

Run from the worktree root:  python -B diagnostics/sdmpc_n31_20260924/make_reference_config.py [--check]
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BOUNDARY = ('diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/res10_b110_20260923/'
            'train_s31_v2nc/boundary_literature_v1/boundary_config.json')
TRANSPORT = 'diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/transport_step1_exchange_off_v2/config.json'
OUT = HERE / 'reference_config_n31_v2.json'
TRANSPORT_KEYS = ('physical_component_residence', 'physical_offramp_interval_service', 'physical_ramp_capacity_vph',
                  'physical_ramp_head_service_veh_per_cycle', 'physical_ramp_receiving_nodes')
LANE_GROUP_KEYS = ('physical_mainline_lane_groups', 'physical_ramp_lane_coupling',
                   'physical_ramp_conflict_through_inventory', 'physical_offramp_lanes',
                   'physical_lane_destination_policy', 'physical_port_travel_lengths',
                   'physical_port_initial_positions', 'physical_port_origin_split', 'physical_branch_partition',
                   'physical_partition_exchange', 'physical_partition_speed_context',
                   'physical_upstream_exit_inventory')


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8-sig'))


def build():
    base, transport = load(BOUNDARY), load(TRANSPORT)
    only = set(transport['freeway']) - set(base['freeway'])
    if only != set(TRANSPORT_KEYS) | set(LANE_GROUP_KEYS):
        raise ValueError('Transport-only freeway keys changed: ' + repr(sorted(only)))
    if any(k in base['freeway'] for k in LANE_GROUP_KEYS):
        raise ValueError('Boundary config already declares a lane-group key')
    out = copy.deepcopy(base)
    for key in TRANSPORT_KEYS:
        out['freeway'][key] = copy.deepcopy(transport['freeway'][key])
    caps = out['freeway']['physical_ramp_capacity_vph']
    if caps.get('RM_C10482') != 3600.0 or caps.get('RM_C10681') != 3600.0:
        raise ValueError('Two-lane ramp capacities must be 3600 veh/h')
    if out['freeway'].get('component_boundary') != {'source': 'admitted_interface', 'terminal': 'open_exit'}:
        raise ValueError('Reference config must keep the calibrated component boundary')
    overrides = out['config_overrides']
    if overrides['freeway_follower']['vsl_set'] != [60.0, 80.0, 110.0] or overrides['network']['v_free'] != 110.0:
        raise ValueError('Reference config must keep vsl_set [60,80,110] and v_free 110')
    out['_n31_note'] = ('SDMPC-31 v2 plant reference (plan C7): ' + BOUNDARY + ' plus the five transport keys '
                        + ', '.join(TRANSPORT_KEYS) + ' from ' + TRANSPORT + '; the twelve lane-group keys are omitted.')
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = (json.dumps(build(), indent=2, ensure_ascii=False) + '\n').encode('utf-8')
    if args.check:
        if OUT.read_bytes() != data:
            raise SystemExit('reference_config_n31_v2.json differs from its generator')
    else:
        OUT.write_bytes(data)
    print('REFERENCE_CONFIG_OK ' + OUT.name)


if __name__ == '__main__':
    main()
