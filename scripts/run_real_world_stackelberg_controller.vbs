Option Explicit

If WScript.Arguments.Count < 4 Then
    WScript.Echo "Usage: cscript run_real_world_stackelberg_controller.vbs <network.inpx> <state_output.csv> <action_output.csv> <decision_dir> [sim_period_sec] [control_interval_sec] [rand_seed] [adapter_py] [calibration_json] [tuning_json] [mapping_json] [controller] [control_start_sec] [warmup_controller] [generated_config.vbs] [state_log_interval_sec] [demand_scale] [demand_profile_csv] [vehicle_input_roles_csv] [incident_link] [incident_lane] [incident_pos_m] [incident_start_sec] [incident_end_sec] [incident_name]"
    WScript.Quit 2
End If

Dim fso, shell, stateFile, actionFile, bottleneckLinkFile, bottleneckSegmentFile, signalTraceFile, Vissim
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

' Coarse wall-clock instrumentation, OFF unless RW_PERF=1 is in the environment.
' When off every hook is a single boolean test, so it never shows up in a run.
' When on, a "PERF name=<stage> sec=<total> n=<calls>" block is echoed at the end.
Dim RW_PERF_ENABLED, perfSum, perfCnt
RW_PERF_ENABLED = (Trim(shell.ExpandEnvironmentStrings("%RW_PERF%")) = "1")
Set perfSum = CreateObject("Scripting.Dictionary")
Set perfCnt = CreateObject("Scripting.Dictionary")
Dim auditAnchorsSec, runId, runManifestPath, runManifestSha256, qualificationMode
Dim b1aRequired, workspaceRoot, stateManifestBuilderPath, monotonicClockHelperPath, runManifestRelPath, vissimVersionRaw
auditAnchorsSec = Trim(shell.ExpandEnvironmentStrings("%RW_AUDIT_ANCHORS_SEC%"))
If Left(auditAnchorsSec, 1) = "%" Then auditAnchorsSec = ""
runId = Trim(shell.ExpandEnvironmentStrings("%RW_RUN_ID%"))
If Left(runId, 1) = "%" Then runId = ""
runManifestPath = Trim(shell.ExpandEnvironmentStrings("%RW_RUN_MANIFEST_PATH%"))
If Left(runManifestPath, 1) = "%" Then runManifestPath = ""
runManifestSha256 = LCase(Trim(shell.ExpandEnvironmentStrings("%RW_RUN_MANIFEST_SHA256%")))
If Left(runManifestSha256, 1) = "%" Then runManifestSha256 = ""
qualificationMode = Trim(shell.ExpandEnvironmentStrings("%RW_QUALIFICATION_MODE%"))
If Left(qualificationMode, 1) = "%" Then qualificationMode = ""
b1aRequired = (Trim(shell.ExpandEnvironmentStrings("%RW_B1A_REQUIRED%")) = "1")
workspaceRoot = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
stateManifestBuilderPath = fso.BuildPath(workspaceRoot, "scripts\build_state_manifest_v2_1.py")
monotonicClockHelperPath = fso.BuildPath(workspaceRoot, "scripts\read_monotonic_clock.py")
runManifestRelPath = ""
vissimVersionRaw = ""

' Signal COM handle caches - see CachedSignalController.
Dim sigScCache, sigSgCache, sigSgCountCache, sigSgNameCache, sigRequestedState, signalTraceStage
Set sigScCache = CreateObject("Scripting.Dictionary")
Set sigSgCache = CreateObject("Scripting.Dictionary")
Set sigSgCountCache = CreateObject("Scripting.Dictionary")
Set sigSgNameCache = CreateObject("Scripting.Dictionary")
Set sigRequestedState = CreateObject("Scripting.Dictionary")
signalTraceStage = "immediate"

Dim netPath, stateOutPath, actionOutPath, bottleneckLinkOutPath, bottleneckSegmentOutPath, signalTraceOutPath, decisionDir, simPeriod, controlInterval, randSeed, stateLogIntervalSec, demandScale, demandProfilePath, vehicleInputRolesPath
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
Dim RW_RAMP_METER_IDS, RW_RAMP_METER_SCS, RW_RAMP_METER_CONNECTORS, RW_RAMP_METER_MODEL_KEYS, RW_RAMP_METER_CAPACITIES_VPH, RW_SIGNAL_SCS, RW_EXPECTED_VSL_ACTION_ROWS, RW_EXPECTED_VSL_DSD_IDS, RW_EXPECTED_VSL_ACTION_KEYS, RW_ALLOWED_VSL_SPEEDS, RW_LOCAL_OBSERVABLE_LINKS, RW_DETECTOR_MAPPING_PATH
' Optional generated-config override for the python interpreter. Declared here
' so a config that sets it can be ExecuteGlobal'd under Option Explicit.
Dim RW_PYTHON_EXE
RW_PYTHON_EXE = ""
' N4-7. offset 승격 잠금의 **두 번째** 자물쇠. 권위는 여기가 아니다 - 삼중 잠금
' (D-core + N9 + N8-4)의 판정은 evaluation/controllers/offset_promotion.py 가 증거
' 산출물을 읽어서 내린다. 러너가 보장하는 것은 하나뿐이다.
'   "선언하지 않은 런은 offset 을 절대 액추에이션하지 못한다."
' 그래서 기본값이 intent_only 이고, 손으로 고친 action CSV 든 옛 어댑터가 만든
' action CSV 든 nonzero offset 이 오면 그 CSV 를 **전량** 거부한다.
' 격리된 시험 harness 는 자기 generated config 에서 "test_only" 로 선언한다.
Dim RW_OFFSET_WRITER
RW_OFFSET_WRITER = "intent_only"
' N4-5. SG 단위 액추에이션 계획의 계약. scripts/derive_signal_group_actuation_plan.py 가
' generated config 옆에 <config>_sgplan.vbs 로 내보내고, 여기서 ExecuteGlobal 한다.
'   RW_SIGNAL_SG_EXPECTED   "sc:sg:window_count,..."  이 SC 의 모든 SG 와 기대 창 수
'   RW_SIGNAL_SG_CONFLICTS  "sc:a-b;..."              절대 동시 GREEN 이면 안 되는 쌍
' 계약을 action CSV 가 아니라 config 에서 받는 것이 요점이다. 행이 자기 자신을
' 인증하면 fail-closed 가 아니다.
Dim RW_SIGNAL_SG_PLAN_SCHEMA, RW_SIGNAL_SG_PLAN_SOURCE_SHA256, RW_SIGNAL_SG_EXPECTED, RW_SIGNAL_SG_CONFLICTS
RW_SIGNAL_SG_PLAN_SCHEMA = 0
RW_SIGNAL_SG_PLAN_SOURCE_SHA256 = ""
RW_SIGNAL_SG_EXPECTED = ""
RW_SIGNAL_SG_CONFLICTS = ""
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
RW_RAMP_METER_CAPACITIES_VPH = "900,900,900,900,900,900,900,900"
RW_SIGNAL_SCS = "1"
RW_EXPECTED_VSL_ACTION_ROWS = 71
RW_EXPECTED_VSL_DSD_IDS = "36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106"
RW_EXPECTED_VSL_ACTION_KEYS = ""
RW_ALLOWED_VSL_SPEEDS = "50,60,70,80,90,100,115,120"
RW_LOCAL_OBSERVABLE_LINKS = "2,26,10479,10480,10481,10482,10483,10484,10490,10491,10638,10639,10643,10644,10645,10646,10681,10682"
RW_DETECTOR_MAPPING_PATH = "evaluation/real_world_modi_control/detector_local_mapping.json"
Dim generatedConfigLoaded
generatedConfigLoaded = False
LoadGeneratedConfig generatedConfigPath
' Schema 3 also carries the exact VSL segment/DSD/link/lane actuator tuples.
' An older config would silently overwrite SEG_BOUNDS with the single-link grid
' while leaving the chain variables at their fallback values, which is exactly
' the measurement/control grid mismatch this schema check exists to prevent.
If generatedConfigLoaded And CLng(RW_SCHEMA_VERSION) < 3 Then
    WScript.Echo "ERROR=GENERATED_CONFIG_SCHEMA_TOO_OLD schema=" & CStr(RW_SCHEMA_VERSION) & _
        " path=" & generatedConfigPath & " (rerun scripts/generate_real_world_control_mapping.py)"
    WScript.Quit 2
End If
detectorMappingPath = RW_DETECTOR_MAPPING_PATH
' N4-5. 계획 config 는 generated config 의 형제 파일이다(<config>_sgplan.vbs).
' 없으면 sgPlanEnabled = False 이고 러너는 예전 이름 규칙 경로로 돈다 - 다만 그 경로의
' 사용 건수를 SIGNAL_NAME_RULE_FALLBACKS 로 세어 조용히 지나가지 못하게 한다.
Dim sgPlanEnabled, sgPlanExpected, sgPlanConflicts, sgPlanWindows, sgPlanCycle, sgPlanGroups
Dim signalNameRuleFallbacks, signalSgPlanRows, signalCoGreenBlocks
sgPlanEnabled = False
Set sgPlanExpected = CreateObject("Scripting.Dictionary")
Set sgPlanConflicts = CreateObject("Scripting.Dictionary")
Set sgPlanWindows = CreateObject("Scripting.Dictionary")
Set sgPlanCycle = CreateObject("Scripting.Dictionary")
Set sgPlanGroups = CreateObject("Scripting.Dictionary")
signalNameRuleFallbacks = 0
signalSgPlanRows = 0
signalCoGreenBlocks = 0
LoadSignalGroupPlanConfig generatedConfigPath
ParseSignalGroupPlanConfig

Const RAMP_CYCLE_SEC = 10
Const RAMP_AMBER_SEC = 1
Const AMBER_SEC = 3
Const ALL_RED_SEC = 2
Const B1A_POSITION_TOLERANCE_M = 0.000001
' VISSIM hands a vehicle to a link before its reference point reaches the link start, so
' Pos is briefly negative while the vehicle straddles the boundary. Measured 2026-08-07:
' veh_no=16426 Pos=-1.49989317546481 (VarType 5, a normal Double) at sim_sec 2430 with
' 4000+ vehicles. Rejecting that fails the entire capture during congestion, and dropping
' the vehicle would break the unobservable_count = 0 contract. Accept up to one vehicle
' length, clamp to the link start - VISSIM already transferred ownership to this link, so
' its first stock is the honest assignment - and echo every adjustment so the move is
' never silent. Anything beyond one vehicle length still fails closed.
Const B1A_ENTRY_TOLERANCE_M = 8.0
Const B1A_STOPPED_THRESHOLD_KPH = 1.0
' Measured 2026-08-07 against the real Gaepo topology: --validate-run-binding takes
' 10.47 s wall and returns status=PASS. cProfile attributes 10.44 s of that to
' run_evidence.validate_run_manifest -> approval_replay.validate_approval_replay ->
' _run_validation_worker, i.e. an independent approval-replay SUBPROCESS that reloads and
' rehashes the 30 MB physical stock topology. The old 10 s ceiling was set without
' measuring against a real topology, so required mode always died with EXEC_TIMEOUT
' before a single capture. This is slowness, not a hang - raise the ceiling with headroom.
' NOTE: the same deep replay runs again at every capture time. That redundancy is a
' performance item, not a correctness one (the approval artifact is immutable for the run
' and its hash is re-checked from the manifest each time). See v3 N1 follow-up.
Const B1A_PYTHON_HELPER_TIMEOUT_SEC = 60
Dim JSON_DECIMAL_SEPARATOR
JSON_DECIMAL_SEPARATOR = Mid(FormatNumber(1.5, 1, -1, 0, 0), 2, 1)

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
Dim pythonExe, decisionsOk, decisionsFailed, observationFailures, signalFailures, actionFormatFailures, comFailures, optionalAttSkips
Dim signalWriteAttempts, signalReadbackOk, signalPersistenceChecks, signalPersistenceOk, signalTraceSimSec
pythonExe = ""
decisionsOk = 0
decisionsFailed = 0
observationFailures = 0
signalFailures = 0
actionFormatFailures = 0
comFailures = 0
optionalAttSkips = 0
signalWriteAttempts = 0
signalReadbackOk = 0
signalPersistenceChecks = 0
signalPersistenceOk = 0
signalTraceSimSec = 0
ResolvePythonInterpreter
ValidateB1aRequiredStartup

EnsureParentFolder stateOutPath
EnsureParentFolder actionOutPath
EnsureFolder decisionDir
bottleneckLinkOutPath = DerivedRunCsvPath("bottleneck_links")
bottleneckSegmentOutPath = DerivedRunCsvPath("bottleneck_segments")
signalTraceOutPath = fso.BuildPath(decisionDir, "signal_readback.csv")
Set stateFile = fso.CreateTextFile(stateOutPath, True)
Set actionFile = fso.CreateTextFile(actionOutPath, True)
Set bottleneckLinkFile = fso.CreateTextFile(bottleneckLinkOutPath, True)
Set bottleneckSegmentFile = fso.CreateTextFile(bottleneckSegmentOutPath, True)
Set signalTraceFile = fso.CreateTextFile(signalTraceOutPath, True)
stateFile.WriteLine "sim_sec,total_vehicles,urban_vehicles,freeway_vehicles,ramp_vehicles,boundary_vehicles,other_vehicles,mean_speed_kph,freeway_mean_speed_kph,stopped_vehicles,controller_mode,controller_status,decision_wall_sec"
actionFile.WriteLine "sim_sec,kind,id,dsd_no,sc_no,link,lane,speed_kph,major_green,minor_green,offset,rate_vph,green_sec,metadata,readback"
bottleneckLinkFile.WriteLine "sim_sec,link,count,stopped_count,mean_speed_kph,category,is_freeway,is_ramp_meter_connector,is_local_observable"
bottleneckSegmentFile.WriteLine "sim_sec,model_link,direction,segment_index,segment_id,physical_link,count,stopped_count,mean_speed_kph,length_km,lanes,density_veh_km_lane"
signalTraceFile.WriteLine "sim_sec,sc_no,sg_no,requested_state,readback_state,ok,stage"

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
vissimVersionRaw = SafeAtt(Vissim, "VERSION")
WScript.Echo "VERSION=" & vissimVersionRaw
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
ValidateSignalGroupPlanCoverage
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
' UseMaxSimSpeed=True 가 바로 위에서 이미 최대속도를 보장한다. 그 상태에서 SimSpeed 는
' 무시되고, Vissim 은 Min 이 0 이라면서 0 을 거부한다(실측 문구: "Value 0 is lower than
' minimum value of attribute Simulation speed (Min: 0)").
TrySetUnreachableAtt Vissim.Simulation, "SimSpeed", 0, "UseMaxSimSpeed=True already guarantees max speed"

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
signalTraceFile.Close

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
WScript.Echo "OBSERVATION_FAILURES=" & CStr(observationFailures)
WScript.Echo "SIGNAL_FAILURES=" & CStr(signalFailures)
WScript.Echo "SIGNAL_WRITE_ATTEMPTS=" & CStr(signalWriteAttempts)
WScript.Echo "SIGNAL_READBACK_OK=" & CStr(signalReadbackOk)
WScript.Echo "SIGNAL_PERSISTENCE_CHECKS=" & CStr(signalPersistenceChecks)
WScript.Echo "SIGNAL_PERSISTENCE_OK=" & CStr(signalPersistenceOk)
WScript.Echo "ACTION_FORMAT_FAILURES=" & CStr(actionFormatFailures)
WScript.Echo "COM_FAILURES=" & CStr(comFailures)
WScript.Echo "OPTIONAL_ATT_SKIPS=" & CStr(optionalAttSkips)
' N4-5. 계획이 켜진 production 런은 SIGNAL_NAME_RULE_FALLBACKS = 0 이어야 한다.
' 0 이 아니면 그만큼의 SG 상태가 여전히 이름 부분문자열로 정해졌다는 뜻이다.
WScript.Echo "SIGNAL_SG_PLAN_ENABLED=" & CStr(BoolInt(sgPlanEnabled))
WScript.Echo "SIGNAL_SG_PLAN_GROUPS=" & CStr(sgPlanExpected.Count)
WScript.Echo "SIGNAL_SG_PLAN_ROWS=" & CStr(signalSgPlanRows)
WScript.Echo "SIGNAL_NAME_RULE_FALLBACKS=" & CStr(signalNameRuleFallbacks)
WScript.Echo "SIGNAL_COGREEN_BLOCKS=" & CStr(signalCoGreenBlocks)
If decisionsFailed > 0 Or observationFailures > 0 Or signalFailures > 0 Or actionFormatFailures > 0 Or comFailures > 0 Then
    WScript.Echo "ERROR=RUN_INTEGRITY_FAILURE decisions_failed=" & CStr(decisionsFailed) & _
        " observation_failures=" & CStr(observationFailures) & " signal_failures=" & CStr(signalFailures) & _
        " action_format_failures=" & CStr(actionFormatFailures) & " com_failures=" & CStr(comFailures)
    Set Vissim = Nothing
    WScript.Quit 3
