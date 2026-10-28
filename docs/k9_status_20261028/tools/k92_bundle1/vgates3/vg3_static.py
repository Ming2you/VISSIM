"""VerifyGates 2 — static checks (no k92t output value): fixed documents, pin lists, judge thresholds against the
fixed amendments, judge / driver / VR bytes, GWT8 state, processes, drives.  Output OUTV/static.json."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vg3lib as V  # noqa: E402

AMD = {24: 'd46db6dc3959b19525f0fce77ead5432682e3de0ef8060cdc3da09661559aadc',
       25: '4fd7b599fe0f6131143e911dd3ab2be264a175e3f90b185bade9482d60b9ff8e',
       26: '8f8356168a299c07960d86ef12aa9f7af6f2f040af08ba75e5233a5819edba37',
       27: '4ce8b27a2ebf08aa0e8ac3f647b4e4336a98f7be7ec8d6f006a0fd1d12005a13',
       28: '9881eb40c1129af0cdff48026dc8656b4235d43f0eb80566e4be9b66d9ac345e',
       29: '4bd6dc8de8b0a4a4ab0b8703c07d7a73d244c4a622b81585f06dc69d6d83599d',
       30: 'ba556227a6356b1733bfa8125b334cfef180c1eed97e8d69ae4ba53a3106a56a'}
FIXED = {24: 'fbc3d59fe2e47fec00d87262d624aa9a163ed02e113609b06173841397df101a',
         25: 'd1338fbc40a2efaf6997667f59e7bd709951e1fd3f2b1a8a0a0881794c3d24ed',
         26: '6edc55acd5aa0976701456d956e33f33c52ae0853535f6a4d8cb8bf26a354581',
         27: '394ab15fdea0d945a3b766c208e692ee7e1086fca3c178f6b423079d71fedcdb',
         28: '14451cf4d46c5c0095bc896134112148ba5700ee70b2ed78b8ee38d0e62e20e5',
         29: '3ba1d0bdaab8a0189f903d10fc1024baed770080542cbd841f79d3a56df58e43'}
NOTES_SHA = {'eae2e6fa_182': 'eae2e6faf3c13dc42e84ef545fef734ad5ed9650946de72a76cb392b028c8d99'}
BYTES = {'KT/k92t.py': (V.KB / 'k92t' / 'k92t.py', 'b07ffb56789c30c8ef2f60f098ae7212fec52eec8a307b959bf26c44c6f02bec'),
         'KT/k92t_judge.py': (V.KB / 'k92t' / 'k92t_judge.py',
                              'eb4c113a6b7194cdf00d193d5faf07b426aae61a49ff84ae442bcf29b59fb28e'),
         'AD30/k92t30.py': (V.KB / 'a30decl' / 'k92t30.py',
                            '8f28171e7a3721a73f71216ca2823d179b78914dfbf70ef309a2b70fb5223ec4'),
         'AD30/k92t30_judge.py': (V.KB / 'a30decl' / 'k92t30_judge.py',
                                  'a1937942f06cb7d7e0be400dfc367691e9e6575061ed5aa00cee370f697fe7bf'),
         'TREE/SA/k92_vissim_ref.py': (V.TREE / V.SA_REL / 'k92_vissim_ref.py',
                                       'f3fcc574d72f67ed8ad43cc94387fc3138fca1e81ab2d14ecfd9768338344efd'),
         'TK/a27/k92t.build.json': (V.TK / 'a27' / 'k92t.build.json',
                                    'a1e98fa7' + ''),
         'KB/k92t_pins.sha256': (V.KB / 'k92t_pins.sha256',
                                 '38a2ce147795bbe7613fa5b6633441b31b814e781d1948e550753db776ed7cdd'),
         'KB/a30_pins.sha256': (V.KB / 'a30_pins.sha256',
                                '7afabd03f315c8925c4a8bb1b1566d246cbfb9273470876963df9e7fe4f3d30e')}
GWT8 = r'D:/VISSIM-merge/sim3-n31-k8'


def pins(path):
    lines = [x for x in Path(path).read_text(encoding='utf-8').splitlines() if x.strip()]
    bad = []
    for ln in lines:
        want, _, p = ln.partition(' *')
        if not Path(p).is_file() or V.sha_file(p) != want:
            bad.append(p)
    return {'n': len(lines), 'bad': bad[:10], 'ok': not bad}


def git(*a):
    return subprocess.run(['git', '--no-optional-locks', '-C', GWT8] + list(a), capture_output=True, text=True,
                          encoding='utf-8', errors='replace').stdout.strip()


def has(text, pat):
    return re.search(pat, text) is not None


def main():
    out = {'schema': 'vg3-static/v1', 'when': V.now(), 'tool_sha256': V.sha_file(Path(__file__))}
    a = {}
    for n, s in AMD.items():
        doc = V.SP / ('K8_PREDECLARATION_AMENDMENT_%d.md' % n)
        rec = (V.SP / ('K8_PREDECLARATION_AMENDMENT_%d.md.sha256' % n)).read_text(encoding='utf-8').split()[0]
        a[n] = {'doc': V.sha_file(doc) == s, 'sha_file': rec == s}
        fx = V.KB / ('AMENDMENT%d_FIXED.md' % n)
        a[n]['fixation'] = (V.sha_file(fx) == FIXED[n]) if n in FIXED else (s in fx.read_text(encoding='utf-8'))
    out['amendments'] = a
    lines = (V.SP / 'K9_1_J1_NOTES_20261013.md').read_bytes().splitlines(keepends=True)
    out['notes_first_182'] = V.sha_bytes(b''.join(lines[:182])) == NOTES_SHA['eae2e6fa_182']
    out['notes_lines'] = len(lines)
    out['bytes'] = {}
    for k, (p, want) in BYTES.items():
        got = V.sha_file(p) if Path(p).is_file() else None
        out['bytes'][k] = got is not None and got.startswith(want)
    out['pins_k92t'] = pins(V.KB / 'k92t_pins.sha256')
    out['pins_a30'] = pins(V.KB / 'a30_pins.sha256')
    out['a30_pins_eq_expected'] = V.sha_file(V.KB / 'a30_pins.sha256') == V.sha_file(
        V.KB / 'a30decl' / 'a30_pins.expected.sha256')
    # thresholds: amendment text vs judge text
    a24 = (V.SP / 'K8_PREDECLARATION_AMENDMENT_24.md').read_text(encoding='utf-8')
    a30 = (V.SP / 'K8_PREDECLARATION_AMENDMENT_30.md').read_text(encoding='utf-8')
    kg = (V.TREE / V.SA_REL / 'k92_gates.py').read_text(encoding='utf-8')
    j30 = (V.KB / 'a30decl' / 'k92t30_judge.py').read_text(encoding='utf-8')
    jb = (V.KB / 'k92t' / 'k92t_judge.py').read_text(encoding='utf-8')
    th = {
        'a24_F1_text': 'F-1 MAE_B1(M1, T+450) ≤ MAE_OFF(M1, T+450)' in a24,
        'a24_F2_text': 'F-2 |평균 편향_B1(M2, T+450)| ≤ |평균 편향_OFF(M2, T+450)|' in a24,
        'a24_F3_text': 'F-3 평균 편향_B1(M3, T+450) − 평균 편향_OFF(M3, T+450) ≤ +5대' in a24,
        'a24_wall_text': '벽시계 비 중앙 ≤ 1.0158' in a24 and '중앙 비 ≤ 1.0158(= 1.05 / 1.033718118959995' in a24,
        'a30_unchanged_text': 'J 잡 벽시계 문턱 1.0158' in a30 and 'F-1·F-2·F-3의 식·문턱' in a30,
        'judge_F1_code': has(kg, r"f1 = mae\(out\['M1_450'\]\['b1'\]\) <= mae\(out\['M1_450'\]\['off'\]\)"),
        'judge_F2_code': has(kg, r"f2 = abs\(bias\(out\['M2_450'\]\['b1'\]\)\) <= abs\(bias\(out\['M2_450'\]\['off'\]\)\)"),
        'judge_F3_code': has(kg, r"f3 = bias\(out\['M3_450'\]\['b1'\]\) - bias\(out\['M3_450'\]\['off'\]\) <= 5\.0"),
        'judge_err_sign': has(kg, r"r\[m\]\[0\] - r\[m\]\[1\]"),
        'judge_wall_k92t30': 'WALL_LIMIT = 1.05 / 1.033718118959995' in j30,
        'judge_wall_base': 'WALL_LIMIT = 1.05 / 1.033718118959995' in jb,
        'wall_limit_value': round(V.WALL_LIMIT, 6),
        'judge_f_n22': "fj['n'] == 22" in j30,
        'persist_rule': 'T_FROM_U4 = 900' in j30 and "PERSIST_LABEL = 'not measurable (T_FROM=900)'" in j30,
    }
    th['ok'] = all(v for k, v in th.items() if k != 'wall_limit_value') and abs(V.WALL_LIMIT - 1.0158) < 5e-5
    out['thresholds'] = th
    out['gwt8'] = {'head': git('rev-parse', 'HEAD'), 'branch': git('rev-parse', '--abbrev-ref', 'HEAD'),
                   'k8': git('rev-parse', 'claude/k8-sc1001eb-defects-20261004'),
                   'status_lines': len([x for x in git('status', '--porcelain').splitlines() if x.strip()]),
                   'commits_from_k8': len([x for x in git('rev-list', 'b9734abe..HEAD').splitlines() if x.strip()]),
                   'remote_k92': 'k92' in git('for-each-ref', '--format=%(refname)', 'refs/remotes')}
    out['gwt8']['ok'] = (out['gwt8']['head'] == 'e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d'
                         and out['gwt8']['branch'] == 'claude/k92-b1-20261016'
                         and out['gwt8']['k8'] == 'b9734abe1c83f95c9cec5fca5e42b7b18cd45991'
                         and out['gwt8']['status_lines'] == 0 and out['gwt8']['commits_from_k8'] == 6
                         and not out['gwt8']['remote_k92'])
    out['free_gb'] = {d: round(shutil.disk_usage(d + ':/').free / 2 ** 30, 1) for d in ('C', 'D')}
    out['ok'] = (all(all(v.values()) for v in a.values()) and out['notes_first_182'] and all(out['bytes'].values())
                 and out['pins_k92t']['ok'] and out['pins_k92t']['n'] == 56 and out['pins_a30']['ok']
                 and out['pins_a30']['n'] == 83 and out['a30_pins_eq_expected'] and th['ok'] and out['gwt8']['ok']
                 and all(v >= 8 for v in out['free_gb'].values()))
    V.wjson(V.OUTV / 'static.json', out)
    print('VG3_STATIC ok=%s thresholds=%s gwt8=%s pins=%s/%s %s/%s bytes=%s' % (
        out['ok'], th['ok'], out['gwt8']['ok'], out['pins_k92t']['n'], out['pins_k92t']['ok'], out['pins_a30']['n'],
        out['pins_a30']['ok'], [k for k, v in out['bytes'].items() if not v]))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
