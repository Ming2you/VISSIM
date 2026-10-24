"""An upstream peel-off must not inherit the bypassed signal's green gate."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
import ast

from evaluation.controllers.physical_movement_routes import configure_phase_authority
from evaluation.controllers import physical_movement_routes as physical

ROOT=Path(__file__).resolve().parents[3]
EVIDENCE=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/baseline_reproduction_20260929/ramp_entry_space/peeloff10121/authority.json'
NAME='SC1001_N_SC2002_to_W_RAMP'


class PeeloffAuthorityTests(unittest.TestCase):
    def fixture(self):
        document=json.loads(EVIDENCE.read_bytes())
        document['by_movement']={}
        document.pop('head_free_movements')
        specs={name:dict(row['expected_spec'],signal=name.split('_')[0],beta=.25)
               for name,row in document['unsignalized_movements'].items()}
        cfg=SimpleNamespace(network=SimpleNamespace(urban_movements=specs))
        plan=json.loads((ROOT/document['selected_plan']['path']).read_bytes())
        raw={'network_path':str(ROOT/document['network']['path']),
             'run_provenance':{'files':{'network':document['network']}}}
        return document,cfg,plan,raw

    def apply(self,document,cfg,plan,raw):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'authority.json';p.write_text(json.dumps(document),encoding='utf8')
            return configure_phase_authority(cfg,{'urban':{'movements':{'physical_phase_authority':str(p)}}},
                                             plan,state_json=raw)

    def test_only_authority_changes_with_all_native_geometry_checks(self):
        document,cfg,plan,raw=self.fixture();before=copy.deepcopy(cfg.network.urban_movements)
        result=self.apply(document,cfg,plan,raw)
        for name in document['unsignalized_movements']:before[name]['unsignalized']=True
        self.assertEqual(cfg.network.urban_movements,before)
        self.assertEqual(result['physical_unsignalized_authority_corrected_count'],5)
        self.assertEqual(cfg.network.urban_movements[NAME]['phase'],'SC1001_p1')

    def test_old_document_keeps_new_movement_unchanged(self):
        document,cfg,plan,raw=self.fixture();del document['unsignalized_movements'][NAME]
        before=copy.deepcopy(cfg.network.urban_movements[NAME]);self.apply(document,cfg,plan,raw)
        self.assertEqual(cfg.network.urban_movements[NAME],before)

    def test_old_authority_document_matches_archived_function_exactly(self):
        document,cfg,plan,raw=self.fixture();del document['unsignalized_movements'][NAME]
        tree=ast.parse((EVIDENCE.parent/'physical_movement_routes.py.before.txt').read_text(encoding='utf8'))
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='configure_phase_authority')
        namespace=dict(vars(physical));exec(compile(ast.Module(body=[node],type_ignores=[]),'<before-authority>','exec'),namespace)
        previous=copy.deepcopy(cfg)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'authority.json';path.write_text(json.dumps(document),encoding='utf8')
            tuning={'urban':{'movements':{'physical_phase_authority':str(path)}}}
            old=namespace['configure_phase_authority'](previous,tuning,plan,state_json=raw)
            new=configure_phase_authority(cfg,tuning,plan,state_json=raw)
        self.assertEqual(old,new)
        self.assertEqual(vars(previous.network),vars(cfg.network))

    def test_bad_route_head_receiver_and_unknown_movement_fail(self):
        for change in ('route','head','receiver','unknown'):
            with self.subTest(change=change):
                document,cfg,plan,raw=self.fixture();row=document['unsignalized_movements'][NAME]
                if change=='route':row['native_routes']=['1116:1']
                if change=='head':row['source_heads'][0]['pos_m']=400.
                if change=='receiver':row['expected_spec']['receiving_link']='elsewhere'
                if change=='unknown':document['unsignalized_movements']['unreviewed']=row
                with self.assertRaises(ValueError):self.apply(document,cfg,plan,raw)


if __name__=='__main__':unittest.main()
