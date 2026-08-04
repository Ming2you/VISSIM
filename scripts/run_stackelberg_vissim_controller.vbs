Option Explicit

If WScript.Arguments.Count < 4 Then
    WScript.Echo "Usage: cscript run_stackelberg_vissim_controller.vbs <network.inpx> <state_output.csv> <action_output.csv> <decision_dir> [sim_period_sec] [urban_volume_vph] [freeway_volume_vph] [control_interval_sec] [rand_seed] [adapter_py] [calibration_json] [tuning_json] [demand_profile] [controller]"
    WScript.Quit 2
End If

Dim fso, shell, stateFile, actionFile, Vissim
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

Dim netPath, stateOutPath, actionOutPath, decisionDir, simPeriod, urbanVol, freewayVol, controlInterval, randSeed, adapterPath, calibrationPath, tuningPath, demandProfile, controllerName
netPath = WScript.Arguments(0)
stateOutPath = WScript.Arguments(1)
actionOutPath = WScript.Arguments(2)
decisionDir = WScript.Arguments(3)
simPeriod = ArgOrDefault(4, 180)
urbanVol = ArgOrDefault(5, 60)
freewayVol = ArgOrDefault(6, 1200)
controlInterval = ArgOrDefault(7, 60)
randSeed = ArgOrDefault(8, 13)
adapterPath = ArgOrDefaultText(9, DefaultAdapterPath())
calibrationPath = ArgOrDefaultText(10, "evaluation/calibration/vissim_calibrated_overrides_vector_20260626.json")
tuningPath = ArgOrDefaultText(11, "")
demandProfile = LCase(ArgOrDefaultText(12, "sym"))
controllerName = LCase(Replace(ArgOrDefaultText(13, "stackelberg"), "_", "-"))
If IsControllerName(demandProfile) And controllerName = "stackelberg" Then
    controllerName = demandProfile
    If tuningPath <> "" And Not LooksLikeJsonPath(tuningPath) Then
        demandProfile = LCase(tuningPath)
        tuningPath = ""
    Else
        demandProfile = "sym"
    End If
End If

Dim URBAN_LINKS, FREEWAY_LINKS, RAMP_LINKS, BOUNDARY_LINKS, FREEWAY_INPUT_LINKS
URBAN_LINKS = "5,6,7,8,11,12,13,14,19,20,23,24,27,28"
FREEWAY_LINKS = "33,34"
RAMP_LINKS = "25,26,31,32"
BOUNDARY_LINKS = "1,2,3,4,9,10,15,16,17,18,21,22,29,30"
FREEWAY_INPUT_LINKS = "33,34"
Dim LOCAL_OBS_LINKS
LOCAL_OBS_LINKS = "1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34"

Dim MODE_NAME
MODE_NAME = "VISSIM_ADAPTER_" & UCase(controllerName)
Const AMBER_SEC = 3
Const ALL_RED_SEC = 2
Const RAMP_CYCLE_SEC = 10
Const RAMP_AMBER_SEC = 1

' Resolve and verify the controller interpreter BEFORE any VISSIM work. A bad
' interpreter here means every decision fails, so failing now costs seconds
' instead of surfacing after a multi-hour run. This runner has no generated
' config, so the config-constant slot is empty.
Dim RW_PYTHON_EXE, pythonExe, decisionsOk, decisionsFailed
RW_PYTHON_EXE = ""
pythonExe = ""
decisionsOk = 0
decisionsFailed = 0
ResolvePythonInterpreter

EnsureParentFolder stateOutPath
EnsureParentFolder actionOutPath
EnsureFolder decisionDir
Set stateFile = fso.CreateTextFile(stateOutPath, True)
Set actionFile = fso.CreateTextFile(actionOutPath, True)

stateFile.WriteLine "sim_sec,total_vehicles,urban_vehicles,freeway_vehicles,ramp_vehicles,boundary_vehicles,other_vehicles,mean_speed_kph,freeway_mean_speed_kph,stopped_vehicles,controller_mode,controller_status,decision_wall_sec"
actionFile.WriteLine "sim_sec,kind,id,dsd_no,sc_no,link,lane,speed_kph,major_green,minor_green,offset,rate_vph,green_sec,metadata,readback"

Dim sigMajor, sigMinor, sigOffset, rampGreen, lastActionJson
Set sigMajor = CreateObject("Scripting.Dictionary")
Set sigMinor = CreateObject("Scripting.Dictionary")
Set sigOffset = CreateObject("Scripting.Dictionary")
Set rampGreen = CreateObject("Scripting.Dictionary")
InitializeDefaultActionState
lastActionJson = ""

Set Vissim = CreateObject("Vissim.Vissim")
WScript.Echo "STAGE=COM_CREATED"
Vissim.LoadNet netPath, False
WScript.Echo "STAGE=NET_LOADED"
WScript.Echo "VERSION=" & SafeAtt(Vissim, "VERSION")
WScript.Echo "LINKS=" & Vissim.Net.Links.Count
WScript.Echo "VEHICLE_INPUTS=" & Vissim.Net.VehicleInputs.Count
WScript.Echo "SIGNAL_CONTROLLERS=" & Vissim.Net.SignalControllers.Count
WScript.Echo "DESSPEEDDECISIONS=" & Vissim.Net.DesSpeedDecisions.Count

On Error Resume Next
Vissim.Graphics.CurrentNetworkWindow.AttValue("QuickMode") = 1
Vissim.SuspendUpdateGUI
Err.Clear
On Error GoTo 0

SetDemandVolumes urbanVol, freewayVol, demandProfile
ApplyRouteBiasForDemandProfile demandProfile
ActivateSignalControllers
Vissim.Simulation.AttValue("RandSeed") = CLng(randSeed)
Vissim.Simulation.AttValue("SimPeriod") = CDbl(simPeriod) + 1
Vissim.Simulation.AttValue("SimRes") = 1

' Signal COM state writes become reliable after the simulation has started.
Vissim.Simulation.RunSingleStep
WScript.Echo "RUN_SINGLE_STEP sim_sec=1"
InitializeComSignalControl
RunControllerDecision 1
ApplyRuntimeSignals 1
ApplyRuntimeRampMeters 1
LogStateCsv 1

Dim stepNo
For stepNo = 2 To CLng(simPeriod)
    If stepNo Mod CLng(controlInterval) = 0 Then
        RunControllerDecision stepNo
    End If
    ApplyRuntimeSignals stepNo
    ApplyRuntimeRampMeters stepNo
    Vissim.Simulation.RunSingleStep
    If stepNo Mod 30 = 0 Or stepNo = CLng(simPeriod) Then
        WScript.Echo "RUN_SINGLE_STEP sim_sec=" & CStr(stepNo)
    End If
    If stepNo Mod 5 = 0 Or stepNo = CLng(simPeriod) Then
        LogStateCsv stepNo
    End If
