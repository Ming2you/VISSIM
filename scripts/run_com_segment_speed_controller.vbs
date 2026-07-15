Option Explicit

If WScript.Arguments.Count < 3 Then
    WScript.Echo "Usage: cscript run_com_segment_speed_controller.vbs <network.inpx> <state_output.csv> <action_output.csv> [sim_period_sec] [urban_volume_vph] [freeway_volume_vph] [control_interval_sec] [rand_seed]"
    WScript.Quit 2
End If

Dim netPath, stateOutPath, actionOutPath, simPeriod, urbanVol, freewayVol, controlInterval, randSeed
netPath = WScript.Arguments(0)
stateOutPath = WScript.Arguments(1)
actionOutPath = WScript.Arguments(2)
simPeriod = ArgOrDefault(3, 180)
urbanVol = ArgOrDefault(4, 60)
freewayVol = ArgOrDefault(5, 1200)
controlInterval = ArgOrDefault(6, 5)
randSeed = ArgOrDefault(7, 11)

Dim URBAN_LINKS, FREEWAY_LINKS, RAMP_LINKS, BOUNDARY_LINKS, FREEWAY_INPUT_LINKS
URBAN_LINKS = "5,6,7,8,11,12,13,14,19,20,23,24,27,28"
FREEWAY_LINKS = "33,34"
RAMP_LINKS = "25,26,31,32"
BOUNDARY_LINKS = "1,2,3,4,9,10,15,16,17,18,21,22,29,30"
FREEWAY_INPUT_LINKS = "33,34"

Const MODE_NAME = "COM_VSL_SEGMENT_STEP_TEST"

Dim fso, stateFile, actionFile
Set fso = CreateObject("Scripting.FileSystemObject")
EnsureParentFolder stateOutPath
EnsureParentFolder actionOutPath
Set stateFile = fso.CreateTextFile(stateOutPath, True)
Set actionFile = fso.CreateTextFile(actionOutPath, True)

stateFile.WriteLine "sim_sec,total_vehicles,urban_vehicles,freeway_vehicles,ramp_vehicles,boundary_vehicles,other_vehicles,mean_speed_kph,freeway_mean_speed_kph,stopped_vehicles,controller_mode,vsl_profile,weave_limit_kph,nonweave_limit_kph"
actionFile.WriteLine "sim_sec,controller_mode,segment_id,dsd_no,link,lane,set_speed_kph,car_read_kph,hgv_read_kph,bus_read_kph"

Dim Vissim
Set Vissim = CreateObject("Vissim.Vissim")
WScript.Echo "STAGE=COM_CREATED"
Vissim.LoadNet netPath, False
WScript.Echo "STAGE=NET_LOADED"
WScript.Echo "VERSION=" & SafeAtt(Vissim, "VERSION")
WScript.Echo "LINKS=" & Vissim.Net.Links.Count
WScript.Echo "VEHICLE_INPUTS=" & Vissim.Net.VehicleInputs.Count
WScript.Echo "DESSPEEDDECISIONS=" & Vissim.Net.DesSpeedDecisions.Count

On Error Resume Next
Vissim.Graphics.CurrentNetworkWindow.AttValue("QuickMode") = 1
Vissim.SuspendUpdateGUI
Err.Clear
On Error GoTo 0

SetDemandVolumes urbanVol, freewayVol

Vissim.Simulation.AttValue("RandSeed") = CLng(randSeed)
Vissim.Simulation.AttValue("SimPeriod") = CDbl(simPeriod) + 1
Vissim.Simulation.AttValue("SimRes") = 1

ApplySegmentSpeedController 0, True
Vissim.Simulation.RunSingleStep
LogState 1

Dim stepNo, shouldLogAction
For stepNo = 2 To CLng(simPeriod)
    shouldLogAction = (stepNo Mod CLng(controlInterval) = 0) Or IsProfileBoundary(stepNo)
    ApplySegmentSpeedController stepNo, shouldLogAction
    Vissim.Simulation.RunSingleStep
    If stepNo Mod CLng(controlInterval) = 0 Then
        LogState stepNo
    End If
Next

stateFile.Close
actionFile.Close

On Error Resume Next
Vissim.ResumeUpdateGUI True
Err.Clear
On Error GoTo 0

