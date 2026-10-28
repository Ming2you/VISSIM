# C1 P0·미니 탐침 보고 (2026-10-27 KST) — **STOP: P0-4 가 INCOMPLETE (내 P0 도구 결함), 사용자 결정 필요**

- 한 줄 요약: P0-1·P0-2 는 PASS 입니다. P0-4 는 내 P0 도구(`c1_p0.py`)가 글자 디코딩 오류로 중간에 죽어서 INCOMPLETE 입니다. 도구는 첫 P0 계산 전에 고정했으므로, 사용자 결정 없이 고치지 않고 여기서 멈췄습니다. 나머지 P0(P0-3·5·6·7·8·9·10·11·13)와 미니 탐침은 돌리지 않았습니다.
- 판정 낱말은 쓰지 않습니다. 결과는 PASS / STOP / INCOMPLETE / 보고 와 숫자로만 적습니다.
- 표시: [실행] 이번에 돌려서 확인 · [읽음] 문서·코드에서 확인 · [추론] 시험하지 않은 판단.

## 줄임말 (처음 한 번만)

- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, C1D = `SP/c_port/c1`, TC1 = `D:/VISSIM-merge/k8_gate_trees/c1`(C1 스크래치 뿌리), RC1 = `D:/VISSIM_runs/20261001_v3c3/reports/k8/c_port/c1`(보고 사본), GWT8 = `D:/VISSIM-merge/sim3-n31-k8`, CX = codex 인계 트리 `D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff`, FRZ_B1 = B 런 동결 트리, B0F = `FRZ_B1/diagnostics/b0_v3c3`.
- P0 = 탐침 전 점검(보충 C1 §4), 미니 탐침 = 구현 전 보고용 재생(§5). 보충 C1 = `SP/K8_PREDECLARATION_AMENDMENT_C1.md`.
- Ω701 = codex 목적 영역(링크 701개, 우리 Ω635 + 신호 17곳 접근로 66링크). PN = codex `prepare_next.py`(재결속 규칙). 정책 토큰 = SDMPC 옵션의 해시. LOCK = 무거운 일 공유 잠금 `D:/VISSIM-merge/k8_gate_trees/heavy.lock`.

## 1. 고정 확인 [실행 12:00]

- 보충 C1 sha256 = `a98580dd2d787007ab961d692668c4a4042c79d7993f87af972cbc19d1f53acf` = 고정점 `C1D/AMENDMENT_C1_FIXED.md`(`7083d136…`)의 값. 결정 기록 `bbfe77b0…`, 설계 r2 `c32e1006…`, 종합 r2 `4b58fb4e…` 같음.
- GWT8 head `c20aff1d7bf0c432cb4f20e2922bd406d857aa5d`(브랜치 `claude/k92-b1-20261016`), `git status --porcelain` 0줄, `claude/c1-port-*` 브랜치 0. 이 단계에서도 브랜치·커밋·푸시 0 [실행 13:2x].

## 2. 한 일 (순서대로)

1. **탐침 패치** [실행] `C1D/tools/c1_probe.patch` sha256 `5cdc6eb1e42492945e7d412d194d6f4b1a125e9b948a46607b1b939fad2c8993`(1,022,233 B). 보충 C1 §2.2–§2.7·§2.13 자리대로 SD·PRB·LPR·RS·ADP·AFO 6파일을 고치고, 새 모듈 C1M(`evaluation/controllers/c1_port.py`)과 B0 배치 Ω701 10파일·C1 증거 3파일(선언 바이트 그대로)을 더합니다. codex 함수 7개는 CX 에서 ast 범위로 글자 그대로 옮겼습니다. 패치 manifest `c1_probe_patch_manifest.json`(`e706da02…`)에 파일별 앞뒤 sha.
2. **합성 시험** [실행, 실행 자료 0] `c1_selftest.py`: 42/42 참 — 옮긴 함수 7개 `ast.dump` = CX(G-K1 (g) 꼴), None 길 정규화 = c20aff1d 함수, `keep_green_10` 설치 표 = 증거 repr, `c1_port` 거부 21종(G-K3 꼴), `apply_tuning` 세 경우·섞임 거부, 저장 보호 하한 표 내림(직전 7·보호 → 9 → 8), 이웃 후보 수 식 N = f(u_E)+f(u_W) 25조합·계획 g8/g6/g4.
3. **개발 스모크** [실행, 개발 점검 — P0·탐침 데이터 아님, 판정에 쓰지 않음] 선언 목록 밖 상태 R-obs v3c3-s43 T=3,000(직전 NoControl → 첫 SDMPC 결정 길), 개발 트리 `TC1/trees/dev_5cdc6eb1`, LOCK 12:45–13:17: configure 만 off·c1 둘 다 끝까지 감(토큰 off `428e650d…`, c1 `522eec6f…`; 소속 inside 701; FW_E 4미터 g9 뺌), C1 팔 결정 1개 exit 0·오류 파일 0·DECISION_FAILED 0(이웃 검사 incumbent 2 × 조임 후보 10, 고름 없음, cap 목표 3). **이 한 결정의 벽시계 1,869.5 s** — 탐침 멈춤 4(C1 팔 중앙 > 1,500 s)에 걸릴 수 있다는 미리 보기입니다(그때 다른 세션 VISSIM 3개·VSL 워크플로가 함께 돎) [실행; 판정 아님].
4. **P0 고정** [실행 13:20] `C1D/PINS_P0.sha256` = `e1bf667753f423726733f45da2f0bca9427d63502973d57b3777fe00fc2ab954`(28줄, 28/28 OK): 도구 9·패치·manifest·팔 튜닝 13(off = OUC `c8e3ee2c…` 바이트)·바깥 준비 도구 2. LOG 에 첫 P0 계산 전에 적음.
5. **트리** [실행 13:20] `TC1/trees/p0_5cdc6eb1`·`probe_5cdc6eb1` = `git archive c20aff1d` + 패치, 각 10,583 파일, 패치 뒤 sha 대조 다름 0.
6. **P0 가벼운 단계 사슬** [실행 13:21, WMI 분리·BELOW_NORMAL·PYTHONHASHSEED=0·python -B] P0-1 → P0-2 → P0-4 에서 멈춤(§4).
7. **P0-12 문서** [실행, 계산 0] 정정 메모 `SP/codex_handoff/B_RESULTS_ERRATA_20261027.md`("RM_C10480 3,525 m" → "3,625.8 m", 볼 길 (iii) → "SC1001 EBT 녹색 → 127 → 129 → 10491"; B_RESULTS r2 `152a2f6f…`·VERIFY_B `f2851f8b…` 원본 그대로), `C1D/NETWORK_CANDIDATES_C1.md`(1099 입구 처리량 한 줄).