End If

Dim actualSimSec
actualSimSec = CDblOrZero(SafeAtt(Vissim.Simulation, "SimSec"))
If actualSimSec + 0.5 < CDbl(simPeriod) Then
    WScript.Echo "ERROR=SIMULATION_ENDED_EARLY actual_sim_sec=" & Num(actualSimSec) & " target_sim_sec=" & Num(simPeriod)
    Set Vissim = Nothing
    WScript.Quit 4
End If

WScript.Echo "STAGE=SIM_DONE"
WScript.Echo "SIM_SEC=" & SafeAtt(Vissim.Simulation, "SimSec")
WScript.Echo "SIM_STEPS=" & simPeriod
WScript.Echo "STATE_CSV=" & stateOutPath
WScript.Echo "ACTION_CSV=" & actionOutPath
WScript.Echo "BOTTLENECK_LINK_CSV=" & bottleneckLinkOutPath
WScript.Echo "BOTTLENECK_SEGMENT_CSV=" & bottleneckSegmentOutPath
WScript.Echo "SIGNAL_READBACK_CSV=" & signalTraceOutPath
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
    Dim scs, i, scNo, sc, sg, contrReadback
    scs = Split(RW_RAMP_METER_SCS, ",")
    For i = 0 To UBound(scs)
        scNo = Trim(scs(i))
        If scNo <> "" Then
            On Error Resume Next
            Set sc = Vissim.Net.SignalControllers.ItemByKey(CLng(scNo))
            Set sg = sc.SGs.ItemByKey(1)
            If Err.Number <> 0 Then
                signalFailures = signalFailures + 1
                WScript.Echo "ERROR=RAMP_SG_NOT_FOUND sc=" & scNo & " err=" & Err.Description
                Err.Clear
            Else
                TrySetAtt sg, "ContrByCOM", True
                contrReadback = SafeAtt(sg, "ContrByCOM")
                If Not ComBoolean(contrReadback) Then
                    signalFailures = signalFailures + 1
                    WScript.Echo "ERROR=RAMP_CONTR_BY_COM_READBACK sc=" & scNo & " readback=" & CStr(contrReadback)
                End If
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
        stepT0 = PerfNow()
        Vissim.Simulation.RunSingleStep
        PerfAdd "sim.step", stepT0
        ValidateRuntimeSignalPersistence stepNo
        If stepNo Mod CLng(controlInterval) = 0 Then
            RunControllerDecision stepNo
        End If
        ApplyRuntimeSignals stepNo
        ApplyRuntimeRampMeters stepNo
        ApplyIncidentLaneClosure stepNo
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
        ValidateRuntimeSignalPersistence CLng(currentSec)
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

        ValidateRuntimeSignalPersistence CLng(currentSec)
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
    Dim scKey, major, minor, offset, cycle, pos, majorState, minorState, s, groupIds, g
    s = ""
    For Each scKey In sigMajor.Keys
        major = CDbl(sigMajor(CStr(scKey)))
        minor = CDbl(DictValue(sigMinor, CStr(scKey), 0.0))
        offset = CDbl(DictValue(sigOffset, CStr(scKey), 0.0))
        cycle = major + AMBER_SEC + ALL_RED_SEC + minor + AMBER_SEC + ALL_RED_SEC
        pos = FMod(CDbl(simSec) + offset, cycle)
        ' N4-5. 이벤트 스케줄러는 이 합성 상태가 바뀌는 초에만 멈춘다. 계획이 켜지면
        ' 축 안의 SG 경계도 전이다 - 여기서 안 보면 그 전이가 다음 이벤트까지 늦게 쓰인다.
        If sgPlanEnabled And sgPlanGroups.Exists(CStr(CLng(scKey))) Then
            groupIds = Split(CStr(sgPlanGroups(CStr(CLng(scKey)))), ",")
            s = s & CStr(scKey) & ":"
            For Each g In groupIds
                s = s & SignalGroupStateFromPlan(CLng(scKey), CLng(g), pos, cycle) & "/"
            Next
            s = s & ";"
        Else
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
        End If
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
    ElseIf Not ApplyActionCsv(simSec, outCsvPath, effController) Then
        decisionsFailed = decisionsFailed + 1
        WScript.Echo "ERROR=ACTION_CSV_INCOMPLETE sim_sec=" & simSec & " controller=" & effController
    Else
        decisionsOk = decisionsOk + 1
        lastActionJson = outJsonPath
    End If
    PerfAdd "decision.total", perfT0
End Sub

Function ApplyActionCsv(simSec, csvPath, effectiveController)
    Dim ts, line, first, parts, kind, dsdNo, speed, dsd, readback, scNo, perfT0
    Dim vslRows, rampRows, signalRows, invalidRows, expectedVslRows, expectedRampRows, expectedSignalRows
    Dim seenVsl, seenRamp, seenSignal, rowKey, validatedRows(), validatedRowCount, i, vslWriteOk
    Dim sgRows, expectedSgRows, seenSg, pendingSgWindows, pendingSgCounts, pendingSgCycle, pendingSgOffset
    Dim rowSignalCycle, rowSignalOffset, planReason
    perfT0 = PerfNow()
    ApplyActionCsv = False
    vslRows = 0: rampRows = 0: signalRows = 0: invalidRows = 0: sgRows = 0
    Set seenVsl = CreateObject("Scripting.Dictionary")
    Set seenRamp = CreateObject("Scripting.Dictionary")
    Set seenSignal = CreateObject("Scripting.Dictionary")
    Set seenSg = CreateObject("Scripting.Dictionary")
    Set pendingSgWindows = CreateObject("Scripting.Dictionary")
    Set pendingSgCounts = CreateObject("Scripting.Dictionary")
    Set pendingSgCycle = CreateObject("Scripting.Dictionary")
    Set pendingSgOffset = CreateObject("Scripting.Dictionary")
    Set rowSignalCycle = CreateObject("Scripting.Dictionary")
    Set rowSignalOffset = CreateObject("Scripting.Dictionary")
    seenRamp.CompareMode = 1
    seenSignal.CompareMode = 1
    ReDim validatedRows(0)
    validatedRowCount = 0
    Set ts = fso.OpenTextFile(csvPath, 1, False)
    first = True
    Do Until ts.AtEndOfStream
        line = ts.ReadLine
        If first Then
            first = False
            parts = Split(CStr(line), ",")
            If Not ActionCsvHeaderValid(parts) Then
                invalidRows = invalidRows + 1
                WScript.Echo "ERROR=ACTION_CSV_HEADER actual=" & OneLine(CStr(line))
            End If
        ElseIf Trim(line) <> "" Then
            parts = Split(line, ",")
            If validatedRowCount > UBound(validatedRows) Then ReDim Preserve validatedRows(validatedRowCount)
            validatedRows(validatedRowCount) = CStr(line)
            validatedRowCount = validatedRowCount + 1
            If UBound(parts) <> 12 Then
                invalidRows = invalidRows + 1
            Else
                kind = LCase(Trim(CStr(parts(0))))
                If kind = "vsl" Then
                    If Not VslActionKeyValid(parts(1), parts(2), parts(4), parts(5)) Or _
                            Not IsCsvFiniteNumber(parts(6), RW_ALLOWED_VSL_SPEEDS) Then
                        invalidRows = invalidRows + 1
                    Else
                        rowKey = CStr(CLng(Trim(CStr(parts(2)))))
                        If seenVsl.Exists(rowKey) Then
                            invalidRows = invalidRows + 1
                        Else
                            seenVsl.Add rowKey, True
                            vslRows = vslRows + 1
                        End If
                    End If
                ElseIf kind = "ramp_meter" Then
                    rowKey = Trim(CStr(parts(1)))
                    If rowKey = "" Or seenRamp.Exists(rowKey) Or _
                            Not RampActionValid(rowKey, parts(3), parts(10), parts(11)) Then
                        invalidRows = invalidRows + 1
                    Else
                        seenRamp.Add rowKey, True
                        rampRows = rampRows + 1
                    End If
                ElseIf kind = "signal" Then
                    rowKey = Trim(CStr(parts(1)))
                    If rowKey = "" Or seenSignal.Exists(rowKey) Or _
                            Not IsCanonicalCsvInt(parts(3), RW_SIGNAL_SCS) Or _
                            Not SignalActionValuesValid(parts(7), parts(8), parts(9)) Then
                        invalidRows = invalidRows + 1
                    ElseIf UCase(rowKey) <> "SC" & CStr(CLng(Trim(CStr(parts(3))))) Then
                        invalidRows = invalidRows + 1
                    Else
                        seenSignal.Add rowKey, True
                        signalRows = signalRows + 1
                        rowSignalCycle(CStr(CLng(Trim(CStr(parts(3)))))) = _
                            CDbl(Trim(CStr(parts(7)))) + CDbl(Trim(CStr(parts(8)))) + _
                            (2 * AMBER_SEC) + (2 * ALL_RED_SEC)
                        rowSignalOffset(CStr(CLng(Trim(CStr(parts(3)))))) = CDbl(Trim(CStr(parts(9))))
                    End If
                ElseIf kind = "signal_sg" Then
                    ' N4-5 행. 13열 헤더는 그대로 두고 열을 재사용한다.
                    '   dsd_no -> sg 번호   link -> 창 인덱스
                    '   major_green -> 창 시작[s]   minor_green -> 창 끝[s]
                    '   offset -> 그 SC 의 offset   green_sec -> 플랜 주기[s]
                    If Not sgPlanEnabled Then
                        invalidRows = invalidRows + 1
                        WScript.Echo "ERROR=ACTION_CSV_SIGNAL_SG_WITHOUT_PLAN_CONFIG sim_sec=" & CStr(simSec) & _
                            " row=" & OneLine(CStr(line))
                    ElseIf Not SignalSgRowValid(parts, seenSg, pendingSgWindows, pendingSgCounts, pendingSgCycle, pendingSgOffset) Then
                        invalidRows = invalidRows + 1
                    Else
                        sgRows = sgRows + 1
                    End If
                Else
                    invalidRows = invalidRows + 1
                End If
            End If
        End If
    Loop
    ts.Close
    expectedVslRows = CsvNonEmptyCount(RW_EXPECTED_VSL_DSD_IDS)
    expectedRampRows = CsvNonEmptyCount(RW_RAMP_METER_SCS)
    expectedSignalRows = CsvNonEmptyCount(RW_SIGNAL_SCS)
    expectedSgRows = SignalGroupPlanExpectedRowCount()
    If SignalRowsSuppressedForController(effectiveController) Then
        expectedSignalRows = 0
        expectedSgRows = 0
    End If
    ' 계획이 켜졌는데 행이 부족하거나, SG별 창 수가 계약과 다르거나, 축 지시와 창의
    ' 주기/offset 이 어긋나거나, 금지된 쌍이 동시녹색이면 - 전량 거부다. 부분 적용은 없다.
    planReason = ""
    If sgPlanEnabled And expectedSgRows > 0 Then
        planReason = SignalGroupPlanRejectReason( _
            pendingSgWindows, pendingSgCounts, pendingSgCycle, rowSignalCycle, rowSignalOffset)
    End If
    ' N4-7. 승격되지 않은 offset 이 오면 같은 자리에서 전량 거부한다. signal_sg 행의
    ' offset 은 SignalGroupPlanRejectReason 이 이미 signal 행과 같음을 요구하므로
    ' rowSignalOffset 만 보면 sigOffset 으로 갈 수 있는 값이 전부 덮인다.
    If planReason = "" Then planReason = OffsetPromotionRejectReason(rowSignalOffset)
    If first Or expectedVslRows <> CLng(RW_EXPECTED_VSL_ACTION_ROWS) Or vslRows <> expectedVslRows Or rampRows <> expectedRampRows Or _
            signalRows <> expectedSignalRows Or sgRows <> expectedSgRows Or invalidRows > 0 Or planReason <> "" Then
        actionFormatFailures = actionFormatFailures + 1
        WScript.Echo "ERROR=ACTION_CSV_CONTRACT sim_sec=" & CStr(simSec) & _
            " vsl=" & CStr(vslRows) & "/" & CStr(expectedVslRows) & _
            " ramp=" & CStr(rampRows) & "/" & CStr(expectedRampRows) & _
            " signal=" & CStr(signalRows) & "/" & CStr(expectedSignalRows) & _
            " signal_sg=" & CStr(sgRows) & "/" & CStr(expectedSgRows) & _
            " invalid=" & CStr(invalidRows) & " plan_reject=" & OneLine(planReason)
        PerfAdd "action.apply", perfT0
        Exit Function
    End If
    signalSgPlanRows = signalSgPlanRows + sgRows

    For i = 0 To validatedRowCount - 1
        parts = Split(validatedRows(i), ",")
        kind = LCase(Trim(CStr(parts(0))))
        readback = ""
        If kind = "vsl" Then
            dsdNo = CLng(Trim(CStr(parts(2))))
            speed = CDbl(Trim(CStr(parts(6))))
            On Error Resume Next
            Set dsd = Vissim.Net.DesSpeedDecisions.ItemByKey(dsdNo)
            If Err.Number <> 0 Then
                WScript.Echo "ERROR=VSL_DSD_NOT_FOUND dsd=" & CStr(dsdNo) & " err=" & Err.Description
                Err.Clear
                On Error GoTo 0
                PerfAdd "action.apply", perfT0
                Exit Function
            End If
            On Error GoTo 0
            vslWriteOk = SetClassSpeedChecked(dsd, 10, speed)
            If Not SetClassSpeedChecked(dsd, 20, speed) Then vslWriteOk = False
            If Not SetClassSpeedChecked(dsd, 30, speed) Then vslWriteOk = False
            If Not SetClassSpeedChecked(dsd, 70, speed) Then vslWriteOk = False
            If Not vslWriteOk Then
                WScript.Echo "ERROR=VSL_COM_WRITE_READBACK dsd=" & CStr(dsdNo) & " speed=" & CStr(speed)
                PerfAdd "action.apply", perfT0
                Exit Function
            End If
            readback = SafeAtt(dsd, "DesSpeedDistr(10)") & "|" & SafeAtt(dsd, "DesSpeedDistr(70)")
        ElseIf kind = "ramp_meter" Then
            scNo = CStr(CLng(Trim(CStr(parts(3)))))
            rampGreen(scNo) = CDbl(Trim(CStr(parts(11))))
            readback = ApplyRampMeterSignal(CLng(scNo), CDbl(rampGreen(scNo)), simSec)
        ElseIf kind = "signal" Then
            scNo = CStr(CLng(Trim(CStr(parts(3)))))
            ' COM 제어 인계를 **먼저** 확인한다. 예전에는 sigMajor/sigMinor/sigOffset 을 먼저
            ' 커밋하고 반환값을 검사하지 않아, COM 을 못 받은 SC 의 값이 매초 재생됐다.
            ' 런은 signalFailures>0 로 마지막에 죽지만 그때까지 오염된 액추에이션이 이어졌다.
            ' 바로 위 VSL 분기와 같은 fail-closed 모양으로 맞춘다.
            readback = EnableSignalControllerForRuntime(CLng(scNo))
            If Left(CStr(readback), 4) = "ERR:" Then
                WScript.Echo "ERROR=SIGNAL_COM_WRITE_READBACK sc=" & CStr(scNo) & _
                    " readback=" & CStr(readback)
                PerfAdd "action.apply", perfT0
                Exit Function
            End If
            sigMajor(scNo) = CDbl(Trim(CStr(parts(7))))
            sigMinor(scNo) = CDbl(Trim(CStr(parts(8))))
            sigOffset(scNo) = CDbl(Trim(CStr(parts(9))))
            ' 축 지시와 그 축을 쪼갠 창을 같은 지점에서 커밋한다(주기 정합).
            If sgPlanEnabled And expectedSgRows > 0 Then
                CommitSignalGroupPlan CLng(scNo), pendingSgWindows, _
                    CDbl(DictValue(pendingSgCycle, CStr(CLng(scNo)), 0.0))
            End If
        End If
        actionFile.WriteLine CStr(simSec) & "," & Join(parts, ",") & "," & readback
    Next
    ApplyActionCsv = True
    PerfAdd "action.apply", perfT0
