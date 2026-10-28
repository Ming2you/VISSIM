# B run detached launch via WMI (Win32_Process.Create) of b_wrapper.ps1 under pwsh 7 (codex runtime). Windows PowerShell 5.1.
# Same pattern as A1 (D:/VISSIM_runtime/20261025_codex_a1/launch/a1_launch_wmi.ps1, dbcf7048...). Priority Normal (32), hidden.
# Refuses when: COMPARE_RULE_B / PINS_B / FREEZE.json / B config sha differ from the fixed values, STOP exists, C: < 8 GB or
# D: < 8 GB + 8 GB per remaining run, any VISSIM process exists, the receipt of this attempt exists, a native runlog exists
# (attempt 1), or (s41/s43) the previous seed did not finish (SIM_DONE, SIM_SEC=9000, wrapper runner_exit 0).
# Writes a receipt JSON (time, ReturnValue, ProcessId, command line) and one line in work/b/launch_receipts.log.
param([Parameter(Mandatory = $true)][ValidateSet(31, 41, 43)][int]$Seed, [ValidateRange(1, 2)][int]$Attempt = 1)
$ErrorActionPreference = 'Stop'
$W    = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\b'
$SPB  = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\b'
$FRZ  = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\b0\frozen\sdmpc31_a49981ff_202610260258'
$ROOT = 'D:\VISSIM_runs\20261026_codex_b_v3c3'
$RES  = Join-Path $ROOT ('s' + $Seed)
$PWSH = 'C:\Users\TRLAB\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$wrapper = Join-Path $W 'b_wrapper.ps1'
$NAME = 'sdmpc31_sdmpc9000_s' + $Seed
$fixed = [ordered]@{
  (Join-Path $SPB 'COMPARE_RULE_B.md') = 'f902f7f0013bed0a0eb5dec27818e2bda4851995eae235130b7cb241e8b28f0c';
  (Join-Path $SPB 'PINS_B.sha256')     = '5e8ffbc5cc192c25a15a07c11dda5036c7005b73c342aa16d1f7d6ed5e67d804';
  (Join-Path $FRZ 'FREEZE.json')       = '853d1c4fb97ed3de4cf62a409b06b9001648ce56171e2ed826236bdddb1506c6';
  (Join-Path $FRZ 'diagnostics\b0_v3c3\config_b0_v3c3.json') = '729640af754a90c8d7fbe8f81577b27bae02b86f1d504e18333c0fc99717f983' }
$shaSeen = [ordered]@{}
foreach ($p in $fixed.Keys) {
  $h = (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant(); $shaSeen[$p] = $h
  if ($h -ne $fixed[$p]) { throw "fixed file changed: $p $h" }
}
if (Test-Path -LiteralPath (Join-Path $ROOT 'STOP')) { throw 'STOP exists (B root)' }
if (Test-Path -LiteralPath (Join-Path $RES 'STOP')) { throw 'STOP exists (seed root)' }
$remaining = @{ 31 = 3; 41 = 2; 43 = 1 }[$Seed]
$c = [math]::Round((Get-PSDrive C).Free / 1GB, 1); $d = [math]::Round((Get-PSDrive D).Free / 1GB, 1)
if ($c -lt 8 -or $d -lt (8 + 8 * $remaining)) { throw "disk too low: C=$c D=$d (need C>=8, D>=$(8 + 8 * $remaining))" }
$vis = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^Vissim' })
if ($vis.Count) { throw ('VISSIM running, no launch: ' + (($vis | ForEach-Object { $_.ProcessId }) -join ',')) }
$rec = Join-Path $RES 'b_launch'
$receipt = Join-Path $rec ('wmi_launch_run' + $Attempt + '.json')
if (Test-Path -LiteralPath $receipt) { throw "launch receipt exists, no second launch: $receipt" }
$runlog = Join-Path $RES ('sdmpc\runlog_' + $NAME + '.txt')
if (Test-Path -LiteralPath $runlog) { throw "native runlog exists: $runlog" }
if ($Attempt -eq 2) {
  if (-not (Test-Path -LiteralPath (Join-Path $rec 'wmi_launch_run1.json'))) { throw 'attempt 2 needs attempt 1 receipt' }
  $done1 = (Test-Path -LiteralPath (Join-Path $rec 'wrapper_run1_end.json')) -or (Test-Path -LiteralPath (Join-Path $rec 'wrapper_run1_error.json'))
  if (-not $done1) { throw 'attempt 1 wrapper has not ended' }
}
if ($Seed -ne 31) {
  $prev = @{ 41 = 31; 43 = 41 }[$Seed]
  $pres = Join-Path $ROOT ('s' + $prev)
  $plog = Join-Path $pres ('sdmpc\runlog_sdmpc31_sdmpc9000_s' + $prev + '.txt')
  if (-not (Test-Path -LiteralPath $plog)) { throw "previous seed runlog missing: $plog" }
  $pt = Get-Content -LiteralPath $plog -Raw
  if ($pt -notmatch '(?m)^STAGE=SIM_DONE\r?$' -or $pt -notmatch '(?m)^SIM_SEC=9000\r?$') { throw "previous seed s$prev not SIM_DONE / SIM_SEC=9000" }
  $pends = @(Get-ChildItem -LiteralPath (Join-Path $pres 'b_launch') -Filter 'wrapper_run*_end.json' | Sort-Object Name)
  if (-not $pends.Count -or (Get-Content -LiteralPath $pends[-1].FullName -Raw | ConvertFrom-Json).runner_exit -ne 0) { throw "previous seed s$prev wrapper did not end with runner_exit 0" }
}
New-Item -ItemType Directory -Force -Path $rec | Out-Null
$cmd = '"' + $PWSH + '" -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $wrapper + '" -Seed ' + $Seed + ' -Attempt ' + $Attempt
$prio = [uint32]32   # NORMAL_PRIORITY_CLASS (PRE_B s1)
$startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = $prio; ShowWindow = [uint16]0 }
$before = [DateTimeOffset]::Now.ToString('o')
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $FRZ; ProcessStartupInformation = $startup }
$o = [ordered]@{ seed = $Seed; attempt = $Attempt; time_before_create = $before; time_after_create = [DateTimeOffset]::Now.ToString('o');
  ReturnValue = [int]$r.ReturnValue; ProcessId = [int]$r.ProcessId; CommandLine = $cmd; CurrentDirectory = $FRZ;
  PriorityClass = $prio; launcher_pid = $PID; launcher_ps = $PSVersionTable.PSVersion.ToString(); vissim_pids_at_launch = @($vis | ForEach-Object { [int]$_.ProcessId });
  disk_free_gb = [ordered]@{ C = $c; D = $d }; fixed_sha256 = $shaSeen;
  wrapper_sha256 = (Get-FileHash -LiteralPath $wrapper -Algorithm SHA256).Hash.ToLowerInvariant();
  launcher_sha256 = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant() }
($o | ConvertTo-Json -Depth 5) | Set-Content -Encoding UTF8 -LiteralPath $receipt
((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST seed=' + $Seed + ' attempt=' + $Attempt + ' ReturnValue=' + $r.ReturnValue + ' ProcessId=' + $r.ProcessId + ' Command=' + $cmd) |
  Add-Content -Encoding UTF8 -LiteralPath (Join-Path $W 'launch_receipts.log')
$o | ConvertTo-Json -Depth 5
