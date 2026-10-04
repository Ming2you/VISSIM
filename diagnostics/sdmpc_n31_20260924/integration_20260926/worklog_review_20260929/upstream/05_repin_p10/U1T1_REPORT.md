# U1 T1 재판정 on v3c1 (RA-6)

- 작성 2026-09-28 19:3x. 대상 트리: `D:/VISSIM-merge/sim3-n31-v3c1` @ `5323faa` (동결본 `D:/VISSIM-merge/frozen/sdmpc31_5323faa4_202609281442`와 같은 HEAD).
- 표기: **[실행]** 이번에 직접 돌려 얻은 값 · **[읽음]** 코드·파일을 읽고 확인 · **[추론]** 시험하지 않은 판단.
- 이 폴더 = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/v3c1-p10/u1t1/` (아래에서 `B/`).

---

## 0. 결론

| 팔 | β 원천 | 튜닝 sha | 결정 수 | 판정 접근로 | 통과 |
|---|---|---|---|---|---|
| 기본 | `routing_v3c1` | 33027258 (커밋본) | 55 | 119 | **52** |
| U1 | `routing_v3c1_2` | 84d1b74b (scratch, U1만) | 55 | 119 | **114** |
| U1+U3 (확인용 3결정) | `routing_v3c1_2` | 8187505d (커밋본) | 3 | 119 | 114 |
| 참고: v3b T1 (urban-b1d, 09-26) | routing_v3b / v3b2 | — | 55 | 119 | 48 / 105 |

- [실행] U1은 v3b의 105 → **114/119**. 기본은 48 → **52/119**.
- [실행] v3b U1 실패 14개 중 **9개가 사라졌습니다.** 9개 모두 V1·V3·V4·V5·V6·V7 접근로(쌍둥이 포함)입니다.
- [실행] **남은 실패 5개**
  - SC1001|W: 결정별 게이트 β(U6)
  - SC12|W와 쌍둥이 SC12|W_SC11: V2 보류, 경로 없는 차량 54%
  - SC7|E와 쌍둥이 SC7|E_SC16: 단일 경로 결정 1102를 표가 무시함
- [실행] U1에서 통과하다 실패로 바뀐 접근로는 0개입니다(기본 팔도 0개). 정지선 커넥터 출구 불일치도 0건입니다.
- [실행] V1, V3–V7 여섯 정지선은 U1에서 모두 통과했습니다. 최대 편차는 0.002–0.005입니다.
  - U1 런타임 β는 v3c1 영수증 `expected_plant_beta.beta_v3c`와 같습니다(차 < 1e-4, 55결정 동안 변동 0).
- 주의: SC1004|W는 경계선에 있습니다. 5시드에서는 0.049로 통과하지만, 31/41/43 세 시드만 쓰면 0.058로 실패합니다(§5).

---

## 1. 규칙과 입력 (규칙은 v3b와 같음)

**어떤 T1인가.** v3b에서 "기본 48 → U1 105/119"를 낸 T1은 `urban-b1/t1_v2.py`가 아닙니다. 리뷰 U1-2에 따라 그것을 대체한 **독립 판정** `urban-b1d/t1_indep.py`입니다 [읽음].
- `urban-b1/wf_result_part2.txt:13-15`: t1_v2의 FZP 쪽은 검증 대상 표의 anchors를 씁니다. 그래서 순환 문제가 있어 교체했습니다.
- 같은 파일 `:100-102`: 독립 판정, 3시드, 119개, ±0.05에서 기본 48, U1 105.
- 이 재판정은 그 스크립트의 사본 `B/t1_indep_v3c1.py`를 씁니다.

**바뀐 것은 경로와 시드뿐입니다** [실행 `diff --strip-trailing-cr orig/t1_indep.py t1_indep_v3c1.py`].
- 망: `N31D/network/baseline_s31_v3c1nc.inpx` (sha 2577209b) [실행 sha256]
- 진입표: `beta/approach_entry_v3c1_20260928.json`
- 커넥터 점검용 표: `beta/movement_beta_routing_v3c1_2_20260928.json`
- 경로 파일: `B/paths/`
- 시드: 31/41/43/47/53 (`t1_indep_v3c1.py:47-51`)
- 추가 출력(시드별 분율, 결정별 β 범위, `--seeds`/`--out` 민감도 옵션)은 판정에 영향이 없습니다.

**규칙 문장** (v3b `orig/t1_indep.py:295-306`과 v3c1 `t1_indep_v3c1.py:317-329`가 같음)
- 출구: 차량 자신의 궤적으로 정합니다. 첫 out 링크, 또는 다음 신호 영역입니다. β 표와 anchors는 쓰지 않습니다.
- FZP 기대값: 시드별 분율의 시드 평균
- 판정 대상: 모든 시드에서 200대 이상
- 통과: 모든 출구가 ±0.05 안

**FZP 증거**
- v3c1 NC fit 5시드: `D:/VISSIM_runs/20260927_v3c1/s{31,41,43,47,53}_v3c1nc/run/vissim_eval/*_001.fzp`
- R-obs FZP는 따로 세지 않았습니다. 0.10 s 프레임 하나를 빼면 NC s31 FZP와 레코드가 같기 때문입니다 [실행].
  - `B/fzp_identity_skip_robs_vs_s31nc.json`: SIMSEC ≥ 5.0 데이터 줄 6,913,410 = 6,913,410, identical_records true
  - 판정 창이 t ≥ 900이라 그 프레임은 영향이 없습니다 [추론].

**런타임 증거 = R-obs 재생 포착**
- R-obs: `D:/VISSIM_runs/20260928_sdmpc31_v3c1/sdmpc31_v3c1_nc_s31` (무제어 + obs150, 결정 61개)
- 이 중 T ≥ 900인 55결정을 팔별로 오프라인 재생했습니다. 포착 위치는 첫 1스텝 예측(`capture_v3c1.py:170-175`)이고, 설치 연쇄와 결정별 게이트 β가 모두 끝난 뒤의 `urban_movements[*].beta`를 55결정 평균했습니다.
- 팔 설정
  - 기본: `config_n31_v2.json` (33027258), `urban.beta.source = routing_v3c1` [읽음]
  - U1: 커밋 생성기 `make_config_n31.build_urban_batch1(components=('U1',))`(`make_config_n31.py:435`)로 scratch `B/cfg/`에만 만들었습니다(84d1b74b, β 원천 `routing_v3c1_2`, sha 4979c05c).
    - 같은 호출이 커밋된 세 config를 바이트까지 재현합니다 [실행 `B/cfg/gen_cfg_result.json`: u1u3 8187505d, 전체 후보 ad482a53, 기본 33027258 모두 reproduced true].
  - 포착 metadata 확인 [실행]
    - 기본: `measured_beta_movements` 373
    - U1: 492, `measured_beta_complete` 1

---

## 2. 이어받은 것과 검증 (RESUME)

17:37에 시작한 시도가 세션 한도로 끊겼습니다. 폴더의 산출물은 믿지 않고 하나씩 확인한 뒤 썼습니다. 버린 것은 없습니다.

| 산출물 (이전 시도) | 확인 방법 | 결과 |
|---|---|---|
| `cfg/config_n31_v2_urban_b1_u1.json` (17:38) | 현재 sha, gen_cfg의 커밋본 3개 재현 기록 | 84d1b74b 일치, 재현 3/3 [실행] |
| `capture/base`, `capture/u1` 각 55개, `capture/spot_u1u3` 3개 (17:41–18:39; `captures.log` 끝에 MAINDONE·ALLDONE) | `resume/check_captures.py`로 레코드마다 확인. 항목: T 집합(900..9000 간격 150), tag, 튜닝 경로와 그 파일의 현재 sha, exit 0, 예측 ok, β 포착, compare IDENTICAL, ledger 실패 0, 예외 없음, 어댑터가 W 아래 | **113/113 이상 없음** [실행 `resume/check_captures.json`] |
| 포착 당시 트리 | `git reflog`: HEAD가 14:42 커밋 5323faa 이후 그대로. 지금 `git status` 비어 있음. 어댑터, make_config, β 표 둘이 FRZ와 바이트 동일 | 이상 없음 [실행]. 포착 중에도 깨끗했다는 것은 [추론] |
| `paths/paths_s{31,41,43,47,53}.jsonl` | fzp_paths.py md5가 urban-b1 원본과 같음(d27f1742). 줄 수 = 로그의 차량 수(67300/67511/67969/67479/67575). 원천 FZP의 mtime이 더 이름. rc=0 | 이상 없음 [실행] |
| `t1_fzp_exits.json` (17:45) | 같은 스크립트로 다시 돌림(24 s) | **바이트 동일** sha 1d4533d0 [실행] |
| `t1_routed_split.json`, `t1_routed_split_bydec.json` (17:47) | 다시 돌림 | **바이트 동일** [실행] |
| `fzp_identity*_robs_vs_s31nc.json` | 스크립트와 결과를 읽음 | 위 §1과 같음 [읽음] |
| `t1_indep_preview.json` (17:46) | 결정 4개만 쓴 미리보기. `resume/`에 사본만 둠 | 판정에는 안 씀. 참고로 52/114로 최종값과 같음 |

이번에 새로 한 일
- 전체 55결정 포착으로 판정: `t1_indep.json`, `logs/t1_judge.log`
- v3b 대조: `compare_v3b.json`, `logs/compare_v3b.log`
- 3시드 민감도: `t1_indep_s31_41_43.json`
- 세부표: `resume/u1t1_detail.json`, `.txt`
- 이 보고서

---

## 3. V1–V7 정지선 (V2는 보류라 참고로 함께 적음)

- V1, V3–V7은 6개 항목입니다. 결정은 8개(1160, 1162–1168)이고 정지선 링크는 6개입니다. 여기에 V2(보류)의 정지선을 더하면 7개입니다.
- 쌍둥이 접근로(같은 정지선 모집단)를 포함하면 판정 행은 9 + 2개입니다.
- 모두 [실행] (`resume/u1t1_detail.txt`)

| 항목 · 결정 | 접근로 (쌍둥이) | 정지선 | n/시드 | FZP 5시드 평균 | 기본 β → 최대편차 | U1 β → 최대편차 | v3b U1 |
|---|---|---|---|---|---|---|---|
| V1 · 1160 | SC109\|W_SC108 | 173 | 3349–3562 | E_out .822 / to_SC16 .178 | .826/.174 → .004 통과 | .826/.174 → **.004 통과** | .064 실패 |
| V3 · 1162 | SC5\|S (S_SC11) | 1220014100 | 1416–1514 | SC102 .521 / SC6 .304 / SC101 .175 | S .6/.2/.2 → .104 실패, S_SC11 .003 통과 | .5245/.3035/.172 → **.003 통과**(둘 다) | .172 실패 |
| V4 · 1163 | SC16\|N_SC12 | 1210012600 | 893–987 | SC109 .831 / E_out .161 / SC7 .008 | .737/.092/.171 → .163 실패 | .835/.157/.0075 → **.004 통과** | .124 실패 |
| V5 · 1164, 1165 | SC1\|N (N_SC101) | 1210008401 | 1844–2007 | SC107 .777 / SC105 .165 / SC11 .058 | N .556/.222/.222 → .222 실패, N_SC101 .113 실패 | .773/.1665/.061 → **.005 통과**(둘 다) | .108 실패 |
| V6 · 1166, 1167 | SC101\|S (S_SC1) | 1220011503 | 3230–3415 | SC2005 .673 / SC1002 .229 / SC5 .098 | S .6/.2/.2 → .102 실패, S_SC1 .002 통과 | .672/.231/.097 → **.002 통과**(둘 다) | .051 실패 |
| V7 · 1168 | SC104\|S_SC106 | 1220002001 | 2031–2110 | N_out .650 / E_out .290 / SC6 .060 | .653/.289/.058 → .003 통과 | 같음 → **.003 통과** | .194 실패 |
| V2 · (1161 보류) | SC12\|W (W_SC11) | 1220012103 | 960–1022 | SC6 .448 / SC16 .376 / SC106 .176 | .2/.6/.2 → .424 / .393 실패 | .492/.123/.385 → **.253 실패** | .243 실패 |

- 정지선 경로 상태 [실행 `t1_routed_split.json`]
  - V1, V3–V7: 다섯 시드 모두 경로 없는 차량 0.0입니다.
  - 정지선에서 본 결정 조합: V1 = 1081 + 1160, V3 = 1024 + 1162, V4 = 283 + 1163, V5 = 13 + 1164 + 1165, V6 = 1014 + 1166 + 1167, V7 = 1168뿐.
  - v3b에서 이 접근로들이 실패한 원인은 "경로 없는 차량 집단"이었습니다(`urban-b1/wf_result_part2.txt:60`). 그 원인이 망에서 사라졌습니다.
- 3시드(31/41/43)만 써도 V1, V3–V7의 판정은 모두 같습니다. U1 최대편차는 .001–.009입니다 [실행].
- 기본 팔의 변화
  - V1과 V7은 기본 `routing_v3c1`에서도 영수증 값과 같습니다(차 0).
  - 그래서 기본 팔도 4개가 실패 → 통과로 바뀌었습니다: SC109|W_SC108, SC104|S_SC106, SC5|S_SC11, SC101|S_SC1 [실행].
  - V3–V6의 주 접근로는 기본 팔에서 여전히 실패합니다.

---

## 4. v3b 실패 14개의 행방

v3b의 분류(`urban-b1d/guide_block.md:10`): 경로 없는 차량 집단 9, SC1001 W 게이트 β 1(U6), SC104 S_SC106 config 기본값 1, SC109 W_SC108 1, SC7 E 예외 2.

**사라진 9개** [실행]
- SC109|W_SC108 (V1)
- SC5|S, SC5|S_SC11 (V3)
- SC16|N_SC12 (V4)
- SC1|N, SC1|N_SC101 (V5)
- SC101|S, SC101|S_SC1 (V6)
- SC104|S_SC106 (V7)

**남은 5개** [실행 `resume/u1t1_detail.json` remaining_u1_failures]
1. **SC1001|W** — 결정별 게이트 β (U6). v3b 분류와 같습니다.
   - onW 런타임 평균 .602, FZP .669(시드별 .659–.674), 편차 .067(v3b .066).
   - 표 값은 .6667입니다 [읽음 routing_v3c1_2 approaches SC1001|W]. 그러나 런타임은 결정마다 게이트 몫으로 덮어씁니다. 결정 사이 β 범위가 .242입니다.
2. **SC12|W, SC12|W_SC11** — V2 보류. v3b와 같습니다.
   - 결정 31이 준 경로 차량(2254대): .386/.120/.494. U1 표(relFlow .385/.123/.492)와 맞습니다.
   - 경로 없는 차량(2684대, 시드별 51–57%): SC16 .591 / SC6 .409.
   - 편차 .253(v3b .243).
3. **SC7|E, SC7|E_SC16** — 기구가 바뀌었습니다.
   - v3b T1(09-26 07:18) 당시 U1 표는 SC7_E_to_N_SC11을 비존재로 선언했습니다. 그래서 런타임 0 대 FZP .223이었습니다.
   - 그 뒤 SC7 정정(urban-sc7, 커밋 3632fdf / cf3ce37에 포함 [읽음 `git log`])으로 표는 결정 252의 relFlow .571/.429를 줍니다. 현재 5323faa 표도 같습니다(`corrected_declarations`) [읽음].
   - 그래도 실패하는 이유: 정지선 모집단의 절반이 **단일 경로 결정 1102**입니다(1139대, 100% SC108). 나머지 절반인 결정 252(1145대)는 .551/.449입니다 [실행 `t1_routed_split_bydec.json`].
   - 유도기는 다중 경로 결정이 같은 정지선을 지나면 단일 경로 결정을 증거에서 뺍니다 [읽음 `scripts/derive_routing_beta_physical.py:611-621`; 표의 `single_route_decisions_ignored`에 SC7|E·E_SC16의 1102가 있음].
   - 편차 .204(v3b .223). SC7 트랙이 v3b에서 정정 뒤 .206이라고 적은 것(`urban-sc7/wf_result.txt:7,13,15`)과 같은 기구입니다.

---

## 5. 민감도와 경계

- [실행] 3시드(31/41/43, v3b와 같은 시드 수) 결과는 기본 52, U1 113입니다.
  - 차이 하나는 **SC1004|W**입니다: U1 onE .750 대 FZP .808, 편차 .058 → 실패.
  - 5시드에서는 FZP .799, 편차 .049로 통과합니다. 시드별 값은 .776–.818이고, v3b는 .041 통과였습니다.
  - U1 값 .75는 진입표의 게이트 peel-off 몫이라 결정 사이 변동이 0입니다.
  - 판정 기준선(±.05)에 붙어 있으므로, "114"는 SC1004|W 하나만큼 시드 집합에 민감합니다.
- [실행] U1의 판정 119개 중 편차 .035를 넘는 통과는 SC1004|W 하나뿐입니다. 편차 분포의 90분위는 .015입니다.
- v3b 대조는 시드 집합이 다릅니다(v3b는 31/41/37, v3c1은 31/41/43/47/53). 판정 대상 119개 집합은 같습니다. 판정되지 않은 4개(SC103|E, SC16|W, SC16|W_SC7, SC2001|S)도 v3b와 같습니다 [실행].

---

## 6. 재생 판정 (compare 두 가지)

- **판정용: `--tuning` 없는 compare** (`capture_v3c1.py:262`, P0-5와 같음) [실행]
  - IDENTICAL: 기본 55/55, U1 55/55, U1+U3 3/3
  - 확인 항목: 파생 관측, action CSV 바이트, 제어 필드, 계약
- **ps1 자체의 판정 (따로 보고)** [읽음·실행]
  - ps1은 `make_replay_state_v2.py compare <dir> --tuning <tuning>`을 부릅니다(`replay_decision_n31.ps1:144`). 이 호출은 `effective_vsl_max(load_effective_tuning(tuning))`를 기대 VSL로 씁니다(`make_replay_state_v2.py:326-330`).
  - 같은 함수와 같은 인자를 프로세스 안에서 불렀습니다(`capture_v3c1.py:266-270`). ps1 파일 자체는 실행하지 않았습니다.
  - 결과: 세 팔 모두 IDENTICAL, action_contract ok. 조건은 vsl_expected 110, VSL 66행 전부 110, 미터 8행입니다.
  - 알려진 도구 결함(`make_replay_state_v2.py:234-242`: `--tuning`이면 VSL 전부가 max여야 함)은 여기서 드러나지 않습니다. 무제어 재생이라 VSL이 모두 110이기 때문입니다.
- **action JSON 전체 diff** [실행]
  - 기본 팔 51/55는 경로 외 차이가 0입니다.
  - 4개(T2100, T2250, T3450, T4500)는 예측 요약 필드(`off_ramp_storage_veh`, `terminal_features.ramp_vehicles`)의 마지막 자리만 다릅니다(~1e-14). β와 제어에는 영향이 없습니다.
  - U1 팔은 예상대로 prediction, metadata, projection이 다릅니다. 제어는 같습니다(무제어).
- **장부** [실행]: 모든 포착에서 호출 2회, 최대 차이 ≤ 8.3e-9, 실패 0.

---

## 7. 제약 준수 [실행]

- VISSIM, cscript, ps1, 금지된 시험은 하나도 실행하지 않았습니다.
- 계산하는 python은 모두 `bn.py`로 BELOW_NORMAL(읽어 본 값 0x4000), 단일 스레드, `NUMBA_CACHE_DIR=C:\Users\TRLAB\AppData\Local\Temp\nbc_p10`로 한 번에 하나씩 돌렸습니다.
  - 이번 세션에서 돌린 것: FZP 재계산 24 s, 판정 두 번, 대조, 세부표, 경로 분할 재계산 두 번, 포착 점검
  - 몇 초짜리 JSON 조회 몇 번만 일반 우선순위의 `python -c`로 했습니다.
- worktree 상태
  - 작업 전후 `git status --porcelain`은 비어 있고 HEAD는 5323faa입니다.
  - `--ignored`에는 `evaluation/controllers/__tangentcache__/`(60개)만 있습니다. 파일 mtime이 12:22:59–12:23:02로 이 작업(17:37~) 전에 생긴 것이고, 이번에 바뀌지 않았습니다. 그래서 지우지 않았습니다.
  - 새 `__pycache__`는 0개입니다.
- 쓰기 위치: `B/`만(`B/replay/`는 비어 있음). FRZ와 R-obs 폴더는 읽기만 했습니다.
- 데이터 규율
  - seed 37 출력, RM 팔 출력, 봉인 시드는 열지 않았습니다.
  - 예외 하나를 밝혀 둡니다. v3b 대조에 쓴 09-26 결과 파일 `orig/t1_indep_v3b.json`(= `urban-b1d/t1_indep.json`)은 v3b s37을 포함한 3시드 집계입니다. 그 3시드 평균과 통과 여부만 썼고, 한 번은 그 안의 v3b 시드별 n을 터미널에 출력했습니다. s37 원출력 파일은 열지 않았습니다.
  - v3c1 영수증은 s37 망 sha 줄이 있는 JSON이지만, V 항목 정의만 읽었습니다.

---

## 8. 열린 문제

1. **SC7|E (2개)** — relFlow 규칙 안에서는 남는 실패입니다. 단일 경로 결정 1102(정지선 차량의 50%, 전부 SC108)를 증거로 넣을지는 사용자 결정입니다. 넣으면 relFlow만이 아니라 실측 가중이 필요합니다. U1 범위 밖입니다.
2. **SC12|W (2개)** — V2 보류의 직접 결과입니다(경로 없는 차량 54%).
3. **SC1001|W** — U6(결정별 게이트 β)이며 v3b와 같습니다.
4. **SC1004|W 경계** — 5시드 .049, 3시드 .058입니다. "114"를 인용할 때 이 하나가 경계라는 것을 함께 적어야 합니다.
5. U1만 켠 config는 scratch(`B/cfg/`)에만 있습니다. 커밋본은 U1+U3와 U1+U2+U3입니다. U1+U3 확인용 3결정의 β는 U1과 같은 결과(114)를 냈습니다.
6. worktree의 기존 `__tangentcache__`(12:23 생성, git 무시 대상)는 이 작업과 무관해서 그대로 두었습니다. "tangent cache 남기지 않기"를 worktree 전체 규칙으로 본다면, 누가 만든 것인지 확인한 뒤 정리해야 합니다.

---

## 9. 파일

- 판정: `B/t1_indep.json` (5시드, 판정 본), `B/t1_indep_s31_41_43.json` (민감도), `B/logs/t1_judge.log`, `B/logs/t1_judge_s3.log`
- 대조: `B/compare_v3b.json`, `B/logs/compare_v3b.log`
- 세부: `B/resume/u1t1_detail.json`, `B/resume/u1t1_detail.txt`, `B/t1_routed_split.json`, `B/t1_routed_split_bydec.json`
- 이어받기 검증: `B/resume/check_captures.py`, `B/resume/check_captures.json`, `B/resume/t1_fzp_rerun.log`, `B/resume/*prev*` (이전 산출 사본, 재계산과 바이트 동일)
- 스크립트: `B/t1_indep_v3c1.py`, `B/capture_v3c1.py`, `B/gen_cfg.py`, `B/compare_v3b.py`, `B/t1_routed_split.py`, `B/resume/u1t1_detail.py`, `B/bn.py`, `B/env.sh`
