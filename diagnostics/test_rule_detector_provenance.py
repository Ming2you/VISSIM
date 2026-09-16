"""Synthetic rule-detector recording proof tests; no model, COM or native run."""
import copy
import hashlib
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from evaluation.controllers import network_provenance as n


POINT = b'<dataCollectionPoint no="11" name="existing" lane="2 1" pos="20"/>'
MEASUREMENT = (b'<dataCollectionMeasurement no="11" name="existing">'
               b'<dataCollectionPoints><intObjectRef key="11"/></dataCollectionPoints>'
               b'</dataCollectionMeasurement>')
DATA_COLL = b'<dataColl collectData="false" fromTime="15" interval="60" toTime="9000" keep="same"/>'
SOURCE = (b'<?xml version="1.0" encoding="UTF-8"?>\n<network>\n'
          b'<evaluation other="same">' + DATA_COLL + b'<scDetRec writeFile="false"/></evaluation>\n'
          b'<links><link no="2" name="physical"><geometry><linkPolyPts>'
          b'<linkPolyPoint x="0" y="0" z="0"/><linkPolyPoint x="100" y="0" z="0"/>'
          b'</linkPolyPts></geometry><lanes><lane width="3.5"/><lane width="3.5"/></lanes>'
          b'</link></links>\n<vehicleInputs><input volume="800"/></vehicleInputs>\n'
          b'<dataCollectionPoints>' + POINT + b'</dataCollectionPoints>\n'
          b'<dataCollectionMeasurements>' + MEASUREMENT + b'</dataCollectionMeasurements>\n'
          b'<signalControllers><signalController no="1" cycle="150">'
          b'<scDetRecConf><old/></scDetRecConf><sgs><signalGroup no="1"/></sgs>'
          b'</signalController></signalControllers>\n</network>')
GROUPS = {'1': [1]}
SG_BLOCK = b'\n'.join([
    b'<scDetRecConf>',
    b'\t\t\t\t<signalOutputConfigurationElement configName="SIM_SEK" detPort="0" title="" varNo="0" wttFilename="vissim" />',
    b'\t\t\t\t<signalOutputConfigurationElement configName="UML_SEK" detPort="0" title="" varNo="0" wttFilename="vissim" />',
    b'\t\t\t\t<signalOutputConfigurationElement configName="SG_BILD" detPort="0" sg="1 1" title="" varNo="1" wttFilename="vissim" />',
    b'\t\t\t\t</scDetRecConf>',
])
LEGACY = SOURCE.replace(b'<scDetRecConf><old/></scDetRecConf>', SG_BLOCK).replace(
    b'<scDetRec writeFile="false"/>', b'<scDetRec writeFile="true"/>')
