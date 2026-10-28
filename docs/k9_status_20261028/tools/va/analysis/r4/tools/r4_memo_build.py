r"""V-A r4 step 3: build the correction memo from a source text and AV/r4/out/r4_tables.json.  Formatting only.
python -B r4_memo_build.py --src <memo_src.md> --dst <VA_REPORT_r4_CORRECTION.md>
  {{TABLE:NAME}} is replaced by r4_tables.json[NAME] (unknown NAME: exit 2).  Same checks as the r3 builder
  (va_report_build.py): its FORBIDDEN words anywhere (exit 3); a table showing '③ Ω' must also show '④' and 'Ω 밖 (a)'
  (exit 4).  The r3 report bytes must be unchanged before and after (exit 6).  Writes <dst> (UTF-8, LF) + <dst>.sha256."""
import hashlib
import io
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r4_common as RC  # noqa: E402
import va_report_build as VB  # noqa: E402  (r3 builder, pinned; only its FORBIDDEN tuple is used)

V = RC.V


def main():
    src = sys.argv[sys.argv.index('--src') + 1]
    dst = sys.argv[sys.argv.index('--dst') + 1]
    if V.sha(RC.VA_REPORT) != RC.VA_REPORT_SHA:
        print('R3_CHANGED_BEFORE')
        sys.exit(6)
    T = RC.jload(os.path.join(RC.OUT, 'r4_tables.json'))
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
    if V.sha(RC.VA_REPORT) != RC.VA_REPORT_SHA:
        print('R3_CHANGED_AFTER')
        sys.exit(6)
    print('MEMO_BUILT %s sha256=%s tables=%d forbidden_checked=%d' % (dst, sha, len(set(names)), len(VB.FORBIDDEN)))


if __name__ == '__main__':
    main()
