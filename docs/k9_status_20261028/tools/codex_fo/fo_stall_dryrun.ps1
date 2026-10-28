# Dry run of fo_stall_stop.ps1 (2026-10-27 KST, PRE_FO s7). Windows PowerShell 5.1, ASCII only. No process is read or stopped:
# every case uses -Fake (idle seconds and CPU samples from a JSON) on a root under fo\dryrun with fake launcher records.
# Cases: S1 not idle; S2 idle but CPU rising (slow but progressing); S3 idle and CPU flat, -Action check (report only);
# S4 run 1 stalled, -Action stop (stall record + rename to s31_try1_stalled); S5 run 2 stalled (record, no rename);
# S6 a second stop on the same run (record exists -> nothing); S7 the try already ended (tryend) -> not active.
# Results are appended to fo/fo_stall_dryrun.log.
$ErrorActionPreference = 'Stop'
$SPF = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\fo'
$T = Join-Path $SPF 'fo_stall_stop.ps1'
$OUT = Join-Path $SPF 'fo_stall_dryrun.log'
$RUN = Join-Path $SPF ('dryrun\stall_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
$UTF8 = New-Object System.Text.UTF8Encoding $false
function W([string]$m) { [IO.File]::AppendAllText($OUT, $m + "`r`n", $UTF8) }
function J([string]$p, $o) { New-Item -ItemType Directory -Force -Path (Split-Path -Parent $p) | Out-Null; [IO.File]::WriteAllText($p, ($o | ConvertTo-Json -Depth 5), $UTF8) }
$cases = @(
  @{ name = 'S1_not_idle'; a = 1; act = 'stop'; fake = @{ idle_sec = 120; cpu1 = 10; cpu2 = 10; pids = @(1) }; want = 'NOT_IDLE'; marker = $false; renamed = $false },
  @{ name = 'S2_slow_but_progressing'; a = 1; act = 'stop'; fake = @{ idle_sec = 700; cpu1 = 10; cpu2 = 60; pids = @(1, 2) }; want = 'SLOW_BUT_PROGRESSING'; marker = $false; renamed = $false },
  @{ name = 'S3_check_only'; a = 1; act = 'check'; fake = @{ idle_sec = 700; cpu1 = 10; cpu2 = 10.4; pids = @(1, 2) }; want = 'STALLED_CHECK_ONLY'; marker = $false; renamed = $false },
  @{ name = 'S4_run1_stop'; a = 1; act = 'stop'; fake = @{ idle_sec = 700; cpu1 = 10; cpu2 = 10.4; pids = @(1, 2) }; want = 'STOPPED'; marker = $true; renamed = $true },
  @{ name = 'S5_run2_stop'; a = 2; act = 'stop'; fake = @{ idle_sec = 700; cpu1 = 10; cpu2 = 10.0; pids = @(3) }; want = 'STOPPED'; marker = $true; renamed = $false },
  @{ name = 'S6_second_stop'; a = 1; act = 'stop'; pre_marker = $true; fake = @{ idle_sec = 700; cpu1 = 10; cpu2 = 10.0; pids = @(1) }; want = 'STALL_RECORD_EXISTS'; marker = $true; renamed = $false },
  @{ name = 'S7_try_ended'; a = 1; act = 'stop'; tryend = $true; fake = @{ idle_sec = 700; cpu1 = 10; cpu2 = 10.0; pids = @(1) }; want = 'NOT_ACTIVE'; marker = $false; renamed = $false }
)
W ('==== stall dry run ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST run_dir=' + $RUN)
W ('tool sha256=' + (Get-FileHash -LiteralPath $T -Algorithm SHA256).Hash.ToLowerInvariant() + ' harness sha256=' + (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant())
$vis0 = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^Vissim' } | ForEach-Object { $_.ProcessId }) -join ','
W ('PC VISSIM before=[' + $vis0 + ']')
$nPass = 0; $nFail = 0
foreach ($c in $cases) {
  $root = Join-Path (Join-Path $RUN $c.name) 'root'; $LD = Join-Path $root '_launcher'
  New-Item -ItemType Directory -Force -Path (Join-Path $root 's31\sdmpc') | Out-Null
  if ($c.a -eq 2) { New-Item -ItemType Directory -Force -Path (Join-Path $root 's31_try1_stalled') | Out-Null; J (Join-Path $LD 'launched_s31_run1_try1.json') @{ key = 's31_run1_try1' }; J (Join-Path $LD 'tryend_s31_run1_try1.json') @{ status = 'stalled_handled' }; J (Join-Path $LD 'stalled_s31_run1.json') @{ by = 'test' } }
  $key = 's31_run' + $c.a + '_try1'
  J (Join-Path $LD ('launched_' + $key + '.json')) @{ key = $key }
  J (Join-Path $LD ('receipt_' + $key + '.json')) @{ key = $key; ProcessId = 999999; wrapper_creation_ticks = '0' }
  if ($c.ContainsKey('tryend')) { J (Join-Path $LD ('tryend_' + $key + '.json')) @{ status = 'completed' } }
  if ($c.ContainsKey('pre_marker')) { J (Join-Path $LD ('stalled_s31_run' + $c.a + '.json')) @{ by = 'earlier' } }
  $fp = Join-Path (Join-Path $RUN $c.name) 'fake.json'; J $fp $c.fake
  $res1 = (& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $T -Seed 31 -Action $c.act -Root $root -Fake $fp) | Select-Object -Last 1
  $mk = Test-Path -LiteralPath (Join-Path $LD ('stalled_s31_run' + $c.a + '.json'))
  $ren = Test-Path -LiteralPath (Join-Path $root 's31_try1_stalled')
  if ($c.a -eq 2) { $ren = -not (Test-Path -LiteralPath (Join-Path $root 's31')) }
  $bad = @()
  if ([string]$res1 -ne $c.want) { $bad += ('out got=' + $res1 + ' want=' + $c.want) }
  if ($mk -ne $c.marker) { $bad += ('marker got=' + $mk + ' want=' + $c.marker) }
  if ($ren -ne $c.renamed) { $bad += ('renamed got=' + $ren + ' want=' + $c.renamed) }
  if ($bad.Count) { $nFail++; W ('CASE ' + $c.name + ' FAIL :: ' + ($bad -join ' | ')) } else { $nPass++; W ('CASE ' + $c.name + ' PASS out=' + $res1) }
  $lg = Join-Path $root 'fo_stall_stop.log'; if (Test-Path -LiteralPath $lg) { W ((Get-Content -LiteralPath $lg -Raw -Encoding UTF8).TrimEnd()) }
}
$vis1 = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^Vissim' } | ForEach-Object { $_.ProcessId }) -join ','
W ('PC VISSIM after=[' + $vis1 + ']')
W ('SUMMARY pass=' + $nPass + ' fail=' + $nFail + ' run_dir=' + $RUN)
'SUMMARY pass=' + $nPass + ' fail=' + $nFail + ' run_dir=' + $RUN
