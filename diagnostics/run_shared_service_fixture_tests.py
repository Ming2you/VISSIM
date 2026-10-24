"""Shared25 + clock5 using fresh fixtures, with original runs denied in workers."""
import argparse
import atexit
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from uuid import uuid4
from diagnostics.review_fixtures import ROOT, restore
from diagnostics.shared_service_fixtures import ARCHIVE, ENVIRONMENT

TESTS = ['diagnostics.'+name for name in (
    'test_shared_service_pool', 'test_local_landing_clock', 'test_local_landing_clock_receiving')]
AUDIT_ENV = 'VISSIM_SHARED_SERVICE_AUDIT_DIR'
_ISOLATION_INSTALLED = False


def install_isolation():
    """sitecustomize invokes this in the test process and every Python worker."""
    global _ISOLATION_INSTALLED
    if _ISOLATION_INSTALLED:
        return
    forbidden = str((ROOT/'evaluation/runs').resolve()).casefold()
    attempts = []
    def guard(event, args):
        if event in ('open', 'os.listdir', 'os.scandir') and args and isinstance(args[0], (str, bytes, os.PathLike)):
            path = os.path.abspath(os.fsdecode(args[0])).casefold()
            if path == forbidden or path.startswith(forbidden+os.sep):
                attempts.append({'event': event, 'path': path})
                raise AssertionError('Portable shared test tried original run access: '+path)
        if event == 'subprocess.Popen' and args and Path(str(args[0])).name.lower() in ('git', 'git.exe'):
            attempts.append({'event': event, 'path': str(args[0])})
            raise AssertionError('Portable shared test tried Git source access')
    sys.addaudithook(guard)
    _ISOLATION_INSTALLED = True
    os.environ['VISSIM_SHARED_SERVICE_AUDIT_PID'] = str(os.getpid())
    def save():
        output = Path(os.environ[AUDIT_ENV])/f'audit_{os.getpid()}.json'
        output.write_text(json.dumps({'pid': os.getpid(), 'guard_installed': True,
            'forbidden_root': forbidden, 'attempts': attempts}, indent=2)+'\n', encoding='utf-8')
    atexit.register(save)


def child():
    if os.environ.get('VISSIM_SHARED_SERVICE_AUDIT_PID') != str(os.getpid()):
        raise RuntimeError('Fresh Python process did not load its isolation guard')
    started = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(TESTS))
    result_path = Path(os.environ[AUDIT_ENV])/'tests.json'
    result_path.write_text(json.dumps({'tests': TESTS, 'tests_run': result.testsRun,
        'success': result.wasSuccessful(), 'errors': len(result.errors), 'failures': len(result.failures),
        'elapsed_sec': time.monotonic()-started}, indent=2)+'\n', encoding='utf-8')
    return 0 if result.wasSuccessful() else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--child', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        return child()
    manifest_path = ROOT/'diagnostics/contract_candidate_configs/manifest.json'
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    pins = dict(manifest['source_sha256'])
    pins.update({row['path']: row['sha256'] for row in manifest['outputs'].values()})
    def changed():
        return [name for name, expected in pins.items()
                if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected]
    if changed():
        raise ValueError('Runtime pins changed before portable regression: '+str(changed()))
    destination = ROOT/'.review-fixtures'/('sp_'+uuid4().hex[:8])
    restored = restore(destination, archive=ARCHIVE)
    bootstrap = destination/'bootstrap'; bootstrap.mkdir()
    (bootstrap/'sitecustomize.py').write_text(
        'from diagnostics.run_shared_service_fixture_tests import install_isolation\ninstall_isolation()\n', encoding='utf-8')
    env = dict(os.environ, **{ENVIRONMENT: str(destination), AUDIT_ENV: str(bootstrap)})
    env['PYTHONPATH'] = os.pathsep.join([str(bootstrap), str(ROOT), *([env['PYTHONPATH']] if env.get('PYTHONPATH') else [])])
    # sitecustomize already imported this module to install the guard. Invoke
    # that same module instance rather than re-executing it with runpy -m.
    process = subprocess.run([sys.executable, '-X', 'utf8', '-c',
        'from diagnostics.run_shared_service_fixture_tests import child; raise SystemExit(child())'], cwd=ROOT, env=env,
        capture_output=True, text=True, encoding='utf-8', timeout=60)
    (ROOT/'diagnostics/shared_service_fixture_validation.log').write_text(process.stdout+process.stderr, encoding='utf-8')
    print(process.stdout+process.stderr)
    test_result = json.loads((bootstrap/'tests.json').read_text(encoding='utf-8')) if (bootstrap/'tests.json').is_file() else {'success': False}
    audits = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(bootstrap.glob('audit_*.json'))]
    source_changes = changed()
    unchanged_manifest = manifest_path.read_bytes() == manifest_bytes
    passed = (process.returncode == 0 and test_result.get('success') and test_result.get('tests_run') == 30
              and len(audits) == 4 and all(a['guard_installed'] and not a['attempts'] for a in audits)
              and not source_changes and unchanged_manifest)
    report = {'schema': 'shared-service-fixture-validation/v1', 'success': passed,
        'archive_sha256': restored['archive_sha256'], 'fixture_root': str(destination),
        'source_pins_checked': len(manifest['source_sha256']), 'output_pins_checked': len(manifest['outputs']),
        'source_changes': source_changes, 'manifest_unchanged': unchanged_manifest,
        'tests': test_result, 'process_audits': audits, 'returncode': process.returncode,
        'raw_files': restored['raw_files'], 'path_relocations': restored['path_relocations'],
        'scope': 'Fresh restored raw4 inputs; actual canonical functions; original run reads/listing and Git subprocess denied in test process and all3 fresh workers. No full MPC, endpoint or VISSIM.'}
    (ROOT/'diagnostics/shared_service_fixture_validation.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print('PORTABLE_SHARED_SERVICE='+json.dumps({'success': passed, 'processes_audited': len(audits), 'source_changes': source_changes}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
