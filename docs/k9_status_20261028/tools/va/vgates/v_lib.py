"""VerifyGates (amendment 34 section 5.0 'independent verification') shared code, written from the declared text only.

Independent of the gate harness: nothing under VA/gates (gcommon, gjudge, gb7_k92decl, ...) is imported or executed.
Sources of the definitions:
  * deep diff path form = K7 gb_common.deep_diff (D:/VISSIM_runs/20261001_v3c3/reports/gb/gb_common.py:120-136):
    dict key '/key' (keys sorted by str), list element '[i]', one-sided key = one path ('presence'), list of other
    length = the list path ('list_length'), scalar differs in value or type = 'value' / 'type'.
  * list A = V u A_K8 of the frozen gb7_allowed.py.  That file IS the definition, so its source text is compiled and
    executed into a fresh dict (no import system, no __pycache__); its own sha and list sha are checked first.
  * E_K92 = amendment 34 section 5.2-3 text (four exact paths, replay side only, sha / value / binding conditions),
    re-implemented here (gb7_k92decl.py is not read for the implementation).
  * GB-7' conditions 1-8 = OG_METHOD section 2 + amendment 34 section 5.1 row 1; hash A/B = OG_METHOD section 3 +
    section 5.1 row 2; GB-9' = OG_METHOD section 4 + section 5.1 row 3; S = OG_METHOD section 5; G-H5' = section 5.1
    row 5.
BLIND: functions return paths, kinds, booleans, counts, sha256, wall seconds only."""
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

PY = r'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
FRZN = Path(r'D:/VISSIM-merge/frozen/sdmpc31_c20aff1d_202610230833')      # FRZ_K92 (PushFreeze record)
FRZ8 = Path(r'D:/VISSIM-merge/frozen/sdmpc31_b9734abe_202610141821')      # FRZ_K8b
FRZ7 = Path(r'D:/VISSIM-merge/frozen/sdmpc31_6c4c7400_202610011831')      # FRZ_K7 (R-obs3 recorded root)
FROZEN = Path(r'D:/VISSIM-merge/frozen')
WT = Path(r'D:/VISSIM-merge/sim3-n31-k8')                                  # GWT8
ROBS3 = Path(r'D:/VISSIM_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s31')
ROBS3_DEC = ROBS3 / 'decisions_sdmpc31_v3c3_nc_s31'
RR = Path(r'D:/VISSIM_runs/20261004_sdmpc31_k8')
J1 = {k: RR / v for k, v in (('31r', 'sdmpc31_v3c3_k8j1r_s31'), ('31', 'sdmpc31_v3c3_k8j1_s31'),
                              ('41', 'sdmpc31_v3c3_k8j1_s41'), ('43', 'sdmpc31_v3c3_k8j1_s43'))}
RVA = Path(r'D:/VISSIM_runs/20261023_sdmpc31_k92')
REPVA = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_va')
OUTVA = REPVA / 'offline_gates'
VGO = REPVA / 'verify_gates'
OUTH = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/offline_gates_k8h')
K7GB9 = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/gb/gb9/B')
VBT = Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1/vb2_e27ceac8')
VBCHAIN = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/vb2/chain')

