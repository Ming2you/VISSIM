"""Prepare two151s traffic-only checks of the shipping error-log barrier."""
import hashlib
import json
from pathlib import Path
import re
import shutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
source=ROOT/'scripts/run_real_world_stackelberg_controller.vbs'
text=source.read_text(encoding='utf8')
block=re.search(r'(?ms)^Sub Obs150FlushErr\(T, barrier\).*?^End Sub',text).group()
native=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network'
out=HERE/'native_check_v3';out.mkdir(exist_ok=False)
for arm in ['baseline','barrier']:
    directory=out/arm;directory.mkdir();(directory/'eval').mkdir()
    shutil.copy2(native/'native_seed29.inpx',directory/'network.inpx')
    for sig in native.glob('*.sig'):shutil.copy2(sig,directory/sig.name)
script='''Option Explicit
Dim Vissim, fso, folder, useBarrier, target, t, errNo, detail, vi
Set fso=CreateObject("Scripting.FileSystemObject")
folder=WScript.Arguments(0) : useBarrier=(WScript.Arguments(1)="barrier")
Set Vissim=CreateObject("Vissim.Vissim.200")
WScript.Echo "COM_CREATED"
Vissim.AttValue("ShowMessages")=False
Vissim.LoadNet fso.BuildPath(folder,"network.inpx"),False
WScript.Echo "NETWORK_LOADED"
Vissim.Graphics.CurrentNetworkWindow.AttValue("QuickMode")=True
Vissim.Simulation.AttValue("RandSeed")=29
Vissim.Simulation.AttValue("SimRes")=10
Vissim.Simulation.AttValue("SimPeriod")=152
Vissim.Simulation.AttValue("UseMaxSimSpeed")=True
Vissim.Evaluation.AttValue("EvalOutDir")=fso.BuildPath(folder,"eval")
Vissim.Evaluation.AttValue("VehRecWriteFile")=True
Vissim.Evaluation.AttValue("VehRecFromTime")=0
Vissim.Evaluation.AttValue("VehRecToTime")=151
Vissim.Evaluation.AttValue("VehRecResolution")=50
Vissim.Evaluation.AttValue("VehRecFilterType")="ALL"
' Identical diagnostic traffic in both arms; this is not a gain/scenario trial.
For Each vi In Vissim.Net.VehicleInputs.GetAll
    vi.AttValue("Volume(1)")=300
    If vi.AttValue("Volume(1)")<>300 Then Obs150Abort 0,"INPUT_WRITE",CStr(vi.AttValue("No"))
Next
For Each target In Array(1,150,151)
    Vissim.Simulation.AttValue("SimBreakAt")=target
    Vissim.Simulation.RunContinuous
    t=Vissim.Simulation.AttValue("SimSec")
    If Abs(t-target)>0.00001 Then Obs150Abort target,"SIM_CLOCK",CStr(t)
    WScript.Echo "NATIVE_PROGRESS=" & t
    If useBarrier And target<151 Then
        Obs150FlushErr target,"OBS150_ERR_BARRIER_native115_" & target
        If Vissim.Simulation.AttValue("SimSec")<>t Then Obs150Abort target,"BARRIER_ADVANCED_SIM",""
        fso.CopyFile fso.BuildPath(folder,"network_001.err"),fso.BuildPath(folder,"err_at_" & target & ".snapshot"),False
    End If
Next
Vissim.Exit
WScript.Echo "COMPLETE151"
WScript.Quit 0
Sub Obs150Abort(t,stage,message)
    WScript.Echo "FAIL=" & stage & " " & message
    On Error Resume Next
    Vissim.Exit
    WScript.Quit 2
End Sub
'''+block+'\n'
(out/'check.vbs').write_text(script,encoding='ascii')
(out/'protocol.json').write_text(json.dumps(dict(period=152,stop_sec=151,seed=29,simres=10,fzp_sec=5,
    diagnostic_volume_veh_h_per_input=300,
    purpose='Logging-only physical parity, no SDMPC restart or gain trial',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    shipping_procedure_exact=True,network_sha256=hashlib.sha256((native/'native_seed29.inpx').read_bytes()).hexdigest()),indent=2)+'\n')
print(out)
