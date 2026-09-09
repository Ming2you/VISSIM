$ErrorActionPreference = 'Stop'
$runnerPath = Join-Path $PSScriptRoot '../scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1'
$tokens = $null
$parseErrors = $null
$tree = [Management.Automation.Language.Parser]::ParseFile($runnerPath, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
$names = @('Test-SimulationStarted', 'Find-RunVissimIdentity', 'Stop-RunProcesses')
foreach ($name in $names) {
  $definition = $tree.Find({ param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name }, $true)
  if (-not $definition) { throw "Missing helper $name" }
  . ([scriptblock]::Create($definition.Extent.Text))
}
function Assert($Condition, $Message) { if (-not $Condition) { throw $Message } }
$probeFile = Join-Path $PSScriptRoot '.startup_watchdog_test.csv'
try {
  [IO.File]::WriteAllText($probeFile, "sim_sec,total_vehicles`n0,0`n")
  Assert (-not (Test-SimulationStarted $probeFile)) 'zero time must remain in startup'
  [IO.File]::AppendAllText($probeFile, "1,7`n")
  Assert (Test-SimulationStarted $probeFile) 'positive simulation time ends startup timeout'
} finally { Remove-Item -LiteralPath $probeFile -ErrorAction SilentlyContinue }

# These mocks ensure the regression never terminates a real process.
$moment = [datetime]'2026-09-10T01:00:00'
$script:fakeProcesses = @(
  [pscustomobject]@{ Id=1; StartTime=$moment.AddMinutes(-1); MainWindowTitle='target.inpx - VISSIM' },
  [pscustomobject]@{ Id=2; StartTime=$moment.AddSeconds(1); MainWindowTitle='other.inpx - VISSIM' },
  [pscustomobject]@{ Id=3; StartTime=$moment.AddSeconds(1); MainWindowTitle='target.inpx - VISSIM' },
  [pscustomobject]@{ Id=4; StartTime=$moment; MainWindowTitle='' }
)
$script:stoppedIds = [Collections.Generic.List[int]]::new()
function Get-Process { param($Name, $Id, $ErrorAction)
  if ($PSBoundParameters.ContainsKey('Id')) { return $script:fakeProcesses | Where-Object Id -eq $Id }
  return $script:fakeProcesses
}
function Stop-Process { param($Id, [switch]$Force, $ErrorAction) $script:stoppedIds.Add($Id) }
$selected = Find-RunVissimIdentity @(1) $moment 'target.inpx'
Assert ($selected.Id -eq 3) 'must select only the new matching network instance'
Stop-RunProcesses $script:fakeProcesses[3] $selected
Assert (($script:stoppedIds -join ',') -eq '4,3') 'must stop only owned cscript and VISSIM'
$script:stoppedIds.Clear()
$script:fakeProcesses[2].StartTime = $moment.AddSeconds(2)
Stop-RunProcesses $null $selected
Assert ($script:stoppedIds.Count -eq 0) 'must reject recycled PID with changed creation time'
$script:fakeProcesses += [pscustomobject]@{ Id=5; StartTime=$moment.AddSeconds(3); MainWindowTitle='target.inpx - VISSIM' }
Assert ($null -eq (Find-RunVissimIdentity @(1) $moment 'target.inpx')) 'ambiguous new instances must not be selected'
'PASS: positive-time startup detection, scoped termination, PID reuse and ambiguity'
