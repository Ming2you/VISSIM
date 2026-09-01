Option Explicit

' Second probe: is VehicleInput.TimeIntVehVols item Volume writable, and does it stay
' consistent with the indexed VehicleInput.Volume(n) view? Pure ASCII.
'   cscript //nologo probe_vehicle_input_interval_write2.vbs <network.inpx>

If WScript.Arguments.Count < 1 Then
    WScript.Echo "Usage: cscript probe_vehicle_input_interval_write2.vbs <network.inpx>"
    WScript.Quit 2
End If

Dim Vissim
Set Vissim = CreateVissimCom()
Vissim.LoadNet WScript.Arguments(0), False
WScript.Echo "STAGE=NET_LOADED"

Dim tis, tisArr, s, intervalCount
intervalCount = -1
On Error Resume Next
Set tis = Vissim.Net.TimeIntervalSets.ItemByKey(1)
If Err.Number <> 0 Then
    WScript.Echo "TIS_ITEMBYKEY_FAIL err=" & Err.Description
    Err.Clear
Else
    intervalCount = tis.TimeInts.Count
    WScript.Echo "TIS1_INTERVAL_COUNT=" & CStr(intervalCount)
End If
Err.Clear
On Error GoTo 0

Dim viArray, vi, viNo, col, arr, item, i, before, after, ok
viArray = Vissim.Net.VehicleInputs.GetAll
For Each vi In viArray
    viNo = SafeAtt(vi, "No")
    If viNo = "1099" Then
        WScript.Echo "--- SUBITEM WRITE ---"
        Set col = vi.TimeIntVehVols
        arr = col.GetAll
        i = 0
        For Each item In arr
            i = i + 1
            before = SafeAtt(item, "Volume")
            ok = "OK"
            On Error Resume Next
            item.AttValue("Volume") = ToDbl(before) * 3.0
            If Err.Number <> 0 Then
                ok = "SETFAIL:" & Err.Description
                Err.Clear
            End If
            On Error GoTo 0
            after = SafeAtt(item, "Volume")
            WScript.Echo "SUBWRITE row=" & CStr(i) & " TimeInt=" & SafeAtt(item, "TimeInt") & _
                " before=" & before & " after=" & after & " status=" & ok
        Next
        WScript.Echo "--- CROSS VIEW Volume(n) AFTER SUBITEM WRITE ---"
        For i = 1 To 6
            WScript.Echo "CROSS idx=" & CStr(i) & " Volume(" & CStr(i) & ")=" & SafeAtt(vi, "Volume(" & CStr(i) & ")")
        Next
        WScript.Echo "SUBCOL_COUNT=" & CStr(col.Count) & " TIS1_COUNT=" & CStr(intervalCount)
        Exit For
    End If
Next

Set Vissim = Nothing
WScript.Quit 0

Function CreateVissimCom()
    Dim progIds, i, obj
    progIds = Array("Vissim.Vissim", "Vissim.Vissim-64")
    For i = 0 To UBound(progIds)
        On Error Resume Next
        Set obj = CreateObject(progIds(i))
        If Err.Number = 0 Then
            Err.Clear
            On Error GoTo 0
            Set CreateVissimCom = obj
            Exit Function
        End If
        Err.Clear
        On Error GoTo 0
    Next
    WScript.Echo "ERROR=COM_CREATE_FAILED"
    WScript.Quit 3
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
    On Error Resume Next
    ToDbl = CDbl(Trim(CStr(value)))
    If Err.Number <> 0 Then
        ToDbl = 0
        Err.Clear
    End If
    On Error GoTo 0
End Function
