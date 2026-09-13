Option Explicit
' LoadNet-only probe. No SetAttValue, SaveNet, simulation step, controller or model.
Dim sim, fs, output, failures, targets, allDecisions, allRoutes
Dim decision, route, link, behavior, decisionNo, linkNo, i, j
Dim fatalNumber, fatalDescription, inputPath, outputPath
If WScript.Arguments.Count <> 2 Then WScript.Quit 2
inputPath = WScript.Arguments(0)
outputPath = WScript.Arguments(1)
Set fs = CreateObject("Scripting.FileSystemObject")
If Not fs.FileExists(inputPath) Then WScript.Quit 2
If fs.FileExists(outputPath) Then WScript.Quit 3
' UTF-16 preserves localized COM errors without guessing the host ANSI codepage.
Set output = fs.CreateTextFile(outputPath, False, True)
output.WriteLine "kind,owner_no,item_no,attribute,value,vartype,error_number,error_description"
failures = 0
Set targets = CreateObject("Scripting.Dictionary")
For Each decisionNo In Array(1123,1124,1125,1134,1135,1136,1137,1116,1118,1119,1126,1138,1140)
    targets.Add CStr(decisionNo), True
Next
On Error Resume Next
Err.Clear
ReadNetwork
fatalNumber = Err.Number
fatalDescription = Err.Description
Err.Clear
On Error GoTo 0
If fatalNumber <> 0 Then
    failures = failures + 1
    output.WriteLine Csv("fatal") & ",0,0," & Csv("ReadNetwork") & "," & Csv("") & ",0," & _
        CStr(fatalNumber) & "," & Csv(fatalDescription)
End If
' Release child COM references before the application reference.
allRoutes = Empty
allDecisions = Empty
Set behavior = Nothing
Set route = Nothing
Set decision = Nothing
Set link = Nothing
Set targets = Nothing
Set sim = Nothing
output.Close
Set output = Nothing
WScript.Echo "ATTRIBUTE_FAILURES=" & CStr(failures)
If failures > 0 Then WScript.Quit 4
WScript.Echo "ROUTE_PROBE_DONE=1"
WScript.Quit 0

Sub ReadNetwork
    WScript.Echo "CREATING_OWNED_VISSIM"
    Set sim = CreateObject("Vissim.Vissim")
    sim.LoadNet inputPath, False
    WScript.Echo "NETWORK_LOADED_READ_ONLY=1"
    allDecisions = sim.Net.VehicleRoutingDecisionsStatic.GetAll
    For i = 0 To UBound(allDecisions)
        Set decision = allDecisions(i)
        decisionNo = decision.AttValue("No")
        ReadAttribute decision, "decision_index", decisionNo, decisionNo, "No"
        If targets.Exists(CStr(decisionNo)) Then
            ReadAttribute decision, "decision", decisionNo, decisionNo, "CombineStaRoutDec"
            ReadAttribute decision, "decision", decisionNo, decisionNo, "AllVehTypes"
            allRoutes = decision.VehRoutSta.GetAll
            For j = 0 To UBound(allRoutes)
                Set route = allRoutes(j)
                ReadAttribute route, "route", decisionNo, route.AttValue("No"), "RelFlow(1)"
            Next
            allRoutes = Empty
            Set route = Nothing
        End If
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
End Sub

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
