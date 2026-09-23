# Sequential native seed sweep: none/rm x seeds {31,37,41}. VISSIM is single-instance.
$ErrorActionPreference = 'Stop'
$root = 'D:\VISSIM_runs\20260922_seedvar'
$runner = 'D:\VISSIM-merge\sim3\diagnostics\fast_nc_run.ps1'
$state = Join-Path $root 'sweep_status.json'
$results = @()
foreach ($seed in 31,37,41) {
  foreach ($arm in 'none','rm') {
    $tag = "s${seed}_${arm}"
    $prep = Join-Path $root "$tag\prepared"
    $out  = Join-Path $root "$tag\run"
    $log  = Join-Path $root "$tag\launch.log"
    if (Test-Path $out) { Write-Output "SKIP $tag (output exists)"; continue }
    if (@(Get-Process -Name 'VISSIM*' -ErrorAction SilentlyContinue).Count) { throw "VISSIM already running; refusing to overlap before $tag" }
    Write-Output "START $tag $(Get-Date -Format o)"
    $t0 = Get-Date
    $global:LASTEXITCODE = 0
    & $runner -Prepared $prep -Output $out -Execute -MinimumFreeGiB 8 *> $log
    $exit = $LASTEXITCODE
    $mins = [math]::Round(((Get-Date)-$t0).TotalMinutes,1)
    $receipt = $null
    if (Test-Path (Join-Path $out 'run.json')) { $receipt = Get-Content (Join-Path $out 'run.json') -Raw -Encoding UTF8 | ConvertFrom-Json }
    $ok = ($null -ne $receipt -and $receipt.completed)
    $results += [pscustomobject]@{tag=$tag; seed=$seed; arm=$arm; exit=$exit; minutes=$mins; completed=$ok; error=$(if($receipt){$receipt.error})}
    $results | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $state -Encoding UTF8
    Write-Output "DONE  $tag exit=$exit completed=$ok minutes=$mins"
    if (-not $ok) { Write-Output "FAILED $tag - preserved, continuing to next" }
  }
}
Write-Output "SWEEP_COMPLETE"
$results | Format-Table -AutoSize
