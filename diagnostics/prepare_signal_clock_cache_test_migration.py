"""Prepare (never apply) exact-before/after canonical clock test migration."""
import argparse
import difflib
import hashlib
import io
import json
from pathlib import Path
import types
import unittest

ROOT=Path(__file__).resolve().parents[1]
TARGET='diagnostics/test_signal_clock_cache.py'


def once(source, old, new):
    if source.count(old)!=1: raise ValueError('Migration anchor changed: '+old[:80])
    return source.replace(old,new,1)


def migrated(source):
    source=once(source,"        if hashlib.sha256(source.read_bytes()).hexdigest() != manifest['source_sha256']:\n            raise AssertionError('Frozen original no longer matches the current production clock')\n", """        installed_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        patch_manifest = read(ROOT/'diagnostics/signal_clock_cache_patch_manifest.json')
        expected_after = patch_manifest['after_lf_sha256']
        if patch_manifest['source_sha256'] != manifest['source_sha256'] or installed_hash not in (manifest['source_sha256'], expected_after):
            raise AssertionError('Production clock is neither frozen dd13e08 nor the exact reviewed patch')
        if list(manifest['functions']) != ['bounds','validate_vector','_phase_windows','written_offset_sec','phase_fraction']:
            raise AssertionError('Frozen reference function inventory changed')
        cls.installed_clock_source = {'sha256': installed_hash, 'expected_after_lf_sha256': expected_after,
            'cache_installed': installed_hash == expected_after}
""")
    source=source.replace("'source_sha256': cls.before, 'reference_manifest': cls.asserted_manifest}", "'source_sha256': cls.before, 'reference_manifest': cls.asserted_manifest,\n            'canonical_source': cls.installed_clock_source}")
    source=source.replace("diagnostics/signal_clock_cache_exact_validation.json", "diagnostics/signal_clock_cache_canonical_validation.json")
    old="""        source=proposed_source(Path(actual.__file__).read_text(encoding='utf-8'))
        names={'clear_clock_cache','clock_cache_info','_uncached_clock','_immutable',
               '_clock_key','_validated_clock','_finite_fraction','_immutable_plan','phase_fraction'}
        nodes=[n for n in ast.parse(source).body if
            isinstance(n,ast.FunctionDef) and n.name in names or
            isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'MAX_CLOCKS','MAX_INTERVALS','MAX_PLAN_TREES','_PLAN_TREES','_CLOCKS','_STATS'} for t in n.targets)]
        namespace={**actual.__dict__,'OrderedDict':OrderedDict}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'<diagnostic-clock-functions-only>','exec'),namespace)
"""
    new="""        if self.installed_clock_source['cache_installed']:
            # The reviewed patch is already installed: exercise its canonical
            # function directly, never reapply the proposal over new source.
            namespace=actual.__dict__
        else:
            source=proposed_source(Path(actual.__file__).read_text(encoding='utf-8'))
            names={'clear_clock_cache','clock_cache_info','_uncached_clock','_immutable',
                   '_clock_key','_validated_clock','_finite_fraction','_immutable_plan','phase_fraction'}
            nodes=[n for n in ast.parse(source).body if
                isinstance(n,ast.FunctionDef) and n.name in names or
                isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'MAX_CLOCKS','MAX_INTERVALS','MAX_PLAN_TREES','_PLAN_TREES','_CLOCKS','_STATS'} for t in n.targets)]
            namespace={**actual.__dict__,'OrderedDict':OrderedDict}
            exec(compile(ast.Module(body=nodes,type_ignores=[]),'<diagnostic-clock-functions-only>','exec'),namespace)
"""
    source=once(source,old,new)
    source=once(source,"out={}\nfor signal in cfg.network.signals:\n", "out={}\ncanonical_checks=0\nfor signal in cfg.network.signals:\n")
    source=once(source,"   a=reference.phase_fraction(action,cfg,spec,step)\n   with patch.object(actual,'phase_fraction',proposal.validated_clock):", """   a=reference.phase_fraction(action,cfg,spec,step)
   # First test the installed canonical implementation through real worker
   # aliases, with no proposal substitution. This runs before and after apply.
   for module in modules:
    b=module._phase_green_fraction(action,cfg,spec,step)
    assert pickle.dumps(a)==pickle.dumps(b)
    canonical_checks+=1
   with patch.object(actual,'phase_fraction',proposal.validated_clock):""")
    source=once(source,"print(json.dumps({'values':out,'stats':proposal.stats()},sort_keys=True))", """from pathlib import Path
installed_hash=hashlib.sha256(Path(actual.__file__).read_bytes()).hexdigest()
print(json.dumps({'values':out,'stats':proposal.stats(),'canonical_checks':canonical_checks,
 'canonical_sha256':installed_hash,'canonical_cache_stats':actual.clock_cache_info() if hasattr(actual,'clock_cache_info') else None},sort_keys=True))""")
    source=once(source,"        self.assertGreater(worker['stats']['clock_hits'],0)\n", """        self.assertEqual(worker['canonical_sha256'],self.installed_clock_source['sha256'])
        self.assertEqual(worker['canonical_checks'],len(self.cfg.network.signals)*len(actual.PHASES)*4*5)
        if self.installed_clock_source['cache_installed']:
            self.assertGreater(worker['canonical_cache_stats']['clock_hits'],0)
            self.assertGreater(worker['canonical_cache_stats']['clock_misses'],0)
        else:
            self.assertIsNone(worker['canonical_cache_stats'])
        self.assertGreater(worker['stats']['clock_hits'],0)
""")
    return source


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--validate-current',action='store_true');args=parser.parse_args()
    path=ROOT/TARGET;before=path.read_text(encoding='utf-8');after=migrated(before)
    compile(after,TARGET,'exec')
    patch=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+TARGET,tofile='b/'+TARGET))
    output=ROOT/'diagnostics/signal_clock_cache_test_migration.patch';output.write_text(patch,encoding='utf-8',newline='\n')
    report={'schema':'signal-clock-test-migration/v1','applied':False,'test_before_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'test_after_lf_sha256':hashlib.sha256(after.encode()).hexdigest(),'patch_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
        'canonical_source_contract':json.loads((ROOT/'diagnostics/signal_clock_cache_patch_manifest.json').read_text()),
        'frozen_fixture_regenerated':False,'validation_scope':'Not run'}
    if args.validate_current:
        module=types.ModuleType('diagnostics._signal_clock_test_migration');module.__file__=str(path)
        exec(compile(after,str(path),'exec'),module.__dict__)
        stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
        log=stream.getvalue();print(log)
        (ROOT/'diagnostics/signal_clock_cache_test_migration_console.log').write_text(log,encoding='utf-8')
        report.update(tests=result.testsRun,passed=result.wasSuccessful(),validation_scope='Generated test module against the unchanged production original; after-apply canonical run remains root gate')
    (ROOT/'diagnostics/signal_clock_cache_test_migration_manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    if args.validate_current and not result.wasSuccessful():raise SystemExit(1)


if __name__=='__main__':main()
