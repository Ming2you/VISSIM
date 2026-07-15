Option Explicit

If WScript.Arguments.Count < 3 Then
    WScript.Echo "Usage: cscript run_com_fixed_time_controller.vbs <network.inpx> <state_output.csv> <action_output.csv> [sim_period_sec] [urban_volume_vph] [freeway_volume_vph] [control_interval_sec] [generated_config.vbs]"
    WScript.Quit 2
End If

Dim netPath, stateOutPath, actionOutPath, simPeriod, urbanVol, freewayVol, controlInterval, generatedConfigPath
netPath = WScript.Arguments(0)
stateOutPath = WScript.Arguments(1)
actionOutPath = WScript.Arguments(2)
simPeriod = ArgOrDefault(3, 180)
urbanVol = ArgOrDefault(4, 60)
freewayVol = ArgOrDefault(5, 120)
controlInterval = ArgOrDefault(6, 5)
generatedConfigPath = ArgOrDefaultText(7, "")

' Defaults are overwritten by evaluation/generated/global_state_config.vbs when present.
Dim URBAN_LINKS, FREEWAY_LINKS, RAMP_LINKS, BOUNDARY_LINKS, FREEWAY_INPUT_LINKS
URBAN_LINKS = "5,6,7,8,11,12,13,14,19,20,23,24,27,28"
FREEWAY_LINKS = "33,34"
RAMP_LINKS = "25,26,31,32"
BOUNDARY_LINKS = "1,2,3,4,9,10,15,16,17,18,21,22,29,30"
FREEWAY_INPUT_LINKS = "33,34"

Const INTERSECTION_CYCLE_SEC = 90
Const MAJOR_GREEN_SEC = 40
Const MAJOR_AMBER_SEC = 3
Const ALL_RED_SEC = 2
Const MINOR_GREEN_SEC = 40
Const MINOR_AMBER_SEC = 3

Const RAMP_CYCLE_SEC = 10
Const RAMP_GREEN_SEC = 2
Const RAMP_AMBER_SEC = 1

Dim fso, stateFile, actionFile
Set fso = CreateObject("Scripting.FileSystemObject")
LoadGeneratedConfig generatedConfigPath
EnsureParentFolder stateOutPath
EnsureParentFolder actionOutPath
Set stateFile = fso.CreateTextFile(stateOutPath, True)
Set actionFile = fso.CreateTextFile(actionOutPath, True)

stateFile.WriteLine "sim_sec,total_vehicles,urban_vehicles,freeway_vehicles,ramp_vehicles,boundary_vehicles,other_vehicles,mean_speed_kph,stopped_vehicles,controller_mode,phase_A,phase_B,phase_C,phase_D,phase_F,ramp_meter_D,ramp_meter_F"
actionFile.WriteLine "sim_sec,controller_mode,sc_no,control_name,sg1_state,sg2_state,phase_label"

Dim Vissim
Set Vissim = CreateObject("Vissim.Vissim")
WScript.Echo "STAGE=COM_CREATED"
Vissim.LoadNet netPath, False
WScript.Echo "STAGE=NET_LOADED"
WScript.Echo "VERSION=" & Vissim.AttValue("VERSION")
WScript.Echo "LINKS=" & Vissim.Net.Links.Count
WScript.Echo "VEHICLE_INPUTS=" & Vissim.Net.VehicleInputs.Count
WScript.Echo "SIGNAL_CONTROLLERS=" & Vissim.Net.SignalControllers.Count
WScript.Echo "SIGNAL_HEADS=" & Vissim.Net.SignalHeads.Count
WScript.Echo "GLOBAL_STATE_GROUPS=urban(" & URBAN_LINKS & "),freeway(" & FREEWAY_LINKS & "),ramp(" & RAMP_LINKS & "),boundary(" & BOUNDARY_LINKS & ")"

On Error Resume Next
Vissim.Graphics.CurrentNetworkWindow.AttValue("QuickMode") = 1
Vissim.SuspendUpdateGUI
Err.Clear
On Error GoTo 0

SetDemandVolumes urbanVol, freewayVol
ActivateSignalControllers

Vissim.Simulation.AttValue("RandSeed") = 42
' Keep the internal period one second longer to avoid Vissim's exact-period reset.
Vissim.Simulation.AttValue("SimPeriod") = CDbl(simPeriod) + 1
Vissim.Simulation.AttValue("SimRes") = 1

