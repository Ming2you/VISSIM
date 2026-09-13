param([Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
$testRoot = Split-Path $PSScriptRoot -Parent
$testOutput = [IO.Path]::GetFullPath((Join-Path $testRoot $OutputDirectory))
if (-not $testOutput.StartsWith(([IO.Path]::GetFullPath($PSScriptRoot) + [IO.Path]::DirectorySeparatorChar),[StringComparison]::OrdinalIgnoreCase)) { throw 'Output must be under diagnostics' }
if (Test-Path -LiteralPath $testOutput) { throw 'Historical output already exists' }
New-Item -ItemType Directory -Path $testOutput | Out-Null
$testGate = Join-Path $PSScriptRoot 'run_flat_network_native_gate.ps1'
$testTokens = $null; $testErrors = $null
$testAst = [Management.Automation.Language.Parser]::ParseFile($testGate,[ref]$testTokens,[ref]$testErrors)
if ($testErrors.Count) { throw 'Gate PowerShell syntax is invalid' }
$testTry = @($testAst.FindAll({param($node) $node -is [Management.Automation.Language.TryStatementAst] -and $node.Body.Extent.Text.Contains('$armProcess = Start-Process')},$true) | Sort-Object { $_.Extent.Text.Length })[0]
if ($null -eq $testTry) { throw 'Actual gate lifecycle not found' }
$testBody = $testTry.Body.Extent.Text
$testFinally = $testTry.Finally.Extent.Text
$testCut = $testFinally.IndexOf('$armCleanupDeadline =')
if ($testCut -lt 0) { throw 'Actual capture boundary not found' }
$testArgumentsNode = @($testTry.Body.Statements | Where-Object { $_ -is [Management.Automation.Language.AssignmentStatementAst] -and $_.Left.Extent.Text -eq '$armArguments' })
if ($testArgumentsNode.Count -ne 1) { throw 'Actual child argument boundary changed' }
# Substitute only the child executable/arguments. cscript's script engine can
# be disabled by host policy; the Process lifetime under test is unchanged.
$testBody = $testBody.Replace($testArgumentsNode[0].Extent.Text,'# Tiny PowerShell child arguments supplied by fixture').Replace("'cscript.exe'","'powershell.exe'")
$testLaunch = [ScriptBlock]::Create($testBody.Substring(1,$testBody.Length-2))
$testCapture = [ScriptBlock]::Create($testFinally.Substring(1,$testCut-1))
# No COM API is called. These functions cover only the unused VISSIM cleanup
# boundary; launch/poll/handle/WaitForExit/ExitCode are the actual gate source.
function Find-RunVissimIdentity { return $null }
function Test-GateIdentityAlive { param($identity) return $false }
function Stop-RunProcesses { throw 'Unexpected cleanup in tiny completed-child test' }
$testRows = @()
foreach ($testExit in @(0,7)) {
    $testStem = Join-Path $testOutput ('exit_' + $testExit)
    $armArguments = @('-NoProfile','-NonInteractive','-Command',('"Start-Sleep -Milliseconds 250; exit ' + $testExit + '"'))
    $armEvidence = [pscustomobject]@{ network_path='unused-no-network' }
    $armCsv = $testStem + '.unused.csv'; $armLog = $testStem + '.stdout.txt'; $armErr = $testStem + '.stderr.txt'
    $armProcess = $null; $armRunnerIdentity = $null; $armVissim = $null
    $armExisting = @(); $gateArm='tiny-no-COM'; $armStart=Get-Date
    $armTimedOut=$false; $armError=$null; $armExit=$null
    try { . $testLaunch } catch { $armError=$_.Exception.Message } finally { . $testCapture }
    $testRows += [ordered]@{ expected=$testExit; actual=$armExit; exact=($null -ne $armExit -and $armExit -eq $testExit); error=$armError; has_exited=$armProcess.HasExited; handle_nonzero=($armProcessHandle -ne [IntPtr]::Zero) }
    $armProcess.Dispose()
}
$testSha=(Get-FileHash -LiteralPath $testGate -Algorithm SHA256).Hash.ToLowerInvariant()
$testResult=[ordered]@{ schema='native-gate-actual-exit-test/v1'; powershell=$PSVersionTable.PSVersion.ToString(); actual_source_sha256=$testSha; actual_source_path='diagnostics/run_flat_network_native_gate.ps1'; child_invocation_substitution='powershell.exe exit 0/7 only; actual launch options, handle, polling and capture source retained'; syntax_errors=0; com_executed=$false; model_executed=$false; rows=$testRows; passed=(@($testRows | Where-Object { -not $_.exact -or $_.error -or -not $_.has_exited }).Count -eq 0) }
$testJson=$testResult | ConvertTo-Json -Depth 8
[IO.File]::WriteAllText((Join-Path $testOutput 'result.json'),$testJson,(New-Object Text.UTF8Encoding($false)))
$testJson
if (-not $testResult.passed) { throw 'Actual gate exit-code test failed' }
