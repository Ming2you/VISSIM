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
          exist.  Either way the file must differ from BASE by exactly urban.stopline_approach (checked here).
--k8b (K8b-0, K8_PREDECLARATION_AMENDMENT_16 r2 section 5.2): SAF / SAG = the K8b arms "k86h SAF / SAG + the K8b keys":
          --source repo reads <root>/diagnostics/sdmpc_n31_20260924/config_n31_v2_stopline_<storage>_k8b.json (K8b-4),
          --source generate writes make_config_n31.apply_k8b(apply_stopline_approach(...)) to <out>/sa/tuning/.
          Checks (refused otherwise): BASE sha256 = 319d07aa... (r2 condition, not an expectation); the arm differs
          from BASE only at urban.stopline_approach (holding city_arrival), urban.sc1002w_saturation and
          urban.wout_exit_law and carries all three K8b keys; with those three paths removed its JSON value equals the
          k86h arm file config_n31_v2_stopline_<storage>.json of the same root, whose sha256 must be the k86h pin
          (SAF 178de6c2..., SAG 26e3be09...).  arms.json records each arm's K8b keys and both shas.  Without --k8b an
          arm carrying a K8b key is refused."""
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


def check_k8b_arm(base_doc, arm_doc, storage, k86h_path, arm):
    """Amendment 16 section 5.2 (r2): the K8b arm = the k86h arm + exactly the three K8b keys."""
    keys = sc.k8b_keys_of(arm_doc)
    if keys != ['.'.join(p) for p in sc.K8B_KEY_PATHS]:
        raise SystemExit(f'K8b arm {storage}: K8b keys {keys} != all three declared paths')
    b, a = copy.deepcopy(base_doc), copy.deepcopy(arm_doc)
    section = a.get('urban', {}).pop('stopline_approach', None)
    for key in ('sc1002w_saturation', 'wout_exit_law'):
        a.get('urban', {}).pop(key, None)
    if section is None or section.get('storage') != storage:
        raise SystemExit(f'K8b arm {storage}: urban.stopline_approach missing or storage differs')
    if json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True):
        raise SystemExit(f'K8b arm {storage}: differs from BASE outside the four declared paths')
    if sc.sha256_file(k86h_path) != sc.K8B_K86H_ARM_SHA256[arm]:
        raise SystemExit(f'K8b arm {storage}: the k86h arm file {k86h_path} is not the k86h pin')
    k86h = json.loads(Path(k86h_path).read_text(encoding='utf-8-sig'))
    if json.dumps(sc.k8b_strip(arm_doc), sort_keys=True) != json.dumps(k86h, sort_keys=True):
        raise SystemExit(f'K8b arm {storage}: without the K8b keys it differs from the k86h arm {k86h_path}')
    return section, keys


def main():
    ap = c.parser(__doc__)
    ap.add_argument('--source', choices=('generate', 'repo'), default='generate')
    ap.add_argument('--k8b', action='store_true', help='K8b arms (amendment 16 section 5.2)')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    c.apply(args)
    root = c.R
    base_path = root / N31 / 'config_n31_v2.json'
    rows = {'BASE': {'path': str(base_path), 'storage': None, 'source': 'root'}}
    for arm, storage in sc.STORAGE_OF_ARM.items():
        name = (sc.K8B_ARM_FILE.format(storage=storage) if args.k8b else f'config_n31_v2_stopline_{storage}.json')
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
    if args.k8b and sc.sha256_file(base_path) != sc.K8B_BASE_SHA256:
        raise SystemExit(f'K8b: BASE {base_path} sha256 is not {sc.K8B_BASE_SHA256} (amendment 16 section 5.2 r2)')
    if sc.k8b_keys_of(base_doc):
        raise SystemExit('BASE tuning carries a K8b key (amendment 16 section 5.2: BASE has no K8b key)')
    mc = _make_config(root) if args.source == 'generate' else None
    for arm, storage in sc.STORAGE_OF_ARM.items():
        path = Path(rows[arm]['path'])
        if args.source == 'generate':
            doc = mc.apply_stopline_approach(base_doc, EVIDENCE_REL, storage, root)
            if args.k8b:
                doc = mc.apply_k8b(doc, root)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(json.dumps(doc, indent=2, ensure_ascii=False).replace('\n', '\r\n').encode('utf-8'))
        elif not path.is_file():
            raise SystemExit(f'repo arm tuning missing: {path}')
        doc = json.loads(path.read_text(encoding='utf-8-sig'))
        if args.k8b:
            k86h_path = root / N31 / f'config_n31_v2_stopline_{storage}.json'
            rows[arm]['section'], rows[arm]['k8b_keys'] = check_k8b_arm(base_doc, doc, storage, k86h_path, arm)
            rows[arm]['k86h_arm'] = {'path': str(k86h_path), 'sha256': sc.sha256_file(k86h_path)}
        else:
            rows[arm]['section'] = check_key_only(base_doc, doc, storage)
            if sc.k8b_keys_of(doc):
                raise SystemExit(f'arm {storage}: carries K8b keys {sc.k8b_keys_of(doc)} without --k8b')
            rows[arm]['k8b_keys'] = []
    rows['BASE']['k8b_keys'] = []
    for row in rows.values():
        row['sha256'] = sc.sha256_file(row['path'])
    sc.write_json(arms_file(), {'schema': 'k8-sa-arms/v1', 'root': str(root), 'k8b': bool(args.k8b),
                                'amendment16_sha256': sc.K8B_AMENDMENT16_SHA256 if args.k8b else None,
                                'arms': rows})
    for arm, row in rows.items():
        print(f'SA_ARM {arm} sha16={row["sha256"][:16]} {row["path"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
