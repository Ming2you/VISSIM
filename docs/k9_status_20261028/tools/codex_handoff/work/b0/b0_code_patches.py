# B0: code patches to the codex tree for v3c3 (b0 scratch tree only).  Each patched file is rebuilt from the
# untouched A0 copy (D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/code, = A1 FREEZE table) by exact, unique string
# replacements, so the script is idempotent.  Ported text comes from OUR V-A runtime
# (D:/VISSIM-merge/frozen/sdmpc31_c20aff1d_202610230833, read-only), quoted with its file:line in each patch.
# Writes b0/code/<file> and work/b0/code_patches_receipt.json.   usage: python -B b0_code_patches.py
import hashlib, json, os, sys
A0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/code'
B0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/b0/code'
OURS = 'D:/VISSIM-merge/frozen/sdmpc31_c20aff1d_202610230833'
HERE = os.path.dirname(os.path.abspath(__file__))
NL = chr(10)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def ours_block(rel, start_marker, end_marker):
    """Text of OUR file from the line starting with start_marker up to (not including) the line starting with end_marker."""
    lines = open(OURS + '/' + rel, encoding='utf-8').read().split(NL)
    i = next(k for k, l in enumerate(lines) if l.startswith(start_marker))
    j = next(k for k, l in enumerate(lines) if k > i and l.startswith(end_marker))
    return NL.join(lines[i:j]) + NL, (i + 1, j)


PATCHES = []   # (id, file, old, new, why, source)

# ---- F1: network v3c1+ reviewed source routing decision (decision 1160 on source link 21, kept in v3c3)
blk, span = ours_block('evaluation/controllers/physical_movement_routes.py', 'def source_decision_record(node):',
                       'def configure_native_input_signal_authority(')
PATCHES.append(('F1a', 'evaluation/controllers/physical_movement_routes.py',
                'def configure_native_input_signal_authority(cfg, tuning, detectors, *, state_json):',
                blk + NL + 'def configure_native_input_signal_authority(cfg, tuning, detectors, *, state_json):',
                'port check_source_routing_decisions + source_decision_record (v3c1 V1 decision 1160 on source 21)',
                'ours physical_movement_routes.py:%d-%d' % span))
PATCHES.append(('F1b', 'evaluation/controllers/physical_movement_routes.py',
                "    decisions = tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')" + NL +
                "    if any(x.get('link') == source for x in decisions):" + NL +
                "        raise ValueError('Native signal source acquired an unreviewed routing decision')" + NL,
                "    decisions = tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')" + NL +
                "    check_source_routing_decisions(decisions, row)" + NL,
                'call site as ours (no reviewed_source_decisions key = the codex rule, admits none)',
                'ours physical_movement_routes.py:555-556'))

# ---- F2: K8-9 phantom route alias (D-K9-16, D-K9-20), ours control_area_objective.py:252-273, 652-663, 745/759-766
alias_blk, aspan = ours_block('evaluation/controllers/control_area_objective.py', '# K8-9 (K8 amendment 22 section 4.2',
                              'class ModelAreaLedger:')
CAO = 'evaluation/controllers/control_area_objective.py'
PATCHES.append(('F2a', CAO, 'class ModelAreaLedger:', alias_blk + 'class ModelAreaLedger:',
                'PHANTOM_ROUTE_ALIAS table + probability check', 'ours control_area_objective.py:%d-%d' % aspan))
PATCHES.append(('F2b', CAO,
                '                 physical_source_inside=None, outward_crossings=None, inward_crossings=None,' + NL +
                '                 complete_source=False):',
                '                 physical_source_inside=None, outward_crossings=None, inward_crossings=None,' + NL +
                '                 complete_source=False, alias_route=None):',
                'transfer() takes the sibling route', 'ours control_area_objective.py:630'))
