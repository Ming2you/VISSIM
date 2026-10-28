# FO analysis step runner (COMPARE_RULE_FO s7; Windows PowerShell 5.1, started detached by WMI at BELOW_NORMAL; children inherit).
# Derived from codex_handoff/work/b/b_ana_seed.ps1 (737ffc60..., the B step runner). Differences: tools are the FO copies and
# the FO tools pinned in fo/PINS_FO.sha256 (paths relative to the k8 folder); every job that reads an FZP runs under the shared
# heavy lock D:\VISSIM-merge\k8_gate_trees\heavy.lock (exclusive create, retry 30 s, give up after 60 min -> STOP; delete only
# our own token; 25 s pause after release); one FZP job = one lock. Light jobs (decision files, caches, tables) run without it.
# Each tool's sha256 is checked against PINS_FO before it runs; a tool that exits != 0 stops the plan (no tool change: X6).
# Env: python -B, PYTHONHASHSEED=0, PYTHONDONTWRITEBYTECODE=1, OMP/OPENBLAS/MKL threads 1. Writes ana_<plan>[_s<seed>].state.txt.
#  -Plan prescan          NC3 / V-A only (allowed before FO data, as B s7.5): vhr_scan_fo + vhr_firstseen_fo (nc3, va x3),
#                         omega701_recount_fo scan (nc3, va x3, lnc_64cf_s29), scan_fzp_fo_s<s> nc (x3)
#  -Plan stage -Seed S    after the FO run of S ended: rb_readback (fo<S>), walltimes / ramp_fc (wd rawcheck_fo/s<S>),
#                         dec_extract_fo s<S> (wd rawcheck_fo), heavy: vhr_scan_fo j1_s<S>, vhr_firstseen_fo j1_s<S>,
#                         omega701_recount_fo scan j1_s<S>, scan_fzp_fo_s<S> joint, a1_fzp_firstdiff_fo_s<S>, fwe_scan fo_s<S>;
#                         then fo_run_check.py <S>
#  -Plan final            vhr_v3c3_all_fo, omega701_recount_fo metrics, top66 (wd omega_fo), metrics_fo_s<s> x3, fo_fwe.py run,
#                         fo_tables.py
param([Parameter(Mandatory = $true)][ValidateSet('prescan', 'stage', 'final')][string]$Plan,
      [ValidateSet(0, 31, 41, 43)][int]$Seed = 0)
