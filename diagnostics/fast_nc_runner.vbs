Option Explicit
' Native-only runner. --check compiles this entire file without creating COM.
If WScript.Arguments.Count = 1 Then
    If WScript.Arguments(0) = "--check" Then WScript.Echo "SYNTAX_OK": WScript.Quit 0
End If
If WScript.Arguments.Count <> 4 And WScript.Arguments.Count <> 5 Then WScript.Echo "Usage: network prepared output seed [terminal_sec]": WScript.Quit 2
Dim fs, sim, net, prepared, output, seed, terminalSec, logFile, vi, item, arr, volumes, tailVolumes, row, parts, key, count, before, target, sc
Set fs = CreateObject("Scripting.FileSystemObject")
net = WScript.Arguments(0): prepared = WScript.Arguments(1): output = WScript.Arguments(2): seed = CLng(WScript.Arguments(3))
terminalSec = 5400
If WScript.Arguments.Count = 5 Then terminalSec = CDbl(WScript.Arguments(4))
If terminalSec <> 5400 And terminalSec <> 7200 And terminalSec <> 9000 Then WScript.Echo "ERROR=Invalid terminal_sec": WScript.Quit 2
Set logFile = fs.CreateTextFile(fs.BuildPath(output, "readback.csv"), False, False)
logFile.WriteLine "kind,no,time_int,expected,actual"
Set volumes = CreateObject("Scripting.Dictionary")
Set tailVolumes = CreateObject("Scripting.Dictionary")
Set row = fs.OpenTextFile(fs.BuildPath(prepared,"demand.csv"),1)
If row.ReadLine <> "input_no,time_int,start_sec,before_vph,volume_vph" Then Die "Demand CSV schema"
Do Until row.AtEndOfStream
    parts = Split(row.ReadLine,",")
    If UBound(parts) <> 4 Then Die "Demand CSV width"
    key = parts(0) & ":" & parts(1)
    If volumes.Exists(key) Then Die "Duplicate demand key"
    volumes.Add key, Array(CDbl(parts(3)),CDbl(parts(4)))
    If parts(1) = "1-6" Then tailVolumes.Add parts(0), CDbl(parts(4))
Loop
row.Close
If volumes.Count <> 204 Then Die "Expected204 demand intervals"
If tailVolumes.Count <> 34 Then Die "Expected34 final-interval inputs"
Set sim = CreateObject("Vissim.Vissim")
WScript.Echo "STAGE=COM_CREATED"
sim.LoadNet net, False
WScript.Echo "STAGE=NET_LOADED"
Set row = fs.OpenTextFile(fs.BuildPath(prepared,"route_checks.csv"),1)
If row.ReadLine <> "route_no,rel_flow" Then Die "Route checks CSV schema"
Do Until row.AtEndOfStream
    parts=Split(row.ReadLine,",")
    Set item=sim.Net.VehicleRoutingDecisionsStatic.ItemByKey(1130).VehRoutSta.ItemByKey(CLng(parts(0)))
    target=CDbl(parts(1))
    before=CDbl(item.AttValue("RelFlow(1)"))
    If Abs(before-target)>0.0000001 Then Die "Native1130 RelFlow mismatch"
    logFile.WriteLine "route,1130:" & parts(0) & ",1," & CStr(target) & "," & CStr(before)
