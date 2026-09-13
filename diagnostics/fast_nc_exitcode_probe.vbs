Option Explicit
' No COM objects: leave time for the parent to capture the process handle.
WScript.Sleep 300
WScript.Quit CLng(WScript.Arguments(0))
