# Run omega701_recount.py <step> detached (launched by WMI Win32_Process.Create, BELOW_NORMAL inherited).
param([string]$Step = 'scan')
$w = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\omega'
$state = Join-Path $w ("state_" + $Step + ".json")
$env:PYTHONHASHSEED = '0'
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$py = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$start = Get-Date
$s = [ordered]@{ wrapper_pid = $PID; priority = (Get-Process -Id $PID).PriorityClass.ToString();
                 command = "$py -B omega701_recount.py $Step"; start = $start.ToString('yyyy-MM-dd HH:mm:ss.fff zzz'); status = 'running' }
($s | ConvertTo-Json) | Set-Content -Encoding UTF8 -LiteralPath $state
Set-Location -LiteralPath $w
& $py -B (Join-Path $w 'omega701_recount.py') $Step > (Join-Path $w ("stdout_" + $Step + ".txt")) 2> (Join-Path $w ("stderr_" + $Step + ".txt"))
$code = $LASTEXITCODE
$end = Get-Date
$s.status = 'done'
$s.exit_code = $code
$s.end = $end.ToString('yyyy-MM-dd HH:mm:ss.fff zzz')
$s.seconds = [math]::Round(($end - $start).TotalSeconds, 1)
($s | ConvertTo-Json) | Set-Content -Encoding UTF8 -LiteralPath $state
