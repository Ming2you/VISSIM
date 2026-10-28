# Make run_replay2.ps1 = run_replay.ps1 + two optional parameters whose defaults reproduce run_replay.ps1:
#   -TuningName (default optimized_config.json, same folder)   -PyExe (default system Python 3.12.2)
W = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/a0/'
BS = chr(92)
s = open(W + 'run_replay.ps1', 'rb').read().decode('utf-8-sig')
rel = BS.join(['diagnostics', 'repin_v3c3_review_20261001', 'urban_rm269', 'aggregate270', 'native413_adopted355', ''])
old = "(Join-Path $CODE '" + rel + "optimized_config.json')"
assert s.count(old) == 1, s.count(old)
s = s.replace(old, "(Join-Path $CODE ('" + rel + "' + $TuningName))")
nl = '\r\n' if '\r\n' in s else '\n'
p_old = "  [string]$Wrapper = ''" + nl + ")"
assert s.count(p_old) == 1
s = s.replace(p_old, "  [string]$Wrapper = ''," + nl + "  [string]$TuningName = 'optimized_config.json'," + nl
              + "  [string]$PyExe = 'C:" + BS + "Users" + BS + "TRLAB" + BS + "AppData" + BS + "Local" + BS + "Programs" + BS + "Python" + BS + "Python312" + BS + "python.exe'" + nl + ")")
py_old = "$PY = 'C:" + BS + "Users" + BS + "TRLAB" + BS + "AppData" + BS + "Local" + BS + "Programs" + BS + "Python" + BS + "Python312" + BS + "python.exe'"
assert s.count(py_old) == 1, s.count(py_old)
s = s.replace(py_old, "$PY = $PyExe")
k_old = "$s = [ordered]@{ T = $T; label = $Label;"
assert s.count(k_old) == 1
s = s.replace(k_old, "$s = [ordered]@{ T = $T; label = $Label; tuning_name = $TuningName; py_exe = $PyExe;")
# the collector step keeps the system Python (analysis only, not part of the replay)
c_old = "& $PY -B (Join-Path $WORK 's5_collect.py')"
assert s.count(c_old) == 1
s = s.replace(c_old, "& 'C:" + BS + "Users" + BS + "TRLAB" + BS + "AppData" + BS + "Local" + BS + "Programs" + BS + "Python" + BS + "Python312" + BS + "python.exe' -B (Join-Path $WORK 's5_collect.py')")
open(W + 'run_replay2.ps1', 'w', encoding='utf-8-sig', newline='').write(s)
print('ok')
