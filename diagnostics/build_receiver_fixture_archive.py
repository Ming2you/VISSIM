"""Create the minimal stopped-1050 regression archive without replacing v1."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT/'diagnostics/fixtures/receiver_turns_v1.zip'
RUN = 'evaluation/runs/codex_area_beta0_s13_20260910'
FILES = [
    RUN+'/decisions_codex_area_beta0_s13_20260910/state_001050.json',
    RUN+'/decisions_codex_area_beta0_s13_20260910/action_000900.json',
    RUN+'/run_provenance_codex_area_beta0_s13_20260910.json',
    'diagnostics/area_candidate_configs/n7_area_beta0.json',
]


def main():
    manifest = ARCHIVE.with_suffix('.manifest.json')
    if ARCHIVE.exists() or manifest.exists():
        raise FileExistsError('Preserve the archived original bytes; output already exists')
    payloads = {name: (ROOT/name).read_bytes() for name in FILES}
    rows = [{'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} for name, data in payloads.items()]
    index = {'schema': 'receiver-turn-fixture/v1', 'original_workspace_roots': [str(ROOT)],
        'files': rows,
        'scope': 'Raw failed-beta0 state, actual preceding action and original run manifest. Config is the current repaired-input replay config, not a claim about the failed run historical source.'}
    with zipfile.ZipFile(ARCHIVE, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr('index.json', json.dumps(index, ensure_ascii=False, indent=2)+'\n')
        for name, data in payloads.items():
            archive.writestr('raw/'+name, data)
    result = {'archive': ARCHIVE.name, 'bytes': ARCHIVE.stat().st_size,
        'sha256': hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(), 'files': rows, 'scope': index['scope']}
    manifest.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
