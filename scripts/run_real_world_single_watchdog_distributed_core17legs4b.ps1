<#
Run one real-world Gaepo modi VISSIM controller case with a no-progress watchdog.

Progress is the newest mtime among the run log, state CSV, action CSV, and
decision action JSONs. If nothing moves for StallSec seconds, cscript/VISSIM are
killed and the case is retried up to MaxAttempts.

obs150 (a coupled-lane-plant/v2 manifest): one attempt, and never a kill by process
name. Only the cscript this watchdog starts and the VISSIM it identifies are stopped,
by PID and start time; the run always behaves as -NoGlobalKill.
#>
# 위치인자 바인딩을 끈다. 호출자가 실수로 위치인자를 흘리면(예: 문자열 splat —
# `@("-ForceStepwise")` 가 String 으로 언롤돼 문자 14개로 쪼개진 2026-09-01 사고)
# 파라미터가 조용히 밀리는 대신 즉시 죽는다. 호출부 42곳 전부가 명명인자라 회귀 위험이 없다.
[CmdletBinding(PositionalBinding=$false)]
param(
  [Parameter(Mandatory=$true)][string]$Name,
  # 어댑터 경로. 비우면 정본을 쓴다. 실험용 사본을 돌릴 때만 넘긴다 —
  # 기본값이 정본이라 안 넘기면 기존 호출과 완전히 같다.
  [string]$Adapter = "",
  [string]$Network = "",
  [string]$NetworkRecordingProof = "",
  [string]$OutDir = "",
  [int]$SimPeriod = 1800,
  [int]$ControlIntervalSec = 60,
  [int]$Seed = 13,
  [string]$Controller = "stackelberg",
  [string]$Tuning = "",
  [string]$Calibration = "",
  [string]$Mapping = "",
  [string]$VbsConfig = "",
  # Skip global process termination; a stalled run can still stop its identified VISSIM instance.
  [switch]$NoGlobalKill,
  [int]$ControlStartSec = -1,
  [string]$WarmupController = "no-control",
  [int]$StateLogIntervalSec = 30,
  [double]$DemandScale = 1.0,
  [string]$DemandProfile = "",
  [string]$VehicleInputRoles = "",
  [int]$IncidentLink = 0,
  [int]$IncidentLane = 0,
  [double]$IncidentPos = -1.0,
  [int]$IncidentStartSec = -1,
  [int]$IncidentEndSec = -1,
  [string]$IncidentName = "",
  # 도시 유입 게이트 맵. 격자 leg 방위에서 유도되므로 leg 을 고치면 같이 움직인다.
  # 2026-08-19: 비워두면 러너 VBS 가 8방위 시절 기본값(urban_input_gate_map_20260811.csv)으로
  # 떨어지고, 그 대장의 in_SC9001_S 를 core17legs4b config 가 몰라서 어댑터가 ValueError 로
  # 런을 세운다(vissim_stackelberg_adapter.py:3120). legs4b 대장을 기본값으로 박는다.
  [string]$UrbanInputGateMap = "evaluation\real_world_modi_inventory\urban_input_gate_map_legs4b_20260819.csv",
  [switch]$ForceStepwise,
  [ValidateRange(1,3600)][int]$StartupStallSec = 300,
  [int]$StallSec = 300,
  [int]$MaxAttempts = 3,
  [int]$DoneRows = 0,
  [string]$AuditAnchorsSec = "",
  # obs150 (SDMPC31_OBS150_PLAN_20260924 A8/A9): ground-truth windows such as "750:900,1050:1200".
  # Only with a coupled-lane-plant/v2 manifest on a dev run named sdmpc31_g*; exported as RW_OBS150_GT.
  [string]$GroundTruthWindows = "",
  # Write run_provenance_<Name>.json (with the obs150 block for v2) and exit: no VISSIM is started.
  [switch]$PreflightOnly
)