PATCHES.append(('F2c', CAO,
                '        draw_out = count - draw_in' + NL + '        probabilities = (inside_to_inside, outside_to_inside)' + NL,
                '        draw_out = count - draw_in' + NL + '        probabilities = (inside_to_inside, outside_to_inside)' + NL +
                '        if (alias_route is not None and inside_to_inside is None and outside_to_inside is None' + NL +
                '                and (draw_in > 1e-9 or draw_out > 1e-9) and _phantom_alias_probabilities_ok(alias_route)):' + NL +
                "            # K8-9: only where the loop below would raise for a phantom of PHANTOM_ROUTE_ALIAS, use the values" + NL +
                "            # emit_transfer would have passed for its sibling route. route_key and payload stay the phantom's." + NL +
                '            inside_to_inside = alias_route["inside_to_inside"]' + NL +
                '            outside_to_inside = alias_route["outside_to_inside"]' + NL +
                '            physical_source_inside = (alias_route.get("source_inside")' + NL +
                '                                      if "outward_crossings_per_vehicle" in alias_route else None)' + NL +
                '            outward_crossings = alias_route.get("outward_crossings_per_vehicle")' + NL +
                '            inward_crossings = alias_route.get("inward_crossings_per_vehicle")' + NL +
                '            probabilities = (inside_to_inside, outside_to_inside)' + NL +
                '            self.flow_counts["phantom_route_alias:" + str(route_key)] += count' + NL,
                'alias block, same text as ours', 'ours control_area_objective.py:651-663'))
PATCHES.append(('F2d', CAO,
                '    ledger = get_ledger(state)' + NL + '    if ledger is None:' + NL + '        return' + NL +
                '    if preserve_area:' + NL + '        p_in, p_out = 1.0, 0.0' + NL,
                '    ledger = get_ledger(state)' + NL + '    if ledger is None:' + NL + '        return' + NL +
                '    alias_route = None' + NL +
                '    if preserve_area:' + NL + '        p_in, p_out = 1.0, 0.0' + NL,
                'emit_transfer: alias_route default', 'ours control_area_objective.py:745'))
PATCHES.append(('F2e', CAO,
                '        if p_in is None and p_out is None and type(route.get("target_inside")) is bool:' + NL +
                '            p_in = p_out = float(route["target_inside"])' + NL +
                '    ledger.transfer(',
                '        if p_in is None and p_out is None and type(route.get("target_inside")) is bool:' + NL +
                '            p_in = p_out = float(route["target_inside"])' + NL +
                '        if p_in is None and p_out is None and route_key in PHANTOM_ROUTE_ALIAS:' + NL +
                '            alias_route = (getattr(cfg.network, "control_area_routes", {}) or {}).get(PHANTOM_ROUTE_ALIAS[route_key])' + NL +
                '    ledger.transfer(',
                'emit_transfer: look up the sibling route', 'ours control_area_objective.py:759-760'))
PATCHES.append(('F2f', CAO,
                '                    inward_crossings=route.get("inward_crossings_per_vehicle"),' + NL +
                '                    complete_source=complete_source)',
                '                    inward_crossings=route.get("inward_crossings_per_vehicle"),' + NL +
                '                    complete_source=complete_source, alias_route=alias_route)',
                'emit_transfer passes the sibling route', 'ours control_area_objective.py:766'))

# ---- F3: v3c3 route 1133:2 ends on link 70 (v3b route edit; decision 1140 on link 70 is active in v3c3, empty in 64cf).
#      The codex 10638 retained-route tag ("1133:2 continues to 126 with no further choice") does not exist on v3c3, so
#      no tags are bound and 10638 departures take the ordinary upstream schedule, as OUR lane_offramp_runtime.py:109 does.
LOR = 'evaluation/controllers/lane_offramp_runtime.py'
PATCHES.append(('F3', LOR,
                "        route=runtime['routes']['1133:2']" + NL +
                "        if route['target']!='10638' or route['path'][route['path'].index('10638'):]!=['10638','70','10776','126']:" + NL,
                "        route=runtime['routes']['1133:2']" + NL +
                "        if route['target']=='10638' and route['path'][route['path'].index('10638'):]==['10638','70']:" + NL +
                "            # B0 (v3c3 3de889f0): 1133:2 ends on link 70 and decision 1140 there is active, so the 64cf" + NL +
                "            # 'retained to 126' class does not exist. No route tags; ordinary upstream schedule (ours :109)." + NL +
                "            self.local_route_fifo=None" + NL +
                "            return" + NL +
                "        if route['target']!='10638' or route['path'][route['path'].index('10638'):]!=['10638','70','10776','126']:" + NL,
                'v3c3 route 1133:2 form -> no 10638 retained tags (64cf form unchanged)', 'ours lane_offramp_runtime.py:109 (no tags)'))

