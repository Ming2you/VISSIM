$ErrorActionPreference = 'Stop'
$R = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\rmcause'
$O = "$R\o1o4"
$env:PYTHONHASHSEED = '0'; $env:PYTHONDONTWRITEBYTECODE = '1'
$py = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
try { (Get-Process -Id $PID).PriorityClass = 'BelowNormal' } catch {}
Add-Content "$O\logs\chain.log" ("{0} chain start pid={1}" -f (Get-Date -Format s), $PID)
foreach ($ln in (Get-Content "$O\work\jobs.txt" | Where-Object { $_ -match '\|' })) {
  $kind, $tag, $fzp = $ln.Split('|')
  if (Test-Path "$O\scan\$tag.json") { continue }
  if ($kind -eq 'fwe') { $script = "$R\phys\fwe_scan.py" } else { $script = "$O\work\linkbin_scan.py" }
  $p = Start-Process -FilePath $py -ArgumentList @('-B', "`"$script`"", $tag, "`"$fzp`"", "`"$O\scan`"") -NoNewWindow -PassThru -RedirectStandardOutput "$O\logs\$tag.out.txt" -RedirectStandardError "$O\logs\$tag.err.txt"
  try { $p.PriorityClass = 'BelowNormal' } catch {}
  Add-Content "$O\logs\chain.log" ("{0} start {1} pid={2}" -f (Get-Date -Format s), $tag, $p.Id)
  $p.WaitForExit()
  Add-Content "$O\logs\chain.log" ("{0} end {1} exit={2}" -f (Get-Date -Format s), $tag, $p.ExitCode)
}
Add-Content "$O\logs\chain.log" ("{0} CHAIN_DONE" -f (Get-Date -Format s))
