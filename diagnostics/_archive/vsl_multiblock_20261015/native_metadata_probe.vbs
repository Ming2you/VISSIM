Option Explicit
Dim RW_OFFSET_WRITER, fso, i, ts, line, first, parts, invalid, rows, expected
RW_OFFSET_WRITER = "experiment"
Set fso = CreateObject("Scripting.FileSystemObject")
expected = CLng(WScript.Arguments(0))
invalid = 0: rows = 0
For i = 1 To WScript.Arguments.Count - 1
    Set ts = fso.OpenTextFile(WScript.Arguments(i), 1, False)
    first = True
    Do Until ts.AtEndOfStream
        line = ts.ReadLine
        If first Then
            first = False
        ElseIf Trim(line) <> "" Then
            rows = rows + 1
            parts = Split(line, ",")
            If UBound(parts) <> 14 Then
                invalid = invalid + 1
            ElseIf Not ExperimentMetadataValid(parts(14)) Then
                invalid = invalid + 1
            End If
        End If
    Loop
    ts.Close
Next
WScript.Echo "ROWS=" & CStr(rows) & " INVALID=" & CStr(invalid) & " EXPECTED=" & CStr(expected)
If invalid <> expected Then WScript.Quit 2
Function ExperimentMetadataValid(metadataText)
    Dim tokens, required, token, item, count
    ExperimentMetadataValid = True
    If RW_OFFSET_WRITER <> "experiment" Then Exit Function
    tokens = Split(CStr(metadataText), ";")
    For Each required In Array("offset_writer=experiment", "physical_signal_contract=1", "offset_experiment=1")
        count = 0
        For Each token In tokens
            If CStr(token) = required Then count = count + 1
        Next
        If count <> 1 Then
            ExperimentMetadataValid = False
            Exit Function
        End If
    Next
End Function