HEAD = 'c20aff1d7bf0c432cb4f20e2922bd406d857aa5d'          # K9-2-7
HEAD_K926 = '11d99c2a4790f2bed1a610054e322ffff0253bc1'      # K9-2-6
HEAD_K925 = 'e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d'      # K9-2-5
HEAD_K8B = 'b9734abe1c83f95c9cec5fca5e42b7b18cd45991'
FREEZE_SHA = '011f5be253fd31a5fb8342859b2b571375e49b4bbbbb42ea8f3ca93657b68476'
FREEZE_K8B_SHA = '6143d3eb0d455e5fde46b190b4d4d8c2a7068a96c7fc9178126b922af937c7b6'
TUNING_SHA = 'c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866'
TUNING_K8B_SHA = 'd0f9ef395d4f9c51e6c68412f7c33abd546217e0d8cdc59d3c620183fa7aaec6'
TUNING_REL = 'diagnostics/sdmpc_n31_20260924/config_n31_v2.json'
GB7_REL = 'diagnostics/sdmpc_n31_20260924/k8_gates/gb7_allowed.py'
LIST_SHA = 'a8148f3849fb5e26f09d8f0a095d442aa56da051d888df0b2f657dba089e7af1'
LIST_K8B_SHA = 'f954c2b0510ddc8d77d8b5b6d2efb288eee4110e37eac935a4d153baefe366e7'
GB7_FILE_SHA = '61c70c222cf3bed2a0a299b539aa3fccad288c059b72be678cceda2c3dc6f319'
GB7_FILE_K8B_SHA = 'c6f9ca1cbf1e1ac49f1bc7adf44e33add289fea5858be8f5884c7225753894c8'
TOOL_SHA = {'make_replay_state_v2.py': '4adf41cfa7569047d87774bb648b353780fbb7ffc9b916a9c8f726e1d1de0714',
            'replay_decision_n31.ps1': '5d34109fdd61decaf3cbdd32c5b9d80a0768043d3c26fce83306f54144ce99c9'}
TOOLS_REL = 'diagnostics/sdmpc_n31_20260924/tools'
NET_SHA = '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e'
EK92_JUDGE_SHA = 'd15e9cc08a600a60edb29b945bdab407e4e4631f5b0e44bc2d7ac080dc11fb11'
EK92_SELFTEST_OUT_SHA = '666cbac34ace9b76025c66fc655468e733935a7e69e2fc93519c62a20f3c1110'
TIMES = [1] + [150 * k for k in range(1, 61)]
HASH_T = (4050, 4500, 9000)
HASH_SEEDS = ('unset', '0', '2')
GB9_T = (900, 2700, 4950, 6300)
SEEDS = (31, 41, 43)
CONTROL_FIELDS = ('N_P_star', 'N_UF_star', 'ramp_metering', 'vsl', 'green_times', 'offsets', 'inflow_outflow_allocation')

