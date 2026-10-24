"""47 lane1 is not controlled by the straight heads on lanes2-4."""
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'vendor/NumSim-mine'))
from evaluation.controllers.physical_movement_routes import configure_phase_authority

CASE = ROOT/'diagnostics/repin_v3c3_review_20261001/goal8_265/head47_right/authority.json'
NAME = 'SC1003_S_SC1004_to_E_SC105'

class HeadFree47AuthorityTests(unittest.TestCase):
    def fixture(self):
        d = json.loads(CASE.read_bytes()); d['by_movement'] = {}; d.pop('head_free_movements')
        specs = {m:dict(r['expected_spec'], signal=m.split('_')[0], beta=.5)
                 for m,r in d['unsignalized_movements'].items()}
        cfg = SimpleNamespace(network=SimpleNamespace(urban_movements=specs,
            movement_capacity_by_movement_veh_h={NAME:206.53061224489795}))
        plan = json.loads((ROOT/d['selected_plan']['path']).read_bytes())
        raw = dict(network_path=str(ROOT/d['network']['path']), run_provenance={'files':{'network':d['network']}})
        return d,cfg,plan,raw

    def apply(self,d,cfg,plan,raw):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'authority.json';p.write_text(json.dumps(d),encoding='utf-8')
            return configure_phase_authority(cfg,{'urban':{'movements':{'physical_phase_authority':str(p)}}},
                plan,state_json=raw)

    def test_only_gating_changes_capacity_and_beta_stay(self):
        d,cfg,plan,raw=self.fixture();before=copy.deepcopy(cfg.network.urban_movements)
        caps=copy.deepcopy(cfg.network.movement_capacity_by_movement_veh_h)
        self.apply(d,cfg,plan,raw)
        for m in d['unsignalized_movements']:before[m]['unsignalized']=True
        self.assertEqual(cfg.network.urban_movements,before)
        self.assertEqual(cfg.network.movement_capacity_by_movement_veh_h,caps)

    def test_old_document_leaves_right_unchanged(self):
        d,cfg,plan,raw=self.fixture();del d['unsignalized_movements'][NAME]
        before=copy.deepcopy(cfg.network.urban_movements[NAME]);self.apply(d,cfg,plan,raw)
        self.assertEqual(cfg.network.urban_movements[NAME],before)

    def test_wrong_lane_route_head_or_conflict_fails_without_commit(self):
        for change in ('lane','route','head','conflict','relation'):
            with self.subTest(change=change):
                d,cfg,plan,raw=self.fixture();before=copy.deepcopy(cfg.network.urban_movements)
                row=d['unsignalized_movements'][NAME]
                if change=='lane':row['connector']['source_lane']=2
                if change=='route':row['native_routes']=['1122:1']
                if change=='head':row['source_heads'][0]['lane']=1
                if change=='conflict':row['conflicts']['2583']['status']='ONE'
                if change=='relation':row['source_head_relation']='upstream'
                with self.assertRaises(ValueError):self.apply(d,cfg,plan,raw)
                self.assertEqual(cfg.network.urban_movements,before)
