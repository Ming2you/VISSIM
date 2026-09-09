"""Fresh restore + real tests with original run/archive-history access denied."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from uuid import uuid4
from diagnostics.review_fixtures import ROOT, ENVIRONMENT, restore

TESTS = [
    'diagnostics.test_review_fixtures',
    'diagnostics.test_area_projection_coverage',
    'diagnostics.test_dynamic_area_routes',
    'diagnostics.test_sc2001_corridor',
    'diagnostics.test_observation_projection',
    'diagnostics.test_area_arrival_routes',
]


def run_child(include_wsh, strict_only, modules):
    blocked = str((ROOT/'evaluation/runs').resolve()).casefold()
    audited = {'blocked_original_run_accesses': [], 'git_subprocess_attempts': []}
    def guard(event, arguments):
        if event in ('open', 'os.listdir', 'os.scandir') and arguments and isinstance(arguments[0], (str, bytes, os.PathLike)):
            location = os.path.abspath(os.fsdecode(arguments[0])).casefold()
            if location == blocked or location.startswith(blocked+os.sep):
                audited['blocked_original_run_accesses'].append(location)
                raise AssertionError('Portable regression attempted original run access: '+location)
        if event == 'subprocess.Popen' and arguments:
            executable = str(arguments[0])
            if Path(executable).name.lower() in ('git', 'git.exe'):
                audited['git_subprocess_attempts'].append(str(arguments[1]))
                raise AssertionError('Portable regression must use its archived fixed source, not local git history')
    sys.addaudithook(guard)
    names = (['diagnostics.test_strict_decision_failfast'] if strict_only else
             TESTS + (['diagnostics.test_strict_decision_failfast'] if include_wsh else []))
    if modules:
        names = modules
    start = time.monotonic()
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    output = {'fixture_root': os.environ[ENVIRONMENT], 'tests': names, 'tests_run': result.testsRun,
              'failures': len(result.failures), 'errors': len(result.errors), 'successful': result.wasSuccessful(),
              'wall_sec': time.monotonic()-start, **audited,
              'isolation': 'Fresh restored fixture root; all original evaluation/runs reads/listing and git subprocess references forbidden. Production code and pinned runtime inputs are imported from this checkout.'}
    filename = ('portable_fixture_validation_custom.json' if modules else
                'portable_fixture_validation_strict.json' if strict_only else 'portable_fixture_validation.json')
    (ROOT/'diagnostics'/filename).write_text(json.dumps(output, indent=2)+'\n', encoding='utf-8')
    return 0 if result.wasSuccessful() else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--child', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--include-wsh', action='store_true', help='Also run actual PowerShell/cscript with fake COM; Windows only')
    parser.add_argument('--strict-only', action='store_true', help='Run only the Windows watchdog/VBS portable fixture tests')
    parser.add_argument('--module', action='append', default=[], help='Run an explicitly named unittest module instead of the default subset; repeatable')
    parser.add_argument('--destination', type=Path)
    args = parser.parse_args()
    if args.child:
        return run_child(args.include_wsh, args.strict_only, args.module)
    destination = args.destination or ROOT/'.review-fixtures'/('isolated-'+uuid4().hex)
    restore(destination)
    env = dict(os.environ, **{ENVIRONMENT: str(destination.resolve())})
    command = [sys.executable, '-X', 'utf8', '-m', 'diagnostics.run_portable_fixture_tests', '--child']
    if args.include_wsh:
        command.append('--include-wsh')
    if args.strict_only:
        command.append('--strict-only')
    for module in args.module:
        command.extend(['--module', module])
    # A separate process guarantees no previously cached reference/fixture is
    # reused. The working directory differs from the recorded run directories.
    return subprocess.run(command, cwd=ROOT, env=env, check=False).returncode


if __name__ == '__main__':
    raise SystemExit(main())
