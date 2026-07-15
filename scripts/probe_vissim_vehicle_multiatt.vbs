Option Explicit

If WScript.Arguments.Count < 1 Then
    WScript.Echo "Usage: cscript probe_vissim_vehicle_multiatt.vbs <network.inpx> [sim_sec]"
    WScript.Quit 2
End If

Dim netPath, simSec, Vissim
netPath = WScript.Arguments(0)
simSec = 10
If WScript.Arguments.Count >= 2 Then simSec = CLng(WScript.Arguments(1))

Set Vissim = CreateObject("Vissim.Vissim")
WScript.Echo "STAGE=COM_CREATED"
Vissim.LoadNet netPath, False
WScript.Echo "STAGE=NET_LOADED"

On Error Resume Next
Vissim.Graphics.CurrentNetworkWindow.AttValue("QuickMode") = 1
Vissim.SuspendUpdateGUI
Err.Clear
On Error GoTo 0

Vissim.Simulation.AttValue("RandSeed") = 13
Vissim.Simulation.AttValue("SimPeriod") = CDbl(simSec) + 1
Vissim.Simulation.AttValue("SimRes") = 1

Dim viArray, vi
On Error Resume Next
viArray = Vissim.Net.VehicleInputs.GetAll
If Err.Number = 0 Then
    For Each vi In viArray
        vi.AttValue("Volume(1)") = 1200
    Next
End If
Err.Clear
On Error GoTo 0

Dim i
For i = 1 To simSec
    Vissim.Simulation.RunSingleStep
Next

ProbeMulti "No"
ProbeMulti "Link"
ProbeMulti "Lane"
ProbeMulti "Pos"
ProbeMulti "Speed"

On Error Resume Next
Vissim.ResumeUpdateGUI True
Err.Clear
On Error GoTo 0

Set Vissim = Nothing
WScript.Quit 0

Sub ProbeMulti(attName)
    Dim arr, lb1, ub1, lb2, ub2, n, sampleCount, idx, msg
    On Error Resume Next
    arr = Vissim.Net.Vehicles.GetMultiAttValues(attName)
    If Err.Number <> 0 Then
        WScript.Echo "MULTI_FAIL att=" & attName & " err=" & Err.Description
        Err.Clear
        On Error GoTo 0
        Exit Sub
    End If
    lb1 = LBound(arr, 1)
    ub1 = UBound(arr, 1)
    lb2 = LBound(arr, 2)
    ub2 = UBound(arr, 2)
    If Err.Number <> 0 Then
        WScript.Echo "MULTI_FAIL_BOUNDS att=" & attName & " err=" & Err.Description
        Err.Clear
        On Error GoTo 0
        Exit Sub
    End If
    On Error GoTo 0
    n = ub1 - lb1 + 1
    sampleCount = n
    If sampleCount > 3 Then sampleCount = 3
    msg = "MULTI_OK att=" & attName & " rows=" & CStr(n) & " dim1=" & CStr(lb1) & ":" & CStr(ub1) & " dim2=" & CStr(lb2) & ":" & CStr(ub2)
    For idx = 0 To sampleCount - 1
        msg = msg & " sample" & CStr(idx + 1) & "=(" & CStr(arr(lb1 + idx, lb2)) & "," & CStr(arr(lb1 + idx, ub2)) & ")"
    Next
    WScript.Echo msg
End Sub
