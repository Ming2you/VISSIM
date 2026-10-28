# Pre-populate a bytecode cache prefix (outside every code tree) for the speed-candidate replays.
$WORK = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\a0'
$PREFIX = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\a0\pycache_prefix'
$env:PYTHONHASHSEED = '0'; $env:PYTHONUTF8 = '1'; $env:PYTHONPYCACHEPREFIX = $PREFIX
$py = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$t0 = Get-Date
& $py -B -m compileall -q -j 2 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\Lib' 'D:\VISSIM-window264-deps' 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\a0\code' > (Join-Path $WORK 'compileall.out.txt') 2>&1
"exit=$LASTEXITCODE seconds=$([int]((Get-Date)-$t0).TotalSeconds)" | Set-Content -Encoding UTF8 (Join-Path $WORK 'compileall.state.txt')
