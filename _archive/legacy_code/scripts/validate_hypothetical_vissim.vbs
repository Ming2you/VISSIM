Option Explicit

If WScript.Arguments.Count < 3 Then
    WScript.Echo "Usage: cscript validate_hypothetical_vissim.vbs <network.inpx> <layout.layx> <screenshot.png>"
    WScript.Quit 2
End If

Dim netPath, layoutPath, screenshotPath
netPath = WScript.Arguments(0)
layoutPath = WScript.Arguments(1)
screenshotPath = WScript.Arguments(2)

Dim Vissim
Set Vissim = CreateObject("Vissim.Vissim.2020")
Vissim.LoadNet netPath, False
Vissim.LoadLayout layoutPath

Vissim.Graphics.CurrentNetworkWindow.AttValue("3D") = 0
Vissim.Graphics.CurrentNetworkWindow.AttValue("QuickMode") = 1
Vissim.Graphics.CurrentNetworkWindow.ZoomTo -1500, -750, 1500, 1050
Vissim.Graphics.CurrentNetworkWindow.Screenshot screenshotPath, 1

Vissim.Simulation.AttValue("SimPeriod") = 60
Vissim.Simulation.AttValue("SimRes") = 5
Dim stepNo
For stepNo = 1 To 25
    Vissim.Simulation.RunSingleStep
Next

WScript.Echo "VERSION=" & Vissim.AttValue("VERSION")
WScript.Echo "LINKS=" & Vissim.Net.Links.Count
WScript.Echo "NODES=" & Vissim.Net.Nodes.Count
WScript.Echo "VEHICLE_INPUTS=" & Vissim.Net.VehicleInputs.Count
WScript.Echo "QUEUE_COUNTERS=" & Vissim.Net.QueueCounters.Count
WScript.Echo "DATA_COLLECTION_POINTS=" & Vissim.Net.DataCollectionPoints.Count
WScript.Echo "SIM_SEC=" & Vissim.Simulation.AttValue("SimSec")
WScript.Echo "SCREENSHOT=" & screenshotPath

Set Vissim = Nothing
WScript.Quit 0
