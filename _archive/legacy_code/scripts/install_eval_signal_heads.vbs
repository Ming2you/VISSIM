Option Explicit

If WScript.Arguments.Count < 5 Then
    WScript.Echo "Usage: cscript install_eval_signal_heads.vbs <source.inpx> <source.layx> <target.inpx> <target.layx> <manifest.csv>"
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
manifest.WriteLine "object_type,category,name,sc_no,sg_no,link,lane,pos,purpose"

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

WScript.Echo "COUNTS_BEFORE SC=" & Vissim.Net.SignalControllers.Count & " SH=" & Vissim.Net.SignalHeads.Count

AddIntersectionSignalGroupsAndHeads
AddRampMeterSignalGroupsAndHeads
DisableSignalControllersUntilTimingConfigured

WScript.Echo "COUNTS_AFTER_IN_MEMORY SC=" & Vissim.Net.SignalControllers.Count & " SH=" & Vissim.Net.SignalHeads.Count

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

Sub AddIntersectionSignalGroupsAndHeads()
    AddTwoPhaseIntersection "A", 1, Array(1, 6), Array(3, 8)
    AddTwoPhaseIntersection "B", 2, Array(5, 12), Array(9, 14)
    AddTwoPhaseIntersection "C", 3, Array(11, 18), Array(15, 20)
    AddTwoPhaseIntersection "D", 4, Array(21, 24), Array(7, 26)
    AddTwoPhaseIntersection "F", 5, Array(27, 30), Array(19, 32)
End Sub

Sub AddTwoPhaseIntersection(nodeName, scNo, majorLinks, minorLinks)
    AddSignalGroup scNo, 1, "SG_" & nodeName & "_MAJOR"
    AddSignalGroup scNo, 2, "SG_" & nodeName & "_MINOR"
    AddSignalHeadsForLinks "intersection_major", nodeName, scNo, 1, majorLinks, 10, "Major-axis stop-line signal head"
    AddSignalHeadsForLinks "intersection_minor", nodeName, scNo, 2, minorLinks, 10, "Minor/ramp-axis stop-line signal head"
End Sub

Sub AddRampMeterSignalGroupsAndHeads()
    AddSignalGroup 6, 1, "SG_RM_D"
    AddSignalHeadsForLinks "ramp_meter", "RM_D", 6, 1, Array(25), 30, "D on-ramp metering signal head"
    AddSignalGroup 7, 1, "SG_RM_F"
    AddSignalHeadsForLinks "ramp_meter", "RM_F", 7, 1, Array(31), 30, "F on-ramp metering signal head"
End Sub

Sub DisableSignalControllersUntilTimingConfigured()
    Dim no, sc
    For no = 1 To 7
        Set sc = Vissim.Net.SignalControllers.ItemByKey(CLng(no))
        TrySetAtt sc, "Active", False
        WriteManifest "signalController", "disabled_pending_timing", SafeAtt(sc, "Name"), no, "", "", "", "", "Installed signal heads are disabled until fixed-time/controller timing is configured"
    Next
End Sub

Sub AddSignalGroup(scNo, sgNo, name)
    Dim sc, sg
    Set sc = Vissim.Net.SignalControllers.ItemByKey(CLng(scNo))
    On Error Resume Next
    Set sg = sc.SGs.AddSignalGroup(CLng(sgNo))
    If Err.Number <> 0 Then
        WScript.Echo "WARN=FAILED_ADD_SG sc=" & scNo & " sg=" & sgNo & " err=" & Err.Description
        Err.Clear
        On Error GoTo 0
        Exit Sub
    End If
    On Error GoTo 0
    SetName sg, name
    WriteManifest "signalGroup", "signal_group", name, scNo, sgNo, "", "", "", "Signal group for later fixed-time/adaptive control"
End Sub

Sub AddSignalHeadsForLinks(category, label, scNo, sgNo, linkNos, distanceFromEnd, purpose)
    Dim linkNo, link, pos, laneNo, lane, sh, name
    For Each linkNo In linkNos
        Set link = Vissim.Net.Links.ItemByKey(CLng(linkNo))
        pos = ClampPos(CDbl(link.AttValue("Length2D")) - CDbl(distanceFromEnd), link)
        For laneNo = 1 To link.Lanes.Count
            Set lane = link.Lanes.ItemByKey(CLng(laneNo))
            Set sh = Vissim.Net.SignalHeads.AddSignalHead(0, lane, CDbl(pos))
            name = "EVAL_SH_" & label & "_L" & CStr(linkNo) & "_LN" & CStr(laneNo)
            SetName sh, name
            TrySetAtt sh, "SG", CStr(scNo) & "-" & CStr(sgNo)
            TrySetAtt sh, "Type", "CIRCULAR"
            WriteManifest "signalHead", category, name, scNo, sgNo, linkNo, laneNo, Round3(pos), purpose
        Next
    Next
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

Sub WriteManifest(objectType, category, name, scNo, sgNo, linkNo, laneNo, pos, purpose)
    manifest.WriteLine Csv(objectType) & "," & Csv(category) & "," & Csv(name) & "," & Csv(scNo) & "," & Csv(sgNo) & "," & Csv(linkNo) & "," & Csv(laneNo) & "," & Csv(pos) & "," & Csv(purpose)
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
