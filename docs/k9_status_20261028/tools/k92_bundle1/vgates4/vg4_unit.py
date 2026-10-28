"""VerifyGates 3 -- V3: the jb_unit rule computed again from the two pytest -v logs (amendment 31 sections 3.2-3.3).

Written from the amendment text (not from k92t31_unit.py).  Reading of the text:
  * Lines: the log bytes decoded as utf-8 (errors replaced), split into lines (CR LF / LF).
  * collected line: the first line containing 'collected <N> item(s)'.  P1: present, nothing after the item word
    (no ' / N errors'), no line with 'ERROR collecting' and no 'error(s) during collection' line.
  * Run part (P2): the lines after the collected line up to (not including) the first section line '=+ text =+'.
    - row with an outcome: '<selected file>::<rest> <WORD> [ n%]' (WORD in PASSED FAILED ERROR SKIPPED XFAIL XPASS);
      node id = the text before ' <WORD>'.
    - bare row: a line starting with '<selected file>::' that is not a row with an outcome; node id = line.rstrip().
    - lone outcome: '<WORD> [ n%]' alone on its line; it belongs to the last bare row still open (P3: one must be
      open).  A row with an outcome closes an open bare row of the same node id.  Every other line is ignored.
    - P4: no bare row is still open at the end of the run part, and every node id seen in a row has >= 1 word.
    - P5: the number of node ids with >= 1 word == N.
  * Final line (P6): the last line matching '=+ <body> in <sec>s[ (h:mm:ss)] =+'; no line starting 'Interrupted'.
  * P7: from the final body, 'n passed' == PASSED words, 'n failed' == FAILED words + SUBFAILED entries,
    'n error(s)' == ERROR words, 'n skipped' == SKIPPED, 'n xfailed' == XFAIL, 'n xpassed' == XPASS (absent = 0);
    other items (subtests passed, warnings, ...) are reported only.
  * Summary entries: the lines after '=+ short test summary info =+' up to the final line that start with FAILED,
    ERROR or SUBFAILED.  The node id is found as '<selected file>::' in the line, up to the next blank (a ' - msg'
    tail is ignored); the label = the text between the kind word and the node id, stripped ('' for FAILED / ERROR).
  * P8: FAILED entries' node ids == FAILED words' node ids (multisets), ERROR likewise; every SUBFAILED node id is a
    node id with a row.
  * Blocks: inside the '=+ FAILURES =+' and '=+ ERRORS =+' sections, a block title is a line '_+ <title> _+' whose
    title is not only '_' and blanks; a block runs to the next title or section line.  P9: FAILURES blocks ==
    FAILED + SUBFAILED entries, ERRORS blocks == ERROR entries.  Pairing in order (FAILED / SUBFAILED entries in
    summary order <-> FAILURES blocks in order, ERROR entries <-> ERRORS blocks).  P10: each paired title contains
    the node id's last '::' piece; a SUBFAILED title ends with the label.
  * Message = the text after 'E' and its blanks on the block's first line '^E\\s+\\S' (the first E line with text).
  * Normalisation (section 3.3, U rule): backslash -> '/'; each root ('/' form, no trailing '/') -> '<root>',
    longest first, case-insensitive; '0x<hex>' -> '0x?'; 'pytest-<digits>' -> 'pytest-N'; then cut to 300 chars.
    Labels get the same normalisation (cut too).
  * Result per test = (rows: the outcome words in log order, fails: sorted [kind, label, message]).
  * INCOMPLETE: any P false on a side; rc not 0 / 1 or rc == 1 not iff (FAILED + ERROR words + SUBFAILED
    entries) > 0; the platform lines differ; a side's 'rootdir:' line is not its own tree root; a base run that was not
    made / did not finish (rc None).  Otherwise PASS iff (a) every common test has equal results, (b) every test only
    in the new log has rows == ['PASSED'] and no fails, (c) no test only in the base log; else FAIL.
"""
import json
import re

WORDS = ('PASSED', 'FAILED', 'ERROR', 'SKIPPED', 'XFAIL', 'XPASS')
_WORD = r'(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)'
_PCT = r'\s+\[\s*\d+%\]\s*$'
RE_LONE = re.compile(r'^' + _WORD + _PCT)
RE_SECTION = re.compile(r'^=+ (.+?) =+$')
RE_FINAL = re.compile(r'^=+ (.+) in ([0-9.]+)s(?: \([0-9:]+\))? =+$')
RE_TITLE = re.compile(r'^_+ (.*\S) _+$')
RE_E = re.compile(r'^E\s+(\S.*)$')
RE_COLLECTED = re.compile(r'collected (\d+) items?(.*)$')
CUT = 300
FINAL_KEYS = {'passed': 'PASSED', 'failed': None, 'error': 'ERROR', 'errors': 'ERROR', 'skipped': 'SKIPPED',
              'xfailed': 'XFAIL', 'xpassed': 'XPASS'}


