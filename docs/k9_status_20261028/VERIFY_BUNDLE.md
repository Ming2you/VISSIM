# VERIFY_BUNDLE — 묶음 검증과 고침 (2026-10-28 KST)

- **무엇**: `docs/k9_status_20261028/` 묶음을 푸시 전에 점검했습니다. 다섯 가지를 봤습니다. (1) STATUS 숫자를 원 보고서와 대조, (2) STATUS 링크, (3) 비밀 유지 다시 훑기, (4) 크기·바이너리, (5) MANIFEST 다시 만들기.
- **표시**: [실행] = 이번에 명령·도구로 확인 · [읽음] = 파일을 읽어 확인 · [계산] = 산술 · [추론] = 시험하지 않은 판단. 판정 낱말은 쓰지 않습니다.
- **쓴 곳**: 이 묶음 폴더와 `push_bundle/_work/`(검증 스크립트)뿐입니다. 원본(스크래치·저장소·메모리)은 읽기만 했습니다. git 은 상태를 바꾸지 않는 읽기 명령(`log`·`rev-parse`·`branch`·`rev-list`)만 썼습니다. VISSIM·무거운 일·FZP/npz 열기는 0 입니다 [실행]. 밝힘: 워크플로 목록을 거르던 명령 하나가 `/tmp/keep_wf.txt`(파일 이름 목록, 6 KB)를 묶음 밖에 썼고, 곧 지웠습니다 [실행].
- **줄임**: SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`. STATUS = `STATUS_20261028.md`.

---

## 0. 한눈에

1. [실행] **STATUS 가 묶음에 없었습니다.** digest 단계가 11:19 에 썼는데, 같은 때 돈 select 단계의 `finalize.py` 가 11:26 에 묶음 폴더를 통째로 지우고(`shutil.rmtree`) 다시 만들었습니다. digest 에이전트 기록에서 Write 1번 + Edit 8번을 차례대로 다시 적용해 복원했습니다. 복원본 sha256 = `6264fd95a6b29367eccb2bb628be75b020e726284b6b4c8fe1e7f67e802bde84`, 69,195 B, 588줄로 digest 가 보고한 값과 같습니다. 도구: `_work/recover_status.py`.
2. [실행·읽음] **숫자 대조**: STATUS 의 숫자·해시 약 470개를 원 보고서와 맞대 보았습니다(§1 표). §0 은 전부, FO·FW_E·C1 부분은 전부 봤습니다. 틀리거나 빠진 곳 9건을 고쳤습니다(§2). 원 보고서 값과 어긋난 숫자 자체는 1건(④b 옛 방법 차 "35.5")이고, 나머지는 범위·차례·자리 표기입니다.
3. [실행] **링크**: STATUS 의 상대 링크 가운데 27개(대상 21곳)가 묶음 안 파일을 가리키지 않았습니다(트랙 폴더 이름이 다름). 모두 실제 자리로 고쳤습니다. 지금 링크 79개(대상 60곳) 모두 열립니다(이 문서 링크 포함).
4. [실행] **비밀 유지**: 새 스캐너로 묶음 전체를 다시 훑었습니다. 시드 37 을 자료 시드로 쓴 9월 워크플로 23개와 메모리 2개를 뺐습니다. 11개 파일의 27곳을 가렸습니다. v3c3-s47·s53 이 섞인 다섯 시드 평균, v3c3-s53 결과 서술, 봉인 시드 37 이 섞인 v2 3시드 값이 대상입니다(§3).
5. [실행] **크기·바이너리**: 1 MB 넘는 파일 0, 전체 48.6 MB(80 MB 안). UTF-8 이 아니던 글 파일 9개를 UTF-8 로 바꿨습니다. NUL 바이트가 든 파일은 `.diff` 하나뿐입니다(허용된 패치 꼴, §4).
6. [실행] **MANIFEST** 를 지금 파일로 다시 만들었습니다(§5). 줄 수·sha 를 다시 세어 어긋남 0 을 확인했습니다.

---

## 1. 숫자 대조 (STATUS ↔ 원 보고서) [읽음·실행]

- 방법: STATUS 의 각 줄에 적힌 출처 보고서와 절을 묶음 사본(가림 전 원문과 같은 줄)에서 열어 숫자를 맞댔습니다. 커밋·브랜치는 `git log`·`rev-parse`(읽기)로, 동결본·런 뿌리는 폴더 있음으로, sha 앞 16자는 `sha256sum` 으로 봤습니다.

| STATUS 절 | 대조한 원천 | 맞댄 숫자(대략) | 결과 |
|---|---|---:|---|
| §0 한눈에 1–13 | FO_REPORT §0-2·§1.1, B_RESULTS §0, INPUT1099 §0-6, FWE_DECOMP T1, VP_RESULTS §0-3, VSL_RESULTS §0-2, P0_PROBE_R2 §0·§3, 보충 고정점 | 40 | 모두 같음 |
| §1 배경·지표 | R_NET §0·:147, HANDOFF_RESULTS §0-6·§1.1, VA_REPORT :29(t = 2.920) | 25 | 1건 고침(E1) |
| §2.1 J1 | J1_REPORT_CORRECTION §0-2, VA_REPORT §0-7, 결정 기록 :26, 메모리 j1-k8 | 18 | 같음 |
| §2.2 묶음 1·V-A | VA_REPORT §0, VA r4 §0-2·3, FO_REPORT §1.1 기준 열, HANDOFF §0-7, K92_VA_OFFLINE_GATES, GATES_K92B1, git log | 60 | 같음 |
| §2.3 미터 원인 | METER_CAUSE §0, METER_NEXT §0, METER_NEXT2 §1.1 | 25 | 같음 |
| §2.4 codex "8 %"·A1 | R_CLAIMS :21·:59-60, HANDOFF §0-2–10, A1_B0_RESULTS §0 | 35 | 같음(이 문서 계산 −17.9 다시 셈) |
| §2.5 망·수요 | R_NET §0, A1_B0 §0-6, HANDOFF §0-8, FWE_DECOMP T1 | 16 | 같음 |
| §2.6 B·1099 사슬 | B_RESULTS §0, INPUT1099 §0, P0_PROBE §3 Q20·Q21 | 45 | 1건 고침(E4, 빠진 칸) |
| §2.7 readback | READBACK_METER §0, C_PREP §0-1–3 | 10 | 같음 |
| §2.8 VSL | VSL_RESULTS §0, C_PREP §0-6·7, FWE_DECOMP T2 | 30 | 1건 고침(E3) |
| §2.9 우리 plant | VP_RESULTS §0, VERIFY_VP §0-3, 결정 기록 :362 | 22 | 같음 |
| §2.10 FW_E 분해 | FWE_DECOMP §0·T1–T4, R4_REPORT :27, 결정 기록 :370 | 32 | 1건 고침(E2) |
| §2.11 FO | FO_REPORT §0·§1.1·§1.3·§1.5·§5.3·§8·§9, VERIFY_FO §0·§3·§5 | 55 | 같음 |
| §2.12 첫 상태 경로 | C1_PROBE_RESULTS | 10 | 같음 |
| §2.13 가드 자료 | GENERAL_GUARD_DESIGN §0-5–13, 결정 기록 D-K9-107 | 20 | 같음 |
| §2.14 C1 P0·P0-17 | P0_PROBE_R2 §0–§9, P0_PROBE 표, c1 LOG :72·:181 | 22 | 같음 |
| §2.15 결함 목록 | METER_NEXT2 §1·§3, METER_NEXT §0-7, K9_3_DESIGN_DRAFT, git log | 14 | 1건 고침(E5, 차례 표기) |
| §3 코드 | `git log`·`rev-parse`(c20aff1d, b9734abe, bd39205d, a49981ff, 커밋 20개, 38·8 커밋 수), 동결본 7곳·런 뿌리 11곳 있음 | 40 | 같음. §3.3 자리 고침(E6) |
| §4 결정 요약 | 결정 기록 D-K9-58–116 표 줄 | 20(행) | 1건 고침(E5 와 같은 행 80) |
| §5 상태 | 결정 기록 D-K9-61·65·33, P0_PROBE_R2 §9, 메모리 codex-85e3454b(j1rc 2.1 GB) | 8 | 같음 |
| §8 파일 지도 sha 앞 16자 | 원본 52개 `sha256sum` | 52 | 원본과 모두 같음. 가림 사본 2개는 다름(E8) |

- 숫자 합 약 470개 [계산, 대략]. 시드 순서 "v3c3-s31 / s41 / s43" 와 Ω701 옆 ④·Ω 밖 (a) 짝은 모든 결과 줄에서 지켜졌습니다 [읽음].

## 2. STATUS 에서 고친 곳

| # | 자리 | 전 | 후 | 근거 |
|---|---|---|---|---|
| E0 | 파일 자체 | 묶음에 없음 | digest 기록으로 복원(§0-1), 머리에 검증 링크 한 줄 | `_work/recover_status.py` |
| E1 | §1.3 ④b 줄, §7.3 교훈 14 | 옛 방법 차 "최대 35.5 veh·h" | "최대 35.5(codex 꼴)·37.2(우리 꼴) veh·h" | HANDOFF_RESULTS §0-6 |
| E2 | §2.10 B 미터 조임 | "B 는 … GREEN<10 주기 71–100 %" | 범위는 B·codex 조인 팔을 합친 값. B 만은 585–810 / 810 = 72–100 % [계산] | FWE_DECOMP §0-4·T4 |
| E3 | §2.8 O2 | "VSL 구역을 8–37 km/h 느리게" | "VSL 구역과 그 앞(VSa −17 ~ −29, VSb −11 ~ −37, M1 −8 ~ −21 km/h)" | VSL_RESULTS §0-8 |
| E4 | §2.6 B − V-A 같은 부호 칸 | Ω 밖 (b) Ω701 기준·FW_W 본선(참고) 빠짐 | 두 칸 더함 | B_RESULTS §0-5 |
| E5 | §2.15 D1, §4 행 80 | 분할 행 차례 표기 없음(결정 기록 글은 (0.2, 0.6, 0.2)) | "차례 = 10681 · 10646 · 자유" 표기, 결정 기록 차례 함께 적음 | METER_NEXT2 :16, K9_3_DESIGN_DRAFT :374, 결정 기록 :265 |
| E6 | §3.3 번들 자리 칸 | `tools/c1/`·`tools/guard/`·`tools/fo/` 등(없는 폴더), `c1_probe.patch` 가 들어 있다고 적음 | 실제 폴더(`tools/c1/tools/` 등)로 고침, 패치는 1 MB 넘어 빠졌다고 적음 | `ls`, EXCLUDED.tsv |
| E7 | §8.1 | 보충 24…34 가 묶음에 있다고 적음 | 30–34 만 있음, 24–29 는 디스크에 없음. 고정점 링크 더함 | EXCLUDED.tsv(빌드 단계 6행) |
| E8 | §8 머리·§8.2 | sha 가 묶음 사본 값처럼 읽힘, METER_CAUSE "빠질 수 있음" | sha 는 스크래치 원본 값, 가림 사본(결정 기록 `9af6897b…`, METER_CAUSE 등)은 MANIFEST 를 보라고 적음 | `sha256sum` |
| E9 | §8.3 | P0-17 `result.json` 이 small_data 에 있다고 적음, 워크플로 168·메모리 105 | result.json 은 TC1(D:)에만 있음(스크래치에 없어 넣지 못함), 워크플로 145·메모리 103 | `ls`, 원본 자리 확인 |
| L | 링크 27개 | `reports/fo/`·`reports/guard/`·`reports/k92_va/` 등 | `reports/codex_fo/`·`reports/c1_guard_general/`·`reports/va/analysis/` 등, PRE_FO·COMPARE_RULE_FO·PRE_FWE 는 `predeclarations/` | §0-3 |

- 지금 STATUS: sha256 `9ec17eaab9f9805c137ccccfd3411122a0cadc8b0567caa8486bbb51176d0913`, 590줄, 71,500 B [실행].

## 3. 비밀 유지 다시 훑기

- 도구 [실행]: `_work/vscan.py`(빌드 단계 스캐너를 쓰지 않은 새 스캐너). 묶음의 모든 파일을 UTF-8 로 읽어 (가) `s37`·`seed47`·`nc_s53` 같은 시드 표지 뒤 60자 안의 숫자, (나) `31/41/43/47/53` 같은 시드 목록 뒤의 값 목록, (다) JSON 의 시드 열쇠·seed 칸, (라) 자격 증명 꼴(토큰·키·비밀번호)을 셌습니다. 뽑힌 줄은 사람이 읽어 갈랐습니다. 이어 "31/41/37" 처럼 시드 37 을 자료 시드로 쓴 문맥을 따로 찾았습니다.
- 규칙: 봉인 시드 37·59·61·67(모든 망), codex 64cf-s59/s61/s67, v3c3-s47·v3c3-s53 의 결과 숫자는 넣지 않습니다. 그 시드가 섞인 평균·범위 끝값도 결과 숫자로 봅니다(rmcause 보고서들이 이미 따른 꼴, INV_PRIOR :138).

### 3.1 뺀 파일 25개 (EXCLUDED.tsv 에 "검증 단계" 로 더함)

- 워크플로 23개: 시드 37 을 자료 시드로 쓴 9월 스크립트(v2 stage-1 31/41/37, v3b 31/41/37, seedvar 31/37/41). 예: `stage2-plant-rm-response`(3시드 평균 RM − NC 값), `urban-plant-diag-and-rm-replan`(s31/s41/s37 시드별 값 목록). 나머지도 같은 자료를 다루어 통째로 뺐습니다. 빌드 단계가 이 가운데 두 파일(`demand-v3-diagnosis`, `rmcal-v3b-resume`)에 남긴 가림 줄 2개는 REDACTED.tsv 에서 지웠습니다.
- 메모리 2개: `vissim-network-v3-decisions-20260925.md`(v3b NC·RM 3시드 31/41/37 시드별·평균 값), `vissim-ramp-meter-actuation-is-binary.md`(RM_SEED_SWEEP 3시드·seedvar s31/37/41 합친 측정값). `memory/INDEX.md` 에서 두 줄을 지웠습니다.

### 3.2 가린 곳 (REDACTED.tsv 에 "(검증 단계)" 로 18줄 더함, 27곳)

| 파일 | 가린 것 | 까닭 |
|---|---|---|
| `reports/rmcause/METER_CAUSE.md`, `_r1`, `LOG.md`, `o1o4/METER_NEXT.md`, `_r1`, `o1o4/O1_RULE_RM_V3C3.md`, `_r1`, `memory/vissim-meter-never-asked-20261024.md` | 미터가 줄일 수 있는 FW_E 본선 상한의 "평균" 값(보수·관대 두 값) | v3c3 다섯 시드(s47·s53 포함) 평균. s31/s41/s43 값이 다른 곳에 있으면 s47+s53 몫을 거꾸로 셀 수 있음 [추론] |
| `reports/rmcause/METER_CAUSE.md`, `_r1` | c5 상한 줄의 "어느 시드에서 10 % 근처인가" 서술 | v3c3-s53 결과에 대한 서술 |
| `reports/k92_bundle1/LOG.md:40` | H-b 지지값 개수 가운데 s47 몫과 세 시드 합 | v3c3-s47 자료에서 나온 수 |
| `memory/vissim-sdmpc31-obs150-state-20260924.md:40` | RM_GAIN_TRACE 를 옮긴 VISSIM 쪽 값 다섯 | v2 stage-1 3시드(31/41/37) 값 |
| `memory/vissim-v5b-urban-loss-diagnosis-20260925.md:12` | "NC seed 범위" 값 | v2 NC 시드 범위(37 포함) |

### 3.3 남긴 것 (판단을 메인 세션·사용자에게 넘김)

- H-b 씨앗 `1045.1612903225805`, 민감도 1,384.6: v3c3-s31·s43·s47 지지값에서 나왔지만 이미 저장소 설정(커밋 2d5d95f0)에 있는 값입니다 [읽음].
- v3b-s47 1,936.2(U4 `66|p2` per_seed)와 그 밖의 v3b·v3c1 망 s47·s53 값: 규칙의 블라인드는 v3c3-s47·s53 입니다. 다만 프로젝트 문서는 v3b-s47 값을 v3c3-s47 블라인드의 "부분 노출" 로 다룹니다(K9_3_DESIGN_DRAFT §6.8).
- 셈 값(봉인 뿌리 기록 134 / s47 45, F 표본 22·50상태, 이름에 s47 이 든 파일 39,721개): 우리 도구가 만든 파일 수이고 VISSIM 결과가 아닙니다.
- v2-s37 런이 죽은 시각(7340 s, 메모리 watchdog): 진행 시각이며 결과 값이 아닙니다.
- 판정기 자체 시험의 합성 문자열(`objective=4711.25`, `'9' * 3`): 정규식 시험용 가짜 값입니다 [읽음].
- 자격 증명 꼴 6건은 모두 잠금 토큰 이름·정책 토큰 해시(`TOKEN = 'fo_chain-'` 등)입니다. 실제 자격 증명은 0 입니다 [실행·읽음].

### 3.4 다시 훑은 뒤 [실행]

- 훑은 파일 2,551개(MANIFEST·EXCLUDED 뺌, 이 문서 쓰기 전), UTF-8 아닌 파일 0. v3c3 와 s47·s53 이 같은 줄에 있으면서 소수가 있는 줄 33개는 모두 절 번호·디스크 용량·위 §3.3 항목이었습니다.

## 4. 크기·바이너리 [실행]

- 1 MB 넘는 파일 0. 가장 큰 파일은 `MANIFEST.tsv`(약 0.75 MB), 그다음 `reports/k92_bundle1/LOG.md` 300,053 B 입니다.
- 전체: 파일 2,554개(MANIFEST 포함), 약 48.6 MB(목표 80 MB 안). 빌드 단계 끝(2,577개)에서 STATUS 복원 +1, 이 문서 +1, 뺀 파일 −25 입니다 [계산].
- 인코딩 바꿈 9개(REDACTED.tsv 에 "인코딩만" 줄): UTF-16LE 6개(`small_data/codex_handoff/work/b0/b0_replay_summary.out.txt`, `work/gate1/build_R1–R4.txt`, `work/gate1/gate1_summary.out.txt`), cp949 3개(`work/a0/foreign_src_compare.txt`, `work/net/routes_diff.json`, `small_data/c_prep/vsl/out/v3_code_robocopy.txt`). 글자는 그대로입니다.
- NUL 바이트가 든 파일: `tools/codex_handoff/work/verify_b/out/frz_runner.diff` 하나(numba 캐시 줄이 diff 안에 들어 있음). `.diff`·`.patch` 는 허용된 꼴이라 남겼습니다. git 은 이 파일을 바이너리로 볼 수 있습니다 [추론].
- 형식: `.py` 763 · `.json` 658 · `.md` 384(이 문서 전) · `.txt` 243 · `.js` 145 · `.sha256` 143 · `.ps1` 139 · `.csv` 35 · `.diff` 17 · `.sh` 11 · `.cmd` 10 · `.tsv` 3 · `.patch` 2.

## 5. MANIFEST 다시 만들기 [실행]

- 도구: `_work/vmanifest.py`. 묶음의 모든 파일(MANIFEST 자신 빼고)을 다시 읽어 `repo_path / source_path / bytes / sha256` 을 썼습니다. source_path 는 옛 MANIFEST 값을 그대로 두고, 새 파일은 "(복원)"·"(생성)" 으로 적었습니다. 뺀 파일 25개의 줄은 지웠습니다.
- 쓴 뒤 줄마다 bytes·sha 를 다시 세어 어긋남 0 을 확인했습니다. 행 2,553개(MANIFEST 자신 뺌), source_path 를 모르는 행 0. MANIFEST 자신의 sha 는 이 문서가 MANIFEST 안에 들어가므로 여기 적지 않고 반환 요약에 적습니다.

## 6. 남은 것 (메인 세션이 볼 일)

1. 커밋할 때 `push_bundle/_work/` 는 넣지 마십시오(검증·빌드 스크립트와 목록뿐).
2. §3.3 의 남긴 값들(H-b 값, v3b-s47 1,936.2 등)을 공개해도 되는지 정해 주십시오.
3. 워크플로 23개·메모리 2개를 뺀 것이 괜찮은지 정해 주십시오. 필요하면 줄 단위 가림으로 되살릴 수 있습니다.
4. 가린 사본(결정 기록, 보충 31 세 판, METER_CAUSE 등)은 원본 sha·`.sha256` 짝과 다릅니다. `.sha256` 파일은 원본 값을 담고 있어 사본으로 `sha256sum -c` 하면 어긋납니다.
5. P0-17 `result.json` 은 TC1(D:)에만 있어 묶음에 없습니다.
6. 빌드 단계(select)와 digest 단계가 같은 폴더를 동시에 썼고, select 의 `rmtree` 가 STATUS 를 지웠습니다. 다음 워크플로에서는 단계 차례를 나누는 편이 안전합니다 [추론].