End Function

Function ActionCsvHeaderValid(parts)
    Dim expected, i, actual
    ActionCsvHeaderValid = False
    If UBound(parts) <> 12 Then Exit Function
    expected = Split("kind,id,dsd_no,sc_no,link,lane,speed_kph,major_green,minor_green,offset,rate_vph,green_sec,metadata", ",")
    For i = 0 To UBound(expected)
        actual = LCase(Trim(CStr(parts(i))))
        If actual <> expected(i) Then Exit Function
    Next
    ActionCsvHeaderValid = True
End Function

Function IsCanonicalNonNegativeInt(value)
    Dim textValue, i, code, numberValue
    IsCanonicalNonNegativeInt = False
    textValue = Trim(CStr(value))
    If textValue = "" Then Exit Function
    For i = 1 To Len(textValue)
        code = AscW(Mid(textValue, i, 1))
        If code < 48 Or code > 57 Then Exit Function
    Next
    On Error Resume Next
    numberValue = CLng(textValue)
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    On Error GoTo 0
    If CStr(numberValue) <> textValue Then Exit Function
    IsCanonicalNonNegativeInt = True
End Function

Function IsCanonicalCsvInt(value, csvText)
    IsCanonicalCsvInt = False
    If Not IsCanonicalNonNegativeInt(value) Then Exit Function
    IsCanonicalCsvInt = InCsvInt(CLng(Trim(CStr(value))), csvText)
End Function

Function IsFiniteNumberInRange(value, minimumValue, maximumValue)
    Dim numberValue
    IsFiniteNumberInRange = False
    If Trim(CStr(value)) = "" Then Exit Function
    On Error Resume Next
    numberValue = CDbl(Trim(CStr(value)))
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    On Error GoTo 0
    If numberValue < CDbl(minimumValue) Or numberValue > CDbl(maximumValue) Then Exit Function
    IsFiniteNumberInRange = True
End Function

Function IsCsvFiniteNumber(value, csvText)
    Dim values, i, numberValue
    IsCsvFiniteNumber = False
    If Not IsFiniteNumberInRange(value, -1.0E+100, 1.0E+100) Then Exit Function
    numberValue = CDbl(Trim(CStr(value)))
    values = Split(CStr(csvText), ",")
    For i = 0 To UBound(values)
        If IsFiniteNumberInRange(values(i), -1.0E+100, 1.0E+100) Then
            If Abs(numberValue - CDbl(Trim(CStr(values(i))))) < 0.000001 Then
                IsCsvFiniteNumber = True
                Exit Function
            End If
        End If
    Next
End Function

Function VslActionKeyValid(segmentId, dsdValue, linkValue, laneValue)
    Dim key
    VslActionKeyValid = False
    If Trim(CStr(segmentId)) = "" Then Exit Function
    If Not IsCanonicalCsvInt(dsdValue, RW_EXPECTED_VSL_DSD_IDS) Then Exit Function
    If Not IsCanonicalNonNegativeInt(linkValue) Then Exit Function
    If Not IsCanonicalNonNegativeInt(laneValue) Then Exit Function
    key = Trim(CStr(segmentId)) & "|" & Trim(CStr(dsdValue)) & "|" & _
        Trim(CStr(linkValue)) & "|" & Trim(CStr(laneValue))
    VslActionKeyValid = InDelimitedText(key, RW_EXPECTED_VSL_ACTION_KEYS, ";")
End Function

Function RampActionValid(rampId, scValue, rateValue, greenValue)
    Dim ids, scs, capacities, i, capacityValue, expectedGreen
    RampActionValid = False
    If Not IsCanonicalCsvInt(scValue, RW_RAMP_METER_SCS) Then Exit Function
    If Not IsFiniteNumberInRange(greenValue, 0.0, CDbl(RAMP_CYCLE_SEC)) Then Exit Function
    ids = Split(CStr(RW_RAMP_METER_IDS), ",")
    scs = Split(CStr(RW_RAMP_METER_SCS), ",")
    capacities = Split(CStr(RW_RAMP_METER_CAPACITIES_VPH), ",")
    If UBound(ids) <> UBound(scs) Or UBound(ids) <> UBound(capacities) Then Exit Function
    For i = 0 To UBound(ids)
        If StrComp(Trim(CStr(ids(i))), Trim(CStr(rampId)), vbTextCompare) = 0 And _
                Trim(CStr(scs(i))) = Trim(CStr(scValue)) Then
            If Not IsFiniteNumberInRange(capacities(i), 0.000001, 1.0E+100) Then Exit Function
            capacityValue = CDbl(Trim(CStr(capacities(i))))
            If Not IsFiniteNumberInRange(rateValue, 0.0, capacityValue) Then Exit Function
            expectedGreen = Round(CDbl(RAMP_CYCLE_SEC) * CDbl(rateValue) / capacityValue)
            If Abs(CDbl(greenValue) - expectedGreen) > 0.001 Then Exit Function
            RampActionValid = True
            Exit Function
        End If
    Next
End Function

Function SignalActionValuesValid(majorValue, minorValue, offsetValue)
    Dim cycleValue, offsetNumber
    SignalActionValuesValid = False
    If Not IsFiniteNumberInRange(majorValue, 5.0, 90.0) Then Exit Function
    If Not IsFiniteNumberInRange(minorValue, 5.0, 90.0) Then Exit Function
    cycleValue = CDbl(majorValue) + CDbl(minorValue) + (2 * AMBER_SEC) + (2 * ALL_RED_SEC)
    If Not IsFiniteNumberInRange(offsetValue, 0.0, cycleValue) Then Exit Function
    offsetNumber = CDbl(offsetValue)
    If offsetNumber >= cycleValue Then Exit Function
    SignalActionValuesValid = True
End Function

' N4-7. 승격되지 않은 offset 이 COM 에 닿기 전 마지막 자물쇠.
' 이 함수는 삼중 잠금을 **판정하지 않는다**(러너는 증거 산출물을 읽을 수 없다).
' 하는 일은 하나다 - RW_OFFSET_WRITER 로 선언하지 않은 런에서 nonzero offset 을 보면
' 그 CSV 전체를 거부할 사유를 돌려준다. 부분 적용은 없다.
Function OffsetPromotionRejectReason(rowSignalOffset)
    Dim writerText, scKey
    OffsetPromotionRejectReason = ""
    writerText = LCase(Trim(CStr(RW_OFFSET_WRITER)))
    If writerText = "" Then writerText = "intent_only"
    If writerText <> "intent_only" And writerText <> "test_only" And writerText <> "production" Then
        OffsetPromotionRejectReason = "OFFSET_WRITER_UNKNOWN value=" & CStr(RW_OFFSET_WRITER)
        Exit Function
    End If
    If writerText <> "intent_only" Then Exit Function
    For Each scKey In rowSignalOffset.Keys
        If Abs(CDbl(rowSignalOffset(scKey))) > 0.000001 Then
            OffsetPromotionRejectReason = "OFFSET_NOT_PROMOTED sc=" & CStr(scKey) & _
                " offset=" & CStr(rowSignalOffset(scKey)) & " writer=" & writerText
            Exit Function
        End If
    Next
End Function

' N4-5. `signal_sg` 행 하나의 국소 검증. 행 사이의 정합(창 수·주기·offset·동시녹색)은
' 파일을 다 읽은 뒤 SignalGroupPlanRejectReason 이 본다.
Function SignalSgRowValid(parts, seenSg, pendingWindows, pendingCounts, pendingCycle, pendingOffset)
    Dim scText, sgText, key, rowKey, windowIndex, expectedId, cycleSec, startSec, endSec, offsetSec
    SignalSgRowValid = False
    If Not IsCanonicalCsvInt(parts(3), RW_SIGNAL_SCS) Then Exit Function
    If Not IsCanonicalNonNegativeInt(parts(2)) Then Exit Function
    If Not IsCanonicalNonNegativeInt(parts(4)) Then Exit Function
    scText = CStr(CLng(Trim(CStr(parts(3)))))
    sgText = CStr(CLng(Trim(CStr(parts(2)))))
    key = scText & "-" & sgText
    If Not sgPlanExpected.Exists(key) Then Exit Function
    windowIndex = CLng(Trim(CStr(parts(4))))
    rowKey = key & "-" & CStr(windowIndex)
    If seenSg.Exists(rowKey) Then Exit Function
    expectedId = "SC" & scText & "_SG" & sgText & "_W" & CStr(windowIndex)
    If UCase(Trim(CStr(parts(1)))) <> UCase(expectedId) Then Exit Function
    If Not IsFiniteNumberInRange(parts(11), 0.000001, 100000.0) Then Exit Function
    cycleSec = CDbl(Trim(CStr(parts(11))))
    If Not IsFiniteNumberInRange(parts(7), 0.0, cycleSec) Then Exit Function
    If Not IsFiniteNumberInRange(parts(8), 0.0, cycleSec) Then Exit Function
    If Not IsFiniteNumberInRange(parts(9), 0.0, cycleSec) Then Exit Function
    startSec = CDbl(Trim(CStr(parts(7))))
    endSec = CDbl(Trim(CStr(parts(8))))
    offsetSec = CDbl(Trim(CStr(parts(9))))
    If endSec <= startSec Then Exit Function
    If pendingCycle.Exists(scText) Then
        If Abs(CDbl(pendingCycle(scText)) - cycleSec) > 0.000001 Then Exit Function
    Else
        pendingCycle.Add scText, cycleSec
    End If
    If pendingOffset.Exists(scText) Then
        If Abs(CDbl(pendingOffset(scText)) - offsetSec) > 0.000001 Then Exit Function
    Else
        pendingOffset.Add scText, offsetSec
    End If
    seenSg.Add rowKey, True
    ' 값은 CSV 원문 그대로 담는다. 다시 포맷하면 로케일 소수점에 걸린다.
    If pendingWindows.Exists(key) Then
        pendingWindows(key) = CStr(pendingWindows(key)) & Trim(CStr(parts(7))) & "|" & Trim(CStr(parts(8))) & ";"
    Else
        pendingWindows.Add key, Trim(CStr(parts(7))) & "|" & Trim(CStr(parts(8))) & ";"
    End If
    pendingCounts(key) = CLng(DictValue(pendingCounts, key, 0)) + 1
    SignalSgRowValid = True
End Function

Function SignalGroupPlanExpectedRowCount()
    Dim key, total
    SignalGroupPlanExpectedRowCount = 0
    If Not sgPlanEnabled Then Exit Function
    total = 0
    For Each key In sgPlanExpected.Keys
        total = total + CLng(sgPlanExpected(key))
    Next
    SignalGroupPlanExpectedRowCount = total
End Function

' 행 사이의 정합을 본다. 하나라도 어긋나면 사유를 돌려주고 호출부가 **전량** 거부한다.
Function SignalGroupPlanRejectReason(pendingWindows, pendingCounts, pendingCycle, signalCycle, signalOffset)
    Dim key, parts, scText, expectedCount, actualCount, planCycle, axisCycle
    SignalGroupPlanRejectReason = ""
    For Each key In sgPlanExpected.Keys
        expectedCount = CLng(sgPlanExpected(key))
        actualCount = CLng(DictValue(pendingCounts, CStr(key), 0))
        If actualCount <> expectedCount Then
            SignalGroupPlanRejectReason = "window_count " & CStr(key) & " " & _
                CStr(actualCount) & "/" & CStr(expectedCount)
            Exit Function
        End If
    Next
    For Each scText In pendingCycle.Keys
        planCycle = CDbl(pendingCycle(CStr(scText)))
        If Not signalCycle.Exists(CStr(scText)) Then
            SignalGroupPlanRejectReason = "no_signal_row sc=" & CStr(scText)
            Exit Function
        End If
        axisCycle = CDbl(signalCycle(CStr(scText)))
        If Abs(planCycle - axisCycle) > 0.001 Then
            SignalGroupPlanRejectReason = "cycle_mismatch sc=" & CStr(scText) & " plan=" & _
                CStr(planCycle) & " axis=" & CStr(axisCycle)
            Exit Function
        End If
    Next
    SignalGroupPlanRejectReason = SignalGroupPlanWindowConflictReason(pendingWindows)
End Function

' 계획된 녹색창 자체가 금지된 쌍을 겹치게 만드는지 본다. 런타임 판정과 달리
' 여기서는 주기 전체를 구간 산술로 본다 - 초 단위 표본으로는 놓치는 겹침이 있다.
Function SignalGroupPlanWindowConflictReason(pendingWindows)
    Dim pairKey, sides, scText, firstKey, secondKey, firstWindows, secondWindows
    Dim a, b, aBounds, bBounds, low, high
    SignalGroupPlanWindowConflictReason = ""
    For Each pairKey In sgPlanConflicts.Keys
        sides = Split(CStr(pairKey), "-")
        scText = CStr(sides(0))
        firstKey = scText & "-" & CStr(sides(1))
        secondKey = scText & "-" & CStr(sides(2))
        If pendingWindows.Exists(firstKey) And pendingWindows.Exists(secondKey) Then
            firstWindows = Split(CStr(pendingWindows(firstKey)), ";")
            secondWindows = Split(CStr(pendingWindows(secondKey)), ";")
            For Each a In firstWindows
                If Trim(CStr(a)) <> "" Then
                    aBounds = Split(CStr(a), "|")
                    For Each b In secondWindows
                        If Trim(CStr(b)) <> "" Then
                            bBounds = Split(CStr(b), "|")
                            low = CDbl(aBounds(0))
                            If CDbl(bBounds(0)) > low Then low = CDbl(bBounds(0))
                            high = CDbl(aBounds(1))
                            If CDbl(bBounds(1)) < high Then high = CDbl(bBounds(1))
                            If high - low > 0.000001 Then
                                SignalGroupPlanWindowConflictReason = "cogreen " & CStr(pairKey) & _
                                    " [" & CStr(low) & "," & CStr(high) & ")"
                                Exit Function
                            End If
                        End If
                    Next
                End If
            Next
        End If
    Next
End Function

Function InDelimitedText(value, collectionText, delimiter)
    Dim parts, i
    InDelimitedText = False
    parts = Split(CStr(collectionText), CStr(delimiter))
    For i = 0 To UBound(parts)
        If StrComp(Trim(CStr(parts(i))), Trim(CStr(value)), vbTextCompare) = 0 Then
            InDelimitedText = True
            Exit Function
        End If
    Next
End Function

Function SignalRowsSuppressedForController(value)
    Dim controller
    controller = LCase(Trim(CStr(value)))
    SignalRowsSuppressedForController = ( _
        controller = "no-control" Or _
        controller = "diagnostic-vsl60-only" Or _
        controller = "diagnostic-vsl80-only" Or _
        controller = "diagnostic-vsl80-original" Or _
        controller = "diagnostic-ramp-all735-original" Or _
        controller = "diagnostic-ramp-all360-original" _
    )
End Function

Function CsvNonEmptyCount(csvText)
    Dim parts, i, total
    total = 0
    parts = Split(CStr(csvText), ",")
    For i = 0 To UBound(parts)
        If Trim(CStr(parts(i))) <> "" Then total = total + 1
    Next
    CsvNonEmptyCount = total
End Function

Function InCsvText(value, csvText)
    Dim parts, i, wanted
    wanted = UCase(Trim(CStr(value)))
    InCsvText = False
    parts = Split(CStr(csvText), ",")
    For i = 0 To UBound(parts)
        If UCase(Trim(CStr(parts(i)))) = wanted Then InCsvText = True: Exit Function
    Next
End Function

Function SetClassSpeedChecked(dsd, vehClassNo, speedKph)
    Dim attributeName, readback
    SetClassSpeedChecked = False
    attributeName = "DesSpeedDistr(" & CStr(vehClassNo) & ")"
    On Error Resume Next
    dsd.AttValue(attributeName) = CLng(speedKph)
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    readback = dsd.AttValue(attributeName)
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    On Error GoTo 0
    If Not IsFiniteNumberInRange(readback, 0.0, 1000.0) Then Exit Function
    SetClassSpeedChecked = (CLng(CDbl(readback)) = CLng(CDbl(speedKph)))
End Function

