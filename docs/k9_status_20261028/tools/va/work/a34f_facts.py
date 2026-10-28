"""A34 finish 사실 확인 (V-A 데이터 0; 읽기 전용). 이름·sha·형·개수만 출력합니다. 목적값·예측값 출력 0.

(1) GWT8 작업 트리와 V-B 트리(VBT)의 K9-2 증거 파일 두 개 바이트 sha256, git blob(hash-object --no-filters)과 HEAD blob.
(2) V-B VB-41w B1 무제어 결정 T=1…750: metadata k92_w / k92_hb 의 키 이름, sha 잎 세 개, after·seed 형과 repr,
    k92_hb_seed_binding 형, (173,p4) 하한 키 이름. OFF 쪽에 같은 키가 있는지.
(3) R-obs3 v3c3-s31 61결정: metadata 키 가운데 k92_* 와 head_discharge_floor_173_p4_* 이름이 있는 T 목록.
"""
import hashlib
import json
import subprocess
from pathlib import Path

GWT8 = Path('D:/VISSIM-merge/sim3-n31-k8')
VBT = Path('D:/VISSIM-merge/k8_gate_trees/k92b1/vb2_e27ceac8')
VB = Path('D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/vb2/chain')
ROBS = Path('D:/VISSIM_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s31')
EV = ('diagnostics/sdmpc_n31_20260924/k92/sc109w_through_saturation_v3b_u4_20261016.json',
      'diagnostics/sdmpc_n31_20260924/k92/head_floor_seed_v3c3_robs_20261016.json')
FLOOR = 'head_discharge_floor_173_p4_'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git(*a):
    return subprocess.run(['git', '-C', str(GWT8), *a], capture_output=True, check=True).stdout.decode().strip()


def main():
    for rel in EV:
        print('EVIDENCE', rel.rsplit('/', 1)[1], 'gwt8_sha256=%s' % sha(GWT8 / rel),
              'vbt_sha256=%s' % (sha(VBT / rel) if (VBT / rel).is_file() else 'MISSING'),
              'hash_object_no_filters=%s' % git('hash-object', '--no-filters', rel),
              'head_blob=%s' % git('rev-parse', 'HEAD:' + rel))
    for t in (1, 150, 300, 450, 600, 750):
        s6 = '%06d' % t
        b1 = json.loads((VB / 'vb41w_b1' / 'dec' / ('action_%s.json' % s6)).read_text(encoding='utf-8-sig'))['metadata']
        off = json.loads((VB / 'vb41w_off' / 'dec' / ('action_%s.json' % s6)).read_text(encoding='utf-8-sig'))['metadata']
        w, hb = b1.get('k92_w'), b1.get('k92_hb')
        floors = sorted(k for k in b1 if k.startswith(FLOOR))
        print('VB41w_B1 T=%s k92_w_keys=%s' % (s6, sorted(w) if isinstance(w, dict) else type(w).__name__))
        print('   k92_w evidence_sha256=%s u4_sha256=%s after_type=%s after_repr=%s' % (
            w.get('evidence_sha256'), w.get('u4_sha256'), type(w.get('after')).__name__, repr(w.get('after'))))
        print('   k92_hb_keys=%s' % (sorted(hb) if isinstance(hb, dict) else type(hb).__name__))
        print('   k92_hb evidence_sha256=%s rule_code_sha256=%s seed_type=%s seed_repr=%s' % (
            hb.get('evidence_sha256'), hb.get('rule_code_sha256'), type(hb.get('seed')).__name__, repr(hb.get('seed'))))
        sb = b1.get('k92_hb_seed_binding')
        print('   binding_type=%s binding_in_0_1=%s floor_keys_b1=%s floor_value_type=%s floor_repr_is_s=%s' % (
            type(sb).__name__, sb in (0.0, 1.0), floors, [type(b1[k]).__name__ for k in floors],
            [repr(b1[k]) == '1045.1612903225805' for k in floors]))
        print('   OFF has: k92_w=%s k92_hb=%s binding=%s floor_keys_off=%s' % (
            'k92_w' in off, 'k92_hb' in off, 'k92_hb_seed_binding' in off, sorted(k for k in off if k.startswith(FLOOR))))
    names, k92 = {}, {}
    for t in [1] + [150 * k for k in range(1, 61)]:
        s6 = '%06d' % t
        cands = sorted(ROBS.glob('decisions_*/action_%s.json' % s6))
        if len(cands) != 1:
            print('ROBS3 T=%s files=%d' % (s6, len(cands)))
            continue
        md = json.loads(cands[0].read_text(encoding='utf-8-sig')).get('metadata', {})
        for k in md:
            if k.startswith(FLOOR):
                names.setdefault(k, []).append(t)
            if k.startswith('k92_'):
                k92.setdefault(k, []).append(t)
    for k, ts in sorted(names.items()):
        print('ROBS3 floor key %s T_count=%d first=%d last=%d' % (k, len(ts), ts[0], ts[-1]))
    print('ROBS3 k92_* keys:', {k: len(v) for k, v in k92.items()})


if __name__ == '__main__':
    main()
