# B analysis step runner (Windows PowerShell 5.1), started detached by WMI at BELOW_NORMAL (children inherit it).
# Runs pinned tools (PINS_B.sha256) one at a time, unchanged, with python -B, PYTHONHASHSEED=0, PYTHONDONTWRITEBYTECODE=1,
# OMP/OPENBLAS/MKL threads 1 (COMPARE_RULE_B s7.5). Verifies each tool's sha256 against PINS_B before running it.
# -Plan prescan  : vhr_b/vhr_scan_b.py va_s31 nc3_s31            (NC3 / V-A slots only; allowed before B data, rule s7.5)
# -Plan s31stage : walltimes_b_s31, ramp_fc_b_s31, rm_exec_b_s31 (wd rawcheck_b/s31), dec_extract_b s31 (wd rawcheck_b),
#                  vhr_scan_b j1_s31 (prefix sha), a1_fzp_firstdiff_b_s31 -> rawcheck_b/s31/fzp_firstdiff_s31.json
param([Parameter(Mandatory = $true)][ValidateSet('prescan', 's31stage')][string]$Plan)
$ErrorActionPreference = 'Stop'
$CH = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff'
$CW = Join-Path $CH 'work'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$state = Join-Path $CW ('b\ana_' + $Plan + '.state.txt')
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
  $steps += ,@('vhr_b', 'vhr_b\vhr_scan_b.py', @('va_s31', 'nc3_s31'))
} else {
  $steps += ,@('rawcheck_b\s31', 'rawcheck_b\s31\walltimes_b_s31.py', @())
  $steps += ,@('rawcheck_b\s31', 'rawcheck_b\s31\ramp_fc_b_s31.py', @())
  $steps += ,@('rawcheck_b\s31', 'rawcheck_b\s31\rm_exec_b_s31.py', @())
  $steps += ,@('rawcheck_b', 'rawcheck_b\dec_extract_b.py', @('s31'))
  $steps += ,@('vhr_b', 'vhr_b\vhr_scan_b.py', @('j1_s31'))
  $steps += ,@('rawcheck_b\s31', 'rawcheck_b\s31\a1_fzp_firstdiff_b_s31.py', @((Join-Path $CW 'rawcheck_b\s31\fzp_firstdiff_s31.json')))
}
Note ("plan " + $Plan + " start pid=" + $PID + " priority=" + (Get-Process -Id $PID).PriorityClass)
foreach ($s in $steps) {
  $wd = Join-Path $CW $s[0]; $tool = Join-Path $CW $s[1]; $args2 = $s[2]
  $rel = 'work\' + $s[1]
  $h = (Get-FileHash -LiteralPath $tool -Algorithm SHA256).Hash.ToLowerInvariant()
  if (-not $pins.ContainsKey($rel) -or $pins[$rel] -ne $h) { Note ("STOP pin mismatch " + $rel + " " + $h); exit 2 }
  $log = Join-Path $CW ('b\ana_' + $Plan + '_' + [IO.Path]::GetFileNameWithoutExtension($tool) + '.out.txt')
  Note ("step start " + $rel + " sha=" + $h.Substring(0, 16) + " wd=" + $wd + " args=" + ($args2 -join ' '))
  $t0 = Get-Date
  $al = @('-B', ('"' + $tool + '"')) + @($args2 | ForEach-Object { '"' + $_ + '"' })
  $p = Start-Process -FilePath $PY -ArgumentList $al -WorkingDirectory $wd -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput $log -RedirectStandardError ($log + '.err')
  $code = $p.ExitCode
  Note ("step end " + $rel + " exit=" + $code + " sec=" + [math]::Round(((Get-Date) - $t0).TotalSeconds, 1) + " out=" + $log)
  if ($code -ne 0) { Note ("STOP step failed " + $rel); exit 1 }
}
Note ("plan " + $Plan + " done")
exit 0
