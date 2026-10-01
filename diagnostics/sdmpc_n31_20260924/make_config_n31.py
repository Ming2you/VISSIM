"""C9: config_n31_v2.json = the WP-E base tuning plus the v2 plant differences.

The base (N31D/scenario/config_n31_v2.base.json, written by repin_scenario_v2.py) is OBS1
with the scenario pack re-pinned to the runtime network (v3c3 since 2026-10-01; v3c1 2026-09-28..10-01; v3b
2026-09-25..28). This script
adds exactly the
plan C9 differences and nothing else:

  freeway.lane_plant                                  -> plant_n31_v2.json          (OBS1:8082)
  freeway.segment_params                              -> C1 b110 21-row copy        (NEW-10)
  urban.capacity.head_observation.sample_interval_sec    deleted                    (OBS1:7831)
  config_overrides.freeway_follower.vsl_set           -> [80, 90, 100, 110]          (OBS1:7466; the COMMAND set,
                                                         user approval 2026-09-28, was 50..110)
  actuation.vsl_command_distribution                  -> {'model': 'single_value', 'distribution_by_command':
                                                         {'80': 81, '90': 91, '100': 101, '110': 110}} (user
                                                         decision 2026-10-01, single-value VSL with the plant law
                                                         L2: the action CSV writes command c as distribution M(c);
                                                         K5 writer, V-9 family check; absent = identity)
  config_overrides.network.v_free                     -> 110                        (OBS1:7433)
  _canonical.fd_fit_20260828.values.v_free            -> 110                        (OBS1:7961, record only)
  execution.native_signal_record                      -> false                      (NEW-2)
  execution.signal_vbs_config                         -> N31D/scenario/lane_native_b110.vbs
  observation.physical_branch_projection.source.network -> the pinned network (v3c3) (OBS1:8109-8113)
  calibration_override.prediction.local_ramp_arrival_forecast
      .queue_drain_horizon_sec_by_ramp, .max_vph_by_ramp -> keyed by the eight RM_C meters (RAMP_FORECAST)
      .strict_ramp_keys                                  -> true (no silent 120 s / 900 veh/h fallback)
  urban.beta.source                                   -> routing_v3c3 (BETA_SOURCE: the routing beta of the pinned
                                                         network v3c3, N31D/beta/; OBS1 used the 0824 e14 table)
  urban.ramp.offramp_direct_share                     -> {SC1001: 0.468, SC1004: 0.484}, the adapter's former code
                                                         default made explicit (install_offramp_direct_landing); the
                                                         runtime is unchanged

Urban plant batch 1 (U1 + U2 + U3, 2026-09-25/26) is a SEPARATE candidate, not the default above:
  python -B diagnostics/sdmpc_n31_20260924/make_config_n31.py --urban-batch1 [--components U1,U3] [--check]
writes config_n31_v2_urban_b1.json (all three; config_n31_v2_urban_b1_u1u3.json etc. for a subset, U1 always) =
config_n31_v2.json plus (apply_urban_batch1, URBAN_B1_* pins)
  urban.beta.source / sha256                 -> routing_v3c3_2 (complete physical routing beta, 492 movements) + pin
  urban.movements.nonexistent_declaration    -> the pinned movement declaration (U1; user decision 2026-09-26:
                                                SC7 E / E_SC16 -> N_SC11 exist, connector 10332, relFlow 0.429;
                                                re-pinned to v3c1 2026-09-28 and v3c3 2026-10-01, rows unchanged)
  urban.movements.physical_phase_authority   -> the default evidence plus those two rows in their head's phase
                                                (head 140101 = SC7 SG 1 = plan p4; was p3, no green) (U1)
  control_area_objective.route_contract_path -> the default contract plus the departure area route of
                                                SC7_E_SC16_to_N_SC11 (10332, inside -> inside) (U1)
  urban.queue.attribution / route_evidence   -> "route" + the pinned stop-line crossing table
  urban.movements.unsignalized_evidence      -> the pinned head-free exclusive-lane turns (FZP-validated)
  urban.ramp.offramp_direct_route_prior      -> the pinned relFlow direct share per off-ramp group

Network v3c3 (user approval 2026-10-01): the pinned network is 3de889f0 (v3c1 2577209b + vehicle composition 14 on
the freeway entries 1098/1099 (v3c2) + the single-value distributions 81/91/101). The b110 segment_params (and the
plant's boundary fit) are v2 priors fitted on v2 NC s31 (f475ce42) and are NOT refit; the ramp-arrival forecast is
re-derived from the v3c3 NC fit seeds 31/41/43/47 and the v3c2 s53 run (declared substitute; s37 held out), the
routing beta tables and every batch-1 input on v3c3 (new *_v3c3_* files; the v3c1 files and the routing_v3c1 /
routing_v3c1_2 sources left this tree, v3c1 replays run from a frozen tree).

VSL families (repin plan 2026-10-01 U5-a, V-11). The tree holds the single_value family: the map above, the plant
reference with the L2 speed scale, the runner 81,91,101,110. The distribution family (no map, L1, runner
80,90,100,110) is built only as an overlay outside the tree, in this order (each with the same --out-root):
  python -B diagnostics/sdmpc_n31_20260924/repin_scenario_v2.py runner-family --vsl-family distribution --out-root <F>
  python -B scripts/build_obs150_detectors.py --out-root <F>
  python -B diagnostics/sdmpc_n31_20260924/make_reference_config.py --vsl-family distribution --out-root <F>
  python -B diagnostics/sdmpc_n31_20260924/make_plant_n31.py --vsl-family distribution --out-root <F>
  python -B diagnostics/sdmpc_n31_20260924/make_config_n31.py --vsl-family distribution --out-root <F>
      [--urban-batch1 [--components U1,U3]]
Every repo-relative input resolves in <F> first; the outputs keep repo-relative pins. Launching that family means
laying <F> over a worktree, committing and freezing it (run_sdmpc_n31.ps1 reads only a frozen git head).

The pack paths themselves are WP-E's (C9 row "팩 경로"): the generator refuses a
base that still names diagnostics/lane_plant_20260921/scenario/ anywhere, and
checks known_wout_route_evidence's own sha pin. With the plant written, the
result must pass obs150_contract.validate_tuning_v2 and preflight_tuning_paths.

Run from the worktree root:
  python -B diagnostics/sdmpc_n31_20260924/make_config_n31.py [--check]
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

N31D = 'diagnostics/sdmpc_n31_20260924'
BASE = N31D + '/scenario/config_n31_v2.base.json'
OUT = HERE / 'config_n31_v2.json'
PLANT = N31D + '/plant_n31_v2.json'
SEGMENT_PARAMS = ('diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/res10_b110_20260923/'
                  'train_s31_v2nc/free_speed_b110/segment_params.json')
RUNNER_CONFIG = N31D + '/scenario/lane_native_b110.vbs'
NETWORK = N31D + '/network/baseline_s31_v3c3nc.inpx'
NETWORK_SHA256 = '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e'   # v3c3 (v3c1 2577209b until 2026-10-01)
NETWORK_LABEL = 'v3c3 3de889f0'
# Routing beta of the pinned network (adapter BETA_EVIDENCE_JSON['routing_v3c3']): scripts/derive_routing_turn_beta.py
# with the 474-movement core17legs4b config (N31D/beta/movements_core17legs4b_20260819.json = git 4898446^ blob) on
# the v3c3 network (the beta values equal the v3c1 table's: v3c3 edits no routing decision). The default 'routing'
# table (outputs/movement_beta_routing_20260824.json) was derived on network modi_eval_userfix_20260814e (25 movements differ on v2, 48 on v3b before the explicit assignment below).
# The destination-set inference of that script mis-attaches the interchange decisions (SC1004 1124/1126/1138/1140 all
# on E_SC107, SC1001 1117 dropped as a W/offW/offE tie) and, on v3c1, decision 1165 (V5b, on SC1005|W_SC1004 instead of
# SC1|N_SC101); BETA_EXPLICIT attaches them to the approaches whose vehicles pass them (--explicit-approach, user
# decisions 2026-09-25 and 2026-09-28). Both files are pinned, because the adapter reads BETA_FILE by path. Re-derive
# (worktree root):
#   python -B scripts/derive_routing_turn_beta.py --network <NETWORK> --movements-config <BETA_MOVEMENTS>
#       --out <BETA_FILE> --generated 2026-10-01 --explicit-approach <BETA_EXPLICIT>
BETA_SOURCE = 'routing_v3c3'
BETA_FILE = N31D + '/beta/movement_beta_routing_v3c3_20261001.json'
BETA_SHA256 = '506ec5c1d67654a11c2d3f3d9af804535f6d89c6e21685ca879eb7714fb8cb17'
BETA_EXPLICIT = N31D + '/beta/explicit_approach_v3c3_20261001.json'
BETA_EXPLICIT_SHA256 = 'a3957146a606319215b5771525442bf20d73c6a196eeea784d75e00731edca3f'
BETA_MOVEMENTS = N31D + '/beta/movements_core17legs4b_20260819.json'
# Urban plant batch 1 (U1/U2/U3, 2026-09-25; re-pinned to network v3c1 2026-09-28 and to v3c3 2026-10-01): pinned
# inputs of the separate candidate config_n31_v2_urban_b1.json.
# Re-derive (worktree root, in this order; each generator also has --check):
#   python -B scripts/derive_phase_authority_v3b.py --out <URBAN_B1_PHASE_AUTHORITY>
#   python -B scripts/derive_area_routes_v3b.py --out <URBAN_B1_AREA_ROUTES>      (also writes its .provenance.json)
#   python -B scripts/derive_routing_beta_physical.py --out <URBAN_B1_BETA_FILE>
#   python -B scripts/derive_unsignalized_turns.py --out <URBAN_B1_UNSIGNALIZED>
#   python -B scripts/derive_route_queue_attribution.py --out <URBAN_B1_ROUTE_EVIDENCE>
#   python -B scripts/derive_unsignalized_validation.py --out <URBAN_B1_UNSIGNALIZED_VALIDATION>   (reads the five
#       no-control fit-seed FZPs: v3c3 31/41/43/47 and the v3c2 s53 run as the declared substitute, about 5.9 GB; the
#       FZP validation table the unsignalized-turn derivation reads; s37 is held out). On v3c3 the unchanged rule
#       would drop SC103_S_SC6_to_E (connector 10096, stopped_before_share 0.0472 on v3c1 -> 0.0544 > 0.05); by the
#       user decision of 2026-10-01 (K7 amendment 1, O-3) the turn set stays the v3c1 23 (derive_unsignalized_turns
#       MEMBERSHIP_PIN) and SC103_S_SC6_to_E is recorded as the known exceedance (membership_pin).
# (derive_unsignalized_turns reads the validation table: run the validation before it.) The relFlow off-ramp prior
# (URBAN_B1_OFFRAMP_PRIOR, re-derived by offramp_routing.derive_prior at install) and the movement declaration
# (URBAN_B1_DECLARATION, a reviewed decision record that the two derivations verify against the network) are pinned
# inputs.
URBAN_B1_BETA_SOURCE = 'routing_v3c3_2'
URBAN_B1_BETA_FILE = N31D + '/beta/movement_beta_routing_v3c3_2_20261001.json'
URBAN_B1_BETA_SHA256 = '4290d180d09e9ae3a1da7de16a0af6ea917b3aaac623a46eec7cd9c2f013422d'
URBAN_B1_ENTRY = N31D + '/beta/approach_entry_v3c3_20261001.json'
URBAN_B1_ENTRY_SHA256 = '514ae8e064154efa22c4d4e81fb7c3a113fdb63abfaeee6442ce0c707d79f56b'
# User decision 2026-09-26 (U1): the runtime's nonexistence declaration of SC7_E_to_N_SC11 / SC7_E_SC16_to_N_SC11 is the
# v2 reading; on v3b 10332 is their right turn (relFlow 63 / 147 = 0.429). The candidates read the v3b declaration and
# serve the two in the phase of their real head (140101, SC7 SG 1 = plan p4) through the extended phase authority
# (the default tuning's URBAN_B1_PHASE_AUTHORITY_BASE plus two rows).
URBAN_B1_DECLARATION = N31D + '/urban/movement_nonexistent_v3c3_20261001.json'
URBAN_B1_DECLARATION_SHA256 = '04fce57ca7c6a4f8e13331d0bfce6134011da9f52a144ad8b999acab539d2a28'
URBAN_B1_PHASE_AUTHORITY_BASE = N31D + '/scenario/physical_phase_authority_local_1df35c.json'
URBAN_B1_PHASE_AUTHORITY = N31D + '/urban/physical_phase_authority_v3c3_20261001.json'
URBAN_B1_PHASE_AUTHORITY_SHA256 = '9ba47f3bebf383025a00af05d1f8643a8ea0c60db17b02b53fde50e47a0f72ab'
# ... and a departing SC7_E_SC16_to_N_SC11 needs its physical area route (the default contract left it 'no_match'):
# scripts/derive_area_routes_v3b.py writes the default contract plus that route (and a .provenance.json sidecar).
# The contract carries old-network XML copies of decisions 1061, 1128:2 and 1124 inherited from the default contract
# (REPIN_PLAN §4.3 2, decision D5 2026-09-28: kept as is and recorded; their rows carry no branch weight).
URBAN_B1_AREA_ROUTES_BASE = 'diagnostics/control_area_route_contract_physical_routes.json'
URBAN_B1_AREA_ROUTES = N31D + '/urban/control_area_route_contract_v3c3_20261001.json'
URBAN_B1_AREA_ROUTES_SHA256 = 'fdc21f06fcb36f64195e57f51eed189439024c99f157452f8811ab05266a6da1'
URBAN_B1_AREA_ROUTES_PROVENANCE = N31D + '/urban/control_area_route_contract_v3c3_20261001.provenance.json'
URBAN_B1_AREA_ROUTES_PROVENANCE_SHA256 = 'f912429ded82c7161d9969181afd9d0ca1fb0b0c69559c91402fce1f692d39c5'
URBAN_B1_ROUTE_EVIDENCE = N31D + '/urban/route_queue_attribution_v3c3_20261001.json'
URBAN_B1_ROUTE_EVIDENCE_SHA256 = '181a452a967d8e37516a18a8300b02e87dabbeb4b017380930cc2fc3886be1ae'
URBAN_B1_UNSIGNALIZED = N31D + '/urban/unsignalized_turns_v3c3_20261001.json'
URBAN_B1_UNSIGNALIZED_SHA256 = '43247697899a156ad6d078349cf32a3fa2180f0cef922e876fbeaf428ebafa16'
URBAN_B1_UNSIGNALIZED_VALIDATION = N31D + '/urban/unsignalized_validation_v3c3nc_20261001.json'
URBAN_B1_UNSIGNALIZED_VALIDATION_SHA256 = 'd8718b9db9e924f148c91da3aed45d71881f0ad488d81f48a4bbb60381298504'
URBAN_B1_OFFRAMP_PRIOR = N31D + '/urban/offramp_static_route_prior_v3c3_20261001.json'
URBAN_B1_OFFRAMP_PRIOR_SHA256 = 'c2ef5b0fb0379fb827ca7c3899ebf6713b69ef4d232525e01b198a08392cfec7'
OUT_URBAN_B1 = HERE / 'config_n31_v2_urban_b1.json'
# The adapter's former code default of urban.ramp.offramp_direct_share (install_offramp_direct_landing), lifted
# into the config unchanged. The relFlow value per off-ramp group (URBAN_B1_OFFRAMP_PRIOR: OR_D_W 0.5, OR_D_E 0.8,
# OR_F_W 0.75, OR_F_E 2/3) enters only with the batch-1 candidate, through offramp_direct_route_prior.
OFFRAMP_DIRECT_SHARE = {'SC1001': 0.468, 'SC1004': 0.484}
OLD_PACK = 'diagnostics/lane_plant_20260921/scenario/'
NEW_PACK = N31D + '/scenario/'
# The VSL COMMAND set (user approval 2026-09-28: 80..110, the range N1 measured; 50..110 of 2026-09-24 before, the first
# 60/80/110 before that) = repin_scenario_v2.VSL_COMMANDS = make_reference_config.VSL_SET.
VSL_SET = [80.0, 90.0, 100.0, 110.0]
# Command -> written desired-speed distribution (user decision 2026-10-01, single-value VSL compliance; plan REPIN_V3C2
# 3.5 U3-a): the action CSV writes command c as distribution M(c) (vissim_stackelberg_adapter writer, K5); the runner
# allow-list is the image 81,91,101,110 (repin_scenario_v2.VSL_FAMILIES['single_value']). The distribution family has
# no map (identity, runner 80,90,100,110): --vsl-family distribution.
VSL_COMMAND_DISTRIBUTION = {'model': 'single_value', 'distribution_by_command': {'80': 81, '90': 91, '100': 101, '110': 110}}
VSL_FAMILIES = ('single_value', 'distribution')
VSL_FAMILY = 'single_value'
V_FREE = 110.0
# Ramp-arrival forecast per physical meter. The adapter turns connector occupancy into arrivals as
# count * 3600 / drain_sec, clipped at max_vph (vissim_stackelberg_adapter.py:9373-9412), and looks the
# two tables up by the runtime ramp keys. With physical ramp branches those keys are the mapping's
# ramp_meters ids RM_C<connector> (physical_ramp_branches.py:139), but OBS1 still keys both tables by the
# legacy groups R_D_W/R_F_W/R_D_E/R_F_E, so every lookup fell back to 120 s / 900 veh/h.
# Values: network v3c3 NC fit seeds s31/s41/s43/s47 (3de889f0 / 726af589 / 51478c39 / 1895ca30) and the v3c2 NC s53 run
# (c2dd1a48, declared substitute; extract_observations.py into metanet_calibration_v1/v3c3_nc_20261001; s37 held out),
# boundaries_30s.csv per meter (the 2026-08-30 method of scripts/calibrate_ramp_arrival_20260830.py, per meter instead
# of per group):
#   drain_sec = mean snapshot count on the connector * 3600 / merges per hour, 900-5400 s, 5 seeds pooled
#               (Little's law)
#   max_vph   = 1.15 x the highest per-seed mean merge rate over 900-5400 s (the 08-30 cap rule)
# The v3c1 (2577209b, NC fit seeds 31/41/43/47/53) derivation gave drain 16.0/43.6/30.2/88.5/40.8/159.6/33.4/44.4 s,
# cap 220/2347/408/545/551/1248/843/592 veh/h. The v3b (be0075bf, NC s31/s41/s37) derivation gave drain
# 17.4/43.3/30.9/88.0/42.6/161.7/33.3/43.3 s, cap 219/2312/405/514/526/1216/839/611 veh/h. The v2 (f475ce42) derivation gave drain 16.6/43.4/30.2/88.0/42.9/160.7/34.6/47.7 s, cap 277/2310/413/514/
# 526/1217/819/686 veh/h (same meter order as below); the seed-CV figures (<= 0.092 population / 0.113
# sample, both at 10480; 10681 by 900 s block 84/171/176/183/177 s) and the V5b replay below are v2 numbers.
# Replayed on the V5b decisions (T = 2700/3000/3300, all meters open), the summed forecast against the
# VISSIM arrivals over T..T+450 s went from 0.53-0.57 (FW_W 0.46-0.51, FW_E 0.56-0.69) to 0.93-1.09;
# the summed-ratio gain comes mostly from the drain horizon (drain only: 0.88-0.93, cap only: 0.60-0.63),
# while the per-meter |error| drops only with both (2938-2996 -> 453-806 veh/h); 15 of the 24 meter-times
# sit on the cap (1.15 x NC mean merge). A meter that actually holds vehicles is not yet validated.
# NETWORK-SPECIFIC: every value below comes from the pinned network's (v3c3 3de889f0) no-control runs. A
# network change re-runs its no-control seeds, re-extracts them, re-points derive_ramp_forecast_n31.py
# (OBS, FOLDERS, INPUTS) and re-derives. Derivation: derive_ramp_forecast_n31.py.
RAMP_FORECAST = {
    'queue_drain_horizon_sec_by_ramp': {
        'RM_C10480': 17.4, 'RM_C10482': 43.0, 'RM_C10646': 31.1, 'RM_C10644': 88.4,
        'RM_C10639': 38.6, 'RM_C10681': 154.3, 'RM_C10490': 33.1, 'RM_C10484': 44.6},
    'max_vph_by_ramp': {
        'RM_C10480': 220.0, 'RM_C10482': 2353.0, 'RM_C10646': 413.0, 'RM_C10644': 545.0,
        'RM_C10639': 551.0, 'RM_C10681': 1262.0, 'RM_C10490': 850.0, 'RM_C10484': 600.0},
}
LEGACY_RAMP_GROUPS = {'R_D_W', 'R_F_W', 'R_D_E', 'R_F_E'}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def strings(node, trail=''):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from strings(v, trail + '.' + str(k) if trail else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from strings(v, '%s[%d]' % (trail, i))
    elif isinstance(node, str):
        yield trail, node


def _set(document, dotted, value, *, must_exist=True):
    keys = dotted.split('.')
    node = document
    for key in keys[:-1]:
        if key not in node or not isinstance(node[key], dict):
            raise KeyError('Base tuning lacks ' + dotted)
        node = node[key]
    if must_exist and keys[-1] not in node:
        raise KeyError('Base tuning lacks ' + dotted)
    node[keys[-1]] = value


def apply(base, *, network_sha256=NETWORK_SHA256, require_repinned=True, family=VSL_FAMILY):
    """Pure: the plan C9 differences on a flattened base tuning (family single_value adds the command map)."""
    if not isinstance(base, dict) or 'extends' in base:
        raise ValueError('C9 needs the flattened base tuning (no extends)')
    doc = copy.deepcopy(base)
    stale = [(key, value) for key, value in strings(doc) if OLD_PACK in value]
    if require_repinned and stale:
        raise ValueError('Base tuning still names the fcb349d3 pack: ' + ', '.join(k for k, _ in stale[:6]))
    _set(doc, 'freeway.lane_plant', PLANT)
    _set(doc, 'freeway.segment_params', SEGMENT_PARAMS)
    head = doc['urban']['capacity']['head_observation']
    head.pop('sample_interval_sec', None)
    if head.get('enabled') is not True:
        raise ValueError('v2 keeps urban.capacity.head_observation enabled')
    _set(doc, 'config_overrides.freeway_follower.vsl_set', list(VSL_SET))
    _set(doc, 'config_overrides.network.v_free', V_FREE)
    _set(doc, '_canonical.fd_fit_20260828.values.v_free', V_FREE)
    _set(doc, 'execution.native_signal_record', False)
    _set(doc, 'execution.signal_vbs_config', RUNNER_CONFIG)
    _set(doc, 'observation.physical_branch_projection.source.network',
         {'path': NETWORK, 'sha256': network_sha256})
    forecast = doc['calibration_override']['prediction']['local_ramp_arrival_forecast']
    for key, table in RAMP_FORECAST.items():
        if set(forecast.get(key, ())) != LEGACY_RAMP_GROUPS:
            raise ValueError('Base local_ramp_arrival_forecast.%s is not the legacy group table' % key)
        forecast[key] = dict(table)
    forecast['strict_ramp_keys'] = True    # adapter refuses a table whose keys differ from the runtime ramps
    beta = doc['urban']['beta']
    if beta.get('measured') is not True or 'source' in beta:
        raise ValueError('Base urban.beta must be measured with the default source')
    beta['source'] = BETA_SOURCE
    ramp = doc['urban']['ramp']
    if ramp.get('offramp_direct') is not True or 'offramp_direct_share' in ramp:
        raise ValueError('Base urban.ramp must enable offramp_direct with the code-default share')
    ramp['offramp_direct_share'] = dict(OFFRAMP_DIRECT_SHARE)
    if family not in VSL_FAMILIES:
        raise ValueError('Unknown VSL family %r' % (family,))
    actuation = doc['actuation']
    if 'vsl_command_distribution' in actuation:
        raise ValueError('Base actuation already carries vsl_command_distribution')
    if family == 'single_value':
        actuation['vsl_command_distribution'] = copy.deepcopy(VSL_COMMAND_DISTRIBUTION)
    vsl = ('vsl_set [80,90,100,110] (commands) written as the single-value distributions 81/91/101/110 '
           '(actuation.vsl_command_distribution; plant law L2, runner 81,91,101,110; user decision 2026-10-01)'
           if family == 'single_value' else
           'vsl_set [80,90,100,110] written as themselves (VSL family distribution: plant law N1 L1, runner '
           '80,90,100,110; a generator overlay, not the tree)')
    doc['_n31_note'] = ('SDMPC-31 v2 tuning (plan C9) on network v3c3 3de889f0 (user approval 2026-10-01): ' + BASE
                        + ' plus lane_plant v2, b110 segment_params, no head sample interval, ' + vsl + ', v_free 110, '
                        'native_signal_record false, lane_native_b110.vbs, the branch-projection network v3c3, the '
                        'ramp-arrival forecast keyed by RM_C meter (v3c3 NC fit seeds 31/41/43/47 + the v3c2 s53 run) and '
                        'the v3c3 routing beta (urban.beta.source routing_v3c3). The b110 segment_params and boundary fit '
                        'are v2 priors fitted on v2 NC s31 (f475ce42), not refit on v3c3. Generated by make_config_n31.py.')
    return doc


URBAN_B1_COMPONENTS = ('U1', 'U2', 'U3')


def apply_urban_batch1(doc, components=URBAN_B1_COMPONENTS):
    """Pure: an urban plant batch-1 candidate on top of the default C9 tuning. U1 (the complete routing beta, its
    table pin and the relFlow off-ramp direct share) is the base of every variant; U2 (route queue attribution) and
    U3 (unsignalized turns) are added when named."""
    components = tuple(components)
    if 'U1' not in components or set(components) - set(URBAN_B1_COMPONENTS) or len(set(components)) != len(components):
        raise ValueError('Urban batch 1 components must include U1 and be among %s: %r' % (URBAN_B1_COMPONENTS, components))
    components = tuple(c for c in URBAN_B1_COMPONENTS if c in components)
    out = copy.deepcopy(doc)
    urban = out['urban']
    if urban['beta'].get('source') != BETA_SOURCE or 'sha256' in urban['beta']:
        raise ValueError('Urban batch 1 starts from the default %s tuning' % BETA_SOURCE)
    for key in ('attribution', 'route_evidence'):
        if key in urban['queue']:
            raise ValueError('Urban batch 1 expects no urban.queue.%s in the default tuning' % key)
    if ('unsignalized_evidence' in urban['movements'] or 'offramp_direct_route_prior' in urban['ramp']
            or 'nonexistent_declaration' in urban['movements']):
        raise ValueError('Urban batch 1 keys are already present in the default tuning')
    if urban['movements'].get('dead_phase_beta_zero') is not False:
        # it judges declared phases before the phase authority; the adapter refuses it with a complete source
        raise ValueError('Urban batch 1 (complete routing beta) requires urban.movements.dead_phase_beta_zero false')
    if urban['movements'].get('physical_phase_authority') != URBAN_B1_PHASE_AUTHORITY_BASE:
        raise ValueError('Urban batch 1 extends the phase authority %s, the default tuning names %r'
                         % (URBAN_B1_PHASE_AUTHORITY_BASE, urban['movements'].get('physical_phase_authority')))
    area = out['control_area_objective']
    if area.get('route_contract_path') != URBAN_B1_AREA_ROUTES_BASE:
        raise ValueError('Urban batch 1 extends the area route contract %s, the default tuning names %r'
                         % (URBAN_B1_AREA_ROUTES_BASE, area.get('route_contract_path')))
    urban['beta']['source'] = URBAN_B1_BETA_SOURCE
    urban['beta']['sha256'] = URBAN_B1_BETA_SHA256
    urban['movements']['physical_phase_authority'] = URBAN_B1_PHASE_AUTHORITY
    urban['movements']['nonexistent_declaration'] = {'path': URBAN_B1_DECLARATION, 'sha256': URBAN_B1_DECLARATION_SHA256}
    area['route_contract_path'] = URBAN_B1_AREA_ROUTES
    urban['ramp']['offramp_direct_route_prior'] = URBAN_B1_OFFRAMP_PRIOR
    if 'U2' in components:
        urban['queue']['attribution'] = 'route'
        urban['queue']['route_evidence'] = {'path': URBAN_B1_ROUTE_EVIDENCE, 'sha256': URBAN_B1_ROUTE_EVIDENCE_SHA256}
    if 'U3' in components:
        urban['movements']['unsignalized_evidence'] = {'path': URBAN_B1_UNSIGNALIZED, 'sha256': URBAN_B1_UNSIGNALIZED_SHA256}
    parts = {'U1': ('U1 urban.beta.source routing_v3c3_2 pinned by urban.beta.sha256 (every runtime movement: 0 without a '
                    'physical path, else static-route relFlow; approach sums exactly 1 before renormalisation), the '
                    'movement declaration (urban.movements.nonexistent_declaration) with the phase authority that serves '
                    'SC7 E / E_SC16 -> N_SC11 (10332, relFlow 0.429) in their head\'s phase p4 '
                    '(urban.movements.physical_phase_authority) and the area route of the departing one '
                    '(control_area_objective.route_contract_path), and the relFlow off-ramp direct share per group '
                    '(urban.ramp.offramp_direct_route_prior).'),
             'U2': ('U2 urban.queue.attribution route (vehicle route -> route end / diverging -> storage -> lane -> beta; '
                    'off_ramp movements receive no stop-line queue).'),
             'U3': ('U3 urban.movements.unsignalized_evidence (head-free exclusive-lane turns, FZP-validated; they leave '
                    'the head lane-group capacity split).')}
    out['_n31_urban_b1_note'] = (
        'CANDIDATE, not the default: urban plant batch 1 (%s, 2026-09-26) on config_n31_v2.json. ' % ' + '.join(components)
        + ' '.join(parts[c] for c in components)
        + ' Generated by make_config_n31.py --urban-batch1%s.' % (
            '' if components == URBAN_B1_COMPONENTS else ' --components ' + ','.join(components)))
    return out


def check_urban_batch1(root):
    """Every batch-1 input matches its pin and the adapter resolves the new beta source to the pinned file."""
    from evaluation.controllers.vissim_stackelberg_adapter import BETA_EVIDENCE_JSON
    if Path(BETA_EVIDENCE_JSON[URBAN_B1_BETA_SOURCE]).resolve() != (root / URBAN_B1_BETA_FILE).resolve():
        raise ValueError('Adapter beta source %s is not %s' % (URBAN_B1_BETA_SOURCE, URBAN_B1_BETA_FILE))
    for rel, pin in ((URBAN_B1_BETA_FILE, URBAN_B1_BETA_SHA256), (URBAN_B1_ENTRY, URBAN_B1_ENTRY_SHA256),
                     (URBAN_B1_DECLARATION, URBAN_B1_DECLARATION_SHA256),
                     (URBAN_B1_PHASE_AUTHORITY, URBAN_B1_PHASE_AUTHORITY_SHA256),
                     (URBAN_B1_AREA_ROUTES, URBAN_B1_AREA_ROUTES_SHA256),
                     (URBAN_B1_AREA_ROUTES_PROVENANCE, URBAN_B1_AREA_ROUTES_PROVENANCE_SHA256),
                     (URBAN_B1_ROUTE_EVIDENCE, URBAN_B1_ROUTE_EVIDENCE_SHA256),
                     (URBAN_B1_UNSIGNALIZED, URBAN_B1_UNSIGNALIZED_SHA256),
                     (URBAN_B1_UNSIGNALIZED_VALIDATION, URBAN_B1_UNSIGNALIZED_VALIDATION_SHA256),
                     (URBAN_B1_OFFRAMP_PRIOR, URBAN_B1_OFFRAMP_PRIOR_SHA256)):
        if sha256(root / rel) != pin:
            raise ValueError('%s differs from its pin %s' % (rel, pin[:8]))
    beta = json.loads((root / URBAN_B1_BETA_FILE).read_text(encoding='utf-8'))
    if beta['inputs']['network']['sha256'] != NETWORK_SHA256 or beta['inputs']['entry']['sha256'] != URBAN_B1_ENTRY_SHA256:
        raise ValueError('%s was derived from another network or entry table' % URBAN_B1_BETA_SOURCE)
    if (beta['inputs']['nonexistent_declaration'] != {'path': URBAN_B1_DECLARATION, 'sha256': URBAN_B1_DECLARATION_SHA256}
            or beta['inputs']['phase_authority'] != {'path': URBAN_B1_PHASE_AUTHORITY,
                                                     'sha256': URBAN_B1_PHASE_AUTHORITY_SHA256}):
        raise ValueError('%s was derived from another movement declaration or phase authority' % URBAN_B1_BETA_SOURCE)
    authority = json.loads((root / URBAN_B1_PHASE_AUTHORITY).read_text(encoding='utf-8'))['v3b_corrections']
    if (authority['base'] != {'path': URBAN_B1_PHASE_AUTHORITY_BASE, 'sha256': sha256(root / URBAN_B1_PHASE_AUTHORITY_BASE)}
            or authority['declaration'] != {'path': URBAN_B1_DECLARATION, 'sha256': URBAN_B1_DECLARATION_SHA256}):
        raise ValueError('the batch-1 phase authority extends another base or declaration')
    routes = json.loads((root / URBAN_B1_AREA_ROUTES_PROVENANCE).read_text(encoding='utf-8'))
    if (routes['base'] != {'path': URBAN_B1_AREA_ROUTES_BASE, 'sha256': sha256(root / URBAN_B1_AREA_ROUTES_BASE)}
            or routes['inputs']['phase_authority'] != {'path': URBAN_B1_PHASE_AUTHORITY,
                                                       'sha256': URBAN_B1_PHASE_AUTHORITY_SHA256}
            or routes['inputs']['declaration'] != {'path': URBAN_B1_DECLARATION, 'sha256': URBAN_B1_DECLARATION_SHA256}):
        raise ValueError('the batch-1 area route contract extends another base, declaration or phase authority')
    for rel in (URBAN_B1_ROUTE_EVIDENCE, URBAN_B1_UNSIGNALIZED):
        document = json.loads((root / rel).read_text(encoding='utf-8'))
        if document['inputs']['beta']['sha256'] != URBAN_B1_BETA_SHA256:
            raise ValueError('%s was derived from another %s table' % (rel, URBAN_B1_BETA_SOURCE))
    from evaluation.controllers.offramp_routing import derive_prior
    derive_prior(json.loads((root / URBAN_B1_OFFRAMP_PRIOR).read_text(encoding='utf-8')))


def check_ramp_keys(root, doc):
    """The forecast tables name exactly the mapping's physical meters (the runtime ramp keys)."""
    mapping = json.loads((root / doc['mapping_json']).read_text(encoding='utf-8-sig'))
    meters = {str(m['id']) for m in mapping['ramp_meters']}
    forecast = doc['calibration_override']['prediction']['local_ramp_arrival_forecast']
    for key in RAMP_FORECAST:
        if set(forecast[key]) != meters:
            raise ValueError('local_ramp_arrival_forecast.%s keys differ from the ramp meters' % key)


