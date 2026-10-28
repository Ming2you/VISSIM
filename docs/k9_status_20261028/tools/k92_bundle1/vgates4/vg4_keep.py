"""VerifyGates 3 -- V4: archives unchanged (amendment 31 section 4.3 V4 and section 4.1 C7 / C9).

  (a) every a31_pins.sha256 line whose path is under OUTK (26 lines) or is OUT30/check30.json, OUT30/
      sealed_k92t_index.json or OK2/logs/k92t30_chain.txt: the file's sha256 now == the pinned value;
      plus the whole pin list reported (line 127 GATES_K92B1.md is a declared later change, reported only);
  (b) C7 sets: OUTK STOP files == {STOP_a30_post.json, STOP_f.json}; OUTK/stages == 7 names; OUTK/judge == 7 names;
      OUTK/steps.jsonl has 102 lines;
  (c) C9: sealed root top names == the six; SEALED/k92t/logs == three names with sizes 4,971 / 4,996 / 4,936 B
      (names and sizes only, no content);
  (d) the temporary worktree is gone: WT folder absent, admin folder absent, not in `git worktree list`;
      K8 branch == b9734abe; GWT8 head == K9-2-5, branch, status 0 lines (git --no-optional-locks reads);
  (e) CAP: the file list, sizes and byte sha256 of OUTK/jb/sa/cap/k92t == the review manifest (cap_manifest.json,
      sha256 pinned in the fixation record); the manifest's own listing sha256 (sorted '<rel>\\t<size>\\t<sha>\\n' lines,
      utf-8) recomputed from MY walk == the manifest value == the declared 5340ac03...; 3,944 files, 1,690,146,202 B.
"""
import hashlib
import os
import subprocess
from pathlib import Path

import vg4lib as V

STOPS = ['STOP_a30_post.json', 'STOP_f.json']
STAGES = sorted('%s.json' % s for s in ('start', 'prep', 'j0', 'ja', 'seal30', 'f', 'jb'))
JUDGES = sorted('%s.json' % s for s in ('j0', 'ja', 'jwall', 'f_jobs', 'f', 'jb', 'sealed_records'))
STEPS_N = 102
SEALED_TOPS = ['K9-2-0', 'K9-2-1', 'K9-2-2', 'K9-2-3', 'a27', 'k92t']
SEALED_K92T_LOGS = {'f_f_b1_jobs.log': 4971, 'f_f_off_jobs.log': 4996, 'f_f_w_jobs.log': 4936}
GATES_MD_AFTER = '449b361e96d047156e63f73bcdae905ec61408b9a5f9be047629092d3ab0a792'


def pins(P):
    lines = Path(P['A31_PINS']).read_text(encoding='utf-8').splitlines()
    rows = []
    for i, ln in enumerate(lines, 1):
        sha, _, path = ln.partition(' *')
        rows.append((i, sha.strip(), path.strip()))
    return rows


def in_scope(path, P):
    p = V.norm_slash(path).lower()
    outk = V.norm_slash(P['OUTK']).lower().rstrip('/') + '/'
    others = {V.norm_slash(x).lower() for x in (Path(P['OUT30']) / 'check30.json',
                                                 Path(P['OUT30']) / 'sealed_k92t_index.json',
                                                 Path(P['OK2']) / 'logs' / 'k92t30_chain.txt')}
    return p.startswith(outk) or p in others


def check_pins(P):
    rows = pins(P)
    scope, rest = [], []
    for i, want, path in rows:
        now = V.sha256_or_none(path)
        (scope if in_scope(path, P) else rest).append({'line': i, 'path': path, 'same': now == want,
                                                       'now': None if now == want else now})
    return {'pins_file_sha256': V.sha256_or_none(P['A31_PINS']), 'n_lines': len(rows),
            'scope_n': len(scope), 'scope_all_same': all(r['same'] for r in scope),
            'scope_outk_n': sum(1 for r in scope if V.norm_slash(r['path']).lower().startswith(
                V.norm_slash(P['OUTK']).lower().rstrip('/') + '/')),
            'scope_bad': [r for r in scope if not r['same']],
            'all_lines_differ': [{'line': r['line'], 'path': r['path'], 'now': r['now']} for r in scope + rest
                                 if not r['same']]}


def check_sets(P):
    outk = Path(P['OUTK'])
    stops = sorted(p.name for p in outk.glob('STOP_*.json'))
    stages = sorted(p.name for p in (outk / 'stages').glob('*.json'))
    judges = sorted(p.name for p in (outk / 'judge').glob('*.json'))
    try:
        n_steps = len(V.read_text(outk / 'steps.jsonl').splitlines())
    except OSError:
        n_steps = None
    return {'stops': stops, 'stops_ok': stops == STOPS, 'stages_ok': stages == STAGES, 'stages': stages,
            'judges_ok': judges == JUDGES, 'judges': judges, 'steps_lines': n_steps, 'steps_ok': n_steps == STEPS_N}


