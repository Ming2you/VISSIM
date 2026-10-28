# Review probe (read-only, 2026-10-27 KST): negative controls for the r2 additions of fo_run_check.py.
# (1) V4(d) rule with an EMPTY written set on the B v3c3 records (all urban SGs in the .lsa compared): must find differences
#     (the B-written SGs), so (d) is not true by construction.
# (2) V1/V9 regexes on synthetic run-log text: a held scope exception must give V1 true (held) and V9 false.
import importlib.util, json, re, sys
FW = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/fo/work'
spec = importlib.util.spec_from_file_location('m', FW + '/gate/fog_sg_native.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
spec2 = importlib.util.spec_from_file_location('rc', FW + '/ana/fo_run_check.py')
rc = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(rc)
out = {}
for s in (31, 41, 43):
    run, lsa, rb = m.b_inputs(s)
    ev, cyc = m.read_lsa(lsa)
    early, late = list(range(2, 900)), list(range(901, 9001))
    n = bad_sg = 0
    for key in sorted(k for k in ev if k[0] < 9000):
        C, delta, ok = m.native_cycle(cyc.get(key[0], []))
        base = m.lsa_green_frames(ev[key], early)
        prog = {(t + delta) % C for t in base if t >= 2 + C} if ok else set()
        got = m.lsa_green_frames(ev[key], late)
        d = [t for t in late if (t in got) != (((t + delta) % C) in prog)] if ok else late
        n += 1
        bad_sg += 1 if d else 0
    out['neg_d_s%d' % s] = {'urban_sg_in_lsa': n, 'with_difference': bad_sg}
    print('neg V4(d) on B s%d with empty written set: sg=%d with_difference=%d' % (s, n, bad_sg))
rl = ('DECISION_HOLD_ATTEMPT sim_sec=2400 cause=ValueError: Inactive urban actuator changed: green_times\r\n'
      'DECISION_HELD_PREVIOUS sim_sec=2400 source=x\r\nDECISIONS_OK=60\r\nDECISIONS_FAILED=1\r\nDECISIONS_HELD_PREVIOUS=1\r\n'
      'DECISIONS_HELD_ON_EXCEPTION=1\r\nSTAGE=SIM_DONE\r\nSIM_SEC=9000\r\n')
holds = [(int(x.group(1)), x.group(2)[:200]) for x in re.finditer(r'(?m)^DECISION_HOLD_ATTEMPT sim_sec=(\d+) cause=(.*)$', rl)]
summ = {k: (re.search(r'(?m)^%s=(\d+)' % k, rl).group(1)) for k in ('DECISIONS_FAILED', 'DECISIONS_HELD_ON_EXCEPTION')}
v1 = summ['DECISIONS_FAILED'] == summ['DECISIONS_HELD_ON_EXCEPTION'] and 1 == int(summ['DECISIONS_HELD_ON_EXCEPTION'])
v9 = not [(t, c) for t, c in holds if any(x in c for x in rc.SCOPE_MSGS)]
out['synthetic'] = {'holds': holds, 'v1_failed_equals_held_and_one_error_txt': v1, 'v9_no_scope_hold': v9}
print('synthetic: V1 part', v1, 'V9', v9, holds)
json.dump(out, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
