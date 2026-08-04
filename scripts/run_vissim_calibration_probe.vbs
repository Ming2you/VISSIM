Option Explicit

If WScript.Arguments.Count < 4 Then
    WScript.Echo "Usage: cscript run_vissim_calibration_probe.vbs <network.inpx> <state_csv> <segment_csv> <ramp_csv> [sim_period_sec] [urban_volume_vph] [freeway_volume_vph] [ramp_green_D_sec] [ramp_green_F_sec] [log_interval_sec] [rand_seed] [vsl_speed_kph] [major_green_sec] [minor_green_sec] [route_bias]"
    WScript.Quit 2
End If

Dim fso, Vissim, stateFile, segmentFile, rampFile, signalFile, urbanFile
Set fso = CreateObject("Scripting.FileSystemObject")

Dim netPath, stateOutPath, segmentOutPath, rampOutPath
Dim signalOutPath, urbanOutPath
Dim simPeriod, urbanVol, freewayVol, rampGreenD, rampGreenF, logInterval, randSeed, vslSpeed
Dim majorGreen, minorGreen, routeBias
netPath = WScript.Arguments(0)
stateOutPath = WScript.Arguments(1)
segmentOutPath = WScript.Arguments(2)
rampOutPath = WScript.Arguments(3)
signalOutPath = fso.BuildPath(fso.GetParentFolderName(stateOutPath), "signal_discharge.csv")
urbanOutPath = fso.BuildPath(fso.GetParentFolderName(stateOutPath), "urban_production.csv")
simPeriod = ArgOrDefault(4, 300)
urbanVol = ArgOrDefault(5, 60)
freewayVol = ArgOrDefault(6, 1200)
rampGreenD = ArgOrDefault(7, 10)
rampGreenF = ArgOrDefault(8, 10)
logInterval = ArgOrDefault(9, 10)
randSeed = ArgOrDefault(10, 42)
vslSpeed = ArgOrDefault(11, 120)
majorGreen = ArgOrDefault(12, 56)
minorGreen = ArgOrDefault(13, 56)
routeBias = UCase(ArgOrDefaultText(14, ""))

Dim URBAN_LINKS, FREEWAY_LINKS, RAMP_LINKS, BOUNDARY_LINKS, FREEWAY_INPUT_LINKS
URBAN_LINKS = "5,6,7,8,11,12,13,14,19,20,23,24,27,28"
FREEWAY_LINKS = "33,34"
RAMP_LINKS = "25,26,31,32"
BOUNDARY_LINKS = "1,2,3,4,9,10,15,16,17,18,21,22,29,30"
FREEWAY_INPUT_LINKS = "33,34"

Const MODE_NAME = "CALIBRATION_PROBE"
Const AMBER_SEC = 3
Const ALL_RED_SEC = 2
Const RAMP_CYCLE_SEC = 10
Const RAMP_AMBER_SEC = 1

Dim EB_BOUNDS, WB_BOUNDS, EB_IDS, WB_IDS
EB_BOUNDS = Array(1.0,499.0317957686363,812.3914617342674,1735.614696463941,2029.1497729629073,2900.003)
WB_BOUNDS = Array(1.0,537.7388621546322,1155.2495503139976,1743.4595824891098,2398.244756343526,2900.003)
EB_IDS = Array("EB_S0_W_ENTRY_TO_D_DIVERGE","EB_S1_D_DIVERGE_TO_D_MERGE","EB_S2_D_MERGE_TO_F_DIVERGE","EB_S3_F_DIVERGE_TO_F_MERGE","EB_S4_F_MERGE_TO_E_EXIT")
WB_IDS = Array("WB_S0_E_ENTRY_TO_F_DIVERGE","WB_S1_F_DIVERGE_TO_F_MERGE","WB_S2_F_MERGE_TO_D_DIVERGE","WB_S3_D_DIVERGE_TO_D_MERGE","WB_S4_D_MERGE_TO_W_EXIT")