## 3. P0 결과

| # | 결과 | 숫자·근거 |
|---|---|---|
| P0-1 Ω701 소속·경로 계약 재현 | **PASS** [실행] | CX 사본(`TC1/cx_copy`, 원본과 sha 같음; 빌더 `567bca5f…`, PN `525897ad…`)을 python -B·env_hsw 로 돌림. 두 키 뺀 JSON = B0F, `previous_membership` 규칙 참, `area_revision_sources` = codex 문서, 바이트 `9bb740b3…`, inside 701 / outside 535, 경로 계약 바이트 `08fec9c7…`(바탕 `11d0db79…`), turn 57개 갱신. CX status 0줄 앞뒤, FRZ_B1 8,096파일·최신 시각 앞뒤 같음. 결과 `TC1/out/p0/p0_1/result.json` `ee39291f…` |
| P0-2 재결속 재현 | **PASS** [실행] | PN:57-108 을 닫힌 목록(팩 8 + manifest)에 옮겨 돌림: 다시 쓰인 문서 정확히 9, 팩 8 바이트 = §2.2 표, manifest `93f17143…`; 지지 문서 차이 63(link_to_storage 29·evidence 33·controlled_approach_revision 1); 나머지 문서 차이 = §2.2 기대 표; `area_membership_sha256` 두 판 `4863f5ee…`; 연결자 지원 29 = 새 link_to_storage = 새 evidence ⊂ 더한 링크; 경로 핀 111(판정 106 모두 맞음, 뺀 5 정확히, 역슬래시 4); `membership_path` 6칸 모두 B0 자리; `git grep area_membership_sha256 -- evaluation` 0건, `full_area_coverage_audit` 읽는 곳 `projection_support.py:304` 하나. 결과 `e25f8f0f…` |
| P0-4 머리 표 증거 | **INCOMPLETE** [실행] | 도구가 Q26 보고 부분(`git -C CX grep`)에서 죽음(§4). 죽기 전에 쓴 재생성 파일 `TC1/out/p0/p0_4/head_service_fwe_c1.json` 은 sha `3933a882…` 로 선언 바이트와 같음(`cmp` 같음) — 다만 `result.json` 과 Q26 출처 보고가 없어 단계는 끝나지 않음 |
| P0-12 문서 | 끝 [실행] | §2-7 |
| P0-3·5·6·7·8·9·10·11·13 | 돌리지 않음 | STOP 뒤라 |
| 미니 탐침(결정 35·plant 48) | 돌리지 않음 | STOP 뒤라. 탐침 도구 `c1_probe.py` 는 써 두었으나 고정 전(PINS_P0 밖) |

## 4. 멈춘 까닭과 고칠 곳

