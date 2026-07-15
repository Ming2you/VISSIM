Option Explicit

If WScript.Arguments.Count < 1 Then
    WScript.Echo "Usage: cscript probe_desired_speed_api.vbs <network.inpx>"
    WScript.Quit 2
End If

Dim netPath, Vissim
netPath = WScript.Arguments(0)

Set Vissim = CreateObject("Vissim.Vissim")
WScript.Echo "STAGE=COM_CREATED"
Vissim.LoadNet netPath, False
WScript.Echo "STAGE=NET_LOADED"
WScript.Echo "VERSION=" & SafeAtt(Vissim, "ExeVersion")

On Error Resume Next
Vissim.Graphics.CurrentNetworkWindow.AttValue("QuickMode") = 1
Vissim.SuspendUpdateGUI
Err.Clear
On Error GoTo 0

ProbeCollections
ProbeAddMethods
ProbeSpeedDistAccess

If WScript.Arguments.Count >= 2 Then
    WScript.Echo "STAGE=SAVE_PROBE_COPY"
    Vissim.SaveNetAs WScript.Arguments(1)
    WScript.Echo "PROBE_COPY=" & WScript.Arguments(1)
End If

On Error Resume Next
Vissim.ResumeUpdateGUI True
Err.Clear
On Error GoTo 0

Set Vissim = Nothing
WScript.Quit 0

Sub ProbeCollections()
    Dim names, n, col
    names = Array( _
        "DesiredSpeedDecisions", _
        "DesSpeedDecisions", _
        "DesiredSpeedDecision", _
        "DesSpeedDecision" _
    )
    For Each n In names
        On Error Resume Next
        Set col = Eval("Vissim.Net." & n)
        If Err.Number = 0 Then
            WScript.Echo "COLLECTION_OK=" & n & " COUNT=" & CStr(SafeCount(col))
        Else
            WScript.Echo "COLLECTION_FAIL=" & n & " ERR=" & Err.Description
            Err.Clear
        End If
        On Error GoTo 0
    Next
End Sub

Sub ProbeAddMethods()
    Dim col, link, lane, dsd, method
    Set link = Vissim.Net.Links.ItemByKey(33)
    Set lane = link.Lanes.ItemByKey(1)

    On Error Resume Next
    Set col = Vissim.Net.DesSpeedDecisions
    If Err.Number <> 0 Then
        WScript.Echo "SKIP_ADD no DesSpeedDecisions collection"
        Err.Clear
        On Error GoTo 0
        Exit Sub
    End If
    On Error GoTo 0

    Dim methods
    methods = Array( _
        "AddDesiredSpeedDecision(0, link, 100)", _
        "AddDesiredSpeedDecision(0, lane, 100)", _
        "AddDesSpeedDecision(0, link, 110)", _
        "AddDesSpeedDecision(0, lane, 110)", _
        "Add(0, link, 120)", _
        "Add(0, lane, 120)" _
    )

    For Each method In methods
        On Error Resume Next
        Set dsd = Nothing
        Select Case method
            Case "AddDesiredSpeedDecision(0, link, 100)"
                Set dsd = col.AddDesiredSpeedDecision(0, link, CDbl(100))
            Case "AddDesiredSpeedDecision(0, lane, 100)"
                Set dsd = col.AddDesiredSpeedDecision(0, lane, CDbl(100))
            Case "AddDesSpeedDecision(0, link, 110)"
                Set dsd = col.AddDesSpeedDecision(0, link, CDbl(110))
            Case "AddDesSpeedDecision(0, lane, 110)"
                Set dsd = col.AddDesSpeedDecision(0, lane, CDbl(110))
            Case "Add(0, link, 120)"
                Set dsd = col.Add(0, link, CDbl(120))
            Case "Add(0, lane, 120)"
                Set dsd = col.Add(0, lane, CDbl(120))
        End Select

        If Err.Number <> 0 Then
            WScript.Echo "ADD_FAIL=" & method & " ERR=" & Err.Description
            Err.Clear
        ElseIf IsObject(dsd) Then
            WScript.Echo "ADD_OK=" & method
            ProbeDsdObject dsd
            Exit For
        Else
            WScript.Echo "ADD_NO_OBJECT=" & method
        End If
        On Error GoTo 0
    Next
