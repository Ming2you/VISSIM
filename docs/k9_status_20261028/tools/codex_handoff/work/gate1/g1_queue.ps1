# Gate 1 queue (Windows PowerShell 5.1, started detached by WMI at Normal priority). One step at a time, no VISSIM.
#  1) runner -PreflightOnly for s31, s41, s43 (B tuning) and s31gk (group-key tuning, replay input only) via the pwsh 7 wrapper
#  2) build the four T=900 replay inputs (g1_build_inputs.py, provenance = the preflight of the same seed and tuning)
#  3) replays R1 va_s31 (B), R2 va_s41 (B), R3 va_s43 (B), R4 va_s31gk (group keys), one at a time (g1_replay.ps1)
#  4) freeze_manifest.py verify FRZ_B0 (read-only) after the replays
#  5) g1_summary.py
# Stops (no further step) if C: or D: < 8 GB. A replay still running after 7,200 s is stopped (own process tree only) and
# recorded as stopped_cap. Kills nothing else. Writes work/gate1/queue_g1.state.txt and gate1/... outputs.
$W = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\gate1'
$G1 = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\gate1'
$FRZ = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\b0\frozen\sdmpc31_a49981ff_202610260258'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$PWSH = 'C:\Users\TRLAB\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$hsw = 'OPENBLAS_CORETYPE=Haswell;NPY_DISABLE_CPU_FEATURES=AVX512F AVX512CD AVX512_SKX AVX512_CLX;NUMBA_CPU_NAME=haswell'
$B_TUN = 'diagnostics\b0_v3c3\config_b0_v3c3.json'
$GK_TUN = 'diagnostics\b0_v3c3\config_b0_v3c3_groupkeys.json'
$CAP = 7200
$stateFile = Join-Path $W 'queue_g1.state.txt'
function Note([string]$m) { ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz') + ' ' + $m) | Add-Content -Encoding UTF8 $stateFile }
function DiskOk {
  $c = [math]::Round((Get-PSDrive C).Free / 1GB, 1); $d = [math]::Round((Get-PSDrive D).Free / 1GB, 1)
  if ($c -lt 8 -or $d -lt 8) { Note "STOP: disk C=$c D=$d GB"; 'stop disk' | Set-Content -Encoding UTF8 (Join-Path $W 'queue_g1.stop'); return $false }
  Note "disk C=$c D=$d GB"; return $true
}
function Descendants([int]$Root) {
  $all = @(Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId)
  $out = @($Root); $frontier = @($Root)
  while ($frontier.Count) {
    $next = @($all | Where-Object { $frontier -contains $_.ParentProcessId } | ForEach-Object { [int]$_.ProcessId })
    $out += $next; $frontier = $next
  }
  return $out
}
$env:PYTHONHASHSEED = '0'; $env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'
Note ('start wrapper_pid=' + $PID + ' priority=' + (Get-Process -Id $PID).PriorityClass)
if (-not (DiskOk)) { exit 2 }
# 1) preflights
$pf = @(@{ seed = 31; tag = ''; tun = $B_TUN }, @{ seed = 41; tag = ''; tun = $B_TUN }, @{ seed = 43; tag = ''; tun = $B_TUN }, @{ seed = 31; tag = 'gk'; tun = $GK_TUN })
foreach ($x in $pf) {
  if (-not (DiskOk)) { exit 2 }
  $a = @('-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $W 'g1_preflight_wrapper.ps1'), '-Seed', [string]$x.seed, '-TuningRel', $x.tun.Replace('\', '/'))
  if ($x.tag -ne '') { $a += @('-Tag', $x.tag) }
  $p = Start-Process -FilePath $PWSH -ArgumentList $a -WindowStyle Hidden -PassThru
  $null = $p.Handle
  Note ("preflight s" + $x.seed + $x.tag + " start pid=" + $p.Id)
  $p.WaitForExit()
  Note ("preflight s" + $x.seed + $x.tag + " end exit=" + $p.ExitCode)
}
# 2) inputs
$items = @(@{ id = 'R1'; src = 'va_s31'; pre = 's31'; tun = $B_TUN }, @{ id = 'R2'; src = 'va_s41'; pre = 's41'; tun = $B_TUN },
           @{ id = 'R3'; src = 'va_s43'; pre = 's43'; tun = $B_TUN }, @{ id = 'R4'; src = 'va_s31gk'; pre = 's31gk'; tun = $GK_TUN })
$built = @{}
foreach ($it in $items) {
  $seed = [int]($it.pre -replace '^s(\d+).*$', '$1')
  $prov = Join-Path $G1 ('runner_preflight\' + $it.pre + '\sdmpc\preflight\run_provenance_sdmpc31_sdmpc9000_s' + $seed + '.json')
  if (-not (Test-Path -LiteralPath $prov)) { Note ("build " + $it.id + " SKIP: no preflight provenance " + $prov); $built[$it.id] = $false; continue }
  $log = Join-Path $W ('build_' + $it.id + '.txt')
  & $PY -B (Join-Path $W 'g1_build_inputs.py') ('--preflight=' + $prov.Replace('\', '/')) $it.src 900 > $log 2>&1
  $built[$it.id] = ($LASTEXITCODE -eq 0)
  Note ("build " + $it.id + " src=" + $it.src + " exit=" + $LASTEXITCODE)
}
# 3) replays, one at a time
foreach ($it in $items) {
  if (-not $built[$it.id]) { Note ("replay " + $it.id + " SKIP: inputs not built"); continue }
  if (-not (DiskOk)) { exit 2 }
  $label = 'g1' + $it.id
  $a = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $W 'g1_replay.ps1'), '-T', '900', '-Src', $it.src, '-Label', $label,
         '-TuningRel', $it.tun, '-Priority', 'Normal', '-ExtraEnv', ('"' + $hsw + '"'), '-Note', ('"gate1 ' + $it.id + ' T=900 replay"'))
  $p = Start-Process -FilePath 'powershell.exe' -ArgumentList $a -WindowStyle Hidden -PassThru
  $null = $p.Handle
  $t0 = Get-Date
  Note ("$label start src=" + $it.src + " tuning=" + $it.tun + " child_pid=" + $p.Id)
  $capped = $false
  while (-not $p.HasExited) {
    Start-Sleep -Seconds 20
    if (((Get-Date) - $t0).TotalSeconds -gt $CAP -and -not $p.HasExited) {
      $tree = Descendants $p.Id
      Note ("$label CAP: running > $CAP s; stopping own PIDs " + ($tree -join ','))
      foreach ($k in ($tree | Sort-Object -Descending)) { try { Stop-Process -Id $k -Force -ErrorAction Stop } catch {} }
      $capped = $true
      break
    }
  }
  Note ("$label end exit=" + $(if ($capped) { 'stopped_cap' } else { $p.ExitCode }) + " wall=" + [math]::Round(((Get-Date) - $t0).TotalSeconds, 1))
}
# 4) freeze verify after the replays (read-only)
$fv = Join-Path $G1 'freeze_verify_after.txt'
& $PY -B (Join-Path $FRZ 'diagnostics\sdmpc_n31_20260924\tools\freeze_manifest.py') verify $FRZ > $fv 2>&1
Note ("freeze verify after replays exit=" + $LASTEXITCODE)
# 5) summary
& $PY -B (Join-Path $W 'g1_summary.py') (Join-Path $W 'gate1_summary.json') > (Join-Path $W 'gate1_summary.out.txt') 2>&1
Note ("summary exit=" + $LASTEXITCODE)
'done' | Set-Content -Encoding UTF8 (Join-Path $W 'queue_g1.done')
Note 'done'
