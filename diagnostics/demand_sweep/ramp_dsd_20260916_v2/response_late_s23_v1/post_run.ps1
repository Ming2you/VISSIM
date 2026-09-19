$ErrorActionPreference='Stop'
$casePath=$PSScriptRoot
$repoPath=(Resolve-Path (Join-Path $casePath '../../../..')).Path
$pythonPath=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$protocol=Get-Content (Join-Path $casePath 'protocol.json') -Raw | ConvertFrom-Json
$arms=@('rm8','rm_ramp','vsl','both')
do {
  $finishedCount=0
  foreach($arm in $arms){
    $receipt=$null
    try { $receipt=Get-Content (Join-Path $casePath "run_$arm/run.json") -Raw | ConvertFrom-Json } catch { }
    if($receipt.finished){
      if(-not $receipt.completed -or $receipt.owned_native_alive){throw "Native experiment failed: $arm"}
      $finishedCount++
    }
  }
  if($finishedCount -lt $arms.Count){Start-Sleep -Seconds 10}
} until ($finishedCount -eq $arms.Count)
Set-Location -LiteralPath $repoPath
foreach($arm in $arms){
  & $pythonPath -B -X utf8 diagnostics/fast_fixed_profile_verify.py --prepared "$casePath/prepared_$arm" --run "$casePath/run_$arm" --reference $protocol.baseline_run *> "$casePath/paired_verify_$arm.log"
  if($LASTEXITCODE -ne 0){throw "Same-state native verification failed: $arm"}
}
Write-Output 'All native prefixes and commands verified'
& $pythonPath -B -X utf8 diagnostics/demand_sweep/ramp_dsd_20260916_v1/analyze_pair.py --response-pairs --runs $casePath *> "$casePath/analysis.log"
if($LASTEXITCODE -ne 0){throw 'Omega analysis failed'}
Write-Output 'Omega analysis complete'
& $pythonPath -B -X utf8 diagnostics/demand_sweep/ramp_dsd_20260916_v2/extract_response.py --pairs --runs $casePath *> "$casePath/extraction.log"
if($LASTEXITCODE -ne 0){throw 'Physical observations failed'}
Write-Output 'Physical observation extraction complete'
& $pythonPath -B -X utf8 "$casePath/evaluate.py" --analyze *> "$casePath/response_analysis.log"
if($LASTEXITCODE -ne 0){throw 'Response diagnosis failed'}
Write-Output 'Response diagnosis complete'
