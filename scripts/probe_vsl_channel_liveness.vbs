Option Explicit
' probe_vsl_channel_liveness.vbs
' PURE ASCII ONLY.
'
' Purpose: prove by simulation whether every one of the 16 installed VSL channels
' (FW_E S0..S7, FW_W S0..S7) actually reaches the vehicles that drive through its
' segment. Each channel gets a unique ultra narrow desired speed distribution
' (fingerprint) injected by scripts/make_vsl_probe_network.py. During the run the
' probe samples (Lane, Pos, Speed, DesSpeed, VehType) for every vehicle on the
' freeway mainline chain and writes raw rows. Binning into segments is done twice:
'   1) here, with the SAME ChainPosCsv / SegmentIndexCsv code the state recorder in
'      run_real_world_stackelberg_controller.vbs uses (segment count csv), and
'   2) offline in scripts/analyze_vsl_channel_liveness.py from the raw rows.
' Comparing the two validates the state recorder's chain binning (in particular
' whether link 74 vehicles land in FW_E segments at all).
'
' Usage:
'   cscript //nologo probe_vsl_channel_liveness.vbs <net.inpx> <channels.csv> <chain.csv>
'       <out_vehicles.csv> <out_segments.csv> [sim_period_sec] [sample_start_sec]
'       [sample_interval_sec] [rand_seed]

If WScript.Arguments.Count < 5 Then
    WScript.Echo "Usage: cscript probe_vsl_channel_liveness.vbs <net.inpx> <channels.csv> <chain.csv> <out_vehicles.csv> <out_segments.csv> [sim_period_sec] [sample_start_sec] [sample_interval_sec] [rand_seed]"
    WScript.Quit 2
End If

Dim fso, Vissim
Set fso = CreateObject("Scripting.FileSystemObject")

Dim netPath, channelsPath, chainPath, vehOutPath, segOutPath
Dim simPeriod, sampleStart, sampleInterval, randSeed
netPath = WScript.Arguments(0)
channelsPath = WScript.Arguments(1)
chainPath = WScript.Arguments(2)
vehOutPath = WScript.Arguments(3)
segOutPath = WScript.Arguments(4)
simPeriod = CLng(ArgOrDefault(5, 900))
sampleStart = CLng(ArgOrDefault(6, 480))
sampleInterval = CLng(ArgOrDefault(7, 30))
randSeed = CLng(ArgOrDefault(8, 13))

' ---- channel table -------------------------------------------------------
Dim CH_COUNT
Dim chSegId(63), chModelLink(63), chSegIndex(63), chSegStart(63), chSegEnd(63)
Dim chHostLink(63), chDsdPos(63), chDsdNos(63), chDistrNo(63), chDistrSpeed(63)
CH_COUNT = 0
LoadChannels channelsPath

' ---- chain table ---------------------------------------------------------
Dim FW_E_CHAIN_LINKS, FW_E_CHAIN_OFFSETS, FW_E_SEG_BOUNDS
Dim FW_W_CHAIN_LINKS, FW_W_CHAIN_OFFSETS, FW_W_SEG_BOUNDS
FW_E_CHAIN_LINKS = "" : FW_E_CHAIN_OFFSETS = "" : FW_E_SEG_BOUNDS = ""
FW_W_CHAIN_LINKS = "" : FW_W_CHAIN_OFFSETS = "" : FW_W_SEG_BOUNDS = ""
LoadChain chainPath
If FW_E_SEG_BOUNDS = "" Or FW_W_SEG_BOUNDS = "" Then
    WScript.Echo "ERROR=CHAIN_CSV_INCOMPLETE path=" & chainPath
    WScript.Quit 2
End If
WScript.Echo "CHAIN FW_E links=" & FW_E_CHAIN_LINKS & " offsets=" & FW_E_CHAIN_OFFSETS
WScript.Echo "CHAIN FW_E bounds=" & FW_E_SEG_BOUNDS
WScript.Echo "CHAIN FW_W links=" & FW_W_CHAIN_LINKS & " offsets=" & FW_W_CHAIN_OFFSETS
WScript.Echo "CHAIN FW_W bounds=" & FW_W_SEG_BOUNDS

EnsureParentFolder vehOutPath
EnsureParentFolder segOutPath

Dim vehFile, segFile
Set vehFile = fso.CreateTextFile(vehOutPath, True)
vehFile.WriteLine "sim_sec,veh_no,link_no,lane_no,pos_m,speed_kph,des_speed_kph,veh_type"
Set segFile = fso.CreateTextFile(segOutPath, True)
segFile.WriteLine "sim_sec,model_link,seg_index,count,speed_sum"

Set Vissim = CreateVissimCom()
WScript.Echo "STAGE=COM_CREATED"
Vissim.LoadNet netPath, False
WScript.Echo "STAGE=NET_LOADED path=" & netPath

On Error Resume Next
Vissim.Graphics.CurrentNetworkWindow.AttValue("QuickMode") = 1
Vissim.SuspendUpdateGUI
Err.Clear
On Error GoTo 0

Vissim.Simulation.AttValue("RandSeed") = CLng(randSeed)
Vissim.Simulation.AttValue("SimPeriod") = CDbl(simPeriod) + 1
Vissim.Simulation.AttValue("SimRes") = 1
WScript.Echo "SIM_SETUP rand_seed=" & CStr(randSeed) & " sim_period=" & CStr(simPeriod) & _
    " sim_res=" & SafeAtt(Vissim.Simulation, "SimRes")
WScript.Echo "COUNTS DSD=" & Vissim.Net.DesSpeedDecisions.Count & " SC=" & Vissim.Net.SignalControllers.Count

' Inventory every desired speed decision that sits on a mainline chain link.
' A non RW decision downstream of an RW one silently overwrites the VSL, which is
' exactly the failure mode this probe is looking for.
InventoryChainDesSpeedDecisions

' Assign the fingerprint distributions. Vehicle classes 10/20/30/70, on purpose:
' that is what run_real_world_stackelberg_controller.vbs ApplyActionCsv does after
' the 2026-08-01 fix (class 70 = TAXI was folded into the VSL target set), so the
' probe measures the production wiring rather than an idealised one.
Dim ci, assignedOk, assignedFail
assignedOk = 0
assignedFail = 0
For ci = 0 To CH_COUNT - 1
    AssignChannel ci
Next
WScript.Echo "ASSIGN_SUMMARY ok=" & CStr(assignedOk) & " fail=" & CStr(assignedFail)

' ---- run ----------------------------------------------------------------
Dim currentSec, targetSec, sampleCount
Vissim.Simulation.RunSingleStep
currentSec = 1
sampleCount = 0
WScript.Echo "RUN_START sim_sec=1"

' Fail fast on attribute names instead of losing a whole run to a typo.
ProbeVehicleAttribute "No"
ProbeVehicleAttribute "Lane"
ProbeVehicleAttribute "Pos"
ProbeVehicleAttribute "Speed"
ProbeVehicleAttribute "DesSpeed"
ProbeVehicleAttribute "VehType"

Do While CLng(currentSec) < CLng(simPeriod)
    targetSec = NextSampleAfter(CLng(currentSec))
    If CLng(targetSec) > CLng(simPeriod) Then targetSec = CLng(simPeriod)
    RunContinuousTo CLng(targetSec)
    currentSec = CLng(targetSec)
    If CLng(currentSec) >= CLng(sampleStart) Then
        SampleVehicles CLng(currentSec)
        sampleCount = sampleCount + 1
    End If
Loop

WScript.Echo "RUN_DONE sim_sec=" & CStr(currentSec) & " samples=" & CStr(sampleCount)

' Read the assignments back at the end of the run: proves nothing rewrote them.
For ci = 0 To CH_COUNT - 1
    VerifyChannel ci
Next

vehFile.Close
segFile.Close

On Error Resume Next
Vissim.ResumeUpdateGUI True
Err.Clear
On Error GoTo 0
Set Vissim = Nothing
WScript.Echo "STAGE=DONE veh_csv=" & vehOutPath & " seg_csv=" & segOutPath
WScript.Quit 0

' =========================================================================

Sub LoadChannels(path)
    Dim ts, line, first, parts
    If Not fso.FileExists(path) Then
        WScript.Echo "ERROR=CHANNELS_CSV_MISSING path=" & path
        WScript.Quit 2
    End If
    Set ts = fso.OpenTextFile(path, 1, False)
    first = True
    Do Until ts.AtEndOfStream
        line = Trim(ts.ReadLine)
        If first Then
            first = False
        ElseIf line <> "" Then
            parts = Split(line, ",")
            chSegId(CH_COUNT) = Trim(parts(1))
            chModelLink(CH_COUNT) = Trim(parts(2))
            chSegIndex(CH_COUNT) = CLng(Trim(parts(3)))
            chSegStart(CH_COUNT) = CDbl(Trim(parts(4)))
            chSegEnd(CH_COUNT) = CDbl(Trim(parts(5)))
            chHostLink(CH_COUNT) = CLng(Trim(parts(6)))
            chDsdPos(CH_COUNT) = CDbl(Trim(parts(7)))
            chDsdNos(CH_COUNT) = Trim(parts(10))
            chDistrNo(CH_COUNT) = CLng(Trim(parts(11)))
            chDistrSpeed(CH_COUNT) = CDbl(Trim(parts(12)))
            CH_COUNT = CH_COUNT + 1
        End If
    Loop
    ts.Close
    WScript.Echo "CHANNELS_LOADED count=" & CStr(CH_COUNT)
End Sub

Sub LoadChain(path)
    Dim ts, line, first, parts, key
    If Not fso.FileExists(path) Then
        WScript.Echo "ERROR=CHAIN_CSV_MISSING path=" & path
        WScript.Quit 2
    End If
    Set ts = fso.OpenTextFile(path, 1, False)
    first = True
    Do Until ts.AtEndOfStream
        line = Trim(ts.ReadLine)
        If first Then
            first = False
        ElseIf line <> "" Then
            parts = Split(line, ",")
            key = Trim(parts(0))
            If key = "FW_E" Then
                FW_E_CHAIN_LINKS = Replace(Trim(parts(1)), ";", ",")
                FW_E_CHAIN_OFFSETS = Replace(Trim(parts(2)), ";", ",")
                FW_E_SEG_BOUNDS = Replace(Trim(parts(3)), ";", ",")
            ElseIf key = "FW_W" Then
                FW_W_CHAIN_LINKS = Replace(Trim(parts(1)), ";", ",")
                FW_W_CHAIN_OFFSETS = Replace(Trim(parts(2)), ";", ",")
                FW_W_SEG_BOUNDS = Replace(Trim(parts(3)), ";", ",")
            End If
        End If
    Loop
    ts.Close
End Sub

Sub InventoryChainDesSpeedDecisions()
    Dim allDsd, d, laneTxt, linkNo, dsdNo, pos, nameTxt, isChain
    On Error Resume Next
    allDsd = Vissim.Net.DesSpeedDecisions.GetAll
    If Err.Number <> 0 Then
        WScript.Echo "WARN=DSD_GETALL_FAILED err=" & Err.Description
        Err.Clear
        On Error GoTo 0
        Exit Sub
    End If
    On Error GoTo 0
    For Each d In allDsd
        laneTxt = CStr(SafeAtt(d, "Lane"))
        linkNo = FirstInt(laneTxt)
        isChain = InCsvInt(linkNo, FW_E_CHAIN_LINKS) Or InCsvInt(linkNo, FW_W_CHAIN_LINKS)
        If isChain Then
            dsdNo = CStr(SafeAtt(d, "No"))
            pos = CStr(SafeAtt(d, "Pos"))
            nameTxt = CStr(SafeAtt(d, "Name"))
            WScript.Echo "CHAIN_DSD no=" & dsdNo & " lane=" & laneTxt & " pos=" & pos & _
                " name=" & nameTxt & " distr10=" & CStr(SafeAtt(d, "DesSpeedDistr(10)")) & _
                " distr20=" & CStr(SafeAtt(d, "DesSpeedDistr(20)")) & _
                " distr30=" & CStr(SafeAtt(d, "DesSpeedDistr(30)")) & _
                " distr70=" & CStr(SafeAtt(d, "DesSpeedDistr(70)"))
        End If
    Next
End Sub

Sub AssignChannel(idx)
    Dim nos, i, dsdNo, dsd, okAll, rb
    nos = Split(chDsdNos(idx), ";")
    okAll = True
    For i = 0 To UBound(nos)
        If Trim(nos(i)) <> "" Then
            dsdNo = CLng(Trim(nos(i)))
            On Error Resume Next
            Set dsd = Vissim.Net.DesSpeedDecisions.ItemByKey(dsdNo)
            If Err.Number <> 0 Then
                WScript.Echo "ERROR=DSD_NOT_FOUND no=" & CStr(dsdNo) & " channel=" & chSegId(idx)
                Err.Clear
                okAll = False
                On Error GoTo 0
            Else
                On Error GoTo 0
                TrySetAtt dsd, "DesSpeedDistr(10)", CLng(chDistrNo(idx))
                TrySetAtt dsd, "DesSpeedDistr(20)", CLng(chDistrNo(idx))
                TrySetAtt dsd, "DesSpeedDistr(30)", CLng(chDistrNo(idx))
                TrySetAtt dsd, "DesSpeedDistr(70)", CLng(chDistrNo(idx))
                rb = CStr(SafeAtt(dsd, "DesSpeedDistr(10)")) & "|" & CStr(SafeAtt(dsd, "DesSpeedDistr(70)"))
                If FirstInt(CStr(SafeAtt(dsd, "DesSpeedDistr(10)"))) <> CLng(chDistrNo(idx)) Then okAll = False
                If FirstInt(CStr(SafeAtt(dsd, "DesSpeedDistr(70)"))) <> CLng(chDistrNo(idx)) Then okAll = False
                WScript.Echo "ASSIGN channel=" & chSegId(idx) & " dsd=" & CStr(dsdNo) & _
                    " distr=" & CStr(chDistrNo(idx)) & " readback=" & rb
            End If
        End If
    Next
    If okAll Then
        assignedOk = assignedOk + 1
    Else
        assignedFail = assignedFail + 1
    End If
End Sub

Sub VerifyChannel(idx)
    Dim nos, i, dsdNo, dsd, rb
    nos = Split(chDsdNos(idx), ";")
    For i = 0 To UBound(nos)
        If Trim(nos(i)) <> "" Then
            dsdNo = CLng(Trim(nos(i)))
            On Error Resume Next
            Set dsd = Vissim.Net.DesSpeedDecisions.ItemByKey(dsdNo)
            If Err.Number = 0 Then
                rb = CStr(SafeAtt(dsd, "DesSpeedDistr(10)")) & "|" & CStr(SafeAtt(dsd, "DesSpeedDistr(70)"))
                If FirstInt(CStr(SafeAtt(dsd, "DesSpeedDistr(10)"))) <> CLng(chDistrNo(idx)) Or _
                   FirstInt(CStr(SafeAtt(dsd, "DesSpeedDistr(70)"))) <> CLng(chDistrNo(idx)) Then
                    WScript.Echo "POSTRUN_MISMATCH channel=" & chSegId(idx) & " dsd=" & CStr(dsdNo) & _
                        " expected=" & CStr(chDistrNo(idx)) & " actual=" & rb
                End If
            End If
            Err.Clear
            On Error GoTo 0
        End If
    Next
End Sub

Function NextSampleAfter(sec)
    Dim candidate
    If CLng(sec) < CLng(sampleStart) Then
        NextSampleAfter = CLng(sampleStart)
    Else
        candidate = CLng(sec) + CLng(sampleInterval)
        NextSampleAfter = CLng(candidate)
    End If
End Function

Sub RunContinuousTo(target)
    If CLng(target) <= CLng(SafeAtt(Vissim.Simulation, "SimSec")) Then Exit Sub
    TrySetAtt Vissim.Simulation, "SimBreakAt", CDbl(target)
    Vissim.Simulation.RunContinuous
    WScript.Echo "RUN_BREAK target=" & CStr(target) & " actual=" & SafeAtt(Vissim.Simulation, "SimSec")
End Sub

Sub SampleVehicles(simSec)
    Dim noArr, laneArr, posArr, spdArr, desArr, typArr
    Dim lo, hi, row, linkNo, laneNo, pos, speed, des, vtype, vno
    Dim chainPos, seg, i
    Dim countE(7), speedE(7), countW(7), speedW(7)
    Dim onChain, offChain, laneTxt

    For i = 0 To 7
        countE(i) = 0 : speedE(i) = 0 : countW(i) = 0 : speedW(i) = 0
    Next

    If Not ReadVehicleTable(noArr, laneArr, posArr, spdArr, desArr, typArr) Then
        WScript.Echo "WARN=SAMPLE_READ_FAILED sim_sec=" & CStr(simSec)
        Exit Sub
    End If

    lo = MultiLBound(laneArr)
    hi = MultiUBound(laneArr)
    onChain = 0
    offChain = 0
    For row = lo To hi
        laneTxt = CStr(MultiValue(laneArr, row))
        linkNo = FirstInt(laneTxt)
        laneNo = LastInt(laneTxt)
        pos = CDblOrZero(MultiValue(posArr, row))
        speed = CDblOrZero(MultiValue(spdArr, row))
        des = CDblOrZero(MultiValue(desArr, row))
        vtype = FirstInt(MultiValue(typArr, row))
        vno = FirstInt(MultiValue(noArr, row))

        chainPos = ChainPosCsv(linkNo, pos, FW_E_CHAIN_LINKS, FW_E_CHAIN_OFFSETS)
        If chainPos >= 0 Then
            seg = SegmentIndexCsv(chainPos, FW_E_SEG_BOUNDS)
            countE(seg) = countE(seg) + 1
            speedE(seg) = speedE(seg) + speed
            onChain = onChain + 1
            vehFile.WriteLine CStr(simSec) & "," & CStr(vno) & "," & CStr(linkNo) & "," & CStr(laneNo) & _
                "," & Num(pos) & "," & Num(speed) & "," & Num(des) & "," & CStr(vtype)
        Else
            chainPos = ChainPosCsv(linkNo, pos, FW_W_CHAIN_LINKS, FW_W_CHAIN_OFFSETS)
            If chainPos >= 0 Then
                seg = SegmentIndexCsv(chainPos, FW_W_SEG_BOUNDS)
                countW(seg) = countW(seg) + 1
                speedW(seg) = speedW(seg) + speed
                onChain = onChain + 1
                vehFile.WriteLine CStr(simSec) & "," & CStr(vno) & "," & CStr(linkNo) & "," & CStr(laneNo) & _
                    "," & Num(pos) & "," & Num(speed) & "," & Num(des) & "," & CStr(vtype)
            Else
                offChain = offChain + 1
            End If
        End If
    Next

    For i = 0 To 7
        segFile.WriteLine CStr(simSec) & ",FW_E," & CStr(i) & "," & CStr(countE(i)) & "," & Num(speedE(i))
    Next
    For i = 0 To 7
        segFile.WriteLine CStr(simSec) & ",FW_W," & CStr(i) & "," & CStr(countW(i)) & "," & Num(speedW(i))
    Next

    WScript.Echo "SAMPLE sim_sec=" & CStr(simSec) & " total=" & CStr(hi - lo + 1) & _
        " on_chain=" & CStr(onChain) & " off_chain=" & CStr(offChain) & _
        " FW_E=" & CStr(countE(0)) & "/" & CStr(countE(1)) & "/" & CStr(countE(2)) & "/" & CStr(countE(3)) & _
        "/" & CStr(countE(4)) & "/" & CStr(countE(5)) & "/" & CStr(countE(6)) & "/" & CStr(countE(7)) & _
        " FW_W=" & CStr(countW(0)) & "/" & CStr(countW(1)) & "/" & CStr(countW(2)) & "/" & CStr(countW(3)) & _
        "/" & CStr(countW(4)) & "/" & CStr(countW(5)) & "/" & CStr(countW(6)) & "/" & CStr(countW(7))
End Sub

Sub ProbeVehicleAttribute(attName)
    Dim arr, n
    On Error Resume Next
    arr = Vissim.Net.Vehicles.GetMultiAttValues(attName)
    If Err.Number <> 0 Then
        WScript.Echo "ATTR_FAIL att=" & attName & " err=" & Err.Description
        Err.Clear
        On Error GoTo 0
        Exit Sub
    End If
    On Error GoTo 0
    n = MultiUBound(arr) - MultiLBound(arr) + 1
    WScript.Echo "ATTR_OK att=" & attName & " rows=" & CStr(n) & _
        " sample=" & CStr(MultiValue(arr, MultiLBound(arr)))
End Sub

Function ReadVehicleTable(ByRef noArr, ByRef laneArr, ByRef posArr, ByRef spdArr, ByRef desArr, ByRef typArr)
    ReadVehicleTable = False
    On Error Resume Next
    noArr = Vissim.Net.Vehicles.GetMultiAttValues("No")
    laneArr = Vissim.Net.Vehicles.GetMultiAttValues("Lane")
    posArr = Vissim.Net.Vehicles.GetMultiAttValues("Pos")
    spdArr = Vissim.Net.Vehicles.GetMultiAttValues("Speed")
    desArr = Vissim.Net.Vehicles.GetMultiAttValues("DesSpeed")
    typArr = Vissim.Net.Vehicles.GetMultiAttValues("VehType")
    If Err.Number <> 0 Then
        WScript.Echo "WARN=GET_MULTI_FAILED err=" & Err.Description
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    On Error GoTo 0
    ReadVehicleTable = True
End Function

Function ChainPosCsv(linkNo, pos, chainLinksCsv, chainOffsetsCsv)
    Dim links, offsets, i, token
    ChainPosCsv = -1.0
    If Trim(CStr(chainLinksCsv)) = "" Then Exit Function
    links = Split(chainLinksCsv, ",")
    offsets = Split(chainOffsetsCsv, ",")
    For i = 0 To UBound(links)
        token = Trim(links(i))
        If token <> "" Then
            If CLng(token) = CLng(linkNo) Then
                If i <= UBound(offsets) Then
                    ChainPosCsv = CDbl(Trim(offsets(i))) + CDbl(pos)
                Else
                    ChainPosCsv = CDbl(pos)
                End If
                Exit Function
            End If
        End If
    Next
End Function

Function SegmentIndexCsv(pos, boundsCsv)
    Dim parts, i
    parts = Split(boundsCsv, ",")
    SegmentIndexCsv = UBound(parts) - 1
    For i = 0 To UBound(parts) - 1
        If CDbl(pos) < CDbl(parts(i + 1)) Then
            SegmentIndexCsv = i
            Exit Function
        End If
    Next
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

Function FirstInt(value)
    Dim re, matches
    FirstInt = 0
    Set re = New RegExp
    re.Pattern = "-?\d+"
    re.Global = False
    Set matches = re.Execute(CStr(value))
    If matches.Count > 0 Then FirstInt = CLng(matches(0).Value)
End Function

' Lane reads back as "<link>-<lane>" or "<link> <lane>". The pattern deliberately
' omits the minus sign: with "-?\d+" the lane of "74-1" would parse as -1.
Function LastInt(value)
    Dim re, matches
    LastInt = 0
    Set re = New RegExp
    re.Pattern = "\d+"
    re.Global = True
    Set matches = re.Execute(CStr(value))
    If matches.Count > 0 Then LastInt = CLng(matches(matches.Count - 1).Value)
End Function

Function InCsvInt(value, csvText)
    If Len(csvText) = 0 Then
        InCsvInt = False
    Else
        InCsvInt = (InStr(1, "," & csvText & ",", "," & CStr(value) & ",", vbTextCompare) > 0)
    End If
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

Function Num(value)
    Dim s
    s = CStr(value)
    Num = Replace(s, ",", ".")
End Function

Function SafeAtt(obj, attName)
    On Error Resume Next
    SafeAtt = obj.AttValue(attName)
    If Err.Number <> 0 Then
        SafeAtt = ""
        Err.Clear
    End If
    On Error GoTo 0
End Function

Sub TrySetAtt(obj, attName, value)
    On Error Resume Next
    obj.AttValue(attName) = value
    If Err.Number <> 0 Then
        WScript.Echo "WARN=SET_ATT_FAILED att=" & attName & " err=" & Err.Description
        Err.Clear
    End If
    On Error GoTo 0
End Sub

Function ArgOrDefault(index, defaultValue)
    If WScript.Arguments.Count > index Then
        If Trim(WScript.Arguments(index)) <> "" Then
            ArgOrDefault = WScript.Arguments(index)
            Exit Function
        End If
    End If
    ArgOrDefault = defaultValue
End Function

Sub EnsureParentFolder(path)
    Dim parent
    parent = fso.GetParentFolderName(fso.GetAbsolutePathName(path))
    EnsureFolder parent
End Sub

Sub EnsureFolder(path)
    If path = "" Then Exit Sub
    If fso.FolderExists(path) Then Exit Sub
    EnsureFolder fso.GetParentFolderName(path)
    fso.CreateFolder path
End Sub

Function CreateVissimCom()
    Dim candidates, i, obj, forced, shell
    Set shell = CreateObject("WScript.Shell")
    forced = shell.ExpandEnvironmentStrings("%VISSIM_PROGID%")
    If forced <> "%VISSIM_PROGID%" And forced <> "" Then
        Set CreateVissimCom = CreateObject(forced)
        WScript.Echo "STAGE=COM_PROGID " & forced & " (VISSIM_PROGID)"
        Exit Function
    End If
    candidates = Array("Vissim.Vissim", "Vissim.Vissim.2020", "Vissim.Vissim-64.20", "Vissim.Vissim.200")
    For i = 0 To UBound(candidates)
        On Error Resume Next
        Set obj = CreateObject(candidates(i))
        If Err.Number = 0 Then
            Err.Clear
            On Error GoTo 0
            WScript.Echo "STAGE=COM_PROGID " & candidates(i)
            Set CreateVissimCom = obj
            Exit Function
        End If
        Err.Clear
        On Error GoTo 0
    Next
    WScript.Echo "ERROR=NO_VISSIM_COM no registered VISSIM COM ProgID could be created"
    WScript.Quit 3
End Function
