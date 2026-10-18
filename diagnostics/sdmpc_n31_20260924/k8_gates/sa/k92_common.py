"""K9-2 bundle 1 harness constants and the blind guard (K8_PREDECLARATION_AMENDMENT_24, fixed version d46db6dc...;
sections 2.0-7, 3.1-3a, 3.1-3b, 5.1, 5.3).  Diagnostics only: nothing here runs in the deployed path.

Guard k92_guard (replaces sa_common.k91_guard at the capture / job / full call sites; called before any child starts):
  (d) a tuning (or a template's capture metadata) carrying the H-b seed key urban.capacity.head_floor_seed without the
      W key urban.sc109w_through_saturation is refused everywhere (SystemExit K92_SEED_ALONE_REFUSED);
  (e) --gates-stage k92t --declaration-sha <amendment 24 sha> opens the judging stage; any other token or sha
      (k8bt / k91t included) is refused (SystemExit), never ignored;
  (f) the guard key is (run name, T): every harness state is an R-obs state, run = sdmpc31_v3c3_nc_s<seed>;
  k92_judging_state(run, T):
  (a) 'primary'      the F primary sample (v3c3-s47, 22 states): refused for every arm before k92t;
  (c) None           the F second sample (v3c3-s31 8 + v3c3-s43 8, an explicit exception to (b)) and the K8b probe
                     sample 26: allowed;
  (b) 'k91_judging'  every other K9-1 judging state (sa_common.k8b_judging_state): before k92t a run carrying a
                     K8b / K9 / K9-2 key is refused, a keyless run opens only the K9-1 section 0.4 closed list
                     (sa_common.k91_allowed; e.g. the DP 17 k86h SAF / BASE captures);
  None               any other state: allowed.
  With the stage open the first judging-state use is logged to <out>/sa/k92_judging_stage.json.
VISSIM reference blindness (section 3.1-3b): k92_vissim_blind(seed, args) is True for v3c3-s47 unless the stage is
open; the K9-2 recorder and k92_vissim_ref.py then leave every K9-2 VISSIM-side value null (reason k92_blind_s47)."""
import json
import time
from pathlib import Path

import sa_common as sc

K92_AMENDMENT24_SHA256 = 'd46db6dc3959b19525f0fce77ead5432682e3de0ef8060cdc3da09661559aadc'
K92_GATES_STAGE = 'k92t'
K92_W_PATH = ('urban', 'sc109w_through_saturation')
K92_HB_PATH = ('urban', 'capacity', 'head_floor_seed')
K92_KEY_PATHS = (K92_W_PATH, K92_HB_PATH)
K92_META_KEYS = ('k92_w', 'k92_hb')                    # capture metadata of a K9-2-keyed template
K92_BLIND_REASON = 'k92_blind_s47'
F_PRIMARY_SEED = 47
F_PRIMARY = (1050, 1650, 1950, 2400, 3300, 3750, 3900, 4650, 5100, 5550, 6000, 6150, 6450, 6600, 6900, 7050, 7350,
             7500, 7800, 7950, 8250, 8400)
F_SECOND = {31: (1500, 2850, 3900, 5250, 6000, 6600, 7500, 8250), 43: (1050, 3300, 4800, 5550, 6450, 7050, 7800, 8400)}
F_SECOND_STATES = frozenset((s, T) for s, Ts in F_SECOND.items() for T in Ts)
ROBS_RUN = sc.ROBS_NAME                                 # 'sdmpc31_v3c3_nc_s{seed}'
# 174 chain (amendment 24 section 5.3 M1-M3; P0-3 links fixed in K92_VALUES.json)
W_MOVEMENT = 'SC109_W_SC108_to_E'
L_MOVEMENT = 'SC109_W_SC108_to_N_SC16'
CHAIN_STOCKS = ('movement:SC109_W_SC108_to_E', 'movement:SC109_W_SC108_to_N_SC16', 'storage:SC108_to_SC109')
C0_ENTITIES = ('SC109_W_SC108_to_E', 'SC109_W_SC108_to_N_SC16', 'SC108_to_SC109', 'SC109_E_out', 'SC109_to_SC16',
               'out_SC109_E')
E_OUT = 'SC109_E_out'
E_OUT_STORAGE = 220.0
CHAIN_LINKS = ('21', '173', '174', '10024', '10112', '10280', '10281', '10285', '10286', '10293', '10300', '10303',
               '1220000600')
