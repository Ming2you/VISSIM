$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Utility\Microsoft.PowerShell.Utility.psd1') -ErrorAction Stop
$runner = Join-Path $PSScriptRoot '../scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1'
$tokens = $null; $parseErrors = $null
$tree = [Management.Automation.Language.Parser]::ParseFile($runner, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
foreach ($name in @('Read-RampMeterTimingSettings', 'Set-RampMeterTimingTransport')) {
    $definition = $tree.Find({ param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name }, $true)
    if (-not $definition) { throw "Missing helper $name" }
    . ([scriptblock]::Create($definition.Extent.Text))
}
function Assert($condition, $message) { if (-not $condition) { throw $message } }
function Reject($code, $message) {
    $rejected = $false
    try { & $code } catch { $rejected = $true }
    Assert $rejected $message
}
$directory = Join-Path $env:TEMP ('ramp_timing_test_' + [guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $directory
$child = Join-Path $directory 'child.json'; $parent = Join-Path $directory 'parent.json'
$old = [Environment]::GetEnvironmentVariable('RW_RAMP_AMBER_SEC','Process')
try {
    [IO.File]::WriteAllText($child, '{}')
    $default = Read-RampMeterTimingSettings $child
    Assert ($default.amber_sec -eq 1 -and -not $default.declared) 'absent must preserve legacy1'
    Assert ($default.config_chain.Count -eq 1 -and $default.config_chain[0].sha256.Length -eq 64) 'config hash missing'
    $env:RW_RAMP_AMBER_SEC = '0'
    Set-RampMeterTimingTransport $child $default
    Assert ($env:RW_RAMP_AMBER_SEC -ceq '1') 'inherited env must not override absent config'
    [IO.File]::WriteAllText($parent, '{"actuation":{"real_world_ramp_metering":{"amber_sec":0}}}')
    [IO.File]::WriteAllText($child, '{"extends":"parent.json"}')
    $inherited = Read-RampMeterTimingSettings $child
    Assert ($inherited.amber_sec -eq 0 -and $inherited.declared -and $inherited.config_chain.Count -eq 2) 'parent setting not resolved'
    $env:RW_RAMP_AMBER_SEC = 'garbage'
    Set-RampMeterTimingTransport $child $inherited
    Assert ($env:RW_RAMP_AMBER_SEC -ceq '0') 'config0 must explicitly reset inherited env'
    [IO.File]::WriteAllText($child, '{"extends":"parent.json","actuation":{"real_world_ramp_metering":{"amber_sec":1}}}')
    $override = Read-RampMeterTimingSettings $child
    Assert ($override.amber_sec -eq 1) 'child must override parent'
    Reject { Set-RampMeterTimingTransport $child $inherited } 'changed config must fail before launch'
    foreach ($invalid in @('2','-1','0.5','true','"0"','null','[]','{}')) {
        [IO.File]::WriteAllText($child, ('{"actuation":{"real_world_ramp_metering":{"amber_sec":' + $invalid + '}}}'))
        Reject { Read-RampMeterTimingSettings $child } "invalid numeric setting accepted: $invalid"
    }
    [IO.File]::WriteAllText($child, '{"extends":"parent.json"}')
    [IO.File]::WriteAllText($parent, '{"extends":"child.json"}')
    Reject { Read-RampMeterTimingSettings $child } 'cyclic extends accepted'
    Assert ((Read-RampMeterTimingSettings '').amber_sec -eq 1) 'empty tuning needs explicit legacy transport'
    'PASS: ramp amber config, inheritance, strict types, provenance binding and environment reset'
} finally {
    [Environment]::SetEnvironmentVariable('RW_RAMP_AMBER_SEC',$old,'Process')
    # Only this test's freshly created files are removed; no recursive deletion.
    Remove-Item -LiteralPath $child,$parent -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $directory -ErrorAction SilentlyContinue
}
