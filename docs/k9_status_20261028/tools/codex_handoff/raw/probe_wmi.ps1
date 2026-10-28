$out = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\raw\probe_wmi.txt'
$p = Get-Process -Id $PID
$lines = @(
  "pid=$PID priority=$($p.PriorityClass) session=$($p.SessionId)",
  "Y_root=$(Test-Path 'Y:\')",
  "Y_dir=$(Test-Path 'Y:\99_임시휴지통\20261024\HANDOFF.md')",
  "UNC_dir=$(Test-Path '\\147.46.235.162\d\99_임시휴지통\20261024\HANDOFF.md')",
  "D_root=$(Test-Path 'D:\')"
)
$lines | Set-Content -Encoding UTF8 -LiteralPath $out
