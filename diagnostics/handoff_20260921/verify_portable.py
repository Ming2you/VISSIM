"""Offline source/tests verification; never starts VISSIM or edits model inputs."""
from pathlib import Path
import hashlib
import json
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def main():
    import numpy  # Load before historical tests change dependency search paths.
    manifest = HERE / 'direct_files.json'
    if manifest.exists():
        for row in json.loads(manifest.read_text(encoding='utf-8'))['files']:
            p = ROOT / row['path']
            assert p.stat().st_size == row['bytes'], row['path']
            assert hashlib.sha256(p.read_bytes()).hexdigest() == row['sha256'], row['path']
    scope = ROOT / 'diagnostics/demand_sweep/ramp_dsd_20260916_v2'
    names = [p.relative_to(ROOT).with_suffix('').as_posix().replace('/', '.')
             for p in sorted(scope.rglob('test*.py')) if '__pycache__' not in p.parts]
    names += ['diagnostics.test_freeway_fd', 'diagnostics.handoff_20260916.test_restore_evidence']
    started = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromNames(names))
    summary = {'passed': result.wasSuccessful(), 'tests': result.testsRun,
               'failures': len(result.failures), 'errors': len(result.errors),
               'elapsed_s': time.perf_counter() - started, 'modules': names,
               'native_runs': 0}
    print(json.dumps(summary))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