Dim lastD, lastF, passCountD, passCountF, lastRampLogSec
Dim lastSignalPos, sigCounts, signalIntervalTotal
Dim SIG_LABELS, SIG_NODES, SIG_LINKS, SIG_POS
Set lastD = CreateObject("Scripting.Dictionary")
Set lastF = CreateObject("Scripting.Dictionary")
Set lastSignalPos = CreateObject("Scripting.Dictionary")
Set sigCounts = CreateObject("Scripting.Dictionary")
passCountD = 0
passCountF = 0
lastRampLogSec = 0
signalIntervalTotal = 0
InitSignalApproaches

EnsureParentFolder stateOutPath
EnsureParentFolder segmentOutPath
EnsureParentFolder rampOutPath
EnsureParentFolder signalOutPath
EnsureParentFolder urbanOutPath
Set stateFile = fso.CreateTextFile(stateOutPath, True)
Set segmentFile = fso.CreateTextFile(segmentOutPath, True)
Set rampFile = fso.CreateTextFile(rampOutPath, True)
Set signalFile = fso.CreateTextFile(signalOutPath, True)
Set urbanFile = fso.CreateTextFile(urbanOutPath, True)

stateFile.WriteLine "sim_sec,urban_volume_vph,freeway_volume_vph,ramp_green_D_sec,ramp_green_F_sec,vsl_speed_kph,total_vehicles,urban_vehicles,freeway_vehicles,ramp_vehicles,boundary_vehicles,other_vehicles,mean_speed_kph,freeway_mean_speed_kph,stopped_vehicles"
segmentFile.WriteLine "sim_sec,model_link,direction,segment_index,segment_id,count,speed_sum,mean_speed_kph,length_km,lanes,density_veh_km_lane,flow_proxy_veh_h"
rampFile.WriteLine "sim_sec,site,link,green_sec,cycle_sec,interval_sec,passage_count,release_rate_vph,queue_count,presence_count,downstream_count,mean_speed_kph"
signalFile.WriteLine "sim_sec,node,approach_label,link,stop_pos,interval_sec,discharge_count,discharge_rate_vph"
urbanFile.WriteLine "sim_sec,interval_sec,total_signal_discharge,total_signal_discharge_rate_vph,urban_vehicles,boundary_vehicles,ramp_vehicles,mean_speed_kph"

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

SetDemandVolumes urbanVol, freewayVol
ApplyRouteBias routeBias
ActivateSignalControllers
SetAllVslSpeeds vslSpeed
Vissim.Simulation.AttValue("RandSeed") = CLng(randSeed)
Vissim.Simulation.AttValue("SimPeriod") = CDbl(simPeriod) + 1
Vissim.Simulation.AttValue("SimRes") = 1

Vissim.Simulation.RunSingleStep
InitializeComSignalControl
ApplyRuntimeSignals 1
ApplyRuntimeRampMeters 1
UpdateCrossingCounts
LogAll 1

Dim stepNo
For stepNo = 2 To CLng(simPeriod)
    ApplyRuntimeSignals stepNo
    ApplyRuntimeRampMeters stepNo
    Vissim.Simulation.RunSingleStep
    UpdateCrossingCounts
    If stepNo Mod CLng(logInterval) = 0 Or stepNo = CLng(simPeriod) Then
        LogAll stepNo
        WScript.Echo "RUN_SINGLE_STEP sim_sec=" & CStr(stepNo)
    End If
Next

stateFile.Close
segmentFile.Close
rampFile.Close
signalFile.Close
urbanFile.Close

On Error Resume Next
Vissim.ResumeUpdateGUI True
Err.Clear
On Error GoTo 0