def check_beta(root):
    """The adapter resolves BETA_SOURCE to BETA_FILE, that file is the pinned derivation from the pinned network, and
    it was derived with the pinned explicit-approach table."""
    from evaluation.controllers.vissim_stackelberg_adapter import BETA_EVIDENCE_JSON
    if Path(BETA_EVIDENCE_JSON[BETA_SOURCE]).resolve() != (root / BETA_FILE).resolve():
        raise ValueError('Adapter beta source %s is not %s' % (BETA_SOURCE, BETA_FILE))
    for rel, pin in ((BETA_FILE, BETA_SHA256), (BETA_EXPLICIT, BETA_EXPLICIT_SHA256)):
        if sha256(root / rel) != pin:
            raise ValueError('%s differs from its pin %s' % (rel, pin[:8]))
    document = json.loads((root / BETA_FILE).read_text(encoding='utf-8'))
    if str(document.get('source', '')).replace('\\', '/') != NETWORK:
        raise ValueError('Routing beta was derived from another network: %r' % document.get('source'))
    if document.get('explicit_approach', {}).get('sha256') != BETA_EXPLICIT_SHA256:
        raise ValueError('Routing beta was not derived with the pinned explicit-approach table')


def check_pack(root, doc):
    """Every pack path lives under N31D/scenario and exists; the one inline sha pin holds."""
    paths = [(k, v) for k, v in strings(doc) if v.startswith(NEW_PACK)]
    if not paths:
        raise ValueError('No re-pinned N31D scenario pack paths in the base tuning')
    missing = [v for _, v in paths if not (root / v).is_file()]
    if missing:
        raise FileNotFoundError('Re-pinned pack files missing: ' + ', '.join(missing))
    evidence = doc['urban']['known_wout_route_evidence']
    if sha256(root / evidence['path']) != evidence['sha256']:
        raise ValueError('known_wout_route_evidence sha differs from its file')
    return [v for _, v in paths]


