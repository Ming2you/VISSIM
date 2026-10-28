# O4 chain 3: model flow-count extraction (one run at a time). Read-only.
$ErrorActionPreference = 'Continue'
$W = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\rmcause\o1o4\work'
$MOUT = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\rmcause\o1o4\model'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$env:PYTHONHASHSEED = '0'
$status = "$W\logs\chain3_status.txt"
"START $(Get-Date -Format o) PID $PID" | Out-File -Encoding utf8 $status
foreach ($line in Get-Content "$W\jobs_model.txt") {
    if (-not $line.Trim()) { continue }
    $tag, $root = $line.Split('|')
    "BEGIN model2 $tag $(Get-Date -Format o)" | Out-File -Encoding utf8 -Append $status
    & $PY -B "$W\o4_model2.py" $tag $root $MOUT *> "$W\logs\model2_$tag.log"
    "END model2 $tag rc=$LASTEXITCODE $(Get-Date -Format o)" | Out-File -Encoding utf8 -Append $status
}
"CHAIN_DONE $(Get-Date -Format o)" | Out-File -Encoding utf8 -Append $status