$ErrorActionPreference = "Continue"
# A Windows PowerShell child may inherit another edition's PSModulePath.
# Load hashing/JSON support from this host before capturing any provenance.
# Missing hashes must stop before launching VISSIM, not become empty evidence.
Import-Module (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Utility\Microsoft.PowerShell.Utility.psd1') -ErrorAction Stop
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
function Resolve-RepoPath([string]$PathValue) {
  if ($PathValue -eq "") { return "" }
  if ([System.IO.Path]::IsPathRooted($PathValue)) {
    return [System.IO.Path]::GetFullPath($PathValue)
  }
  return [System.IO.Path]::GetFullPath((Join-Path $repo $PathValue))
}

if ($OutDir -eq "") {
  $OutDir = Join-Path $repo "evaluation\runs\real_world_modi_watchdog"
}
$OutDir = Resolve-RepoPath $OutDir
# Strict area accounting must stop when a decision cannot be produced.
# Follow the existing single-parent tuning chain for this one inherited key.
function Read-HeadObservationSettings([string]$TuningFile) {
  $seen = @{}; $chain = @(); $documents = @()
  while ($TuningFile -ne "") {
    $TuningFile = [IO.Path]::GetFullPath($TuningFile)
    if ($seen.ContainsKey($TuningFile)) { throw "Cyclic head observation tuning" }
    $seen[$TuningFile] = $true
    $doc = Get-Content -LiteralPath $TuningFile -Raw -Encoding UTF8 -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
    $chain += [ordered]@{path=$TuningFile; sha256=(Get-FileHash -LiteralPath $TuningFile -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()}
    $documents += $doc
    if (-not $doc.extends) { break }
    $next = [string]$doc.extends
    if (-not [IO.Path]::IsPathRooted($next)) { $next = Join-Path (Split-Path -Parent $TuningFile) $next }
    $TuningFile = $next
  }
  $options = [ordered]@{}; $measured = $false; $declared = $false
  for ($i=$documents.Count-1; $i -ge 0; $i--) {
    $capacity = $documents[$i].urban.capacity
    if ($null -eq $capacity) { continue }
    if ($capacity.PSObject.Properties['measured']) { $measured = $capacity.measured }
    if ($capacity.PSObject.Properties['head_observation']) {
      $declared = $true
      $value = $capacity.head_observation
      if ($value -isnot [PSCustomObject]) { throw "head_observation requires an object" }
      foreach ($property in $value.PSObject.Properties) {
        if ($property.Name -notin @('enabled','min_green_sec','min_crossings','sample_interval_sec')) { throw "Unknown head observation option" }
        $options[$property.Name] = $property.Value
      }
    }
  }
  if ($options.Count -eq 0) {
    if ($declared) { throw "Declared head_observation requires boolean enabled" }
    $options.enabled = $false
  }
  if ($options.enabled -isnot [bool]) { throw "head_observation.enabled must be boolean" }
  if ($options.enabled) {
    if ($options.Contains('sample_interval_sec')) {
      $v=$options.sample_interval_sec
      if (($v -isnot [int] -and $v -isnot [long]) -or $v -notin @(1,5)) { throw 'Vehicle observation sample_interval_sec must be1 or5' }
      $options.sample_interval_sec=[int]$v
    }
    if ($measured -isnot [bool] -or -not $measured) { throw "head observation requires urban.capacity.measured=true" }
    foreach ($key in @('min_green_sec','min_crossings')) {
      $value = $options[$key]
      if ($null -eq $value -or $value -is [bool] -or $value -is [string]) { throw "Explicit numeric head observation quality threshold required: $key" }
      $number = [double]$value
      if ([double]::IsNaN($number) -or [double]::IsInfinity($number) -or $number -le 0 -or $number -ne [Math]::Floor($number)) { throw "Positive integer head observation threshold required: $key" }
      $options[$key] = $number
    }
  } else { $options = [ordered]@{enabled=$false} }
  $result = [ordered]@{config_key='urban.capacity.head_observation'; options=$options; config_chain=$chain}
  $lanePlant = $null
  for ($i=$documents.Count-1; $i -ge 0; $i--) {
    if ($documents[$i].freeway -and $documents[$i].freeway.PSObject.Properties['lane_plant']) {
      $lanePlant = $documents[$i].freeway.lane_plant
    }
  }
  if ($null -ne $lanePlant) {
    if ($lanePlant -isnot [string] -or [string]::IsNullOrWhiteSpace($lanePlant) -or -not $options.enabled) {
      throw 'freeway.lane_plant requires a manifest and enabled head observation'
    }
    $manifestPath = Resolve-RepoPath $lanePlant
    $result.lane_plant = [ordered]@{path=$manifestPath; sha256=(Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()}
    # obs150 (plan 1.1/A8): the manifest schema is the one switch. v2 reads one 150 s window per decision
    # from the generated detector table the manifest pins; a v1 manifest keeps the per-second path.
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
    if ($manifest.schema -ceq 'coupled-lane-plant/v2') {
      if ($options.Contains('sample_interval_sec')) { throw 'obs150 (v2 manifest) rejects head_observation.sample_interval_sec' }
      $result.obs150 = Read-Obs150Observation $manifest $manifestPath $result.lane_plant.sha256
    } elseif ($manifest.schema -cne 'coupled-lane-plant/v1') {
      throw "Unsupported lane plant manifest schema: $($manifest.schema)"
    }
  }
  return $result
}

# A v2 manifest pin (CONTRACT _repo_pin): a repo-relative forward-slash path with no ':' and no '..'
# segment, whose file bytes hash to the pinned lower-case sha256. Returns the resolved path and sha.
function Resolve-Obs150RepoPin($Pin, [string]$What) {
  if ($null -eq $Pin) { throw "v2 manifest lacks $What" }
  $path = $Pin.path
  if ($path -isnot [string] -or $path -eq '' -or $path.Contains('\') -or $path.Contains(':') -or
      [IO.Path]::IsPathRooted($path) -or ($path.Split('/') -contains '..')) {
    throw "$What.path must be a repo-relative forward-slash path"
  }
  if ($Pin.sha256 -isnot [string] -or $Pin.sha256 -cnotmatch '\A[0-9a-f]{64}\z') { throw "$What.sha256 must be a lower-case sha256" }
  $file = Resolve-RepoPath $path
  $actual = (Get-FileHash -LiteralPath $file -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()
  if ($actual -cne $Pin.sha256) { throw "obs150 $What $file sha256 $actual differs from the manifest pin $($Pin.sha256)" }
  return [ordered]@{path=$file; sha256=$actual}
}

# obs150 observation block of a coupled-lane-plant/v2 manifest (CONTRACT 1.1/1.3/1.4). The detector table
# and the runner config bytes must match the manifest pins here, before anything is launched.
function Read-Obs150Observation($Manifest, [string]$ManifestPath, [string]$ManifestSha) {
  $observation = $Manifest.observation
  if ($null -eq $observation -or $null -eq $observation.detectors) { throw 'v2 manifest lacks observation.detectors' }
  $detectorPin = Resolve-Obs150RepoPin $observation.detectors 'observation.detectors'
  $csv = $detectorPin.path
  $actual = $detectorPin.sha256
  $runnerConfig = Resolve-Obs150RepoPin $Manifest.sources.runner_config 'sources.runner_config'
  $text = [Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($csv))
  if (-not $text.EndsWith("`n") -or $text.Contains("`r")) { throw "obs150 detector table must be LF text: $csv" }
  $rows = ($text.Split("`n")).Count - 2
  if ($rows -lt 1) { throw "obs150 detector table has no rows: $csv" }
  foreach ($key in @('expected_simres', 'vehrec_interval_sec')) {
    $value = $observation.$key
    if (($value -isnot [int] -and $value -isnot [long]) -or $value -lt 1) { throw "observation.$key must be a positive integer" }
  }
  return [ordered]@{
    plant_manifest = [ordered]@{path=$ManifestPath; sha256=$ManifestSha}
    detectors = [ordered]@{path=$csv; sha256=$actual; rows=$rows}
    expected_simres = [int]$observation.expected_simres
    vehrec_interval_sec = [int]$observation.vehrec_interval_sec
    runner_config = $runnerConfig
  }
}

# RW_OBS150_GT windows "a:b,c:d" (CONTRACT parse_gt_windows): sorted, 150 s aligned, disjoint, inside the run.
# The runner reaches t=1 in one break (plan A2), so a window starts at a decision stop >= 150. Adjacent
# windows are refused too (the runner would write the shared stop's rows twice): 750:900,900:1050 = 750:1050.
function ConvertTo-Obs150GtWindows([string]$Text, [int]$Period) {
  $windows = New-Object System.Collections.ArrayList
  if ($Text -eq '') { return ,$windows }
  $last = -1
  foreach ($item in $Text.Split(',')) {
    if ($item -cnotmatch '\A([1-9][0-9]*):([1-9][0-9]*)\z') { throw "-GroundTruthWindows item must be start:end seconds: $item" }
    $a = [int]$Matches[1]; $b = [int]$Matches[2]
    if ($a -ge $b -or ($a % 150) -ne 0 -or ($b % 150) -ne 0 -or $a -le $last -or $b -gt $Period) {
      throw "-GroundTruthWindows must be sorted, 150 s aligned, separated (merge adjacent ones) and end inside -SimPeriod: $Text"
    }
    [void]$windows.Add(@($a, $b))
    $last = $b
  }
  return ,$windows
}

function Set-HeadObservationTransport([string]$TuningFile, $Expected) {
  $current = Read-HeadObservationSettings $TuningFile
  if (($current | ConvertTo-Json -Depth 8 -Compress) -cne ($Expected | ConvertTo-Json -Depth 8 -Compress)) {
    throw "Head observation tuning changed after provenance capture"
  }
  $obs150Names = @('RW_OBSERVATION_CADENCE', 'RW_OBS150_DETECTORS', 'RW_OBS150_DETECTORS_SHA256',
    'RW_OBS150_EXPECTED_SIMRES', 'RW_OBS150_VEHREC_SEC', 'RW_OBS150_GT')
  if ($current.obs150) {
    # obs150 (CONTRACT 1.3, expected_runner_env): one exact 150 s read per decision replaces the per-second
    # observer. RW_OBSERVATION_CADENCE is what selects the runner's obs150 mode, and only a v2 manifest sets it.
    $env:RW_SIGNAL_OBSERVATION = '0'
    $env:RW_SIGNAL_OBSERVATION_CONFIG_SHA256 = $(if ($current.options.enabled) { $current.config_chain[0].sha256 } else { '' })
    $env:RW_LANE_PLANT_OBSERVATION = '1'
    $env:RW_VEHICLE_OBSERVATION_INTERVAL_SEC = '1'
    $env:RW_QUEUE_WINDOW = '0'
    $env:RW_OBSERVATION_CADENCE = 'decision150'
    $env:RW_STATE_LOG = 'decision'
    $env:RW_OBS150_DETECTORS = $current.obs150.detectors.path
    $env:RW_OBS150_DETECTORS_SHA256 = $current.obs150.detectors.sha256
    $env:RW_OBS150_EXPECTED_SIMRES = [string]$current.obs150.expected_simres
    $env:RW_OBS150_VEHREC_SEC = [string]$current.obs150.vehrec_interval_sec
    [Environment]::SetEnvironmentVariable('RW_OBS150_GT', $(if ($script:Obs150GtText) { $script:Obs150GtText } else { $null }), 'Process')
    return
  }
  # Transport only: inherited RW_* values can never activate this feature.
  $env:RW_SIGNAL_OBSERVATION = $(if ($current.options.enabled) { '1' } else { '0' })
  $env:RW_SIGNAL_OBSERVATION_CONFIG_SHA256 = $(if ($current.options.enabled) { $current.config_chain[0].sha256 } else { '' })
  $env:RW_LANE_PLANT_OBSERVATION = $(if ($current.lane_plant) { '1' } else { '0' })
  $env:RW_VEHICLE_OBSERVATION_INTERVAL_SEC = $(if ($current.options.enabled -and $current.options.Contains('sample_interval_sec')) { [string]$current.options.sample_interval_sec } else { '1' })
  if ($current.options.enabled) { $env:RW_QUEUE_WINDOW = '1' }
  # Not v2: nothing inherited may switch the runner into the obs150 cadence.
  foreach ($obs150Name in $obs150Names) { [Environment]::SetEnvironmentVariable($obs150Name, $null, 'Process') }
}

function Read-RampMeterTimingSettings([string]$TuningFile) {
  $seen = @{}; $chain = @(); $amber = 1; $declared = $false
  while ($TuningFile -ne '') {
    $TuningFile = [IO.Path]::GetFullPath($TuningFile)
    if ($seen.ContainsKey($TuningFile)) { throw 'Cyclic ramp meter timing tuning' }
    $seen[$TuningFile] = $true
    $doc = Get-Content -LiteralPath $TuningFile -Raw -Encoding UTF8 -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
    $chain += [ordered]@{path=$TuningFile; sha256=(Get-FileHash -LiteralPath $TuningFile -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()}
    $meter = $doc.actuation.real_world_ramp_metering
    if (-not $declared -and $null -ne $meter -and $meter.PSObject.Properties['amber_sec']) {
      $value = $meter.amber_sec
      if (($value -isnot [int] -and $value -isnot [long] -and $value -isnot [double] -and $value -isnot [decimal]) -or
          ($value -ne 0 -and $value -ne 1)) { throw 'actuation.real_world_ramp_metering.amber_sec must be numeric0 or1' }
      $amber = [int]$value; $declared = $true
    }
    if (-not $doc.extends) { break }
    if ($doc.extends -isnot [string]) { throw 'Ramp meter timing requires a single string extends path' }
    $next = $doc.extends
    if (-not [IO.Path]::IsPathRooted($next)) { $next = Join-Path (Split-Path -Parent $TuningFile) $next }
    $TuningFile = $next
  }
  return [ordered]@{config_key='actuation.real_world_ramp_metering.amber_sec'; amber_sec=$amber; declared=$declared; config_chain=$chain}
}

function Set-RampMeterTimingTransport([string]$TuningFile, $Expected) {
  $current = Read-RampMeterTimingSettings $TuningFile
  if (($current | ConvertTo-Json -Depth 8 -Compress) -cne ($Expected | ConvertTo-Json -Depth 8 -Compress)) {
    throw 'Ramp meter timing tuning changed after provenance capture'
  }
  # Environment is transport only: set both0 and legacy1 explicitly on every launch.
  $env:RW_RAMP_AMBER_SEC = [string]$current.amber_sec
}

function Read-ControlAreaObjectiveEnabled([string]$TuningFile) {
  $seenStrictTuning = @{}
  while ($TuningFile -ne "") {
    $TuningFile = [System.IO.Path]::GetFullPath($TuningFile)
    if ($seenStrictTuning.ContainsKey($TuningFile)) { throw "Cyclic tuning extends: $TuningFile" }
    $seenStrictTuning[$TuningFile] = $true
    $strictTuning = Get-Content -LiteralPath $TuningFile -Raw -Encoding UTF8 -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
    $areaProperty = $strictTuning.PSObject.Properties['control_area_objective']
    if ($null -ne $areaProperty) {
      $strictArea = $areaProperty.Value
      if ($null -eq $strictArea -or $strictArea -isnot [PSCustomObject]) { return $false }
      $enabledProperty = $strictArea.PSObject.Properties['enabled']
      if ($null -ne $enabledProperty) { return [bool]$enabledProperty.Value }
    }
    if (-not $strictTuning.extends) { return $false }
    $parentStrictTuning = [string]$strictTuning.extends
    if (-not [System.IO.Path]::IsPathRooted($parentStrictTuning)) {
      $parentStrictTuning = Join-Path (Split-Path -Parent $TuningFile) $parentStrictTuning
    }
    $TuningFile = $parentStrictTuning
  }
  return $false
}
# Always reset inherited process state; only the effective tuning key enables it.
$env:RW_DECISION_FAIL_FAST = "0"
if ($Tuning -ne "") {
  try {
    if (Read-ControlAreaObjectiveEnabled (Resolve-RepoPath $Tuning)) { $env:RW_DECISION_FAIL_FAST = "1" }
  } catch {
    throw "Cannot resolve control_area_objective.enabled: $($_.Exception.Message)"
  }
}
"RW_DECISION_FAIL_FAST=$($env:RW_DECISION_FAIL_FAST) (control_area_objective.enabled)"
# 2026-09-05. RW_MAINLINE_SG_ONLY 를 config(urban.plan.mainline_only) 로 러너가 직접 세운다.
# 종전엔 launch_*/queue_* 스크립트가 env 로 세우고 러너는 믿기만 했다. 그래서 Bash 로 띄운
# 체인(2026-09-04 16:31 이후 22런)이 env 없이 돌아 SG 9+ (미드블록 횡단)까지 ContrByCOM 이
# 걸리고 계획에 없어 영구 적색이 됐다(SC5 SG14 -> 링크 1220014203 막다른 길). 런로그의
# SIGNAL_MIDBLOCK_COM_SKIPS 가 0 이면 이 결함이다.
if ($Tuning -ne "") {
  try {
    $tunJson = Get-Content -Raw -Encoding UTF8 (Resolve-RepoPath $Tuning) | ConvertFrom-Json
    $mlOnly = $null
    if ($tunJson.urban -and $tunJson.urban.plan) { $mlOnly = $tunJson.urban.plan.mainline_only }
    if ($null -eq $mlOnly) {
      $env:RW_MAINLINE_SG_ONLY = "1"
      "RW_MAINLINE_SG_ONLY=1 (config 에 urban.plan.mainline_only 없음 -> 기본 native 미드블록)"
    } elseif ($mlOnly) {
      $env:RW_MAINLINE_SG_ONLY = "1"
      "RW_MAINLINE_SG_ONLY=1 (config urban.plan.mainline_only=true)"
    } else {
      $env:RW_MAINLINE_SG_ONLY = "0"
      "RW_MAINLINE_SG_ONLY=0 (config urban.plan.mainline_only=false)"
    }
  } catch {
    $env:RW_MAINLINE_SG_ONLY = "1"
    "RW_MAINLINE_SG_ONLY=1 (config 읽기 실패: $($_.Exception.Message))"
  }
}
# 2026-09-05. 기준선 런처(queue_audit2/ctlcanon_20260904)가 세우던 RW_QUEUE_COUNTER=1 도 러너가 세운다.
# VBS 가 state JSON 에 queue_counters 진단을 싣는 스위치일 뿐 어댑터는 읽지 않는다(제어 무영향).
if ([string]::IsNullOrWhiteSpace($env:RW_QUEUE_COUNTER)) { $env:RW_QUEUE_COUNTER = "1" }
"RW_QUEUE_COUNTER=$($env:RW_QUEUE_COUNTER)"
# 2026-09-06. RW_QUEUE_WINDOW(VBS 가 link_departures_window 를 state 에 싣는 스위치)를 config(urban.capacity.measured)로 러너가 세운다.
# 실측 방출률 갱신(install_measured_movement_capacity)의 유일한 입력인데 env 뒤에 있어 어떤 런에도 없었다.
if ($Tuning -ne "") {
  try {
    $tunJson2 = Get-Content -Raw -Encoding UTF8 (Resolve-RepoPath $Tuning) | ConvertFrom-Json
    $measured = $null
    if ($tunJson2.urban -and $tunJson2.urban.capacity) { $measured = $tunJson2.urban.capacity.measured }
    if ($measured) {
      $env:RW_QUEUE_WINDOW = "1"
      "RW_QUEUE_WINDOW=1 (config urban.capacity.measured=true)"
    } else {
      if ([string]::IsNullOrWhiteSpace($env:RW_QUEUE_WINDOW)) { $env:RW_QUEUE_WINDOW = "0" }
      "RW_QUEUE_WINDOW=$($env:RW_QUEUE_WINDOW) (config urban.capacity.measured 꺼짐/없음)"
    }
  } catch {
    "RW_QUEUE_WINDOW 미설정 (config 읽기 실패: $($_.Exception.Message))"
  }
}
# 2026-08-27. -Tuning 기본값을 없앤다. 종전 기본값
# (real_world_modi_pstack_distributed_core17legs4b_20260819.json) 은 정본 통합 때
# 격리 폴더로 옮겨져 더는 존재하지 않는다. 그런데 어댑터의 load_optional_json 은
# 없는 경로에서 조용히 {} 를 돌려주므로, -Tuning 을 빠뜨리면 **무설정 런이 정상
# 종료**하고 TTT 만 다르게 나온다. 시끄럽게 죽는 편이 낫다.
if ($Tuning -eq "") {
  Write-Output "!! -Tuning 이 필요하다. 정본: evaluation/configs/canon_{tau,bstoA,plantfix,fdfit}_20260827.json"
  exit 2
}
$Tuning = Resolve-RepoPath $Tuning
if (-not (Test-Path $Tuning)) {
  Write-Output ("!! -Tuning 파일이 없다: {0}" -f $Tuning)
  exit 2
}
if ($Calibration -eq "") {
  $Calibration = Join-Path $repo "evaluation\calibration\real_world_prediction_calibration_core17legs4b_20260820.json"
}
$Calibration = Resolve-RepoPath $Calibration
if ($Mapping -eq "") {
  $Mapping = Join-Path $repo "evaluation\real_world_modi_control_distributed_20260728\control_mapping_distributed_core17legs4b_20260819.json"
}
$Mapping = Resolve-RepoPath $Mapping
if ($VehicleInputRoles -eq "") {
  $VehicleInputRoles = Join-Path $repo "evaluation\real_world_modi_inventory\vehicle_input_roles.csv"
}
$VehicleInputRoles = Resolve-RepoPath $VehicleInputRoles
if ($DemandProfile -ne "") {
  $DemandProfile = Resolve-RepoPath $DemandProfile
}
if ($ControlIntervalSec -le 0 -or ($ControlIntervalSec % 10) -ne 0) {
  throw "ControlIntervalSec must be a positive multiple of the 10s ramp-meter cycle. Got $ControlIntervalSec."
}
if ($StateLogIntervalSec -le 0) {
  throw "StateLogIntervalSec must be positive. Got $StateLogIntervalSec."
}

$runner = Join-Path $repo "scripts\run_real_world_stackelberg_controller.vbs"
if ($Network -eq "") {
  $Network = Join-Path $repo "network\real_world_gaepo_modi\modi_eval_rw_control.inpx"
}
$net = Resolve-RepoPath $Network
if ($Adapter) { $adapter = Resolve-RepoPath $Adapter }
else { $adapter = Join-Path $repo "evaluation\controllers\vissim_stackelberg_adapter.py" }
# VBS generated config (positional arg 14). This carries RW_LOCAL_OBSERVABLE_LINKS and
# RW_DETECTOR_MAPPING_PATH, i.e. WHAT THE PLANT RECORDS into state_*.json local_observation.
# 2026-08-04: this was hardcoded to the base config while grids passed a distributed
# -Mapping. Result: the plant logged only 22 observable links (base) while G6 scoring
# projected with the distributed 175-link detector mapping, so 153 links had no data and
# the observed objective captured 1.4% of urban vehicles. Every urban-axis candidate was
# then scored with the wrong sign. Default keeps the old path = bit-identical.
# 2026-08-25: 기본값을 **본선 전용 계획** 형제를 가진 사본으로 옮긴다.
#
# 러너는 sgplan 을 이 파일의 형제(<config>_sgplan.vbs)로 찾는다. 옛 형제는 액추에이션
# 계획의 현시 그룹에 **미드블록 SG(9+)를 함께 넣은** 판이라, 그 축이 미드블록 창으로
# 잡혀 본선 SG 창이 분율로 깎였다 - SC5 p1 은 axis 97(SG20 창) 기준 43/97 = 0.4433 이라
# 컨트롤러가 54.5초를 주문해도 본선에 24.2초만 배달됐다(1초 되읽기 12주기 실측).
#
# 러너는 RW_MAINLINE_SG_ONLY=1 로 이미 sg<=8 만 COM 으로 몰고 미드블록엔 ContrByCOM 조차
# 안 건다(:1827-1833). 계획만 아직 미드블록을 현시에 넣고 있었다. 본선만 보면 이미
# 완전한 4현시 순차다(SC5 43+23+47+25 = 138 = 모델 예산, +4x3s 황색 = 150 = 주기).
#
# 실측: mainline_20260825 = 4723.9 (무제어 4808.1 대비 -84.2). 같은 스택에서 옛 계획을
# 쓴 allfix_20260825 는 4783.9 였다 - **이 한 줄이 -60.0 이다.**
#
# 무제어 기준선은 영향을 받지 않는다 - nocontrol 런은 signal/signal_sg 행을 하나도 쓰지
# 않고 VISSIM native 프로그램이 그대로 돈다(실측 확인: vsl 71 + ramp_meter 8 행뿐).
#
# 옛 계획으로 되돌리려면 -VbsConfig 로 ..._core17legs4b_20260819.vbs 를 넘기면 된다.
if ($VbsConfig -eq "") {
  $VbsConfig = Join-Path $repo "evaluation\generated\real_world_modi_control_config_distributed_core17legs4b_mainline_20260825.vbs"
}
$vbsConfig = Resolve-RepoPath $VbsConfig
if (-not (Test-Path $vbsConfig)) { Log "ERROR vbs config not found: $vbsConfig"; exit 2 }

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$progress = Join-Path $OutDir "WATCHDOG_PROGRESS.txt"

function Log($m) {
  $line = ("{0}  {1}" -f (Get-Date -Format "MM-dd HH:mm:ss"), $m)
  for ($r = 0; $r -lt 5; $r++) {
    try { [System.IO.File]::AppendAllText($progress, $line + "`r`n"); break }
    catch { Start-Sleep -Milliseconds 200 }
  }
  Write-Host $line
}

function Kill-Vissim {
  # By NAME: this stops every VISSIM and cscript on the machine, other runs included (it killed three
  # live runs on 2026-09-24 03:15). The obs150 (v2) path never comes here: it forces NoGlobalKill and
  # stops only what it launched, by PID and start time (Stop-RunProcesses). A future call site on
  # that path fails here instead of killing.
  if ($script:Obs150Run) { throw 'obs150 (v2) never stops processes by name (Kill-Vissim)' }
  Get-Process -Name "VISSIM200","VISSIM200CL","cscript" -ErrorAction SilentlyContinue |
    Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 3
}

function Clear-DecisionDir([string]$Dir) {
  if (-not (Test-Path $Dir)) {
    New-Item -ItemType Directory -Force -Path $Dir | Out-Null
    return
  }
  Get-ChildItem -LiteralPath $Dir -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "action_*.json" -or $_.Name -like "action_*.csv" -or $_.Name -like "state_*.json" } |
    Remove-Item -Force -ErrorAction SilentlyContinue
}

function Normalize-ProcessPathEnv {
  $pathValue = [Environment]::GetEnvironmentVariable("Path", "Process")
  if ([string]::IsNullOrWhiteSpace($pathValue)) {
    $pathValue = [Environment]::GetEnvironmentVariable("PATH", "Process")
  }
  [Environment]::SetEnvironmentVariable("PATH", $null, "Process")
  [Environment]::SetEnvironmentVariable("Path", $null, "Process")
  if (-not [string]::IsNullOrWhiteSpace($pathValue)) {
    [Environment]::SetEnvironmentVariable("Path", $pathValue, "Process")
  }
}

function Q($s) { '"' + $s + '"' }

function Get-ArtifactEvidence([string]$ArtifactPath) {
  $exists = -not [string]::IsNullOrWhiteSpace($ArtifactPath) -and (Test-Path -LiteralPath $ArtifactPath -PathType Leaf)
  [ordered]@{
    path = $ArtifactPath
    exists = $exists
    sha256 = if ($exists) { (Get-FileHash -LiteralPath $ArtifactPath -Algorithm SHA256).Hash.ToLowerInvariant() } else { "" }
  }
}

function Get-ExactGitCommit([string]$RepositoryPath) {
  if ([string]::IsNullOrWhiteSpace($RepositoryPath) -or -not (Test-Path -LiteralPath $RepositoryPath -PathType Container)) {
    return ""
  }
  # Git emits UTF-8 paths, but Windows PowerShell 5.1 may decode native output
  # with a legacy code page. Root checks below return ASCII and avoid that path.
  try {
    $inside = @(& git -C $RepositoryPath rev-parse --is-inside-work-tree 2>$null)
    if ($LASTEXITCODE -ne 0 -or $inside.Count -ne 1 -or $inside[0] -cne 'true') { return "" }
    $up = @(& git -C $RepositoryPath rev-parse --show-cdup 2>$null)
    if ($LASTEXITCODE -ne 0 -or $up.Count -gt 1 -or ($up.Count -eq 1 -and $up[0] -cne '')) { return "" }
    $head = @(& git -C $RepositoryPath rev-parse --verify 'HEAD^{commit}' 2>$null)
    if ($LASTEXITCODE -ne 0 -or $head.Count -ne 1 -or $head[0] -cnotmatch '\A(?:[0-9a-f]{40}|[0-9a-f]{64})\z') { return "" }
    return [string]$head[0]
  } catch {
    return ""
  }
}

function Test-SimulationStarted([string]$CsvPath, [string]$LogPath = '') {
  # Only exact ASCII actual-time markers count; stream until a marker or EOF.
  # Startup demand/ordinary log writes do not reset the 300-second deadline.
  # Starting from the beginning retains the marker during a long first decision.
  if ($LogPath -and (Test-Path -LiteralPath $LogPath -PathType Leaf)) {
    $stream = $null; $reader = $null
    try {
      $stream = [IO.File]::Open($LogPath, [IO.FileMode]::Open, [IO.FileAccess]::Read,
        [IO.FileShare]::ReadWrite)
      $reader = [IO.StreamReader]::new($stream, [Text.Encoding]::ASCII, $false)
      while ($null -ne ($line = $reader.ReadLine())) {
        if ($line -cnotmatch '^NATIVE_SIM_PROGRESS sim_sec=([0-9]+(?:\.[0-9]+)?)$') { continue }
        $sampleTime = 0.0
        if ([double]::TryParse($Matches[1], [Globalization.NumberStyles]::Float,
            [Globalization.CultureInfo]::InvariantCulture, [ref]$sampleTime) -and
            -not [double]::IsNaN($sampleTime) -and -not [double]::IsInfinity($sampleTime) -and
            $sampleTime -gt 0) { return $true }
      }
    } catch [IO.IOException] {
      # A concurrent open/append can be retried on the next existing poll.
    } finally {
      if ($null -ne $reader) { $reader.Dispose() }
      elseif ($null -ne $stream) { $stream.Dispose() }
    }
  }
  # Preserve the actual state-clock fallback, excluding nonfinite numbers.
  if (-not (Test-Path -LiteralPath $CsvPath -PathType Leaf)) { return $false }
  foreach ($line in (Get-Content -LiteralPath $CsvPath -Tail 4 -ErrorAction SilentlyContinue)) {
    $sampleTime = 0.0
    if ([double]::TryParse(($line -split ',',2)[0], [Globalization.NumberStyles]::Float,
        [Globalization.CultureInfo]::InvariantCulture, [ref]$sampleTime) -and
        -not [double]::IsNaN($sampleTime) -and -not [double]::IsInfinity($sampleTime) -and
        $sampleTime -gt 0) { return $true }
  }
  return $false
}

# The network file name as a whole path component of a window title ('...\net.inpx', 'net.inpx - ...'):
# another run's 'a_net.inpx' or 'xnet.inpx' must not match 'net.inpx'.
function Test-RunVissimTitle([string]$Title, [string]$NetworkFileName) {
  if ($NetworkFileName -eq '') { return $false }
  $pattern = '(?:^|(?<=[\\/\[(\s"'']))' + [regex]::Escape($NetworkFileName) + '(?![\w.-])'
  return [regex]::IsMatch([string]$Title, $pattern, [Text.RegularExpressions.RegexOptions]::IgnoreCase)
}

function Find-RunVissimIdentity([int[]]$ExistingIds, [datetime]$AttemptStart, [string]$NetworkFileName) {
  $candidates = @(
    Get-Process -Name VISSIM200 -ErrorAction SilentlyContinue | Where-Object {
      $_.Id -notin $ExistingIds -and $_.StartTime -ge $AttemptStart -and
      (Test-RunVissimTitle $_.MainWindowTitle $NetworkFileName)
    }
  )
  if ($candidates.Count -eq 1) {
    return [pscustomobject]@{ Id = $candidates[0].Id; StartTime = $candidates[0].StartTime }
  }
  return $null
}

# obs150: the processes the runner cscript started (adapter python, SDMPC workers, their consoles),
# found from parent links while the runner still runs. A child counts only when it was created after
# its parent, so a recycled parent PID cannot adopt an older process; identity = PID + start time.
function Get-RunDescendantIdentities($RootIdentity) {
  $found = New-Object System.Collections.ArrayList
  if ($null -eq $RootIdentity) { return ,$found }
  $root = Get-Process -Id $RootIdentity.Id -ErrorAction SilentlyContinue
  if (-not $root -or $root.StartTime -ne $RootIdentity.StartTime) { return ,$found }
  $all = @(Get-CimInstance -ClassName Win32_Process -ErrorAction SilentlyContinue)
  $queue = New-Object System.Collections.Queue
  $queue.Enqueue([pscustomobject]@{ Id = [int]$RootIdentity.Id; StartTime = $RootIdentity.StartTime })
  while ($queue.Count -gt 0) {
    $parent = $queue.Dequeue()
    foreach ($child in $all) {
      if ([int]$child.ParentProcessId -ne $parent.Id -or [int]$child.ProcessId -eq $parent.Id) { continue }
      if ($null -eq $child.CreationDate -or $child.CreationDate -lt $parent.StartTime) { continue }
      $live = Get-Process -Id ([int]$child.ProcessId) -ErrorAction SilentlyContinue
      if (-not $live -or [math]::Abs(($live.StartTime - $child.CreationDate).TotalSeconds) -ge 1) { continue }
      $identity = [pscustomobject]@{ Id = $live.Id; StartTime = $live.StartTime }
      [void]$found.Add($identity)
      $queue.Enqueue($identity)
    }
  }
  return ,$found
}

function Stop-RunProcesses($RunnerProcess, $VissimIdentity, $Descendants = @()) {
  # Recheck creation times so a recycled PID cannot target another process.
  foreach ($identity in @($RunnerProcess, $VissimIdentity) + @($Descendants)) {
    if ($null -eq $identity) { continue }
    $current = Get-Process -Id $identity.Id -ErrorAction SilentlyContinue
    if ($current -and $current.StartTime -eq $identity.StartTime) {
      Stop-Process -Id $current.Id -Force -ErrorAction SilentlyContinue
    }
  }
}

function Copy-VissimError([string]$DestinationDir) {
  $vissimErr = [System.IO.Path]::ChangeExtension($net, ".err")
  if (Test-Path -LiteralPath $vissimErr -PathType Leaf) {
    Copy-Item -LiteralPath $vissimErr -Destination (Join-Path $DestinationDir "vissim_network.err") `
      -Force -ErrorAction SilentlyContinue
  }
  # Runtime removals/skipped decisions are in <network>_001.err, while the
  # unnumbered .err contains network-load warnings. Preserve both before the
  # next run overwrites the numbered simulation log.
  $networkStem = [System.IO.Path]::GetFileNameWithoutExtension($net)
  $simulationPattern = "^" + [regex]::Escape($networkStem) + "_(\d+)\.err$"
  foreach ($simulationErr in Get-ChildItem -LiteralPath ([System.IO.Path]::GetDirectoryName($net)) -File -ErrorAction SilentlyContinue) {
    if ($simulationErr.Name -match $simulationPattern -and $simulationErr.LastWriteTime -ge $t0) {
      $simulationNumber = $Matches[1]
      # COM server shutdown can outlive cscript by several seconds. Copying
      # immediately archived a 16-KiB-aligned, truncated warning log in a run.
      $flushDeadline = (Get-Date).AddSeconds(20)
      $closed = $false
      do {
        try {
          $probeStream = [System.IO.File]::Open($simulationErr.FullName,
            [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::None)
          $probeStream.Dispose()
          $closed = $true
        } catch [System.IO.IOException] {
          if ((Get-Date) -lt $flushDeadline) { Start-Sleep -Milliseconds 250 }
        }
      } while (-not $closed -and (Get-Date) -lt $flushDeadline)
      if (-not $closed) { Log "WARNING runtime error log is still open; archive may be incomplete: $($simulationErr.Name)" }
      Copy-Item -LiteralPath $simulationErr.FullName -Destination (Join-Path $DestinationDir "vissim_simulation_$simulationNumber.err") `
        -Force -ErrorAction Stop
    }
  }
}

$stateCsv = Join-Path $OutDir "state_$Name.csv"
$actionCsv = Join-Path $OutDir "action_$Name.csv"
$bottleneckLinkCsv = Join-Path $OutDir "bottleneck_links_$Name.csv"
$bottleneckSegmentCsv = Join-Path $OutDir "bottleneck_segments_$Name.csv"
$decisionDir = Join-Path $OutDir "decisions_$Name"
$log = Join-Path $OutDir "runlog_$Name.txt"
New-Item -ItemType Directory -Force -Path $decisionDir | Out-Null
$runId = [guid]::NewGuid().ToString("N")
$wallPolicyDoc = Get-Content -LiteralPath $Tuning -Raw -Encoding UTF8 -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
$unlimitedDecision = $wallPolicyDoc.adapter.joint_owner_game.ignore_wall_time_limits -eq $true

$recordingDoc = $null
if ($NetworkRecordingProof -ne "") {
  $NetworkRecordingProof = Resolve-RepoPath $NetworkRecordingProof
  $recordingTuning = Get-Content -LiteralPath $Tuning -Raw -Encoding UTF8 -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
  if ($recordingTuning.execution.native_signal_record -isnot [bool] -or -not $recordingTuning.execution.native_signal_record) {
    throw 'Recording copy requires execution.native_signal_record=true'
  }
  $recordingDoc = Get-Content -LiteralPath $NetworkRecordingProof -Raw -Encoding UTF8 -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
  $recordingPython = [Environment]::GetEnvironmentVariable('RW_PYTHON', 'Process')
  if ([string]::IsNullOrWhiteSpace($recordingPython)) { throw 'Recording proof requires explicit RW_PYTHON' }
  $recordingCheck = 'import json,sys; from pathlib import Path; sys.path.insert(0,sys.argv[2]); from evaluation.controllers.network_provenance import validate_recording_proof; p=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig")); assert Path(p["recorded_network"]["path"]).resolve()==Path(sys.argv[3]).resolve(), "Loaded network differs from recording proof"; print(validate_recording_proof(p))'
  $recordingEncoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($recordingCheck))
  $recordingBootstrap = "exec(__import__('base64').b64decode('" + $recordingEncoded + "'))"
  $recordingPhysicalSha = & $recordingPython -B -X utf8 -c $recordingBootstrap $NetworkRecordingProof $repo $net
  if ($LASTEXITCODE -ne 0 -or $recordingPhysicalSha -cne $recordingDoc.source_network.sha256) {
    throw 'Recording-only network proof failed before native launch'
  }
}

$provenanceFiles = [ordered]@{
  network = Get-ArtifactEvidence $net
  main_vbs_runner = Get-ArtifactEvidence $runner
  watchdog_wrapper = Get-ArtifactEvidence $PSCommandPath
  adapter = Get-ArtifactEvidence $adapter
  calibration = Get-ArtifactEvidence $Calibration
  tuning = Get-ArtifactEvidence $Tuning
  control_mapping = Get-ArtifactEvidence $Mapping
  generated_vbs_config = Get-ArtifactEvidence $vbsConfig
  vehicle_input_roles = Get-ArtifactEvidence $VehicleInputRoles
  demand_profile = Get-ArtifactEvidence $DemandProfile
  urban_input_gate_map = Get-ArtifactEvidence $UrbanInputGateMap
  # 2026-08-19: provenance 가 2026-08-05 세대를 해시하고 있었다. core17legs4b 정본으로 옮긴다.
  # 링크 배정은 권역 정본이 대신한다 - 그것이 이 세대의 배정이다.
  link_assignment = Get-ArtifactEvidence (Join-Path $repo "outputs\urban_player_territory_v1_20260819.json")
  intersection_adjacency = Get-ArtifactEvidence (Join-Path $repo "outputs\intersection_adjacency_core17legs4b_20260819.json")
  storage_capacity = Get-ArtifactEvidence (Join-Path $repo "outputs\urban_storage_capacity_core17legs4b_20260819.json")
  pn_boundary_turns = Get-ArtifactEvidence (Join-Path $repo "outputs\pn_boundary_turns_v1_20260819.json")
  numsim_snapshot = Get-ArtifactEvidence (Join-Path $repo "vendor\NumSim-mine\SNAPSHOT.md")
}
$signalPlan = Join-Path ([IO.Path]::GetDirectoryName($vbsConfig)) ([IO.Path]::GetFileNameWithoutExtension($vbsConfig) + '_sgplan.vbs')
if (Test-Path -LiteralPath $signalPlan -PathType Leaf) { $provenanceFiles.signal_group_plan = Get-ArtifactEvidence $signalPlan }
if ($null -ne $recordingDoc) { $provenanceFiles.network_recording_proof = Get-ArtifactEvidence $NetworkRecordingProof }
$signalPrograms = @(
  Get-ChildItem -LiteralPath ([System.IO.Path]::GetDirectoryName($net)) -Filter "*.sig" -File -ErrorAction SilentlyContinue |
    Sort-Object Name |
    ForEach-Object { Get-ArtifactEvidence $_.FullName }
)
$controllerSources = @(
  Get-ChildItem -LiteralPath (Join-Path $repo "evaluation\controllers") -Filter "*.py" -File |
    Sort-Object Name |
    ForEach-Object { Get-ArtifactEvidence $_.FullName }
)
$workspaceCommit = Get-ExactGitCommit $repo
$numsimRootEnv = [Environment]::GetEnvironmentVariable("NUMSIM_REPO_ROOT", "Process")
$numsimRoot = $numsimRootEnv
if ([string]::IsNullOrWhiteSpace($numsimRoot)) {
  $numsimRoot = Join-Path $repo "vendor\NumSim-mine"
}
$provenanceFiles.numsim_default_yaml = Get-ArtifactEvidence (Join-Path $numsimRoot "src\config\default.yaml")
$numsimCommit = ""
if (-not [string]::IsNullOrWhiteSpace($numsimRoot) -and (Test-Path -LiteralPath $numsimRoot)) {
  $numsimCommit = Get-ExactGitCommit $numsimRoot
}
$numsimSnapshotCommit = ""
$numsimSnapshotPath = Join-Path $numsimRoot "SNAPSHOT.md"
if (Test-Path -LiteralPath $numsimSnapshotPath -PathType Leaf) {
  $match = [regex]::Match([System.IO.File]::ReadAllText($numsimSnapshotPath), "(?<![0-9a-f])[0-9a-f]{7,40}(?![0-9a-f])", "IgnoreCase")
  if ($match.Success) { $numsimSnapshotCommit = $match.Value }
}
# 거동을 바꾸는 RW_* 환경변수를 provenance 에 남긴다.
#
# 왜. 이 러너는 RW_FORCE_STEPWISE / RW_AUDIT_ANCHORS_SEC / RW_RUN_ID / RW_RUN_MANIFEST_PATH
# 넷만 저장·설정·원복하고 나머지는 **부모 셸에서 그대로 상속**한다. 그런데 어댑터와 VBS 가
# 읽는 RW_* 는 그보다 훨씬 많고(RW_ADAPTER_MODE · RW_STOPPED_SPLIT · RW_SUBWINDOW_SERVICE ·
# RW_NARROW_AXIS_SG · RW_MAINLINE_SG_ONLY · RW_QUEUE_ORIGIN_FILTER · RW_OFFSET_WRITER ...),
# 그것들이 실런 기록에 **한 줄도 안 남았다**. 팔끼리 비교할 때 무엇이 켜져 있었는지
# 사후에 알 방법이 없다 - 논문 재현성에 직접 걸린다.
#
# 순수 추가다. 값을 바꾸지 않고 적기만 한다.
$headObservation = Read-HeadObservationSettings $Tuning
# obs150 (plan A8, CONTRACT 1.5): a v2 manifest refuses every argument that would label a window wrongly.
# The runner VBS re-checks the same rules from the environment it receives.
$script:Obs150GtText = ''
$script:Obs150Run = [bool]$headObservation.obs150
$obs150GtWindows = New-Object System.Collections.ArrayList
if ($headObservation.obs150) {
  # Never by process name: Kill-Vissim stops every VISSIM and cscript on the machine, the other live
  # runs' included. The v2 path always behaves as -NoGlobalKill and stops only the cscript it starts
  # and the VISSIM it identifies, by PID and start time (Stop-RunProcesses).
  $NoGlobalKill = $true
  if ($MaxAttempts -gt 1) {
    throw "obs150 runs one attempt; got -MaxAttempts $MaxAttempts (a retry reuses the run folder, its obs150 chunks and the network's _001.err, which the runner refuses)"
  }
  Write-Output ("OBS150 kill_policy=pid_only no_global_kill={0} max_attempts={1}" -f [bool]$NoGlobalKill, $MaxAttempts)
  if ($vbsConfig -ne $headObservation.obs150.runner_config.path) {
    throw "obs150 -VbsConfig $vbsConfig is not the manifest runner_config $($headObservation.obs150.runner_config.path)"
  }
  if ($ForceStepwise) { throw 'obs150 (v2 manifest) rejects -ForceStepwise: 0.1 s steps would be labelled as seconds' }
  if ($ControlIntervalSec -ne 150) { throw "obs150 decides every 150 s; got -ControlIntervalSec $ControlIntervalSec" }
  if ($StateLogIntervalSec -ne $ControlIntervalSec) { throw "obs150 requires -StateLogIntervalSec equal to -ControlIntervalSec; got $StateLogIntervalSec" }
  if ($SimPeriod -lt 150 -or ($SimPeriod % 150) -ne 0) { throw "obs150 requires -SimPeriod as a positive multiple of 150; got $SimPeriod" }
  if (-not [string]::IsNullOrWhiteSpace($AuditAnchorsSec)) { throw 'obs150 rejects -AuditAnchorsSec (a second state writer)' }
  if ($IncidentLink -gt 0) { throw 'obs150 rejects an incident closure (signal writes outside the runner log)' }
  $obs150GtWindows = ConvertTo-Obs150GtWindows $GroundTruthWindows $SimPeriod
  if ($obs150GtWindows.Count -gt 0 -and -not $Name.StartsWith('sdmpc31_g', [StringComparison]::Ordinal)) {
    throw '-GroundTruthWindows is allowed only on dev runs named sdmpc31_g*'
  }
  $script:Obs150GtText = (@($obs150GtWindows | ForEach-Object { '{0}:{1}' -f $_[0], $_[1] }) -join ',')
} elseif ($GroundTruthWindows -ne '') {
  throw '-GroundTruthWindows needs a coupled-lane-plant/v2 manifest (obs150)'
}
Set-HeadObservationTransport $Tuning $headObservation
if ($headObservation.obs150) { Write-Output 'OBS150 RW_QUEUE_WINDOW=0 (decision150 overrides the urban.capacity.measured line above)' }
$rampMeterTiming = Read-RampMeterTimingSettings $Tuning
Set-RampMeterTimingTransport $Tuning $rampMeterTiming
$rwEnv = [ordered]@{}
foreach ($e in (Get-ChildItem Env: | Where-Object { $_.Name -like "RW_*" } | Sort-Object Name)) {
  $rwEnv[$e.Name] = [string]$e.Value
}
# RW_ADAPTER_MODE 는 tuning 뒤에 적용돼 설정의 leader_candidate_count / max_nash_iter 를
# 조용히 덮어쓴다(fuller-smoke = 9->5 / 4->2). 켜져 있으면 크게 알린다.
if (-not [string]::IsNullOrWhiteSpace($env:RW_ADAPTER_MODE)) {
  Log "WARNING $Name RW_ADAPTER_MODE=$($env:RW_ADAPTER_MODE) - tuning 의 탐색 예산을 덮어쓴다. 의도한 것이 아니면 지우고 다시 돌려라."
}
$provenance = [ordered]@{
  schema_version = 1
  run_id = $runId
  name = $Name
  created_at = (Get-Date).ToString("o")
  workspace_root = $repo
  workspace_git_commit = [string]$workspaceCommit
  numsim_repo_root_env = [string]$numsimRootEnv
  numsim_repo_root_effective = [string]$numsimRoot
  numsim_git_commit = [string]$numsimCommit
  numsim_snapshot_commit = [string]$numsimSnapshotCommit
  seed = $Seed
  sim_period_sec = $SimPeriod
  control_interval_sec = $ControlIntervalSec
  state_log_interval_sec = $StateLogIntervalSec
  startup_stall_sec = $StartupStallSec
  demand_scale = $DemandScale
  demand_profile = $DemandProfile
  controller = $Controller
  audit_anchors_sec = $AuditAnchorsSec
  env = $rwEnv
  files = $provenanceFiles
  signal_programs = $signalPrograms
  controller_sources = $controllerSources
}
if ($headObservation.options.enabled) { $provenance.signal_observation = $headObservation }
$provenance.ramp_meter_timing = $rampMeterTiming
if ($headObservation.obs150) {
  # CONTRACT 1.4 (validate_provenance_observation). A launch runs from a frozen tree only (NEW-14);
  # PreflightOnly in the working tree has no FREEZE.json and records null.
  $freezeFile = Join-Path $repo 'FREEZE.json'
  $freezePin = $null
  if (Test-Path -LiteralPath $freezeFile -PathType Leaf) {
    $freezePin = [ordered]@{path=$freezeFile; sha256=(Get-FileHash -LiteralPath $freezeFile -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()}
  } elseif (-not $PreflightOnly) {
    throw "An obs150 launch runs only from a frozen tree: $freezeFile is missing (freeze_worktree.ps1)"
  }
  $provenance.observation = [ordered]@{
    schema = 'obs150-provenance/v1'
    cadence = 'decision150'
    plant_manifest = $headObservation.obs150.plant_manifest
    detectors = $headObservation.obs150.detectors
    expected_simres = $headObservation.obs150.expected_simres
    vehrec_interval_sec = $headObservation.obs150.vehrec_interval_sec
    ground_truth_windows = $obs150GtWindows
    freeze = $freezePin
  }
  Write-Output ("OBS150 cadence=decision150 detectors={0} rows={1} gt={2} freeze={3}" -f $headObservation.obs150.detectors.path,
    $headObservation.obs150.detectors.rows, $(if ($script:Obs150GtText) { $script:Obs150GtText } else { '-' }), $(if ($freezePin) { $freezePin.path } else { 'null' }))
}
if ($null -ne $recordingDoc) { $provenance.network_recording = $recordingDoc }
$provenancePath = Join-Path $OutDir "run_provenance_$Name.json"
[System.IO.File]::WriteAllText(
  $provenancePath,
  ($provenance | ConvertTo-Json -Depth 8),
  [System.Text.UTF8Encoding]::new($false)
)
if ($PreflightOnly) {
  # Plan A8: the provenance (env, pins, obs150 block) exactly as a launch writes it; nothing is started.
  Write-Output ("PREFLIGHT_ONLY provenance={0}" -f $provenancePath)
  exit 0
}

function Archive-AttemptOutputs([int]$Attempt) {
  # Shorten run-specific paths without merging failures in a shared OutDir.
  $archiveParentLeaf = [IO.Path]::GetFileName([IO.Path]::GetFullPath($OutDir).TrimEnd(
    [IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar))
  if ($archiveParentLeaf.Equals($Name, [StringComparison]::OrdinalIgnoreCase)) {
    $archive = Join-Path $OutDir ("attempt_{0:00}" -f $Attempt)
  } else {
    $archive = Join-Path $OutDir ("attempt_{0:00}_{1}" -f $Attempt, $Name)
  }
  New-Item -ItemType Directory -Force -Path $archive | Out-Null
  foreach ($path in @($stateCsv, $actionCsv, $bottleneckLinkCsv, $bottleneckSegmentCsv, $log, "$log.err")) {
    if (Test-Path $path) {
      Copy-Item -LiteralPath $path -Destination (Join-Path $archive ([System.IO.Path]::GetFileName($path))) -Force -ErrorAction SilentlyContinue
    }
  }
  if (Test-Path $decisionDir) {
    $decisionArchive = Join-Path $archive 'decisions'
    Copy-Item -LiteralPath $decisionDir -Destination $decisionArchive -Recurse -Force -ErrorAction SilentlyContinue
  }
  Copy-VissimError $archive
}

if ($DoneRows -gt 0 -and (Test-Path $stateCsv)) {
  $rows = (Get-Content $stateCsv | Measure-Object -Line).Lines
  if ($rows -ge $DoneRows) {
    Log "SKIP $Name rows=$rows"
    exit 0
  }
}

for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
  if (-not $NoGlobalKill) { Kill-Vissim } else { Log "NoGlobalKill: 전역 VISSIM/cscript kill 생략" }
  Clear-DecisionDir $decisionDir
  $argline = "//nologo " + (Q $runner) + " " + (Q $net) + " " + (Q $stateCsv) + " " + (Q $actionCsv) + " " + (Q $decisionDir) +
    " $SimPeriod $ControlIntervalSec $Seed " + (Q $adapter) + " " + (Q $Calibration) + " " + (Q $Tuning) + " " + (Q $Mapping) +
    " " + (Q $Controller) + " $ControlStartSec " + (Q $WarmupController) + " " + (Q $vbsConfig)
  $argline = $argline + " $StateLogIntervalSec"
  $argline = $argline + " $DemandScale"
  $argline = $argline + " " + (Q $DemandProfile) + " " + (Q $VehicleInputRoles)
  $argline = $argline + " $IncidentLink $IncidentLane $IncidentPos $IncidentStartSec $IncidentEndSec " + (Q $IncidentName)
  $argline = $argline + " " + (Q $UrbanInputGateMap)

  $t0 = Get-Date
  $existingVissimIds = @(Get-Process -Name VISSIM200 -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
  $runVissimIdentity = $null
  $simulationStarted = $false
  Normalize-ProcessPathEnv
  $oldForceStepwise = [Environment]::GetEnvironmentVariable("RW_FORCE_STEPWISE", "Process")
  $oldAuditAnchors = [Environment]::GetEnvironmentVariable("RW_AUDIT_ANCHORS_SEC", "Process")
  $oldRunId = [Environment]::GetEnvironmentVariable("RW_RUN_ID", "Process")
  $oldRunManifest = [Environment]::GetEnvironmentVariable("RW_RUN_MANIFEST_PATH", "Process")
  if ($ForceStepwise) {
    [Environment]::SetEnvironmentVariable("RW_FORCE_STEPWISE", "1", "Process")
  } else {
    [Environment]::SetEnvironmentVariable("RW_FORCE_STEPWISE", $null, "Process")
  }
  if ([string]::IsNullOrWhiteSpace($AuditAnchorsSec)) {
    [Environment]::SetEnvironmentVariable("RW_AUDIT_ANCHORS_SEC", $null, "Process")
  } else {
    [Environment]::SetEnvironmentVariable("RW_AUDIT_ANCHORS_SEC", $AuditAnchorsSec, "Process")
  }
  [Environment]::SetEnvironmentVariable("RW_RUN_ID", $runId, "Process")
  [Environment]::SetEnvironmentVariable("RW_RUN_MANIFEST_PATH", $provenancePath, "Process")
  Set-HeadObservationTransport $Tuning $headObservation
  Set-RampMeterTimingTransport $Tuning $rampMeterTiming
  $cscriptExe = Join-Path $env:SystemRoot "System32\cscript.exe"
  if (-not (Test-Path $cscriptExe)) { $cscriptExe = "cscript.exe" }
  $proc = Start-Process -FilePath $cscriptExe -ArgumentList $argline -RedirectStandardOutput $log `
    -RedirectStandardError "$log.err" -WorkingDirectory $repo -PassThru -WindowStyle Hidden
  [Environment]::SetEnvironmentVariable("RW_FORCE_STEPWISE", $oldForceStepwise, "Process")
  [Environment]::SetEnvironmentVariable("RW_AUDIT_ANCHORS_SEC", $oldAuditAnchors, "Process")
  [Environment]::SetEnvironmentVariable("RW_RUN_ID", $oldRunId, "Process")
  [Environment]::SetEnvironmentVariable("RW_RUN_MANIFEST_PATH", $oldRunManifest, "Process")
  if (-not $proc -or -not $proc.Id) {
    throw "Failed to start cscript for $Name attempt=$attempt"
  }
  # Recorded at launch: a stop targets this PID only while its start time still matches.
  $runnerIdentity = [pscustomobject]@{ Id = $proc.Id; StartTime = $proc.StartTime }
  Log "START $Name attempt=$attempt pid=$($proc.Id)"
  if ($script:Obs150Run) {
    Log "KILL_POLICY $Name pid_only runner_pid=$($runnerIdentity.Id) runner_start=$($runnerIdentity.StartTime.ToString('o'))"
  }

  while ($true) {
    Start-Sleep -Seconds 20
    if ($proc.HasExited) {
      $done = Select-String -Path $log -Pattern "STAGE=SIM_DONE" -Quiet -ErrorAction SilentlyContinue
      if ($done) {
        Copy-VissimError $OutDir
        Log "OK $Name attempt=$attempt elapsed=$([int]((Get-Date)-$t0).TotalSeconds)s"
        exit 0
      }
      Log "EXIT_NO_DONE $Name attempt=$attempt"
      Archive-AttemptOutputs $attempt
      if ($script:Obs150Run) {
        # One attempt and never a kill by name, so nothing else would free the seat of a VISSIM the exited
        # runner left behind. Archive-AttemptOutputs has waited for its .err; stop it by PID and start time.
        if ($null -eq $runVissimIdentity) {
          $runVissimIdentity = Find-RunVissimIdentity $existingVissimIds $t0 ([IO.Path]::GetFileName($net))
        }
        Stop-RunProcesses $runnerIdentity $runVissimIdentity
        if ($null -eq $runVissimIdentity) { Log "WARNING no unique VISSIM process identified after EXIT_NO_DONE" }
      }
      break
    }

    if ($null -eq $runVissimIdentity) {
      $runVissimIdentity = Find-RunVissimIdentity $existingVissimIds $t0 ([IO.Path]::GetFileName($net))
      if ($runVissimIdentity) { Log "VISSIM_PROCESS $Name pid=$($runVissimIdentity.Id)" }
    }
    if (-not $simulationStarted) {
      $simulationStarted = Test-SimulationStarted $stateCsv $log
      if (-not $simulationStarted -and ((Get-Date)-$t0).TotalSeconds -ge $StartupStallSec) {
        Log "STARTUP_TIMEOUT $Name attempt=$attempt limit=${StartupStallSec}s"
        $runDescendants = $(if ($script:Obs150Run) { Get-RunDescendantIdentities $runnerIdentity } else { @() })
        Stop-RunProcesses $runnerIdentity $runVissimIdentity $runDescendants
        if ($null -eq $runVissimIdentity) { Log "WARNING no unique VISSIM process identified; stopped only this run's cscript" }
        Archive-AttemptOutputs $attempt
        break
      }
    }

    $lastT = $proc.StartTime
    $signals = @()
    $signals += Get-Item $log -ErrorAction SilentlyContinue
    $signals += Get-Item $stateCsv -ErrorAction SilentlyContinue
    $signals += Get-Item $actionCsv -ErrorAction SilentlyContinue
    $signals += Get-Item $bottleneckLinkCsv -ErrorAction SilentlyContinue
    $signals += Get-Item $bottleneckSegmentCsv -ErrorAction SilentlyContinue
    $signals += Get-ChildItem (Join-Path $decisionDir "action_*.json") -ErrorAction SilentlyContinue |
      Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($unlimitedDecision) {
      # Real model progress is not a native simulation step. It may nevertheless
      # keep an intentionally long decision alive after the first native step.
      # Startup's actual-progress300s watchdog above remains independent.
      $signals += Get-ChildItem (Join-Path $decisionDir "action_*.joint.progress.jsonl") -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    }
    foreach ($signal in $signals) {
      if ($signal -and $signal.LastWriteTime -gt $lastT) {
        $lastT = $signal.LastWriteTime
      }
    }
    $idle = [int]((Get-Date) - $lastT).TotalSeconds
    if ($idle -gt $StallSec) {
      Log "WATCHDOG_KILL $Name attempt=$attempt idle=${idle}s"
      $runDescendants = $(if ($script:Obs150Run) { Get-RunDescendantIdentities $runnerIdentity } else { @() })
      Stop-RunProcesses $runnerIdentity $runVissimIdentity $runDescendants
      if ($null -eq $runVissimIdentity) { Log "WARNING no unique VISSIM process identified; stopped only this run's cscript" }
      Archive-AttemptOutputs $attempt
      break
    }
  }
}

Log "FAIL $Name after $MaxAttempts attempts"
exit 1
