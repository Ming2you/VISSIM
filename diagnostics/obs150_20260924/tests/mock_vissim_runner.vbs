' TEST ONLY (WP-A). VBScript stand-in for the Vissim 2020 COM surface the obs150 runner
' procedures touch. Adapted from D:\VISSIM-merge\tools\obs150_probe\test\mock_vissim.vbs, without
' its toy traffic: a test sets the state it needs (vehicles, counts, signal states) and the
' mock only answers. It never talks to VISSIM. Loaded as plain text into a harness together
' with procedures cut out of scripts\run_real_world_stackelberg_controller.vbs.
'
' Test knobs (globals the harness declares and may set):
'   gMockPosShift    readback offset added to DataCollectionPoint Pos
'   gMockEvalBad     Evaluation attribute whose readback is off by one
'   gMockStopShift   RunContinuous stops this many 0.1 s steps after SimBreakAt
'   gMockNoVehs      Vehs(...) of this measurement key reads Empty
'   gMockLastShift   Vehs(Current,Last,All) differs from (Current,k,All) by this much
'   gMockStuck       "<sc>-<sg>" whose SigState ignores writes

Class MockVissimR
    Public mNet, mSim, mEval
    Private Sub Class_Initialize()
        Set mNet = New MockNetR
        Set mSim = New MockSimR
        Set mEval = New MockEvalR
    End Sub
    Public Property Get Net(): Set Net = mNet: End Property
    Public Property Get Simulation(): Set Simulation = mSim: End Property
    Public Property Get Evaluation(): Set Evaluation = mEval: End Property
End Class

Class MockNetR
    Public mLinks, mDcps, mDcms, mVehs, mScs
    Private Sub Class_Initialize()
        Set mLinks = New MockLinksR
        Set mDcps = New MockDcpsR
        Set mDcms = New MockDcmsR
        Set mVehs = New MockVehiclesR
        Set mScs = New MockScsR
    End Sub
    Public Property Get Links(): Set Links = mLinks: End Property
    Public Property Get DataCollectionPoints(): Set DataCollectionPoints = mDcps: End Property
    Public Property Get DataCollectionMeasurements(): Set DataCollectionMeasurements = mDcms: End Property
    Public Property Get Vehicles(): Set Vehicles = mVehs: End Property
    Public Property Get SignalControllers(): Set SignalControllers = mScs: End Property
End Class

' ------------------------------------------------------------------ simulation clock (0.1 s steps)
Class MockSimR
    Public t10, brk, res, runs
    Private Sub Class_Initialize()
        t10 = 0: brk = 0: res = 10: runs = 0
    End Sub
    Public Property Get AttValue(n)
        Select Case LCase(n)
            Case "simsec": AttValue = CDbl(t10) / 10
            Case "simres": AttValue = CLng(res)
            Case "simbreakat": AttValue = CDbl(brk)
            Case Else: Err.Raise vbObjectError + 3, "MockSimR", "AttValue failed: unknown attribute " & n
        End Select
    End Property
    Public Property Let AttValue(n, v)
        Select Case LCase(n)
            Case "simbreakat": brk = CDbl(v)
            Case "simres": res = v
            Case Else: Err.Raise vbObjectError + 3, "MockSimR", "put_AttValue failed: unknown attribute " & n
        End Select
    End Property
    Public Sub RunContinuous()
        runs = runs + 1
        t10 = CLng(brk * 10) + CLng(gMockStopShift)
    End Sub
    Public Sub RunSingleStep()
        t10 = t10 + 1
    End Sub
End Class

