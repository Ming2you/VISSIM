# VERIFY_NEXT detached chain: one heavy read at a time, BELOW_NORMAL. Read-only toward run folders.
$ErrorActionPreference = 'Continue'
$V = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\rmcause\o1o4\vnext'
$env:PYTHONHASHSEED = '0'; $env:PYTHONDONTWRITEBYTECODE = '1'
$py = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
try { (Get-Process -Id $PID).PriorityClass = 'BelowNormal' } catch {}
$log = "$V\logs\vn_chain.log"
Add-Content $log ("{0} CHAIN_START pid={1}" -f (Get-Date -Format s), $PID)
foreach ($ln in (Get-Content "$V\tools\jobs.txt" | Where-Object { $_ -match '\|' })) {
  $kind, $tag, $arg = $ln.Split('|', 3)
  $outj = "$V\out\$tag.json"
  if (Test-Path $outj) { Add-Content $log ("{0} skip {1}" -f (Get-Date -Format s), $tag); continue }
  if ($kind -eq 'fzp') {
    $al = @('-B', "`"$V\tools\vn_fzp_scan.py`"", "`"$arg`"", "`"$outj`"")
  } else {
    $al = @('-B', "`"$V\tools\vn_model_extract.py`"", "`"$outj`"") + ($arg.Split(' ') | ForEach-Object { "`"$_`"" })
  }
  $p = Start-Process -FilePath $py -ArgumentList $al -NoNewWindow -PassThru -RedirectStandardOutput "$V\logs\$tag.out.txt" -RedirectStandardError "$V\logs\$tag.err.txt"
  try { $p.PriorityClass = 'BelowNormal' } catch {}
  Add-Content $log ("{0} start {1} pid={2}" -f (Get-Date -Format s), $tag, $p.Id)
  $p.WaitForExit()
  Add-Content $log ("{0} end {1} exit={2}" -f (Get-Date -Format s), $tag, $p.ExitCode)
}
Add-Content $log ("{0} CHAIN_DONE" -f (Get-Date -Format s))
