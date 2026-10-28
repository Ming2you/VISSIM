$ErrorActionPreference = 'Stop'
$R = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\rmcause\codex_scan'
$env:PYTHONHASHSEED = '0'; $env:PYTHONDONTWRITEBYTECODE = '1'
$py = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
Add-Content "$R\logs\chain.log" ("{0} chain start pid={1}" -f (Get-Date -Format s), $PID)
foreach ($ln in (Get-Content "$R\jobs.txt" | Where-Object { $_ -match '\|' })) {
  $tag, $fzp = $ln.Split('|')
  if (Test-Path "$R\out\$tag.json") { continue }
  $p = Start-Process -FilePath $py -ArgumentList @('-B', "`"$R\cx_scan.py`"", $tag, "`"$fzp`"", "`"$R\out`"") -NoNewWindow -PassThru -RedirectStandardOutput "$R\logs\$tag.out.txt" -RedirectStandardError "$R\logs\$tag.err.txt"
  try { $p.PriorityClass = 'BelowNormal' } catch {}
  Add-Content "$R\logs\chain.log" ("{0} start {1} pid={2}" -f (Get-Date -Format s), $tag, $p.Id)
  $p.WaitForExit()
  Add-Content "$R\logs\chain.log" ("{0} end {1} exit={2}" -f (Get-Date -Format s), $tag, $p.ExitCode)
}
Add-Content "$R\logs\chain.log" ("{0} CHAIN_DONE" -f (Get-Date -Format s))