def check_sealed_top(P):
    root = Path(P['SEALED'])
    try:
        tops = sorted(os.listdir(V.lp(root)))
    except OSError:
        tops = None
    logs = {}
    try:
        for n in sorted(os.listdir(V.lp(root / 'k92t' / 'logs'))):
            logs[n] = os.path.getsize(V.lp(root / 'k92t' / 'logs' / n))
    except OSError:
        logs = None
    return {'tops': tops, 'tops_ok': tops == SEALED_TOPS, 'k92t_logs': logs, 'k92t_logs_ok': logs == SEALED_K92T_LOGS}


def git(P, *args):
    r = subprocess.run(['git', '--no-optional-locks', '-C', str(P['GWT8'])] + list(args), capture_output=True,
                       text=True, timeout=120)
    return r.returncode, r.stdout


def check_git(P):
    out = {}
    rc, s = git(P, 'rev-parse', 'HEAD')
    out['head'] = s.strip()
    rc, s = git(P, 'rev-parse', '--abbrev-ref', 'HEAD')
    out['branch'] = s.strip()
    rc, s = git(P, 'rev-parse', V.K8_BRANCH)
    out['k8'] = s.strip()
    rc, s = git(P, 'status', '--porcelain')
    out['status_lines'] = len(s.splitlines()) if rc == 0 else None
    rc, s = git(P, 'rev-list', '--count', V.K8 + '..HEAD')
    out['k92_commits'] = s.strip()
    rc, s = git(P, 'for-each-ref', '--format=%(refname)', 'refs/remotes')
    out['remote_k92_refs'] = sum(1 for ln in s.splitlines() if 'k92' in ln)
    rc, s = git(P, 'worktree', 'list', '--porcelain')
    wt_norm = V.norm_slash(P['WT']).lower().rstrip('/')
    out['wt_listed'] = any(V.norm_slash(ln[len('worktree '):]).lower().rstrip('/') == wt_norm
                           for ln in s.splitlines() if ln.startswith('worktree ')) if rc == 0 else None
    out['worktree_list_rc'] = rc
    out['wt_exists'] = os.path.exists(V.lp(P['WT']))
    out['wt_admin_exists'] = os.path.exists(V.lp(P['WT_ADMIN']))
    out['ok'] = (out['head'] == V.HEAD and out['branch'] == V.BRANCH and out['k8'] == V.K8
                 and out['status_lines'] == 0 and out['k92_commits'] == '6' and out['remote_k92_refs'] == 0
                 and out['wt_listed'] is False and not out['wt_exists'] and not out['wt_admin_exists'])
    return out


def walk_cap(cap):
    root = V.lp(cap)
    files = {}
    errs = []
    for base, dirs, names in os.walk(root, onerror=lambda e: errs.append(str(e))):
        dirs.sort()
        for n in sorted(names):
            full = os.path.join(base, n)
            rel = os.path.relpath(full, root).replace('\\', '/')
            files[rel] = [os.path.getsize(full), V.sha256_file(full)]
    return files, errs


def listing_sha(files):
    listing = '\n'.join('%s\t%d\t%s' % (k, v[0], v[1]) for k, v in sorted(files.items())) + '\n'
    return hashlib.sha256(listing.encode('utf-8')).hexdigest()


def check_cap(P, manifest):
    files, errs = walk_cap(P['CAP'])
    man = (manifest or {}).get('files') or {}
    only_now = sorted(set(files) - set(man))
    only_man = sorted(set(man) - set(files))
    size_diff = sorted(k for k in set(files) & set(man) if files[k][0] != man[k][0])
    sha_diff = sorted(k for k in set(files) & set(man) if files[k][1] != man[k][1])
    mine_listing = listing_sha(files)
    return {'n_files_now': len(files), 'n_bytes_now': sum(v[0] for v in files.values()),
            'walk_errors': len(errs), 'n_files_manifest': len(man),
            'manifest_n_files': (manifest or {}).get('n_files'), 'manifest_n_bytes': (manifest or {}).get('n_bytes'),
            'only_now': only_now[:20], 'n_only_now': len(only_now), 'only_manifest': only_man[:20],
            'n_only_manifest': len(only_man), 'size_differ': size_diff[:20], 'n_size_differ': len(size_diff),
            'sha_differ': sha_diff[:20], 'n_sha_differ': len(sha_diff),
            'listing_sha256_now': mine_listing, 'listing_sha256_manifest': (manifest or {}).get('listing_sha256'),
            'ok': (not errs and not only_now and not only_man and not size_diff and not sha_diff
                   and len(files) == V.CAP_N_FILES and sum(v[0] for v in files.values()) == V.CAP_N_BYTES
                   and mine_listing == V.CAP_LISTING_SHA256
                   and (manifest or {}).get('listing_sha256') == V.CAP_LISTING_SHA256)}
