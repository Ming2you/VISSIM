"""Protect actual runtime inputs while excluding one reviewed pytest scratch."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from diagnostics.sdmpc_n31_20260924.tools import freeze_manifest as fm


class FreezeScopeTests(unittest.TestCase):
    def test_only_reviewed_subtree_is_excluded(self):
        scratch=fm.EXCLUDED_RELATIVE_DIRS[0]
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            files=(scratch+'/synthetic.fzp',scratch+'_real/input.json',
                   'another/pytest_controlled_pair_area/input.json',
                   'evaluation/boundary_fit/freeze.json','evaluation/model.py')
            for name in files:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('fixture',encoding='utf8')
            self.assertEqual(set(fm.walk_files(root)),set(files[1:]))

    def test_other_permission_error_is_not_silently_omitted(self):
        def walk(root,*,onerror):
            onerror(PermissionError('unreadable actual input directory'))
            return []
        with patch.object(fm.os,'walk',side_effect=walk), self.assertRaisesRegex(fm.ToolError,'Cannot enumerate'):
            fm.walk_files(Path.cwd())

    def test_robocopy_uses_same_exact_relative_path(self):
        root=Path(__file__).resolve().parents[4]
        script=(root/'tools/sdmpc31/freeze_worktree.ps1').read_text(encoding='utf8')
        self.assertIn("$scratch = Join-Path $src '"+fm.EXCLUDED_RELATIVE_DIRS[0]+"'",script)
        self.assertIn('__tangentcache__ $scratch /XF .git *.pyc',script)
        self.assertNotIn('/XD pytest_*',script)


if __name__=='__main__':unittest.main()