# ---- H1: decision hold only on a Python exception (our K8-8, D-K9-13/D-K9-17, NOTES:47), watchdog side.
#      Codex 'hold_previous' (any failure incl. timeout, adapter --hold-previous-action) stays as it was for A.
#      'hold_previous_on_exception': no deadline (timeout key refused, StallSec bounds a decision), the VBS calls
#      scripts/decision_hold.py (ours) only after exit 1 with the adapter's .error.txt report.  Source: ours
#      run_real_world_single_watchdog_distributed_core17legs4b.ps1:319-363 (Read-DecisionErrorPolicy, single file here).
WD = 'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1'
PATCHES.append(('H1', WD,
                "$env:RW_DECISION_HOLD_PREVIOUS = '0'" + NL + "$env:RW_DECISION_TIMEOUT_SEC = '0'" + NL +
                "if ($Tuning -ne '') {" + NL +
                "  $runtimeTuning = Get-Content -LiteralPath (Resolve-RepoPath $Tuning) -Raw -Encoding UTF8 -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop" + NL +
                "  if ($runtimeTuning.runtime.decision_error_policy) {" + NL,
                "$env:RW_DECISION_HOLD_PREVIOUS = '0'" + NL + "$env:RW_DECISION_TIMEOUT_SEC = '0'" + NL +
                "$env:RW_DECISION_ERROR_POLICY = 'strict'" + NL +
                "if ($Tuning -ne '') {" + NL +
                "  $runtimeTuning = Get-Content -LiteralPath (Resolve-RepoPath $Tuning) -Raw -Encoding UTF8 -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop" + NL +
                "  # B0 port of our K8-8 (hold only on a Python exception, no deadline). The codex hold_previous branch is unchanged." + NL +
                "  if ($runtimeTuning.runtime.decision_error_policy -ceq 'hold_previous_on_exception') {" + NL +
                "    if ($Controller -ne 'wu-link') { throw 'Decision recovery is supported only for wu-link' }" + NL +
                "    if ($null -ne $runtimeTuning.runtime.PSObject.Properties['decision_timeout_sec']) { throw 'runtime deadline key refused (no hold on time)' }" + NL +
                "    $env:RW_DECISION_ERROR_POLICY = 'hold_previous_on_exception'" + NL +
                "    # The codex VBS hold path is used, gated to exit 1 + .error.txt (H3); timeout 0 = no deadline in the VBS." + NL +
                "    $env:RW_DECISION_HOLD_PREVIOUS = '1'" + NL +
                "    $env:RW_DECISION_TIMEOUT_SEC = '0'" + NL +
                "  } elseif ($runtimeTuning.runtime.decision_error_policy) {" + NL,
                'accept hold_previous_on_exception (RW_DECISION_ERROR_POLICY, codex hold path on, timeout 0 = none); codex branch unchanged',
                'ours watchdog :319-363'))
# ---- H2: control_hold.write_hold accepts hold_previous_on_exception and then applies our eligibility first
#      (ours scripts/decision_hold.py:49-63 lists + P-4/P-5 rules: the failure report must exist, no excluded exception
#      type in it, no frame in a previous-command/history contract function, no contract message).
CH = 'evaluation/controllers/control_hold.py'
PATCHES.append(('H2a', CH,
                "    if tuning.get('runtime', {}).get('decision_error_policy') != 'hold_previous':" + NL +
                "        raise ValueError('Holding a failed decision is not enabled in tuning')" + NL,
                "    policy_value = tuning.get('runtime', {}).get('decision_error_policy')" + NL +
                "    if policy_value not in ('hold_previous', 'hold_previous_on_exception'):" + NL +
                "        raise ValueError('Holding a failed decision is not enabled in tuning')" + NL +
                "    if policy_value == 'hold_previous_on_exception':" + NL +
                "        require_exception_hold(Path(args.out_action_json))" + NL,
                'policy hold_previous_on_exception accepted after the eligibility check', 'ours decision_hold.py check()'))
