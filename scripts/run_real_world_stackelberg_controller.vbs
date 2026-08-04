Option Explicit

If WScript.Arguments.Count < 4 Then
    WScript.Echo "Usage: cscript run_real_world_stackelberg_controller.vbs <network.inpx> <state_output.csv> <action_output.csv> <decision_dir> [sim_period_sec] [control_interval_sec] [rand_seed] [adapter_py] [calibration_json] [tuning_json] [mapping_json] [controller] [control_start_sec] [warmup_controller] [generated_config.vbs] [state_log_interval_sec] [demand_scale] [demand_profile_csv] [vehicle_input_roles_csv] [incident_link] [incident_lane] [incident_pos_m] [incident_start_sec] [incident_end_sec] [incident_name]"
    WScript.Quit 2
End If

Dim fso, shell, stateFile, actionFile, bottleneckLinkFile, bottleneckSegmentFile, Vissim
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

' Coarse wall-clock instrumentation, OFF unless RW_PERF=1 is in the environment.
' When off every hook is a single boolean test, so it never shows up in a run.
' When on, a "PERF name=<stage> sec=<total> n=<calls>" block is echoed at the end.
Dim RW_PERF_ENABLED, perfSum, perfCnt
RW_PERF_ENABLED = (Trim(shell.ExpandEnvironmentStrings("%RW_PERF%")) = "1")
Set perfSum = CreateObject("Scripting.Dictionary")
Set perfCnt = CreateObject("Scripting.Dictionary")

' Signal COM handle caches - see CachedSignalController.
Dim sigScCache, sigSgCache, sigSgCountCache, sigSgNameCache
Set sigScCache = CreateObject("Scripting.Dictionary")
Set sigSgCache = CreateObject("Scripting.Dictionary")
Set sigSgCountCache = CreateObject("Scripting.Dictionary")
Set sigSgNameCache = CreateObject("Scripting.Dictionary")

Dim netPath, stateOutPath, actionOutPath, bottleneckLinkOutPath, bottleneckSegmentOutPath, decisionDir, simPeriod, controlInterval, randSeed, stateLogIntervalSec, demandScale, demandProfilePath, vehicleInputRolesPath
Dim adapterPath, calibrationPath, tuningPath, mappingPath, detectorMappingPath, controllerName, controlStartSec, warmupControllerName, generatedConfigPath
Dim incidentLinkNo, incidentLaneNo, incidentPosM, incidentStartSec, incidentEndSec, incidentName, incidentEnabled
Dim incidentSignalControllerNo, incidentSignalGroupNo, incidentStateLast, incidentSc, incidentSg, incidentSignalHead
netPath = WScript.Arguments(0)
stateOutPath = WScript.Arguments(1)
actionOutPath = WScript.Arguments(2)
decisionDir = WScript.Arguments(3)
simPeriod = CLng(ArgOrDefault(4, 600))
controlInterval = CLng(ArgOrDefault(5, 60))
randSeed = CLng(ArgOrDefault(6, 13))
adapterPath = ArgOrDefaultText(7, DefaultAdapterPath())
calibrationPath = ArgOrDefaultText(8, "evaluation/calibration/real_world_modi_control_v0_20260719.json")
tuningPath = ArgOrDefaultText(9, "evaluation/configs/real_world_modi_pstack_adapter_v0_20260719.json")
mappingPath = ArgOrDefaultText(10, "evaluation/real_world_modi_control/control_mapping.json")
controllerName = LCase(Replace(ArgOrDefaultText(11, "stackelberg"), "_", "-"))
controlStartSec = CLng(ArgOrDefault(12, -1))
warmupControllerName = LCase(Replace(ArgOrDefaultText(13, "no-control"), "_", "-"))
generatedConfigPath = ArgOrDefaultText(14, "")
stateLogIntervalSec = CLng(ArgOrDefault(15, 5))
demandScale = CDbl(ArgOrDefault(16, 1.0))
demandProfilePath = ArgOrDefaultText(17, "")
vehicleInputRolesPath = ArgOrDefaultText(18, DefaultVehicleInputRolesPath())
incidentLinkNo = CLng(ArgOrDefault(19, 0))
incidentLaneNo = CLng(ArgOrDefault(20, 0))
incidentPosM = CDbl(ArgOrDefault(21, -1.0))
incidentStartSec = CLng(ArgOrDefault(22, -1))
incidentEndSec = CLng(ArgOrDefault(23, -1))
incidentName = ArgOrDefaultText(24, "")
If Trim(CStr(incidentName)) = "" Then incidentName = "INCIDENT_LANE_CLOSURE"
incidentEnabled = (CLng(incidentLinkNo) > 0 And CLng(incidentLaneNo) > 0 And CLng(incidentStartSec) >= 0 And CLng(incidentEndSec) > CLng(incidentStartSec))
incidentSignalControllerNo = 9901
incidentSignalGroupNo = 1
incidentStateLast = ""
Set incidentSc = Nothing
Set incidentSg = Nothing
Set incidentSignalHead = Nothing

' Freeway mainline geometry. THE GENERATED CONFIG IS AUTHORITATIVE - the values
' below are only the no-config fallback and must stay in sync with
'   evaluation/real_world_modi_control/freeway_mainline_chain.csv (chain membership)
'   scripts\generate_real_world_control_mapping.py                (lengths read from the .inpx)
' The mainline is a link CHAIN, not one link. RW_*_CHAIN_LINKS lists the member
' links in order and RW_*_CHAIN_OFFSETS_M gives each member start in chain
' coordinates, so a vehicle at (link, pos) maps to chain offset + pos and then
' into RW_*_SEG_BOUNDS. This makes the measurement grid identical to the control
' grid the VSL decisions were installed on.
Dim RW_SCHEMA_VERSION, RW_FREEWAY_LINKS, RW_FREEWAY_INPUT_LINKS, RW_CLASSIFY_UNMATCHED_AS_URBAN
Dim RW_FW_E_LINK, RW_FW_E_LENGTH_M, RW_FW_E_LANES, RW_FW_E_SEG_BOUNDS, RW_FW_E_SEG_LENGTHS_KM
Dim RW_FW_W_LINK, RW_FW_W_LENGTH_M, RW_FW_W_LANES, RW_FW_W_SEG_BOUNDS, RW_FW_W_SEG_LENGTHS_KM
Dim RW_FW_E_CHAIN_LINKS, RW_FW_E_CHAIN_OFFSETS_M, RW_FW_W_CHAIN_LINKS, RW_FW_W_CHAIN_OFFSETS_M
Dim RW_RAMP_METER_IDS, RW_RAMP_METER_SCS, RW_RAMP_METER_CONNECTORS, RW_RAMP_METER_MODEL_KEYS, RW_SIGNAL_SCS, RW_LOCAL_OBSERVABLE_LINKS, RW_DETECTOR_MAPPING_PATH
' Optional generated-config override for the python interpreter. Declared here
' so a config that sets it can be ExecuteGlobal'd under Option Explicit.
Dim RW_PYTHON_EXE
RW_PYTHON_EXE = ""
RW_SCHEMA_VERSION = 0
RW_FREEWAY_LINKS = "2,24,26,74,10699,10702"
RW_FREEWAY_INPUT_LINKS = "26,74"
RW_CLASSIFY_UNMATCHED_AS_URBAN = True
RW_FW_E_LINK = 2
RW_FW_E_LENGTH_M = 10773.109163
RW_FW_E_LANES = 4
RW_FW_E_CHAIN_LINKS = "74,10699,2,10702,24"
RW_FW_E_CHAIN_OFFSETS_M = "0.000000,2701.577000,2734.527232,7426.126232,7427.127732"
RW_FW_E_SEG_BOUNDS = "0.000000,1346.638645,2693.277291,4039.915936,5386.554581,6733.193227,8079.831872,9426.470517,10773.109163"
RW_FW_E_SEG_LENGTHS_KM = "1.346639,1.346639,1.346639,1.346639,1.346639,1.346639,1.346639,1.346639"
RW_FW_W_LINK = 26
RW_FW_W_LENGTH_M = 10777.693079
RW_FW_W_LANES = 4
RW_FW_W_CHAIN_LINKS = "26"
RW_FW_W_CHAIN_OFFSETS_M = "0.000000"
RW_FW_W_SEG_BOUNDS = "0.000000,1347.211635,2694.423270,4041.634904,5388.846539,6736.058174,8083.269809,9430.481444,10777.693079"
RW_FW_W_SEG_LENGTHS_KM = "1.347212,1.347212,1.347212,1.347212,1.347212,1.347212,1.347212,1.347212"
RW_RAMP_METER_IDS = "RM_C10480,RM_C10482,RM_C10646,RM_C10644,RM_C10639,RM_C10681,RM_C10490,RM_C10484"
RW_RAMP_METER_SCS = "9101,9102,9103,9104,9105,9106,9107,9108"
RW_RAMP_METER_CONNECTORS = "10480,10482,10646,10644,10639,10681,10490,10484"
RW_RAMP_METER_MODEL_KEYS = "R_D_W,R_D_W,R_F_W,R_F_W,R_F_E,R_F_E,R_D_E,R_D_E"
RW_SIGNAL_SCS = "1"
RW_LOCAL_OBSERVABLE_LINKS = "2,26,10479,10480,10481,10482,10483,10484,10490,10491,10638,10639,10643,10644,10645,10646,10681,10682"
RW_DETECTOR_MAPPING_PATH = "evaluation/real_world_modi_control/detector_local_mapping.json"
Dim generatedConfigLoaded
generatedConfigLoaded = False
LoadGeneratedConfig generatedConfigPath
' Schema 2 is the first generated config that carries the mainline link chain.
' An older config would silently overwrite SEG_BOUNDS with the single-link grid
' while leaving the chain variables at their fallback values, which is exactly
' the measurement/control grid mismatch this schema check exists to prevent.
If generatedConfigLoaded And CLng(RW_SCHEMA_VERSION) < 2 Then
    WScript.Echo "ERROR=GENERATED_CONFIG_SCHEMA_TOO_OLD schema=" & CStr(RW_SCHEMA_VERSION) & _
        " path=" & generatedConfigPath & " (rerun scripts/generate_real_world_control_mapping.py)"
    WScript.Quit 2
End If
detectorMappingPath = RW_DETECTOR_MAPPING_PATH

Const RAMP_CYCLE_SEC = 10
Const RAMP_AMBER_SEC = 1
Const AMBER_SEC = 3
Const ALL_RED_SEC = 2

If CLng(controlInterval) <= 0 Or (CLng(controlInterval) Mod RAMP_CYCLE_SEC) <> 0 Then
    WScript.Echo "ERROR=CONTROL_INTERVAL_MUST_BE_POSITIVE_MULTIPLE_OF_RAMP_CYCLE control_interval_sec=" & CStr(controlInterval) & " ramp_cycle_sec=" & CStr(RAMP_CYCLE_SEC)
    WScript.Quit 2
End If
If CLng(stateLogIntervalSec) <= 0 Then
    WScript.Echo "ERROR=STATE_LOG_INTERVAL_MUST_BE_POSITIVE state_log_interval_sec=" & CStr(stateLogIntervalSec)
    WScript.Quit 2
End If

' Resolve and verify the controller interpreter BEFORE any VISSIM work. A bad
' interpreter here means every decision fails, so failing now costs seconds
' instead of surfacing after a multi-hour run.
Dim pythonExe, decisionsOk, decisionsFailed
pythonExe = ""
decisionsOk = 0
decisionsFailed = 0
ResolvePythonInterpreter

