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
          arm carrying a K8b key is refused.
--k91 (K9-1-0, K8_PREDECLARATION_AMENDMENT_19 r2 section 2.6): SAF / SAG = the K91 arms "SAF-K8b / SAG-K8b + the K9
          keys": --source repo reads <root>/diagnostics/sdmpc_n31_20260924/config_n31_v2_stopline_<storage>_k91.json
          (K9-1-4), --source generate writes make_config_n31.apply_k91(apply_k8b(apply_stopline_approach(...))) to
          <out>/sa/tuning/.  Checks (refused otherwise): BASE sha256 = 319d07aa... and BASE without K8b / K9 keys; the
          arm carries the three K8b keys and the three K9 keys urban.sc1001_wout_saturation, urban.wout_side_handoff,
          freeway.offramp_split_forecast (urban.latent_reservation_touch only in the Z1-b form, value true); with the
          four K9 key paths removed its JSON value equals the K8b arm file config_n31_v2_stopline_<storage>_k8b.json of
          the same root, whose sha256 must be the K8b-4 pin (SAF af2a7783..., SAG f5189611...).  Without --k91 an arm
          carrying a K9 key is refused.
--k92b1 (K9-2-0, K8_PREDECLARATION_AMENDMENT_24 sections 2.0-6 / 2.3 / 4.1 / 5.2; generate only): SAF = the SAF-K92b1
          arm "SAF-K91 + the W and H-b keys", written to <out>/sa/tuning/config_n31_v2_stopline_observed_full_k91_k92b1.json
          from the repository SAF-K91 file (sha 5f0d0e40..., json.dumps(indent=2) + LF bytes, no K9-2 key) with
          urban.sc109w_through_saturation and urban.capacity.head_floor_seed = the pins of the committed evidence
          (k92_common.K92_EVIDENCE, schema checked, sha of the bytes); checks: the arm differs from SAF-K91 in exactly
          these two paths, k92_strip(arm) = SAF-K91.  BASE = --base-file (the K9-1 BASE, sha 319d07aa..., for J-a /
          J-b) or no BASE row; no SAG row."""
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


def check_k91_arm(base_doc, arm_doc, storage, k8b_path, arm):
    """Amendment 19 r2 section 2.6: the K91 arm = the K8b-4 arm + the K9 keys (three; the Z1-b latent key optional)."""
    keys = sc.k9_keys_of(arm_doc)
    extra = [k for k in keys if k not in sc.K91_ARM_KEYS]
    if [k for k in keys if k in sc.K91_ARM_KEYS] != list(sc.K91_ARM_KEYS) or extra not in ([], [sc.K91_Z1B_KEY]):
        raise SystemExit(f'K91 arm {storage}: K9 keys {keys} != the three declared keys (+ the Z1-b key only)')
    if extra and arm_doc['urban'][sc.K91_Z1B_KEY.split('.')[1]] is not True:
        raise SystemExit(f'K91 arm {storage}: {sc.K91_Z1B_KEY} must be true when present')
    if sc.k8b_keys_of(arm_doc) != ['.'.join(p) for p in sc.K8B_KEY_PATHS]:
        raise SystemExit(f'K91 arm {storage}: K8b keys {sc.k8b_keys_of(arm_doc)} != all three')
    if sc.sha256_file(k8b_path) != sc.K91_K8B_ARM_SHA256[arm]:
        raise SystemExit(f'K91 arm {storage}: the K8b arm file {k8b_path} is not the K8b-4 pin')
    k8b = json.loads(Path(k8b_path).read_text(encoding='utf-8-sig'))
    if json.dumps(sc.k9_strip(arm_doc), sort_keys=True) != json.dumps(k8b, sort_keys=True):
        raise SystemExit(f'K91 arm {storage}: without the K9 keys it differs from the K8b arm {k8b_path}')
    b = copy.deepcopy(base_doc)
    a = sc.k9_strip(arm_doc)
    section = a.get('urban', {}).pop('stopline_approach', None)
    for key in ('sc1002w_saturation', 'wout_exit_law'):
        a.get('urban', {}).pop(key, None)
    if section is None or section.get('storage') != storage:
        raise SystemExit(f'K91 arm {storage}: urban.stopline_approach missing or storage differs')
    if json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True):
        raise SystemExit(f'K91 arm {storage}: differs from BASE outside the K8b / SA / K9 paths')
    return section, sc.k8b_keys_of(arm_doc), keys


def k92b1_arms(args):
    """--k92b1 (module docstring): arms.json with SAF = SAF-K92b1 (+ BASE = --base-file when given)."""
    import k92_common as k92c
    if args.k8b or args.k91:
        raise SystemExit('--k92b1 builds on the committed SAF-K91 file; pass it alone')
    if args.source != 'generate':
        raise SystemExit('--k92b1 writes the SAF-K92b1 arm (--source generate only)')
    root = c.R
    saf = root / k92c.SAF_K91_REL
    raw = saf.read_bytes()
    if sc.sha256_file(saf) != k92c.SAF_K91_SHA256:
        raise SystemExit(f'--k92b1: {saf} is not SAF-K91 {k92c.SAF_K91_SHA256[:16]}')
    base_doc = json.loads(raw.decode('utf-8'))
    if k92c.dumps_tuning(base_doc) != raw or k92c.k92_keys_of(base_doc):
        raise SystemExit('--k92b1: SAF-K91 is not json.dumps(indent=2) + LF bytes without a K9-2 key')
    arm = k92c.apply_k92b1(base_doc, root)
    if json.dumps(k92c.k92_strip(arm), sort_keys=True) != json.dumps(base_doc, sort_keys=True):
        raise SystemExit('--k92b1: the arm differs from SAF-K91 outside the two K9-2 paths')
    if k92c.k92_keys_of(arm) != ['urban.sc109w_through_saturation', 'urban.capacity.head_floor_seed']:
        raise SystemExit('--k92b1: the arm does not carry both K9-2 keys (D-K9-31)')
    path = sc.sa_out() / 'tuning' / k92c.K92B1_SAF_FILE
    rows = {}
    if args.base_file:
        if sc.sha256_file(args.base_file) != k92c.K91_BASE_SHA256:
            raise SystemExit(f'--base-file {args.base_file} is not the K9-1 BASE {k92c.K91_BASE_SHA256[:16]}')
        rows['BASE'] = {'path': str(Path(args.base_file).resolve()), 'storage': None, 'source': 'base-file',
                        'k8b_keys': [], 'k9_keys': [], 'k92_keys': []}
    if args.dry_run:
        print(f'DRY SAF -> {path}', rows)
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(k92c.dumps_tuning(arm))
    rows['SAF'] = {'path': str(path), 'storage': 'observed_full', 'source': 'generate', 'k8b_keys': sc.k8b_keys_of(arm),
                   'k9_keys': sc.k9_keys_of(arm), 'k92_keys': k92c.k92_keys_of(arm),
                   'pins': {'w': arm['urban']['sc109w_through_saturation'],
                            'hb': arm['urban']['capacity']['head_floor_seed']},
                   'base_saf_k91': {'path': str(saf), 'sha256': k92c.SAF_K91_SHA256}}
    for row in rows.values():
        row['sha256'] = sc.sha256_file(row['path'])
    sc.write_json(arms_file(), {'schema': 'k8-sa-arms/v1', 'root': str(root), 'k8b': True, 'k91': True, 'k92b1': True,
                                'amendment24_sha256': k92c.K92_AMENDMENT24_SHA256, 'arms': rows})
    for arm_name, row in rows.items():
        print(f'SA_ARM {arm_name} sha16={row["sha256"][:16]} {row["path"]}')
    return 0


def main():
    ap = c.parser(__doc__)
    ap.add_argument('--source', choices=('generate', 'repo'), default='generate')
    ap.add_argument('--k8b', action='store_true', help='K8b arms (amendment 16 section 5.2)')
    ap.add_argument('--k91', action='store_true', help='K91 arms (amendment 19 r2 section 2.6; implies the K8b base)')
    ap.add_argument('--k92b1', action='store_true', help='K9-2 bundle-1 SAF arm (amendment 24; generate only)')
    ap.add_argument('--base-file', help='--k92b1: the K9-1 BASE tuning (sha 319d07aa...) for the BASE row')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    c.apply(args)
    if args.k92b1:
        return k92b1_arms(args)
    if args.k91 and args.k8b:
        raise SystemExit('--k91 already holds the K8b keys; pass one of --k8b / --k91')
    root = c.R
    base_path = root / N31 / 'config_n31_v2.json'
    rows = {'BASE': {'path': str(base_path), 'storage': None, 'source': 'root'}}
    for arm, storage in sc.STORAGE_OF_ARM.items():
        name = (sc.K91_ARM_FILE.format(storage=storage) if args.k91 else
                sc.K8B_ARM_FILE.format(storage=storage) if args.k8b else f'config_n31_v2_stopline_{storage}.json')
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
    if (args.k8b or args.k91) and sc.sha256_file(base_path) != sc.K8B_BASE_SHA256:
        raise SystemExit(f'K8b: BASE {base_path} sha256 is not {sc.K8B_BASE_SHA256} (amendment 16 section 5.2 r2)')
    if sc.k8b_keys_of(base_doc):
        raise SystemExit('BASE tuning carries a K8b key (amendment 16 section 5.2: BASE has no K8b key)')
    if sc.k9_keys_of(base_doc):
        raise SystemExit('BASE tuning carries a K9 key (amendment 19 r2 section 2.6: BASE has no K9 key)')
    mc = _make_config(root) if args.source == 'generate' else None
    for arm, storage in sc.STORAGE_OF_ARM.items():
        path = Path(rows[arm]['path'])
        if args.source == 'generate':
            doc = mc.apply_stopline_approach(base_doc, EVIDENCE_REL, storage, root)
            if args.k8b or args.k91:
                doc = mc.apply_k8b(doc, root)
            if args.k91:
                doc = mc.apply_k91(doc, root)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(json.dumps(doc, indent=2, ensure_ascii=False).replace('\n', '\r\n').encode('utf-8'))
        elif not path.is_file():
            raise SystemExit(f'repo arm tuning missing: {path}')
        doc = json.loads(path.read_text(encoding='utf-8-sig'))
        if args.k91:
            k8b_path = root / N31 / sc.K8B_ARM_FILE.format(storage=storage)
            rows[arm]['section'], rows[arm]['k8b_keys'], rows[arm]['k9_keys'] = check_k91_arm(
                base_doc, doc, storage, k8b_path, arm)
            rows[arm]['k8b_arm'] = {'path': str(k8b_path), 'sha256': sc.sha256_file(k8b_path)}
        elif sc.k9_keys_of(doc):
            raise SystemExit(f'arm {storage}: carries K9 keys {sc.k9_keys_of(doc)} without --k91')
        elif args.k8b:
            k86h_path = root / N31 / f'config_n31_v2_stopline_{storage}.json'
            rows[arm]['section'], rows[arm]['k8b_keys'] = check_k8b_arm(base_doc, doc, storage, k86h_path, arm)
            rows[arm]['k86h_arm'] = {'path': str(k86h_path), 'sha256': sc.sha256_file(k86h_path)}
        else:
            rows[arm]['section'] = check_key_only(base_doc, doc, storage)
            if sc.k8b_keys_of(doc):
                raise SystemExit(f'arm {storage}: carries K8b keys {sc.k8b_keys_of(doc)} without --k8b')
            rows[arm]['k8b_keys'] = []
    rows['BASE']['k8b_keys'] = []
    rows['BASE']['k9_keys'] = []
    for row in rows.values():
        row['sha256'] = sc.sha256_file(row['path'])
        row.setdefault('k9_keys', [])
    sc.write_json(arms_file(), {'schema': 'k8-sa-arms/v1', 'root': str(root), 'k8b': bool(args.k8b or args.k91),
                                'k91': bool(args.k91),
                                'amendment16_sha256': sc.K8B_AMENDMENT16_SHA256 if (args.k8b or args.k91) else None,
                                'amendment19_sha256': sc.K91_AMENDMENT19_SHA256 if args.k91 else None,
                                'arms': rows})
    for arm, row in rows.items():
        print(f'SA_ARM {arm} sha16={row["sha256"][:16]} {row["path"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
