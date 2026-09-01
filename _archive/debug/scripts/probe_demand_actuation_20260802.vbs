Option Explicit

' Demand actuation probe: does a COM demand scale actually change the vehicles
' that ENTER the network in every time interval, not just the warmup interval?
'
' Two arms are run in one process against the same network and seed, so the only
' difference is the scale factor. Cumulative entries are tracked by the highest
' vehicle number in the network, which VISSIM assigns sequentially as vehicles
' are generated; per-interval entries are its increment over that interval.
'
' Discriminator: interval 1 (0-900 s) was scaled by the old buggy code too, so it
' proves nothing. Intervals 2+ are the test. Old code -> ratio 1.00 there.
'
' Scaling DOWN (0.50) is used on purpose: a downscale can never be suppressed by
' network capacity, so a measured ratio that misses the target cannot be blamed
' on congestion.
'
' Pure ASCII. Usage:
'   cscript //nologo probe_demand_actuation_20260802.vbs <network.inpx> <out.csv> [simPeriodSec] [seed]

If WScript.Arguments.Count < 2 Then
    WScript.Echo "Usage: cscript probe_demand_actuation_20260802.vbs <network.inpx> <out.csv> [simPeriodSec] [seed]"
    WScript.Quit 2
End If

Dim netPath, outPath, simPeriod, seed, fso, outFile
netPath = WScript.Arguments(0)
outPath = WScript.Arguments(1)
simPeriod = 1800
If WScript.Arguments.Count >= 3 Then simPeriod = CLng(WScript.Arguments(2))
seed = 13
If WScript.Arguments.Count >= 4 Then seed = CLng(WScript.Arguments(3))

Set fso = CreateObject("Scripting.FileSystemObject")
Set outFile = fso.CreateTextFile(outPath, True)
outFile.WriteLine "scale,sim_sec,cum_entries,vehicles_in_network"

Dim Vissim
Set Vissim = CreateVissimCom()

' baseline / fixed all-interval write / old warmup-only write (counterfactual)
RunArm 1.0, "all", "base100"
RunArm 0.5, "all", "fixed050"
RunArm 0.5, "warmup", "oldbug050"

outFile.Close
Set Vissim = Nothing
WScript.Echo "PROBE_DONE out=" & outPath
WScript.Quit 0

Sub RunArm(scale, mode, armName)
    Dim i, maxNo, poll
    WScript.Echo "=== ARM name=" & armName & " scale=" & CStr(scale) & " mode=" & mode
    Vissim.LoadNet netPath, False
    On Error Resume Next
    Vissim.Graphics.CurrentNetworkWindow.AttValue("QuickMode") = 1
    Vissim.SuspendUpdateGUI
    Err.Clear
    On Error GoTo 0
    Vissim.Simulation.AttValue("RandSeed") = CLng(seed)
    Vissim.Simulation.AttValue("SimPeriod") = CDbl(simPeriod) + 1
    Vissim.Simulation.AttValue("SimRes") = 1

    ScaleAllInputsAllIntervals scale, mode

    poll = 60
    outFile.WriteLine armName & ",0,0,0"
    For i = 1 To simPeriod
        Vissim.Simulation.RunSingleStep
        If (i Mod poll) = 0 Then
            maxNo = MaxVehicleNo()
            outFile.WriteLine armName & "," & CStr(i) & "," & CStr(maxNo) & "," & CStr(VehicleCount())
        End If
    Next
    On Error Resume Next
    Vissim.Simulation.Stop
    Vissim.ResumeUpdateGUI True
    Err.Clear
    On Error GoTo 0
End Sub

' mode "all"    -> the all-interval write the fixed runner performs.
' mode "warmup" -> the old Volume(1)-only write, kept so the probe can show what
'                  the bug looked like instead of only asserting the fix works.
Sub ScaleAllInputsAllIntervals(scale, mode)
    Dim viArray, vi, arr, item, before, target, after, viNo, n, line
    viArray = Vissim.Net.VehicleInputs.GetAll
    For Each vi In viArray
        viNo = CStr(vi.AttValue("No"))
        arr = vi.TimeIntVehVols.GetAll
        n = 0
        line = ""
        For Each item In arr
            before = CDbl(item.AttValue("Volume"))
            If mode = "warmup" And n >= 1 Then
                target = before
            Else
                target = before * CDbl(scale)
            End If
            item.AttValue("Volume") = target
            after = CDbl(item.AttValue("Volume"))
            If Abs(after - target) > 0.001 + Abs(target) * 0.000001 Then
                WScript.Echo "ERROR=PROBE_READBACK_MISMATCH no=" & viNo & " target=" & Num(target) & " readback=" & Num(after)
                WScript.Quit 12
            End If
            n = n + 1
            If n > 1 Then line = line & ","
            line = line & Num(after)
        Next
        If viNo = "1098" Or viNo = "1099" Then
            WScript.Echo "PROBE_INPUT no=" & viNo & " intervals=" & CStr(n) & " after=" & line
        End If
    Next
End Sub

Function MaxVehicleNo()
    Dim arr, i, v, best
    best = 0
    On Error Resume Next
    arr = Vissim.Net.Vehicles.GetMultiAttValues("No")
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        MaxVehicleNo = 0
        Exit Function
    End If
    On Error GoTo 0
    For i = LBound(arr, 1) To UBound(arr, 1)
        v = CDbl(arr(i, 1))
        If v > best Then best = v
    Next
    MaxVehicleNo = CLng(best)
End Function

Function VehicleCount()
    VehicleCount = 0
    On Error Resume Next
    VehicleCount = Vissim.Net.Vehicles.Count
    If Err.Number <> 0 Then
        VehicleCount = 0
        Err.Clear
    End If
    On Error GoTo 0
End Function

Function CreateVissimCom()
    Dim progIds, i, obj
    progIds = Array("Vissim.Vissim", "Vissim.Vissim-64")
    For i = 0 To UBound(progIds)
        On Error Resume Next
        Set obj = CreateObject(progIds(i))
        If Err.Number = 0 Then
            Err.Clear
            On Error GoTo 0
            Set CreateVissimCom = obj
            Exit Function
        End If
        Err.Clear
        On Error GoTo 0
    Next
    WScript.Echo "ERROR=COM_CREATE_FAILED"
    WScript.Quit 3
End Function

Function Num(value)
    Num = Replace(FormatNumber(CDbl(value), 3, -1, 0, 0), ",", "")
End Function
