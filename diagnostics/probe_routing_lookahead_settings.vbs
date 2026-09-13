Option Explicit
' Read loaded engine settings before preparing a routing counterfactual.
' No SetAttValue, SaveNet, route deletion or simulation step is performed.
Dim sim, fs, output, failures, decisionNo, decision, routes, route, i, linkNo, link, behavior
If WScript.Arguments.Count <> 2 Then WScript.Quit 2
Set fs = CreateObject("Scripting.FileSystemObject")
If fs.FileExists(WScript.Arguments(1)) Then WScript.Quit 3
Set output = fs.CreateTextFile(WScript.Arguments(1), False, False)
output.WriteLine "kind,owner_no,item_no,attribute,value,vartype,error_number,error_description"
failures = 0
WScript.Echo "CREATING_OWNED_VISSIM"
Set sim = CreateObject("Vissim.Vissim")
sim.LoadNet WScript.Arguments(0), False
WScript.Echo "NETWORK_LOADED_READ_ONLY=1"
For Each decisionNo In Array(1123,1124,1125,1134,1135,1136,1137,1116,1118,1119,1126,1138,1140)
    Set decision = sim.Net.VehicleRoutingDecisionsStatic.ItemByKey(decisionNo)
    ReadAttribute decision, "decision", decisionNo, decisionNo, "CombineStaRoutDec"
    ReadAttribute decision, "decision", decisionNo, decisionNo, "AllVehTypes"
    routes = decision.VehRoutSta.GetAll
    For i = 0 To UBound(routes)
        Set route = routes(i)
        ReadAttribute route, "route", decisionNo, route.AttValue("No"), "RelFlow(1)"
    Next
Next
For Each linkNo In Array(10635,10643,10641,10700)
    Set link = sim.Net.Links.ItemByKey(linkNo)
    ReadAttribute link, "connector", linkNo, linkNo, "LnChgDist"
    ReadAttribute link, "connector", linkNo, linkNo, "LnChgDistIsPerLn"
    ReadAttribute link, "connector", linkNo, linkNo, "EmergStopDist"
Next
Set behavior = sim.Net.DrivingBehaviors.ItemByKey(1)
ReadAttribute behavior, "driving_behavior", 1, 1, "VehRoutDecLookAhead"
ReadAttribute behavior, "driving_behavior", 1, 1, "ConsNextTurn"
output.Close
Set behavior = Nothing
Set route = Nothing
Set decision = Nothing
Set link = Nothing
Set sim = Nothing
WScript.Echo "ATTRIBUTE_FAILURES=" & CStr(failures)
If failures > 0 Then WScript.Quit 4
WScript.Echo "ROUTE_PROBE_DONE=1"

Sub ReadAttribute(obj, kind, owner, item, name)
    Dim value, errorNumber, errorDescription
    On Error Resume Next
    Err.Clear
    value = obj.AttValue(name)
    errorNumber = Err.Number
    errorDescription = Err.Description
    Err.Clear
    On Error GoTo 0
    If errorNumber <> 0 Then failures = failures + 1
    output.WriteLine Csv(kind) & "," & CStr(owner) & "," & CStr(item) & "," & Csv(name) & "," & _
        Csv(value) & "," & CStr(VarType(value)) & "," & CStr(errorNumber) & "," & Csv(errorDescription)
End Sub

Function Csv(value)
    If IsNull(value) Then
        Csv = "<NULL>"
    ElseIf IsEmpty(value) Then
        Csv = "<EMPTY>"
    Else
        Csv = """" & Replace(CStr(value), """", """""") & """"
    End If
End Function
