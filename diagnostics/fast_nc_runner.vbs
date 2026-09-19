Option Explicit
' Native-only runner. --check compiles this entire file without creating COM.
If WScript.Arguments.Count = 1 Then
    If WScript.Arguments(0) = "--check" Then WScript.Echo "SYNTAX_OK": WScript.Quit 0
End If
If WScript.Arguments.Count <> 4 And WScript.Arguments.Count <> 5 And WScript.Arguments.Count <> 6 Then WScript.Echo "Usage: network prepared output seed [terminal_sec] [native_preserve|fixed_profile]": WScript.Quit 2
Dim fs, sim, net, prepared, output, seed, terminalSec, logFile, vi, item, arr, volumes, tailVolumes, row, parts, key, count, before, target, sc, nativePreserve
Dim fixedProfile, fixedTrace, fixedExpected, fixedOwnership, fixedMeters, fixedEventCount, fixedBreakSec
Set fs = CreateObject("Scripting.FileSystemObject")
net = WScript.Arguments(0): prepared = WScript.Arguments(1): output = WScript.Arguments(2): seed = CLng(WScript.Arguments(3))
terminalSec = 5400
If WScript.Arguments.Count >= 5 Then terminalSec = CDbl(WScript.Arguments(4))
nativePreserve = False
fixedProfile = False
If WScript.Arguments.Count = 6 Then
    If WScript.Arguments(5) = "native_preserve" Then
        nativePreserve = True
    ElseIf WScript.Arguments(5) = "fixed_profile" Then
        fixedProfile = True
    Else
        WScript.Echo "ERROR=Invalid mode": WScript.Quit 2
    End If
End If
If terminalSec <> 5400 And terminalSec <> 7200 And terminalSec <> 9000 Then
    If Not fixedProfile Or (terminalSec <> 1050 And terminalSec <> 1800 And terminalSec <> 2250 And terminalSec <> 3000 And terminalSec <> 4500) Then WScript.Echo "ERROR=Invalid terminal_sec": WScript.Quit 2
End If
Set logFile = fs.CreateTextFile(fs.BuildPath(output, "readback.csv"), False, False)
logFile.WriteLine "kind,no,time_int,expected,actual"
If nativePreserve Or fixedProfile Then RunPreservedNative
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
ContinueToTerminal
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

