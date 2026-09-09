# 검토 요청 — Ver2 21셀 격자: 망·매핑 정합성 + 컨트롤러 성능 부진 (2026-09-09)

검토해 주셨으면 하는 것 둘입니다.

1. **망·매핑 변경이 서로 맞는가** — 본선 격자를 8셀 → 21셀로 올리면서 매핑·VBS 계약·어댑터가
   같은 것을 가리키는지.
2. **왜 컨트롤러가 무제어를 못 이기는가** — 아래 사다리에서 최고가 −0.78% 이고, 미터링을
   켜면 +1.98% 로 뒤집힙니다.

망 파일(`network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx`) 자체는 **이번에 안 건드렸습니다**
(마지막 변경은 커밋 `3b1c03a`·`dd0d66f`). 바뀐 것은 그 위의 격자·매핑·컨트롤러입니다.

---

## 1. 이번에 바뀐 것

| 대상 | 내용 |
|---|---|
| 본선 격자 | 링크당 8셀 → **21셀** (2링크 42셀). 매핑 `evaluation/real_world_modi_control_ver2n21_20260907/` |
| 램프 배치 | 셀당 on/off-ramp 각 1개 이하가 되도록 재분할 (`outputs/freeway_ramp_split_v2_20260907.json`, 위반 0) |
| FD·동역학 | 21셀 격자 위에서 150 s 창으로 재보정 (`outputs/freeway_segment_params_dlit_20260908.json`) |
| VSL 자유도 | 셀 21개 → **표지판 구역 4개**(머리 셀 0/5/10/15), 구역 3은 `vsl_max` 고정 |
| 수요 | x15 (본선 배율 1.5). 무제어 기준 **7403.9** (`n21_x15_nocontrol_ver2_20260907`) |

### 정합성 관련해서 특히 봐 주셨으면 하는 자리

**(a) VSL 표지판과 구역.** 이 망의 VSL 은 방향당 표지판 **8개**이고 자리가 고정입니다 —
21셀 격자에서 셀 `0·2·5·7·10·13·15·18`, 간격 ~1,347 m. 근거 둘이 일치합니다:
매핑 `segments[].dsds`(DSD 보유 세그먼트 16 = 8 × 2방향)와 VBS `RW_EXPECTED_VSL_ACTION_KEYS`
66행(= `RW_EXPECTED_VSL_ACTION_ROWS`).

그런데 종전 모형은 **셀 21개에 각각 다른 VSL** 을 걸 수 있다고 보고 롤아웃했고, 플랜트는 그 8자리에만
씁니다. 반대로 팔로워의 자유 셀 규칙은 표지판이 아니라 "첫 off-ramp 상류"(`upstream_control_idx`)라
FW_E 는 8개 중 4개, FW_W 는 3개만 움직였습니다.

지금은 표지판 2개 간격으로 구역을 묶고 셀이 구역 머리 값을 상속합니다:

    구역 0 [셀 0-4]   2.57 km  상류 접근        가변
    구역 1 [셀 5-9]   2.57 km  첫 IC 포함        가변   (FW_E 램프 S8·S9 / FW_W S6·S7)
    구역 2 [셀 10-14] 2.57 km  둘째 IC 포함      가변   (FW_E S13·S14 / FW_W S11~S13)
    구역 3 [셀 15-20] 3.08 km  둘째 IC 하류      vsl_max 고정 (회복)

**봐 주셨으면 하는 점**: 구역 경계를 표지판 위치로만 잡았는데, 병목(FW_E S8/S9 램프 합류) 기준으로
잡는 게 더 맞는지. 그리고 구역 3을 고정한 것이 타당한지(하류 VSL 이 방류를 깎는 것을 막으려는 의도).

**(b) 매핑 `signals` 결함 (수정함).** `generate_real_world_control_mapping.py:908` 이
`"signals": REAL_WORLD_INTERFACE_SIGNALS` 로 **인터페이스 컨트롤러만**(SC1001, `id:"D"`) 싣는데,
런타임 `_signal_rows_for_mapping` 은 그것을 **전체 신호 목록**으로 읽습니다. 그래서 `{id}_{phase}` 조회가
전부 빗나가 p1/p2 는 진단 기본값(40 s), p3/p4 는 0 이 되고 `signal_group_action_rows` 가 죽습니다.

    SignalGroupPlanError: sc 1001: action commands green on phases ('p1','p2')
                          but the actuation plan has signal groups on ('p1','p2','p3','p4')

