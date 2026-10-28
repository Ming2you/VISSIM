# Gate 1 (2026-10-26): runner -PreflightOnly of the B frozen tree (FRZ_B0) for one seed. No VISSIM, no cscript.
# Same pattern as A1 wrapper v2 (D:/VISSIM_runtime/20261025_codex_a1/launch/a1_wrapper.ps1 7a913760...):
# clears NUMBA*/PYTHON*/OPENBLAS/NPY/MKL extras and every RW_* with Remove-Item (pwsh 7 SetEnvironmentVariable(null)
# leaves an empty value), sets env_hsw + PYTHONHASHSEED=0, records the environment and the Python/dependency versions,
# then runs the frozen runner unchanged with the PRE_B s1 arguments. Results go to a scratch root (not the B results root).
# usage (pwsh 7): g1_preflight_wrapper.ps1 -Seed 31 [-Tag gk -TuningRel diagnostics/b0_v3c3/config_b0_v3c3_groupkeys.json]
param([Parameter(Mandatory = $true)][int]$Seed, [string]$Tag = '',
      [string]$TuningRel = 'diagnostics/b0_v3c3/config_b0_v3c3.json')
$ErrorActionPreference = 'Stop'
$FRZ  = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\b0\frozen\sdmpc31_a49981ff_202610260258'
$G1   = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\gate1'
$PY   = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$PWSH = 'C:\Users\TRLAB\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$DEPS = 'D:\VISSIM-window264-deps'
$NETREL = 'diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx'
$NETSHA = '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e'
$RUNNER = Join-Path $FRZ 'diagnostics\sdmpc_n31_20260924\integration_20260926\run_closedloop3000.ps1'
$label = 's' + $Seed + $Tag
$RES = Join-Path $G1 ('runner_preflight\' + $label)
$rec = Join-Path $G1 ('runner_preflight\_wrapper\' + $label)
if (Test-Path -LiteralPath $RES) { throw "results root exists, no second preflight: $RES" }
New-Item -ItemType Directory -Force -Path $rec | Out-Null
function Save([string]$name, $obj) { ($obj | ConvertTo-Json -Depth 8) | Set-Content -Encoding utf8 -LiteralPath (Join-Path $rec $name) }
try {
$me = Get-Process -Id $PID
Save 'started.json' ([ordered]@{ label = $label; time = [DateTimeOffset]::Now.ToString('o'); wrapper_pid = $PID;
  wrapper_priority = $me.PriorityClass.ToString(); wrapper_exe = $me.Path; ps_version = $PSVersionTable.PSVersion.ToString(); cwd = (Get-Location).Path })
$cleared = @('NUMBA_NUM_THREADS','NUMBA_THREADING_LAYER','NUMBA_CACHE_DIR','NUMBA_DISABLE_JIT','NUMBA_OPT','NUMBA_DEBUG',
  'PYTHONPYCACHEPREFIX','PYTHONHOME','PYTHONSTARTUP','PYTHONPATH','PYTHONOPTIMIZE','PYTHONWARNINGS','PYTHONINSPECT','PYTHONNOUSERSITE',
  'OPENBLAS_VERBOSE','OPENBLAS_MAIN_FREE','NPY_ENABLE_CPU_FEATURES','MKL_CBWR','MKL_ENABLE_INSTRUCTIONS')
foreach ($n in $cleared) { Remove-Item -LiteralPath ('Env:' + $n) -ErrorAction SilentlyContinue }
foreach ($item in @(Get-ChildItem Env: | Where-Object { $_.Name -like 'RW_*' })) { Remove-Item -LiteralPath ('Env:' + $item.Name) -ErrorAction SilentlyContinue }
$set = [ordered]@{ PYTHONHASHSEED = '0'; OPENBLAS_CORETYPE = 'Haswell';
  NPY_DISABLE_CPU_FEATURES = 'AVX512F AVX512CD AVX512_SKX AVX512_CLX'; NUMBA_CPU_NAME = 'haswell' }
foreach ($k in $set.Keys) { [Environment]::SetEnvironmentVariable($k, $set[$k], 'Process') }
$envRec = [ordered]@{}
foreach ($e in (Get-ChildItem Env: | Sort-Object Name)) {
  if ($e.Name -match '(?i)(token|secret|password|passwd|apikey|api_key|credential|auth)') { $envRec[$e.Name] = '<redacted>' } else { $envRec[$e.Name] = [string]$e.Value }
}
Save 'env.json' ([ordered]@{ time = [DateTimeOffset]::Now.ToString('o'); set = $set; removed = $cleared; removed_rw_prefix = 'RW_*'; process_env = $envRec })
$argv = @('-NoProfile', '-NonInteractive', '-File', $RUNNER, '-PreflightOnly', '-FrozenTree', $FRZ, '-ResultsRoot', $RES,
  '-StatusPath', (Join-Path $rec 'preflight_status.json'), '-SimPeriod', '9000', '-Seed', [string]$Seed, '-Arms', 'sdmpc',
  '-TuningRelativePath', $TuningRel, '-NetworkRelativePath', $NETREL, '-NetworkSha256', $NETSHA,
  '-PythonExe', $PY, '-PowerShellExe', $PWSH, '-DependenciesPath', $DEPS)
Save 'runner_cmd.json' ([ordered]@{ time = [DateTimeOffset]::Now.ToString('o'); exe = $PWSH; argv = $argv; cwd = $FRZ })
Set-Location -LiteralPath $FRZ
$t0 = Get-Date
& $PWSH @argv *> (Join-Path $rec 'runner.log')
$code = $LASTEXITCODE
Save 'end.json' ([ordered]@{ time = [DateTimeOffset]::Now.ToString('o'); runner_exit = $code; wall_sec = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1) })
exit $code
} catch {
  Save 'error.json' ([ordered]@{ time = [DateTimeOffset]::Now.ToString('o'); error = [string]$_ })
  exit 3
}