Sub RunPreservedNative()
    Dim saved, fields, actual, checks, savedPeriod, effectivePeriod
    Set sim = CreateObject("Vissim.Vissim")
    WScript.Echo "STAGE=COM_CREATED"
    sim.LoadNet net, False
    WScript.Echo "STAGE=NET_LOADED"
    Set saved = fs.OpenTextFile(fs.BuildPath(prepared,"native_simulation.csv"),1)
    If saved.ReadLine <> "attribute,value" Then Die "Native simulation schema"
    checks = 0
    Do Until saved.AtEndOfStream
        fields = Split(saved.ReadLine,",")
        If UBound(fields) <> 1 Then Die "Native simulation row"
        actual = CDbl(sim.Simulation.AttValue(fields(0)))
        If actual <> CDbl(fields(1)) Then Die "Saved simulation differs: " & fields(0)
        logFile.WriteLine "native_simulation," & fields(0) & ",," & fields(1) & "," & CStr(actual)
        checks = checks + 1
    Loop
    saved.Close
    If (Not fixedProfile And checks <> 3) Or (fixedProfile And checks <> 4) Or CDbl(sim.Simulation.AttValue("RandSeed")) <> seed Then Die "Native simulation identity"
    On Error Resume Next
    sim.Graphics.CurrentNetworkWindow.AttValue("QuickMode") = 1
    sim.SuspendUpdateGUI
    Err.Clear
    On Error GoTo 0
    ' Recording only: no input, route, signal, meter, VSL, seed or SimRes writes.
    SetChecked sim.Evaluation, "EvalOutDir", fs.BuildPath(output,"vissim_eval")
    SetChecked sim.Evaluation, "ListAutoExportType", "FILE"
    SetChecked sim.Evaluation, "VehRecWriteFile", True
    SetChecked sim.Evaluation, "VehRecFromTime", 0
    SetChecked sim.Evaluation, "VehRecToTime", terminalSec
    SetChecked sim.Evaluation, "VehRecFilterType", "ALL"
    SetChecked sim.Evaluation, "VehRecResolution", 1
    SetChecked sim.Evaluation, "SigChangesWriteFile", True
    If fixedProfile Then
        savedPeriod = CDbl(sim.Simulation.AttValue("SimPeriod"))
        effectivePeriod = savedPeriod
        If savedPeriod <= terminalSec Then
            effectivePeriod = terminalSec + 1
            SetChecked sim.Simulation, "SimPeriod", effectivePeriod
        End If
        actual = CDbl(sim.Simulation.AttValue("SimPeriod"))
        If actual <> effectivePeriod Then Die "Fixed effective simulation period differs"
        logFile.WriteLine "fixed_simulation,SimPeriod,," & CStr(effectivePeriod) & "," & CStr(actual)
        WScript.Echo "FIXED_SIM_PERIOD_SAVED=" & CStr(savedPeriod)
        WScript.Echo "FIXED_SIM_PERIOD_EFFECTIVE=" & CStr(actual)
    Else
        If CDbl(sim.Simulation.AttValue("SimPeriod")) <> terminalSec + 1 Then SetChecked sim.Simulation, "SimPeriod", terminalSec + 1
    End If
    SetChecked sim.Simulation, "UseMaxSimSpeed", True
    SetChecked sim.Simulation, "SimBreakAt", terminalSec
    logFile.Close
    If fixedProfile Then
        RunFixedProfile
    Else
        WScript.Echo "NATIVE_PRESERVE=1"
        WScript.Echo "TRAFFIC_SETTING_WRITES=0"
        WScript.Echo "STAGE=RUN_CONTINUOUS_BEGIN"
        ContinueToTerminal
    End If
    WScript.Echo "STAGE=SIM_DONE"
    WScript.Echo "SIM_SEC=" & CStr(terminalSec)
    sim.Simulation.Stop
    Set saved = Nothing
    Set sim = Nothing
    WScript.Quit 0
End Sub

Sub ContinueToTerminal()
    Dim targetSec
    targetSec = terminalSec
    If fixedProfile Then targetSec = fixedBreakSec
    If fixedProfile Then SetChecked sim.Simulation, "SimBreakAt", targetSec
    sim.Simulation.RunContinuous
    If CDbl(sim.Simulation.AttValue("SimSec")) <> targetSec Then Die "Terminal differs from requested horizon"
End Sub

Sub RunFixedProfile()
    Dim input, fields, sec, previousSec, obj, address, value, actual, own
    Set fixedExpected = CreateObject("Scripting.Dictionary")
    Set fixedOwnership = CreateObject("Scripting.Dictionary")
    Set fixedMeters = CreateObject("Scripting.Dictionary")
    Set fixedTrace = fs.CreateTextFile(fs.BuildPath(output,"fixed_readback.csv"),False,False)
    fixedTrace.WriteLine "time_s,phase,kind,no,veh_class,expected,actual,contr_by_com,ok"
    fixedEventCount = 0
    FixedSnapshot "initial"
    WScript.Echo "FIXED_PROFILE=1"
    WScript.Echo "STAGE=RUN_CONTINUOUS_BEGIN"
    If fs.FileExists(fs.BuildPath(prepared,"rule_policy.json")) Then
        RunRuleProfile
    Else
        ApplyEventFile fs.BuildPath(prepared,"fixed_events.csv")
    End If
    fixedBreakSec = terminalSec
    ContinueToTerminal
    FixedSnapshot "final"
    fixedTrace.Close
    WScript.Echo "FIXED_EVENT_ROWS=" & CStr(fixedEventCount)
    WScript.Echo "FIXED_UNTARGETED_PRESERVATION=1"
End Sub

