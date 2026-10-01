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
is replaced by the command set [80,90,100,110] (user approval 2026-09-28, =
make_config_n31.VSL_SET = repin_scenario_v2.VSL_COMMANDS; it was [50,...,110] from
2026-09-24); the plant reads only max(vsl_set), which stays the boundary's 110
(the inactive command, and the last knot of the L2 speed scale).

VSL model: the two model keys of branch codex/control-full-review-20260909 commit
d80faf9 (diagnostics/vsl_handoff_20260924/candidate.json, sha256 a2fe3366...),
under the branch's own key names, ported 2026-09-24:
  freeway.vsl_fd_response          FW_E Carlson law, base = max vsl_set = 110
  freeway.component_vsl_transport  FW_E sign cells + initial/ramp command 110
Since 2026-10-01 (user decision: single-value VSL compliance with plant law L2;
REPIN_V3C2_PLAN 3.4 / U4) the law is the N1F stage-2 selection L2: Carlson A 1.33,
E 0.87, alpha 0 with the measured speed scale m_v (80 0.7225223093088844, 90
0.8119772280655296, 100 0.9006844904146349; b = the cubic Lagrange polynomial
through (80,m80), (90,m90), (100,m100), (110,1), freeway_fd.speed_scale_ratio)
(D:/VISSIM_runs/20260928_n1f_vsl_stage2/reports/fit_results.json sha256 4091d6e1...
k4_stage2.D6.fits.L2, plan n1f_plan_stage2_v1.json d0e8fdba...), fitted on the
v3b-based single-value arms (seeds 41/43/47/53) and carried over to network v3c3
as a prior. 2026-09-28..10-01 it was the N1 selection L1 (A 0.94, E 1.44, alpha 0,
fit_results a81eb5cf...), which stays buildable as the distribution family:
  --vsl-family distribution --out-root <folder>   (never written into the tree)
writes the L1 reference there (VSL_FD_RESPONSE_BY_FAMILY). Before 2026-09-28 the
branch's initial A 0.5 / E 4 (seed 29, demand v1, a different 110 km/h curve). The sign cells are
re-derived here from this network's FW_E DSDs with the rule that reproduces
the handoff's cells (nearest refined cell boundary): DSD63-66 sit at chain
6733.2 m here (link 2 pos 3998.666), so its cell is 18, not the handoff's 16.
Not taken (separate local corrections fitted on the handoff scenario that
would override the v2 calibration): segment_params v_free 108.159 at parents
14/15, state_response anticipation 18.375, physical_cell_fd, ramp head-service
curves. FW_W has no fitted law and keeps the legacy speed cap.

Run from the worktree root:  python -B diagnostics/sdmpc_n31_20260924/make_reference_config.py [--check]
       [--vsl-family distribution --out-root <folder outside the tree>]
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
# Network v3c3 (2026-10-01) and its own no-control s31 geometry (only the sign cells read them; the geometry equals
# the v2, v3b and v3c1 ones except provenance, so the sign cells did not change with the re-pins).
NETWORK = 'diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx'
GEOMETRY = ('diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/v3c3_nc_20261001/'
            'observations/s31_v3c3nc_observations/geometry.json')
VSL_KEYS = ('vsl_fd_response', 'component_vsl_transport', '_vsl_model_note')
BOUNDARY_VSL_SET = [60.0, 80.0, 110.0]
VSL_SET = [80.0, 90.0, 100.0, 110.0]   # the command set, user approval 2026-09-28 (= make_config_n31.VSL_SET)
# The plant law per VSL family (= repin_scenario_v2.VSL_FAMILIES; plan REPIN_V3C2 3.5 U5-a). single_value is the live
# family (user decision 2026-10-01: N1F stage-2 L2, exact m_v of fit_results 4091d6e1, not the rounded 0.901/0.812/
# 0.723); distribution is N1 L1 (2026-09-28..10-01), built only with --vsl-family distribution --out-root.
L2_SPEED_SCALE = {'form': 'cubic_lagrange',
                  'levels': {'80': 0.7225223093088844, '90': 0.8119772280655296, '100': 0.9006844904146349},
                  'maximum': 110.0}
