"""Known-route proposal tests with original run and Git reads denied, including worker."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from uuid import uuid4
from diagnostics.review_fixtures import ROOT, restore
from diagnostics.known_wout_fixtures import ARCHIVE, ENVIRONMENT
from diagnostics.run_shared_service_fixture_tests import AUDIT_ENV


def child():
    if os.environ.get('VISSIM_SHARED_SERVICE_AUDIT_PID')!=str(os.getpid()):
        raise RuntimeError('Portable guard was not loaded in this process')
    result=unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromName('diagnostics.test_known_wout_routes'))
    (Path(os.environ[AUDIT_ENV])/'tests.json').write_text(json.dumps({
        'tests_run':result.testsRun,'success':result.wasSuccessful(),
        'failures':len(result.failures),'errors':len(result.errors)})+'\n',encoding='utf-8')
    return 0 if result.wasSuccessful() else 1


def main():
    manifest=ROOT/'diagnostics/contract_candidate_configs/manifest.json'
    doc=json.loads(manifest.read_text()); paths=[ROOT/p for p in doc['source_sha256']]
    paths.extend(ROOT/v['path'] for v in doc['outputs'].values()); paths.append(manifest)
    before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    target=ROOT/'.review-fixtures'/('kw_'+uuid4().hex[:8])
    restored=restore(target,archive=ARCHIVE)
    boot=target/'bootstrap';boot.mkdir()
    (boot/'sitecustomize.py').write_text(
        'from diagnostics.run_shared_service_fixture_tests import install_isolation\ninstall_isolation()\n',encoding='utf-8')
    env=dict(os.environ,**{ENVIRONMENT:str(target),AUDIT_ENV:str(boot)})
    env['PYTHONPATH']=os.pathsep.join([str(boot),str(ROOT)])
    process=subprocess.run([sys.executable,'-X','utf8','-c',
        'from diagnostics.run_known_wout_fixture_tests import child;raise SystemExit(child())'],
        cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=60)
    (ROOT/'diagnostics/known_wout_fixture_validation.log').write_text(process.stdout+process.stderr,encoding='utf-8')
    tests=json.loads((boot/'tests.json').read_text()) if (boot/'tests.json').exists() else {'success':False}
    audits=[json.loads(p.read_text()) for p in sorted(boot.glob('audit_*.json'))]
    changed=[p for p,h in before.items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
    success=(process.returncode==0 and tests.get('success') and tests.get('tests_run')==12
             and len(audits)==2 and all(not a['attempts'] for a in audits) and not changed)
    result={'schema':'known-wout-fixture-validation/v1','success':success,'tests':tests,
        'process_audits':audits,'source_changes':changed,'source_sha256':before,
        'archive_sha256':restored['archive_sha256'],'raw_files':restored['raw_files'],
        'path_relocations':restored['path_relocations'],
        'scope':'Actual canonical initialization/body plus diagnostic-only proposed hooks; original run and Git denied in parent test and fresh runtime worker. No endpoint, optimizer or VISSIM.'}
    (ROOT/'diagnostics/known_wout_fixture_validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(process.stdout+process.stderr)
    print(json.dumps({'success':success,'processes':len(audits),'source_changes':changed}))
    return 0 if success else 1


if __name__=='__main__':raise SystemExit(main())
