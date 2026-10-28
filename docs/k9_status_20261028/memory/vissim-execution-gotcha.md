---
name: vissim-execution-gotcha
description: How to launch PTV Vissim COM in this project (PowerShell-only due to Korean path) and license/install facts
metadata: 
  node_type: memory
  type: reference
  originSessionId: 7c1323b0-ca64-4d8c-bf2b-0c9f5bd5c5b4
---

PTV Vissim 2020 (SP 14) is installed at `C:\Program Files\PTV Vision\PTV Vissim 2020` (`VISSIM200.exe` GUI, `VISSIM200CL.exe` console). COM ProgID `Vissim.Vissim` → `VISSIM.Vissim-64.2000`. License (CodeMeter) is available — `CreateObject("Vissim.Vissim")` + `LoadNet` both succeed.

**Always launch Vissim COM / cscript from the PowerShell tool, NOT the Git Bash tool.** The project path contains Korean (`C:\Users\TRLAB\Desktop\찐찐막\...`); passing it through Git Bash → cscript codepage-mangles it and Vissim's `LoadNet` fails with "The file does not exist." PowerShell passes the Unicode path correctly.

Runner: `scripts/run_stackelberg_vissim_controller.vbs <inpx> <stateCsv> <actionCsv> <decisionDir> [simPeriod] [urbanVol] [freewayVol] [ctrlInterval] [seed] [adapterPy] [calibrationJson] [tuningJson] [demandProfile] [controller]`. Note arg10 calibration defaults to an OLD vector json — pass the v2 json explicitly. Probe license/load with `scripts/probe_vissim_load_only.vbs <inpx>`. Eval network (8-seg, current): `Network_Vissim_Work/modi_eval_vsl_8seg.inpx` (116 links, 32 DSDs; 5-seg `modi_eval_vsl_segmented.inpx` kept for archive). 8-seg runner: `scripts/run_stackelberg_vissim_controller_8seg.vbs` (the old runner has 5-seg binning hardcoded - do not mix). **If CreateObject("Vissim.Vissim") fails with 0x80080005 CO_E_SERVER_EXEC_FAILURE, the CodeMeter Runtime Server service is stopped - Start-Service 'CodeMeter.exe' fixes it.** See [[numerical-sim-adapter-state]].
