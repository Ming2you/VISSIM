# extra (not a judge, run after ALL_OK): normalized line comparison K92 preflight output vs K8b output (read-only)
import re
SP = r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
a = open(SP + '/j1/fix/freeze/k8r_freeze_preflight.out', encoding='utf-8').read().splitlines()
b = open(SP + '/k92/va/freeze/k92_freeze_preflight.out', encoding='utf-8').read().splitlines()


def norm(ln):
    ln = re.sub(r'^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\s+', '', ln)
    ln = re.sub(r'[A-Za-z]:\\[^ ]*', '<PATH>', ln)
    ln = re.sub(r'\b[0-9a-f]{32,64}\b', '<HEX>', ln)
    ln = re.sub(r'sdmpc31_v3c3_k8\w*pre_s31|sdmpc31_v3c3_k92pre_s31', '<NAME>', ln)
    ln = re.sub(r'claude/[\w./-]+', '<BRANCH>', ln)
    ln = re.sub(r'(files|bytes|wall_sec)=[\d.]+', r'\1=<N>', ln)
    return ln


na, nb = [norm(x) for x in a], [norm(x) for x in b]
print('lines', len(a), len(b))
print('equal_after_norm', na == nb)
for i, (x, y) in enumerate(zip(na, nb)):
    if x != y:
        print('DIFF', i, '|', x[:200], '|', y[:200])