PATCHES.append(('H2b', CH,
                "def write_hold(args, tuning):" + NL,
                "# B0 port of our K8-8 eligibility (ours scripts/decision_hold.py:49-63, P-4/P-5). Same lists, same parsing rule." + NL +
                "EXCLUDED_TYPES = ('DecisionDeadline', 'TimeoutError', 'MemoryError', 'KeyboardInterrupt', 'GeneratorExit'," + NL +
                "                  'BrokenProcessPool', 'BrokenPipeError', 'ConnectionResetError')" + NL +
                "CONTRACT_PAIRS = (('vissim_stackelberg_adapter.py', 'load_joint_historical_reference')," + NL +
                "                  ('vissim_stackelberg_adapter.py', 'joint_runtime_source_pins')," + NL +
                "                  ('vissim_stackelberg_adapter.py', 'control_from_json')," + NL +
                "                  ('sdmpc.py', 'load_prices')," + NL +
                "                  ('physical_ramp_branches.py', 'read_recorded_control')," + NL +
                "                  ('physical_ramp_branches.py', 'held_actual_reference')," + NL +
                "                  ('lane_plant_runtime.py', 'applied_vsl_from_previous')," + NL +
                "                  ('offramp_split_forecast.py', 'window_counts')," + NL +
                "                  ('area_meter_finalization.py', 'configure'))" + NL +
                "CONTRACT_MESSAGES = ('Invalid applied central multiplier warm start',)" + NL +
                "_HEADER_RE = re.compile(r'^[A-Za-z_][\\w.]*(: .*|:)?$')" + NL +
                "_FRAME_RE = re.compile(r'^\\s*File \"(.+)\", line \\d+, in (.+?)\\s*$')" + NL + NL + NL +
                "def require_exception_hold(out_action_json):" + NL +
                "    \"\"\"Refuse a hold unless the decision died on an eligible Python exception (failure report present).\"\"\"" + NL +
                "    report = out_action_json.with_suffix('.error.txt')" + NL +
                "    if not report.is_file():" + NL +
                "        raise ValueError('Exception hold requires the decision failure report: ' + report.name)" + NL +
                "    lines = [b.decode('utf-8', errors='replace').rstrip(chr(13)) for b in report.read_bytes().split(b'\\n')]" + NL +
                "    types = [l.split(':', 1)[0].split('.')[-1] for l in lines" + NL +
                "             if l != 'Traceback (most recent call last):' and _HEADER_RE.match(l)]" + NL +
                "    bad = sorted(set(types) & set(EXCLUDED_TYPES))" + NL +
                "    if bad:" + NL +
                "        raise ValueError('Exception hold refused, excluded type: ' + ','.join(bad))" + NL +
                "    frames = set()" + NL +
                "    for l in lines:" + NL +
                "        m = _FRAME_RE.match(l)" + NL +
                "        if m:" + NL +
                "            frames.add((re.split(r'[\\\\/]', m.group(1))[-1], m.group(2).strip()))" + NL +
                "    hit = sorted(frames & set(CONTRACT_PAIRS))" + NL +
                "    if hit:" + NL +
                "        raise ValueError('Exception hold refused, previous-command contract: ' + repr(hit))" + NL +
                "    if any(m in l for l in lines for m in CONTRACT_MESSAGES):" + NL +
                "        raise ValueError('Exception hold refused, contract message')" + NL + NL + NL +
                "def write_hold(args, tuning):" + NL,
                'eligibility function (excluded types, contract frames/messages)', 'ours decision_hold.py:49-63, check()'))
