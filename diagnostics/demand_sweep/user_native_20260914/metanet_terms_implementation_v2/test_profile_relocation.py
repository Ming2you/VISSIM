"""Standard-library regression for the harness's hash-pinned path relocation."""
import ast
import hashlib
from pathlib import Path, PureWindowsPath
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
HARNESS = HERE.parent / 'metanet_calibration_v1/canonical_harness.py'
# Load the actual two helpers without importing the traffic-model dependencies.
tree = ast.parse(HARNESS.read_text(encoding='utf-8-sig'))
helpers = ast.Module(body=[node for node in tree.body if isinstance(node, ast.FunctionDef)
                          and node.name in ('sha256', 'resolve_geometry_profile')], type_ignores=[])
namespace = {'hashlib': hashlib, 'Path': Path, 'PureWindowsPath': PureWindowsPath, 'ROOT': HERE}
exec(compile(helpers, str(HARNESS), 'exec'), namespace)
resolve_profile = namespace['resolve_geometry_profile']


class ProfileRelocationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.relative = 'diagnostics/example/physical_geometry.json'
        self.path = self.root / self.relative
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(b'{"physical_geometry_sha256":"frozen"}')
        self.digest = hashlib.sha256(self.path.read_bytes()).hexdigest()

    def resolve(self, path, digest=None):
        return resolve_profile({'path': path, 'sha256': digest or self.digest}, self.root)

    def test_current_relative_path(self):
        self.assertEqual(self.resolve(self.relative), self.path)

    def test_current_absolute_path(self):
        self.assertEqual(self.resolve(str(self.path)), self.path)

    def test_old_windows_checkout(self):
        self.assertEqual(self.resolve('D:\\former-machine\\VISSIM\\' + self.relative.replace('/', '\\')), self.path)

    def test_old_posix_checkout(self):
        self.assertEqual(self.resolve('/former-machine/VISSIM/' + self.relative), self.path)

    def test_relocated_content_must_match(self):
        with self.assertRaisesRegex(ValueError, 'changed after observation'):
            self.resolve('D:/former-machine/VISSIM/' + self.relative, '0' * 64)

    def test_current_content_mismatch_does_not_fallback(self):
        with self.assertRaisesRegex(ValueError, 'changed after observation'):
            self.resolve(str(self.path), '0' * 64)

    def test_unrelated_external_path_rejected(self):
        with self.assertRaisesRegex(ValueError, 'cannot be relocated'):
            self.resolve('D:/outside/arbitrary.json')

    def test_parent_traversal_rejected(self):
        with self.assertRaisesRegex(ValueError, 'cannot be relocated'):
            self.resolve('D:/former/diagnostics/../../arbitrary.json')

    def test_missing_relocated_file_is_not_silently_accepted(self):
        with self.assertRaises(FileNotFoundError):
            self.resolve('D:/former/diagnostics/example/absent.json')

    def test_saved_profile_object_is_unchanged(self):
        original = {'path': 'D:/former/' + self.relative, 'sha256': self.digest}
        before = original.copy()
        resolve_profile(original, self.root)
        self.assertEqual(original, before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
