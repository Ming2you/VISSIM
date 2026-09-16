"""Exercise the handoff restorer using temporary packages, never real results."""
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile


SCRIPT = Path(__file__).with_name('restore_evidence.py')
spec = importlib.util.spec_from_file_location('restore_evidence', SCRIPT)
restorer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restorer)


class RestoreEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name).resolve()
        self.package = self.folder / 'package'
        self.package.mkdir()
        self.root = self.folder / 'destination'
        self.root.mkdir()

    def make_package(self, payloads, corrupt_object=False):
        objects = {}
        rows = []
        for path, body in payloads.items():
            digest = hashlib.sha256(body).hexdigest()
            rows.append({'path': path, 'bytes': len(body), 'sha256': digest})
            objects[digest] = body
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
            for digest, body in objects.items():
                archive.writestr('objects/' + digest, b'corrupt' if corrupt_object else body)
            archive.writestr('../../not-extracted.txt', b'not referenced')
        contents = stream.getvalue()
        cut = max(1, len(contents) // 2)
        parts = []
        for index, body in enumerate((contents[:cut], contents[cut:])):
            name = 'evidence.part%02d' % index
            (self.package / name).write_bytes(body)
            parts.append({'name': name, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()})
        manifest = {'files': rows, 'parts': parts}
        (self.package / 'evidence_manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        return manifest

    def run_restore(self, *options):
        output = io.StringIO()
        with patch.object(restorer, 'HERE', self.package), patch.object(sys, 'argv',
                [str(SCRIPT), '--root', str(self.root), *options]), redirect_stdout(output):
            restorer.main()
        return json.loads(output.getvalue())

    def test_default_root_is_repository(self):
        self.assertEqual(restorer.ROOT, SCRIPT.resolve().parents[2])

    def test_split_archive_restore_verify_and_idempotence(self):
        payloads = {'diagnostics/a.json': b'{"a":1}', 'diagnostics/b.json': b'{"a":1}'}
        self.make_package(payloads)
        result = self.run_restore('--restore', '--verify')
        self.assertEqual(result['restored'], 2)
        self.assertTrue(result['verified'])
        self.assertEqual(result['missing'], 0)
        self.assertFalse(result['native_started'])
        for path, body in payloads.items():
            self.assertEqual((self.root / path).read_bytes(), body)
        self.assertFalse((self.folder / 'not-extracted.txt').exists())
        self.assertEqual(self.run_restore('--restore', '--verify')['restored'], 0)

    def test_inspection_does_not_create_missing_files(self):
        self.make_package({'diagnostics/a.json': b'a'})
        result = self.run_restore()
        self.assertEqual(result['missing'], 1)
        self.assertEqual(list(self.root.iterdir()), [])
        with self.assertRaisesRegex(ValueError, 'Restore first'):
            self.run_restore('--verify')

    def test_conflict_aborts_before_any_writes(self):
        self.make_package({'diagnostics/new.json': b'new', 'diagnostics/existing.json': b'expected'})
        existing = self.root / 'diagnostics/existing.json'
        existing.parent.mkdir()
        existing.write_bytes(b'actual local modification')
        with self.assertRaisesRegex(ValueError, 'nothing overwritten'):
            self.run_restore('--restore', '--verify')
        self.assertEqual(existing.read_bytes(), b'actual local modification')
        self.assertFalse((self.root / 'diagnostics/new.json').exists())

    def test_corrupt_part_rejected_before_writes(self):
        manifest = self.make_package({'diagnostics/a.json': b'a'})
        (self.package / manifest['parts'][1]['name']).write_bytes(b'bad part')
        with self.assertRaisesRegex(ValueError, 'part checksum differs'):
            self.run_restore('--restore')
        self.assertEqual(list(self.root.iterdir()), [])

    def test_corrupt_object_rejected(self):
        self.make_package({'diagnostics/a.json': b'a'}, corrupt_object=True)
        with self.assertRaisesRegex(ValueError, 'object checksum differs'):
            self.run_restore('--restore')
        self.assertEqual(list(self.root.iterdir()), [])

    def test_unsafe_destination_paths_rejected(self):
        for value in ('../escape', '/absolute', 'C:/drive', r'diagnostics\windows',
                      'diagnostics/../../escape'):
            with self.subTest(path=value), self.assertRaises(ValueError):
                restorer.target(self.root, value)

    def test_directory_conflict_is_not_overwritten(self):
        self.make_package({'diagnostics/a.json': b'a'})
        (self.root / 'diagnostics/a.json').mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, 'nothing overwritten'):
            self.run_restore('--restore')


if __name__ == '__main__':
    unittest.main(verbosity=2)
