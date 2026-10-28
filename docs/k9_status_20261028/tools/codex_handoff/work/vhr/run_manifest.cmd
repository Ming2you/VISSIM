@echo off
cd /d "C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\vhr"
set PYTHONHASHSEED=0
set PYTHONUTF8=1
"C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe" -B vhr_manifest.py > manifest_run.log 2>&1
echo exit=%ERRORLEVEL% > manifest_run.exit
