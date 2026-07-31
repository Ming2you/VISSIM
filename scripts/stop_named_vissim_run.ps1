param(
  [Parameter(Mandatory=$true)][string]$Name,
  [int]$CscriptPid = 0,
  [switch]$StopVissim
)

$ErrorActionPreference = "SilentlyContinue"
$selfPid = $PID
$targets = @{}

function Add-Target([int]$Id, [string]$Reason) {
  if ($Id -le 0 -or $Id -eq $selfPid) { return }
  if (-not $targets.ContainsKey($Id)) {
    $targets[$Id] = $Reason
  }
}

if ($CscriptPid -gt 0) {
  Add-Target $CscriptPid "explicit-cscript"
}

$procs = Get-CimInstance Win32_Process |
  Where-Object {
    $_.Name -in @("powershell.exe", "cscript.exe", "VISSIM200.exe", "VISSIM200CL.exe")
  }

foreach ($proc in $procs) {
  $cmd = [string]$proc.CommandLine
  if ($cmd -like "*$Name*") {
    Add-Target ([int]$proc.ProcessId) "name-match"
  }
  if ($cmd -like "*run_real_world_single_watchdog.ps1*" -and $cmd -like "*$Name*") {
    Add-Target ([int]$proc.ProcessId) "watchdog-match"
  }
  if ($cmd -like "*run_real_world_stackelberg_controller.vbs*" -and $cmd -like "*$Name*") {
    Add-Target ([int]$proc.ProcessId) "cscript-match"
  }
  if ($StopVissim -and $proc.Name -in @("VISSIM200.exe", "VISSIM200CL.exe")) {
    Add-Target ([int]$proc.ProcessId) "vissim-cleanup"
  }
}

foreach ($id in $targets.Keys) {
  $reason = $targets[$id]
  try {
    Stop-Process -Id ([int]$id) -Force -ErrorAction SilentlyContinue
    Write-Host ("STOPPED id={0} reason={1}" -f $id, $reason)
  } catch {
    Write-Host ("STOP_FAILED id={0} reason={1} err={2}" -f $id, $reason, $_.Exception.Message)
  }
}

if ($targets.Count -eq 0) {
  Write-Host "NO_MATCHING_PROCESSES"
}