End Sub

Sub ProbeDsdObject(dsd)
    Dim atts, a
    atts = Array("No", "Name", "Link", "Lane", "Pos", "DesSpeedDistr", "DesSpeedDist", "SpeedDistr", "SpeedDistribution", "VehType", "VehClass")
    For Each a In atts
        WScript.Echo "DSD_ATT " & a & "=" & SafeAtt(dsd, a)
    Next

    Dim setAtts, s
    setAtts = Array("Name", "DesSpeedDistr", "DesSpeedDist", "SpeedDistr", "SpeedDistribution")
    For Each s In setAtts
        If s = "Name" Then
            TrySetAtt dsd, s, "PROBE_DSD_VSL_EB"
        Else
            TrySetAtt dsd, s, 80
        End If
        WScript.Echo "DSD_AFTER_SET " & s & "=" & SafeAtt(dsd, s)
    Next

    ProbeDsdSubAttributes dsd
End Sub

Sub ProbeDsdSubAttributes(dsd)
    Dim names, idxs, n, i, att
    names = Array("DesSpeedDistr", "DesSpeedDist", "SpeedDistr", "SpeedDistribution")
    idxs = Array("1", "10", "20", "100", "101", "VehType(100)", "VehType(101)", "VehClass(10)", "VehClass(20)", "Car", "HGV")

    For Each n In names
        For Each i In idxs
            att = n & "(" & i & ")"
            On Error Resume Next
            dsd.AttValue(att) = 80
            If Err.Number = 0 Then
                WScript.Echo "SUBATT_SET_OK " & att & "=80 READ=" & SafeAtt(dsd, att)
                On Error GoTo 0
                Exit Sub
            Else
                WScript.Echo "SUBATT_SET_FAIL " & att & " ERR=" & Err.Description
                Err.Clear
            End If
            On Error GoTo 0
        Next
    Next
End Sub

Sub ProbeSpeedDistAccess()
    Dim names, n, col, obj
    names = Array("DesiredSpeedDistributions", "DesSpeedDistributions", "SpeedDistributions")
    For Each n In names
        On Error Resume Next
        Set col = Eval("Vissim.Net." & n)
        If Err.Number <> 0 Then
            WScript.Echo "SPEED_DIST_COLLECTION_FAIL=" & n & " ERR=" & Err.Description
            Err.Clear
        Else
            WScript.Echo "SPEED_DIST_COLLECTION_OK=" & n & " COUNT=" & CStr(SafeCount(col))
            On Error Resume Next
            Set obj = col.ItemByKey(80)
            If Err.Number = 0 Then
                WScript.Echo "SPEED_DIST_80_NAME=" & SafeAtt(obj, "Name")
            Else
                WScript.Echo "SPEED_DIST_80_FAIL=" & Err.Description
                Err.Clear
            End If
        End If
        On Error GoTo 0
    Next
End Sub

Function SafeCount(col)
    SafeCount = -1
    On Error Resume Next
    SafeCount = CLng(col.Count)
    If Err.Number <> 0 Then
        SafeCount = -1
        Err.Clear
    End If
    On Error GoTo 0
End Function

Function SafeAtt(obj, att)
    SafeAtt = ""
    On Error Resume Next
    SafeAtt = CStr(obj.AttValue(att))
    If Err.Number <> 0 Then
        SafeAtt = "<ERR " & Err.Description & ">"
        Err.Clear
    End If
    On Error GoTo 0
End Function

Sub TrySetAtt(obj, att, value)
    On Error Resume Next
    obj.AttValue(att) = value
    If Err.Number <> 0 Then
        WScript.Echo "SET_FAIL " & att & "=" & CStr(value) & " ERR=" & Err.Description
        Err.Clear
    Else
        WScript.Echo "SET_OK " & att & "=" & CStr(value)
    End If
    On Error GoTo 0
End Sub