WScript.Echo "STAGE=SIM_DONE"
WScript.Echo "SIM_SEC=" & SafeAtt(Vissim.Simulation, "SimSec")
WScript.Echo "SIM_STEPS=" & simPeriod
WScript.Echo "STATE_CSV=" & stateOutPath
WScript.Echo "SEGMENT_CSV=" & segmentOutPath
WScript.Echo "RAMP_CSV=" & rampOutPath
WScript.Echo "SIGNAL_CSV=" & signalOutPath
WScript.Echo "URBAN_CSV=" & urbanOutPath

Set Vissim = Nothing
WScript.Quit 0

Sub InitSignalApproaches()
    SIG_LABELS = Array( _
        "A_L1","A_L3","A_L6","A_L8", _
        "B_L5","B_L9","B_L12","B_L14", _
        "C_L11","C_L15","C_L18","C_L20", _
        "D_L7","D_L21","D_L24","D_L26", _
        "F_L19","F_L27","F_L30","F_L32" _
    )
    SIG_NODES = Array( _
        "A","A","A","A", _
        "B","B","B","B", _
        "C","C","C","C", _
        "D","D","D","D", _
        "F","F","F","F" _
    )
    SIG_LINKS = Array( _
        1,3,6,8, _
        5,9,12,14, _
        11,15,18,20, _
        7,21,24,26, _
        19,27,30,32 _
    )
    SIG_POS = Array( _
        470.0,430.0,518.011,418.014, _
        518.011,430.0,518.011,418.014, _
        518.011,430.0,470.0,418.014, _
        418.014,470.0,518.011,172.883, _
        418.014,518.011,470.0,268.326 _
    )
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

Sub SetAllVslSpeeds(speedKph)
    Dim arr, dsd
    On Error Resume Next
    arr = Vissim.Net.DesSpeedDecisions.GetAll
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        Exit Sub
    End If
    On Error GoTo 0
    For Each dsd In arr
        SetClassSpeed dsd, 10, speedKph
        SetClassSpeed dsd, 20, speedKph
        SetClassSpeed dsd, 30, speedKph
    Next
End Sub

Sub SetClassSpeed(dsd, vehClassNo, speedKph)
    TrySetAtt dsd, "DesSpeedDistr(" & CStr(vehClassNo) & ")", CLng(speedKph)
End Sub

Sub ApplyRuntimeSignals(simSec)
    Dim scNo, pos, cycle, majorState, minorState
    cycle = majorGreen + AMBER_SEC + ALL_RED_SEC + minorGreen + AMBER_SEC + ALL_RED_SEC
    For scNo = 1 To 5
        pos = FMod(CDbl(simSec), cycle)
        If pos < majorGreen Then
            majorState = "GREEN": minorState = "RED"
        ElseIf pos < majorGreen + AMBER_SEC Then
            majorState = "AMBER": minorState = "RED"
        ElseIf pos < majorGreen + AMBER_SEC + ALL_RED_SEC Then
            majorState = "RED": minorState = "RED"
        ElseIf pos < majorGreen + AMBER_SEC + ALL_RED_SEC + minorGreen Then
            majorState = "RED": minorState = "GREEN"
        ElseIf pos < majorGreen + AMBER_SEC + ALL_RED_SEC + minorGreen + AMBER_SEC Then
            majorState = "RED": minorState = "AMBER"
        Else
            majorState = "RED": minorState = "RED"
        End If
        SetSignalGroupState scNo, 1, majorState
        SetSignalGroupState scNo, 2, minorState
    Next
End Sub

Sub ApplyRuntimeRampMeters(simSec)
    ApplyRampMeterSignal 6, CDbl(rampGreenD), simSec
    ApplyRampMeterSignal 7, CDbl(rampGreenF), simSec
End Sub

Sub ApplyRampMeterSignal(scNo, greenSec, simSec)
    Dim pos, state
    If greenSec >= RAMP_CYCLE_SEC Then
        state = "GREEN"
    ElseIf greenSec <= 0 Then
        state = "RED"
    Else
        pos = FMod(CDbl(simSec), RAMP_CYCLE_SEC)
        If pos < greenSec Then
            state = "GREEN"
        ElseIf pos < greenSec + RAMP_AMBER_SEC Then
            state = "AMBER"
        Else
            state = "RED"
        End If
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