EnsureParentFolder stateOutPath
EnsureParentFolder actionOutPath
EnsureFolder decisionDir
bottleneckLinkOutPath = DerivedRunCsvPath("bottleneck_links")
bottleneckSegmentOutPath = DerivedRunCsvPath("bottleneck_segments")
Set stateFile = fso.CreateTextFile(stateOutPath, True)
Set actionFile = fso.CreateTextFile(actionOutPath, True)
Set bottleneckLinkFile = fso.CreateTextFile(bottleneckLinkOutPath, True)
Set bottleneckSegmentFile = fso.CreateTextFile(bottleneckSegmentOutPath, True)
stateFile.WriteLine "sim_sec,total_vehicles,urban_vehicles,freeway_vehicles,ramp_vehicles,boundary_vehicles,other_vehicles,mean_speed_kph,freeway_mean_speed_kph,stopped_vehicles,controller_mode,controller_status,decision_wall_sec"
actionFile.WriteLine "sim_sec,kind,id,dsd_no,sc_no,link,lane,speed_kph,major_green,minor_green,offset,rate_vph,green_sec,metadata,readback"
bottleneckLinkFile.WriteLine "sim_sec,link,count,stopped_count,mean_speed_kph,category,is_freeway,is_ramp_meter_connector,is_local_observable"
bottleneckSegmentFile.WriteLine "sim_sec,model_link,direction,segment_index,segment_id,physical_link,count,stopped_count,mean_speed_kph,length_km,lanes,density_veh_km_lane"

Dim sigMajor, sigMinor, sigOffset, signalControlled, rampGreen, lastActionJson, urbanDemandVph, freewayDemandVph
Dim demandScheduleLoaded, demandUrbanBySec, demandFreewayBySec, demandForecastProfileName
Set sigMajor = CreateObject("Scripting.Dictionary")
Set sigMinor = CreateObject("Scripting.Dictionary")
Set sigOffset = CreateObject("Scripting.Dictionary")
Set signalControlled = CreateObject("Scripting.Dictionary")
Set rampGreen = CreateObject("Scripting.Dictionary")
InitializeDefaultActionState
lastActionJson = ""
urbanDemandVph = 60.0
freewayDemandVph = 1200.0
demandScheduleLoaded = False
demandForecastProfileName = "real_world_original"
Set demandUrbanBySec = CreateObject("Scripting.Dictionary")
Set demandFreewayBySec = CreateObject("Scripting.Dictionary")

Set Vissim = CreateObject("Vissim.Vissim")
WScript.Echo "STAGE=COM_CREATED"
Vissim.LoadNet netPath, False
WScript.Echo "STAGE=NET_LOADED"
WScript.Echo "VERSION=" & SafeAtt(Vissim, "VERSION")
WScript.Echo "LINKS=" & Vissim.Net.Links.Count
WScript.Echo "VEHICLE_INPUTS=" & Vissim.Net.VehicleInputs.Count
WScript.Echo "SIGNAL_CONTROLLERS=" & Vissim.Net.SignalControllers.Count
WScript.Echo "DESSPEEDDECISIONS=" & Vissim.Net.DesSpeedDecisions.Count
WScript.Echo "FREEWAY_LINKS=" & RW_FREEWAY_LINKS
WScript.Echo "FW_E_CHAIN=" & RW_FW_E_CHAIN_LINKS & " offsets_m=" & RW_FW_E_CHAIN_OFFSETS_M & " length_m=" & Num(RW_FW_E_LENGTH_M)
WScript.Echo "FW_E_SEG_BOUNDS=" & RW_FW_E_SEG_BOUNDS
WScript.Echo "FW_W_CHAIN=" & RW_FW_W_CHAIN_LINKS & " offsets_m=" & RW_FW_W_CHAIN_OFFSETS_M & " length_m=" & Num(RW_FW_W_LENGTH_M)
WScript.Echo "FW_W_SEG_BOUNDS=" & RW_FW_W_SEG_BOUNDS
WScript.Echo "RAMP_METER_SCS=" & RW_RAMP_METER_SCS
If incidentEnabled Then
    WScript.Echo "INCIDENT=ENABLED link=" & CStr(incidentLinkNo) & " lane=" & CStr(incidentLaneNo) & " pos_m=" & Num(incidentPosM) & " start_sec=" & CStr(incidentStartSec) & " end_sec=" & CStr(incidentEndSec) & " name=" & incidentName
Else
    WScript.Echo "INCIDENT=DISABLED"
End If
If Trim(CStr(demandProfilePath)) <> "" Then
    ApplyVehicleInputDemandProfile CDbl(demandScale), demandProfilePath, vehicleInputRolesPath
    WScript.Echo "DEMAND=PROFILE_SCALED_IN_MEMORY scale=" & Num(demandScale) & " profile=" & demandProfilePath
ElseIf Abs(CDbl(demandScale) - 1.0) > 0.000001 Then
    ScaleVehicleInputDemand CDbl(demandScale)
    WScript.Echo "DEMAND=SCALED_IN_MEMORY scale=" & Num(demandScale)
Else
    WScript.Echo "DEMAND=ORIGINAL_INPX_UNCHANGED"
End If
ConfigureEvaluationOutput fso.BuildPath(fso.GetParentFolderName(stateOutPath), "vissim_eval")
LoadInpxDemandSchedule netPath, vehicleInputRolesPath, demandScale, demandProfilePath
DemandForecastAtSimSec 0, urbanDemandVph, freewayDemandVph
WScript.Echo "DEMAND_FORECAST_CURRENT sim_sec=0 urban_vph=" & Num(urbanDemandVph) & " freeway_vph=" & Num(freewayDemandVph) & " profile=" & demandForecastProfileName

On Error Resume Next
Vissim.Graphics.CurrentNetworkWindow.AttValue("QuickMode") = 1
Vissim.SuspendUpdateGUI
Err.Clear
On Error GoTo 0

ActivateRampMeters
If incidentEnabled Then InstallIncidentLaneClosure
ApplyIncidentLaneClosure 0
Vissim.Simulation.AttValue("RandSeed") = CLng(randSeed)
Vissim.Simulation.AttValue("SimPeriod") = CDbl(simPeriod) + 1
Vissim.Simulation.AttValue("SimRes") = 1
TrySetAtt Vissim.Simulation, "NumRuns", 1
TrySetAtt Vissim.Simulation, "UseMaxSimSpeed", True
TrySetAtt Vissim.Simulation, "SimSpeed", 0

If UseContinuousStaticMode() Then
    RunContinuousStaticMode
ElseIf UseEventContinuousMode() Then
    RunEventContinuousMode
Else
    WScript.Echo "RUN_MODE=STEPWISE controller=" & controllerName
    RunStepwiseMode
End If

stateFile.Close
actionFile.Close
bottleneckLinkFile.Close
bottleneckSegmentFile.Close

On Error Resume Next
Vissim.ResumeUpdateGUI True
Err.Clear
On Error GoTo 0

' The watchdog treats STAGE=SIM_DONE as success, so a run that produced no
' control at all must not print it - otherwise a silent no-control run is
' archived as a controller result.
PerfReport
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
WScript.Echo "BOTTLENECK_LINK_CSV=" & bottleneckLinkOutPath
WScript.Echo "BOTTLENECK_SEGMENT_CSV=" & bottleneckSegmentOutPath
WScript.Echo "DECISION_DIR=" & decisionDir

Set Vissim = Nothing
WScript.Quit 0

Sub InitializeDefaultActionState()
    Dim scs, i, scNo
    scs = Split(RW_RAMP_METER_SCS, ",")
    For i = 0 To UBound(scs)
        scNo = Trim(scs(i))
        If scNo <> "" Then rampGreen(scNo) = 10.0
    Next
End Sub

Sub ActivateRampMeters()
    Dim scs, i, scNo, sc
    scs = Split(RW_RAMP_METER_SCS, ",")
    For i = 0 To UBound(scs)
        scNo = Trim(scs(i))
        If scNo <> "" Then
            On Error Resume Next
            Set sc = Vissim.Net.SignalControllers.ItemByKey(CLng(scNo))
            If Err.Number <> 0 Then
                WScript.Echo "WARN=RAMP_SC_NOT_FOUND sc=" & scNo & " err=" & Err.Description
                Err.Clear
            Else
                TrySetAtt sc, "Active", True
            End If
            On Error GoTo 0
        End If
    Next
End Sub

Sub InitializeComRampMeterControl()
    Dim scs, i, scNo, sc, sg
    scs = Split(RW_RAMP_METER_SCS, ",")
    For i = 0 To UBound(scs)
        scNo = Trim(scs(i))
        If scNo <> "" Then
            On Error Resume Next
            Set sc = Vissim.Net.SignalControllers.ItemByKey(CLng(scNo))
            Set sg = sc.SGs.ItemByKey(1)
            If Err.Number <> 0 Then
                WScript.Echo "WARN=RAMP_SG_NOT_FOUND sc=" & scNo & " err=" & Err.Description
                Err.Clear
            Else
                TrySetAtt sg, "ContrByCOM", True
                TrySetAtt sg, "SigState", "GREEN"
            End If
            On Error GoTo 0
        End If
    Next
End Sub

Function UseContinuousStaticMode()
    Dim c
    c = LCase(CStr(controllerName))
    UseContinuousStaticMode = (Not ForceStepwiseMode()) And (c = "no-control" Or c = "diagnostic-vsl60-only" Or c = "diagnostic-vsl80-only")
    If UseContinuousStaticMode Then
        WScript.Echo "RUN_MODE=CONTINUOUS_STATIC controller=" & controllerName
    End If
End Function

Function UseEventContinuousMode()
    Dim c
    c = LCase(CStr(controllerName))
    UseEventContinuousMode = (Not ForceStepwiseMode()) And (Left(c, 11) = "diagnostic-" Or c = "stackelberg")
    If UseEventContinuousMode Then
        WScript.Echo "RUN_MODE=CONTINUOUS_EVENT controller=" & controllerName
    End If
End Function

Function ForceStepwiseMode()
    Dim shell, value
    ForceStepwiseMode = False
    On Error Resume Next
    Set shell = CreateObject("WScript.Shell")
    value = LCase(CStr(shell.Environment("PROCESS")("RW_FORCE_STEPWISE")))
    If Err.Number = 0 Then
        ForceStepwiseMode = (value = "1" Or value = "true" Or value = "yes")
    End If
    Err.Clear
    On Error GoTo 0
End Function

Function UseSingleDecisionEventMode()
    Dim c
    c = LCase(CStr(controllerName))
    UseSingleDecisionEventMode = (Left(c, 11) = "diagnostic-" And CLng(controlStartSec) >= 0)
End Function

Sub RunStepwiseMode()
    Vissim.Simulation.RunSingleStep
    WScript.Echo "RUN_SINGLE_STEP sim_sec=1"
    InitializeComRampMeterControl
    RunControllerDecision 1
    ApplyRuntimeSignals 1
    ApplyRuntimeRampMeters 1
    ApplyIncidentLaneClosure 1
    LogStateCsv 1

    Dim stepNo, stepT0
    For stepNo = 2 To CLng(simPeriod)
        If stepNo Mod CLng(controlInterval) = 0 Then
            RunControllerDecision stepNo
        End If
        ApplyRuntimeSignals stepNo
        ApplyRuntimeRampMeters stepNo
        ApplyIncidentLaneClosure stepNo
        stepT0 = PerfNow()
        Vissim.Simulation.RunSingleStep
        PerfAdd "sim.step", stepT0
        If stepNo Mod 30 = 0 Or stepNo = CLng(simPeriod) Then
            WScript.Echo "RUN_SINGLE_STEP sim_sec=" & CStr(stepNo)
        End If
        If stepNo Mod CLng(stateLogIntervalSec) = 0 Or stepNo = CLng(simPeriod) Then
            LogStateCsv stepNo
        End If
    Next
End Sub

