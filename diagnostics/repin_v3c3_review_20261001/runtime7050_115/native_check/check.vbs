Option Explicit
Dim Vissim, fso, folder, useBarrier, target, t, errNo, detail
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
Vissim.Simulation.AttValue("SimPeriod")=151
Vissim.Simulation.AttValue("UseMaxSimSpeed")=True
Vissim.Evaluation.AttValue("EvalOutDir")=fso.BuildPath(folder,"eval")
Vissim.Evaluation.AttValue("VehRecWriteFile")=True
Vissim.Evaluation.AttValue("VehRecFromTime")=0
Vissim.Evaluation.AttValue("VehRecToTime")=151
Vissim.Evaluation.AttValue("VehRecResolution")=50
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
Sub Obs150FlushErr(T, barrier)
    Dim i, errNo, detail
    ' VISSIM2020 has no documented .err flush method. NOTE logging drains its
    ' buffered native warnings; Python must see this exact complete marker.
    ' No simulation step, traffic setting, or vehicle query is performed here.
    On Error Resume Next
    Err.Clear
    Vissim.Log 20480, barrier
    errNo = Err.Number : detail = Err.Description
    If errNo = 0 Then
        For i = 1 To 2
            Vissim.Log 20480, "OBS150_ERR_FLUSH_PADDING " & String(8192, "x")
            If Err.Number <> 0 Then
                errNo = Err.Number : detail = Err.Description
                Exit For
            End If
        Next
    End If
    On Error GoTo 0
    If errNo <> 0 Then Obs150Abort T, "ERR_BARRIER_WRITE", CStr(errNo) & " " & detail
End Sub