Class MockEvalR
    Public d
    Private Sub Class_Initialize()
        Set d = CreateObject("Scripting.Dictionary")
        d("evaloutdir") = "C:\nowhere"
        d("datacollcollectdata") = 0: d("datacollfromtime") = 0: d("datacolltotime") = 10800
        d("datacollinterval") = 300: d("datacollrawwritefile") = 0: d("datacollrawfromtime") = 0
        d("datacollrawtotime") = 5400
    End Sub
    Public Property Get AttValue(n)
        If Not d.Exists(LCase(n)) Then Err.Raise vbObjectError + 2, "MockEvalR", "AttValue failed: " & n
        AttValue = d(LCase(n))
        If LCase(n) = LCase(CStr(gMockEvalBad)) Then AttValue = CLng(AttValue) + 1
    End Property
    Public Property Let AttValue(n, v)
        If Not d.Exists(LCase(n)) Then Err.Raise vbObjectError + 2, "MockEvalR", "put_AttValue failed: " & n
        ' VISSIM reads booleans back as 1/0 (probe run, check a).
        If VarType(v) = vbBoolean Then
            If v Then d(LCase(n)) = CLng(1) Else d(LCase(n)) = CLng(0)
        Else
            d(LCase(n)) = CLng(v)
        End If
    End Property
End Class

' ------------------------------------------------------------------ links, lanes, link evaluation
Class MockLinksR
    Public d, vol
    Private Sub Class_Initialize()
        Set d = CreateObject("Scripting.Dictionary")
        Set vol = CreateObject("Scripting.Dictionary")
    End Sub
    Public Sub AddLink(no, lanes)
        Dim lk
        Set lk = New MockLinkR
        lk.no = CLng(no): lk.nLanes = CLng(lanes)
        Set d(CStr(no)) = lk
    End Sub
    Public Function ItemByKey(k)
        If Not d.Exists(CStr(CLng(k))) Then Err.Raise vbObjectError + 4, "MockLinksR", "ItemByKey failed: link " & k
        Set ItemByKey = d(CStr(CLng(k)))
    End Function
End Class

Class MockLinkR
    Public no, nLanes
    Public Property Get Lanes()
        Dim c
        Set c = New MockLanesR
        c.link = no: c.n = nLanes
        Set Lanes = c
    End Property
    Public Property Get AttValue(n)
        Dim key
        If Left(n, 26) <> "AVG:LinkEvalSegs\Volume(Cu" Then Err.Raise vbObjectError + 5, "MockLinkR", "Relation type and aggregate function do not match"
        key = CStr(no) & "|" & n
        If Not gMock.mNet.mLinks.vol.Exists(key) Then Err.Raise vbObjectError + 5, "MockLinkR", "no link evaluation for " & key
        AttValue = gMock.mNet.mLinks.vol(key)
    End Property
End Class

Class MockLanesR
    Public link, n
    Public Function ItemByKey(k)
        Dim ln
        If CLng(k) < 1 Or CLng(k) > n Then Err.Raise vbObjectError + 6, "MockLanesR", "ItemByKey failed: lane " & k
        Set ln = New MockLaneR
        ln.link = link: ln.lane = CLng(k)
        Set ItemByKey = ln
    End Function
End Class

Class MockLaneR
    Public link, lane
End Class

' ------------------------------------------------------------------ data collection points / measurements
Class MockDcpsR
    Public d
    Private Sub Class_Initialize()
        Set d = CreateObject("Scripting.Dictionary")
    End Sub
    Public Property Get Count(): Count = d.Count: End Property
    Public Function ItemByKey(k)
        If Not d.Exists(CStr(CLng(k))) Then Err.Raise vbObjectError + 7, "MockDcpsR", "ItemByKey failed: point " & k
        Set ItemByKey = d(CStr(CLng(k)))
    End Function
    Public Function AddDataCollectionPoint(key, laneObj, pos)
        Dim p
        If d.Exists(CStr(CLng(key))) Then Err.Raise vbObjectError + 8, "MockDcpsR", "key already in use " & key
        Set p = New MockDcpR
        p.no = CLng(key): p.link = laneObj.link: p.lane = laneObj.lane: p.pos = CDbl(pos)
        Set d(CStr(CLng(key))) = p
        Set AddDataCollectionPoint = p
    End Function
End Class

