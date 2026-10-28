# make_launcher_fo.py (2026-10-27 KST, PRE_FO s5) - make the FO launcher package from the pinned B package by name changes,
# plus the declared FO additions, and write a unified diff of every file (record). Writes only into codex_handoff/fo/.
#   b_launcher.ps1 (cb657ecb) -> fo_launcher.ps1   b_wrapper_b1.ps1 (93814842) -> fo_wrapper.ps1   b_status.ps1 (f07a8f6b) -> fo_status.ps1
#   b_launcher_start.ps1 (9c818f1f) -> fo_launcher_start.ps1   b_launcher_dryrun.ps1 (fa5652b5) -> fo_launcher_dryrun.ps1
# Name changes (all files): B folder -> FO folder, B results root -> FO results root, FRZ_B1 -> FRZ_FO, B tuning -> FO tuning,
# b_wrapper_b1/b_launcher*/b_launch/STOP_B_LAUNCHER -> fo_*, 'PRE_B_CONCURRENT s' -> 'PRE_FO s', header words B -> FO.
# FO additions (declared in PRE_FO s5): launcher params -PreSha -RuleSha -PinsSha -GateSha (+ file params for the dry run),
# all four files join the FIXED sha list checked before every launch; the gate summary must say pass = true at start
# (else LAUNCH_STOPPED GATE_NOT_PASSED); FIXED B entries replaced by the FO ones (FREEZE d7fa4db6, config 80e0abef, wrapper);
# the start script checks the four shas too and passes them; the dry-run harness passes them and has two more cases.
# usage: python -B make_launcher_fo.py <wrapper_sha_placeholder_ok>
import difflib, hashlib, os, re, sys

SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
BD, FD = SP + '/codex_handoff/b', SP + '/codex_handoff/fo'
SRC = {'b_launcher.ps1': 'cb657ecbe0aa01fb810137422646fdba3c652191db7cc070c040058ae692d463',
       'b_wrapper_b1.ps1': '93814842ae7a504e714c309a58caf77621aba153db36fa953258db72db5a1185',
       'b_status.ps1': 'f07a8f6b9621f457b904e53cda83b422338bb1407ca0c9b6cf6b41528e2d3c37',
       'b_launcher_start.ps1': '9c818f1f4d5e6aadd338060e52e84b25f400e5741204cb41963cdf547b635c23',
       'b_launcher_dryrun.ps1': 'fa5652b59f56e1e3613b9ed5a482f45e9056aaf7b30d81b36e7339ab8ee6e7d1'}
DST = {'b_launcher.ps1': 'fo_launcher.ps1', 'b_wrapper_b1.ps1': 'fo_wrapper.ps1', 'b_status.ps1': 'fo_status.ps1',
       'b_launcher_start.ps1': 'fo_launcher_start.ps1', 'b_launcher_dryrun.ps1': 'fo_launcher_dryrun.ps1'}
BS = '\\'
NAMES = [
    ('k8' + BS + 'codex_handoff' + BS + 'b' + "'", 'k8' + BS + 'codex_handoff' + BS + 'fo' + "'"),
    ('k8' + BS + 'codex_handoff' + BS + 'b' + BS, 'k8' + BS + 'codex_handoff' + BS + 'fo' + BS),
    ('20261026_codex_b_v3c3', '20261028_codex_fo_v3c3'),
    ('codexhandoff' + BS + 'b1' + BS + 'frozen' + BS + 'sdmpc31_a49981ff_202610261410', 'codexhandoff' + BS + 'fo' + BS + 'frozen' + BS + 'sdmpc31_a49981ff_202610271954'),
    ('config_b0_v3c3.json', 'config_fo_v3c3.json'),
    ('b_wrapper_b1.ps1', 'fo_wrapper.ps1'),
    ('b/b_launcher_start_receipts.log', 'fo/fo_launcher_start_receipts.log'),
    ('b/b_launcher_dryrun.log', 'fo/fo_launcher_dryrun.log'),
    ('b_launcher_start_receipts.log', 'fo_launcher_start_receipts.log'),
    ('b_launcher_start.ps1', 'fo_launcher_start.ps1'),
    ('b_launcher_dryrun.ps1', 'fo_launcher_dryrun.ps1'),
    ('b_launcher_dryrun.log', 'fo_launcher_dryrun.log'),
    ('b_launcher.ps1', 'fo_launcher.ps1'),
    ('b_launcher.log', 'fo_launcher.log'),
    ("'b_launch'", "'fo_launch'"),
    ('b_launch' + BS, 'fo_launch' + BS),
    ('STOP_B_LAUNCHER', 'STOP_FO_LAUNCHER'),
    ('PRE_B_CONCURRENT s', 'PRE_FO s'),
    ('# B launcher (2026-10-26 KST, user decision D-K9-90; rules PRE_B_CONCURRENT.md 3d21dddd... s5-s7)',
     '# FO launcher (2026-10-27 KST, user decision D-K9-113; rules PRE_FO.md s5-s7; copy of the B launcher cb657ecb... with names changed)'),
    ('# B run status (2026-10-26)', '# FO run status (2026-10-27; copy of the B status script f07a8f6b... with names changed)'),
    ("'B_STATUS '", "'FO_STATUS '"),
    ('# Dry run of fo_launcher.ps1 (2026-10-26)', '# Dry run of fo_launcher.ps1 (2026-10-27; copy of the B dry-run harness fa5652b5... with names changed + FO cases)'),
    ('Launch = PRE_B s1 on FRZ_B1', 'Launch = PRE_B s1 on FRZ_FO with the FO config'),
    ('#     <root>/STOP_FO_LAUNCHER', '#     <root>/STOP_FO_LAUNCHER'),
]


