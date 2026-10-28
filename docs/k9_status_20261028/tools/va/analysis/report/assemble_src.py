r"""V-A report source assembler (text only; reads no run data, no analysis output).
Fills the verbatim quote blocks of report_body.txt from the source documents and writes report_src.txt (UTF-8, LF).
Each quote block is checked: removing the '> ' prefix gives back the source bytes (or the source line) exactly.
usage: python -B assemble_src.py  ->  report_src.txt, assemble_check.json"""
import hashlib
import io
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
SP = r'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8'
SRC = {
    'ADDENDUM1': (os.path.join(SP, 'j1', 'J1_CAVEAT_ADDENDUM.md'), None,
                  'b34849374a5fa49dab493f84c3d653e3fbe9e9cff27f97d1dc42cd224bca083b'),
    'ADDENDUM2': (os.path.join(SP, 'k92', 'va', 'J1_CAVEAT_ADDENDUM_K92VA.md'), None,
                  'e034593e7456ca931dae46de5aca28e7483946d656bfcd74de70a4ab9a74ad59'),
    'A22_11': (os.path.join(SP, 'K8_PREDECLARATION_AMENDMENT_22.md'), 409,
               '81cba5ae85e8d17e0b8bcd7c2f2e522c86a8bc2f2b4e19f4de3bb9de36bb459d'),
    'A24_10': (os.path.join(SP, 'K8_PREDECLARATION_AMENDMENT_24.md'), 191,
               'd46db6dc3959b19525f0fce77ead5432682e3de0ef8060cdc3da09661559aadc'),
    'A24_6': (os.path.join(SP, 'K8_PREDECLARATION_AMENDMENT_24.md'), 187,
              'd46db6dc3959b19525f0fce77ead5432682e3de0ef8060cdc3da09661559aadc'),
}


def quote(lines):
    return '\n'.join(('> ' + x) if x else '>' for x in lines)


def unquote(block):
    out = []
    for x in block.split('\n'):
        out.append(x[2:] if x.startswith('> ') else ('' if x == '>' else None))
    return out


def main():
    body = io.open(os.path.join(HERE, 'report_body.txt'), encoding='utf-8', newline='').read()
    check = {}
    for key, (path, lineno, want) in SRC.items():
        raw = open(path, 'rb').read()
        h = hashlib.sha256(raw).hexdigest()
        if h != want:
            raise SystemExit('source sha mismatch %s' % key)
        text = raw.decode('utf-8')
        if '\r' in text:
            raise SystemExit('CR in %s' % key)
        if lineno is None:
            lines = text[:-1].split('\n') if text.endswith('\n') else text.split('\n')
        else:
            lines = [text.split('\n')[lineno - 1]]
        block = quote(lines)
        back = unquote(block)
        if lineno is None:
            ok = ('\n'.join(back) + '\n').encode('utf-8') == raw
        else:
            ok = back == lines
        mark = '@@%s@@' % key
        if body.count(mark) != 1 or not ok:
            raise SystemExit('placeholder or round trip failed %s' % key)
        body = body.replace(mark, block)
        check[key] = {'source': path, 'line': lineno, 'source_sha256': h, 'round_trip_same': ok}
    if '@@' in body:
        raise SystemExit('unfilled placeholder left')
    dst = os.path.join(HERE, 'report_src.txt')
    with io.open(dst, 'w', encoding='utf-8', newline='\n') as f:
        f.write(body)
    check['report_src_sha256'] = hashlib.sha256(open(dst, 'rb').read()).hexdigest()
    with io.open(os.path.join(HERE, 'assemble_check.json'), 'w', encoding='utf-8') as f:
        json.dump(check, f, indent=1, ensure_ascii=False)
    print('ASSEMBLED', check['report_src_sha256'])


if __name__ == '__main__':
    main()