Sub ApplyEventFile(path)
    Dim input, fields, sec, previousSec, obj, address, value, actual, own
    Set input = fs.OpenTextFile(path,1)
    If input.ReadLine <> "time_s,kind,no,veh_class,value" Then Die "Fixed event CSV schema"
    previousSec = CDbl(sim.Simulation.AttValue("SimSec"))
    Do Until input.AtEndOfStream
        fields = Split(input.ReadLine,",")
        If UBound(fields) <> 4 Then Die "Fixed event CSV width"
        sec = CDbl(fields(0))
        If sec < previousSec Or sec <= 0 Or sec >= terminalSec Then Die "Fixed event time order"
        If sec > previousSec Then
            fixedBreakSec = sec
            ContinueToTerminal
            WScript.Echo "SIM_SEC=" & CStr(sec)
        End If
        previousSec = sec
        If fields(1) = "vsl" Then
            Set obj = sim.Net.DesSpeedDecisions.ItemByKey(CLng(fields(2)))
            value = CLng(fields(4))
            SetChecked obj, "DesSpeedDistr(" & fields(3) & ")", value
            actual = obj.AttValue("DesSpeedDistr(" & fields(3) & ")")
            address = fields(2) & ":" & fields(3)
            If Not fixedExpected.Exists(address) Then Die "Fixed event unknown DSD class"
            fixedExpected(address) = value
            fixedTrace.WriteLine CStr(sec) & ",write,vsl," & fields(2) & "," & fields(3) & "," & CStr(value) & "," & CStr(actual) & ",,1"
        ElseIf fields(1) = "meter" Then
            If CLng(fields(2)) < 9101 Or CLng(fields(2)) > 9108 Or fields(3) <> "1" Then Die "Fixed meter address"
            If fields(4) <> "RED" And fields(4) <> "GREEN" Then Die "Fixed meter RED/GREEN only"
            Set obj = sim.Net.SignalControllers.ItemByKey(CLng(fields(2))).SGs.ItemByKey(1)
            SetChecked obj, "ContrByCOM", True
            SetChecked obj, "SigState", fields(4)
            actual = obj.AttValue("SigState"): own = obj.AttValue("ContrByCOM")
            fixedMeters(fields(2) & ":1") = True
            fixedTrace.WriteLine CStr(sec) & ",write,meter," & fields(2) & ",1," & fields(4) & "," & CStr(actual) & "," & CStr(CBool(own)) & ",1"
        Else
            Die "Fixed event kind"
        End If
        fixedEventCount = fixedEventCount + 1
    Loop
    input.Close
End Sub

Sub RunRuleProfile()
    Dim settings, python, helper, startSec, sec, ids, input, mid, measurements, measurement
    Dim suffix, n, speed, occupancy, observation, shell, command, code, q
    Set settings = fs.OpenTextFile(fs.BuildPath(prepared,"rule_runtime.txt"),1,False,-1)
    python = settings.ReadLine: helper = settings.ReadLine: startSec = CLng(settings.ReadLine)
    settings.Close
    Set measurements = CreateObject("Scripting.Dictionary")
    Set input = fs.OpenTextFile(fs.BuildPath(prepared,"rule_measurements.csv"),1)
    If input.ReadLine <> "measurement" Then Die "Rule measurement schema"
    Do Until input.AtEndOfStream
        mid = input.ReadLine
        Set measurements(mid) = sim.Net.DataCollectionMeasurements.ItemByKey(CLng(mid))
    Loop
    input.Close
    Set shell = CreateObject("WScript.Shell")
    q = Chr(34)
    For sec = startSec To terminalSec - 1 Step 150
        fixedBreakSec = sec: ContinueToTerminal
        WScript.Echo "SIM_SEC=" & CStr(sec)
        suffix = "(Current," & CStr(sec \ 150) & ",All)"
        Set observation = fs.CreateTextFile(fs.BuildPath(output,"observation_" & CStr(sec) & ".csv"),False,False)
        observation.WriteLine "measurement,vehicles,speed,occupancy"
        For Each mid In measurements.Keys
            Set measurement = measurements(mid)
            n = measurement.AttValue("Vehs" & suffix)
            speed = measurement.AttValue("SpeedAvgArith" & suffix)
            occupancy = measurement.AttValue("OccupRate" & suffix)
            If IsNull(n) Or IsEmpty(n) Or Not IsNumeric(n) Then Die "Missing rule count"
            If CDbl(n) = 0 And (IsNull(speed) Or IsEmpty(speed)) Then speed = 0
            If IsNull(speed) Or IsEmpty(speed) Or Not IsNumeric(speed) Then Die "Missing rule speed"
            If IsNull(occupancy) Or IsEmpty(occupancy) Or Not IsNumeric(occupancy) Then Die "Missing rule occupancy"
            observation.WriteLine mid & "," & CStr(n) & "," & CStr(speed) & "," & CStr(occupancy)
        Next
        observation.Close
        If fs.FileExists(fs.BuildPath(prepared,"mpc_policy.json")) Then MpcVehicleSnapshot sec
        command = q & python & q & " -B -X utf8 " & q & helper & q & " --rule-step " & q & prepared & q & " " & q & output & q & " " & CStr(sec)
        code = shell.Run(command,0,True)
        If code <> 0 Then Die "Canonical rule calculation failed at " & CStr(sec)
        ApplyEventFile fs.BuildPath(output,"rule_events.csv")
    Next
