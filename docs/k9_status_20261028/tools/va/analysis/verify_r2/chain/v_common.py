# V-A 독립 검증 공통 정의 (보충 34 §8.0-3). 분석 도구(VA/analysis/tools)·stage1 도구를 import 하지 않음.
# J1 검증 도구 SP/j1/analysis/verify/v_common.py 의 정의를 V-A 런(9런: V-A 3·J1 3·NC3 3)으로 넓힌 것.
# 프로필: --profile va (V-A 팔 = RVA 런) | selftest (V-A 팔 = J1 런; 고정 전 자기 시험용).
# J1·NC3 의 FZP 행렬(fzp.npz)은 J1 검증 출력(SP/j1/analysis/verify/out/<tag>/)을 sha256 확인 뒤 다시 씀. 다르면 새로 만듦.
import ctypes, hashlib, io, json, math, os, sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
V = os.path.dirname(os.path.abspath(__file__))
SP = r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
J1V = SP + '/j1/analysis/verify/out'
RVA = r'D:/VISSIM_runs/20261023_sdmpc31_k92'
RR = r'D:/VISSIM_runs/20261004_sdmpc31_k8'
NCR = r'D:/VISSIM_runs/20261001_v3c3'
SEEDS = (31, 41, 43)
J1N = {31: 'sdmpc31_v3c3_k8j1r_s31', 41: 'sdmpc31_v3c3_k8j1_s41', 43: 'sdmpc31_v3c3_k8j1_s43'}
VAN = {s: 'sdmpc31_v3c3_k92va_s%d' % s for s in SEEDS}
# J1 검증 출력 fzp.npz sha256 (2026-10-23 확인, 재사용 조건)
J1V_NPZ_SHA16 = {'j1_s31': '14d460ef7425fa29', 'j1_s41': 'a0db5046c8eda530', 'j1_s43': '74c3e9fcb01f944f',
                 'nc3_s31': 'e3cf128829153f0d', 'nc3_s41': '927c1b93690969ad', 'nc3_s43': '6f674c57116c36d1'}
MEMBERSHIP = r'D:/VISSIM-merge/sim3/diagnostics/control_area_membership.json'
MAPPING = r'D:/VISSIM-merge/sim3/evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'
LINKSETS = r'D:/VISSIM-merge/review-d80faf9/diagnostics/vsl_handoff_20260924/evidence/accounting/east_link_sets_source.json'
# 구역 DSD 목록: stage1_common.DEFAULT_ZONE_DSDS 와 같은 값(정의값 복사; 코드 import 아님, J1 검증과 같음)
ZONE_DSDS = {
    'FW_E__seg0': [36, 37, 38, 39, 43, 44, 45, 46, 47, 48, 49, 50],
    'FW_E__seg5': [51, 52, 53, 54, 55, 56, 57, 58],
    'FW_E__seg10': [59, 60, 61, 62, 63, 64, 65, 66],
    'FW_E__seg15': [67, 68, 69, 71, 72, 73],
    'FW_W__seg0': [40, 41, 42, 75, 76, 77, 79, 80, 81],
    'FW_W__seg5': [83, 84, 85, 87, 88, 89, 90],
    'FW_W__seg10': [91, 92, 93, 94, 95, 96, 97, 98],
    'FW_W__seg15': [99, 100, 101, 102, 103, 104, 105, 106],
}
BIN = 150
NB = 60
T_END = 9000.0
T3 = 2.920


def profile():
    p = sys.argv[sys.argv.index('--profile') + 1] if '--profile' in sys.argv else 'va'
    if p not in ('va', 'selftest'):
        raise SystemExit('profile va|selftest')
    return p


def out_dir(prof):
    d = os.path.join(V, 'out' if prof == 'va' else 'selftest_out')
    os.makedirs(d, exist_ok=True)
    return d


def runs(prof):
    R = {}
    for s in SEEDS:
        R['nc3_s%d' % s] = dict(seed=s, arm='nc3',
                                fzp='%s/s%d_v3c3nc/run/vissim_eval/baseline_s%d_v3c3nc_001.fzp' % (NCR, s, s),
                                inpx='%s/s%d_v3c3nc/prepared/network/baseline_s%d_v3c3nc.inpx' % (NCR, s, s),
                                err='%s/s%d_v3c3nc/run/baseline_s%d_v3c3nc_001.err' % (NCR, s, s))
        for arm, root, name in (('j1', RR, J1N[s]), ('va', RVA if prof == 'va' else RR, VAN[s] if prof == 'va' else J1N[s])):
            R['%s_s%d' % (arm, s)] = dict(seed=s, arm=arm, name=name, dir='%s/%s' % (root, name), root=root,
                                          fzp='%s/%s/vissim_eval/sdmpc31_%s_001.fzp' % (root, name, name),
                                          inpx='%s/%s/network/sdmpc31_%s.inpx' % (root, name, name),
                                          err='%s/%s/network/sdmpc31_%s_001.err' % (root, name, name))
    return R