# ---- H3: VBS - with hold_previous_on_exception the codex hold path runs only after exit 1 with the failure report,
#      never for the first controlled decision (ours :1241-1259 gates), plus the summary line (ours :564).
VBS = 'scripts/run_real_world_stackelberg_controller.vbs'
PATCHES.append(('H3a', VBS,
                "            LCase(CStr(controllerName)) = \"wu-link\" And Trim(CStr(RW_COMMAND_REPLAY_DIR)) = \"\" Then" + NL +
                "        WScript.Echo \"DECISION_HOLD_ATTEMPT sim_sec=\"",
                "            LCase(CStr(controllerName)) = \"wu-link\" And Trim(CStr(RW_COMMAND_REPLAY_DIR)) = \"\" And _" + NL +
                "            ExceptionHoldGate(simSec, exitCode, outJsonPath, effController) Then" + NL +
                "        WScript.Echo \"DECISION_HOLD_ATTEMPT sim_sec=\"",
                'gate the codex hold path by our policy', 'ours VBS :1241-1259'))
PATCHES.append(('H3b', VBS,
                "Function EnvText(name)" + NL,
                "' B0 port of our K8-8 gate (ours VBS :1241-1259). Other policies: the codex rule unchanged (True)." + NL +
                "Function ExceptionHoldGate(simSec, exitCode, outJsonPath, effController)" + NL +
                "    ExceptionHoldGate = True" + NL +
                "    If EnvText(\"RW_DECISION_ERROR_POLICY\") <> \"hold_previous_on_exception\" Then Exit Function" + NL +
                "    ExceptionHoldGate = False" + NL +
                "    If CLng(exitCode) <> 1 Then Exit Function" + NL +
                "    If LCase(CStr(effController)) <> LCase(CStr(controllerName)) Then Exit Function" + NL +
                "    If CLng(controlStartSec) < 0 Then Exit Function" + NL +
                "    If CLng(simSec) < CLng(controlStartSec) + CLng(controlInterval) Then Exit Function" + NL +
                "    If Not fso.FileExists(Left(outJsonPath, Len(outJsonPath) - 5) & \".error.txt\") Then Exit Function" + NL +
                "    ExceptionHoldGate = True" + NL +
                "End Function" + NL + NL +
                "Function EnvText(name)" + NL,
                'gate function', 'ours VBS :1241-1259'))
PATCHES.append(('H3c', VBS,
                "WScript.Echo \"DECISIONS_HELD_PREVIOUS=\" & CStr(decisionsHeld)" + NL,
                "WScript.Echo \"DECISIONS_HELD_PREVIOUS=\" & CStr(decisionsHeld)" + NL +
                "If EnvText(\"RW_DECISION_ERROR_POLICY\") = \"hold_previous_on_exception\" Then WScript.Echo \"DECISIONS_HELD_ON_EXCEPTION=\" & CStr(decisionsHeld)" + NL,
                'summary line', 'ours VBS :564'))
PATCHES.append(('H1b', WD,
                "    $env:RW_DECISION_HOLD_PREVIOUS = '1'" + NL + "    $env:RW_DECISION_TIMEOUT_SEC = [string]$seconds" + NL + "  }" + NL + "}" + NL,
                "    $env:RW_DECISION_HOLD_PREVIOUS = '1'" + NL + "    $env:RW_DECISION_TIMEOUT_SEC = [string]$seconds" + NL + "  }" + NL + "}" + NL +
                "\"RW_DECISION_ERROR_POLICY=$($env:RW_DECISION_ERROR_POLICY) (runtime.decision_error_policy)\"" + NL,
                'log line as ours :363', 'ours watchdog :363'))

# ---- N1: runner network path and sha as parameters (defaults = the codex 64cf values, so A1-style launches are unchanged)
RUN = 'diagnostics/sdmpc_n31_20260924/integration_20260926/run_closedloop3000.ps1'
CX_NET = 'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
CX_SHA = '64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
PATCHES.append(('N1a', RUN,
                "      [ValidateSet('nc','sdmpc')][string[]]$Arms=@('nc','sdmpc'))",
                "      [ValidateSet('nc','sdmpc')][string[]]$Arms=@('nc','sdmpc')," + NL +
                "      [string]$NetworkRelativePath='" + CX_NET + "'," + NL +
                "      [ValidatePattern('^[0-9a-f]{64}$')][string]$NetworkSha256='" + CX_SHA + "')",
                'network path/sha parameters (B0: v3c3)', 'TAKEOVER_PLAN 1.2 / R_NET 3.3'))
