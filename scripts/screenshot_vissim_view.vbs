Option Explicit

If WScript.Arguments.Count < 7 Then
    WScript.Echo "Usage: cscript screenshot_vissim_view.vbs <network.inpx> <layout.layx> <screenshot.png> <x1> <y1> <x2> <y2>"
    WScript.Quit 2
End If

Dim netPath, layoutPath, screenshotPath, x1, y1, x2, y2
netPath = WScript.Arguments(0)
layoutPath = WScript.Arguments(1)
screenshotPath = WScript.Arguments(2)
x1 = CDbl(WScript.Arguments(3))
y1 = CDbl(WScript.Arguments(4))
x2 = CDbl(WScript.Arguments(5))
y2 = CDbl(WScript.Arguments(6))

Dim Vissim
Set Vissim = CreateObject("Vissim.Vissim")
Vissim.LoadNet netPath, False
Vissim.LoadLayout layoutPath

Vissim.Graphics.CurrentNetworkWindow.AttValue("3D") = 0
Vissim.Graphics.CurrentNetworkWindow.AttValue("QuickMode") = 1
On Error Resume Next
Vissim.Graphics.CurrentNetworkWindow.AttValue("ShowMap") = False
Err.Clear
On Error GoTo 0
Vissim.Graphics.CurrentNetworkWindow.ZoomTo x1, y1, x2, y2
Vissim.Graphics.CurrentNetworkWindow.Screenshot screenshotPath, 1

WScript.Echo "SCREENSHOT=" & screenshotPath
WScript.Echo "LINKS=" & Vissim.Net.Links.Count

Set Vissim = Nothing
WScript.Quit 0
