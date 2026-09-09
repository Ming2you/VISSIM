"""Raw archive integrity and path-only relocation without source-run access."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from diagnostics.review_fixtures import ROOT, ARCHIVE, ENVIRONMENT, restore, fixture_path, sha, _safe_relative


class PortableFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT/'.review-fixtures').mkdir(exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(prefix='integrity-', dir=ROOT/'.review-fixtures')
        cls.base = Path(cls.temporary.name)
        cls.destination = cls.base/'restored'
        cls.report = restore(cls.destination, repo_root=cls.base/'different_checkout')

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_every_original_byte_and_hash_is_preserved(self):
        self.assertEqual(len(self.report['raw_files']), 49)
        with zipfile.ZipFile(ARCHIVE) as bundle:
            for row in self.report['raw_files']:
                with self.subTest(path=row['path']):
                    raw = (self.destination/'raw'/row['path']).read_bytes()
                    self.assertEqual(raw, bundle.read('raw/'+row['path']))
                    self.assertEqual(sha(raw), row['sha256'])

    def test_relocated_json_diff_is_exactly_the_declared_path_alias_list(self):
        def differences(before, after, pointer=''):
            if isinstance(before, dict):
                self.assertEqual(set(before), set(after))
                return sum((differences(value, after[key], pointer+'/'+str(key).replace('~', '~0').replace('/', '~1')) for key, value in before.items()), [])
            if isinstance(before, list):
                self.assertEqual(len(before), len(after))
                return sum((differences(a, b, pointer+'/'+str(i)) for i, (a, b) in enumerate(zip(before, after))), [])
            return [] if before == after else [(pointer, before, after)]
        for row in self.report['raw_files']:
            if row['kind'] != 'raw_run_file' or not row['path'].endswith('.json'):
                continue
            before = json.loads((self.destination/'raw'/row['path']).read_text(encoding='utf-8-sig'))
            after = json.loads((self.destination/'relocated'/row['path']).read_text(encoding='utf-8'))
            expected = [(x['pointer'], x['before'], x['after']) for x in self.report['path_relocations'].get(row['path'], [])]
            self.assertEqual(differences(before, after), expected)
            if 'run_id' in before:
                self.assertEqual(before['run_id'], after['run_id'])
            if 'vehicle_records' in before:
                self.assertEqual(before['vehicle_records'], after['vehicle_records'])
                self.assertEqual(before['run_provenance']['run_id'], after['run_provenance']['run_id'])

    def test_relocated_snapshot_opens_matching_relocated_manifest(self):
        from evaluation.controllers.network_provenance import snapshot_network_sha256
        rows = [r for r in self.report['raw_files'] if Path(r['path']).name.startswith('state_')]
        for row in rows:
            after = json.loads((self.destination/'relocated'/row['path']).read_text(encoding='utf-8'))
            manifest = Path(after['run_provenance']['manifest_path'])
            self.assertTrue(manifest.is_relative_to(self.destination/'relocated'))
            self.assertEqual(snapshot_network_sha256(after), '085a10c71874e897083c97097af8fa3f1f08da1ef7416fef2f7cfbedabdfc317')

    def test_existing_destination_is_never_overwritten(self):
        marker = self.destination/'restoration.json'
        before = marker.read_bytes()
        with self.assertRaises(FileExistsError):
            restore(self.destination)
        self.assertEqual(marker.read_bytes(), before)

    def test_activated_helper_never_falls_back_to_an_unlisted_original(self):
        with patch.dict(os.environ, {ENVIRONMENT: str(self.destination)}):
            path = fixture_path(ROOT/'evaluation/runs/codex_nc_s13_6056c94_20260909_retry/decisions_codex_nc_s13_6056c94_20260909_retry/state_000900.json')
            self.assertTrue(path.is_relative_to(self.destination/'relocated'))
            with self.assertRaises(FileNotFoundError):
                fixture_path(ROOT/'evaluation/runs/a_missing_archive/state.json')

    def test_archive_paths_reject_windows_separators_drives_and_parent(self):
        for value in ('a\\..\\..\\escape', '\\\\server\\share', 'a/C:evil', 'C:/escape', 'a/../escape', '/escape', '.', ''):
            with self.subTest(path=value), self.assertRaises(ValueError):
                _safe_relative(value)
        self.assertEqual(_safe_relative('evaluation/runs/example/state.json'), Path('evaluation/runs/example/state.json'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
