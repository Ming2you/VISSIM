<#
VBS compile check (SDMPC31_OBS150_PLAN_20260924 V1, WP-A). No VISSIM, no COM object, no seat.

VBScript compiles a whole file before it runs a single statement. A copy of the runner with
`WScript.Quit 0` inserted right after its `Option Explicit` line therefore reports every syntax
error and, when there is none, exits before the first statement runs. The copy keeps the
original bytes (cscript reads them in the ANSI code page exactly as it reads the real runner)
except for the one inserted line, which takes the line ending of the `Option Explicit` line.

An undefined variable is a run-time error in VBScript, so it is NOT caught here (G1 catches it).

  powershell -NoProfile -ExecutionPolicy Bypass -File tools\vbs_compile_check.ps1 [-Path <file.vbs>[,<file.vbs>...]]

Default path: scripts\run_real_world_stackelberg_controller.vbs of this tree. Run it from
PowerShell, never from Git Bash (the working tree may sit under a non-ASCII path).
One line per file: VBS_COMPILE_OK path=<p> sha256=<sha> | VBS_COMPILE_FAIL path=<p> exit=<n> message=<text>.
Exit 0: every file compiles. 1: a file does not compile. 2: usage (missing file, no Option Explicit).
#>
[CmdletBinding(PositionalBinding=$false)]
param(
  [string[]]$Path = @(),
  [ValidateRange(5,600)][int]$TimeoutSec = 60
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if ($Path.Count -eq 0) { $Path = @(Join-Path $repo 'scripts\run_real_world_stackelberg_controller.vbs') }
$cscript = Join-Path $env:SystemRoot 'System32\cscript.exe'
# Latin-1 maps every byte to one char and back, so the copy is byte-exact apart from the insert.
$latin1 = [Text.Encoding]::GetEncoding(28591)
$failed = 0
foreach ($item in $Path) {
  $full = $item
  if (-not [IO.Path]::IsPathRooted($full)) { $full = Join-Path (Get-Location).Path $full }
  $full = [IO.Path]::GetFullPath($full)
  if (-not (Test-Path -LiteralPath $full -PathType Leaf)) {
    [Console]::Out.WriteLine("VBS_COMPILE_USAGE missing=$full")
    exit 2
  }
  $bytes = [IO.File]::ReadAllBytes($full)
  $sha = (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLowerInvariant()
  $text = $latin1.GetString($bytes)
  $match = [regex]::Match($text, '(?im)^[ \t]*Option[ \t]+Explicit[ \t]*(\r?\n)')
  if (-not $match.Success) {
    [Console]::Out.WriteLine("VBS_COMPILE_USAGE no_option_explicit=$full")
    exit 2
  }
  $insertAt = $match.Index + $match.Length
  $copyText = $text.Substring(0, $insertAt) + 'WScript.Quit 0' + $match.Groups[1].Value + $text.Substring($insertAt)
  $work = Join-Path ([IO.Path]::GetTempPath()) ('vbs_compile_check_' + [guid]::NewGuid().ToString('N'))
  New-Item -ItemType Directory -Force -Path $work | Out-Null
  try {
    $copy = Join-Path $work ([IO.Path]::GetFileName($full))
    [IO.File]::WriteAllBytes($copy, $latin1.GetBytes($copyText))
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = $cscript
    $info.Arguments = '//nologo //T:' + $TimeoutSec + ' "' + $copy + '"'
    $info.UseShellExecute = $false
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $info.CreateNoWindow = $true
    $info.WorkingDirectory = $work
    # cscript writes its messages in the OEM code page (949 on this PC).
    $oem = [Text.Encoding]::GetEncoding([Globalization.CultureInfo]::CurrentCulture.TextInfo.OEMCodePage)
    $info.StandardOutputEncoding = $oem
    $info.StandardErrorEncoding = $oem
    $process = [Diagnostics.Process]::Start($info)
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    if (-not $process.WaitForExit(($TimeoutSec + 30) * 1000)) {
      $process.Kill()
      throw "cscript did not finish: $copy"
    }
    $out = $stdoutTask.Result
    $err = $stderrTask.Result
    $code = $process.ExitCode
    $message = (($out + ' ' + $err) -replace '\s+', ' ').Trim()
    # Quit 0 runs before any statement of the runner, so any output means the insert did not take.
    if ($code -eq 0 -and $message -eq '') {
      [Console]::Out.WriteLine("VBS_COMPILE_OK path=$full sha256=$sha")
    } else {
      $failed++
      [Console]::Out.WriteLine("VBS_COMPILE_FAIL path=$full exit=$code message=$message")
    }
  } finally {
    Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
  }
}
if ($failed -gt 0) { exit 1 }
exit 0
