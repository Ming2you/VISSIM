"""The optional1092 prior is calibrated evidence, never a native route claim."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from diagnostics.test_native_internal_input import ROOT, NativeInputTests
from evaluation.controllers import native_internal_input as native


class EmpiricalNativeChoiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        NativeInputTests.setUpClass();cls.f=NativeInputTests.f
        cls.document=json.loads((ROOT/'diagnostics/native_internal_inputs_extended_ver2.json').read_text())
        cls.document['inputs']={'1092':cls.document['inputs']['1092']}

    def configure(self,document):
        with tempfile.TemporaryDirectory(dir=ROOT/'diagnostics') as directory:
            path=Path(directory)/'source.json';path.write_text(json.dumps(document))
            cfg=deepcopy(self.f.cfg)
            native.configure(cfg,{'urban':{'native_internal_inputs':str(path)}},self.f.raw,self.f.detectors)
            return cfg.network.native_internal_inputs['inputs']['1092']

    def test_explicit_empirical_prior_complete_cohorts_and_first_selected_head(self):
        spec=self.configure(self.document);proof=spec['branch_coverage']['217']
        self.assertEqual(proof['prior_probability'],1.)
        self.assertEqual(proof['resolved_source_vehicles'],80)
        self.assertEqual(proof['validation_scope'],'offline_seed13_requires_seed14_holdout')
        self.assertEqual(spec['target_storage'],'SC11_to_SC12')
        self.assertEqual(spec['intermediate_unselected_heads'],['41701'])
        self.assertAlmostEqual(spec['minimum_approach_distance_m'],296.32808451454434)
        self.assertEqual(spec['physical_projection_links'],['217','10350'])

    def test_alternative_connector_nonunit_prior_missing_sample_and_false_holdout_rejected(self):
        for key,value in [('connector','10349'),('prior_probability',.5),('resolved_source_vehicles',79),
                          ('validation_scope','native_deterministic'),('calibration_seed',14)]:
            document=deepcopy(self.document);document['inputs']['1092']['branch_coverage']['217'][key]=value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'pinned cohort evidence'):
                self.configure(document)

    def test_unknown_cohort_or_changed_network_cannot_be_dropped_from_denominator(self):
        original=self.document['inputs']['1092']['branch_coverage']['217']['calibration']
        for kind in ('unknown','network'):
            calibration=json.loads((ROOT/original['path']).read_text())
            if kind=='unknown':calibration['inputs']['1092']['all_0_5400']['unresolved_or_censored_ids']=1
            else:
                key=next(k for k in calibration['source_sha256'] if k.endswith('.inpx'))
                calibration['source_sha256'][key]='0'*64
            with tempfile.TemporaryDirectory(dir=ROOT/'diagnostics') as directory:
                path=Path(directory)/'calibration.json';path.write_text(json.dumps(calibration))
                document=deepcopy(self.document)
                document['inputs']['1092']['branch_coverage']['217']['calibration']={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
                with self.subTest(kind=kind),self.assertRaisesRegex(ValueError,'pinned cohort evidence'):
                    self.configure(document)


if __name__=='__main__':unittest.main()