# ------------------------------------------------------------------------------------------------ E_K92 (5.2-3 text)
W_EVID_REL = 'diagnostics/sdmpc_n31_20260924/k92/sc109w_through_saturation_v3b_u4_20261016.json'
HB_EVID_REL = 'diagnostics/sdmpc_n31_20260924/k92/head_floor_seed_v3c3_robs_20261016.json'
W_EVID_SHA = 'b4b7294df0369874ea53dd5f0538abd31bac1c946aebdf241bdc7837a7671712'
HB_EVID_SHA = 'b9fa1d01b9d922e9fc327793aa428cd7b544dae221044704dea7f0af610f20ee'
U4_SHA = '22384c00313a0104a9febf5344914acd15f20058a0a62fe91d2bc085dcbb292b'
RULE_SHA = 'd9bd53920eea89ace2b71a589d780069c3c7191be889aca894994ddf65bcc106'
W_AFTER_REPR = '5209.8'
SEED_REPR = '1045.1612903225805'
FLOOR_KEY = 'head_discharge_floor_173_p4_e36d6761cfeac634'
FLOOR_173_RE = re.compile(r'head_discharge_floor_173_p4_[0-9a-f]{16}')


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(long(path), 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def git_blob_sha1(data):
    """git hash-object --no-filters of these bytes, computed here (sha1 of 'blob <n>\\0' + bytes)."""
    return hashlib.sha1(b'blob %d\x00' % len(data) + data).hexdigest()


def long(path):
    p = os.path.abspath(str(path))
    return p if p.startswith('\\\\?\\') else '\\\\?\\' + p


def read_json(path):
    with open(long(path), 'rb') as f:
        return json.loads(f.read().decode('utf-8-sig'))


def write_json(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, indent=1, ensure_ascii=False, default=str)
        f.write('\n')


def read_text(path):
    with open(long(path), 'rb') as f:
        return f.read().decode('utf-8-sig', errors='replace')


def same_path(a, b):
    if a is None or b is None:
        return False
    return os.path.normcase(os.path.normpath(str(a))).rstrip('\\') == os.path.normcase(os.path.normpath(str(b))).rstrip('\\')


def git(*args, cwd=WT, binary=False):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
    r = subprocess.run(['git', '-C', str(cwd)] + list(args), capture_output=True, env=env)
    return r.stdout if binary else r.stdout.decode('utf-8', errors='replace')


# ------------------------------------------------------------------------------------------------ deep diff (K7)
def deep_diff(a, b, path='', out=None):
    """List of (path, kind, side).  kind in presence / list_length / value / type; side = 'replay' or 'original' for
    presence (the side that HAS the key), else None.  Same traversal and path strings as K7 gb_common.deep_diff."""
    out = [] if out is None else out
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b), key=str):
            if key not in a or key not in b:
                out.append((f'{path}/{key}', 'presence', 'replay' if key in b else 'original'))
            else:
                deep_diff(a[key], b[key], f'{path}/{key}', out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((path, 'list_length', None))
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                deep_diff(x, y, f'{path}[{i}]', out)
    elif a != b or type(a) is not type(b):
        out.append((path, 'value' if type(a) is type(b) else 'type', None))
    return out


# ------------------------------------------------------------------------------------------------ list A
class AllowedList:
    """The frozen gb7_allowed.py, compiled from its bytes into a fresh namespace (definition, not gate tooling)."""

    def __init__(self, root, file_sha, list_sha, n_a):
        p = Path(root) / GB7_REL
        data = open(long(p), 'rb').read()
        self.file = str(p)
        self.file_sha256 = sha256_bytes(data)
        ns = {'__name__': 'gb7_allowed_vgates', '__file__': str(p)}
        exec(compile(data.decode('utf-8'), str(p), 'exec'), ns)  # noqa: S102 - the declared list is the definition
        self.ns = ns
        self.V = tuple(ns['V'])
        self.A_K8 = tuple(ns['A_K8'])
        self.list_sha256 = ns['list_sha256']()
        canon = json.dumps({'schema': ns['LIST_SCHEMA'], 'scan': ns['SCAN'], 'V': list(self.V),
                            'A_K8': [list(e) for e in self.A_K8]}, sort_keys=True, ensure_ascii=False,
                           separators=(',', ':'))
        self.list_sha256_recomputed = sha256_bytes(canon.encode('utf-8'))
        self.compiled = [(e[0], re.compile(e[2])) for e in self.A_K8]
        self.ok = (self.file_sha256 == file_sha and self.list_sha256 == list_sha == self.list_sha256_recomputed
                   and len(self.A_K8) == n_a and len(self.V) == 7)
        self.expect = {'file_sha256': file_sha, 'list_sha256': list_sha, 'A_K8': n_a, 'V': 7}

    def which(self, path):
        """'V', an A_K8 id, or None.  My own matcher (V exact, A_K8 regex fullmatch in list order); it is checked
        against the list module's own which() on every path (which_agrees)."""
        if path in self.V:
            return 'V'
        for i, rx in self.compiled:
            if rx.fullmatch(path):
                return i
        return None

    def which_module(self, path):
        return self.ns['which'](path)

    def record(self):
        return {'file': self.file, 'file_sha256': self.file_sha256, 'list_sha256': self.list_sha256,
                'list_sha256_recomputed': self.list_sha256_recomputed, 'A_K8': len(self.A_K8), 'V': len(self.V),
                'ok': self.ok, 'expect': self.expect}


# ------------------------------------------------------------------------------------------------ E_K92
def ek92_conditions(path, kind, side, a, b, ev_root, floor_key=FLOOR_KEY):
    """Amendment 34 section 5.2-3.  Returns (item, conds) where item in E1..E4 or None when path is not one of the
    four exact paths; conds = {name: bool}.  The path is in E_K92 only if every cond is True."""
    names = {'/metadata/k92_w': 'E1', '/metadata/k92_hb': 'E2', '/metadata/k92_hb_seed_binding': 'E3',
             '/metadata/' + floor_key: 'E4'}
    item = names.get(path)
    if item is None:
        return None, {}
    key = path[len('/metadata/'):]
    ma = a.get('metadata') if isinstance(a, dict) else None
    mb = b.get('metadata') if isinstance(b, dict) else None
    c = {'kind_presence': kind == 'presence',
         'replay_side_only': (side == 'replay' and isinstance(ma, dict) and isinstance(mb, dict)
                              and key not in ma and key in mb)}
    v = mb.get(key) if isinstance(mb, dict) else None
    if item == 'E1':
        c['is_dict'] = type(v) is dict
        vv = v if type(v) is dict else {}
        c['evidence_sha_fixed'] = vv.get('evidence_sha256') == W_EVID_SHA
        f = Path(ev_root) / W_EVID_REL
        c['evidence_sha_root_file'] = f.is_file() and vv.get('evidence_sha256') == sha256_file(f)
        c['u4_sha_fixed'] = vv.get('u4_sha256') == U4_SHA
        c['after_float_repr'] = type(vv.get('after')) is float and repr(vv.get('after')) == W_AFTER_REPR
    elif item == 'E2':
        c['is_dict'] = type(v) is dict
        vv = v if type(v) is dict else {}
        c['evidence_sha_fixed'] = vv.get('evidence_sha256') == HB_EVID_SHA
        f = Path(ev_root) / HB_EVID_REL
        c['evidence_sha_root_file'] = f.is_file() and vv.get('evidence_sha256') == sha256_file(f)
        c['rule_sha_fixed'] = vv.get('rule_code_sha256') == RULE_SHA
    elif item == 'E3':
        c['float_0_or_1'] = type(v) is float and v in (0.0, 1.0)
    else:
        c['name_exact'] = key == floor_key
        c['float_repr_s'] = type(v) is float and repr(v) == SEED_REPR
        bind = mb.get('k92_hb_seed_binding') if isinstance(mb, dict) else None
        c['binding_float_1'] = type(bind) is float and bind == 1.0
    return item, c


def cond7(a, b, allowed, ev_root, floor_key=FLOOR_KEY):
    """Condition 7 both ways: declared list A alone, and A u E_K92 (5.2).  Paths / kinds / booleans only."""
    diff = deep_diff(a, b)
    out_a, out_ae, hits, e_hits, e_failed, disagree = [], [], {}, [], [], []
    for p, kind, side in diff:
        w = allowed.which(p)
        if w != allowed.which_module(p):
            disagree.append(p)
        if w is None:
            out_a.append(p)
            item, conds = ek92_conditions(p, kind, side, a, b, ev_root, floor_key)
            if item is not None and all(conds.values()):
                e_hits.append([p, item])
                w = item
            else:
                out_ae.append(p)
                if item is not None:
                    e_failed.append({'path': p, 'item': item, 'false': sorted(k for k, v in conds.items() if not v)})
        h = hits.setdefault(w if w is not None else 'OUTSIDE', {'paths': 0, 'kinds': {}})
        h['paths'] += 1
        h['kinds'][kind] = h['kinds'].get(kind, 0) + 1
    return {'diff_count': len(diff), 'c7_declared_A': not out_a, 'c7_A_or_EK92': not out_ae,
            'outside_A': out_a, 'outside_A_and_EK92': out_ae, 'ek92_hits': e_hits, 'ek92_failed': e_failed,
            'hits': hits, 'which_disagree': disagree}


def control_fields_equal(a, b):
    return all(not deep_diff(a.get(k), b.get(k)) for k in CONTROL_FIELDS)


# ------------------------------------------------------------------------------------------------ text helpers
def lines_of(path):
    p = Path(path)
    return read_text(p).splitlines() if p.is_file() else None


def ps1_facts(text_lines, s6):
    """Facts from the replay_decision_n31.ps1 output text and the ps1 exit inferred from it
    (replay_decision_n31.ps1:19,31,141-146: refused -> 3, adapter exit != 0 -> 1, compare not IDENTICAL -> 2, else 0)."""
    L = text_lines or []
    refused = [l for l in L if l.startswith('REPLAY_REFUSED')]
    rl = [l for l in L if l.startswith('REPLAY_%s exit=' % s6)]
    m = re.match(r'REPLAY_\d{6} exit=(-?\d+) wall_sec=([\d.]+)', rl[-1]) if rl else None
    adapter_exit = int(m.group(1)) if m else None
    verdicts = [re.search(r'verdict=(\w+)', l).group(1) for l in L if l.startswith('REPLAY_COMPARE verdict=')]
    if refused:
        inferred = 3
    elif adapter_exit is None:
        inferred = None
    elif adapter_exit != 0:
        inferred = 1
    else:
        inferred = 0 if (verdicts and verdicts[-1] == 'IDENTICAL') else 2
    return {'refused': len(refused), 'adapter_exit_line': adapter_exit, 'compare_verdicts': verdicts,
            'ps1_exit_inferred': inferred,
            'freeze_lines': [l for l in L if 'FREEZE_VERIFIED' in l],
            'rebase_lines': [l for l in L if l.startswith('REBASE ')],
            'decision_failed': sum('DECISION_FAILED' in l for l in L)}


def count_in_file(path, needle):
    L = lines_of(path)
    return None if L is None else sum(needle in l for l in L)


# ------------------------------------------------------------------------------------------------ trees
EXCL_DIRS = ('__pycache__', '.pytest_cache', '.git', '__tangentcache__')


def tree_table(root, with_sha=True):
    """{rel: sha256} of every file under root with the FREEZE.json exclusions (dirs at any depth, name '.git',
    suffix .pyc, root FREEZE.json).  Written here from the FREEZE.json 'exclusions' field, not imported."""
    root_l = long(root)
    out = {}
    for cur, dirs, files in os.walk(root_l):
        dirs[:] = sorted(d for d in dirs if d.lower() not in EXCL_DIRS)
        rd = os.path.relpath(cur, root_l)
        for n in files:
            rel = (n if rd == '.' else os.path.join(rd, n)).replace('\\', '/')
            parts = rel.split('/')
            if any(x.lower() in EXCL_DIRS for x in parts[:-1]):
                continue
            if (len(parts) == 1 and n == 'FREEZE.json') or n.lower() == '.git' or n.lower().endswith('.pyc'):
                continue
            out[rel] = sha256_file(os.path.join(cur, n)) if with_sha else None
    return dict(sorted(out.items()))


def table_diff(expected, actual):
    return {'changed': sorted(k for k in expected.keys() & actual.keys() if expected[k] != actual[k]),
            'missing': sorted(expected.keys() - actual.keys()), 'extra': sorted(actual.keys() - expected.keys())}


def listing(root):
    """rel -> [size, mtime_ns] of every file (caches INCLUDED, nothing excluded); metadata only."""
    root_l = long(root)
    out = {}
    if not os.path.isdir(root_l):
        return None
    for cur, dirs, files in os.walk(root_l):
        dirs.sort()
        rd = os.path.relpath(cur, root_l)
        for n in files:
            p = os.path.join(cur, n)
            st = os.stat(p)
            out[(n if rd == '.' else os.path.join(rd, n)).replace('\\', '/')] = [st.st_size, st.st_mtime_ns]
    return out


def digest(obj):
    return sha256_bytes(json.dumps(obj, sort_keys=True, separators=(',', ':')).encode('utf-8'))
