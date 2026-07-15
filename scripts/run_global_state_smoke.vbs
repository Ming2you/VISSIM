Option Explicit

If WScript.Arguments.Count < 2 Then
    WScript.Echo "Usage: cscript run_global_state_smoke.vbs <network.inpx> <output.csv> [sim_period_sec] [urban_volume_vph] [freeway_volume_vph] [control_interval_sec] [generated_config.vbs]"
    WScript.Quit 2
End If

Dim netPath, outPath, simPeriod, urbanVol, freewayVol, controlInterval, generatedConfigPath
netPath = WScript.Arguments(0)
outPath = WScript.Arguments(1)
simPeriod = ArgOrDefault(2, 180)
urbanVol = ArgOrDefault(3, 60)
freewayVol = ArgOrDefault(4, 120)
controlInterval = ArgOrDefault(5, 5)
generatedConfigPath = ArgOrDefaultText(6, "")

' Defaults are overwritten by evaluation/generated/global_state_config.vbs when present.
Dim URBAN_LINKS, FREEWAY_LINKS, RAMP_LINKS, BOUNDARY_LINKS, FREEWAY_INPUT_LINKS
URBAN_LINKS = "5,6,7,8,11,12,13,14,19,20,23,24,27,28"
FREEWAY_LINKS = "33,34"
RAMP_LINKS = "25,26,31,32"
BOUNDARY_LINKS = "1,2,3,4,9,10,15,16,17,18,21,22,29,30"
FREEWAY_INPUT_LINKS = "33,34"

Dim fso, outFile
Set fso = CreateObject("Scripting.FileSystemObject")
LoadGeneratedConfig generatedConfigPath
EnsureParentFolder outPath
Set outFile = fso.CreateTextFile(outPath, True)
outFile.WriteLine "sim_sec,total_vehicles,urban_vehicles,freeway_vehicles,ramp_vehicles,boundary_vehicles,other_vehicles,mean_speed_kph,stopped_vehicles,controller_action"

Dim Vissim
Set Vissim = CreateObject("Vissim.Vissim")
WScript.Echo "STAGE=COM_CREATED"

Vissim.LoadNet netPath, False
WScript.Echo "STAGE=NET_LOADED"
WScript.Echo "VERSION=" & Vissim.AttValue("VERSION")
WScript.Echo "LINKS=" & Vissim.Net.Links.Count
WScript.Echo "VEHICLE_INPUTS=" & Vissim.Net.VehicleInputs.Count
WScript.Echo "GLOBAL_STATE_GROUPS=urban(" & URBAN_LINKS & "),freeway(" & FREEWAY_LINKS & "),ramp(" & RAMP_LINKS & "),boundary(" & BOUNDARY_LINKS & ")"
WScript.Echo "FREEWAY_INPUT_LINKS=" & FREEWAY_INPUT_LINKS

On Error Resume Next
Vissim.Graphics.CurrentNetworkWindow.AttValue("QuickMode") = 1
Vissim.SuspendUpdateGUI
Err.Clear
On Error GoTo 0

SetDemandVolumes urbanVol, freewayVol
WScript.Echo "DEMAND_URBAN_VPH=" & urbanVol
WScript.Echo "DEMAND_FREEWAY_VPH=" & freewayVol

Vissim.Simulation.AttValue("RandSeed") = 42
' Vissim can reset SimSec exactly at SimPeriod; keep the internal period one second longer
' and run an explicit step count so the final logged row is still pre-reset state.
Vissim.Simulation.AttValue("SimPeriod") = CDbl(simPeriod) + 1
Vissim.Simulation.AttValue("SimRes") = 1

Dim lastLoggedSec
lastLoggedSec = 0
LogState 0, "INIT"

Dim stepNo, totalSteps
totalSteps = CLng(simPeriod)
For stepNo = 1 To totalSteps
    Vissim.Simulation.RunSingleStep
    If stepNo <> lastLoggedSec And stepNo Mod controlInterval = 0 Then
        LogState stepNo, "GLOBAL_NOOP"
        lastLoggedSec = stepNo
    End If
Next

outFile.Close
On Error Resume Next
Vissim.ResumeUpdateGUI True
Err.Clear
On Error GoTo 0
WScript.Echo "STAGE=SIM_DONE"
WScript.Echo "SIM_SEC=" & Vissim.Simulation.AttValue("SimSec")
WScript.Echo "SIM_STEPS=" & totalSteps
WScript.Echo "OUTPUT_CSV=" & outPath

Set Vissim = Nothing
WScript.Quit 0

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
            ' Fallback for older COM attribute behavior.
            volume = freewayVolume
        Else
            volume = urbanVolume
        End If
        On Error Resume Next
        vi.AttValue("Volume(1)") = CDbl(volume)
        If Err.Number <> 0 Then
            WScript.Echo "WARN=FAILED_SET_VOLUME input=" & name & " err=" & Err.Description
            Err.Clear
        End If
        On Error GoTo 0
    Next
End Sub

Sub LogState(simSec, action)
    Dim total, urban, freeway, ramp, boundary, other, meanSpeed, stopped
    ComputeGlobalState total, urban, freeway, ramp, boundary, other, meanSpeed, stopped
    outFile.WriteLine CStr(simSec) & "," & CStr(total) & "," & CStr(urban) & "," & CStr(freeway) & "," & _
        CStr(ramp) & "," & CStr(boundary) & "," & CStr(other) & "," & Num(meanSpeed) & "," & _
        CStr(stopped) & "," & action
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
