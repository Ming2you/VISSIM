Option Explicit

If WScript.Arguments.Count < 1 Then
    WScript.Echo "Usage: cscript probe_vissim_load_only.vbs <network.inpx>"
    WScript.Quit 2
End If

Dim netPath
netPath = WScript.Arguments(0)

Dim Vissim
Set Vissim = CreateObject("Vissim.Vissim")
WScript.Echo "STAGE=COM_CREATED"

Vissim.LoadNet netPath, False
WScript.Echo "STAGE=NET_LOADED"
WScript.Echo "VERSION=" & Vissim.AttValue("VERSION")
WScript.Echo "LINKS=" & Vissim.Net.Links.Count
WScript.Echo "NODES=" & Vissim.Net.Nodes.Count
WScript.Echo "VEHICLE_INPUTS=" & Vissim.Net.VehicleInputs.Count
WScript.Echo "QUEUE_COUNTERS=" & Vissim.Net.QueueCounters.Count
WScript.Echo "DATA_COLLECTION_POINTS=" & Vissim.Net.DataCollectionPoints.Count

Set Vissim = Nothing
WScript.Quit 0
