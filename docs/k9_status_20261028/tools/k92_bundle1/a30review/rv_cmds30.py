"""ReviewDeclare A30: which agent commands touched the F job logs (OUTK/logs/f_f_*_jobs.log) or K92T_JOB lines.
Prints the command text of tool calls only (the agent's own input), and for each its result: length, whether the
result holds 's47', the counts of the leak rules of rv_leak30.py.  No result text is printed.

    python -B rv_cmds30.py <transcript.jsonl> [...]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rv_leak30 as R  # noqa: E402

TOKENS = ('jobs.log', 'K92T_JOB', 'f_f_off', 'f_f_w', 'f_f_b1', 'f_*_jobs', 'f_*')


def strings_of(x):
    yield from R.strings_of(x)


def main():
    for path in sys.argv[1:]:
        uses, results = {}, {}
        for raw in Path(path).read_bytes().splitlines():
            try:
                doc = json.loads(raw.decode('utf-8', 'replace'))
            except ValueError:
                continue
            msg = doc.get('message') if isinstance(doc, dict) else None
            content = (msg or {}).get('content') if isinstance(msg, dict) else None
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue
                if c.get('type') == 'tool_use':
                    uses[c.get('id')] = (doc.get('timestamp'), c.get('name'), json.dumps(c.get('input'),
                                                                                        ensure_ascii=False))
                elif c.get('type') == 'tool_result':
                    acc = R.new_acc()
                    n, s47 = 0, False
                    for s in strings_of(c.get('content')):
                        n += len(s)
                        s47 = s47 or ('s47' in s)
                        for ln in s.splitlines():
                            R.classify_line(ln, acc)
                    results[c.get('tool_use_id')] = (n, s47, acc)
        print('FILE', Path(path).name, 'tool_uses', len(uses))
        for uid, (ts, name, inp) in uses.items():
            if any(t in inp for t in TOKENS):
                n, s47, acc = results.get(uid, (None, None, None))
                print('  %s %s result_chars=%s result_has_s47=%s rules=%s' % (ts, name, n, s47, acc))
                print('    CMD', inp[:600])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