' Start simulation first; signal-group COM control attributes are active only during simulation.
Vissim.Simulation.RunSingleStep
InitializeComSignalControl
ApplyController 1
LogAll 1

Dim stepNo
For stepNo = 2 To CLng(simPeriod)
    ApplyController stepNo
    Vissim.Simulation.RunSingleStep
    If stepNo Mod controlInterval = 0 Then
        LogAll stepNo
    End If
Next

stateFile.Close
actionFile.Close

On Error Resume Next
Vissim.ResumeUpdateGUI True
Err.Clear
On Error GoTo 0

WScript.Echo "STAGE=SIM_DONE"
WScript.Echo "SIM_SEC=" & Vissim.Simulation.AttValue("SimSec")
WScript.Echo "SIM_STEPS=" & simPeriod
WScript.Echo "STATE_CSV=" & stateOutPath
WScript.Echo "ACTION_CSV=" & actionOutPath

Set Vissim = Nothing
WScript.Quit 0

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

Sub ApplyController(simSec)
    ApplyIntersectionController simSec, 1, "A"
    ApplyIntersectionController simSec, 2, "B"
    ApplyIntersectionController simSec, 3, "C"
    ApplyIntersectionController simSec, 4, "D"
    ApplyIntersectionController simSec, 5, "F"
    ApplyRampMeterController simSec, 6, "D"
    ApplyRampMeterController simSec, 7, "F"
End Sub

Sub ApplyIntersectionController(simSec, scNo, label)
    Dim phase, majorState, minorState
    phase = TwoPhaseLabel(simSec)
    majorState = TwoPhaseMajorState(simSec)
    minorState = TwoPhaseMinorState(simSec)
    SetSignalGroupState scNo, 1, majorState
    SetSignalGroupState scNo, 2, minorState
    actionFile.WriteLine CStr(simSec) & ",COM_FIXED_TIME," & CStr(scNo) & "," & label & "," & majorState & "," & minorState & "," & phase
End Sub

Sub ApplyRampMeterController(simSec, scNo, label)
    Dim state, phase
    phase = RampMeterPhaseLabel(simSec)
    state = RampMeterState(simSec)
    SetSignalGroupState scNo, 1, state
    actionFile.WriteLine CStr(simSec) & ",COM_FIXED_TIME," & CStr(scNo) & ",RM_" & label & "," & state & ",," & phase
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

Function TwoPhaseLabel(simSec)
    Dim pos
    pos = simSec Mod INTERSECTION_CYCLE_SEC
    If pos < MAJOR_GREEN_SEC Then
        TwoPhaseLabel = "MAJOR_GREEN"
    ElseIf pos < MAJOR_GREEN_SEC + MAJOR_AMBER_SEC Then
        TwoPhaseLabel = "MAJOR_AMBER"
    ElseIf pos < MAJOR_GREEN_SEC + MAJOR_AMBER_SEC + ALL_RED_SEC Then
        TwoPhaseLabel = "ALL_RED_1"
    ElseIf pos < MAJOR_GREEN_SEC + MAJOR_AMBER_SEC + ALL_RED_SEC + MINOR_GREEN_SEC Then
        TwoPhaseLabel = "MINOR_GREEN"
    ElseIf pos < MAJOR_GREEN_SEC + MAJOR_AMBER_SEC + ALL_RED_SEC + MINOR_GREEN_SEC + MINOR_AMBER_SEC Then
        TwoPhaseLabel = "MINOR_AMBER"
    Else
        TwoPhaseLabel = "ALL_RED_2"
    End If
End Function

Function TwoPhaseMajorState(simSec)
    Dim phase
    phase = TwoPhaseLabel(simSec)
    If phase = "MAJOR_GREEN" Then
        TwoPhaseMajorState = "GREEN"
    ElseIf phase = "MAJOR_AMBER" Then
        TwoPhaseMajorState = "AMBER"
    Else
        TwoPhaseMajorState = "RED"
    End If
End Function

