# FO gate queue (PRE_FO s4; Windows PowerShell 5.1, started detached by WMI at BELOW_NORMAL). One step at a time, no VISSIM.
# Derived from work/gate1/g1_queue.ps1 (7b41d3d8..., gate 1 of B). Steps:
#  0) FRZ_FO FREEZE.json sha == -FrzSha and freeze verify FRZ_FO (FREEZE_VERIFIED) before anything
#  1) build the four T=900 replay inputs from the recorded B states (fog_build_inputs.py; provenance = the FO preflight of the
#     same seed and tuning made by the build chain): R1 b_s31, R2 b_s41, R3 b_s43 (FO config), R0 b_s31b (B config control)
#  2) replays R1, R2, R3, R0, one at a time, each under the shared heavy lock D:\VISSIM-merge\k8_gate_trees\heavy.lock
#     (exclusive create, retry 30 s, give up after 60 min -> stop; delete only our own token; >= 25 s pause after release).
#     A replay still running after 7,200 s is stopped (own process tree only) and recorded as stopped_cap (not a pass).
#  3) freeze verify FRZ_FO after the replays; 4) G2 (fog_sg_native.py gate) for R1-R3; 5) fog_summary.py
# Stops (no further step) if C: or D: < 8 GB. Kills nothing else. Writes work/gate/queue_fog.state.txt and fo/gate/ outputs.
param([Parameter(Mandatory=$true)][string]$Frz, [Parameter(Mandatory=$true)][string]$FrzSha)
$W = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\fo\work\gate'
$G = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\fo\gate'
$FOR = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\fo'
$LOCK = 'D:\VISSIM-merge\k8_gate_trees\heavy.lock'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$hsw = 'OPENBLAS_CORETYPE=Haswell;NPY_DISABLE_CPU_FEATURES=AVX512F AVX512CD AVX512_SKX AVX512_CLX;NUMBA_CPU_NAME=haswell'
$FO_TUN = 'diagnostics\b0_v3c3\config_fo_v3c3.json'
$B_TUN = 'diagnostics\b0_v3c3\config_b0_v3c3.json'
$CAP = 7200
$FMREL = 'diagnostics\sdmpc_n31_20260924\tools\freeze_manifest.py'
$stateFile = Join-Path $W 'queue_fog.state.txt'
$TOKEN = 'fo_gate-' + $PID + '-' + [guid]::NewGuid().ToString('N')
$script:haveLock = $false
function Note([string]$m) { ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST ' + $m) | Add-Content -Encoding UTF8 $stateFile }
function Release-Lock {
  if (-not $script:haveLock) { return }
  try { $t = [IO.File]::ReadAllText($LOCK); if ($t -like ('*' + $TOKEN + '*')) { Remove-Item -LiteralPath $LOCK -Force; Note 'lock released (own token)' } else { Note 'lock NOT released: token differs' } } catch { Note ('lock release error: ' + [string]$_) }
  $script:haveLock = $false
  Start-Sleep -Seconds 25
}
function Stop-Queue([string]$why) { Note ('STOP: ' + $why); $why | Set-Content -Encoding UTF8 (Join-Path $W 'queue_fog.stop'); Release-Lock; exit 2 }
function Acquire-Lock([string]$job) {
  $t0 = Get-Date
  while ($true) {
    try {
      $fs = [IO.File]::Open($LOCK, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
      $body = '{"owner": "fo_gate", "pid": ' + $PID + ', "token": "' + $TOKEN + '", "started_kst": "' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST", "job": "' + $job + '"}'
      $b = (New-Object System.Text.UTF8Encoding $false).GetBytes($body); $fs.Write($b, 0, $b.Length); $fs.Dispose()
      $script:haveLock = $true; Note ('lock acquired for ' + $job + ' after ' + [int]((Get-Date) - $t0).TotalSeconds + ' s'); return $true
    } catch {
      if (((Get-Date) - $t0).TotalMinutes -gt 60) { return $false }
      $holder = ''; try { $holder = [IO.File]::ReadAllText($LOCK) } catch {}
      Note ('lock busy, retry in 30 s; holder=' + $holder)
      Start-Sleep -Seconds 30
    }
  }
}
function DiskOk {
  $c = [math]::Round((Get-PSDrive C).Free / 1GB, 1); $d = [math]::Round((Get-PSDrive D).Free / 1GB, 1)
  if ($c -lt 8 -or $d -lt 8) { Note "STOP: disk C=$c D=$d GB"; return $false }
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
function Run-Py([string[]]$argList, [string]$outFile) {
  $p = Start-Process -FilePath $PY -ArgumentList $argList -NoNewWindow -PassThru -Wait -RedirectStandardOutput $outFile -RedirectStandardError ($outFile + '.err')
  return $p.ExitCode
}
$env:PYTHONHASHSEED = '0'; $env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'
try {
  Note ('start pid=' + $PID + ' priority=' + (Get-Process -Id $PID).PriorityClass + ' token=' + $TOKEN + ' frz=' + $Frz)
  Note ('VISSIM now (not ours, untouched): ' + ((@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^Vissim' }) | ForEach-Object { $_.ProcessId }) -join ','))
  if (-not (DiskOk)) { Stop-Queue 'disk < 8 GB' }
  # 0
  $fsha = (Get-FileHash -LiteralPath (Join-Path $Frz 'FREEZE.json') -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($fsha -ne $FrzSha) { Stop-Queue "FRZ_FO FREEZE.json sha $fsha != $FrzSha" }
  $c = Run-Py @('-B', ('"' + (Join-Path $Frz $FMREL) + '"'), 'verify', ('"' + $Frz + '"')) (Join-Path $G 'freeze_verify_before.txt')
  Note ('freeze verify before exit=' + $c)
  if ($c) { Stop-Queue 'freeze verify before failed' }
  # 1
  $items = @(@{ id = 'R1'; src = 'b_s31'; pre = 's31'; tun = $FO_TUN }, @{ id = 'R2'; src = 'b_s41'; pre = 's41'; tun = $FO_TUN },
             @{ id = 'R3'; src = 'b_s43'; pre = 's43'; tun = $FO_TUN }, @{ id = 'R0'; src = 'b_s31b'; pre = 's31b'; tun = $B_TUN })
  $built = @{}
  foreach ($it in $items) {
    $seed = [int]($it.pre -replace '^s(\d+).*$', '$1')
    $prov = Join-Path $FOR ('runner_preflight\' + $it.pre + '\sdmpc\preflight\run_provenance_sdmpc31_sdmpc9000_s' + $seed + '.json')
    if (-not (Test-Path -LiteralPath $prov)) { Note ("build " + $it.id + " SKIP: no preflight provenance " + $prov); $built[$it.id] = $false; continue }
    $c = Run-Py @('-B', ('"' + (Join-Path $W 'fog_build_inputs.py') + '"'), ('"--preflight=' + $prov.Replace('\', '/') + '"'), ('"--frz=' + $Frz + '"'), $it.src, '900') (Join-Path $W ('build_' + $it.id + '.txt'))
    $built[$it.id] = ($c -eq 0)
    Note ("build " + $it.id + " src=" + $it.src + " exit=" + $c)
  }
  # 2
  foreach ($it in $items) {
    if (-not $built[$it.id]) { Note ("replay " + $it.id + " SKIP: inputs not built"); continue }
    if (-not (DiskOk)) { Stop-Queue 'disk < 8 GB' }
    $label = 'fog' + $it.id
    if (-not (Acquire-Lock ('FO gate replay ' + $it.id + ' T=900'))) { Stop-Queue ('heavy lock not acquired within 60 min for ' + $it.id) }
    $a = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + (Join-Path $W 'fog_replay.ps1') + '"'), '-T', '900', '-Src', $it.src, '-Label', $label,
           '-TuningRel', $it.tun, '-Frz', ('"' + $Frz + '"'), '-Priority', 'BelowNormal', '-ExtraEnv', ('"' + $hsw + '"'), '-Note', ('"FO gate ' + $it.id + ' T=900 replay"'))
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
    Release-Lock
  }
  # 3
  $c = Run-Py @('-B', ('"' + (Join-Path $Frz $FMREL) + '"'), 'verify', ('"' + $Frz + '"')) (Join-Path $G 'freeze_verify_after.txt')
  Note ("freeze verify after replays exit=" + $c)
  # 4
  foreach ($it in @($items | Where-Object { $_.id -ne 'R0' })) {
    $seed = [int]($it.pre -replace '^s(\d+).*$', '$1')
    $act = Join-Path $G ('out\fog' + $it.id + '\' + $it.src + '\T000900\files\decisions_sdmpc31_sdmpc9000_s' + $seed + '\action_000900.csv')
    if (-not (Test-Path -LiteralPath $act)) { Note ("G2 " + $it.id + " SKIP: no replay action csv"); continue }
    $c = Run-Py @('-B', ('"' + (Join-Path $W 'fog_sg_native.py') + '"'), 'gate', [string]$seed, ('"' + $act + '"'), ('"' + (Join-Path $W ('g2_' + $it.id + '.json')) + '"'), ('"' + $Frz + '"')) (Join-Path $W ('g2_' + $it.id + '.out.txt'))
    Note ("G2 " + $it.id + " exit=" + $c)
  }
  # 5
  $c = Run-Py @('-B', ('"' + (Join-Path $W 'fog_summary.py') + '"'), ('"' + $Frz + '"'), ('"' + (Join-Path $W 'fog_summary.json') + '"')) (Join-Path $W 'fog_summary.out.txt')
  Note ("summary exit=" + $c)
  'done' | Set-Content -Encoding UTF8 (Join-Path $W 'queue_fog.done')
  Note 'done'
} catch {
  Stop-Queue ('exception: ' + [string]$_)
}
