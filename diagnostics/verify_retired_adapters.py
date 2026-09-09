"""Verify exact Git recovery of the eighteen retired adapter source copies.

This script only reads Git and files. It never installs recovered legacy code.
"""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT/'evaluation/controllers/_superseded_20260827'
COMMIT = '6056c94770bb45c19e0a32b90416444db2bce2d1'
NAMES = (
    'legacy_base_20260827.py',
    'vissim_stackelberg_adapter_allfix_20260825.py',
    'vissim_stackelberg_adapter_dual_20260826.py',
    'vissim_stackelberg_adapter_mainline_20260825.py',
    'vissim_stackelberg_adapter_map4e_20260826.py',
    'vissim_stackelberg_adapter_merge_20260824.py',
    'vissim_stackelberg_adapter_nfclean_20260824.py',
    'vissim_stackelberg_adapter_ninref_20260825.py',
    'vissim_stackelberg_adapter_npband_20260826.py',
    'vissim_stackelberg_adapter_offarm_20260825.py',
    'vissim_stackelberg_adapter_offset_20260824.py',
    'vissim_stackelberg_adapter_qprice_20260825.py',
    'vissim_stackelberg_adapter_qstop_20260825.py',
    'vissim_stackelberg_adapter_regret_20260824.py',
    'vissim_stackelberg_adapter_slew_20260826.py',
    'vissim_stackelberg_adapter_subwin_20260824.py',
    'vissim_stackelberg_adapter_tau_20260825.py',
    'vissim_stackelberg_adapter_tauoff_20260825.py',
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def audit():
    manifest = json.loads((DIRECTORY/'MANIFEST_20260827.json').read_text(encoding='utf-8'))
    entries = {row['file']: row for row in manifest['entries']}
    actual_names = {p.name for p in DIRECTORY.glob('*.py')}
    if actual_names and actual_names != set(NAMES):
        raise ValueError('Archive Python contents differ from the explicit eighteen-file cleanup')
    rows = []
    for name in NAMES:
        path = (DIRECTORY/name).resolve()
        if path.parent != DIRECTORY.resolve() or not path.is_relative_to(ROOT.resolve()):
            raise ValueError('Adapter recovery path escaped its exact archive directory')
        relative = path.relative_to(ROOT).as_posix()
        blob = subprocess.check_output(['git', 'show', COMMIT+':'+relative], cwd=ROOT)
        blob_id = subprocess.check_output(['git', 'rev-parse', COMMIT+':'+relative], cwd=ROOT).decode().strip()
        crlf = blob.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
        row = entries.get(name, {})
        raw = path.read_bytes() if path.exists() else None
        expected_sha = sha(raw) if raw is not None else row['sha256']
        modes = [mode for mode, data in [('git_blob_bytes', blob), ('normalize_lf_then_crlf', crlf)] if sha(data) == expected_sha]
        rows.append({'file': name, 'original_relative_path': relative, 'resolved_absolute_path': str(path),
                     'exists': raw is not None, 'raw_sha256': expected_sha,
                     'raw_bytes': len(raw) if raw is not None else row['raw_bytes'],
                     'actual_splitlines': len(raw.splitlines()) if raw is not None else row['actual_splitlines'],
                     'git_commit': COMMIT, 'git_blob': blob_id, 'git_blob_sha256': sha(blob),
                     'git_blob_crlf_sha256': sha(crlf), 'matching_recovery_modes': modes,
                     'historical_manifest_sha_matches': not row or row['sha256'] == expected_sha,
                     'raw_crlf_count': raw.count(b'\r\n') if raw is not None else row['raw_crlf_count'],
                     'raw_lone_lf_count': raw.count(b'\n')-raw.count(b'\r\n') if raw is not None else row['raw_lone_lf_count']})
    return {'commit': COMMIT, 'archive_directory': str(DIRECTORY.resolve()),
            'all_exactly_recoverable': all(row['matching_recovery_modes'] and row['historical_manifest_sha_matches'] for row in rows),
            'source_copies_present': sum(row['exists'] for row in rows), 'files': rows,
            'total_raw_bytes': sum(row['raw_bytes'] for row in rows),
            'total_actual_lines': sum(row['actual_splitlines'] for row in rows)}


if __name__ == '__main__':
    output = audit()
    print(json.dumps(output, ensure_ascii=False, indent=2))
    raise SystemExit(0 if output['all_exactly_recoverable'] else 2)