- 무슨 일 [실행, `TC1/out/logs/p0_light_1.txt` sha `64a21f1b…`]: `c1_p0.py:588-589` 의 `subprocess.run(['git', '-C', CX, 'grep', '-n', 'physical_ramp_head_service_veh_per_cycle'], capture_output=True, text=True)` 가 출력 디코딩을 Windows 기본 cp949 로 하다가 CX 파일의 UTF-8 한글에서 `UnicodeDecodeError`(읽기 스레드) → `stdout` 이 None → `AttributeError: 'NoneType' object has no attribute 'splitlines'`. 셈 정의·값·문턱과 무관한 입출력 결함입니다.
- 규칙: 보충 C1 §12 끝 "어떤 관문·점검이든 FAIL·보류·INCOMPLETE 는 STOP 이고 사용자가 정합니다", §14 "고정 목록은 고정 뒤 바이트가 바뀌면 S-C1-1·S-C1-12", 작업 규칙 "any FAIL/INCOMPLETE/HOLD ⇒ STOP". 그래서 고정한 도구를 고치지 않고, 남은 단계도 돌리지 않고 멈췄습니다(K9-2 탐침의 `k92_vissim_ref.py` 멈춤과 같은 꼴).
- 고칠 곳(제안, 아직 하지 않음): `c1_p0.py` 의 `git grep` 세 호출(P0-2 둘, P0-4 하나)에 `encoding='utf-8', errors='replace'` 를 더함. 셈 줄은 바뀌지 않습니다.
- 사용자에게 묻는 것:
  - (가) 위 한 가지만 고친 `c1_p0.py` 를 새 고정 목록 `PINS_P0_r2.sha256` 로 고정하고, P0-1·P0-2 결과(고정판 `a7f1c479…` 도구가 낸 PASS)는 그대로 둔 채 P0-4 부터 이어 함.
  - (나) 같은 고침으로 P0 전체(P0-1 부터)를 새 출력 자리에서 다시 함.
  - (다) 다른 방법.
- 덧붙여 알릴 것(막힘 아님): 개발 스모크의 C1 결정 하나가 1,869.5 s 였습니다(§2-3). 탐침 멈춤 4(C1 팔 중앙 > 1,500 s)는 탐침에서야 판정되지만, 넘을 수 있습니다. 넘으면 보충 C1 S-C1-8 의 선택지(cap 캐시 이식·cap 2·예산 재선언)로 질문하게 됩니다 [추론].

## 5. 지킨 것

- VISSIM·COM·폐루프 러너·동결 0. 브랜치·커밋·푸시 0(GWT8 head `c20aff1d…`, status 0줄). 금지 시험 0.
- 무거운 일(개발 스모크)은 LOCK 을 배타 생성으로 잡고 끝나면 내 LOCK 만 지움(12:45:44–13:17:42). LOCK 을 기다리던 첫 스모크(내 PID 52052)는 LOCK 을 잡기 전에 내가 끔(출력 0) — 다른 세션의 VISSIM·python·LOCK 은 건드리지 않음.
- 읽기만: CX(앞뒤 status 0줄), FRZ_B1(파일 수·최신 시각 같음), 런 폴더, 동결 트리, 인계 사본, Y:. CX 코드는 TC1 사본으로만 돌림.
- 블라인드: 봉인 시드 37·59·61·67 열람 0, codex 64cf-s59/s61/s67 숫자 0, R-obs v3c3-s47 자료 0(이 단계의 P0-7 도 아직 안 돎). 목적값·예측값 출력 0(개발 스모크의 벽시계·후보 이름·개수만).
- 디스크 [실행 13:2x]: C: 24 GB, D: 208 GB (8 GB 문턱 위).

## 6. 파일 (sha256)

| 파일 | sha256 |
|---|---|
| `C1D/PINS_P0.sha256` (P0 고정 목록) | `e1bf667753f423726733f45da2f0bca9427d63502973d57b3777fe00fc2ab954` |
| `C1D/tools/c1_probe.patch` | `5cdc6eb1e42492945e7d412d194d6f4b1a125e9b948a46607b1b939fad2c8993` |
| `C1D/tools/c1_p0.py` (고정판, 결함 있음) | `a7f1c479b1cbae6c…`(64자는 PINS_P0) |
| `TC1/out/p0/p0_1/result.json` | `ee39291f9a1ac91d0ff405e457053d4d8f8753d23a7f082cb270b45b04adee0f` |
| `TC1/out/p0/p0_2/result.json` | `e25f8f0f6e9d43bc9b7d01dac374fbc3c02f0bf8c747e999bd24e8aceddb3de3` |
| `TC1/out/p0/p0_4/head_service_fwe_c1.json` (부분 출력) | `3933a882b7948abdae825731ecd06494dead4628d5d26c69d1d8f53dc6866333` |
| `TC1/out/logs/p0_light_1.txt` (멈춘 기록) | `64a21f1b4b7c58855b83512ada1c3477d843ed73d32e4302967e279d1ec0cf9d` |
| `SP/codex_handoff/B_RESULTS_ERRATA_20261027.md` / `C1D/NETWORK_CANDIDATES_C1.md` | LOG 와 RC1 사본 표 |
| 개발 스모크 표지 `TC1/out/dev/dev_smoke_flags.json` | LOG |
