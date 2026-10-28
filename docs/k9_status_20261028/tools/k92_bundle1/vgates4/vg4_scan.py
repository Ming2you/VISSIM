"""VerifyGates 3 -- V2: the sealed-root k92_record.json scan counted again (amendment 31 section 4.3 V2).

Rule, written from the text of amendment 31 section 2.2 (not from any judge code):
  * A record = a file named exactly 'k92_record.json' anywhere under the sealed root SEALED (os.walk, no links).
  * s47 record  <=>  (1) str(record['seed']) == '47'   or   (2) a piece of the record's path RELATIVE to SEALED is an
    s47 piece.  s47 piece: p = piece.lower(); p == 's47' or p ends with '_s47' or '_s47_' in p or p starts with 's47_'.
    Relative path: drop a leading long-path prefix \\\\?\\; normcase(abspath(path)) equal to normcase(abspath(SEALED))
    -> no pieces; starting with that root + separator -> the rest; anything else -> all pieces of the path (unchanged
    amendment-30 reading for paths outside the sealed root).
  * An s47 record must have the key 'vissim' with value null and 'vissim_reason' == 'k92_blind_s47'; otherwise bad.
    A record that cannot be read as a JSON object is counted and is bad when it is an s47 record by path; it is also
    listed (stricter than the text; disclosed).
  * Extra counts (section 4.3 V2 (a)(b)): seed values (str) per record, 'missing' when the key is absent; and the
    records where "seed == '47'" and "relative path has an s47 piece" disagree.
  * The relative pieces are computed two ways: from the text function on the long-path string, and from the os.walk
    relative folder; they must agree (internal check).
Output: counts, verdict pieces, relative paths of bad / disagreeing records (no record values).
"""
import os
import re
from pathlib import Path

import vg4lib as V

BLIND_REASON = 'k92_blind_s47'


def is_s47_piece(piece):
    p = str(piece).lower()
    return p == 's47' or p.endswith('_s47') or '_s47_' in p or p.startswith('s47_')


def rel_pieces(path, sealed_root):
    """Pieces of `path` per amendment 31 section 2.2 (relative to the sealed root when at / under it)."""
    s = str(path)
    if s.startswith('\\\\?\\'):
        s = s[4:]
    full = os.path.normcase(os.path.abspath(s))
    root = os.path.normcase(os.path.abspath(str(sealed_root))).rstrip('\\/')
    if full == root:
        rest = ''
    elif full.startswith(root + os.sep):
        rest = full[len(root) + 1:]
    else:
        rest = s
    return [p for p in re.split(r'[\\/]', rest) if p != '']


def path_is_s47(path, sealed_root):
    return any(is_s47_piece(p) for p in rel_pieces(path, sealed_root))


def scan(sealed_root):
    """Walk the sealed root; return counts and lists (values stay in memory)."""
    root = Path(sealed_root)
    walk_root = V.lp(root)
    res = {'files': 0, 's47': 0, 'bad': 0, 'unreadable': 0, 'seed_values': {}, 'disagree_seed_vs_path': 0,
           'disagree_examples': [], 'bad_paths': [], 'unreadable_paths': [], 'two_way_piece_mismatch': 0,
           'per_top': {}, 'vissim_key_missing_in_s47': 0, 's47_by_seed': 0, 's47_by_path': 0, 'walk_errors': 0}

    def onerr(_e):
        res['walk_errors'] += 1
    for base, dirs, names in os.walk(walk_root, onerror=onerr):
        dirs.sort()
        rel_dir = os.path.relpath(base, walk_root)
        rel_dir_pieces = [] if rel_dir == '.' else [p for p in re.split(r'[\\/]', rel_dir) if p]
        for n in sorted(names):
            if n != 'k92_record.json':
                continue
            full = os.path.join(base, n)
            rel = '/'.join(rel_dir_pieces + [n])
            res['files'] += 1
            top = rel_dir_pieces[0] if rel_dir_pieces else '.'
            res['per_top'][top] = res['per_top'].get(top, 0) + 1
            by_text = path_is_s47(full, root)
            by_walk = any(is_s47_piece(p) for p in rel_dir_pieces + [n])
            if by_text != by_walk:
                res['two_way_piece_mismatch'] += 1
            doc = V.read_json_or(full, None)
            if not isinstance(doc, dict):
                res['unreadable'] += 1
                res['unreadable_paths'].append(rel)
                res['seed_values']['<unreadable>'] = res['seed_values'].get('<unreadable>', 0) + 1
                if by_text:
                    res['s47'] += 1
                    res['s47_by_path'] += 1
                    res['bad'] += 1
                    res['bad_paths'].append([rel, 'unreadable s47 record'])
                continue
            has_seed = 'seed' in doc
            sv = str(doc.get('seed')) if has_seed else '<missing>'
            res['seed_values'][sv] = res['seed_values'].get(sv, 0) + 1
            seed47 = has_seed and str(doc.get('seed')) == '47'
            if seed47 != by_text:
                res['disagree_seed_vs_path'] += 1
                if len(res['disagree_examples']) < 50:
                    res['disagree_examples'].append(rel)
            if seed47 or by_text:
                res['s47'] += 1
                res['s47_by_seed'] += int(seed47)
                res['s47_by_path'] += int(by_text)
                if 'vissim' not in doc:
                    res['vissim_key_missing_in_s47'] += 1
                if not ('vissim' in doc and doc['vissim'] is None and doc.get('vissim_reason') == BLIND_REASON):
                    res['bad'] += 1
                    res['bad_paths'].append([rel, 's47 record VISSIM side not blind'])
    return res


EXPECT = {'files': 134, 's47': 45, 'bad': 0}
EXPECT_SEEDS = {'31': 42, '43': 47, '47': 45}


def judge(res):
    """V2 pieces: my counts, (a) seed distribution, (b) disagreement 0, internal two-way check."""
    return {'counts_ok': {k: res[k] for k in EXPECT} == EXPECT,
            'ok_like_judge': res['bad'] == 0,
            'seed_distribution_ok': res['seed_values'] == EXPECT_SEEDS,
            'disagree_zero': res['disagree_seed_vs_path'] == 0,
            'two_way_ok': res['two_way_piece_mismatch'] == 0,
            'walk_ok': res['walk_errors'] == 0}


def compare_records(res, scan31, sealed_records, sealed_records_sha):
    """My counts against OUT31/scan31.json and OUT31/sealed_records_a31.json (the apply records)."""
    sr = (sealed_records or {}).get('sealed_records') or {}
    s31 = scan31 or {}
    mine = {'files': res['files'], 's47': res['s47'], 'bad': res['bad'], 'ran': True}
    rows = {
        'sealed_records_counts_equal': sr == mine,
        'sealed_records_ok_equal': (sealed_records or {}).get('ok') is (res['bad'] == 0),
        'sealed_records_n_bad_equal': (sealed_records or {}).get('n_bad') == res['bad'],
        'scan31_verdict_PASS': s31.get('verdict') == 'PASS',
        'scan31_rc_0': s31.get('rc') == 0,
        'scan31_ok_true': s31.get('ok') is True,
        'scan31_n_bad_equal': s31.get('n_bad') == res['bad'],
        'scan31_counts_equal': s31.get('counts') == mine,
        'scan31_expected_counts_declared': s31.get('expected_counts') == dict(EXPECT, ran=True),
        'scan31_archive_unchanged_true': s31.get('archive_unchanged') is True,
        'scan31_output_sha_equal': s31.get('output_sha256') == sealed_records_sha,
    }
    return rows
