"""Small PS5.1 tests of the installed canonical function; no watchdog/model/COM run.

Run from the repository with normal Python. Evidence is retained in a unique
diagnostics directory. Git commands are read-only; no repository is initialized.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import unittest
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1"
PATCH = ROOT / "diagnostics/watchdog_exact_git_commit.patch"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def installed_and_historical_functions():
    patch = PATCH.read_text(encoding="utf-8").splitlines()
    body = patch[next(i for i, row in enumerate(patch) if row.startswith("@@")) + 1:]
    before = "\n".join(row[1:] for row in body if row.startswith((" ", "-")))
    after = "\n".join(row[1:] for row in body if row.startswith((" ", "+")))
    actual = re.search(r"function Get-ExactGitCommit\(.*?\n\}", SOURCE.read_text(encoding="utf-8-sig"), re.S).group()
    if actual != after:
        raise ValueError("Installed canonical function differs from the reviewed correction")
    return before, after


class ExactGitCommitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        before, after = installed_and_historical_functions()
        cls.pins = {str(p.relative_to(ROOT)): sha(p) for p in (SOURCE, PATCH, Path(__file__))}
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        cls.output = ROOT / "diagnostics" / ("watchdog_exact_git_commit_validation_" + stamp)
        cls.output.mkdir()
        native = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
        cls.expected = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", "HEAD^{commit}"],
                                     capture_output=True, check=True).stdout.decode("ascii").strip()
        top = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"], capture_output=True, check=True).stdout
        quote_off = subprocess.run(["git", "-c", "core.quotepath=false", "-C", str(ROOT), "rev-parse", "--show-toplevel"], capture_output=True, check=True).stdout
        cls.raw_git = {"toplevel_hex": top.hex(), "toplevel_utf8": top.decode("utf-8"),
                       "quotepath_false_bytes_equal": top == quote_off, "expected_commit": cls.expected}
        vendor = ROOT / "vendor/NumSim-mine"
        vendor_cdup = subprocess.run(["git", "-C", str(vendor), "rev-parse", "--show-cdup"], capture_output=True, check=True).stdout.decode("ascii").strip()
        vendor_head = subprocess.run(["git", "-C", str(vendor), "rev-parse", "--verify", "HEAD^{commit}"], capture_output=True, check=True).stdout.decode("ascii").strip()
        cls.vendor_expected = vendor_head if vendor_cdup == "" else ""
        cls.raw_git["vendor"] = {"path": str(vendor), "show_cdup": vendor_cdup,
                                 "head_from_git_C": vendor_head, "exact_root_commit_expected": cls.vendor_expected,
                                 "is_own_git_root": vendor_cdup == ""}
        invalid = [
            {"name": "not_work_tree", "steps": [{"out": ["false"], "exit": 0}]},
            {"name": "inside_failed", "steps": [{"out": ["true"], "exit": 1}]},
            {"name": "inside_multiline", "steps": [{"out": ["true", "true"], "exit": 0}]},
            {"name": "root_failed", "steps": [{"out": ["true"], "exit": 0}, {"out": [], "exit": 1}]},
            {"name": "root_parent", "steps": [{"out": ["true"], "exit": 0}, {"out": ["../"], "exit": 0}]},
            {"name": "root_whitespace", "steps": [{"out": ["true"], "exit": 0}, {"out": [" "], "exit": 0}]},
            {"name": "root_multiline", "steps": [{"out": ["true"], "exit": 0}, {"out": ["", ""], "exit": 0}]},
        ]
        for name, output, code in (("head_failed", [cls.expected], 1), ("head_missing", [], 0),
                                   ("head_multiline", [cls.expected, cls.expected], 0),
                                   ("head_bad", ["not-a-commit"], 0),
                                   ("head_quoted", ['"' + cls.expected + '"'], 0)):
            invalid.append({"name": name, "steps": [{"out": ["true"], "exit": 0}, {"out": [], "exit": 0}, {"out": output, "exit": code}]})
        valid = [{"name": "sha1_blank_root", "expected": cls.expected, "steps": [{"out": ["true"], "exit": 0}, {"out": [""], "exit": 0}, {"out": [cls.expected], "exit": 0}]},
                 {"name": "sha256_empty_root", "expected": "a" * 64, "steps": [{"out": ["true"], "exit": 0}, {"out": [], "exit": 0}, {"out": ["a" * 64], "exit": 0}]}]
        cases = cls.output / "mock_cases.json"
        cases.write_text(json.dumps(invalid + valid), encoding="utf-8")
        script = r'''
$ErrorActionPreference = 'Continue'
$repo = $env:EXACT_GIT_TEST_REPO
$output = $env:EXACT_GIT_TEST_OUTPUT
$tokens = $null; $errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile((Join-Path $repo 'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1'), [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw 'Production PS syntax failure' }
$nodes = @($ast.FindAll({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'Get-ExactGitCommit'}, $true))
if ($nodes.Count -ne 1) { throw 'Function extraction count failure' }
# Execute only the AST-extracted installed helper. Historical bytes reproduce the old failure.
Invoke-Expression $nodes[0].Extent.Text
__HISTORICAL__
function Capture([string]$FunctionName, [string]$PathValue) {
  $Error.Clear()
  $value = ''
  try { $value = & $FunctionName $PathValue 2>$null } catch { }
  $failure = @($Error | ForEach-Object { [ordered]@{type=$_.Exception.GetType().FullName; message=$_.Exception.Message} })
  return [ordered]@{value=[string]$value; errors=$failure}
}
$initialEncoding = [Console]::OutputEncoding.CodePage
$initialInput = $OutputEncoding.CodePage
$results = @()
try {
  foreach ($cp in @($initialEncoding, 949, 437, 65001)) {
    [Console]::OutputEncoding = [Text.Encoding]::GetEncoding($cp)
    $top = [string](& git -C $repo rev-parse --show-toplevel 2>$null)
    $paths = [ordered]@{root=$repo; trailing=($repo+'\'); relative='.'; child=(Join-Path $repo 'scripts'); vendor=(Join-Path $repo 'vendor\NumSim-mine'); missing=(Join-Path $output 'missing'); file=(Join-Path $repo 'AGENTS.md')}
    $records = [ordered]@{}
    foreach ($name in $paths.Keys) {
      $records[$name] = [ordered]@{original=(Capture 'Get-OriginalGitCommit' $paths[$name]); proposed=(Capture 'Get-ExactGitCommit' $paths[$name])}
    }
    $results += [ordered]@{code_page=$cp; decoded_toplevel=$top; decoded_codepoints=@($top.ToCharArray() | ForEach-Object {[int]$_}); cases=$records}
  }
} finally { [Console]::OutputEncoding = [Text.Encoding]::GetEncoding($initialEncoding) }
$mocks = @()
function git {
  $step = $script:steps[$script:stepIndex]
  $script:stepIndex++
  $global:LASTEXITCODE = [int]$step.exit
  foreach ($line in $step.out) { Write-Output ([string]$line) }
}
foreach ($case in (Get-Content -LiteralPath (Join-Path $output 'mock_cases.json') -Raw -Encoding UTF8 | ConvertFrom-Json)) {
  $script:steps = @($case.steps); $script:stepIndex = 0
  $record = Capture 'Get-ExactGitCommit' $repo
  $mocks += [ordered]@{name=$case.name; expected=[string]$case.expected; result=$record; calls=$script:stepIndex}
}
Remove-Item Function:git
$report = [ordered]@{ps_version=$PSVersionTable.PSVersion.ToString(); initial_output_code_page=$initialEncoding; initial_input_code_page=$initialInput; output_code_page_restored=([Console]::OutputEncoding.CodePage -eq $initialEncoding); native=$results; mocks=$mocks; production_ast_errors=0}
[IO.File]::WriteAllText((Join-Path $output 'ps_result.json'), ($report | ConvertTo-Json -Depth 20), (New-Object Text.UTF8Encoding($false)))
'''.replace("__HISTORICAL__", before.replace('Get-ExactGitCommit(', 'Get-OriginalGitCommit('))
        path = cls.output / "isolated_functions.ps1"
        path.write_text(script, encoding="utf-8-sig")
        env = dict(os.environ, EXACT_GIT_TEST_REPO=str(ROOT), EXACT_GIT_TEST_OUTPUT=str(cls.output))
        env["PSModulePath"] = str(native.parent / "Modules")
        proc = subprocess.run([str(native), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(path)], cwd=ROOT, env=env, capture_output=True, timeout=30)
        (cls.output / "stdout.bin").write_bytes(proc.stdout)
        (cls.output / "stderr.bin").write_bytes(proc.stderr)
        cls.report = {"process_exit": proc.returncode, "git_raw": cls.raw_git, "source_before": cls.pins}
        cls.report["source_after"] = {str(p.relative_to(ROOT)): sha(p) for p in (SOURCE, PATCH, Path(__file__))}
        cls.report["source_changes"] = [p for p in cls.pins if cls.pins[p] != cls.report["source_after"][p]]
        if (cls.output / "ps_result.json").exists():
            cls.report["powershell"] = json.loads((cls.output / "ps_result.json").read_text(encoding="utf-8-sig"))
        (cls.output / "evidence.json").write_text(json.dumps(cls.report, ensure_ascii=False, indent=2), encoding="utf-8")
        print("EVIDENCE=" + str(cls.output), flush=True)
        if proc.returncode or "powershell" not in cls.report:
            raise RuntimeError("Isolated PowerShell failed; inspect retained stdout/stderr")

    def test_ps51_source_unchanged_and_raw_utf8_unquoted(self):
        self.assertTrue(self.report["powershell"]["ps_version"].startswith("5.1."))
        self.assertEqual(self.report["source_changes"], [])
        self.assertTrue(self.raw_git["quotepath_false_bytes_equal"])
        self.assertFalse(self.raw_git["toplevel_utf8"].startswith('"'))

    def test_original_cp949_invalid_path_reproduced(self):
        row = next(r for r in self.report["powershell"]["native"] if r["code_page"] == 949)
        self.assertEqual(row["cases"]["root"]["original"]["value"], "")
        self.assertTrue(row["cases"]["root"]["original"]["errors"])
        self.assertIn("?", row["decoded_toplevel"])

    def test_root_commit_exact_all_encodings(self):
        for row in self.report["powershell"]["native"]:
            for name in ("root", "trailing", "relative"):
                with self.subTest(code_page=row["code_page"], case=name):
                    result = row["cases"][name]["proposed"]
                    self.assertEqual(result, {"value": self.expected, "errors": []})

    def test_nonroots_and_missing_paths_fail_closed(self):
        for row in self.report["powershell"]["native"]:
            for name in ("child", "missing", "file"):
                with self.subTest(code_page=row["code_page"], case=name):
                    self.assertEqual(row["cases"][name]["proposed"], {"value": "", "errors": []})

    def test_installed_vendor_identity_does_not_alias_parent_commit(self):
        for row in self.report["powershell"]["native"]:
            with self.subTest(code_page=row["code_page"]):
                self.assertEqual(row["cases"]["vendor"]["proposed"], {"value": self.vendor_expected, "errors": []})
        if not self.raw_git["vendor"]["is_own_git_root"]:
            self.assertEqual(self.vendor_expected, "")
            self.assertNotEqual(self.raw_git["vendor"]["show_cdup"], "")

    def test_failed_or_malformed_git_outputs(self):
        for row in self.report["powershell"]["mocks"]:
            with self.subTest(case=row["name"]):
                self.assertEqual(row["result"], {"value": row["expected"], "errors": []})

    def test_utf8_old_new_and_environment(self):
        row = next(r for r in self.report["powershell"]["native"] if r["code_page"] == 65001)
        self.assertEqual(row["cases"]["root"]["original"], row["cases"]["root"]["proposed"])
        self.assertTrue(self.report["powershell"]["output_code_page_restored"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
