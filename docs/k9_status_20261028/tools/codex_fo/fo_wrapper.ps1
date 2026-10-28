# [FO copy 2026-10-27 KST, PRE_FO s5: copy of codex_handoff/b/b_wrapper_b1.ps1 (sha256 93814842ae7a504e714c309a58caf77621aba153db36fa953258db72db5a1185) with names changed and the declared FO
# additions; full diff in codex_handoff/fo/work/run/launcher_b_to_fo.diff. The original header follows.]
# B run wrapper for FRZ_B1 (2026-10-26, D-K9-90, PRE_B_CONCURRENT.md 3d21dddd... s4). Runs under pwsh 7 (codex runtime),
# started detached by WMI from fo_launcher.ps1 only. Derived from work/b/b_wrapper.ps1 (43348294...), itself the A1 wrapper v2
# pattern (7a913760...): clears NUMBA*/PYTHON*/OPENBLAS/NPY/MKL extras and every RW_* with Remove-Item, sets env_hsw +
# PYTHONHASHSEED=0, records the environment and Python/dependency versions, then runs the frozen codex runner
# run_closedloop3000.ps1 of FRZ_B1 unchanged with the PRE_B s1 arguments (B closed loop, one seed, 9,000 s, arm sdmpc only).
# Differences from work/b/b_wrapper.ps1 (only these):
#   1. FRZ = FRZ_B1 (b1/frozen/sdmpc31_a49981ff_202610261410).
#   2. -Try <n>: a launch try number, separate from -Attempt (run attempt; 2 = the one relaunch after a stall).
#      A runner refusal at the 4-seat cap is a failed launch try, not a run (PRE_FO s6-4), so each try has its own
#      record names 'run<A>_try<T>' and its own once-only marker.
#   3. After the runner ends, the runner status file (native_status.json) is copied to b_launch/native_status_run<A>_try<T>.json
#      so the launcher can tell a seat refusal from an abnormal end even after a later try overwrites the status file.
# usage (pwsh 7): fo_wrapper.ps1 -Seed 31 -Attempt 1 -Try 1
param([Parameter(Mandatory = $true)][ValidateSet(31, 41, 43)][int]$Seed,
      [Parameter(Mandatory = $true)][ValidateRange(1, 2)][int]$Attempt,
      [Parameter(Mandatory = $true)][ValidateRange(1, 20)][int]$Try)