def normalise(text, roots):
    if text is None:
        return None
    s = str(text).replace('\\', '/')
    rs = sorted({str(r).replace('\\', '/').rstrip('/') for r in roots if str(r).strip()}, key=len, reverse=True)
    for r in rs:
        s = re.sub(re.escape(r), '<root>', s, flags=re.IGNORECASE)
    s = re.sub(r'0x[0-9a-fA-F]+', '0x?', s)
    s = re.sub(r'pytest-\d+', 'pytest-N', s)
    return s[:CUT]


def _row_nid(line, files):
    for f in files:
        if line.startswith(f + '::'):
            return True
    return False


def parse(text, files):
    """One pytest -v log -> dict with rows, entries (+ paired messages), counts, checks P1-P10."""
    lines = text.splitlines()
    P = {}
    out = {'platform': None, 'rootdir': None, 'collected': None, 'rows': {}, 'order': [], 'entries': [],
           'final': None, 'final_counts': {}, 'words': {w: 0 for w in WORDS}, 'checks': P, 'problems': []}
    for ln in lines:
        if out['platform'] is None and ln.startswith('platform '):
            out['platform'] = ln
        if out['rootdir'] is None and ln.startswith('rootdir: '):
            out['rootdir'] = ln[len('rootdir: '):].split(', ')[0].strip()
    # P1
    ci = None
    for i, ln in enumerate(lines):
        m = RE_COLLECTED.search(ln)
        if m:
            ci = i
            out['collected'] = int(m.group(1))
            rest = m.group(2).strip()
            break
    coll_err = any('ERROR collecting' in ln for ln in lines) or any(
        re.search(r'\d+ errors? during collection', ln) for ln in lines)
    P['P1'] = ci is not None and rest == '' and not coll_err
    if ci is None:
        for k in ('P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9', 'P10'):
            P[k] = False
        return out
    # run part (P2)
    end = None
    for j in range(ci + 1, len(lines)):
        if RE_SECTION.match(lines[j]):
            end = j
            break
    P['P2'] = end is not None
    if end is None:
        end = len(lines)
    rows = out['rows']
    word_nids = {w: [] for w in WORDS}
    open_bare = None
    p3 = True
    for ln in lines[ci + 1:end]:
        m_lone = RE_LONE.match(ln)
        if _row_nid(ln, files):
            m = re.match(r'^(\S.*?) ' + _WORD + _PCT, ln)
            if m:
                nid, w = m.group(1), m.group(2)
                rows.setdefault(nid, [])
                if nid not in out['order']:
                    out['order'].append(nid)
                rows[nid].append(w)
                word_nids[w].append(nid)
                out['words'][w] += 1
                if open_bare == nid:
                    open_bare = None
            else:
                nid = ln.rstrip()
                rows.setdefault(nid, [])
                if nid not in out['order']:
                    out['order'].append(nid)
                open_bare = nid
        elif m_lone:
            w = m_lone.group(1)
            if open_bare is None:
                p3 = False
                continue
            rows[open_bare].append(w)
            word_nids[w].append(open_bare)
            out['words'][w] += 1
            open_bare = None
    P['P3'] = p3
    P['P4'] = open_bare is None and all(len(v) >= 1 for v in rows.values())
    with_word = [k for k, v in rows.items() if v]
    P['P5'] = len(with_word) == out['collected']
    # final line (P6)
    fi = None
    for j in range(len(lines) - 1, -1, -1):
        if RE_FINAL.match(lines[j]):
            fi = j
            break
    interrupted = any(ln.startswith('Interrupted') or '!!!!!!' in ln and 'Interrupted' in ln for ln in lines)
    P['P6'] = fi is not None and not interrupted
    # summary entries
    si = None
    for j in range(end, len(lines)):
        m = RE_SECTION.match(lines[j])
        if m and m.group(1).strip() == 'short test summary info':
            si = j
            break
    entries = []
    stop_at = fi if fi is not None else len(lines)
    if si is not None:
        for ln in lines[si + 1:stop_at]:
            kind = None
            for k in ('SUBFAILED', 'FAILED', 'ERROR'):
                if ln.startswith(k):
                    kind = k
                    break
            if kind is None:
                continue
            pos = -1
            for f in files:
                q = ln.find(f + '::')
                if q >= 0 and (pos < 0 or q < pos):
                    pos = q
            if pos < 0:
                entries.append({'kind': kind, 'label': ln[len(kind):].strip(), 'nid': None, 'raw': ln})
                continue
            nid = ln[pos:].split()[0]
            label = ln[len(kind):pos].strip() if kind == 'SUBFAILED' else ''
            entries.append({'kind': kind, 'label': label, 'nid': nid})
    out['entries'] = entries
    # P7
    counts = {}
    if fi is not None:
        body = RE_FINAL.match(lines[fi]).group(1)
        out['final'] = lines[fi]
        for item in body.split(', '):
            m = re.match(r'^(\d+) ([a-z][a-z ]*)$', item.strip())
            if m:
                counts[m.group(2)] = counts.get(m.group(2), 0) + int(m.group(1))
            else:
                counts['<unparsed>'] = counts.get('<unparsed>', 0) + 1
    out['final_counts'] = counts
    n_sub = sum(1 for e in entries if e['kind'] == 'SUBFAILED')
    want = {'passed': out['words']['PASSED'], 'failed': out['words']['FAILED'] + n_sub,
            'error': out['words']['ERROR'], 'skipped': out['words']['SKIPPED'],
            'xfailed': out['words']['XFAIL'], 'xpassed': out['words']['XPASS']}
    got = {'passed': counts.get('passed', 0), 'failed': counts.get('failed', 0),
           'error': counts.get('error', 0) + counts.get('errors', 0), 'skipped': counts.get('skipped', 0),
           'xfailed': counts.get('xfailed', 0), 'xpassed': counts.get('xpassed', 0)}
    P['P7'] = fi is not None and want == got and '<unparsed>' not in counts
    out['p7'] = {'from_words': want, 'final_line': got}
    # P8
    ent_f = sorted(e['nid'] or '' for e in entries if e['kind'] == 'FAILED')
    ent_e = sorted(e['nid'] or '' for e in entries if e['kind'] == 'ERROR')
    P['P8'] = (ent_f == sorted(word_nids['FAILED']) and ent_e == sorted(word_nids['ERROR'])
               and all(e['nid'] in rows for e in entries if e['kind'] == 'SUBFAILED')
               and all(e['nid'] is not None for e in entries))
    # blocks
    blocks = {'FAILURES': [], 'ERRORS': []}
    cur_sec, cur = None, None
    for j in range(end, len(lines)):
        ln = lines[j]
        ms = RE_SECTION.match(ln)
        if ms:
            cur_sec = ms.group(1).strip() if ms.group(1).strip() in blocks else None
            cur = None
            continue
        if cur_sec is None:
            continue
        mt = RE_TITLE.match(ln)
        if mt and mt.group(1).replace('_', '').strip() != '':
            cur = {'title': mt.group(1), 'msg': None}
            blocks[cur_sec].append(cur)
            continue
        if cur is not None and cur['msg'] is None:
            me = RE_E.match(ln)
            if me:
                cur['msg'] = me.group(1)
    fs = [e for e in entries if e['kind'] in ('FAILED', 'SUBFAILED')]
    es = [e for e in entries if e['kind'] == 'ERROR']
    P['P9'] = len(blocks['FAILURES']) == len(fs) and len(blocks['ERRORS']) == len(es)
    p10 = True
    for group, blist in ((fs, blocks['FAILURES']), (es, blocks['ERRORS'])):
        for e, b in zip(group, blist):
            e['msg'] = b['msg']
            e['title'] = b['title']
            last = (e['nid'] or '').split('::')[-1]
            if not last or last not in b['title']:
                p10 = False
            if e['kind'] == 'SUBFAILED' and not b['title'].endswith(e['label']):
                p10 = False
    P['P10'] = p10 and P['P9']
    out['blocks_n'] = {k: len(v) for k, v in blocks.items()}
    return out


