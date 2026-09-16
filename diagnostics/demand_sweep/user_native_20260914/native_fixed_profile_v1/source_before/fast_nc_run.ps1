param(
  [Parameter(Mandatory=$true)][string]$Prepared,
  [Parameter(Mandatory=$true)][string]$Output,
  [ValidateRange(1,2147483647)][int]$Seed = 13,
  [switch]$Execute
)
$ErrorActionPreference = 'Stop'
$preparedPath = (Resolve-Path -LiteralPath $Prepared).Path
$settings = Get-Content -LiteralPath (Join-Path $preparedPath 'prepared.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if (@(5400,7200,9000) -notcontains $settings.terminal_sec) { throw 'Prepared terminal_sec must be5400,7200 or9000' }
$terminalSec = [int]$settings.terminal_sec
$nativePreserve = $settings.mode -eq 'native_preserve'
if ($nativePreserve) {
  if ($PSBoundParameters.ContainsKey('Seed') -and $Seed -ne [int]$settings.seed) { throw 'Native-preserve cannot override saved seed' }
  $Seed = [int]$settings.seed
  foreach ($entry in $settings.snapshot_sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath $entry.Name -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value) { throw 'Native snapshot changed before launch' }
  }
}
$network = (Resolve-Path -LiteralPath $settings.network).Path
$outputPath = [IO.Path]::GetFullPath($Output)
$script = Join-Path $PSScriptRoot 'fast_nc_runner.vbs'
$cscript = Join-Path $env:SystemRoot 'System32\cscript.exe'
foreach ($p in @($network,$preparedPath,$outputPath,$script)) {
  if ($p.Contains('"') -or $p.Contains("`n") -or $p.Contains("`r")) { throw 'Invalid argument path' }
}
$arguments = '//nologo "{0}" "{1}" "{2}" "{3}" {4} {5}' -f $script,$network,$preparedPath,$outputPath,$Seed,$terminalSec
if ($nativePreserve) { $arguments += ' native_preserve' }
if (-not $Execute) {
  [pscustomobject]@{execute=$false; program=$cscript; arguments=$arguments; startup_no_progress_sec=300;
    controller='none'; vehicle_queries=0; initial_native_steps=$(if ($nativePreserve) {0} else {1}); continuous_calls=1; terminal_sec=$terminalSec; native_preserve=$nativePreserve} | ConvertTo-Json
  exit 0
}
if (Test-Path -LiteralPath $outputPath) { throw 'Require a new output directory' }
if (@(Get-Process -Name 'VISSIM*' -ErrorAction SilentlyContinue).Count) { throw 'Existing VISSIM instance: do not share ownership' }
$null = New-Item -ItemType Directory -Path $outputPath
$evalPath = Join-Path $outputPath 'vissim_eval'
$null = New-Item -ItemType Directory -Path $evalPath
$stdout = Join-Path $outputPath 'stdout.txt'
$stderr = Join-Path $outputPath 'stderr.txt'
$started = Get-Date
$runner = Start-Process -FilePath $cscript -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
# Retain the OS handle before HasExited/Refresh: Windows PowerShell otherwise
# loses ExitCode for Start-Process children even after WaitForExit (0 and7 tested).
$runnerHandle = $runner.Handle
$runnerStart = $runner.StartTime
$owned = $null
$progress = $false
$timedOut = $false
$lastSim = $null
$record = [ordered]@{network=$network; prepared=$preparedPath; output=$outputPath; seed=$Seed; requested_terminal_sec=$terminalSec;
  cscript_pid=$runner.Id; cscript_start=$runnerStart.ToString('o'); vissim=$null;
  started=$started.ToString('o'); first_native_progress=$null; completed=$false; error=$null}
