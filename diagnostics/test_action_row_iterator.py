"""Actual canonical writer against immutable 74/213-row source fixtures.

Import the adapter without its model bootstrap. The baseline executes only its
preserved original method/helpers; the candidate calls the installed functions.
No traffic model, endpoint, COM session or original run directory is required.
"""
from __future__ import annotations
import ast
import copy
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
import zipfile
from unittest.mock import patch
from collections.abc import Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.controllers import action_csv_schema, signal_group_plan, plant_cycle, offset_promotion, diagnostic_profile
from diagnostics.prepare_action_row_iterator_patch import OUT, sha

INSTALLED = ROOT / 'diagnostics/action_row_iterator_installed_v1'

HELPERS = {'clamp','nearest','_as_float','_mapping','_segment_model_coordinates',
           '_segment_dsd_controls','_signal_rows_for_mapping','plan_live_phases',
           'signal_group_action_rows','_action_csv_metadata','_meter_flow_vph',
           '_measured_meter_allocation','real_world_ramp_meter_actions',
           'physical_ramp_actions','green_from_release_map'}
SIGNAL_CHECKS = {'enabled','bounds','validate_vector','validate_control','validate_writer','written_offset_sec'}


def selected(source, names, *, assignments=()):
    nodes = [n for n in ast.parse(source).body if (isinstance(n, ast.FunctionDef) and n.name in names)
             or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in assignments for t in n.targets))]
    if {n.name for n in nodes if isinstance(n, ast.FunctionDef)} != set(names):
        raise ValueError('Exact function fixture is incomplete')
    return '\n\n'.join(ast.get_source_segment(source,n) for n in nodes)+'\n'