Next

stateFile.Close
actionFile.Close

On Error Resume Next
Vissim.ResumeUpdateGUI True
Err.Clear
On Error GoTo 0

' The watchdog treats STAGE=SIM_DONE as success, so a run that produced no
' control at all must not print it - otherwise a silent no-control run is
' archived as a controller result.
WScript.Echo "DECISIONS_OK=" & CStr(decisionsOk)
WScript.Echo "DECISIONS_FAILED=" & CStr(decisionsFailed)
If decisionsOk = 0 And decisionsFailed > 0 Then
    WScript.Echo "ERROR=ALL_DECISIONS_FAILED decisions_failed=" & CStr(decisionsFailed) & " python=" & pythonExe
    Set Vissim = Nothing
    WScript.Quit 3
End If

WScript.Echo "STAGE=SIM_DONE"
WScript.Echo "SIM_SEC=" & SafeAtt(Vissim.Simulation, "SimSec")
WScript.Echo "SIM_STEPS=" & simPeriod
WScript.Echo "STATE_CSV=" & stateOutPath
WScript.Echo "ACTION_CSV=" & actionOutPath
WScript.Echo "DECISION_DIR=" & decisionDir

Set Vissim = Nothing
WScript.Quit 0

Sub InitializeDefaultActionState()
    Dim scNo
    For scNo = 1 To 5
        sigMajor(CStr(scNo)) = 40
        sigMinor(CStr(scNo)) = 40
        sigOffset(CStr(scNo)) = 0
    Next
    rampGreen("6") = 2
    rampGreen("7") = 2
End Sub

Sub ActivateSignalControllers()
    Dim no, sc
    For no = 1 To 7
        Set sc = Vissim.Net.SignalControllers.ItemByKey(CLng(no))
        TrySetAtt sc, "Active", True
    Next
End Sub

Sub InitializeComSignalControl()
    Dim scNo, sc, sgNo, sg
    For scNo = 1 To 5
        Set sc = Vissim.Net.SignalControllers.ItemByKey(CLng(scNo))
        For sgNo = 1 To 2
            Set sg = sc.SGs.ItemByKey(CLng(sgNo))
            TrySetAtt sg, "ContrByCOM", True
        Next
    Next
    For scNo = 6 To 7
        Set sc = Vissim.Net.SignalControllers.ItemByKey(CLng(scNo))
        Set sg = sc.SGs.ItemByKey(1)
        TrySetAtt sg, "ContrByCOM", True
    Next
End Sub

Sub RunControllerDecision(simSec)
    Dim stateJsonPath, outJsonPath, outCsvPath, cmd, result
    Dim wallT0, wallSec, exitCode, outText, errText
    stateJsonPath = fso.BuildPath(decisionDir, "state_" & Pad6(simSec) & ".json")
    outJsonPath = fso.BuildPath(decisionDir, "action_" & Pad6(simSec) & ".json")
    outCsvPath = fso.BuildPath(decisionDir, "action_" & Pad6(simSec) & ".csv")
    WriteStateJson simSec, stateJsonPath
    cmd = pythonExe & " " & Q(adapterPath) & " --state-json " & Q(stateJsonPath) & _
        " --out-action-json " & Q(outJsonPath) & " --out-action-csv " & Q(outCsvPath) & _
        " --controller " & Q(controllerName)
    If calibrationPath <> "" Then
        cmd = cmd & " --calibration-json " & Q(calibrationPath)
    End If
    If tuningPath <> "" Then
        cmd = cmd & " --tuning-json " & Q(tuningPath)
    End If
    If lastActionJson <> "" Then
        cmd = cmd & " --previous-action-json " & Q(lastActionJson)
    End If
    wallT0 = Timer
    exitCode = RunCapture3(cmd, outText, errText)
    wallSec = ElapsedSec(wallT0)
    result = "exit=" & exitCode & " stdout=" & OneLine(outText) & " stderr=" & OneLine(errText)
    WScript.Echo "CONTROLLER_DECISION sim_sec=" & simSec & " wall_sec=" & CStr(Round(wallSec, 2)) & " result=" & result
    ' A failed decision leaves the plant uncontrolled for this interval. That is
    ' an error, not a warning - see the DECISIONS_OK/DECISIONS_FAILED summary.
    If exitCode <> 0 Then
        decisionsFailed = decisionsFailed + 1
        WScript.Echo "ERROR=DECISION_EXIT_NONZERO sim_sec=" & simSec & " exit=" & exitCode & " stderr=" & OneLine(errText)
    ElseIf Not fso.FileExists(outCsvPath) Then
        decisionsFailed = decisionsFailed + 1
        WScript.Echo "ERROR=ACTION_CSV_MISSING sim_sec=" & simSec & " path=" & outCsvPath
    Else
        decisionsOk = decisionsOk + 1
        ApplyActionCsv simSec, outCsvPath
        lastActionJson = outJsonPath
    End If
End Sub

Sub ApplyActionCsv(simSec, csvPath)
    Dim ts, line, first, parts, kind, dsdNo, speed, dsd, readback, scNo
    Set ts = fso.OpenTextFile(csvPath, 1, False)
    first = True
    Do Until ts.AtEndOfStream
        line = ts.ReadLine
        If first Then
            first = False
        ElseIf Trim(line) <> "" Then
            parts = Split(line, ",")
            If UBound(parts) >= 12 Then
                kind = parts(0)
                readback = ""
                If kind = "vsl" Then
                    dsdNo = CLng(ToDbl(parts(2)))
                    speed = CDbl(ToDbl(parts(6)))
                    Set dsd = Vissim.Net.DesSpeedDecisions.ItemByKey(dsdNo)
                    SetClassSpeed dsd, 10, speed
                    SetClassSpeed dsd, 20, speed
                    SetClassSpeed dsd, 30, speed
                    readback = SafeAtt(dsd, "DesSpeedDistr(10)")
                ElseIf kind = "signal" Then
                    scNo = CStr(CLng(ToDbl(parts(3))))
                    sigMajor(scNo) = CDbl(ToDbl(parts(7)))
                    sigMinor(scNo) = CDbl(ToDbl(parts(8)))
                    sigOffset(scNo) = CDbl(ToDbl(parts(9)))
                    readback = "stored"
                ElseIf kind = "ramp_meter" Then
                    scNo = CStr(CLng(ToDbl(parts(3))))
                    rampGreen(scNo) = CDbl(ToDbl(parts(11)))
                    readback = "stored"
                End If
                actionFile.WriteLine CStr(simSec) & "," & Join(parts, ",") & "," & readback
            End If
        End If
    Loop
    ts.Close