PATCHES.append(('N1b', RUN,
                "            Copy-Item -LiteralPath (Join-Path $selectedRoot 'network/native_seed29.inpx') -Destination $network" + NL +
                "            Get-ChildItem -LiteralPath (Join-Path $selectedRoot 'network') -Filter '*.sig' |",
                "            $networkSource=[IO.Path]::GetFullPath((Join-Path $frozen $NetworkRelativePath))" + NL +
                "            Copy-Item -LiteralPath $networkSource -Destination $network" + NL +
                "            Get-ChildItem -LiteralPath (Split-Path -Parent $networkSource) -Filter '*.sig' |",
                'copy the parameterised network and the .sig files beside it', 'R_NET 3.1-1'))
PATCHES.append(('N1c', RUN,
                "        if ((Get-FileHash -LiteralPath $network -Algorithm SHA256).Hash.ToLowerInvariant() -cne '" + CX_SHA + "') { throw 'Network differs' }",
                "        if ((Get-FileHash -LiteralPath $network -Algorithm SHA256).Hash.ToLowerInvariant() -cne $NetworkSha256) { throw 'Network differs' }",
                'sha check against the parameter', 'R_NET 3.1-1'))
PATCHES.append(('N1d', RUN,
                "                $provenance.files.network.sha256 -ne '" + CX_SHA + "') {",
                "                $provenance.files.network.sha256 -ne $NetworkSha256) {",
                'NC reuse check against the parameter', 'R_NET 3.1-1'))
PATCHES.append(('N1e', RUN,
                "    $argv+=@('-PythonExe',$PythonExe,'-PowerShellExe',$pwshExe,'-DependenciesPath',$DependenciesPath)",
                "    $argv+=@('-PythonExe',$PythonExe,'-PowerShellExe',$pwshExe,'-DependenciesPath',$DependenciesPath)" + NL +
                "    if($NetworkRelativePath -ne '" + CX_NET + "' -or $NetworkSha256 -ne '" + CX_SHA + "'){" + NL +
                "        $argv+=@('-NetworkRelativePath',$NetworkRelativePath,'-NetworkSha256',$NetworkSha256)" + NL +
                "    }",
                'detached mode passes the network parameters', 'R_NET 3.1-1'))

EXTRA = os.environ.get('B0_PATCH_STAGE', 'all')


def main():
    by_file = {}
    for p in PATCHES:
        by_file.setdefault(p[1], []).append(p)
    receipt = []
    for rel, plist in by_file.items():
        raw = open(A0 + '/' + rel, 'rb').read()
        eol = chr(13) + NL if b'\r\n' in raw else NL
        txt = raw.decode('utf-8')
        for pid, _, old, new, why, src in plist:
            old, new = old.replace(NL, eol), new.replace(NL, eol)
            n = txt.count(old)
            if n != 1:
                raise SystemExit('%s: expected one match in %s, found %d' % (pid, rel, n))
            txt = txt.replace(old, new)
        out = txt.encode('utf-8')
        open(B0 + '/' + rel, 'wb').write(out)
        receipt.append({'file': rel, 'codex_sha256': sha(raw), 'b0_sha256': sha(out),
                        'patches': [{'id': p[0], 'why': p[4], 'source': p[5]} for p in plist]})
    json.dump({'schema': 'b0-code-patches/v1', 'a0_code': A0, 'ours': OURS, 'files': receipt},
              open(os.path.join(HERE, 'code_patches_receipt.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for r in receipt:
        print(r['file'], r['codex_sha256'][:12], '->', r['b0_sha256'][:12], [p['id'] for p in r['patches']])


main()
