$ErrorActionPreference = 'Stop'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONUTF8 = '1'
$env:PYTHONPATH = 'C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.review-deps/sdmpc'
$pythonPath = 'C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$resultRoot = Join-Path $PSScriptRoot 'cdf_cap_candidate'
if (-not (Test-Path -LiteralPath (Join-Path $resultRoot 'completion.json'))) {
    if (Test-Path -LiteralPath (Join-Path $resultRoot 'launch.json')) {
        throw 'An existing forecast launch must be inspected; this entry point never retries it.'
    }
    & $pythonPath (Join-Path $PSScriptRoot 'run_cdf_cap_candidate.py')
    if ($LASTEXITCODE -ne 0) { throw 'Forecast stopped; preserve records and inspect without automatic retry.' }
}
if (-not (Test-Path -LiteralPath (Join-Path $resultRoot 'assessment.json'))) {
    & $pythonPath (Join-Path $PSScriptRoot 'assess_cdf_cap_candidate.py')
    if ($LASTEXITCODE -ne 0) { throw 'Assessment stopped; preserve records and inspect.' }
}
Get-Content -LiteralPath (Join-Path $resultRoot 'assessment.json') -Raw -Encoding UTF8