WScript.Echo "STAGE=SIM_DONE"
WScript.Echo "SIM_SEC=" & SafeAtt(Vissim.Simulation, "SimSec")
WScript.Echo "SIM_STEPS=" & simPeriod
WScript.Echo "STATE_CSV=" & stateOutPath
WScript.Echo "ACTION_CSV=" & actionOutPath

Set Vissim = Nothing
WScript.Quit 0

Sub ApplySegmentSpeedController(simSec, writeActions)
    ApplySegment simSec, writeActions, "EB_S0_W_ENTRY_TO_D_DIVERGE", "1,2", 33
    ApplySegment simSec, writeActions, "EB_S1_D_DIVERGE_TO_D_MERGE", "3,4", 33
    ApplySegment simSec, writeActions, "EB_S2_D_MERGE_TO_F_DIVERGE", "5,6", 33
    ApplySegment simSec, writeActions, "EB_S3_F_DIVERGE_TO_F_MERGE", "7,8", 33
    ApplySegment simSec, writeActions, "EB_S4_F_MERGE_TO_E_EXIT", "9,10", 33
    ApplySegment simSec, writeActions, "WB_S0_E_ENTRY_TO_F_DIVERGE", "11,12", 34
    ApplySegment simSec, writeActions, "WB_S1_F_DIVERGE_TO_F_MERGE", "13,14", 34
    ApplySegment simSec, writeActions, "WB_S2_F_MERGE_TO_D_DIVERGE", "15,16", 34
    ApplySegment simSec, writeActions, "WB_S3_D_DIVERGE_TO_D_MERGE", "17,18", 34
    ApplySegment simSec, writeActions, "WB_S4_D_MERGE_TO_W_EXIT", "19,20", 34
End Sub

Sub ApplySegment(simSec, writeActions, segmentId, dsdNosCsv, linkNo)
    Dim speedKph, parts, dsdNo, dsd, laneText, laneNo
    speedKph = DesiredSpeedForSegment(simSec, segmentId)
    parts = Split(dsdNosCsv, ",")

    For Each dsdNo In parts
        Set dsd = Vissim.Net.DesSpeedDecisions.ItemByKey(CLng(dsdNo))
        SetClassSpeed dsd, 10, speedKph
        SetClassSpeed dsd, 20, speedKph
        SetClassSpeed dsd, 30, speedKph

        If writeActions Then
            laneText = SafeAtt(dsd, "Lane")
            laneNo = LastInt(laneText)
            actionFile.WriteLine CStr(simSec) & "," & MODE_NAME & "," & segmentId & "," & CStr(dsdNo) & "," & _
                CStr(linkNo) & "," & CStr(laneNo) & "," & CStr(speedKph) & "," & _
                SafeAtt(dsd, "DesSpeedDistr(10)") & "," & SafeAtt(dsd, "DesSpeedDistr(20)") & "," & SafeAtt(dsd, "DesSpeedDistr(30)")
        End If
    Next
End Sub

Function DesiredSpeedForSegment(simSec, segmentId)
    Dim profile
    profile = VslProfile(simSec)
    If profile = "FREE_FLOW" Then
        DesiredSpeedForSegment = 120
    ElseIf profile = "MODERATE" Then
        If IsWeaveSegment(segmentId) Then
            DesiredSpeedForSegment = 80
        Else
            DesiredSpeedForSegment = 100
        End If
    Else
        If IsWeaveSegment(segmentId) Then
            DesiredSpeedForSegment = 60
        Else
            DesiredSpeedForSegment = 80
        End If
    End If
End Function

Function IsWeaveSegment(segmentId)
    IsWeaveSegment = _
        InStr(1, segmentId, "_D_DIVERGE_TO_D_MERGE", vbTextCompare) > 0 Or _
        InStr(1, segmentId, "_F_DIVERGE_TO_F_MERGE", vbTextCompare) > 0
End Function

Function VslProfile(simSec)
    If CLng(simSec) < 60 Then
        VslProfile = "FREE_FLOW"
    ElseIf CLng(simSec) < 120 Then
        VslProfile = "MODERATE"
    Else
        VslProfile = "RESTRICTIVE"
    End If
