Option Explicit
Dim v, fso, folder, p, stream, i, code, msg
Set fso=CreateObject("Scripting.FileSystemObject")
folder=WScript.Arguments(0)
If Not fso.FolderExists(folder) Then fso.CreateFolder folder
If fso.FileExists(fso.BuildPath(folder,"empty.inpx")) Then WScript.Quit 3
On Error Resume Next
Set v=CreateObject("Vissim.Vissim.200")
If Err.Number<>0 Then
    WScript.Echo "CREATE_FAILED " & Err.Number & " " & Err.Description
    WScript.Quit 2
End If
WScript.Echo "COM_CREATED"
v.AttValue("ShowMessages")=False
v.New
v.SaveNetAs fso.BuildPath(folder,"empty.inpx")
v.Simulation.AttValue("SimPeriod")=10
v.Simulation.AttValue("SimRes")=10
v.Simulation.RunSingleStep
WScript.Echo "SIM_SEC=" & v.Simulation.AttValue("SimSec")
v.Log 20480, "OBS150_LOG_PROBE_115_BEFORE"
Snapshot "single"
For i=1 To 2
    v.Log 20480, "OBS150_LOG_PROBE_115_PAD" & i & " " & String(8192,"x")
Next
Snapshot "padded"
v.Simulation.RunSingleStep
WScript.Echo "AFTER_LOG_SIM_SEC=" & v.Simulation.AttValue("SimSec")
code=Err.Number : msg=Err.Description
Err.Clear
v.Exit
WScript.Echo "COM_EXIT=" & Err.Number
WScript.Echo "PROBE_STATUS=" & code & " " & msg
If code<>0 Then WScript.Quit 2
WScript.Quit 0

Sub Snapshot(label)
    Dim f, text
    For Each f In fso.GetFolder(folder).Files
        If LCase(fso.GetExtensionName(f.Name))="err" Then
            Set stream=fso.OpenTextFile(f.Path,1,False)
            text=""
            If Not stream.AtEndOfStream Then text=stream.ReadAll
            stream.Close
            WScript.Echo "READ=" & label & " bytes=" & f.Size & " marker=" & CStr(InStr(text,"OBS150_LOG_PROBE_115_BEFORE"))
            fso.CopyFile f.Path,fso.BuildPath(folder,label & ".snapshot"),False
        End If
    Next
End Sub
