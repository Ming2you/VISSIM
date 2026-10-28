param([string]$Jobs, [int]$Lane, [int]$Lanes)
$ErrorActionPreference = 'Stop'
$R = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PYTHONHASHSEED = '0'; $env:PYTHONDONTWRITEBYTECODE = '1'
$lines = Get-Content $Jobs | Where-Object { $_ -match '\|' }
for ($i = 0; $i -lt $lines.Count; $i++) {
  if (($i % $Lanes) -ne $Lane) { continue }
  $tag, $fzp = $lines[$i].Split('|')
  if (Test-Path "$R/scan/$tag.json") { continue }
  $p = Start-Process -FilePath python -ArgumentList @('-B', "$R/fwe_scan.py", $tag, $fzp, "$R/scan") -NoNewWindow -PassThru -RedirectStandardOutput "$R/logs/$tag.out.txt" -RedirectStandardError "$R/logs/$tag.err.txt"
  try { $p.PriorityClass = 'BelowNormal' } catch {}
  Add-Content "$R/logs/chain_$Lane.log" ("{0} start {1} pid={2}" -f (Get-Date -Format s), $tag, $p.Id)
  $p.WaitForExit()
  Add-Content "$R/logs/chain_$Lane.log" ("{0} end {1} exit={2}" -f (Get-Date -Format s), $tag, $p.ExitCode)
}