def freeze_fixtures():
    """One-time small evidence capture. Existing captures are never rewritten."""
    target = OUT/'fixtures'
    if target.exists():
        raise ValueError('Fixture already exists; historical bytes are immutable')
    target.mkdir()
    sources = {}
    def read(relative):
        path = ROOT/relative
        raw = path.read_bytes(); sources[relative] = sha(raw)
        return raw
    adapter = read('evaluation/controllers/vissim_stackelberg_adapter.py').decode('utf-8-sig')
    helpers = selected(adapter,HELPERS,assignments=('METER_PER_LANE_VEH_PER_CYCLE_DEFAULT','METER_LANES_DEFAULT','SEGMENT_TO_MODEL'))
    (target/'adapter_helpers.py').write_text(helpers,encoding='utf-8')
    # This is a function-level fixture, not a cache/clock regression or source
    # pin: the parent may swap the full original/cached module during its trace.
    clock = (ROOT/'evaluation/controllers/signal_actuation_contract.py').read_text(encoding='utf-8-sig')
    frozen_signal = selected(clock,SIGNAL_CHECKS)
    (target/'signal_writer_checks.py').write_text(frozen_signal,encoding='utf-8')
    state = read('vendor/NumSim-mine/src/models/state.py').decode('utf-8-sig')
    (target/'segment_vsl.py').write_text(selected(state,{'segment_vsl'}),encoding='utf-8')
    projection = read('plant/src/vissim_strict/physical_projection.py').decode('utf-8-sig')
    (target/'thaw_json.py').write_text(selected(projection,{'_thaw','thaw_json'}),encoding='utf-8')
    mapping = json.loads(read('evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'))
    plan = json.loads(read('outputs/signal_group_actuation_plan_mainline_20260825.json'))
    tuning = json.loads(read('diagnostics/contract_candidate_configs_v4/n7_area_beta300.json'))
    parameters = json.loads(read('evaluation/parameters.json'))
    fixture = {'mapping':mapping, 'plan':plan, 'actuation':tuning['actuation'],
               'vsl_set':tuning['config_overrides']['freeway_follower']['vsl_set'],
               'cycle_length':parameters['network']['cycle_length'],
               'green_min':parameters['network']['green_min'],
               'ramp_capacity_veh_h':parameters['network']['ramp_capacity_veh_h'], 'actions':{}}
    run = 'codex_contract_beta300_s13_1050_v3_20260910'
    for stamp in ('000001','000900'):
        folder = f'evaluation/runs/{run}/decisions_{run}'
        action = json.loads(read(f'{folder}/action_{stamp}.json'))
        # Preserve the complete four lever/diagnostic payload and only the
        # metadata fields consumed by this writer. No state/trajectory/model.
        fixture['actions'][stamp] = {
            'control':{k:action[k] for k in ('vsl','green_times','offsets','ramp_metering','diagnostics')},
            'metadata':{k:v for k,v in action['metadata'].items() if k in (
                'controller_status','controller_variant','suppress_signal_rows','offset_writer',
                'physical_signal_contract_enabled','offset_experiment','physical_projection_provenance')}}
        (target/f'action_{stamp}.csv').write_bytes(read(f'{folder}/action_{stamp}.csv'))
    (target/'writer_inputs.json').write_text(json.dumps(fixture,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    evidence = {'source_sha256':sources, 'signal_writer_functions_sha256':sha(frozen_signal.encode()),
                'source_scope':'Only writer input fields; signal clock implementation/phase_fraction/cache deliberately excluded',
                'files_sha256':{p.name:sha(p.read_bytes()) for p in target.iterdir()}}
    (target/'manifest.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')


def execute(source, ns, name):
    code = 'from __future__ import annotations\n'+source
    exec(compile(code,name,'exec'),ns)


def load():
    fixture = OUT/'fixtures'
    manifest = json.loads((fixture/'manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest['files_sha256'].items():
        if sha((fixture/name).read_bytes()) != expected:
            raise ValueError(f'Frozen fixture changed: {name}')
    ns = dict(Mapping=Mapping,math=math,json=json,csv=csv,Path=Path,
              signal_group_plan=signal_group_plan,action_csv_schema=action_csv_schema,
              plant_cycle=plant_cycle,offset_promotion=offset_promotion,diagnostic_profile=diagnostic_profile,
              RUNNER_CLEARANCE_SEC=plant_cycle.runner_clearance_sec())
    sns = dict(math=math,plant_cycle=plant_cycle,offset_promotion=offset_promotion,PHASES=signal_group_plan.MODEL_PHASES)
    execute((fixture/'signal_writer_checks.py').read_text(encoding='utf-8'),sns,'<frozen-signal-writer-checks>')
    ns['signal_actuation_contract'] = SimpleNamespace(**{k:sns[k] for k in SIGNAL_CHECKS})
    for name in ('thaw_json.py','segment_vsl.py','adapter_helpers.py'):
        execute((fixture/name).read_text(encoding='utf-8'),ns,f'<frozen-{name}>')
    installed = json.loads((INSTALLED/'manifest.json').read_text(encoding='utf-8'))
    archive = INSTALLED/'baseline_writer.zip'
    if sha(archive.read_bytes()) != installed['baseline_zip_sha256']:
        raise ValueError('Installed baseline archive changed')
    with zipfile.ZipFile(archive) as z:
        baseline = z.read('original_write_action_csv.py')
    if sha(baseline) != installed['original_writer_raw_sha256']:
        raise ValueError('Installed original writer changed')
    old = dict(ns)
    execute(baseline.decode('utf-8'),old,'<preserved-original-canonical-writer>')
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    new = vars(adapter)
    return json.loads((fixture/'writer_inputs.json').read_text(encoding='utf-8')),old,new


def geometry(data):
    nodes = {r['id']:data['plan']['controllers'][str(r['sc_no'])] for r in data['mapping']['signals']}
    phases = signal_group_plan.MODEL_PHASES
    live = {s:tuple(p for p in phases if n['phase_signal_groups'][p] and n['axis_green_sec'][p]>0) for s,n in nodes.items()}
    amber, all_red = plant_cycle.runner_clearance_sec()
    cycle = data['cycle_length']; low=data['green_min']
    total={s:cycle-len(live[s])*(amber+all_red) for s in nodes}
    net=SimpleNamespace(signals=tuple(nodes),cycle_length=cycle,green_min=low,
                        signal_live_phases=lambda s:live[s],signal_effective_green_total=lambda s:total[s],
                        signal_actuation_contract={'nodes':copy.deepcopy(nodes),'amber':amber,'all_red':all_red,'offset_writer':'experiment'},
                        ramp_capacity_veh_h=copy.deepcopy(data['ramp_capacity_veh_h']))
    return SimpleNamespace(network=net,freeway_follower=SimpleNamespace(vsl_set=data['vsl_set']))


class RowIteratorTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'RW_OFFSET_WRITER':'experiment'}); self.env.start(); self.addCleanup(self.env.stop)
        self.data,self.old,self.new=load();self.cfg=geometry(self.data)
        # The real writer accepts this callback as an argument. Keep the frozen
        # model-free scalar lookup only as test input, never replace its helpers.
        self.callback = patch.dict(self.new, {'segment_vsl':self.old['segment_vsl']})
        self.callback.start(); self.addCleanup(self.callback.stop)
        self.control=SimpleNamespace(**copy.deepcopy(self.data['actions']['000900']['control']))
        self.metadata=copy.deepcopy(self.data['actions']['000900']['metadata'])
        self.mapping=copy.deepcopy(self.data['mapping']);self.plan=copy.deepcopy(self.data['plan']);self.actuation=copy.deepcopy(self.data['actuation'])

    def call_writer(self,ns,control=None,metadata=None):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'nested'/'action.csv'
            ns['write_action_csv'](path,control or self.control,self.cfg,self.mapping,ns['segment_vsl'],
                                   self.metadata if metadata is None else metadata,self.actuation,self.plan,
                                   self.cfg.network.signal_actuation_contract['offset_writer'] if self.cfg.network.signal_actuation_contract else 'intent_only')
            return path.read_bytes()

    def rows(self,control=None,metadata=None):
        c=control or self.control
        values=[self.old['segment_vsl'](c,*self.old['_segment_model_coordinates'](str(s['segment_id']),s),self.cfg) for s in self.mapping['segments']]
        resolved=self.old['real_world_ramp_meter_actions'](copy.deepcopy(c),self.cfg,self.actuation,self.mapping) if self.mapping.get('ramp_meters') else self.old['physical_ramp_actions'](copy.deepcopy(c),self.cfg,self.actuation)
        return list(self.new['iter_action_csv_rows'](c,self.cfg,self.mapping,values,resolved,
                    self.metadata if metadata is None else metadata,self.actuation,self.plan,
                    self.cfg.network.signal_actuation_contract['offset_writer'] if self.cfg.network.signal_actuation_contract else 'intent_only'))

    def assert_parity(self,control=None,metadata=None):
        c=control or self.control; before=copy.deepcopy(c)
        old_control=copy.deepcopy(c);new_control=copy.deepcopy(c)
        a=self.call_writer(self.old,old_control,metadata);b=self.call_writer(self.new,new_control,metadata)
        self.assertEqual(a,b);self.assertEqual(old_control,new_control);self.assertEqual(c,before)
        text=io.StringIO(newline='');w=csv.DictWriter(text,fieldnames=action_csv_schema.ACTION_CSV_FIELDS);w.writeheader();w.writerows(self.rows(c,metadata))
        self.assertEqual(a,text.getvalue().encode('utf-8'))
        return a

    def test_actual_warmup74_and_control213_binary_exact(self):
        for stamp,count in [('000001',74),('000900',213)]:
            with self.subTest(stamp=stamp):
                a=self.data['actions'][stamp];c=SimpleNamespace(**copy.deepcopy(a['control']))
                actual=self.assert_parity(c,a['metadata']);reference=(OUT/'fixtures'/f'action_{stamp}.csv').read_bytes()
                self.assertEqual(reference,actual)
                rows=list(csv.DictReader(io.StringIO(actual.decode('utf-8'))));self.assertEqual(len(rows),count)
                self.assertFalse(actual.startswith(b'\xef\xbb\xbf'));self.assertEqual(actual.count(b'\n'),actual.count(b'\r\n'))
                self.assertEqual(actual.split(b'\r\n')[0],(','.join(action_csv_schema.ACTION_CSV_FIELDS)).encode())

    def test_sc5_red_only_not_new_green_rows_and_all_addresses(self):
        rows=self.rows();ref=list(csv.DictReader(io.StringIO((OUT/'fixtures/action_000900.csv').read_text(encoding='utf-8'))))
        self.assertEqual([(r['kind'],r['id']) for r in rows],[(r['kind'],r['id']) for r in ref])
        sg5=[r for r in rows if r['kind']=='signal_sg' and r['sc_no']==5]
        self.assertEqual({str(r['dsd_no']) for r in sg5},set(map(str,range(1,9))))
        self.assertFalse({str(r['dsd_no']) for r in sg5}&set(self.plan['controllers']['5']['red_only_signal_groups']))
        self.assertEqual(sum(r['kind']=='vsl' for r in rows),66);self.assertEqual(sum(r['kind']=='ramp_meter' for r in rows),8)
        self.assertEqual(sum(r['kind']=='signal_sg' for r in rows),122)

    def test_iterator_does_not_call_allocators_or_vsl_callback_or_mutate_inputs(self):
        c=copy.deepcopy(self.control); values=[120.]*len(self.mapping['segments'])
        resolved=self.old['real_world_ramp_meter_actions'](copy.deepcopy(c),self.cfg,self.actuation,self.mapping)
        frozen=copy.deepcopy((c,self.mapping,values,resolved,self.metadata,self.actuation,self.plan))
        def forbidden(*args,**kwargs): raise AssertionError('Pure iterator called runtime preparation')
        with patch.dict(self.new,{k:forbidden for k in ('real_world_ramp_meter_actions','physical_ramp_actions','segment_vsl','_measured_meter_allocation')}):
            rows=list(self.new['iter_action_csv_rows'](c,self.cfg,self.mapping,values,resolved,self.metadata,self.actuation,self.plan,'experiment'))
        self.assertEqual(len(rows),213);self.assertEqual(frozen,(c,self.mapping,values,resolved,self.metadata,self.actuation,self.plan))
        rows[0]['speed_kph']=40.;self.assertEqual(values,[120.]*len(values))

    def test_preparation_callback_count_order_and_meter_diagnostics_retained(self):
        self.control.diagnostics={k:v for k,v in self.control.diagnostics.items() if not k.startswith('rw_meter_')}
        self.control.ramp_metering={k:300. for k in self.control.ramp_metering}
        events=[]
        for ns in (self.old,self.new):
            log=[]; sv=ns['segment_vsl']; meter=ns['real_world_ramp_meter_actions']
            def vsl(c,l,i,cfg): log.append(('vsl',l,i)); return sv(c,l,i,cfg)
            def meters(*args): log.append(('meter',));return meter(*args)
            with patch.dict(ns,{'segment_vsl':vsl,'real_world_ramp_meter_actions':meters}):
                c=copy.deepcopy(self.control);b=self.call_writer(ns,c);events.append((log,c,b))
        self.assertEqual(events[0],events[1]);self.assertEqual(events[0][0][-1],('meter',))
        self.assertEqual(len(events[0][0]),len(self.mapping['segments'])+1)
        self.assertIn('rw_meter_green_RM_C10480',events[0][1].diagnostics)

    def test_closed_and_asymmetric_meter_schedule_preserved(self):
        mids=[m['id'] for m in self.mapping['ramp_meters']]
        for i,mid in enumerate(mids): self.control.diagnostics['rw_meter_green_'+mid]=float([0,2,3,4,5,6,9,10][i])
        self.assert_parity()
        rows=[r for r in self.rows() if r['kind']=='ramp_meter']
        self.assertEqual([r['green_sec'] for r in rows],[0.,2.,3.,4.,5.,6.,9.,10.])
        self.assertEqual(rows[0]['rate_vph'],0.)

    def test_vsl_all_addresses_nonuniform_and_rounding_preserved(self):
        for i,s in enumerate(self.mapping['segments']):
            l,j=self.old['_segment_model_coordinates'](str(s['segment_id']),s)
            self.control.vsl[f'{l}__seg{j}']=[80.,100.,120.,90.,110.][i%5]
        self.assert_parity()
        self.assertEqual({r['speed_kph'] for r in self.rows() if r['kind']=='vsl'},{80.,100.,120.})

    def test_metadata_quoted_unicode_provenance_is_separate_from_physical(self):
        self.cfg.network.signal_actuation_contract=None
        a={'controller_variant':'wu-link','controller_status':'ok,한글"\nnext','physical_projection_provenance':{'x':['가',{'b':1}]}}
        b=copy.deepcopy(a);b['physical_projection_provenance']['x'][1]['b']=2
        self.assert_parity(metadata=a);self.assert_parity(metadata=b)
        ar=self.rows(metadata=a);br=self.rows(metadata=b)
        self.assertEqual([{k:v for k,v in r.items() if k!='metadata'} for r in ar],[{k:v for k,v in r.items() if k!='metadata'} for r in br])
        self.assertNotEqual(ar[0]['metadata'],br[0]['metadata'])

    def test_signal_suppression_no_plan_and_legacy_two_meter_fallback(self):
        self.assertEqual(len(list(csv.DictReader(io.StringIO(self.assert_parity(metadata={**self.metadata,'suppress_signal_rows':True}).decode())))),74)
        self.cfg.network.signal_actuation_contract=None;self.plan=None
        self.assertEqual(len(self.rows(metadata={'controller_variant':'wu-link'})),91)
        self.mapping.pop('ramp_meters');rows=self.rows(metadata={'controller_variant':'wu-link'})
        self.assertEqual([(r['id'],r['sc_no']) for r in rows if r['kind']=='ramp_meter'],[('D',6),('F',7)])
        self.assert_parity(metadata={'controller_variant':'wu-link'})

    def test_short_prepared_vsl_rejected_and_forced_arm_authority_preserved(self):
        with self.assertRaisesRegex(ValueError,'ordered segment'):
            list(self.new['iter_action_csv_rows'](self.control,self.cfg,self.mapping,[120.],{},self.metadata,self.actuation,self.plan,'experiment'))
        with self.assertRaisesRegex(ValueError,'ordered physical meter'):
            list(self.new['iter_action_csv_rows'](self.control,self.cfg,self.mapping,[120.]*len(self.mapping['segments']),{},self.metadata,self.actuation,self.plan,'experiment'))
        self.control.diagnostics['diagnostic_forced_signal_offset_sec']=10.
        self.cfg.network.signal_actuation_contract=None
        for ns in (self.old,self.new):
            with self.assertRaises(offset_promotion.OffsetPromotionError): self.call_writer(ns)

    def test_actual_canonical_functions_without_model_bootstrap(self):
        from evaluation.controllers import vissim_stackelberg_adapter as adapter
        self.assertIs(self.new['write_action_csv'], adapter.write_action_csv)
        self.assertIs(self.new['iter_action_csv_rows'], adapter.iter_action_csv_rows)
        self.assertEqual(adapter.write_action_csv.__module__, adapter.__name__)
        self.assertEqual(adapter.iter_action_csv_rows.__module__, adapter.__name__)
        # Other suites may already have bootstrapped NumSim in this process.
        # Independently prove that importing the real adapter needs no model.
        code = '''import json, pathlib, sys
root = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
from evaluation.controllers import vissim_stackelberg_adapter as adapter
expected = root / 'evaluation/controllers/vissim_stackelberg_adapter.py'
assert pathlib.Path(adapter.__file__).resolve() == expected
for name in ('write_action_csv', 'iter_action_csv_rows'):
    function = getattr(adapter, name)
    assert function.__module__ == adapter.__name__
    assert pathlib.Path(function.__code__.co_filename).resolve() == expected
models = [name for name in sys.modules if name == 'src' or name.startswith('src.')]
assert not models, models
print(json.dumps({'actual_adapter': str(expected), 'model_modules': models}))
'''
        result = subprocess.run(
            [sys.executable, '-I', '-B', '-X', 'utf8', '-c', code, str(ROOT)],
            cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        evidence = json.loads(result.stdout)
        self.assertEqual(Path(evidence['actual_adapter']), Path(adapter.__file__).resolve())
        self.assertEqual(evidence['model_modules'], [])


if __name__=='__main__':
    if '--freeze-fixtures' in sys.argv:
        freeze_fixtures()
    else:
        unittest.main()