Sub RunContinuousStaticMode()
    Dim currentSec, nextLogSec, targetSec, nextIncidentSec, mainControlApplied, dueToControlStart, dueToLog

    Vissim.Simulation.RunSingleStep
    currentSec = 1
    WScript.Echo "RUN_SINGLE_STEP sim_sec=1"
    InitializeComRampMeterControl
    RunControllerDecision 1
    ApplyIncidentLaneClosure 1
    LogStateCsv 1

    mainControlApplied = (CLng(controlStartSec) < 0 Or CLng(controlStartSec) <= 1)
    nextLogSec = NextLogAfter(currentSec)

    Do While CLng(currentSec) < CLng(simPeriod)
        targetSec = nextLogSec
        If CLng(targetSec) > CLng(simPeriod) Then targetSec = CLng(simPeriod)
        nextIncidentSec = NextIncidentTransitionAfter(CLng(currentSec))
        If CLng(nextIncidentSec) < CLng(targetSec) Then targetSec = CLng(nextIncidentSec)
        If (Not mainControlApplied) And CLng(controlStartSec) > CLng(currentSec) And CLng(controlStartSec) < CLng(targetSec) Then
            targetSec = CLng(controlStartSec)
        End If

        RunContinuousTo CLng(targetSec)
        currentSec = CLng(targetSec)
        ApplyIncidentLaneClosure CLng(currentSec)

        dueToControlStart = ((Not mainControlApplied) And CLng(controlStartSec) >= 0 And CLng(currentSec) >= CLng(controlStartSec))
        dueToLog = ((CLng(currentSec) Mod CLng(stateLogIntervalSec)) = 0 Or CLng(currentSec) = CLng(simPeriod))

        If dueToControlStart Then
            If dueToLog Then
                LogStateCsv CLng(currentSec)
                nextLogSec = NextLogAfter(CLng(currentSec))
            End If
            RunControllerDecision CLng(currentSec)
            mainControlApplied = True
        ElseIf dueToLog Then
            LogStateCsv CLng(currentSec)
            nextLogSec = NextLogAfter(CLng(currentSec))
        End If
    Loop
End Sub

Sub RunEventContinuousMode()
    Dim currentSec, targetSec, singleDecisionMode, mainControlApplied
    Dim nextControlSec, nextIncidentSec, dueToControlStart, dueToRepeatedControl, dueToLog, loggedAtCurrentSec

    Vissim.Simulation.RunSingleStep
    currentSec = 1
    WScript.Echo "RUN_SINGLE_STEP sim_sec=1"
    InitializeComRampMeterControl
    RunControllerDecision 1
    ApplyRuntimeSignals 1
    ApplyRuntimeRampMeters 1
    ApplyIncidentLaneClosure 1
    LogStateCsv 1
    singleDecisionMode = UseSingleDecisionEventMode()
    mainControlApplied = ((Not singleDecisionMode) Or CLng(controlStartSec) <= 1)

    Do While CLng(currentSec) < CLng(simPeriod)
        If singleDecisionMode Then
            If Not mainControlApplied Then
                nextControlSec = CLng(controlStartSec)
                If CLng(nextControlSec) <= CLng(currentSec) Then nextControlSec = CLng(currentSec) + 1
            Else
                nextControlSec = CLng(simPeriod)
            End If
        Else
            nextControlSec = NextControlAfter(CLng(currentSec))
        End If

        targetSec = MinEventTarget( _
            CLng(nextControlSec), _
            NextLogAfter(CLng(currentSec)), _
            NextRampTransitionAfter(CLng(currentSec)), _
            NextSignalTransitionAfter(CLng(currentSec)) _
        )
        nextIncidentSec = NextIncidentTransitionAfter(CLng(currentSec))
        If CLng(nextIncidentSec) < CLng(targetSec) Then targetSec = CLng(nextIncidentSec)
        If CLng(targetSec) <= CLng(currentSec) Then targetSec = CLng(currentSec) + 1
        If CLng(targetSec) > CLng(simPeriod) Then targetSec = CLng(simPeriod)

        RunContinuousTo CLng(targetSec)
        currentSec = CLng(targetSec)

        dueToLog = ((CLng(currentSec) Mod CLng(stateLogIntervalSec)) = 0 Or CLng(currentSec) = CLng(simPeriod))
        loggedAtCurrentSec = False
        dueToControlStart = (singleDecisionMode And (Not mainControlApplied) And CLng(controlStartSec) >= 0 And CLng(currentSec) >= CLng(controlStartSec))
        dueToRepeatedControl = ((Not singleDecisionMode) And (CLng(currentSec) Mod CLng(controlInterval)) = 0)

        If dueToControlStart Then
            If dueToLog Then
                LogStateCsv CLng(currentSec)
                loggedAtCurrentSec = True
            End If
            RunControllerDecision CLng(currentSec)
            mainControlApplied = True
        ElseIf dueToRepeatedControl Then
            RunControllerDecision CLng(currentSec)
        End If
        ApplyRuntimeSignals CLng(currentSec)
        ApplyRuntimeRampMeters CLng(currentSec)
        ApplyIncidentLaneClosure CLng(currentSec)
        If dueToLog And Not loggedAtCurrentSec Then
            LogStateCsv CLng(currentSec)
        End If
    Loop
End Sub

Function MinEventTarget(a, b, c, d)
    Dim m
    m = CLng(a)
    If CLng(b) < m Then m = CLng(b)
    If CLng(c) < m Then m = CLng(c)
    If CLng(d) < m Then m = CLng(d)
    MinEventTarget = CLng(m)
End Function

Function NextControlAfter(sec)
    Dim interval, candidate
    interval = CLng(controlInterval)
    candidate = (Int(CDbl(sec) / CDbl(interval)) + 1) * interval
    If CLng(candidate) <= CLng(sec) Then candidate = CLng(candidate) + interval
    If CLng(candidate) > CLng(simPeriod) Then candidate = CLng(simPeriod)
    NextControlAfter = CLng(candidate)
End Function

Function NextLogAfter(sec)
    Dim interval, candidate
    interval = CLng(stateLogIntervalSec)
    candidate = (Int(CDbl(sec) / CDbl(interval)) + 1) * interval
    If CLng(candidate) <= CLng(sec) Then candidate = CLng(candidate) + interval
    If CLng(candidate) > CLng(simPeriod) Then candidate = CLng(simPeriod)
    NextLogAfter = CLng(candidate)
End Function

Sub RunContinuousTo(targetSec)
    If CLng(targetSec) <= CLng(SafeAtt(Vissim.Simulation, "SimSec")) Then Exit Sub
    TrySetAtt Vissim.Simulation, "SimBreakAt", CDbl(targetSec)
    Vissim.Simulation.RunContinuous
    WScript.Echo "RUN_CONTINUOUS_BREAK target_sim_sec=" & CStr(targetSec) & " actual_sim_sec=" & SafeAtt(Vissim.Simulation, "SimSec")
End Sub

Function NextRampTransitionAfter(sec)
    Dim currentState, t, limit
    currentState = RampCompositeStateAt(CLng(sec))
    If currentState = "" Then
        NextRampTransitionAfter = CLng(simPeriod)
        Exit Function
    End If
    limit = CLng(sec) + RAMP_CYCLE_SEC + 1
    If CLng(limit) > CLng(simPeriod) Then limit = CLng(simPeriod)
    For t = CLng(sec) + 1 To CLng(limit)
        If RampCompositeStateAt(CLng(t)) <> currentState Then
            NextRampTransitionAfter = CLng(t)
            Exit Function
        End If
    Next
    NextRampTransitionAfter = CLng(simPeriod)
End Function

Function RampCompositeStateAt(simSec)
    Dim scs, i, scNo, s
    scs = Split(RW_RAMP_METER_SCS, ",")
    s = ""
    For i = 0 To UBound(scs)
        scNo = Trim(scs(i))
        If scNo <> "" Then
            s = s & scNo & ":" & RampStateAt(CDbl(DictValue(rampGreen, scNo, 10.0)), CLng(simSec)) & ";"
        End If
    Next
    RampCompositeStateAt = s
End Function

Function RampStateAt(greenSec, simSec)
    Dim pos
    pos = FMod(CDbl(simSec), RAMP_CYCLE_SEC)
    If CDbl(greenSec) <= 0 Then
        RampStateAt = "RED"
    ElseIf pos < CDbl(greenSec) Then
        RampStateAt = "GREEN"
    ElseIf pos < CDbl(greenSec) + RAMP_AMBER_SEC Then
        RampStateAt = "AMBER"
    Else
        RampStateAt = "RED"
    End If
End Function

Function NextSignalTransitionAfter(sec)
    Dim currentState, t, limit, horizon
    If sigMajor.Count <= 0 Then
        NextSignalTransitionAfter = CLng(simPeriod)
        Exit Function
    End If
    currentState = SignalCompositeStateAt(CLng(sec))
    horizon = MaxSignalCycleSec() + 1
    If horizon < 1 Then horizon = 1
    limit = CLng(sec) + CLng(horizon)
    If CLng(limit) > CLng(simPeriod) Then limit = CLng(simPeriod)
    For t = CLng(sec) + 1 To CLng(limit)
        If SignalCompositeStateAt(CLng(t)) <> currentState Then
            NextSignalTransitionAfter = CLng(t)
            Exit Function
        End If
    Next
    NextSignalTransitionAfter = CLng(simPeriod)
End Function

Function NextIncidentTransitionAfter(sec)
    If Not incidentEnabled Then
        NextIncidentTransitionAfter = CLng(simPeriod)
        Exit Function
    End If
    If CLng(sec) < CLng(incidentStartSec) Then
        NextIncidentTransitionAfter = CLng(incidentStartSec)
    ElseIf CLng(sec) < CLng(incidentEndSec) Then
        NextIncidentTransitionAfter = CLng(incidentEndSec)
    Else
        NextIncidentTransitionAfter = CLng(simPeriod)
    End If
End Function

Function IncidentStateAt(simSec)
    If incidentEnabled And CLng(simSec) >= CLng(incidentStartSec) And CLng(simSec) < CLng(incidentEndSec) Then
        IncidentStateAt = "RED"
    Else
        IncidentStateAt = "GREEN"
    End If
End Function

Function SignalCompositeStateAt(simSec)
    Dim scKey, major, minor, offset, cycle, pos, majorState, minorState, s
    s = ""
    For Each scKey In sigMajor.Keys
        major = CDbl(sigMajor(CStr(scKey)))
        minor = CDbl(DictValue(sigMinor, CStr(scKey), 0.0))
        offset = CDbl(DictValue(sigOffset, CStr(scKey), 0.0))
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
        s = s & CStr(scKey) & ":" & majorState & "/" & minorState & ";"
    Next
    SignalCompositeStateAt = s
End Function

Function MaxSignalCycleSec()
    Dim scKey, cycle, maxCycle
    maxCycle = 0
    For Each scKey In sigMajor.Keys
        cycle = CDbl(sigMajor(CStr(scKey))) + CDbl(DictValue(sigMinor, CStr(scKey), 0.0)) + _
            (2 * AMBER_SEC) + (2 * ALL_RED_SEC)
        If CLng(cycle) > CLng(maxCycle) Then maxCycle = CLng(cycle)
    Next
    MaxSignalCycleSec = CLng(maxCycle)
End Function

