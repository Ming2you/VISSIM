Option Explicit

If WScript.Arguments.Count < 5 Then
    WScript.Echo "Usage: cscript install_eval_detectors.vbs <source.inpx> <source.layx> <target.inpx> <target.layx> <manifest.csv>"
    WScript.Quit 2
End If

Dim sourceNet, sourceLayout, targetNet, targetLayout, manifestPath
sourceNet = WScript.Arguments(0)
sourceLayout = WScript.Arguments(1)
targetNet = WScript.Arguments(2)
targetLayout = WScript.Arguments(3)
manifestPath = WScript.Arguments(4)

Dim fso, manifest, Vissim, portNo
Set fso = CreateObject("Scripting.FileSystemObject")
EnsureParentFolder manifestPath
Set manifest = fso.CreateTextFile(manifestPath, True)
manifest.WriteLine "object_type,category,name,sc_no,link,lane,pos,length,port_no,purpose"
portNo = 1000

Set Vissim = CreateObject("Vissim.Vissim")
WScript.Echo "STAGE=COM_CREATED"

Vissim.LoadNet sourceNet, False
WScript.Echo "STAGE=SOURCE_NET_LOADED"

On Error Resume Next
Vissim.LoadLayout sourceLayout
If Err.Number <> 0 Then
    WScript.Echo "WARN=SOURCE_LAYOUT_LOAD_FAILED err=" & Err.Description
    Err.Clear
Else
    WScript.Echo "STAGE=SOURCE_LAYOUT_LOADED"
End If
On Error GoTo 0

On Error Resume Next
Vissim.Graphics.CurrentNetworkWindow.AttValue("QuickMode") = 1
Vissim.SuspendUpdateGUI
Err.Clear
On Error GoTo 0

WScript.Echo "COUNTS_BEFORE LINKS=" & Vissim.Net.Links.Count & " DCP=" & Vissim.Net.DataCollectionPoints.Count & " QC=" & Vissim.Net.QueueCounters.Count & " SC=" & Vissim.Net.SignalControllers.Count & " DET=" & Vissim.Net.Detectors.Count

AddPlaceholderSignalControllers
AddApproachDetectors
AddRampMeterAndRampDetectors
AddFreewayMainlineDetectors
AddRampDataCollectionPoints
AddBottleneckDataCollectionPoints
AddSupplementalQueueCounters

WScript.Echo "COUNTS_AFTER_IN_MEMORY LINKS=" & Vissim.Net.Links.Count & " DCP=" & Vissim.Net.DataCollectionPoints.Count & " QC=" & Vissim.Net.QueueCounters.Count & " SC=" & Vissim.Net.SignalControllers.Count & " DET=" & Vissim.Net.Detectors.Count

EnsureParentFolder targetNet
EnsureParentFolder targetLayout
Vissim.SaveNetAs targetNet
Vissim.SaveLayout targetLayout
manifest.Close

On Error Resume Next
Vissim.ResumeUpdateGUI True
Err.Clear
On Error GoTo 0

WScript.Echo "STAGE=SAVED"
WScript.Echo "TARGET_NET=" & targetNet
WScript.Echo "TARGET_LAYOUT=" & targetLayout
WScript.Echo "MANIFEST=" & manifestPath

Set Vissim = Nothing
WScript.Quit 0

Sub AddPlaceholderSignalControllers()
    AddSignalController 1, "EVAL_SC_A"
    AddSignalController 2, "EVAL_SC_B"
    AddSignalController 3, "EVAL_SC_C"
    AddSignalController 4, "EVAL_SC_D"
    AddSignalController 5, "EVAL_SC_F"
    AddSignalController 6, "EVAL_SC_RM_D"
    AddSignalController 7, "EVAL_SC_RM_F"
    AddSignalController 8, "EVAL_SC_VSL_EB"
    AddSignalController 9, "EVAL_SC_VSL_WB"
End Sub

Sub AddSignalController(no, name)
    Dim sc
    Set sc = Vissim.Net.SignalControllers.AddSignalController(no)
    SetName sc, name
    WriteManifest "signalController", "placeholder", name, no, "", "", "", "", "", "Placeholder SC required by Vissim Detector objects; signal heads/control logic are added later"
End Sub

Sub AddApproachDetectors()
    AddIntersectionApproach "A", 1, Array(1, 3, 6, 8)
    AddIntersectionApproach "B", 2, Array(5, 9, 12, 14)
    AddIntersectionApproach "C", 3, Array(11, 15, 18, 20)
    AddIntersectionApproach "D", 4, Array(7, 21, 24, 26)
    AddIntersectionApproach "F", 5, Array(19, 27, 30, 32)
End Sub

