"""Arm tunings for the SA gates (BASE = key absent, SAF = storage observed_full = judging arm D-K8-1,
SAG = storage geometric = report arm).

    python -B sa_arms.py [--root R] [--out O] [--source generate|repo] [--dry-run]
        -> <out>/sa/tuning/arms.json  {arm: {path, sha256, source, storage}}  (+ generated arm files)

BASE      <root>/diagnostics/sdmpc_n31_20260924/config_n31_v2.json (the deployed tuning, read in place)
SAF/SAG   --source generate (default): make_config_n31.apply_stopline_approach(<root config>, <root evidence>,
          storage) of the CODE ROOT, written to <out>/sa/tuning/config_n31_v2_stopline_<storage>.json (json indent 2,
          CRLF, like capture.py lgk); config-relative paths resolve against the adapter's workspace root, not the
          tuning location.  --source repo: the committed <root>/diagnostics/sdmpc_n31_20260924/
          config_n31_v2_stopline_<storage>.json (after the arm files are generated on the final base) - required to
          exist.  Either way the file must differ from BASE by exactly urban.stopline_approach (checked here)."""
import copy
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sa_common as sc  # noqa: E402

c = sc.c
N31 = Path('diagnostics') / 'sdmpc_n31_20260924'
EVIDENCE_REL = (N31 / 'stopline' / 'sc1001eb_evidence_v3c3_20261004.json').as_posix()


def arms_file():
    return sc.sa_out() / 'tuning' / 'arms.json'


def load_arms():
    data = sc.read_json(arms_file())
    if not data:
        raise SystemExit(f'arm tunings missing: run sa_arms.py first ({arms_file()})')
    for arm, row in data['arms'].items():
        if sc.sha256_file(row['path']) != row['sha256']:
            raise SystemExit(f'arm tuning {arm} changed since sa_arms.py: {row["path"]}')
    return data['arms']


def _make_config(root):
    path = root / N31 / 'make_config_n31.py'
    spec = importlib.util.spec_from_file_location('k8sa_make_config_n31', path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(path.parent))
    return module


def check_key_only(base_doc, arm_doc, storage):
    b, a = copy.deepcopy(base_doc), copy.deepcopy(arm_doc)
    section = a.get('urban', {}).pop('stopline_approach', None)
    if section is None or section.get('storage') != storage:
        raise SystemExit(f'arm {storage}: urban.stopline_approach missing or storage differs')
    if json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True):
        raise SystemExit(f'arm {storage}: differs from BASE outside urban.stopline_approach')
    return section


def main():
    ap = c.parser(__doc__)
    ap.add_argument('--source', choices=('generate', 'repo'), default='generate')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    c.apply(args)
    root = c.R
    base_path = root / N31 / 'config_n31_v2.json'
    rows = {'BASE': {'path': str(base_path), 'storage': None, 'source': 'root'}}
    for arm, storage in sc.STORAGE_OF_ARM.items():
        name = f'config_n31_v2_stopline_{storage}.json'
        path = (root / N31 / name) if args.source == 'repo' else (sc.sa_out() / 'tuning' / name)
        rows[arm] = {'path': str(path), 'storage': storage, 'source': args.source}
    if args.dry_run:
        for arm, row in rows.items():
            print(f'DRY {arm}: {row}')
        print('DRY ->', arms_file())
        return 0
    base_doc = json.loads(base_path.read_text(encoding='utf-8-sig'))
    if 'stopline_approach' in base_doc.get('urban', {}):
        raise SystemExit('BASE tuning already carries urban.stopline_approach (promotion happened?)')
    mc = _make_config(root) if args.source == 'generate' else None
    for arm, storage in sc.STORAGE_OF_ARM.items():
        path = Path(rows[arm]['path'])
        if args.source == 'generate':
            doc = mc.apply_stopline_approach(base_doc, EVIDENCE_REL, storage, root)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(json.dumps(doc, indent=2, ensure_ascii=False).replace('\n', '\r\n').encode('utf-8'))
        elif not path.is_file():
            raise SystemExit(f'repo arm tuning missing: {path}')
        doc = json.loads(path.read_text(encoding='utf-8-sig'))
        rows[arm]['section'] = check_key_only(base_doc, doc, storage)
    for row in rows.values():
        row['sha256'] = sc.sha256_file(row['path'])
    sc.write_json(arms_file(), {'schema': 'k8-sa-arms/v1', 'root': str(root), 'arms': rows})
    for arm, row in rows.items():
        print(f'SA_ARM {arm} sha16={row["sha256"][:16]} {row["path"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