VSL_FD_RESPONSE_BY_FAMILY = {
    'single_value': {'FW_E': {'law': 'carlson', 'A': 1.33, 'E': 0.87, 'alpha': 0.0, 'speed_scale': L2_SPEED_SCALE}},
    'distribution': {'FW_E': {'law': 'carlson', 'A': 0.94, 'E': 1.44, 'alpha': 0.0}},
}
VSL_FAMILIES = tuple(VSL_FD_RESPONSE_BY_FAMILY)
VSL_FAMILY = 'single_value'
VSL_FD_RESPONSE = VSL_FD_RESPONSE_BY_FAMILY[VSL_FAMILY]
VSL_ROAD = 'FW_E'
HANDOFF_SIGN_CELLS = [0, 3, 5, 8, 14, 16, 26, 28]   # handoff network: DSD63-66 at chain 6341.7 m
EXPECTED_SIGN_CELLS = [0, 3, 5, 8, 14, 18, 26, 28]  # this network: DSD63-66 at chain 6733.2 m
_TRANSPORT_NOTE = ('Exposure transport from branch codex/control-full-review-20260909 d80faf9917fc '
                   '(diagnostics/vsl_handoff_20260924/candidate.json sha256 '
                   'a2fe3366bfae8de33796020f067c75ed17fe3451bb742b1a3475f6440f10b7dd, its A0.5/E4 replaced). '
                   'Sign cells re-derived from this network (nearest refined boundary of each FW_E DSD section): '
                   'DSD63-66 at chain 6733.2 m -> 18 (handoff 16). Not taken: v_free 108.159 at parents 14/15, '
                   'anticipation 18.375, physical_cell_fd, ramp head-service curves. FW_W keeps the legacy cap law.')
VSL_MODEL_NOTE_BY_FAMILY = {
    'single_value': (
        'VSL law N1F stage-2 L2 (user decision 2026-10-01, single-value VSL compliance): Carlson speed-limit FD A=1.33 '
        'E=0.87 alpha=0 on FW_E with the measured speed scale m_v 80 0.7225223093088844 / 90 0.8119772280655296 / 100 '
        '0.9006844904146349 (b = the cubic Lagrange polynomial through these and (110, 1); base command 110 = '
        'max(vsl_set)); D:/VISSIM_runs/20260928_n1f_vsl_stage2/reports/fit_results.json sha256 '
        '4091d6e140f1cf1b29ae51e7863eb1d41d0d8169756ae28987deda69b2516f6c k4_stage2.D6.fits.L2, plan n1f_plan_stage2_v1.json '
        'sha256 d0e8fdba6362084ace5128ca9352789a3235a905bb0ec634692c054d69f524b0, analysis freeze 6267ba5e, report '
        'N1F_STAGE2_RESULTS.md 04a3fb25; selected by rule (LOSO + LOLO loss 152.2 vs L1 185.5); fitted on the v3b-based '
        'single-value arms (seeds 41/43/47/53) and carried over to network v3c3 as a prior; the Carlson family is '
        'formally rejected by rule (b)(i) (chi2/dof 6.41; L2 itself 5.73); pessimistic at 80 (B2 outflow -4.0 % '
        'predicted vs -0.34 % observed). The commands 80/90/100/110 are written as the single-value distributions '
        '81/91/101/110 (tuning actuation.vsl_command_distribution, runner 81,91,101,110). ' + _TRANSPORT_NOTE),
    'distribution': (
        'VSL law N1 L1 (distribution family, generator option only since 2026-10-01; live 2026-09-28..10-01): Carlson '
        'speed-limit FD A=0.94 E=1.44 alpha=0 on FW_E, base command 110 = max(vsl_set); '
        'D:/VISSIM_runs/20260927_n1_vsl/reports/fit_results.json sha256 '
        'a81eb5cf7a090d3da6184bc9572e873ece255f1cce024823a1c468df4fdf5117 k4_core.fits.L1, plan n1_plan_v3.json sha256 '
        '0db0d1c6e50ed2688066d3bf59e9d06116661df71930e83988df0cc6af37c511, fitted on the v3b NC seeds 41/43/47/53 at '
        '80-110 (spread distributions 80/90/100), carried over to network v3c3 as a prior; the Carlson family is '
        'formally rejected by rule (b)(i) (chi2/dof 4.19). The commands are written as themselves (no map, runner '
        '80,90,100,110). ' + _TRANSPORT_NOTE),
}
VSL_MODEL_NOTE = VSL_MODEL_NOTE_BY_FAMILY[VSL_FAMILY]
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


