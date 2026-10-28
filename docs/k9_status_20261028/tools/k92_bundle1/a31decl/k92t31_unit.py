"""K9-2 bundle 1, amendment 31 (D-K9-59): the jb_unit rule.  Scratch judge in KB/a31decl, never committed; fixed (sha256
in KB/LOG.md and KB/a31_pins.sha256) before the base run it judges.  Standard library only; imports nothing of the
project, of the harness, of the k92t drivers or judges.

    python -B k92t31_unit.py judge --base <b9734abe log> --new <jb_unit log> --base-root <WT> --new-root <TREE>
                             --base-rc N --new-rc N --roots <json list> --files <json list> --dest D

Rule (amendment 31 section 3.3).  Both logs are 'pytest -v' outputs of the same selection (the 4c unit files).  Per
test item (node id = the -v row text up to the outcome word) the result is
  rows  = the outcome words of the item's -v rows in log order (PASSED / FAILED / ERROR / SKIPPED / XFAIL / XPASS; a
          bare row without a word adds nothing: pytest 9 prints one before the subtests of an item; an outcome word
          alone on its line, with its [ n%] progress, belongs to the last bare row: an item that prints a line of
          its own, e.g. K8_SA_CAPTURE_PROVENANCE),
  fails = the sorted [kind, label, message] of every 'short test summary info' entry of the item: kind FAILED /
          ERROR / SUBFAILED, label = the subtest text between 'SUBFAILED' and the node id ('' otherwise), message =
          the first 'E ' line of the item's block in the FAILURES / ERRORS section (blocks pair with the entries in
          order), normalised as k92_gates._norm_msg (the amendment-24 U rule: backslashes -> '/', every root of
          --roots -> '<root>' longest first, case-insensitive, '0x<hex>' -> '0x?', 'pytest-<n>' -> 'pytest-N'),
          then cut to 300 characters; the label gets the same normalisation.
Verdict.  INCOMPLETE when a log does not parse completely (section 3.3-P list below), when an exit code is not 0 / 1 or
disagrees with the log (1 iff a failure or error), when the platform lines differ, or when the 'rootdir:' line is not
the side's own tree root.  Otherwise PASS iff (a) every item present in both logs has equal rows and fails, (b) every
item only in the new (K9-2) log has rows == ['PASSED'] and no fails, (c) no item is only in the base (b9734abe) log;
FAIL otherwise.  Skip reasons are not in a -v log and are not compared (disclosed).  The subtest counts of the final
line are reported only.

Parse checks (3.3-P): a 'collected N items' line without collection errors; rows only between that line and the first
'=== ... ===' section line; no outcome word without a bare row before it; no bare row left without a word at the end
of the run part; N = the number of items with at least one word; the final '=== ... in <s>s ===' line present and no
'Interrupted' line; final counts: passed = PASSED words, failed = FAILED words + SUBFAILED entries, error(s) = ERROR
words, skipped = SKIPPED, xfailed = XFAIL, xpassed = XPASS (absent = 0); summary entries: FAILED entries = FAILED
words (same multiset of node ids), ERROR entries = ERROR words (same multiset), every SUBFAILED node id is an item;
FAILURES blocks = FAILED + SUBFAILED entries, ERRORS blocks = ERROR entries, and each paired block title contains the
item's last '::' piece (a SUBFAILED block title also ends with the label).  A block title is a line '_+ <title> _+'
whose title is not only '_' and blanks (pytest's '_ _ _' frame separators are not titles)."""
import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
OUTCOMES = ('PASSED', 'FAILED', 'ERROR', 'SKIPPED', 'XFAIL', 'XPASS')
_W = '(?P<out>PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)'
_PCT = r'\s+\[\s*\d+%\]\s*$'
RE_ROW_OUT = re.compile(r'^(?P<nid>\S.*?) ' + _W + _PCT)
RE_LONE_OUT = re.compile(r'^' + _W + _PCT)
RE_COLLECTED = re.compile(r'collected (?P<n>\d+) items?(?P<rest>.*)$')
RE_SECTION = re.compile(r'^=+ (?P<name>.+?) =+$')
RE_FINAL = re.compile(r'^=+ (?P<body>.+?) in (?P<sec>[0-9.]+)s(?: \([0-9:]+\))? =+$')
RE_BLOCK = re.compile(r'^_+ (?P<title>.+?) _+$')
RE_ELINE = re.compile(r'^E +(?P<txt>\S.*)$')
RE_COUNT = re.compile(r'^(?P<n>\d+) (?P<what>[a-z][a-z ]*)$')
COUNT_KEYS = {'passed': 'PASSED', 'failed': 'FAILED', 'error': 'ERROR', 'errors': 'ERROR', 'skipped': 'SKIPPED',
              'xfailed': 'XFAIL', 'xpassed': 'XPASS'}