Class MockDcpR
    Public no, link, lane, pos
    Public Property Get AttValue(n)
        Select Case LCase(n)
            Case "no": AttValue = CLng(no)
            Case "lane": AttValue = CStr(link) & "-" & CStr(lane)
            Case "pos": AttValue = CDbl(pos) + CDbl(gMockPosShift)
            Case Else: Err.Raise vbObjectError + 9, "MockDcpR", "AttValue failed: " & n
        End Select
    End Property
End Class

' counts(key)(k) = Vehs of interval k; an open interval reads its partial count the same way.
Class MockDcmsR
    Public d, counts
    Private Sub Class_Initialize()
        Set d = CreateObject("Scripting.Dictionary")
        Set counts = CreateObject("Scripting.Dictionary")
    End Sub
    Public Property Get Count(): Count = d.Count: End Property
    Public Function ItemByKey(k)
        If Not d.Exists(CStr(CLng(k))) Then Err.Raise vbObjectError + 10, "MockDcmsR", "ItemByKey failed: measurement " & k
        Set ItemByKey = d(CStr(CLng(k)))
    End Function
    Public Function AddDataCollectionMeasurement(key)
        Dim m
        If d.Exists(CStr(CLng(key))) Then Err.Raise vbObjectError + 11, "MockDcmsR", "key already in use " & key
        Set m = New MockDcmR
        m.no = CLng(key): m.points = ""
        Set d(CStr(CLng(key))) = m
        Set AddDataCollectionMeasurement = m
    End Function
    Public Sub SetCount(key, k, value)
        counts(CStr(key) & "|" & CStr(k)) = value
    End Sub
    Public Function GetMultiAttValues(att)
        Dim keys, arr(), i, kText, a, v
        keys = d.Keys
        ReDim arr(UBound(keys), 1)
        For i = 0 To UBound(keys)
            arr(i, 0) = CLng(i + 1)
            If att = "No" Then
                arr(i, 1) = CLng(keys(i))
            ElseIf Left(att, 13) = "Vehs(Current," Then
                kText = Mid(att, 14, InStr(14, att, ",") - 14)
                If kText = "Last" Then kText = CStr(gMockCurrentK)
                v = CLng(0)
                If counts.Exists(CStr(keys(i)) & "|" & kText) Then v = CLng(counts(CStr(keys(i)) & "|" & kText))
                If Mid(att, 14, 4) = "Last" Then v = CLng(v + CLng(gMockLastShift))
                If CStr(keys(i)) = CStr(gMockNoVehs) Then v = Empty
                arr(i, 1) = v
            Else
                Err.Raise vbObjectError + 12, "MockDcmsR", "GetMultiAttValues failed: " & att
            End If
        Next
        GetMultiAttValues = arr
    End Function
End Class

Class MockDcmR
    Public no, points
    Public Property Get AttValue(n)
        Select Case LCase(n)
            Case "no": AttValue = CLng(no)
            Case "datacollectionpoints": AttValue = CStr(points)
            Case Else: Err.Raise vbObjectError + 13, "MockDcmR", "AttValue failed: " & n
        End Select
    End Property
    Public Property Let AttValue(n, v)
        If LCase(n) <> "datacollectionpoints" Then Err.Raise vbObjectError + 13, "MockDcmR", "put_AttValue failed: " & n
        points = CStr(v)
    End Property
End Class

