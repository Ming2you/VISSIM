"""Explicit capture only: archive seven complete JSON windows, never FZP."""
import hashlib
import json
import zipfile
from diagnostics.head_service_resource_fixtures import ROOT, ARCHIVE, RUN, DECISIONS, CONFIG


def main():
    if ARCHIVE.exists() or ARCHIVE.with_suffix('.manifest.json').exists():
        raise FileExistsError('Refusing to overwrite fixed head evidence')
    names = [DECISIONS/'state_000001.json', DECISIONS/'action_000001.json', CONFIG]
    for sec in range(150, 1051, 150):
        names += [DECISIONS/f'state_{sec:06d}.json', DECISIONS/f'action_{sec:06d}.json']
    raw = json.loads((ROOT/DECISIONS/'state_001050.json').read_text(encoding='utf-8-sig'))
    from pathlib import Path
    names.append(Path(raw['run_provenance']['manifest_path']).relative_to(ROOT))
    payload = {p.as_posix(): (ROOT/p).read_bytes() for p in names}
    rows = [{'path': p, 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()} for p,b in payload.items()]
    index = {'schema': 'review-fixtures/v1', 'original_workspace_roots': [str(ROOT)], 'files': rows,
             'scope': 'Complete observed NC v2 startup1 plus150..1050 raw JSON, previous/actual action JSON, run provenance, effective config; no FZP.'}
    with zipfile.ZipFile(ARCHIVE, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for name, data in {'index.json': (json.dumps(index, indent=2, ensure_ascii=False)+'\n').encode('utf-8'),
                           **{'raw/'+p:b for p,b in payload.items()}}.items():
            info = zipfile.ZipInfo(name, date_time=(2026,9,10,0,0,0)); info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, data, compresslevel=9)
    manifest = {'sha256': hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(), 'bytes': ARCHIVE.stat().st_size,
                'uncompressed_bytes': sum(r['bytes'] for r in rows), 'files': rows,
                'source_run': RUN, 'policy': index['scope']}
    ARCHIVE.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in manifest.items() if k != 'files'}))


if __name__ == '__main__':
    main()
