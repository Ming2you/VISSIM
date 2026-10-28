param([int]$T, [string]$Prefix, [int]$MaxIt = 25)
$WORK = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\a0'
$env:PYTHONHASHSEED = '0'; $env:PYTHONUTF8 = '1'; $env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'
$py = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
& $py -B (Join-Path $WORK 's10_iterate.py') $T $Prefix $MaxIt > (Join-Path $WORK ('iterate_' + $Prefix + '.out.txt')) 2>&1
