Option Explicit

If WScript.Arguments.Count < 1 Then
    WScript.Echo "Usage: cscript probe_com_signal_state_during_sim.vbs <network.inpx>"
    WScript.Quit 2
End If

Dim Vissim, netPath
netPath = WScript.Arguments(0)
Set Vissim = CreateObject("Vissim.Vissim")
WScript.Echo "STAGE=COM_CREATED"
Vissim.LoadNet netPath, False
WScript.Echo "STAGE=NET_LOADED"

Dim sc, sg1, sg2
Set sc = Vissim.Net.SignalControllers.ItemByKey(1)
TrySetAtt sc, "Active", True
Set sg1 = sc.SGs.ItemByKey(1)
Set sg2 = sc.SGs.ItemByKey(2)

Vissim.Simulation.AttValue("RandSeed") = 42
Vissim.Simulation.AttValue("SimPeriod") = 20
Vissim.Simulation.AttValue("SimRes") = 1
Vissim.Simulation.RunSingleStep
WScript.Echo "STAGE=SIM_STARTED SIM_SEC=" & Vissim.Simulation.AttValue("SimSec")

TrySetAtt sg1, "ContrByCOM", True
TrySetAtt sg2, "ContrByCOM", True

TryState sg1, "SigState", "GREEN"
TryState sg2, "SigState", "RED"
ReportState "after_green_red", sg1, sg2

Vissim.Simulation.RunSingleStep
ReportState "after_step_1", sg1, sg2

TryState sg1, "SigState", "AMBER"
TryState sg2, "SigState", "RED"
ReportState "after_amber_red", sg1, sg2

Vissim.Simulation.RunSingleStep
ReportState "after_step_2", sg1, sg2

TryState sg1, "SigState", "RED"
TryState sg2, "SigState", "GREEN"
ReportState "after_red_green", sg1, sg2

WScript.Echo "NOTE=Network was not saved."
Set Vissim = Nothing
WScript.Quit 0

Sub TryState(obj, att, value)
    On Error Resume Next
    obj.AttValue(att) = value
    If Err.Number <> 0 Then
        WScript.Echo "TRY_STATE " & SafeAtt(obj, "No") & " " & att & "=" & CStr(value) & " RESULT=FAIL ERR=" & Err.Description
        Err.Clear
    Else
        WScript.Echo "TRY_STATE " & SafeAtt(obj, "No") & " " & att & "=" & CStr(value) & " RESULT=OK"
    End If
    On Error GoTo 0
End Sub

Sub TrySetAtt(obj, att, value)
    On Error Resume Next
    obj.AttValue(att) = value
    If Err.Number <> 0 Then
        WScript.Echo "TRY_SET " & att & "=" & CStr(value) & " RESULT=FAIL ERR=" & Err.Description
        Err.Clear
    Else
        WScript.Echo "TRY_SET " & att & "=" & CStr(value) & " RESULT=OK"
    End If
    On Error GoTo 0
End Sub

Sub ReportState(label, a, b)
    WScript.Echo "STATE " & label & " SG1=" & SafeAtt(a, "SigState") & " COM1=" & SafeAtt(a, "ContrByCOM") & " SG2=" & SafeAtt(b, "SigState") & " COM2=" & SafeAtt(b, "ContrByCOM")
End Sub

Function SafeAtt(obj, att)
    On Error Resume Next
    SafeAtt = CStr(obj.AttValue(att))
    If Err.Number <> 0 Then
        SafeAtt = "ERR:" & Err.Description
        Err.Clear
    End If
    On Error GoTo 0
End Function