End Function

Function VslWeaveLimit(simSec)
    If VslProfile(simSec) = "FREE_FLOW" Then
        VslWeaveLimit = 120
    ElseIf VslProfile(simSec) = "MODERATE" Then
        VslWeaveLimit = 80
    Else
        VslWeaveLimit = 60
    End If
End Function

Function VslNonweaveLimit(simSec)
    If VslProfile(simSec) = "FREE_FLOW" Then
        VslNonweaveLimit = 120
    ElseIf VslProfile(simSec) = "MODERATE" Then
        VslNonweaveLimit = 100
    Else
        VslNonweaveLimit = 80
    End If
End Function

Function IsProfileBoundary(simSec)
    IsProfileBoundary = (CLng(simSec) = 60) Or (CLng(simSec) = 120)
End Function

Sub SetClassSpeed(dsd, vehClassNo, speedKph)
    TrySetAtt dsd, "DesSpeedDistr(" & CStr(vehClassNo) & ")", CLng(speedKph)
End Sub

Sub LogState(simSec)
    Dim total, urban, freeway, ramp, boundary, other, meanSpeed, freewayMeanSpeed, stopped
    ComputeGlobalState total, urban, freeway, ramp, boundary, other, meanSpeed, freewayMeanSpeed, stopped
    stateFile.WriteLine CStr(simSec) & "," & CStr(total) & "," & CStr(urban) & "," & CStr(freeway) & "," & _
        CStr(ramp) & "," & CStr(boundary) & "," & CStr(other) & "," & Num(meanSpeed) & "," & _
        Num(freewayMeanSpeed) & "," & CStr(stopped) & "," & MODE_NAME & "," & VslProfile(simSec) & "," & _
        CStr(VslWeaveLimit(simSec)) & "," & CStr(VslNonweaveLimit(simSec))
End Sub

Sub ComputeGlobalState(ByRef total, ByRef urban, ByRef freeway, ByRef ramp, ByRef boundary, ByRef other, ByRef meanSpeed, ByRef freewayMeanSpeed, ByRef stopped)
    total = 0
    urban = 0
    freeway = 0
    ramp = 0
    boundary = 0
    other = 0
    meanSpeed = 0
    freewayMeanSpeed = 0
    stopped = 0

    Dim vehArray, veh, linkNo, speed, speedSum, freewaySpeedSum
    speedSum = 0
    freewaySpeedSum = 0
    On Error Resume Next
    vehArray = Vissim.Net.Vehicles.GetAll
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        Exit Sub
    End If
    On Error GoTo 0

    For Each veh In vehArray
        total = total + 1
        linkNo = VehicleLinkNo(veh)
        speed = VehicleSpeed(veh)
        speedSum = speedSum + speed
        If speed < 1 Then stopped = stopped + 1

        If InCsvInt(linkNo, URBAN_LINKS) Then
            urban = urban + 1
        ElseIf InCsvInt(linkNo, FREEWAY_LINKS) Then
            freeway = freeway + 1
            freewaySpeedSum = freewaySpeedSum + speed
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
        TrySetAtt vi, "Volume(1)", CDbl(volume)
    Next
End Sub

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

Function LastInt(value)
    Dim text, i, ch, digits, current
    text = CStr(value)
    digits = ""
    current = ""
    For i = 1 To Len(text)
        ch = Mid(text, i, 1)
        If ch >= "0" And ch <= "9" Then
            current = current & ch
        Else
            If current <> "" Then
                digits = current
                current = ""
            End If
        End If
    Next
    If current <> "" Then digits = current
    If digits = "" Then
        LastInt = 0
    Else
        LastInt = CLng(digits)
    End If
End Function

Function InCsvInt(value, csv)
    InCsvInt = InStr(1, "," & csv & ",", "," & CStr(value) & ",", vbTextCompare) > 0
End Function

Function Num(value)
    Num = Replace(FormatNumber(CDbl(value), 3, -1, 0, 0), ",", "")
End Function

Function ArgOrDefault(index, defaultValue)
    If WScript.Arguments.Count > index Then
        ArgOrDefault = CDbl(WScript.Arguments(index))
    Else
        ArgOrDefault = defaultValue
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
