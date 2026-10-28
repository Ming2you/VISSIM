$ErrorActionPreference = 'Continue'
$W = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\vfy_a1b0'
$O = Join-Path $W 'out'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$state = Join-Path $W 'run_vfy2.state.txt'
$env:PYTHONHASHSEED = '0'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:PYTHONIOENCODING = 'utf-8'
"START $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') pid=$PID" | Out-File -FilePath $state -Encoding utf8
function Step($name, $argList) {
  $t0 = Get-Date
  $p = Start-Process -FilePath $PY -ArgumentList $argList -NoNewWindow -PassThru -RedirectStandardOutput (Join-Path $O ($name + '.out.txt')) -RedirectStandardError (Join-Path $O ($name + '.err.txt'))
  try { $p.PriorityClass = 'BelowNormal' } catch {}
  $h = $p.Handle
  $p.WaitForExit()
  "$name exit=$($p.ExitCode) sec=$([math]::Round(((Get-Date) - $t0).TotalSeconds,1)) at $(Get-Date -Format 'HH:mm:ss')" | Out-File -FilePath $state -Append -Encoding utf8
}
Step 'b0_r2' ('-B "' + (Join-Path $W 'vfy_b0.py') + '" "' + (Join-Path $O 'b0.json') + '"')
Step 'form_diag' ('-B "' + (Join-Path $W 'vfy_form_diag.py') + '" "' + (Join-Path $O 'form_diag.json') + '"')
Step 'inputs_extra' ('-B "' + (Join-Path $W 'vfy_inputs_extra.py') + '" "' + (Join-Path $O 'inputs_extra.json') + '"')
"DONE $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -FilePath $state -Append -Encoding utf8