Sub AddIntersectionApproach(nodeName, scNo, linkNos)
    Dim linkNo, link, stopPos, advPos
    For Each linkNo In linkNos
        Set link = Vissim.Net.Links.ItemByKey(CLng(linkNo))
        stopPos = ClampPos(link.AttValue("Length2D") - 18, link)
        advPos = ClampPos(link.AttValue("Length2D") - 120, link)
        AddDetectorAllLanes scNo, "EVAL_DET_" & nodeName & "_L" & CStr(linkNo) & "_STOP", linkNo, stopPos, 8, "approach_stopline", "Stop-line presence detector for future signal actuation"
        AddDetectorAllLanes scNo, "EVAL_DET_" & nodeName & "_L" & CStr(linkNo) & "_ADV", linkNo, advPos, 8, "approach_advance", "Advance detector for arrivals/actuated signal logic"
    Next
End Sub

Sub AddRampMeterAndRampDetectors()
    AddOnRampMeterDetectorSet "D", 6, 25
    AddOnRampMeterDetectorSet "F", 7, 31
    AddOffRampDetectorSet "D", 4, 26
    AddOffRampDetectorSet "F", 5, 32
End Sub

Sub AddOnRampMeterDetectorSet(siteName, scNo, linkNo)
    Dim link, length
    Set link = Vissim.Net.Links.ItemByKey(CLng(linkNo))
    length = CDbl(link.AttValue("Length2D"))
    AddDetectorAllLanes scNo, "EVAL_DET_RM_" & siteName & "_QUEUE", linkNo, ClampPos(length * 0.25, link), 20, "ramp_meter_queue", "Ramp queue detector for queue override"
    AddDetectorAllLanes scNo, "EVAL_DET_RM_" & siteName & "_PRES", linkNo, ClampPos(length - 35, link), 8, "ramp_meter_presence", "Ramp meter stop-line presence detector"
    AddDetectorAllLanes scNo, "EVAL_DET_RM_" & siteName & "_PASS", linkNo, ClampPos(length - 15, link), 4, "ramp_meter_passage", "Ramp meter passage/release detector"
End Sub

Sub AddOffRampDetectorSet(siteName, scNo, linkNo)
    Dim link
    Set link = Vissim.Net.Links.ItemByKey(CLng(linkNo))
    AddDetectorAllLanes scNo, "EVAL_DET_OFF_" & siteName & "_ENTRY", linkNo, ClampPos(35, link), 8, "offramp_entry", "Off-ramp arrival detector from freeway"
End Sub

Sub AddFreewayMainlineDetectors()
    AddFreewayDetectorSet "EB", 8, 33, Array(430, 880, 1450, 1680, 2070, 2450)
    AddFreewayDetectorSet "WB", 9, 34, Array(430, 1200, 1450, 1680, 2430, 2600)
End Sub

Sub AddFreewayDetectorSet(directionName, scNo, linkNo, positions)
    Dim pos
    For Each pos In positions
        AddDetectorAllLanes scNo, "EVAL_DET_VSL_" & directionName & "_" & CStr(pos), linkNo, CDbl(pos), 10, "freeway_vsl_mainline", "Mainline detector for VSL/ramp-metering feedback"
    Next
End Sub

Sub AddRampDataCollectionPoints()
    AddDcpFractions "EVAL_DCP_RAMP_D_ON", 25, Array(0.25, 0.5, 0.75), "ramp_flow_speed", "Ramp flow/speed data collection on D on-ramp"
    AddDcpFractions "EVAL_DCP_RAMP_D_OFF", 26, Array(0.25, 0.5, 0.75), "ramp_flow_speed", "Ramp flow/speed data collection on D off-ramp"
    AddDcpFractions "EVAL_DCP_RAMP_F_ON", 31, Array(0.25, 0.5, 0.75), "ramp_flow_speed", "Ramp flow/speed data collection on F on-ramp"
    AddDcpFractions "EVAL_DCP_RAMP_F_OFF", 32, Array(0.25, 0.5, 0.75), "ramp_flow_speed", "Ramp flow/speed data collection on F off-ramp"
End Sub

Sub AddBottleneckDataCollectionPoints()
    AddDcpPositions "EVAL_DCP_FW_E_BOT", 33, Array(430, 880, 1680, 2070), "freeway_bottleneck_flow_speed", "Freeway bottleneck data collection around D/F merge-diverge areas"
    AddDcpPositions "EVAL_DCP_FW_W_BOT", 34, Array(430, 1200, 1680, 2430), "freeway_bottleneck_flow_speed", "Freeway bottleneck data collection around D/F merge-diverge areas"
End Sub

Sub AddSupplementalQueueCounters()
    AddQueueCounterAtEnd "EVAL_QC_RM_D_ON", 25, 20, "ramp_meter_queue", "D on-ramp queue counter for metering queue override"
    AddQueueCounterAtEnd "EVAL_QC_RM_F_ON", 31, 20, "ramp_meter_queue", "F on-ramp queue counter for metering queue override"
    AddQueueCounterAtPos "EVAL_QC_FW_E_D", 33, 880, "freeway_queue", "EB freeway queue/spillback around D merge-diverge"
    AddQueueCounterAtPos "EVAL_QC_FW_E_F", 33, 2070, "freeway_queue", "EB freeway queue/spillback around F merge-diverge"
    AddQueueCounterAtPos "EVAL_QC_FW_W_F", 34, 1200, "freeway_queue", "WB freeway queue/spillback around F merge-diverge"
    AddQueueCounterAtPos "EVAL_QC_FW_W_D", 34, 2430, "freeway_queue", "WB freeway queue/spillback around D merge-diverge"
