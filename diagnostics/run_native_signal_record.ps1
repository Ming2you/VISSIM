[CmdletBinding()]
param([string]$EvidenceDirectory = 'diagnostics/native_signal_record_s13_60_v1')
$ErrorActionPreference = 'Stop'
$probeRoot = Split-Path -Parent $PSScriptRoot
$probeDirectory = [IO.Path]::GetFullPath((Join-Path $probeRoot $EvidenceDirectory))
if (-not $probeDirectory.StartsWith($PSScriptRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Diagnostic workspace path required' }
$probePreflight = Get-Content -LiteralPath (Join-Path $probeDirectory 'preflight.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$probeNetwork = [IO.Path]::GetFullPath($probePreflight.network)
if (-not $probeNetwork.StartsWith($probeDirectory + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Network must be the prepared diagnostic copy' }
if ((Get-FileHash -LiteralPath $probeNetwork -Algorithm SHA256).Hash.ToLowerInvariant() -ne $probePreflight.network_sha256) { throw 'Prepared network changed' }
$probeResultPath = Join-Path $probeDirectory 'process.json'
if (Test-Path -LiteralPath $probeResultPath) { throw 'Evidence exists; use a new directory' }
if (@(Get-Process -Name VISSIM200,cscript -ErrorAction SilentlyContinue).Count) { throw 'Existing simulator/script host; do not overlap or terminate it' }
# Use the canonical PID + creation-time cleanup functions; never invoke its
# launcher body or the legacy blanket Kill-Vissim function.
$probeTokens = $null; $probeParseErrors = $null
$probeWatchdog = Join-Path $probeRoot 'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1'
$probeAst = [Management.Automation.Language.Parser]::ParseFile($probeWatchdog,[ref]$probeTokens,[ref]$probeParseErrors)
if ($probeParseErrors.Count) { throw 'Canonical watchdog parse failed' }
foreach ($probeFunction in @('Find-RunVissimIdentity','Stop-RunProcesses')) {
    $probeMatches = @($probeAst.FindAll({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $probeFunction},$true))
    if ($probeMatches.Count -ne 1) { throw 'Canonical cleanup function is not unique' }
    . ([scriptblock]::Create($probeMatches[0].Extent.Text))
}
$probeScript = Join-Path $PSScriptRoot 'probe_native_signal_record.vbs'
$probeStdout = Join-Path $probeDirectory 'stdout.txt'
$probeStderr = Join-Path $probeDirectory 'stderr.txt'
$probeArgs = '//nologo "' + $probeScript + '" "' + $probeNetwork + '" "' + (Join-Path $probeDirectory 'vissim_eval') + '"'
$probeStarted = Get-Date
$probeRunner = $null; $probeOwnedVissim = $null; $probeProcess = $null
$probeLastSec = 0.; $probeLastProgress = $probeStarted; $probeFailure = $null
$probeReport = [ordered]@{started_utc=$probeStarted.ToUniversalTime().ToString('o'); native_completed=$false; actual_sim_sec=0; script_sha256=(Get-FileHash -LiteralPath $probeScript -Algorithm SHA256).Hash.ToLowerInvariant(); network_sha256=$probePreflight.network_sha256; arguments=$probeArgs; native_lsa_coverage_passed=$false}
try {
    $probeProcess = Start-Process -FilePath 'cscript.exe' -ArgumentList $probeArgs -WindowStyle Hidden -PassThru -RedirectStandardOutput $probeStdout -RedirectStandardError $probeStderr
    $probeHandle = $probeProcess.Handle
    $probeRunner = [pscustomobject]@{Id=$probeProcess.Id; StartTime=$probeProcess.StartTime}
    while (-not $probeProcess.HasExited) {
        Start-Sleep -Milliseconds 500
        $probeProcess.Refresh()
        if ($null -eq $probeOwnedVissim) { $probeOwnedVissim = Find-RunVissimIdentity @() $probeStarted ([IO.Path]::GetFileNameWithoutExtension($probeNetwork)) }
        $probeText = if (Test-Path -LiteralPath $probeStdout) { Get-Content -LiteralPath $probeStdout -Raw } else { '' }
        $probeProgress = [regex]::Matches([string]$probeText, '(?m)^ACTUAL_SIMSEC=([0-9]+)\s*$')
        if ($probeProgress.Count) {
            $probeCurrentSec = [double]$probeProgress[$probeProgress.Count-1].Groups[1].Value
            if ($probeCurrentSec -gt $probeLastSec) { $probeLastSec=$probeCurrentSec; $probeLastProgress=Get-Date }
        }
        if (((Get-Date)-$probeLastProgress).TotalSeconds -ge 300) {
            throw $(if ($probeLastSec -eq 0) { 'NO_INITIAL_ACTUAL_PROGRESS_300_SECONDS' } else { 'NO_FURTHER_ACTUAL_PROGRESS_300_SECONDS' })
        }
    }
    $probeProcess.WaitForExit()
    $probeReport.exit_code = $probeProcess.ExitCode
    if ($probeProcess.ExitCode -ne 0) { throw 'Native diagnostic returned failure; preserve stdout/stderr/readbacks' }
    $probeText = Get-Content -LiteralPath $probeStdout -Raw
    if ($probeText -notmatch '(?m)^ACTUAL_SIMSEC=60\s*$' -or $probeText -notmatch 'NATIVE_RECORD_PROBE_DONE=1') { throw 'Missing actual final time or completion marker' }
    $probeLastSec = 60.
    $probeReport.native_completed = $true
} catch {
    $probeFailure = $_.Exception.Message
} finally {
    if ($null -eq $probeOwnedVissim) { $probeOwnedVissim = Find-RunVissimIdentity @() $probeStarted ([IO.Path]::GetFileNameWithoutExtension($probeNetwork)) }
    if ($probeFailure) { Stop-RunProcesses $probeRunner $probeOwnedVissim }
    $probeDeadline = (Get-Date).AddSeconds(20)
    do {
        $probeAlive = if ($probeOwnedVissim) { Get-Process -Id $probeOwnedVissim.Id -ErrorAction SilentlyContinue } else { $null }
        if (-not $probeAlive -or $probeAlive.StartTime -ne $probeOwnedVissim.StartTime) { break }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $probeDeadline)
    $probeReport.runner_identity = $probeRunner
    $probeReport.vissim_identity = $probeOwnedVissim
    $probeReport.actual_sim_sec = $probeLastSec
    $probeReport.error = $probeFailure
    $probeReport.wall_sec = ((Get-Date)-$probeStarted).TotalSeconds
    $probeReport.owned_vissim_remaining = [bool]($probeAlive -and $probeAlive.StartTime -eq $probeOwnedVissim.StartTime)
    $probeReport | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $probeResultPath -Encoding UTF8
}
$probeReport | ConvertTo-Json -Depth 8
if ($probeFailure) { exit 1 }
