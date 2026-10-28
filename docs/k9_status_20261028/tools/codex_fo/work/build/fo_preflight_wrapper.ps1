# FO (2026-10-27, D-K9-113): runner -PreflightOnly of the FO frozen tree (FRZ_FO) for one seed. No VISSIM, no cscript.
# Copy of work/b1/b1_preflight_wrapper.ps1 (B1) with only these changes: root = fo (FRZ must be under fo\frozen), default tuning =
# the FO config diagnostics/b0_v3c3/config_fo_v3c3.json, optional -Tag (label s<seed><tag>; tag 'b' = the B config on FRZ_FO,
# used only as the provenance input of the gate control replay R0). Same environment handling (clears NUMBA*/PYTHON*/OPENBLAS/
# NPY/MKL extras and every RW_* with Remove-Item, sets env_hsw + PYTHONHASHSEED=0, records the environment), same runner
# arguments as B (PRE_B s1) except -FrozenTree / -ResultsRoot / -TuningRelativePath. Records the watchdog child command line
# (-StallSec) and the runner status at stage 'preflight'. usage (pwsh 7): fo_preflight_wrapper.ps1 -Seed 31 -Frz <FRZ_FO> [-Tag b -TuningRel ...]
param([Parameter(Mandatory = $true)][ValidateSet(31, 41, 43)][int]$Seed, [Parameter(Mandatory = $true)][string]$Frz,
      [string]$TuningRel = 'diagnostics/b0_v3c3/config_fo_v3c3.json', [ValidateSet('', 'b')][string]$Tag = '')
