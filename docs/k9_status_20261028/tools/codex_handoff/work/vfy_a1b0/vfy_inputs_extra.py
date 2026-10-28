# -*- coding: utf-8 -*-
"""VERIFY_A1_B0 추가(규칙 고정 뒤 더한 점검, 밝힘): T=1,050·1,200 결정의 나머지 입력 파일과 직전 명령 가격 상태 대조.

- obs150/{capture,err,mer,vsl_cohorts}_T, lane_observations/frame_T.json: A1 대 joint 바이트 같음, 다르면 잎 대조(값 잎 수).
- action_001050.json / action_000900.json metadata.sdmpc_state: A1 대 joint 잎 대조(가격·토큰).
분류는 vfy_trace.py 와 같은 규칙(경로꼴·64hex·시각꼴·부속 키 제외)을 이 파일에 다시 적음.
"""
import json, os, sys, re

OUT = sys.argv[1]
A1 = 'D:/VISSIM_runs/20261025_codex_a1_s29/sdmpc/decisions_sdmpc31_sdmpc8100_s29'
JT = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29'
HEX64 = re.compile(r'^[0-9a-fA-F]{64}$')
CLOCK = re.compile(r'\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}|^\d{8}T\d{6}|^\d{10}(\.\d+)?$')
ACCESSORY = {'run_id', 'byte_start', 'byte_end', 'max_t_any'}


def rd(p):
    with open(p, 'rb') as f:
        return f.read()


def flatten(x, p='', out=None):
    if out is None:
        out = {}
    if isinstance(x, dict):
        if not x:
            out[p + '/{}'] = '{}'
        for k, v in x.items():
            flatten(v, p + '/' + str(k), out)
    elif isinstance(x, list):
        if not x:
            out[p + '/[]'] = '[]'
        for i, v in enumerate(x):
            flatten(v, p + '/%d' % i, out)
    else:
        out[p] = x
    return out


def looks_path(s):
    return isinstance(s, str) and ('\\' in s or (':/' in s) or s.startswith('/'))


def classify(fa, fb):
    ka, kb = set(fa), set(fb)
    cls = {'path': 0, 'hex64': 0, 'clock': 0, 'accessory': 0, 'value': 0, 'only_a': len(ka - kb), 'only_b': len(kb - ka)}
    ex = []
    for k in sorted(ka & kb):
        a, b = fa[k], fb[k]
        if a == b and type(a) == type(b):
            continue
        last = k.rsplit('/', 1)[-1]
        if last in ACCESSORY:
            cls['accessory'] += 1
        elif isinstance(a, str) and isinstance(b, str) and HEX64.match(a) and HEX64.match(b):
            cls['hex64'] += 1
        elif looks_path(a) and looks_path(b):
            cls['path'] += 1
        elif isinstance(a, str) and isinstance(b, str) and CLOCK.search(a) and CLOCK.search(b):
            cls['clock'] += 1
        else:
            cls['value'] += 1
            if len(ex) < 10:
                ex.append([k, str(a)[:100], str(b)[:100]])
    return {'n_a': len(fa), 'n_b': len(fb), 'classes': cls, 'value_examples': ex}


def load_any(p):
    raw = rd(p)
    # r2 고침(꼴만): UTF-16 BOM 파일은 utf-16 으로 읽음(값 판단과 무관)
    b = raw.decode('utf-16') if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else raw.decode('utf-8-sig')
    if p.endswith('.jsonl'):
        return [json.loads(l) for l in b.splitlines() if l.strip()]
    return json.loads(b)


def main():
    res = {}
    for T in (1050, 1200):
        files = ['obs150/capture_%06d.json', 'obs150/err_%06d.jsonl', 'obs150/mer_%06d.jsonl',
                 'obs150/vsl_cohorts_%06d.json', 'lane_observations/frame_%06d.json']
        r = {}
        for f in files:
            pa, pb = os.path.join(A1, f % T), os.path.join(JT, f % T)
            if not (os.path.isfile(pa) and os.path.isfile(pb)):
                r[f % T] = {'exists_a1': os.path.isfile(pa), 'exists_joint': os.path.isfile(pb)}
                continue
            ba, bb = rd(pa), rd(pb)
            x = {'bytes_equal': ba == bb, 'size': [len(ba), len(bb)]}
            if ba != bb:
                x.update(classify(flatten(load_any(pa)), flatten(load_any(pb))))
            r[f % T] = x
        res[T] = r
    for T in (900, 1050):
        ja = json.loads(rd('%s/action_%06d.json' % (A1, T)).decode('utf-8-sig')).get('metadata', {}).get('sdmpc_state')
        jb = json.loads(rd('%s/action_%06d.json' % (JT, T)).decode('utf-8-sig')).get('metadata', {}).get('sdmpc_state')
        x = {'a1_has': ja is not None, 'joint_has': jb is not None}
        if ja is not None and jb is not None:
            x.update(classify(flatten(ja), flatten(jb)))
            x['next_prices_scaled'] = [ja.get('next_prices_scaled'), jb.get('next_prices_scaled')]
            x['policy_sha256_equal'] = ja.get('policy_sha256') == jb.get('policy_sha256')
        res['sdmpc_state_%d' % T] = x
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=str)
    print(json.dumps(res, ensure_ascii=False, default=str)[:4000])


if __name__ == '__main__':
    main()