Loop
row.Close
On Error Resume Next
sim.Graphics.CurrentNetworkWindow.AttValue("QuickMode") = 1
sim.SuspendUpdateGUI
Err.Clear
On Error GoTo 0
arr = sim.Net.VehicleInputs.GetAll
count = 0
For Each vi In arr
    For Each item In vi.TimeIntVehVols.GetAll
        key = CStr(vi.AttValue("No")) & ":" & CStr(item.AttValue("TimeInt"))
        If Not volumes.Exists(key) Then Die "Unknown native demand interval " & key
        parts = volumes(key)
        before = CDbl(item.AttValue("Volume")): target = CDbl(parts(1))
        If Abs(before-CDbl(parts(0))) > 0.0000001 Then Die "Prepared/native input mismatch " & key
        item.AttValue("Volume") = target
        If Abs(CDbl(item.AttValue("Volume"))-target) > 0.001+Abs(target)*0.000001 Then Die "Demand readback mismatch " & key
        logFile.WriteLine "demand," & CStr(vi.AttValue("No")) & "," & CStr(item.AttValue("TimeInt")) & "," & CStr(target) & "," & CStr(item.AttValue("Volume"))
        volumes.Remove key: count = count + 1
    Next
Next
If count <> 204 Or volumes.Count <> 0 Then Die "Missing native demand interval"
SetChecked sim.Evaluation, "EvalOutDir", fs.BuildPath(output,"vissim_eval")
SetChecked sim.Evaluation, "ListAutoExportType", "FILE"
SetChecked sim.Evaluation, "VehRecWriteFile", True
SetChecked sim.Evaluation, "VehRecFromTime", 0
SetChecked sim.Evaluation, "VehRecToTime", terminalSec
SetChecked sim.Evaluation, "VehRecFilterType", "ALL"
SetChecked sim.Evaluation, "VehRecResolution", 1
SetChecked sim.Evaluation, "SigChangesWriteFile", True
' Keep the prior NC native collection settings; no result/queue/vehicle queries.
SetChecked sim.Evaluation, "LinkResCollectData", True
SetChecked sim.Evaluation, "LinkResFromTime", 0
SetChecked sim.Evaluation, "LinkResToTime", terminalSec
SetChecked sim.Evaluation, "LinkResInterval", 150
SetChecked sim.Evaluation, "LinkResPerLane", False
SetChecked sim.Evaluation, "QueuesCollectData", True
SetChecked sim.Evaluation, "QueuesFromTime", 0
SetChecked sim.Evaluation, "QueuesToTime", terminalSec
SetChecked sim.Evaluation, "QueuesInterval", 150
For count = 9101 To 9108
    Set sc = sim.Net.SignalControllers.ItemByKey(count)
    SetChecked sc, "Active", True
Next
SetChecked sim.Simulation, "RandSeed", seed
SetChecked sim.Simulation, "SimPeriod", terminalSec + 1
SetChecked sim.Simulation, "SimRes", 1
SetChecked sim.Simulation, "NumRuns", 1
SetChecked sim.Simulation, "UseMaxSimSpeed", True
If terminalSec > 5400 Then CheckTailDemand
sim.Simulation.RunSingleStep
If CDbl(sim.Simulation.AttValue("SimSec")) <> 1 Then Die "First step is not1"
WScript.Echo "SIM_SEC=1"
' Match original NC: native first second, then meters first, then all74 writes.
For count = 9101 To 9108
    Set sc = sim.Net.SignalControllers.ItemByKey(count)
    SetChecked sc.SGs.ItemByKey(1), "ContrByCOM", True
    SetChecked sc.SGs.ItemByKey(1), "SigState", "GREEN"
Next
ApplyAndCheckControls True
logFile.Close
SetChecked sim.Simulation, "SimBreakAt", terminalSec
WScript.Echo "STAGE=RUN_CONTINUOUS_BEGIN"
sim.Simulation.RunContinuous
If CDbl(sim.Simulation.AttValue("SimSec")) <> terminalSec Then Die "Terminal differs from requested horizon"
Set logFile = fs.OpenTextFile(fs.BuildPath(output,"readback.csv"),8)
ApplyAndCheckControls False
If terminalSec > 5400 Then CheckTailDemand
logFile.Close
WScript.Echo "STAGE=SIM_DONE"
WScript.Echo "SIM_SEC=" & CStr(terminalSec)
sim.Simulation.Stop
Set sc = Nothing: Set vi = Nothing: Set item = Nothing: arr = Empty
Set sim = Nothing
WScript.Quit 0