Function TwoPhaseMinorState(simSec)
    Dim phase
    phase = TwoPhaseLabel(simSec)
    If phase = "MINOR_GREEN" Then
        TwoPhaseMinorState = "GREEN"
    ElseIf phase = "MINOR_AMBER" Then
        TwoPhaseMinorState = "AMBER"
    Else
        TwoPhaseMinorState = "RED"
    End If
End Function

Function RampMeterPhaseLabel(simSec)
    Dim pos
    pos = simSec Mod RAMP_CYCLE_SEC
    If pos < RAMP_GREEN_SEC Then
        RampMeterPhaseLabel = "RAMP_GREEN"
    ElseIf pos < RAMP_GREEN_SEC + RAMP_AMBER_SEC Then
        RampMeterPhaseLabel = "RAMP_AMBER"
    Else
        RampMeterPhaseLabel = "RAMP_RED"
    End If
End Function

Function RampMeterState(simSec)
    Dim phase
    phase = RampMeterPhaseLabel(simSec)
    If phase = "RAMP_GREEN" Then
        RampMeterState = "GREEN"
    ElseIf phase = "RAMP_AMBER" Then
        RampMeterState = "AMBER"
    Else
        RampMeterState = "RED"
    End If
End Function

Sub LogAll(simSec)
    Dim total, urban, freeway, ramp, boundary, other, meanSpeed, stopped
    ComputeGlobalState total, urban, freeway, ramp, boundary, other, meanSpeed, stopped
    stateFile.WriteLine CStr(simSec) & "," & CStr(total) & "," & CStr(urban) & "," & CStr(freeway) & "," & _
        CStr(ramp) & "," & CStr(boundary) & "," & CStr(other) & "," & Num(meanSpeed) & "," & _
        CStr(stopped) & ",COM_FIXED_TIME," & TwoPhaseLabel(simSec) & "," & TwoPhaseLabel(simSec) & "," & _
        TwoPhaseLabel(simSec) & "," & TwoPhaseLabel(simSec) & "," & TwoPhaseLabel(simSec) & "," & _
        RampMeterPhaseLabel(simSec) & "," & RampMeterPhaseLabel(simSec)
End Sub

Sub ComputeGlobalState(ByRef total, ByRef urban, ByRef freeway, ByRef ramp, ByRef boundary, ByRef other, ByRef meanSpeed, ByRef stopped)
    total = 0
    urban = 0
    freeway = 0
    ramp = 0
    boundary = 0
    other = 0
    meanSpeed = 0
    stopped = 0

    Dim vehArray, veh, linkNo, speed, speedSum
    speedSum = 0
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
        ElseIf InCsvInt(linkNo, RAMP_LINKS) Then
            ramp = ramp + 1
        ElseIf InCsvInt(linkNo, BOUNDARY_LINKS) Then
            boundary = boundary + 1
        Else
            other = other + 1
        End If
    Next

    If total > 0 Then meanSpeed = speedSum / total
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

Function ArgOrDefaultText(index, defaultValue)
    If WScript.Arguments.Count > index Then
        ArgOrDefaultText = CStr(WScript.Arguments(index))
    Else
        ArgOrDefaultText = defaultValue
    End If
End Function

Function DefaultGeneratedConfigPath()
    Dim scriptFolder
    scriptFolder = fso.GetParentFolderName(WScript.ScriptFullName)
    DefaultGeneratedConfigPath = fso.BuildPath(scriptFolder, "..\evaluation\generated\global_state_config.vbs")
End Function

Sub LoadGeneratedConfig(path)
    Dim configPath, ts, scriptText
    If path = "" Then
        configPath = DefaultGeneratedConfigPath()
    Else
        configPath = path
    End If

    If Not fso.FileExists(configPath) Then
        WScript.Echo "WARN=GENERATED_CONFIG_NOT_FOUND using_embedded_defaults path=" & configPath
        Exit Sub
    End If

    Set ts = fso.OpenTextFile(configPath, 1, False)
    scriptText = ts.ReadAll
    ts.Close
    ExecuteGlobal scriptText
    WScript.Echo "CONFIG_LOADED=" & configPath
End Sub

Sub EnsureParentFolder(path)
    Dim parent
    parent = fso.GetParentFolderName(path)
    If parent <> "" And Not fso.FolderExists(parent) Then
        EnsureParentFolder parent
        fso.CreateFolder parent
    End If
End Sub