Sub UpdateCrossingCounts()
    Dim laneArray, posArray, ok, lo, hi, i
    Dim linkNo, pos, key, newD, newF, newSignalPos, prev
    Dim idx, stopPos, label
    Set newD = CreateObject("Scripting.Dictionary")
    Set newF = CreateObject("Scripting.Dictionary")
    Set newSignalPos = CreateObject("Scripting.Dictionary")

    ok = ReadVehicleLanePos(laneArray, posArray)
    If Not ok Then
        Set lastD = newD
        Set lastF = newF
        Set lastSignalPos = newSignalPos
        Exit Sub
    End If

    lo = MultiLBound(laneArray)
    hi = MultiUBound(laneArray)
    For i = lo To hi
        linkNo = FirstInt(MultiValue(laneArray, i))
        pos = CDblOrZero(MultiValue(posArray, i))
        key = CStr(MultiKey(laneArray, i))

        If linkNo = 25 Or linkNo = 31 Then
            If key = "" Then key = CStr(linkNo) & "_" & Num(pos)
            If linkNo = 25 Then
                If lastD.Exists(key) Then
                    prev = CDbl(lastD.Item(key))
                    If prev < 175.883 And pos >= 175.883 Then passCountD = passCountD + 1
                End If
                newD(key) = pos
            ElseIf linkNo = 31 Then
                If lastF.Exists(key) Then
                    prev = CDbl(lastF.Item(key))
                    If prev < 271.326 And pos >= 271.326 Then passCountF = passCountF + 1
                End If
                newF(key) = pos
            End If
        End If

        idx = SignalIndexByLink(linkNo)
        If idx >= 0 Then
            stopPos = CDbl(SIG_POS(idx))
            label = CStr(SIG_LABELS(idx))
            key = CStr(MultiKey(laneArray, i)) & "_" & CStr(linkNo)
            If key = "_" & CStr(linkNo) Then key = CStr(linkNo) & "_" & Num(pos)
            If lastSignalPos.Exists(key) Then
                prev = CDbl(lastSignalPos.Item(key))
                If prev < stopPos And pos >= stopPos Then
                    IncDict sigCounts, label, 1
                    signalIntervalTotal = signalIntervalTotal + 1
                End If
            End If
            newSignalPos(key) = pos
        End If
    Next
    Set lastD = newD
    Set lastF = newF
    Set lastSignalPos = newSignalPos
End Sub

Function SignalIndexByLink(linkNo)
    Dim i
    SignalIndexByLink = -1
    For i = 0 To UBound(SIG_LINKS)
        If CLng(SIG_LINKS(i)) = CLng(linkNo) Then
            SignalIndexByLink = i
            Exit Function
        End If
    Next
End Function

Sub IncDict(dict, key, delta)
    If dict.Exists(key) Then
        dict(key) = CLng(dict(key)) + CLng(delta)
    Else
        dict(key) = CLng(delta)
    End If
End Sub

Sub LogAll(simSec)
    Dim total, urban, freeway, ramp, boundary, other, meanSpeed, freewayMeanSpeed, stopped
    Dim countE(4), speedE(4), countW(4), speedW(4)
    ComputeDetailedState total, urban, freeway, ramp, boundary, other, meanSpeed, freewayMeanSpeed, stopped, countE, speedE, countW, speedW
    stateFile.WriteLine CStr(simSec) & "," & Num(urbanVol) & "," & Num(freewayVol) & "," & Num(rampGreenD) & "," & Num(rampGreenF) & "," & Num(vslSpeed) & "," & _
        CStr(total) & "," & CStr(urban) & "," & CStr(freeway) & "," & CStr(ramp) & "," & CStr(boundary) & "," & CStr(other) & "," & _
        Num(meanSpeed) & "," & Num(freewayMeanSpeed) & "," & CStr(stopped)
    WriteSegmentRows simSec, "FW_E", "EB", EB_IDS, countE, speedE, EB_BOUNDS
    WriteSegmentRows simSec, "FW_W", "WB", WB_IDS, countW, speedW, WB_BOUNDS
    WriteRampRows simSec
    WriteSignalRows simSec
    WriteUrbanProductionRow simSec, urban, boundary, ramp, meanSpeed
