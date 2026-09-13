Option Explicit
' Short diagnostic only. No controller, demand setter, route query or vehicle scan.
Dim sim, fs, log, sg, sc, second, fatalNumber, fatalText, inputPath, outPath
Set sim = Nothing
If WScript.Arguments.Count <> 2 Then WScript.Quit 2
inputPath = WScript.Arguments(0)
outPath = WScript.Arguments(1)
Set fs = CreateObject("Scripting.FileSystemObject")
If fs.FileExists(outPath & "\actual_readback.csv") Then WScript.Quit 3
Set log = fs.CreateTextFile(outPath & "\actual_readback.csv", False, True)
log.WriteLine "sim_sec,stage,sc,sg,state,contr_by_com"
On Error Resume Next
RunProbe
fatalNumber = Err.Number
fatalText = Err.Description
Err.Clear
If Not sim Is Nothing Then sim.Simulation.Stop
If fatalNumber = 0 And Err.Number <> 0 Then
    fatalNumber = Err.Number
    fatalText = "Stop failed: " & Err.Description
End If
Err.Clear
Set sg = Nothing
Set sc = Nothing
Set sim = Nothing
log.Close
If fatalNumber = 0 And Err.Number <> 0 Then
    fatalNumber = Err.Number
    fatalText = "Readback close failed: " & Err.Description
End If
Err.Clear
Set log = Nothing
On Error GoTo 0
If fatalNumber <> 0 Then
    WScript.Echo "FAILED=" & CStr(fatalNumber) & " " & fatalText
    WScript.Quit 4
End If
WScript.Echo "NATIVE_RECORD_PROBE_DONE=1"
WScript.Quit 0

Sub Capture(scNo, sgNo, stage)
    Set sg = sim.Net.SignalControllers.ItemByKey(scNo).SGs.ItemByKey(sgNo)
    log.WriteLine CStr(sim.Simulation.AttValue("SimSec")) & "," & stage & "," & CStr(scNo) & "," & CStr(sgNo) & "," & sg.AttValue("SigState") & "," & CStr(sg.AttValue("ContrByCOM"))
    Set sg = Nothing
End Sub

Sub Apply(scNo, sgNo, state)
    Capture scNo, sgNo, "before_write"
    Set sg = sim.Net.SignalControllers.ItemByKey(scNo).SGs.ItemByKey(sgNo)
    sg.AttValue("SigState") = state
    Set sg = Nothing
    Capture scNo, sgNo, "after_write"
End Sub

Sub RunProbe
    WScript.Echo "CREATING_OWNED_VISSIM"
    Set sim = CreateObject("Vissim.Vissim")
    sim.LoadNet inputPath, False
    WScript.Echo "NETWORK_LOADED=1"
    sim.Graphics.CurrentNetworkWindow.AttValue("QuickMode") = 1
    WScript.Echo "QUICK_MODE_SET=1"
    sim.Simulation.AttValue("RandSeed") = 13
    sim.Simulation.AttValue("SimRes") = 1
    sim.Simulation.AttValue("SimPeriod") = 61
    sim.Simulation.AttValue("UseMaxSimSpeed") = True
    WScript.Echo "SIMULATION_SETTINGS_SET=1"
    sim.Evaluation.AttValue("EvalOutDir") = outPath
    sim.Evaluation.AttValue("SigChangesWriteFile") = True
    sim.Evaluation.AttValue("SCDetRecWriteFile") = True
    sim.Evaluation.AttValue("VehRecWriteFile") = True
    sim.Evaluation.AttValue("VehRecFromTime") = 0
    sim.Evaluation.AttValue("VehRecToTime") = 60
    sim.Evaluation.AttValue("VehRecFilterType") = "ALL"
    sim.Evaluation.AttValue("VehRecResolution") = 1
    WScript.Echo "EVAL_LSA=" & CStr(sim.Evaluation.AttValue("SigChangesWriteFile")) & " LDP=" & CStr(sim.Evaluation.AttValue("SCDetRecWriteFile"))
    Capture 1, 1, "initial"
    Capture 1004, 5, "initial"
    Capture 9103, 1, "initial"
    For second = 1 To 60
        sim.Simulation.RunSingleStep
        If CDbl(sim.Simulation.AttValue("SimSec")) <> CDbl(second) Then Err.Raise 513, , "Actual SimSec differs from requested step"
        WScript.Echo "ACTUAL_SIMSEC=" & CStr(sim.Simulation.AttValue("SimSec"))
        Capture 1, 1, "after_step"
        Capture 1004, 5, "after_step"
        Capture 9103, 1, "after_step"
        Select Case second
            Case 1, 20, 50
                Apply 1004, 5, "GREEN"
                Apply 9103, 1, "GREEN"
            Case 10, 40
                Apply 1004, 5, "AMBER"
                Apply 9103, 1, "AMBER"
            Case 11, 41
                Apply 9103, 1, "RED"
            Case 13, 43
                Apply 1004, 5, "RED"
        End Select
    Next
End Sub