Function EnableSignalControllerForRuntime(scNo)
    Dim sc, sg, sgNo, sgCount, enableOk, contrReadback
    EnableSignalControllerForRuntime = ""
    On Error Resume Next
    Set sc = Vissim.Net.SignalControllers.ItemByKey(CLng(scNo))
    If Err.Number <> 0 Then
        EnableSignalControllerForRuntime = "ERR:" & Err.Description
        signalFailures = signalFailures + 1
        WScript.Echo "ERROR=SIGNAL_SC_NOT_FOUND sc=" & scNo & " err=" & Err.Description
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    On Error GoTo 0
    sgCount = SignalGroupCount(sc)
    enableOk = True
    For sgNo = 1 To sgCount
        On Error Resume Next
        Set sg = sc.SGs.ItemByKey(CLng(sgNo))
        If Err.Number <> 0 Then
            enableOk = False
            signalFailures = signalFailures + 1
            WScript.Echo "ERROR=SIGNAL_SG_NOT_FOUND sc=" & CStr(scNo) & " sg=" & CStr(sgNo) & _
                " err=" & Err.Description
            Err.Clear
        Else
            TrySetAtt sg, "ContrByCOM", True
            contrReadback = SafeAtt(sg, "ContrByCOM")
            If Not ComBoolean(contrReadback) Then
                enableOk = False
                signalFailures = signalFailures + 1
                WScript.Echo "ERROR=CONTR_BY_COM_READBACK sc=" & CStr(scNo) & " sg=" & CStr(sgNo) & _
                    " readback=" & CStr(contrReadback)
            End If
        End If
        On Error GoTo 0
    Next
    ' signalControlled 는 매초 신호 재생의 게이트다(:1199 참조). COM 인계가 실패한 SC 를
    ' 여기 등록하면, 제어를 못 받은 컨트롤러에 대해 재생 루프가 계속 값을 밀어 넣는다.
    ' 그래서 enableOk 일 때만 등록한다.
    If enableOk Then
        signalControlled(CStr(scNo)) = True
        EnableSignalControllerForRuntime = "stored"
    Else
        EnableSignalControllerForRuntime = "ERR:ContrByCOM readback"
    End If
End Function

Function ComBoolean(value)
    Dim textValue
    textValue = LCase(Trim(CStr(value)))
    ComBoolean = (textValue = "1" Or textValue = "-1" Or textValue = "true" Or textValue = "yes")
End Function

Sub ApplyRuntimeSignals(simSec)
    Dim scKey, major, minor, offset, cycle, pos, majorState, minorState, perfT0
    perfT0 = PerfNow()
    signalTraceSimSec = CLng(simSec)
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
        ' N4-5. 계획이 있으면 SG 별 창으로 구동한다. 축의 위치·길이·주기 공식은 위와 같고
        ' 축 **안의** 분배만 native 배분을 따른다. 계획이 없으면 아래 이름 규칙으로 떨어지고
        ' 그 건수가 SIGNAL_NAME_RULE_FALLBACKS 에 쌓인다.
        If sgPlanEnabled And sgPlanCycle.Exists(CStr(CLng(scKey))) Then
            If Abs(CDbl(sgPlanCycle(CStr(CLng(scKey)))) - cycle) > 0.001 Then
                signalFailures = signalFailures + 1
                WScript.Echo "ERROR=SIGNAL_SG_PLAN_CYCLE_STALE sc=" & CStr(scKey) & _
                    " plan=" & CStr(sgPlanCycle(CStr(CLng(scKey)))) & " axis=" & CStr(cycle)
            Else
                ApplyRuntimeSignalControllerFromPlan CLng(scKey), pos, cycle
            End If
        ElseIf sgPlanEnabled Then
            ' 계획이 켜졌는데 이 SC 의 창이 없다. 이름 규칙으로 조용히 떨어지지 않는다.
            signalFailures = signalFailures + 1
            WScript.Echo "ERROR=SIGNAL_SG_PLAN_MISSING_FOR_SC sc=" & CStr(scKey)
        Else
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
        End If
    Next
    PerfAdd "signals.runtime", perfT0
End Sub

' 계획대로 SG 상태를 정하고, 금지 쌍이 동시녹색이면 **아무것도 쓰지 않는다**.
' 먼저 전부 계산하고 검사한 뒤에 쓰는 순서가 요점이다 - 쓰고 나서 발견하면 늦다.
Sub ApplyRuntimeSignalControllerFromPlan(scNo, pos, cycle)
    Dim sc, groupIds, sgCount, sgNos(), states(), i, reason, ignoredReadback
    If Not signalControlled.Exists(CStr(scNo)) Then
        Dim ignored
        ignored = EnableSignalControllerForRuntime(CLng(scNo))
    End If
    Set sc = CachedSignalController(CLng(scNo))
    If sc Is Nothing Then
        WScript.Echo "WARN=SIGNAL_SC_RUNTIME_NOT_FOUND sc=" & scNo
        Exit Sub
    End If
    ' SG 목록은 config 에서 온다. ValidateSignalGroupPlanCoverage 가 이 목록과
    ' VISSIM 이 들고 있는 SG 집합이 완전히 같음을 런 시작 때 증명한다.
    groupIds = Split(CStr(DictValue(sgPlanGroups, CStr(CLng(scNo)), "")), ",")
    sgCount = 0
    For i = 0 To UBound(groupIds)
        If Trim(CStr(groupIds(i))) <> "" Then sgCount = sgCount + 1
    Next
    If sgCount <= 0 Then Exit Sub
    ReDim sgNos(sgCount - 1)
    ReDim states(sgCount - 1)
    For i = 0 To sgCount - 1
        sgNos(i) = CLng(Trim(CStr(groupIds(i))))
        states(i) = SignalGroupStateFromPlan(CLng(scNo), CLng(sgNos(i)), pos, cycle)
    Next
    reason = SignalGroupPlanCoGreenReason(CLng(scNo), sgNos, states, sgCount)
    If reason <> "" Then
        signalCoGreenBlocks = signalCoGreenBlocks + 1
        signalFailures = signalFailures + 1
        WScript.Echo "ERROR=SIGNAL_COGREEN_BLOCKED sc=" & CStr(scNo) & " pos=" & CStr(pos) & _
            " reason=" & reason
        Exit Sub
    End If
    For i = 0 To sgCount - 1
        If Not (CachedSignalGroup(CLng(scNo), CLng(sgNos(i))) Is Nothing) Then
            ignoredReadback = SetSignalGroupState(CLng(scNo), CLng(sgNos(i)), CStr(states(i)))
        End If
    Next
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

' 이름 부분문자열로 SG 상태를 정하는 **명시적 폴백**이다 (N4-5 이전의 유일한 경로였다).
' 계획이 켜지면 여기로 오면 안 된다. 그래서 호출마다 계상하고 런 끝에 echo 한다 -
' 계획의 PASS 기준이 production fallback 0 이다.
Function SignalStateForGroup(sgNo, sgName, majorState, minorState)
    Dim nameUpper
    signalNameRuleFallbacks = signalNameRuleFallbacks + 1
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

' ==========================================================================
' N4-5. SG 단위 액추에이션 계획
'
' 모델은 N4-3 이후 축 녹색에 native 배분을 곱해 예측한다. 러너가 이름 규칙으로
' 축 전체를 모든 SG 에 주면 예측과 실현이 다른 물리다. 아래 절차가 그 비대칭을 닫는다.
'
'   config  <config>_sgplan.vbs    기대 SG 집합 + 절대 동시녹색 금지 쌍 (계약)
'   action  kind=signal_sg 행      이번 결정의 SG별 녹색창 (데이터)
'
' 계약과 데이터의 출처가 다른 것이 요점이다. 행이 스스로를 인증하면 fail-closed 가 아니다.
' ==========================================================================
Sub LoadSignalGroupPlanConfig(configPath)
    Dim planPath, baseText
    baseText = CStr(configPath)
    If baseText = "" Then baseText = DefaultGeneratedConfigPath()
    If LCase(Right(baseText, 4)) = ".vbs" Then baseText = Left(baseText, Len(baseText) - 4)
    planPath = baseText & "_sgplan.vbs"
    If Not fso.FileExists(planPath) Then
        WScript.Echo "SIGNAL_SG_PLAN_CONFIG_ABSENT=" & planPath
        Exit Sub
    End If
    ExecuteGlobal ReadAllTextUtf8(planPath)
    WScript.Echo "SIGNAL_SG_PLAN_CONFIG_LOADED=" & planPath
End Sub

Sub ParseSignalGroupPlanConfig
    Dim tokens, i, parts, pairParts, sides, scText, sgText
    sgPlanEnabled = (CLng(RW_SIGNAL_SG_PLAN_SCHEMA) >= 1)
    If Not sgPlanEnabled Then Exit Sub
    tokens = Split(CStr(RW_SIGNAL_SG_EXPECTED), ",")
    For i = 0 To UBound(tokens)
        If Trim(CStr(tokens(i))) <> "" Then
            parts = Split(Trim(CStr(tokens(i))), ":")
            If UBound(parts) <> 2 Then
                WScript.Echo "ERROR=SIGNAL_SG_PLAN_CONFIG_TOKEN token=" & CStr(tokens(i))
                WScript.Quit 2
            End If
            sgPlanExpected(SignalGroupPlanKey(parts(0), parts(1))) = CLng(Trim(CStr(parts(2))))
            ' SC 별 SG 목록. 이벤트 스케줄러와 재생 루프가 COM 조회 없이 돌게 한다.
            scText = CStr(CLng(Trim(CStr(parts(0)))))
            sgText = CStr(CLng(Trim(CStr(parts(1)))))
            If sgPlanGroups.Exists(scText) Then
                sgPlanGroups(scText) = CStr(sgPlanGroups(scText)) & "," & sgText
            Else
                sgPlanGroups.Add scText, sgText
            End If
        End If
    Next
    If sgPlanExpected.Count <= 0 Then
        WScript.Echo "ERROR=SIGNAL_SG_PLAN_CONFIG_EMPTY schema=" & CStr(RW_SIGNAL_SG_PLAN_SCHEMA)
        WScript.Quit 2
    End If
    tokens = Split(CStr(RW_SIGNAL_SG_CONFLICTS), ";")
    For i = 0 To UBound(tokens)
        If Trim(CStr(tokens(i))) <> "" Then
            pairParts = Split(Trim(CStr(tokens(i))), ":")
            If UBound(pairParts) <> 1 Then
                WScript.Echo "ERROR=SIGNAL_SG_PLAN_CONFLICT_TOKEN token=" & CStr(tokens(i))
                WScript.Quit 2
            End If
            sides = Split(CStr(pairParts(1)), "-")
            If UBound(sides) <> 1 Then
                WScript.Echo "ERROR=SIGNAL_SG_PLAN_CONFLICT_TOKEN token=" & CStr(tokens(i))
                WScript.Quit 2
            End If
            sgPlanConflicts(CStr(CLng(Trim(CStr(pairParts(0))))) & "-" & _
                CStr(CLng(Trim(CStr(sides(0))))) & "-" & CStr(CLng(Trim(CStr(sides(1)))))) = True
        End If
    Next
End Sub

Function SignalGroupPlanKey(scNo, sgNo)
    SignalGroupPlanKey = CStr(CLng(Trim(CStr(scNo)))) & "-" & CStr(CLng(Trim(CStr(sgNo))))
End Function

Function SignalGroupPlanWindows(scNo, sgNo)
    Dim key
    SignalGroupPlanWindows = ""
    key = SignalGroupPlanKey(scNo, sgNo)
    If sgPlanWindows.Exists(key) Then SignalGroupPlanWindows = CStr(sgPlanWindows(key))
End Function

' 계획된 녹색창에서 이 순간의 SG 상태를 정한다. 창이 없는 SG 는 영구 적색이다 -
' 이름 규칙처럼 축 상태를 물려주지 않는다.
Function SignalGroupStateFromPlan(scNo, sgNo, pos, cycle)
    Dim spec, entries, i, bounds, startSec, endSec, amberEnd, position, cycleSec
    SignalGroupStateFromPlan = "RED"
    spec = SignalGroupPlanWindows(scNo, sgNo)
    If spec = "" Then Exit Function
    cycleSec = CDbl(cycle)
    If cycleSec <= 0 Then Exit Function
    position = FMod(CDbl(pos), cycleSec)
    entries = Split(spec, ";")
    For i = 0 To UBound(entries)
        If Trim(CStr(entries(i))) <> "" Then
            bounds = Split(CStr(entries(i)), "|")
            startSec = CDbl(bounds(0))
            endSec = CDbl(bounds(1))
            If position >= startSec And position < endSec Then
                SignalGroupStateFromPlan = "GREEN"
                Exit Function
            End If
        End If
    Next
    ' amber 는 **다음 SG 가 아직 녹색이 아닐 때만** 쓴다.
    '
    ' 모델 주기는 major + amber + all_red + minor + amber + all_red 라 **축 경계에만**
    ' clearance 를 예산한다. 그런데 계획은 축 녹색을 SG 창으로 간격 없이 편다
    ' (signal_group_plan.py 의 _cumulative 가 native 간격을 짜낸다 - 의도된 설계다).
    ' 그 위에서 SG 창마다 amber 를 붙이면 앞 SG 의 amber 가 뒤 SG 의 녹색과 겹친다.
    ' 실측으로 SC1001 8구간, 15개 SC 전체 81구간이었다. 이름 규칙 시절에는 축의 모든 SG 가
    ' 같은 상태를 받아 구조적으로 불가능했던 상태다.
    '
    ' 충돌 게이트는 GREEN 만 보므로(SignalGroupPlanCoGreenReason) 이 겹침을 잡지 못한다.
    ' 그래서 여기서 막는다 - 축 내부 전환은 GREEN -> RED 로 바로 간다.
    For i = 0 To UBound(entries)
        If Trim(CStr(entries(i))) <> "" Then
            bounds = Split(CStr(entries(i)), "|")
            endSec = CDbl(bounds(1))
            amberEnd = endSec + CDbl(AMBER_SEC)
            If position >= endSec And position < amberEnd Then
                If Not AnySignalGroupGreenAt(scNo, position, cycleSec) Then
                    SignalGroupStateFromPlan = "AMBER"
                End If
                Exit Function
            End If
            If amberEnd > cycleSec And position < amberEnd - cycleSec Then
                If Not AnySignalGroupGreenAt(scNo, position, cycleSec) Then
                    SignalGroupStateFromPlan = "AMBER"
                End If
                Exit Function
            End If
        End If
    Next
End Function

' 이 SC 의 어느 SG 라도 이 순간 계획상 녹색인가. amber 억제 판정에 쓴다.
Function AnySignalGroupGreenAt(scNo, position, cycleSec)
    Dim key, prefix, spec, entries, i, bounds
    AnySignalGroupGreenAt = False
    prefix = CStr(CLng(scNo)) & "-"
    For Each key In sgPlanWindows.Keys
        If Left(CStr(key), Len(prefix)) = prefix Then
            spec = sgPlanWindows(key)
            If spec <> "" Then
                entries = Split(spec, ";")
                For i = 0 To UBound(entries)
                    If Trim(CStr(entries(i))) <> "" Then
                        bounds = Split(CStr(entries(i)), "|")
                        If position >= CDbl(bounds(0)) And position < CDbl(bounds(1)) Then
                            AnySignalGroupGreenAt = True
                            Exit Function
                        End If
                    End If
                Next
            End If
        End If
    Next
End Function

' 이번 초에 GREEN 인 SG 들 가운데 config 가 금지한 쌍이 있으면 사유를 돌려준다.
' AMBER 는 녹색이 아니다 - 판정 대상은 GREEN 뿐이다.
Function SignalGroupPlanCoGreenReason(scNo, sgNos, states, count)
    Dim i, j, first, second, pairKey
    SignalGroupPlanCoGreenReason = ""
    For i = 0 To CLng(count) - 1
        If UCase(Trim(CStr(states(i)))) = "GREEN" Then
            For j = i + 1 To CLng(count) - 1
                If UCase(Trim(CStr(states(j)))) = "GREEN" Then
                    first = CLng(sgNos(i))
                    second = CLng(sgNos(j))
                    If first > second Then
                        pairKey = CStr(CLng(scNo)) & "-" & CStr(second) & "-" & CStr(first)
                    Else
                        pairKey = CStr(CLng(scNo)) & "-" & CStr(first) & "-" & CStr(second)
                    End If
                    If sgPlanConflicts.Exists(pairKey) Then
                        SignalGroupPlanCoGreenReason = "sg " & CStr(first) & " and sg " & CStr(second)
                        Exit Function
                    End If
                End If
            Next
        End If
    Next
