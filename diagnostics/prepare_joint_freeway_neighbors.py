"""Produce an unapplied new-file patch and optional bounded, model-free proof."""
import argparse
import ast
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
STEM = ROOT / 'diagnostics/joint_freeway_neighbors'
SOURCE = ROOT / 'diagnostics/joint_freeway_neighbors_candidate.py'
TARGET = 'evaluation/controllers/joint_freeway_neighbors.py'
PINS = (
    'evaluation/controllers/vissim_stackelberg_adapter.py',
    'evaluation/controllers/area_meter_finalization.py',
    'evaluation/controllers/link_predictor.py',
    'vendor/NumSim-mine/src/controllers/wu_faithful_follower.py',
    'vendor/NumSim-mine/src/models/state.py',
    'diagnostics/joint_owner_addresses_candidate.py',
    'diagnostics/test_joint_owner_addresses.py',
    'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json',
    'outputs/signal_group_actuation_plan_mainline_20260825.json',
    'diagnostics/contract_candidate_configs_v4/n7_area_beta300.json',
)


def pins():
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in PINS}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    if (ROOT / TARGET).exists():
        raise ValueError('Target already exists; this artifact only adds an inactive module')
    body = SOURCE.read_text(encoding='utf-8')
    ast.parse(body)
    artifact = f'diff --git a/{TARGET} b/{TARGET}\nnew file mode 100644\n'
    artifact += ''.join(difflib.unified_diff([], body.splitlines(keepends=True),
                                           fromfile='/dev/null', tofile='b/' + TARGET))
    path = STEM.with_suffix('.patch')
    path.write_text(artifact, encoding='utf-8', newline='\n')
    restored = ''.join(line[1:] for line in artifact.splitlines(keepends=True)
                       if line.startswith('+') and not line.startswith('+++'))
    if restored != body or b'\r' in path.read_bytes():
        raise AssertionError('Patch reconstruction/newline mismatch')
    if not args.verify:
        print(path)
        return
    before = pins()
    start = time.perf_counter()
    command = [sys.executable, '-B', '-X', 'utf8', '-m', 'unittest', 'diagnostics.test_joint_freeway_neighbors', '-v']
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=30)
    elapsed = time.perf_counter() - start
    log = STEM.with_name(STEM.name + '_tests.log')
    log.write_text(run.stdout + run.stderr, encoding='utf-8', newline='\n')
    after = pins()
    changed = [p for p in before if before[p] != after[p]]
    result = {
        'schema': 'joint-freeway-neighbors-proposal/v2', 'passed': run.returncode == 0 and not changed,
        'exit_code': run.returncode, 'runner_elapsed_sec': elapsed,
        'command': command, 'model_imports': 0, 'model_execution': 0, 'com_execution': 0,
        'scope': 'Ten address-only/synthetic-callback tests; actual mapping/selected-plan/config values; no canonical allocator/model integration',
        'source_changes': changed, 'source_sha256_before': before, 'source_sha256_after': after,
        'proposal_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'patch_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'test_sha256': hashlib.sha256((ROOT / 'diagnostics/test_joint_freeway_neighbors.py').read_bytes()).hexdigest(),
        'target_text_sha256': hashlib.sha256(body.encode()).hexdigest(),
        'patch_reconstruction_exact': True, 'production_applied': False,
        'required_predecessor': 'diagnostics/joint_owner_addresses.patch',
        'prior_evidence_archive': 'diagnostics/fixtures/joint_freeway_neighbors_pre_incumbent_guard_v1.zip',
        'incumbent_guard_prior_reproduction': 'diagnostics/joint_freeway_incumbent_guard_prior_reproduction.json',
        'unverified': ['effective-runtime domain extraction', 'canonical physical realization callbacks',
                       'fixed-candidate score/price/quantity contract', 'game dispatch/OFF integration',
                       'actual-main/fresh-worker/VISSIM behavior'],
    }
    STEM.with_name(STEM.name + '_validation.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(result, indent=2))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