End Sub

Sub WriteSegmentRows(simSec, modelLink, direction, ids, counts, speeds, bounds)
    Dim i, lengthKm, meanSpeed, density, flow
    For i = 0 To 4
        lengthKm = (CDbl(bounds(i + 1)) - CDbl(bounds(i))) / 1000.0
        meanSpeed = 0
        If CDbl(counts(i)) > 0 Then meanSpeed = CDbl(speeds(i)) / CDbl(counts(i))
        density = CDbl(counts(i)) / (lengthKm * 2.0)
        flow = density * meanSpeed * 2.0
        segmentFile.WriteLine CStr(simSec) & "," & modelLink & "," & direction & "," & CStr(i) & "," & ids(i) & "," & _
            CStr(counts(i)) & "," & Num(speeds(i)) & "," & Num(meanSpeed) & "," & Num(lengthKm) & ",2," & Num(density) & "," & Num(flow)
    Next
End Sub

Sub WriteRampRows(simSec)
    Dim intervalSec
    intervalSec = CDbl(simSec) - CDbl(lastRampLogSec)
    If intervalSec <= 0 Then intervalSec = CDbl(logInterval)

    Dim laneArray, posArray, speedArray, ok, lo, hi, i
    Dim linkNo, pos, speed
    Dim dq, dpres, ddown, dspeedSum, dspeedCount
    Dim fq, fpres, fdown, fspeedSum, fspeedCount
    dq = 0: dpres = 0: ddown = 0: dspeedSum = 0: dspeedCount = 0
    fq = 0: fpres = 0: fdown = 0: fspeedSum = 0: fspeedCount = 0

    ok = ReadVehicleLanePosSpeed(laneArray, posArray, speedArray)
    If ok Then
        lo = MultiLBound(laneArray)
        hi = MultiUBound(laneArray)
        For i = lo To hi
            linkNo = FirstInt(MultiValue(laneArray, i))
            If linkNo = 25 Or linkNo = 31 Then
                pos = CDblOrZero(MultiValue(posArray, i))
                speed = CDblOrZero(MultiValue(speedArray, i))
                If linkNo = 25 Then
                    dspeedSum = dspeedSum + speed
                    dspeedCount = dspeedCount + 1
                    If pos < 155.883 Then dq = dq + 1
                    If pos >= 145.883 And pos <= 160.883 Then dpres = dpres + 1
                    If pos > 175.883 Then ddown = ddown + 1
                ElseIf linkNo = 31 Then
                    fspeedSum = fspeedSum + speed
                    fspeedCount = fspeedCount + 1
                    If pos < 251.326 Then fq = fq + 1
                    If pos >= 241.326 And pos <= 256.326 Then fpres = fpres + 1
                    If pos > 271.326 Then fdown = fdown + 1
                End If
            End If
        Next
    End If

    WriteRampMetricRow simSec, "D", 25, CDbl(rampGreenD), intervalSec, passCountD, dq, dpres, ddown, dspeedSum, dspeedCount
    WriteRampMetricRow simSec, "F", 31, CDbl(rampGreenF), intervalSec, passCountF, fq, fpres, fdown, fspeedSum, fspeedCount
    passCountD = 0
    passCountF = 0
    lastRampLogSec = CDbl(simSec)
End Sub

