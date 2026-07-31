Option Explicit

If WScript.Arguments.Count < 2 Then
    WScript.Echo "Usage: cscript run_real_world_state_smoke.vbs <network.inpx> <output.csv> [sim_period_sec] [log_interval_sec] [rand_seed] [generated_config.vbs]"
    WScript.Quit 2
End If

Dim fso, netPath, outPath, simPeriod, logInterval, randSeed, generatedConfigPath
Set fso = CreateObject("Scripting.FileSystemObject")
netPath = WScript.Arguments(0)
outPath = WScript.Arguments(1)
simPeriod = CLng(ArgOrDefault(2, 120))
logInterval = CLng(ArgOrDefault(3, 5))
randSeed = CLng(ArgOrDefault(4, 13))
generatedConfigPath = ArgOrDefaultText(5, "")

Dim FREEWAY_LINKS, URBAN_LINKS, RAMP_LINKS, BOUNDARY_LINKS, FREEWAY_INPUT_LINKS, CLASSIFY_UNMATCHED_AS_URBAN
FREEWAY_LINKS = "2,26"
URBAN_LINKS = ""
RAMP_LINKS = ""
BOUNDARY_LINKS = ""
FREEWAY_INPUT_LINKS = "26,74"
CLASSIFY_UNMATCHED_AS_URBAN = True

LoadGeneratedConfig generatedConfigPath

Dim outFile
EnsureParentFolder outPath
Set outFile = fso.CreateTextFile(outPath, True)
outFile.WriteLine "sim_sec,sim_sec_att,vehicles_count_att,total_vehicles,urban_vehicles,freeway_vehicles,ramp_vehicles,boundary_vehicles,other_vehicles,mean_speed_kph,freeway_mean_speed_kph,stopped_vehicles"

Dim Vissim
Set Vissim = CreateObject("Vissim.Vissim")
WScript.Echo "STAGE=COM_CREATED"

Vissim.LoadNet netPath, False
WScript.Echo "STAGE=NET_LOADED"
WScript.Echo "VERSION=" & SafeAtt(Vissim, "VERSION")
WScript.Echo "LINKS=" & Vissim.Net.Links.Count
WScript.Echo "VEHICLE_INPUTS=" & Vissim.Net.VehicleInputs.Count
WScript.Echo "SIGNAL_CONTROLLERS=" & Vissim.Net.SignalControllers.Count
WScript.Echo "DESSPEEDDECISIONS=" & Vissim.Net.DesSpeedDecisions.Count
WScript.Echo "FREEWAY_LINKS=" & FREEWAY_LINKS
WScript.Echo "FREEWAY_INPUT_LINKS=" & FREEWAY_INPUT_LINKS
WScript.Echo "DEMAND=ORIGINAL_INPX_UNCHANGED"
ConfigureEvaluationOutput fso.BuildPath(fso.GetParentFolderName(outPath), "vissim_eval")

On Error Resume Next
Vissim.Graphics.CurrentNetworkWindow.AttValue("QuickMode") = 1
Vissim.SuspendUpdateGUI
Err.Clear
On Error GoTo 0

Vissim.Simulation.AttValue("RandSeed") = randSeed
Vissim.Simulation.AttValue("SimPeriod") = CDbl(simPeriod) + 1
Vissim.Simulation.AttValue("SimRes") = 1
TrySetAtt Vissim.Simulation, "NumRuns", 1
TrySetAtt Vissim.Simulation, "UseMaxSimSpeed", True
TrySetAtt Vissim.Simulation, "SimSpeed", 0

LogState 0

Dim stepNo
For stepNo = 1 To simPeriod
    Vissim.Simulation.RunSingleStep
    If stepNo Mod logInterval = 0 Or stepNo = simPeriod Then
        LogState stepNo
    End If
    If stepNo Mod 30 = 0 Or stepNo = simPeriod Then
        WScript.Echo "RUN_SINGLE_STEP sim_sec=" & CStr(stepNo)
    End If
Next

outFile.Close

On Error Resume Next
Vissim.ResumeUpdateGUI True
Err.Clear
On Error GoTo 0

WScript.Echo "STAGE=SIM_DONE"
WScript.Echo "SIM_SEC=" & SafeAtt(Vissim.Simulation, "SimSec")
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
    DefaultGeneratedConfigPath = fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "..\evaluation\generated\real_world_modi_global_state_config.vbs")
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

Sub EnsureFolder(path)
    If path <> "" And Not fso.FolderExists(path) Then
        EnsureParentFolder fso.BuildPath(path, "placeholder.txt")
        If Not fso.FolderExists(path) Then fso.CreateFolder path
    End If
