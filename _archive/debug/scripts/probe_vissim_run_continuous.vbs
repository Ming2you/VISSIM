Option Explicit

If WScript.Arguments.Count < 1 Then
    WScript.Echo "Usage: cscript probe_vissim_run_continuous.vbs <network.inpx> [break_at_sec] [rand_seed]"
    WScript.Quit 2
End If

Dim netPath, breakAtSec, randSeed
netPath = WScript.Arguments(0)
breakAtSec = CLng(ArgOrDefault(1, 10))
randSeed = CLng(ArgOrDefault(2, 13))

Dim fso, Vissim
Set fso = CreateObject("Scripting.FileSystemObject")
Set Vissim = CreateObject("Vissim.Vissim")
WScript.Echo "STAGE=COM_CREATED"
Vissim.LoadNet netPath, False
WScript.Echo "STAGE=NET_LOADED"
WScript.Echo "VERSION=" & SafeAtt(Vissim, "VERSION")
ConfigureEvaluationOutput fso.BuildPath(fso.GetParentFolderName(netPath), "vissim_eval_probe")

On Error Resume Next
Vissim.Graphics.CurrentNetworkWindow.AttValue("QuickMode") = 1
Vissim.SuspendUpdateGUI
Err.Clear
On Error GoTo 0

TrySetAtt Vissim.Simulation, "RandSeed", randSeed
TrySetAtt Vissim.Simulation, "SimPeriod", CDbl(breakAtSec) + 1
TrySetAtt Vissim.Simulation, "SimRes", 1
TrySetAtt Vissim.Simulation, "NumRuns", 1
TrySetAtt Vissim.Simulation, "UseMaxSimSpeed", True
TrySetAtt Vissim.Simulation, "SimBreakAt", CDbl(breakAtSec)

WScript.Echo "BEFORE_RUN sim_sec=" & SafeAtt(Vissim.Simulation, "SimSec") & " vehicles=" & VehicleCollectionCount()
Vissim.Simulation.RunContinuous
WScript.Echo "AFTER_RUN sim_sec=" & SafeAtt(Vissim.Simulation, "SimSec") & " vehicles=" & VehicleCollectionCount()
WScript.Echo "STAGE=RUN_CONTINUOUS_DONE"

On Error Resume Next
Vissim.ResumeUpdateGUI True
Err.Clear
On Error GoTo 0

Set Vissim = Nothing
WScript.Quit 0

Function ArgOrDefault(index, defaultValue)
    If WScript.Arguments.Count > index Then
        ArgOrDefault = CDbl(WScript.Arguments(index))
    Else
        ArgOrDefault = defaultValue
    End If
End Function

Function VehicleCollectionCount()
    On Error Resume Next
    VehicleCollectionCount = CLng(Vissim.Net.Vehicles.Count)
    If Err.Number <> 0 Then
        Err.Clear
        VehicleCollectionCount = -1
    End If
    On Error GoTo 0
End Function

Sub EnsureParentFolder(path)
    Dim parent
    parent = fso.GetParentFolderName(path)
    If parent <> "" And Not fso.FolderExists(parent) Then
        EnsureParentFolder parent
        fso.CreateFolder parent
    End If
End Sub

Sub EnsureFolder(path)
    If path <> "" And Not fso.FolderExists(path) Then
        EnsureParentFolder fso.BuildPath(path, "placeholder.txt")
        If Not fso.FolderExists(path) Then fso.CreateFolder path
    End If
End Sub

Sub ConfigureEvaluationOutput(path)
    EnsureFolder path
    TrySetEvaluationAtt "EvalOutDir", path
    TrySetEvaluationAtt "DatabaseConnection", ""
    TrySetEvaluationAtt "ListAutoExportType", "FILE"
    WScript.Echo "EVAL_OUT_DIR=" & path
End Sub

Sub TrySetAtt(obj, name, value)
    On Error Resume Next
    obj.AttValue(name) = value
    If Err.Number <> 0 Then
        WScript.Echo "WARN=FAILED_SET_ATT name=" & name & " err=" & Err.Description
        Err.Clear
    End If
    On Error GoTo 0
End Sub

Sub TrySetEvaluationAtt(name, value)
    On Error Resume Next
    Vissim.Evaluation.AttValue(name) = value
    If Err.Number <> 0 Then
        WScript.Echo "WARN=FAILED_SET_EVALUATION_ATT name=" & name & " err=" & Err.Description
        Err.Clear
    End If
    On Error GoTo 0
End Sub

Function SafeAtt(obj, name)
    On Error Resume Next
    SafeAtt = CStr(obj.AttValue(name))
    If Err.Number <> 0 Then
        Err.Clear
        SafeAtt = ""
    End If
    On Error GoTo 0
End Function