Sub CheckTailDemand()
    Dim intervals, interval, index, inputs, input, volume, no, actual, n
    intervals = sim.Net.TimeIntervalSets.ItemByKey(1).TimeInts.GetAll
    index = 0
    For Each interval In intervals
        If CDbl(interval.AttValue("Start")) <> index * 900 Then Die "Changed input interval schedule"
        index = index + 1
    Next
    If index <> 6 Then Die "Expected unchanged six input intervals"
    inputs = sim.Net.VehicleInputs.GetAll
    n = 0
    For Each input In inputs
        no = CStr(input.AttValue("No"))
        For Each volume In input.TimeIntVehVols.GetAll
            If CStr(volume.AttValue("TimeInt")) = "1-6" Then
                actual = CDbl(volume.AttValue("Volume"))
                If Abs(actual-tailVolumes(no)) > 0.001+Abs(tailVolumes(no))*0.000001 Then Die "Final demand interval changed"
                logFile.WriteLine "tail_demand," & no & ",1-6," & CStr(tailVolumes(no)) & "," & CStr(actual)
                n = n + 1
            End If
        Next
    Next
    If n <> 34 Then Die "Final demand interval coverage"
    WScript.Echo "TAIL_DEMAND_HOLD start_sec=4500 terminal_sec=" & CStr(terminalSec) & " inputs=34"
End Sub

Sub SetChecked(obj, attribute, value)
    Dim actual
    obj.AttValue(attribute) = value
    actual = obj.AttValue(attribute)
    If VarType(value) = vbBoolean Then
        If CBool(actual) <> value Then Die "Readback " & attribute
    ElseIf IsNumeric(value) Then
        If Abs(CDbl(actual)-CDbl(value)) > 0.0000001 Then Die "Readback " & attribute
    Else
        If CStr(actual) <> CStr(value) Then Die "Readback " & attribute
    End If
End Sub

Sub ApplyAndCheckControls(writeValues)
    Dim input, p, obj, n, cls, actual, nv, nm
    nv=0: nm=0
    Set input = fs.OpenTextFile(fs.BuildPath(prepared,"controls.csv"),1)
    If input.ReadLine <> "kind,no" Then Die "Controls CSV schema"
    Do Until input.AtEndOfStream
        p=Split(input.ReadLine,","): n=CLng(p(1))
        If p(0)="vsl" Then
            Set obj=sim.Net.DesSpeedDecisions.ItemByKey(n)
            For Each cls In Array(10,20,30,70)
                If writeValues Then SetChecked obj,"DesSpeedDistr(" & cls & ")",120
                actual=obj.AttValue("DesSpeedDistr(" & cls & ")")
                If CDbl(actual)<>120 Then Die "VSL persistence"
                logFile.WriteLine "vsl," & n & "," & cls & ",120," & CStr(actual)
            Next
            nv=nv+1
        ElseIf p(0)="meter" Then
            If n<9101 Or n>9108 Then Die "Meter identity"
            Set obj=sim.Net.SignalControllers.ItemByKey(n).SGs.ItemByKey(1)
            If writeValues Then SetChecked obj,"ContrByCOM",True
            If writeValues Then SetChecked obj,"SigState","GREEN"
            If Not CBool(obj.AttValue("ContrByCOM")) Then Die "Meter ownership"
            actual=obj.AttValue("SigState")
            If CStr(actual)<>"GREEN" Then Die "Meter persistence"
            logFile.WriteLine "meter," & n & ",1,GREEN," & CStr(actual)
            nm=nm+1
        Else
            Die "Non-NC command"
        End If
    Loop
    input.Close
    If nv<>66 Or nm<>8 Then Die "Expected66 VSL and8 meter commands"
End Sub

Sub Die(message)
    WScript.Echo "ERROR=" & message
    WScript.Quit 1
End Sub
