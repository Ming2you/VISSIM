r"""Launch plan of one SDMPC-31 obs150 run (plan D4 / section 1.1: the tuning file decides everything).

run_sdmpc_n31.ps1 calls this from the frozen tree FRZ. Every value the watchdog receives is either
derived from the tuning (manifest, runner config, network, detector table, observation env) or a
constant of the SDMPC-31 scenario below; nothing is guessed and nothing falls back.

    launch_plan.py plan --tuning <file> --name <Name> --sim-period <s> --seed <n> --controller <c>
                        [--gt-windows 750:900,1050:1200] [--stall-sec 2400] [--runs-root <dir>] [--preflight]
        Validates, then claims the run folder <runs-root>\<Name> (mkdir, never reused) and writes
        <run folder>\launch_plan.json. First stdout line: LAUNCH_PLAN_OK plan=<path>.
        --preflight claims <runs-root>\_preflight\<Name>_<stamp> instead.
    launch_plan.py verify-network --plan <plan.json>
    launch_plan.py check-provenance --plan <plan.json> --provenance <run_provenance_<Name>.json>

Refusals (exit 1, one line 'LAUNCH_PLAN_ERROR <reason>'): tuning outside a frozen tree, a v1
manifest (v1 reproduction stays with run_sdmpc_laneplant.ps1), any manifest pin whose bytes differ,
validate_tuning_v2 failure, no <runner config stem>_sgplan.vbs beside the runner config, a
ground-truth window on a non-dev name, an existing run folder.
check-provenance also requires files.signal_group_plan = that file and no RW_ADAPTER_MODE in env.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from n31_common import (FREEZE_NAME, NETWORK_PREFIX, RUNS_ROOT, ToolError, file_sha256, find_freeze_root,  # noqa: E402
                        load_effective_tuning, oc, read_json, repo_path, require, vbs_constants, write_json)

PLAN_SCHEMA = 'sdmpc31-launch-plan/v1'
PLAN_FILE = 'launch_plan.json'
NAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$')
CONTROLLERS = ('wu-link', 'no-control')
WARMUP_CONTROLLER = 'no-control'
CONTROL_START_SEC = 900
MIN_STALL_SEC = 2400        # plan V5: StallSec = max(2400, 2 x measured decision wall)
STARTUP_STALL_SEC = 300
SIG_COUNT = 42              # NEW-1: the v2 network folder carries 42 .sig supply files
WATCHDOG_REL = 'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1'
# Scenario constants of plan section 7 (V5 launch block). The mapping comes from the tuning's
# mapping_json and must equal the constant, so a tuning cannot silently retarget it.
RUNNER_FILES = {
    'DemandProfile': 'diagnostics/sdmpc_n31_20260924/scenario/profile.csv',
    'Mapping': 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json',
    'Calibration': 'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json',
    'UrbanInputGateMap': 'evaluation/real_world_modi_inventory/urban_input_gate_map_ver2_20260907.csv',
    'VehicleInputRoles': 'evaluation/real_world_modi_inventory/vehicle_input_roles.csv',
}
EXTRA_NETWORK_SUFFIXES = ('.json',)   # a copy tool may leave a receipt; nothing else may sit beside the .inpx
# The runner finds its signal-group plan only as the runner config's sibling <stem>_sgplan.vbs; a missing or
# misnamed copy switches the plan off without an error (VBS:2149-2161, plan section 8 copy table).
SGPLAN_SUFFIX = '_sgplan.vbs'
# Runner env keys that must never reach an obs150 run (the queue script's RW_ADAPTER_MODE leak).
FORBIDDEN_ENV = ('RW_ADAPTER_MODE',)


def _pin(root, pin, what):
    path = repo_path(root, pin['path'])
    require(path.is_file(), f'{what} missing in the frozen tree: {pin["path"]}')
    actual = file_sha256(path)
    require(actual == pin['sha256'], f'{what} bytes differ from the manifest pin: {pin["path"]} {actual} != {pin["sha256"]}')
    return {'path': str(path), 'rel': pin['path'], 'sha256': actual}


def sig_table(document):
    """{file name: sha256} from sig_manifest.json (WP-E). Accepts a name->sha map or a list of rows."""
    body = document
    if isinstance(document, dict):
        for key in ('files', 'sig', 'sigs', 'signals', 'sig_files'):
            if key in document:
                body = document[key]
                break
    table = {}
    if isinstance(body, dict):
        items = [(name, sha) for name, sha in body.items() if isinstance(name, str) and name.lower().endswith('.sig')]
    elif isinstance(body, list):
        items = []
        for row in body:
            require(isinstance(row, dict), 'sig_manifest rows must be objects')
            name = next((row[k] for k in ('name', 'file', 'path') if k in row), None)
            require(isinstance(name, str), 'sig_manifest row lacks a file name')
            items.append((Path(name.replace('\\', '/')).name if '/' in name.replace('\\', '/') else name, row.get('sha256')))
    else:
        raise ToolError('Unrecognized sig_manifest.json layout')
    for name, sha in items:
        require(isinstance(sha, str) and re.fullmatch(r'[0-9a-f]{64}', sha) is not None, f'sig_manifest sha for {name}')
        require(name not in table, f'Duplicate .sig in sig_manifest: {name}')
        table[name] = sha
    require(len(table) == SIG_COUNT, f'sig_manifest lists {len(table)} .sig files, expected {SIG_COUNT}')
    return dict(sorted(table.items()))


def freeze_pin(root):
    """{path, sha256, head, tree_sha256} of <root>/FREEZE.json."""
    path = Path(root) / FREEZE_NAME
    document = read_json(path)
    return {'path': str(path), 'sha256': file_sha256(path), 'head': document.get('git', {}).get('head'),
            'tree_sha256': document.get('tree_sha256')}


def build_plan(args):
    tuning_path = Path(args.tuning).resolve()
    require(tuning_path.is_file(), f'Tuning file missing: {tuning_path}')
    root = find_freeze_root(tuning_path)
    require(root is not None, f'Tuning is not inside a frozen tree (no {FREEZE_NAME} above it): {tuning_path}. '
                              'Launch only from FRZ (freeze_worktree.ps1).')
    freeze = freeze_pin(root)
    require(NAME_RE.match(args.name) is not None, f'Run name must match {NAME_RE.pattern}: {args.name!r}')
    require(args.controller in CONTROLLERS, f'Controller must be one of {CONTROLLERS}')
    require(args.sim_period >= oc.DECISION_INTERVAL_SEC and args.sim_period % oc.DECISION_INTERVAL_SEC == 0,
            'SimPeriod must be a positive multiple of 150 s (obs150 decision clock)')
    require(args.stall_sec >= MIN_STALL_SEC, f'StallSec must be >= {MIN_STALL_SEC} (plan V5)')
    gt = oc.parse_gt_windows(args.gt_windows or '')
    if gt:
        require(args.name.startswith(oc.GT_RUN_NAME_PREFIX),
                f'Ground-truth windows are allowed only on dev runs named {oc.GT_RUN_NAME_PREFIX}*')
        require(gt[-1][1] <= args.sim_period, 'Ground-truth windows must end inside the simulation')

    tuning, chain = load_effective_tuning(tuning_path)
    lane_plant = tuning.get('freeway', {}).get('lane_plant')
    require(isinstance(lane_plant, str) and lane_plant, 'Tuning lacks freeway.lane_plant')
    manifest_path = repo_path(root, lane_plant)
    require(manifest_path.is_file(), f'Lane plant manifest missing: {lane_plant}')
    document = read_json(manifest_path)
    mode = oc.plant_mode(document)
    require(mode == 'v2', 'Tuning selects a coupled-lane-plant/v1 manifest; reproduce v1 with run_sdmpc_laneplant.ps1')
    oc.validate_tuning_v2(tuning, document)   # also validates the manifest (section 1.1)

    pins = {key: _pin(root, pin, 'sources.' + key) for key, pin in document['sources'].items()}
    membership = _pin(root, document['membership'], 'membership')
    detectors = _pin(root, document['observation']['detectors'], 'observation.detectors')
    rows, _ = oc.read_detector_csv(detectors['path'], detectors['sha256'])   # (rows, sha256)
    detectors['rows'] = len(rows)
    off_groups = repo_path(root, document['off_groups'])
    require(off_groups.is_file(), f'off_groups missing: {document["off_groups"]}')
    sigs = sig_table(read_json(pins['sig_manifest']['path']))
    sig_dir = Path(pins['sig_manifest']['path']).parent
    for name, sha in sigs.items():
        require((sig_dir / name).is_file(), f'.sig copy missing beside sig_manifest.json: {name}')
        require(file_sha256(sig_dir / name) == sha, f'.sig copy differs from sig_manifest: {name}')

    runner_files = {}
    for key, rel in RUNNER_FILES.items():
        path = repo_path(root, rel)
        require(path.is_file(), f'{key} missing in the frozen tree: {rel}')
        runner_files[key] = {'path': str(path), 'rel': rel, 'sha256': file_sha256(path)}
    mapping = tuning.get('mapping_json')
    require(mapping == RUNNER_FILES['Mapping'], f'tuning mapping_json {mapping!r} differs from {RUNNER_FILES["Mapping"]}')
    runner_config = Path(pins['runner_config']['path'])
    sgplan = runner_config.with_name(runner_config.stem + SGPLAN_SUFFIX)
    require(sgplan.is_file(), f'Signal-group plan missing beside the runner config (the runner would run without it): {sgplan}')
    signal_group_plan = {'path': str(sgplan), 'sha256': file_sha256(sgplan)}
    warnings = []
    constants = vbs_constants(pins['runner_config']['path'])
    detector_mapping = constants.get('RW_DETECTOR_MAPPING_PATH', '').replace('\\', '/')
    if tuning.get('detector_mapping_json') not in (None, detector_mapping):
        warnings.append(f'tuning detector_mapping_json {tuning.get("detector_mapping_json")!r} differs from the runner '
                        f'config RW_DETECTOR_MAPPING_PATH {detector_mapping!r} (the runner passes its own)')

    runs_root = Path(args.runs_root).resolve()
    if args.preflight:
        stamp = _dt.datetime.now().strftime('%Y%m%d_%H%M%S')
        out_dir = runs_root / '_preflight' / f'{args.name}_{stamp}'
    else:
        out_dir = runs_root / args.name
    require(not out_dir.exists(), f'Run folder already exists (a failed run keeps its name; pick a new one): {out_dir}')
    network_dir = out_dir / 'network'
    network_file = network_dir / f'{NETWORK_PREFIX}{args.name}.inpx'
    env = oc.expected_runner_env(document, detectors['path'])
    if gt:
        env['RW_OBS150_GT'] = oc.format_gt_windows(gt)
    watchdog = repo_path(root, WATCHDOG_REL)
    require(watchdog.is_file(), f'Watchdog missing in the frozen tree: {WATCHDOG_REL}')
    return {
        'schema': PLAN_SCHEMA, 'created_at': _dt.datetime.now().astimezone().isoformat(timespec='seconds'),
        'name': args.name, 'sim_period': args.sim_period, 'seed': args.seed, 'controller': args.controller,
        'warmup_controller': WARMUP_CONTROLLER, 'control_start_sec': CONTROL_START_SEC,
        'control_interval_sec': oc.DECISION_INTERVAL_SEC, 'state_log_interval_sec': oc.DECISION_INTERVAL_SEC,
        'stall_sec': args.stall_sec, 'startup_stall_sec': STARTUP_STALL_SEC, 'preflight': bool(args.preflight),
        'ground_truth_windows': gt, 'gt_text': oc.format_gt_windows(gt) if gt else '',
        'root': str(root),
        'freeze': freeze,
        'tuning': {'path': str(tuning_path), 'sha256': chain[0]['sha256'], 'chain': chain},
        'manifest': {'path': str(manifest_path), 'rel': lane_plant, 'sha256': file_sha256(manifest_path), 'mode': mode},
        'sources': pins, 'membership': membership, 'detectors': detectors,
        'sig_files': sigs, 'sig_dir': str(sig_dir),
        'runner_config': pins['runner_config'], 'signal_group_plan': signal_group_plan, 'runner_files': runner_files,
        'out_dir': str(out_dir), 'network_dir': str(network_dir), 'network_file': str(network_file),
        'watchdog': str(watchdog), 'expected_env': env, 'warnings': warnings,
    }


def verify_network(plan):
    network_dir = Path(plan['network_dir'])
    require(network_dir.is_dir(), f'Network folder missing: {network_dir}')
    inpx = sorted(p.name for p in network_dir.iterdir() if p.suffix.lower() == '.inpx')
    require(inpx == [Path(plan['network_file']).name], f'Network folder must hold exactly {Path(plan["network_file"]).name}; found {inpx}')
    sha = file_sha256(plan['network_file'])
    require(sha == plan['sources']['network']['sha256'], f'Network copy {sha} differs from the manifest pin')
    sigs = {p.name: p for p in network_dir.iterdir() if p.suffix.lower() == '.sig'}
    require(set(sigs) == set(plan['sig_files']), f'.sig set differs: missing {sorted(set(plan["sig_files"]) - set(sigs))} '
                                                  f'extra {sorted(set(sigs) - set(plan["sig_files"]))}')
    for name, path in sigs.items():
        require(file_sha256(path) == plan['sig_files'][name], f'.sig copy differs: {name}')
    others = sorted(p.name for p in network_dir.iterdir()
                    if p.suffix.lower() not in ('.inpx', '.sig') + EXTRA_NETWORK_SUFFIXES)
    require(not others, f'Unexpected files beside the network (a stale .err breaks the obs150 capture): {others}')
    print(f'NETWORK_OK file={plan["network_file"]} sha256={sha} sig={len(sigs)}')


def check_provenance(plan, provenance_path, *, require_freeze=True):
    """The run_provenance_<Name>.json the watchdog wrote must carry exactly this plan.

    require_freeze=False only for the integration test of a PreflightOnly in the unfrozen worktree
    (the watchdog then records observation.freeze null, CONTRACT 1.4); the CLI always requires it."""
    doc = read_json(provenance_path)
    problems = []

    def expect(condition, message):
        if not condition:
            problems.append(message)

    same = lambda a, b: a is not None and b is not None and Path(a).resolve() == Path(b).resolve()
    expect(doc.get('name') == plan['name'], 'name')
    expect(doc.get('seed') == plan['seed'] and doc.get('sim_period_sec') == plan['sim_period'], 'seed/sim_period')
    expect(doc.get('controller') == plan['controller'], 'controller')
    expect(doc.get('control_interval_sec') == 150 and doc.get('state_log_interval_sec') == 150, 'intervals 150/150')
    expect(same(doc.get('workspace_root'), plan['root']), 'workspace_root is not FRZ')
    files = doc.get('files', {})
    for key, want in (('network', (plan['network_file'], plan['sources']['network']['sha256'])),
                      ('tuning', (plan['tuning']['path'], plan['tuning']['sha256'])),
                      ('generated_vbs_config', (plan['runner_config']['path'], plan['runner_config']['sha256'])),
                      ('signal_group_plan', (plan['signal_group_plan']['path'], plan['signal_group_plan']['sha256'])),
                      *((key, (plan['runner_files'][arg]['path'], plan['runner_files'][arg]['sha256']))
                        for key, arg in (('demand_profile', 'DemandProfile'), ('control_mapping', 'Mapping'),
                                         ('calibration', 'Calibration'), ('urban_input_gate_map', 'UrbanInputGateMap'),
                                         ('vehicle_input_roles', 'VehicleInputRoles')))):
        got = files.get(key, {})
        expect(same(got.get('path'), want[0]) and got.get('sha256') == want[1], f'files.{key}')
    env = doc.get('env', {})
    for key, value in plan['expected_env'].items():
        if key == 'RW_OBS150_DETECTORS':      # a path: the same file, however PS1 spells it
            expect(same(env.get(key), value), f'env {key}={env.get(key)!r} is not {value!r}')
        else:
            expect(env.get(key) == value, f'env {key}={env.get(key)!r} != {value!r}')
    if not plan['gt_text']:
        expect('RW_OBS150_GT' not in env, 'env RW_OBS150_GT on a non-ground-truth run')
    expect(env.get('RW_OFFSET_WRITER') == 'experiment', 'env RW_OFFSET_WRITER')
    expect(env.get('RW_FORCE_STEPWISE') in (None, ''), 'env RW_FORCE_STEPWISE')
    for key in FORBIDDEN_ENV:
        expect(key not in env, f'env {key}={env.get(key)!r} leaked into the run')
    # The .sig files the watchdog found beside the network are exactly the pinned 42 (PS1 signal_programs).
    programs = doc.get('signal_programs')
    found = {Path(str(p.get('path'))).name: p.get('sha256') for p in programs or () if isinstance(p, dict)}
    expect(isinstance(programs, list) and len(found) == len(programs) and found == plan['sig_files'],
           f'signal_programs ({len(found)} .sig) differ from the pinned sig files')
    block = doc.get('observation')
    try:
        oc.validate_provenance_observation(block, require_freeze=require_freeze)
    except (oc.ObsContractError, TypeError) as error:
        problems.append(f'observation block: {error}')
    else:
        expect(same(block['plant_manifest']['path'], plan['manifest']['path'])
               and block['plant_manifest']['sha256'] == plan['manifest']['sha256'], 'observation.plant_manifest')
        expect(same(block['detectors']['path'], plan['detectors']['path'])
               and block['detectors']['sha256'] == plan['detectors']['sha256']
               and block['detectors']['rows'] == plan['detectors']['rows'], 'observation.detectors')
        expect(block['ground_truth_windows'] == plan['ground_truth_windows'], 'observation.ground_truth_windows')
        if require_freeze or block['freeze'] is not None:
            expect(block['freeze'] is not None and plan['freeze'] is not None
                   and same(block['freeze']['path'], plan['freeze']['path'])
                   and block['freeze']['sha256'] == plan['freeze']['sha256'], 'observation.freeze')
    require(not problems, 'Provenance differs from the launch plan: ' + '; '.join(problems))
    print(f'PROVENANCE_OK path={provenance_path} run_id={doc.get("run_id")} '
          f'freeze={(plan.get("freeze") or {}).get("sha256")}')


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('plan')
    p.add_argument('--tuning', required=True)
    p.add_argument('--name', required=True)
    p.add_argument('--sim-period', type=int, required=True)
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--controller', default='wu-link')
    p.add_argument('--gt-windows', default='')
    p.add_argument('--stall-sec', type=int, default=MIN_STALL_SEC)
    p.add_argument('--runs-root', default=str(RUNS_ROOT))
    p.add_argument('--preflight', action='store_true')
    v = sub.add_parser('verify-network')
    v.add_argument('--plan', required=True)
    c = sub.add_parser('check-provenance')
    c.add_argument('--plan', required=True)
    c.add_argument('--provenance', required=True)
    args = parser.parse_args(argv)
    if args.command == 'plan':
        plan = build_plan(args)
        out_dir = Path(plan['out_dir'])
        out_dir.parent.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(exist_ok=False)          # claims the name; a second launch of it is refused
        plan_path = out_dir / PLAN_FILE
        sha = write_json(plan_path, plan)
        print(f'LAUNCH_PLAN_OK plan={plan_path}')
        for warning in plan['warnings']:
            print('LAUNCH_PLAN_WARN ' + warning)
        print(f'LAUNCH_PLAN_DETAIL sha256={sha} root={plan["root"]} manifest={plan["manifest"]["rel"]} '
              f'network_sha={plan["sources"]["network"]["sha256"][:8]} detectors={plan["detectors"]["rows"]} '
              f'controller={plan["controller"]} sim_period={plan["sim_period"]} seed={plan["seed"]} '
              f'gt={plan["gt_text"] or "-"}')
    elif args.command == 'verify-network':
        verify_network(read_json(args.plan))
    else:
        check_provenance(read_json(args.plan), args.provenance)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except (ToolError, oc.ObsContractError) as error:
        print(f'LAUNCH_PLAN_ERROR {error}')
        sys.exit(1)