**증상이 조용합니다** — action JSON 은 예외 **전에** 써져서 `status=ok` 로 남고 시뮬도 완주합니다.
런로그 마지막 줄 `RUN_INTEGRITY_FAILURE decisions_failed=31` 만이 단서였습니다.
ver2 매핑 계열이 FD 스윕(무제어)용으로 만들어져 **제어런에 처음 쓰인 것이 2026-09-08** 이라 안 보였습니다.

수정: `scripts/fix_ver2n21_mapping_signals_20260908.py` — 통제 17개를 CLAUDE.md 지정 정본
`control_mapping_distributed_core17legs4b_20260819.json` 에서 가져오고, SC1001 의 `major_maps_to=p1`
과 인터페이스 주석을 보존하며, VBS `RW_SIGNAL_SCS` 와 sc_no 집합을 대조합니다.
**생성기는 안 고쳤습니다** — `REAL_WORLD_INTERFACE_SIGNALS` 가 `RW_SIGNAL_SCS` 생성에도 쓰여
의미를 바꾸면 VBS 상수까지 흔들립니다. 여기를 어떻게 정리하는 게 맞는지 의견 주시면 좋겠습니다.
**8셀 `control_mapping_ver2.json` 은 아직 같은 상태입니다.**

**(c) 세그먼트 VSL 이 플랜트에 도달하는 경로.** `actuation.active_lever_mask.enabled=false` +
`vsl_segment_override_policy="clear_when_mask_disabled"` 조합이 커밋 직전에 세그먼트 VSL 키 42개를
전부 지워, 플랜트가 방향당 값 하나만 받고 있었습니다(`vsl_segment_overrides_cleared=42`).
정본 n21 config 에서만 정책을 `keep` 으로 열었습니다. 마스크를 켜는 대신 정책만 연 이유는
마스크의 `allowed_ramps`(4개 중 3개)·`allowed_signals` 가 옛 실험 목록이라 켜면 다른 레버가 조용히
꺼지기 때문입니다. **이 판단이 맞는지 봐 주세요.**

---

## 2. 성능 — 사다리 결과 (수요 x15, 시드 13, 무제어 7403.9)

| 단 | 누적 구성 | TTT | 무제어 대비 | 직전 대비 |
|---|---|---:|---:|---:|
| n0 | canon (21셀 재보정) | 7433.7 | +29.8 (+0.40%) | — |
| n1 | +SPILL | 7390.1 | −13.8 (−0.19%) | −43.6 |
| **n2** | **+RL** | **7346.5** | **−57.4 (−0.78%)** | −43.6 |
| n3 | +METER+MF1 | 7550.3 | +146.4 (+1.98%) | **+203.8** |
| n4 | +PW25 | 7469.0 | +65.1 (+0.88%) | −81.3 |
| n5 | +B5 | 7483.8 | +79.9 (+1.08%) | +14.8 |
| n6 | +B0 | 7429.8 | +25.9 (+0.35%) | −54.0 |
| n7 | +SATV2 | (진행 중) | | |
| n8 | +SAT3 | (예정) | | |

전 단 무결성 정상: 결정 37/37 **적용**, `DECISIONS_FAILED=0`, `SIGNAL_MIDBLOCK_COM_SKIPS=744`.
(마지막 둘은 조용한 실패 두 종류를 각각 막는 관문입니다.)

### 우리가 읽는 그림

- **최고점이 −0.78%** 입니다. 21셀 재보정 자체(n0)는 무제어보다 오히려 나쁩니다.
- **METER+MF1 이 혼자 +203.8** 을 까먹고, 뒤 네 단이 합쳐 −120 을 되찾지만 원복이 안 됩니다.
  저장소에 기록된 사전 지식과 방향이 맞습니다 — 램프 미터는 플랜트에서 `{0, ≥600~1000, 열림}`
  3단계만 실현되고 부분 폐쇄는 허구이며, 미터를 닫는 주범은 `density_penalty` 입니다.
