# Run verify_manifest.py detached (WMI, BELOW_NORMAL inherited) with the fixed Python env conventions.
$raw = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\raw'
$state = Join-Path $raw 'verify_state.json'
$env:PYTHONHASHSEED = '0'
$env:PYTHONUTF8 = '1'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$py = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$start = Get-Date
$s = [ordered]@{ wrapper_pid = $PID; priority = (Get-Process -Id $PID).PriorityClass.ToString();
                 command = "$py -B verify_manifest.py"; start = $start.ToString('yyyy-MM-dd HH:mm:ss.fff zzz'); status = 'running' }
($s | ConvertTo-Json) | Set-Content -Encoding UTF8 -LiteralPath $state
& $py -B (Join-Path $raw 'verify_manifest.py') > (Join-Path $raw 'verify_stdout.txt') 2> (Join-Path $raw 'verify_stderr.txt')
$code = $LASTEXITCODE
$end = Get-Date
$s.status = 'done'
$s.exit_code = $code
$s.end = $end.ToString('yyyy-MM-dd HH:mm:ss.fff zzz')
$s.seconds = [math]::Round(($end - $start).TotalSeconds, 1)
($s | ConvertTo-Json) | Set-Content -Encoding UTF8 -LiteralPath $state
