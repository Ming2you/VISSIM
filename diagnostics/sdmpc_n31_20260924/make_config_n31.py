"""C9: config_n31_v2.json = the WP-E base tuning plus the v2 plant differences.

The base (N31D/scenario/config_n31_v2.base.json, written by repin_scenario_v2.py) is OBS1
with the scenario pack re-pinned to the runtime network (v3b since 2026-09-25). This script adds exactly the
plan C9 differences and nothing else:

  freeway.lane_plant                                  -> plant_n31_v2.json          (OBS1:8082)
  freeway.segment_params                              -> C1 b110 21-row copy        (NEW-10)
  urban.capacity.head_observation.sample_interval_sec    deleted                    (OBS1:7831)
  config_overrides.freeway_follower.vsl_set           -> [50, 60, ..., 110] step 10 (OBS1:7466)
  config_overrides.network.v_free                     -> 110                        (OBS1:7433)
  _canonical.fd_fit_20260828.values.v_free            -> 110                        (OBS1:7961, record only)
  execution.native_signal_record                      -> false                      (NEW-2)
  execution.signal_vbs_config                         -> N31D/scenario/lane_native_b110.vbs
  observation.physical_branch_projection.source.network -> the pinned network (v3b) (OBS1:8109-8113)
  calibration_override.prediction.local_ramp_arrival_forecast
      .queue_drain_horizon_sec_by_ramp, .max_vph_by_ramp -> keyed by the eight RM_C meters (RAMP_FORECAST)
      .strict_ramp_keys                                  -> true (no silent 120 s / 900 veh/h fallback)
  urban.beta.source                                   -> routing_v3b (BETA_SOURCE: the routing beta of the pinned
                                                         network v3b, N31D/beta/; OBS1 used the 0824 e14 table)
  urban.ramp.offramp_direct_share                     -> {SC1001: 0.468, SC1004: 0.484}, the adapter's former code
                                                         default made explicit (install_offramp_direct_landing); the
                                                         runtime is unchanged

Urban plant batch 1 (U1 + U2 + U3, 2026-09-25/26) is a SEPARATE candidate, not the default above:
  python -B diagnostics/sdmpc_n31_20260924/make_config_n31.py --urban-batch1 [--components U1,U3] [--check]
writes config_n31_v2_urban_b1.json (all three; config_n31_v2_urban_b1_u1u3.json etc. for a subset, U1 always) =
config_n31_v2.json plus (apply_urban_batch1, URBAN_B1_* pins)
  urban.beta.source / sha256                 -> routing_v3b2 (complete physical routing beta, 492 movements) + pin
  urban.movements.nonexistent_declaration    -> the pinned v3b movement declaration (U1; user decision 2026-09-26:
                                                SC7 E / E_SC16 -> N_SC11 exist on v3b, connector 10332, relFlow 0.429)
  urban.movements.physical_phase_authority   -> the default evidence plus those two rows in their head's phase
                                                (head 140101 = SC7 SG 1 = plan p4; was p3, no green) (U1)
  control_area_objective.route_contract_path -> the default contract plus the departure area route of
                                                SC7_E_SC16_to_N_SC11 (10332, inside -> inside) (U1)
  urban.queue.attribution / route_evidence   -> "route" + the pinned stop-line crossing table
  urban.movements.unsignalized_evidence      -> the pinned head-free exclusive-lane turns (FZP-validated)
  urban.ramp.offramp_direct_route_prior      -> the pinned relFlow direct share per off-ramp group

Network v3b (user decision 2026-09-25): the pinned network is be0075bf; the b110 segment_params (and the plant's
boundary fit) are v2 priors fitted on v2 NC s31 (f475ce42) and are NOT refit; the ramp-arrival forecast and the
routing beta are re-derived on v3b.

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
NETWORK = N31D + '/network/baseline_s31_v3bnc.inpx'
NETWORK_SHA256 = 'be0075bf4d5e9e239ffc1e9efb6d70d11c6ec6136e46f1a92d910bc79d813cdc'   # v3b (was v2 f475ce42)
# Routing beta of the pinned network (adapter BETA_EVIDENCE_JSON['routing_v3b']): scripts/derive_routing_turn_beta.py
# with the 474-movement core17legs4b config (N31D/beta/movements_core17legs4b_20260819.json = git 4898446^ blob) on
# the v3b network. The default 'routing' table (outputs/movement_beta_routing_20260824.json) was derived on network
# modi_eval_userfix_20260814e: 25 movements differ on v2, 48 on v3b (before the explicit assignment below).
# The destination-set inference of that script mis-attaches the interchange decisions (SC1004 1124/1126/1138/1140 all
# on E_SC107, SC1001 1117 dropped as a W/offW/offE tie); BETA_EXPLICIT attaches them to the approaches whose vehicles
# pass them in the v3b NC FZP (--explicit-approach, user decision 2026-09-25). Both files are pinned, because the
# adapter reads BETA_FILE by path. Re-derive (worktree root):
#   python -B scripts/derive_routing_turn_beta.py --network <NETWORK> --movements-config <BETA_MOVEMENTS>
#       --out <BETA_FILE> --generated 2026-09-25 --explicit-approach <BETA_EXPLICIT>
BETA_SOURCE = 'routing_v3b'
BETA_FILE = N31D + '/beta/movement_beta_routing_v3b_20260925.json'
BETA_SHA256 = 'e81d545fce294c0850ed821810bf47a36b042eb25a6e0989b2e14d18db0f1a6d'
BETA_EXPLICIT = N31D + '/beta/explicit_approach_v3b_20260925.json'
BETA_EXPLICIT_SHA256 = '36162d5032b899369e33e6cab5ebad932119587733f0721cabc691d557942c65'
BETA_MOVEMENTS = N31D + '/beta/movements_core17legs4b_20260819.json'
# Urban plant batch 1 (U1/U2/U3, 2026-09-25): pinned inputs of the separate candidate config_n31_v2_urban_b1.json.
# Re-derive (worktree root, in this order; each generator also has --check):
#   python -B scripts/derive_phase_authority_v3b.py --out <URBAN_B1_PHASE_AUTHORITY>
#   python -B scripts/derive_area_routes_v3b.py --out <URBAN_B1_AREA_ROUTES>      (also writes its .provenance.json)
#   python -B scripts/derive_routing_beta_physical.py --out <URBAN_B1_BETA_FILE>
#   python -B scripts/derive_unsignalized_turns.py --out <URBAN_B1_UNSIGNALIZED>
#   python -B scripts/derive_route_queue_attribution.py --out <URBAN_B1_ROUTE_EVIDENCE>
#   python -B scripts/derive_unsignalized_validation.py --out <URBAN_B1_UNSIGNALIZED_VALIDATION>   (reads the three
#       v3b no-control FZPs, about 3.5 GB; the FZP validation table the unsignalized-turn derivation reads)
# The relFlow off-ramp prior (URBAN_B1_OFFRAMP_PRIOR, re-derived by offramp_routing.derive_prior at install) and the v3b
# movement declaration (URBAN_B1_DECLARATION, a reviewed decision record that the two derivations verify against the
# network) are pinned inputs.
URBAN_B1_BETA_SOURCE = 'routing_v3b2'
URBAN_B1_BETA_FILE = N31D + '/beta/movement_beta_routing_v3b2_20260925.json'
URBAN_B1_BETA_SHA256 = '41b3113ff8e64b40175e45e64ae983bd138e80dbdd7f913253627b3db2662cb6'
URBAN_B1_ENTRY = N31D + '/beta/approach_entry_v3b2_20260925.json'
URBAN_B1_ENTRY_SHA256 = '56a1bb3c955e936771bf676fe96a53415e6894a43e6a08aba7415810bc1477b6'
# User decision 2026-09-26 (U1): the runtime's nonexistence declaration of SC7_E_to_N_SC11 / SC7_E_SC16_to_N_SC11 is the
# v2 reading; on v3b 10332 is their right turn (relFlow 63 / 147 = 0.429). The candidates read the v3b declaration and
# serve the two in the phase of their real head (140101, SC7 SG 1 = plan p4) through the extended phase authority
# (the default tuning's URBAN_B1_PHASE_AUTHORITY_BASE plus two rows).
URBAN_B1_DECLARATION = N31D + '/urban/movement_nonexistent_v3b_20260926.json'
URBAN_B1_DECLARATION_SHA256 = '3135dcdaf7b01feb426eb1bb48df15470d31c06934a3f84ebb048df231b61fce'
URBAN_B1_PHASE_AUTHORITY_BASE = N31D + '/scenario/physical_phase_authority_local_1df35c.json'
URBAN_B1_PHASE_AUTHORITY = N31D + '/urban/physical_phase_authority_v3b_20260926.json'
URBAN_B1_PHASE_AUTHORITY_SHA256 = 'e729cdc4ec22414877295bed8ba98c7dc43e14b2202fe7222516fe0ee8c7d907'
# ... and a departing SC7_E_SC16_to_N_SC11 needs its physical area route (the default contract left it 'no_match'):
# scripts/derive_area_routes_v3b.py writes the default contract plus that route (and a .provenance.json sidecar).
URBAN_B1_AREA_ROUTES_BASE = 'diagnostics/control_area_route_contract_physical_routes.json'
URBAN_B1_AREA_ROUTES = N31D + '/urban/control_area_route_contract_v3b_20260926.json'
URBAN_B1_AREA_ROUTES_SHA256 = 'fdc21f06fcb36f64195e57f51eed189439024c99f157452f8811ab05266a6da1'
URBAN_B1_AREA_ROUTES_PROVENANCE = N31D + '/urban/control_area_route_contract_v3b_20260926.provenance.json'
URBAN_B1_AREA_ROUTES_PROVENANCE_SHA256 = 'db5826a103c61bad58381b80c7d7e4d4206f9c54fa7472c78ad0444f071b5f7e'
URBAN_B1_ROUTE_EVIDENCE = N31D + '/urban/route_queue_attribution_v3b_20260925.json'
URBAN_B1_ROUTE_EVIDENCE_SHA256 = 'ec8697a4a24e8fe945edf717e96e78f2416abb4cde3b3dff5ea0cae9c4b155dc'
URBAN_B1_UNSIGNALIZED = N31D + '/urban/unsignalized_turns_v3b_20260925.json'
URBAN_B1_UNSIGNALIZED_SHA256 = '6febd53fcb732c2297fd37497cb3d2e9e47dfaea491ed6d5d9bbd84d477a34cd'
URBAN_B1_UNSIGNALIZED_VALIDATION = N31D + '/urban/unsignalized_validation_v3bnc_20260925.json'
URBAN_B1_UNSIGNALIZED_VALIDATION_SHA256 = 'b5dedf800c8bf11b52a8cc3cfee7ad787f89278e891bdff8a4d603088fdb44b9'
URBAN_B1_OFFRAMP_PRIOR = N31D + '/urban/offramp_static_route_prior_v3b_20260925.json'
URBAN_B1_OFFRAMP_PRIOR_SHA256 = 'd9a4a8f17c0b9e9eb567d60275f177c5152954d71be849fa00f97b84f62733ee'
OUT_URBAN_B1 = HERE / 'config_n31_v2_urban_b1.json'
# The adapter's former code default of urban.ramp.offramp_direct_share (install_offramp_direct_landing), lifted
# into the config unchanged. The relFlow value per off-ramp group (URBAN_B1_OFFRAMP_PRIOR: OR_D_W 0.5, OR_D_E 0.8,
# OR_F_W 0.75, OR_F_E 2/3) enters only with the batch-1 candidate, through offramp_direct_route_prior.
OFFRAMP_DIRECT_SHARE = {'SC1001': 0.468, 'SC1004': 0.484}
OLD_PACK = 'diagnostics/lane_plant_20260921/scenario/'
NEW_PACK = N31D + '/scenario/'
VSL_SET = [50.0, 60.0, 70.0, 80.0, 90.0, 100.0, 110.0]   # user decision 2026-09-24: 10 km/h steps, c_max 110
V_FREE = 110.0
# Ramp-arrival forecast per physical meter. The adapter turns connector occupancy into arrivals as
# count * 3600 / drain_sec, clipped at max_vph (vissim_stackelberg_adapter.py:9373-9412), and looks the
# two tables up by the runtime ramp keys. With physical ramp branches those keys are the mapping's
# ramp_meters ids RM_C<connector> (physical_ramp_branches.py:139), but OBS1 still keys both tables by the
# legacy groups R_D_W/R_F_W/R_D_E/R_F_E, so every lookup fell back to 120 s / 900 veh/h.
# Values: network v3b NC s31/s41/s37 (be0075bf / 261a1fb0 / f5c3d640; extract_observations.py into
# metanet_calibration_v1/v3b_nc_20260925), boundaries_30s.csv per meter (the 2026-08-30
# method of scripts/calibrate_ramp_arrival_20260830.py, per meter instead of per group):
#   drain_sec = mean snapshot count on the connector * 3600 / merges per hour, 900-5400 s, 3 seeds pooled
#               (Little's law)
#   max_vph   = 1.15 x the highest per-seed mean merge rate over 900-5400 s (the 08-30 cap rule)
# The v2 (f475ce42) derivation gave drain 16.6/43.4/30.2/88.0/42.9/160.7/34.6/47.7 s, cap 277/2310/413/514/
# 526/1217/819/686 veh/h (same meter order as below); the seed-CV figures (<= 0.092 population / 0.113
# sample, both at 10480; 10681 by 900 s block 84/171/176/183/177 s) and the V5b replay below are v2 numbers.
# Replayed on the V5b decisions (T = 2700/3000/3300, all meters open), the summed forecast against the
# VISSIM arrivals over T..T+450 s went from 0.53-0.57 (FW_W 0.46-0.51, FW_E 0.56-0.69) to 0.93-1.09;
# the summed-ratio gain comes mostly from the drain horizon (drain only: 0.88-0.93, cap only: 0.60-0.63),
# while the per-meter |error| drops only with both (2938-2996 -> 453-806 veh/h); 15 of the 24 meter-times
# sit on the cap (1.15 x NC mean merge). A meter that actually holds vehicles is not yet validated.
# NETWORK-SPECIFIC: every value below comes from the pinned network's (v3b be0075bf) no-control runs. A
# network change re-runs its no-control seeds, re-extracts them, re-points derive_ramp_forecast_n31.py
# (OBS, PATTERN, INPUTS) and re-derives. Derivation: derive_ramp_forecast_n31.py.
RAMP_FORECAST = {
    'queue_drain_horizon_sec_by_ramp': {
        'RM_C10480': 17.4, 'RM_C10482': 43.3, 'RM_C10646': 30.9, 'RM_C10644': 88.0,
        'RM_C10639': 42.6, 'RM_C10681': 161.7, 'RM_C10490': 33.3, 'RM_C10484': 43.3},
    'max_vph_by_ramp': {
        'RM_C10480': 219.0, 'RM_C10482': 2312.0, 'RM_C10646': 405.0, 'RM_C10644': 514.0,
        'RM_C10639': 526.0, 'RM_C10681': 1216.0, 'RM_C10490': 839.0, 'RM_C10484': 611.0},
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


def apply(base, *, network_sha256=NETWORK_SHA256, require_repinned=True):
    """Pure: the plan C9 differences on a flattened base tuning."""
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
    doc['_n31_note'] = ('SDMPC-31 v2 tuning (plan C9) on network v3b be0075bf (user decision 2026-09-25): ' + BASE
                        + ' plus lane_plant v2, b110 segment_params, no head sample interval, vsl_set '
                        '[50,60,70,80,90,100,110], v_free 110, native_signal_record false, lane_native_b110.vbs, the '
                        'branch-projection network v3b, the ramp-arrival forecast keyed by RM_C meter (v3b NC) and the '
                        'v3b routing beta (urban.beta.source routing_v3b). The b110 segment_params and boundary fit are '
                        'v2 priors fitted on v2 NC s31 (f475ce42), not refit on v3b. Generated by make_config_n31.py.')
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
        raise ValueError('Urban batch 1 starts from the default routing_v3b tuning')
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
    parts = {'U1': ('U1 urban.beta.source routing_v3b2 pinned by urban.beta.sha256 (every runtime movement: 0 without a '
                    'physical path, else static-route relFlow; approach sums exactly 1 before renormalisation), the v3b '
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
        raise ValueError('routing_v3b2 was derived from another network or entry table')
    if (beta['inputs']['nonexistent_declaration'] != {'path': URBAN_B1_DECLARATION, 'sha256': URBAN_B1_DECLARATION_SHA256}
            or beta['inputs']['phase_authority'] != {'path': URBAN_B1_PHASE_AUTHORITY,
                                                     'sha256': URBAN_B1_PHASE_AUTHORITY_SHA256}):
        raise ValueError('routing_v3b2 was derived from another movement declaration or phase authority')
    authority = json.loads((root / URBAN_B1_PHASE_AUTHORITY).read_text(encoding='utf-8'))['v3b_corrections']
    if (authority['base'] != {'path': URBAN_B1_PHASE_AUTHORITY_BASE, 'sha256': sha256(root / URBAN_B1_PHASE_AUTHORITY_BASE)}
            or authority['declaration'] != {'path': URBAN_B1_DECLARATION, 'sha256': URBAN_B1_DECLARATION_SHA256}):
        raise ValueError('the v3b phase authority extends another base or declaration')
    routes = json.loads((root / URBAN_B1_AREA_ROUTES_PROVENANCE).read_text(encoding='utf-8'))
    if (routes['base'] != {'path': URBAN_B1_AREA_ROUTES_BASE, 'sha256': sha256(root / URBAN_B1_AREA_ROUTES_BASE)}
            or routes['inputs']['phase_authority'] != {'path': URBAN_B1_PHASE_AUTHORITY,
                                                       'sha256': URBAN_B1_PHASE_AUTHORITY_SHA256}
            or routes['inputs']['declaration'] != {'path': URBAN_B1_DECLARATION, 'sha256': URBAN_B1_DECLARATION_SHA256}):
        raise ValueError('the v3b area route contract extends another base, declaration or phase authority')
    for rel in (URBAN_B1_ROUTE_EVIDENCE, URBAN_B1_UNSIGNALIZED):
        document = json.loads((root / rel).read_text(encoding='utf-8'))
        if document['inputs']['beta']['sha256'] != URBAN_B1_BETA_SHA256:
            raise ValueError('%s was derived from another routing_v3b2 table' % rel)
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


def build(root=ROOT):
    from evaluation.controllers import obs150_contract as oc
    for rel in (BASE, PLANT, SEGMENT_PARAMS, RUNNER_CONFIG, NETWORK, BETA_FILE, BETA_EXPLICIT):
        if not (root / rel).is_file():
            raise FileNotFoundError('config_n31_v2 input missing (owner package pending): ' + rel)
    if sha256(root / NETWORK) != NETWORK_SHA256:
        raise ValueError('network copy differs from v3b be0075bf')
    check_beta(root)
    base = json.loads((root / BASE).read_text(encoding='utf-8-sig'))
    doc = apply(base)
    check_pack(root, doc)
    check_ramp_keys(root, doc)
    plant = json.loads((root / PLANT).read_text(encoding='utf-8-sig'))
    oc.validate_tuning_v2(doc, plant)
    if plant['membership']['path'] != doc['control_area_objective']['membership_path']:
        raise ValueError('Plant and tuning name different area memberships')
    return doc


def dumps(doc):
    return (json.dumps(doc, indent=2, ensure_ascii=False) + '\n').encode('utf-8')


def urban_batch1_out(components=URBAN_B1_COMPONENTS):
    """config_n31_v2_urban_b1.json for U1 + U2 + U3, config_n31_v2_urban_b1_<u1u3...>.json for a named subset."""
    components = tuple(c for c in URBAN_B1_COMPONENTS if c in components)
    if components == URBAN_B1_COMPONENTS:
        return OUT_URBAN_B1
    return HERE / ('config_n31_v2_urban_b1_%s.json' % ''.join(c.lower() for c in components))


def build_urban_batch1(root=ROOT, components=URBAN_B1_COMPONENTS):
    from evaluation.controllers import obs150_contract as oc
    check_urban_batch1(root)
    doc = apply_urban_batch1(build(root), components)
    plant = json.loads((root / PLANT).read_text(encoding='utf-8-sig'))
    oc.validate_tuning_v2(doc, plant)
    return doc


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--urban-batch1', action='store_true',
                        help='write the separate urban batch-1 candidate config_n31_v2_urban_b1.json instead')
    parser.add_argument('--components', default=','.join(URBAN_B1_COMPONENTS),
                        help='with --urban-batch1: the batch-1 items (U1 always), e.g. U1,U3 -> config_n31_v2_urban_b1_u1u3.json')
    args = parser.parse_args()
    components = tuple(c.strip().upper() for c in args.components.split(',') if c.strip())
    if args.urban_batch1:
        out, name = urban_batch1_out(components), 'CONFIG_N31_URBAN_B1_OK'
        data = dumps(build_urban_batch1(components=components))
    else:
        out, name = OUT, 'CONFIG_N31_OK'
        data = dumps(build())
    if args.check:
        if out.read_bytes() != data:
            raise SystemExit('%s differs from its generator' % out.name)
    else:
        out.write_bytes(data)
    done = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/preflight_tuning_paths.py'), str(out), '--quiet'],
                          cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if done.returncode:
        raise SystemExit('preflight_tuning_paths failed:\n' + done.stdout + done.stderr)
    print(name + ' sha256=' + hashlib.sha256(data).hexdigest())


if __name__ == '__main__':
    main()
