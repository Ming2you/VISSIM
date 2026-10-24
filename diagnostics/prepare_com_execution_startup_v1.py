"""Emit an unapplied two-file startup evidence patch. No model or COM imports."""
from pathlib import Path
import difflib
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
VBS = 'scripts/run_real_world_stackelberg_controller.vbs'
PS = 'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1'

MARKER = '''Sub RecordStartupSimulationProgress()
    Dim actualSec
    actualSec = SafeAtt(Vissim.Simulation, "SimSec")
    If Not IsFiniteNumberInRange(actualSec, 0.000001, CDbl(simPeriod) + 1.0) Then
        Err.Raise 513, , "First native step did not return a positive simulation time"
    End If
    ' Actual native readback, before initialization/observation/controller work.
    WScript.Echo "NATIVE_SIM_PROGRESS sim_sec=" & Num(CDbl(actualSec))
End Sub

'''

STARTED = '''function Test-SimulationStarted([string]$CsvPath, [string]$LogPath = '') {
  # Only exact ASCII actual-time markers count; stream until a marker or EOF.
  # Startup demand/ordinary log writes do not reset the 300-second deadline.
  # Starting from the beginning retains the marker during a long first decision.
  if ($LogPath -and (Test-Path -LiteralPath $LogPath -PathType Leaf)) {
    $stream = $null; $reader = $null
    try {
      $stream = [IO.File]::Open($LogPath, [IO.FileMode]::Open, [IO.FileAccess]::Read,
        [IO.FileShare]::ReadWrite)
      $reader = [IO.StreamReader]::new($stream, [Text.Encoding]::ASCII, $false)
      while ($null -ne ($line = $reader.ReadLine())) {
        if ($line -cnotmatch '^NATIVE_SIM_PROGRESS sim_sec=([0-9]+(?:\\.[0-9]+)?)$') { continue }
        $sampleTime = 0.0
        if ([double]::TryParse($Matches[1], [Globalization.NumberStyles]::Float,
            [Globalization.CultureInfo]::InvariantCulture, [ref]$sampleTime) -and
            -not [double]::IsNaN($sampleTime) -and -not [double]::IsInfinity($sampleTime) -and
            $sampleTime -gt 0) { return $true }
      }
    } catch [IO.IOException] {
      # A concurrent open/append can be retried on the next existing poll.
    } finally {
      if ($null -ne $reader) { $reader.Dispose() }
      elseif ($null -ne $stream) { $stream.Dispose() }
    }
  }
  # Preserve the actual state-clock fallback, excluding nonfinite numbers.
  if (-not (Test-Path -LiteralPath $CsvPath -PathType Leaf)) { return $false }
  foreach ($line in (Get-Content -LiteralPath $CsvPath -Tail 4 -ErrorAction SilentlyContinue)) {
    $sampleTime = 0.0
    if ([double]::TryParse(($line -split ',',2)[0], [Globalization.NumberStyles]::Float,
        [Globalization.CultureInfo]::InvariantCulture, [ref]$sampleTime) -and
        -not [double]::IsNaN($sampleTime) -and -not [double]::IsInfinity($sampleTime) -and
        $sampleTime -gt 0) { return $true }
  }
  return $false
}
'''


def main():
    vbs = (ROOT / VBS).read_text(encoding='utf-8')
    ps = (ROOT / PS).read_text(encoding='utf-8-sig')
    old_started = ps[ps.index('function Test-SimulationStarted('):ps.index('\nfunction Find-RunVissimIdentity(')]
    targets = [
        (VBS, vbs, [
            {'old': 'Sub RunStepwiseMode()\n', 'new': MARKER + 'Sub RunStepwiseMode()\n', 'count': 1},
            {'old': '    InitializeComRampMeterControl\n',
             'new': '    RecordStartupSimulationProgress\n    InitializeComRampMeterControl\n', 'count': 3},
        ]),
        (PS, ps, [
            {'old': old_started, 'new': STARTED, 'count': 1},
            {'old': '$simulationStarted = Test-SimulationStarted $stateCsv',
             'new': '$simulationStarted = Test-SimulationStarted $stateCsv $log', 'count': 1},
        ]),
    ]
    records, patches = [], []
    for target, original, edits in targets:
        changed = original
        for edit in edits:
            assert changed.count(edit['old']) == edit['count'], (target, edit['old'])
            changed = changed.replace(edit['old'], edit['new'])
        records.append({'target': target,
                        'source_sha256': hashlib.sha256((ROOT / target).read_bytes()).hexdigest(),
                        'edits': edits})
        patches.extend(difflib.unified_diff(original.splitlines(True), changed.splitlines(True),
                       fromfile='a/' + target, tofile='b/' + target))
    doc = {'schema': 'canonical-com-startup-edit/v1', 'applied': False, 'targets': records,
           'integration': 'Apply these exact replacement edits after or before writer/timing/VSL edits; these markers precede InitializeComRampMeterControl in all three modes. Standalone patch targets frozen original bytes.',
           'scope': 'Three call sites, exactly one extra actual SimSec read per run. No vehicles, extra steps, model changes, timer resets, process cleanup changes, or production writes.',
           'log_scope': 'Startup-only streaming from the first line until a valid marker or current EOF, FileShare.ReadWrite. No byte cap or Tail loss. Caller already latches simulationStarted and stops further reads. Existing completed source/run01 marker offsets 4402/36343 bytes.',
           'new_marker': 'NATIVE_SIM_PROGRESS sim_sec=<existing Num(actual SimSec)>',
           'limitations': 'Does not make the existing 20-second polling interval an exact wall-time deadline; does not replace later StallSec activity monitoring.'}
    (ROOT / 'diagnostics/com_execution_startup_edits_v1.json').write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    (ROOT / 'diagnostics/com_execution_startup_v1.patch').write_text(
        ''.join(patches), encoding='utf-8', newline='\n')
    print(json.dumps({'applied': False, 'target_sha256': {r['target']: r['source_sha256'] for r in records}}))


if __name__ == '__main__':
    main()
