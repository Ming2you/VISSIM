Option Explicit

If WScript.Arguments.Count < 1 Then
    WScript.Echo "Usage: cscript probe_vissim_sim_only.vbs <network.inpx>"
    WScript.Quit 2
End If

Dim netPath
netPath = WScript.Arguments(0)

Dim Vissim
Set Vissim = CreateObject("Vissim.Vissim")
WScript.Echo "STAGE=COM_CREATED"

Vissim.LoadNet netPath, False
WScript.Echo "STAGE=NET_LOADED"

Vissim.Simulation.AttValue("RandSeed") = 42
Vissim.Simulation.AttValue("SimPeriod") = 10
Vissim.Simulation.AttValue("SimRes") = 1
WScript.Echo "STAGE=SIM_CONFIGURED"

Vissim.Simulation.RunSingleStep
WScript.Echo "STAGE=SIM_SINGLE_STEP_DONE"
WScript.Echo "SIM_SEC=" & Vissim.Simulation.AttValue("SimSec")

Set Vissim = Nothing
WScript.Quit 0
