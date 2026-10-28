# B0: launch one configure probe via launch_wmi_b0.ps1 (detached, BELOW_NORMAL) and wait for it (max -MaxSec), then print
# status, exit code, wall time and the last error lines.  Read-only toward everything but b0/out and b0/runs.
param([Parameter(Mandatory=$true)][string]$Label, [int]$T = 3900, [string]$Src = 'va_s31',
      [string]$TuningRel = 'diagnostics\b0_v3c3\config_b0_v3c3.json', [string]$Mode = 'configure', [int]$MaxSec = 900)
$W = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\b0'
$hsw = 'OPENBLAS_CORETYPE=Haswell;NPY_DISABLE_CPU_FEATURES=AVX512F AVX512CD AVX512_SKX AVX512_CLX;NUMBA_CPU_NAME=haswell'
$a = '-T ' + $T + ' -Src ' + $Src + ' -Label ' + $Label + ' -TuningRel "' + $TuningRel + '" -Mode ' + $Mode + ' -ExtraEnv "' + $hsw + '" -Note "' + $Label + '"'
& (Join-Path $W 'launch_wmi_b0.ps1') -Script (Join-Path $W 'run_replay_b0.ps1') -ArgString $a | Out-Null
$O = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\b0\out\' + $Label + '\' + $Src + '\T' + ('{0:D6}' -f $T)
$t0 = Get-Date
while (((Get-Date) - $t0).TotalSeconds -lt $MaxSec) {
  Start-Sleep -Seconds 5
  $sp = Join-Path $O 'replay_state.json'
  if (Test-Path -LiteralPath $sp) { try { if ((Get-Content -LiteralPath $sp -Raw | ConvertFrom-Json).status -eq 'done') { break } } catch {} }
}
$st = Get-Content -LiteralPath (Join-Path $O 'replay_state.json') -Raw | ConvertFrom-Json
"status=$($st.status) exit=$($st.exit_code) wall=$($st.wall_sec) prio=$($st.python_priority)"
if (Test-Path -LiteralPath (Join-Path $O 'stdout.txt')) { Get-Content -LiteralPath (Join-Path $O 'stdout.txt') -Tail 2 }
if (Test-Path -LiteralPath (Join-Path $O 'stderr.txt')) { Get-Content -LiteralPath (Join-Path $O 'stderr.txt') -Tail 2 }
$err = Get-ChildItem -Path ('D:\VISSIM-merge\k8_gate_trees\codexhandoff\b0\runs\' + $Src + '\T' + ('{0:D6}' -f $T) + '\run\decisions_*\action_*.error.txt') -ErrorAction SilentlyContinue
foreach ($e in $err) { Get-Content -LiteralPath $e.FullName | Select-String -Pattern '^  File ' | Select-Object -Last 4 | ForEach-Object { $_.Line } }
