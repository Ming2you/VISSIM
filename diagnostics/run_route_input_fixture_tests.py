"""Fresh route/input fixtures; canonical model tests with original runs denied."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from uuid import uuid4
from diagnostics.review_fixtures import ROOT, ARCHIVE as CORE_ARCHIVE, ENVIRONMENT as CORE_ENV, restore
from diagnostics.route_input_fixtures import ARCHIVE, ENVIRONMENT

TESTS = ['diagnostics.'+name for name in (
    'test_projection_support_road_paths', 'test_projection_support_source_lineage',
    'test_route_choice_projection_claim', 'test_native_internal_input',
    'test_route_choice_corridor', 'test_route_choice_1128', 'test_physical_phase_authority')]
EXTENDED_TESTS = ['diagnostics.'+name for name in (
    'test_native_demand_forecast', 'test_native1083_signal_authority',
    'test_native_input_position_partition', 'test_native_input_routes',
    'test_native_route_choice', 'test_native_internal_common_approach',
    'test_native_internal_empirical_choice', 'test_native_input_prehead')]


def child(extended=False):
    forbidden = str((ROOT/'evaluation/runs').resolve()).casefold()
    attempts = []
    def guard(event, args):
        if event in ('open', 'os.listdir', 'os.scandir') and args and isinstance(args[0], (str, bytes, os.PathLike)):
            path = os.path.abspath(os.fsdecode(args[0])).casefold()
            if path == forbidden or path.startswith(forbidden+os.sep):
                attempts.append(path)
                raise AssertionError('Portable route/input test tried original run access: '+path)
        if event == 'subprocess.Popen' and args and Path(str(args[0])).name.lower() in ('git', 'git.exe'):
            attempts.append(str(args))
            raise AssertionError('Portable route/input test tried Git source access')
    sys.addaudithook(guard)
    started = time.monotonic()
    selected_tests = TESTS + EXTENDED_TESTS if extended else TESTS
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(selected_tests))
    report = {'route_fixture_root': os.environ[ENVIRONMENT], 'core_fixture_root': os.environ[CORE_ENV],
        'tests': selected_tests, 'tests_run': result.testsRun, 'successful': result.wasSuccessful(),
        'failures': len(result.failures), 'errors': len(result.errors),
        'blocked_original_or_git_accesses': attempts, 'wall_sec': time.monotonic()-started,
        'scope': 'Fresh restored byte-pinned historical inputs; current production imports; original run reads and Git subprocesses denied. Explicit pre-route baseline setup; feature-specific ON behavior is configured in each test. Historical missing current-route labels use declared diagnostic holding only.'}
    report_name = 'route_input_fixture_validation_v2.json' if extended else 'route_input_fixture_validation.json'
    (ROOT/'diagnostics'/report_name).write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return 0 if result.wasSuccessful() else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--child', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--extended', action='store_true', help='Use v2 observed-NC anchors and the additional native-source tests.')
    args = parser.parse_args()
    if args.child:
        return child(args.extended)
    # Keep restored original run names below Windows MAX_PATH.
    route = ROOT/'.review-fixtures'/('ri_'+uuid4().hex[:8])
    core = ROOT/'.review-fixtures'/('ric_'+uuid4().hex[:8])
    archive = ARCHIVE.with_name('route_input_v2.zip') if args.extended else ARCHIVE
    restored = restore(route, archive=archive)
    # Tracked baseline configs/one observed-record fixture stay at stable repo
    # paths; require their bytes to equal the raw copies preserved in this ZIP.
    for row in restored['raw_files']:
        if row['path'].startswith('diagnostics/fixtures/'):
            if (ROOT/row['path']).read_bytes() != (route/'raw'/row['path']).read_bytes():
                raise ValueError('Tracked diagnostic fixture differs from archive: '+row['path'])
    restore(core, archive=CORE_ARCHIVE)
    env = dict(os.environ, **{ENVIRONMENT: str(route), CORE_ENV: str(core)})
    command = [sys.executable, '-X', 'utf8', '-m', 'diagnostics.run_route_input_fixture_tests', '--child']
    if args.extended: command.append('--extended')
    return subprocess.run(command,
        cwd=ROOT, env=env, check=False).returncode


if __name__ == '__main__':
    raise SystemExit(main())
