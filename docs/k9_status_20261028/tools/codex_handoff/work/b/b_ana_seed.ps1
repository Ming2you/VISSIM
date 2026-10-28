# B analysis step runner per seed (Windows PowerShell 5.1), started detached by WMI at BELOW_NORMAL (children inherit it).
# Same as b_ana.ps1 (11a7deef...) but the seed is a parameter (b_ana.ps1 only knows s31).
# Runs pinned tools (PINS_B.sha256) one at a time, unchanged, with python -B, PYTHONHASHSEED=0, PYTHONDONTWRITEBYTECODE=1,
# OMP/OPENBLAS/MKL threads 1 (COMPARE_RULE_B s7.5). Verifies each tool's sha256 against PINS_B before running it.
# -Plan prescan -Seed S : vhr_b/vhr_scan_b.py va_sS nc3_sS        (NC3 / V-A slots only; allowed before B data, rule s7.5)
# -Plan stage   -Seed S : walltimes_b_sS, ramp_fc_b_sS, rm_exec_b_sS (wd rawcheck_b/sS), dec_extract_b sS (wd rawcheck_b),
#                         vhr_scan_b j1_sS (prefix sha), a1_fzp_firstdiff_b_sS -> rawcheck_b/sS/fzp_firstdiff_sS.json
# -Plan rest    -Seed S : the stage steps after rm_exec (dec_extract_b sS, vhr_scan_b j1_sS, a1_fzp_firstdiff_b_sS); added 2026-10-27
#                         because rm_exec_b_sS cannot run on B (no LDP file in the B run folder); rm_exec is not re-run or changed.
param([Parameter(Mandatory = $true)][ValidateSet('prescan', 'stage', 'rest')][string]$Plan,
      [Parameter(Mandatory = $true)][ValidateSet(31, 41, 43)][int]$Seed)
$ErrorActionPreference = 'Stop'
$CH = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff'
$CW = Join-Path $CH 'work'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$S = 's' + $Seed
$tagp = $Plan + '_' + $S
$state = Join-Path $CW ('b\ana_' + $tagp + '.state.txt')
function Note([string]$m) { ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST ' + $m) | Add-Content -Encoding UTF8 -LiteralPath $state }
$pins = @{}
foreach ($l in (Get-Content -LiteralPath (Join-Path $CH 'b\PINS_B.sha256'))) {
  if ($l -match '^([0-9a-f]{64}) \*?(.+)$') { $pins[($Matches[2] -replace '/', '\')] = $Matches[1] }
}
foreach ($k in @('PYTHONPATH','PYTHONHOME','PYTHONSTARTUP','PYTHONOPTIMIZE','PYTHONWARNINGS')) { Remove-Item -LiteralPath ('Env:' + $k) -ErrorAction SilentlyContinue }
$env:PYTHONHASHSEED = '0'; $env:PYTHONDONTWRITEBYTECODE = '1'; $env:PYTHONUTF8 = '1'
$env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'
$steps = @()
if ($Plan -eq 'prescan') {
  $steps += ,@('vhr_b', 'vhr_b\vhr_scan_b.py', @(('va_' + $S), ('nc3_' + $S)))
} elseif ($Plan -eq 'rest') {
  $rd = 'rawcheck_b\' + $S
  $steps += ,@('rawcheck_b', 'rawcheck_b\dec_extract_b.py', @($S))
  $steps += ,@('vhr_b', 'vhr_b\vhr_scan_b.py', @(('j1_' + $S)))
  $steps += ,@($rd, ($rd + '\a1_fzp_firstdiff_b_' + $S + '.py'), @((Join-Path $CW ($rd + '\fzp_firstdiff_' + $S + '.json'))))
} else {
  $rd = 'rawcheck_b\' + $S
  $steps += ,@($rd, ($rd + '\walltimes_b_' + $S + '.py'), @())
  $steps += ,@($rd, ($rd + '\ramp_fc_b_' + $S + '.py'), @())
  $steps += ,@($rd, ($rd + '\rm_exec_b_' + $S + '.py'), @())
  $steps += ,@('rawcheck_b', 'rawcheck_b\dec_extract_b.py', @($S))
  $steps += ,@('vhr_b', 'vhr_b\vhr_scan_b.py', @(('j1_' + $S)))
  $steps += ,@($rd, ($rd + '\a1_fzp_firstdiff_b_' + $S + '.py'), @((Join-Path $CW ($rd + '\fzp_firstdiff_' + $S + '.json'))))
}
Note ("plan " + $tagp + " start pid=" + $PID + " priority=" + (Get-Process -Id $PID).PriorityClass)
foreach ($s in $steps) {
  $wd = Join-Path $CW $s[0]; $tool = Join-Path $CW $s[1]; $args2 = $s[2]
  $rel = 'work\' + $s[1]
  $h = (Get-FileHash -LiteralPath $tool -Algorithm SHA256).Hash.ToLowerInvariant()
  if (-not $pins.ContainsKey($rel) -or $pins[$rel] -ne $h) { Note ("STOP pin mismatch " + $rel + " " + $h); exit 2 }
  $log = Join-Path $CW ('b\ana_' + $tagp + '_' + [IO.Path]::GetFileNameWithoutExtension($tool) + '.out.txt')
  Note ("step start " + $rel + " sha=" + $h.Substring(0, 16) + " wd=" + $wd + " args=" + ($args2 -join ' '))
  $t0 = Get-Date
  $al = @('-B', ('"' + $tool + '"')) + @($args2 | ForEach-Object { '"' + $_ + '"' })
  $p = Start-Process -FilePath $PY -ArgumentList $al -WorkingDirectory $wd -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput $log -RedirectStandardError ($log + '.err')
  $code = $p.ExitCode
  Note ("step end " + $rel + " exit=" + $code + " sec=" + [math]::Round(((Get-Date) - $t0).TotalSeconds, 1) + " out=" + $log)
  if ($code -ne 0) { Note ("STOP step failed " + $rel); exit 1 }
}
Note ("plan " + $tagp + " done")
exit 0