End Sub

Sub AddDetectorAllLanes(scNo, prefix, linkNo, pos, detLength, category, purpose)
    Dim link, laneNo, lane, det, name
    Set link = Vissim.Net.Links.ItemByKey(CLng(linkNo))
    pos = ClampPos(pos, link)
    For laneNo = 1 To link.Lanes.Count
        Set lane = link.Lanes.ItemByKey(laneNo)
        Set det = Vissim.Net.Detectors.AddDetector(0, lane, CDbl(pos))
        name = prefix & "_L" & CStr(laneNo)
        SetName det, name
        TrySetAtt det, "SC", CLng(scNo)
        TrySetAtt det, "Length", CDbl(detLength)
        TrySetAtt det, "PortNo", CLng(portNo)
        WriteManifest "detector", category, name, scNo, linkNo, laneNo, Round3(pos), detLength, portNo, purpose
        portNo = portNo + 1
    Next
End Sub

Sub AddDcpFractions(prefix, linkNo, fractions, category, purpose)
    Dim link, frac, pos
    Set link = Vissim.Net.Links.ItemByKey(CLng(linkNo))
    For Each frac In fractions
        pos = ClampPos(CDbl(link.AttValue("Length2D")) * CDbl(frac), link)
        AddDcpAllLanes prefix & "_P" & CStr(CInt(CDbl(frac) * 100)), linkNo, pos, category, purpose
    Next
End Sub

Sub AddDcpPositions(prefix, linkNo, positions, category, purpose)
    Dim pos
    For Each pos In positions
        AddDcpAllLanes prefix & "_" & CStr(pos), linkNo, CDbl(pos), category, purpose
    Next
End Sub

Sub AddDcpAllLanes(prefix, linkNo, pos, category, purpose)
    Dim link, laneNo, lane, dp, name
    Set link = Vissim.Net.Links.ItemByKey(CLng(linkNo))
    pos = ClampPos(pos, link)
    For laneNo = 1 To link.Lanes.Count
        Set lane = link.Lanes.ItemByKey(laneNo)
        Set dp = Vissim.Net.DataCollectionPoints.AddDataCollectionPoint(0, lane, CDbl(pos))
        name = prefix & "_L" & CStr(laneNo)
        SetName dp, name
        WriteManifest "dataCollectionPoint", category, name, "", linkNo, laneNo, Round3(pos), "", "", purpose
    Next
End Sub

Sub AddQueueCounterAtEnd(name, linkNo, distanceFromEnd, category, purpose)
    Dim link, pos
    Set link = Vissim.Net.Links.ItemByKey(CLng(linkNo))
    pos = ClampPos(CDbl(link.AttValue("Length2D")) - CDbl(distanceFromEnd), link)
    AddQueueCounterAtPos name, linkNo, pos, category, purpose
End Sub

Sub AddQueueCounterAtPos(name, linkNo, pos, category, purpose)
    Dim link, qc
    Set link = Vissim.Net.Links.ItemByKey(CLng(linkNo))
    pos = ClampPos(pos, link)
    Set qc = Vissim.Net.QueueCounters.AddQueueCounter(0, link, CDbl(pos))
    SetName qc, name
    WriteManifest "queueCounter", category, name, "", linkNo, "", Round3(pos), "", "", purpose
End Sub

Function ClampPos(pos, link)
    Dim length
    length = CDbl(link.AttValue("Length2D"))
    If CDbl(pos) < 1 Then
        ClampPos = 1
    ElseIf CDbl(pos) > length - 1 Then
        ClampPos = length - 1
    Else
        ClampPos = CDbl(pos)
    End If
End Function

Sub SetName(obj, name)
    On Error Resume Next
    obj.AttValue("Name") = name
    If Err.Number <> 0 Then
        WScript.Echo "WARN=FAILED_SET_NAME name=" & name & " err=" & Err.Description
        Err.Clear
    End If
    On Error GoTo 0
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

Sub WriteManifest(objectType, category, name, scNo, linkNo, laneNo, pos, objLength, objPortNo, purpose)
    manifest.WriteLine Csv(objectType) & "," & Csv(category) & "," & Csv(name) & "," & Csv(scNo) & "," & Csv(linkNo) & "," & Csv(laneNo) & "," & Csv(pos) & "," & Csv(objLength) & "," & Csv(objPortNo) & "," & Csv(purpose)
End Sub

Function Csv(value)
    Dim text
    text = CStr(value)
    text = Replace(text, """", """""")
    Csv = """" & text & """"
End Function

Function Round3(value)
    Round3 = Replace(FormatNumber(CDbl(value), 3, -1, 0, 0), ",", "")
End Function

Sub EnsureParentFolder(path)
    Dim parent
    parent = fso.GetParentFolderName(path)
    If parent <> "" And Not fso.FolderExists(parent) Then
        EnsureParentFolder parent
        fso.CreateFolder parent
    End If
End Sub
