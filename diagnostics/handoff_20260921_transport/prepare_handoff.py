"""Package the explicit transport and passage continuation; preserve previous archives."""
from pathlib import Path
import hashlib
import json
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
K = ROOT / 'diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def record(p):
    return dict(path=p.relative_to(ROOT).as_posix(), bytes=p.stat().st_size, sha256=sha(p))


def main():
    if (HERE / 'evidence_manifest.json').exists():
        raise FileExistsError('Completed packages are immutable')
    tracked = set(subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0'))
    changed = set(filter(None, subprocess.check_output(['git', 'diff', 'HEAD', '--name-only', '-z'], cwd=ROOT).decode().split('\0')))
    selected = set()
    prefixes = ('matched_cohort_response', 'matched_outlet_response', 'matched_passage_response', 'high_order_transport', 'check_high_order_transport', 'verify_matched_cohort_outlet')
    for p in [p for prefix in prefixes for p in K.glob(prefix + '*')]:
        selected.update([p] if p.is_file() else (v for v in p.rglob('*') if v.is_file()))
    expected_changed = {'AGENTS.md', 'docs/HANDOFF_20260921_gain_prediction.md',
        K.relative_to(ROOT).as_posix() + '/PLAN.md',
        K.relative_to(ROOT).as_posix() + '/downstream_spatial_rollout.py',
        'diagnostics/handoff_20260921_spatial/verify_records.py'}
    assert changed <= expected_changed, sorted(changed - expected_changed)
    direct = {ROOT / p for p in changed}
    direct.update(K / name for name in ('MATCHED_COHORT_AND_OUTLET.md', 'TRANSPORT_DIFFUSION_AND_PASSAGE.md'))
    raw = {'.fzp', '.db', '.knr', '.rsr', '.jpg', '.jpeg', '.png', '.pyc', '.pkl', '.pickle'}
    excluded, eligible = [], []
    for p in sorted(selected):
        if '__pycache__' in p.parts:
            continue
        if p.suffix.lower() in raw:
            excluded.append(dict(path=p.relative_to(ROOT).as_posix(), bytes=p.stat().st_size,
                                 reason='Raw native/cache/background: retained locally, not needed for saved-record checks'))
        elif p.suffix in ('.py', '.ps1', '.vbs', '.md'):
            direct.add(p)
        elif p.relative_to(ROOT).as_posix() not in tracked:
            eligible.append(p)
    records, objects = [], {}
    for p in eligible:
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
        requires_package='diagnostics/handoff_20260921_matched_response', files=records, parts=parts,
        unique_objects=len(objects), archive_bytes=archive.stat().st_size, excluded_raw=excluded,
        excluded_note='Matched initial-cohort/passage records and rejected local transport/outlet candidates only. No raw native files selected in this increment. Earlier packages provide observations and native validation. Candidate switches remain unqualified.')
    (HERE / 'evidence_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    assert archive.resolve().parent == HERE.resolve()
    archive.unlink()
    attrs = ROOT / '.gitattributes'
    marker = '# 2026-09-21 transport and passage handoff byte preservation'
    text = attrs.read_bytes().decode('utf-8')
    assert marker not in text
    rules = [f'"{p.relative_to(ROOT).as_posix()}" -text whitespace=cr-at-eol' for p in sorted(direct)]
    rules += ['"diagnostics/handoff_20260921_transport/**" -text whitespace=cr-at-eol']
    attrs.write_bytes((text.rstrip()+'\n\n'+marker+'\n'+'\n'.join(rules)+'\n').encode('utf-8'))
    direct.add(attrs)
    direct.update(p for p in HERE.iterdir() if p.is_file())
    direct.update([HERE / 'paths.txt', HERE / 'direct_files.json', HERE / 'restore_verification.json'])
    (HERE / 'paths.txt').write_text('\n'.join(sorted(p.relative_to(ROOT).as_posix() for p in direct))+'\n', encoding='utf-8')
    (HERE / 'direct_files.json').write_text(json.dumps(dict(files=[record(p) for p in sorted(direct) if p.name not in ('direct_files.json', 'restore_verification.json')]), indent=2), encoding='utf-8')
    print(json.dumps(dict(files=len(records), unique_objects=len(objects), direct=len(direct),
                          archive_bytes=manifest['archive_bytes'], parts=len(parts))))


if __name__ == '__main__':
    main()
