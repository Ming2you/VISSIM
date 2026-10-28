# V-A launch of ONE seed (amendment 34 sec.6.1-6.2): WMI detached (Win32_Process.Create), CurrentDirectory = FRZ_K92,
# the exact sec.6.1 line, no priority argument (J1 form).  Seat rule = run_sdmpc_n31.ps1:84-86 for the REQUESTED flag:
# -Flag none needs PC-wide VISSIM <= 3 and dev = 0; -Flag dev (-AllowConcurrentDev) needs total <= 2 and dev <= 1;
# otherwise WAIT (no launch, exit 3).  Kills nothing.  Never launches twice (run folder, record line, done marker).
# Writes the record line to RVA\wmi_launch_lines.txt and VA\launch\wmi_launch_lines.txt, and the cmd PID with its
# creation time to VA\launch\launch_s<Seed>.json (for the monitor / the s43 watcher targets).
param([Parameter(Mandatory=$true)][ValidateSet(31, 41, 43)][int]$Seed,
      [Parameter(Mandatory=$true)][ValidateSet('none', 'dev')][string]$Flag)
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$frz = 'D:\VISSIM-merge\frozen\sdmpc31_c20aff1d_202610230833'
$rva = 'D:\VISSIM_runs\20261023_sdmpc31_k92'
$name = 'sdmpc31_v3c3_k92va_s{0}' -f $Seed
$record = Join-Path $rva 'wmi_launch_lines.txt'
$done = Join-Path $here ('launch_s{0}.done' -f $Seed)
if (Test-Path -LiteralPath (Join-Path $rva $name)) { Write-Output "STOP run name folder already exists: $name"; exit 2 }
if ((Test-Path -LiteralPath $record) -and ((Get-Content -LiteralPath $record -Raw -Encoding UTF8) -match [regex]::Escape("-Name $name "))) { Write-Output "STOP already recorded in $record"; exit 2 }
if (Test-Path -LiteralPath $done) { Write-Output "STOP $done exists (never launch twice)"; exit 2 }
$devPattern = 'obs150|sdmpc|probe'
$procs = @(Get-Process -Name 'VISSIM*' -ErrorAction SilentlyContinue)
$total = $procs.Count
$dev = @($procs | Where-Object { $_.MainWindowTitle -match $devPattern }).Count
if ($Flag -eq 'none') {
  if (-not ($total -le 3 -and $dev -eq 0)) { Write-Output ("WAIT seats total={0} dev={1} (flag none needs total<=3, dev=0)" -f $total, $dev); exit 3 }
  $flagArg = ''; $flagText = 'none'
} else {
  if (-not ($total -le 2 -and $dev -le 1)) { Write-Output ("WAIT seats total={0} dev={1} (-AllowConcurrentDev needs total<=2, dev<=1)" -f $total, $dev); exit 3 }
  $flagArg = ' -AllowConcurrentDev'; $flagText = '-AllowConcurrentDev'
}
$cmd = 'cmd.exe /c set "PYTHONHASHSEED=0" && powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\VISSIM-merge\tools\run_sdmpc_n31.ps1 -Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2.json -Name ' + $name + ' -SimPeriod 9000 -Seed ' + $Seed + ' -Controller wu-link -RunsRoot D:\VISSIM_runs\20261023_sdmpc31_k92' + $flagArg + ' > D:\VISSIM_runs\20261023_sdmpc31_k92\wmi_' + $name + '.log 2>&1'
New-Item -ItemType File -Path $done | Out-Null
$t = Get-Date
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $frz }
$line = '{0}  k92va_s{8}  RV={1} PID={2} VISSIM_before={3} dev_before={4} cwd={5} head=c20aff1d flag={6} | {7}' -f $t.ToString('o'), $r.ReturnValue, $r.ProcessId, $total, $dev, $frz, $flagText, $cmd, $Seed
Add-Content -LiteralPath $record -Value $line -Encoding UTF8
Add-Content -LiteralPath (Join-Path $here 'wmi_launch_lines.txt') -Value $line -Encoding UTF8
Set-Content -LiteralPath $done -Value $line -Encoding UTF8
$created = $null; $cwdSeen = $null; $cmdSeen = $null
$cp = Get-CimInstance Win32_Process -Filter ("ProcessId={0}" -f $r.ProcessId) -ErrorAction SilentlyContinue
if ($cp) { $created = $cp.CreationDate.ToString('yyyy-MM-ddTHH:mm:ss.ffffffzzz'); $cmdSeen = $cp.CommandLine }
$lj = [ordered]@{ seed = $Seed; name = $name; pid = $r.ProcessId; created = $created; rv = $r.ReturnValue; flag = $flagText;
  vissim_before = $total; dev_before = $dev; launched_at = $t.ToString('o'); cwd = $frz; command = $cmd;
  command_seen_equal = ($cmdSeen -eq $cmd) }
[IO.File]::WriteAllText((Join-Path $here ('launch_s{0}.json' -f $Seed)), ($lj | ConvertTo-Json -Depth 3))
Write-Output $line
Write-Output ('LAUNCH seed={0} RV={1} PID={2} created={3} command_seen_equal={4}' -f $Seed, $r.ReturnValue, $r.ProcessId, $created, ($cmdSeen -eq $cmd))
