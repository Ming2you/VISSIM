"""C9: config_n31_v2.json = the WP-E base tuning plus the v2 plant differences.

The base (N31D/scenario/config_n31_v2.base.json, written by repin_scenario_v2.py) is OBS1
with the scenario pack re-pinned to the v2 network. This script adds exactly the
plan C9 differences and nothing else:

  freeway.lane_plant                                  -> plant_n31_v2.json          (OBS1:8082)
  freeway.segment_params                              -> C1 b110 21-row copy        (NEW-10)
  urban.capacity.head_observation.sample_interval_sec    deleted                    (OBS1:7831)
  config_overrides.freeway_follower.vsl_set           -> [50, 60, ..., 110] step 10 (OBS1:7466)
  config_overrides.network.v_free                     -> 110                        (OBS1:7433)
  _canonical.fd_fit_20260828.values.v_free            -> 110                        (OBS1:7961, record only)
  execution.native_signal_record                      -> false                      (NEW-2)
  execution.signal_vbs_config                         -> N31D/scenario/lane_native_b110.vbs
  observation.physical_branch_projection.source.network -> the v2 network pin       (OBS1:8109-8113)

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
NETWORK = N31D + '/network/baseline_s31_v2nc.inpx'
NETWORK_SHA256 = 'f475ce42b0afaceccfd7974066a7b040600ddb93849bcf09174cd794bc0b255b'
OLD_PACK = 'diagnostics/lane_plant_20260921/scenario/'
NEW_PACK = N31D + '/scenario/'
VSL_SET = [50.0, 60.0, 70.0, 80.0, 90.0, 100.0, 110.0]   # user decision 2026-09-24: 10 km/h steps, c_max 110
V_FREE = 110.0


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
    doc['_n31_note'] = ('SDMPC-31 v2 tuning (plan C9): ' + BASE + ' plus lane_plant v2, b110 segment_params, '
                        'no head sample interval, vsl_set [50,60,70,80,90,100,110], v_free 110, native_signal_record false, '
                        'lane_native_b110.vbs and the v2 branch-projection network. Generated by make_config_n31.py.')
    return doc


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
    for rel in (BASE, PLANT, SEGMENT_PARAMS, RUNNER_CONFIG, NETWORK):
        if not (root / rel).is_file():
            raise FileNotFoundError('config_n31_v2 input missing (owner package pending): ' + rel)
    if sha256(root / NETWORK) != NETWORK_SHA256:
        raise ValueError('v2 network copy differs from f475ce42')
    base = json.loads((root / BASE).read_text(encoding='utf-8-sig'))
    doc = apply(base)
    check_pack(root, doc)
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
