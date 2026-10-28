# throwaway (not a judge): try check_freeze_k92 regex shapes on the K8b captured output (read-only)
import re
L = open(r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/j1/fix/freeze/k8r_freeze_preflight.out', encoding='utf-8').read().splitlines()
pats = {
    'plan_ok': r"PLAN LAUNCH_PLAN_OK plan=(.+?)\\launch_plan\.json\s*$",
    'frz': r"FREEZE_TOOL FRZ=(.+?)\s*$",
    'rd': r"\bRUN_DIR (.+?)\s*$",
    'done': r"FREEZE_TOOL FREEZE_DONE ",
    'pd': r"PLAN LAUNCH_PLAN_DETAIL sha256=([0-9a-f]{64}) ",
    'wdpol': r"WD RW_DECISION_ERROR_POLICY=hold_previous_on_exception \(runtime\.decision_error_policy\)\s*$",
    'exit_any': r"\bEXIT ",
    'netok': r"NETWORK NETWORK_OK .*sha256=3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e sig=42\s*$",
    'pd2': r"PLAN LAUNCH_PLAN_DETAIL .*network_sha=3de889f0 detectors=294 controller=no-control sim_period=9000 seed=31 ",
    'wdargs': r"WATCHDOG_ARGS .* -NoGlobalKill( |.* )-PreflightOnly\s*$",
    'launch': r"LAUNCH name=sdmpc31_v3c3_k8rpre_s31 .*preflight_only=True ",
}
for k, pt in pats.items():
    ms = [m for m in (re.search(pt, l) for l in L) if m]
    print(k, len(ms), (ms[0].group(1) if ms and ms[0].groups() else ''))
print('pre name ok', re.fullmatch(r"sdmpc31_v3c3_k8rpre_s31_\d{8}_\d{6}", 'sdmpc31_v3c3_k8rpre_s31_20261014_182451') is not None)