DECLARATION = {
    'schema': 'rule-native-detectors/v1', 'interval_sec': 150, 'from_sec': 0, 'to_sec': 10800,
    'stations': [{'id': 'ramp_a', 'role': 'ramps', 'target': 'RM_C1', 'link_no': 2,
                  'position_m': 50.0, 'lane_numbers': [1, 2],
                  'measurement_ids': [910001, 910002], 'point_ids': [910001, 910002]}],
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def element_pattern(tag):
    # The synthetic fixture puts the root points before the measurement's points.
    return rb'<' + tag + rb'\b[^>]*(?:/>|>.*?</' + tag + rb'>)'


class RuleDetectorProofTests(unittest.TestCase):
    def setUp(self):
        n._PROOF_CACHE.clear()
        self.addCleanup(n._PROOF_CACHE.clear)

    def proof_files(self, output, declaration):
        temp = tempfile.TemporaryDirectory(prefix='rule_detector_proof_')
        self.addCleanup(temp.cleanup)
        source, recorded = Path(temp.name) / 'source.inpx', Path(temp.name) / 'recorded.inpx'
        source.write_bytes(SOURCE)
        recorded.write_bytes(output)
        proof = {'schema': n.RECORDING_SCHEMA, 'groups': copy.deepcopy(GROUPS),
                 'source_network': {'path': str(source), 'sha256': sha(SOURCE)},
                 'recorded_network': {'path': str(recorded), 'sha256': sha(output)},
                 'rule_detectors': copy.deepcopy(declaration)}
        return source, recorded, proof

    def test_off_is_exact_legacy_bytes(self):
        self.assertEqual(n.prepare_recording_bytes(SOURCE, GROUPS), LEGACY)
        self.assertEqual(n.prepare_recording_bytes(SOURCE, GROUPS, rule_detectors=None), LEGACY)
        n.validate_recording_bytes(SOURCE, LEGACY, GROUPS, rule_detectors=None)
        self.assertIn(DATA_COLL, LEGACY)
        self.assertIn(POINT, LEGACY)
        self.assertIn(MEASUREMENT, LEGACY)

    def test_only_declared_edits_are_reversible_with_empty_or_existing_collections(self):
        for source in (SOURCE, SOURCE.replace(POINT, b'').replace(MEASUREMENT, b'')):
            with self.subTest(existing=POINT in source):
                declaration = copy.deepcopy(DECLARATION)
                output = n.prepare_recording_bytes(source, GROUPS, rule_detectors=declaration)
                self.assertEqual(declaration, DECLARATION)
                n.validate_recording_bytes(source, output, GROUPS, rule_detectors=declaration)
                root = ET.fromstring(output)
                points = {int(row.get('no')): row for row in root.find('dataCollectionPoints')}
                measurements = {int(row.get('no')): row for row in root.find('dataCollectionMeasurements')}
                expected_ids = {910001, 910002} | ({11} if POINT in source else set())
                self.assertEqual(set(points), expected_ids)
                self.assertEqual(set(measurements), expected_ids)
                for lane, number in enumerate((910001, 910002), 1):
                    self.assertEqual(points[number].get('lane'), f'2 {lane}')
                    self.assertEqual(float(points[number].get('pos')), 50.0)
                    self.assertEqual(measurements[number].get('name'), f'RULE|ramps|RM_C1|lane{lane}')
                    refs = measurements[number].findall('dataCollectionPoints/intObjectRef')
                    self.assertEqual([ref.get('key') for ref in refs], [str(number)])
                settings = root.find('evaluation/dataColl').attrib
                self.assertEqual(settings['collectData'], 'true')
                for name, value in [('fromTime', 0), ('interval', 150), ('toTime', 10800)]:
                    self.assertEqual(float(settings[name]), value)
                self.assertEqual(settings['keep'], 'same')
                if POINT in source:
                    self.assertIn(POINT, output)
                    self.assertIn(MEASUREMENT, output)
                # Restore exactly the three allowed detector/evaluation blocks.
                restored = output
                for tag in (b'dataCollectionPoints', b'dataCollectionMeasurements', b'dataColl'):
                    original = re.search(element_pattern(tag), source, re.S).group()
                    restored = re.sub(element_pattern(tag), lambda match: original, restored, count=1, flags=re.S)
                self.assertEqual(restored, n.prepare_recording_bytes(source, GROUPS))

    def test_identical_physical_points_can_be_shared_by_distinct_measurements(self):
        declaration = copy.deepcopy(DECLARATION)
        other = copy.deepcopy(declaration['stations'][0])
        other.update(id='ramp_b', target='RM_C2', measurement_ids=[910003, 910004])
        declaration['stations'].append(other)
        output = n.prepare_recording_bytes(SOURCE, GROUPS, rule_detectors=declaration)
        n.validate_recording_bytes(SOURCE, output, GROUPS, rule_detectors=declaration)
        root = ET.fromstring(output)
        self.assertEqual(len(root.find('dataCollectionPoints')), 3)
        measurements = {int(row.get('no')): row for row in root.find('dataCollectionMeasurements')}
        self.assertEqual(set(measurements), {11, 910001, 910002, 910003, 910004})
        for number, point in ((910003, 910001), (910004, 910002)):
            self.assertEqual([ref.get('key') for ref in measurements[number].findall(
                'dataCollectionPoints/intObjectRef')], [str(point)])

    def test_physical_and_measurement_tampering_fails_even_with_truthful_sha(self):
        output = n.prepare_recording_bytes(SOURCE, GROUPS, rule_detectors=DECLARATION)
        _, recorded, proof = self.proof_files(output, DECLARATION)
        n.validate_recording_proof(proof)
        for before, after in [(b'name="physical"', b'name="changed"'),
                              (b'volume="800"', b'volume="801"'),
                              (b'keep="same"', b'keep="changed"'),
                              (b'pos="20"', b'pos="21"'),
                              (b'RULE|ramps|RM_C1|lane1', b'RULE|ramps|RM_C1|lane2'),
                              (b'key="910001"', b'key="11"'),
                              (b'</network>', b' </network>')]:
            with self.subTest(before=before):
                changed = output.replace(before, after)
                self.assertNotEqual(output, changed)
                with self.assertRaises(ValueError):
                    n.validate_recording_bytes(SOURCE, changed, GROUPS, rule_detectors=DECLARATION)
                recorded.write_bytes(changed)
                proof['recorded_network']['sha256'] = sha(changed)
                with self.assertRaises(ValueError):
                    n.validate_recording_proof(proof)

    def test_invalid_declarations_fail_closed(self):
        cases = [('measurement_ids', [11, 910002]), ('measurement_ids', [910001, 910001]),
                 ('measurement_ids', [True, 910002]), ('point_ids', [0, 910002]),
                 ('point_ids', [910001]), ('lane_numbers', [1, 3]), ('lane_numbers', [1, 1]),
                 ('lane_numbers', [True, 2]), ('link_no', 99), ('position_m', -1.0),
                 ('position_m', 101.0), ('position_m', float('nan')), ('role', 'unknown')]
        for key, value in cases:
            declaration = copy.deepcopy(DECLARATION)
            declaration['stations'][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                n.prepare_recording_bytes(SOURCE, GROUPS, rule_detectors=declaration)
        for key, value in [('schema', 'other'), ('interval_sec', 0), ('interval_sec', True),
                           ('to_sec', 0), ('stations', [])]:
            declaration = copy.deepcopy(DECLARATION)
            declaration[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                n.prepare_recording_bytes(SOURCE, GROUPS, rule_detectors=declaration)

    def test_point_collisions_and_missing_native_containers_fail_closed(self):
        declaration = copy.deepcopy(DECLARATION)
        declaration['stations'][0]['point_ids'][0] = 11
        with self.assertRaises(ValueError):
            n.prepare_recording_bytes(SOURCE, GROUPS, rule_detectors=declaration)
        declaration = copy.deepcopy(DECLARATION)
        other = copy.deepcopy(declaration['stations'][0])
        other.update(id='ramp_b', measurement_ids=[910003, 910004], position_m=51.0)
        declaration['stations'].append(other)
        with self.assertRaises(ValueError):
            n.prepare_recording_bytes(SOURCE, GROUPS, rule_detectors=declaration)
        for tag in (b'dataCollectionPoints', b'dataCollectionMeasurements', b'dataColl'):
            missing = re.sub(element_pattern(tag), b'', SOURCE, count=1, flags=re.S)
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                n.prepare_recording_bytes(missing, GROUPS, rule_detectors=DECLARATION)

    def test_mutable_nested_proof_declaration_cannot_reuse_a_successful_cache_entry(self):
        output = n.prepare_recording_bytes(SOURCE, GROUPS, rule_detectors=DECLARATION)
        source, recorded, proof = self.proof_files(output, DECLARATION)
        original_read, reads = Path.read_bytes, []

        def observe(path):
            reads.append(path)
            return original_read(path)

        with patch.object(Path, 'read_bytes', observe):
            self.assertEqual(n.validate_recording_proof(proof), sha(SOURCE))
            self.assertEqual(n.validate_recording_proof(proof), sha(SOURCE))
        self.assertEqual(reads, [source, recorded])
        for key, value in [('position_m', 51.0), ('lane_numbers', [2, 1]),
                           ('measurement_ids', [910002, 910001])]:
            proof['rule_detectors'] = copy.deepcopy(DECLARATION)
            proof['rule_detectors']['stations'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                n.validate_recording_proof(proof)
        proof['rule_detectors'] = copy.deepcopy(DECLARATION)
        self.assertEqual(n.validate_recording_proof(proof), sha(SOURCE))
        self.assertLessEqual(len(n._PROOF_CACHE), n._CACHE_LIMIT)


if __name__ == '__main__':
    unittest.main()
