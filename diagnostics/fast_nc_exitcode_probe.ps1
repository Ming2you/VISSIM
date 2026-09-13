param([Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference='Stop'
if (Test-Path -LiteralPath $Output) { throw 'Require new probe output' }
$null=New-Item -ItemType Directory -Path $Output
$rows=@()
foreach ($capture in @($false,$true)) {
  foreach ($expected in @(0,7)) {
    $name=('{0}_{1}' -f $capture,$expected)
    $arguments='//nologo "{0}" {1}' -f (Join-Path $PSScriptRoot 'fast_nc_exitcode_probe.vbs'),$expected
    $child=Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\cscript.exe') -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $Output ($name+'.out')) -RedirectStandardError (Join-Path $Output ($name+'.err'))
    if ($capture) { $handle=$child.Handle }
    $start=$child.StartTime
    while (-not $child.HasExited) { Start-Sleep -Milliseconds 50; $child.Refresh() }
    $child.WaitForExit()
    $rows += [pscustomobject]@{capture_handle=$capture;expected=$expected;actual=$child.ExitCode;pid=$child.Id;start=$start.ToString('o')}
    $child.Dispose()
  }
}
$rows | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Output 'result.json') -Encoding UTF8
$rows | ConvertTo-Json
if (@($rows | Where-Object { $_.capture_handle -and ($null -eq $_.actual -or $_.actual -ne $_.expected) }).Count) { exit 1 }