Sub RunControllerDecision(simSec)
    Dim stateJsonPath, outJsonPath, outCsvPath, cmd, result, effController
    Dim wallT0, wallSec, exitCode, outText, errText, perfT0
    perfT0 = PerfNow()
    stateJsonPath = fso.BuildPath(decisionDir, "state_" & Pad6(simSec) & ".json")
    outJsonPath = fso.BuildPath(decisionDir, "action_" & Pad6(simSec) & ".json")
    outCsvPath = fso.BuildPath(decisionDir, "action_" & Pad6(simSec) & ".csv")
    WriteStateJson simSec, stateJsonPath
    effController = controllerName
    If controlStartSec >= 0 And simSec < controlStartSec Then
        effController = warmupControllerName
        WScript.Echo "WARMUP_CONTROLLER sim_sec=" & simSec & " controller=" & effController
    End If
    cmd = pythonExe & " " & Q(adapterPath) & " --state-json " & Q(stateJsonPath) & _
        " --out-action-json " & Q(outJsonPath) & " --out-action-csv " & Q(outCsvPath) & _
        " --mapping-json " & Q(mappingPath) & " --controller " & Q(effController)
    If detectorMappingPath <> "" Then cmd = cmd & " --detector-mapping-json " & Q(detectorMappingPath)
    If calibrationPath <> "" Then cmd = cmd & " --calibration-json " & Q(calibrationPath)
    If tuningPath <> "" Then cmd = cmd & " --tuning-json " & Q(tuningPath)
    If lastActionJson <> "" Then cmd = cmd & " --previous-action-json " & Q(lastActionJson)
    wallT0 = Timer
    exitCode = RunCapture3(cmd, outText, errText)
    wallSec = ElapsedSec(wallT0)
    PerfAdd "decision.python", wallT0
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
    PerfAdd "decision.total", perfT0
End Sub

