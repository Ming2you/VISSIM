"""Run the canonical regressions with original runs and all Git calls denied."""
import hashlib
import json
from pathlib import Path
import sys
import time
import unittest
from diagnostics.review_fixtures import ROOT
from diagnostics.head_service_resource_fixtures import ARCHIVE

COUNTS = {'blocked_original_run_access': 0, 'blocked_git_calls': 0}
ORIGINAL_RUNS = (ROOT/'evaluation/runs').resolve()


def deny(event, args):
    if event in ('open', 'os.listdir', 'os.scandir') and args and isinstance(args[0], (str,bytes)):
        path = Path(args[0].decode() if isinstance(args[0],bytes) else args[0]).resolve()
        if path.is_relative_to(ORIGINAL_RUNS):
            COUNTS['blocked_original_run_access'] += 1
            raise PermissionError('Original run access forbidden in portable regression')
    if event == 'subprocess.Popen':
        command = args[1]
        executable = command[0] if isinstance(command, (list,tuple)) else str(command).split()[0].strip('"')
        if Path(executable).name.lower() in ('git','git.exe'):
            COUNTS['blocked_git_calls'] += 1
            raise PermissionError('Git access forbidden in portable regression')


if __name__ == '__main__':
    sys.addaudithook(deny)
    started = time.perf_counter()
    suite = unittest.defaultTestLoader.loadTestsFromName('diagnostics.test_head_service_resources')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    evidence = {'schema': 'head-resource-canonical-portable-validation/v1', 'tests_run': result.testsRun,
        'errors': len(result.errors), 'failures': len(result.failures), 'successful': result.wasSuccessful(),
        'elapsed_sec': time.perf_counter()-started, **COUNTS,
        'fixture_sha256': hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
        'scope': 'Parent process original-run reads/listing and Git subprocess denied. Fresh worker receives private pickle only; no raw fixture reads.'}
    (ROOT/'diagnostics/head_service_resources_canonical_portable_validation.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(evidence))
    raise SystemExit(0 if result.wasSuccessful() else 1)