MSG_CUT = 300


def norm_msg(msg, roots):
    """k92_gates._norm_msg (amendment 24 U rule), text copied; None stays None."""
    if msg is None:
        return None
    out = re.sub(r'\\+', '/', str(msg))
    for r in sorted((re.sub(r'\\+', '/', str(x)).rstrip('/') for x in roots if x), key=len, reverse=True):
        out = re.sub(re.escape(r), '<root>', out, flags=re.IGNORECASE)
    out = re.sub(r'0x[0-9a-fA-F]+', '0x?', out)
    return re.sub(r'pytest-\d+', 'pytest-N', out)


def _item_of(text, files):
    """True when the text starts with a node id of the selection: '<selected file>::...'."""
    for f in files:
        if text.startswith(f + '::'):
            return True
    return False


def parse_log(text, files):
    """One 'pytest -v' log -> rows, entries, blocks, counts, problems (section 3.3-P)."""
    lines = text.splitlines()
    res = {'platform': None, 'rootdir': None, 'collected': None, 'rows': {}, 'entries': [],
           'blocks': {'FAILURES': [], 'ERRORS': []}, 'final': None, 'counts': {}, 'interrupted': False,
           'problems': []}
    prob = res['problems']
    i, n = 0, len(lines)
    while i < n:
        ln = lines[i]
        if ln.startswith('platform ') and res['platform'] is None:
            res['platform'] = ln.strip()
        elif ln.startswith('rootdir: ') and res['rootdir'] is None:
            res['rootdir'] = ln[len('rootdir: '):].strip()
        m = RE_COLLECTED.search(ln)
        if m:
            res['collected'] = int(m.group('n'))
            if 'error' in m.group('rest'):
                prob.append('collection errors: %s' % ln.strip())
            i += 1
            break
        i += 1
    if res['collected'] is None:
        prob.append('no collected line')
        return res
    # run part
    pending = None
    order = []
    while i < n:
        ln = lines[i]
        if RE_SECTION.match(ln):
            break
        if ln.startswith('!') and 'Interrupted' in ln:
            res['interrupted'] = True
        m = RE_ROW_OUT.match(ln)
        if m and _item_of(m.group('nid'), files):          # row with its outcome word
            nid = m.group('nid')
            res['rows'].setdefault(nid, []).append(m.group('out'))
            if nid not in order:
                order.append(nid)
            pending = None
        elif _item_of(ln.rstrip(), files):                # bare row (no outcome word on this line)
            pending = ln.rstrip()
        else:
            m2 = RE_LONE_OUT.match(ln)
            if m2:
                if pending is None:
                    prob.append('outcome word without a bare row (line %d)' % (i + 1))
                else:
                    res['rows'].setdefault(pending, []).append(m2.group('out'))
                    if pending not in order:
                        order.append(pending)
                    pending = None
        i += 1
    if pending is not None and not res['rows'].get(pending):
        prob.append('bare row without an outcome word at the end of the run part: %s' % pending)
    # sections
    section = None
    block = None
    while i < n:
        ln = lines[i]
        if ln.startswith('!') and 'Interrupted' in ln:
            res['interrupted'] = True
        fm = RE_FINAL.match(ln)
        if fm:
            res['final'] = ln.strip()
            for part in fm.group('body').split(', '):
                cm = RE_COUNT.match(part.strip())
                if not cm:
                    prob.append('final line part not understood: %s' % part)
                    continue
                res['counts'][cm.group('what')] = int(cm.group('n'))
            section = None
            i += 1
            continue
        sm = RE_SECTION.match(ln)
        if sm:
            name = sm.group('name').strip()
            section = name if name in ('FAILURES', 'ERRORS', 'short test summary info') else 'other'
            block = None
            i += 1
            continue
        if section in ('FAILURES', 'ERRORS'):
            bm = RE_BLOCK.match(ln)
            if bm and bm.group('title').replace('_', '').strip():
                block = {'title': bm.group('title').strip(), 'msg': None}
                res['blocks'][section].append(block)
            elif block is not None and block['msg'] is None:
                em = RE_ELINE.match(ln)
                if em:
                    block['msg'] = em.group('txt').rstrip()
        elif section == 'short test summary info':
            for kind in ('FAILED', 'ERROR', 'SUBFAILED'):
                if ln.startswith(kind):
                    rest = ln[len(kind):]
                    hit = None
                    for f in files:
                        k = rest.find(' ' + f + '::')
                        if k >= 0 and (hit is None or k < hit[0]):
                            hit = (k, f)
                    if hit is None:
                        prob.append('summary entry without a selected node id: %s' % ln.strip())
                        break
                    label = rest[:hit[0]].strip() if kind == 'SUBFAILED' else ''
                    if kind != 'SUBFAILED' and rest[:hit[0]].strip():
                        break                               # e.g. 'FAILED_X' is not an entry
                    tail = rest[hit[0] + 1:]
                    nid = max((x for x in res['rows'] if tail == x or tail.startswith(x + ' ')), key=len,
                              default=None)
                    if nid is None:
                        prob.append('summary entry for an unknown item: %s' % ln.strip())
                        break
                    res['entries'].append([kind, label, nid])
                    break
        i += 1
    if res['final'] is None:
        prob.append('no final count line')
    if res['interrupted']:
        prob.append('interrupted')
    words = {w: sum(v.count(w) for v in res['rows'].values()) for w in OUTCOMES}
    if len([k for k, v in res['rows'].items() if v]) != res['collected']:
        prob.append('items with an outcome %d != collected %d' % (len([k for k, v in res['rows'].items() if v]),
                                                                   res['collected']))
    want = {w: 0 for w in OUTCOMES}
    for what, k in res['counts'].items():
        if what in COUNT_KEYS:
            want[COUNT_KEYS[what]] += k
    n_sub = sum(1 for e in res['entries'] if e[0] == 'SUBFAILED')
    got = dict(words, FAILED=words['FAILED'] + n_sub)
    if got != want:
        prob.append('final counts %s != words %s' % (want, got))
    for kind in ('FAILED', 'ERROR'):
        ent = sorted(e[2] for e in res['entries'] if e[0] == kind)
        rows = sorted(nid for nid, v in res['rows'].items() for w in v if w == kind)
        if ent != rows:
            prob.append('%s entries %d != %s words %d (or other items)' % (kind, len(ent), kind, len(rows)))
    fail_entries = [e for e in res['entries'] if e[0] in ('FAILED', 'SUBFAILED')]
    err_entries = [e for e in res['entries'] if e[0] == 'ERROR']
    for sec, ents in (('FAILURES', fail_entries), ('ERRORS', err_entries)):
        blocks = res['blocks'][sec]
        if len(blocks) != len(ents):
            prob.append('%s blocks %d != entries %d' % (sec, len(blocks), len(ents)))
            continue
        for b, e in zip(blocks, ents):
            name = e[2].split('::')[-1]
            if name not in b['title'] or (e[0] == 'SUBFAILED' and not b['title'].endswith(e[1])):
                prob.append('block "%s" does not match entry %s' % (b['title'], e))
            e.append(b['msg'])
    res['words'] = words
    res['ok'] = not prob
    return res


