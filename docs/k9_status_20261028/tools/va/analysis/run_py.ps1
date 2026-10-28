# Detached runner for one analysis / verify Python tool (WMI Win32_Process.Create, BelowNormal,
# PYTHONHASHSEED=0, PYTHONDONTWRITEBYTECODE=1, python -B).  Output files <LogDir>\<Tag>.out.txt / .err.txt; the launch
# line goes to <LogDir>\wmi_py_lines.txt.  The temp/log name carries a timestamp with ms and a random suffix (not the PID).
param(
  [Parameter(Mandatory=$true)][string]$Script,
  [Parameter(Mandatory=$true)][string]$Tag,
  [Parameter(Mandatory=$true)][string]$LogDir,
  [string]$ArgsLine = '',
  [string]$Cwd = ''
)
$ErrorActionPreference = 'Stop'
$py = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$stamp = (Get-Date -Format 'yyyyMMdd_HHmmss_fff') + '_' + ([guid]::NewGuid().ToString('N').Substring(0, 6))
$out = Join-Path $LogDir ("{0}_{1}.out.txt" -f $Tag, $stamp)
$err = Join-Path $LogDir ("{0}_{1}.err.txt" -f $Tag, $stamp)
if (-not $Cwd) { $Cwd = Split-Path -Parent $Script }
$cmd = 'cmd.exe /c set "PYTHONHASHSEED=0" && set "PYTHONDONTWRITEBYTECODE=1" && set "PYTHONIOENCODING=utf-8" && "{0}" -B "{1}" {2} > "{3}" 2> "{4}"' -f $py, $Script, $ArgsLine, $out, $err
$startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]16384 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $Cwd; ProcessStartupInformation = $startup }
$line = '{0}  {1}  RV={2} PID={3} prio=BelowNormal cwd={4} | {5}' -f (Get-Date -Format o), $Tag, $r.ReturnValue, $r.ProcessId, $Cwd, $cmd
Add-Content -LiteralPath (Join-Path $LogDir 'wmi_py_lines.txt') -Value $line -Encoding UTF8
Write-Output ('RV={0} PID={1} OUT={2} ERR={3}' -f $r.ReturnValue, $r.ProcessId, $out, $err)
