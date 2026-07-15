Option Explicit

If WScript.Arguments.Count < 5 Then
    WScript.Echo "Usage: cscript install_eval_vsl.vbs <source.inpx> <source.layx> <target.inpx> <target.layx> <manifest.csv>"
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
manifest.WriteLine "object_type,category,name,no,link,lane,pos,section,default_speed_kph,veh_classes,purpose"

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

InstallMainlineVsl

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

Sub InstallMainlineVsl()
    ' Mainline length is about 2900 m in both directions.
    ' Station locations mirror the existing DCP bottleneck positions:
    ' EB: around the D and F merge/diverge areas while travelling west -> east.
    ' WB: around the F and D merge/diverge areas while travelling east -> west.
    AddVslStation "EB_PRE_D", 33, 430, "EB upstream of D ramp area"
    AddVslStation "EB_D_BOT", 33, 880, "EB D ramp bottleneck control point"
    AddVslStation "EB_PRE_F", 33, 1680, "EB upstream of F ramp area"
    AddVslStation "EB_F_BOT", 33, 2070, "EB F ramp bottleneck control point"

    AddVslStation "WB_PRE_F", 34, 430, "WB upstream of F ramp area"
    AddVslStation "WB_F_BOT", 34, 1200, "WB F ramp bottleneck control point"
    AddVslStation "WB_PRE_D", 34, 1680, "WB upstream of D ramp area"
    AddVslStation "WB_D_BOT", 34, 2430, "WB D ramp bottleneck control point"
End Sub

Sub AddVslStation(section, linkNo, pos, purpose)
    Dim link, laneNo, lane, dsd, name, dsdNo, defaultSpeed
    defaultSpeed = 120
    Set link = Vissim.Net.Links.ItemByKey(CLng(linkNo))
    pos = ClampPos(CDbl(pos), link)

    For laneNo = 1 To link.Lanes.Count
        Set lane = link.Lanes.ItemByKey(CLng(laneNo))
        On Error Resume Next
        Set dsd = Vissim.Net.DesSpeedDecisions.AddDesSpeedDecision(0, lane, CDbl(pos))
        If Err.Number <> 0 Then
            WScript.Echo "WARN=FAILED_ADD_DSD section=" & section & " link=" & linkNo & " lane=" & laneNo & " pos=" & pos & " err=" & Err.Description
            Err.Clear
            On Error GoTo 0
        Else
            On Error GoTo 0
            name = "EVAL_VSL_" & section & "_L" & CStr(linkNo) & "_LN" & CStr(laneNo)
            SetName dsd, name
            SetClassSpeed dsd, 10, defaultSpeed
            SetClassSpeed dsd, 20, defaultSpeed
            SetClassSpeed dsd, 30, defaultSpeed
            dsdNo = SafeAtt(dsd, "No")
            WriteManifest "desSpeedDecision", "mainline_vsl", name, dsdNo, linkNo, laneNo, Round3(pos), section, defaultSpeed, "10;20;30", purpose
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

Sub WriteManifest(objectType, category, name, no, linkNo, laneNo, pos, section, defaultSpeed, vehClasses, purpose)
    manifest.WriteLine Csv(objectType) & "," & Csv(category) & "," & Csv(name) & "," & Csv(no) & "," & Csv(linkNo) & "," & Csv(laneNo) & "," & Csv(pos) & "," & Csv(section) & "," & Csv(defaultSpeed) & "," & Csv(vehClasses) & "," & Csv(purpose)
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
