"""Shared69/input1101 profile derivation only; no model imports or execution."""
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from diagnostics.prepare_selected_control_demand import package,sha

ROOT=Path(__file__).resolve().parents[1]
TUNING=ROOT/'diagnostics/contract_candidate_configs_v4/n7_area_beta0.json'
SELECTED=ROOT/'diagnostics/demand_sweep/fw070_urban040/prepared'


class SharedProfile(unittest.TestCase):
    def test_physical_declaration_and_original_bytes_preserved(self):
        original=json.loads(TUNING.read_text(encoding='utf-8-sig'))
        source=ROOT/original['urban']['shared_approach']; before=source.read_bytes()
        old=json.loads(before.decode('utf-8-sig'))
        profile,rows,report,native,config,shared=package(SELECTED,TUNING,ROOT/'diagnostics/selected_control_demand/synthetic_r02_only')
        self.assertEqual(shared['demand_profile'],native['demand_profile'])
        self.assertEqual(report['source_sha256'][str(source.resolve())],sha(source))
        self.assertEqual(shared['selected_demand_derivation']['source_declaration']['sha256'],sha(source))
        shared.pop('selected_demand_derivation'); shared['demand_profile']=old['demand_profile']
        self.assertEqual(shared,old)  # branches, finite storage, geometry and all pins
        self.assertEqual(source.read_bytes(),before)
        self.assertEqual(config['urban']['shared_approach'],'diagnostics/selected_control_demand/synthetic_r02_only/shared_approach.json')

    def test_input1101_six_intervals_use_selected_profile_sha_and_factor(self):
        profile,rows,report,_,_,shared=package(SELECTED,TUNING,ROOT/'diagnostics/selected_control_demand/synthetic_r02_only')
        actual_sha=hashlib.sha256(profile.encode('ascii')).hexdigest()
        self.assertEqual(shared['demand_profile']['sha256'],actual_sha)
        old=json.loads((ROOT/'diagnostics/shared_approach_ver2.json').read_text(encoding='utf-8-sig'))
        self.assertNotEqual(old['demand_profile']['sha256'],actual_sha)  # reproduces old pin guard condition
        factors={r['role']:float(r['multiplier']) for r in csv.DictReader(io.StringIO(profile))}
        subset=[r for r in rows if r['input_no']=='1101']
        self.assertEqual(len(subset),6); self.assertEqual(factors['no:1101'],0.4)
        for row in subset:
            self.assertEqual(row['before_vph']*factors['no:1101'],row['profile_vph'])
            self.assertLessEqual(abs(row['profile_vph']-row['selected_vph']),1e-10)

    def test_network_rebinding_is_still_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            directory=Path(directory)
            cfg=json.loads(TUNING.read_text(encoding='utf-8-sig'))
            shared=json.loads((ROOT/cfg['urban']['shared_approach']).read_text(encoding='utf-8-sig'))
            shared['network']['sha256']='0'*64
            source=directory/'shared.json';source.write_text(json.dumps(shared))
            cfg['urban']['shared_approach']=str(source)
            tuning=directory/'config.json';tuning.write_text(json.dumps(cfg))
            with self.assertRaisesRegex(ValueError,'shared physical declaration'):
                package(SELECTED,tuning,directory/'out')


if __name__=='__main__': unittest.main()