End Sub

Sub ConfigureEvaluationOutput(path)
    EnsureFolder path
    TrySetEvaluationAtt "EvalOutDir", path
    TrySetEvaluationAtt "DatabaseConnection", ""
    TrySetEvaluationAtt "ListAutoExportType", "FILE"
    WScript.Echo "EVAL_OUT_DIR=" & path
End Sub

Sub LogState(simSec)
    Dim total, urban, freeway, ramp, boundary, other, meanSpeed, freewayMeanSpeed, stopped
    Dim simSecAtt, countAtt
    ComputeGlobalState total, urban, freeway, ramp, boundary, other, meanSpeed, freewayMeanSpeed, stopped
    simSecAtt = SafeAtt(Vissim.Simulation, "SimSec")
    countAtt = VehicleCollectionCount()
    outFile.WriteLine CStr(simSec) & "," & simSecAtt & "," & CStr(countAtt) & "," & _
        CStr(total) & "," & CStr(urban) & "," & CStr(freeway) & "," & _
        CStr(ramp) & "," & CStr(boundary) & "," & CStr(other) & "," & Num(meanSpeed) & "," & _
        Num(freewayMeanSpeed) & "," & CStr(stopped)
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
        WScript.Echo "WARN=VEHICLES_GETALL_FAILED err=" & Err.Description
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

        If InCsvInt(linkNo, FREEWAY_LINKS) Then
            freeway = freeway + 1
            freewaySpeedSum = freewaySpeedSum + speed
        ElseIf InCsvInt(linkNo, RAMP_LINKS) Then
            ramp = ramp + 1
        ElseIf InCsvInt(linkNo, BOUNDARY_LINKS) Then
            boundary = boundary + 1
        ElseIf CLASSIFY_UNMATCHED_AS_URBAN Or InCsvInt(linkNo, URBAN_LINKS) Then
            urban = urban + 1
        Else
            other = other + 1
        End If
    Next

    If total > 0 Then meanSpeed = speedSum / total
    If freeway > 0 Then freewayMeanSpeed = freewaySpeedSum / freeway
End Sub

Function VehicleLinkNo(veh)
    Dim raw
    VehicleLinkNo = 0
    On Error Resume Next
    raw = veh.AttValue("Lane")
    If Err.Number <> 0 Then
        Err.Clear
        raw = veh.AttValue("Lane\Link")
    End If
    On Error GoTo 0
    VehicleLinkNo = FirstInt(raw)
End Function

Function VehicleSpeed(veh)
    On Error Resume Next
    VehicleSpeed = CDbl(veh.AttValue("Speed"))
    If Err.Number <> 0 Then
        Err.Clear
        VehicleSpeed = 0
    End If
    On Error GoTo 0
End Function

Function VehicleCollectionCount()
    On Error Resume Next
    VehicleCollectionCount = CLng(Vissim.Net.Vehicles.Count)
    If Err.Number <> 0 Then
        Err.Clear
        VehicleCollectionCount = -1
    End If
    On Error GoTo 0
End Function

Sub TrySetAtt(obj, name, value)
    On Error Resume Next
    obj.AttValue(name) = value
    If Err.Number <> 0 Then
        WScript.Echo "WARN=FAILED_SET_ATT name=" & name & " err=" & Err.Description
        Err.Clear
    End If
    On Error GoTo 0
End Sub

Sub TrySetEvaluationAtt(name, value)
    On Error Resume Next
    Vissim.Evaluation.AttValue(name) = value
    If Err.Number <> 0 Then
        WScript.Echo "WARN=FAILED_SET_EVALUATION_ATT name=" & name & " err=" & Err.Description
        Err.Clear
    End If
    On Error GoTo 0
End Sub

Function FirstInt(value)
    Dim re, matches
    FirstInt = 0
    Set re = New RegExp
    re.Pattern = "-?\d+"
    re.Global = False
    Set matches = re.Execute(CStr(value))
    If matches.Count > 0 Then FirstInt = CLng(matches(0).Value)
End Function

Function InCsvInt(value, csvText)
    If Len(csvText) = 0 Then
        InCsvInt = False
    Else
        InCsvInt = (InStr(1, "," & csvText & ",", "," & CStr(value) & ",", vbTextCompare) > 0)
    End If
End Function

Function SafeAtt(obj, name)
    On Error Resume Next
    SafeAtt = CStr(obj.AttValue(name))
    If Err.Number <> 0 Then
        Err.Clear
        SafeAtt = ""
    End If
    On Error GoTo 0
End Function

Function Num(value)
    Num = Replace(CStr(Round(CDbl(value), 6)), ",", ".")
End Function
