"""C8: plant_n31_v2.json, the coupled-lane-plant/v2 manifest (plan C8, contract 1.1).

Every source is a {path, sha256} pin computed from the bytes in this worktree;
nothing is copied or edited here. Inputs owned by other packages must exist
first, and the generator fails listing whatever is missing:

  network, sig_manifest            WP-E  N31D/network/ (byte copy of NET, .sig table)
  runner_config                    WP-E  N31D/scenario/lane_native_b110.vbs
  membership                       WP-E  the re-pinned pack entry named by the E base
                                         config's control_area_objective.membership_path
  observation.detectors            WP-B2 N31D/obs150/obs150_detectors_v2.csv
  geometry                         the runtime network's own no-control s31 extraction (v3b since
                                         2026-09-25: metanet_calibration_v1/v3b_nc_20260925, extract_observations.py)
  parameters                       WP-C  C1 b110 copy (copy_b110.py): v2 prior, fitted on v2 NC s31 f475ce42
  refined_partition                tracked geometry_200_branch_guard.json (9769b3a4)
  reference_config                 WP-C  C7 reference_config_n31_v2.json
  port_profile                     WP-C  C12 port_profile_v2/port_profile.json
  reference_protocol, off_groups   unchanged v1 plant entries

Cross checks: the C1 geometry was extracted from the pinned network and refined
by the pinned partition; parameters.json equals its freeze pin; the detector
CSV is canonical (obs150_contract.read_detector_csv); the result passes
validate_plant_manifest_v2.

Run from the worktree root:
  python -B diagnostics/sdmpc_n31_20260924/make_plant_n31.py [--check]
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

N31D = 'diagnostics/sdmpc_n31_20260924'
B110 = 'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/res10_b110_20260923'
TRANSPORT = 'diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/transport_step1_exchange_off_v2'
# Network v3b (user decision 2026-09-25): its no-control runs s31/s41/s37, extracted with extract_observations.py.
V3B_NC = 'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/v3b_nc_20260925'
SOURCES = {
    'network': N31D + '/network/baseline_s31_v3bnc.inpx',
    'geometry': V3B_NC + '/observations/s31_v3bnc_observations/geometry.json',
    'refined_partition': 'diagnostics/demand_sweep/ramp_dsd_20260916_v2/segment_resolution_20260921/geometry_200_branch_guard.json',
    'reference_config': N31D + '/reference_config_n31_v2.json',
    'parameters': B110 + '/train_s31_v2nc/boundary_literature_v1/boundary_fit/parameters.json',
    'port_profile': N31D + '/port_profile_v2/port_profile.json',
    'reference_protocol': TRANSPORT + '/protocol.json',
    'runner_config': N31D + '/scenario/lane_native_b110.vbs',
    'sig_manifest': N31D + '/network/sig_manifest.json',
}
FREEZE = B110 + '/train_s31_v2nc/boundary_literature_v1/boundary_fit/freeze.json'
OFF_GROUPS = 'diagnostics/control_improvement/decision_common_anchor_20260911/ramp8_physical_v1/offramp_route_inventory_v1.json'
DETECTORS = N31D + '/obs150/obs150_detectors_v2.csv'
BASE_CONFIG = N31D + '/scenario/config_n31_v2.base.json'
OUT = HERE / 'plant_n31_v2.json'
NETWORK_SHA256 = 'be0075bf4d5e9e239ffc1e9efb6d70d11c6ec6136e46f1a92d910bc79d813cdc'   # v3b (was v2 f475ce42)
QUALIFICATION = ('NOT_QUALIFIED: network v3b be0075bf (differs from v2 f475ce42 only in static routes: 19 route '
                 'destinations, 1061 pos, 32 relFlows; user decision 2026-09-25); the b110 segment_params, boundary fit '
                 'and boundary_config are v2 priors fitted on v2 NC s31 (f475ce42), not refit on v3b; geometry, port '
                 'profile and ramp-arrival forecast re-derived from the v3b NC runs; '
                 '31-cell b110 boundary family with the baseline FD (no FD refit); held-out '
                 'history_forecast speed RMSE FW_E 20-25 / FW_W 13-17 km/h (v2 NC, not re-scored on v3b); scenario pack priors carried over from '
                 'fcb349d3 with prior_mismatch receipts (D-B); obs150 observation integrated and verified offline '
                 'only (probe V0 + V1 code tests), not yet against native ground truth (G1 D6 pending); COM head '
                 'delay D10=1 s pending the G1 D6 re-check; VSL model = branch d80faf9 candidate A0.5_E4 on FW_E (Carlson '
                 'A0.5/E4/alpha0 base 110 + exposure transport, sign cells re-derived for this network; fitted on seed29 '
                 'demand-v1 with a different 110 curve, refit on v2 pending; action set 50-110 step 10: 50-80 extrapolate and '
                 '100 interpolates the 90-only fit; cohorts start from the last applied command; FW_W keeps '
                 'the legacy cap, zero derivative at 110); no native9000 launch approval claimed')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def membership_path(root, base_config, prefix=N31D + '/scenario/'):
    """The membership pin comes from the E base config (one source of truth with C9)."""
    base = load(root / base_config)
    path = base['control_area_objective']['membership_path']
    if not isinstance(path, str) or not path.startswith(prefix):
        raise ValueError('Base config membership is not a re-pinned N31D scenario entry: ' + repr(path))
    return path


def build(root=ROOT, *, sources=None, detectors=DETECTORS, base_config=BASE_CONFIG, network_sha256=NETWORK_SHA256,
          membership_prefix=N31D + '/scenario/'):
    from evaluation.controllers import obs150_contract as oc
    sources = dict(SOURCES if sources is None else sources)
    required = [*sources.values(), detectors, base_config, OFF_GROUPS, FREEZE]
    missing = [rel for rel in required if not (root / rel).is_file()]
    if missing:
        raise FileNotFoundError('plant_n31_v2 inputs missing (owner packages pending): ' + ', '.join(missing))
    membership = membership_path(root, base_config, membership_prefix)
    if not (root / membership).is_file():
        raise FileNotFoundError('Membership named by the base config is missing: ' + membership)
    pins = {key: {'path': rel, 'sha256': sha256(root / rel)} for key, rel in sources.items()}
    if pins['network']['sha256'] != network_sha256:
        raise ValueError('Pinned network is not the runtime network v3b be0075bf')
    geometry = load(root / sources['geometry'])
    if geometry['network']['sha256'] != pins['network']['sha256']:
        raise ValueError('C1 geometry was extracted from another network')
    if geometry['refined_partition']['sha256'] != pins['refined_partition']['sha256']:
        raise ValueError('C1 geometry was refined by another partition')
    if load(root / FREEZE)['parameters_sha256'] != pins['parameters']['sha256']:
        raise ValueError('parameters.json differs from its freeze pin')
    detector_sha = sha256(root / detectors)
    oc.read_detector_csv(root / detectors, detector_sha)
    document = {
        'schema': oc.PLANT_SCHEMA_V2,
        'sources': pins,
        'membership': {'path': membership, 'sha256': sha256(root / membership)},
        'off_groups': OFF_GROUPS,
        'observation': {'detectors': {'path': detectors, 'sha256': detector_sha},
                        'expected_simres': oc.EXPECTED_SIMRES, 'vehrec_interval_sec': oc.VEHREC_INTERVAL_SEC},
        'source_boundary': copy.deepcopy(oc.SOURCE_BOUNDARY_BLOCK),
        'lane_groups': False,
        'fw_e_terminal': 'component',
        'vsl_command_space': oc.VSL_COMMAND_SPACE,
        'future_observations': False,
        'qualification': QUALIFICATION,
    }
    oc.validate_plant_manifest_v2(document)
    return document


def dumps(document):
    return (json.dumps(document, indent=2, ensure_ascii=False) + '\n').encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true', help='compare with the written manifest')
    args = parser.parse_args()
    data = dumps(build())
    if args.check:
        if OUT.read_bytes() != data:
            raise SystemExit('plant_n31_v2.json differs from its generator')
    else:
        OUT.write_bytes(data)
    print('PLANT_N31_OK sha256=' + hashlib.sha256(data).hexdigest())


if __name__ == '__main__':
    main()
