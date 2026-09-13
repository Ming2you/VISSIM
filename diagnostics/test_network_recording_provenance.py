"""Small installed-source tests; no model, COM, native run or asset copying."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from evaluation.controllers import network_provenance as n

SOURCE = b'''<?xml version="1.0" encoding="UTF-8"?>
<network><evaluation other="same"><scDetRec title='writeFile="false"' writeFile="false"/></evaluation>
<links><link no="2" name="geometry"/></links><vehicleInputs><input volume="800"/></vehicleInputs>
<vehicleRoutes><route target="5"/></vehicleRoutes><signalControllers>
<signalController no="1" cycle="150"><sgs><signalGroup no="1"/><signalGroup no="2"/></sgs></signalController>
<signalController no="9101"><scDetRecConf><old value="keep original for reversal"/></scDetRecConf><sgs><signalGroup no="1"/></sgs></signalController>
</signalControllers><!-- <scDetRec writeFile="false"/> --> </network>'''
GROUPS = {'1': [1, 2], '9101': [1]}


def sha(data): return hashlib.sha256(data).hexdigest()


class RecordingProofTests(unittest.TestCase):
    def setUp(self):
        n._PROOF_CACHE.clear()
        self.temp = tempfile.TemporaryDirectory(prefix='native_recording_proof_')
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.source = self.folder/'원본.inpx'; self.recorded = self.folder/'기록.inpx'
        self.source.write_bytes(SOURCE)
        self.recorded.write_bytes(n.prepare_recording_bytes(SOURCE, GROUPS))
        self.proof = {'schema': n.RECORDING_SCHEMA, 'source_network': {'path': str(self.source), 'sha256': sha(SOURCE)},
                      'recorded_network': {'path': str(self.recorded), 'sha256': sha(self.recorded.read_bytes())}, 'groups': copy.deepcopy(GROUPS)}
        self.manifest = {'run_id': 'run-a', 'files': {'network': dict(self.proof['recorded_network'])},
                         'network_recording': copy.deepcopy(self.proof)}
        self.raw = {'network_path': str(self.recorded), 'run_provenance': self.manifest}

    def test_prepare_exact_reversible_and_idempotent(self):
        output = self.recorded.read_bytes()
        n.validate_recording_bytes(SOURCE, output, GROUPS)
        self.assertEqual(n.prepare_recording_bytes(output, GROUPS), output)
        self.assertIn(b'title=\'writeFile="false"\' writeFile="true"', output)
        self.assertEqual(output.count(b'configName="SG_BILD"'), 3)
        # Restore ONLY the generated replacement spans; all other bytes exact.
        reverted = output
        shift = 0; reverse = []
        for start, end, replacement in n._recording_edits(SOURCE, GROUPS):
            reverse.append((start+shift, start+shift+len(replacement), SOURCE[start:end]))
            shift += len(replacement)-(end-start)
        for start, end, original in reversed(reverse): reverted = reverted[:start]+original+reverted[end:]
        self.assertEqual(reverted, SOURCE)

    def test_reject_nonrecording_changes_even_with_new_file_sha(self):
        good = self.recorded.read_bytes()
        for before, after in [(b'name="geometry"', b'name="changed"'), (b'volume="800"', b'volume="801"'),
                              (b'target="5"', b'target="6"'), (b'cycle="150"', b'cycle="120"'),
                              (b'other="same"', b'other="else"'), (b'</network>', b' </network>'),
                              (b'varNo="2"', b'varNo="3"')]:
            with self.subTest(before=before):
                bad = good.replace(before, after)
                self.assertNotEqual(good, bad)
                self.recorded.write_bytes(bad)
                proof = copy.deepcopy(self.proof); proof['recorded_network']['sha256'] = sha(bad)
                with self.assertRaises(ValueError): n.validate_recording_proof(proof)

    def test_groups_fail_closed(self):
        for groups in ({}, {'2':[1]}, {'1':[3]}, {'1':[1,1]}, {'1':[True]}, {'1':[]}, {1:[1],'1':[1]}, {'01':[1]}):
            with self.subTest(groups=groups), self.assertRaises(ValueError): n.prepare_recording_bytes(SOURCE, groups)
        self.assertEqual(n.prepare_recording_bytes(SOURCE, {1:[2,1],9101:[1]}), self.recorded.read_bytes())

    def test_duplicate_native_or_recording_nodes_rejected(self):
        for bad in (SOURCE.replace(b'<signalGroup no="2"/>',b'<signalGroup no="1"/>'),
                    SOURCE.replace(b'no="9101"',b'no="1"'),
                    SOURCE.replace(b'</evaluation>',b'<scDetRec writeFile="false"/></evaluation>')):
            with self.assertRaises(ValueError): n.prepare_recording_bytes(bad, GROUPS)
        bad=SOURCE.replace(b'<sgs><signalGroup no="1"/></sgs>',b'<scDetRecConf/><sgs><signalGroup no="1"/></sgs>')
        with self.assertRaises(ValueError): n.prepare_recording_bytes(bad,GROUPS)

    def test_no_dtd_or_mutable_bytes(self):
        with self.assertRaises(ValueError): n.prepare_recording_bytes(bytearray(SOURCE), GROUPS)
        with self.assertRaises(ValueError): n.prepare_recording_bytes(SOURCE.replace(b'<network>', b'<!DOCTYPE network><network>'),GROUPS)

    def test_physical_sha_keeps_truthful_loaded_pin(self):
        before = copy.deepcopy(self.raw)
        self.assertEqual(n.snapshot_network_sha256(self.raw), sha(SOURCE))
        self.assertEqual(self.raw, before)
        self.assertNotEqual(self.manifest['files']['network']['sha256'], sha(SOURCE))
        self.assertEqual(n.snapshot_physical_file_sha256(self.raw),sha(SOURCE))

    def test_run_and_path_binding(self):
        path = self.folder/'manifest.json'; path.write_text(json.dumps(self.manifest),encoding='utf8')
        raw={'network_path':str(self.recorded), 'run_provenance':{'manifest_path':str(path),'run_id':'run-a'}}
        self.assertEqual(n.snapshot_network_sha256(raw),sha(SOURCE))
        raw['run_provenance']['run_id']='run-b'
        with self.assertRaisesRegex(ValueError,'run IDs'): n.snapshot_network_sha256(raw)
        for change in ('raw_path','loaded_sha','loaded_path','proof_run','empty_run'):
            bad=copy.deepcopy(self.raw)
            if change=='raw_path':bad['network_path']=str(self.source)
            elif change=='loaded_sha':bad['run_provenance']['files']['network']['sha256']='0'*64
            elif change=='loaded_path':bad['run_provenance']['files']['network']['path']=str(self.source)
            elif change=='proof_run':bad['run_provenance']['network_recording']['run_id']='other'
            else:bad['run_provenance']['run_id']=''
            with self.subTest(change=change),self.assertRaises(ValueError): n.snapshot_network_sha256(bad)

    def test_missing_bad_proof_not_silently_off(self):
        for proof in (None,{}, {**self.proof,'schema':'other'}, {**self.proof,'groups':{'1':[1]}}):
            bad=copy.deepcopy(self.raw);bad['run_provenance']['network_recording']=proof
            with self.assertRaises(ValueError):n.snapshot_network_sha256(bad)

    def test_file_tamper_missing_and_wrong_hash(self):
        self.assertEqual(n.validate_recording_proof(self.proof),sha(SOURCE))
        old=self.recorded.stat()
        self.recorded.write_bytes(self.recorded.read_bytes().replace(b'cycle="150"',b'cycle="151"'))
        os.utime(self.recorded, ns=(old.st_atime_ns,old.st_mtime_ns+10000000))
        with self.assertRaisesRegex(ValueError,'SHA'):n.validate_recording_proof(self.proof)
        self.recorded.unlink()
        with self.assertRaises(FileNotFoundError):n.validate_recording_proof(self.proof)

    def test_cache_does_not_rehash_same_files_and_mutable_groups_revalidated(self):
        original=Path.read_bytes; reads=[]
        def observe(path):reads.append(path);return original(path)
        with patch.object(Path,'read_bytes',observe):
            n.validate_recording_proof(self.proof);n.validate_recording_proof(self.proof)
        self.assertEqual(reads,[self.source,self.recorded])
        self.proof['groups']['1'].pop()
        with self.assertRaises(ValueError):n.validate_recording_proof(self.proof)
        self.assertLessEqual(len(n._PROOF_CACHE),n._CACHE_LIMIT)

    def test_off_fingerprint_contract_and_direct_file_guard(self):
        legacy={'run_provenance':{'files':{'network':{'sha256':'Z'*64}}}}
        self.assertEqual(n.snapshot_network_sha256(legacy),'Z'*64)
        with self.assertRaises(ValueError):n.snapshot_network_sha256({})
        with self.assertRaises(ValueError):n.snapshot_physical_file_sha256({'network_path':str(self.source)})

    def test_actual_head_guard_explicit_config_and_off_unchanged(self):
        from evaluation.controllers import head_service_resources as heads
        contract=self.folder/'head_contract.json'
        contract.write_text(json.dumps({'schema':'physical-head-resource-join/v1',
            'resources':{'10619':{},'10629':{}},'network':self.proof['source_network']}),encoding='utf8')
        tuning={'urban':{'capacity':{'head_resource_contract':str(contract),'head_observation':{'enabled':True}},
                         'shared_local_service_pool':True},'execution':{'native_signal_record':False}}
        cfg=SimpleNamespace(network=SimpleNamespace())
        def geometry(*args):raise RuntimeError('GEOMETRY_REACHED')
        fake=SimpleNamespace(physical_groups=geometry)
        with patch.dict(sys.modules,{'evaluation.controllers.signal_head_observation':fake}):
            legacy={'network_path':str(self.source),'run_provenance':{'manifest_path':'does not exist'}}
            with self.assertRaisesRegex(RuntimeError,'GEOMETRY_REACHED'):heads.configure(cfg,tuning,legacy,{})
            # Merely attaching a proof does not opt an OFF consumer in.
            with self.assertRaisesRegex(ValueError,'snapshot networks differ'):heads.configure(cfg,tuning,self.raw,{})
            tuning['execution']['native_signal_record']=True
            with self.assertRaisesRegex(RuntimeError,'GEOMETRY_REACHED'):heads.configure(cfg,tuning,self.raw,{})
            with self.assertRaises(ValueError):heads.configure(cfg,tuning,{'network_path':str(self.source)},{})

    def test_actual_144_sg_fixture_bytes_exact(self):
        root=Path(__file__).resolve().parents[1]
        path=root/'diagnostics/com_execution_equivalence/native_all_sg_300_v1/preflight.json'
        if not path.exists():self.skipTest('Historical small network fixture unavailable')
        preflight=json.loads(path.read_text(encoding='utf8'))
        groups={}
        for row in json.loads(Path(preflight['recorded_groups_path']).read_text(encoding='utf8')):
            groups.setdefault(row['sc_no'],[]).append(row['sg_no'])
        source=Path(preflight['source_network']).read_bytes();recorded=Path(preflight['network']).read_bytes()
        self.assertEqual(sha(source),preflight['source_network_sha256'])
        self.assertEqual(sha(recorded),preflight['network_sha256'])
        self.assertEqual(sum(map(len,groups.values())),144)
        self.assertEqual(n.prepare_recording_bytes(source,groups),recorded)


if __name__=='__main__':unittest.main()
