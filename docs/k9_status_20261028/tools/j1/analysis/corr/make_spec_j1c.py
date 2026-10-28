r"""Writes spec_j1c_copies.json for codex_handoff/work/gate1/mkcopy.py (pinned 8ec4f60c...): copies of the pinned r4
tools for the J1 report correction (D-K9-89 7).  r4_common.py: one path constant (AV); r4_fzp_first.py, r4_firstobs.py:
byte copies; r4_driver_v2.ps1 -> j1c_driver.ps1 (header, log name, guard, step list); r4_launch_v2.ps1 -> j1c_launch.ps1
(header, driver name).  2026-10-26 KST."""
import json
import os

SP = r'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8'
R4T = os.path.join(SP, 'k92', 'va', 'analysis', 'r4', 'tools')
CT = os.path.join(SP, 'j1', 'analysis', 'corr', 'tools')
AV = os.path.join(SP, 'k92', 'va', 'analysis')

spec = [
    {'src': os.path.join(R4T, 'r4_common.py'), 'dst': os.path.join(CT, 'r4_common.py'),
     'why': 'J1 correction copy: the copy lives in SP/j1/analysis/corr/tools, so AV (r3 analysis folder: va_common, '
            'va_metrics.json, VA_REPORT.md) becomes an absolute path constant; R4 = corr, OUT = corr/out follow unchanged',
     'reps': [['AV = os.path.dirname(R4)',
               "AV = r'%s'  # J1 correction copy (D-K9-89 7): path constant only" % AV]]},
    {'src': os.path.join(R4T, 'r4_fzp_first.py'), 'dst': os.path.join(CT, 'r4_fzp_first.py'),
     'why': 'byte copy (imports the r4_common copy next to it)', 'reps': []},
    {'src': os.path.join(R4T, 'r4_firstobs.py'), 'dst': os.path.join(CT, 'r4_firstobs.py'),
     'why': 'byte copy (imports the r4_common copy next to it)', 'reps': []},
    {'src': os.path.join(R4T, 'r4_driver_v2.ps1'), 'dst': os.path.join(CT, 'j1c_driver.ps1'),
     'why': 'runner wrapper (not an analysis tool): log name, guard (this workflow heavy python only; the A1 guard is '
            'obsolete, A1 ended), step list + j1c_compare.py',
     'reps': [
         ['# V-A r4 driver v2 (= r4_driver.ps1',
          "# J1 correction driver (D-K9-89 7) = copy of r4_driver_v2.ps1 with: log name j1c_driver.log; guard = wait only\n"
          "# while a heavy python of this workflow runs (Gate 1 replays, codex_handoff\\work tools, r4 tools; never the B run\n"
          "# itself or other sessions); steps = 9 scans + r4_firstobs.py + j1c_compare.py.  Original r4 v2 header follows.\n"
          "# V-A r4 driver v2 (= r4_driver.ps1"],
         ["$log = Join-Path $logs 'r4_driver_v2.log'", "$log = Join-Path $logs 'j1c_driver.log'"],
         ["    $a1 = @($ps | Where-Object { $_.CommandLine -match 'vissim_stackelberg_adapter\\.py' -and $_.CommandLine -match '20261025_codex_a1' })\n"
          "    $age = 0.0\n"
          "    foreach ($p in $a1) { $x = ($now - $p.CreationDate).TotalSeconds; if ($x -gt $age) { $age = $x } }\n"
          "    $other = @($ps | Where-Object { $_.CommandLine -notmatch '20261025_codex_a1' -and $_.CommandLine -notmatch 'r4_(fzp_first|firstobs)\\.py' })\n"
          "    if ($age -le 1500 -and $other.Count -eq 0) { return ('a1_decision_age={0:N0}s' -f $age) }\n"
          "    L ('WAIT a1_decision_age={0:N0}s other_python={1}' -f $age, (($other | ForEach-Object { $_.ProcessId }) -join ','))",
          "    $vis = @(Get-CimInstance Win32_Process -Filter \"Name='VISSIM200.exe'\")\n"
          "    $other = @($ps | Where-Object { $_.CommandLine -match 'codexhandoff\\\\gate1|codex_handoff\\\\work\\\\|k92\\\\va\\\\analysis\\\\r4\\\\tools' })\n"
          "    if ($other.Count -eq 0) { return ('vissim_pids={0} python_total={1}' -f (($vis | ForEach-Object { $_.ProcessId }) -join ','), $ps.Count) }\n"
          "    L ('WAIT workflow_heavy_python={0}' -f (($other | ForEach-Object { $_.ProcessId }) -join ','))"],
         ["$steps += , @('firstobs', @('-B', (Join-Path $tools 'r4_firstobs.py')))",
          "$steps += , @('firstobs', @('-B', (Join-Path $tools 'r4_firstobs.py')))\n"
          "$steps += , @('j1c_compare', @('-B', (Join-Path $tools 'j1c_compare.py')))"],
     ]},
    {'src': os.path.join(R4T, 'r4_launch_v2.ps1'), 'dst': os.path.join(CT, 'j1c_launch.ps1'),
     'why': 'launcher wrapper: driver name only (logs go to corr/logs via the relative path)',
     'reps': [
         ['# (v2: launches r4_driver_v2.ps1) Launch r4_driver_v2.ps1 detached',
          '# (J1 correction copy of r4_launch_v2.ps1: launches j1c_driver.ps1) Launch j1c_driver.ps1 detached'],
         ["$drv = Join-Path $tools 'r4_driver_v2.ps1'", "$drv = Join-Path $tools 'j1c_driver.ps1'"],
     ]},
]
out = os.path.join(SP, 'j1', 'analysis', 'corr', 'spec_j1c_copies.json')
with open(out, 'w', encoding='utf-8') as h:
    json.dump(spec, h, ensure_ascii=False, indent=1)
print('spec written', out, len(spec))