End Sub

Sub SetClassSpeed(dsd, vehClassNo, speedKph)
    TrySetAtt dsd, "DesSpeedDistr(" & CStr(vehClassNo) & ")", CLng(speedKph)
End Sub

Sub ApplyRuntimeSignals(simSec)
    Dim scNo, major, minor, offset, cycle, pos, majorState, minorState
    For scNo = 1 To 5
        major = CDbl(sigMajor(CStr(scNo)))
        minor = CDbl(sigMinor(CStr(scNo)))
        offset = CDbl(sigOffset(CStr(scNo)))
        cycle = major + AMBER_SEC + ALL_RED_SEC + minor + AMBER_SEC + ALL_RED_SEC
        pos = FMod(CDbl(simSec) + offset, cycle)
        If pos < major Then
            majorState = "GREEN": minorState = "RED"
        ElseIf pos < major + AMBER_SEC Then
            majorState = "AMBER": minorState = "RED"
        ElseIf pos < major + AMBER_SEC + ALL_RED_SEC Then
            majorState = "RED": minorState = "RED"
        ElseIf pos < major + AMBER_SEC + ALL_RED_SEC + minor Then
            majorState = "RED": minorState = "GREEN"
        ElseIf pos < major + AMBER_SEC + ALL_RED_SEC + minor + AMBER_SEC Then
            majorState = "RED": minorState = "AMBER"
        Else
            majorState = "RED": minorState = "RED"
        End If
        SetSignalGroupState scNo, 1, majorState
        SetSignalGroupState scNo, 2, minorState
    Next
End Sub

Sub ApplyRuntimeRampMeters(simSec)
    ApplyRampMeterSignal 6, CDbl(rampGreen("6")), simSec
    ApplyRampMeterSignal 7, CDbl(rampGreen("7")), simSec
End Sub

Sub ApplyRampMeterSignal(scNo, greenSec, simSec)
    Dim pos, state
    pos = FMod(CDbl(simSec), RAMP_CYCLE_SEC)
    If greenSec <= 0 Then
        state = "RED"
    ElseIf pos < greenSec Then
        state = "GREEN"
    ElseIf pos < greenSec + RAMP_AMBER_SEC Then
        state = "AMBER"
    Else
        state = "RED"
    End If
    SetSignalGroupState scNo, 1, state
End Sub

Sub SetSignalGroupState(scNo, sgNo, state)
    Dim sc, sg
    Set sc = Vissim.Net.SignalControllers.ItemByKey(CLng(scNo))
    Set sg = sc.SGs.ItemByKey(CLng(sgNo))
    On Error Resume Next
    sg.AttValue("SigState") = state
    If Err.Number <> 0 Then
        WScript.Echo "WARN=FAILED_SET_SIGSTATE sc=" & scNo & " sg=" & sgNo & " state=" & state & " err=" & Err.Description
        Err.Clear
    End If
    On Error GoTo 0
End Sub

