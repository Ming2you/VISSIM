# A1 analysis chain (rule COMPARE_RULE_A1_FULL.md). Launched detached by WMI, BELOW_NORMAL (inherited by children).
# -Smoke : tool self-test on codex data only ("a1" = codex joint record); writes *_smoke outputs. No VISSIM, no COM, no replay.
# Steps run one at a time; each step's exit code goes to the state file. Stops if C: or D: < 8 GB.
param([switch]$Smoke, [string]$Steps = 'scan,metrics,first,unins,ours,table,fzpdiff,trace')
$F = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\a1\full'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$sfx = if ($Smoke) { '_smoke' } else { '' }
$sm = if ($Smoke) { @('--smoke') } else { @() }
$state = Join-Path $F ('analysis' + $sfx + '.state.txt')
foreach ($d in @('scan', 'firstseen', 'logs')) { New-Item -ItemType Directory -Force -Path (Join-Path $F ($d + $(if ($d -ne 'logs') { $sfx } else { '' }))) | Out-Null }
function Note([string]$m) { ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz') + ' ' + $m) | Add-Content -Encoding UTF8 $state }
function RunPy([string]$Name, [string[]]$PyArgs) {
  $c = [math]::Round((Get-PSDrive C).Free / 1GB, 1); $d = [math]::Round((Get-PSDrive D).Free / 1GB, 1)
  if ($c -lt 8 -or $d -lt 8) { Note "STOP disk C=$c D=$d"; exit 2 }
  $quoted = @($PyArgs | ForEach-Object { '"' + $_ + '"' }) -join ' '
  $base = Join-Path $F ('logs\' + $Name + $sfx)
  $t0 = Get-Date
  $p = Start-Process -FilePath $PY -ArgumentList ('-B ' + $quoted) -WorkingDirectory $F -NoNewWindow -Wait -PassThru `
    -RedirectStandardOutput ($base + '.out.txt') -RedirectStandardError ($base + '.err.txt')
  Note ("$Name exit=" + $p.ExitCode + ' sec=' + [math]::Round(((Get-Date) - $t0).TotalSeconds, 1) + " disk C=$c D=$d")
  return $p.ExitCode
}
$env:PYTHONHASHSEED = '0'; $env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'
$env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'
Note ('start pid=' + $PID + ' priority=' + (Get-Process -Id $PID).PriorityClass + ' smoke=' + [bool]$Smoke + ' steps=' + $Steps)
$want = $Steps.Split(',')
if ($want -contains 'scan')    { RunPy 'scan_fzp_a1' (@((Join-Path $F 'scan_fzp_a1.py'), 'a1') + $sm) | Out-Null }
if ($want -contains 'metrics') { RunPy 'metrics_a1' (@((Join-Path $F 'metrics_a1.py')) + $sm) | Out-Null }
if ($want -contains 'first')   { RunPy 'vhr_firstseen_a1' (@((Join-Path $F 'vhr_firstseen_a1.py'), 'a1', 'lnc') + $sm) | Out-Null }
if ($want -contains 'unins')   { RunPy 'unins_a1' (@((Join-Path $F 'unins_a1.py')) + $sm) | Out-Null }
if ($want -contains 'ours')    { RunPy 'a1_ours' (@((Join-Path $F 'a1_ours.py')) + $sm) | Out-Null }
if ($want -contains 'table')   { RunPy 'a1_table' (@((Join-Path $F 'a1_table.py')) + $sm) | Out-Null }
if ($want -contains 'fzpdiff') { RunPy 'a1_fzp_firstdiff' (@((Join-Path $F 'a1_fzp_firstdiff.py'), (Join-Path $F ('fzpdiff' + $sfx + '.json'))) + $sm) | Out-Null }
if ($want -contains 'trace')   { RunPy 'a1_trace' (@((Join-Path $F 'a1_trace.py'), (Join-Path $F ('trace' + $sfx + '.json'))) + $sm) | Out-Null }
Note 'done'
'done' | Set-Content -Encoding UTF8 (Join-Path $F ('analysis' + $sfx + '.done'))
