param([Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
$probeRoot = Split-Path $PSScriptRoot -Parent
$probeOutput = [IO.Path]::GetFullPath((Join-Path $probeRoot $OutputDirectory))
$probeDiagnostics = [IO.Path]::GetFullPath($PSScriptRoot) + [IO.Path]::DirectorySeparatorChar
if (-not $probeOutput.StartsWith($probeDiagnostics,[StringComparison]::OrdinalIgnoreCase)) { throw 'Output must be beneath diagnostics' }
if (Test-Path -LiteralPath $probeOutput) { throw 'Output already exists; historical results are never overwritten' }
New-Item -ItemType Directory -Path $probeOutput | Out-Null
$probeRows = @()
foreach ($probeMode in @('original_refresh','no_refresh','retained_handle')) {
    foreach ($probeExpected in @(0,7)) {
        $probeStem = Join-Path $probeOutput ($probeMode + '_' + $probeExpected)
        $probeProcess = $null
        $probeError = $null
        $probeActual = $null
        $probeHandleAcquired = $false
        try {
            $probeProcess = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-NonInteractive','-Command',('"Start-Sleep -Milliseconds 250; exit ' + $probeExpected + '"')) -PassThru -WindowStyle Hidden -RedirectStandardOutput ($probeStem + '.stdout.txt') -RedirectStandardError ($probeStem + '.stderr.txt')
            if ($probeMode -eq 'retained_handle') {
                $probeHandle = $probeProcess.Handle
                if ($probeHandle -eq [IntPtr]::Zero) { throw 'No process handle' }
                $probeHandleAcquired = $true
            }
            $probeIdentity = [pscustomobject]@{ Id=$probeProcess.Id; StartTime=$probeProcess.StartTime }
            $probeDeadline = (Get-Date).AddSeconds(10)
            while (-not $probeProcess.HasExited) {
                Start-Sleep -Milliseconds 100
                if ($probeMode -ne 'no_refresh') { $probeProcess.Refresh() }
                if ((Get-Date) -ge $probeDeadline) { throw 'Tiny process did not finish in 10 seconds' }
            }
            $null = $probeProcess.WaitForExit(5000)
            if ($probeMode -ne 'no_refresh') { $probeProcess.Refresh() }
            if ($probeProcess.HasExited) { $probeActual = $probeProcess.ExitCode }
        } catch { $probeError = $_.Exception.Message }
        $probeRows += [ordered]@{ mode=$probeMode; expected=$probeExpected; actual=$probeActual; exact=($null -ne $probeActual -and $probeActual -eq $probeExpected); error=$probeError; handle_acquired=$probeHandleAcquired; process_id=$probeProcess.Id; exited=$probeProcess.HasExited }
        if ($null -ne $probeProcess) { $probeProcess.Dispose() }
    }
}
$probeResult = [ordered]@{ schema='native-gate-process-exit-probe/v1'; powershell=$PSVersionTable.PSVersion.ToString(); clr=$PSVersionTable.CLRVersion.ToString(); com_executed=$false; model_executed=$false; rows=$probeRows }
$probeJson = $probeResult | ConvertTo-Json -Depth 8
[IO.File]::WriteAllText((Join-Path $probeOutput 'result.json'),$probeJson,(New-Object Text.UTF8Encoding($false)))
$probeJson
