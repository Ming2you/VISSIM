[CmdletBinding()]
param(
    [string]$FlatDirectory = 'diagnostics/fixed_beta300v3_network_arms_flat_v1',
    [string]$OutputDirectory = 'diagnostics/flat_network_native_readback_v1',
    [string]$PythonPath = 'C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
)
$ErrorActionPreference = 'Stop'
$gateRepo = Split-Path -Parent $PSScriptRoot
$gateFlat = [IO.Path]::GetFullPath((Join-Path $gateRepo $FlatDirectory))
$gateOutput = [IO.Path]::GetFullPath((Join-Path $gateRepo $OutputDirectory))
$gateDiagnosticPrefix = $PSScriptRoot + [IO.Path]::DirectorySeparatorChar
if (-not $gateFlat.StartsWith($gateDiagnosticPrefix,[StringComparison]::OrdinalIgnoreCase)) { throw 'Flat assets must be inside diagnostics' }
if (-not $gateOutput.StartsWith($gateDiagnosticPrefix,[StringComparison]::OrdinalIgnoreCase)) { throw 'Gate output must be inside diagnostics' }
if ($gateOutput.StartsWith($gateFlat + [IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -or $gateOutput -eq $gateFlat) { throw 'Do not write native evidence inside immutable asset input' }
if (Test-Path -LiteralPath $gateOutput) { throw 'Output exists; use a new evidence directory' }
if (-not (Test-Path -LiteralPath (Join-Path $gateFlat 'manifest.json') -PathType Leaf)) { throw 'Flat asset generation must finish first' }
if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) { throw 'Python runtime not found' }

$gateVbs = Join-Path $PSScriptRoot 'probe_flat_network_native_settings.vbs'
$gateValidator = Join-Path $PSScriptRoot 'validate_flat_network_native_gate.py'
$gateWatchdog = Join-Path $gateRepo 'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1'
# Reuse only these identity-checked cleanup functions. Never dot-source or run
# the live simulation launcher body, and never kill all VISSIM/cscript processes.
$gateTokens = $null; $gateParseErrors = $null
$gateAst = [Management.Automation.Language.Parser]::ParseFile($gateWatchdog,[ref]$gateTokens,[ref]$gateParseErrors)
if ($gateParseErrors.Count) { throw 'Cannot parse canonical watchdog' }
foreach ($gateName in @('Find-RunVissimIdentity','Stop-RunProcesses')) {
    $gateMatches = @($gateAst.FindAll({ param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $gateName },$true))
    if ($gateMatches.Count -ne 1) { throw "Expected one canonical function: $gateName" }
    . ([scriptblock]::Create($gateMatches[0].Extent.Text))
}

function Test-GateIdentityAlive($Identity) {
    if ($null -eq $Identity) { return $false }
    $current = Get-Process -Id $Identity.Id -ErrorAction SilentlyContinue
    return ($null -ne $current -and $current.StartTime -eq $Identity.StartTime)
}

function Save-GateProcess($Evidence,[string]$Path) {
    if (Test-Path -LiteralPath $Path) { throw 'Process evidence already exists' }
    $Evidence | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Assert-GateQuiet {
    if (@(Get-Process -Name VISSIM200 -ErrorAction SilentlyContinue).Count) { throw 'A VISSIM instance already exists; do not overlap live experiments' }
    if (@(Get-Process -Name cscript -ErrorAction SilentlyContinue).Count) { throw 'An existing cscript may be starting native COM; wait for a quiet interval' }
}

# A parent-controlled quiet interval is required; this tool must not race a live
# experiment. The mutex prevents concurrent copies of this native gate only.
$gateMutex = [Threading.Mutex]::new($false,'Local\CodexFlatNetworkNativeGate')
$gateOwnsMutex = $false
$gatePrepared = $false
$gateFailure = $null
try {
    $gateOwnsMutex = $gateMutex.WaitOne(0)
    if (-not $gateOwnsMutex) { throw 'Another flat native gate is already running' }
    Assert-GateQuiet
    New-Item -ItemType Directory -Path $gateOutput | Out-Null
    & $PythonPath -X utf8 $gateValidator --flat $gateFlat --output $gateOutput
    if ($LASTEXITCODE -ne 0) { throw 'Static source/asset preflight failed before COM' }
    $gatePrepared = $true
    $gatePreflightPath = Join-Path $gateOutput 'preflight.json'
    $gatePreflight = Get-Content -LiteralPath $gatePreflightPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $gatePreflightSha = (Get-FileHash -LiteralPath $gatePreflightPath -Algorithm SHA256).Hash.ToLowerInvariant()

    foreach ($gateArm in @('baseline','lcd10635_2000','upstream1135')) {
        Assert-GateQuiet
        $armEvidence = $gatePreflight.arms.$gateArm
        $armDirectory = Join-Path $gateOutput $gateArm
        New-Item -ItemType Directory -Path $armDirectory | Out-Null
        $armCsv = Join-Path $armDirectory 'routes.csv'
        $armLog = Join-Path $armDirectory 'stdout.txt'
        $armErr = Join-Path $armDirectory 'stderr.txt'
        $armProcess = $null; $armRunnerIdentity = $null; $armVissim = $null
        $armTimedOut = $false; $armError = $null; $armExit = $null
        $armStart = Get-Date
        Assert-GateQuiet
        $armExisting = @(Get-Process -Name VISSIM200 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
        if ($armExisting.Count) { throw 'A concurrent VISSIM instance appeared; no COM probe launched' }
        try {
            # Windows paths cannot contain quotes; do not compose other shell commands.
            $armArguments = '//nologo "' + $gateVbs + '" "' + $armEvidence.network_path + '" "' + $armCsv + '"'
            $armProcess = Start-Process -FilePath 'cscript.exe' -ArgumentList $armArguments -PassThru -WindowStyle Hidden -RedirectStandardOutput $armLog -RedirectStandardError $armErr
            # Windows PowerShell 5.1 can lose ExitCode after a redirected child
            # exits unless its native handle is acquired while it is running.
            $armProcessHandle = $armProcess.Handle
            if ($armProcessHandle -eq [IntPtr]::Zero) { throw 'Unable to retain the owned cscript process handle' }
            $armRunnerIdentity = [pscustomobject]@{ Id=$armProcess.Id; StartTime=$armProcess.StartTime }
            while (-not $armProcess.HasExited) {
                Start-Sleep -Milliseconds 500
                $armProcess.Refresh()
                if ($null -eq $armVissim) {
                    $armVissim = Find-RunVissimIdentity $armExisting $armStart $gateArm
                }
                if (((Get-Date)-$armStart).TotalSeconds -ge 300) {
                    $armTimedOut = $true
                    $armError = 'LOADNET_READBACK_TIMEOUT_300_SECONDS'
                    break
                }
            }
        } catch {
            $armError = $_.Exception.Message
        } finally {
            # Try to identify a loaded native process once more, then only stop
            # recorded PID+creation-time identities. A startup process whose
            # network title never appeared is NOT assumed to be ours.
            if ($null -eq $armVissim) { $armVissim = Find-RunVissimIdentity $armExisting $armStart $gateArm }
            if (Test-GateIdentityAlive $armRunnerIdentity) {
                Stop-RunProcesses $armRunnerIdentity $armVissim
            }
            if ($null -ne $armProcess) {
                $null = $armProcess.WaitForExit(5000)
                $armProcess.Refresh()
                if ($armProcess.HasExited) { $armExit = $armProcess.ExitCode }
                if ($null -eq $armExit -and $null -eq $armError) { $armError = 'OWNED_CSCRIPT_EXIT_CODE_UNAVAILABLE' }
            }
            $armCleanupDeadline = (Get-Date).AddSeconds(20)
            do {
                if ($null -eq $armVissim) { $armVissim = Find-RunVissimIdentity $armExisting $armStart $gateArm }
                $armKnownAlive = Test-GateIdentityAlive $armVissim
                if (-not $armKnownAlive) { break }
                Start-Sleep -Milliseconds 500
            } while ((Get-Date) -lt $armCleanupDeadline)
            if (Test-GateIdentityAlive $armVissim) { Stop-RunProcesses $null $armVissim }
            $armAfterStop = (Get-Date).AddSeconds(5)
            while (((Test-GateIdentityAlive $armRunnerIdentity) -or (Test-GateIdentityAlive $armVissim)) -and (Get-Date) -lt $armAfterStop) {
                Start-Sleep -Milliseconds 250
            }
            $armRemaining = @(Get-Process -Name VISSIM200 -ErrorAction SilentlyContinue | ForEach-Object {
                [pscustomobject]@{ Id=$_.Id; StartTime=$_.StartTime.ToString('o'); MainWindowTitle=$_.MainWindowTitle }
            })
            $armGone = -not (Test-GateIdentityAlive $armRunnerIdentity) -and -not (Test-GateIdentityAlive $armVissim) -and $armRemaining.Count -eq 0
            $record = [ordered]@{
                schema='flat-network-native-process/v1'; arm=$gateArm
                network_path=$armEvidence.network_path; network_sha256=$armEvidence.network_sha256
                preflight_sha256=$gatePreflightSha; start_time=$armStart.ToString('o')
                elapsed_sec=((Get-Date)-$armStart).TotalSeconds; timeout_sec=300
                exit_code=$armExit; timed_out=$armTimedOut; error=$armError
                owned_cscript=$armRunnerIdentity; owned_vissim=$armVissim
                owned_processes_gone=$armGone; requires_cleanup=(-not $armGone)
                remaining_vissim=$armRemaining; simulation_executed=$false
                ownership_limit='An unidentified startup VISSIM is never killed; remaining instances block serial continuation.'
            }
            Save-GateProcess $record (Join-Path $armDirectory 'process.json')
            $armLoadErr = [IO.Path]::ChangeExtension($armEvidence.network_path,'.err')
            if (Test-Path -LiteralPath $armLoadErr -PathType Leaf) {
                Copy-Item -LiteralPath $armLoadErr -Destination (Join-Path $armDirectory 'load_network.err') -ErrorAction Stop
            }
        }
        if ($armError -or $armTimedOut -or $armExit -ne 0 -or -not $armGone) { throw "Native arm failed or cleanup uncertain: $gateArm" }
    }
} catch {
    $gateFailure = $_.Exception.Message
} finally {
    if ($gatePrepared) {
        & $PythonPath -X utf8 $gateValidator --output $gateOutput --finish
        if ($LASTEXITCODE -ne 0 -and $null -eq $gateFailure) { $gateFailure = 'Native readback/source gate failed' }
    }
    if ($gateOwnsMutex) { $gateMutex.ReleaseMutex() }
    $gateMutex.Dispose()
}
if ($null -ne $gateFailure) { throw $gateFailure }
Write-Output "PASS native LoadNet/settings only: $(Join-Path $gateOutput 'native_gate.json')"
