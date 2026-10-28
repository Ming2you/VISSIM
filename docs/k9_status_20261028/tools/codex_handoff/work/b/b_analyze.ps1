# B analysis driver (Windows PowerShell 5.1), started detached by WMI at BELOW_NORMAL (children inherit it). New 2026-10-27 KST.
# Runs the COMPARE_RULE_B s7.5 steps that were not yet run, with the pinned tools unchanged (sha256 checked against PINS_B
# before every step), python -B, PYTHONHASHSEED=0, PYTHONDONTWRITEBYTECODE=1, OMP/OPENBLAS/MKL threads 1, one step at a time.
# Already run earlier by b_ana_seed.ps1 (same pins): vhr_scan_b (all 9 slots), walltimes, ramp_fc, rm_exec (exit 1, no LDP),
# dec_extract, a1_fzp_firstdiff. Not re-run here.
# Chains (a failed step stops only its own chain; later chains still run; failures are recorded, tools are never changed):
#   A: vhr_firstseen_b.py (9 slots) -> vhr_v3c3_all_b.py                       (wd vhr_b)
#   B: omega701_recount_b.py scan -> omega701_recount_b.py metrics -> omega\top66.py   (wd omega_b)
#   C<s>: scan_fzp_b_s<s>.py nc -> scan_fzp_b_s<s>.py joint -> metrics_b_s<s>.py       (wd rawcheck_b\s<s>), s = 31, 41, 43
# v2 (2026-10-27 01:08 KST): v1 (2ae30018...) stopped silently between a finished python step (C31 scan joint, output written)
# and its 'step end' note; most likely Add-Content was refused while a reader (tail -f) held the state file open, and
# $ErrorActionPreference Stop ended the script. Note now appends with retries and never throws. -Chains picks chains,
# -Tag names the state/log files (default 'full'). Steps, tools, args and environment are unchanged.
param([string[]]$Chains = @(), [string]$Tag = 'full')
$ErrorActionPreference = 'Stop'
$Chains = @($Chains | ForEach-Object { $_ -split ',' } | Where-Object { $_ })   # -File passes "C31,C41" as one string
$CH ='C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff'
$CW = Join-Path $CH 'work'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$state = Join-Path $CW ('b\ana_' + $Tag + '.state.txt')
function Note([string]$m) {
  $line = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST ' + $m + "`r`n"
  for ($i = 0; $i -lt 40; $i++) {
    try { [IO.File]::AppendAllText($state, $line, (New-Object Text.UTF8Encoding($false))); return } catch { Start-Sleep -Milliseconds 500 }
  }
}
$pins = @{}
foreach ($l in (Get-Content -LiteralPath (Join-Path $CH 'b\PINS_B.sha256'))) {
  if ($l -match '^([0-9a-f]{64}) \*?(.+)$') { $pins[($Matches[2] -replace '/', '\')] = $Matches[1] }
}
foreach ($k in @('PYTHONPATH','PYTHONHOME','PYTHONSTARTUP','PYTHONOPTIMIZE','PYTHONWARNINGS')) { Remove-Item -LiteralPath ('Env:' + $k) -ErrorAction SilentlyContinue }
$env:PYTHONHASHSEED = '0'; $env:PYTHONDONTWRITEBYTECODE = '1'; $env:PYTHONUTF8 = '1'
$env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'
$tags9 = @('va_s31','nc3_s31','j1_s31','va_s41','nc3_s41','j1_s41','va_s43','nc3_s43','j1_s43')
$chainDef = [ordered]@{}
$chainDef['A'] = @( ,@('vhr_b', 'vhr_b\vhr_firstseen_b.py', $tags9, 'firstseen') )
$chainDef['A'] += ,@('vhr_b', 'vhr_b\vhr_v3c3_all_b.py', @(), 'v3c3all')
$chainDef['B'] = @( ,@('omega_b', 'omega_b\omega701_recount_b.py', @('scan'), 'omega_scan') )
$chainDef['B'] += ,@('omega_b', 'omega_b\omega701_recount_b.py', @('metrics'), 'omega_metrics')
$chainDef['B'] += ,@('omega_b', 'omega\top66.py', @(), 'top66')
foreach ($s in 31, 41, 43) {
  $rd = 'rawcheck_b\s' + $s
  $chainDef['C' + $s] = @( ,@($rd, ($rd + '\scan_fzp_b_s' + $s + '.py'), @('nc'), ('scan_nc_s' + $s)) )
  $chainDef['C' + $s] += ,@($rd, ($rd + '\scan_fzp_b_s' + $s + '.py'), @('joint'), ('scan_joint_s' + $s))
  $chainDef['C' + $s] += ,@($rd, ($rd + '\metrics_b_s' + $s + '.py'), @(), ('metrics_s' + $s))
}
Note ($Tag + " start chains=" + ($Chains -join ',') + " pid=" + $PID + " priority=" + (Get-Process -Id $PID).PriorityClass)
$failed = @()
foreach ($cn in @($chainDef.Keys)) {
  if ($Chains.Count -and ($Chains -notcontains $cn)) { continue }
  foreach ($st in $chainDef[$cn]) {
    $wd = Join-Path $CW $st[0]; $tool = Join-Path $CW $st[1]; $args2 = $st[2]; $lab = $st[3]
    $rel = 'work\' + $st[1]
    $h = (Get-FileHash -LiteralPath $tool -Algorithm SHA256).Hash.ToLowerInvariant()
    if (-not $pins.ContainsKey($rel) -or $pins[$rel] -ne $h) { Note ("STOP pin mismatch " + $rel + " " + $h); exit 2 }
    $log = Join-Path $CW ('b\ana_' + $Tag + '_' + $lab + '.out.txt')
    Note ("step start chain=" + $cn + " " + $rel + " sha=" + $h.Substring(0, 16) + " wd=" + $wd + " args=" + ($args2 -join ' '))
    $t0 = Get-Date
    $al = @('-B', ('"' + $tool + '"')) + @($args2 | ForEach-Object { '"' + $_ + '"' })
    $p = Start-Process -FilePath $PY -ArgumentList $al -WorkingDirectory $wd -NoNewWindow -Wait -PassThru `
          -RedirectStandardOutput $log -RedirectStandardError ($log + '.err')
    $code = $p.ExitCode
    Note ("step end chain=" + $cn + " " + $rel + " exit=" + $code + " sec=" + [math]::Round(((Get-Date) - $t0).TotalSeconds, 1) + " out=" + $log)
    if ($code -ne 0) { Note ("CHAIN_STOP chain=" + $cn + " step failed " + $rel); $failed += $cn; break }
  }
}
if ($failed.Count) { Note ($Tag + " done with failed chains: " + ($failed -join ',')); exit 1 }
Note ($Tag + " done")
exit 0
