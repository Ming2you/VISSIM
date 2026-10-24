"""Shared fixtures for the WP-C (SDMPC-31 wiring) tests.

The v2 plant is loaded from the real C1/C7/C12 files. Inputs owned by other
packages that may not exist yet (WP-E network copy, runner config, .sig table,
membership; WP-B2 detector CSV and obs150_observation.load_context) are
synthesized inside a temporary folder under this tests directory, so every pin
stays repo-relative as the contract requires. The temporary folder is removed
on exit. Nothing outside this folder is written.
"""
from __future__ import annotations

import contextlib
import copy
import dataclasses
import hashlib
import json
import shutil
import sys
import tempfile
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
N31D = HERE.parent
ROOT = HERE.parents[2]
for extra in (ROOT, ROOT / 'vendor/NumSim-mine', ROOT / 'diagnostics/obs150_20260924/tests', N31D):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import contract_fixtures as cf  # noqa: E402
import make_plant_n31  # noqa: E402
from evaluation.controllers import obs150_contract as oc  # noqa: E402

# The pinned runtime network's original (v3b since 2026-09-25; was the v2 stage-1 s31_v2nc copy f475ce42).
NET_INPX = Path(r'D:\VISSIM_runs\20260925_v3b\s31_v3bnc\prepared\network\baseline_s31_v3bnc.inpx')
E_INPX = ROOT / make_plant_n31.SOURCES['network']
V1_PLANT = 'diagnostics/lane_plant_20260921/plant.json'
V1_MEMBERSHIP = 'diagnostics/lane_plant_20260921/scenario/control_area_membership_6c3aee.json'
OBS1 = ROOT / 'diagnostics/sdmpc_pfo_caps_20260922/config_candidate_obs1.json'
GEOMETRY = ROOT / make_plant_n31.SOURCES['geometry']
PARAMETERS = ROOT / make_plant_n31.SOURCES['parameters']
REFERENCE = ROOT / make_plant_n31.SOURCES['reference_config']
DETECTORS = ROOT / make_plant_n31.DETECTORS
# The v2 (f475ce42) B110 calibration observations: kept for the source-boundary equivalence test (code parity,
# any observation set); the plant geometry now comes from the v3b extraction (make_plant_n31.SOURCES).
B110_OBSERVATIONS = Path(r'D:\VISSIM-merge\sim3') / make_plant_n31.B110 / 'observations/s31_v2nc_observations'
OBS_MODULE = 'evaluation.controllers.obs150_observation'

# N31 plan section 2 (verified): parents, port cells and parent-space VSL tables.
EXPECTED_TO_CELL = {'RM_C10480': 8, 'RM_C10482': 10, 'RM_C10646': 18, 'RM_C10644': 22, 'RM_C10639': 10,
                    'RM_C10681': 12, 'RM_C10490': 21, 'RM_C10484': 23}
EXPECTED_FROM_CELL = {'10481': 18, '10483': 20, '10491': 9, '10479': 7, '10643': 9, '10682': 11, '10638': 19,
                      '10645': 16}
EXPECTED_HEAD_OF_CELL = {'FW_E': [0] * 5 + [5] * 9 + [10] * 11 + [15] * 6,
                         'FW_W': [0] * 5 + [5] * 10 + [10] * 10 + [15] * 6}


def rel(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def calibration_schedules():
    from evaluation.controllers import source_boundary
    return source_boundary.geometry_schedules(load_json(GEOMETRY))


def stub_context(document, paths, *, manifest_sha256=None):
    """A contract-valid Obs150Context bound to this manifest (stands in for WP-B2's load_context)."""
    schedules = calibration_schedules()
    return dataclasses.replace(cf.context(), manifest_sha256=manifest_sha256,
                               network_sha256=document['sources']['network']['sha256'],
                               detector_csv_sha256=document['observation']['detectors']['sha256'],
                               source_schedule=schedules)


@contextlib.contextmanager
def obs150_stub(**functions):
    """Temporarily install evaluation.controllers.obs150_observation with the given functions."""
    import evaluation.controllers as package
    module = types.ModuleType(OBS_MODULE)
    module.load_context = functions.pop('load_context', stub_context)
    for name, function in functions.items():
        setattr(module, name, function)
    saved_module = sys.modules.get(OBS_MODULE)
    saved_attr = getattr(package, 'obs150_observation', None)
    sys.modules[OBS_MODULE] = module
    package.obs150_observation = module
    try:
        yield module
    finally:
        if saved_module is None:
            sys.modules.pop(OBS_MODULE, None)
        else:
            sys.modules[OBS_MODULE] = saved_module
        if saved_attr is None:
            if getattr(package, 'obs150_observation', None) is module:
                delattr(package, 'obs150_observation')
        else:
            package.obs150_observation = saved_attr


class V2Sandbox:
    """A coupled-lane-plant/v2 manifest over real WP-C inputs and synthesized pending inputs."""

    def __init__(self, *, network=None):
        self.network = network

    def __enter__(self):
        self.dir = Path(tempfile.mkdtemp(prefix='_tmp_', dir=HERE))
        try:
            self._build()
        except BaseException:
            shutil.rmtree(self.dir, ignore_errors=True)
            raise
        return self

    def _write(self, name, data):
        path = self.dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return rel(path)

    def _build(self):
        sources = dict(make_plant_n31.SOURCES)
        if self.network is not None:
            sources['network'] = self.network
        elif E_INPX.is_file() and sha256(E_INPX) == make_plant_n31.NETWORK_SHA256:
            sources['network'] = rel(E_INPX)
        else:
            if not NET_INPX.is_file():
                raise FileNotFoundError('Neither the WP-E network copy nor the NET original is available')
            target = self.dir / 'network' / NET_INPX.name
            target.parent.mkdir(parents=True)
            shutil.copyfile(NET_INPX, target)
            sources['network'] = rel(target)
        sources['runner_config'] = self._write('scenario/lane_native_b110.vbs', b"' synthetic WP-C test runner config\n")
        sources['sig_manifest'] = self._write('network/sig_manifest.json', b'{"synthetic": true}\n')
        membership = self._write('scenario/control_area_membership_test.json', (ROOT / V1_MEMBERSHIP).read_bytes())
        base = self._write('config_n31_v2.base.json', json.dumps(
            {'control_area_objective': {'membership_path': membership}}).encode('utf-8'))
        detectors = self._write('obs150/obs150_detectors_v2.csv', oc.format_detector_csv(cf.detector_rows()))
        network_sha = sha256(ROOT / sources['network'])
        self.document = make_plant_n31.build(ROOT, sources=sources, detectors=detectors, base_config=base,
                                             network_sha256=network_sha, membership_prefix=rel(self.dir) + '/')
        self.manifest = self._write('plant_n31_v2.json', make_plant_n31.dumps(self.document))

    def __exit__(self, *exc):
        shutil.rmtree(self.dir, ignore_errors=True)
        return False


def build_full_tuning(plant_rel=make_plant_n31.N31D + '/plant_n31_v2.json'):
    """OBS1 with the C9 differences (the E re-pin is not required for freeway-only use)."""
    import make_config_n31
    tuning = make_config_n31.apply(load_json(OBS1), require_repinned=False)
    tuning['freeway']['lane_plant'] = plant_rel
    return tuning


def parameters():
    return load_json(PARAMETERS)['parameters']


def component():
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import CanonicalFreewayModel
    return CanonicalFreewayModel(load_json(GEOMETRY), REFERENCE)


def deep(value):
    return copy.deepcopy(value)