THROUGH_HEADS = ('1090201', '1090202', '1090203')
LEFT_HEADS = ('1090501', '1090502')
FEED4_STOCKS = ('storage:in_SC1004_S', 'storage:in_SC108_S', 'storage:in_SC16_E', 'storage:in_SC109_E',
                'movement:SC1004_S_to_E_SC1005', 'movement:SC1004_S_to_E_SC107', 'movement:SC1004_S_to_N_SC1003',
                'movement:SC1004_S_to_W', 'movement:SC108_S_to_E_SC109', 'movement:SC108_S_to_N_SC7',
                'movement:SC108_S_to_W', 'movement:SC108_S_to_W_SC107', 'movement:SC16_E_to_N_SC12',
                'movement:SC16_E_to_S', 'movement:SC16_E_to_S_SC109', 'movement:SC16_E_to_W', 'movement:SC16_E_to_W_SC7',
                'movement:SC109_E_to_N_SC16', 'movement:SC109_E_to_W_SC108')       # KA/METHOD.md:321 (19)
PHANTOM = 'movement:SC109_N_SC16_to_W_SC108'                                  # D-K9-19 report


def _value(doc, path):
    node = doc
    for key in path:
        node = node.get(key) if isinstance(node, dict) else None
    return node


def k92_keys_of(doc):
    """The K9-2 key paths present in a tuning document (dotted names, declaration order)."""
    return ['.'.join(p) for p in K92_KEY_PATHS if _value(doc or {}, p) is not None]


def k92_strip(doc):
    """A deep copy of `doc` without the two K9-2 key paths (arm identity, section 2.0-6)."""
    import copy
    out = copy.deepcopy(doc)
    for path in K92_KEY_PATHS:
        node = _value(out, path[:-1])
        if isinstance(node, dict):
            node.pop(path[-1], None)
    return out


def seed_alone(keys):
    """(d): the H-b seed without the W key (tuning key names or capture metadata names)."""
    ks = set(keys)
    has_seed = '.'.join(K92_HB_PATH) in ks or 'k92_hb' in ks or 'capture metadata k92_hb' in ks
    has_w = '.'.join(K92_W_PATH) in ks or 'k92_w' in ks or 'capture metadata k92_w' in ks
    return has_seed and not has_w


def run_name(seed):
    return ROBS_RUN.format(seed=int(seed))


def k92_judging_state(run, T):
    """(a) / (b) / (c) of section 3.1-3a on the guard key (run name, T)."""
    T = int(T)
    prefix = ROBS_RUN.split('{')[0]
    if not str(run).startswith(prefix):
        return None                                     # not an R-obs state (J1 run states are not harness states)
    seed = int(str(run)[len(prefix):])
    if seed == F_PRIMARY_SEED and T in F_PRIMARY:
        return 'primary'
    if (seed, T) in F_SECOND_STATES or (seed, T) in sc.K8B_PROBE_STATES:
        return None
    if sc.k8b_judging_state(seed, T):
        return 'k91_judging'
    return None


def k92_stage_open(args):
    """(e): True only for --gates-stage k92t with the amendment 24 sha; any other token or sha -- the old k8bt / k91t
    ones included -- is refused (SystemExit)."""
    stage = getattr(args, 'gates_stage', None)
    sha = getattr(args, 'declaration_sha', None)
    if stage is None and sha is None:
        return False
    if stage != K92_GATES_STAGE or sha != K92_AMENDMENT24_SHA256:
        raise SystemExit(f'K92_STAGE_REFUSED --gates-stage {stage!r} / --declaration-sha {sha!r}: the only judging '
                         f'stage is --gates-stage {K92_GATES_STAGE} --declaration-sha {K92_AMENDMENT24_SHA256} '
                         f'(amendment 24 sections 3.1-3a / 5.1; k8bt / k91t open nothing)')
    return True


def _mark(what, run, T, tuning_path, keys):
    mark = sc.sa_out() / 'k92_judging_stage.json'
    if mark.is_file():
        return
    sc.write_json(mark, {'schema': 'k92-judging-stage/v1', 'started': time.strftime('%Y-%m-%d %H:%M:%S'),
                         'first': {'what': what, 'run': run, 'T': int(T), 'tuning': str(tuning_path),
                                   'keys': list(keys)},
                         'amendment24_sha256': K92_AMENDMENT24_SHA256, 'root': str(sc.c.R)})


