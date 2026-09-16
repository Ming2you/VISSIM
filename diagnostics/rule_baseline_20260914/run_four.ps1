param(
    [int]$EndSec=3000,
    [ValidateSet('none','vsl','rm','both')][string[]]$Arms=@('none','vsl','rm','both'),
    [ValidatePattern('^v[0-9]+$')][string]$Revision='v2',
    [string]$SelectedPrepared='diagnostics/demand_sweep/fw080_urban050/prepared',
    [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$CasePrefix='rule100'
)
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $repo
foreach ($arm in $Arms) {
    $name="${CasePrefix}_${arm}${EndSec}_s13_${Revision}"
    $log=Join-Path $PSScriptRoot ($name+'_console.log')
    if (Test-Path -LiteralPath $log) { throw "Preserve existing case log: $log" }
    & ./diagnostics/run_selected_control_trial.ps1 `
        -SelectedPrepared $SelectedPrepared `
        -Tuning (Join-Path $PSScriptRoot ('config_'+$arm+'_'+$Revision+'.json')) `
        -Name $name -Controller diagnostic-rule-profile -SimPeriod $EndSec `
        -ControlStartSec 900 -Seed 13 -Execute *> $log
    if ($LASTEXITCODE -ne 0) { throw "Rule case failed; preserved $name" }
    $receipt=Get-Content -LiteralPath (Join-Path $repo "evaluation/runs/$name/completion_receipt.json") -Raw | ConvertFrom-Json
    if (-not $receipt.completed) { throw "Rule case did not complete: $name" }
    Write-Output "RULE_CASE_COMPLETED arm=$arm end=$EndSec run=$name"
}
