[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$OutputDirectory,
      [string]$ProbeScript = 'diagnostics/probe_vehicle_route_com.vbs',
      [string[]]$AdditionalSources = @())
$ErrorActionPreference = 'Stop'
$probeRepo = Split-Path -Parent $PSScriptRoot
$probeOutput = [IO.Path]::GetFullPath((Join-Path $probeRepo $OutputDirectory))
if (-not $probeOutput.StartsWith($probeRepo + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Probe output must remain inside the worktree' }
if (Test-Path -LiteralPath $probeOutput) { throw 'Probe output already exists' }
New-Item -ItemType Directory -Path $probeOutput | Out-Null
$probeNetwork = Join-Path $probeRepo 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'
$probeVbs = [IO.Path]::GetFullPath((Join-Path $probeRepo $ProbeScript))
if (-not $probeVbs.StartsWith($PSScriptRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetExtension($probeVbs) -ne '.vbs') { throw 'Probe script must be a VBS file inside worktree diagnostics' }
$probeLog = Join-Path $probeOutput 'stdout.txt'
$probeErr = Join-Path $probeOutput 'stderr.txt'
$probeCsv = Join-Path $probeOutput 'routes.csv'
# Reuse the reviewed process-identity/stop procedures without executing the runner.
$probeWatchdog = Join-Path $probeRepo 'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1'
$probeTokens = $null; $probeParseErrors = $null
$probeAst = [Management.Automation.Language.Parser]::ParseFile($probeWatchdog, [ref]$probeTokens, [ref]$probeParseErrors)
if ($probeParseErrors.Count) { throw 'Cannot parse canonical watchdog' }
foreach ($probeFunction in @('Find-RunVissimIdentity','Stop-RunProcesses')) {
    $probeNode = $probeAst.Find({ param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $probeFunction }, $true)
    if ($null -eq $probeNode) { throw "Missing canonical watchdog function: $probeFunction" }
    . ([scriptblock]::Create($probeNode.Extent.Text))
}
$probeEvidence = [ordered]@{ scope='Native attribute types and current-route semantics only; no performance comparison'; sources=@{}; startup_timeout_sec=300 }
foreach ($probePath in @($probeNetwork,$probeVbs,$PSCommandPath,$probeWatchdog) + @(Get-ChildItem -LiteralPath (Split-Path $probeNetwork) -Filter '*.sig' -File | Select-Object -ExpandProperty FullName) + @($AdditionalSources | ForEach-Object { Join-Path $probeRepo $_ })) {
    $probeEvidence.sources[$probePath] = (Get-FileHash -LiteralPath $probePath -Algorithm SHA256).Hash
}
$probeExisting = @(Get-Process -Name VISSIM200 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
if ($probeExisting.Count) { throw 'A VISSIM instance already exists; probe needs the one license free' }
$probeStart = Get-Date
$probeArguments = '//nologo "' + $probeVbs + '" "' + $probeNetwork + '" "' + $probeCsv + '"'
$probeProcess = Start-Process -FilePath 'cscript.exe' -ArgumentList $probeArguments -PassThru -WindowStyle Hidden -RedirectStandardOutput $probeLog -RedirectStandardError $probeErr
$probeIdentity = $null
$probeProgressTime = $probeStart
$probeSimTime = 0.0
$probeTimedOut = $false
try {
    while (-not $probeProcess.HasExited) {
        Start-Sleep -Seconds 5
        $probeProcess.Refresh()
        if ($null -eq $probeIdentity) {
            $probeIdentity = Find-RunVissimIdentity $probeExisting $probeStart ([IO.Path]::GetFileNameWithoutExtension($probeNetwork))
            if ($probeIdentity) { Write-Output "OWNED_VISSIM=$($probeIdentity.Id)" }
        }
        $probeLines = @(Get-Content -LiteralPath $probeLog -Tail 8 -ErrorAction SilentlyContinue)
        foreach ($probeLine in $probeLines) {
            if ($probeLine -match '^SIM_SEC=([0-9.]+)$' -and [double]$Matches[1] -gt $probeSimTime) {
                $probeSimTime = [double]$Matches[1]
                $probeProgressTime = Get-Date
                Write-Output $probeLine
            }
        }
        if (((Get-Date) - $probeProgressTime).TotalSeconds -ge 300) {
            $probeTimedOut = $true
            Write-Output 'PROBE_TIMEOUT_NO_SIM_PROGRESS=300'
            Stop-RunProcesses $probeProcess $probeIdentity
            break
        }
    }
    $probeProcess.WaitForExit()
    $probeEvidence.exit_code = $probeProcess.ExitCode
    $probeEvidence.timed_out = $probeTimedOut
    $probeEvidence.owned_cscript_pid = $probeProcess.Id
    $probeEvidence.owned_vissim = $probeIdentity
    $probeEvidence.elapsed_sec = ((Get-Date)-$probeStart).TotalSeconds
    $probeEvidence.source_changes = @($probeEvidence.sources.Keys | Where-Object { (Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash -ne $probeEvidence.sources[$_] })
    $probeEvidence.passed = (-not $probeTimedOut -and $probeProcess.ExitCode -eq 0 -and $probeEvidence.source_changes.Count -eq 0 -and (Select-String -LiteralPath $probeLog -Pattern '^ROUTE_PROBE_DONE=1$' -Quiet))
    $probeEvidence | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $probeOutput 'manifest.json') -Encoding UTF8
    if (-not $probeEvidence.passed) { Get-Content -LiteralPath $probeErr; throw 'Route COM probe failed' }
    Write-Output "PASS route attribute probe $probeOutput"
} finally {
    if (-not $probeProcess.HasExited) { Stop-RunProcesses $probeProcess $probeIdentity }
}