def k92_guard(tuning_path, seed, T, args, what, *, op, harness, arm, entry=None, H=None, variant='REF',
              mode='scalar', hooks=False, chain=None, arm_sha=None, extra_keys=()):
    """K9-2 blind guard (module docstring).  Returns the key list (K8b + K9 + K9-2 tuning keys + extra_keys)."""
    doc = sc._tuning_doc(tuning_path, 'K92 guard')
    keys = sc.guard_keys_of(doc) + k92_keys_of(doc)
    keys = keys + [str(k) for k in extra_keys if str(k) not in keys]
    if seed_alone(keys):
        raise SystemExit(f'K92_SEED_ALONE_REFUSED {what}: the H-b seed without the W key {keys} (D-K9-31, amendment 24 '
                         f'section 2.3-4)')
    opened = k92_stage_open(args)
    seed = sc.ROBS_SEED if seed is None else int(seed)
    run = run_name(seed)
    state = k92_judging_state(run, T)
    if state is None:
        return keys
    if opened:
        _mark(what, run, T, tuning_path, keys)
        return keys
    tag = (f'(amendment 24 section 3.1-3a; the judging stage is --gates-stage {K92_GATES_STAGE} --declaration-sha '
           f'<amendment 24 sha>)')
    if state == 'primary':
        raise SystemExit(f'K92_BLIND_REFUSED {what}: {run} T={T} is an F primary-sample state ({keys or "keyless"}) '
                         f'{tag}')
    if keys:
        raise SystemExit(f'K92_BLIND_REFUSED {what}: {run} T={T} is a K9-1 judging state and the run carries {keys} '
                         f'{tag}')
    sha = arm_sha or (sc.sha256_file(tuning_path) if tuning_path and Path(tuning_path).is_file() else None)
    nonscalar = sc.k91_nonscalar(op, variant, mode, hooks)
    if (op == 'full' or not nonscalar) and sc.k91_allowed(op, harness, arm, sha, T, entry=entry, H=H, variant=variant,
                                                          mode=mode, chain=chain):
        return keys
    raise SystemExit(f'K92_BLIND_REFUSED {what}: {run} T={T} is a K9-1 judging state and this keyless run ({op} '
                     f'{harness} {arm} sha {str(sha)[:8]}) is not on the K9-1 closed list {tag}')


def k92_vissim_blind(seed, args=None):
    """Section 3.1-3b: True when the K9-2 VISSIM-side values of this seed must stay null (v3c3-s47 before k92t)."""
    if int(seed) != F_PRIMARY_SEED:
        return False
    try:
        return not k92_stage_open(args) if args is not None else True
    except SystemExit:
        return True


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


# ------------------------------------------------------------------------------------------------ K9-2 arm (sa_arms --k92b1)
K92_EVIDENCE = {'w': 'diagnostics/sdmpc_n31_20260924/k92/sc109w_through_saturation_v3b_u4_20261016.json',
                'hb': 'diagnostics/sdmpc_n31_20260924/k92/head_floor_seed_v3c3_robs_20261016.json'}
K92_SCHEMA = {'w': 'k92-sc109w-through-saturation/v1', 'hb': 'k92-head-floor-seed/v1'}
SAF_K91_REL = 'diagnostics/sdmpc_n31_20260924/config_n31_v2_stopline_observed_full_k91.json'
SAF_K91_SHA256 = '5f0d0e40a39e44b3c7601f23177afbad8c2eee23d4421626482f2244a86c3341'
K92B1_SAF_FILE = 'config_n31_v2_stopline_observed_full_k91_k92b1.json'
K91_BASE_SHA256 = '319d07aac77472d4318ddf6266003916cb7afab98da35a06254952e393542bb8'


def k92_pin(part, root):
    """{'evidence': <repository-relative path>, 'evidence_sha256': <sha256 of its bytes>} of the committed K9-2
    evidence `part` (w / hb) in `root`; its schema must be the declared one."""
    import hashlib
    root = Path(root)
    path = (root / K92_EVIDENCE[part]).resolve(strict=True)
    if not path.is_relative_to(root.resolve()):
        raise SystemExit('K9-2 evidence must lie in the tree: %s' % path)
    data = path.read_bytes()
    if json.loads(data.decode('utf-8')).get('schema') != K92_SCHEMA[part]:
        raise SystemExit('K9-2 evidence %s: schema is not %s' % (path, K92_SCHEMA[part]))
    return {'evidence': path.relative_to(root.resolve()).as_posix(),
            'evidence_sha256': hashlib.sha256(data).hexdigest()}


def apply_k92b1(doc, root):
    """Pure on doc: the base tuning + the two K9-2 keys (urban.sc109w_through_saturation appended to urban,
    urban.capacity.head_floor_seed appended to urban.capacity; section 2.3: always together)."""
    import copy
    if k92_keys_of(doc):
        raise SystemExit('the base tuning already carries a K9-2 key %s' % k92_keys_of(doc))
    out = copy.deepcopy(doc)
    out['urban']['sc109w_through_saturation'] = k92_pin('w', root)
    out['urban']['capacity']['head_floor_seed'] = k92_pin('hb', root)
    return out


def dumps_tuning(doc):
    return (json.dumps(doc, indent=2, ensure_ascii=False) + chr(10)).encode('utf-8')