def results(parsed, roots):
    res = {nid: {'rows': list(w), 'fails': []} for nid, w in parsed['rows'].items()}
    for e in parsed['entries']:
        nid = e.get('nid')
        if nid is None:
            continue
        res.setdefault(nid, {'rows': [], 'fails': []})['fails'].append(
            [e['kind'], normalise(e['label'], roots) if e['label'] else '', normalise(e.get('msg'), roots)])
    for v in res.values():
        v['fails'].sort(key=lambda x: json.dumps(x))
    return res


def same_root(line_root, root):
    if line_root is None or root is None:
        return False
    a = re.sub(r'[\\/]+', '/', str(line_root)).rstrip('/').lower()
    b = re.sub(r'[\\/]+', '/', str(root)).rstrip('/').lower()
    return a == b


def judge(base_text, new_text, files, roots, base_root, new_root, base_rc, new_rc):
    pb, pn = parse(base_text, files), parse(new_text, files)
    rb, rn = results(pb, roots), results(pn, roots)
    inc = []
    for side, p, rc, root in (('base', pb, base_rc, base_root), ('new', pn, new_rc, new_root)):
        falses = [k for k, v in p['checks'].items() if not v]
        if falses:
            inc.append('%s parse checks false: %s' % (side, falses))
        bad = p['words']['FAILED'] + p['words']['ERROR'] + sum(1 for e in p['entries'] if e['kind'] == 'SUBFAILED')
        if rc not in (0, 1) or (rc == 1) != (bad > 0):
            inc.append('%s rc %r vs failures/errors %d' % (side, rc, bad))
        if not same_root(p['rootdir'], root):
            inc.append('%s rootdir is not its tree root' % side)
    if pb['platform'] is None or pb['platform'] != pn['platform']:
        inc.append('platform lines differ or missing')
    common = sorted(set(rb) & set(rn))
    differ = [t for t in common if rb[t] != rn[t]]
    only_base = sorted(set(rb) - set(rn))
    only_new = sorted(set(rn) - set(rb))
    new_bad = [t for t in only_new if rn[t]['rows'] != ['PASSED'] or rn[t]['fails']]
    if inc:
        verdict = 'INCOMPLETE'
    elif differ or only_base or new_bad:
        verdict = 'FAIL'
    else:
        verdict = 'PASS'
    non_passed = [[t, rb[t]] for t in common if rb[t]['rows'] != ['PASSED'] or rb[t]['fails']]
    return {'verdict': verdict, 'incomplete': inc, 'n_base': len(rb), 'n_new': len(rn), 'n_common': len(common),
            'common': common, 'differ': differ, 'n_differ': len(differ), 'only_base': only_base,
            'only_new': only_new, 'new_bad': new_bad, 'non_passed_common': non_passed,
            'n_non_passed_common': len(non_passed),
            'checks': {'base': pb['checks'], 'new': pn['checks']},
            'words': {'base': pb['words'], 'new': pn['words']},
            'final_counts': {'base': pb['final_counts'], 'new': pn['final_counts']},
            'final_lines': {'base': pb['final'], 'new': pn['final']},
            'collected': {'base': pb['collected'], 'new': pn['collected']},
            'rootdir_ok': {'base': same_root(pb['rootdir'], base_root), 'new': same_root(pn['rootdir'], new_root)},
            'platform_equal': pb['platform'] is not None and pb['platform'] == pn['platform'],
            'rc': {'base': base_rc, 'new': new_rc}}


