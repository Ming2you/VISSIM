"""Actual stopped150s evidence, exact serializer matching and strict identity."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from diagnostics import test_signal_observation_window_patch as harness
from evaluation.controllers import signal_head_observation as observed

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT/'diagnostics/fixtures/observer_precision_failure_v1.zip'


def fixture_bytes():
    proof = json.loads(ARCHIVE.with_suffix('.manifest.json').read_text(encoding='utf-8'))
    if hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() != proof['sha256']:
        raise ValueError('Exact stopped-run fixture archive changed')
    with zipfile.ZipFile(ARCHIVE) as stream:
        expected = {'state_000150.json','action_000001.json','run_provenance.json','tuning.json','index.json'}
        if set(stream.namelist()) != expected or len(stream.namelist()) != len(expected):
            raise ValueError('Unexpected/duplicate archive member')
        index = json.loads(stream.read('index.json'))
        data = {name:stream.read(name) for name in expected if name != 'index.json'}
    for name,blob in data.items():
        if hashlib.sha256(blob).hexdigest() != index['files'][name]['sha256']:
            raise ValueError('Original raw fixture bytes changed')
    return data,index


def relocated_fixture(directory):
    data,index = fixture_bytes()
    destination = Path(directory)
    # Paths are the only changed fields. Exact original bytes remain in ZIP.
    aliases = {index['files']['run_provenance.json']['original_path']:str(destination/'run_provenance.json'),
               index['files']['tuning.json']['original_path']:str(destination/'tuning.json')}
    def relocate(value):
        if isinstance(value,dict):return {k:relocate(v) for k,v in value.items()}
        if isinstance(value,list):return [relocate(v) for v in value]
        if isinstance(value,str):
            if value in aliases:return aliases[value]
            prefix=index['original_root']
            if value.startswith(prefix+'\\') or value.startswith(prefix+'/'):
                return str(ROOT)+value[len(prefix):]
        return value
    for name,blob in data.items():
        if name == 'tuning.json':(destination/name).write_bytes(blob)
        else:(destination/name).write_text(json.dumps(relocate(json.loads(blob.decode('utf-8-sig'))),ensure_ascii=False),encoding='utf-8')
    return destination/'tuning.json',destination/'state_000150.json',destination/'action_000001.json'


class HeadPrecisionTests(unittest.TestCase):
    def test_all235_actual_heads_have_only_serializer_position_difference(self):
        data,_ = fixture_bytes();raw=json.loads(data['state_000150.json'])
        network=ROOT/'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'
        nodes={n.get('no'):n for n in ET.parse(network).getroot().findall('./signalHeads/signalHead')}
        rows=raw['local_observation']['signal_observation_window']['heads'];different=[]
        self.assertEqual(len(rows),235)
        for row in rows:
            node=nodes[row['head_id']];position=float(node.get('pos'))
            self.assertEqual(node.get('lane'),row['link']+' '+str(row['lane']))
            self.assertEqual(node.get('sg'),row['sc']+' '+row['sg'])
            self.assertEqual(row['position_m'],observed.serialized_head_position(position))
            if row['position_m'] != position:different.append(abs(row['position_m']-position))
        self.assertEqual(len(different),116)
        self.assertEqual(max(different),4.547473508864641e-12)

    def test_actual150_canonical_runtime_accepts_relocated_raw_and_keeps_input_bytes(self):
        from diagnostics.probe_model_area_integration import build_projected
        with tempfile.TemporaryDirectory() as directory:
            config,state,previous=relocated_fixture(directory)
            before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in (config,state,previous)}
            _,_,_,_,_,_,metadata=build_projected(config,state,previous,fixture_inputs=False)
            self.assertEqual(metadata['head_observation_enabled'],1)
            self.assertEqual(metadata['head_observation_invalid_window'],0)
            self.assertEqual(metadata['head_observation_groups_updated'],0)
            self.assertGreater(metadata['head_observation_waiting_second_window'],0)
            self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in before})

    def test_changed_identity_and_one_serialized_coordinate_unit_still_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg,raw,plan,dist=harness.InstalledConsumerTests().fixture(directory)
            for key,value in (('link','67'),('lane',2),('sc','1005'),('sg','7'),
                              ('position_m',100.000000000001),('position_m',float('nan')),
                              ('position_m',True)):
                changed=deepcopy(raw);changed['local_observation']['signal_observation_window']['heads'][0][key]=value
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                    observed.install(deepcopy(cfg),changed,None,{'through':200.0},plan,dist,harness.OPTIONS)

    def test_actual_vbs_serializer_matches_python_expected_canonicalization(self):
        data,_ = fixture_bytes();raw=json.loads(data['state_000150.json'])
        nodes={n.get('no'):n for n in ET.parse(ROOT/'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx').getroot().findall('./signalHeads/signalHead')}
        source=(ROOT/'scripts/run_real_world_stackelberg_controller.vbs').read_text(encoding='utf-8-sig')
        script='Dim JSON_DECIMAL_SEPARATOR\nJSON_DECIMAL_SEPARATOR="."\n'
        script+=harness.procedure(source,'JsonDoubleInvariant')+harness.procedure(source,'B1aSignificantDigitCount')
        rows=raw['local_observation']['signal_observation_window']['heads']
        script+='\n'.join('WScript.Echo JsonDoubleInvariant(CDbl("'+nodes[r['head_id']].get('pos')+'"))' for r in rows)
        values=[float(x) for x in harness.run_vbs(script).splitlines() if x.strip()]
        self.assertEqual(values,[r['position_m'] for r in rows])
        self.assertEqual(values,[observed.serialized_head_position(float(nodes[r['head_id']].get('pos'))) for r in rows])


if __name__=='__main__':unittest.main()
