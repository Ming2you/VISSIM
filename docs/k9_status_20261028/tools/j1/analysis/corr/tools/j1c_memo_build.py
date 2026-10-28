r"""J1 report correction: build the memo from a source text and AN/corr/out/j1c_tables.json.  Formatting only.
python -B j1c_memo_build.py --src <memo_src.md> --dst <J1_REPORT_CORRECTION.md>
  {{TABLE:NAME}} is replaced by j1c_tables.json[NAME] (unknown NAME: exit 2).  Same checks as r4_memo_build.py: the r3
  builder's FORBIDDEN words anywhere (exit 3); a table showing '③ Ω' must also show '④' and 'Ω 밖 (a)' (exit 4).
  J1_REPORT.md bytes must be unchanged before and after (exit 6).  Writes <dst> (UTF-8, LF) + <dst>.sha256."""
import hashlib
import io
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import j1c_compare as JC  # noqa: E402  (paths and the J1_REPORT sha only)
import va_report_build as VB  # noqa: E402  (r3 builder, pinned; only its FORBIDDEN tuple is used)

V = JC.V


def main():
    src = sys.argv[sys.argv.index('--src') + 1]
    dst = sys.argv[sys.argv.index('--dst') + 1]
    if V.sha(JC.J1_REPORT) != JC.J1_REPORT_SHA:
        print('J1_REPORT_CHANGED_BEFORE')
        sys.exit(6)
    T = V.jload(os.path.join(JC.CORR, 'out', 'j1c_tables.json'))
    text = io.open(src, encoding='utf-8').read()
    names = re.findall(r'\{\{TABLE:([A-Za-z0-9_]+)\}\}', text)
    unknown = sorted(set(n for n in names if n not in T))
    if unknown:
        print('UNKNOWN_TABLES', unknown)
        sys.exit(2)
    out = re.sub(r'\{\{TABLE:([A-Za-z0-9_]+)\}\}', lambda m: T[m.group(1)], text)
    bad = [w for w in VB.FORBIDDEN if w in out]
    if bad:
        print('FORBIDDEN_WORDS', bad)
        sys.exit(3)
    for name in set(names):
        t = T[name]
        if '③ Ω' in t and not ('④' in t and 'Ω 밖 (a)' in t):
            print('OMEGA_WITHOUT_4_AND_OUTSIDE', name)
            sys.exit(4)
    with io.open(dst, 'w', encoding='utf-8', newline='\n') as h:
        h.write(out)
    sha = hashlib.sha256(open(dst, 'rb').read()).hexdigest()
    with io.open(dst + '.sha256', 'w', encoding='utf-8', newline='\n') as h:
        h.write('%s *%s\n' % (sha, os.path.basename(dst)))
    if V.sha(JC.J1_REPORT) != JC.J1_REPORT_SHA:
        print('J1_REPORT_CHANGED_AFTER')
        sys.exit(6)
    print('MEMO_BUILT %s sha256=%s tables=%d forbidden_checked=%d' % (dst, sha, len(set(names)), len(VB.FORBIDDEN)))


if __name__ == '__main__':
    main()
