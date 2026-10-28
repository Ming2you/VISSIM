"""보충 34 §3.2 K9-2-7 편집 (바이트, LF만). GWT8 gb7_allowed.py 하나만 씁니다.

글자 원천 = 보충 24(sha256 d46db6dc…aadc) §14.3 줄:
  :591 R2-12 튜플 꼴(정규식), :592 이유 문구(따옴표 안), :593 docstring 문구(따옴표 안).
넣는 것:
  (1) docstring 줄 `  A 밖 경로가 하나라도 다르면(값·유무·형) GB-7' 실패 → STOP입니다(보충 1 §E).` 바로 뒤에
      `- ` + :593 글자 + `.` 한 줄 (보충 34 §3.2 꼴).
  (2) R2-11 튜플 끝 줄 바로 뒤에 두 줄:
      `    ('R2-12', 'R2', r'<정규식>',`
      `     '<이유>'),`
그 밖 바이트 0. 앞 sha가 c6f9ca1c…94c8가 아니면 쓰지 않고 끝냅니다(exit 2).
인자: --write 이 있어야 씁니다(없으면 마른 실행: 결과 sha만 찍음).
"""
import hashlib
import re
import sys

A24 = ('C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/'
       '491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/K8_PREDECLARATION_AMENDMENT_24.md')
A24_SHA = 'd46db6dc3959b19525f0fce77ead5432682e3de0ef8060cdc3da09661559aadc'
TARGET = 'D:/VISSIM-merge/sim3-n31-k8/diagnostics/sdmpc_n31_20260924/k8_gates/gb7_allowed.py'
TARGET_SHA_BEFORE = 'c6f9ca1cbf1e1ac49f1bc7adf44e33add289fea5858be8f5884c7225753894c8'
REASON_SHA16 = '7a51c150f6bc3cc4'
REGEX_EXPECT = r'/diagnostics/leg_ramp_split_(?:len_[^/\[]*|length_fallback)'


def die(msg, code=2):
    print('P7_STOP', msg)
    sys.exit(code)


def main():
    write = '--write' in sys.argv[1:]
    a24 = open(A24, 'rb').read()
    if hashlib.sha256(a24).hexdigest() != A24_SHA:
        die('a24 sha')
    lines24 = a24.decode('utf-8').split('\n')
    l591, l592, l593 = lines24[590], lines24[591], lines24[592]
    m1 = re.fullmatch(r"  - `\('R2-12', 'R2', r'(.*)', '<이유>'\)` — 접미 `_SUB` 없음.*", l591)
    m2 = re.fullmatch(r'  - 이유 문구: "(.*)"\.', l592)
    m3 = re.fullmatch(r'  - 모듈 docstring에 한 줄을 더합니다: "(.*)"\.', l593)
    if not (m1 and m2 and m3):
        die('a24 line form %s %s %s' % (bool(m1), bool(m2), bool(m3)))
    regex, reason, doc = m1.group(1), m2.group(1), m3.group(1)
    if regex != REGEX_EXPECT:
        die('regex text')
    re.compile(regex)
    if hashlib.sha256(reason.encode('utf-8')).hexdigest()[:16] != REASON_SHA16:
        die('reason sha')
    if "'" in reason or '\\' in reason:
        die('reason needs escaping')
    docline = '- ' + doc + '.'

    raw = open(TARGET, 'rb').read()
    if hashlib.sha256(raw).hexdigest() != TARGET_SHA_BEFORE:
        die('target sha before')
    if b'\r' in raw:
        die('target has CR')
    src = raw.decode('utf-8').split('\n')

    a_prev = '- A_K8 항목은 "달라도 됨"이지 "달라야 함"이 아닙니다. 재생 출력을 본 뒤에는 이 목록에 더하지 않습니다.'
    a_line = "  A 밖 경로가 하나라도 다르면(값·유무·형) GB-7' 실패 → STOP입니다(보충 1 §E)."
    idx_doc = [i for i, s in enumerate(src) if s == a_line]
    if len(idx_doc) != 1 or src[idx_doc[0] - 1] != a_prev:
        die('docstring anchor')
    r211 = [i for i, s in enumerate(src) if s.startswith("    ('R2-11', 'R2', ")]
    if len(r211) != 1:
        die('R2-11 anchor')
    end = r211[0]
    while not src[end].endswith('),'):
        end += 1
    if src[end] != "     '신호 앞 수용(S1)에 기댐'),":
        die('R2-11 end line')
    if not src[end + 1].startswith('    # ----') or 'R3' not in src[end + 1]:
        die('line after R2-11')
    tup = ["    ('R2-12', 'R2', r'" + regex + "',",
           "     '" + reason + "'),"]
    out = src[:idx_doc[0] + 1] + [docline] + src[idx_doc[0] + 1:end + 1] + tup + src[end + 1:]
    new = '\n'.join(out).encode('utf-8')
    print('added_doc_line_index', idx_doc[0] + 1)
    print('added_tuple_line_index', end + 2, end + 3)
    print('new_sha256', hashlib.sha256(new).hexdigest(), 'bytes', len(new), 'cr', new.count(b'\r'))
    print('reason_sha256', hashlib.sha256(reason.encode('utf-8')).hexdigest(), 'chars', len(reason))
    if write:
        with open(TARGET, 'wb') as f:
            f.write(new)
        print('P7_WRITTEN')
    else:
        print('P7_DRY')
    return 0


if __name__ == '__main__':
    sys.exit(main())
