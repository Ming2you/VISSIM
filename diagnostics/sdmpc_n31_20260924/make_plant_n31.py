"""C8: plant_n31_v2.json, the coupled-lane-plant/v2 manifest (plan C8, contract 1.1).

Every source is a {path, sha256} pin computed from the bytes in this worktree;
nothing is copied or edited here. Inputs owned by other packages must exist
first, and the generator fails listing whatever is missing:

  network, sig_manifest            WP-E  N31D/network/ (byte copy of NET, .sig table)
  runner_config                    WP-E  N31D/scenario/lane_native_b110.vbs
  membership                       WP-E  the re-pinned pack entry named by the E base
                                         config's control_area_objective.membership_path
  observation.detectors            WP-B2 N31D/obs150/obs150_detectors_v2.csv
  geometry                         the runtime network's own no-control s31 extraction (v3c3 since
                                         2026-10-01: metanet_calibration_v1/v3c3_nc_20261001, extract_observations.py;
                                         v3c1_nc_20260928 2026-09-28..10-01, v3b_nc_20260925 before)
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
  python -B diagnostics/sdmpc_n31_20260924/make_plant_n31.py --vsl-family distribution --out-root <folder> [--check]
The second form (VSL family overlay, repin plan 2026-10-01 V-11 / U5-a) reads every repo-relative input in <folder>
first (the family's reference_config, runner_config and detector table + sidecar, written there by
make_reference_config / repin_scenario_v2 runner-family / build_obs150_detectors with the same --out-root) and in the
tree otherwise, keeps every pin path repo-relative and writes <folder>/<repo-relative OUT>. Nothing in the tree.
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
# Network v3c3 (user approval 2026-10-01): its no-control fit-seed runs s31/s41/s43/s47 and the v3c2 s53 run (declared
# substitute; s37 held out), extracted with extract_observations.py (the v3c1 extractions of 2026-09-28 stay in
# v3c1_nc_20260928 and the v3b ones in v3b_nc_20260925 as their records).
V3C3_NC = 'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/v3c3_nc_20261001'
SOURCES = {
    'network': N31D + '/network/baseline_s31_v3c3nc.inpx',
    'geometry': V3C3_NC + '/observations/s31_v3c3nc_observations/geometry.json',
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
NETWORK_SHA256 = '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e'   # v3c3 (v3c1 2577209b until 2026-10-01)
NETWORK_LABEL = 'v3c3 3de889f0'
_QUALIFICATION_HEAD = (
    'NOT_QUALIFIED: network v3c3 3de889f0 (user approval 2026-10-01; = v3c2 597191ac + the single-value desired-speed '
    'distributions 81/91/101; v3c2 = v3c1 2577209b + vehicle composition 14 "Freeway entry DSD110" on the 12 '
    'freeway-entry intervals of inputs 1098/1099, user decision 2026-09-30; v3c1 = v3b be0075bf + decisions 1160, '
    '1162-1168, V2 held; v3b = v2 f475ce42 + static-route edits: 19 route destinations, 1061 pos, 32 relFlows); the '
    'b110 segment_params, boundary fit and boundary_config are v2 priors fitted on v2 NC s31 (f475ce42), not refit on '
    'v3b, v3c1 or v3c3 (carried-over priors); geometry, port profile, ramp-arrival forecast and the unsignalized-turn '
    'validation re-derived from the v3c3 NC fit seeds 31/41/43/47 and the v3c2 NC s53 run (declared substitute: the '
    'v3c3 s53 run did not complete; s37 held out); the 10490 measured head-service curve is carried over (service '
    'table normalised at install, K3); 31-cell b110 boundary family with the baseline FD (no FD refit); held-out '
    'history_forecast speed RMSE FW_E 20-25 / FW_W 13-17 km/h (v2 NC, not re-scored since); scenario pack priors '
    'carried over from fcb349d3 with prior_mismatch receipts (D-B); obs150 observation integrated and verified offline '
    'only (probe V0 + V1 code tests), not yet against native ground truth (G1 D6 pending); COM head delay D10=1 s '
    'pending the G1 D6 re-check; ')
QUALIFICATION_BY_FAMILY = {
    'single_value': _QUALIFICATION_HEAD + (
        'VSL law = N1F stage-2 L2 Carlson A 1.33 / E 0.87 / alpha 0 with the measured speed scale m_v (80 0.72252, 90 '
        '0.81198, 100 0.90068, cubic Lagrange to (110, 1)) on FW_E (fit_results 4091d6e1, rule-selected; fitted on the '
        'v3b-based single-value arms s41/43/47/53 and carried over to v3c3 as a prior; Carlson family formally '
        'rejected, chi2/dof 6.41; pessimistic at 80: B2 outflow -4.0 % predicted vs -0.34 % observed) with the branch '
        'd80faf9 exposure transport (base 110, sign cells re-derived for this network), FW_W legacy cap (zero '
        'derivative at 110, never fitted on single-value distributions although its commands are written as them too); '
        'single-value compliance: the commands 80/90/100/110 are written as the distributions 81/91/101/110 (tuning '
        'actuation.vsl_command_distribution, runner 81,91,101,110); cohorts start from the last applied command; no '
        'native9000 launch approval claimed'),
    'distribution': _QUALIFICATION_HEAD + (
        'VSL family distribution (generator option, not the tree): law N1 L1 Carlson A 0.94 / E 1.44 / alpha 0 on FW_E '
        '(fit on v3b NC s41/43/47/53, 80-110; Carlson family formally rejected by rule (b)(i) chi2/dof 4.19) with the '
        'branch d80faf9 exposure transport, FW_W legacy cap; the commands 80/90/100/110 are written as themselves '
        '(runner 80,90,100,110); cohorts start from the last applied command; no native9000 launch approval claimed'),
}
VSL_FAMILIES = tuple(QUALIFICATION_BY_FAMILY)
VSL_FAMILY = 'single_value'
QUALIFICATION = QUALIFICATION_BY_FAMILY[VSL_FAMILY]
# The inputs a VSL family overlay replaces (V-11): its plant law, its runner list and the detector sidecar that pins it.
FAMILY_INPUTS = ('reference_config', 'runner_config')


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


class Overlay:
    """root / rel, but a repo-relative file present in the family overlay folder is read from there (V-11)."""

    def __init__(self, root, overlay=None):
        self.root, self.overlay = Path(root), (Path(overlay) if overlay is not None else None)

    def __truediv__(self, rel):
        if self.overlay is not None and (self.overlay / rel).is_file():
            return self.overlay / rel
        return self.root / rel


def build(root=ROOT, *, sources=None, detectors=DETECTORS, base_config=BASE_CONFIG, network_sha256=NETWORK_SHA256,
          membership_prefix=N31D + '/scenario/', family=VSL_FAMILY, overlay=None):
    from evaluation.controllers import obs150_contract as oc
    root = Overlay(root, overlay)
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
        raise ValueError('Pinned network is not the runtime network ' + NETWORK_LABEL)
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
        'qualification': QUALIFICATION_BY_FAMILY[family],
    }
    oc.validate_plant_manifest_v2(document)
    return document


def dumps(document):
    return (json.dumps(document, indent=2, ensure_ascii=False) + '\n').encode('utf-8')


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
    parser.add_argument('--check', action='store_true', help='compare with the written manifest')
    parser.add_argument('--vsl-family', choices=VSL_FAMILIES, default=VSL_FAMILY)
    parser.add_argument('--out-root', help='VSL family overlay folder: read its family inputs, write the manifest there')
    args = parser.parse_args()
    overlay = family_root(args.vsl_family, args.out_root)
    out = OUT if overlay is None else overlay / OUT.relative_to(ROOT)
    data = dumps(build(family=args.vsl_family, overlay=overlay))
    if args.check:
        if out.read_bytes() != data:
            raise SystemExit('plant_n31_v2.json differs from its generator')
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    print('PLANT_N31_OK family=' + args.vsl_family + ' sha256=' + hashlib.sha256(data).hexdigest())


if __name__ == '__main__':
    main()
