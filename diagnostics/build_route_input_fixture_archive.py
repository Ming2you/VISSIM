"""Preserve actual stopped1350/preceding1200 bytes; never overwrite an archive."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from diagnostics.review_fixtures import ROOT
from diagnostics.route_input_fixtures import ARCHIVE, RUN


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-observed', action='store_true',
                        help='Create v2 with the immutable v1 members plus the complete observed NC anchors.')
    args = parser.parse_args()
    archive = ARCHIVE.with_name('route_input_v2.zip') if args.include_observed else ARCHIVE
    manifest = archive.with_suffix('.manifest.json')
    if archive.exists() or manifest.exists():
        raise FileExistsError('Route/input fixture archive already exists')
    folder = f'evaluation/runs/{RUN}/decisions_{RUN}'
    paths = [f'{folder}/{name}' for name in (
        'state_001350.json', 'state_001200.json', 'action_001200.json', 'action_001050.json')]
    paths += [f'evaluation/runs/{RUN}/run_provenance_{RUN}.json',
        'diagnostics/fixtures/area_baseline_before_route_choice_beta0.json',
        'diagnostics/fixtures/area_baseline_before_route_choice_beta300.json',
        'diagnostics/fixtures/link10379_observed_record.json']
    payloads = {name: (ROOT/name).read_bytes() for name in paths}
    roots = [str(ROOT)]
    if args.include_observed:
        with zipfile.ZipFile(ARCHIVE) as original:
            original_index = json.loads(original.read('index.json'))
            roots = list(dict.fromkeys(roots + original_index['original_workspace_roots']))
            payloads = {}
            for item in original_index['files']:
                data = original.read('raw/'+item['path'])
                if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
                    raise ValueError('Prior archive member differs: '+item['path'])
                payloads[item['path']] = data
        observed = 'codex_area_observed_nc_s13_20260910'
        run = ROOT/'evaluation/runs'/observed
        decisions = run/('decisions_'+observed)
        added = [decisions/'state_000900.json', decisions/'action_000001.json',
                 run/('run_provenance_'+observed+'.json')]
        added += [decisions/f'anchor_{time:06d}.json' for time in (1500,1800,2100,2700,3600,4500,5400)]
        for path in added:
            payloads[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    index = {'schema': 'portable-review-fixtures/v1',
        'original_workspace_roots': roots,
        'files': [{'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                  for name, data in payloads.items()]}
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        bundle.writestr('index.json', json.dumps(index, ensure_ascii=False, indent=2)+'\n')
        for name, data in payloads.items():
            bundle.writestr('raw/'+name, data)
    result = {'archive': archive.name, 'bytes': archive.stat().st_size,
        'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'files': index['files'],
        'scope': 'Original retry1350/1200 snapshots, their actual previous actions and run manifest; explicit diagnostic pre-route/input baseline configs and observed10379 record. Numerical fields and historical source hashes are unchanged. Existing archives are not replaced.'}
    if args.include_observed:
        result['scope'] += ' V2 additionally preserves the complete observed NC900 state and seven later anchors, actual initial action and run provenance. No historical byte is replaced.'
    with zipfile.ZipFile(archive) as check:
        if check.testzip() is not None: raise ValueError('Fixture archive CRC check failed')
        for item in index['files']:
            if check.read('raw/'+item['path']) != payloads[item['path']]:
                raise ValueError('Written fixture bytes differ')
    manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'archive': str(archive), 'bytes': result['bytes'], 'sha256': result['sha256'], 'files': len(payloads)}))


if __name__ == '__main__':
    main()
