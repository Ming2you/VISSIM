# O4 read-only FZP scan chain (one FZP at a time). Writes only under o1o4/fzp and o1o4/work/logs.
$ErrorActionPreference = 'Continue'
$W = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\rmcause\o1o4\work'
$OUT = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\rmcause\o1o4\fzp'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
New-Item -ItemType Directory -Force "$W\logs" | Out-Null
New-Item -ItemType Directory -Force $OUT | Out-Null
$env:PYTHONHASHSEED = '0'
$status = "$W\logs\chain_status.txt"
"START $(Get-Date -Format o) PID $PID" | Out-File -Encoding utf8 $status
foreach ($line in Get-Content "$W\jobs_fzp.txt") {
    if (-not $line.Trim()) { continue }
    $tag, $fzp = $line.Split('|')
    "BEGIN $tag $(Get-Date -Format o)" | Out-File -Encoding utf8 -Append $status
    & $PY -B "$W\o4_fzp.py" $tag $fzp $OUT *> "$W\logs\$tag.log"
    "END $tag rc=$LASTEXITCODE $(Get-Date -Format o)" | Out-File -Encoding utf8 -Append $status
}
"CHAIN_DONE $(Get-Date -Format o)" | Out-File -Encoding utf8 -Append $status