def vsl_model(family=VSL_FAMILY):
    signs = sign_cells()
    if signs != EXPECTED_SIGN_CELLS:
        raise ValueError('FW_E DSD sign cells changed: ' + repr(signs))
    return {'vsl_fd_response': copy.deepcopy(VSL_FD_RESPONSE_BY_FAMILY[family]),
            'component_vsl_transport': {VSL_ROAD: {'sign_cells': signs, 'initial_command': 110, 'ramp_command': 110}},
            '_vsl_model_note': VSL_MODEL_NOTE_BY_FAMILY[family]}


def build(family=VSL_FAMILY):
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
    out['freeway'].update(vsl_model(family))
    overrides = out['config_overrides']
    if overrides['freeway_follower']['vsl_set'] != BOUNDARY_VSL_SET or overrides['network']['v_free'] != 110.0:
        raise ValueError('Boundary config must keep vsl_set [60,80,110] and v_free 110')
    if max(VSL_SET) != max(BOUNDARY_VSL_SET):
        raise ValueError('The action set must keep the calibrated maximum command 110')
    overrides['freeway_follower']['vsl_set'] = list(VSL_SET)
    out['_n31_note'] = ('SDMPC-31 v2 plant reference (plan C7): ' + BOUNDARY + ' plus the five transport keys '
                        + ', '.join(TRANSPORT_KEYS) + ' from ' + TRANSPORT + '; the twelve lane-group keys are omitted; '
                        + 'the branch VSL model keys ' + ', '.join(VSL_KEYS[:2]) + ' (freeway._vsl_model_note); '
                        + 'config_overrides.freeway_follower.vsl_set = the action set [80,90,100,110] '
                        + '(boundary [60,80,110]; max 110 unchanged).')
    return out


def family_out(family, out_root):
    """OUT for the live family; <out_root>/<repo-relative OUT> for a family overlay (never inside the tree)."""
    if out_root is None:
        if family != VSL_FAMILY:
            raise SystemExit('--vsl-family %s writes only with --out-root (the tree holds the %s family)' % (family, VSL_FAMILY))
        return OUT
    root = Path(out_root).resolve()
    if root.is_relative_to(ROOT.resolve()):
        raise SystemExit('--out-root must lie outside the tree: ' + str(root))
    return root / OUT.relative_to(ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--vsl-family', choices=VSL_FAMILIES, default=VSL_FAMILY)
    parser.add_argument('--out-root', help='write the reference of --vsl-family under this folder (repo-relative path)')
    args = parser.parse_args()
    out = family_out(args.vsl_family, args.out_root)
    data = (json.dumps(build(args.vsl_family), indent=2, ensure_ascii=False) + '\n').encode('utf-8')
    if args.check:
        if out.read_bytes() != data:
            raise SystemExit('reference_config_n31_v2.json differs from its generator')
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    print('REFERENCE_CONFIG_OK ' + out.name + ' family=' + args.vsl_family + ' sha256=' + hashlib.sha256(data).hexdigest())


if __name__ == '__main__':
    main()