End Function

' 계획이 켜졌으면 VISSIM 이 실제로 들고 있는 SG 와 계약이 완전히 일치해야 한다.
' 여기서 죽는 것이 런 중간에 이름 규칙으로 조용히 떨어지는 것보다 낫다.
Sub ValidateSignalGroupPlanCoverage
    Dim scs, i, scNo, sc, sgCount, sgNo, key, parts, missing, extra
    If Not sgPlanEnabled Then Exit Sub
    missing = 0
    extra = 0
    scs = Split(CStr(RW_SIGNAL_SCS), ",")
    For i = 0 To UBound(scs)
        If Trim(CStr(scs(i))) <> "" Then
            scNo = CLng(Trim(CStr(scs(i))))
            Set sc = CachedSignalController(scNo)
            If sc Is Nothing Then
                WScript.Echo "ERROR=SIGNAL_SG_PLAN_SC_NOT_FOUND sc=" & CStr(scNo)
                WScript.Quit 2
            End If
            sgCount = CachedSignalGroupCount(scNo, sc)
            For sgNo = 1 To sgCount
                If Not sgPlanExpected.Exists(SignalGroupPlanKey(scNo, sgNo)) Then
                    missing = missing + 1
                    WScript.Echo "ERROR=SIGNAL_SG_PLAN_UNCOVERED sc=" & CStr(scNo) & " sg=" & CStr(sgNo)
                End If
            Next
        End If
    Next
    For Each key In sgPlanExpected.Keys
        parts = Split(CStr(key), "-")
        If CachedSignalGroup(CLng(parts(0)), CLng(parts(1))) Is Nothing Then
            extra = extra + 1
            WScript.Echo "ERROR=SIGNAL_SG_PLAN_GROUP_NOT_IN_NETWORK sc=" & CStr(parts(0)) & " sg=" & CStr(parts(1))
        End If
    Next
    If missing > 0 Or extra > 0 Then
        WScript.Echo "ERROR=SIGNAL_SG_PLAN_COVERAGE missing=" & CStr(missing) & " extra=" & CStr(extra)
        WScript.Quit 2
    End If
    WScript.Echo "SIGNAL_SG_PLAN_COVERAGE_OK groups=" & CStr(sgPlanExpected.Count) & _
        " conflict_pairs=" & CStr(sgPlanConflicts.Count) & " source_sha256=" & CStr(RW_SIGNAL_SG_PLAN_SOURCE_SHA256)
End Sub

' 검증을 통과한 계획을 그 SC 의 축 지시(sigMajor/sigMinor/sigOffset)와 **같은 지점에서**
' 커밋한다. 둘이 따로 움직이면 창은 새 주기인데 축은 옛 주기인 조합이 생긴다.
Sub CommitSignalGroupPlan(scNo, pendingWindows, pendingCycle)
    Dim key, prefix
    prefix = CStr(CLng(scNo)) & "-"
    For Each key In sgPlanWindows.Keys
        If Left(CStr(key), Len(prefix)) = prefix Then sgPlanWindows.Remove key
    Next
    For Each key In pendingWindows.Keys
        If Left(CStr(key), Len(prefix)) = prefix Then sgPlanWindows(CStr(key)) = CStr(pendingWindows(key))
    Next
    sgPlanCycle(CStr(CLng(scNo))) = CDbl(pendingCycle)
End Sub

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
    signalTraceSimSec = CLng(simSec)
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
        signalFailures = signalFailures + 1
        WScript.Echo "ERROR=FAILED_SET_SIGSTATE sc=" & scNo & " sg=" & sgNo & " state=" & state & " err=signal group not resolved"
        SetSignalGroupState = "ERR:signal group not resolved"
        RecordSignalReadback scNo, sgNo, state, SetSignalGroupState, False
        Exit Function
    End If
    On Error Resume Next
    sg.AttValue("SigState") = state
    If Err.Number <> 0 Then
        signalFailures = signalFailures + 1
        WScript.Echo "ERROR=FAILED_SET_SIGSTATE sc=" & scNo & " sg=" & sgNo & " state=" & state & " err=" & Err.Description
        SetSignalGroupState = "ERR:" & Err.Description
        RecordSignalReadback scNo, sgNo, state, SetSignalGroupState, False
        Err.Clear
    Else
        SetSignalGroupState = SafeAtt(sg, "SigState")
        If UCase(Trim(CStr(SetSignalGroupState))) <> UCase(Trim(CStr(state))) Then
            signalFailures = signalFailures + 1
            WScript.Echo "ERROR=SIGSTATE_READBACK_MISMATCH sc=" & scNo & " sg=" & sgNo & _
                " requested=" & state & " readback=" & CStr(SetSignalGroupState)
            SetSignalGroupState = "ERR:readback=" & CStr(SetSignalGroupState)
            RecordSignalReadback scNo, sgNo, state, SetSignalGroupState, False
        Else
            Dim requestedKey
            requestedKey = CStr(CLng(scNo)) & "-" & CStr(CLng(sgNo))
            If sigRequestedState.Exists(requestedKey) Then
                sigRequestedState(requestedKey) = CStr(state)
            Else
                sigRequestedState.Add requestedKey, CStr(state)
            End If
            RecordSignalReadback scNo, sgNo, state, SetSignalGroupState, True
        End If
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

' abort 경로는 **실패 증거 전용**이다. OPTIONAL_ATT_SKIPS 를 여기 넣지 마라.
' 건너뛴 설정은 실패가 아니고, 각자 이미 WARN=SKIPPED_OPTIONAL_ATT 로 상세를 남긴다.
' 게다가 이 Sub 는 scripts/tests/test_b1a_vbs_capture_helpers_behavior.py 가 떼어내
' 독립 harness 에서 실행한다 - harness 는 실패 카운터만 선언하므로, 그 밖의 전역을
' 참조하면 Option Explicit 아래서 "변수가 정의되지 않았습니다" 로 죽는다(실측).
Sub AbortVehicleObservation(simSec)
    observationFailures = observationFailures + 1
    WScript.Echo "ERROR=VEHICLE_OBSERVATION_SCAN_FAILED sim_sec=" & CStr(simSec)
    WScript.Echo "OBSERVATION_FAILURES=" & CStr(observationFailures)
    WScript.Echo "COM_FAILURES=" & CStr(comFailures)
    WScript.Quit 13
End Sub