Sub WriteSignalRows(simSec)
    Dim intervalSec, i, label, count, rate
    intervalSec = CDbl(logInterval)
    If CDbl(simSec) < CDbl(logInterval) Then intervalSec = CDbl(simSec)
    If intervalSec <= 0 Then intervalSec = 1
    For i = 0 To UBound(SIG_LABELS)
        label = CStr(SIG_LABELS(i))
        count = 0
        If sigCounts.Exists(label) Then count = CLng(sigCounts(label))
        rate = CDbl(count) / intervalSec * 3600.0
        signalFile.WriteLine CStr(simSec) & "," & CStr(SIG_NODES(i)) & "," & label & "," & CStr(SIG_LINKS(i)) & "," & Num(SIG_POS(i)) & "," & Num(intervalSec) & "," & CStr(count) & "," & Num(rate)
    Next
    sigCounts.RemoveAll
End Sub

Sub WriteUrbanProductionRow(simSec, urban, boundary, ramp, meanSpeed)
    Dim intervalSec, rate
    intervalSec = CDbl(logInterval)
    If CDbl(simSec) < CDbl(logInterval) Then intervalSec = CDbl(simSec)
    If intervalSec <= 0 Then intervalSec = 1
    rate = CDbl(signalIntervalTotal) / intervalSec * 3600.0
    urbanFile.WriteLine CStr(simSec) & "," & Num(intervalSec) & "," & CStr(signalIntervalTotal) & "," & Num(rate) & "," & CStr(urban) & "," & CStr(boundary) & "," & CStr(ramp) & "," & Num(meanSpeed)
    signalIntervalTotal = 0
End Sub

Sub WriteRampMetricRow(simSec, site, linkNo, greenSec, intervalSec, passageCount, countQueue, countPresence, countDownstream, speedSum, speedCount)
    Dim meanSpeed, releaseRate
    meanSpeed = 0
    If speedCount > 0 Then meanSpeed = speedSum / speedCount
    releaseRate = 0
    If intervalSec > 0 Then releaseRate = CDbl(passageCount) / CDbl(intervalSec) * 3600.0
    rampFile.WriteLine CStr(simSec) & "," & site & "," & CStr(linkNo) & "," & Num(greenSec) & "," & CStr(RAMP_CYCLE_SEC) & "," & Num(intervalSec) & "," & _
        CStr(passageCount) & "," & Num(releaseRate) & "," & CStr(countQueue) & "," & CStr(countPresence) & "," & CStr(countDownstream) & "," & Num(meanSpeed)
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
                seg = SegmentIndex(pos, EB_BOUNDS)
                countE(seg) = countE(seg) + 1
                speedE(seg) = speedE(seg) + speed
            ElseIf linkNo = 34 Then
                seg = SegmentIndex(pos, WB_BOUNDS)
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

Sub SetDemandVolumes(urbanVolume, freewayVolume)
    Dim viArray, vi, name, volume, linkNo
    viArray = Vissim.Net.VehicleInputs.GetAll
    For Each vi In viArray
        name = ""
        On Error Resume Next
        name = CStr(vi.AttValue("Name"))
        On Error GoTo 0
        linkNo = ObjectLinkNo(vi)
        If InCsvInt(linkNo, FREEWAY_INPUT_LINKS) Then
            volume = freewayVolume
        ElseIf linkNo = 0 And InStr(1, name, "VI_FW_", vbTextCompare) > 0 Then
            volume = freewayVolume
        Else
            volume = urbanVolume
        End If
        SetInputVolumeAllIntervals vi, CDbl(volume)
    Next
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

Function VehicleNo(veh)
    VehicleNo = SafeAtt(veh, "No")
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

Function MultiKey(arr, row)
    On Error Resume Next
    MultiKey = CStr(arr(row, LBound(arr, 2)))
    If Err.Number <> 0 Then
        MultiKey = ""
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

Sub EnsureParentFolder(path)
    Dim parent
    parent = fso.GetParentFolderName(path)
    If parent <> "" And Not fso.FolderExists(parent) Then
        EnsureParentFolder parent
        fso.CreateFolder parent
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