def compare_record(mine, rec):
    """Mine against OUT31/unit_judge.json: verdict, the common / differ / one-side lists, the non-passing list."""
    rec = rec or {}

    def ids(x):
        return sorted((t[0] if isinstance(t, (list, tuple)) else t) for t in (x or []))
    rec_np = {t[0]: t[1] for t in (rec.get('non_passed_common_base') or []) if isinstance(t, (list, tuple))}
    mine_np = {t[0]: t[1] for t in mine['non_passed_common']}
    np_detail = {}
    for t in sorted(set(rec_np) | set(mine_np)):
        a, b = mine_np.get(t), rec_np.get(t)
        np_detail[t] = {'rows_equal': (a or {}).get('rows') == (b or {}).get('rows'),
                        'fails_equal': (a or {}).get('fails') == (b or {}).get('fails'),
                        'present_both': a is not None and b is not None}
    rows = {
        'verdict_equal': mine['verdict'] == rec.get('verdict'),
        'incomplete_both_empty_or_equal': (not mine['incomplete']) == (not rec.get('incomplete')),
        'n_base_equal': mine['n_base'] == rec.get('n_base'),
        'n_new_equal': mine['n_new'] == rec.get('n_new'),
        'n_common_equal': mine['n_common'] == rec.get('n_common'),
        'differ_equal': mine['differ'] == ids(rec.get('differ')) and mine['n_differ'] == rec.get('n_differ'),
        'only_base_equal': mine['only_base'] == ids(rec.get('only_base')),
        'only_new_equal': mine['only_new'] == ids(rec.get('only_new')),
        'new_bad_equal': mine['new_bad'] == ids(rec.get('new_bad')),
        'non_passed_ids_equal': sorted(mine_np) == sorted(rec_np),
        'non_passed_detail_equal': all(v['rows_equal'] and v['fails_equal'] and v['present_both']
                                       for v in np_detail.values()),
        'n_non_passed_equal': mine['n_non_passed_common'] == rec.get('n_non_passed_common'),
        'rc_equal': rec.get('rc') == mine['rc'],
    }
    return rows, np_detail
