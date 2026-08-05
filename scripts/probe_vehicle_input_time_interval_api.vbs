Option Explicit

' Probe the VISSIM COM schema for per-time-interval vehicle input volumes.
' Pure ASCII. Usage:
'   cscript //nologo probe_vehicle_input_time_interval_api.vbs "<abs path to .inpx>"

If WScript.Arguments.Count < 1 Then
    WScript.Echo "Usage: cscript probe_vehicle_input_time_interval_api.vbs <network.inpx>"
    WScript.Quit 2
End If

Dim netPath, Vissim
netPath = WScript.Arguments(0)

Set Vissim = CreateVissimCom()
WScript.Echo "STAGE=COM_CREATED"
Vissim.LoadNet netPath, False
WScript.Echo "STAGE=NET_LOADED"
WScript.Echo "VERSION=" & SafeAtt(Vissim, "ExeVersion")

ProbeTimeIntervalSets
ProbeIndexedVolume
ProbeSubContainer
ProbeWriteReadback

Set Vissim = Nothing
WScript.Quit 0

Function CreateVissimCom()
    Dim progIds, i, obj
    progIds = Array("Vissim.Vissim", "Vissim.Vissim-64", "VISSIM.Vissim.2024", "VISSIM.Vissim.2023")
    For i = 0 To UBound(progIds)
        On Error Resume Next
        Set obj = CreateObject(progIds(i))
        If Err.Number = 0 Then
            Err.Clear
            On Error GoTo 0
            WScript.Echo "COM_PROGID=" & progIds(i)
            Set CreateVissimCom = obj
            Exit Function
        End If
        Err.Clear
        On Error GoTo 0
    Next
    WScript.Echo "ERROR=COM_CREATE_FAILED"
    WScript.Quit 3
End Function

Sub ProbeTimeIntervalSets()
    Dim names, n, col, setObj, arr, ti, cnt
    WScript.Echo "--- TIME INTERVAL SET COLLECTIONS ---"
    names = Array("TimeIntervalSets", "TimeIntervalSet", "TimeIntervals")
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

    On Error Resume Next
    Set col = Vissim.Net.TimeIntervalSets
    If Err.Number <> 0 Then
        WScript.Echo "TIS_UNAVAILABLE err=" & Err.Description
        Err.Clear
        On Error GoTo 0
        Exit Sub
    End If
    arr = col.GetAll
    If Err.Number <> 0 Then
        WScript.Echo "TIS_GETALL_FAILED err=" & Err.Description
        Err.Clear
        On Error GoTo 0
        Exit Sub
    End If
    On Error GoTo 0
    For Each setObj In arr
        WScript.Echo "TIS no=" & SafeAtt(setObj, "No") & " name=" & SafeAtt(setObj, "Name")
        On Error Resume Next
        cnt = -1
        cnt = setObj.TimeInts.Count
        If Err.Number <> 0 Then
            Err.Clear
            cnt = -1
            cnt = setObj.TimeIntervals.Count
            If Err.Number <> 0 Then
                WScript.Echo "   TIS_SUB_FAIL err=" & Err.Description
                Err.Clear
            Else
                WScript.Echo "   TIS_SUB=TimeIntervals count=" & CStr(cnt)
                DumpIntervals setObj.TimeIntervals
            End If
        Else
            WScript.Echo "   TIS_SUB=TimeInts count=" & CStr(cnt)
            DumpIntervals setObj.TimeInts
        End If
        On Error GoTo 0
    Next
End Sub

Sub DumpIntervals(col)
    Dim arr, ti, line
    On Error Resume Next
    arr = col.GetAll
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        Exit Sub
    End If
    On Error GoTo 0
    line = ""
    For Each ti In arr
        line = line & " [Index=" & SafeAtt(ti, "Index") & " No=" & SafeAtt(ti, "No") & _
               " Start=" & SafeAtt(ti, "Start") & " End=" & SafeAtt(ti, "End") & "]"
    Next
    WScript.Echo "   INTERVALS:" & line
End Sub

