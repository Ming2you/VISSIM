# B0: the codex watchdog in -PreflightOnly mode on the b0 tree and the v3c3 network (no VISSIM, no cscript, no COM).
# Same environment and arguments as run_closedloop3000.ps1:107-117 and :153-161 would give, except: the workspace is the
# b0 tree (not frozen; the watchdog then records freeze = null), the network is the v3c3 copy, the tuning is the b0 one.
# Output: b0/preflight/<Label>/  (network copy, preflight provenance, launch log).
param([Parameter(Mandatory=$true)][string]$Label, [int]$Seed = 31, [int]$SimPeriod = 9000,
      [string]$TuningRel = 'diagnostics\b0_v3c3\config_b0_v3c3.json',
      [string]$VbsRel = 'diagnostics\sdmpc_n31_20260924\integration_20260926\selected\scenario\lane_native_b110.vbs')
$ErrorActionPreference = 'Stop'
$B0 = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\b0'
$frozen = Join-Path $B0 'code'
$pythonExe = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$pwshExe = 'C:\Users\TRLAB\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$DependenciesPath = 'D:\VISSIM-window264-deps'
$root = Join-Path $B0 ('preflight\' + $Label)
if (Test-Path -LiteralPath $root) { throw "exists: $root" }
$name = 'sdmpc31_sdmpc' + $SimPeriod + '_s' + $Seed
$out = Join-Path $root 'sdmpc'
$netDir = Join-Path $out 'network'
New-Item -ItemType Directory -Path $netDir -Force | Out-Null
$srcNet = Join-Path $frozen 'diagnostics\sdmpc_n31_20260924\network'
$network = Join-Path $netDir ($name + '.inpx')
Copy-Item -LiteralPath (Join-Path $srcNet 'baseline_s31_v3c3nc.inpx') -Destination $network
Get-ChildItem -LiteralPath $srcNet -Filter '*.sig' | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $netDir }
$netSha = (Get-FileHash -LiteralPath $network -Algorithm SHA256).Hash.ToLowerInvariant()
if ($netSha -cne '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e') { throw 'Network differs' }
Set-Location -LiteralPath $frozen
foreach ($item in @(Get-ChildItem Env: | Where-Object { $_.Name -like 'RW_*' })) { Remove-Item -LiteralPath ('Env:' + $item.Name) }
$env:RW_PYTHON = $pythonExe; $env:RW_MAINLINE_SG_ONLY = '1'; $env:RW_OFFSET_WRITER = 'experiment'
$env:RW_RAMP_AMBER_SEC = '0'; $env:RW_DECISION_FAIL_FAST = '1'; $env:RW_QUEUE_COUNTER = '1'
$env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONPATH = $DependenciesPath + ';' + $frozen
$env:NUMSIM_REPO_ROOT = Join-Path $frozen 'vendor/NumSim-mine'
$env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'
$env:PYTHONHASHSEED = '0'
$env:OPENBLAS_CORETYPE = 'Haswell'; $env:NPY_DISABLE_CPU_FEATURES = 'AVX512F AVX512CD AVX512_SKX AVX512_CLX'; $env:NUMBA_CPU_NAME = 'haswell'
$tuningPath = Join-Path $frozen $TuningRel
$selectedRoot = Join-Path $frozen 'diagnostics/sdmpc_n31_20260924/integration_20260926/selected'
$arguments = @('-NoProfile', '-File', (Join-Path $frozen 'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1'),
  '-Name', $name, '-Network', $network, '-OutDir', (Join-Path $out 'preflight'), '-SimPeriod', [string]$SimPeriod, '-ControlIntervalSec', '150', '-Seed', [string]$Seed,
  '-Controller', 'wu-link', '-ControlStartSec', '900', '-WarmupController', 'no-control', '-StateLogIntervalSec', '150',
  '-DemandScale', '1', '-DemandProfile', (Join-Path $selectedRoot 'scenario/profile.csv'),
  '-VehicleInputRoles', (Join-Path $frozen 'evaluation/real_world_modi_inventory/vehicle_input_roles.csv'),
  '-UrbanInputGateMap', (Join-Path $frozen 'evaluation/real_world_modi_inventory/urban_input_gate_map_ver2_20260907.csv'),
  '-Calibration', (Join-Path $frozen 'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'),
  '-Mapping', (Join-Path $frozen 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'),
  '-Tuning', $tuningPath, '-VbsConfig', (Join-Path $frozen $VbsRel),
  '-NoGlobalKill', '-MaxAttempts', '1', '-StartupStallSec', '300', '-StallSec', '2400', '-PreflightOnly')
$rec = [ordered]@{ label = $Label; wrapper_pid = $PID; start = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss.fff zzz'); network_sha256 = $netSha;
  tuning = $tuningPath; tuning_sha256 = (Get-FileHash -LiteralPath $tuningPath -Algorithm SHA256).Hash.ToLowerInvariant(); arguments = $arguments }
($rec | ConvertTo-Json -Depth 5) | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $root 'wd_preflight.json')
& $pwshExe @arguments *> (Join-Path $out 'preflight_launch.log')
$rec.exit = $LASTEXITCODE
$rec.end = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss.fff zzz')
($rec | ConvertTo-Json -Depth 5) | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $root 'wd_preflight.json')
