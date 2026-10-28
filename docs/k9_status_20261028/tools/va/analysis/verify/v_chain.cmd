@echo off
rem Verify chain (one process at a time): v_fzp for the three V-A tags, v_control, v_metrics, v_local, v_compare.
rem usage: v_chain.cmd <profile> <logprefix>
set PYTHONHASHSEED=0
set PYTHONDONTWRITEBYTECODE=1
set PYTHONIOENCODING=utf-8
set PY=C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe
cd /d "%~dp0"
echo CHAIN_START %date% %time% > "%~2_chain.txt"
for %%T in (va_s31 va_s41 va_s43) do (
  "%PY%" -B v_fzp.py %%T --profile %1 >> "%~2_fzp_%%T.out.txt" 2>> "%~2_fzp_%%T.err.txt" || (echo FAIL v_fzp %%T >> "%~2_chain.txt" & exit /b 1)
  echo DONE v_fzp %%T %time% >> "%~2_chain.txt"
)
for %%S in (v_control v_metrics v_local v_compare) do (
  "%PY%" -B %%S.py --profile %1 >> "%~2_%%S.out.txt" 2>> "%~2_%%S.err.txt" || (echo FAIL %%S >> "%~2_chain.txt" & exit /b 1)
  echo DONE %%S %time% >> "%~2_chain.txt"
)
echo CHAIN_END %date% %time% >> "%~2_chain.txt"