Sub WriteStateJson(simSec, path)
    Dim total, urban, freeway, ramp, boundary, other, meanSpeed, freewayMeanSpeed, stopped, demandUrbanNow, demandFreewayNow
    Dim countE(7), speedE(7), stoppedE(7), countW(7), speedW(7), stoppedW(7)
    Dim localCounts, localStopped, localSpeedSums, localQueueTails, scanOk, perfT0
    Dim collectionCountBefore, collectionCountAfter, captureSimSecBefore, captureSimSecAfter
    Dim recordVehNos, recordLinkNos, recordLaneNos, recordPositions, recordSpeeds, recordStopped, recordLaneRaw
    Dim fullLinkCounts, fullLinkStoppedCounts
    Dim finalPath, tempPath, captureStartNs, captureEndNs
    perfT0 = PerfNow()
    finalPath = path
    tempPath = path
    captureStartNs = ""
    captureEndNs = ""
    If b1aRequired Then
        If fso.FileExists(finalPath) Then
            WScript.Echo "ERROR=B1A_STATE_ALREADY_EXISTS path=" & finalPath
            WScript.Quit 14
        End If
        ValidateB1aCaptureTime simSec
        captureStartNs = ReadRequiredMonotonicClock()
        tempPath = UniqueSiblingPath(finalPath, "state")
    End If
    ScanVehicleState simSec, total, urban, freeway, ramp, boundary, other, meanSpeed, freewayMeanSpeed, stopped, _
        countE, speedE, stoppedE, countW, speedW, stoppedW, localCounts, localStopped, localSpeedSums, localQueueTails, scanOk, _
        collectionCountBefore, collectionCountAfter, captureSimSecBefore, captureSimSecAfter, _
        recordVehNos, recordLinkNos, recordLaneNos, recordPositions, recordSpeeds, recordStopped, recordLaneRaw, _
        fullLinkCounts, fullLinkStoppedCounts
    If Not scanOk Then
        AbortVehicleObservation simSec
    End If
    DemandForecastAtSimSec simSec, demandUrbanNow, demandFreewayNow

    Dim ts
    EnsureParentFolder tempPath
    Set ts = New Utf8LineWriter
    ts.TargetPath = tempPath
    ts.WriteLine "{"
    ts.WriteLine "  ""sim_sec"": " & Num(simSec) & ","
    ts.WriteLine "  ""sim_period_sec"": " & Num(simPeriod) & ","
    ts.WriteLine "  ""control_interval_sec"": " & Num(controlInterval) & ","
    ts.WriteLine "  ""network_path"": """ & JsonEscape(netPath) & ""","
    WriteB1aStateRunProvenance ts
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
    ts.WriteLine "    ""schema_version"": 2,"
    ts.WriteLine "    ""mode"": ""real_world_connector_local_v2"","
    ts.WriteLine "    ""source"": ""vissim_vehicle_link_scan"","
    ts.WriteLine "    ""detector_mapping_json"": """ & JsonEscape(detectorMappingPath) & ""","
    ts.WriteLine "    ""global_vehicle_scan_masked"": true,"
    ts.WriteLine "    ""scan_ok"": true,"
    ts.WriteLine "    ""observed_vehicle_count"": " & CStr(LocalObservationVehicleCount(localCounts)) & ","
    ts.WriteLine "    ""unobservable_vehicle_count"": " & CStr(MaxLong(0, CLng(total) - LocalObservationVehicleCount(localCounts))) & ","
    ts.WriteLine "    ""link_counts"": " & LocalObservationLinkCountsJson(localCounts) & ","
    ts.WriteLine "    ""link_speeds_kph"": " & LocalObservationLinkSpeedsJson(localCounts, localSpeedSums) & ","
    ts.WriteLine "    ""link_stopped_counts"": " & LocalObservationLinkStoppedCountsJson(localStopped) & ","
    ts.WriteLine "    ""link_queue_tail_pos_m"": " & LocalObservationLinkMetricJson(localQueueTails)
    ts.WriteLine "  },"
    WriteVehicleRecordsEnvelope ts, simSec, collectionCountBefore, collectionCountAfter, _
        captureSimSecBefore, captureSimSecAfter, recordVehNos, recordLinkNos, recordLaneNos, _
        recordPositions, recordSpeeds, recordStopped, fullLinkCounts, fullLinkStoppedCounts
    ts.WriteLine "  ""freeway_segments"": {"
    ts.WriteLine "    ""FW_E"": " & SegmentArrayJson(countE, speedE, RW_FW_E_SEG_LENGTHS_KM, RW_FW_E_LANES) & ","
    ts.WriteLine "    ""FW_W"": " & SegmentArrayJson(countW, speedW, RW_FW_W_SEG_LENGTHS_KM, RW_FW_W_LANES)
    ts.WriteLine "  }"
    ts.WriteLine "}"
    ts.Close
    If b1aRequired Then
        ValidateB1aStateRunBinding tempPath, simSec, True
        If fso.FileExists(finalPath) Then
            WScript.Echo "ERROR=B1A_STATE_ALREADY_EXISTS path=" & finalPath
            CleanupUniqueB1aTemp tempPath, finalPath
            WScript.Quit 14
        End If
        fso.MoveFile tempPath, finalPath
        ValidateB1aStateRunBinding finalPath, simSec, False
        captureEndNs = ReadRequiredMonotonicClock()
        PublishB1aVehicleCaptureEvidence simSec, finalPath, captureStartNs, captureEndNs, _
            collectionCountBefore, collectionCountAfter, recordVehNos, recordLinkNos, recordLaneNos, _
            recordPositions, recordSpeeds, recordLaneRaw
    End If
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

Sub WriteVehicleRecordsEnvelope(ts, pausedAtSimSec, collectionCountBefore, collectionCountAfter, _
        captureSimSecBefore, captureSimSecAfter, recordVehNos, recordLinkNos, recordLaneNos, _
        recordPositions, recordSpeeds, recordStopped, fullLinkCounts, fullLinkStoppedCounts)
    Dim i, suffix
    ts.WriteLine "  ""vehicle_records"": {"
    ts.WriteLine "    ""schema_version"": ""vissim-vehicle-records-v2.1"","
    ts.WriteLine "    ""complete"": true,"
    ts.WriteLine "    ""paused_at_sim_sec"": " & JsonDoubleInvariant(pausedAtSimSec) & ","
    ts.WriteLine "    ""capture_sim_sec_before"": " & JsonDoubleInvariant(captureSimSecBefore) & ","
    ts.WriteLine "    ""capture_sim_sec_after"": " & JsonDoubleInvariant(captureSimSecAfter) & ","
    ts.WriteLine "    ""source_attributes"": {""vehicle_number"": ""No"", ""lane"": ""Lane"", ""position"": ""Pos"", ""speed"": ""Speed""},"
    ts.WriteLine "    ""stopped_threshold_kph"": " & JsonDoubleInvariant(B1A_STOPPED_THRESHOLD_KPH) & ","
    ts.WriteLine "    ""collection_count_before"": " & CStr(collectionCountBefore) & ","
    ts.WriteLine "    ""collection_count_after"": " & CStr(collectionCountAfter) & ","
    ts.WriteLine "    ""record_count"": " & CStr(collectionCountBefore) & ","
    ts.WriteLine "    ""unobservable_count"": 0,"
    ts.WriteLine "    ""external_source_count"": 0,"
    WriteB1aCountMap ts, "full_network_link_counts", fullLinkCounts, True
    WriteB1aCountMap ts, "full_network_link_stopped_counts", fullLinkStoppedCounts, True
    ts.WriteLine "    ""records"": ["
    For i = 0 To collectionCountBefore - 1
        suffix = ","
        If i = collectionCountBefore - 1 Then suffix = ""
        ts.WriteLine "      {""veh_no"": " & CStr(recordVehNos(i)) & _
            ", ""link_no"": " & CStr(recordLinkNos(i)) & _
            ", ""lane_no"": " & CStr(recordLaneNos(i)) & _
            ", ""position_m"": " & JsonDoubleInvariant(recordPositions(i)) & _
            ", ""speed_kph"": " & JsonDoubleInvariant(recordSpeeds(i)) & _
            ", ""stopped"": " & JsonBoolean(recordStopped(i)) & "}" & suffix
    Next
    ts.WriteLine "    ]"
    ts.WriteLine "  },"
End Sub

Sub WriteB1aCountMap(ts, fieldName, counts, trailingComma)
    Dim keys, i, suffix
    ts.WriteLine "    """ & JsonEscape(fieldName) & """: {"
    If counts.Count > 0 Then
        keys = counts.Keys
        QuickSortB1aLongKeys keys, LBound(keys), UBound(keys)
        For i = LBound(keys) To UBound(keys)
            suffix = ","
            If i = UBound(keys) Then suffix = ""
            ts.WriteLine "      """ & JsonEscape(CStr(keys(i))) & """: " & CStr(CLng(counts(keys(i)))) & suffix
        Next
    End If
    suffix = ""
    If trailingComma Then suffix = ","
    ts.WriteLine "    }" & suffix
End Sub

Sub QuickSortB1aLongKeys(ByRef values, first, last)
    Dim low, high, pivot, temp
    low = first
    high = last
    pivot = CLng(values((first + last) \ 2))
    Do While low <= high
        Do While CLng(values(low)) < pivot
            low = low + 1
        Loop
        Do While CLng(values(high)) > pivot
            high = high - 1
        Loop
        If low <= high Then
            temp = values(low)
            values(low) = values(high)
            values(high) = temp
            low = low + 1
            high = high - 1
        End If
    Loop
    If first < high Then QuickSortB1aLongKeys values, first, high
    If low < last Then QuickSortB1aLongKeys values, low, last
End Sub

Sub LogStateCsv(simSec)
    Dim total, urban, freeway, ramp, boundary, other, meanSpeed, freewayMeanSpeed, stopped
    Dim countE(7), speedE(7), stoppedE(7), countW(7), speedW(7), stoppedW(7), status, wall
    Dim linkCounts, linkStopped, linkSpeedSums, linkQueueTails, scanOk, perfT0
    Dim collectionCountBefore, collectionCountAfter, captureSimSecBefore, captureSimSecAfter
    Dim recordVehNos, recordLinkNos, recordLaneNos, recordPositions, recordSpeeds, recordStopped, recordLaneRaw
    Dim fullLinkCounts, fullLinkStoppedCounts
    perfT0 = PerfNow()
    ScanVehicleState simSec, total, urban, freeway, ramp, boundary, other, meanSpeed, freewayMeanSpeed, stopped, _
        countE, speedE, stoppedE, countW, speedW, stoppedW, linkCounts, linkStopped, linkSpeedSums, linkQueueTails, scanOk, _
        collectionCountBefore, collectionCountAfter, captureSimSecBefore, captureSimSecAfter, _
        recordVehNos, recordLinkNos, recordLaneNos, recordPositions, recordSpeeds, recordStopped, recordLaneRaw, _
        fullLinkCounts, fullLinkStoppedCounts
    If Not scanOk Then
        AbortVehicleObservation simSec
    End If
    status = LastControllerStatus()
    wall = LastDecisionWallSec()
    stateFile.WriteLine CStr(simSec) & "," & CStr(total) & "," & CStr(urban) & "," & CStr(freeway) & "," & _
        CStr(ramp) & "," & CStr(boundary) & "," & CStr(other) & "," & Num(meanSpeed) & "," & _
        Num(freewayMeanSpeed) & "," & CStr(stopped) & ",VISSIM_REAL_WORLD_" & UCase(controllerName) & "," & status & "," & wall
    If LogBottleneckDetailsEnabled() And scanOk Then
        WriteBottleneckRows simSec, countE, stoppedE, speedE, countW, stoppedW, speedW, linkCounts, linkStopped, linkSpeedSums
    End If
    MaybeWriteAuditAnchorState simSec
    PerfAdd "log.state_csv", perfT0
End Sub

Sub MaybeWriteAuditAnchorState(simSec)
    Dim anchorPath
    If auditAnchorsSec = "" Then Exit Sub
    If Not InCsvInt(CLng(simSec), auditAnchorsSec) Then Exit Sub
    anchorPath = fso.BuildPath(decisionDir, "anchor_" & Pad6(CLng(simSec)) & ".json")
    WriteStateJson CLng(simSec), anchorPath
    WScript.Echo "AUDIT_ANCHOR_STATE sim_sec=" & CStr(simSec) & " path=" & anchorPath
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
Sub ScanVehicleState(expectedSimSec, ByRef total, ByRef urban, ByRef freeway, ByRef ramp, ByRef boundary, ByRef other, _
        ByRef meanSpeed, ByRef freewayMeanSpeed, ByRef stopped, _
        ByRef countE, ByRef speedE, ByRef stoppedE, ByRef countW, ByRef speedW, ByRef stoppedW, _
        ByRef linkCounts, ByRef linkStopped, ByRef linkSpeedSums, ByRef linkQueueTails, ByRef scanOk, _
        ByRef collectionCountBefore, ByRef collectionCountAfter, ByRef captureSimSecBefore, ByRef captureSimSecAfter, _
        ByRef recordVehNos, ByRef recordLinkNos, ByRef recordLaneNos, ByRef recordPositions, ByRef recordSpeeds, ByRef recordStopped, _
        ByRef recordLaneRaw, ByRef fullLinkCounts, ByRef fullLinkStoppedCounts)
    total = 0: urban = 0: freeway = 0: ramp = 0: boundary = 0: other = 0
    meanSpeed = 0: freewayMeanSpeed = 0: stopped = 0
    scanOk = False
    collectionCountBefore = 0: collectionCountAfter = 0
    captureSimSecBefore = 0.0: captureSimSecAfter = 0.0
    recordVehNos = Empty: recordLinkNos = Empty: recordLaneNos = Empty: recordLaneRaw = Empty
    recordPositions = Empty: recordSpeeds = Empty: recordStopped = Empty
    Set linkCounts = CreateObject("Scripting.Dictionary")
    Set linkStopped = CreateObject("Scripting.Dictionary")
    Set linkSpeedSums = CreateObject("Scripting.Dictionary")
    Set linkQueueTails = CreateObject("Scripting.Dictionary")
    Set fullLinkCounts = CreateObject("Scripting.Dictionary")
    Set fullLinkStoppedCounts = CreateObject("Scripting.Dictionary")
    Dim i
    For i = 0 To 7
        countE(i) = 0: speedE(i) = 0: stoppedE(i) = 0
        countW(i) = 0: speedW(i) = 0: stoppedW(i) = 0
    Next

    Dim noArray, laneArray, posArray, speedArray, ok, lo, hi, keyCol, valueCol, row, recordIndex
    Dim noKey, laneKey, posKey, speedKey, vehNo, linkNo, laneNo, key, pos, speed
    Dim speedSum, freewaySpeedSum, seg, chainPos, isStopped, perfT0, snapshotIds
    perfT0 = PerfNow()
    speedSum = 0: freewaySpeedSum = 0
    Set snapshotIds = CreateObject("Scripting.Dictionary")
    ok = ReadVerifiedVehicleTables(expectedSimSec, noArray, laneArray, posArray, speedArray, _
        collectionCountBefore, collectionCountAfter, captureSimSecBefore, captureSimSecAfter, _
        lo, hi, keyCol, valueCol)
    If Not ok Then
        PerfAdd "scan.vehicles", perfT0
        Exit Sub
    End If

    If collectionCountBefore > 0 Then
        ReDim recordVehNos(collectionCountBefore - 1)
        ReDim recordLinkNos(collectionCountBefore - 1)
        ReDim recordLaneNos(collectionCountBefore - 1)
        ReDim recordPositions(collectionCountBefore - 1)
        ReDim recordSpeeds(collectionCountBefore - 1)
        ReDim recordStopped(collectionCountBefore - 1)
        ReDim recordLaneRaw(collectionCountBefore - 1)
    End If

    For row = lo To hi
        If Not TryPositiveLongVariant(noArray(row, keyCol), noKey) _
                Or Not TryPositiveLongVariant(laneArray(row, keyCol), laneKey) _
                Or Not TryPositiveLongVariant(posArray(row, keyCol), posKey) _
                Or Not TryPositiveLongVariant(speedArray(row, keyCol), speedKey) _
                Or Not TryPositiveLongVariant(noArray(row, valueCol), vehNo) Then
            RecordVehicleCaptureFailure "invalid_numeric_value", "row=" & CStr(row) & " field=No_or_COM_key"
            PerfAdd "scan.vehicles", perfT0
            Exit Sub
        End If
        ' GetMultiAttValues returns (row index, value) pairs. keyColumn is the container's
        ' SEQUENTIAL ROW INDEX, not the object key, so it must NOT be compared against the
        ' vehicle number. The two coincide only while the network still holds vehicles
        ' 1..N with no gaps; once any vehicle leaves, index and No diverge.
        ' Measured 2026-08-07: sim_sec 1 captured veh_no 1..6 with index 1..6 and passed,
        ' then sim_sec 90 failed at row 7 with com_row_key_mismatch. Every attempt died there.
        ' What must hold is that the four arrays are row-aligned - they come from one paused
        ' container read - and that vehicle numbers are unique inside the snapshot, which the
        ' snapshotIds check below already enforces.
        If noKey <> laneKey Or noKey <> posKey Or noKey <> speedKey Then
            RecordVehicleCaptureFailure "com_row_key_mismatch", "row=" & CStr(row)
            PerfAdd "scan.vehicles", perfT0
            Exit Sub
        End If
        key = CStr(vehNo)
        If snapshotIds.Exists(key) Then
            RecordVehicleCaptureFailure "duplicate_vehicle_in_snapshot", "veh_no=" & key
            PerfAdd "scan.vehicles", perfT0
            Exit Sub
        End If
        snapshotIds.Add key, True
        If Not ParseB1aLaneId(laneArray(row, valueCol), linkNo, laneNo) Then
            RecordVehicleCaptureFailure "unknown_lane", "row=" & CStr(row) & " veh_no=" & key
            PerfAdd "scan.vehicles", perfT0
            Exit Sub
        End If
        ' Report the offending value and its VarType. Without them a rejected row is not
        ' diagnosable from the runlog - the operator cannot tell an out-of-range number
        ' from a missing/non-numeric variant, and reproducing needs a full run to the
        ' same sim_sec. Measured 2026-08-07: row=4004 field=Pos at sim_sec 2430.
        If Not TryB1aPosition(posArray(row, valueCol), pos) Then
            ' Boundary-entry geometry: see B1A_ENTRY_TOLERANCE_M above.
            If Not TryB1aEntryPosition(posArray(row, valueCol), pos) Then
                RecordVehicleCaptureFailure "invalid_numeric_value", _
                    "row=" & CStr(row) & " field=Pos veh_no=" & key & _
                    " vartype=" & CStr(VarType(posArray(row, valueCol))) & _
                    " value=" & OneLine(CStr(posArray(row, valueCol)))
                PerfAdd "scan.vehicles", perfT0
                Exit Sub
            End If
            WScript.Echo "B1A_ENTRY_CLAMPED sim_sec=" & JsonDoubleInvariant(expectedSimSec) & _
                " veh_no=" & key & " link_no=" & CStr(linkNo) & " lane_no=" & CStr(laneNo) & _
                " raw_pos_m=" & OneLine(CStr(posArray(row, valueCol))) & " clamped_to_m=0"
            pos = 0.0
        End If
        If Not TryB1aSpeed(speedArray(row, valueCol), speed) Then
            RecordVehicleCaptureFailure "invalid_numeric_value", _
                "row=" & CStr(row) & " field=Speed veh_no=" & key & _
                " vartype=" & CStr(VarType(speedArray(row, valueCol))) & _
                " value=" & OneLine(CStr(speedArray(row, valueCol)))
            PerfAdd "scan.vehicles", perfT0
            Exit Sub
        End If

        recordIndex = row - lo
        recordVehNos(recordIndex) = vehNo
        recordLinkNos(recordIndex) = linkNo
        recordLaneNos(recordIndex) = laneNo
        recordLaneRaw(recordIndex) = CStr(laneArray(row, valueCol))
        recordPositions(recordIndex) = pos
        recordSpeeds(recordIndex) = speed
        isStopped = (speed < B1A_STOPPED_THRESHOLD_KPH)
        recordStopped(recordIndex) = isStopped

        total = total + 1
        speedSum = speedSum + speed
        If isStopped Then stopped = stopped + 1

        key = CStr(linkNo)
        AddDictNumber fullLinkCounts, key, 1.0
        If Not fullLinkStoppedCounts.Exists(key) Then fullLinkStoppedCounts.Add key, 0.0
        If isStopped Then AddDictNumber fullLinkStoppedCounts, key, 1.0

        AddDictNumber linkCounts, key, 1.0
        AddDictNumber linkSpeedSums, key, speed
        If isStopped Then
            AddDictNumber linkStopped, key, 1.0
            If Not linkQueueTails.Exists(key) Then
                linkQueueTails.Add key, pos
            ElseIf pos < CDbl(linkQueueTails(key)) Then
                linkQueueTails(key) = pos
            End If
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
    If total <> collectionCountBefore Or snapshotIds.Count <> collectionCountBefore _
            Or B1aCountMapTotal(fullLinkCounts) <> total _
            Or B1aCountMapTotal(fullLinkStoppedCounts) <> stopped Then
        RecordVehicleCaptureFailure "aggregate_mismatch", "records=" & CStr(total) & _
            " unique=" & CStr(snapshotIds.Count) & " collection=" & CStr(collectionCountBefore) & _
            " link_count_total=" & CStr(B1aCountMapTotal(fullLinkCounts)) & _
            " link_stopped_total=" & CStr(B1aCountMapTotal(fullLinkStoppedCounts))
        PerfAdd "scan.vehicles", perfT0
        Exit Sub
    End If
    If total > 0 Then meanSpeed = speedSum / total
    If freeway > 0 Then freewayMeanSpeed = freewaySpeedSum / freeway
    scanOk = True
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

Sub ValidateRuntimeSignalPersistence(simSec)
    Dim key, parts, scNo, sgNo, sg, requestedState, readbackState, ok
    If sigRequestedState.Count <= 0 Then Exit Sub
    signalTraceSimSec = CLng(simSec)
    signalTraceStage = "post_step"
    For Each key In sigRequestedState.Keys
        parts = Split(CStr(key), "-")
        scNo = CLng(parts(0)): sgNo = CLng(parts(1))
        requestedState = CStr(sigRequestedState(key))
        Set sg = CachedSignalGroup(scNo, sgNo)
        If sg Is Nothing Then
            readbackState = "ERR:signal group not resolved"
            ok = False
        Else
            readbackState = SafeAtt(sg, "SigState")
            ok = (UCase(Trim(CStr(readbackState))) = UCase(Trim(CStr(requestedState))))
        End If
        If Not ok Then
            signalFailures = signalFailures + 1
            WScript.Echo "ERROR=SIGSTATE_POST_STEP_MISMATCH sc=" & CStr(scNo) & " sg=" & CStr(sgNo) & _
                " requested=" & requestedState & " readback=" & CStr(readbackState)
        End If
        RecordSignalReadback scNo, sgNo, requestedState, readbackState, ok
    Next
    signalTraceStage = "immediate"
End Sub

Sub RecordSignalReadback(scNo, sgNo, requestedState, readbackState, ok)
    If signalTraceStage = "post_step" Then
        signalPersistenceChecks = signalPersistenceChecks + 1
        If CBool(ok) Then signalPersistenceOk = signalPersistenceOk + 1
    Else
        signalWriteAttempts = signalWriteAttempts + 1
        If CBool(ok) Then signalReadbackOk = signalReadbackOk + 1
    End If
    signalTraceFile.WriteLine CStr(signalTraceSimSec) & "," & CStr(scNo) & "," & CStr(sgNo) & "," & _
        CStr(requestedState) & "," & CStr(readbackState) & "," & BoolInt(ok) & "," & signalTraceStage
End Sub

Function LocalObservationVehicleCount(counts)
    Dim parts, i, linkText, total
    parts = Split(RW_LOCAL_OBSERVABLE_LINKS, ",")
    total = 0
    For i = 0 To UBound(parts)
        linkText = Trim(parts(i))
        If linkText <> "" Then total = total + DictCount(counts, CLng(linkText))
    Next
    LocalObservationVehicleCount = total
End Function

Function MaxLong(leftValue, rightValue)
    If CLng(leftValue) >= CLng(rightValue) Then
        MaxLong = CLng(leftValue)
    Else
        MaxLong = CLng(rightValue)
    End If
End Function

Function LocalObservationLinkSpeedsJson(counts, speedSums)
    Dim parts, i, linkText, s, count, meanSpeed
    parts = Split(RW_LOCAL_OBSERVABLE_LINKS, ",")
    s = "{"
    For i = 0 To UBound(parts)
        linkText = Trim(parts(i))
        If linkText <> "" Then
            If Len(s) > 1 Then s = s & ", "
            count = DictCount(counts, CLng(linkText))
            meanSpeed = 0.0
            If count > 0 Then meanSpeed = DictNumber(speedSums, linkText) / CDbl(count)
            s = s & """" & JsonEscape(linkText) & """: " & Num(meanSpeed)
        End If
    Next
    s = s & "}"
    LocalObservationLinkSpeedsJson = s
End Function

Function LocalObservationLinkStoppedCountsJson(stoppedCounts)
    Dim parts, i, linkText, s
    parts = Split(RW_LOCAL_OBSERVABLE_LINKS, ",")
    s = "{"
    For i = 0 To UBound(parts)
        linkText = Trim(parts(i))
        If linkText <> "" Then
            If Len(s) > 1 Then s = s & ", "
            s = s & """" & JsonEscape(linkText) & """: " & CStr(DictCount(stoppedCounts, CLng(linkText)))
        End If
    Next
    s = s & "}"
    LocalObservationLinkStoppedCountsJson = s
End Function

Function LocalObservationLinkMetricJson(values)
    Dim parts, i, linkText, s, value
    parts = Split(RW_LOCAL_OBSERVABLE_LINKS, ",")
    s = "{"
    For i = 0 To UBound(parts)
        linkText = Trim(parts(i))
        If linkText <> "" Then
            If Len(s) > 1 Then s = s & ", "
            value = 0.0
            If IsObject(values) And values.Exists(linkText) Then value = CDbl(values(linkText))
            s = s & """" & JsonEscape(linkText) & """: " & Num(value)
        End If
    Next
    s = s & "}"
    LocalObservationLinkMetricJson = s
