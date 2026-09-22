"""Package the completed ordered-response diagnostics, not raw native recordings."""
from pathlib import Path
import hashlib
import json
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
K = ROOT / 'diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(path):
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=path.stat().st_size, sha256=sha(path))


def main():
    if (HERE / 'evidence_manifest.json').exists():
        raise FileExistsError('Completed packages are immutable')
    tracked = set(subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0'))
    changed = set(filter(None, subprocess.check_output(['git', 'diff', 'HEAD', '--name-only', '-z'], cwd=ROOT).decode().split('\0')))
    expected = {'AGENTS.md', 'docs/HANDOFF_20260921_gain_prediction.md',
        K.relative_to(ROOT).as_posix() + '/PLAN.md',
        K.relative_to(ROOT).as_posix() + '/downstream_restart.py'}
    assert changed == expected, (sorted(changed - expected), sorted(expected - changed))
    direct = {ROOT / p for p in changed}
    direct.update(K / name for name in ('VELOCITY_MIXING_AND_REACTION_LEDGER.md', 'ORDERED_RELATIVE_RESPONSE_GATE.md'))
    prefixes = ('velocity_ledger_audit', 'velocity_ledger_mechanism', 'verify_velocity_ledger',
        'check_ordered_relative_response', 'verify_ordered_relative_response',
        'ordered_relative_response', 'lateral_body_observation')
    selected = set()
    for prefix in prefixes:
        for p in K.glob(prefix + '*'):
            selected.update([p] if p.is_file() else (v for v in p.rglob('*') if v.is_file()))
    records, objects = [], {}
    for p in sorted(selected):
        if '__pycache__' in p.parts:
            continue
        assert p.suffix.lower() in ('.py', '.json', '.txt', '.log', '.md'), p
        if p.suffix in ('.py', '.md'):
            direct.add(p)
        elif p.relative_to(ROOT).as_posix() not in tracked:
            r = record(p)
            records.append(r)
            objects.setdefault(r['sha256'], p)
    archive = HERE / 'evidence.build.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for digest, p in sorted(objects.items()):
            z.write(p, 'objects/' + digest)
    parts = []
    with archive.open('rb') as f:
        while data := f.read(48 * 1024 * 1024):
            p = HERE / f'evidence.part{len(parts)+1:03d}.bin'
            p.write_bytes(data)
            parts.append(dict(name=p.name, bytes=len(data), sha256=sha(p)))
    manifest = dict(schema='deduplicated-git-handoff/v1',
        baseline_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        requires_package='diagnostics/handoff_20260921_acceleration', files=records, parts=parts,
        unique_objects=len(objects), archive_bytes=archive.stat().st_size, excluded_raw=[],
        excluded_note='No raw native files selected. Earlier packages supply baseline observations. Failed candidates remain default-off and NOT_QUALIFIED.')
    (HERE / 'evidence_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    assert archive.resolve().parent == HERE.resolve()
    archive.unlink()
    attrs = ROOT / '.gitattributes'
    marker = '# 2026-09-21 ordered response handoff byte preservation'
    original = attrs.read_bytes()
    assert marker.encode() not in original
    rules = [f'"{p.relative_to(ROOT).as_posix()}" -text whitespace=cr-at-eol' for p in sorted(direct)]
    rules.append('"diagnostics/handoff_20260921_ordered/**" -text whitespace=cr-at-eol')
    attrs.write_bytes(original + ('\n' + marker + '\n' + '\n'.join(rules) + '\n').encode())
    direct.add(attrs)
    direct.update(p for p in HERE.iterdir() if p.is_file())
    direct.update(HERE / n for n in ('paths.txt', 'direct_files.json', 'restore_verification.json'))
    (HERE / 'paths.txt').write_text('\n'.join(sorted(p.relative_to(ROOT).as_posix() for p in direct))+'\n', encoding='utf-8')
    (HERE / 'direct_files.json').write_text(json.dumps(dict(files=[record(p) for p in sorted(direct)
        if p.name not in ('direct_files.json', 'restore_verification.json')]), indent=2), encoding='utf-8')
    print(json.dumps(dict(evidence_paths=len(records), unique_objects=len(objects), direct_files=len(direct),
        archive_bytes=manifest['archive_bytes'], parts=len(parts))))


if __name__ == '__main__':
    main()