def sha(b):
    return hashlib.sha256(b).hexdigest()


EOL = [chr(10)]
CRLF = chr(13) + chr(10)


def edit(text, old, new, count=1):
    old, new = old.replace(CRLF, EOL[0]), new.replace(CRLF, EOL[0])
    c = text.count(old)
    if c != count:
        raise SystemExit('edit must match %d time(s) (%d): %r' % (count, c, old[:90]))
    return text.replace(old, new)


def main():
    rec = []
    for src, want in SRC.items():
        raw = open(BD + '/' + src, 'rb').read()
        if sha(raw) != want:
            raise SystemExit('B source changed: ' + src)
        t = raw.decode('ascii')
        EOL[0] = CRLF if CRLF in t else chr(10)
        for a, b in NAMES:
            t = t.replace(a, b)
        if src == 'b_launcher.ps1':
            t = edit(t, "  [double]$GiveUpHours = 72\r\n)",
                     "  [double]$GiveUpHours = 72,\r\n  [string]$PreFile = '',\r\n  [string]$PreSha = '',\r\n  [string]$RuleFile = '',\r\n  [string]$RuleSha = '',\r\n"
                     "  [string]$PinsFile = '',\r\n  [string]$PinsSha = '',\r\n  [string]$GateFile = '',\r\n  [string]$GateSha = ''\r\n)")
            t = edit(t, "$FIXED[(Join-Path $SPB 'COMPARE_RULE_B.md')] = 'f902f7f0013bed0a0eb5dec27818e2bda4851995eae235130b7cb241e8b28f0c'\r\n"
                        "$FIXED[(Join-Path $SPB 'PINS_B.sha256')] = '5e8ffbc5cc192c25a15a07c11dda5036c7005b73c342aa16d1f7d6ed5e67d804'\r\n"
                        "$FIXED[(Join-Path $SPB 'PRE_B_CONCURRENT.md')] = '3d21dddd5cf4c75ba02dc826f6ea15370d21cf26062e7a328efbb5d15a243fef'\r\n"
                        "$FIXED[(Join-Path $FRZ 'FREEZE.json')] = '558de2c1b80799a9bedfb192b40b6f5cfa2775853b3431eb181f7b25beca10d1'\r\n"
                        "$FIXED[(Join-Path $FRZ 'diagnostics\\b0_v3c3\\config_fo_v3c3.json')] = '729640af754a90c8d7fbe8f81577b27bae02b86f1d504e18333c0fc99717f983'\r\n",
                     "$FIXED[(Join-Path $FRZ 'FREEZE.json')] = 'd7fa4db6c3ca854a3c6c7dfd352f97626d6f9ca9d0e5ea6f18e36fc779d37373'\r\n"
                     "$FIXED[(Join-Path $FRZ 'diagnostics\\b0_v3c3\\config_fo_v3c3.json')] = '80e0abefdb25526374c97d8f7a6b45b9ad434db1f3499cec208985038ac249f3'\r\n")
            t = edit(t, "$FIXED[$WRAPPER] = '93814842ae7a504e714c309a58caf77621aba153db36fa953258db72db5a1185'\r\n",
                     "$FIXED[$WRAPPER] = (Get-FileHash -LiteralPath $WRAPPER -Algorithm SHA256).Hash.ToLowerInvariant()   # FO: the start script checks it against -WrapperSha\r\n"
                     "# FO additions (PRE_FO s5): PRE_FO, COMPARE_RULE_FO, PINS_FO and the gate summary join the FIXED list (sha given at start)\r\n"
                     "$PAIRS4 = @(@('PreFile', $PreFile, $PreSha, 'PRE_FO.md'), @('RuleFile', $RuleFile, $RuleSha, 'COMPARE_RULE_FO.md'),\r\n"
                     "            @('PinsFile', $PinsFile, $PinsSha, 'PINS_FO.sha256'), @('GateFile', $GateFile, $GateSha, 'work\\gate\\fog_summary.json'))\r\n"
                     "foreach ($q in $PAIRS4) {\r\n"
                     "  $qf = [string]$q[1]; if (-not $qf) { $qf = Join-Path $SPB $q[3] }\r\n"
                     "  if ([string]$q[2] -notmatch '^[0-9a-f]{64}$') { throw ($q[0] + ' sha (64 hex) is required') }\r\n"
                     "  if ($script:LMODE -eq 'run' -and [IO.Path]::GetFullPath($qf) -ne (Join-Path $SPB $q[3])) { throw ('run mode ' + $q[0] + ' must be ' + (Join-Path $SPB $q[3])) }\r\n"
                     "  $FIXED[[IO.Path]::GetFullPath($qf)] = [string]$q[2]\r\n"
                     "  if ($q[0] -eq 'GateFile') { $GATE_PATH = [IO.Path]::GetFullPath($qf) }\r\n"
                     "}\r\n")
            t = edit(t, "  's seatwait=' + $SeatWaitHours + 'h giveup=' + $GiveUpHours + 'h first_start=' + (Read-Json $fsPath).time + ' stop=' + (Get-StopReason) + ' ps=' + $PSVersionTable.PSVersion.ToString())\r\n",
                     "  's seatwait=' + $SeatWaitHours + 'h giveup=' + $GiveUpHours + 'h first_start=' + (Read-Json $fsPath).time + ' stop=' + (Get-StopReason) + ' ps=' + $PSVersionTable.PSVersion.ToString() +\r\n"
                     "  ' pre=' + $PreSha + ' rule=' + $RuleSha + ' pins=' + $PinsSha + ' gate=' + $GateSha)\r\n"
                     "# FO addition (PRE_FO s5): no launch unless the T=900 gate summary says pass = true (its sha is in FIXED as well)\r\n"
                     "$gj = Read-Json $GATE_PATH\r\n"
                     "if (-not $gj -or $gj.pass -ne $true) { Set-Stop 'GATE_NOT_PASSED' ('gate summary pass is not true: ' + $GATE_PATH) }\r\n"
                     "$bad0 = Test-Fixed; if ($bad0) { Set-Stop 'SHA_MISMATCH' $bad0 }\r\n")
        if src == 'b_launcher_start.ps1':
            t = edit(t, "param([Parameter(Mandatory = $true)][string]$LauncherSha, [Parameter(Mandatory = $true)][string]$WrapperSha)\r\n",
                     "param([Parameter(Mandatory = $true)][string]$LauncherSha, [Parameter(Mandatory = $true)][string]$WrapperSha,\r\n"
                     "      [Parameter(Mandatory = $true)][string]$PreSha, [Parameter(Mandatory = $true)][string]$RuleSha,\r\n"
                     "      [Parameter(Mandatory = $true)][string]$PinsSha, [Parameter(Mandatory = $true)][string]$GateSha)\r\n")
            t = edit(t, "$running = @(",
                     "foreach ($q in @(@('PRE_FO.md', $PreSha), @('COMPARE_RULE_FO.md', $RuleSha), @('PINS_FO.sha256', $PinsSha), @('work\\gate\\fog_summary.json', $GateSha))) {\r\n"
                     "  $hq = (Get-FileHash -LiteralPath (Join-Path $SPB $q[0]) -Algorithm SHA256).Hash.ToLowerInvariant(); if ($hq -ne $q[1]) { throw ($q[0] + ' sha ' + $hq + ' != ' + $q[1]) }\r\n"
                     "}\r\n"
                     "$gate = Get-Content -LiteralPath (Join-Path $SPB 'work\\gate\\fog_summary.json') -Raw -Encoding UTF8 | ConvertFrom-Json\r\n"
                     "if ($gate.pass -ne $true) { throw 'the T=900 gate summary does not say pass = true; no start (PRE_FO s4)' }\r\n"
                     "$running = @(")
            t = edit(t, "-File \"' + $L + '\" -Mode run'",
                     "-File \"' + $L + '\" -Mode run -PreSha ' + $PreSha + ' -RuleSha ' + $RuleSha + ' -PinsSha ' + $PinsSha + ' -GateSha ' + $GateSha")
        if src == 'b_launcher_dryrun.ps1':
            t = edit(t, "function Invoke-Launcher([string]$root, [string]$log, [string]$scen) {\r\n"
                        "  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $L -Mode dryrun -Root $root -Log $log -Scenario $scen -PollSec 0 -VissimUpWaitSec 3 | Out-Null\r\n",
                     "# FO addition: every dry-run root gets its own PRE / rule / pins / gate files (_fixed\\...) and passes their shas.\r\n"
                     "function Invoke-Launcher([string]$root, [string]$log, [string]$scen, [string]$gateText = '{\"pass\": true}') {\r\n"
                     "  $fx = Join-Path $root '_fixed'; New-Item -ItemType Directory -Force -Path $fx | Out-Null\r\n"
                     "  $files = [ordered]@{ Pre = 'PRE_FO.md'; Rule = 'COMPARE_RULE_FO.md'; Pins = 'PINS_FO.sha256'; Gate = 'fog_summary.json' }\r\n"
                     "  $a = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $L, '-Mode', 'dryrun', '-Root', $root, '-Log', $log, '-Scenario', $scen, '-PollSec', '0', '-VissimUpWaitSec', '3')\r\n"
                     "  foreach ($k in $files.Keys) {\r\n"
                     "    $p = Join-Path $fx $files[$k]\r\n"
                     "    if (-not (Test-Path -LiteralPath $p)) { $body = 'dryrun ' + $k; if ($k -eq 'Gate') { $body = $gateText }; [IO.File]::WriteAllText($p, $body, $UTF8) }\r\n"
                     "    $a += @(('-' + $k + 'File'), $p, ('-' + $k + 'Sha'), (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant())\r\n"
                     "  }\r\n"
                     "  & powershell.exe @a | Out-Null\r\n")
            t = edit(t, "  @{ name = 'L_marker_without_receipt';",
                     "  @{ name = 'M_gate_not_passed'; gate = '{\"pass\": false}'; outcomes = @{}; steps = @(@{ vissim = 0; note = 'gate pass false: must not launch' }, @{ vissim = 0; note = 'free' });\r\n"
                     "    expect_launched = @(); expect_stop = 'GATE_NOT_PASSED'; expect_exit = 0; expect_tryend = @{}; expect_log = @('LAUNCH_STOPPED reason=GATE_NOT_PASSED', 'LAUNCHER_EXIT launching stopped') },\r\n"
                     "  @{ name = 'N_pre_changed_after_s31'; outcomes = @{}; steps = @(\r\n"
                     "      @{ vissim = 1; note = 'free -> s31' }, @{ vissim = 2; note = 'PRE file changed on disk'; write = @(@{ path = '_fixed\\PRE_FO.md'; text = 'changed' }) },\r\n"
                     "      @{ vissim = 2; note = 'still changed' }, @{ vissim = 1; note = 's31 completes'; write = $done31 });\r\n"
                     "    expect_launched = @('s31_run1_try1'); expect_stop = 'SHA_MISMATCH'; expect_exit = 0; expect_tryend = @{ s31_run1_try1 = 'completed' }; expect_log = @('LAUNCH_STOPPED reason=SHA_MISMATCH') },\r\n"
                     "  @{ name = 'L_marker_without_receipt';")
            t = edit(t, "  $code = Invoke-Launcher $root $log $scen\r\n",
                     "  $gt = '{\"pass\": true}'; if ($c.ContainsKey('gate')) { $gt = [string]$c.gate }\r\n"
                     "  $code = Invoke-Launcher $root $log $scen $gt\r\n")
        t = ('# [FO copy 2026-10-27 KST, PRE_FO s5: copy of codex_handoff/b/%s (sha256 %s) with names changed and the declared FO' + EOL[0] +
             '# additions; full diff in codex_handoff/fo/work/run/launcher_b_to_fo.diff. The original header follows.]' + EOL[0]) % (src, want) + t
        if not all(ord(ch) < 128 for ch in t):
            raise SystemExit('non-ASCII in ' + src)
        dst = FD + '/' + DST[src]
        if os.path.exists(dst):
            raise SystemExit('exists: ' + dst)
        out = t.encode('ascii')
        open(dst, 'wb').write(out)
        d = list(difflib.unified_diff(raw.decode('ascii').splitlines(), t.splitlines(), 'b/' + src, 'fo/' + DST[src], lineterm='', n=0))
        rec.append('\n'.join(d))
        print(DST[src], sha(out), 'diff lines', len(d))
    open(FD + '/work/run/launcher_b_to_fo.diff', 'w', encoding='ascii', newline='\n').write('\n\n'.join(rec) + '\n')


if __name__ == '__main__':
    main()
