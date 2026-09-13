"""Exact frozen-function vs diagnostic clock-cache comparisons; no solve."""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import pickle
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from diagnostics.test_head_service_resources import ROOT, adapter, configured, read, CONFIG, input_path, CONTRACT
from diagnostics.fixtures import signal_clock_dd13e08 as reference
from diagnostics import signal_clock_cache_proposal as proposal
from evaluation.controllers import signal_actuation_contract as actual, offset_promotion


def outcome(function, *args):
    try:
        value = function(*args)
        return ('None',) if value is None else ('float_bits', struct.pack('!d', value).hex())
    except Exception as exc:
        return ('error', type(exc).__name__, str(exc))


def fixture():
    tuning = read(CONFIG)
    tuning['urban']['capacity']['head_resource_contract'] = CONTRACT
    result = configured(tuning, input_path('state_000900.json'), input_path('action_000750.json'))
    cfg = result[0]
    from src.models.state import ControlAction
    action = adapter.control_from_json(input_path('action_000900.json'), cfg, ControlAction)
    action = actual.prepare_control(action, cfg)
    return result, action


class ClockCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = read(ROOT/'diagnostics/fixtures/signal_clock_dd13e08_manifest.json')
        cls.asserted_manifest = manifest
        source = ROOT/manifest['source_path']
        installed_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        patch_manifest = read(ROOT/'diagnostics/signal_clock_cache_patch_manifest.json')
        expected_after = patch_manifest['after_lf_sha256']
        if patch_manifest['source_sha256'] != manifest['source_sha256'] or installed_hash not in (manifest['source_sha256'], expected_after):
            raise AssertionError('Production clock is neither frozen dd13e08 nor the exact reviewed patch')
        if list(manifest['functions']) != ['bounds','validate_vector','_phase_windows','written_offset_sec','phase_fraction']:
            raise AssertionError('Frozen reference function inventory changed')
        cls.installed_clock_source = {'sha256': installed_hash, 'expected_after_lf_sha256': expected_after,
            'cache_installed': installed_hash == expected_after}
        cls.runtime, cls.action = fixture()
        cls.cfg = cls.runtime[0]
        cls.paths = list((ROOT/'evaluation/controllers').glob('*.py')) + [
            ROOT/'diagnostics/signal_clock_cache_proposal.py', Path(__file__),
            ROOT/'diagnostics/fixtures/signal_clock_dd13e08.py']
        cls.before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in cls.paths}
        cls.checks = 0

    @classmethod
    def tearDownClass(cls):
        changed = [p for p,h in cls.before.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest() != h]
        evidence = {'scope': 'Frozen dd13e08 reference, current actual setup, diagnostic-only clock cache',
            'exact_comparisons': cls.checks, 'source_changes': changed,
            'source_sha256': cls.before, 'reference_manifest': cls.asserted_manifest,
            'canonical_source': cls.installed_clock_source}
        (ROOT/'diagnostics/signal_clock_cache_canonical_validation.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
        if changed:
            raise AssertionError(changed)

    def setUp(self):
        proposal.clear()

    def compare(self, control, cfg, spec, step):
        expected = outcome(reference.phase_fraction, control, cfg, spec, step)
        self.assertEqual(outcome(actual.phase_fraction, control, cfg, spec, step), expected)
        for function in (proposal.finite_only, proposal.validated_clock_full_check, proposal.validated_clock):
            self.assertEqual(outcome(function, control, cfg, spec, step), expected,
                             (function.__name__, spec, step))
            self.assertEqual(outcome(function, control, cfg, spec, step), expected)
        type(self).checks += 1
        return expected

    def test_all_signals_decimal_cycles_signed_offsets_absolute_and_fractional_steps(self):
        for cycle in (150., 150.001, 149.999):
            cfg = deepcopy(self.cfg)
            for signal in cfg.network.signals:
                cfg.network.cycle_length_by_signal[signal] = cycle
                cfg.network.effective_green_total_by_signal[signal] = round(cycle - 3*len(cfg.network.signal_live_phases(signal)), 3)
            action = actual.prepare_control(self.action, cfg)
            for offset in (-20., -0.0001, 0., 10., cycle-0.0001, cycle, 2*cycle+10):
                action.offsets = dict.fromkeys(cfg.network.signals, offset)
                for signal in cfg.network.signals:
                    for phase in actual.PHASES:
                        spec = {'phase':signal+'_'+phase}
                        for step in (None, 0, 29, 30, 31, 179, 180, 181, 209, 210, 29999, 30000, 30001):
                            self.compare(action, cfg, spec, step)
            cfg.simulation.T_u = 2.5
            for signal in cfg.network.signals:
                for phase in actual.PHASES:
                    for step in (-.1, 0., .5, 180.2, 30000.25):
                        self.compare(action, cfg, {'phase':signal+'_'+phase}, step)

    def test_in_place_and_copy_mutations_invalidate_all_clock_operands(self):
        cfg, action = deepcopy(self.cfg), self.action.copy()
        signal = 'SC1004'; spec = {'phase': signal+'_p3'}
        self.compare(action,cfg,spec,180)
        for offset in (1., 10., -10., 150.001):
            action.offsets[signal] = offset
            self.compare(action,cfg,spec,180)
        copy = action.copy(); copy.green_times[signal+'_p1'] += .001; copy.green_times[signal+'_p3'] -= .001
        self.compare(copy,cfg,spec,180)
        self.compare(action,cfg,spec,180)
        stable = pickle.dumps((cfg,action))
        for mutation in ('clearance','order','segments','duration','total','minimum','live','writer'):
            other = deepcopy(cfg)
            if mutation == 'clearance': other.network.signal_actuation_contract['amber'] += .001
            if mutation == 'order':
                row=other.network.signal_actuation_contract['nodes'][signal];row['_order']=tuple(reversed(row['_order']))
            if mutation == 'segments':
                row=other.network.signal_actuation_contract['nodes'][signal]
                row['_segments']=tuple((p,()) if p=='p3' else (p,spans) for p,spans in row['_segments'])
            if mutation == 'duration': other.simulation.T_u=2.5
            if mutation == 'total': other.network.effective_green_total_by_signal[signal]+=.001
            if mutation == 'minimum': other.network.green_min=90.
            if mutation == 'live': other.network.live_phases_by_signal[signal]=['p1','p3']
            if mutation == 'writer': other.network.signal_actuation_contract['offset_writer']='intent_only'
            self.compare(action,other,spec,180)
        # Cache is external to the objects. The only differences are our explicit mutations.
        self.assertEqual(pickle.dumps((cfg,action)),stable)

    def test_invalid_candidate_after_valid_hit_preserves_exact_errors(self):
        cfg = deepcopy(self.cfg); signal='SC1004';spec={'phase':signal+'_p3'}
        self.compare(self.action,cfg,spec,180)
        for field, value in [('green',float('nan')),('green',float('inf')),('green',-.001),
                             ('green',90.001),('green',21.0001),('offset',float('nan')),
                             ('offset',float('inf')),('offset',None),('offset','bad')]:
            action=self.action.copy()
            if field=='green':action.green_times[signal+'_p3']=value
            else:action.offsets[signal]=value
            expected=self.compare(action,cfg,spec,180)
            self.assertEqual(expected[0],'error',(field,value))
        for duration in (0.,-1.,float('nan'),float('inf')):
            other=deepcopy(cfg);other.simulation.T_u=duration
            self.assertEqual(self.compare(self.action,other,spec,180)[0],'error')
        other=deepcopy(cfg);other.network.live_phases_by_signal[signal]=[]
        self.assertEqual(self.compare(self.action,other,spec,180)[0],'error')
        action=self.action.copy();action.green_times['SC109_p1']=1.
        self.assertEqual(self.compare(action,cfg,{'phase':'SC109_p2'},180)[0],'error')

    def test_writer_inputs_not_intent_alone(self):
        cfg=deepcopy(self.cfg);action=self.action.copy();spec={'phase':'SC1004_p3'}
        for writer in ('intent_only','production','test_only','experiment'):
            cfg.network.signal_actuation_contract['offset_writer']=writer
            for table,scalar in [(None,None),('',0.),('{"SC1004":17.25}',3.),('invalid',-9.),('[]',30.)]:
                action.diagnostics={offset_promotion.FORCED_ARM_TABLE_KEY:table,
                    offset_promotion.FORCED_ARM_DIAGNOSTIC_KEYS[0]:scalar}
                self.compare(action,cfg,spec,180)
        # Invalid mutable diagnostic is a bypass, never an identity-key hit.
        cfg.network.signal_actuation_contract['offset_writer']='test_only'
        action.diagnostics[offset_promotion.FORCED_ARM_TABLE_KEY]={}
        self.compare(action,cfg,spec,180)

    def test_forced_offset_presence_and_custom_equal_key_after_hit(self):
        cfg=deepcopy(self.cfg);signal='SC1004';spec={'phase':signal+'_p3'}
        cfg.network.signal_actuation_contract['offset_writer']='test_only'
        first,second=offset_promotion.FORCED_ARM_DIAGNOSTIC_KEYS
        a=self.action.copy();a.diagnostics={second:10.}
        b=self.action.copy();b.diagnostics={first:None,second:10.}
        self.assertEqual(actual.written_offset_sec(a,cfg,signal),10.)
        self.assertEqual(actual.written_offset_sec(b,cfg,signal),0.)
        distinct=[]
        for step in range(30):
            proposal.clear()
            left=self.compare(a,cfg,spec,step)
            right=self.compare(b,cfg,spec,step)
            self.compare(a,cfg,spec,step)
            if left!=right: distinct.append(step)
        self.assertEqual(distinct,[13,14,20,21])
        class BadFloatZero(int):
            def __float__(self): return float('nan')
        cfg.network.signal_actuation_contract['offset_writer']='experiment'
        a=self.action.copy();a.offsets[signal]=0.
        b=self.action.copy();b.offsets[signal]=BadFloatZero(0)
        proposal.clear();self.compare(a,cfg,spec,0)
        expected=self.compare(b,cfg,spec,0)
        self.assertEqual(expected[0:2],('error','OffsetPromotionError'))
        self.assertGreater(proposal.stats()['clock_bypasses'],0)
        self.compare(a,cfg,spec,0)

    def test_bounded_immutable_plan_identity_requires_exact_builtin_tree(self):
        class EqualInt(int):
            def __float__(self): return float('nan')
        tree=tuple([('p3',((2,'g',0.,1.),))])
        self.assertTrue(proposal._immutable_plan(tree))
        self.assertIs(proposal._PLAN_TREES[id(tree)],tree)
        # A proved object skips recursive work; equal new objects do not.
        with patch.object(proposal,'_immutable',wraps=proposal._immutable) as checked:
            self.assertTrue(proposal._immutable_plan(tree))
            self.assertEqual(checked.call_count,0)
            other=tuple([('p3',((2,'g',0.,1.),))])
            self.assertIsNot(tree,other)
            self.assertTrue(proposal._immutable_plan(other))
            self.assertEqual(checked.call_count,1)
        self.assertFalse(proposal._immutable_plan((('p3',((2,'g',EqualInt(0),1.),)),)))
        self.assertFalse(proposal._immutable_plan((['mutable'],)))
        self.assertFalse(proposal._immutable_plan([tree]))
        self.assertFalse(proposal._immutable_plan(((float('nan'),),)))
        proposal.clear()
        with patch.object(proposal,'MAX_PLAN_TREES',2):
            for n in range(4): self.assertTrue(proposal._immutable_plan(tuple([n])))
            self.assertEqual(len(proposal._PLAN_TREES),2)
        self.assertTrue(all(type(t) is tuple and id(t)==key for key,t in proposal._PLAN_TREES.items()))
        proposal.clear()
        self.assertEqual(len(proposal._PLAN_TREES),0)

    def test_write_clamp_and_decimal_fmod_boundary_after_hit(self):
        from evaluation.controllers import plant_cycle
        self.compare(self.action,self.cfg,{'phase':'SC1004_p3'},180)
        with patch.object(plant_cycle,'SIGNAL_GREEN_WRITE_CLAMP_SEC',(1.,20.)):
            self.assertEqual(self.compare(self.action,self.cfg,{'phase':'SC1004_p3'},180)[0],'error')
        cycle=150.001;sec=150001
        self.assertEqual(sec-math.floor(sec/cycle)*cycle,0.)
        self.assertNotEqual(sec % cycle,0.)
        cfg=deepcopy(self.cfg)
        for signal in cfg.network.signals:
            cfg.network.cycle_length_by_signal[signal]=cycle
            cfg.network.effective_green_total_by_signal[signal]=round(cycle-3*len(cfg.network.signal_live_phases(signal)),3)
        action=actual.prepare_control(self.action,cfg);action.offsets=dict.fromkeys(cfg.network.signals,0.)
        for phase in actual.PHASES:
            self.compare(action,cfg,{'phase':'SC1004_'+phase},30000)

    def test_generated_single_module_patch_function_exact(self):
        import ast
        from collections import OrderedDict
        from diagnostics.prepare_signal_clock_cache_patch import proposed_source
        if self.installed_clock_source['cache_installed']:
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
        for signal in self.cfg.network.signals:
            for phase in actual.PHASES:
                for step in (None,180,210,30000):
                    args=(self.action,self.cfg,{'phase':signal+'_'+phase},step)
                    self.assertEqual(outcome(namespace['phase_fraction'],*args),outcome(reference.phase_fraction,*args))
        self.assertGreater(namespace['clock_cache_info']()['clock_hits'],0)

    def test_off_native_unknown_and_unsignalized_preserve_dispatch(self):
        for phase in ('SC1004_p3','SC1004_unknown','SC404_p1','',None):
            for unsignalized in (False,True):
                spec={'phase':phase,'unsignalized':unsignalized}
                self.compare(self.action,self.cfg,spec,180)
                cfg=deepcopy(self.cfg);delattr(cfg.network,'signal_actuation_contract')
                self.compare(self.action,cfg,spec,180)
        from src.models import urban_queue_model as uqm
        cfg=deepcopy(self.cfg);delattr(cfg.network,'signal_actuation_contract')
        previous=uqm._phase_green_fraction
        for signal in cfg.network.signals:
            spec={'phase':signal+'_p3','intersection':signal}
            self.assertEqual(outcome(proposal.wrap(previous),self.action,cfg,spec,180),
                             outcome(previous,self.action,cfg,spec,180))
        # Non-selected native movement must call precisely the original wrapper.
        specs=[s for s in cfg.network.urban_movements.values() if not s.get('phase') and not s.get('unsignalized')]
        self.assertTrue(specs)
        for spec in specs[:10]:
            self.assertEqual(outcome(proposal.wrap(previous),self.action,cfg,spec,180),
                             outcome(previous,self.action,cfg,spec,180))

    def test_effective_total_fallback_preserves_getter_counters(self):
        from src.models import state
        cfg=deepcopy(self.cfg);signal='SC1004';spec={'phase':signal+'_p3'}
        cfg.network.effective_green_total_by_signal.pop(signal,None)
        cfg.network.cycle_length_by_signal.pop(signal,None)
        for function in (reference.phase_fraction,proposal.finite_only,proposal.validated_clock):
            state._CYCLE_LENGTH_FALLBACK_COUNTS.clear()
            expected=[outcome(function,self.action,cfg,spec,180) for _ in range(2)]
            counters=dict(state._CYCLE_LENGTH_FALLBACK_COUNTS)
            if function is reference.phase_fraction: baseline=(expected,counters)
            else:self.assertEqual((expected,counters),baseline)
        self.assertGreater(proposal.stats()['clock_bypasses'],0)

    def test_actual_local_profile_aliases_and_fresh_worker(self):
        from src.controllers import wu_faithful_follower as follower_module
        controller=adapter.build_priced_wu_link_controller(self.cfg,self.runtime[3])
        follower=controller.nash_solver
        previous=follower_module._phase_green_fraction
        results={}
        for signal in self.cfg.network.signals:
            greens={p:self.action.green_times[signal+'_'+p] for p in actual.PHASES}
            with patch.object(actual,'phase_fraction',reference.phase_fraction):
                expected=follower._offset_green_fractions_vec(signal,greens,10.,30,180)
            with patch.object(actual,'phase_fraction',proposal.validated_clock):
                actual_profile=follower._offset_green_fractions_vec(signal,greens,10.,30,180)
            self.assertEqual(pickle.dumps(expected),pickle.dumps(actual_profile))
            results[signal]=hashlib.sha256(pickle.dumps(actual_profile)).hexdigest()
        code='''import json,pickle,sys,hashlib,importlib
from unittest.mock import patch
from diagnostics.test_signal_clock_cache import proposal,reference,actual,adapter
from evaluation.controllers import runtime_setup
cfg,action,raw,detectors=pickle.loads(sys.stdin.buffer.read())
runtime_setup.install_worker_runtime(adapter,cfg,raw,detectors)
modules=[importlib.import_module(n) for n in ('src.models.urban_queue_model','src.controllers.distributed_coordinator','src.controllers.local_signal_plant','src.controllers.wu_distributed','src.controllers.wu_faithful_follower')]
out={}
canonical_checks=0
for signal in cfg.network.signals:
 for phase in proposal.PHASES:
  for step in (None,180,210,30000):
   spec={'phase':signal+'_'+phase}
   a=reference.phase_fraction(action,cfg,spec,step)
   # First test the installed canonical implementation through real worker
   # aliases, with no proposal substitution. This runs before and after apply.
   for module in modules:
    b=module._phase_green_fraction(action,cfg,spec,step)
    assert pickle.dumps(a)==pickle.dumps(b)
    canonical_checks+=1
   with patch.object(actual,'phase_fraction',proposal.validated_clock):
    for module in modules:
     b=module._phase_green_fraction(action,cfg,spec,step)
     assert pickle.dumps(a)==pickle.dumps(b)
   out[str((signal,phase,step))]=b
from pathlib import Path
installed_hash=hashlib.sha256(Path(actual.__file__).read_bytes()).hexdigest()
print(json.dumps({'values':out,'stats':proposal.stats(),'canonical_checks':canonical_checks,
 'canonical_sha256':installed_hash,'canonical_cache_stats':actual.clock_cache_info() if hasattr(actual,'clock_cache_info') else None},sort_keys=True))
'''
        result=subprocess.run([sys.executable,'-X','utf8','-c',code],input=pickle.dumps((self.cfg,self.action,self.runtime[4],self.runtime[2])),
            capture_output=True,cwd=ROOT,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr.decode('utf-8',errors='replace'))
        worker=json.loads(result.stdout)
        self.assertEqual(worker['canonical_sha256'],self.installed_clock_source['sha256'])
        self.assertEqual(worker['canonical_checks'],len(self.cfg.network.signals)*len(actual.PHASES)*4*5)
        if self.installed_clock_source['cache_installed']:
            self.assertGreater(worker['canonical_cache_stats']['clock_hits'],0)
            self.assertGreater(worker['canonical_cache_stats']['clock_misses'],0)
        else:
            self.assertIsNone(worker['canonical_cache_stats'])
        self.assertGreater(worker['stats']['clock_hits'],0)
        self.assertGreater(worker['stats']['clock_misses'],0)

    def test_bounded_cache_eviction_and_no_object_retention(self):
        import gc,weakref
        cfg=deepcopy(self.cfg);action=self.action.copy()
        cfg_ref,action_ref=weakref.ref(cfg),weakref.ref(action)
        with patch.object(proposal,'MAX_CLOCKS',3):
            for offset in range(8):
                action.offsets['SC1004']=float(offset)
                self.compare(action,cfg,{'phase':'SC1004_p3'},180)
            self.assertEqual(proposal.stats()['clocks'],3)
        del cfg,action;gc.collect()
        self.assertIsNone(cfg_ref());self.assertIsNone(action_ref())
        self.assertEqual(proposal._finite_fraction.cache_info().maxsize,proposal.MAX_INTERVALS)


if __name__=='__main__':
    unittest.main()