Sub WriteStateJson(simSec, path)
    Dim total, urban, freeway, ramp, boundary, other, meanSpeed, freewayMeanSpeed, stopped
    Dim countE(4), speedE(4), countW(4), speedW(4)
    Dim localCounts
    ComputeDetailedState total, urban, freeway, ramp, boundary, other, meanSpeed, freewayMeanSpeed, stopped, countE, speedE, countW, speedW
    Set localCounts = VehicleLinkCounts()

    Dim ts
    EnsureParentFolder path
    Set ts = New Utf8LineWriter
    ts.TargetPath = path
    ts.WriteLine "{"
    ts.WriteLine "  ""sim_sec"": " & Num(simSec) & ","
    ts.WriteLine "  ""sim_period_sec"": " & Num(simPeriod) & ","
    ts.WriteLine "  ""control_interval_sec"": " & Num(controlInterval) & ","
    ts.WriteLine "  ""total_vehicles"": " & CStr(total) & ","
    ts.WriteLine "  ""urban_vehicles"": " & CStr(urban) & ","
    ts.WriteLine "  ""freeway_vehicles"": " & CStr(freeway) & ","
    ts.WriteLine "  ""ramp_vehicles"": " & CStr(ramp) & ","
    ts.WriteLine "  ""boundary_vehicles"": " & CStr(boundary) & ","
    ts.WriteLine "  ""other_vehicles"": " & CStr(other) & ","
    ts.WriteLine "  ""mean_speed_kph"": " & Num(meanSpeed) & ","
    ts.WriteLine "  ""freeway_mean_speed_kph"": " & Num(freewayMeanSpeed) & ","
    ts.WriteLine "  ""stopped_vehicles"": " & CStr(stopped) & ","
    ts.WriteLine "  ""demand"": {""urban_volume_vph"": " & Num(urbanVol) & ", ""freeway_volume_vph"": " & Num(freewayVol) & ", ""ramp_volume_vph"": 250, ""demand_profile"": """ & JsonEscape(demandProfile) & """},"
    ts.WriteLine "  ""ramp_counts"": {""D"": " & DictCount(localCounts, 25) & ", ""F"": " & DictCount(localCounts, 31) & "},"
    ts.WriteLine "  ""local_observation"": {""schema_version"": 1, ""mode"": ""detector_local_v1"", ""source"": ""vehicle_scan_masked_by_detector_mapping"", ""global_vehicle_scan_masked"": true, ""link_counts"": " & RelevantLinkCountsJson(localCounts) & "},"
    ts.WriteLine "  ""freeway_segments"": {"
    ts.WriteLine "    ""FW_E"": " & SegmentArrayJson(countE, speedE, Array(1.0,499.0317957686363,812.3914617342674,1735.614696463941,2029.1497729629073,2900.003)) & ","
    ts.WriteLine "    ""FW_W"": " & SegmentArrayJson(countW, speedW, Array(1.0,537.7388621546322,1155.2495503139976,1743.4595824891098,2398.244756343526,2900.003))
    ts.WriteLine "  }"
    ts.WriteLine "}"
    ts.Close
End Sub

Function SegmentArrayJson(counts, speeds, bounds)
    Dim i, s, lengthKm
    s = "["
    For i = 0 To 4
        If i > 0 Then s = s & ", "
        lengthKm = (CDbl(bounds(i + 1)) - CDbl(bounds(i))) / 1000.0
        s = s & "{""count"": " & CStr(counts(i)) & ", ""speed_sum"": " & Num(speeds(i)) & ", ""length_km"": " & Num(lengthKm) & ", ""lanes"": 2}"
    Next
    s = s & "]"
    SegmentArrayJson = s
End Function

Sub LogStateCsv(simSec)
    Dim total, urban, freeway, ramp, boundary, other, meanSpeed, freewayMeanSpeed, stopped
    Dim countE(4), speedE(4), countW(4), speedW(4), status, wall
    ComputeDetailedState total, urban, freeway, ramp, boundary, other, meanSpeed, freewayMeanSpeed, stopped, countE, speedE, countW, speedW
    status = LastControllerStatus()
    wall = LastDecisionWallSec()
    stateFile.WriteLine CStr(simSec) & "," & CStr(total) & "," & CStr(urban) & "," & CStr(freeway) & "," & _
        CStr(ramp) & "," & CStr(boundary) & "," & CStr(other) & "," & Num(meanSpeed) & "," & _
        Num(freewayMeanSpeed) & "," & CStr(stopped) & "," & MODE_NAME & "," & status & "," & wall
End Sub

Sub ComputeDetailedState(ByRef total, ByRef urban, ByRef freeway, ByRef ramp, ByRef boundary, ByRef other, ByRef meanSpeed, ByRef freewayMeanSpeed, ByRef stopped, ByRef countE, ByRef speedE, ByRef countW, ByRef speedW)
    total = 0: urban = 0: freeway = 0: ramp = 0: boundary = 0: other = 0
    meanSpeed = 0: freewayMeanSpeed = 0: stopped = 0
    Dim i
    For i = 0 To 4
        countE(i) = 0: speedE(i) = 0
        countW(i) = 0: speedW(i) = 0
    Next

    Dim laneArray, posArray, speedArray, ok, lo, hi, row
    Dim linkNo, pos, speed, speedSum, freewaySpeedSum, seg
    speedSum = 0: freewaySpeedSum = 0

    ok = ReadVehicleLanePosSpeed(laneArray, posArray, speedArray)
    If Not ok Then
        Exit Sub
    End If

    lo = MultiLBound(laneArray)
    hi = MultiUBound(laneArray)
    For row = lo To hi
        total = total + 1
        linkNo = FirstInt(MultiValue(laneArray, row))
        pos = CDblOrZero(MultiValue(posArray, row))
        speed = CDblOrZero(MultiValue(speedArray, row))
        speedSum = speedSum + speed
        If speed < 1 Then stopped = stopped + 1

        If InCsvInt(linkNo, URBAN_LINKS) Then
            urban = urban + 1
        ElseIf InCsvInt(linkNo, FREEWAY_LINKS) Then
            freeway = freeway + 1
            freewaySpeedSum = freewaySpeedSum + speed
            If linkNo = 33 Then
                seg = SegmentIndex(pos, Array(1.0,499.0317957686363,812.3914617342674,1735.614696463941,2029.1497729629073,2900.003))
                countE(seg) = countE(seg) + 1
                speedE(seg) = speedE(seg) + speed
            ElseIf linkNo = 34 Then
                seg = SegmentIndex(pos, Array(1.0,537.7388621546322,1155.2495503139976,1743.4595824891098,2398.244756343526,2900.003))
                countW(seg) = countW(seg) + 1
                speedW(seg) = speedW(seg) + speed
            End If
        ElseIf InCsvInt(linkNo, RAMP_LINKS) Then
            ramp = ramp + 1
        ElseIf InCsvInt(linkNo, BOUNDARY_LINKS) Then
            boundary = boundary + 1
        Else
            other = other + 1
        End If
    Next
    If total > 0 Then meanSpeed = speedSum / total
    If freeway > 0 Then freewayMeanSpeed = freewaySpeedSum / freeway
End Sub

Function SegmentIndex(pos, bounds)
    Dim i
    SegmentIndex = 4
    For i = 0 To 4
        If CDbl(pos) < CDbl(bounds(i + 1)) Then
            SegmentIndex = i
            Exit Function
        End If
    Next
End Function

Function CountOnLink(linkNoTarget)
    Dim laneArray, posArray, ok, count, lo, hi, row
    count = 0
    ok = ReadVehicleLanePos(laneArray, posArray)
    If Not ok Then
        CountOnLink = 0
        Exit Function
    End If
    lo = MultiLBound(laneArray)
    hi = MultiUBound(laneArray)
    For row = lo To hi
        If FirstInt(MultiValue(laneArray, row)) = CLng(linkNoTarget) Then count = count + 1
    Next
    CountOnLink = count
End Function

Function VehicleLinkCounts()
    Dim counts, laneArray, posArray, ok, lo, hi, row, linkNo, key
    Set counts = CreateObject("Scripting.Dictionary")
    ok = ReadVehicleLanePos(laneArray, posArray)
    If ok Then
        lo = MultiLBound(laneArray)
        hi = MultiUBound(laneArray)
        For row = lo To hi
            linkNo = FirstInt(MultiValue(laneArray, row))
            If linkNo > 0 Then
                key = CStr(linkNo)
                If Not counts.Exists(key) Then counts.Add key, 0
                counts(key) = CLng(counts(key)) + 1
            End If
        Next
    End If
    Set VehicleLinkCounts = counts
End Function

Function DictCount(counts, linkNo)
    Dim key
    key = CStr(CLng(linkNo))
    If IsObject(counts) And counts.Exists(key) Then
        DictCount = CLng(counts(key))
    Else
        DictCount = 0
    End If
End Function

Function RelevantLinkCountsJson(counts)
    Dim parts, i, linkNo, s
    parts = Split(LOCAL_OBS_LINKS, ",")
    s = "{"
    For i = 0 To UBound(parts)
        If i > 0 Then s = s & ", "
        linkNo = CLng(parts(i))
        s = s & """" & CStr(linkNo) & """: " & CStr(DictCount(counts, linkNo))
    Next
    s = s & "}"
    RelevantLinkCountsJson = s
End Function

Sub SetDemandVolumes(urbanVolume, freewayVolume, profile)
    Dim viArray, vi, name, volume, linkNo
    viArray = Vissim.Net.VehicleInputs.GetAll
    For Each vi In viArray
        name = ""
        On Error Resume Next
        name = CStr(vi.AttValue("Name"))
        On Error GoTo 0
        linkNo = ObjectLinkNo(vi)
        volume = DemandVolumeForInput(linkNo, name, urbanVolume, freewayVolume, profile)
        SetInputVolumeAllIntervals vi, CDbl(volume)
    Next
End Sub

