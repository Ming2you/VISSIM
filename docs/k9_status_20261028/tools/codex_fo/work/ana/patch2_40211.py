# -*- coding: utf-8 -*-
p = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/fo/work/ana/FO_REPORT_src.md'
s = open(p, encoding='utf-8').read()
a = '\uc758 \ud569\uc785\ub2c8\ub2e4.\n9. [\uc2e4\ud589]'
assert s.count(a) == 1, s.count(a)
s = s.replace(a, '\uc758 \ud569\uc785\ub2c8\ub2e4(\ubc18\uc62c\ub9bc \ucc28 \u2264 0.1).\n9. [\uc2e4\ud589]')
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('PATCH2 ok')
