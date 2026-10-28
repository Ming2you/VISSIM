"""Assemble the V-B r2 report from the hand-written parts and the pinned formatter output (session helper, formatting
only).  Section 9 sha values are computed here from the files, never typed.  Also checks every 64-hex token of the
hand-written parts against the files named next to it is NOT attempted; instead the hand parts carry only 16-hex
prefixes, which are checked against the computed full values below.

    python -B assemble.py <out.md>
"""
import hashlib
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SP = Path(r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/'
          r'scratchpad/k8')
KB = SP / 'k92' / 'bundle1'
KV2 = KB / 'k92_vb2'
VBR = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/vb2')
OK2 = VBR.parent
TK = Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1')


def sh(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


FILES = [
    ('보충 33 고정판 `SP/K8_PREDECLARATION_AMENDMENT_33.md`', SP / 'K8_PREDECLARATION_AMENDMENT_33.md'),
    ('고정점 `KB/AMENDMENT33_FIXED.md`', KB / 'AMENDMENT33_FIXED.md'),
    ('고정 목록 `KB/a33_pins.sha256`(= `AD33/a33_pins.expected.sha256`, 63줄)', KB / 'a33_pins.sha256'),
    ('새 훅 `AD33/vbhook/sitecustomize.py`', KB / 'a33decl' / 'vbhook' / 'sitecustomize.py'),
    ('구동기 `KV2/vb_chain.py`', KV2 / 'vb_chain.py'),
    ('재계산기 `KV2/vb_recalc.py`', KV2 / 'vb_recalc.py'),
    ('고르기 `AD32/vb_select.py`', KB / 'a32decl' / 'vb_select.py'),
    ('도움 함수 `AD32/vb_lib32.py`', KB / 'a32decl' / 'vb_lib32.py'),
    ('닫힌 잎 목록 `AD32/vb_closed_leaves.json`', KB / 'a32decl' / 'vb_closed_leaves.json'),
    ('세션 도우미 `KV2/poll_vb2.sh`(판정 도구 아님)', KV2 / 'poll_vb2.sh'),
    ('세션 도우미 `KV2/mk_vb2_tables.py`(판정 도구 아님)', KV2 / 'mk_vb2_tables.py'),
    ('표 도구 출력 `KV2/report/tables.md`', KV2 / 'report' / 'tables.md'),
    ('표 도구 출력 `KV2/report/tables_summary.json`', KV2 / 'report' / 'tables_summary.json'),
    ('`VBR/check_v0.json`', VBR / 'check_v0.json'),
    ('`VBR/zi/zi.json`', VBR / 'zi' / 'zi.json'),
    ('`VBR/zi/z1_off/zi_judge.json`', VBR / 'zi' / 'z1_off' / 'zi_judge.json'),
    ('`VBR/zi/z1_b1/zi_judge.json`', VBR / 'zi' / 'z1_b1' / 'zi_judge.json'),
    ('`VBR/zi/z2_b1/zi_judge.json`', VBR / 'zi' / 'z2_b1' / 'zi_judge.json'),
    ('`VBR/judge/vb_i1.json`', VBR / 'judge' / 'vb_i1.json'),
    ('`VBR/judge/vb_reportonly.json`', VBR / 'judge' / 'vb_reportonly.json'),
    ('`VBR/judge/vb_i.json`', VBR / 'judge' / 'vb_i.json'),
    ('`VBR/judge/vb_m.json`', VBR / 'judge' / 'vb_m.json'),
    ('`VBR/recalc/recalc.json`', VBR / 'recalc' / 'recalc.json'),
] + [('`VBR/stages/%s.json`' % s, VBR / 'stages' / ('%s.json' % s)) for s in
     ('V0', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6', 'V7', 'V8', 'V9', 'V10')] + [
    ('스냅숏 `OK2/snap/%s.json`' % s, OK2 / 'snap' / ('%s.json' % s)) for s in
    ('s43_vb2_v0', 's44_vb2_zi', 's45_vb2_off', 's46_vb2_end')] + [
    ('빌드 기록 `TK/vb2_e27ceac8.build.json`', TK / 'vb2_e27ceac8.build.json'),
    ('SAF-B1 `VBR/arms/sa/tuning/config_n31_v2_stopline_observed_full_k91_k92b1.json`',
     VBR / 'arms' / 'sa' / 'tuning' / 'config_n31_v2_stopline_observed_full_k91_k92b1.json'),
    ('STOP 판 r1 보관 사본 `KV/K92_VB_REPORT_stop_r1.md`', KB / 'k92_vb' / 'K92_VB_REPORT_stop_r1.md'),
    ('STOP 판 r1 보관 사본 `KB/VB_REPORT_stop_r1.md`', KB / 'VB_REPORT_stop_r1.md'),
    ('STOP 판 r1 보관 사본 `OK2/vb/K92_VB_REPORT.md`', OK2 / 'vb' / 'K92_VB_REPORT.md'),
]


def section_split(text):
    """Split the formatter output at '### ' / '#### ' headings -> list of (heading, body)."""
    out, cur, buf = [], None, []
    for line in text.splitlines():
        if line.startswith('### ') or line.startswith('#### '):
            if cur is not None:
                out.append((cur, '\n'.join(buf).strip('\n')))
            cur, buf = line, []
        else:
            buf.append(line)
    if cur is not None:
        out.append((cur, '\n'.join(buf).strip('\n')))
    return out


NOTES = {
    'ZI': ['- 상태는 V-B 55결정 밖의 RR v3c3-s43 두 시각입니다(z1: T=1,050 SS, z2: T=750 NN). 칸마다 같은 준비 폴더·같은 '
           '출력 경로로 훅 끔 → 훅 켬을 돌렸습니다(보충 32 §3.5).',
           '- 보충 32 P12(같은 경로면 16진 토큰도 같다는 [추론])는 이번 실행에서도 세 칸 모두 그대로였습니다 [실행 (z5) 참].',
           '- 새 훅이 더한 프로세스마다 `os.urandom(8)`·`time.time_ns()` 한 번이 결정 출력을 바꾸지 않았음을 세 칸이 '
           '보입니다(보충 33 P8) [실행].'],
    'VB-I1': ['- 비교 = `KC.compare(RR 결정 폴더, VBR/chain/<사슬>_off/dec, T, VBT, keyed=None, old_root=그 런의 동결본)`'
              '(보충 32 §2.1). 이 4결정도 새 훅을 켠 채 돌았으므로 "훅을 켠 결정 출력 = RR 기록"의 증거이기도 합니다.',
              '- 보충 32 P13(VB-41w T=1의 직접 선례 없음)은 이번 실행에서도 PASS였습니다 [실행].'],
    'RO': ['- 판정 아님, STOP 아님(D-K9-62·66). 결과 넷 값은 참고로만 적었습니다. 닫힌 목록 `AD32/vb_closed_leaves.json`'
           '(`b800be45…`)은 바꾸지 않았습니다.',
           '- 목록 밖 경로의 까닭 추론은 §0의 정해진 글에 있습니다. 목록 안 HARD 경로(NN·SN: `/prediction_error/'
           'source_action_json`; SS: 그것과 `/metadata/sdmpc_state/previous_application/receipt_sha256`·`…/source`)는 '
           '목록이 정한 대로 모두 보였습니다(보이지 않은 목록 잎 0).'],
    'I55': ['- **`selected`가 아닌 SDMPC 결정 2개(눈에 띄게 적음, 보충 32 §2.5)**: VB-41 B1 T=3,300(후보 3, 맞음 0)과 '
            'T=4,500(후보 2, 맞음 0), 상태 `no_match`. 그 두 결정의 VB-M5·M6·M8 = 없음(`record:no_match`). 두 결정의 고른 '
            '행동 SC109 p2·p3·p4는 바로 앞 B1 결정(T=3,150, T=4,350)과 같은 값입니다 [실행 §4.5 표]. 까닭은 이 보고에서 '
            '정하지 않습니다.',
            '- VB-I6: 하한 키 이름은 결정마다 하나이고 그 런의 기대 이름과 같습니다(`K92_VALUES.json` `/p0_2/'
            'f_expected_floor_keys`).'],
    'HOOK': ['- 이 절은 보고만입니다. 훅 이름 꼴·토큰 짝의 판정은 VerifyVB가 보충 33 §6.5 넷으로 합니다.',
             '- **PID 재사용 1번**: VB-41 B1 T=4,200 훅 폴더에서 PID 3024를 두 프로세스(토큰 둘)가 받았습니다. 새 이름에서는 '
             '두 토큰이 달라 폴더·파일이 겹치지 않았고, 두 토큰의 후보 `time_ns` 구간도 겹치지 않았습니다(차례로 뜬 두 '
             '프로세스) [실행]. 이 결정의 고르기 상태는 `selected`, VB-I7 참입니다. 옛 이름(보충 32)이었다면 r1과 같은 '
             '`hook_error`가 났을 꼴입니다 [추론].',
             '- `loaded` 수 = 토큰 수(381)이고, 후보가 있는 토큰 323 = 후보 폴더 323입니다. 토큰마다 후보는 한 개였습니다'
             '(작업자 한 프로세스가 `omega_costs`를 한 번 부름) [실행].'],
    'WALL': ['- 사슬 결정 벽시계 합: OFF 1.67 h, B1 6.53 h [계산]. 구동기 전체: 2026-10-22 15:28:04 발사 → 10-23 00:49:14 '
             '끝(약 9.4 h; ZI 약 0.8 h 포함) [실행]. 보충 33 §6.6 어림 9.5–10 h 안쪽입니다.',
             '- SDMPC 결정만: B1 35결정 중앙 710.4 s(354.5–795.5), OFF 8결정 중앙 733.5 s(615.3–787.0) [계산 `vb_m.json` '
             '`wall_run_sec`]. RR 기록 `decision_wall_sec`(같은 T, 35결정) 중앙 493.8 s는 재는 자리가 달라 같은 양이 '
             '아닙니다(기록 런은 VISSIM과 함께 돈 러너 안의 값).'],
}


def main(out):
    tables = section_split((KV2 / 'report' / 'tables.md').read_text(encoding='utf-8'))
    head = (HERE / 'part_head.md').read_text(encoding='utf-8')
    s4 = (HERE / 'part_s4.md').read_text(encoding='utf-8')
    tail = (HERE / 'static_tail.md').read_text(encoding='utf-8')
    disc = (HERE / 'static_disclosure.md').read_text(encoding='utf-8')
    L = [head.rstrip('\n'), '']
    sec3 = {'ZI 세 칸': ('3.1', 'ZI'), 'VB-I1 판정 4결정': ('3.2', 'VB-I1'), '보고 전용 10결정': ('3.3', 'RO'),
            'VB-I2·VB-I7 — OFF 14결정': ('3.4', None), 'VB-I2–VB-I7 (55결정': ('3.5', 'I55'),
            '훅 폴더 이름 요약': ('3.6', 'HOOK'), '사슬 결정 벽시계': ('3.7', 'WALL')}
    used = set()
    for hd, body in tables:
        for key, (num, note) in sec3.items():
            if hd.startswith('### ' + key):
                L.append('### %s %s' % (num, hd[4:]))
                L.append('')
                L.append(body)
                if note:
                    L.append('')
                    L.extend(NOTES[note])
                L.append('')
                used.add(key)
    assert used == set(sec3), used
    L.append(s4.rstrip('\n'))
    L.append('')
    n = 2
    for hd, body in tables:
        if hd.startswith('#### '):
            L.append('### 4.%d %s' % (n, hd[5:]))
            L.append('')
            L.append(body)
            L.append('')
            n += 1
    assert n == 6, n
    L.append(tail.rstrip('\n'))
    L.append('')
    L.append(disc.rstrip('\n'))
    L.append('')
    L.append('## 9. 파일과 sha256 (조립 때 파일에서 다시 계산)')
    L.append('')
    L.append('| 파일 | sha256 |')
    L.append('|---|---|')
    full = {}
    for label, p in FILES:
        h = sh(p)
        full[label] = h
        L.append('| %s | `%s` |' % (label, h))
    L.append('')
    L.append('- 이 보고서 자신의 sha256은 LOG의 보고서 항목에 적습니다(정본·사본 둘 같은 바이트).')
    text = '\n'.join(L) + '\n'
    # every 16-hex prefix in backticks that the hand parts quote must be a prefix of some computed / known sha
    known = set(full.values())
    Path(out).write_text(text, encoding='utf-8', newline='\n')
    pref = set(re.findall(r'`([0-9a-f]{16})`', head))
    miss = sorted(x for x in pref if not any(k.startswith(x) for k in known))
    print('written', out, len(text.splitlines()), 'lines; head 16-hex prefixes not in section 9:', miss)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