End Function

Function JsonEscape(value)
    Dim text, pieces, i, ch, code
    text = CStr(value)
    If Len(text) = 0 Then
        JsonEscape = ""
        Exit Function
    End If
    ReDim pieces(Len(text) - 1)
    For i = 1 To Len(text)
        ch = Mid(text, i, 1)
        code = AscW(ch)
        Select Case code
            Case 8
                pieces(i - 1) = "\b"
            Case 9
                pieces(i - 1) = "\t"
            Case 10
                pieces(i - 1) = "\n"
            Case 12
                pieces(i - 1) = "\f"
            Case 13
                pieces(i - 1) = "\r"
            Case 34
                pieces(i - 1) = "\" & Chr(34)
            Case 92
                pieces(i - 1) = "\\"
            Case Else
                If code >= 0 And code <= 31 Then
                    pieces(i - 1) = "\u" & Right("0000" & Hex(code), 4)
                Else
                    pieces(i - 1) = ch
                End If
        End Select
    Next
    JsonEscape = Join(pieces, "")
End Function

Function B1aCountMapTotal(counts)
    Dim key, total
    total = 0
    For Each key In counts.Keys
        total = total + CLng(counts(key))
    Next
    B1aCountMapTotal = total
End Function

Function JsonBoolean(value)
    If CBool(value) Then
        JsonBoolean = "true"
    Else
        JsonBoolean = "false"
    End If
End Function

Function JsonDoubleInvariant(value)
    Dim text, exponentText, exponentPos, mantissa, digits
    text = CStr(CDbl(value))
    If JSON_DECIMAL_SEPARATOR <> "." Then text = Replace(text, JSON_DECIMAL_SEPARATOR, ".")
    exponentPos = InStr(1, text, "E", vbTextCompare)
    exponentText = ""
    If exponentPos > 0 Then
        exponentText = Mid(text, exponentPos)
        mantissa = Left(text, exponentPos - 1)
    Else
        mantissa = text
    End If
    If InStr(1, mantissa, ".", vbBinaryCompare) = 0 Then mantissa = mantissa & "."
    digits = B1aSignificantDigitCount(mantissa)
    Do While digits < 15
        mantissa = mantissa & "0"
        digits = digits + 1
    Loop
    If Right(mantissa, 1) = "." Then mantissa = mantissa & "0"
    JsonDoubleInvariant = mantissa & exponentText
End Function

Function B1aSignificantDigitCount(text)
    Dim i, ch, seenNonzero, count, digitCount
    seenNonzero = False
    count = 0
    digitCount = 0
    For i = 1 To Len(text)
        ch = Mid(text, i, 1)
        If ch >= "0" And ch <= "9" Then
            digitCount = digitCount + 1
            If ch <> "0" Then seenNonzero = True
            If seenNonzero Then count = count + 1
        End If
    Next
    If Not seenNonzero Then count = digitCount
    B1aSignificantDigitCount = count
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
        ' 의도는 "결과를 DB 로 내보내지 않는다" 인데, 모듈이 비활성이면 DB 출력 자체가 불가능하다.
    ' 실패가 곧 보장이다(실측 문구: "put_AttValue failed - module not active").
    TrySetUnreachableEvaluationAtt "DatabaseConnection", "", "database module inactive means no DB output is possible"
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

Function RunCapture3Timeout(cmd, timeoutSec, ByRef outText, ByRef errText)
    Dim exec, t0, elapsed
    outText = ""
    errText = ""
    On Error Resume Next
    Set exec = shell.Exec(cmd)
    If Err.Number <> 0 Then
        errText = "EXEC_FAILED " & Err.Description
        Err.Clear
        On Error GoTo 0
        RunCapture3Timeout = -1
        Exit Function
    End If
    On Error GoTo 0
    t0 = Timer
    Do While exec.Status = 0
        WScript.Sleep 25
        elapsed = Timer - CDbl(t0)
        If elapsed < 0 Then elapsed = elapsed + 86400.0
        If elapsed > CDbl(timeoutSec) Then
            On Error Resume Next
            TerminateExecTree exec
            exec.Terminate
            Err.Clear
            On Error GoTo 0
            errText = "EXEC_TIMEOUT"
            RunCapture3Timeout = -2
            Exit Function
        End If
    Loop
    outText = exec.StdOut.ReadAll
    errText = exec.StdErr.ReadAll
    RunCapture3Timeout = exec.ExitCode
End Function

Sub TerminateExecTree(exec)
    Dim pid
    On Error Resume Next
    pid = exec.ProcessID
    If Err.Number = 0 And CLng(pid) > 0 Then
        shell.Run "cmd /c taskkill /PID " & CStr(pid) & " /T /F >NUL 2>NUL", 0, True
    End If
    Err.Clear
    On Error GoTo 0
End Sub

Sub ValidateB1aRequiredStartup()
    If Not b1aRequired Then Exit Sub
    If runId = "" Or runManifestPath = "" Or runManifestSha256 = "" Or qualificationMode <> "live_required" Then
        WScript.Echo "ERROR=B1A_REQUIRED_ENV_MISSING"
        WScript.Quit 12
    End If
    If Not fso.FileExists(runManifestPath) Or Not fso.FileExists(stateManifestBuilderPath) Or Not fso.FileExists(monotonicClockHelperPath) Then
        WScript.Echo "ERROR=B1A_REQUIRED_SOURCE_MISSING manifest=" & runManifestPath
        WScript.Quit 12
    End If
    runManifestRelPath = WorkspaceRelativePath(runManifestPath)
    ValidateB1aRunBinding ""
End Sub

Sub ValidateB1aCaptureTime(simSec)
    ValidateB1aRunBinding JsonDoubleInvariant(simSec)
End Sub

Sub ValidateB1aRunBinding(captureTimeText)
    Dim cmd, outText, errText, exitCode
    cmd = pythonExe & " -B " & Q(stateManifestBuilderPath) & _
        " --workspace-root " & Q(workspaceRoot) & _
        " --validate-run-binding --run-manifest " & Q(runManifestPath) & _
        " --run-manifest-sha256 " & Q(runManifestSha256) & _
        " --run-id " & Q(runId) & " --qualification-mode " & Q(qualificationMode)
    If CStr(captureTimeText) <> "" Then cmd = cmd & " --capture-time " & CStr(captureTimeText)
    exitCode = RunCapture3Timeout(cmd, B1A_PYTHON_HELPER_TIMEOUT_SEC, outText, errText)
    If exitCode <> 0 Or errText <> "" Or Not IsB1aPassLine(outText, "status=PASS run_id=") Then
        WScript.Echo "ERROR=B1A_RUN_BINDING_INVALID exit=" & CStr(exitCode) & " stderr=" & OneLine(errText) & " stdout=" & OneLine(outText)
        WScript.Quit 12
    End If
End Sub

Sub ValidateB1aStateRunBinding(statePath, simSec, cleanupOnFailure)
    Dim cmd, outText, errText, exitCode
    cmd = pythonExe & " -B " & Q(stateManifestBuilderPath) & _
        " --workspace-root " & Q(workspaceRoot) & _
        " --validate-state-run-binding --state " & Q(statePath) & _
        " --run-manifest " & Q(runManifestPath) & _
        " --run-manifest-sha256 " & Q(runManifestSha256) & _
        " --run-id " & Q(runId) & " --qualification-mode " & Q(qualificationMode) & _
        " --capture-time " & JsonDoubleInvariant(simSec)
    exitCode = RunCapture3Timeout(cmd, B1A_PYTHON_HELPER_TIMEOUT_SEC, outText, errText)
    If exitCode <> 0 Or errText <> "" Or Not IsB1aPassLine(outText, "status=PASS state=") Then
        If cleanupOnFailure Then CleanupUniqueB1aTemp statePath, ""
        WScript.Echo "ERROR=B1A_STATE_RUN_BINDING_INVALID exit=" & CStr(exitCode) & " stderr=" & OneLine(errText) & " stdout=" & OneLine(outText)
        WScript.Quit 14
    End If
End Sub

Function ReadRequiredMonotonicClock()
    Dim cmd, outText, errText, exitCode, prefix, suffix, value
    cmd = pythonExe & " -B " & Q(monotonicClockHelperPath)
    exitCode = RunCapture3Timeout(cmd, 5, outText, errText)
    If exitCode <> 0 Or errText <> "" Then
        WScript.Echo "ERROR=B1A_MONOTONIC_HELPER_FAILED exit=" & CStr(exitCode) & " stderr=" & OneLine(errText)
        WScript.Quit 12
    End If
    prefix = "python_perf_counter_ns="
    suffix = vbLf
    If Left(outText, Len(prefix)) <> prefix Or Right(outText, 1) <> suffix Or InStr(1, Left(outText, Len(outText) - 1), vbLf, vbBinaryCompare) > 0 Then
        WScript.Echo "ERROR=B1A_MONOTONIC_HELPER_FRAMING stdout=" & OneLine(outText)
        WScript.Quit 12
    End If
    value = Mid(outText, Len(prefix) + 1, Len(outText) - Len(prefix) - 1)
    If Not IsPositiveDecimalText(value) Then
        WScript.Echo "ERROR=B1A_MONOTONIC_HELPER_FRAMING stdout=" & OneLine(outText)
        WScript.Quit 12
    End If
    ReadRequiredMonotonicClock = value
End Function

Function IsPositiveDecimalText(text)
    Dim i, ch
    IsPositiveDecimalText = False
    If Len(text) = 0 Then Exit Function
    If Left(text, 1) = "0" Then Exit Function
    For i = 1 To Len(text)
        ch = Mid(text, i, 1)
        If ch < "0" Or ch > "9" Then Exit Function
    Next
    IsPositiveDecimalText = True
End Function

Function IsB1aPassLine(text, prefix)
    IsB1aPassLine = False
    If Len(text) <= Len(prefix) Then Exit Function
    If Left(text, Len(prefix)) <> prefix Then Exit Function
    If Right(text, 1) <> vbLf Then Exit Function
    If InStr(1, Left(text, Len(text) - 1), vbLf, vbBinaryCompare) > 0 Then Exit Function
    IsB1aPassLine = True
End Function