Sub ProbeIndexedVolume()
    Dim viArray, vi, i, val, keyForms, k, viNo
    WScript.Echo "--- INDEXED Volume(n) READ ---"
    viArray = Vissim.Net.VehicleInputs.GetAll
    WScript.Echo "VEHICLE_INPUT_COUNT=" & CStr(Vissim.Net.VehicleInputs.Count)
    For Each vi In viArray
        viNo = SafeAtt(vi, "No")
        If viNo = "1098" Or viNo = "1099" Or viNo = "114" Then
            For i = 1 To 8
                val = SafeAtt(vi, "Volume(" & CStr(i) & ")")
                WScript.Echo "VI no=" & viNo & " Volume(" & CStr(i) & ")=[" & val & "]" & _
                    " Cont=[" & SafeAtt(vi, "Cont(" & CStr(i) & ")") & "]" & _
                    " VolType=[" & SafeAtt(vi, "VolType(" & CStr(i) & ")") & "]" & _
                    " VehComp=[" & SafeAtt(vi, "VehComp(" & CStr(i) & ")") & "]"
            Next
            keyForms = Array("Volume", "Volume(1 900000)", "Volume(900)", "Volume(900000)", "Volume(2,1)", "TimeIntVehVols")
            For Each k In keyForms
                WScript.Echo "VI no=" & viNo & " ALTKEY " & k & "=[" & SafeAtt(vi, k) & "]"
            Next
            Exit For
        End If
    Next
End Sub

Sub ProbeSubContainer()
    Dim viArray, vi, names, n, col, arr, item, viNo
    WScript.Echo "--- SUB CONTAINER ON VehicleInput ---"
    viArray = Vissim.Net.VehicleInputs.GetAll
    For Each vi In viArray
        viNo = SafeAtt(vi, "No")
        If viNo = "1099" Then
            names = Array("TimeIntVehVols", "TimeIntervalVehVolumes", "VehVols", "TimeIntervalVehVolume")
            For Each n In names
                On Error Resume Next
                Set col = Eval("vi." & n)
                If Err.Number = 0 Then
                    WScript.Echo "SUBCOL_OK=" & n & " COUNT=" & CStr(SafeCount(col))
                    arr = col.GetAll
                    If Err.Number = 0 Then
                        For Each item In arr
                            WScript.Echo "   ITEM TimeInt=[" & SafeAtt(item, "TimeInt") & "]" & _
                                " Volume=[" & SafeAtt(item, "Volume") & "]" & _
                                " Cont=[" & SafeAtt(item, "Cont") & "]" & _
                                " VehComp=[" & SafeAtt(item, "VehComp") & "]"
                        Next
                    Else
                        WScript.Echo "   SUBCOL_GETALL_FAIL err=" & Err.Description
                        Err.Clear
                    End If
                Else
                    WScript.Echo "SUBCOL_FAIL=" & n & " ERR=" & Err.Description
                    Err.Clear
                End If
                On Error GoTo 0
            Next
            Exit For
        End If
    Next
End Sub

Sub ProbeWriteReadback()
    Dim viArray, vi, i, before, after, viNo, ok
    WScript.Echo "--- WRITE / READBACK Volume(n) ---"
    viArray = Vissim.Net.VehicleInputs.GetAll
    For Each vi In viArray
        viNo = SafeAtt(vi, "No")
        If viNo = "1099" Then
            For i = 1 To 6
                before = SafeAtt(vi, "Volume(" & CStr(i) & ")")
                ok = "OK"
                On Error Resume Next
                vi.AttValue("Volume(" & CStr(i) & ")") = CDbl(ToDbl(before)) * 2.0
                If Err.Number <> 0 Then
                    ok = "SETFAIL:" & Err.Description
                    Err.Clear
                End If
                On Error GoTo 0
                after = SafeAtt(vi, "Volume(" & CStr(i) & ")")
                WScript.Echo "WRITE no=" & viNo & " idx=" & CStr(i) & " before=" & before & _
                    " target=" & CStr(ToDbl(before) * 2.0) & " after=" & after & " status=" & ok
            Next
            Exit For
        End If
    Next
End Sub

Function SafeCount(col)
    SafeCount = -1
    On Error Resume Next
    SafeCount = col.Count
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
        SafeAtt = "<ERR:" & Err.Description & ">"
        Err.Clear
    End If
    On Error GoTo 0
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