$ErrorActionPreference = 'Stop'
$FOR  = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\fo'
$PY   = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$PWSH = 'C:\Users\TRLAB\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$DEPS = 'D:\VISSIM-window264-deps'
$NETREL = 'diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx'
$NETSHA = '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e'
$FRZ = [IO.Path]::GetFullPath($Frz)
if (-not $FRZ.StartsWith($FOR + '\frozen\', [StringComparison]::OrdinalIgnoreCase)) { throw "FRZ is not under fo\frozen: $FRZ" }
$RUNNER = Join-Path $FRZ 'diagnostics\sdmpc_n31_20260924\integration_20260926\run_closedloop3000.ps1'
$label = 's' + $Seed + $Tag
$RES = Join-Path $FOR ('runner_preflight\' + $label)
$rec = Join-Path $FOR ('runner_preflight\_wrapper\' + $label)
if (Test-Path -LiteralPath $RES) { throw "results root exists, no second preflight: $RES" }
New-Item -ItemType Directory -Force -Path $rec | Out-Null
function Save([string]$name, $obj) { ($obj | ConvertTo-Json -Depth 8) | Set-Content -Encoding utf8 -LiteralPath (Join-Path $rec $name) }
try {
$me = Get-Process -Id $PID
Save 'started.json' ([ordered]@{ label = $label; time = [DateTimeOffset]::Now.ToString('o'); wrapper_pid = $PID; tuning_rel = $TuningRel;
  wrapper_priority = $me.PriorityClass.ToString(); wrapper_exe = $me.Path; ps_version = $PSVersionTable.PSVersion.ToString(); cwd = (Get-Location).Path; frz = $FRZ })
$cleared = @('NUMBA_NUM_THREADS','NUMBA_THREADING_LAYER','NUMBA_CACHE_DIR','NUMBA_DISABLE_JIT','NUMBA_OPT','NUMBA_DEBUG',
  'PYTHONPYCACHEPREFIX','PYTHONHOME','PYTHONSTARTUP','PYTHONPATH','PYTHONOPTIMIZE','PYTHONWARNINGS','PYTHONINSPECT','PYTHONNOUSERSITE',
  'OPENBLAS_VERBOSE','OPENBLAS_MAIN_FREE','NPY_ENABLE_CPU_FEATURES','MKL_CBWR','MKL_ENABLE_INSTRUCTIONS')
foreach ($n in $cleared) { Remove-Item -LiteralPath ('Env:' + $n) -ErrorAction SilentlyContinue }
foreach ($item in @(Get-ChildItem Env: | Where-Object { $_.Name -like 'RW_*' })) { Remove-Item -LiteralPath ('Env:' + $item.Name) -ErrorAction SilentlyContinue }
$set = [ordered]@{ PYTHONHASHSEED = '0'; OPENBLAS_CORETYPE = 'Haswell';
  NPY_DISABLE_CPU_FEATURES = 'AVX512F AVX512CD AVX512_SKX AVX512_CLX'; NUMBA_CPU_NAME = 'haswell' }
foreach ($k in $set.Keys) { [Environment]::SetEnvironmentVariable($k, $set[$k], 'Process') }
$rwLeft = @(Get-ChildItem Env: | Where-Object { $_.Name -like 'RW_*' } | ForEach-Object { $_.Name })
if ($rwLeft.Count) { throw ('RW_* still present after clearing: ' + ($rwLeft -join ',')) }
$envRec = [ordered]@{}
foreach ($e in (Get-ChildItem Env: | Sort-Object Name)) {
  if ($e.Name -match '(?i)(token|secret|password|passwd|apikey|api_key|credential|auth)') { $envRec[$e.Name] = '<redacted>' } else { $envRec[$e.Name] = [string]$e.Value }
}
Save 'env.json' ([ordered]@{ time = [DateTimeOffset]::Now.ToString('o'); set = $set; removed = $cleared; removed_rw_prefix = 'RW_*'; rw_left_after_clear = $rwLeft; process_env = $envRec })
$statusPath = Join-Path $rec 'preflight_status.json'
$argv = @('-NoProfile', '-NonInteractive', '-File', $RUNNER, '-PreflightOnly', '-FrozenTree', $FRZ, '-ResultsRoot', $RES,
  '-StatusPath', $statusPath, '-SimPeriod', '9000', '-Seed', [string]$Seed, '-Arms', 'sdmpc',
  '-TuningRelativePath', $TuningRel, '-NetworkRelativePath', $NETREL, '-NetworkSha256', $NETSHA,
  '-PythonExe', $PY, '-PowerShellExe', $PWSH, '-DependenciesPath', $DEPS)
foreach ($a in $argv) { if ($a -match '[\s"]') { throw "argument with space or quote: $a" } }
Save 'runner_cmd.json' ([ordered]@{ time = [DateTimeOffset]::Now.ToString('o'); exe = $PWSH; argv = $argv; cwd = $FRZ })
Set-Location -LiteralPath $FRZ
$t0 = Get-Date
$p = Start-Process -FilePath $PWSH -ArgumentList $argv -NoNewWindow -PassThru `
  -RedirectStandardOutput (Join-Path $rec 'runner.log') -RedirectStandardError (Join-Path $rec 'runner.err.log')
$null = $p.Handle
$wdSeen = $null; $statusSeen = $false
while (-not $p.HasExited) {
  if ($null -eq $wdSeen) {
    $kids = @(Get-CimInstance Win32_Process -Filter ("ParentProcessId=" + $p.Id) -ErrorAction SilentlyContinue |
      Where-Object { $_.CommandLine -match 'run_real_world_single_watchdog' })
    if ($kids.Count) {
      $wdSeen = [ordered]@{ time = [DateTimeOffset]::Now.ToString('o'); runner_pid = $p.Id; pid = [int]$kids[0].ProcessId;
        name = $kids[0].Name; command_line = [string]$kids[0].CommandLine }
      Save 'watchdog_cmdline.json' $wdSeen
    }
  }
  if (-not $statusSeen -and (Test-Path -LiteralPath $statusPath)) {
    try {
      $txt = Get-Content -LiteralPath $statusPath -Raw -Encoding utf8
      if (($txt | ConvertFrom-Json).stage -eq 'preflight') {
        Set-Content -LiteralPath (Join-Path $rec 'preflight_status_stage_preflight.json') -Value $txt -Encoding utf8 -NoNewline
        $statusSeen = $true
      }
    } catch {}
  }
  Start-Sleep -Milliseconds 300
}
$p.WaitForExit()
$code = $p.ExitCode
Save 'end.json' ([ordered]@{ time = [DateTimeOffset]::Now.ToString('o'); runner_exit = $code; wall_sec = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1);
  watchdog_cmdline_seen = ($null -ne $wdSeen); status_stage_preflight_seen = $statusSeen })
exit $code
} catch {
  Save 'error.json' ([ordered]@{ time = [DateTimeOffset]::Now.ToString('o'); error = [string]$_ })
  exit 3
}
