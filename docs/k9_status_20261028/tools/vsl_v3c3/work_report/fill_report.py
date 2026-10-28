# -*- coding: utf-8 -*-
"""Fill VSL_REPORT.template.md: {{V:a-b}} -> lines a..b of out/vsl_tables.md, {{R:a-b}} -> lines a..b of
out/report_tables.md (verbatim). Writes VS/VSL_REPORT.md. 2026-10-27 KST, vsl_v3c3. No numbers are computed here."""
import re

VS = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/vsl_v3c3'
SRC = {'V': open(VS + '/out/vsl_tables.md', encoding='utf-8').read().split('\n'),
       'R': open(VS + '/out/report_tables.md', encoding='utf-8').read().split('\n')}
t = open(VS + '/work_report/VSL_REPORT.template.md', encoding='utf-8').read()


def sub(m):
    k, a, b = m.group(1), int(m.group(2)), int(m.group(3))
    lines = SRC[k][a - 1:b]
    assert lines and all(l.startswith('|') for l in lines), (k, a, b)
    return '\n'.join(lines)


out = re.sub(r'\{\{([VR]):(\d+)-(\d+)\}\}', sub, t)
assert '{{' not in out
open(VS + '/VSL_REPORT.md', 'w', encoding='utf-8').write(out)
print('written', len(out.split('\n')), 'lines')