Sub ApplyActionCsv(simSec, csvPath)
    Dim ts, line, first, parts, kind, dsdNo, speed, dsd, readback, scNo, perfT0
    perfT0 = PerfNow()
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
                    ' 2026-08-01: class 70 (TAXI) is a VSL target. This row is also
                    ' emitted for the network's own entry DSDs 36-42 (they arrive as
                    ' segments[*].extra_dsd_controls), so the legacy decision points
                    ' get the same four classes as the RW ones - no class can be
                    ' silently restored to its inflow distribution downstream.
                    SetClassSpeed dsd, 70, speed
                    readback = SafeAtt(dsd, "DesSpeedDistr(10)") & "|" & SafeAtt(dsd, "DesSpeedDistr(70)")
                ElseIf kind = "ramp_meter" Then
                    scNo = CStr(CLng(ToDbl(parts(3))))
                    rampGreen(scNo) = CDbl(ToDbl(parts(11)))
                    readback = ApplyRampMeterSignal(CLng(scNo), CDbl(rampGreen(scNo)), simSec)
                ElseIf kind = "signal" Then
                    scNo = CStr(CLng(ToDbl(parts(3))))
                    sigMajor(scNo) = CDbl(ToDbl(parts(7)))
                    sigMinor(scNo) = CDbl(ToDbl(parts(8)))
                    sigOffset(scNo) = CDbl(ToDbl(parts(9)))
                    readback = EnableSignalControllerForRuntime(CLng(scNo))
                End If
                actionFile.WriteLine CStr(simSec) & "," & Join(parts, ",") & "," & readback
            End If
        End If
    Loop
    ts.Close
    PerfAdd "action.apply", perfT0
End Sub

Sub SetClassSpeed(dsd, vehClassNo, speedKph)
    TrySetAtt dsd, "DesSpeedDistr(" & CStr(vehClassNo) & ")", CLng(speedKph)
End Sub

Function EnableSignalControllerForRuntime(scNo)
    Dim sc, sg, sgNo, sgCount
    EnableSignalControllerForRuntime = ""
    On Error Resume Next
    Set sc = Vissim.Net.SignalControllers.ItemByKey(CLng(scNo))
    If Err.Number <> 0 Then
        EnableSignalControllerForRuntime = "ERR:" & Err.Description
        WScript.Echo "WARN=SIGNAL_SC_NOT_FOUND sc=" & scNo & " err=" & Err.Description
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    On Error GoTo 0
    sgCount = SignalGroupCount(sc)
    For sgNo = 1 To sgCount
        On Error Resume Next
        Set sg = sc.SGs.ItemByKey(CLng(sgNo))
        If Err.Number <> 0 Then
            Err.Clear
        Else
            TrySetAtt sg, "ContrByCOM", True
        End If
        On Error GoTo 0
    Next
    signalControlled(CStr(scNo)) = True
    EnableSignalControllerForRuntime = "stored"
End Function

Sub ApplyRuntimeSignals(simSec)
    Dim scKey, major, minor, offset, cycle, pos, majorState, minorState, perfT0
    perfT0 = PerfNow()
    If sigMajor.Count <= 0 Then
        PerfAdd "signals.runtime", perfT0
        Exit Sub
    End If
    For Each scKey In sigMajor.Keys
        major = CDbl(sigMajor(CStr(scKey)))
        minor = CDbl(sigMinor(CStr(scKey)))
        offset = CDbl(sigOffset(CStr(scKey)))
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
        ApplyRuntimeSignalController CLng(scKey), majorState, minorState
    Next
    PerfAdd "signals.runtime", perfT0
End Sub

Sub ApplyRuntimeSignalController(scNo, majorState, minorState)
    Dim sc, sg, sgNo, sgCount, sgName, state
    If Not signalControlled.Exists(CStr(scNo)) Then
        Dim ignored
        ignored = EnableSignalControllerForRuntime(CLng(scNo))
    End If
    Set sc = CachedSignalController(CLng(scNo))
    If sc Is Nothing Then
        WScript.Echo "WARN=SIGNAL_SC_RUNTIME_NOT_FOUND sc=" & scNo
        Exit Sub
    End If
    sgCount = CachedSignalGroupCount(CLng(scNo), sc)
    For sgNo = 1 To sgCount
        Set sg = CachedSignalGroup(CLng(scNo), CLng(sgNo))
        If Not (sg Is Nothing) Then
            sgName = CachedSignalGroupName(CLng(scNo), CLng(sgNo), sg)
            state = SignalStateForGroup(CLng(sgNo), sgName, majorState, minorState)
            If state <> "" Then
                Dim ignoredReadback
                ignoredReadback = SetSignalGroupState(CLng(scNo), CLng(sgNo), state)
            End If
        End If
    Next
End Sub

' Signal COM handles, group counts and group names are immutable for the whole
' run, but the per-second replay path re-resolved them every simulated second:
' ~1.3 ms per SignalControllers.ItemByKey and ~0.8 ms per SGs.ItemByKey, over 12k
' lookups that only ever produced 9 distinct SCs and 16 distinct SGs. Resolving
' once and reusing writes the same values through the same objects in the same
' order, so the actuation sequence is unchanged. Failed lookups are not cached,
' so a genuinely missing SC still retries and still warns on every attempt.
Function CachedSignalController(scNo)
    Dim key, sc
    key = CStr(CLng(scNo))
    If sigScCache.Exists(key) Then
        Set CachedSignalController = sigScCache(key)
        Exit Function
    End If
    Set CachedSignalController = Nothing
    On Error Resume Next
    Set sc = Vissim.Net.SignalControllers.ItemByKey(CLng(scNo))
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    On Error GoTo 0
    sigScCache.Add key, sc
    Set CachedSignalController = sc
End Function

Function CachedSignalGroup(scNo, sgNo)
    Dim key, sc, sg
    key = CStr(CLng(scNo)) & "-" & CStr(CLng(sgNo))
    If sigSgCache.Exists(key) Then
        Set CachedSignalGroup = sigSgCache(key)
        Exit Function
    End If
    Set CachedSignalGroup = Nothing
    Set sc = CachedSignalController(CLng(scNo))
    If sc Is Nothing Then Exit Function
    On Error Resume Next
    Set sg = sc.SGs.ItemByKey(CLng(sgNo))
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    On Error GoTo 0
    sigSgCache.Add key, sg
    Set CachedSignalGroup = sg
End Function

Function CachedSignalGroupCount(scNo, sc)
    Dim key
    key = CStr(CLng(scNo))
    If Not sigSgCountCache.Exists(key) Then sigSgCountCache.Add key, SignalGroupCount(sc)
    CachedSignalGroupCount = CLng(sigSgCountCache(key))
End Function

Function CachedSignalGroupName(scNo, sgNo, sg)
    Dim key
    key = CStr(CLng(scNo)) & "-" & CStr(CLng(sgNo))
    If Not sigSgNameCache.Exists(key) Then sigSgNameCache.Add key, SafeAtt(sg, "Name")
    CachedSignalGroupName = CStr(sigSgNameCache(key))
End Function

Function SignalStateForGroup(sgNo, sgName, majorState, minorState)
    Dim nameUpper
    nameUpper = UCase(CStr(sgName))
    If InStr(1, nameUpper, "EB", vbTextCompare) > 0 Or InStr(1, nameUpper, "WB", vbTextCompare) > 0 Then
        SignalStateForGroup = majorState
    ElseIf InStr(1, nameUpper, "NB", vbTextCompare) > 0 Or InStr(1, nameUpper, "SB", vbTextCompare) > 0 Then
        SignalStateForGroup = minorState
    ElseIf CLng(sgNo) = 1 Then
        SignalStateForGroup = majorState
    ElseIf CLng(sgNo) = 2 Then
        SignalStateForGroup = minorState
    Else
        SignalStateForGroup = "RED"
    End If
End Function

Function SignalGroupCount(sc)
    On Error Resume Next
    SignalGroupCount = CLng(sc.SGs.Count)
    If Err.Number <> 0 Then
        SignalGroupCount = 0
        Err.Clear
    End If
    On Error GoTo 0
End Function

Sub ApplyRuntimeRampMeters(simSec)
    Dim scs, i, scNo, perfT0
    perfT0 = PerfNow()
    scs = Split(RW_RAMP_METER_SCS, ",")
    For i = 0 To UBound(scs)
        scNo = Trim(scs(i))
        If scNo <> "" Then
            Dim ignoredReadback
            ignoredReadback = ApplyRampMeterSignal(CLng(scNo), CDbl(DictValue(rampGreen, scNo, 10.0)), simSec)
        End If
    Next
    PerfAdd "rampmeters.runtime", perfT0
End Sub

Function ApplyRampMeterSignal(scNo, greenSec, simSec)
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
    ApplyRampMeterSignal = SetSignalGroupState(scNo, 1, state)
End Function

Function SetSignalGroupState(scNo, sgNo, state)
    Dim sg
    SetSignalGroupState = ""
    Set sg = CachedSignalGroup(CLng(scNo), CLng(sgNo))
    If sg Is Nothing Then
        WScript.Echo "WARN=FAILED_SET_SIGSTATE sc=" & scNo & " sg=" & sgNo & " state=" & state & " err=signal group not resolved"
        SetSignalGroupState = "ERR:signal group not resolved"
        Exit Function
    End If
    On Error Resume Next
    sg.AttValue("SigState") = state
    If Err.Number <> 0 Then
        WScript.Echo "WARN=FAILED_SET_SIGSTATE sc=" & scNo & " sg=" & sgNo & " state=" & state & " err=" & Err.Description
        SetSignalGroupState = "ERR:" & Err.Description
        Err.Clear
    Else
        SetSignalGroupState = SafeAtt(sg, "SigState")
    End If
    On Error GoTo 0
End Function

Sub InstallIncidentLaneClosure()
    Dim link, lane, pos, sh, sgKey, shName
    Set incidentSc = EnsureSignalController(CLng(incidentSignalControllerNo), "RW_SC_" & incidentName)
    Set incidentSg = EnsureSignalGroup(incidentSc, CLng(incidentSignalGroupNo), "RW_SG_" & incidentName)
    TrySetAtt incidentSc, "Active", True
    TrySetAtt incidentSg, "ContrByCOM", True
    TrySetAtt incidentSg, "SigState", "GREEN"

    On Error Resume Next
    Set link = Vissim.Net.Links.ItemByKey(CLng(incidentLinkNo))
    If Err.Number <> 0 Then
        WScript.Echo "ERROR=INCIDENT_LINK_NOT_FOUND link=" & CStr(incidentLinkNo) & " err=" & Err.Description
        WScript.Quit 5
    End If
    Err.Clear
    If CDbl(incidentPosM) <= 0 Then
        pos = CDbl(link.AttValue("Length2D")) / 2.0
    Else
        pos = CDbl(incidentPosM)
    End If
    pos = ClampLinkPos(CDbl(pos), link)
    Set lane = link.Lanes.ItemByKey(CLng(incidentLaneNo))
    If Err.Number <> 0 Then
        WScript.Echo "ERROR=INCIDENT_LANE_NOT_FOUND link=" & CStr(incidentLinkNo) & " lane=" & CStr(incidentLaneNo) & " err=" & Err.Description
        WScript.Quit 6
    End If
    Err.Clear
    Set sh = Vissim.Net.SignalHeads.AddSignalHead(0, lane, CDbl(pos))
    If Err.Number <> 0 Then
        WScript.Echo "ERROR=INCIDENT_SIGNAL_HEAD_FAILED link=" & CStr(incidentLinkNo) & " lane=" & CStr(incidentLaneNo) & " pos=" & Num(pos) & " err=" & Err.Description
        WScript.Quit 7
    End If
    On Error GoTo 0

    shName = "RW_SH_" & incidentName & "_L" & CStr(incidentLinkNo) & "_LN" & CStr(incidentLaneNo)
    SetName sh, shName
    sgKey = CStr(incidentSignalControllerNo) & "-" & CStr(incidentSignalGroupNo)
    TrySetAtt sh, "SG", sgKey
    TrySetAtt sh, "Type", "CIRCULAR"
    Set incidentSignalHead = sh
    WScript.Echo "INCIDENT_INSTALLED sc=" & CStr(incidentSignalControllerNo) & " sg=" & CStr(incidentSignalGroupNo) & " link=" & CStr(incidentLinkNo) & " lane=" & CStr(incidentLaneNo) & " pos=" & Num(pos) & " sh=" & SafeAtt(sh, "No")
End Sub

Sub ApplyIncidentLaneClosure(simSec)
    Dim state, readback
    If Not incidentEnabled Then Exit Sub
    state = IncidentStateAt(CLng(simSec))
    If state = incidentStateLast Then Exit Sub
    readback = SetSignalGroupState(CLng(incidentSignalControllerNo), CLng(incidentSignalGroupNo), state)
    incidentStateLast = state
    WScript.Echo "INCIDENT_STATE sim_sec=" & CStr(simSec) & " state=" & state & " readback=" & readback
End Sub

Function EnsureSignalController(scNo, name)
    Dim sc
    On Error Resume Next
    Set sc = Vissim.Net.SignalControllers.ItemByKey(CLng(scNo))
    If Err.Number <> 0 Then
        Err.Clear
        Set sc = Vissim.Net.SignalControllers.AddSignalController(CLng(scNo))
    End If
    If Err.Number <> 0 Then
        WScript.Echo "ERROR=FAILED_ADD_SIGNAL_CONTROLLER sc=" & CStr(scNo) & " err=" & Err.Description
        WScript.Quit 8
    End If
    On Error GoTo 0
    SetName sc, name
    Set EnsureSignalController = sc
End Function

Function EnsureSignalGroup(sc, sgNo, name)
    Dim sg
    On Error Resume Next
    Set sg = sc.SGs.ItemByKey(CLng(sgNo))
    If Err.Number <> 0 Then
        Err.Clear
        Set sg = sc.SGs.AddSignalGroup(CLng(sgNo))
    End If
    If Err.Number <> 0 Then
        WScript.Echo "ERROR=FAILED_ADD_SIGNAL_GROUP sc=" & SafeAtt(sc, "No") & " sg=" & CStr(sgNo) & " err=" & Err.Description
        WScript.Quit 9
    End If
    On Error GoTo 0
    SetName sg, name
    Set EnsureSignalGroup = sg
End Function

Function ClampLinkPos(pos, link)
    Dim length
    length = CDbl(link.AttValue("Length2D"))
    If CDbl(pos) < 1 Then
        ClampLinkPos = 1
    ElseIf CDbl(pos) > length - 1 Then
        ClampLinkPos = length - 1
    Else
        ClampLinkPos = CDbl(pos)
    End If
End Function

Sub SetName(obj, name)
    On Error Resume Next
    obj.AttValue("Name") = name
    If Err.Number <> 0 Then
        WScript.Echo "WARN=FAILED_SET_NAME name=" & CStr(name) & " err=" & Err.Description
        Err.Clear
    End If
    On Error GoTo 0
End Sub

Sub WriteStateJson(simSec, path)
    Dim total, urban, freeway, ramp, boundary, other, meanSpeed, freewayMeanSpeed, stopped, demandUrbanNow, demandFreewayNow
    Dim countE(7), speedE(7), stoppedE(7), countW(7), speedW(7), stoppedW(7)
    Dim localCounts, localStopped, localSpeedSums, scanOk, perfT0
    perfT0 = PerfNow()
    ScanVehicleState total, urban, freeway, ramp, boundary, other, meanSpeed, freewayMeanSpeed, stopped, _
        countE, speedE, stoppedE, countW, speedW, stoppedW, localCounts, localStopped, localSpeedSums, scanOk
    DemandForecastAtSimSec simSec, demandUrbanNow, demandFreewayNow

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
    ts.WriteLine "  ""demand"": {""urban_volume_vph"": " & Num(demandUrbanNow) & ", ""freeway_volume_vph"": " & Num(demandFreewayNow) & ", ""ramp_volume_vph"": 0, ""demand_profile"": """ & demandForecastProfileName & """},"
    ts.WriteLine "  ""ramp_counts"": " & RampCountsJson(localCounts) & ","
    ts.WriteLine "  ""local_observation"": {"
    ts.WriteLine "    ""schema_version"": 1,"
    ts.WriteLine "    ""mode"": ""real_world_connector_local_v1"","
    ts.WriteLine "    ""source"": ""vissim_vehicle_link_scan"","
    ts.WriteLine "    ""detector_mapping_json"": """ & JsonEscape(detectorMappingPath) & ""","
    ts.WriteLine "    ""global_vehicle_scan_masked"": true,"
    ts.WriteLine "    ""link_counts"": " & LocalObservationLinkCountsJson(localCounts)
    ts.WriteLine "  },"
    ts.WriteLine "  ""freeway_segments"": {"
    ts.WriteLine "    ""FW_E"": " & SegmentArrayJson(countE, speedE, RW_FW_E_SEG_LENGTHS_KM, RW_FW_E_LANES) & ","
    ts.WriteLine "    ""FW_W"": " & SegmentArrayJson(countW, speedW, RW_FW_W_SEG_LENGTHS_KM, RW_FW_W_LANES)
    ts.WriteLine "  }"
    ts.WriteLine "}"
    ts.Close
    PerfAdd "state.json", perfT0
End Sub

Function SegmentArrayJson(counts, speeds, lengthsCsv, lanes)
    Dim i, s, lengthKm
    s = "["
    For i = 0 To 7
        If i > 0 Then s = s & ", "
        lengthKm = CsvNumberAt(lengthsCsv, i, 1.0)
        s = s & "{""count"": " & CStr(counts(i)) & ", ""speed_sum"": " & Num(speeds(i)) & ", ""length_km"": " & Num(lengthKm) & ", ""lanes"": " & CStr(lanes) & "}"
    Next
    s = s & "]"
    SegmentArrayJson = s
End Function

Sub LogStateCsv(simSec)
    Dim total, urban, freeway, ramp, boundary, other, meanSpeed, freewayMeanSpeed, stopped
    Dim countE(7), speedE(7), stoppedE(7), countW(7), speedW(7), stoppedW(7), status, wall
    Dim linkCounts, linkStopped, linkSpeedSums, scanOk, perfT0
    perfT0 = PerfNow()
    ScanVehicleState total, urban, freeway, ramp, boundary, other, meanSpeed, freewayMeanSpeed, stopped, _
        countE, speedE, stoppedE, countW, speedW, stoppedW, linkCounts, linkStopped, linkSpeedSums, scanOk
    status = LastControllerStatus()
    wall = LastDecisionWallSec()
    stateFile.WriteLine CStr(simSec) & "," & CStr(total) & "," & CStr(urban) & "," & CStr(freeway) & "," & _
        CStr(ramp) & "," & CStr(boundary) & "," & CStr(other) & "," & Num(meanSpeed) & "," & _
        Num(freewayMeanSpeed) & "," & CStr(stopped) & ",VISSIM_REAL_WORLD_" & UCase(controllerName) & "," & status & "," & wall
    If LogBottleneckDetailsEnabled() And scanOk Then
        WriteBottleneckRows simSec, countE, stoppedE, speedE, countW, stoppedW, speedW, linkCounts, linkStopped, linkSpeedSums
    End If
    PerfAdd "log.state_csv", perfT0
End Sub

Function LogBottleneckDetailsEnabled()
    LogBottleneckDetailsEnabled = True
End Function

Sub WriteBottleneckRows(simSec, countE, stoppedE, speedE, countW, stoppedW, speedW, linkCounts, linkStopped, linkSpeedSums)
    Dim item, count, stopped, meanSpeed
    For Each item In linkCounts.Keys
        count = CDbl(linkCounts(item))
        stopped = DictNumber(linkStopped, item)
        meanSpeed = 0
        If count > 0 Then meanSpeed = DictNumber(linkSpeedSums, item) / count
        bottleneckLinkFile.WriteLine CStr(simSec) & "," & item & "," & CStr(CLng(count)) & "," & _
            CStr(CLng(stopped)) & "," & Num(meanSpeed) & "," & LinkCategory(CLng(item)) & "," & _
            BoolInt(InCsvInt(CLng(item), RW_FREEWAY_LINKS)) & "," & _
            BoolInt(InCsvInt(CLng(item), RW_RAMP_METER_CONNECTORS)) & "," & _
            BoolInt(InCsvInt(CLng(item), RW_LOCAL_OBSERVABLE_LINKS))
    Next

    WriteBottleneckSegmentRows simSec, "FW_E", "E", CLng(RW_FW_E_LINK), countE, stoppedE, speedE, RW_FW_E_SEG_LENGTHS_KM, CLng(RW_FW_E_LANES)
    WriteBottleneckSegmentRows simSec, "FW_W", "W", CLng(RW_FW_W_LINK), countW, stoppedW, speedW, RW_FW_W_SEG_LENGTHS_KM, CLng(RW_FW_W_LANES)
End Sub

Sub WriteBottleneckSegmentRows(simSec, modelLink, direction, physicalLink, counts, stoppedCounts, speedSums, lengthsCsv, lanes)
    Dim i, count, stopped, meanSpeed, lengthKm, density, segmentId
    For i = 0 To 7
        count = CDbl(counts(i))
        stopped = CDbl(stoppedCounts(i))
        meanSpeed = 0
        If count > 0 Then meanSpeed = CDbl(speedSums(i)) / count
        lengthKm = CsvNumberAt(lengthsCsv, i, 1.0)
        density = 0
        If lengthKm > 0 And lanes > 0 Then density = count / (lengthKm * CDbl(lanes))
        segmentId = "RW_" & modelLink & "_S" & CStr(i)
        bottleneckSegmentFile.WriteLine CStr(simSec) & "," & modelLink & "," & direction & "," & CStr(i) & "," & _
            segmentId & "," & CStr(physicalLink) & "," & CStr(CLng(count)) & "," & CStr(CLng(stopped)) & "," & _
            Num(meanSpeed) & "," & Num(lengthKm) & "," & CStr(lanes) & "," & Num(density)
    Next
End Sub

Sub AddDictNumber(dict, key, value)
    If Not dict.Exists(CStr(key)) Then dict.Add CStr(key), 0.0
    dict(CStr(key)) = CDbl(dict(CStr(key))) + CDbl(value)
End Sub

Function DictNumber(dict, key)
    If IsObject(dict) And dict.Exists(CStr(key)) Then
        DictNumber = CDbl(dict(CStr(key)))
    Else
        DictNumber = 0.0
    End If
End Function

Function LinkCategory(linkNo)
    If InCsvInt(linkNo, RW_FREEWAY_LINKS) Then
        LinkCategory = "freeway"
    ElseIf InCsvInt(linkNo, RW_RAMP_METER_CONNECTORS) Then
        LinkCategory = "ramp_meter_connector"
    ElseIf InCsvInt(linkNo, RW_LOCAL_OBSERVABLE_LINKS) Then
        LinkCategory = "local_observable_connector"
    ElseIf InCsvInt(linkNo, RW_FREEWAY_INPUT_LINKS) Then
        LinkCategory = "freeway_input"
    Else
        LinkCategory = "urban_or_other"
    End If
End Function

Function BoolInt(value)
    If CBool(value) Then
        BoolInt = 1
    Else
        BoolInt = 0
    End If
End Function

' ONE vehicle scan per time point. This is the union of what three separate
' passes used to compute - ComputeDetailedState (state row + FW_E/FW_W segment
' aggregates), LogBottleneckCsv (per-link and per-segment aggregates) and
' VehicleLinkCounts (per-link counts for the state JSON). Each of those re-read
' the same GetMultiAttValues arrays and re-parsed every row, and no simulation
' step happens between them, so folding them into one pass leaves every emitted
' value identical. scanOk mirrors the old behaviour where a failed array read
' suppressed the bottleneck rows entirely.
Sub ScanVehicleState(ByRef total, ByRef urban, ByRef freeway, ByRef ramp, ByRef boundary, ByRef other, _
        ByRef meanSpeed, ByRef freewayMeanSpeed, ByRef stopped, _
        ByRef countE, ByRef speedE, ByRef stoppedE, ByRef countW, ByRef speedW, ByRef stoppedW, _
        ByRef linkCounts, ByRef linkStopped, ByRef linkSpeedSums, ByRef scanOk)
    total = 0: urban = 0: freeway = 0: ramp = 0: boundary = 0: other = 0
    meanSpeed = 0: freewayMeanSpeed = 0: stopped = 0
    scanOk = False
    Set linkCounts = CreateObject("Scripting.Dictionary")
    Set linkStopped = CreateObject("Scripting.Dictionary")
    Set linkSpeedSums = CreateObject("Scripting.Dictionary")
    Dim i
    For i = 0 To 7
        countE(i) = 0: speedE(i) = 0: stoppedE(i) = 0
        countW(i) = 0: speedW(i) = 0: stoppedW(i) = 0
    Next

    Dim laneArray, posArray, speedArray, ok, lo, hi, row
    Dim linkNo, key, pos, speed, speedSum, freewaySpeedSum, seg, chainPos, isStopped, perfT0
    perfT0 = PerfNow()
    speedSum = 0: freewaySpeedSum = 0
    ok = ReadVehicleLanePosSpeed(laneArray, posArray, speedArray)
    If Not ok Then
        PerfAdd "scan.vehicles", perfT0
        Exit Sub
    End If
    scanOk = True

    lo = MultiLBound(laneArray)
    hi = MultiUBound(laneArray)
    For row = lo To hi
        total = total + 1
        linkNo = FirstInt(MultiValue(laneArray, row))
        pos = CDblOrZero(MultiValue(posArray, row))
        speed = CDblOrZero(MultiValue(speedArray, row))
        speedSum = speedSum + speed
        isStopped = (speed < 1)
        If isStopped Then stopped = stopped + 1

        ' Malformed lane strings cannot be tied back to a VISSIM link, so they stay
        ' out of the per-link aggregates - exactly as LogBottleneckCsv skipped them.
        If linkNo > 0 Then
            key = CStr(linkNo)
            AddDictNumber linkCounts, key, 1.0
            AddDictNumber linkSpeedSums, key, speed
            If isStopped Then AddDictNumber linkStopped, key, 1.0
        End If

        chainPos = ChainPosCsv(linkNo, pos, RW_FW_E_CHAIN_LINKS, RW_FW_E_CHAIN_OFFSETS_M)
        If chainPos >= 0 Then
            freeway = freeway + 1
            freewaySpeedSum = freewaySpeedSum + speed
            seg = SegmentIndexCsv(chainPos, RW_FW_E_SEG_BOUNDS)
            countE(seg) = countE(seg) + 1
            speedE(seg) = speedE(seg) + speed
            If isStopped Then stoppedE(seg) = stoppedE(seg) + 1
        Else
            chainPos = ChainPosCsv(linkNo, pos, RW_FW_W_CHAIN_LINKS, RW_FW_W_CHAIN_OFFSETS_M)
            If chainPos >= 0 Then
                freeway = freeway + 1
                freewaySpeedSum = freewaySpeedSum + speed
                seg = SegmentIndexCsv(chainPos, RW_FW_W_SEG_BOUNDS)
                countW(seg) = countW(seg) + 1
                speedW(seg) = speedW(seg) + speed
                If isStopped Then stoppedW(seg) = stoppedW(seg) + 1
            ElseIf InCsvInt(linkNo, RW_RAMP_METER_CONNECTORS) Then
                ramp = ramp + 1
            ElseIf RW_CLASSIFY_UNMATCHED_AS_URBAN Then
                urban = urban + 1
            Else
                other = other + 1
            End If
        End If
    Next
    If total > 0 Then meanSpeed = speedSum / total
    If freeway > 0 Then freewayMeanSpeed = freewaySpeedSum / freeway
    PerfAdd "scan.vehicles", perfT0
End Sub

' (link, pos on link) -> mainline chain coordinate, or -1 when the link is not a
' member of that chain. This is what keeps the measurement grid aligned with the
' control grid: the VSL decisions were placed on the same chain coordinates.
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

Function RampCountsJson(counts)
    Dim sums, keys, conns, i, key, conn, s
    Set sums = CreateObject("Scripting.Dictionary")
    sums("R_D_W") = 0: sums("R_D_E") = 0: sums("R_F_W") = 0: sums("R_F_E") = 0
    keys = Split(RW_RAMP_METER_MODEL_KEYS, ",")
    conns = Split(RW_RAMP_METER_CONNECTORS, ",")
    For i = 0 To UBound(conns)
        key = Trim(keys(i))
        conn = CLng(Trim(conns(i)))
        If Not sums.Exists(key) Then sums(key) = 0
        sums(key) = CLng(sums(key)) + DictCount(counts, conn)
    Next
    s = "{"
    s = s & """R_D_W"": " & CStr(sums("R_D_W")) & ", "
    s = s & """R_D_E"": " & CStr(sums("R_D_E")) & ", "
    s = s & """R_F_W"": " & CStr(sums("R_F_W")) & ", "
    s = s & """R_F_E"": " & CStr(sums("R_F_E")) & ", "
    s = s & """D"": " & CStr(CLng(sums("R_D_W")) + CLng(sums("R_D_E"))) & ", "
    s = s & """F"": " & CStr(CLng(sums("R_F_W")) + CLng(sums("R_F_E"))) & "}"
    RampCountsJson = s
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

Function LinkCountsJson(counts)
    Dim s, key, first
    s = "{"
    first = True
    If IsObject(counts) Then
        For Each key In counts.Keys
            If Not first Then s = s & ", "
            s = s & """" & JsonEscape(CStr(key)) & """: " & CStr(CLng(counts(key)))
            first = False
        Next
    End If
    s = s & "}"
    LinkCountsJson = s
End Function

Function LocalObservationLinkCountsJson(counts)
    Dim parts, i, linkText, s
    parts = Split(RW_LOCAL_OBSERVABLE_LINKS, ",")
    s = "{"
    For i = 0 To UBound(parts)
        linkText = Trim(parts(i))
        If linkText <> "" Then
            If Len(s) > 1 Then s = s & ", "
            s = s & """" & JsonEscape(linkText) & """: " & CStr(DictCount(counts, CLng(linkText)))
        End If
    Next
    s = s & "}"
    LocalObservationLinkCountsJson = s
End Function

Function JsonEscape(value)
    JsonEscape = Replace(CStr(value), "\", "\\")
    JsonEscape = Replace(JsonEscape, Chr(34), "\" & Chr(34))
End Function

Function DictValue(dictObj, key, defaultValue)
    If IsObject(dictObj) And dictObj.Exists(CStr(key)) Then
        DictValue = dictObj(CStr(key))
    Else
        DictValue = defaultValue
    End If
End Function

Sub ComputeOriginalDemandAverages(ByRef urbanAvg, ByRef freewayAvg)
    Dim viArray, vi, linkNo, volume, urbanSum, urbanN, freewaySum, freewayN
    urbanSum = 0: urbanN = 0: freewaySum = 0: freewayN = 0
    On Error Resume Next
    viArray = Vissim.Net.VehicleInputs.GetAll
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        Exit Sub
    End If
    On Error GoTo 0
    For Each vi In viArray
        linkNo = ObjectLinkNo(vi)
        volume = ToDbl(SafeAtt(vi, "Volume(1)"))
        If InCsvInt(linkNo, RW_FREEWAY_INPUT_LINKS) Then
            freewaySum = freewaySum + CDbl(volume)
            freewayN = freewayN + 1
        Else
            urbanSum = urbanSum + CDbl(volume)
            urbanN = urbanN + 1
        End If
    Next
    If urbanN > 0 Then urbanAvg = urbanSum / urbanN
    If freewayN > 0 Then freewayAvg = freewaySum / freewayN
End Sub

Sub LoadInpxDemandSchedule(inpxPath, rolesPath, scale, profilePath)
    Dim xmlDoc, inputRoles, roleMultipliers, defaultMultiplier, viNode, volNode
    Dim viNo, role, roleKey, multiplier, linkNo, secKey, sec, volume, isFreeway
    Dim urbanSumBySec, urbanNBySec, freewaySumBySec, freewayNBySec, key
    Set demandUrbanBySec = CreateObject("Scripting.Dictionary")
    Set demandFreewayBySec = CreateObject("Scripting.Dictionary")
    Set urbanSumBySec = CreateObject("Scripting.Dictionary")
    Set urbanNBySec = CreateObject("Scripting.Dictionary")
    Set freewaySumBySec = CreateObject("Scripting.Dictionary")
    Set freewayNBySec = CreateObject("Scripting.Dictionary")
    demandScheduleLoaded = False
    demandForecastProfileName = "real_world_inpx_time_profile"

    Set xmlDoc = CreateObject("Msxml2.DOMDocument.6.0")
    xmlDoc.async = False
    xmlDoc.validateOnParse = False
    On Error Resume Next
    xmlDoc.Load inpxPath
    If Err.Number <> 0 Or xmlDoc.parseError.errorCode <> 0 Then
        WScript.Echo "WARN=DEMAND_SCHEDULE_XML_LOAD_FAILED path=" & CStr(inpxPath) & " err=" & Err.Description
        Err.Clear
        On Error GoTo 0
        ComputeOriginalDemandAverages urbanDemandVph, freewayDemandVph
        Exit Sub
    End If
    On Error GoTo 0

    Set inputRoles = LoadVehicleInputRoles(rolesPath)
    Set roleMultipliers = CreateObject("Scripting.Dictionary")
    defaultMultiplier = 1.0
    If Trim(CStr(profilePath)) <> "" Then
        Set roleMultipliers = LoadRoleMultipliers(profilePath)
        demandForecastProfileName = "real_world_inpx_time_profile_scaled"
        If roleMultipliers.Exists("__default__") Then defaultMultiplier = CDbl(roleMultipliers("__default__"))
    End If

    For Each viNode In xmlDoc.SelectNodes("//vehicleInput")
        viNo = CStr(viNode.GetAttribute("no"))
        linkNo = FirstInt(viNode.GetAttribute("link"))
        role = ""
        If inputRoles.Exists(viNo) Then role = CStr(inputRoles(viNo))
        roleKey = LCase(Trim(role))
        multiplier = defaultMultiplier
        If roleMultipliers.Exists(roleKey) Then multiplier = CDbl(roleMultipliers(roleKey))
        If roleMultipliers.Exists("no:" & viNo) Then multiplier = CDbl(roleMultipliers("no:" & viNo))
        isFreeway = (Left(roleKey, 7) = "freeway" Or InCsvInt(linkNo, RW_FREEWAY_INPUT_LINKS))

        For Each volNode In viNode.SelectNodes("./timeIntVehVols/timeIntervalVehVolume")
            sec = TimeIntStartSec(CStr(volNode.GetAttribute("timeInt")))
            secKey = CStr(sec)
            volume = ToDbl(volNode.GetAttribute("volume")) * CDbl(scale) * CDbl(multiplier)
            If isFreeway Then
                AddDemandScheduleValue freewaySumBySec, freewayNBySec, secKey, volume
            Else
                AddDemandScheduleValue urbanSumBySec, urbanNBySec, secKey, volume
            End If
        Next
    Next

    For Each key In urbanSumBySec.Keys
        If CDbl(urbanNBySec(key)) > 0 Then demandUrbanBySec(key) = CDbl(urbanSumBySec(key)) / CDbl(urbanNBySec(key))
    Next
    For Each key In freewaySumBySec.Keys
        If CDbl(freewayNBySec(key)) > 0 Then demandFreewayBySec(key) = CDbl(freewaySumBySec(key)) / CDbl(freewayNBySec(key))
    Next

    If demandUrbanBySec.Count > 0 Or demandFreewayBySec.Count > 0 Then
        demandScheduleLoaded = True
        WScript.Echo "DEMAND_FORECAST_SCHEDULE_LOADED intervals=" & CStr(MaxDictCount(demandUrbanBySec, demandFreewayBySec)) & " profile=" & demandForecastProfileName
    Else
        WScript.Echo "WARN=DEMAND_FORECAST_SCHEDULE_EMPTY fallback=Volume(1)_averages"
        ComputeOriginalDemandAverages urbanDemandVph, freewayDemandVph
    End If
End Sub

Sub AddDemandScheduleValue(sumDict, nDict, secKey, volume)
    If Not sumDict.Exists(secKey) Then
        sumDict(secKey) = 0.0
        nDict(secKey) = 0
    End If
    sumDict(secKey) = CDbl(sumDict(secKey)) + CDbl(volume)
    nDict(secKey) = CLng(nDict(secKey)) + 1
End Sub

Function MaxDictCount(a, b)
    If a.Count >= b.Count Then
        MaxDictCount = a.Count
    Else
        MaxDictCount = b.Count
    End If
End Function

Function TimeIntStartSec(value)
    Dim parts, text
    text = Trim(CStr(value))
    If text = "" Then
        TimeIntStartSec = 0
        Exit Function
    End If
    parts = Split(text, " ")
    TimeIntStartSec = CLng(ToDbl(parts(UBound(parts))) / 1000.0)
End Function

Sub DemandForecastAtSimSec(simSec, ByRef urbanOut, ByRef freewayOut)
    Dim secKey
    urbanOut = urbanDemandVph
    freewayOut = freewayDemandVph
    If CBool(demandScheduleLoaded) Then
        secKey = ActiveDemandScheduleKey(simSec)
        If CStr(secKey) <> "" Then
            If demandUrbanBySec.Exists(secKey) Then urbanOut = CDbl(demandUrbanBySec(secKey))
            If demandFreewayBySec.Exists(secKey) Then freewayOut = CDbl(demandFreewayBySec(secKey))
        End If
    End If
End Sub

Function ActiveDemandScheduleKey(simSec)
    Dim key, sec, best, minSec
    ActiveDemandScheduleKey = ""
    best = -1
    minSec = 2147483647
    If demandUrbanBySec.Count > 0 Then
        For Each key In demandUrbanBySec.Keys
            sec = CLng(key)
            If sec < minSec Then minSec = sec
            If sec <= CLng(simSec) And sec > best Then best = sec
        Next
    ElseIf demandFreewayBySec.Count > 0 Then
        For Each key In demandFreewayBySec.Keys
            sec = CLng(key)
            If sec < minSec Then minSec = sec
            If sec <= CLng(simSec) And sec > best Then best = sec
        Next
    End If
    If best >= 0 Then
        ActiveDemandScheduleKey = CStr(best)
    ElseIf minSec < 2147483647 Then
        ActiveDemandScheduleKey = CStr(minSec)
    End If
End Function

' ---------------------------------------------------------------------------
' Vehicle input demand scaling.
'
' Bug fixed 2026-08-02: these two entry points used to write only "Volume(1)".
' Volume(n) indexes the n-th VEHICLEINPUT time interval, and this network has
' six of them (start 0 / 900 / 1800 / 2700 / 3600 / 4500 s). Volume(1) is the
' 0-900 s warmup alone, so the 900-4500 s analysis window always ran at the
' original .inpx demand while the runner reported the scale as applied. Every
' -DemandScale / -DemandProfile run before this date was unscaled in its
' analysis window.
'
' COM schema, confirmed by direct probe against modi_eval_rw_control.inpx
' (scripts/probe_vehicle_input_time_interval_api.vbs):
'   Vissim.Net.TimeIntervalSets.ItemByKey(1).TimeInts -> 6 items,
'       AttValue("Index") = 1..6, AttValue("Start") = 0,900,...,4500 (seconds).
'   vehicleInput.TimeIntVehVols -> one item per (time interval, veh composition).
'       item.AttValue("TimeInt") = "<intervalSetNo>-<intervalIndex>", e.g. "1-2".
'       item.AttValue("Volume")  is readable AND writable for every interval.
'   vi.AttValue("Volume(k)") is the same storage as the k-th TimeIntVehVols item
'       (write to either is visible through the other); k > interval count raises
'       "Object k not found".
' The .inpx spelling timeInt="1 900000" is "<intervalSetNo> <start in ms>";
' COM reports the same interval as "1-2".
'
' The interval count is read from the network per input, never assumed.
' Any COM failure or readback mismatch is fatal: the original bug was a silent
' partial write, so a half-applied demand must not reach the simulation.
' ---------------------------------------------------------------------------

Sub ScaleVehicleInputDemand(scale)
    Dim roleMultipliers, inputRoles, scaledCount
    Set roleMultipliers = CreateObject("Scripting.Dictionary")
    Set inputRoles = CreateObject("Scripting.Dictionary")
    scaledCount = ApplyDemandMultipliers(scale, roleMultipliers, inputRoles, 1.0, "DEMAND_SCALE")
    WScript.Echo "DEMAND_SCALE_APPLIED scale=" & Num(scale) & " vehicle_inputs=" & CStr(scaledCount)
End Sub

Sub ApplyVehicleInputDemandProfile(scale, profilePath, rolesPath)
    Dim roleMultipliers, inputRoles, defaultMultiplier, scaledCount
    Set roleMultipliers = LoadRoleMultipliers(profilePath)
    Set inputRoles = LoadVehicleInputRoles(rolesPath)
    defaultMultiplier = 1.0
    If roleMultipliers.Exists("__default__") Then defaultMultiplier = CDbl(roleMultipliers("__default__"))
    scaledCount = ApplyDemandMultipliers(scale, roleMultipliers, inputRoles, defaultMultiplier, "DEMAND_PROFILE")
    WScript.Echo "DEMAND_PROFILE_APPLIED scale=" & Num(scale) & " vehicle_inputs=" & CStr(scaledCount) & " profile_roles=" & CStr(roleMultipliers.Count) & " mapped_inputs=" & CStr(inputRoles.Count)
End Sub

' Multiply every time interval of every vehicle input by scale * role multiplier.
' Returns the number of vehicle inputs touched. Freeway inputs are echoed with
' per-interval before/after volumes; all inputs are echoed as per-interval totals.
Function ApplyDemandMultipliers(scale, roleMultipliers, inputRoles, defaultMultiplier, tag)
    Dim viArray, vi, viNo, linkNo, role, roleKey, multiplier, factor
    Dim beforeText, afterText, nIntervals, scaledCount, maxIntervals
    Dim totalsBefore, totalsAfter, i, key, totalBeforeText, totalAfterText

    EchoDemandIntervalSchedule

    On Error Resume Next
    viArray = Vissim.Net.VehicleInputs.GetAll
    If Err.Number <> 0 Then FatalDemandError tag & "_GET_INPUTS_FAILED err=" & Err.Description
    Err.Clear
    On Error GoTo 0

    Set totalsBefore = CreateObject("Scripting.Dictionary")
    Set totalsAfter = CreateObject("Scripting.Dictionary")
    scaledCount = 0
    maxIntervals = 0
    For Each vi In viArray
        viNo = CStr(CLng(ToDbl(SafeAtt(vi, "No"))))
        linkNo = ObjectLinkNo(vi)
        role = ""
        If inputRoles.Exists(viNo) Then role = CStr(inputRoles(viNo))
        roleKey = LCase(Trim(role))
        multiplier = defaultMultiplier
        If roleMultipliers.Exists(roleKey) Then multiplier = CDbl(roleMultipliers(roleKey))
        If roleMultipliers.Exists("no:" & viNo) Then multiplier = CDbl(roleMultipliers("no:" & viNo))
        factor = CDbl(scale) * CDbl(multiplier)
        ScaleInputAllIntervals vi, factor, totalsBefore, totalsAfter, beforeText, afterText, nIntervals
        If CLng(nIntervals) > maxIntervals Then maxIntervals = CLng(nIntervals)
        scaledCount = scaledCount + 1
        If Left(roleKey, 7) = "freeway" Or InCsvInt(linkNo, RW_FREEWAY_INPUT_LINKS) Then
            WScript.Echo tag & "_INPUT no=" & viNo & " link=" & CStr(linkNo) & _
                " role=" & roleKey & " factor=" & Num(factor) & _
                " intervals=" & CStr(nIntervals) & _
                " before=" & beforeText & " after=" & afterText
        End If
    Next

    totalBeforeText = ""
    totalAfterText = ""
    For i = 1 To maxIntervals
        key = CStr(i)
        If i > 1 Then
            totalBeforeText = totalBeforeText & ","
            totalAfterText = totalAfterText & ","
        End If
        If totalsBefore.Exists(key) Then
            totalBeforeText = totalBeforeText & Num(totalsBefore(key))
            totalAfterText = totalAfterText & Num(totalsAfter(key))
        Else
            totalBeforeText = totalBeforeText & "0"
            totalAfterText = totalAfterText & "0"
        End If
    Next
    WScript.Echo tag & "_TOTALS vehicle_inputs=" & CStr(scaledCount) & _
        " intervals=" & CStr(maxIntervals) & _
        " before_vph=" & totalBeforeText & " after_vph=" & totalAfterText

    ApplyDemandMultipliers = scaledCount
End Function

' Scale one vehicle input across all of its time intervals, verifying each write
' by readback. Fills beforeText/afterText (comma separated, interval order),
' accumulates per-interval sums into totalsBefore/totalsAfter, and returns the
' interval row count in nIntervals.
Sub ScaleInputAllIntervals(vi, factor, totalsBefore, totalsAfter, beforeText, afterText, nIntervals)
    Dim col, arr, item, viNo, timeInt, before, target, after, idx, key, tol
    viNo = SafeAtt(vi, "No")
    beforeText = ""
    afterText = ""
    nIntervals = 0

    On Error Resume Next
    Set col = vi.TimeIntVehVols
    If Err.Number <> 0 Then FatalDemandError "DEMAND_INTERVAL_CONTAINER_MISSING no=" & viNo & " err=" & Err.Description
    arr = col.GetAll
    If Err.Number <> 0 Then FatalDemandError "DEMAND_INTERVAL_GETALL_FAILED no=" & viNo & " err=" & Err.Description
    Err.Clear
    On Error GoTo 0

    For Each item In arr
        timeInt = SafeAtt(item, "TimeInt")
        before = ToDbl(SafeAtt(item, "Volume"))
        target = CDbl(before) * CDbl(factor)
        On Error Resume Next
        item.AttValue("Volume") = target
        If Err.Number <> 0 Then FatalDemandError "DEMAND_INTERVAL_SET_FAILED no=" & viNo & " time_int=" & timeInt & " target=" & Num(target) & " err=" & Err.Description
        Err.Clear
        On Error GoTo 0
        after = ToDbl(SafeAtt(item, "Volume"))
        tol = 0.001 + Abs(CDbl(target)) * 0.000001
        If Abs(CDbl(after) - CDbl(target)) > tol Then
            FatalDemandError "DEMAND_INTERVAL_READBACK_MISMATCH no=" & viNo & " time_int=" & timeInt & _
                " target=" & Num(target) & " readback=" & Num(after)
        End If

        nIntervals = nIntervals + 1
        idx = TimeIntIndex(timeInt)
        If idx <= 0 Then idx = nIntervals
        key = CStr(idx)
        If Not totalsBefore.Exists(key) Then
            totalsBefore(key) = 0.0
            totalsAfter(key) = 0.0
        End If
        totalsBefore(key) = CDbl(totalsBefore(key)) + CDbl(before)
        totalsAfter(key) = CDbl(totalsAfter(key)) + CDbl(after)

        If nIntervals > 1 Then
            beforeText = beforeText & ","
            afterText = afterText & ","
        End If
        beforeText = beforeText & Num(before)
        afterText = afterText & Num(after)
    Next

    If nIntervals = 0 Then FatalDemandError "DEMAND_INTERVAL_EMPTY no=" & viNo
End Sub

' "1-2" -> 2. Returns 0 when the key does not carry an interval index.
Function TimeIntIndex(value)
    Dim text, p
    text = Trim(CStr(value))
    p = InStrRev(text, "-")
    If p > 0 And p < Len(text) Then
        TimeIntIndex = CLng(ToDbl(Mid(text, p + 1)))
    Else
        TimeIntIndex = 0
    End If
End Function

' Echo the VEHICLEINPUT time interval schedule read from the network, so the
' runlog records how many intervals the demand write had to cover.
Sub EchoDemandIntervalSchedule()
    Dim tis, arr, ti, line, cnt
    On Error Resume Next
    Set tis = Vissim.Net.TimeIntervalSets.ItemByKey(1)
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        WScript.Echo "WARN=DEMAND_INTERVAL_SCHEDULE_UNAVAILABLE"
        Exit Sub
    End If
    arr = tis.TimeInts.GetAll
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        WScript.Echo "WARN=DEMAND_INTERVAL_SCHEDULE_UNAVAILABLE"
        Exit Sub
    End If
    On Error GoTo 0
    line = ""
    cnt = 0
    For Each ti In arr
        cnt = cnt + 1
        If cnt > 1 Then line = line & ","
        line = line & CStr(CLng(ToDbl(SafeAtt(ti, "Start"))))
    Next
    WScript.Echo "DEMAND_INTERVAL_SCHEDULE set=1 count=" & CStr(cnt) & " start_sec=" & line
End Sub

Sub FatalDemandError(detail)
    WScript.Echo "ERROR=" & detail
    WScript.Quit 12
End Sub

Function LoadRoleMultipliers(profilePath)
    Dim dict, fullPath, ts, line, first, parts, key, value
    Set dict = CreateObject("Scripting.Dictionary")
    fullPath = fso.GetAbsolutePathName(profilePath)
    If Not fso.FileExists(fullPath) Then
        WScript.Echo "WARN=DEMAND_PROFILE_NOT_FOUND path=" & fullPath
        Set LoadRoleMultipliers = dict
        Exit Function
    End If
    Set ts = fso.OpenTextFile(fullPath, 1, False)
    first = True
    Do Until ts.AtEndOfStream
        line = Trim(ts.ReadLine)
        If line <> "" And Left(line, 1) <> "#" Then
            parts = Split(line, ",")
            If first And UBound(parts) >= 1 And LCase(Trim(parts(0))) = "role" Then
                first = False
            ElseIf UBound(parts) >= 1 Then
                key = LCase(Trim(parts(0)))
                value = ToDbl(parts(1))
                If key <> "" Then dict(key) = CDbl(value)
                first = False
            End If
        End If
    Loop
    ts.Close
    Set LoadRoleMultipliers = dict
End Function

Function LoadVehicleInputRoles(rolesPath)
    Dim dict, fullPath, ts, line, first, parts, noText, roleText
    Set dict = CreateObject("Scripting.Dictionary")
    fullPath = fso.GetAbsolutePathName(rolesPath)
    If Not fso.FileExists(fullPath) Then
        WScript.Echo "WARN=VEHICLE_INPUT_ROLES_NOT_FOUND path=" & fullPath
        Set LoadVehicleInputRoles = dict
        Exit Function
    End If
    Set ts = fso.OpenTextFile(fullPath, 1, False)
    first = True
    Do Until ts.AtEndOfStream
        line = Trim(ts.ReadLine)
        If line <> "" And Left(line, 1) <> "#" Then
            parts = Split(line, ",")
            If first Then
                first = False
            ElseIf UBound(parts) >= 1 Then
                noText = CStr(CLng(ToDbl(parts(0))))
                roleText = LCase(Trim(parts(1)))
                If noText <> "" Then dict(noText) = roleText
            End If
        End If
    Loop
    ts.Close
    Set LoadVehicleInputRoles = dict
End Function

Sub ConfigureEvaluationOutput(path)
    EnsureFolder path
    TrySetEvaluationAtt "EvalOutDir", path
    TrySetEvaluationAtt "DatabaseConnection", ""
    TrySetEvaluationAtt "ListAutoExportType", "FILE"
    WScript.Echo "EVAL_OUT_DIR=" & path
End Sub

Function LastControllerStatus()
    LastControllerStatus = "unknown"
    If lastActionJson <> "" And fso.FileExists(lastActionJson) Then
        LastControllerStatus = JsonFieldText(ReadAllText(lastActionJson), "controller_status")
    End If
End Function

Function LastDecisionWallSec()
    LastDecisionWallSec = ""
    If lastActionJson <> "" And fso.FileExists(lastActionJson) Then
        LastDecisionWallSec = JsonFieldNumber(ReadAllText(lastActionJson), "decision_wall_sec")
    End If
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

Sub TrySetEvaluationAtt(att, value)
    On Error Resume Next
    Vissim.Evaluation.AttValue(att) = value
    If Err.Number <> 0 Then
        WScript.Echo "WARN=FAILED_SET_EVALUATION_ATT att=" & att & " err=" & Err.Description
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

' Leftmost "-?\d+" match, found by a plain string scan instead of RegExp.
' New RegExp costs ~620 us per call and this ran once per vehicle per scan, so it
' alone was ~87% of a controller run. The scan below returns the identical value
' for every input: the leftmost regex match starts either at the first digit or,
' when that digit is immediately preceded by "-", at the "-". Verified equal on
' 20,025 hand + fuzz cases against the RegExp version.
Function FirstInt(value)
    Dim text, n, i, j, ch, startPos
    FirstInt = 0
    text = CStr(value)
    n = Len(text)
    startPos = 0
    i = 1
    Do While i <= n
        ch = Mid(text, i, 1)
        If ch >= "0" And ch <= "9" Then
            startPos = i
            If i > 1 Then
                If Mid(text, i - 1, 1) = "-" Then startPos = i - 1
            End If
            Exit Do
        End If
        i = i + 1
    Loop
    If startPos = 0 Then Exit Function
    j = i
    Do While j <= n
        ch = Mid(text, j, 1)
        If ch < "0" Or ch > "9" Then Exit Do
        j = j + 1
    Loop
    FirstInt = CLng(Mid(text, startPos, j - startPos))
End Function

Function InCsvInt(value, csvText)
    If Len(csvText) = 0 Then
        InCsvInt = False
    Else
        InCsvInt = (InStr(1, "," & csvText & ",", "," & CStr(value) & ",", vbTextCompare) > 0)
    End If
End Function

Function CsvNumberAt(csvText, idx, defaultValue)
    Dim parts
    parts = Split(csvText, ",")
    If idx >= 0 And idx <= UBound(parts) Then
        CsvNumberAt = ToDbl(parts(idx))
    Else
        CsvNumberAt = defaultValue
    End If
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

Function DerivedRunCsvPath(prefix)
    Dim parent, stem
    parent = fso.GetParentFolderName(stateOutPath)
    stem = fso.GetBaseName(stateOutPath)
    If LCase(Left(stem, 6)) = "state_" Then stem = Mid(stem, 7)
    DerivedRunCsvPath = fso.BuildPath(parent, CStr(prefix) & "_" & stem & ".csv")
End Function

Function PerfNow()
    If RW_PERF_ENABLED Then
        PerfNow = Timer
    Else
        PerfNow = 0
    End If
End Function

Sub PerfAdd(name, t0)
    Dim d
    If Not RW_PERF_ENABLED Then Exit Sub
    d = Timer - t0
    If d < 0 Then d = d + 86400.0
    If Not perfSum.Exists(name) Then
        perfSum.Add name, 0.0
        perfCnt.Add name, 0
    End If
    perfSum(name) = CDbl(perfSum(name)) + d
    perfCnt(name) = CLng(perfCnt(name)) + 1
End Sub

Sub PerfReport()
    Dim k
    If Not RW_PERF_ENABLED Then Exit Sub
    For Each k In perfSum.Keys
        WScript.Echo "PERF name=" & k & " sec=" & Num(CDbl(perfSum(k))) & " n=" & CStr(perfCnt(k))
    Next
End Sub

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

Function DefaultGeneratedConfigPath()
    DefaultGeneratedConfigPath = fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "..\evaluation\generated\real_world_modi_control_config.vbs")
End Function

Function DefaultVehicleInputRolesPath()
    DefaultVehicleInputRolesPath = fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "..\evaluation\real_world_modi_inventory\vehicle_input_roles.csv")
End Function

Sub LoadGeneratedConfig(path)
    Dim configPath, scriptText
    If path = "" Then
        configPath = DefaultGeneratedConfigPath()
    Else
        configPath = path
    End If
    If Not fso.FileExists(configPath) Then
        WScript.Echo "WARN=GENERATED_CONFIG_NOT_FOUND using_embedded_defaults path=" & configPath
        Exit Sub
    End If
    ' scripts\generate_real_world_control_mapping.py writes this config as UTF-8
    ' and it carries absolute paths, which are non-ASCII in this workspace.
    ' Reading it through the ANSI text reader turned RW_DETECTOR_MAPPING_PATH
    ' into mojibake that then poisoned every state JSON.
    scriptText = ReadAllTextUtf8(configPath)
    ExecuteGlobal scriptText
    generatedConfigLoaded = True
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
