Option Explicit
' Read-only route-attribute qualification on an owned native VISSIM instance.
' This is not a controller trial: original input volumes and native signals.
Dim sim, fs, output, stepNo, vehicles, rows, names, field, i, arrays(5), keys, key
Dim rowCount, value, laneParts, linkNo, selected, attrNo, stamps
If WScript.Arguments.Count <> 2 Then WScript.Quit 2
Set fs = CreateObject("Scripting.FileSystemObject")
If fs.FileExists(WScript.Arguments(1)) Then WScript.Quit 3
Set output = fs.CreateTextFile(WScript.Arguments(1), False, False)
output.WriteLine "sim_sec,veh_no,lane,pos_m,route_decision_no,route_no,route_decision_type,decision_vartype,route_vartype,type_vartype"
WScript.Echo "CREATING_OWNED_VISSIM"
Set sim = CreateObject("Vissim.Vissim")
sim.LoadNet WScript.Arguments(0), False
sim.Simulation.AttValue("RandSeed") = 13
sim.Simulation.AttValue("SimPeriod") = 1051
sim.Simulation.AttValue("SimRes") = 1
sim.Simulation.AttValue("UseMaxSimSpeed") = True
sim.Graphics.CurrentNetworkWindow.AttValue("QuickMode") = 1
names = Array("No", "Lane", "Pos", "RoutDecNo", "RouteNo", "RoutDecType")
For stepNo = 1 To 1050
    sim.Simulation.RunSingleStep
    If stepNo = 1 Or stepNo Mod 30 = 0 Then WScript.Echo "SIM_SEC=" & CStr(sim.Simulation.AttValue("SimSec"))
    If stepNo = 1 Or stepNo Mod 30 = 0 Or stepNo >= 600 Then
        rowCount = sim.Net.Vehicles.Count
        If rowCount > 0 Then
            For attrNo = 0 To UBound(names)
                arrays(attrNo) = sim.Net.Vehicles.GetMultiAttValues(names(attrNo))
                If UBound(arrays(attrNo), 1) + 1 <> rowCount Then WScript.Quit 4
            Next
            For i = 0 To rowCount - 1
                For attrNo = 1 To UBound(names)
                    If arrays(attrNo)(i, 0) <> arrays(0)(i, 0) Then WScript.Quit 5
                Next
                laneParts = Split(CStr(arrays(1)(i, 1)), "-")
                linkNo = laneParts(0)
                selected = InStr(",10627,10634,10632,56,10617,57,10621,", "," & linkNo & ",") > 0
                If selected Or (stepNo Mod 150 = 0 And i < 12) Then
                    output.WriteLine CStr(sim.Simulation.AttValue("SimSec")) & "," & _
                        Csv(arrays(0)(i,1)) & "," & Csv(arrays(1)(i,1)) & "," & Csv(arrays(2)(i,1)) & "," & _
                        Csv(arrays(3)(i,1)) & "," & Csv(arrays(4)(i,1)) & "," & Csv(arrays(5)(i,1)) & "," & _
                        CStr(VarType(arrays(3)(i,1))) & "," & CStr(VarType(arrays(4)(i,1))) & "," & CStr(VarType(arrays(5)(i,1)))
                End If
            Next
            If sim.Net.Vehicles.Count <> rowCount Then WScript.Quit 6
        End If
    End If
Next
output.Close
sim.Simulation.Stop
Set sim = Nothing
WScript.Echo "ROUTE_PROBE_DONE=1"

Function Csv(raw)
    If IsNull(raw) Then
        Csv = "<NULL>"
    ElseIf IsEmpty(raw) Then
        Csv = "<EMPTY>"
    Else
        Csv = """" & Replace(CStr(raw), """", """""") & """"
    End If
End Function
