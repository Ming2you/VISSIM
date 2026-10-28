r"""V-A analysis step 7: build the report from a source text and <out>/va_tables.json.  Formatting only.
python -B va_report_build.py --profile va|selftest --src <report_src.txt> --dst <REPORT.md>
  {{TABLE:NAME}} in the source is replaced by va_tables.json[NAME]; an unknown NAME stops (exit 2).
  Checks (amendment 34 sec.8.4 R12, sec.8.0-1 R10/R11): the word "개선" and verdict words (이긴/이겼/진다/졌다/낫다/
  좋아졌/나빠졌) must not appear anywhere (exit 3); every table that shows Omega (3) also shows (4) and Omega outside
  (a) (exit 4); the fixed line under header item 8 and the J1 caveat addendum 2 file name must be present when
  --require-header is given (exit 5).  Writes <dst> (UTF-8, LF) and <dst>.sha256, prints the sha256."""
import hashlib
import io
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import va_common as V  # noqa: E402

FORBIDDEN = ('개선', '이긴', '이겼', '진다', '졌다', '낫다', '좋아졌', '나빠졌')
HEADER8 = ('[K9-2 V-A] 묶음 1(W·H-b)은 유령 movement 수정을 담지 않는다(보충 24 §2.4, D-K9-19). '
           '위 줄의 "K9-2에서 고친다"는 이 V-A 런에서 아직 이루어지지 않았다.')
ADDENDUM2 = 'J1_CAVEAT_ADDENDUM_K92VA.md'


def main():
    prof = V.profile_from_argv()
    V.require_pinned(prof, __file__)
    src = sys.argv[sys.argv.index('--src') + 1]
    dst = sys.argv[sys.argv.index('--dst') + 1]
    T = V.jload(os.path.join(prof.out, 'va_tables.json'))
    text = io.open(src, encoding='utf-8').read()
    names = re.findall(r'\{\{TABLE:([A-Za-z0-9_]+)\}\}', text)
    unknown = sorted(set(n for n in names if n not in T))
    if unknown:
        print('UNKNOWN_TABLES', unknown)
        sys.exit(2)
    out = re.sub(r'\{\{TABLE:([A-Za-z0-9_]+)\}\}', lambda m: T[m.group(1)], text)
    bad = [w for w in FORBIDDEN if w in out]
    if bad:
        print('FORBIDDEN_WORDS', bad)
        sys.exit(3)
    for name in set(names):
        t = T[name]
        if '③ Ω' in t and not ('④' in t and 'Ω 밖 (a)' in t):
            print('OMEGA_WITHOUT_4_AND_OUTSIDE', name)
            sys.exit(4)
    if '--require-header' in sys.argv and (HEADER8 not in out or ADDENDUM2 not in out):
        print('HEADER_LINES_MISSING')
        sys.exit(5)
    with io.open(dst, 'w', encoding='utf-8', newline='\n') as f:
        f.write(out)
    h = hashlib.sha256(open(dst, 'rb').read()).hexdigest()
    with io.open(dst + '.sha256', 'w', encoding='utf-8', newline='\n') as f:
        f.write('%s *%s\n' % (h, os.path.basename(dst)))
    print('REPORT_BUILT %s sha256=%s tables=%d' % (dst, h, len(set(names))))


if __name__ == '__main__':
    main()
