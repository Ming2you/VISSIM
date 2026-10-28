# O4 chain 2: feeder-link split scans (one FZP at a time), then model JSON extraction (one run at a time). Read-only.
$ErrorActionPreference = 'Continue'
$W = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\rmcause\o1o4\work'
$OUT = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\rmcause\o1o4\fzp'
$MOUT = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\rmcause\o1o4\model'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
New-Item -ItemType Directory -Force $MOUT | Out-Null
$env:PYTHONHASHSEED = '0'
$status = "$W\logs\chain2_status.txt"
"START $(Get-Date -Format o) PID $PID" | Out-File -Encoding utf8 $status
foreach ($line in Get-Content "$W\jobs_fzp.txt") {
    if (-not $line.Trim()) { continue }
    $tag, $fzp = $line.Split('|')
    "BEGIN split $tag $(Get-Date -Format o)" | Out-File -Encoding utf8 -Append $status
    & $PY -B "$W\o4_fzp_split.py" $tag $fzp $OUT *> "$W\logs\split_$tag.log"
    "END split $tag rc=$LASTEXITCODE $(Get-Date -Format o)" | Out-File -Encoding utf8 -Append $status
}
foreach ($line in Get-Content "$W\jobs_model.txt") {
    if (-not $line.Trim()) { continue }
    $tag, $root = $line.Split('|')
    "BEGIN model $tag $(Get-Date -Format o)" | Out-File -Encoding utf8 -Append $status
    & $PY -B "$W\o4_model.py" $tag $root $MOUT *> "$W\logs\model_$tag.log"
    "END model $tag rc=$LASTEXITCODE $(Get-Date -Format o)" | Out-File -Encoding utf8 -Append $status
}
"CHAIN_DONE $(Get-Date -Format o)" | Out-File -Encoding utf8 -Append $status