- VSL 은 이제 실제로 움직입니다(t=1800 이후 {80,100,120}, 구역 상수 유지). 다만 **FW_E 구역 0·1 만**
  쓰이고 구역 2·FW_W 는 한 번도 안 내려갔습니다.

### 검토 부탁드리는 질문

1. n0 가 무제어보다 나쁜 것이 **재보정 품질** 문제인지(150 s 창·문헌 제약 δ 0.3 / φ 3.0 이 둘 다
   제약 격자 상한에 붙어 있습니다), 아니면 **21셀 격자 자체**가 롤아웃 오차를 키운 것인지.
2. METER 손실이 **미터 고유**인지 **다른 조각과의 상호작용**인지. 이걸 가르려고 METER 를 뺀 가지를
   지금 큐에 걸어 두었습니다(`scripts/chain_n21_nometer_20260909.py`: n2 위에 PW25→B5→B0→SATV2→SAT3).
3. VSL 이 FW_W 와 구역 2에서 한 번도 안 쓰이는 것이 정상인지, 아니면 그 구역의 가격/후보가
   여전히 죽어 있는 것인지.

---

## 3. 성능(계산시간) 쪽에서 고친 것 — 참고

21셀로 올린 직후 결정이 **OOM 으로 죽어** 고정계획으로 폴백했습니다(`controller_error_type=MemoryError`,
`controller_status=fallback_fixed`). 원인은 `WuFaithfulFollower._freeway_vsl_sequence_candidates` 가
세그먼트별 VSL 옵션의 **데카르트 곱을 전량 전개**한 뒤에야 12개로 자르는 것 — 자유 셀이 8셀에서 3개(10³)
였는데 21셀에서 8개(**10⁸**)가 됩니다.

| | 결정 1회 (오프라인, 워커 10) | 직렬 |
|---|---:|---:|
| 수선 전 | OOM · 결정 불가 | 1,600 s 초과 |
| + k-best 지연 생성 | 113.7 s | 233.7 s |
| + 녹색분율 hot path | 106.6 s | — |
| + VSL 구역 | 106.8 s | 204.5 s |
| + 가격 롤아웃 중복 제거 | **89.6 s** | 152.2 s |

라이브 실측은 결정당 109~120 s 입니다(제어 간격 150 s). 워커를 10→16 으로 올리는 것은 **효과 0**
(113.7 vs 113.6 s) — 병목은 워커 수가 아니라 직렬 잔여입니다(결정 106.6 s 중 프로세스 풀 안 체류 34.3 s).

검증:

- k-best: 자유 셀 2/3/4 에서 원본과 **후보 목록 완전 일치**, 21셀에서 0.016 s
- 녹색분율: **제어 출력 비트 동치**(차이는 시간 진단 2개뿐), −3.1%
- 가격 중복 제거: **제어 출력 비트 동치**, 롤아웃 169 → 89, −25.6%
- VSL 구역: 머리가 전부 실제 표지판 자리, `segment_vsl` 구역 인식, 후보 구역 위반 0

관련 스크립트: `scripts/test_vsl_kbest_offline_20260908.py`, `scripts/test_vsl_zones_offline_20260908.py`,
`scripts/ab_decision_adapters_20260908.py`, `scripts/time_decision_parallel_20260908.py`.

---

## 4. 재현

```bash
# 사다리 (9단, 단당 ~90분)
N21_STALL_SEC=2400 python scripts/chain_n21_ladder_20260908.py 0

# METER 없는 가지 (n2 에서 분기, 5단)
N21_STALL_SEC=2400 python scripts/chain_n21_nometer_20260909.py 0
```

`StallSec` 이 2400 인 이유: 시뮬 시작 전 수요 스케일링 COM 한 번에 VISSIM 이 **8분** 붙잡혀 있고
그동안 워치독이 보는 파일이 하나도 안 바뀝니다(기본 300 s 로는 시뮬이 시작조차 못 합니다).

**커밋에서 뺀 것**: `outputs/fd_ver2_20260907/*_samples_*.csv`(48 MB)와 프로파일링 로그·PNG.
FD 적합 결과(JSON)와 경계조건 CSV 는 넣었습니다. 사다리가 만드는 rung config
(`evaluation/configs/n21_n*_20260908.json`)는 스크립트가 결정적으로 재생성하므로 뺐습니다.