def npz_dir(prof, tag):
    """J1/NC3: J1 검증 출력(sha 맞을 때), 아니면 이 프로필 출력 폴더. V-A: 이 프로필 출력 폴더."""
    if not tag.startswith('va_'):
        d = os.path.join(J1V, tag)
        try:
            if sha(os.path.join(d, 'fzp.npz'))[:16] == J1V_NPZ_SHA16[tag]:
                return d
        except OSError:
            pass
    return os.path.join(out_dir(prof), tag)


def below_normal():
    try:
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    except Exception:
        pass


def jl(p):
    return json.load(io.open(p, encoding='utf-8-sig'))


def jd(o, p):
    with io.open(p + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(o, f, ensure_ascii=False, default=_d)
    os.replace(p + '.tmp', p)


def _d(o):
    try:
        import numpy as np
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
    except ImportError:
        pass
    return str(o)


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def parse_inpx(path):
    root = ET.parse(path).getroot()
    links = {}
    for el in root.find('links'):
        no = int(el.get('no'))
        pts = [(float(p.get('x')), float(p.get('y'))) for p in el.iter('linkPolyPoint')]
        ln = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
        rec = dict(no=no, length=ln, lanes=len(el.find('lanes')), name=el.get('name') or '')
        f, t = el.find('fromLinkEndPt'), el.find('toLinkEndPt')
        rec['conn'] = f is not None
        if f is not None:
            rec['from'] = int(f.get('lane').split()[0])
            rec['to'] = int(t.get('lane').split()[0])
        links[no] = rec
    inputs = []
    for el in root.find('vehicleInputs'):
        rows = []
        for v in el.iter('timeIntervalVehVolume'):
            rows.append(dict(start=float(v.get('timeInt').split()[-1]) / 1000.0, vph=float(v.get('volume')),
                             cont=(v.get('cont') == 'true')))
        rows.sort(key=lambda r: r['start'])
        inputs.append(dict(no=int(el.get('no')), link=int(el.get('link')), name=el.get('name'), rows=rows))
    dsds = {}
    for el in root.find('desSpeedDecisions'):
        lk, lnn = el.get('lane').split()
        dsds[int(el.get('no'))] = dict(link=int(lk), lane=int(lnn), pos=float(el.get('pos')))
    sim = root.find('simulation')
    return dict(links=links, inputs=inputs, dsds=dsds, seed=int(sim.get('randSeed')), simPeriod=sim.get('simPeriod'))


def schedule(inp, t_end=T_END):
    out, prev = [], 0.0
    rows = inp['rows']
    for i, r in enumerate(rows):
        end = rows[i + 1]['start'] if i + 1 < len(rows) else t_end
        end = min(end, t_end)
        rate = prev if r['cont'] else r['vph'] / 3600.0
        prev = rate
        if end > r['start']:
            out.append((r['start'], end, rate))
    return out


def chains():
    m = jl(MAPPING)['freeway_model_links']
    return {d: dict(links=m[d]['chain_links'], offs=dict(zip(m[d]['chain_links'], m[d]['chain_offsets_m'])),
                    length=m[d]['length_m']) for d in ('FW_E', 'FW_W')}


def membership():
    d = jl(MEMBERSHIP)
    assert d['schema'] == 'control-area-membership/v1' and not d['unresolved']
    ins = {int(x) for x in d['inside_links']}
    outs = {int(x) for x in d['outside_links']}
    assert not (ins & outs)
    return ins, outs, d


def sign_positions(net, ch):
    res = {}
    for z, ids in ZONE_DSDS.items():
        d = z.split('__')[0]
        offs = ch[d]['offs']
        pos = sorted(offs[net['dsds'][i]['link']] + net['dsds'][i]['pos'] for i in ids
                     if i in net['dsds'] and net['dsds'][i]['link'] in offs)
        res[z] = pos
    return res


def st(v, ncs):
    m = sum(v) / len(v)
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))
    h = T3 * sd / math.sqrt(len(v))
    ncm = sum(ncs) / len(ncs)
    return dict(d=list(v), mean=m, sd=sd, ci=[m - h, m + h], neg=sum(x < 0 for x in v), pos=sum(x > 0 for x in v),
                pct=(100 * m / ncm if ncm else None), ci_excl0=(m - h > 0) or (m + h < 0))
