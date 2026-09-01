Option Explicit

' Quick flow-through probe for the 8-seg extended mainline:
' runs a short sim and reports vehicle counts on entry/main/exit links.

If WScript.Arguments.Count < 1 Then
    WScript.Echo "Usage: cscript probe_8seg_flow.vbs <network.inpx> [simSec]"
    WScript.Quit 2
End If

Dim netPath, simSec
netPath = WScript.Arguments(0)
simSec = 240
If WScript.Arguments.Count >= 2 Then simSec = CLng(WScript.Arguments(1))

Dim Vissim
Set Vissim = CreateObject("Vissim.Vissim")
WScript.Echo "STAGE=COM_CREATED"
Vissim.LoadNet netPath, False
WScript.Echo "STAGE=NET_LOADED"

Vissim.Simulation.AttValue("SimPeriod") = simSec + 1
Vissim.Simulation.AttValue("SimRes") = 1
On Error Resume Next
Vissim.Graphics.CurrentNetworkWindow.AttValue("QuickMode") = 1
Vissim.SuspendUpdateGUI
Err.Clear
On Error GoTo 0

Dim stepNo
For stepNo = 1 To simSec
    Vissim.Simulation.RunSingleStep
Next
WScript.Echo "STAGE=SIM_DONE t=" & Vissim.Simulation.AttValue("SimSec")

Dim laneArray, counts, row, lo, hi, linkNo, key
Set counts = CreateObject("Scripting.Dictionary")
laneArray = Vissim.Net.Vehicles.GetMultiAttValues("Lane")
lo = LBound(laneArray, 1)
hi = UBound(laneArray, 1)
For row = lo To hi
    linkNo = FirstInt(CStr(laneArray(row, 1)))
    If counts.Exists(linkNo) Then
        counts(linkNo) = counts(linkNo) + 1
    Else
        counts.Add linkNo, 1
    End If
Next

WScript.Echo "TOTAL_VEHICLES=" & (hi - lo + 1)
Dim probeLinks, i
probeLinks = Array(35, 10074, 33, 10075, 36, 37, 10076, 34, 10077, 38)
For i = 0 To UBound(probeLinks)
    key = probeLinks(i)
    If counts.Exists(key) Then
        WScript.Echo "LINK_" & key & "=" & counts(key)
    Else
        WScript.Echo "LINK_" & key & "=0"
    End If
Next

Set Vissim = Nothing
WScript.Quit 0

Function FirstInt(text)
    Dim p
    p = InStr(1, text, "-")
    If p > 0 Then
        FirstInt = CLng(Left(text, p - 1))
    Else
        FirstInt = CLng(text)
    End If
End Function
