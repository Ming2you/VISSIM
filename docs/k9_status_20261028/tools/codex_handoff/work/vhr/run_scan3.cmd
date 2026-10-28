@echo off
cd /d "C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\vhr"
set PYTHONHASHSEED=0
set PYTHONUTF8=1
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
"C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe" -B vhr_scan.py va_s41 j1_s41 nc3_s41 va_s43 j1_s43 nc3_s43 > scan_out\scan3.log 2>&1
"C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe" -B vhr_firstseen.py va_s41 j1_s41 nc3_s41 va_s43 j1_s43 nc3_s43 > scan_out\first3.log 2>&1
echo exit=%ERRORLEVEL% > scan_out\scan3.exit
