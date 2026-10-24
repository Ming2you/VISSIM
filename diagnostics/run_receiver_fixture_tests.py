"""Run actual1050 regressions from a fresh minimal archive with run reads denied."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from uuid import uuid4
from diagnostics.review_fixtures import ROOT, restore

ENV = 'VISSIM_RECEIVER_FIXTURE_ROOT'
ARCHIVE = ROOT/'diagnostics/fixtures/receiver_turns_v1.zip'
TESTS = ['diagnostics.test_projection_support_receiver_turns.ReceiverTurnTests.'+name for name in (
    'test_actual_1050_is_single_transit_stock_without_initial_entry',
    'test_removing_proved_support_reproduces_original_failure',
    'test_all_remaining_unknown_links_still_fail_before_mutation')]


def child():
    forbidden = str((ROOT/'evaluation/runs').resolve()).casefold()
    attempts = []
    def guard(event, arguments):
        if event in ('open', 'os.listdir', 'os.scandir') and arguments and isinstance(arguments[0], (str, bytes, os.PathLike)):
            path = os.path.abspath(os.fsdecode(arguments[0])).casefold()
            if path == forbidden or path.startswith(forbidden+os.sep):
                attempts.append(path)
                raise AssertionError('Portable receiver test attempted original run access: '+path)
        if event == 'subprocess.Popen' and arguments and Path(str(arguments[0])).name.lower() in ('git', 'git.exe'):
            attempts.append(str(arguments))
            raise AssertionError('Portable receiver test attempted git history access')
    sys.addaudithook(guard)
    started = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(TESTS))
    output = {'fixture_root': os.environ[ENV], 'tests': TESTS, 'tests_run': result.testsRun,
        'successful': result.wasSuccessful(), 'failures': len(result.failures), 'errors': len(result.errors),
        'blocked_original_or_git_accesses': attempts, 'wall_sec': time.monotonic()-started,
        'scope': 'Fresh minimal4-file restoration; current production imports; original run access and git subprocesses denied. Full31-state regression is separately retained.'}
    (ROOT/'diagnostics/receiver_fixture_validation.json').write_text(json.dumps(output, indent=2)+'\n', encoding='utf-8')
    return 0 if result.wasSuccessful() else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--child', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        return child()
    destination = ROOT/'.review-fixtures'/('receiver-'+uuid4().hex)
    restore(destination, archive=ARCHIVE)
    env = dict(os.environ, **{ENV: str(destination)})
    return subprocess.run([sys.executable, '-X', 'utf8', '-m', 'diagnostics.run_receiver_fixture_tests', '--child'],
        cwd=ROOT, env=env, check=False).returncode


if __name__ == '__main__':
    raise SystemExit(main())
