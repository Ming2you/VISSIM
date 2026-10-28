# B1 seat-check logic test (2026-10-26, D-K9-90). No VISSIM, no process started or stopped.
# Extracts the runner's pre-launch block (from the first '$live=@(Get-CimInstance' line to the refusal 'if($live.Count' line)
# and runs it with Get-CimInstance mocked to return N fake 'VISSIM200.exe' rows (and one 'cscript.exe' row that must not count)
# and Start-Sleep mocked to a no-op, for N = 0..6. Prints one line per N: allowed / refused:<message>.
#   powershell -NoProfile -ExecutionPolicy Bypass -File b1_seat_logic_test.ps1 -Runner <run_closedloop3000.ps1> -Out <json>
param([Parameter(Mandatory = $true)][string]$Runner, [Parameter(Mandatory = $true)][string]$Out)
$ErrorActionPreference = 'Stop'
$lines = [IO.File]::ReadAllLines($Runner)
$i0 = -1; $i1 = -1
for ($i = 0; $i -lt $lines.Count; $i++) {
  if ($i0 -lt 0 -and $lines[$i] -match '^\s*\$live=@\(Get-CimInstance Win32_Process') { $i0 = $i }
  if ($i0 -ge 0 -and $lines[$i] -match '^\s*if\(\$live\.Count') { $i1 = $i; break }
}
if ($i0 -lt 0 -or $i1 -lt 0) { throw 'pre-launch block not found' }
$blockText = ($lines[$i0..$i1] -join "`n")
$tmp = Join-Path $env:TEMP ('b1_seat_test_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp | Out-Null
$results = @()
foreach ($n in 0..6) {
  $sb = [scriptblock]::Create(@"
function Get-CimInstance { param([string]`$ClassName)
  `$rows = @([pscustomobject]@{ Name = 'cscript.exe' })
  for (`$k = 0; `$k -lt $n; `$k++) { `$rows += [pscustomobject]@{ Name = 'VISSIM200.exe' } }
  return `$rows }
function Start-Sleep { param([int]`$Seconds) }
`$runsRoot = '$tmp'
$blockText
"@)
  try { & $sb; $results += [ordered]@{ vissim = $n; outcome = 'allowed' } }
  catch { $results += [ordered]@{ vissim = $n; outcome = ('refused: ' + $_.Exception.Message) } }
}
Remove-Item -LiteralPath $tmp -Recurse -Force
$rec = [ordered]@{ runner = $Runner; runner_sha256 = (Get-FileHash -LiteralPath $Runner -Algorithm SHA256).Hash.ToLowerInvariant();
  block_lines = ('{0}-{1}' -f ($i0 + 1), ($i1 + 1)); results = $results }
($rec | ConvertTo-Json -Depth 5) | Set-Content -Encoding UTF8 -LiteralPath $Out
foreach ($r in $results) { 'N={0} {1}' -f $r.vissim, $r.outcome }