Function DemandVolumeForInput(linkNo, name, urbanVolume, freewayVolume, profile)
    Dim volume, p
    p = LCase(CStr(profile))
    If InCsvInt(linkNo, FREEWAY_INPUT_LINKS) Or (linkNo = 0 And InStr(1, name, "VI_FW_", vbTextCompare) > 0) Then
        volume = freewayVolume
    Else
        volume = urbanVolume
    End If

    If p = "fw_eb_heavy" Then
        If linkNo = 33 Or InStr(1, name, "VI_FW_E", vbTextCompare) > 0 Then
            volume = freewayVolume * 1.55
        ElseIf linkNo = 34 Or InStr(1, name, "VI_FW_W", vbTextCompare) > 0 Then
            volume = freewayVolume * 0.55
        End If
    ElseIf p = "fw_wb_heavy" Then
        If linkNo = 34 Or InStr(1, name, "VI_FW_W", vbTextCompare) > 0 Then
            volume = freewayVolume * 1.55
        ElseIf linkNo = 33 Or InStr(1, name, "VI_FW_E", vbTextCompare) > 0 Then
            volume = freewayVolume * 0.55
        End If
    ElseIf p = "urban_west_heavy" Then
        If linkNo = 1 Or linkNo = 21 Or InStr(1, name, "VI_A_W", vbTextCompare) > 0 Or InStr(1, name, "VI_D_W", vbTextCompare) > 0 Then
            volume = urbanVolume * 1.8
        ElseIf Not InCsvInt(linkNo, FREEWAY_INPUT_LINKS) Then
            volume = urbanVolume * 0.65
        End If
    ElseIf p = "urban_east_heavy" Then
        If linkNo = 18 Or linkNo = 30 Or InStr(1, name, "VI_C_E", vbTextCompare) > 0 Or InStr(1, name, "VI_F_E", vbTextCompare) > 0 Then
            volume = urbanVolume * 1.8
        ElseIf Not InCsvInt(linkNo, FREEWAY_INPUT_LINKS) Then
            volume = urbanVolume * 0.65
        End If
    ElseIf p = "urban_north_heavy" Then
        If linkNo = 3 Or linkNo = 9 Or linkNo = 15 Or InStr(1, name, "VI_A_N", vbTextCompare) > 0 Or InStr(1, name, "VI_B_N", vbTextCompare) > 0 Or InStr(1, name, "VI_C_N", vbTextCompare) > 0 Then
            volume = urbanVolume * 1.65
        ElseIf Not InCsvInt(linkNo, FREEWAY_INPUT_LINKS) Then
            volume = urbanVolume * 0.6
        End If
    ElseIf p = "urban_d_heavy" Then
        If linkNo = 21 Or InStr(1, name, "VI_D_W", vbTextCompare) > 0 Then
            volume = urbanVolume * 2.2
        ElseIf Not InCsvInt(linkNo, FREEWAY_INPUT_LINKS) Then
            volume = urbanVolume * 0.65
        End If
    ElseIf p = "urban_f_heavy" Then
        If linkNo = 30 Or InStr(1, name, "VI_F_E", vbTextCompare) > 0 Then
            volume = urbanVolume * 2.2
        ElseIf Not InCsvInt(linkNo, FREEWAY_INPUT_LINKS) Then
            volume = urbanVolume * 0.65
        End If
    End If
    DemandVolumeForInput = CDbl(volume)
End Function

Sub ApplyRouteBiasForDemandProfile(profile)
    Dim p
    p = LCase(CStr(profile))
    If p = "d_ramp_bias" Or p = "d_ramp_heavy" Then
        ApplyRouteBias "D_RAMP"
    ElseIf p = "f_ramp_bias" Or p = "f_ramp_heavy" Then
        ApplyRouteBias "F_RAMP"
    End If
End Sub

Sub ApplyRouteBias(bias)
    If bias = "" Or bias = "NONE" Then Exit Sub
    Dim targetLink
    If bias = "F_RAMP" Then
        targetLink = 31
    ElseIf bias = "D_RAMP" Then
        targetLink = 25
    Else
        WScript.Echo "WARN=UNKNOWN_ROUTE_BIAS bias=" & bias
        Exit Sub
    End If

    Dim rdArray, rd, routeArray, route, seq, boosted, suppressed
    boosted = 0
    suppressed = 0
    On Error Resume Next
    rdArray = Vissim.Net.VehicleRoutingDecisionsStatic.GetAll
    If Err.Number <> 0 Then
        WScript.Echo "WARN=ROUTE_BIAS_FAILED_GET_RD err=" & Err.Description
        Err.Clear
        On Error GoTo 0
        Exit Sub
    End If
    On Error GoTo 0

    For Each rd In rdArray
        On Error Resume Next
        routeArray = rd.VehRoutSta.GetAll
        If Err.Number <> 0 Then
            Err.Clear
            On Error GoTo 0
        Else
            On Error GoTo 0
            For Each route In routeArray
                seq = "," & SafeAtt(route, "LinkSeq") & ","
                If InStr(1, seq, "," & CStr(targetLink) & ",", vbTextCompare) > 0 Then
                    TrySetAtt route, "RelFlow(1)", 100.0
                    boosted = boosted + 1
                Else
                    TrySetAtt route, "RelFlow(1)", 0.01
                    suppressed = suppressed + 1
                End If
            Next
        End If
    Next
    WScript.Echo "ROUTE_BIAS=" & bias & " target_link=" & CStr(targetLink) & " boosted=" & CStr(boosted) & " suppressed=" & CStr(suppressed)
End Sub

Function LastControllerStatus()
    LastControllerStatus = "unknown"
    If lastActionJson <> "" And fso.FileExists(lastActionJson) Then
        Dim text
        text = ReadAllText(lastActionJson)
        LastControllerStatus = JsonFieldText(text, "controller_status")
    End If
End Function

Function LastDecisionWallSec()
    LastDecisionWallSec = ""
    If lastActionJson <> "" And fso.FileExists(lastActionJson) Then
        Dim text
        text = ReadAllText(lastActionJson)
        LastDecisionWallSec = JsonFieldNumber(text, "decision_wall_sec")
    End If
End Function

Function IsControllerName(value)
    Dim v
    v = LCase(Replace(CStr(value), "_", "-"))
    IsControllerName = (v = "stackelberg" Or v = "stackelberg-wu-metered" Or v = "pfo" Or v = "wu" Or v = "wu-leader" Or v = "no-control" Or v = "diagnostic-vsl-rm")
End Function