class Overlay:
    """root / rel, but a repo-relative file present in the VSL family overlay folder is read from there (V-11)."""

    def __init__(self, root, overlay=None):
        self.root, self.overlay = Path(root), (Path(overlay) if overlay is not None else None)

    def __truediv__(self, rel):
        if self.overlay is not None and (self.overlay / rel).is_file():
            return self.overlay / rel
        return self.root / rel


def build(root=ROOT, *, family=VSL_FAMILY, overlay=None):
    from evaluation.controllers import obs150_contract as oc
    tree = Path(root)
    files = Overlay(tree, overlay)
    for rel in (BASE, PLANT, SEGMENT_PARAMS, RUNNER_CONFIG, NETWORK, BETA_FILE, BETA_EXPLICIT):
        if not (files / rel).is_file():
            raise FileNotFoundError('config_n31_v2 input missing (owner package pending): ' + rel)
    if sha256(tree / NETWORK) != NETWORK_SHA256:
        raise ValueError('network copy differs from ' + NETWORK_LABEL)
    check_beta(tree)
    base = json.loads((tree / BASE).read_text(encoding='utf-8-sig'))
    doc = apply(base, family=family)
    check_pack(tree, doc)
    check_ramp_keys(tree, doc)
    plant = json.loads((files / PLANT).read_text(encoding='utf-8-sig'))
    oc.validate_tuning_v2(doc, plant)
    # V-9 (repin plan 2026-10-01 K5): the generated map/vsl_set, the plant law and the runner list agree.
    from evaluation.controllers import vsl_command_distribution
    family_record = vsl_command_distribution.check_family_files(doc, files / plant['sources']['reference_config']['path'],
                                                                files / plant['sources']['runner_config']['path'])
    if family_record['family'] != family:
        raise ValueError('Generated VSL family %s differs from the requested %s' % (family_record['family'], family))
    if plant['membership']['path'] != doc['control_area_objective']['membership_path']:
        raise ValueError('Plant and tuning name different area memberships')
    return doc


