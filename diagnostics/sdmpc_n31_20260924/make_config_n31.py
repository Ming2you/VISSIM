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
    doc['_n31_note'] = ('SDMPC-31 v2 tuning (plan C9) on network v3b be0075bf (user decision 2026-09-25): ' + BASE
                        + ' plus lane_plant v2, b110 segment_params, no head sample interval, vsl_set '
                        '[50,60,70,80,90,100,110], v_free 110, native_signal_record false, lane_native_b110.vbs, the '
                        'branch-projection network v3b, the ramp-arrival forecast keyed by RM_C meter (v3b NC) and the '
                        'v3b routing beta (urban.beta.source routing_v3b). The b110 segment_params and boundary fit are '
                        'v2 priors fitted on v2 NC s31 (f475ce42), not refit on v3b. Generated by make_config_n31.py.')
    return doc


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


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = dumps(build())
    if args.check:
        if OUT.read_bytes() != data:
            raise SystemExit('config_n31_v2.json differs from its generator')
    else:
        OUT.write_bytes(data)
    done = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/preflight_tuning_paths.py'), str(OUT), '--quiet'],
                          cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if done.returncode:
        raise SystemExit('preflight_tuning_paths failed:\n' + done.stdout + done.stderr)
    print('CONFIG_N31_OK sha256=' + hashlib.sha256(data).hexdigest())


if __name__ == '__main__':
    main()