def results(parsed, roots):
    out = {}
    for nid, rows in parsed['rows'].items():
        out[nid] = {'rows': list(rows), 'fails': []}
    for e in parsed['entries']:
        kind, label, nid = e[0], e[1], e[2]
        msg = e[3] if len(e) > 3 else None
        msg = norm_msg(msg, roots)
        out.setdefault(nid, {'rows': [], 'fails': []})['fails'].append(
            [kind, norm_msg(label, roots) if label else '', None if msg is None else msg[:MSG_CUT]])
    for v in out.values():
        v['fails'].sort(key=lambda x: json.dumps(x))
    return out


def _same_root(line_root, root):
    if line_root is None or root is None:
        return False
    a = re.sub(r'[\\/]+', '/', str(line_root)).rstrip('/').lower()
    b = re.sub(r'[\\/]+', '/', str(root)).rstrip('/').lower()
    return a == b


def judge(base_text, new_text, files, roots, base_root, new_root, base_rc, new_rc):
    pb, pn = parse_log(base_text, files), parse_log(new_text, files)
    rb, rn = results(pb, roots), results(pn, roots)
    inc = []
    for side, p, rc, root in (('base', pb, base_rc, base_root), ('new', pn, new_rc, new_root)):
        if not p['ok']:
            inc.append('%s log: %s' % (side, p['problems'][:10]))
        bad = sum(p['words'].get(w, 0) for w in ('FAILED', 'ERROR')) + sum(
            1 for e in p['entries'] if e[0] == 'SUBFAILED') if p.get('words') else None
        if rc not in (0, 1) or bad is None or (rc == 1) != (bad > 0):
            inc.append('%s exit code %r vs failures/errors %r' % (side, rc, bad))
        if not _same_root(p['rootdir'], root):
            inc.append('%s rootdir %r is not %s' % (side, p['rootdir'], root))
    if pb['platform'] != pn['platform']:
        inc.append('platform lines differ: %r / %r' % (pb['platform'], pn['platform']))
    common = sorted(set(rb) & set(rn))
    differ = [[t, rb[t], rn[t]] for t in common if rb[t] != rn[t]]
    only_base = sorted(set(rb) - set(rn))
    only_new = sorted(set(rn) - set(rb))
    new_bad = [[t, rn[t]] for t in only_new if rn[t]['rows'] != ['PASSED'] or rn[t]['fails']]
    if inc:
        verdict = 'INCOMPLETE'
    else:
        verdict = 'PASS' if not differ and not only_base and not new_bad else 'FAIL'
    known = [[t, rb[t]] for t in common if rb[t]['rows'] != ['PASSED'] or rb[t]['fails']]
    return {'schema': 'k92t31-unit/v1', 'verdict': verdict, 'incomplete': inc,
            'n_base': len(rb), 'n_new': len(rn), 'n_common': len(common), 'differ': differ[:50],
            'n_differ': len(differ), 'only_base': only_base[:50], 'only_new': only_new[:50], 'new_bad': new_bad[:50],
            'non_passed_common_base': known[:50], 'n_non_passed_common': len(known),
            'counts': {'base': pb['counts'], 'new': pn['counts']},
            'words': {'base': pb.get('words'), 'new': pn.get('words')},
            'collected': {'base': pb['collected'], 'new': pn['collected']},
            'rootdir_ok': {'base': _same_root(pb['rootdir'], base_root), 'new': _same_root(pn['rootdir'], new_root)},
            'platform_equal': pb['platform'] == pn['platform'],
            'rc': {'base': base_rc, 'new': new_rc}, 'files': list(files), 'roots_n': len(roots)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['judge'])
    ap.add_argument('--base', required=True)
    ap.add_argument('--new', required=True)
    ap.add_argument('--base-root', required=True)
    ap.add_argument('--new-root', required=True)
    ap.add_argument('--base-rc', type=int, required=True)
    ap.add_argument('--new-rc', type=int, required=True)
    ap.add_argument('--roots', required=True)
    ap.add_argument('--files', required=True)
    ap.add_argument('--dest', required=True)
    a = ap.parse_args()
    files, roots = json.loads(a.files), json.loads(a.roots)
    bt = Path(a.base).read_text(encoding='utf-8', errors='replace')
    nt = Path(a.new).read_text(encoding='utf-8', errors='replace')
    res = judge(bt, nt, files, roots, a.base_root, a.new_root, a.base_rc, a.new_rc)
    dest = Path(a.dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(dest) + '.tmp')
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(res, indent=1, sort_keys=True, ensure_ascii=False) + '\n')
    tmp.replace(dest)
    print('K92T31_UNIT verdict=%s common=%d differ=%d only_base=%d only_new=%d new_bad=%d incomplete=%d' % (
        res['verdict'], res['n_common'], res['n_differ'], len(res['only_base']), len(res['only_new']),
        len(res['new_bad']), len(res['incomplete'])))
    return {'PASS': 0, 'FAIL': 3, 'INCOMPLETE': 4}[res['verdict']]


if __name__ == '__main__':
    raise SystemExit(main())
