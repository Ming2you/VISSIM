"""C7: reference_config_n31_v2.json = b110 boundary config + five transport keys + the VSL model.

Start: the b110 boundary_literature_v1 boundary_config.json (C1 copy).
Add from transport_step1_exchange_off_v2/config.json exactly these five
freeway keys (plan C7 / N31 E6): physical_component_residence,
physical_offramp_interval_service, physical_ramp_capacity_vph (3600 for
RM_C10482/RM_C10681; else canonical_harness:354-361 defaults them to 1800),
physical_ramp_head_service_veh_per_cycle, physical_ramp_receiving_nodes.
Omit the twelve lane-group keys; canonical_harness:384-448 rejects them when
lane groups are off. component_boundary {admitted_interface, open_exit} and
v_free 110 come from the boundary config unchanged. Its vsl_set [60,80,110]
is replaced by the action set [50,60,70,80,90,100,110] (user decision
2026-09-24, = make_config_n31.VSL_SET); the plant reads only max(vsl_set),
which stays the boundary's 110 (the Carlson base and the inactive command).

VSL model (2026-09-24, user decision: port the branch VSL model into the plant
first): the two model keys of branch codex/control-full-review-20260909 commit
d80faf9, candidate A0.5_E4 (diagnostics/vsl_handoff_20260924/candidate.json,
sha256 a2fe3366...), under the branch's own key names:
  freeway.vsl_fd_response          FW_E Carlson A 0.5, E 4, alpha 0 (base = max vsl_set = 110)
  freeway.component_vsl_transport  FW_E sign cells + initial/ramp command 110
The coefficients are the branch's initial values: fitted on seed 29, demand v1,
with a different 110 km/h curve; a refit on v2 is pending. The sign cells are
re-derived here from this network's FW_E DSDs with the rule that reproduces
the handoff's cells (nearest refined cell boundary): DSD63-66 sit at chain
6733.2 m here (link 2 pos 3998.666), so its cell is 18, not the handoff's 16.
Not taken (separate local corrections fitted on the handoff scenario that
would override the v2 calibration): segment_params v_free 108.159 at parents
14/15, state_response anticipation 18.375, physical_cell_fd, ramp head-service
curves. FW_W has no fitted law and keeps the legacy speed cap.

Run from the worktree root:  python -B diagnostics/sdmpc_n31_20260924/make_reference_config.py [--check]
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BOUNDARY = ('diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/res10_b110_20260923/'
            'train_s31_v2nc/boundary_literature_v1/boundary_config.json')
TRANSPORT = 'diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/transport_step1_exchange_off_v2/config.json'
OUT = HERE / 'reference_config_n31_v2.json'
TRANSPORT_KEYS = ('physical_component_residence', 'physical_offramp_interval_service', 'physical_ramp_capacity_vph',
                  'physical_ramp_head_service_veh_per_cycle', 'physical_ramp_receiving_nodes')
NETWORK = 'diagnostics/sdmpc_n31_20260924/network/baseline_s31_v2nc.inpx'
GEOMETRY = ('diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/res10_b110_20260923/'
            'observations/s31_v2nc_observations/geometry.json')
VSL_KEYS = ('vsl_fd_response', 'component_vsl_transport', '_vsl_model_note')
BOUNDARY_VSL_SET = [60.0, 80.0, 110.0]
VSL_SET = [50.0, 60.0, 70.0, 80.0, 90.0, 100.0, 110.0]   # user decision 2026-09-24 (= make_config_n31.VSL_SET)
VSL_FD_RESPONSE = {'FW_E': {'law': 'carlson', 'A': 0.5, 'E': 4.0, 'alpha': 0.0}}
VSL_ROAD = 'FW_E'
HANDOFF_SIGN_CELLS = [0, 3, 5, 8, 14, 16, 26, 28]   # handoff network: DSD63-66 at chain 6341.7 m
EXPECTED_SIGN_CELLS = [0, 3, 5, 8, 14, 18, 26, 28]  # this network: DSD63-66 at chain 6733.2 m
VSL_MODEL_NOTE = ('Branch VSL model: codex/control-full-review-20260909 d80faf9917fc, candidate A0.5_E4 '
                  '(diagnostics/vsl_handoff_20260924/candidate.json sha256 a2fe3366bfae8de33796020f067c75ed17fe3451bb742b1a3475f6440f10b7dd): '
                  'Carlson speed-limit FD A=0.5 E=4 alpha=0, base command 110, and VSL exposure transport on FW_E. '
                  'Provenance: fitted on seed29 demand-v1 with a different 110 curve; refit on v2 pending. '
                  'Sign cells re-derived from this network (nearest refined boundary of each FW_E DSD section): '
                  'DSD63-66 at chain 6733.2 m -> 18 (handoff 16). Not taken: v_free 108.159 at parents 14/15, '
                  'anticipation 18.375, physical_cell_fd, ramp head-service curves. FW_W keeps the legacy cap law.')
LANE_GROUP_KEYS = ('physical_mainline_lane_groups', 'physical_ramp_lane_coupling',
                   'physical_ramp_conflict_through_inventory', 'physical_offramp_lanes',
                   'physical_lane_destination_policy', 'physical_port_travel_lengths',
                   'physical_port_initial_positions', 'physical_port_origin_split', 'physical_branch_partition',
                   'physical_partition_exchange', 'physical_partition_speed_context',
                   'physical_upstream_exit_inventory')


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8-sig'))


def sign_cells(road=VSL_ROAD):
    """Refined FW_E cells whose upstream boundary is nearest to each mainline DSD section.

    The rule reproduces the handoff's [0,3,5,8,14,16,26,28] on its own network;
    the geometry must be the one extracted from this pinned network.
    """
    geometry = load(GEOMETRY)
    network = ROOT / NETWORK
    if hashlib.sha256(network.read_bytes()).hexdigest() != geometry['network']['sha256']:
        raise ValueError('VSL sign geometry was extracted from another network')
    bounds = geometry['bounds'][road]
    cells = set()
    for node in ET.parse(network).getroot().findall('./desSpeedDecisions/desSpeedDecision'):
        link = node.get('lane').split()[0]
        address = geometry['addresses'].get(link)
        if address is None or address[0] != road:
            continue
        chain = float(address[1]) + float(node.get('pos'))
        index = min(range(len(bounds)), key=lambda i: abs(bounds[i] - chain))
        if index >= len(bounds) - 1:
            raise ValueError('A mainline DSD maps to the downstream end of ' + road)
        cells.add(index)
    return sorted(cells)


def vsl_model():
    signs = sign_cells()
    if signs != EXPECTED_SIGN_CELLS:
        raise ValueError('FW_E DSD sign cells changed: ' + repr(signs))
    return {'vsl_fd_response': copy.deepcopy(VSL_FD_RESPONSE),
            'component_vsl_transport': {VSL_ROAD: {'sign_cells': signs, 'initial_command': 110, 'ramp_command': 110}},
            '_vsl_model_note': VSL_MODEL_NOTE}


def build():
    base, transport = load(BOUNDARY), load(TRANSPORT)
    only = set(transport['freeway']) - set(base['freeway'])
    if only != set(TRANSPORT_KEYS) | set(LANE_GROUP_KEYS):
        raise ValueError('Transport-only freeway keys changed: ' + repr(sorted(only)))
    if any(k in base['freeway'] for k in LANE_GROUP_KEYS):
        raise ValueError('Boundary config already declares a lane-group key')
    if any(k in base['freeway'] or k in transport['freeway'] for k in VSL_KEYS):
        raise ValueError('A source config already declares a VSL model key')
    out = copy.deepcopy(base)
    for key in TRANSPORT_KEYS:
        out['freeway'][key] = copy.deepcopy(transport['freeway'][key])
    caps = out['freeway']['physical_ramp_capacity_vph']
    if caps.get('RM_C10482') != 3600.0 or caps.get('RM_C10681') != 3600.0:
        raise ValueError('Two-lane ramp capacities must be 3600 veh/h')
    if out['freeway'].get('component_boundary') != {'source': 'admitted_interface', 'terminal': 'open_exit'}:
        raise ValueError('Reference config must keep the calibrated component boundary')
    out['freeway'].update(vsl_model())
    overrides = out['config_overrides']
    if overrides['freeway_follower']['vsl_set'] != BOUNDARY_VSL_SET or overrides['network']['v_free'] != 110.0:
        raise ValueError('Boundary config must keep vsl_set [60,80,110] and v_free 110')
    if max(VSL_SET) != max(BOUNDARY_VSL_SET):
        raise ValueError('The action set must keep the calibrated maximum command 110')
    overrides['freeway_follower']['vsl_set'] = list(VSL_SET)
    out['_n31_note'] = ('SDMPC-31 v2 plant reference (plan C7): ' + BOUNDARY + ' plus the five transport keys '
                        + ', '.join(TRANSPORT_KEYS) + ' from ' + TRANSPORT + '; the twelve lane-group keys are omitted; '
                        + 'the branch VSL model keys ' + ', '.join(VSL_KEYS[:2]) + ' (freeway._vsl_model_note); '
                        + 'config_overrides.freeway_follower.vsl_set = the action set [50..110] step 10 '
                        + '(boundary [60,80,110]; max 110 unchanged).')
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