' ------------------------------------------------------------------ vehicles
' Each vehicle: Array(no, link, lane, pos, speed, length, routDecNo, routeNo).
Class MockVehiclesR
    Public list
    Private Sub Class_Initialize()
        Set list = CreateObject("Scripting.Dictionary")
    End Sub
    Public Property Get Count(): Count = list.Count: End Property
    Public Sub AddVehicle(no, link, lane, pos, speed, length, routDecNo, routeNo)
        list(CStr(no)) = Array(CLng(no), CLng(link), CLng(lane), CDbl(pos), CDbl(speed), CDbl(length), routDecNo, routeNo)
    End Sub
    Public Function GetMultiAttValues(att)
        Dim keys, arr(), i, v
        keys = list.Keys
        If list.Count = 0 Then
            GetMultiAttValues = Empty
            Exit Function
        End If
        ReDim arr(UBound(keys), 1)
        For i = 0 To UBound(keys)
            v = list(keys(i))
            arr(i, 0) = CLng(i + 1)
            Select Case att
                Case "No": arr(i, 1) = v(0)
                Case "Lane": arr(i, 1) = CStr(v(1)) & "-" & CStr(v(2))
                Case "Pos": arr(i, 1) = v(3)
                Case "Speed": arr(i, 1) = v(4)
                Case "Length": arr(i, 1) = v(5)
                Case "RoutDecNo": arr(i, 1) = v(6)
                Case "RouteNo": arr(i, 1) = v(7)
                Case "RoutDecType": arr(i, 1) = Null
                Case "NextLink\No": arr(i, 1) = Null
                Case Else: Err.Raise vbObjectError + 14, "MockVehiclesR", "GetMultiAttValues failed: " & att
            End Select
        Next
        GetMultiAttValues = arr
    End Function
End Class

' ------------------------------------------------------------------ signal controllers and groups
Class MockScsR
    Public d
    Private Sub Class_Initialize()
        Set d = CreateObject("Scripting.Dictionary")
    End Sub
    Public Sub AddController(no, sgCount)
        Dim sc, i, sg
        Set sc = New MockScR
        sc.no = CLng(no)
        Set sc.mSgs = New MockSgsR
        For i = 1 To sgCount
            Set sg = New MockSgR
            sg.sc = CLng(no): sg.no = CLng(i): sg.state = "RED": sg.com = False
            Set sc.mSgs.d(CStr(i)) = sg
        Next
        Set d(CStr(no)) = sc
    End Sub
    Public Function ItemByKey(k)
        If Not d.Exists(CStr(CLng(k))) Then Err.Raise vbObjectError + 15, "MockScsR", "ItemByKey failed: SC " & k
        Set ItemByKey = d(CStr(CLng(k)))
    End Function
End Class

Class MockScR
    Public no, mSgs
    Public Property Get SGs(): Set SGs = mSgs: End Property
End Class

Class MockSgsR
    Public d
    Private Sub Class_Initialize()
        Set d = CreateObject("Scripting.Dictionary")
    End Sub
    Public Property Get Count(): Count = d.Count: End Property
    Public Function ItemByKey(k)
        If Not d.Exists(CStr(CLng(k))) Then Err.Raise vbObjectError + 16, "MockSgsR", "ItemByKey failed: SG " & k
        Set ItemByKey = d(CStr(CLng(k)))
    End Function
    Public Function GetMultiAttValues(att)
        Dim keys, arr(), i
        keys = d.Keys
        ReDim arr(UBound(keys), 1)
        For i = 0 To UBound(keys)
            arr(i, 0) = CLng(i + 1)
            arr(i, 1) = d(keys(i)).AttValue(att)
        Next
        GetMultiAttValues = arr
    End Function
End Class

Class MockSgR
    Public sc, no, state, com
    Public Property Get AttValue(n)
        Select Case LCase(n)
            Case "no": AttValue = CLng(no)
            Case "sigstate": AttValue = state
            Case "contrbycom": AttValue = com
            Case Else: Err.Raise vbObjectError + 17, "MockSgR", "AttValue failed: " & n
        End Select
    End Property
    Public Property Let AttValue(n, v)
        Select Case LCase(n)
            Case "sigstate"
                If Not com Then Err.Raise vbObjectError + 18, "MockSgR", "SigState is not writable: SG not under COM"
                If CStr(sc) & "-" & CStr(no) <> CStr(gMockStuck) Then state = UCase(CStr(v))
            Case "contrbycom": com = CBool(v)
            Case Else: Err.Raise vbObjectError + 17, "MockSgR", "put_AttValue failed: " & n
        End Select
    End Property
End Class
