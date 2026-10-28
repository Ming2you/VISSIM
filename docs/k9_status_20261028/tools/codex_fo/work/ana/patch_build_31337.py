# -*- coding: utf-8 -*-
# one-off text patch for fo_report_build.py and FO_REPORT_src.md (sign formatting, Korean true/false, entry W s43 number)
import sys
D = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/fo/work/ana/'


def patch(p, reps):
    s = open(p, encoding='utf-8').read()
    for a, b in reps:
        n = s.count(a)
        if n != 1:
            sys.exit('NO MATCH (%d) in %s: %s' % (n, p, a[:80]))
        s = s.replace(a, b)
    open(p, 'w', encoding='utf-8', newline='\n').write(s)


patch(D + 'fo_report_build.py', [
    ("else ('차 %d/%d' % (x['B1_d'], x['M_d']))", "else ('차 %s/%s' % (f1(x['B1_d'], 0), f1(x['M_d'], 0)))"),
    ("' · '.join('s%d %.1e' % (x['seed'], x['diff']) for x in C['X2'])",
     "' · '.join('v3c3-s%d %s' % (x['seed'], ('%.1e' % x['diff']).replace('-', '\\u2212')) for x in C['X2'])"),
    ("% (C['X3']['V_va_nc3_cells_equal'], C['X3']['O_va_nc3_equal'], C['X3']['stop'])",
     "% (tf(C['X3']['V_va_nc3_cells_equal']), tf(C['X3']['O_va_nc3_equal']), tf(C['X3']['stop']))"),
    ("' · '.join('%s %s' % (k, v) for k, v in C['X3b_scans_equal_b'].items())",
     "' · '.join('%s %s' % (k.replace('nc3_s', 'NC3 v3c3-s').replace('va_s', 'V-A v3c3-s'), tf(v)) for k, v in C['X3b_scans_equal_b'].items())"),
    ("'%s %+d · %+d' % (VS[s], X5[s]['first_plus_remain_FO_minus_NC3_calc'], X5[s]['first_plus_remain_B_minus_NC3_calc'])",
     "'%s %s · %s' % (VS[s], f1(X5[s]['first_plus_remain_FO_minus_NC3_calc'], 0), f1(X5[s]['first_plus_remain_B_minus_NC3_calc'], 0))"),
    ("'%s · %s' % (rc[s]['usable'], rc[s]['pass'])", "'%s · %s' % (tf(rc[s]['usable']), tf(rc[s]['pass']))"),
    ("def n0(x):", "def tf(x):\n    return '참' if x is True else ('거짓' if x is False else str(x))\n\n\ndef n0(x):"),
])
patch(D + 'FO_REPORT_src.md', [
    ("진입 W(codex 규칙·codex 꼴) +1.4 / +1.7 / +1.4.", "진입 W(codex 규칙·codex 꼴) +1.4 / +1.7 / +1.3."),
    ("FO − NC3 +1.4 / +1.7 / +1.4, B − FO ±0.0 / +0.2 / −0.3 veh·h (§1.6).", "FO − NC3 +1.4 / +1.7 / +1.3, B − FO ±0.0 / +0.2 / −0.3 veh·h (§1.6)."),
    ("① 차가 B 의 0.86–1.06배이고, B − FO ① 은 잣대(+32.5)보다 작습니다.",
     "① 차가 B 의 0.86–1.06배이고, B − FO ① 의 크기(4.6–12.6)는 잣대(64cf A1 − joint ① +32.5)보다 작습니다."),
])
print('PATCH ok')