$ErrorActionPreference = 'Stop'
$SP = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8'
$CW = Join-Path $SP 'codex_handoff\work'
$FA = Join-Path $SP 'codex_handoff\fo\work\ana'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$LOCK = 'D:\VISSIM-merge\k8_gate_trees\heavy.lock'
$FORUN = 'D:\VISSIM_runs\20261028_codex_fo_v3c3'
if ($Plan -eq 'stage' -and $Seed -eq 0) { throw 'stage needs -Seed' }
$tagp = $Plan; if ($Seed) { $tagp = $Plan + '_s' + $Seed }
$state = Join-Path $FA ('ana_' + $tagp + '.state.txt')
if (Test-Path -LiteralPath $state) { throw ('plan already started once: ' + $state) }
$TOKEN = 'fo_ana-' + $PID + '-' + [guid]::NewGuid().ToString('N')
$script:haveLock = $false
function Note([string]$m) { ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST ' + $m) | Add-Content -Encoding UTF8 -LiteralPath $state }
function Release-Lock {
  if (-not $script:haveLock) { return }
  try { $t = [IO.File]::ReadAllText($LOCK); if ($t -like ('*' + $TOKEN + '*')) { Remove-Item -LiteralPath $LOCK -Force; Note 'lock released (own token)' } else { Note 'lock NOT released: token differs' } } catch { Note ('lock release error: ' + [string]$_) }
  $script:haveLock = $false
  Start-Sleep -Seconds 25
}
function Acquire-Lock([string]$job) {
  $t0 = Get-Date
  while ($true) {
    try {
      $fs = [IO.File]::Open($LOCK, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
      $body = '{"owner": "fo_ana", "pid": ' + $PID + ', "token": "' + $TOKEN + '", "started_kst": "' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST", "job": "' + $job + '"}'
      $b = (New-Object System.Text.UTF8Encoding $false).GetBytes($body); $fs.Write($b, 0, $b.Length); $fs.Dispose()
      $script:haveLock = $true; Note ('lock acquired for ' + $job + ' after ' + [int]((Get-Date) - $t0).TotalSeconds + ' s'); return $true
    } catch {
      if (((Get-Date) - $t0).TotalMinutes -gt 60) { return $false }
      Start-Sleep -Seconds 30
    }
  }
}
$pins = @{}
foreach ($l in (Get-Content -LiteralPath (Join-Path $SP 'codex_handoff\fo\PINS_FO.sha256'))) {
  if ($l -match '^([0-9a-f]{64}) \*?(.+)$') { $pins[($Matches[2] -replace '/', '\')] = $Matches[1] }
}
foreach ($k in @('PYTHONPATH','PYTHONHOME','PYTHONSTARTUP','PYTHONOPTIMIZE','PYTHONWARNINGS')) { Remove-Item -LiteralPath ('Env:' + $k) -ErrorAction SilentlyContinue }
$env:PYTHONHASHSEED = '0'; $env:PYTHONDONTWRITEBYTECODE = '1'; $env:PYTHONUTF8 = '1'
$env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'
# step = @(work dir (rel to SP), tool (rel to SP), args, heavy 0/1)
$steps = @()
$V = 'codex_handoff\work\vhr_fo'; $O = 'codex_handoff\work\omega_fo'; $R = 'codex_handoff\work\rawcheck_fo'
if ($Plan -eq 'prescan') {
  foreach ($s in 31, 41, 43) { foreach ($t in @(('nc3_s' + $s), ('va_s' + $s))) {
    $steps += ,@($V, ($V + '\vhr_scan_fo.py'), @($t), 1)
    $steps += ,@($V, ($V + '\vhr_firstseen_fo.py'), @($t), 1)
    $steps += ,@($O, ($O + '\omega701_recount_fo.py'), @('scan', $t), 1) } }
  $steps += ,@($O, ($O + '\omega701_recount_fo.py'), @('scan', 'lnc_64cf_s29'), 1)
  foreach ($s in 31, 41, 43) { $steps += ,@(($R + '\s' + $s), ($R + '\s' + $s + '\scan_fzp_fo_s' + $s + '.py'), @('nc'), 1) }
} elseif ($Plan -eq 'stage') {
  $SeedTag = 's' + $Seed; $rd = $R + '\' + $SeedTag
  $steps += ,@('c_port\readback\tools', 'c_port\readback\tools\rb_readback.py', @((Join-Path $FA 'readback'), ('fo' + $Seed + '=' + (Join-Path $FORUN ($SeedTag + '\sdmpc')))), 0)
  $steps += ,@($rd, ($rd + '\walltimes_fo_' + $SeedTag + '.py'), @(), 0)
  $steps += ,@($rd, ($rd + '\ramp_fc_fo_' + $SeedTag + '.py'), @(), 0)
  $steps += ,@($R, ($R + '\dec_extract_fo.py'), @($SeedTag), 0)
  $steps += ,@($V, ($V + '\vhr_scan_fo.py'), @(('j1_' + $SeedTag)), 1)
  $steps += ,@($V, ($V + '\vhr_firstseen_fo.py'), @(('j1_' + $SeedTag)), 1)
  $steps += ,@($O, ($O + '\omega701_recount_fo.py'), @('scan', ('j1_' + $SeedTag)), 1)
  $steps += ,@($rd, ($rd + '\scan_fzp_fo_' + $SeedTag + '.py'), @('joint'), 1)
  $steps += ,@($rd, ($rd + '\a1_fzp_firstdiff_fo_' + $SeedTag + '.py'), @((Join-Path (Join-Path $SP $rd) ('fzp_firstdiff_' + $SeedTag + '.json'))), 1)
  $steps += ,@('rmcause\phys', 'rmcause\phys\fwe_scan.py', @(('fo_' + $SeedTag), (Join-Path $FORUN ($SeedTag + '\sdmpc\vissim_eval\sdmpc31_sdmpc9000_' + $SeedTag + '_001.fzp')), (Join-Path $FA 'fwe')), 1)
  $steps += ,@('codex_handoff\fo\work\ana', 'codex_handoff\fo\work\ana\fo_run_check.py', @([string]$Seed, (Join-Path $FA ('runcheck_' + $SeedTag + '.json'))), 0)
} else {
  $steps += ,@($V, ($V + '\vhr_v3c3_all_fo.py'), @(), 0)
  $steps += ,@($O, ($O + '\omega701_recount_fo.py'), @('metrics'), 0)
  $steps += ,@($O, 'codex_handoff\work\omega\top66.py', @(), 0)
  foreach ($s in 31, 41, 43) { $steps += ,@(($R + '\s' + $s), ($R + '\s' + $s + '\metrics_fo_s' + $s + '.py'), @(), 0) }
  $steps += ,@('codex_handoff\fo\work\ana', 'codex_handoff\fo\work\ana\fo_fwe.py', @('run', (Join-Path $FA 'fo_fwe_out.json')), 0)
  $steps += ,@('codex_handoff\fo\work\ana', 'codex_handoff\fo\work\ana\fo_tables.py', @((Join-Path $FA 'fo_tables_out')), 0)
}
New-Item -ItemType Directory -Force -Path (Join-Path $FA 'readback'), (Join-Path $FA 'fwe'), (Join-Path $FA 'logs') | Out-Null
Note ("plan " + $tagp + " start pid=" + $PID + " priority=" + (Get-Process -Id $PID).PriorityClass + " steps=" + $steps.Count)
$n = 0
foreach ($s in $steps) {
  $n++
  $wd = Join-Path $SP $s[0]; $tool = Join-Path $SP $s[1]; $args2 = $s[2]; $heavy = [int]$s[3]
  $h = (Get-FileHash -LiteralPath $tool -Algorithm SHA256).Hash.ToLowerInvariant()
  if (-not $pins.ContainsKey($s[1]) -or $pins[$s[1]] -ne $h) { Note ("STOP pin mismatch " + $s[1] + " " + $h); exit 2 }
  $log = Join-Path $FA ('logs\ana_' + $tagp + '_' + $n + '_' + [IO.Path]::GetFileNameWithoutExtension($tool) + '.out.txt')
  if ($heavy) { if (-not (Acquire-Lock ('FO analysis ' + $tagp + ' step ' + $n + ' ' + [IO.Path]::GetFileName($tool) + ' ' + ($args2 -join ' ')))) { Note 'STOP heavy lock not acquired within 60 min'; exit 3 } }
  Note ("step start " + $n + " " + $s[1] + " sha=" + $h.Substring(0, 16) + " heavy=" + $heavy + " wd=" + $wd + " args=" + ($args2 -join ' '))
  $t0 = Get-Date
  $al = @('-B', ('"' + $tool + '"')) + @($args2 | ForEach-Object { '"' + $_ + '"' })
  $p = Start-Process -FilePath $PY -ArgumentList $al -WorkingDirectory $wd -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput $log -RedirectStandardError ($log + '.err')
  $code = $p.ExitCode
  Note ("step end " + $n + " " + $s[1] + " exit=" + $code + " sec=" + [math]::Round(((Get-Date) - $t0).TotalSeconds, 1) + " out=" + $log)
  if ($heavy) { Release-Lock }
  if ($code -ne 0) { Note ("STOP step failed " + $s[1]); exit 1 }
}
Note ("plan " + $tagp + " done")
exit 0