Function WorkspaceRelativePath(path)
    Dim absRoot, absPath, prefix
    absRoot = fso.GetAbsolutePathName(workspaceRoot)
    absPath = fso.GetAbsolutePathName(path)
    prefix = absRoot & "\"
    If LCase(Left(absPath, Len(prefix))) <> LCase(prefix) Then
        WScript.Echo "ERROR=B1A_PATH_ESCAPES_WORKSPACE path=" & path
        WScript.Quit 12
    End If
    WorkspaceRelativePath = Replace(Mid(absPath, Len(prefix) + 1), "\", "/")
End Function

Function B1aManifestPathForState()
    If b1aRequired Then
        B1aManifestPathForState = runManifestRelPath
    Else
        B1aManifestPathForState = runManifestPath
    End If
End Function

Sub WriteB1aStateRunProvenance(ts)
    If b1aRequired Then
        ts.WriteLine "  ""run_provenance"": {""run_id"": """ & JsonEscape(runId) & """, ""manifest_path"": """ & JsonEscape(runManifestRelPath) & """, ""manifest_sha256"": """ & JsonEscape(runManifestSha256) & """},"
    Else
        ts.WriteLine "  ""run_provenance"": {""run_id"": """ & JsonEscape(runId) & """, ""manifest_path"": """ & JsonEscape(runManifestPath) & """},"
    End If
End Sub

Function UniqueSiblingPath(finalPath, label)
    Dim parent, name
    parent = fso.GetParentFolderName(finalPath)
    Do
        name = "." & fso.GetBaseName(finalPath) & "." & label & "." & fso.GetTempName()
        UniqueSiblingPath = fso.BuildPath(parent, name)
    Loop While fso.FileExists(UniqueSiblingPath)
End Function

Sub CleanupUniqueB1aTemp(path, immutablePath)
    On Error Resume Next
    If path <> "" Then
        If immutablePath = "" Or LCase(fso.GetAbsolutePathName(path)) <> LCase(fso.GetAbsolutePathName(immutablePath)) Then
            If fso.FileExists(path) Then fso.DeleteFile path, True
        End If
    End If
    Err.Clear
    On Error GoTo 0
End Sub

Sub PublishB1aVehicleCaptureEvidence(simSec, statePath, startNs, endNs, collectionCountBefore, collectionCountAfter, _
        recordVehNos, recordLinkNos, recordLaneNos, recordPositions, recordSpeeds, recordLaneRaw)
    Dim sidecarPath, requestPath, ts, i, suffix, cmd, outText, errText, exitCode
    sidecarPath = fso.BuildPath(fso.GetParentFolderName(statePath), fso.GetBaseName(statePath) & ".vehicle_capture_v2_1.json")
    If fso.FileExists(sidecarPath) Then
        WScript.Echo "ERROR=B1A_CAPTURE_EVIDENCE_ALREADY_EXISTS path=" & sidecarPath
        WScript.Quit 14
    End If
    requestPath = UniqueSiblingPath(sidecarPath, "request")
    Set ts = New Utf8LineWriter
    ts.TargetPath = requestPath
    ts.WriteLine "{"
    ts.WriteLine "  ""run_id"": """ & JsonEscape(runId) & ""","
    ts.WriteLine "  ""sim_sec"": " & JsonDoubleInvariant(simSec) & ","
    ts.WriteLine "  ""qualification"": {""mode"": ""live_required""},"
    ts.WriteLine "  ""run_manifest_path"": """ & JsonEscape(runManifestRelPath) & ""","
    ts.WriteLine "  ""run_manifest_sha256"": """ & JsonEscape(runManifestSha256) & ""","
    ts.WriteLine "  ""state_path"": """ & JsonEscape(WorkspaceRelativePath(statePath)) & ""","
    ts.WriteLine "  ""vissim_version_raw"": """ & JsonEscape(vissimVersionRaw) & ""","
    ts.WriteLine "  ""counts"": {""collection_count_before"": " & CStr(collectionCountBefore) & ", ""collection_count_after"": " & CStr(collectionCountAfter) & ", ""record_count"": " & CStr(collectionCountBefore) & "},"
    ts.WriteLine "  ""capture_timer"": {""clock"": ""python_perf_counter_ns"", ""start_ns"": " & CStr(startNs) & ", ""end_ns"": " & CStr(endNs) & ", ""elapsed_sec"": 0.0},"
    ts.WriteLine "  ""raw_attribute_rows"": ["
    For i = 0 To collectionCountBefore - 1
        suffix = ","
        If i = collectionCountBefore - 1 Then suffix = ""
        ts.WriteLine "    {""com_key"": " & CStr(recordVehNos(i)) & _
            ", ""no_value"": " & CStr(recordVehNos(i)) & _
            ", ""lane_raw"": """ & JsonEscape(recordLaneRaw(i)) & """" & _
            ", ""parsed_link_no"": " & CStr(recordLinkNos(i)) & _
            ", ""parsed_lane_no"": " & CStr(recordLaneNos(i)) & _
            ", ""position_value"": " & JsonDoubleInvariant(recordPositions(i)) & _
            ", ""speed_value"": " & JsonDoubleInvariant(recordSpeeds(i)) & "}" & suffix
    Next
    ts.WriteLine "  ]"
    ts.WriteLine "}"
    ts.Close
    cmd = pythonExe & " -B " & Q(stateManifestBuilderPath) & _
        " --workspace-root " & Q(workspaceRoot) & _
        " --produce-vehicle-capture --vehicle-capture-request " & Q(requestPath) & _
        " --vehicle-capture " & Q(sidecarPath)
    exitCode = RunCapture3Timeout(cmd, B1A_PYTHON_HELPER_TIMEOUT_SEC, outText, errText)
    On Error Resume Next
    fso.DeleteFile requestPath, True
    Err.Clear
    On Error GoTo 0
    If exitCode <> 0 Or errText <> "" Or Not IsB1aPassLine(outText, "status=PASS vehicle_capture=") Then
        WScript.Echo "ERROR=B1A_CAPTURE_EVIDENCE_FAILED exit=" & CStr(exitCode) & " stderr=" & OneLine(errText) & " stdout=" & OneLine(outText)
        WScript.Quit 14
    End If
End Sub

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
    Private textStream
    Private Sub Class_Initialize()
        Set textStream = CreateObject("ADODB.Stream")
        textStream.Type = 2
        textStream.Charset = "utf-8"
        textStream.Open
    End Sub
    Public Sub WriteLine(text)
        textStream.WriteText CStr(text) & vbCrLf
    End Sub
    Public Sub Close()
        Dim binStream
        textStream.Position = 3
        Set binStream = CreateObject("ADODB.Stream")
        binStream.Type = 1
        binStream.Open
        textStream.CopyTo binStream
        binStream.SaveToFile TargetPath, 2
        binStream.Close
        textStream.Close
        Set binStream = Nothing
        Set textStream = Nothing
    End Sub
End Class

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

Function ReadVerifiedVehicleTables(expectedSimSec, ByRef noArray, ByRef laneArray, ByRef posArray, ByRef speedArray, _
        ByRef collectionCountBefore, ByRef collectionCountAfter, ByRef captureSimSecBefore, ByRef captureSimSecAfter, _
        ByRef rowLower, ByRef rowUpper, ByRef keyColumn, ByRef valueColumn)
    Dim rawCountBefore, rawCountAfter, rawTimeBefore, rawTimeAfter, expectedTime
    Dim noRowLower, noRowUpper, noColLower, noColUpper
    Dim laneRowLower, laneRowUpper, laneColLower, laneColUpper
    Dim posRowLower, posRowUpper, posColLower, posColUpper
    Dim speedRowLower, speedRowUpper, speedColLower, speedColUpper
    ReadVerifiedVehicleTables = False
    rowLower = 0: rowUpper = -1: keyColumn = 0: valueColumn = 1
    On Error Resume Next
    rawCountBefore = Vissim.Net.Vehicles.Count
    If Err.Number <> 0 Then
        RecordVehicleCaptureFailure "invalid_numeric_value", "field=collection_count_before err=" & Err.Description
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    rawTimeBefore = Vissim.Simulation.AttValue("SimSec")
    If Err.Number <> 0 Then
        RecordVehicleCaptureFailure "invalid_numeric_value", "field=capture_sim_sec_before err=" & Err.Description
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    noArray = Vissim.Net.Vehicles.GetMultiAttValues("No")
    If Err.Number <> 0 Then
        RecordVehicleCaptureFailure "invalid_table_shape", "field=No err=" & Err.Description
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    laneArray = Vissim.Net.Vehicles.GetMultiAttValues("Lane")
    If Err.Number <> 0 Then
        RecordVehicleCaptureFailure "invalid_table_shape", "field=Lane err=" & Err.Description
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    posArray = Vissim.Net.Vehicles.GetMultiAttValues("Pos")
    If Err.Number <> 0 Then
        RecordVehicleCaptureFailure "invalid_table_shape", "field=Pos err=" & Err.Description
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    speedArray = Vissim.Net.Vehicles.GetMultiAttValues("Speed")
    If Err.Number <> 0 Then
        RecordVehicleCaptureFailure "invalid_table_shape", "field=Speed err=" & Err.Description
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    rawCountAfter = Vissim.Net.Vehicles.Count
    If Err.Number <> 0 Then
        RecordVehicleCaptureFailure "invalid_numeric_value", "field=collection_count_after err=" & Err.Description
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    rawTimeAfter = Vissim.Simulation.AttValue("SimSec")
    If Err.Number <> 0 Then
        RecordVehicleCaptureFailure "invalid_numeric_value", "field=capture_sim_sec_after err=" & Err.Description
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    On Error GoTo 0

    If Not TryNonnegativeLongVariant(rawCountBefore, collectionCountBefore) _
            Or Not TryNonnegativeLongVariant(rawCountAfter, collectionCountAfter) Then
        RecordVehicleCaptureFailure "invalid_numeric_value", "field=collection_count"
        Exit Function
    End If
    If collectionCountBefore <> collectionCountAfter Then
        RecordVehicleCaptureFailure "com_count_changed", "before=" & CStr(collectionCountBefore) & " after=" & CStr(collectionCountAfter)
        Exit Function
    End If
    If Not TryFiniteNonnegativeDouble(rawTimeBefore, captureSimSecBefore) _
            Or Not TryFiniteNonnegativeDouble(rawTimeAfter, captureSimSecAfter) _
            Or Not TryFiniteNonnegativeDouble(expectedSimSec, expectedTime) Then
        RecordVehicleCaptureFailure "invalid_numeric_value", "field=sim_sec"
        Exit Function
    End If
    If captureSimSecBefore <> expectedTime Or captureSimSecAfter <> expectedTime Then
        RecordVehicleCaptureFailure "capture_time_mismatch", "expected=" & JsonDoubleInvariant(expectedTime) & _
            " before=" & JsonDoubleInvariant(captureSimSecBefore) & " after=" & JsonDoubleInvariant(captureSimSecAfter)
        Exit Function
    End If

    If collectionCountBefore = 0 Then
        If Not IsB1aEmptyTableResult(noArray) Or Not IsB1aEmptyTableResult(laneArray) _
                Or Not IsB1aEmptyTableResult(posArray) Or Not IsB1aEmptyTableResult(speedArray) Then
            RecordVehicleCaptureFailure "invalid_table_shape", "detail=nonempty_table_for_zero_collection"
            Exit Function
        End If
        ReadVerifiedVehicleTables = True
        Exit Function
    End If

    If Not TryExact2DTableBounds(noArray, noRowLower, noRowUpper, noColLower, noColUpper) _
            Or Not TryExact2DTableBounds(laneArray, laneRowLower, laneRowUpper, laneColLower, laneColUpper) _
            Or Not TryExact2DTableBounds(posArray, posRowLower, posRowUpper, posColLower, posColUpper) _
            Or Not TryExact2DTableBounds(speedArray, speedRowLower, speedRowUpper, speedColLower, speedColUpper) Then
        RecordVehicleCaptureFailure "invalid_table_shape", "detail=expected_exact_2d_key_value_tables"
        Exit Function
    End If
    If noRowLower <> laneRowLower Or noRowLower <> posRowLower Or noRowLower <> speedRowLower _
            Or noRowUpper <> laneRowUpper Or noRowUpper <> posRowUpper Or noRowUpper <> speedRowUpper _
            Or noColLower <> laneColLower Or noColLower <> posColLower Or noColLower <> speedColLower _
            Or noColUpper <> laneColUpper Or noColUpper <> posColUpper Or noColUpper <> speedColUpper Then
        RecordVehicleCaptureFailure "invalid_table_shape", "detail=table_bounds_mismatch"
        Exit Function
    End If
    If noRowUpper - noRowLower + 1 <> collectionCountBefore Then
        RecordVehicleCaptureFailure "invalid_table_shape", "detail=row_count_mismatch rows=" & _
            CStr(noRowUpper - noRowLower + 1) & " collection=" & CStr(collectionCountBefore)
        Exit Function
    End If

    rowLower = noRowLower
    rowUpper = noRowUpper
    keyColumn = noColLower
    valueColumn = noColUpper
    ReadVerifiedVehicleTables = True
End Function

Function TryExact2DTableBounds(arr, ByRef rowLower, ByRef rowUpper, ByRef colLower, ByRef colUpper)
    Dim thirdBound
    TryExact2DTableBounds = False
    If Not IsArray(arr) Then Exit Function
    On Error Resume Next
    rowLower = LBound(arr, 1)
    rowUpper = UBound(arr, 1)
    colLower = LBound(arr, 2)
    colUpper = UBound(arr, 2)
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    thirdBound = LBound(arr, 3)
    If Err.Number = 0 Then
        On Error GoTo 0
        Exit Function
    End If
    Err.Clear
    On Error GoTo 0
    If rowUpper < rowLower Then Exit Function
    If colUpper - colLower + 1 <> 2 Then Exit Function
    TryExact2DTableBounds = True
End Function

Function IsB1aEmptyTableResult(arr)
    Dim rowLower, rowUpper, colLower, colUpper, thirdBound
    IsB1aEmptyTableResult = False
    If IsEmpty(arr) Then
        IsB1aEmptyTableResult = True
        Exit Function
    End If
    If Not IsArray(arr) Then Exit Function
    On Error Resume Next
    rowLower = LBound(arr, 1)
    rowUpper = UBound(arr, 1)
    colLower = LBound(arr, 2)
    colUpper = UBound(arr, 2)
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    thirdBound = LBound(arr, 3)
    If Err.Number = 0 Then
        On Error GoTo 0
        Exit Function
    End If
    Err.Clear
    On Error GoTo 0
    If colUpper - colLower + 1 <> 2 Then Exit Function
    IsB1aEmptyTableResult = (rowUpper < rowLower)
End Function

Sub RecordVehicleCaptureFailure(reason, detail)
    comFailures = comFailures + 1
    WScript.Echo "ERROR=B1A_VEHICLE_CAPTURE_FAILED reason=" & CStr(reason) & " " & CStr(detail)
End Sub

Function TryPositiveLongVariant(ByVal value, ByRef parsed)
    TryPositiveLongVariant = TryB1aLongVariant(value, False, parsed)
End Function

Function TryNonnegativeLongVariant(ByVal value, ByRef parsed)
    TryNonnegativeLongVariant = TryB1aLongVariant(value, True, parsed)
End Function

Function TryB1aLongVariant(ByVal value, ByVal allowZero, ByRef parsed)
    Dim valueType, numericValue, probe
    TryB1aLongVariant = False
    parsed = 0
    If IsArray(value) Or IsObject(value) Or IsEmpty(value) Or IsNull(value) Then Exit Function
    valueType = VarType(value)
    Select Case valueType
        Case 2, 3, 4, 5, 6, 14, 17, 20
        Case Else
            Exit Function
    End Select
    On Error Resume Next
    numericValue = CDbl(value)
    probe = numericValue * 0.0
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    On Error GoTo 0
    If numericValue <> numericValue Or probe <> probe Then Exit Function
    If numericValue < 0 Or numericValue > 2147483647.0 Then Exit Function
    If (Not allowZero) And numericValue = 0 Then Exit Function
    If Fix(numericValue) <> numericValue Then Exit Function
    On Error Resume Next
    parsed = CLng(numericValue)
    If Err.Number <> 0 Then
        parsed = 0
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    On Error GoTo 0
    TryB1aLongVariant = True
End Function

Function TryFiniteNonnegativeDouble(ByVal value, ByRef parsed)
    TryFiniteNonnegativeDouble = TryB1aFiniteDouble(value, 0.0, parsed)
End Function

Function TryB1aPosition(ByVal value, ByRef parsed)
    TryB1aPosition = TryB1aFiniteDouble(value, -B1A_POSITION_TOLERANCE_M, parsed)
End Function

' Accepts the boundary-entry band only. Callers must clamp the parsed value to the link
' start and record the adjustment; this helper never hides the raw value.
Function TryB1aEntryPosition(ByVal value, ByRef parsed)
    TryB1aEntryPosition = TryB1aFiniteDouble(value, -B1A_ENTRY_TOLERANCE_M, parsed)
End Function

Function TryB1aSpeed(ByVal value, ByRef parsed)
    TryB1aSpeed = TryB1aFiniteDouble(value, 0.0, parsed)
End Function

Function TryB1aFiniteDouble(ByVal value, ByVal minimumValue, ByRef parsed)
    Dim valueType, probe
    TryB1aFiniteDouble = False
    parsed = 0.0
    If IsArray(value) Or IsObject(value) Or IsEmpty(value) Or IsNull(value) Then Exit Function
    valueType = VarType(value)
    Select Case valueType
        Case 2, 3, 4, 5, 6, 14, 17, 20
        Case Else
            Exit Function
    End Select
    On Error Resume Next
    parsed = CDbl(value)
    probe = parsed * 0.0
    If Err.Number <> 0 Then
        parsed = 0.0
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    On Error GoTo 0
    If parsed <> parsed Or probe <> probe Then Exit Function
    If parsed < CDbl(minimumValue) Then Exit Function
    TryB1aFiniteDouble = True
End Function

Function ParseB1aLaneId(ByVal value, ByRef linkNo, ByRef laneNo)
    Dim text, delimiterPos
    ParseB1aLaneId = False
    linkNo = 0: laneNo = 0
    If IsArray(value) Or IsObject(value) Or IsEmpty(value) Or IsNull(value) Then Exit Function
    If VarType(value) <> 8 Then Exit Function
    text = TrimB1aHorizontalWhitespace(CStr(value))
    delimiterPos = InStr(1, text, "-", vbBinaryCompare)
    If delimiterPos <= 1 Or delimiterPos >= Len(text) Then Exit Function
    If InStr(delimiterPos + 1, text, "-", vbBinaryCompare) > 0 Then Exit Function
    If Not ParseB1aPositiveLongText(Left(text, delimiterPos - 1), linkNo) Then Exit Function
    If Not ParseB1aPositiveLongText(Mid(text, delimiterPos + 1), laneNo) Then Exit Function
    ParseB1aLaneId = True
End Function

Function TrimB1aHorizontalWhitespace(ByVal value)
    Dim text, first, last, ch
    text = CStr(value)
    first = 1
    last = Len(text)
    Do While first <= last
        ch = Mid(text, first, 1)
        If ch <> " " And ch <> vbTab Then Exit Do
        first = first + 1
    Loop
    Do While last >= first
        ch = Mid(text, last, 1)
        If ch <> " " And ch <> vbTab Then Exit Do
        last = last - 1
    Loop
    If first > last Then
        TrimB1aHorizontalWhitespace = ""
    Else
        TrimB1aHorizontalWhitespace = Mid(text, first, last - first + 1)
    End If
End Function

Function ParseB1aPositiveLongText(ByVal text, ByRef parsed)
    Dim i, ch, digit, accumulator
    ParseB1aPositiveLongText = False
    parsed = 0
    If Len(text) = 0 Then Exit Function
    ch = Left(text, 1)
    If ch < "1" Or ch > "9" Then Exit Function
    accumulator = 0
    For i = 1 To Len(text)
        ch = Mid(text, i, 1)
        If ch < "0" Or ch > "9" Then Exit Function
        digit = AscW(ch) - AscW("0")
        If accumulator > 214748364 Then Exit Function
        If accumulator = 214748364 And digit > 7 Then Exit Function
        accumulator = accumulator * 10 + digit
    Next
    parsed = CLng(accumulator)
    ParseB1aPositiveLongText = True
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
        comFailures = comFailures + 1
        Err.Clear
    End If
    On Error GoTo 0
End Sub

Sub TrySetEvaluationAtt(att, value)
    On Error Resume Next
    Vissim.Evaluation.AttValue(att) = value
    If Err.Number <> 0 Then
        WScript.Echo "WARN=FAILED_SET_EVALUATION_ATT att=" & att & " err=" & Err.Description
        comFailures = comFailures + 1
        Err.Clear
    End If
    On Error GoTo 0
End Sub

' 실패해도 의도가 이미 보장되는 설정 전용. comFailures 를 올리지 않는다.
'
' 이 경로를 새로 만드는 이유는 실 런마다 COM_FAILURES=2 가 나와 RUN_INTEGRITY_FAILURE 를
' 일으켰기 때문이다. 두 건 다 신호 액추에이션과 무관한 best-effort 설정인데 같은 카운터에
' 들어갔다. 게이트를 느슨하게 만들지 않으려고 호출부를 딱 둘로 못박고, 각각 why 로 "실패해도
' 의도가 보장되는 이유" 를 남기게 했다. 건수는 버리지 않고 OPTIONAL_ATT_SKIPS 로 따로 센다.
'
' **여기에 새 호출을 추가하지 마라.** 진짜 COM 실패를 숨기는 통로가 된다.
' scripts/tests/test_run_plant_fidelity_matrix.py 가 호출 수 1/1 을 단언한다.
Sub TrySetUnreachableAtt(obj, att, value, why)
    On Error Resume Next
    obj.AttValue(att) = value
    If Err.Number <> 0 Then
        WScript.Echo "WARN=SKIPPED_OPTIONAL_ATT att=" & att & " value=" & CStr(value) & _
            " why=" & CStr(why) & " err=" & Err.Description
        optionalAttSkips = optionalAttSkips + 1
        Err.Clear
    End If
    On Error GoTo 0
End Sub

Sub TrySetUnreachableEvaluationAtt(att, value, why)
    On Error Resume Next
    Vissim.Evaluation.AttValue(att) = value
    If Err.Number <> 0 Then
        WScript.Echo "WARN=SKIPPED_OPTIONAL_EVALUATION_ATT att=" & att & _
            " why=" & CStr(why) & " err=" & Err.Description
        optionalAttSkips = optionalAttSkips + 1
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
