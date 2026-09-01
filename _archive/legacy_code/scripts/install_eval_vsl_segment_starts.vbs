Option Explicit

If WScript.Arguments.Count < 5 Then
    WScript.Echo "Usage: cscript install_eval_vsl_segment_starts.vbs <source.inpx> <source.layx> <target.inpx> <target.layx> <manifest.csv>"
    WScript.Quit 2
End If

Dim sourceNet, sourceLayout, targetNet, targetLayout, manifestPath
sourceNet = WScript.Arguments(0)
sourceLayout = WScript.Arguments(1)
targetNet = WScript.Arguments(2)
targetLayout = WScript.Arguments(3)
manifestPath = WScript.Arguments(4)

Dim fso, manifest, Vissim
Set fso = CreateObject("Scripting.FileSystemObject")
EnsureParentFolder manifestPath
Set manifest = fso.CreateTextFile(manifestPath, True)
manifest.WriteLine "object_type,category,segment_id,direction,name,no,link,lane,pos,segment_start_m,segment_end_m,default_speed_kph,veh_classes,purpose"

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

WScript.Echo "COUNTS_BEFORE DSD=" & Vissim.Net.DesSpeedDecisions.Count

InstallSegmentStartVsl

WScript.Echo "COUNTS_AFTER_IN_MEMORY DSD=" & Vissim.Net.DesSpeedDecisions.Count

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

Sub InstallSegmentStartVsl()
    ' Segment boundaries are taken from the ramp connector endpoints on the freeway mainline.
    ' EB link 33 runs west -> east.
    AddVslSegmentStart "EB_S0_W_ENTRY_TO_D_DIVERGE", "EB", 33, 1.0, 499.0317957686363, "Start of EB entry/upstream segment before D off-ramp diverge"
    AddVslSegmentStart "EB_S1_D_DIVERGE_TO_D_MERGE", "EB", 33, 499.0317957686363, 812.3914617342674, "Start of EB D weave/ramp influence segment"
    AddVslSegmentStart "EB_S2_D_MERGE_TO_F_DIVERGE", "EB", 33, 812.3914617342674, 1735.614696463941, "Start of EB mid-mainline segment between D and F"
    AddVslSegmentStart "EB_S3_F_DIVERGE_TO_F_MERGE", "EB", 33, 1735.614696463941, 2029.1497729629073, "Start of EB F weave/ramp influence segment"
    AddVslSegmentStart "EB_S4_F_MERGE_TO_E_EXIT", "EB", 33, 2029.1497729629073, 2900.003, "Start of EB downstream segment after F on-ramp merge"

    ' WB link 34 runs east -> west.
    AddVslSegmentStart "WB_S0_E_ENTRY_TO_F_DIVERGE", "WB", 34, 1.0, 537.7388621546322, "Start of WB entry/upstream segment before F off-ramp diverge"
    AddVslSegmentStart "WB_S1_F_DIVERGE_TO_F_MERGE", "WB", 34, 537.7388621546322, 1155.2495503139976, "Start of WB F weave/ramp influence segment"
    AddVslSegmentStart "WB_S2_F_MERGE_TO_D_DIVERGE", "WB", 34, 1155.2495503139976, 1743.4595824891098, "Start of WB mid-mainline segment between F and D"
    AddVslSegmentStart "WB_S3_D_DIVERGE_TO_D_MERGE", "WB", 34, 1743.4595824891098, 2398.244756343526, "Start of WB D weave/ramp influence segment"
    AddVslSegmentStart "WB_S4_D_MERGE_TO_W_EXIT", "WB", 34, 2398.244756343526, 2900.003, "Start of WB downstream segment after D on-ramp merge"
End Sub

Sub AddVslSegmentStart(segmentId, direction, linkNo, startPos, endPos, purpose)
    Dim link, laneNo, lane, dsd, name, dsdNo, defaultSpeed, pos
    defaultSpeed = 120
    Set link = Vissim.Net.Links.ItemByKey(CLng(linkNo))
    pos = ClampPos(CDbl(startPos), link)

    For laneNo = 1 To link.Lanes.Count
        Set lane = link.Lanes.ItemByKey(CLng(laneNo))
        On Error Resume Next
        Set dsd = Vissim.Net.DesSpeedDecisions.AddDesSpeedDecision(0, lane, CDbl(pos))
        If Err.Number <> 0 Then
            WScript.Echo "WARN=FAILED_ADD_DSD segment=" & segmentId & " link=" & linkNo & " lane=" & laneNo & " pos=" & pos & " err=" & Err.Description
            Err.Clear
            On Error GoTo 0
        Else
            On Error GoTo 0
            name = "EVAL_VSL_SEG_" & segmentId & "_L" & CStr(linkNo) & "_LN" & CStr(laneNo)
            SetName dsd, name
            SetClassSpeed dsd, 10, defaultSpeed
            SetClassSpeed dsd, 20, defaultSpeed
            SetClassSpeed dsd, 30, defaultSpeed
            dsdNo = SafeAtt(dsd, "No")
            WriteManifest "desSpeedDecision", "segment_start_vsl", segmentId, direction, name, dsdNo, linkNo, laneNo, Round3(pos), Round3(startPos), Round3(endPos), defaultSpeed, "10;20;30", purpose
        End If
    Next
End Sub

Sub SetClassSpeed(dsd, vehClassNo, speedKph)
    TrySetAtt dsd, "DesSpeedDistr(" & CStr(vehClassNo) & ")", CLng(speedKph)
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

Function SafeAtt(obj, att)
    On Error Resume Next
    SafeAtt = CStr(obj.AttValue(att))
    If Err.Number <> 0 Then
        SafeAtt = ""
        Err.Clear
    End If
    On Error GoTo 0
End Function

Sub WriteManifest(objectType, category, segmentId, direction, name, no, linkNo, laneNo, pos, startPos, endPos, defaultSpeed, vehClasses, purpose)
    manifest.WriteLine Csv(objectType) & "," & Csv(category) & "," & Csv(segmentId) & "," & Csv(direction) & "," & Csv(name) & "," & Csv(no) & "," & Csv(linkNo) & "," & Csv(laneNo) & "," & Csv(pos) & "," & Csv(startPos) & "," & Csv(endPos) & "," & Csv(defaultSpeed) & "," & Csv(vehClasses) & "," & Csv(purpose)
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