End Sub

Sub MpcVehicleSnapshot(sec)
    Dim numbers, lanes, positions, speeds, i, snapshot
    'Four bulk reads at a control boundary only. First array column is row index,
    'not Vehicle.No; read the explicit number for native trajectory alignment.
    numbers = sim.Net.Vehicles.GetMultiAttValues("No")
    lanes = sim.Net.Vehicles.GetMultiAttValues("Lane")
    positions = sim.Net.Vehicles.GetMultiAttValues("Pos")
    speeds = sim.Net.Vehicles.GetMultiAttValues("Speed")
    Set snapshot = fs.CreateTextFile(fs.BuildPath(output,"mpc_vehicles_" & CStr(sec) & ".csv"),False,False)
    snapshot.WriteLine "vehicle,lane,position_m,speed_kmh"
    For i = LBound(lanes,1) To UBound(lanes,1)
        If lanes(i,0) <> numbers(i,0) Or lanes(i,0) <> positions(i,0) Or lanes(i,0) <> speeds(i,0) Then Die "MPC snapshot vehicle alignment"
        snapshot.WriteLine CStr(numbers(i,1)) & "," & CStr(lanes(i,1)) & "," & CStr(positions(i,1)) & "," & CStr(speeds(i,1))
    Next
    snapshot.Close
End Sub

Sub FixedSnapshot(phase)
    Dim input, fields, obj, address, expected, actual, own, sec
    sec = sim.Simulation.AttValue("SimSec")
    Set input = fs.OpenTextFile(fs.BuildPath(prepared,"fixed_initial.csv"),1)
    If input.ReadLine <> "time_s,kind,no,veh_class,value" Then Die "Fixed initial CSV schema"
    Do Until input.AtEndOfStream
        fields = Split(input.ReadLine,",")
        If UBound(fields) <> 4 Then Die "Fixed initial CSV width"
        address = fields(2) & ":" & fields(3)
        If fields(1) = "vsl" Then
            Set obj = sim.Net.DesSpeedDecisions.ItemByKey(CLng(fields(2)))
            actual = obj.AttValue("DesSpeedDistr(" & fields(3) & ")")
            If phase = "initial" Then fixedExpected(address) = CLng(fields(4))
            expected = fixedExpected(address)
            If CLng(actual) <> CLng(expected) Then Die "Fixed DSD snapshot differs"
            fixedTrace.WriteLine CStr(sec) & "," & phase & ",vsl," & fields(2) & "," & fields(3) & "," & CStr(expected) & "," & CStr(actual) & ",,1"
        ElseIf fields(1) = "signal" Then
            Set obj = sim.Net.SignalControllers.ItemByKey(CLng(fields(2))).SGs.ItemByKey(CLng(fields(3)))
            actual = obj.AttValue("SigState"): own = CBool(obj.AttValue("ContrByCOM"))
            If phase = "initial" Then
                fixedOwnership(address) = own
            ElseIf Not fixedMeters.Exists(address) Then
                If own <> fixedOwnership(address) Then Die "Untargeted SG ownership changed"
            Else
                If Not own Then Die "Targeted meter ownership lost"
            End If
            fixedTrace.WriteLine CStr(sec) & "," & phase & ",signal," & fields(2) & "," & fields(3) & ",READ," & CStr(actual) & "," & CStr(own) & ",1"
        Else
            Die "Fixed initial kind"
        End If
    Loop
    input.Close
End Sub