def dumps(doc):
    return (json.dumps(doc, indent=2, ensure_ascii=False) + '\n').encode('utf-8')


def urban_batch1_out(components=URBAN_B1_COMPONENTS, overlay=None):
    """config_n31_v2_urban_b1.json for U1 + U2 + U3, config_n31_v2_urban_b1_<u1u3...>.json for a named subset."""
    components = tuple(c for c in URBAN_B1_COMPONENTS if c in components)
    out = OUT_URBAN_B1 if components == URBAN_B1_COMPONENTS else HERE / (
        'config_n31_v2_urban_b1_%s.json' % ''.join(c.lower() for c in components))
    return out if overlay is None else Path(overlay) / out.relative_to(ROOT)


def build_urban_batch1(root=ROOT, components=URBAN_B1_COMPONENTS, *, family=VSL_FAMILY, overlay=None):
    from evaluation.controllers import obs150_contract as oc
    check_urban_batch1(Path(root))
    doc = apply_urban_batch1(build(root, family=family, overlay=overlay), components)
    plant = json.loads((Overlay(root, overlay) / PLANT).read_text(encoding='utf-8-sig'))
    oc.validate_tuning_v2(doc, plant)
    return doc


def family_root(family, out_root):
    """None for the live family in the tree; the resolved overlay folder (outside the tree) otherwise."""
    if out_root is None:
        if family != VSL_FAMILY:
            raise SystemExit('--vsl-family %s writes only with --out-root (the tree holds the %s family)' % (family, VSL_FAMILY))
        return None
    folder = Path(out_root).resolve()
    if folder.is_relative_to(ROOT.resolve()):
        raise SystemExit('--out-root must lie outside the tree: ' + str(folder))
    return folder


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--urban-batch1', action='store_true',
                        help='write the separate urban batch-1 candidate config_n31_v2_urban_b1.json instead')
    parser.add_argument('--components', default=','.join(URBAN_B1_COMPONENTS),
                        help='with --urban-batch1: the batch-1 items (U1 always), e.g. U1,U3 -> config_n31_v2_urban_b1_u1u3.json')
    parser.add_argument('--vsl-family', choices=VSL_FAMILIES, default=VSL_FAMILY)
    parser.add_argument('--out-root', help='VSL family overlay folder (outside the tree): read its family files, write there')
    args = parser.parse_args()
    components = tuple(c.strip().upper() for c in args.components.split(',') if c.strip())
    overlay = family_root(args.vsl_family, args.out_root)
    if args.urban_batch1:
        out, name = urban_batch1_out(components, overlay), 'CONFIG_N31_URBAN_B1_OK'
        data = dumps(build_urban_batch1(components=components, family=args.vsl_family, overlay=overlay))
    else:
        out, name = (OUT if overlay is None else overlay / OUT.relative_to(ROOT)), 'CONFIG_N31_OK'
        data = dumps(build(family=args.vsl_family, overlay=overlay))
    if args.check:
        if out.read_bytes() != data:
            raise SystemExit('%s differs from its generator' % out.name)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    if overlay is None:
        done = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/preflight_tuning_paths.py'), str(out), '--quiet'],
                              cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if done.returncode:
            raise SystemExit('preflight_tuning_paths failed:\n' + done.stdout + done.stderr)
    # (an overlay tuning names repo-relative files that resolve in the overlay; the tree preflight would read the
    # live family's files instead, so it runs only for the tree)
    print(name + ' family=' + args.vsl_family + ' sha256=' + hashlib.sha256(data).hexdigest())


if __name__ == '__main__':
    main()