Function LooksLikeJsonPath(value)
    Dim v
    v = LCase(CStr(value))
    LooksLikeJsonPath = (Right(v, 5) = ".json" Or InStr(1, v, "\", vbTextCompare) > 0 Or InStr(1, v, "/", vbTextCompare) > 0)
End Function

Function JsonFieldText(text, fieldName)
    Dim pattern, p, q, r
    JsonFieldText = ""
    pattern = """" & fieldName & """:"
    p = InStr(1, text, pattern, vbTextCompare)
    If p <= 0 Then Exit Function
    q = InStr(p + Len(pattern), text, """")
    If q <= 0 Then Exit Function
    r = InStr(q + 1, text, """")
    If r <= 0 Then Exit Function
    JsonFieldText = Mid(text, q + 1, r - q - 1)
End Function

Function JsonFieldNumber(text, fieldName)
    Dim pattern, p, startPos, endPos, ch
    JsonFieldNumber = ""
    pattern = """" & fieldName & """:"
    p = InStr(1, text, pattern, vbTextCompare)
    If p <= 0 Then Exit Function
    startPos = p + Len(pattern)
    Do While startPos <= Len(text) And Mid(text, startPos, 1) = " "
        startPos = startPos + 1
    Loop
    endPos = startPos
    Do While endPos <= Len(text)
        ch = Mid(text, endPos, 1)
        If (ch >= "0" And ch <= "9") Or ch = "." Or ch = "-" Then
            endPos = endPos + 1
        Else
            Exit Do
        End If
    Loop
    JsonFieldNumber = Mid(text, startPos, endPos - startPos)
End Function

Function ReadAllText(path)
    Dim ts
    Set ts = fso.OpenTextFile(path, 1, False)
    ReadAllText = ts.ReadAll
    ts.Close
End Function

' ---------------------------------------------------------------------------
' Python interpreter resolution. Keep this block identical in the three
' controller runners:
'   scripts\run_real_world_stackelberg_controller.vbs
'   scripts\run_stackelberg_vissim_controller.vbs
'   scripts\run_stackelberg_vissim_controller_8seg.vbs
'
' 2026-08-01: the runners used to shell out to a bare "python". On this machine
' PATH resolves that to the Microsoft Store stub under
' %LOCALAPPDATA%\Microsoft\WindowsApps, which exits 9009 with "Python" on
' stderr. Every decision therefore failed, no action CSV was ever written, the
' failure was logged as WARN=ACTION_CSV_MISSING, and the run still ended with
' STAGE=SIM_DONE - a controller run silently degraded into a no-control run.
' The interpreter is now resolved and verified once before the simulation
' starts, and a failed decision is an ERROR that feeds a run-level summary.
' ---------------------------------------------------------------------------

Function RunnerEnvValue(name)
    Dim v
    v = ""
    On Error Resume Next
    v = CStr(shell.Environment("PROCESS")(CStr(name)))
    If Err.Number <> 0 Then
        v = ""
        Err.Clear
    End If
    On Error GoTo 0
    RunnerEnvValue = Trim(v)
End Function

Function OneLine(text)
    Dim s
    s = Replace(CStr(text), vbCrLf, " ")
    s = Replace(s, vbCr, " ")
    s = Replace(s, vbLf, " ")
    OneLine = Trim(s)
End Function

Function ElapsedSec(t0)
    Dim d
    d = Timer - CDbl(t0)
    If d < 0 Then d = d + 86400.0
    ElapsedSec = d
End Function

Function RunCapture3(cmd, ByRef outText, ByRef errText)
    Dim exec
    outText = ""
    errText = ""
    On Error Resume Next
    Set exec = shell.Exec(cmd)
    If Err.Number <> 0 Then
        errText = "EXEC_FAILED " & Err.Description
        Err.Clear
        On Error GoTo 0
        RunCapture3 = -1
        Exit Function
    End If
    On Error GoTo 0
    Do While exec.Status = 0
        WScript.Sleep 50
    Loop
    outText = exec.StdOut.ReadAll
    errText = exec.StdErr.ReadAll
    RunCapture3 = exec.ExitCode
End Function

Function IsPythonPathCandidate(cand)
    IsPythonPathCandidate = (InStr(cand, "\") > 0 Or InStr(cand, "/") > 0 Or LCase(Right(cand, 4)) = ".exe")
End Function

Function PythonCommandPrefix(cand)
    If IsPythonPathCandidate(cand) Then
        PythonCommandPrefix = """" & cand & """"
    Else
        PythonCommandPrefix = cand
    End If
End Function

Sub AddPythonCandidate(list, cand)
    Dim c
    c = Trim(CStr(cand))
    If c = "" Then Exit Sub
    ' The Store stub lives under ...\AppData\Local\Microsoft\WindowsApps and only
    ' exists to open the Store page. It must never be selected.
    If InStr(1, c, "\WindowsApps\", 1) > 0 Or InStr(1, c, "/WindowsApps/", 1) > 0 Then
        WScript.Echo "PYTHON_CANDIDATE_SKIPPED reason=windowsapps_stub path=" & c
        Exit Sub
    End If
    If IsPythonPathCandidate(c) Then
        If Not fso.FileExists(c) Then Exit Sub
    End If
    If list.Exists(LCase(c)) Then Exit Sub
    list.Add LCase(c), c
End Sub

Sub AddPythonWhereCandidates(list, exeName)
    Dim exitCode, outText, errText, lines, i
    exitCode = RunCapture3("cmd /c where " & exeName, outText, errText)
    If exitCode <> 0 Then Exit Sub
    lines = Split(Replace(outText, vbCrLf, vbLf), vbLf)
    For i = 0 To UBound(lines)
        AddPythonCandidate list, Trim(lines(i))
    Next
End Sub

Sub AddPythonDirCandidates(list, rootDir)
    Dim folder, child
    If Trim(CStr(rootDir)) = "" Then Exit Sub
    If Not fso.FolderExists(rootDir) Then Exit Sub
    Set folder = fso.GetFolder(rootDir)
    For Each child In folder.SubFolders
        AddPythonCandidate list, fso.BuildPath(child.Path, "python.exe")
    Next
End Sub

Function PythonCandidates()
    Dim list, home, localApp, condaPrefix
    Set list = CreateObject("Scripting.Dictionary")
    ' 1) explicit operator override
    AddPythonCandidate list, RunnerEnvValue("RW_PYTHON")
    ' 2) generated-config constant, when the loaded config carries one
    AddPythonCandidate list, RW_PYTHON_EXE
    ' 3) the conda environment this process was launched from
    condaPrefix = RunnerEnvValue("CONDA_PREFIX")
    If condaPrefix <> "" Then AddPythonCandidate list, fso.BuildPath(condaPrefix, "python.exe")
    ' 4) conda roots - the model stack is developed against a conda interpreter,
    '    so prefer one when it exists and passes the probe below
    home = RunnerEnvValue("USERPROFILE")
    If home <> "" Then
        AddPythonCandidate list, fso.BuildPath(home, "anaconda3\python.exe")
        AddPythonCandidate list, fso.BuildPath(home, "miniconda3\python.exe")
        AddPythonCandidate list, fso.BuildPath(home, "miniforge3\python.exe")
    End If
    AddPythonCandidate list, "C:\ProgramData\Anaconda3\python.exe"
    ' 5) whatever PATH resolves, minus the store stubs
    AddPythonWhereCandidates list, "python.exe"
    AddPythonWhereCandidates list, "python3.exe"
    ' 6) per-user and machine-wide CPython installs
    localApp = RunnerEnvValue("LOCALAPPDATA")
    If localApp <> "" Then AddPythonDirCandidates list, fso.BuildPath(localApp, "Programs\Python")
    AddPythonDirCandidates list, "C:\Program Files\Python"
    ' 7) the py launcher, last resort (a command, not a file path)
    AddPythonCandidate list, "py -3"
    PythonCandidates = list.Items
End Function

' Empty string on success, else a short reason. Loads the adapter as a module and
' pulls in the model repo, so a candidate that cannot reach the controller code
' is rejected here rather than at the first decision.
Function AdapterImportProbe(prefix)
    Dim absAdapter, adapterDir, moduleName, cmd, exitCode, outText, errText
    absAdapter = fso.GetAbsolutePathName(adapterPath)
    adapterDir = fso.GetParentFolderName(absAdapter)
    moduleName = fso.GetBaseName(absAdapter)
    cmd = prefix & " -c ""import sys;sys.path.insert(0,r'" & adapterDir & "');import " & moduleName & _
        " as m;m.repo_imports(m.DEFAULT_REPO_ROOT);print('ADAPTER_IMPORT_OK')"""
    exitCode = RunCapture3(cmd, outText, errText)
    If exitCode = 0 And InStr(outText, "ADAPTER_IMPORT_OK") > 0 Then
        AdapterImportProbe = ""
    Else
        AdapterImportProbe = "exit=" & exitCode & " err=" & OneLine(errText)
    End If
End Function

Sub ResolvePythonInterpreter()
    Dim cands, i, cand, prefix, exitCode, outText, errText, verText, probeErr
    If Not fso.FileExists(fso.GetAbsolutePathName(adapterPath)) Then
        WScript.Echo "ERROR=ADAPTER_NOT_FOUND path=" & adapterPath
        WScript.Quit 3
    End If
    cands = PythonCandidates()
    For i = 0 To UBound(cands)
        cand = cands(i)
        prefix = PythonCommandPrefix(cand)
        exitCode = RunCapture3(prefix & " --version", outText, errText)
        verText = OneLine(outText & " " & errText)
        If exitCode <> 0 Or InStr(1, verText, "Python 3", 1) <> 1 Then
            WScript.Echo "PYTHON_CANDIDATE_REJECTED reason=version path=" & cand & " exit=" & exitCode & " out=" & verText
        Else
            probeErr = AdapterImportProbe(prefix)
            If probeErr = "" Then
                pythonExe = prefix
                WScript.Echo "PYTHON=" & cand
                WScript.Echo "PYTHON_VERSION=" & verText
                WScript.Echo "PYTHON_ADAPTER_IMPORT=OK adapter=" & fso.GetAbsolutePathName(adapterPath)
                Exit Sub
            End If
            WScript.Echo "PYTHON_CANDIDATE_REJECTED reason=adapter_import path=" & cand & " " & probeErr
        End If
    Next
    WScript.Echo "ERROR=NO_USABLE_PYTHON candidates=" & CStr(UBound(cands) + 1) & _
        " hint=set RW_PYTHON to a python.exe that can import " & adapterPath
    WScript.Quit 3
End Sub

' The adapter reads the state JSON with encoding="utf-8" and this workspace path
' contains non-ASCII characters, so the state JSON must not go through the
' FileSystemObject ANSI text writer (CP949 on this machine). Writing it as ANSI
' made every decision die with UnicodeDecodeError - another failure the old
' WARN-only decision handling hid.
Class Utf8LineWriter
    Public TargetPath
    Private buf
    Private Sub Class_Initialize()
        buf = ""
    End Sub
    Public Sub WriteLine(text)
        buf = buf & CStr(text) & vbCrLf
    End Sub
    Public Sub Close()
        WriteUtf8NoBom TargetPath, buf
        buf = ""
    End Sub
End Class

Sub WriteUtf8NoBom(path, text)
    Dim textStream, binStream
    Set textStream = CreateObject("ADODB.Stream")
    textStream.Type = 2
    textStream.Charset = "utf-8"
    textStream.Open
    textStream.WriteText text
    ' ADODB emits a UTF-8 BOM that json.loads rejects, so copy out past it.
    textStream.Position = 3
    Set binStream = CreateObject("ADODB.Stream")
    binStream.Type = 1
    binStream.Open
    textStream.CopyTo binStream
    binStream.SaveToFile path, 2
    binStream.Close
    textStream.Close
End Sub

Function ReadAllTextUtf8(path)
    Dim st
    Set st = CreateObject("ADODB.Stream")
    st.Type = 2
    st.Charset = "utf-8"
    st.Open
    st.LoadFromFile path
    ReadAllTextUtf8 = st.ReadText
    st.Close
End Function

Function ReadVehicleLanePos(ByRef laneArray, ByRef posArray)
    ReadVehicleLanePos = False
    On Error Resume Next
    laneArray = Vissim.Net.Vehicles.GetMultiAttValues("Lane")
    posArray = Vissim.Net.Vehicles.GetMultiAttValues("Pos")
    If Err.Number <> 0 Then
        WScript.Echo "WARN=FAILED_GET_MULTI_LANE_POS err=" & Err.Description
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    On Error GoTo 0
    ReadVehicleLanePos = True
End Function

Function ReadVehicleLanePosSpeed(ByRef laneArray, ByRef posArray, ByRef speedArray)
    ReadVehicleLanePosSpeed = False
    On Error Resume Next
    laneArray = Vissim.Net.Vehicles.GetMultiAttValues("Lane")
    posArray = Vissim.Net.Vehicles.GetMultiAttValues("Pos")
    speedArray = Vissim.Net.Vehicles.GetMultiAttValues("Speed")
    If Err.Number <> 0 Then
        WScript.Echo "WARN=FAILED_GET_MULTI_LANE_POS_SPEED err=" & Err.Description
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    On Error GoTo 0
    ReadVehicleLanePosSpeed = True
End Function

Function MultiLBound(arr)
    On Error Resume Next
    MultiLBound = LBound(arr, 1)
    If Err.Number <> 0 Then
        MultiLBound = 0
        Err.Clear
    End If
    On Error GoTo 0
End Function

Function MultiUBound(arr)
    On Error Resume Next
    MultiUBound = UBound(arr, 1)
    If Err.Number <> 0 Then
        MultiUBound = -1
        Err.Clear
    End If
    On Error GoTo 0
End Function

Function MultiValue(arr, row)
    On Error Resume Next
    MultiValue = arr(row, UBound(arr, 2))
    If Err.Number <> 0 Then
        MultiValue = ""
        Err.Clear
    End If
    On Error GoTo 0
End Function

Function CDblOrZero(value)
    On Error Resume Next
    CDblOrZero = CDbl(value)
    If Err.Number <> 0 Then
        CDblOrZero = 0
        Err.Clear
    End If
    On Error GoTo 0
End Function

Function VehicleLinkNo(veh)
    Dim raw
    VehicleLinkNo = 0
    On Error Resume Next
    raw = veh.AttValue("Link")
    If Err.Number <> 0 Then
        Err.Clear
        raw = veh.AttValue("Lane")
    End If
    On Error GoTo 0
    VehicleLinkNo = FirstInt(raw)
End Function

Function VehiclePos(veh)
    VehiclePos = 0
    On Error Resume Next
    VehiclePos = CDbl(veh.AttValue("Pos"))
    If Err.Number <> 0 Then
        VehiclePos = 0
        Err.Clear
    End If
    On Error GoTo 0
End Function

Function VehicleSpeed(veh)
    VehicleSpeed = 0
    On Error Resume Next
    VehicleSpeed = CDbl(veh.AttValue("Speed"))
    If Err.Number <> 0 Then
        VehicleSpeed = 0
        Err.Clear
    End If
    On Error GoTo 0
End Function

Function ObjectLinkNo(obj)
    Dim raw
    ObjectLinkNo = 0
    On Error Resume Next
    raw = obj.AttValue("Link")
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    On Error GoTo 0
    ObjectLinkNo = FirstInt(raw)
End Function

Sub TrySetAtt(obj, att, value)
    On Error Resume Next
    obj.AttValue(att) = value
    If Err.Number <> 0 Then
        WScript.Echo "WARN=FAILED_SET_ATT att=" & att & " value=" & CStr(value) & " err=" & Err.Description
        Err.Clear
    End If
    On Error GoTo 0
End Sub

Function SafeAtt(obj, att)
    SafeAtt = ""
    On Error Resume Next
    SafeAtt = CStr(obj.AttValue(att))
    If Err.Number <> 0 Then
        SafeAtt = ""
        Err.Clear
    End If
    On Error GoTo 0
End Function

Function FirstInt(value)
    Dim text, i, ch, digits, started
    text = CStr(value)
    digits = ""
    started = False
    For i = 1 To Len(text)
        ch = Mid(text, i, 1)
        If ch >= "0" And ch <= "9" Then
            digits = digits & ch
            started = True
        ElseIf started Then
            Exit For
        End If
    Next
    If digits = "" Then
        FirstInt = 0
    Else
        FirstInt = CLng(digits)
    End If
End Function

Function InCsvInt(value, csv)
    InCsvInt = InStr(1, "," & csv & ",", "," & CStr(value) & ",", vbTextCompare) > 0
End Function

Function FMod(x, y)
    If CDbl(y) = 0 Then
        FMod = 0
    Else
        FMod = CDbl(x) - Int(CDbl(x) / CDbl(y)) * CDbl(y)
    End If
End Function

Function Num(value)
    Num = Replace(FormatNumber(CDbl(value), 6, -1, 0, 0), ",", "")
End Function

Function JsonEscape(value)
    Dim text
    text = CStr(value)
    text = Replace(text, Chr(92), Chr(92) & Chr(92))
    text = Replace(text, Chr(34), Chr(92) & Chr(34))
    JsonEscape = text
End Function

Function ToDbl(value)
    Dim text
    text = Trim(CStr(value))
    If text = "" Then
        ToDbl = 0
        Exit Function
    End If

    On Error Resume Next
    ToDbl = CDbl(text)
    If Err.Number <> 0 Then
        ToDbl = 0
        Err.Clear
    End If
    On Error GoTo 0
End Function

Function Pad6(value)
    Pad6 = Right("000000" & CStr(CLng(value)), 6)
End Function

Function Q(value)
    Q = """" & CStr(value) & """"
End Function

Function ArgOrDefault(index, defaultValue)
    If WScript.Arguments.Count > index Then
        ArgOrDefault = CDbl(WScript.Arguments(index))
    Else
        ArgOrDefault = defaultValue
    End If
End Function

Function ArgOrDefaultText(index, defaultValue)
    If WScript.Arguments.Count > index Then
        ArgOrDefaultText = CStr(WScript.Arguments(index))
    Else
        ArgOrDefaultText = defaultValue
    End If
End Function

Function DefaultAdapterPath()
    Dim scriptFolder
    scriptFolder = fso.GetParentFolderName(WScript.ScriptFullName)
    DefaultAdapterPath = fso.BuildPath(scriptFolder, "..\evaluation\controllers\vissim_stackelberg_adapter.py")
End Function

Sub EnsureParentFolder(path)
    Dim parent
    parent = fso.GetParentFolderName(path)
    If parent <> "" And Not fso.FolderExists(parent) Then
        EnsureParentFolder parent
        fso.CreateFolder parent
    End If
End Sub

Sub EnsureFolder(path)
    If path <> "" And Not fso.FolderExists(path) Then
        EnsureParentFolder path
        fso.CreateFolder path
    End If
End Sub

' Set the same volume on every VEHICLEINPUT time interval of this input.
' The networks these runners drive have a single time interval, so this is
' identical to the old Volume(1) write. It stays correct if the network ever
' gains intervals: Volume(1) is only the FIRST interval, and writing it alone
' silently leaves every later interval at its .inpx value. That exact bug hit
' run_real_world_stackelberg_controller.vbs (six intervals) before 2026-08-02.
Sub SetInputVolumeAllIntervals(vi, volume)
    Dim arr, item, n
    n = 0
    On Error Resume Next
    arr = vi.TimeIntVehVols.GetAll
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        TrySetAtt vi, "Volume(1)", CDbl(volume)
        Exit Sub
    End If
    On Error GoTo 0
    For Each item In arr
        TrySetAtt item, "Volume", CDbl(volume)
        n = n + 1
    Next
    If n = 0 Then TrySetAtt vi, "Volume(1)", CDbl(volume)
End Sub