$record.native_preserve=$nativePreserve
$record.runner_sha256=(Get-FileHash -LiteralPath $script -Algorithm SHA256).Hash.ToLowerInvariant()
function Save-Receipt {
  $record | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $outputPath 'run.json') -Encoding UTF8
}
function Last-Fzp-Time([string]$Path) {
  $stream = $null
  try {
    $stream = [IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
    $size = [int][Math]::Min(65536,$stream.Length)
    $null = $stream.Seek(-$size,[IO.SeekOrigin]::End)
    $bytes = New-Object byte[] $size
    $read = $stream.Read($bytes,0,$size)
    $lines = [Text.Encoding]::ASCII.GetString($bytes,0,$read) -split "`n"
    # Ignore both potentially partial edge lines; require a complete data row.
    for ($i=$lines.Length-2; $i -ge 1; $i--) {
      if ($lines[$i] -match '^([0-9]+\.[0-9]+);[0-9]+;[0-9]+;[0-9]+;') {
        return [double]::Parse($Matches[1],[Globalization.CultureInfo]::InvariantCulture)
      }
    }
  } catch [IO.IOException] { return $null }
  finally { if ($null -ne $stream) { $stream.Dispose() } }
  return $null
}
Save-Receipt
while (-not $runner.HasExited) {
  if ($null -eq $owned) {
    $new = @(Get-Process -Name 'VISSIM*' -ErrorAction SilentlyContinue | Where-Object {
      $_.StartTime -ge $started -and $_.MainWindowTitle.IndexOf([IO.Path]::GetFileName($network),[StringComparison]::OrdinalIgnoreCase) -ge 0
    })
    if ($new.Count -eq 1) {
      $owned = [pscustomobject]@{pid=$new[0].Id; start=$new[0].StartTime}
      $record.vissim = @{pid=$owned.pid;start=$owned.start.ToString('o')}; Save-Receipt
    }
  }
  if (-not $progress) {
    foreach ($file in @(Get-ChildItem -LiteralPath $evalPath -Filter '*.fzp' -File)) {
      $lastSim = Last-Fzp-Time $file.FullName
      if ($null -ne $lastSim -and $lastSim -gt $(if ($nativePreserve) {0} else {1})) {
        $progress = $true; $record.first_native_progress=@{sim_sec=$lastSim; at=(Get-Date).ToString('o')}; Save-Receipt
      }
    }
    if (-not $progress -and ((Get-Date)-$started).TotalSeconds -ge 300) {
      $timedOut=$true; $record.error='Startup300s: no complete FZP data timestamp showing actual native progression'
      # Exact PID + creation-time identity only. Unknown servers are never killed.
      $identities=@([pscustomobject]@{pid=$runner.Id;start=$runnerStart})
      if ($null -ne $owned) { $identities += $owned }
      foreach ($identity in $identities) {
        $current=Get-Process -Id $identity.pid -ErrorAction SilentlyContinue
        if ($current -and $current.StartTime -eq $identity.start) { Stop-Process -Id $current.Id -Force }
      }
      break
    }
  }
  Start-Sleep -Seconds 2
  $runner.Refresh()
}
$runner.WaitForExit()
$record.exit_code=$runner.ExitCode
$deadline=(Get-Date).AddSeconds(20)
do {
  $native=$null
  if ($null -ne $owned) { $native=Get-Process -Id $owned.pid -ErrorAction SilentlyContinue }
  if (-not $native -or $native.StartTime -ne $owned.start) { break }
  Start-Sleep -Milliseconds 500
} while ((Get-Date) -lt $deadline)
$record.owned_native_alive=($null -ne $native -and $native.StartTime -eq $owned.start)
$stem=[IO.Path]::GetFileNameWithoutExtension($network)
foreach ($file in Get-ChildItem -LiteralPath ([IO.Path]::GetDirectoryName($network)) -Filter '*.err' -File) {
  if ($file.Name -match ('^'+[regex]::Escape($stem)+'(?:_\d+)?\.err$') -and $file.LastWriteTime -ge $started) {
    Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $outputPath $file.Name)
  }
}
$log=Get-Content -LiteralPath $stdout -Raw
$record.native_files=@(Get-ChildItem -LiteralPath $evalPath -File | ForEach-Object { @{name=$_.Name;bytes=$_.Length} })
$fzp=@(Get-ChildItem -LiteralPath $evalPath -Filter '*.fzp' -File | Where-Object Length -gt 0)
$lsa=@(Get-ChildItem -LiteralPath $evalPath -Filter '*.lsa' -File | Where-Object Length -gt 0)
$terminalPattern = '(?m)^SIM_SEC=' + $terminalSec + '\r?$'
$record.completed=(!$timedOut -and $runner.ExitCode -eq 0 -and !$record.owned_native_alive -and $log -match $terminalPattern -and $log -match '(?m)^STAGE=SIM_DONE\r?$' -and $fzp.Count -eq 1 -and $lsa.Count -eq 1)
if ($null -eq $owned -and @(Get-Process -Name 'VISSIM*' -ErrorAction SilentlyContinue).Count) {
  $record.completed=$false; $record.error='Native identity was not established and a VISSIM process remains'
}
$record.terminal_sec=if ($log -match $terminalPattern) { $terminalSec } else { $null }
$record.stdout=$stdout; $record.stderr=$stderr
$record.error_files=@(Get-ChildItem -LiteralPath $outputPath -Filter '*.err' -File | ForEach-Object { @{name=$_.Name;bytes=$_.Length} })
$record.finished=(Get-Date).ToString('o'); Save-Receipt
$record | ConvertTo-Json -Depth 6
if (-not $record.completed) { exit 1 }
