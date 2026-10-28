# mkcopy.py - make a copy of a pinned tool with exact text replacements (each must occur exactly once), keeping the
# source file's bytes, encoding and line endings everywhere else. Writes the copy and a JSON record of the changed
# lines (source line no., old text, new text) so the LOG can list them.  Gate 1 / COMPARE_RULE_B, 2026-10-26 KST.
# usage: python -B mkcopy.py <spec.json> <record.json>
#   spec = [{"src": path, "dst": path, "why": text, "reps": [[old, new], ...]}, ...]   ("\n" in old/new = one line break)
import difflib, hashlib, json, os, sys


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main(spec_path, rec_path):
    spec = json.load(open(spec_path, encoding='utf-8'))
    out = []
    for item in spec:
        raw = open(item['src'], 'rb').read()
        eol = b'\r\n' if b'\r\n' in raw else b'\n'
        text = raw
        for old, new in item['reps']:
            o = old.encode('utf-8').replace(b'\n', eol)
            n = new.encode('utf-8').replace(b'\n', eol)
            c = text.count(o)
            if c != 1:
                raise SystemExit('replacement must occur exactly once (%d): %s :: %r' % (c, item['src'], old[:80]))
            text = text.replace(o, n)
        if os.path.exists(item['dst']):
            raise SystemExit('destination exists: ' + item['dst'])
        os.makedirs(os.path.dirname(item['dst']), exist_ok=True)
        open(item['dst'], 'wb').write(text)
        a = raw.decode('utf-8').splitlines()
        b = text.decode('utf-8').splitlines()
        changes = []
        sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag != 'equal':
                changes.append({'op': tag, 'src_lines': [i1 + 1, i2], 'dst_lines': [j1 + 1, j2],
                                'old': a[i1:i2], 'new': b[j1:j2]})
        out.append({'src': item['src'], 'src_sha256': sha(raw), 'dst': item['dst'], 'dst_sha256': sha(text),
                    'eol': 'CRLF' if eol == b'\r\n' else 'LF', 'why': item.get('why', ''), 'n_replacements': len(item['reps']),
                    'changes': changes})
        print(os.path.basename(item['dst']), sha(text), 'changed blocks', len(changes))
    json.dump(out, open(rec_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