$ErrorActionPreference = 'Stop'
$FRZ  = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\fo\frozen\sdmpc31_a49981ff_202610271954'
$RES  = 'D:\VISSIM_runs\20261028_codex_fo_v3c3\s' + $Seed
$PY   = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$PWSH = 'C:\Users\TRLAB\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$DEPS = 'D:\VISSIM-window264-deps'
$TUN  = 'diagnostics/b0_v3c3/config_fo_v3c3.json'
$NETREL = 'diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx'
$NETSHA = '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e'
$RUNNER = Join-Path $FRZ 'diagnostics\sdmpc_n31_20260924\integration_20260926\run_closedloop3000.ps1'
$mode = 'run' + $Attempt + '_try' + $Try
$rec = Join-Path $RES 'fo_launch'
New-Item -ItemType Directory -Force -Path $rec | Out-Null
$marker = Join-Path $rec ('wrapper_' + $mode + '_started.json')
if (Test-Path -LiteralPath $marker) { throw "wrapper $mode already started once: $marker" }
function Save([string]$name, $obj) { ($obj | ConvertTo-Json -Depth 8) | Set-Content -Encoding utf8 -LiteralPath (Join-Path $rec $name) }
try {
$me = Get-Process -Id $PID
Save ('wrapper_' + $mode + '_started.json') ([ordered]@{ mode = $mode; seed = $Seed; attempt = $Attempt; try = $Try;
  time = [DateTimeOffset]::Now.ToString('o'); wrapper_pid = $PID; wrapper_priority = $me.PriorityClass.ToString(); wrapper_exe = $me.Path;
  ps_version = $PSVersionTable.PSVersion.ToString(); cwd = (Get-Location).Path; frz = $FRZ })

# ---- environment (declared, PRE_B s1) ----
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

# ---- record the whole environment the runner will inherit (secret-looking names redacted) ----
$envRec = [ordered]@{}
foreach ($e in (Get-ChildItem Env: | Sort-Object Name)) {
  if ($e.Name -match '(?i)(token|secret|password|passwd|apikey|api_key|credential|auth)') { $envRec[$e.Name] = '<redacted>' } else { $envRec[$e.Name] = [string]$e.Value }
}
Save ('wrapper_' + $mode + '_env.json') ([ordered]@{ time = [DateTimeOffset]::Now.ToString('o'); set = $set; removed = $cleared; removed_rw_prefix = 'RW_*';
  rw_left_after_clear = $rwLeft; process_env = $envRec })

# ---- Python / dependency versions under the same env (+ PYTHONPATH = deps only, then cleared again) ----
$probe = @'
import sys, json, platform
out = {"sys_version": sys.version, "executable": sys.executable, "platform": platform.platform()}
import numpy, scipy, numba, llvmlite, pandas
out["versions"] = {m.__name__: m.__version__ for m in (numpy, scipy, numba, llvmlite, pandas)}
out["files"] = {m.__name__: m.__file__ for m in (numpy, scipy, numba, llvmlite, pandas)}
try:
    from numpy._core._multiarray_umath import __cpu_features__ as f
    out["numpy_cpu_features_avx512_true"] = sorted(k for k, v in f.items() if v and k.startswith("AVX512"))
    out["numpy_cpu_features_avx2"] = bool(f.get("AVX2"))
except Exception as e:
    out["numpy_cpu_features_error"] = repr(e)
try:
    import llvmlite.binding as llb
    out["llvm_host_cpu_name"] = llb.get_host_cpu_name()
    out["numba_config_cpu_name"] = numba.config.CPU_NAME
except Exception as e:
    out["numba_cpu_error"] = repr(e)
print(json.dumps(out))
'@
$probeFile = Join-Path $rec ('probe_' + $mode + '.py')
Set-Content -Encoding utf8 -LiteralPath $probeFile -Value $probe
$env:PYTHONPATH = $DEPS
$pyvv = (& $PY -VV) -join ' '
$probeOut = (& $PY -B $probeFile) -join ''
Remove-Item -LiteralPath 'Env:PYTHONPATH' -ErrorAction SilentlyContinue
Save ('wrapper_' + $mode + '_python.json') ([ordered]@{ python_exe = $PY; python_vv = $pyvv; probe = ($probeOut | ConvertFrom-Json); deps = $DEPS; pwsh = $PWSH })

# ---- the runner, unchanged (PRE_B s1 arguments, FRZ_B1) ----
$statusPath = Join-Path $RES 'native_status.json'
$argv = @('-NoProfile', '-NonInteractive', '-File', $RUNNER, '-FrozenTree', $FRZ, '-ResultsRoot', $RES,
  '-StatusPath', $statusPath,
  '-SimPeriod', '9000', '-Seed', [string]$Seed, '-Arms', 'sdmpc', '-TuningRelativePath', $TUN,
  '-NetworkRelativePath', $NETREL, '-NetworkSha256', $NETSHA,
  '-PythonExe', $PY, '-PowerShellExe', $PWSH, '-DependenciesPath', $DEPS)
Save ('wrapper_' + $mode + '_runner_cmd.json') ([ordered]@{ time = [DateTimeOffset]::Now.ToString('o'); exe = $PWSH; argv = $argv; cwd = $FRZ })
Set-Location -LiteralPath $FRZ
$t0 = Get-Date
& $PWSH @argv *> (Join-Path $rec ('runner_' + $mode + '.log'))
$code = $LASTEXITCODE
if (Test-Path -LiteralPath $statusPath) {
  Copy-Item -LiteralPath $statusPath -Destination (Join-Path $rec ('native_status_' + $mode + '.json')) -Force -ErrorAction SilentlyContinue
}
Save ('wrapper_' + $mode + '_end.json') ([ordered]@{ time = [DateTimeOffset]::Now.ToString('o'); runner_exit = $code;
  wall_sec = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1) })
exit $code
} catch {
  Save ('wrapper_' + $mode + '_error.json') ([ordered]@{ time = [DateTimeOffset]::Now.ToString('o'); error = [string]$_ })
  exit 3
}
