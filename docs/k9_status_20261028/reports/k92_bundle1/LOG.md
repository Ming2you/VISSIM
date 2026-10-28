# K9-2 묶음 1 작업 기록 (덧붙이기만)

## 2026-10-16 12:55 +0900 — Declare: 보충 24 고정판

- 쓴 파일: `SP/K8_PREDECLARATION_AMENDMENT_24.md` sha256 `26b70218088f594e9b2798f31344d047dba49e8e212ddc3193754ded9b4a22b2` (88,950 바이트), 고정 기록 `SP/K8_PREDECLARATION_AMENDMENT_24.md.sha256` 같은 값.
- 바탕: 초안 r2 `4d8c7883a22e82cf96dd92309894a7ff9bc56b00d35c4090a2f3a931617ea4f6`, 설계 r2 `1100f7af519839beb0bd1345f8d576e2ce64d6bb01162b03eea27830d5d7ad2a`, 결정 기록 `bf6f01ab46298426c7d9acd5bf61167e6590df09b12b38662a944931df915d2d`(D-K9-34~38; 앞 109줄 = `919b0f33…`).
- 채운 결정: W = U4 173|p3 F2 1,736.6 × 3 → round(·,1) = 5209.8(repr 고정; 실수 곱 5209.799999999999), 5,700.6 = 보고 팔 Wu, 5,927 = J1 사후 Wj; 씨앗 1045.1612903225805(repr), 학습 유지, 1,384.6 = 민감도 B1s; F 표본·F-3 비블라인드; J-b 판정 잎 전부; J-b 다름 STOP; W 단독 = 관문·탐침만; 브랜치 claude/k92-b1-20261016; V-B 방법 전부(§14.1); V-A는 다음 단계(사용자 go); GB-7′ R2-12 보충 규칙(§14.3).
- G-K2 재정의: 기준 팔 CWf·X1f(몫 가르기 패치에서 `5700.6` → `5209.8` 한 곳). 기대 바이트 CWf RS `ea79be3a6b60b300e660a88e7c3ec76c2df8321ca6c06a756e9b40b08a862a53`, X1f RS `0ba3fa61ef61c25a402b47429fdc666598c5a5f83c7a3dde45aed060570adc3b`, X1f SHO `0d295c113678ba80ef8c1442370652b147fb31c81b69a70076f77799e9368816`(메모리 안 계산, 파일 쓰기 0). 5,700.6 대 CW·X1 동일성 = G-K2 (e) 보고.
- 한 일(읽기 전용): 근거 sha, U4 행·build_table.py:363, GWT8 rev-parse/branch/status(head b9734abe, 0줄, claude/k92* 없음), SHO·RS sha(FRZ_K7·FRZ_K8b·GWT8·블롭), 몫 가르기 패치·빌드 기록, DA 재현 CSV sha, RR launch_plan·provenance, J1 v3c3-s41 결정 JSON head_observation 키 이름, gb7_allowed.py 목록 sha 출력·R2-12 정규식 판정(메모리 안), df(C: 24 GB·D: 640 GB 여유).
- 새 도구: `KB/work/check_tables.py` sha256 `805393c9817019499a7bd60508c99b2286686e4c0dc5725269063776f9066c49`(표 칸 수 점검, 결과 bad 0).
- 하지 않은 일: 코드 변경·커밋·브랜치·푸시·동결·재생·VISSIM·COM·러너·시험 0. TK·OK2·KB/k92_probe 생성 0. 동결본·런 폴더·k92attrib 쓰기 0. 봉인 시드·codex 64cf·v3c3-s47 R-obs 자료 열람 0.

## 2026-10-16 13:25 +0900 — ReviewDeclare: 보충 24 반박 검토와 고정점

- 고정점: `KB/AMENDMENT24_FIXED.md` sha256 `fbc3d59fe2e47fec00d87262d624aa9a163ed02e113609b06173841397df101a`. 보충 24 검토 판 `SP/K8_PREDECLARATION_AMENDMENT_24.md` sha256 `d46db6dc3959b19525f0fce77ead5432682e3de0ef8060cdc3da09661559aadc`(116,685 바이트), 고정 시각 2026-10-16T13:24:44+09:00. `.sha256` 파일 같은 값 [실행 `sha256sum -c`].
- 검토 전 판 보존: `SP/K8_PREDECLARATION_AMENDMENT_24_r1.md` = `26b70218…4a22b2`(12:55 Declare 판과 바이트 같음) + `.sha256`.
- 고친 것 20건(보충 §16, 고정점 §1): V1 VB-I2가 VB-41w B1 T=150에서 반드시 거짓(씨앗이 T=1에 하한 키를 남겨 `prior_discarded` = 1.0, 계산 영향 0) → 조건 붙은 예외 하나 + V-A 알림; V2 G-K0 P-a·G-K1 동적의 v3c3-s47 탐침 9상태에서 K9-2 VISSIM 기준 값이 주 표본 F 프레임과 겹침 → s47은 k92t 안에서만; V3 판정기 사후 수정(S-K12 넓힘, §3.1-8 고정 목록, §4.4 사용자 결정 뒤에만); V4 J-b 판정 계산기 자체 점검; V5 `K92_VALUES.json` 고정 뒤 수정 모순 → `K92_REF.json`·`K92_PROBE_OUT.json`; V6 기준 팔 순서·env·훅; V7 INCOMPLETE 자동 재실행 삭제; V8–V9 STOP·PASS 빈자리; V10 U 닫힌 목록; V11 A_K92·A_K92-M 동어 반복 조건; V12 H5 (가) 키 이름·묶임 조건 + P0-2 (f) + VB-I6; V13 G-K1 좌회전 값; V14 G-K3 값; V15 벽시계 짝; V16 (c) 보고 팔 사본; V17 GB-7′ 기대 목록 sha `a8148f38…7af1`; V18 출처 서술 정정; V19 P0-2 s47 출력 제한; V20 읽기 전용 루트 스냅숏.
- 검토 도구: `KB/work/review_a24_checks.py` `ab411657…7350`, 출력 `review_a24_checks.out.txt` `b7fc5e43…a753`(읽기 전용; k92attrib 패치 트리 RS·SHO, U4 행, `gb7_allowed.py`(-B), 결정 기록, J1 v3c3-s41 T=1·150, J1 v3c3-s43 T=3,750 키 이름. v3c3-s47 파일 0).
- 한 일(모두 읽기 전용): SHO:114-258·RS:100-200, :340-370·HSR:90-140·ADP:4425-4445, :4565-4610 읽기, `sa_common.py` 표본 상수, `gates_k91t.json` 판정 항목·RG 값, DA CSV sha 10개, 몫 가르기 S1_CW·S3_X1 호출 기록·summary(`hooked: true`), K9-1 U 기록(`k91_3_record.json`), 보충 21 §6·보충 23, 선례 `j1/fix/AMENDMENTS_FIXED.md`, df(C: 24 GB·D: 640 GB).
- 하지 않은 일: 코드 변경·커밋·브랜치·푸시·동결·재생·VISSIM·COM·러너·시험 0. P0·탐침·관문 0. TK·OK2·`KB/k92_probe` 생성 0. 동결본·런 폴더·k92attrib·DA·V4 쓰기 0(GWT8 `git status` 0줄, head·K8 브랜치 b9734abe 확인). 봉인 시드·codex 64cf·v3c3-s47 자료 열람 0. J1 성능 숫자 0.

## 2026-10-16 13:44 +0900 — Implement 시작: 고정점 확인·순서·스냅숏

- 고정점 확인 [실행 `sha256sum`]: `SP/K8_PREDECLARATION_AMENDMENT_24.md` = `d46db6dc3959b19525f0fce77ead5432682e3de0ef8060cdc3da09661559aadc`(116,685 B) = `KB/AMENDMENT24_FIXED.md`의 값. 결정 기록 = `bf6f01ab…915d2d`.
- 시작 상태 [실행]: GWT8 head = K8 브랜치 = 원격 K8 브랜치 = `b9734abe1c83f95c9cec5fca5e42b7b18cd45991`, `git status --porcelain` 0줄, `claude/k92*` 없음, TK·OK2 없음, VISSIM 0·python 0, C: 24 GB·D: 640 GB.
- 순서(보충 24 §3·§4 그대로): P0-1…P0-5 → `K92_VALUES.json` 고정 → 미니 탐침(기준 팔 먼저) → 탐침 정지·질문 규칙 확인 → 커밋 K9-2-0…3과 커밋별 관문. 커밋 관문이 P0·탐침 산출(`K92_VALUES.json`, `K92_REF.json`, `K92_PROBE_OUT.json`)을 기준으로 쓰므로 P0·탐침을 이 Implement 단계 안에서 먼저 합니다.
- 새 도구 `KB/impl/k92snap.py`(읽기 전용 뿌리의 이름·크기·시각만, 봉인 시드 이름 폴더는 내려가지 않음) sha256 아래 줄. 스냅숏 `OK2/snap/s00_before_p0.json`(RR 4,269 / RO 2,046 / NC3(reports 밖) 853 / FRZ_K7 10,450 / FRZ_K8 10,769 / FRZ_K8b 10,775 / k92attrib 255,184 / DA 3,533 / V4 16,114 / OUTH 7,329 파일).
- `KB/impl/k92snap.py` sha256 `0dbd7d2c75f982d867eff46f27b1c2d8fbf34301d39952bdc87ebd7a0c8beeff`, 스냅숏 sha256 `060dba2f3e762c9344a5a2a47f79f4a14ab2cdc30f62e7e284494ec4b421733e`.

## 2026-10-16 14:05 +0900 — P0 도구 고정 (§3.1-8, 첫 P0 실행 전)

- W·H-b 증거 빌더(스크래치판, 커밋 K9-2-1·K9-2-2 대상) `KB/impl/repo/diagnostics/sdmpc_n31_20260924/k92/build_k92_evidence.py` sha256 `d33ee9f000184c070c29ad29f0f0d5a22b76d240fe8f67a852c29dd6be3b2a84` (P0-1 w, P0-2 (a)(b)(c)(d)(e)·B1–B4·B6·B8 hb; P0-2 읽기기 = 이 빌더의 `hb_keys`·`hb_obs150_candidates`).
- P0-2 (f) 이름 계산기·P0-3·P0-4 훑기 `KB/impl/p0_lists.py` sha256 `b9f23614fc60030e96362b6859c701236e945684ae78a37cdfb5dfe2fc968710`.
- 출력 자리: `KB/k92_probe/p0/`.
- [2026-10-16 14:11 +0900] 정정: 바로 앞 항목 머리의 시각 "14:05"는 잘못 적었습니다. 도구 고정은 첫 P0 실행(파일 시각 13:52) 전인 13:51 무렵입니다(sha 값은 그대로). 앞으로 시각은 `date` 출력으로 적습니다.

## 2026-10-16 14:17 +0900 — P0-1·P0-2·P0-3 실행, P0-4 도구 범위 좁힘

- P0-1 [실행]: `build_k92_evidence.py w` → `KB/k92_probe/p0/sc109w_through_saturation_v3b_u4_20261016.json` sha256 `bff6c9c0ddeb20610ecfdb72a494edcc48aa4072a7e2cf36db8111ed3fa2835d`, 입력 행 `p0/inputs/u4_row_173_p3_v3b.json` `0499ad27f1f28eb41fa5dc5181c24f0307348b9722111fa444ecc1d4d6b06256`. A1 1736.6000000000001, A2 구성원 {SC109_W_SC108_to_E}·5209.8 ≤ 6000, A3 1736.6, A4 차로 3 = 머리 3 = 차로 파일 3.0 = .inpx {1,2,3}, A8 참, A9 머리 셋 위치 ±1e-3 안, A10 좌회전 차로 5·4, A11 곱 repr 5209.799999999999·값 repr 5209.8. 단언 거짓 0.
- P0-2 (a)(b)(e) [실행]: `build_k92_evidence.py hb` → `p0/head_floor_seed_v3c3_robs_20261016.json` sha256 `b9fa1d01b9d922e9fc327793aa428cd7b544dae221044704dea7f0af610f20ee`. 지지값 n = 53 / 56 / 〔가림: 봉인·블라인드 시드 값〕(합 〔가림: 봉인·블라인드 시드 값〕), 중앙값 셋·합친 값 repr `1045.1612903225805`. (b) v3c3-s31·s43 obs150 머리 1090501·1090502 행만으로 다시 낸 후보·지지값 = 결정 기록(같음, 창 시작 = T−150). v3c3-s47 obs150은 열지 않음. B1 참, B2 1045.16 > 413.06, B3 머리 {1090501 차로 5, 1090502 차로 4}·SG 109 5·allVehTypes true, B4 구성원 {SC109_W_SC108_to_N_SC16}(KA 훅 E1 S1_A0h 명세 + link_to_origins['173']), 결합 origin 같음(SC108_to_SC109), B6 CFG·SAF-K91 모두 {true, 30, 5}, B7(보고) 참, B8 repr 같음·s31/s43 지지 repr 집합 안. 출력은 (173, p4) 값만(지지값 목록은 s31·s43만).
- P0-2 (f) [실행]: `p0_lists.py f` → `p0/p0_2f_names.json`. 식이 J1 v3c3-s43 T=3,750 기록 이름 `head_discharge_floor_173_p4_3e3dc5ca5bf80727`을 다시 냄(참). 기대 이름: s43(S1·S4·VB-43) `…_3e3dc5ca5bf80727`, s31r(S2·VB-31) `…_1170360c34e5b57b`(T=3,900 기록 이름과 같음 [실행]), s41(S3·VB-41·VB-41w) `…_301ceabb95f116fa`(기록에 하한 키 없음).
- P0-3 [실행]: `p0/p0_3_links.json`. movement 링크 {21, 173, 174, 1220000600}(두 movement 같음), origin SC108_to_SC109 링크 13개(위 4 + 연결자 10024·10112·10280·10281·10285·10286·10293·10300·10303). 사슬 링크 = 합집합 13개, 목록 sha256(정규 JSON) 앞 16자 `c7e24edaf911f3e5`. 통과 판정기 사본 sha 둘 같음.
- P0-4 첫 실행: 11분 뒤 스스로 멈춤(자기 PID 10260; 출력 파일 0개, 값 출력 0). 원인: 앞 산출 루트의 JSON 전부(수만 개)를 열어 키 이름을 훑음. 도구를 고쳐 범위를 VISSIM 쪽 파일(이름에 vissim·fzp·frames, w_s*)로 좁힘 — 노출 목록은 VISSIM 값(링크 대수·머리 통과)에 관한 것이라 모형 산출은 대상 밖. 데이터가 나오기 전 고침. 새 `p0_lists.py` sha256 `47a0630791b68fbe754e82d9ce92573ee196025a7ba4e2ac79cbde10b037d798`(P0-4 재실행 전 고정).

## 2026-10-16 14:18 +0900 — P0-4 결과, P0-5 도구 고정

- P0-4 [실행]: `p0/p0_4_samples.json` sha256 `1851f6cc92f9a339d4bfbb0b9dcd15ea715634a8ba9f8b5e1aa11c5560bc30c3`. 주 표본 22상태·둘째 표본 8·8이 §5.3 목록과 같음(참). 노출 훑기: VISSIM 쪽 JSON 46개 열어 키 이름만 봄. 도구의 거친 규칙(키 토큰 '21')이 3파일·22상태를 걸렀으나, 키 경로를 보니 모두 FW_W 셀 번호 21·창 번호 21·계열 번호 21이고 링크 173·174·1220000600·머리 1090201–03 키는 0개, s47 FZP 프레임 사이드카 링크 목록에도 대상 링크 0 → 실효 노출 목록 = 빈 집합. 검토 기록 `p0/p0_4_exposure_review.json` sha256 `21fd54e7ce3bf50719339cd0ba1d56f935eb6c9c41d59e3e2b7d618f324fba74`(키 경로만, 값 0). 두 판을 함께 보존·보고(F-1·F-2 판정은 어느 쪽이든 22상태 전부).
- P0-5 도구 `KB/impl/p0_ref.py` sha256 `96e9adad06683824bce61cb371dcd8b1571924262e0da83266b5ad72d37f8394`(기준 팔 트리 CWf·X1f + 보고 팔 증거 Wu·Wj·B1s) — 실행 전 고정.
- 런타임 패치 글(탐침·커밋 공용, 아직 실행 0) `KB/impl/patch_runtime.py` sha256 `271159b7b22060ff0ab45c24d26732c827b4796528c651bec91e3cc1ed8e9733`(임시 사본에서 붙이기·compile만 시험, 계산 0).

## 2026-10-16 14:30 +0900 — P0-5 결과, P0 끝, K92_VALUES.json 고정

- P0-5 [실행 `p0_ref.py trees`]: TK/ref_t74_CWf·ref_t9b_CWf·ref_t74_X1f = k92attrib t74_base·t9b_base·t74_base 복사(copy2, 원본 읽기만) + 패치. RS ea79be3a…(CWf 둘)·0ba3fa61…(X1f), X1f SHO 0d295c11… — 모두 기대 바이트와 같음. 사본 대 base 차이 = {RS}(CWf)·{RS, SHO}(X1f), 빠짐·더함 0, 튜닝 t74 5f0d0e40… / t9b d0f9ef39…. 넣은 줄 끝 = 앵커 줄(\r\n). 빌드 기록 `TK/<트리>.build.json`.
- P0-5 (d) 보고 팔 증거 [실행 `p0_ref.py arms`]: `p0/report_arms/` Wu `150af510f6b57d9825513b252d3444b4b917b3a296399a4551d499d4633b8c05`, Wj `be260482813f714ca02fd010b52412f5c54655ac33ab08c20d0c1c5f601e8f17`, B1s `e7a4c7e95ee260eeb3798bddca399905a52ad65daf58365468da1b9fdead38bd`. 커밋 증거와 다른 필드 = §2.0-9 목록뿐(도구가 확인).
- P0-2 (c)(d) [실행]: SHO 바이트 FRZ_K7 = FRZ_K8b = GWT8 = d9bd5392…, RO 세 런 run_provenance `signal_observation.options` = {true, 30, 5}.
- 읽기 전용 뿌리 스냅숏 `OK2/snap/s01_after_p0.json` 대 s00: SAME [실행]. 여유 C: 24 GB, D: 634 GB.
- **`KB/k92_probe/K92_VALUES.json` sha256 `887664200cb4b5352d79823211b8c8587344e311ab6d33d0375a79ba2bfa3990` — 첫 탐침 계산 전 고정, 이후 고치지 않음.** (두 증거 sha, P0-2 (c)(d)(f), P0-3·P0-4 목록 sha, P0-5 트리 기록·보고 팔 증거 sha, P0 도구 sha.)

## 2026-10-16 15:33 +0900 — 미니 탐침 준비 끝, 첫 탐침 계산 전 고정 (§3.1-8)

- 탐침 트리 `TK/k92b1_probe` = `git archive b9734abe` + 패치 [실행 `probe.py trees`, 기록 `TK/k92b1_probe.build.json` sha256 `64f3e88f4974ee2419759acedf6a6a2d74a2ddd858bac953280246ff300fb53a`]. archive 대비 바뀐 파일 6개(RS `70cca680…`, SHO `a6b5931e…`, sa_worker `beca80c0…`, sa_capture `2b35d10e…`, sa_jobs `53c5c0fc…`, sa_cap_child `10a77972…`), 새 파일 21개(k92_common `013d26db…`, k92_record `1d1dfa36…`, k92_vissim_ref `6335400b…`, k92_compare `55df106b…`, 증거 W `bff6c9c0…`·H-b `b9fa1d01…`·입력 행 `0499ad27…`, 보고 팔 Wu·Wj·B1s, 팔 튜닝 11개). 선언 밖 차이 0 [실행].
- 탐침 팔 튜닝(바탕 + 선언 경로만, 도구 확인): t74(SAF-K91 5f0d0e40 바탕) W `434fe6bf…`, B1 `4c5f4302…`, B1s `2bb82963…`, Wu `e5dc0246…`, Wj `513d1b39…`, Xu `bbebf539…`; t9b(CFG d0f9ef39 바탕) W `d70864c0…`, B1 `f42fc98e…`, B1s `7eec5699…`, Wu `723f12db…`, Wj `7cace0b7…`. 팔별 결정 트리 `TK/p_<fam>_<arm>`(탐침 트리 사본 + config_n31_v2.json = 팔 튜닝, 차이 = 그 한 파일), 벽시계 짝 트리 `TK/arch_t9b`(= git archive b9734abe)·`TK/arch_t74`(+ SAF-K91 바이트를 config로) [실행, 기록 `TK/*.build.json`].
- 가드 자체 시험(자식 프로세스 0) 21사례 모두 기대대로(주 표본 거부·씨앗 단독 거부·옛 토큰 거부·탐침 상태 허용·k92t 엶·(런, T) 열쇠·3.1-3b) — `KB/k92_probe/guard_selftest.json` sha256 `892afe97d734adbd28cbcbdb9f0c1ea1b358f1ffacf10def63eb449647298845`.
- 비교기 자체 점검(데이터 0, 기존 판정 재현): `k92_compare.py`(키 끔) = 보충 21 비교기 `cmp21.py`와 OUTH G-H3 10짝에서 보고서 전체가 같음(10/10, 판정 PASS 그대로) [실행 `KB/impl/selftest/cmp_parity.py`].
- 탐침 도구 고정: `KB/impl/probe.py` sha256 `c91b2eea4038e3f1a374c80d7d23e1afb4d1d7c36c6b93f088cdf6c9655d4f15`, `k92lib.py` `ae5de0ccd90d688c0442eac2aeb35fec0aabd2abce4ba3ff75a637927fb998d9`, `patch_runtime.py` `271159b7b22060ff0ab45c24d26732c827b4796528c651bec91e3cc1ed8e9733`, `patch_harness.py` `e13cdeb932cf5b243225fc0b9735e7a74a6ab7557b128a48c784dbf6a5acaf38`, 탐침 비교기 = 트리 안 `k92_compare.py` `55df106bfa37a28e56047a489b9969e0c2779968ecda0830b63dbd38e75e104e`, 재생 = gprep `0482a538…`·frozen ps1 `5d34109f…`, 계측 훅 KA `6ad45fd4…`. 탐침 코드는 이 뒤 바꾸지 않음.
- 순서: 기준 팔(ref) → 탐침 팔(arms) → plant(둘째 표본 16 × {OFF, W, B1}, K9-1 탐침 포착 2 × {OFF, B1}, VISSIM 기준 s31·s43) → 벽시계 짝(wall) → 보고(report). 한 번에 하나, WMI 분리.

## 2026-10-16 16:16 +0900 — 커밋 관문 준비: 시험 고침, G-K1 정적 하한 키 이름 도구 고정

- 스크래치판 `tests/test_k92_hb.py` 두 실패 고침(시험 쪽 결함: CRLF를 `read_text`가 바꿔 읽음 → `read_bytes`로 줄 끝 포함 비교, 같은 cfg 재사용으로 기준 용량 오염 → `run()` 앞에서 용량 맵 초기화). 데이터 0. `TK/dev_k922`에서 `test_k92_w.py`·`test_k92_hb.py` 16 passed [실행].
- G-K1 정적 메타 점검에 쓸 (173, p4) 하한 키 기대 이름 도구 `KB/impl/gk1_names.py` sha256 `38a5d96044f2e8741bda8069da4cc3a4641e69928b71696e99dd582a86613940` — 실행 전 고정. P0-2 (f) 도구 `p0_lists.py`(`47a06307…`)를 고치지 않고 불러 같은 식으로 G-K0 결정 상태의 런(R-obs v3c3-s31 무제어, J1 s31·s41·s43·k8j1r_s31)의 이름을 냄. 결정 JSON 키 이름과 런 기록만 읽음(값 0), v3c3-s47 0. J1 세 런은 `K92_VALUES.json`의 P0-2 (f) 이름과 같아야 함(아니면 STOP).
- 커밋 관문 보조 `KB/impl/cglib.py` sha256 `6e70bfe890ab77496d11c1c56e419c5475bf7069d4e79236948bf87774eb5613`(초안, 관문 데이터 전; 판정 계산 없음).
- [2026-10-16 16:18 +0900] `gk1_names.py` 실행 [실행]: 식 재현 참(J1 v3c3-s43 T=3,750 기록 이름), J1 세 런 = P0-2 (f) 이름(참). 새 이름: R-obs v3c3-s31 무제어 `…_e36d6761cfeac634`, J1 v3c3-s31(원래 런) `…_c6f585e4e035cf63`. 산출 `KB/k92_probe/gk1_floor_names.json` sha256 `cf1ae3fbf659d97c2b855b4a72c944e1cba30c3a6ddbdbb34baa792bd8eb869f` — 고정. 이 이름들은 K9-2-0 블롭 `k92_gates.py`의 `GK1_FLOOR_KEYS` 상수로 들어감.
- [2026-10-16 16:24 +0900] 탐침 기준 팔 재생 5칸 끝(probe.py ref, 자동 기록): `KB/k92_probe/K92_REF.json` sha256 `f74986cfda65d1f2d1e63df5804e083d501331cd6f6c3aaf9a84178513cee6ad` — 고정(RG-3a), 이후 다시 계산하지 않음.

## 2026-10-16 17:27 +0900 — 커밋 준비 중 개발 점검(관문 데이터 아님)

- 탐침은 계속 도는 중(기준 팔 5칸 끝, `K92_REF.json` 자동 고정 `f74986cf…`; 탐침 팔 진행). 아래는 커밋 전 개발 점검이고 관문 데이터가 아닙니다.
- B 관문 조작화 발견 [실행]: 빌더 `hb --check`는 규칙 코드 SHO 바이트(`d9bd5392…`)를 고정해 둡니다. K9-2-2 뒤 트리의 SHO는 바뀐 파일이라 기본 `--root`로는 구조적으로 `K92_EVIDENCE_STOP`이 납니다(`TK/dev_k922`에서 확인). 그래서 B(hb)는 `--root` = git archive b9734abe 트리로 돌립니다(빌더 docstring의 `--root` 인자 그대로; 비교하는 증거는 커밋 트리의 것). 같은 점검으로 `--root TK/arch_t9b`에서 `K92_EVIDENCE_CHECK_OK hb`. 이 조작화는 `k92_gates.py` 머리말(K9-2-0 블롭)에 적음.
- 빌더 나누기: 보충 24 §4.1 표대로 K9-2-1에는 w 부분만(`KB/impl/split_builder.py`로 hb 블록만 뺀 판 sha256 `8877c850…`, w `--check` 통과 [실행]), K9-2-2에서 hb 부분을 더해 P0 빌더 바이트(`d33ee9f0…`)가 됩니다.
- `make_config_n31.py --k92b1`: b9734abe에서 `make_config_n31.py --check`(기본 CFG)가 이미 실패합니다(`build()`가 CFG의 K8b·K9·runtime 절을 쓰지 않음, 기존 드리프트) [실행]. 그래서 묶음 팔은 커밋된 CFG 바이트 위에 만듭니다(`cfg_document`). 결과 sha256 `f42fc98e…` = 탐침 t9b B1 팔 [실행 `TK/dev_k922`].
- U 미리 돌리기 [실행]: 선언된 기존 시험 14파일을 깨끗한 `git archive b9734abe`(`TK/u_b9_dev`)와 K9-2-0 후보 트리(`TK/tc_k920` = archive + patch_harness k920)에서 같은 env로 돌림. b9734abe 쪽 9개 실패(알려진 `test_called_path_satisfies_capture_contract` + K8-10 뒤 CFG에 키가 생겨 생긴 `test_k91_harness` 7개·`test_sa_harness` 1개, 기존 상태). 후보 트리는 같은 256개 시험이 같은 결과·같은 메시지(정규화 뒤), 새 `test_k92_harness.py` 15개 통과 → `judge_u` PASS.
- 관문 계산기 보강(K9-2-0 블롭으로 들어갈 것, 첫 관문 데이터 전): `k92_gates.py`에 U 메시지 정규화(루트 → `<root>`, 16진 주소, pytest 임시 폴더 번호), K9-2-0 diff 판정, B 판정, G-K2 (e) 보고, G-K3·팔 동일성 판정(`g3` 자식), G-K4 EXPLAIN(1e-9 안 차이는 설명이 필요하므로 보고·멈춤), 비교 기록의 값 지우기(`_blind`), `GK1_FLOOR_KEYS`. 새 시험 3개(`test_k92_harness.py`).
- 새 스크래치 도구(커밋 안 함; 아래 sha는 이 시각 판): 아래 줄.
  - `KB/impl/cglib.py` sha256 `6955f01f2bb9a7e18ca86295eaff84369a127df09a503593a3dbb4053e8d84ad`
  - `KB/impl/cgates.py` sha256 `b6ecb89832fdc653aa3102d37bfee1e81d23258c287534311394e922be1bdc1f`
  - `KB/impl/commit_k92.py` sha256 `1bdb3c70ca8c6916d960ba1ab48ee4b47ff383c20b64f285eb67b88d166c3d24`
  - `KB/impl/tools_check.py` sha256 `7ab1e1d16c8847d0d6d852b1dc836ebb324a68fe5d353893e9f9e812eb1db60c`
  - `KB/impl/k923_edits.py` sha256 `76893c7dc667195f70b425e3f32fd85071373a78b04718059dde64ded19fc10f`
  - `KB/impl/split_builder.py` sha256 `f973c29aeeec2ab8f56ec93a0595607e571a8bcdbe94fb6d7d0a025f45a1bf05`
  - `KB/impl/probe_md.py` sha256 `b7018d3c41530f7136a9f184e30bee9eb1940753a0d5d81a084884e132108caf`
- [2026-10-16 22:36 +0900] 탐침 팔 재생 21칸 끝(probe.py arms, 자동 기록): `KB/k92_probe/K92_PROBE_OUT.json` sha256 `844312dc59bfec8eb026b562d132ecbe1521c8be4a16cd9038e002dfbc89e9f4` — 고정.

## 2026-10-17 03:50 +0900 — 미니 탐침 멈춤(정지·질문 규칙 1·6): 커밋 전 STOP

- 무슨 일 [실행]: `probe.py` plant 단계에서 하네스 잡·포착은 모두 끝났고(`PLANT_CHILD exit=0`), 이어서 돈 VISSIM 기준 도구 `k92_vissim_ref.py`가 v3c3-s31(8상태)은 끝냈지만 v3c3-s43에서 `SystemExit`로 끝났습니다. 메시지: `D:\VISSIM_runs\20261001_v3c3\s43_v3c3nc\prepared\network\baseline_s43_v3c3nc.inpx: not the v3c3 network 3de889f0257d998b`. 그래서 `stage_plant`가 `k92_vissim_ref failed rc=1`로 멈췄고, 뒤 단계 wall(키 끔 벽시계 짝)·report는 돌지 않았습니다. 탐침 프로세스는 스스로 끝났습니다(남은 자식 0, VISSIM 0).
- 원인 [실행]: 도구가 모든 시드의 NC `.inpx`에 v3c3-s31 파일의 sha(`3de889f0…`)를 요구합니다(`k92_vissim_ref.py:57-58`). v3c3-s43 NC `.inpx`(sha 앞 16자 `51478c397b3a2570`)는 v3c3-s31 파일과 `<simulation … randSeed="43" …>` 한 속성만 다릅니다(`>` 단위로 나눈 diff에서 다른 줄 2개, randSeed 31 대 43). 즉 망 기하가 아니라 시드 속성 때문에 걸린 도구 결함입니다 [추론: 다른 속성은 같음을 diff로 확인].
- 규칙: 보충 24 §3.1-8 "탐침 코드는 고정 뒤 바꾸지 않습니다. 정지·질문 규칙 1(예외…)에 걸리면 고치기 전에 보고·질문", §3.3 규칙 6 "INCOMPLETE — 다시 돌리지 않고 보고·질문", 워크플로 "FAIL·INCOMPLETE ⇒ STOP". 그래서 도구를 고치지 않고, 남은 탐침 단계도 돌리지 않고, 커밋·관문을 시작하지 않고 멈춥니다. 사용자가 정합니다.
- 멈춘 때까지 끝난 것 [실행, 읽기 전용 요약; 값 출력 0]: 기준 팔 5칸·탐침 팔 21칸 재생 모두 종료 0·`derived`·`action_contract` 참, 오류 파일·DECISION_FAILED·훅 오류 0. 규칙 2 대상 HARD 쌍 8개(W 대 CWf S1–S4, B1 대 CWf S1·S2·S4, B1s 대 X1f S3) 모두 SAME(S3 B1s는 선언된 H5 차이 1건). plant 잡 48개 ok·기록기 오류 0, 포착 52개 실패 0. VISSIM 기준은 v3c3-s31만(`k92_vissim_ref.json` sha256 `9d8fb95084ceb12e1c136c6057b9e27a47ac444a9a70d3dede181a03508a4e87`). 규칙 3·4(둘째 표본 16상태 필요)는 v3c3-s43 기준이 없어 계산할 수 없고, 규칙 5(벽시계 짝)는 돌지 않았습니다. `K92_PROBE_RESULTS.json/.md`는 만들어지지 않았습니다.
- 고정된 탐침 산출: `K92_REF.json` `f74986cf…`, `K92_PROBE_OUT.json` `844312dc…`(둘 다 계산 직후 자동 고정 줄이 위에 있음).
- 읽기 전용 뿌리 스냅숏 `OK2/snap/s02_after_probe_stop.json` sha256 `88a5e142872f9141b65c279622d3f3546dab1e7012a1b5e053e679bcc755d5dd`, s01 대비 SAME [실행 `k92snap.py diff`].
- GWT8 [실행]: HEAD = K8 브랜치 = `b9734abe`, `claude/k92*` 브랜치 없음, `git status --porcelain` 0줄, 접선 캐시 135개(시작과 같음). 커밋 0, 푸시 0.
- 관찰(보고만, 판정 아님) [실행]: 키 있는 TL3 포착이 키 없는 포착보다 오래 걸림(약 380–430 s 대 30–60 s); 키 있는 결정 재생도 기준 팔보다 약 400 s 길었음. 원인은 확인하지 않음 [추론 없음]. 기존 하네스의 `SA_JOB … objective=` 줄이 탐침 로그에 둘째 표본(v3c3-s31·s43) 잡의 목적값을 찍습니다(기존 K9-1 하네스 동작, v3c3-s47 값 아님). 이후 확인 출력은 이런 줄을 걸러 보는 `KB/impl/waitfor2.ps1`(sha256 `8c07962b…`)로 봄.
- 커밋 준비물(아직 쓰지 않음, sha는 이 시각 판): `KB/impl/cgates.py` `88a23ff4…`, `cglib.py` `866a79e7…`, `commit_k92.py` `1bdb3c70…`, `tools_check.py` `a7f7510a…`, `k923_edits.py` `76893c7d…`; 스테이징 하네스 `k92_gates.py` `1a611805…`(첫 관문 데이터 전 판; K9-2-0 커밋 때 블롭으로 고정 예정이었음).
- [2026-10-17 03:50 +0900] `KB/IMPLEMENT.md` 작성(멈춤 보고, 한국어) sha256 `2e826f6caa12680c0843d62625fe537c23ea8a29fb86520c076f3d98942b5645`. 결과 STOP: 커밋 0, 푸시 0, GWT8 깨끗함. 사용자 결정 대기(탐침 도구 `k92_vissim_ref.py` 망 점검 결함, 보충 24 §3.3 규칙 1·6).

## 2026-10-17 12:24 +0900 — Declare A25: 보충 25 고정판 작성

- 쓴 파일: `SP/K8_PREDECLARATION_AMENDMENT_25.md` sha256 `84a5bfc9e97e98ffb417f9e7087c0b9466c72600c2e375953fd8b8ce2ea45d59` (82,864 바이트), 기록 `SP/K8_PREDECLARATION_AMENDMENT_25.md.sha256` 같은 값(`sha256sum -c` OK). 고정점 `KB/AMENDMENT25_FIXED.md`는 반박 검토 단계가 씀(보충 24 꼴).
- 바탕: 초안 r2 `67497400…83d1`, 결정 기록 `362cd6c2…399a`(D-K9-42~45 :130-138; 앞 128줄 = `711a1180…`), SLOW r2 `aed10ed4…`, VERIFY `69169f8f…`.
- 담은 것: D-K9-42 데이터만 고침(W 증거 `/sources` 4필드·입력 행 `/source` 2필드를 이름+sha로; 빌더 :149-152·:177-178·:237-239·:424), D-K9-43 미니 탐침 전체 재실행(새 자리 `TK/a25`·`OK2/probe_a25`·`KB/k92_probe_a25`, 보존본 그대로, A0–A11), 망 동일성 도구 고정(`f3fcc574…`, 건너뛰는 s31도 기록), 봉인 A′와 여는 규칙, D-K9-44 사실 기록, 보충 24 바뀌는 곳 표, EQ 비교(EQ-T·EQ-1–EQ-5·EQ-P), STOP S-K21–S-K26.
- 지금 계산한 새 기대 sha: W 증거 `b4b7294d…71712`, 입력 행 `435bb673…2731c`(values 정규 `6cc956f0…` 그대로), Wu `6f151334…`, Wj `a82022fc…`, B1s 그대로, `REPORT_ARMS.json` `372bf81f…`, `K92_VALUES.json` `296c6595…975a`, 팔 튜닝 11개(t74_B1 `65cac7ea…`, t9b_B1 `c8e3ee2c…` 등, 보충 25 §2.5), 빌더 `0a74d8e9…`(K9-2-1 판 `3be7a36b…`), `k92_gates.py` `14231534…`, 재실행 도구(KIA) `probe.py` `e20ffdf7…`·`k92lib.py` `cbe1d94f…`·`p0_ref.py` `46985b9e…`·`probe_md.py` `ada32767…`, 판정 도구 `a25_eq.py` `84e444a4…`.
- 후보·확인 도구 폴더 `KB/a25decl/`(AD): `make_a25_tools.py` `01cbab69…`, `make_a25_data.py` `ce818726…`, `make_a25_tools2.py` `e9e1ce13…`, `verify_harness.py` `0f84fdf7…`, 출력 `A25_DATA.json` `38897457…`, `A25_CANDIDATES.diff` `dddf0e6e…`, 자기 시험 `selftest/a25_eq_selftest.json` `3fd69683…`(첫 탐침 S1_W 핀 점검 FAIL·추가 622개 = 원인 검출, 같은 칸 비교 PASS). 모든 AD 파일 sha가 보충 25 본문에 전체 값으로 있음 [실행].
- 한 일(읽기 전용 또는 AD 안 쓰기만) [실행]: 고친 빌더 `w`·`w --check`(U4 표·v3c3-s31 NC .inpx·`TK/arch_t9b` 차로 파일 읽기, 출력 AD), 옛 증거로 보고 팔 3개·팔 튜닝 11개 sha 재현, GWT8 `git show b9734abe:<sa 파일 4개>`로 하네스 패치 재현(8파일 = 첫 탐침, VR만 새 값), 첫 탐침 산출 목록 다시 찍기(M0와 3,806/3,806 같음), 첫 탐침 v3c3-s43·s31 상태의 핀 목록·키 이름 셈(값 0), 옛 트리 캐시 밖 새 파일 0 확인, GWT8 head·K8 브랜치 `b9734abe`, `claude/k92*` 0, status 0줄.
- 새로 찾은 사실: `KI/patch_harness.py` 지금 sha `e38e5e70…`(15:46:39 수정) ≠ LOG 15:33 고정값 `e13cdeb9…`; 첫 탐침 트리는 14:52:32에 이미 빌드됨. 재실행은 지금 바이트를 쓰고 결과 바이트로 맞춰 봄(보충 25 §11-1). D: 여유 630 → 587 GB(이 단계 쓰기는 수 MB).
- 해석 공개: D-K9-42 문구의 빌더 줄(:177)에 더해, W 증거에 남는 경로 문자열 셋(:237-239)도 같은 결정 범위로 읽어 고침(보충 25 §2.2).
- 하지 않은 일: VISSIM·COM·러너·동결·결정 재생·plant 잡 0, 커밋·브랜치·푸시 0, GWT8·PT·KP·OK2P·KI·동결본·런 폴더 쓰기 0, v3c3-s47·봉인 시드 파일 열람 0, 금지 시험 0.

## 2026-10-17 13:3x +0900 — ReviewDeclare A25: 보충 25 반박 검토와 고정

- 검토 전 판(Declare) `SP/K8_PREDECLARATION_AMENDMENT_25.md` `84a5bfc9…5d59` 을 `SP/K8_PREDECLARATION_AMENDMENT_25_r1.md`(+ `.sha256`)로 남김 [실행 `cp -p`, `cmp` 같음].
- 고친 판 `SP/K8_PREDECLARATION_AMENDMENT_25.md` sha256 `4fd7b599fe0f6131143e911dd3ab2be264a175e3f90b185bade9482d60b9ff8e`(98,585 B), `.sha256` 같은 값(`sha256sum -c` OK). 고정점 `KB/AMENDMENT25_FIXED.md` sha256 `d1338fbc40a2efaf6997667f59e7bd709951e1fd3f2b1a8a0a0881794c3d24ed`, 고정 시각 2026-10-17T13:29:43+09:00.
- 고친 곳 8개(보충 25 §14.1, R1–R8): R1 A0에서 빈 `KPA/a25/` 만들기(tksnap 폴더 없음 오류)·M1/T0/M2/T1/s03/s04 자리, R2 A11 이름 셈(TKA는 첫 탐침 트리와 같은 목록; git archive 추적 이름 25개/트리), R3 §6.5-4 훑기 정의를 정규식으로(규칙 문서 자기 매칭 제거), R4 EQ-P 크기 조건 글을 고정 도구 `0 <=`에 맞춤(기대 3,452–70,705 B), R5 발사기 `KI/launch.ps1` `bf7a8132…` 고정·꼬리표 `probe_a25_<단계>`·보존 로그 `probe_trees_guard.txt` `e5781079…` 추가, R6 P0 바이트 복사의 블라인드 까닭, R7 D-K9-45 ③ 범위 공개(k92t 안), R8 재현성 근거·미확인 공개.
- 사슬 끊김 [실행, 결정 재생 0]: `KB/a25review/pin_emul.py`(어댑터 visit 흉내) 새 파일로 키 켬 21칸 추가 집합 = D(팔) 정확히(1 / 3개), 옛 파일로 첫 탐침 실제 622/624와 같은 집합; 흉내 검증 키 끔 4칸 = 실제 1,086(흉내에만 0). `old`은 WMI 분리·BELOW_NORMAL PID 25592(cmd)/27580(python), 12:35:57–12:43, 444.4 s, 스스로 끝남.
- 그 밖 확인 [실행]: 판정 도구 빈 돌리기(EQ-1 선언 잎 26칸, EQ-P D(팔) ⊂ 첫 탐침 추가 집합 21 + 34), 재현성(몫 가르기 재실행 짝 2개 잎 약 242만 개 문제 0; K9-1 잡 짝 18개 summary 문제 0; k92_record 미확인), 망 동일성 s31·s43, 산출 목록 = M0(3,806/3,806), 읽기 전용 뿌리 = s02 SAME, GWT8 `b9734abe`·`claude/k92*` 0·status 0줄.
- 끝 훑기 [실행 `KB/a25review/scan_65_4_v2.py`, 이 항목 쓰기 전]: 고친 §6.5-4 규칙으로 훑기 대상 635파일 0줄.
- 하지 않은 일: VISSIM·COM·러너·동결·결정 재생·plant 잡 0, 커밋·브랜치·푸시 0, 판정 도구·KIA·AD 후보 수정 0, v3c3-s47·봉인 시드 파일 열람 0(그런 이름 경로는 `stat`만), 금지 시험 0. 내 PID만 끔(검토용 `find` 하나, 21256).

## 2026-10-17 13:36 +0900 — Implement 둘째 시도 시작, A0 사전 확인 (보충 25 §4.5)

- 고정점 확인 [실행 `sha256sum`]: 보충 24 `d46db6dc…aadc` = `KB/AMENDMENT24_FIXED.md` 값, 보충 25 `4fd7b599…ff8e` = `.sha256` = `KB/AMENDMENT25_FIXED.md` 값(고정점 파일 자체 `d1338fbc…24ed`). 결정 기록 138줄, `head -n 138` = `362cd6c2…399a`.
- §13 AD 파일 sha 전부, §2.5 AD 데이터(W 증거 `b4b7294d…`, 입력 행 `435bb673…`, H-b `b9fa1d01…`, Wu `6f151334…`, Wj `a82022fc…`, B1s `e7a4c7e9…`, `REPORT_ARMS.json` `372bf81f…`, 팔 튜닝 11개), `AD/data/K92_VALUES.json` `296c6595…`, §4.3 KIA 출처(KI·AD·A25) sha, 발사기 `KI/launch.ps1` `bf7a8132…` — 모두 보충 값과 같음 [실행].
- 자리: TKA·OK2A·KPA·KIA 모두 없음을 먼저 확인 → 빈 `KPA/a25/`만 만듦 [실행].
- M1 [실행 `python -B A25/probe_manifest.py KPA/a25/M1.json`, 21.6 s]: 3,806파일, sha256 `f366a5577ff9463c33a9047d606b6c56e7e7ca3a2ddc85015755576f0969e158`. `a25_eq.py mcmp M0 M1` → `MCMP files=3806/3806 differing=0`(rc 0).
- 보존 로그 [실행]: `OK2/logs/probe_main.txt` `6175a528…9576`, `probe_trees_guard.txt` `e5781079…0652` — 보충 값과 같음.
- 읽기 전용 뿌리 스냅숏 s03 [실행 `KI/k92snap.py take OK2/snap/s03_a25_A0.json`, 35.9 s] sha256 `992e8a8278931618df5f06f6f084e05f6d6bbaed8f834fc34e8f93546443b316`; `diff s02 s03` → SAME.
- GWT8 [실행]: head = K8 브랜치 = `b9734abe1c83f95c9cec5fca5e42b7b18cd45991`, `claude/k92*` 0개, `git status --porcelain` 0줄. 드라이브 C: 26 GB, D: 588 GB. VISSIM 0, python 0.
- A0 통과 조건 모두 참. 다음: A1 도구 설치.

## 2026-10-17 13:39 +0900 — A1 도구 설치 (보충 25 §4.3, §4.5 A1)

- 옛 스테이징 바이트 보존 `KI/pre_a25/<같은 상대 경로>` [실행 `cp -p`]: VR `6335400b…`, `tests/test_k92_harness.py` `62c5341e…`, `k92_gates.py` `1a611805…`, `test_k92_w.py` `30c33f9a…`, `test_k92_hb.py` `4d3799d9…`, `k92/README.md` `90f41b48…`, 빌더 `d33ee9f0…`, `stage_k921` 빌더 `8877c850…`, `commit_k92.py` `1bdb3c70…`, `split_builder.py` `f973c29a…` (옛 값 그대로).
- KIA(`KI/a25`) 설치 [실행]: `probe.py` `e20ffdf7…`, `k92lib.py` `cbe1d94f…`, `p0_ref.py` `46985b9e…`, `probe_md.py` `ada32767…`, `patch_harness.py` `e38e5e70…`, `patch_runtime.py` `271159b7…`, `repo/…/sa/k92_common.py` `013d26db…`, `k92_record.py` `1d1dfa36…`, `k92_compare.py` `55df106b…`, `k92_vissim_ref.py` `f3fcc574…`, `a25_eq.py` `84e444a4…`. 파일 11개뿐(표와 같음).
- 스테이징 바꿈 [실행]: VR `f3fcc574…`, `test_k92_harness.py` `e217359b…`, `k92_gates.py` `14231534…`, `test_k92_w.py` `ae31896b…`, `test_k92_hb.py` `b0b16c5b…`, `k92/README.md` `b190759a…`, 빌더 `0a74d8e9…`, `KI/stage_k921` 빌더 `3be7a36b…`, `KI/commit_k92.py` `e3c7e38e…`, `KI/split_builder.py` `d9cd3e95…` — 모두 보충 값.
- T0 [실행 `KI/launch.ps1 -Tag probe_a25_A1_tksnap -Script a25\a25_eq.py tksnap KPA/a25/tk_T0.json`, WMI PID 22004, 13:37:49–13:38:58]: `TKSNAP files=244388`, sha256 `bac1274bb1f2e1299511ab8112242009e9e71576df3354fcfb254c193c69c4ea`. TKA 아직 없음.
- A1 통과 조건 모두 참.

## 2026-10-17 13:51 +0900 — A2 P0′ (보충 25 §4.2, §4.5 A2)

- (i) [실행 13:39 `python -B KI/repo/…/k92/build_k92_evidence.py w --root TK/arch_t9b --out-dir KPA/p0`] `K92_EVIDENCE_OK w` 증거 `b4b7294d…71712`, 입력 행 `435bb673…2731c`, `capacity_repr=5209.8`; `w --check` → `K92_EVIDENCE_CHECK_OK w values_sha256=6cc956f0…0aac`.
- (ii) 바이트 복사 [실행 `cp -p`, KP → KPA]: H-b 증거 `b9fa1d01…`, `p0_2f_names.json` `a1f4ffb3…`, `p0_3_links.json` `cc71626b…`, `p0_4_samples.json` `1851f6cc…`, `p0_4_exposure_review.json` `21fd54e7…`, `gk1_floor_names.json` `cf1ae3fb…` — 복사본 sha = 원본.
- (iii) [실행 `KIA/p0_ref.py arms`] Wu `6f151334…`, Wj `a82022fc…`, B1s `e7a4c7e9…`, `REPORT_ARMS.json` `372bf81f…`.
- (iv) [실행 `KI/launch.ps1 -Tag probe_a25_A2_reftrees -Script a25\p0_ref.py trees`, WMI PID 11748, 13:39:52–13:49:09] `TKA/ref_t74_CWf`·`ref_t9b_CWf`·`ref_t74_X1f` 모두 `ok=True`(RS `ea79be3a…`·`ea79be3a…`·`0ba3fa61…`, X1f SHO `0d295c11…`). 빌드 기록의 `files`·`compare_to_base`·`tuning_sha256`·`expected`가 첫 탐침 기록과 같음.
- (v) `AD/data/K92_VALUES.json` → `KPA/K92_VALUES.json` `296c659562e45528606599aa4df99535faa694a86533ffca6bb2fbcde7db975a`.
- KPA/p0의 7개 파일 = `AD/data/p0` 같은 이름 파일과 바이트 같음(다름 0) [실행 `cmp`].
- A2 통과 조건 모두 참(S-K24 아님).

## 2026-10-17 14:30 +0900 — A3 트리 (보충 25 §4.4, §4.5 A3)

- [실행 `KI/launch.ps1 -Tag probe_a25_A3_trees -Script a25\probe.py trees`, WMI PID 19628, 13:49:56–14:29:21] PTA = `git archive b9734abe`(10,548파일) + 런타임 w·hb(RS `70cca680…`, SHO `a6b5931e…`) + 하네스 probe(VR `f3fcc574…`) → `PROBE_TREE ok files_changed=6 new=21`. 팔 트리 13개 모두 `ok=True`(튜닝 sha = 보충 25 §2.5 새 값, OFF = `5f0d0e40…`·`d0f9ef39…`), `arch_t9b`·`arch_t74` 생김(`ARCH_TREE arch_t74 ok=True`).
- 빌드 기록 sha 목록 `KPA/a25/tka_build_records.sha256.txt`; `TKA/k92b1_probe.build.json` = `78f954ec756c85789eef929ed628d46b626f7b2532c5ee0c657d01b62d46b7ec`.
- EQ-T [실행 14:29 `python -B KIA/a25_eq.py treecheck`]: `ok=True`(rev·archive_files·runtime·diff_declared_only·diff_vs_archive·harness·evidence·arms·arm_trees·arch·ref_trees 모두 참). `KPA/A25_EQT.json` sha256 `10a55a049078f498b3b25e43b2831acf42d4003572c406958c5a4a1b56554b79`.
- A3 통과 조건 모두 참.

## 2026-10-17 14:30 +0900 — A4 가드, A5 발사

- A4 [실행 `KI/launch.ps1 -Tag probe_a25_A4_guard -Script a25\probe.py guard`, WMI PID 19692, 14:29:56–14:29:57]: `GUARD_SELFTEST ok=True n=21 bad=[]`. `KPA/guard_selftest.json` sha256 `cb5dc58e5ab2599a69e7dcf55d638a10d0ba1525f3598dee051b3f9d6eaa7982`; `k92_common_sha256` = `013d26db…`; 사례 21개의 (이름, 기대 거부, 거부, ok)가 첫 탐침 파일과 같음(미리 보기, 판정은 A10 EQ-4).
- A5 발사 [실행 14:30:15 `KI/launch.ps1 -Tag probe_a25_A5_ref -Script a25\probe.py ref`, WMI PID 21816].
- [2026-10-17 15:21 +0900] 탐침 기준 팔 재생 5칸 끝(probe.py ref, 자동 기록): `KB/k92_probe_a25/K92_REF.json` sha256 `af916995f9e3bfb049ebb34bd68e8ba5d261e9a892afaabca92ccc01b52fd021` — 고정(RG-3a), 이후 다시 계산하지 않음.

## 2026-10-17 15:23 +0900 — A5 기준 팔 5칸 (보충 25 §4.5 A5)

- [실행 `KI/launch.ps1 -Tag probe_a25_A5_ref -Script a25\probe.py ref`, WMI PID 21816, 14:30:15–15:21:58] S1_CWf·S2_CWf·S3_CWf·S4_CWf·S3_X1f 모두 `replay_run.exit_code` 0, `REPLAY_CHECK derived ok=True`, `action_contract ok=True`, 오류 파일 0, DECISION_FAILED 0, 훅 오류 0, 트리 앞뒤 sha 같음. 튜닝 = 바탕(`5f0d0e40…`, S2 `d0f9ef39…`). 결정 벽시계 381.5 / 742.4 / 376.5 / 775.9 / 768.3 s.
- 자동 고정 `KPA/K92_REF.json` sha256 `af916995f9e3bfb049ebb34bd68e8ba5d261e9a892afaabca92ccc01b52fd021`(위 자동 줄과 같음). CSV sha 5칸 모두 첫 탐침 색인과 같음(미리 보기, 판정은 A10 EQ-1).
- A5 통과 조건 모두 참.
- [2026-10-17 18:57 +0900] 탐침 팔 재생 21칸 끝(probe.py arms, 자동 기록): `KB/k92_probe_a25/K92_PROBE_OUT.json` sha256 `e3ded96bbe14581fa6cfb5c387c51c4bb453c3aa983c0f8e7c1189bdef870c4d` — 고정.

## 2026-10-18 12:50 +0900 — 이어 하기(사용 한도로 끊긴 뒤): 상태 확인, A6 통과 확인

- 고정점 다시 확인 [실행 `sha256sum`]: 보충 24 `d46db6dc…aadc`, 보충 25 `4fd7b599…ff8e` = `.sha256` = `KB/AMENDMENT25_FIXED.md` 값(고정점 파일 `d1338fbc…24ed`), 보충 24 고정점 `fbc3d59f…101a`, 결정 기록 138줄 `362cd6c2…399a`.
- 기록된 산출 확인 [실행]: `KPA/K92_REF.json` `af916995…d021`, `KPA/K92_PROBE_OUT.json` `e3ded96b…0c4d`, `KPA/K92_VALUES.json` `296c6595…975a`, `KPA/A25_EQT.json` `10a55a04…4b79`, `KPA/guard_selftest.json` `cb5dc58e…7982` — LOG 값과 같음. KIA 11개·발사기 `bf7a8132…` sha = 보충 25 §4.3 값.
- A6 통과 조건 [실행, 값 출력 0]: `OK2A/arms/*.summary.json` 21개 모두 `replay_run.exit_code` 0, `derived`·`action_contract` 참, 오류 파일 0, DECISION_FAILED 0, 훅 오류 0, infra 없음; `K92_PROBE_OUT.json` 21칸 `ok` 참. 표준 출력 `OK2/logs/probe_a25_A6_arms.txt` 끝 줄 `PROBE end ['arms']`. 결정 벽시계 359–757 s(키 켬 칸이 같은 상태 키 끔 칸과 비슷함, 보고만).
- 현재 [실행]: GWT8 head = K8 브랜치 = `b9734abe`, `claude/k92*` 0, status 0줄; python·VISSIM 프로세스 0; C: 29.7 GB, D: 543 GB.
- 다음: A7 plant 발사.
- [2026-10-18 12:50 +0900] A7 발사 [실행 `KI/launch.ps1 -Tag probe_a25_A7_plant -Script a25\probe.py -ArgLine plant`, WMI PID 11496(cmd), 12:50:08, 그때 VISSIM 0·python 0]. 표준 출력 `OK2/logs/probe_a25_A7_plant.txt`.

## 2026-10-18 13:03 +0900 — 커밋 도구 검토(관문 데이터 0개 상태): A′ 구동기 변경 확인, 첫 탐침 트리를 가리키는 곳 3개 발견

- 구동기 [실행 `diff -u KI/pre_a25/<f> KI/<f>`]: 이전 세션이 2026-10-17 14:01–14:02에 `KI/cglib.py`(`866a79e7…` → `be5a0c95ad7bc86da55f6cf65b3804447ebce75cf4e829f6609e86d2a292b048`)와 `KI/cgates.py`(`88a23ff4…` → `14733a2cbfa25d7ce1ebeefc9ac889764965e21769c5ed3ec64009f558c36fa9`)를 고쳤고 LOG에는 적지 않았음. 옛 바이트는 `KI/pre_a25/`에 있음(sha 옛 값 그대로). 차이는 보충 25 §6.3 항목 1–5뿐: 봉인 뿌리 `OK2/sealed_s47/<커밋>/plant/{base,new}`(G-K0 plant base·new, G-K1 동적, G-K4 plant), 봉인·판정 실행 표준 출력 = 봉인 뿌리 `logs/<실행>.txt`(다시 읽지 않음, 새 파일만), 실패 보고 = 종료 코드·파일 이름·크기, 봉인 밖 색인 `OK2/commit/<커밋>/sealed_s47_index.json` + `SEALED_S47` 한 줄, 상수 `KP`·`PROBE_OUT`·`VALUES_SHA`·`REPORT_ARM_SHA`(§2.8 값). 자식 환경 변수 처리는 기존 `run_child`·`run_py`와 같음(열기 모드만 `x`). 항목 6(감시)은 내 대기 방법으로 지킴.
- 스테이징 [실행 sha256·`git hash-object --no-filters`]: `KI/repo` 12파일과 `KI/stage_k921` 빌더 = 보충 25 §8.1·§2.8 값(VR `f3fcc574…`/`1f351efd…`, 시험 `e217359b…`/`ee8a8ea3…`, `k92_gates.py` `14231534…`/`251350fe…`, 빌더 `0a74d8e9…`/`3c17712b…`·`3be7a36b…`, `test_k92_w.py` `ae31896b…`/`5f81a4e1…`, `test_k92_hb.py` `b0b16c5b…`/`9dca3de5…`, README `b190759a…`/`7a733537…`). `KI/commit_k92.py` = `e3c7e38e…`, `KI/split_builder.py` = `d9cd3e95…`(§13 값). 커밋 메시지 4개는 보충 25 sha를 담도록 14:12에 고쳐져 있음(옛 판 `KI/pre_a25/commit_msgs`).
- **발견(데이터 전) — 재실행 뒤에도 첫 탐침 트리(PT `TK/k92b1_probe`)를 가리키는 곳 3개** [실행]:
  - D1 `KI/cgates.py:184` `arm_bytes`가 커밋 트리 팔 바이트를 `TK/k92b1_probe.build.json`(첫 탐침, 옛 팔 sha)과 맞춤. 새 증거로 만든 팔은 보충 25 §2.5 새 sha(t74_W `d179f01d…` 등)라 옛 값(`434fe6bf…`)과 다름 → K9-2-1 `trees` 단계에서 SystemExit(관문 판정 전 구동기 멈춤). K9-2-2도 같음. K9-2-0·K9-2-3은 이 함수를 쓰지 않음.
  - D2 `KI/cgates.py:720` G-K4 판정의 뿌리 목록에 `probe_root = TK/k92b1_probe`(PT). 탐침 잡은 이제 PTA 위에서 돌았으므로 뿌리는 PTA여야 함. 다만 첫 탐침 잡 `k92pW/TL3_1500_SAF_OBS_H3`의 `summary.json`·`k92_record.json`에는 `k8_gate_trees` 문자열이 0개라 판정에 닿지 않을 수 있음(보고만).
  - D3 `KI/commit_k92.py:191`(보충 25 §13 후보 `e3c7e38e…`) K9-2-3 기대 팔 바이트를 PT에서 읽음: PT의 `config_n31_v2_k92b1.json` = `f42fc98e…`(옛), PTA = `c8e3ee2c…`(= `CFG_ARM_SHA`) → K9-2-3 커밋 앞에서 SystemExit.
  - 까닭: 보충 25 §2.8(같이 바뀌는 바이트, 닫힌 목록)과 §6.3(구동기 변경, 닫힌 목록)이 이 세 곳을 담지 않음. `KI/k92lib.py`(첫 탐침 고정 도구)의 `TK`가 옛 뿌리라서 생김.
  - 처리: D3은 §13 후보를 손으로 고치는 일이라 S-K26(그 단계 전 STOP). D1도 §6.3 닫힌 목록 밖 변경이라 고치지 않음. 그래서 **K9-2-0 커밋·관문(이 세 곳에 닿지 않음)까지 하고, K9-2-1 커밋 전에 멈춰 사용자에게 묻는다**. 구동기 sha는 위 값 그대로 K9-2-0 관문 데이터 전에 고정함(아래 K9-2-0 항목).

## 2026-10-18 14:20 +0900 — A7 plant (보충 25 §4.5 A7), A8 발사

- [실행 `KI/launch.ps1 -Tag probe_a25_A7_plant -Script a25\probe.py -ArgLine plant`, WMI PID 11496, 12:50:08–14:19:38] `PLANT_CHILD exit=0`, `K92_PLANT_DONE`; 이어 새 VR: `K92_VISSIM_REF s31 states=[1500, 2850, 3900, 5250, 6000, 6600, 7500, 8250] … inpx=3de889f0257d998b`, `K92_VISSIM_REF s43 states=[1050, 3300, 4800, 5550, 6450, 7050, 7800, 8400] … inpx=51478c397b3a2570`, `VISSIM_REF exit=0`, `PROBE end ['plant']`.
- 셈 [실행, 값 출력 0]: 잡 48개 `summary.ok` 참·기록기 오류 0·`k92_record.errors` 0; 포착 `capture.json` 52개, `capture_failed.json` 0개, `*.error.txt` 52개(포착 멈춤 기록, EQ-5에서 판정). `OK2A/plant/sa/k92_vissim_ref.json` sha256 `418b7eaec761a91d2c4df0aa0b84975dc3d0a698d36e112c665365181f0c663e`.
- 시간(보고만): 포착 키 끔·켬 모두 약 29–33 s, 잡 약 70–80 s(첫 탐침 키 켬 포착 380–430 s).
- A7 통과 조건 모두 참.
- A8 발사 [실행 14:20:05 `KI/launch.ps1 -Tag probe_a25_A8_wall -Script a25\probe.py -ArgLine wall`, WMI PID 2188, 그때 python 0·VISSIM 0]. 끝날 때까지 다른 무거운 잡 0.

## 2026-10-18 17:23 +0900 — A8 벽시계 짝 (보충 25 §4.5 A8)

- [실행 `KI/launch.ps1 -Tag probe_a25_A8_wall -Script a25\probe.py -ArgLine wall`, WMI PID 2188, 14:20:05–17:23:03] `WALL done pairs=8`, `PROBE end ['wall']`. 재생 기록 16개, 짝 8개 모두 `ok` 참·`clean` 참(VISSIM 개수 세 번 0). 이 동안 내 다른 무거운 잡 0(확인은 로그 `stat`·짧은 읽기만).
- `OK2A/wall_pairs.json` sha256 `385a8303636bcaeddedf8bf61ddea041f5fb504cafdfb13a5a53b9426c7cae43`. 짝 비(B/A, 벽시계 초끼리; 모형 값 아님): S1 0.99570·1.00014, S2 0.99545·0.97976, S3 1.00019·0.96808, S4 0.95957·1.01361.
- A8 통과 조건(16재생 종료 0, 짝 8 기록) 참. 규칙 5 판정은 A9 보고 도구가 냄.
- [2026-10-18 17:27 +0900] A9 보고 [실행 `KI/launch.ps1 -Tag probe_a25_A9_report -Script a25\probe.py -ArgLine report`, WMI PID 10820, 17:23:43–17:26:58]: `REPORT stop_ask=True problems=1 incomplete=0`. **`KPA/K92_PROBE_RESULTS.json` sha256 `e56af450e0222de50cc6da9ae2039c98a7847cfa451d1b410f19d599a2f73c86` — 계산 직후 고정.**
- [2026-10-18 17:43 +0900] A9 계속 [실행 `python -B KIA/probe_md.py`]: `KPA/K92_PROBE_RESULTS.md` sha256 `c43f9f628a4710e150b8480606d2316d712f499807c5e7065fd220730dda1a1a`. 머리 메모 `K92_PROBE_RESULTS_A25_NOTE.md`는 §4.7-5(EQ 요약)가 A10 결과를 담아야 해서 A10 뒤에 씀(순서만 바뀜, 내용 규칙 그대로).
- [2026-10-18 17:43 +0900] A10 비교 [실행 `KI/launch.ps1 -Tag probe_a25_A10_eq -Script a25\a25_eq.py -ArgLine eq`, WMI PID 21980, 17:27:45–17:42:4x]: `A25_EQ ok=True {EQT, EQ1, EQ2, EQ3, EQ4, EQ5, EQP 모두 True}`. EQ-1 26칸 모두 CSV 같음·HARD SAME·잎 문제 0; EQ-2 잡 48개; EQ-3 참; EQ-4 참; EQ-5 `error_files=52 capture_failed=0`; EQ-P 결정 21/21(W 계열 12칸 핀 1,087 대 키 끔 1,086, H-b 계열 9칸 1,089 대 1,086, 추가 = D(팔) 정확히), 키 끔 = 첫 탐침 참, 포착 34/34. **`KPA/A25_EQ.json` sha256 `213651d0c05ceed56e111365cac498eccb913ff09776605be194d94ea0b028bc` — 계산 직후 고정.** A10 통과 조건 참.

## 2026-10-18 17:47 +0900 — A11 사후 (보충 25 §4.5 A11)

- M2 [실행 `python -B A25/probe_manifest.py KPA/a25/M2.json`, 75.0 s]: 3,806파일, `blind_named 0`, sha256 `8bad04b00f9c903d75ea48bec38ab9e9ecea8a6d30c77eb2dbd8539da8aaadf7`. `a25_eq.py mcmp M0 M2` → `MCMP files=3806/3806 differing=0`(rc 0).
- s04 [실행 `KI/k92snap.py take OK2/snap/s04_a25_A11.json`, 39.3 s] sha256 `4a5869f98f08fe42c34d39426b18edd5f1fcbc87a04305a7c9de66f85737a3e1`; `diff s02 s04` → `SAME`(rc 0).
- T1 [실행 `KIA/a25_eq.py tksnap KPA/a25/tk_T1.json`] `TKSNAP files=244388`, sha256 `bac1274bb1f2e1299511ab8112242009e9e71576df3354fcfb254c193c69c4ea`(= T0 파일 sha); `tkcmp T0 T1` → `same=True n=244388/244388`(rc 0).
- 보존 로그 [실행]: `OK2/logs/probe_main.txt` `6175a528…9576`, `probe_trees_guard.txt` `e5781079…0652` — §4.1-2 값과 같음.
- 이름 셈 [실행 새 도구 `KB/a25post/names_a11_run.py` sha256 `5887e9420e79d309feecfc860310a1eb0cff2a3f2b678a658b3d2a615f16b987`(정규식 = `a25_eq.BLIND`, os.walk 이름만, 파일 열지 않음), 출력 `KB/a25post/names_a11_run.out.json` `de89f9da…10b5`]: OK2A 0개, KPA 0개, TKA 19트리 모두 같은 이름 첫 탐침 트리와 상대 경로 목록 같음(각 25개).
- GWT8 [실행]: HEAD = K8 브랜치 = `b9734abe`, `claude/k92*` 0, `status --porcelain` 0줄. python 0, VISSIM 0. C: 29.7 GB, D: 539.9 GB.
- A11 통과 조건 모두 참. 재실행 A0–A11 통과 조건은 모두 참이고 `A25_EQ.json` `ok` 참(규칙 7 거짓).
- **탐침 정지·질문 규칙 상태(보충 25 §4.6)**: 규칙 1 거짓(재생 26칸·잡 48·포착 52 정상, 포착 멈춤 기록은 EQ-5 참), 규칙 2 거짓(대상 8쌍 HARD SAME, S3 B1s는 선언된 H5 한 건), 규칙 3 거짓, 규칙 4 거짓(M3 편향 차 +0.223대 ≤ +5), **규칙 5 참**(짝 8개 모두 clean, 비 중앙 0.99558 ≤ 1.0158, **사분위 범위 0.02331 > 0.006**), 규칙 6 거짓, 규칙 7 거짓. → 보충 24 §3.3·보충 25 §4.6: 하나라도 참이면 구현 전 보고·질문. **커밋 K9-2-0…3으로 가지 않고 STOP.**
- [2026-10-18 17:48 +0900] A9 끝: 손으로 쓴 머리 메모 `KPA/K92_PROBE_RESULTS_A25_NOTE.md` sha256 `cd438f4a18f2db874e538a7851d083026241f76a6978004c725b72427eb15dc2`(§4.7 1–6, EQ 요약, 시간 보고, 규칙 표). A9 세 파일 모두 있음.

## 2026-10-18 17:51 +0900 — 둘째 시도 끝: STOP(탐침 규칙 5), 커밋 0

- `KB/IMPLEMENT.md`에 둘째 시도 절을 덧붙임(앞 12,267 B = `2e826f6c…5645` 그대로) [실행]: 전체 sha256 `8fcc6a9451a7a5cd84b3947cfe63b63706b13b004eeb2443a5105326f4198b03`(24,994 B). 덧붙인 원문 사본 `KB/a25post/implement_attempt2_section.md` sha256 `4a951e09a851747d368a088b7366dce63d55ceb47bd1edd571d39e83db24ec75`.
- 결과 STOP: 재실행 A0–A11 참·EQ 모두 PASS, 탐침 규칙 5 참(사분위 범위 0.02331 > 0.006) → 보충 24 §3.3·보충 25 §4.6에 따라 커밋 K9-2-0…3 시작 안 함. 브랜치·커밋·푸시 0. 사용자 결정 대기: Q1 규칙 5 처리, Q2 커밋 도구 결함 D1–D3(새 보충 필요).
- 끝 상태 [실행]: GWT8 HEAD = K8 브랜치 = `b9734abe`, `claude/k92*` 0, status 0줄; python 0, VISSIM 0; 내 PID만 썼고 끈 프로세스 0.

## 2026-10-18 18:55 +0900 — Declare A26: 보충 26 작성 (D-K9-46·47·48)

- 시작 확인 [실행]: 결정 기록 `e15ae943…`(147줄, 앞 138줄 = `362cd6c2…`), 보충 24 `d46db6dc…`/고정점 `fbc3d59f…`, 보충 25 `4fd7b599…`(= `.sha256`)/고정점 `d1338fbc…`. `OK2/commit`·`OK2/sealed_s47` 없음(커밋 관문 데이터 0개). GWT8 HEAD = K8 브랜치 = `b9734abe`, `claude/k92*` 0, status 0줄. python·VISSIM 0. C: 29.7 GB, D: 540 GB.
- 쓴 파일: `SP/K8_PREDECLARATION_AMENDMENT_26.md` sha256 `5e1453ea6cc0bcd4ae9f365fd1d0148a2bbda5073fb23cf8ecf2dba4463d7d03`(51,977 B), `SP/K8_PREDECLARATION_AMENDMENT_26.md.sha256` 같은 값(`sha256sum -c` OK). 고정점 `KB/AMENDMENT26_FIXED.md`는 반박 검토 단계가 씀.
- 담은 것: (1) D-K9-46 탐침 규칙 5 "가릴 수 없음" 처리 기록(짝 비 8개, 중앙 0.99558, 사분위 범위 0.02331; 규칙 정의 불변). (2) D-K9-47 G-K5 (a) 새 통과 칸 = 깨끗한 짝 비 중앙 ≤ 1.0158이면 PASS, 사분위 범위는 보고만(근거 = K9-1 미니 탐침 IQR 0.0395·0.0577, K9-2 재실행 0.0233). 보충 24 §3.1-8 "커밋별 관문 계산은 그 블롭으로만" 때문에 구현 자리는 K9-2-0 판정기 `k92_gates.py`(:37·:91·:511·:512)와 시험 `test_k92_harness.py`(:261) — D-K9-48 목록 밖 변경으로 공개. (3) D-K9-48 D1 `cgates.py:184`·D2 `:720`·D3 `commit_k92.py:191`을 `TK/a25/k92b1_probe`(+ 빌드 기록 `78f954ec…`)로. (4) 구동기·도우미·스테이징·메시지·기준 파일 sha 고정 규칙(첫 `commit_k92.py` 전, 발사마다 대조, S-K27), 적용 순서 B0–B4, S-K28. (5) 그 밖의 보충 24·25 그대로(§8·§9).
- 후보·확인 도구 폴더 `KB/a26decl/`(AD6) [실행]: `make_a26_cands.py` `ef6fab5c…` → 후보 `cand/cgates.py` `1fbe827f…`, `cand/commit_k92.py` `511fbf9e…`, `cand/repo/…/k92_gates.py` `9418d3e4…`(블롭 `2d907dca…`), `cand/repo/…/tests/test_k92_harness.py` `ae9741d9…`(블롭 `9a8a5e3a…`), 차이 `A26_CANDIDATES.diff` `4a4aa87f…`. 확인 도구 `dry_a26.py` `2c7447fb…`.
- 데이터 없는 시험 [실행 `dry_a26.py static --src cand` 18:44:36, 2 s → `dry/dry_a26_static_cand.json` `c43998ef…` ok=True]: D1 새 줄 8/8 팔 = TKA 기록 = 보충 25 §2.5, 옛 줄 8/8 SystemExit(결함 재현), PT 위 새 줄 8/8 SystemExit; 보고 팔 다시 만들기 바이트 = KPA; D2 탐침 잡 4개 문자열에 트리 뿌리 0개; D3 새 줄 `c8e3ee2c…`, 옛 줄 SystemExit; G-K5 판정식(ast로 꺼냄) 탐침 짝 8개 옛 CANNOT_TELL → 새 PASS, 합성 6사례 중 다른 곳은 넓은 짝 하나뿐.
- [실행 `dry_a26.py pytest --src cand` 18:44:49–18:45:11 → `dry/dry_a26_pytest_cand.json` `a16e8d57…` ok=True]: TC6 = `OK2/slow/verify_u_k920` 복사(읽기만, 4,710파일, 블라인드 이름 19개 이름만 보고 건너뜀, `TK/a26decl/tc.copy.json` `f1d2b4dd…`), K9-2-0 파일 묶음을 `patch_harness.apply(…, 'k920')`로 써서 `test_k92_harness.py` 지금 판 16 passed, 후보 판 16 passed; 묶음 차이 = 두 파일뿐.
- 발견(공개, 결함 아님): 스테이징에 `k92/WORKLOG_20261016.md`가 아직 없어 `expect_k923`이 그 줄에서 멈춤 — 첫 시도 계획("관문 결과가 필요해 아직 안 씀")대로이며 보충 26 §5-5가 K9-2-3 전에 쓰고 LOG에 적도록 정함.
- 스냅숏 [실행 `KI/k92snap.py`]: s05 `OK2/snap/s05_a26decl_before.json` `934b056a…`, s06 `s06_a26decl_after.json` `b1e2624a…`, 둘 다 s02 대비 SAME.
- 하지 않은 일: VISSIM·COM·러너·동결·결정 재생·plant 잡 0, 커밋·브랜치·푸시 0, KI·KIA·KPA·PT·PTA·OK2A·GWT8 쓰기 0(GWT8은 `cat-file`·`rev-parse`·`status`만), v3c3-s47·봉인 시드 파일 열람 0, 금지 시험 0. 내 PID만 썼고 끈 프로세스 0.

## 2026-10-18 19:20 +0900 — ReviewDeclare A26: 보충 26 반박 검토·고정

- 시작 확인 [실행]: 보충 26 Declare 판 `5e1453ea…7d03` = `.sha256`, 결정 기록 `e15ae943…`(147줄), 보충 24 `d46db6dc…`/고정점 `fbc3d59f…`, 보충 25 `4fd7b599…`/고정점 `d1338fbc…`. `OK2/commit`·`OK2/sealed_s47` 없음(커밋 관문 데이터 0). GWT8 head = K8 브랜치 = `b9734abe`, `claude/k92*` 0, status 0줄. python·VISSIM 0. C: 30 GB, D: 540 GB.
- 검토 전 사본 `SP/K8_PREDECLARATION_AMENDMENT_26_r1.md` = `5e1453ea6cc0bcd4ae9f365fd1d0148a2bbda5073fb23cf8ecf2dba4463d7d03`(+ `.sha256`, Declare 판과 `cmp` 같음).
- 고친 곳 8개(보충 26 §13.1, [검토] 표시): R1 완결성 STOP S-K29(G-K5 `n_rows`·`n_clean` ≠ 8 → 다음 커밋 전 STOP; 판정 칸·바이트 그대로), R2 중앙만 판정이 잡는 것(고르게 ×1.02027부터 FAIL = 옛 경계)·못 잡는 것(3짝 이하에 몰린 느려짐) 공개와 보고 항목, R3 K9-1 관측 ①의 측정 종류 바로잡음, R4 고정 목록에 재생 칸 바깥 도구 4개(44개), R5 `KB/a26_pins.sha256` + `sha256sum -c` 대조 방법, R6 K9-2-0 메시지 기대 sha를 고정점에 미리 적음, R7 `ok` 조건은 판정기 기존 조건, R8 B0에 39개 대조. G-K5 (a) 판정 칸(D-K9-47)·문턱은 바꾸지 않음.
- 점검 [실행 `KB/a26review/review_a26_checks.py` `ab4a37da…` → `out/review_a26_checks.json` `00478a4e…`]: 판정식 옮겨 감 무작위 200,000개 — CANNOT_TELL→PASS 52,693 말고는 같은 판정, 그 밖 0; 고정 목록 44개 지금 값 모두 맞음; 판정기·시험 후보 블롭 `2d907dca…`·`9a8a5e3a…`, CR 0. D1–D3 빠짐없음: 커밋 단계가 닿는 KI 파일에서 옛 탐침 트리·옛 빌드 기록을 가리키는 줄은 세 줄뿐 [grep·가져오기 추적].
- 고정판: `SP/K8_PREDECLARATION_AMENDMENT_26.md` sha256 `8f8356168a299c07960d86ef12aa9f7af6f2f040af08ba75e5233a5819edba37`(72,092 B), `.sha256` 같은 값(`sha256sum -c` OK).
- K9-2-0 메시지 기대 바이트 [실행 `KB/a26review/make_msg_expect.py` `e6e7fa40…`]: `out/K9-2-0.expected.txt` sha256 `874e6a3f5af190ab00a4582ef381b9013f3a83b1aa354d61d4e1be9459394083`(3,501 B), 점검 모두 참(`out/msg_expect.json` `aa1ca2a3…`).
- 고정점 `KB/AMENDMENT26_FIXED.md` sha256 `6edc55acd5aa0976701456d956e33f33c52ae0853535f6a4d8cb8bf26a354581`(11,962 B), 고정 시각 2026-10-18T19:18:22+09:00. 남은 미해결 없음.
- 하지 않은 일: VISSIM·COM·러너·동결·결정 재생·plant 잡 0, 커밋·브랜치·푸시 0, KI·AD6·스테이징·GWT8·PT·PTA·OK2A 쓰기 0(GWT8은 `rev-parse`·`branch --list`·`status`만), v3c3-s47·봉인 시드 파일 열람 0, 금지 시험 0. 내 PID만 썼고 끈 프로세스 0.

## 2026-10-18 19:25 +0900 — Implement A26: B0 사전 확인 (보충 26 §6 B0)

- 새 점검 도구 폴더 `KB/a26impl/`(구현 단계, 커밋 안 함): `a26_lists.py` sha256 `0d971f8a969aad7e01be708a5a6f3ee9c430f363d9f6fc494e3a8aa0bf13b5fa`(보충 26 §5-2 44개·§12 AD6 18개·§0 문서 값을 그대로 옮김), `b0_check.py` `521aec928975060202505d23a05972e422d67be2caa11407b0000e8ca4c46b01`.
- [실행 `python -B KB/a26impl/b0_check.py` → `KB/a26impl/out/b0_files.json`] `B0_FILES ok=True`: 문서 6/6(보충 26 `8f835616…ba37` = `.sha256` = 고정점 `6edc55ac…4581`의 값, 보충 25 `4fd7b599…`/고정점 `d1338fbc…`, 보충 24 `d46db6dc…`/고정점 `fbc3d59f…`), 결정 기록 147줄 전체 = `e15ae943…`, AD6 18/18, B1이 바꿀 5개의 지금 바이트 5/5(`cgates.py` `14733a2c…`, `commit_k92.py` `e3c7e38e…`, 판정기 `14231534…`, 시험 `e217359b…`, `K9-2-0.txt` `ad6359e8…`), B1이 바꾸지 않는 고정 39/39.
- [실행] `OK2/commit`·`OK2/sealed_s47` 없음. GWT8 HEAD = K8 브랜치 = `b9734abe1c83f95c9cec5fca5e42b7b18cd45991`, 지금 브랜치 = K8 브랜치, `claude/k92*` 0, `status --porcelain` 0줄, core.autocrlf=true. C: 34 GB, D: 540 GB. VISSIM·python·cscript 프로세스 0.
- [실행 `KI/k92snap.py take OK2/snap/s07_a26_B0.json`, 36.4 s] sha256 `8290d7bdf5a082980822330c9ac372decacdd31f81d09c13e3d5ae503be34ed9`; `diff s02 s07` → `SAME`(rc 0).
- B0 통과 조건 모두 참.

## 2026-10-18 19:28 +0900 — Implement A26: B1 설치 (보충 26 §6 B1)

- [실행 `python -B KB/a26impl/b1_install.py`(sha256 `a216f62c886c9a54f6cfe1dd10ff56a5d1362864fb856a6cbc3d79d5f343fa0a`) → `KB/a26impl/out/b1.json` `43874cd17f3e55f6101b275f99d443639cba1154d8e05fe3b0a93549f3fc6bf9`] `B1 ok=True`.
- 옛 바이트 5개 → `KI/pre_a26/`(같은 상대 경로; `cgates.py`, `commit_k92.py`, `repo/…/sa/k92_gates.py`, `repo/…/sa/tests/test_k92_harness.py`, `commit_msgs/K9-2-0.txt`), 사본 sha = 옛 값 5/5.
- AD6 후보 4개 설치, sha = 보충 26 새 값 4/4: `cgates.py` `1fbe827f…8b17`, `commit_k92.py` `511fbf9e…b5a1`, 판정기 `9418d3e4…5acf`, 시험 `ae9741d9…5a2f`. `diff` [실행]: 구동기는 :184(D1)·:720(D2), 커밋 도구는 :191(D3) 한 줄씩만 다름.
- K9-2-0 메시지: 고정판 §3.7 코드 블록 네 줄을 파일에서 그대로 꺼내 `<A26SHA>` = `8f835616…ba37`로 바꾸어 끝 줄 앞에 넣음. 결과 sha256 `874e6a3f5af190ab00a4582ef381b9013f3a83b1aa354d61d4e1be9459394083`, 3,501 B = 고정점 값, `RV6/out/K9-2-0.expected.txt`와 바이트 같음. 첫 줄 = `G.SUBJECT['K9-2-0']`, 끝 줄 = Co-Authored-By(한 번), CR 0, `diff` = 네 줄 + 빈 줄 하나(:30-34 덧붙임).
- B1 통과 조건 모두 참.

## 2026-10-18 19:27 +0900 — Implement A26: B2 다시 점검, B3 구동기 고정 (보충 26 §6 B2·B3, §5)

- 시각 바로잡음: 바로 위 B1 항목 머리의 "19:28"은 잘못 적은 것이고 실제 B1 실행은 19:25 전후입니다(`date` 19:25:42에 B2 시작) [실행]. 내용은 그대로.
- B2 [실행 19:25:42–19:26:05 `python -B AD6/dry_a26.py static --src ki` → `AD6/dry/dry_a26_static_ki.json` `d9e545f952701121ed6a875d66e820f9b4f0d3d5042629e0e17a748dd01a6927` `ok=True D1=True D2=True D3=True GK5=True`; `python -B AD6/dry_a26.py pytest --src ki` → `AD6/dry/dry_a26_pytest_ki.json` `0b6f1b3c8407c9c55d3d848cc2e5035c9d113183b8e5f4a21bd9da1ae0d8a3e5`, 지금 판(`pre_a26` 판정기·시험) 16 passed, 설치 판 16 passed, 묶음 차이 2파일]. 비교 [실행 `KB/a26impl/b2_compare.py` `479a83f1…1274` → `out/b2.json` `499010a9…f3bf`]: `D1`·`D2`·`D3`·`GK5` 객체 = `dry_a26_static_cand.json`(정규 JSON), `base_set`·`new_set`·`set_diff` = `dry_a26_pytest_cand.json`, 두 시험 끝 줄 `16 passed`, AD6 선언 18파일 그대로. B2 통과 조건 모두 참.
- **B3 구동기 고정 (보충 26 §5)** — 첫 `commit_k92.py` 전, 커밋 관문 데이터 0개(`OK2/commit`·`OK2/sealed_s47` 없음). `KB/a26_pins.sha256` sha256 **`c9a9bbcab8f989d25bef4c71a1621bc59d02553d2ea7510f763741fb31cb1c47`**, **44줄**(보충 26 §5-2 표 순서, `<sha> *<절대 경로>`, LF). [실행 `sha256sum -c KB/a26_pins.sha256`] 44줄 모두 `OK`, 종료 0(`KB/a26impl/out/b3_check.txt`). 44개 값(= §5-2 값, K9-2-0 메시지 = 고정점 값):

```
1fbe827f3199e59bce18b49b1a955c0ffd753a8939b56719b1eebd255a138b17 *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/cgates.py
be5a0c95ad7bc86da55f6cf65b3804447ebce75cf4e829f6609e86d2a292b048 *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/cglib.py
511fbf9eeb0ab20a0680d78a61238658d5425e8965c699186db6dc4f3bbbf5a1 *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/commit_k92.py
ae5de0ccd90d688c0442eac2aeb35fec0aabd2abce4ba3ff75a637927fb998d9 *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/k92lib.py
96e9adad06683824bce61cb371dcd8b1571924262e0da83266b5ad72d37f8394 *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/p0_ref.py
e38e5e70ac2d9be8b0bf8f0f8ad9c2b808da904a6770b945cb4f8ed43c31adfb *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/patch_harness.py
271159b7b22060ff0ab45c24d26732c827b4796528c651bec91e3cc1ed8e9733 *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/patch_runtime.py
a490b90d492ade86f6aaddd320b1cf6ffc66c09e0305f3d4eec89d0bd46f9d92 *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/k920_edits.py
76893c7dc667195f70b425e3f32fd85071373a78b04718059dde64ded19fc10f *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/k923_edits.py
0dbd7d2c75f982d867eff46f27b1c2d8fbf34301d39952bdc87ebd7a0c8beeff *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/k92snap.py
bf7a81322086625d68b9df0961f9b00753fcf6ae499fa3aca5cad49b5d76ffff *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/launch.ps1
9418d3e4dbc3edfa46a60d4e273168f539cbc38dbb64aef85f9c63c3e6df5acf *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/repo/diagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_gates.py
ae9741d9abadf7609ff2fbee9c172e6d45e16ad0c192bebfd36eb626de5c5a2f *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/repo/diagnostics/sdmpc_n31_20260924/k8_gates/sa/tests/test_k92_harness.py
cb2a0335fefc94d7eca9be0cd0a6b5d870a35a15a21266b397b33e1bd181c012 *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/repo/diagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_common.py
1d1dfa36efbfa68e6ccc19cbeeb53f241437b1c5145e06fb843a9564661d4f90 *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/repo/diagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_record.py
f3fcc574d72f67ed8ad43cc94387fc3138fca1e81ab2d14ecfd9768338344efd *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/repo/diagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_vissim_ref.py
55df106bfa37a28e56047a489b9969e0c2779968ecda0830b63dbd38e75e104e *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/repo/diagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_compare.py
822dd78ffde70e07baebf83e948d72ed3f82ab71107920b02a05ee8783a1b965 *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/repo/diagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_replay.py
79827465ea72ca9206f260a9176d0efad6c65aa178981cd02f3de12b03e44337 *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/repo/diagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_cfgsnap/sitecustomize.py
0a74d8e969884b705fb6489832c2ea77c1e2430936249d9ef3aed6e2b4e63b1a *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/repo/diagnostics/sdmpc_n31_20260924/k92/build_k92_evidence.py
b190759a0685a5b209bbc1c2cc0297bf25645f28b09a98747fbd0cbc331ed610 *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/repo/diagnostics/sdmpc_n31_20260924/k92/README.md
ae31896b941d0dc07b5ceed7ad55dd7d29ab918b0abac4d3793615ab7b195fc1 *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/repo/diagnostics/sdmpc_n31_20260924/tests/test_k92_w.py
b0b16c5b7ac51d274a6a17e38630c014c1f98bff7fda2586c1f4b3d011eda1db *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/repo/diagnostics/sdmpc_n31_20260924/tests/test_k92_hb.py
3be7a36b6ca64db3a0f311f561a188b77d775ea44b27a7df122bca9d92e8b501 *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/stage_k921/diagnostics/sdmpc_n31_20260924/k92/build_k92_evidence.py
874e6a3f5af190ab00a4582ef381b9013f3a83b1aa354d61d4e1be9459394083 *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/commit_msgs/K9-2-0.txt
1db0ecf2472aff4ca5665e10f73b173c81bd8372b434861072acca5e8ddb01a3 *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/commit_msgs/K9-2-1.txt
00c9ec1345757efb1510655838d54deab32e09942a543c40133a9d59df36b835 *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/commit_msgs/K9-2-2.txt
94ba79859f15534bf6232bbf06824b98998f8513b56a4bb2e3fcfc9430c53b46 *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/impl/commit_msgs/K9-2-3.txt
78f954ec756c85789eef929ed628d46b626f7b2532c5ee0c657d01b62d46b7ec *D:/VISSIM-merge/k8_gate_trees/k92b1/a25/k92b1_probe.build.json
c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866 *D:/VISSIM-merge/k8_gate_trees/k92b1/a25/k92b1_probe/diagnostics/sdmpc_n31_20260924/config_n31_v2_k92b1.json
296c659562e45528606599aa4df99535faa694a86533ffca6bb2fbcde7db975a *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/k92_probe_a25/K92_VALUES.json
cf1ae3fbf659d97c2b855b4a72c944e1cba30c3a6ddbdbb34baa792bd8eb869f *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/k92_probe_a25/gk1_floor_names.json
af916995f9e3bfb049ebb34bd68e8ba5d261e9a892afaabca92ccc01b52fd021 *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/k92_probe_a25/K92_REF.json
e3ded96bbe14581fa6cfb5c387c51c4bb453c3aa983c0f8e7c1189bdef870c4d *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/k92_probe_a25/K92_PROBE_OUT.json
b4b7294df0369874ea53dd5f0538abd31bac1c946aebdf241bdc7837a7671712 *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/k92_probe_a25/p0/sc109w_through_saturation_v3b_u4_20261016.json
435bb673c43121ec40b796d31eac7f70f9ebc9d2b955cbfea289ffd3a682731c *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/k92_probe_a25/p0/inputs/u4_row_173_p3_v3b.json
b9fa1d01b9d922e9fc327793aa428cd7b544dae221044704dea7f0af610f20ee *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/k92_probe_a25/p0/head_floor_seed_v3c3_robs_20261016.json
6f151334028cf3f789570bcf5e1c706aa92db3fbbcb1167bc5cd3d739d2e9196 *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/k92_probe_a25/p0/report_arms/Wu.json
a82022fc051b0e9ff3bad0d02df5d26cdb1f1fe33b0a6b07070768addf03f923 *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/k92_probe_a25/p0/report_arms/Wj.json
e7a4c7e95ee260eeb3798bddca399905a52ad65daf58365468da1b9fdead38bd *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/k92_probe_a25/p0/report_arms/B1s.json
0482a53868fd3ee644724dab2dcb6af2c56d749708ccec5242f6b3549ae26f22 *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/j1/fix/gates/gprep.py
6ad45fd421c03f08716d71fdcdaf59491c4c1b6e5f238a9f43d4d7dd92b0f46b *C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/attrib/hook/sitecustomize.py
5d34109fdd61decaf3cbdd32c5b9d80a0768043d3c26fce83306f54144ce99c9 *D:/VISSIM-merge/frozen/sdmpc31_b9734abe_202610141821/diagnostics/sdmpc_n31_20260924/tools/replay_decision_n31.ps1
4adf41cfa7569047d87774bb648b353780fbb7ffc9b916a9c8f726e1d1de0714 *D:/VISSIM-merge/frozen/sdmpc31_b9734abe_202610141821/diagnostics/sdmpc_n31_20260924/tools/make_replay_state_v2.py
```

- 이후 `commit_k92.py`·`cgates.py`를 띄우기 전마다 `sha256sum -c KB/a26_pins.sha256`(44 OK·종료 0)와 이 파일 sha `c9a9bbca…1c47`를 대조하고 LOG에 적음(§5-4, S-K27).

## 2026-10-18 19:28 +0900 — B4: 커밋 K9-2-0 (보충 24 §4.1, 보충 26 §5-6)

- 발사 전 핀 대조 [실행 19:27, `sha256sum -c KB/a26_pins.sha256`]: 파일 sha `c9a9bbca…1c47`(= B3), 44/44 `OK`, 종료 0 (빈 돌리기 앞·커밋 앞 두 번; 출력 `KB/a26impl/out/pincheck_commit_K9-2-0.txt`).
- 빈 돌리기 [실행 `python -B KI/commit_k92.py K9-2-0 --dry-run` 19:27:44]: `FRONT_CHECK ok=true`(K8 브랜치 = b9734abe, status 0, 새 브랜치 없음), 기대 파일 15개(바뀜 7 + 새 8 = 보충 24 §4.1·보충 25 §8.1), `DRY RUN: no change`.
- 커밋 [실행 `python -B KI/commit_k92.py K9-2-0` 19:27:57–19:28:03]: 브랜치 `claude/k92-b1-20261016` 생성 at `b9734abe`, **K9-2-0 = `1868b37cada2f44028c303cff445872dfa0bd42a`**, `ok=True files=15`(파일마다 ls-tree 블롭 = `hash-object --no-filters`). 작성자 = 커밋터 = `Ming2you <alsrjsrb1915@snu.ac.kr>`, 부모 `b9734abe`, 메시지 = `KI/commit_msgs/K9-2-0.txt`(`874e6a3f…`, Co-Authored-By 끝 줄).
- 확인 [실행]: 판정기 `SA/k92_gates.py` 블롭 `2d907dca0ddc130057b0b5330242f86c67cc7d76`, 시험 `SA/tests/test_k92_harness.py` 블롭 `9a8a5e3ab065232ec338708f278177ce83a525de`(= 보충 26 §5-6, S-K28 아님), VR 블롭 `1f351efd…`(= 보충 25 §8.1). K8 브랜치 = `b9734abe` 그대로, `status --porcelain` 0줄, `b9734abe..HEAD` 이름 15개. 푸시 0.
- 기록: `OK2/commit/commits.json`, `OK2/commit/K9-2-0/k920_blobs.json`(판정기 블롭 15개; 이후 커밋 관문의 S-K12 대조 기준), `OK2/commit/commit_log.txt`.

## 2026-10-18 19:31 +0900 — B4: K9-2-0 관문 발사

- 발사 전 핀 대조 [실행 19:28]: `c9a9bbca…1c47`, 44/44 OK, 종료 0(`KB/a26impl/out/pincheck_cg_K9-2-0.txt`). C: 34 GB, D: 540 GB.
- [실행 `KI/launch.ps1 -Tag cg_K9-2-0 -Script cgates.py -ArgLine K9-2-0`, WMI PID 9608(cmd), 19:28:43, 그때 VISSIM 0·python 0, BelowNormal] 단계 = pre, trees, diff0, pycompile, selftest, jb, U, gk0_plant, after. 표준 출력 `OK2/logs/cg_K9-2-0.txt`.
- 대기 도구 `KB/a26impl/waitstat.ps1`(sha256 아래 줄): 프로세스 유무·python·VISSIM 개수·파일 `stat`만 봄(보충 25 §6.3-6, 내용 읽기 0).
- waitstat.ps1 sha256 1bc886e9c53018f24025c71b7beb31ad08735b4667b43382894e530107db0cca
- [2026-10-18 23:43 +0900] 커밋 관문 끝(cgates.py, 자동 기록): K9-2-0 모든 선언 관문 PASS — pre=PASS, trees=PASS, diff0=PASS, pycompile=PASS, selftest=PASS, jb=PASS, U=PASS, gk0_plant=PASS. 판정 파일 `D:\VISSIM_runs\20261001_v3c3\reports\k8\k92_b1\commit\K9-2-0\gates.json` sha256 `04a5f3161a9a77c44ccc8860e96d3c414f9e6909a80428353fa415f0b6374a16`.

## 2026-10-18 23:47 +0900 — B4: K9-2-0 관문 끝 (모두 PASS)

- [실행 WMI PID 9608, 19:28:43–23:43:20; 대기는 프로세스 유무·`stat`만] `CGATES_DONE K9-2-0`. `OK2/commit/K9-2-0/gates.json` sha256 `04a5f3161a9a77c44ccc8860e96d3c414f9e6909a80428353fa415f0b6374a16`: pre·trees·diff0·pycompile·selftest·jb·U·gk0_plant·after 모두 PASS.
- 요약(판정 파일에서, 값 0): diff0 = 경로 15개·선언 밖 0·`evaluation vendor plant scripts` 차이 0 B. pycompile 14파일. 자기 시험 `selftest.json` 10사례·§3.1-3b 5·J-b 계산기 sha 5·자식 프로세스 0. jb 계산기 5파일 블롭 = b9734abe. U: 기존 256(b9734abe 쪽)·새 트리 272(= 256 + 새 16), `differ` 0·`only_base` 0·`other_new` 0·`new_bad` 0, 알려진 실패 같음, `test_sa_harness.py` 바뀐 줄 = `gates_stage=`·`declaration_sha` 인자 줄 4쌍(단언 줄 0). G-K0 plant: P-a 26행 PASS, P-b 17행 PASS(K9-1 G5 규칙, 허용 0), `b9_pl` 대 FRZ_K8b 차이 0.
- 봉인 실행 5건(`OK2/commit/K9-2-0/sealed_s47_index.json` `a3ea2976…78fb`): plant base rc 0(6,955 s), new Pa rc 0(6,430 s), new Pb rc 0(484 s), 판정 두 건 rc 0. 봉인 로그는 열지 않음(이름·크기·시각만).
- 판정 파일 sha [실행]: U `dc88fdab…`, diff0 `f52bc1e8…`, pycompile `0e9176ed…`, selftest `d575a16c…`, jb `71a6b42b…`, trees `a401ba34…`, gk0_plant `24cbbded…`(Pa raw `50c84bf5…`, Pb raw `d617a9ec…`), after `df4ee1ea…`.
- 스냅숏 [실행 `KI/k92snap.py take OK2/snap/s08_K9-2-0_gates.json`] `9bdba23b…fc16`, s02 대비 `SAME`. GWT8 status 0줄, HEAD = K9-2-0 `1868b37c`. C: 35 GB, D: 527 GB. python·VISSIM 0.

## 2026-10-18 23:45 +0900 — B4: 커밋 K9-2-1

- 시각 바로잡음: 바로 위 "23:47" 항목은 실제로 23:44 전후에 적었습니다(내용 그대로).
- 발사 전 핀 대조 [실행 23:45, 두 번]: `c9a9bbca…1c47`, 44/44 OK, 종료 0(`KB/a26impl/out/pincheck_commit_K9-2-1.txt`).
- 빈 돌리기 [실행 23:45:00] `FRONT_CHECK ok=true`(K8 브랜치 = b9734abe, status 0, 브랜치 커밋 = [K9-2-0 `1868b37c`]), 기대 5파일.
- 커밋 [실행 `python -B KI/commit_k92.py K9-2-1` 23:45:14–23:45:17]: **K9-2-1 = `7ed49cdfb548a0b82a8615f59a6650869de7c908`**, 부모 `1868b37c`, `ok=True files=5`. 작성자 = 커밋터 = Ming2you. 메시지 = `KI/commit_msgs/K9-2-1.txt`(`1db0ecf2…`).
- 파일·블롭 [실행 `rev-parse HEAD:<경로>` = `hash-object --no-filters`]: RS `a21fd7c0…`(sha256 앞 `1ab45c03f67fb108`, w 패치), 빌더(w) `0363cd84…`, 입력 행 `75cd34b6…`, W 증거 `0399c369…`, `tests/test_k92_w.py` `5f81a4e1…` — 빌더·입력 행·증거·시험 블롭 = 보충 25 §8.1. status 0줄, K8 브랜치 = b9734abe. 푸시 0.
- K9-2-1 관문 발사 [실행 23:45, 핀 대조 44/44 OK·종료 0(`out/pincheck_cg_K9-2-1.txt`); `KI/launch.ps1 -Tag cg_K9-2-1 -Script cgates.py -ArgLine K9-2-1`, WMI PID 21200(cmd), 23:45:38, VISSIM 0·python 0, BelowNormal]. 단계 = pre, trees, U, B, gk0_dec, gk0_plant, gk1_static, gk1_dyn, gk2, gk4, gk5, after. 표준 출력 `OK2/logs/cg_K9-2-1.txt`.
- [2026-10-18 23:47 +0900] K9-2-1 커밋 트리 사본용 보고 팔 증거를 커밋 증거에서 같은 도구(p0_ref.py report_arms, 고치지 않고 불러 씀)로 다시 만듦(cgates.py, 자동 기록), 계산 전 고정: Wu `6f151334028cf3f789570bcf5e1c706aa92db3fbbcb1167bc5cd3d739d2e9196`, Wj `a82022fc051b0e9ff3bad0d02df5d26cdb1f1fe33b0a6b07070768addf03f923`, B1s `e7a4c7e95ee260eeb3798bddca399905a52ad65daf58365468da1b9fdead38bd`. 탐침판과 values 같음 True, 바이트 같음 True.
- [2026-10-19 15:27 +0900] 커밋 관문 끝(cgates.py, 자동 기록): K9-2-1 모든 선언 관문 PASS — pre=PASS, trees=PASS, U=PASS, B=PASS, gk0_dec=PASS, gk0_plant=PASS, gk1_static=PASS, gk1_dyn=PASS, gk2=PASS, gk4=PASS, gk5=PASS. 판정 파일 `D:\VISSIM_runs\20261001_v3c3\reports\k8\k92_b1\commit\K9-2-1\gates.json` sha256 `dbf644937010c510a7a2de7336246ae0c1b78219192033e3d548d0a20c98aa24`.

## 2026-10-19 15:28 +0900 — B4: K9-2-1 관문 끝 (모두 PASS), S-K29 확인

- [실행 WMI PID 21200, 2026-10-18 23:45:38 – 2026-10-19 15:27:02; 대기는 프로세스 유무·`stat`만] `CGATES_DONE K9-2-1`. `OK2/commit/K9-2-1/gates.json` sha256 `dbf644937010c510a7a2de7336246ae0c1b78219192033e3d548d0a20c98aa24`: pre·trees·U·B·gk0_dec·gk0_plant·gk1_static·gk1_dyn·gk2·gk4·gk5·after 모두 PASS.
- 요약(판정 파일에서, 모형 값 0): trees — D1 고친 줄로 팔 t74_W·t9b_W·(보고) t74_Wu·t9b_Wu가 TKA 기록과 같아 통과, 보고 팔 다시 만들기 Wu·Wj·B1s 바이트 = KPA(자동 기록 줄). U 기존 256·새 279(= 256 + 하네스 16 + W 7), `differ`·`new_bad`·`only_base`·`other_new` 0. B(w) PASS(`bad` 0). G-K0 결정 79칸 PASS, GWT8 겨눔 앞뒤 참. G-K0 plant P-a 26·P-b 17 PASS. G-K1 정적 79/79 PASS, 동적 26/26 PASS. G-K2 (a) S1–S4 W 대 `OK2A/ref/S*_CWf`: HARD SAME 4/4(전체 비교 칸 `verdict_full`은 HOLD·미분류 198/396 — 선언 통과 조건은 HARD뿐, 보고만). G-K2 (e) Wu 대 `DA/runs/S*_CW`: 4/4 SAME(첫 차이 없음). G-K4: 결정 S1–S4 4행 + plant 2잡 PASS(6/6).
- **G-K5 (보충 26 판정기)**: `verdict` PASS, **`n_rows` 8, `n_clean` 8 → S-K29 아님**, 중앙 0.9899949870786262(문턱 1.0157507938976496), 사분위 범위(inclusive) 0.0151879536894437 — 0.006 참고선 넘음(`iqr_over_reference` 참, `iqr_report_only` 참; 보고만). `CANNOT_TELL` 없음(S-K28 아님). 짝 비(B/A, 벽시계 초): S1 0.98512·0.98618, S2 0.99834·0.99900, S3 0.97793·0.99381, S4 0.97453·1.00628. 최댓값 1.00628(S4 둘째 짝). 짝 원자료 `OK2/commit/K9-2-1/gk5/wall_pairs.json`.
- 봉인 실행 9건 모두 rc 0(`sealed_s47_index.json`; 열지 않음).
- 판정 파일 sha256 앞 16자 [실행]: U `637c3126a4a167a4`, B `9a6a9d19b40c49b0`, trees `bca39d5082fdd499`, gk0_dec `79e1ea611955f158`, gk0_plant `7e8c617968fe1d20`, gk1_static `06db232345ff8421`, gk1_dyn `43b32b54b4a497ff`, gk2 `85003f6b61da0121`, gk4 `8f635d6b738fccfd`, gk5 `7707a33265ac2fa0`, after `c0497bd9a7e2b4d6`, wall_pairs `5359dc5b965ac663`.
- 스냅숏 s09 `OK2/snap/s09_K9-2-1_gates.json`(`df083983faf59721…`) s02 대비 SAME. GWT8 HEAD = K9-2-1 `7ed49cdf`, status 0줄. C: 35 GB, D: 485 GB. python·VISSIM 0.

## 2026-10-19 15:29 +0900 — B4: 커밋 K9-2-2

- 발사 전 핀 대조 [실행 15:29, 두 번]: `c9a9bbca…1c47`, 44/44 OK, 종료 0(`out/pincheck_commit_K9-2-2.txt`).
- 빈 돌리기 [실행 15:29:06] `FRONT_CHECK ok=true`(브랜치 커밋 = [K9-2-0 `1868b37c`, K9-2-1 `7ed49cdf`]), 기대 5파일(RS `70cca680…`·SHO `a6b5931e…` = 탐침 트리 바이트, 빌더 전체 `0a74d8e9…`, H-b 증거 `b9fa1d01…`, 시험 `b0b16c5b…`).
- 커밋 [실행 `python -B KI/commit_k92.py K9-2-2` 15:29:17–15:29:20]: **K9-2-2 = `2d5d95f05f83b06f841ac4f3ace46056f9ba3b2b`**, 부모 `7ed49cdf`, `ok=True files=5`. 작성자 = 커밋터 = Ming2you, 메시지 = `KI/commit_msgs/K9-2-2.txt`(`00c9ec13…`).
- 블롭 [실행 `rev-parse HEAD:<경로>` = `hash-object --no-filters`]: RS `bcf7a777…`, SHO `37076a29…`, 빌더 `3c17712b…`(= 보충 25 §8.1), H-b 증거 `6ed42f16…`, `tests/test_k92_hb.py` `9dca3de5…`(= 보충 25 §8.1). status 0줄, K8 브랜치 = b9734abe. 푸시 0.
- K9-2-2 관문 발사 [실행 15:29, 핀 대조 44/44 OK·종료 0(`out/pincheck_cg_K9-2-2.txt`); `KI/launch.ps1 -Tag cg_K9-2-2 -Script cgates.py -ArgLine K9-2-2`, WMI PID 5504(cmd), 15:29:41, VISSIM 0·python 0, BelowNormal]. 단계 = pre, trees, U, B, gk0_dec, gk0_plant, gk1_static, gk1_dyn, gk2, gk3, gk4, gk5, after. 표준 출력 `OK2/logs/cg_K9-2-2.txt`.
- [2026-10-19 15:31 +0900] K9-2-2 커밋 트리 사본용 보고 팔 증거를 커밋 증거에서 같은 도구(p0_ref.py report_arms, 고치지 않고 불러 씀)로 다시 만듦(cgates.py, 자동 기록), 계산 전 고정: Wu `6f151334028cf3f789570bcf5e1c706aa92db3fbbcb1167bc5cd3d739d2e9196`, Wj `a82022fc051b0e9ff3bad0d02df5d26cdb1f1fe33b0a6b07070768addf03f923`, B1s `e7a4c7e95ee260eeb3798bddca399905a52ad65daf58365468da1b9fdead38bd`. 탐침판과 values 같음 True, 바이트 같음 True.
- [2026-10-20 06:45 +0900] 커밋 관문 끝(cgates.py, 자동 기록): K9-2-2 모든 선언 관문 PASS — pre=PASS, trees=PASS, U=PASS, B=PASS, gk0_dec=PASS, gk0_plant=PASS, gk1_static=PASS, gk1_dyn=PASS, gk2=PASS, gk3=PASS, gk4=PASS, gk5=PASS. 판정 파일 `D:\VISSIM_runs\20261001_v3c3\reports\k8\k92_b1\commit\K9-2-2\gates.json` sha256 `176dd263eb38b132e0b25ac18b86aa9ad73c5c65aa04c7f4f709f4a72f73420e`.

## 2026-10-20 06:47 +0900 — B4: K9-2-2 관문 끝 (모두 PASS), S-K29 확인

- [실행 WMI PID 5504, 2026-10-19 15:29:41 – 2026-10-20 06:45:19; 대기는 프로세스 유무·`stat`만] `CGATES_DONE`. `OK2/commit/K9-2-2/gates.json` sha256 `176dd263eb38b132e0b25ac18b86aa9ad73c5c65aa04c7f4f709f4a72f73420e`: pre·trees·U·B·gk0_dec·gk0_plant·gk1_static·gk1_dyn·gk2·gk3·gk4·gk5·after 모두 PASS.
- 요약(판정 파일에서, 모형 값 0): trees — D1 고친 줄로 t74_B1·t9b_B1·(보고) t74_B1s·t74_Xu가 TKA 기록과 같아 통과, 보고 팔 Wu·Wj·B1s 바이트 = KPA. U 기존 256·새 288(= 256 + 하네스 16 + W 7 + H-b 9), 다름 0. B(hb, `--root u_b9_k922`) rc 0, `K92_EVIDENCE_CHECK_OK hb`, 커밋 증거 = `b9fa1d01…`. G-K0 결정 79, plant P-a 26·P-b 17 PASS. G-K1 정적 79/79 PASS(씨앗 묶임 행 12), 동적 26/26 PASS. G-K2 (b) S1·S2·S4 대 `S*_CWf`, S3 대 탐침 `S3_B1`: HARD SAME 4/4. (c) S3 B1s 대 `S3_X1f`: HARD SAME, 선언된 H5 한 건 `/metadata/head_discharge_floor_173_p4_301ceabb95f116fa`(존재; 키 이름 = P0-2 (f) v3c3-s41 기대 이름). 전체 비교 칸 `verdict_full` HOLD(미분류 198/396; 보고만). (e) Xu 대 `DA/runs/S3_X1`: SAME(첫 차이 없음). G-K3 6점검 참(씨앗만 ValueError, 하네스 거부, `sa_arms --k92b1` 두 키, SAF 팔 두 경로·값, CFG 바탕, CFG 팔 두 경로·값). G-K4 6/6 PASS.
- **G-K5**: PASS, **`n_rows` 8, `n_clean` 8 → S-K29 아님**, 중앙 0.995050862095435(문턱 1.0157507938976496), 사분위 범위 0.009583768023486705 — 0.006 참고선 넘음(보고만). `CANNOT_TELL` 없음. 짝 비: S1 0.99895·0.99069, S2 0.98880·0.99819, S3 1.02941·1.00235, S4 0.98204·0.99192. 최댓값 1.02941(S3 첫 짝, 보고만).
- 봉인 실행 9건 모두 rc 0(열지 않음; 구동기 `SEALED_S47` 줄 9개, rc≠0 0개).
- 판정 파일 sha256 앞 16자: U `1e1350f45c8836c3`, B `062966fc96c6dea8`, trees `4e3814b7b1346479`, gk0_dec `49c46f31fe0342d8`, gk0_plant `6010ba42f0855498`, gk1_static `c2234e0a9a3f1dcf`, gk1_dyn `8245a00b7ffcd729`, gk2 `82034200829ae799`, gk3 `5a32671d201fdc0f`, gk4 `03d8ff5a5bf10ba8`, gk5 `32ce53b60badc424`, after `b66714e3cd839276`, wall_pairs `63b0895bae42ab85`, sealed index `447de9aaab3c320d`.
- 스냅숏 s10 `OK2/snap/s10_K9-2-2_gates.json`(`06b0c330…`) s02 대비 SAME. GWT8 HEAD = K9-2-2 `2d5d95f0`, status 0줄. C: 38 GB, D: 443 GB. python·VISSIM 0.

## 2026-10-20 06:47 +0900 — B4: WORKLOG 스테이징 (보충 26 §5-5)

- K9-2-2 관문 PASS 뒤, K9-2-3 커밋 전. 초안 `KB/a26impl/WORKLOG_20261016.draft.md`를 `KI/repo/diagnostics/sdmpc_n31_20260924/k92/WORKLOG_20261016.md`로 복사(`cmp` 같음) [실행].
- **WORKLOG sha256 `d58ce98424091ff1869656bcd0b7d27377e7c8fdee578a8622eafb50a9ee9fba`**, 4,634 B, git 블롭(`hash-object --no-filters`) `c7cd52b9df30196f9f33c339970322bdfcc5b720`, CR 0, UTF-8. 판정에 쓰지 않음. 스테이징 파일 = 고정 12 + 이 파일 1 + `stage_k921` 1 = 14(다른 새 스테이징 파일 0).
- 내용: 근거 sha·순서(탐침 두 번, 보충 25·26, 커밋 K9-2-0…3과 관문 요약)·공개 사항(G-K2 `verdict_full` HOLD 보고만, G-K5 사분위 범위 보고만·짝 8/8, 봉인 뿌리, D-K9-44 해시 계산)·남은 일. 모형 값·s47 값 0.

## 2026-10-20 06:48 +0900 — B4: 커밋 K9-2-3

- 발사 전 핀 대조 [실행 06:47·06:48]: `c9a9bbca…1c47`, 44/44 OK, 종료 0(`out/pincheck_commit_K9-2-3.txt`).
- 빈 돌리기 [실행 06:47:50] `FRONT_CHECK ok=true`(브랜치 커밋 = K9-2-0·1·2), 기대 4파일: `make_config_n31.py` `b707869a…`, README `b190759a…`, WORKLOG `d58ce984…`, 팔 `config_n31_v2_k92b1.json` `c8e3ee2c…`(D3 고친 줄로 PTA에서 읽음; 옛 줄이면 여기서 멈췄을 자리).
- 커밋 [실행 `python -B KI/commit_k92.py K9-2-3` 06:48:03–06:48:06]: GWT8에서 `make_config_n31.py --k92b1` rc 0(`CONFIG_N31_K92B1_OK family=single_value sha256=c8e3ee2c…`), **K9-2-3 = `b887f99f2f8441b6aa88c8633dff778c0fade91e`**, 부모 `2d5d95f0`, `ok=True files=4`. 작성자 = 커밋터 = Ming2you, 메시지 = `KI/commit_msgs/K9-2-3.txt`(`94ba7985…`).
- 블롭 [실행 `rev-parse HEAD:<경로>` = `hash-object --no-filters`]: `make_config_n31.py` `26b6252d…`, README `7a733537…`(= 보충 25 §8.1), WORKLOG `c7cd52b9…`, 팔 `b6ccd50d…`(= 보충 25 §8.1). status 0줄, K8 브랜치 = b9734abe. 푸시 0.
- K9-2-3 관문 발사 [실행 06:48, 핀 대조 44/44 OK·종료 0(`out/pincheck_cg_K9-2-3.txt`); `KI/launch.ps1 -Tag cg_K9-2-3 -Script cgates.py -ArgLine K9-2-3`, WMI PID 2432(cmd), 06:48:26, VISSIM 0·python 0, BelowNormal]. 단계 = pre, trees, gk0_dec(D-d 4칸), gk0_plant(P-b), gk3(팔 동일성·`--check` 포함), after. 표준 출력 `OK2/logs/cg_K9-2-3.txt`.
- [2026-10-20 08:03 +0900] 커밋 관문 끝(cgates.py, 자동 기록): K9-2-3 모든 선언 관문 PASS — pre=PASS, trees=PASS, gk0_dec=PASS, gk0_plant=PASS, gk3=PASS. 판정 파일 `D:\VISSIM_runs\20261001_v3c3\reports\k8\k92_b1\commit\K9-2-3\gates.json` sha256 `064d1b4b62748d648e2379ace9cf89e5a0f210281724b77c01b59eb957906d71`.

## 2026-10-20 08:05 +0900 — B4: K9-2-3 관문 끝 (모두 PASS), 마무리 확인

- [실행 WMI PID 2432, 06:48:26–08:03:22; 대기는 프로세스 유무·`stat`만] `CGATES_DONE K9-2-3`. `OK2/commit/K9-2-3/gates.json` sha256 `064d1b4b62748d648e2379ace9cf89e5a0f210281724b77c01b59eb957906d71`: pre·trees·gk0_dec·gk0_plant·gk3·after 모두 PASS.
- 요약: G-K0 결정 D-d S1–S4 4칸 PASS(겨눔 앞뒤 참), plant P-b 17 PASS(봉인 실행 3건 rc 0). G-K3 7점검 참(K9-2-2의 6점검 + `cfg_arm_committed`). 팔 동일성 3점검 참(SAF 팔 = 탐침 t74_B1, CFG 팔 = 탐침 t9b_B1, `make_config_n31.py --k92b1 --check` rc 0 `CONFIG_N31_K92B1_OK … sha256=c8e3ee2c…`). 판정 파일 sha 앞 16자: gk0_dec `ef91820820b212ac`, gk0_plant `a2d2e8358afeee96`(Pb raw `45132e5e6e48b9d2`), gk3 `f63c32cfe3500daf`, trees `a37dc58489aa07f8`, after `03a1c32bf7b971f9`.
- **S-K27 창 끝(K9-2-3 `after` PASS) 핀 대조** [실행 08:0x `sha256sum -c KB/a26_pins.sha256`]: 파일 sha `c9a9bbca…1c47`(= B3), 44/44 OK, 종료 0(`out/pincheck_final.txt`). B3 뒤 고정 목록 바이트 변경 0.
- GWT8 [실행]: `b9734abe..claude/k92-b1-20261016` = K9-2-0 `1868b37c` → K9-2-1 `7ed49cdf` → K9-2-2 `2d5d95f0` → K9-2-3 `b887f99f`(작성자·커밋터 모두 Ming2you, 메시지 끝 줄 Co-Authored-By 한 번씩). HEAD = `b887f99f`, 지금 브랜치 = `claude/k92-b1-20261016`, K8 브랜치 = `b9734abe` 그대로. `status --porcelain` 0줄(무시 파일 포함·캐시 빼고도 0줄). 바뀐 파일 27개 모두 `rev-parse HEAD:<경로>` = `hash-object --no-filters`. 원격 추적 참조 없음, 상류 없음 → 푸시 0. 접선 캐시 135개(시작과 같음).
- `OK2/commit/commits.json` sha256 `081fd0db2cdab2044e926cd8426acdefa49471ee2bf81a9d55f2a5953ae772b3`.
- 스냅숏 s11 `OK2/snap/s11_final.json`(`7b0e86cd9afc3812…`) s02 대비 SAME. python·VISSIM·cscript 0. C: 38 GB, D: 438 GB.
- 결과: 커밋 4개 모두 있음, 커밋별 선언 관문 모두 PASS, S-K29 두 번 모두 8/8, STOP 0. 판정 단계 k92t·독립 검증·V-B·V-A는 하지 않음(이 워크플로 밖).

## 2026-10-20 08:06 +0900 — 셋째 시도 끝: IMPLEMENT.md 덧붙임

- `KB/IMPLEMENT.md`에 셋째 시도 절을 덧붙임(앞 24,994 B = `8fcc6a94…8b03` 그대로) [실행]: 전체 sha256 `a1f3681e1c135ce16f02b51ecf2965dac27907272ecb3041b1525825716bf7cb`(35,104 B, CR 0). 덧붙인 원문 사본 `KB/a26impl/implement_attempt3_section.md` `51df65dd0f764c592d5d0ef2079991376d9e2c2a59d65a713375951f59e9a83f`(파일 끝과 `cmp` 같음).
- 공개: 첫 발사 전 핀 대조(K9-2-0 빈 돌리기 앞)의 출력은 스크래치 대신 Git Bash `/tmp/pc.txt`에 썼습니다(44줄 OK, 종료 0). 그 뒤 대조 출력은 모두 `KB/a26impl/out/pincheck_*.txt`.
- 결과: K9-2-0 `1868b37c`, K9-2-1 `7ed49cdf`, K9-2-2 `2d5d95f0`, K9-2-3 `b887f99f` — 커밋별 선언 관문 모두 PASS, GWT8 status 0줄, 푸시 0. 다음 단계(k92t·독립 검증·V-B)와 V-A(사용자 결정)는 이 워크플로 밖.

## 2026-10-20 08:40 +0900 — VerifyImpl r1: 구현 독립 검증 (결함 1건 D-1 → STOP, 사용자 결정)

- 고정점 [실행]: 보충 24 `d46db6dc…`·25 `4fd7b599…`·26 `8f835616…`·결정 기록 `e15ae943…` = 기록 값. `KB/a26_pins.sha256` `c9a9bbca…` 44/44 OK.
- 결과 문서 `KB/VERIFY_IMPL_r1.md` sha256 `8ff723eb6f570691cd7730abca83fbe7647f51dfceb976d785e1f88d1ea2a9f7`. 도구·출력 `KB/vimpl_r1/`(sha는 문서 §6).
- D-1: G-K2 (a)(b)(c) 9칸이 보충 21 §6.4 결과 규칙(보충 24 §4.2 "결과 넷", §6 FIX_INTEGRITY, S-K4·S-K6b)으로는 모두 보류(`verdict_full` HOLD, 미분류 D5 198/396). 판정기 `k92_gates.py:31`·구동기 `cgates.py:672-674`는 HARD만 판정. 원인 진단(판정 아님): N 뿌리 규칙 깊이(`k92_compare.py:40`), CR만 다른 소스 3개(`TK/cr_only_files.json`). 고칠 길 (가) 보충 27로 HARD만 판정을 소급 확정 + 공개, (나) 보충 27로 N·CR 규칙 고정 뒤 G-K2 9칸 재생·전체 판정. S-K12라 사용자 결정 뒤에만.
- 문제를 찾지 못한 점검: 선언 덩어리, 키 끔 길(무작위 4,000사례 차이 0, G-K0 전체 PASS), 키 켬 범위(G-K1 스냅숏 79×2 재확인), 씨앗 repr, 묶기 규칙, 새 시험(망가뜨린 구현 10/11 잡음, 빈 곳 O-1), 커밋 위생, 푸시 0(`ls-remote` 읽기 한 번).
- 한 일: 스크래치 트리 `TK/vimpl_r1`(git archive b887f99f 일부, 186 MB) 만들고 새 시험 2파일·망가뜨린 구현 시험 실행(끝에 RS·SHO 바이트 = 커밋 블롭 확인). 기존 출력 비교만 함. VISSIM·COM·러너·동결·재생·plant 잡·커밋·푸시 0. GWT8·동결본·런 폴더·k92attrib·KI·KPA·OK2 쓰기 0. 봉인 시드·v3c3-s47 파일 열람 0. 금지 시험 0. C: 38 GB, D: 438 GB.

## 2026-10-20 08:43 +0900 — FixImpl r1: D-1은 보충 24 안에서 고칠 수 없음 → STOP (커밋 0, 사용자 결정)

- 고정점 [실행]: 보충 24 `d46db6dc…`·25 `4fd7b599…`·26 `8f835616…`·결정 기록 `e15ae943…`(147줄, D-1 관련 새 결정 없음)·`VERIFY_IMPL_r1.md` `8ff723eb…` = 기록 값.
- D-1 다시 확인 [읽음·실행]: 판정기 `k92_gates.py:31`(`9418d3e4…`) "G-K2 = hard_verdict SAME", 구동기 `KI/cgates.py:672-674`(`1fbe827f…`) `ok = ok and r["hard_verdict"] == "SAME"`. `OK2C/K9-2-1/gates/gk2.json`(`85003f6b…`) S1–S4_W, `OK2C/K9-2-2/gates/gk2.json`(`82034200…`) S1·S2·S4_B1·S3_B1·S3_B1s = 9칸 모두 hard SAME·full HOLD(미분류 198/396), 묶음 verdict PASS. 비교기 `k92_compare.py:503-504` HOLD 규칙, `:40` 뿌리 규칙 한 단계.
- 선언 [읽음]: 보충 24 :269(결과 넷), :272(A_K92-M 이유 "G-K2 … 보류(→ STOP)"), :362 FIX_INTEGRITY("G-K2 (a)(b)(c) 중 FAIL·보류" → STOP → 사용자 결정 → 보충 → 고친 커밋 → 관문 처음부터), :389 S-K4, :392 S-K6b, 보충 21 :265-271. 다만 보충 24 :287 G-K2 통과 칸 글자는 "(a)(b)(c): §4.2 HARD 같음"이라 두 읽기가 맞섬 — 어느 읽기인지 정하는 것도 데이터 뒤 정의 문제.
- 고칠 수 없는 이유 [추론]: (1) 판정기를 선언대로(전체 결과) 고치면 데이터 뒤 판정기 변경(S-K12)이고, 고정 비교기로도 결과가 보류라 §6에 따라 STOP. (2) 뿌리 정규화·CR 트리 규칙을 고치고 9칸 재생은 판정 규칙·절차 변경(보충 27 필요). (3) "HARD만"을 소급 확정도 보충 27. 과제 규칙 "보충 변경이나 데이터 뒤 판정기 변경이 필요하면 STOP"에 해당.
- 관찰 O-1·O-4·O-5 등은 검증 문서가 결함 아님으로 분류. O-4(G-K4 판정기가 HARD 수치만 봄)도 D-1과 같은 꼴이라, 사용자가 D-1을 정할 때 함께 정할 항목으로 적음.
- 한 일: 읽기·세기만. GWT8 머리 `b887f99f`(claude/k92-b1-20261016), K8 브랜치 `b9734abe`, status 0줄 [실행]. 커밋·브랜치·푸시 0. VISSIM·COM·러너·동결·재생·plant 잡 0. 판정기·구동기·관문 산출 쓰기 0. 봉인 시드·v3c3-s47 열람 0. 금지 시험 0. C: 37.9 GB, D: 437.1 GB.

## 2026-10-20 09:50 +0900 — Declare A27: 보충 27 작성 (D-K9-49·D-K9-50)

- 근거 [실행 sha]: 결정 기록 `SP/K9_1_J1_NOTES_20261013.md` `2299bcb6…caa9`(155줄), `KB/VERIFY_IMPL_r1.md` `8ff723eb…a2f7`, 보충 24 `d46db6dc…`·25 `4fd7b599…`·26 `8f835616…`(고정점 sha 모두 기록 값과 같음), `KB/a26_pins.sha256` 44/44 OK. 이 항목 덧붙임 전 LOG `65aed126…b71c`(94,304 B).
- **보충 27 Declare 판** `SP/K8_PREDECLARATION_AMENDMENT_27.md` sha256 `c7146e6ec814f78304d79296429cca023a2f90714bae894b5d27820900295192`(66,935 B, 525줄, CR 0) = `SP/K8_PREDECLARATION_AMENDMENT_27.md.sha256`. 고정점 `KB/AMENDMENT27_FIXED.md`는 반박 검토가 씀(아직 없음).
- 내용: (1) N에 K9-2 트리 뿌리 규칙 하나(`k8_gate_trees/(?:k92b1/(?:a25/|a26decl/|a27/)?|k92attrib/)[a-z0-9_]+` → `<root>`, 옛 한 단계 규칙 앞)와 트리 자리 닫힌 목록, (2) CR 짝 규칙 R-CR(두 쪽 트리의 L 10파일 형태가 같음; 기준이 커밋 바이트면 `cglib.apply_cr_fix`로 고침, 기준이 고치지 않은 보관 사본이면 고치지 않음), (3) 새 판정기 커밋 K9-2-4(SA 4파일, 런타임 0)와 관문 R0–R7(R-old: 옛 출력 184쌍을 옛·새 비교기로 다시 비교), (4) G-K2 (a)(b)(c) 9칸 다시 재생(트리 9개, (b) S3만 보관 형태)과 결과 넷 판정, (5) G-K4 결정 8행 옛 출력으로 모든 차이 + plant 4행 그대로, (6) J·VB-I1·독립 검증에 같은 규칙, (7) 보충 24 :287 대 :269·:272·:362·:389·:392 충돌을 결과 넷 쪽으로, (8) HARD만 판정했던 사실 공개.
- **먼저 알림(예측, 판정 아님)**: VERIFY_IMPL_r1 O-4 진단(`gk4_full_diag.out.json` `2224f97d…`)대로면 G-K4 W 4행은 D5 `runtime_setup.py`의 `A_K92 condition false`(탐침 W 트리 RS `70cca680…` = W+H-b 최종판, A_K92 옛 값 목록 밖)로 보류 → RJ-G4에서 STOP할 것으로 봄. D-K9-50 "허용 차이는 선언대로"라 보충 27은 허용 목록을 넓히지 않음. 그 뒤 처리는 사용자 결정.
- 후보·도구 [실행] AD7 = `KB/a27decl`: `rj27.py` `365ce310…a8fa8`, `dry_a27.py` `641368b3…0c34`, `make_a27_cands.py` `0ad471a9…cb68`, `A27_CANDIDATES.diff` `f3ae820c…cc8d`. 커밋 후보: `k92_compare.py` `94f31635…3ed4`(블롭 `0bffbaf5…`), `k92_gates.py` `7b19f7f3…53bd`(블롭 `01ce99d3…`), 새 `k92_a27.py` `6458b74f…3b7d`(블롭 `eb51c0a8…`), 새 `tests/test_k92_a27.py` `18d0cf56…e33e`(블롭 `e9b4245d…`). 메시지 틀 `cand/commit_msgs/K9-2-4.txt` `1895e59e…a5a9`(1,446 B, `<A27SHA>` 한 곳).
- 데이터 없는 확인 [실행]: `dry_a27.py static` ok(`dry/dry_a27_static.json` `f51f435d…682e`; 다시 만들기 같음, 자체 시험 39/39, 형태 표, 뿌리 32+12 모두 `<root>`), `dry_a27.py pytest` ok(`dry/dry_a27_pytest.json` `4a5b8bba…18e6`; 바탕 16 passed, 후보 21 passed), `rj27.py check` ok(`dry/rj27_check_decl.json` `96151ab7…ab783`). 망가뜨린 구현 8개 모두 잡음(첫 판에서 하나를 못 잡아 자체 시험 사례 둘 더함). 개발 시험 두 번(`dev1`·`dev2`, 출력 지움): `dev1`에서 `judge_g4_decision_full`이 CSV 없는 출력에서 `numeric_hard` 예외로 죽어 고침.
- 쓴 곳: AD7, TKD = `TK/a27decl/tc_base`·`tc_cand`(각 약 203 MB, `TK/a26decl/tc` 복사; 봉인·s47 이름 19개는 원본에서 이미 빠짐), 스냅숏 `OK2/snap/s12_a27decl.json` `810f2f60…4066`(s02 대비 SAME). `TK/a27`·`OK2/a27`·`OK2/sealed_s47/a27` 만들지 않음 [실행 `rj27.py check` absent 참].
- 하지 않은 일: VISSIM·COM·러너·동결 0. 결정 재생·plant 잡·포착 0. 관문 출력끼리 비교 0(기준·커밋 출력은 `replay_run.json`의 `root`와 CSV·JSON sha만 읽음). 커밋·브랜치·푸시 0(GWT8 head `b887f99f`, K8 브랜치 `b9734abe`, status 0줄). GWT8·KI·KPA·OK2A·OK2C·동결본·런 폴더·k92attrib·기존 TK 트리 쓰기 0. 봉인 시드·v3c3-s47 파일 열람 0. 금지 시험 0(돌린 시험은 `test_k92_harness.py`·새 `test_k92_a27.py`뿐). C: 38 GB, D: 437 GB 여유.

## 2026-10-20 10:26 +0900 — ReviewDeclare A27: 보충 27 반박 검토·고정

- 근거 [실행 sha]: Declare 판 `SP/K8_PREDECLARATION_AMENDMENT_27.md` `c7146e6e…5192` = `.sha256` = 이 LOG 09:50 항목 값. 결정 기록 `2299bcb6…caa9`(155줄), VERIFY_IMPL_r1 `8ff723eb…`, 보충 24–26·고정점, `a26_pins` 44/44 OK, §0 표 sha 모두 같음. 이 항목 덧붙임 전 LOG `004e9dd4e40dbe6ebd5020c18d1bbf010f02aee71129afdc8217bcd1084474db`(98,338 B).
- **고정판** `SP/K8_PREDECLARATION_AMENDMENT_27.md` = `4ce8b27a2ebf08aa0e8ac3f647b4e4336a98f7be7ec8d6f006a0fd1d12005a13`(88,262 B, 588줄, CR 0) = `.sha256`. Declare 판 사본 `SP/K8_PREDECLARATION_AMENDMENT_27_r1.md`(+ `.sha256`, `c7146e6e…`). 고정점 `KB/AMENDMENT27_FIXED.md` `394ab15fdea0d945a3b766c208e692ee7e1086fca3c178f6b423079d71fedcdb`(14,053 B; 고정 시각 10:25:22). K9-2-4 메시지 기대 `23f36116f091acb4a483236ca9996b82f58ff2f8bf7cc7eba108706feaab1f86`(1,502 B).
- 고친 곳(보충 27 §16.1): V1 R-old 무리 R 조건 5 — 옛 N 허용 R3-02 60·R3-04 4·R3-05 30·R3-06 2가 뿌리 규칙에서 0이 되어 r1대로면 R6이 도구 산물로 반드시 FAIL(S-K32) → 경로 문자열 항목은 같거나 줄어야 함으로 고침 [읽음 `OK2C/K9-2-{1,2}/gates/gk2.json`, `vimpl_r1/gk2_fullnorm_diag.out.json`]. V2 N 규칙에 `(?=/|$)`·묶음 이름 제외(r1은 묶음 폴더 아래 다른 파일·폴더 37짝을 같은 글자로 만듦 [실행 합성]). V3 keyed 증거 핀(구동기 `keyed_pin_ok`, 거짓이면 INCOMPLETE; 지금 모두 참). V4 G-K4 plant 행 A(탐침 `k92b1_probe`) 대 C(`k92{1,2}_pl`) 공개·형태 보고만. V5 정규화 정확성 근거·한계. V6 G-K0 결정 C 대 C.
- 바뀐 도구 바이트 [실행]: 후보 `k92_compare.py` `c08a1111…`(블롭 `4f4ecc89…`), `k92_a27.py` `73931554…`(`f11d4cd9…`), `tests/test_k92_a27.py` `3960e759…`(`71283857…`), `k92_gates.py` 그대로 `7b19f7f3…`; `AD7/rj27.py` `4020548a…`, `make_a27_cands.py` `7aef9c08…`, `A27_CANDIDATES.diff` `421baa44…`(112줄). 새 확인 출력 `AD7/dry/dry_a27_static_r2.json` `6c43b40b…`(ok, 자체 시험 50/50), `dry_a27_pytest_r2.json` `e8b7ed93…`(16/21 passed), `rj27_check_decl_r2.json` `1e9cabcd…`(ok, G-K4 keyed 핀 8/8), `cands_list_r2.txt` `3793b0c9…`. Declare 판 도구·후보·출력 사본 `KB/a27review/r1/`(목록 `e8076482…`).
- 검토 시험 [실행 RV7 = `KB/a27review`]: N 정확성(`n_exact.py`, 문자열 3,136짝 합쳐짐 0·갈림 0, 합성 결정 출력 17가지), 망가뜨림 7/7(`mutants_r2.py`), R-old 쌍 184(K 162, R 22)·뿌리 11 빌드 기록 같음(`rold_list_check.py`), §10 31개 = 고정판 글 sha·`rj27.amendment_sha`·`message4`·`front` 참(`pins31_check.py`). 도구 sha는 고정점 §4.
- 하지 않은 일: VISSIM·COM·러너·동결 0. 결정 재생·plant 잡·R-old·관문 출력끼리 비교 0. 커밋·브랜치·푸시 0(GWT8 head `b887f99f`, K8 `b9734abe`, status 0줄, 원격 추적 없음). `TK/a27`·`OK2/a27`·`OK2/sealed_s47/a27` 없음(만들지 않음). KI·KPA·OK2·GWT8·동결본·런 폴더·`k92attrib`·기존 TK 트리 쓰기 0(TKD `tc_cand` 후보 4파일 덮어쓰기만). 봉인 시드·v3c3-s47 파일 열람 0. 금지 시험 0. 내가 만든 `AD7/__pycache__` 하나 지움. C: 38 GB, D: 437 GB 여유.

## 2026-10-20 10:32 +0900 — Rejudge A27: 보충 27 적용 시작 (C0 사전 확인)

- 이 항목 덧붙임 전 LOG 101,650 B. 작업 폴더 AI7 = `KB/a27impl`(점검 도구·출력, 판정에 쓰지 않음).
- C0 [실행 `AI7/c0_check.py` `f329f4d9…3f24` → `AI7/out/c0.json` `a70e24ca…10d7`]: 보충 27 `4ce8b27a…5a13` = `.sha256` = 고정점(`394ab15f…dcdb`, 메시지 기대 `23f36116…` 들어 있음). 결정 기록 앞 155줄 = `2299bcb6…caa9`(지금 155줄). LOG 앞 94,304 B = `65aed126…`. §0 표 문서 20개 sha 같음. `a26_pins` 44/44 OK. §10 목록 31개 지금 바이트 = §10 값(값 모두 고정판 글에 있음). GWT8 head `b887f99f`, 브랜치 `claude/k92-b1-20261016`, K8 브랜치 `b9734abe`, `b9734abe..` 커밋 4개, status 0줄, `refs/remotes/origin/claude/k92-b1-20261016` 없음, 상류 없음. GWT8 SA 비교기·판정기 = 옛 값(`55df106b…`, `9418d3e4…`). `TK/a27`·`OK2/a27`·`OK2/sealed_s47/a27` 없음. python·VISSIM·cscript 0개. C: 37.9 GB, D: 436.7 GB.
- 스냅숏 `OK2/snap/s13_a27_C0.json` `2f279712…550b`(36.6 s) 대 s02: SAME [실행 `KI/k92snap.py diff`].

## 2026-10-20 10:34 +0900 — Rejudge A27: C1 정적 다시 점검, C2 빈 돌리기, C3 고정

- C1 [실행 `AD7/rj27.py check --dest AD7/dry/rj27_check_impl.json`]: `RJ27_CHECK ok=True`, 세 폴더 없음. 출력 `2792ea2f…a50a`; `when` 밖의 칸이 `rj27_check_decl_r2.json`(`1e9cabcd…`)과 정규 JSON으로 같음(키 차이 0).
- C2 [실행 `AD7/rj27.py commit --dry-run`]: `FRONT_CHECK` 6점검 모두 참(K8 브랜치 b9734abe, 브랜치, 사슬 4커밋, head = 끝, status 0, 원격 추적 없음), `EXPECT` 후보 4파일 sha 앞 16자 = 선언 값, `msg_sha256=23f36116f091acb4a483236ca9996b82f58ff2f8bf7cc7eba108706feaab1f86` = 고정점 값, `DRY RUN: no change`. GWT8 head `b887f99f`·status 0줄 그대로. 구동기가 `OK2/a27/logs/rj27.log`를 처음 만듦.
- **C3 고정** [실행 `AI7/make_pins31.py` `7ab7298b…c9d7`]: `KB/a27_pins.sha256` = **`a06c78d752216808ae265204424194b1421dd72dc8cf5a4b3456b43ef0ecf364`, 31줄**(표 순서, `<sha> *<절대 경로>`, LF, CR 0). 값 = 보충 27 §10(구동기 `4020548a…`, `dry_a27.py` `641368b3…`, `make_a27_cands.py` `7aef9c08…`, 바탕 `55df106b…`·`9418d3e4…`, 후보 `c08a1111…`·`7b19f7f3…`·`73931554…`·`3960e759…`, 틀 `1895e59e…`, 확인 출력 `6c43b40b…`·`e8b7ed93…`·`1e9cabcd…`, KI `ae5de0cc…`·`be5a0c95…`·`1fbe827f…`·`bf7a8132…`·`0dbd7d2c…`, KPA `cf1ae3fb…`·`296c6595…`·`af916995…`·`e3ded96b…`·`6f151334…`·`e7a4c7e9…`, 기록 `78f954ec…`·`d7da2fe9…`·`67d12151…`, 바깥 도구 `0482a538…`·`6ad45fd4…`·`5d34109f…`·`4adf41cf…`). Git Bash `sha256sum -c` 31/31 OK, 종료 0(`AI7/out/pincheck_C3.txt`). 고정 창은 지금부터 C8 끝 대조까지.
- [2026-10-20 10:33 +0900] 보충 27 커밋(rj27.py, 자동 기록): K9-2-4 = `bfd609c03a17b6f1ced27dd235f9ffe9634b4e0d`, ok=True, 파일 4개 블롭 = 선언 값 True, 푸시 0.

## 2026-10-20 10:35 +0900 — Rejudge A27: C4 커밋 K9-2-4

- 바로잡음: 앞 항목 머리 "10:34"는 실제 10:32–10:33(C3 고정은 커밋 10:33:04 전)입니다. 내용은 같습니다.
- 발사 전 대조 [실행 `AI7/pincheck.sh C4`]: 31/31 OK, 종료 0, 목록 파일 sha = `a06c78d7…`.
- C4 [실행 `AD7/rj27.py commit`]: **K9-2-4 = `bfd609c03a17b6f1ced27dd235f9ffe9634b4e0d`**(부모 `b887f99f`). 파일 4개 ls-tree 블롭 = 작업 바이트(`--no-filters`) = 선언 블롭(`4f4ecc89…`, `01ce99d3…`, `f11d4cd9…`, `71283857…`). `diff --name-status b887f99f HEAD` = M `k92_compare.py`, M `k92_gates.py`, A `k92_a27.py`, A `tests/test_k92_a27.py`. 작성자 = 커밋터 = `Ming2you <alsrjsrb1915@snu.ac.kr>`, 메시지 바이트 = 만든 바이트(sha `23f36116…`), 끝 줄 Co-Authored-By 한 번. status 0줄, K8 브랜치 `b9734abe`, 상류 없음. 기록 `OK2/a27/commit_k924.json`(`ok` 참). **푸시 0.**

## 2026-10-20 10:55 +0900 — Rejudge A27: C5 K9-2-4 관문 — R6(R-old)에서 구동기 비정상 종료 → STOP (S-K32)

- 발사 전 대조 [실행 `AI7/pincheck.sh C5`]: 31/31 OK, 종료 0, 목록 sha `a06c78d7…`. 발사 [실행 `KI/launch.ps1 -Tag a27_gates -Script ..\a27decl\rj27.py -ArgLine gates`]: 10:33:36, WMI ReturnValue 0, cmd PID 23668, BelowNormal, python 0·VISSIM 0(발사 때).
- 결과 [실행 `OK2/a27/gates.json` `23f60b37…a719`, 태그 로그 `OK2/logs/a27_gates.txt` `c1b0819e…872d`]: R0 `pre4` PASS, R1 `trees4` PASS(`TK/a27/k924`·`u_k923`·`u_k924`, 차이 = 4경로, 판정기 4파일 sha = 선언), R2 `diff4` PASS(이름·상태 넷, 런타임 차이 0 B), R3 `pycompile4` PASS 4/4, R4a `jb4` PASS(J-b 5파일 블롭 = b9734abe, 판정기 목록 15 → `OUT27/k924_blobs.json` 17개 `2bc71c9e…`), R4b `selftest4` PASS(50/50, 자식 0), R5 `U4` PASS(바탕 288·새 293 = 기대 개수, 겹친 288 결과 같음, 새 시험 5 통과, 두 쪽 pytest rc 1은 같은 옛 실패 9개·건너뜀 1개).
- **R6 `rold4`: 판정 없음(INCOMPLETE).** 10:47:45 `rj27.py:601` `child(code, 'rold4')` → `KI/cglib.py:317` `subprocess.run([PY, '-B', '-c', code])`에서 `FileNotFoundError: [WinError 206]`(파일 이름이나 확장명이 너무 김). 구동기가 184쌍 목록 전체를 `-c` 명령줄 글자로 넘기는데, 그 명령줄이 64,242자로 Windows CreateProcess 상한 32,767자를 넘음 [실행 진단 `AI7/diag_cmdlen.py` `99dd1388…` → `AI7/out/diag_cmdlen.json` `21e8dab1…`; 아무것도 비교·재생하지 않고 명령줄 길이만 셈]. 같은 셈으로 rjg4 명령줄 8,730자(옛 출력으로 정확히), rjg2 약 7,169자(트리가 없어 옛 G-K2 트리 keyed로 어림)라 상한 아래.
- R-old 데이터 0: 자식 프로세스가 만들어지지 않음(`OK2/a27/judge/rold4.log` 0 B, `rold4.json`·`gates/rold4.json` 없음). 예외가 잡히지 않아 구동기의 `STOP_rold4.json`·자동 LOG 줄은 없음. 내 기록 = `AI7/out/STOP_C5_R6.json` `69f1dff2…23cb`.
- 처리: 보충 27 §11 S-K32(R0–R7 가운데 PASS 아님) → **STOP**. 같은 입력으로 다시 돌리지 않음. 구동기 고침은 C3 고정 뒤라 S-K31·S-K12에 해당 → 하지 않음(사용자 결정). R7 `after4`, C6 RJ-G2, C7 RJ-G4는 하지 않음.
- 뒤 점검 [실행]: 스냅숏 `OK2/snap/s14_a27_C5_stop.json` `b4343e79…259e` 대 s02 SAME. 끝 대조 31/31 OK·종료 0(`AI7/out/pincheck_final.txt`). GWT8 head `bfd609c0`(K9-2-4), status 0줄, K8 브랜치 `b9734abe`, 원격 추적 참조·상류 없음, 푸시 0. python·VISSIM 0. `TK/a27` 6.1 GB. C: 38 GB, D: 431 GB.

## 2026-10-20 10:53 +0900 — Rejudge A27: 마무리 보고 (STOP, 사용자 결정 대기)

- 바로잡음: 앞 항목 머리 "10:55"는 실제 10:50–10:52입니다. 내용은 같습니다.
- 보고 `KB/REJUDGE_A27.md` sha256 `0a311a002c2f14a8b734a21e0db7fb2f587d955ed98b92cfc5bcf3f16be2e364`. `KB/IMPLEMENT.md`에 넷째 시도 절 덧붙임(앞 35,104 B = `a1f3681e…` 그대로).
- 상태: K9-2-4 `bfd609c0` 로컬(푸시 0). K9-2-4 관문 R0–R5 PASS, R6 R-old 구동기 비정상 종료(명령줄 64,242자 > 32,767자, WinError 206) → S-K32 STOP. C6 RJ-G2·C7 RJ-G4 하지 않음. 구동기 고침·다시 돌리기 0(C3 고정 뒤 = S-K31·S-K12). python·VISSIM 0.

## 2026-10-20 11:10 +0900 — Declare A28: 보충 28 작성 시작 (D-K9-51·D-K9-52)

- 근거 [실행 sha]: 결정 기록 `SP/K9_1_J1_NOTES_20261013.md` `2bfe5c56…1a76`(165줄; 앞 155줄 `2299bcb6…` 그대로), 보충 24 `d46db6dc…`·25 `4fd7b599…`·26 `8f835616…`·27 `4ce8b27a…`(각 `.sha256`와 같음), 고정점 27 `394ab15f…`, `KB/a27_pins.sha256` `a06c78d7…` 31/31 OK. 이 항목 덧붙임 전 LOG `42c72c75…3ce8`(108,916 B).
- 작업 폴더 AD8 = `KB/a28decl`(새로 만듦). 보충 28·고정점 28은 아직 없음. GWT8·OUT27·TK·KI·KPA·동결본·런 폴더 쓰기 0으로 진행.

## 2026-10-20 11:45 +0900 — Declare A28: 보충 28 작성 끝 (D-K9-51·D-K9-52)

- 이 항목 덧붙임 전 LOG 1295e3667c0d49347bdbe29b54d6d41c886e141665e52d578d7ba9759248d88f(109535 B).
- **보충 28 Declare 판** `SP/K8_PREDECLARATION_AMENDMENT_28.md` sha256 `f397fb3f6c02e0896ed144b68da20e759b6b97ed3037b3ae22d19e3c0a890f70`(57,833 B, 430줄, CR 0) = `SP/K8_PREDECLARATION_AMENDMENT_28.md.sha256`(sha256sum -c OK). 고정점 `KB/AMENDMENT28_FIXED.md`는 반박 검토가 씀(아직 없음).
- 내용 [실행·읽음]: (1) 새 구동기 `KB/a28decl/rj28.py` `57e79a78…35a9` = `a27decl/rj27.py`(`4020548a…`, 바꾸지 않음) + 덩어리 18개(`A28_DRIVER.diff` `ef732c11…34dd`, 541줄): 판정 자식 목록을 `OK2/a27/judge/<이름>.input.json`(JSON, 정확성·목록 sha 고정 점검)으로 넘기고 자식 확인 파일로 되봄, 명령줄 길이 점검(> 32,766자면 STOP), 시작 실패 기록. KI `cglib.py` 그대로. (2) A28-W(`a28w.py` `f921f1d3…4fe6`): K9-2-1 W 결정 4행만, 잎 `…/tangent_derivatives[*]/transformed_source_sha256/<root>/evaluation/controllers/runtime_setup.py`, 옛 쪽(탐침) `70cca680…`·새 쪽(K9-2-1) `1ab45c03…`, 개수 1·2·1·2, 점검 11개 모두 참일 때만 HOLD → PASS, 그 밖 → STOP. (3) 새 고정 목록 `KB/a28_pins.sha256` 40줄(1–31 = a27 31줄 그대로 + AD8 8 + a27_pins), D1에서 씀. (4) 이어 하기 resume28(OUT27 21파일 sha·집합, TK/a27, 브랜치 앞, 판정기 SA 39 블롭, 보충 27·28 고정 등 14점검 + 보관 복사 `OUT27/a28_base/`), R0 다시 봄·R1–R5 건너뜀·R6부터.
- 목록 sha(입력 파일 글자): rold4 `318474fb…e9e3`(184쌍, 61,126 B), rjg2 `c0523271…3a4c`(9칸, 옛 G-K2 트리 keyed로 셈), rjg4 `968d17fa…59bd`(8+4행). R-old `pairs_sha256` 기대 `63a05d8a…63eb`.
- 데이터 없는 확인 [실행 `a28decl/dry_a28.py` `f75a587f…5f85` → `dry/decl2/dry_a28.json` `2a82e2b6…497c`, ok 참]: 자식 코드 글자 = 보충 27(목록 자리만 다름), 메아리 자식이 받은 인자별 repr = 구동기 = 보충 27 경로(1,472/72/72개), 확인 파일 참, 명령줄 rold4 64,242 → 1,974·rjg4 8,730 → 1,551·rjg2 7,169 → 1,406, 진짜 child 끝까지(봉인 갈래 포함, 봉인 자리는 dry 폴더) 참, 길이 점검·시작 실패 STOP 확인, resume 14점검 참, a28w 자체 시험 24/24, py_compile ok, OUT27 21파일 sha 그대로, SEALED27 없음. `rj28.py check` ok(보충 27 r2 출력과 when·absent만 다름), `check28` ok(보충 28 고정 전이라 amendment28 없음). 개발 실행 `dry/learn1`(값 셈)·`dry/decl` 보관. 스냅숏 `OK2/snap/s15_a28decl.json` `b80a5166…9354` = s02(SAME).
- 지킨 것: VISSIM·COM·러너·동결·재생·plant 잡·트리 만들기 0, 판정 함수 호출 0(R-old·RJ-G2·RJ-G4 데이터 0), 커밋·브랜치·푸시 0(GWT8 head `bfd609c0`, status 0줄, K8 `b9734abe`), GWT8·OUT27·TK·KI·KPA·OK2A·OK2C·AD7·동결본·런 폴더·k92attrib 쓰기 0, 봉인 시드·v3c3-s47 파일·봉인 로그 열람 0, 금지 시험 0, a27_pins 31/31 OK, 결정 기록 `2bfe5c56…` 그대로. 공개: sha 목록을 Git Bash `/tmp/h.txt`에 한 번 썼다가 지움. python·VISSIM 0. C: 38 GB, D: 431 GB.

## 2026-10-20 11:44 +0900 — ReviewDeclare A28: 보충 28 반박 검토 시작

- 검토 대상 [실행 sha]: `SP/K8_PREDECLARATION_AMENDMENT_28.md` `f397fb3f…0f70`(= `.sha256`), `a28decl/rj28.py` `57e79a78…35a9`, `a28w.py` `f921f1d3…4fe6`, `dry_a28.py` `f75a587f…5f85`, `A28_DRIVER.diff` `ef732c11…34dd`. 결정 기록 `2bfe5c56…1a76`(165줄). `KB/a27_pins.sha256` 31/31 OK. 이 항목 덧붙임 전 LOG `915c810a…9f4e`(112,752 B).
- 검토 폴더 RV8 = `KB/a28review`(새로 만듦). 지킬 것: VISSIM·COM·러너·동결·재생·plant 잡·트리 만들기 0, 판정 함수의 실제 데이터 호출 0(합성 자료만), R-old·RJ-G2·RJ-G4 데이터 0, GWT8·OUT27·TK·KI·KPA·OK2A·OK2C·AD7·동결본·런 폴더 쓰기 0, 봉인 시드·v3c3-s47 열람 0, 커밋·푸시 0.
- 참고: Declare 끝 항목의 머리 시각 "11:45"는 실제 덧붙임 시각(LOG 파일 수정 11:33)보다 늦게 적혀 있음 [실행 `ls -l`, `date` 11:43]. 내용에는 영향 없음.

## 2026-10-20 12:08 +0900 — ReviewDeclare A28: 보충 28 고정 (반박 검토 끝)

- 이 항목 덧붙임 전 LOG 4c42fca165b6e4d0d1ee6fda4bf7c9b43a1f80634cb02556997e5daa43e1756f(113749 B).
- **보충 28 고정판** `SP/K8_PREDECLARATION_AMENDMENT_28.md` sha256 `9881eb40c1129af0cdff48026dc8656b4235d43f0eb80566e4be9b66d9ac345e`(75,676 B, 492줄, CR 0) = `.sha256`(sha256sum -c OK). Declare 판 = `_r1` `f397fb3f…0f70`(+ `.sha256`). **고정점** `KB/AMENDMENT28_FIXED.md` sha256 `14451cf4d46c5c0095bc896134112148ba5700ee70b2ed78b8ee38d0e62e20e5`, 고정 시각 2026-10-20T12:06:30+09:00. `rj28.py check28`(읽기만) → `amendment28` = 고정판 sha, 14점검 참 [실행 `a28review/out/rj28_check28_rv_after.json` `1b65999d…977e`].
- 고친 곳(보충 28 §12.1): V1 판정 자식이 SA 밖 `k8_gates/k8common.py`를 불러옴(`sa_common.py:65-69`; r1 §5.4 "SA 안만"은 틀림) → 판정 자식이 불러오는 판정기 트리 파일 9개를 고정 목록 41–49줄로(40 → 49줄, 기대 파일 `a28review/out/a28_pins.expected.sha256` `2427e2dd…28cd`, 49/49 OK, 9개 모두 K9-2-4 블롭). V2 D2·D5에 R1–R5 기록 18파일 바이트 그대로·`a28_base` 21개 점검. V3 D4에 자식 원본·판정 파일 대조(바뀐 행 = 원본 HOLD W 행뿐, `a28_w.ok`, 옛 쪽 JSON sha = 탐침 핀). V4 D0에 `OUT27/logs/rj28.log` 없음, `check28`은 D0에서만. V5·V6 글. **구동기 `rj28.py`·규칙 `a28w.py`·Declare 확인 출력 바이트, LIST_SHA256·A28W_SHA256·RESUME_BASE, A28-W의 행·잎·두 값·점검은 바꾸지 않음.**
- 확인 [실행]: 차이 파일 다시 만들기 바이트 같음(`ef732c11…`), `ast` 비교 그대로 67·글자만 5·코드 7·새 25·빠짐 0(= §2.2 표), 자식 코드 글자 = 보충 27(목록 자리만), 목록 셋 sha = LIST_SHA256, 형까지 같음, 명령줄 1,974/1,551/1,406자, `pairs_sha256` `63a05d8a…`. A28-W: 따로 쓴 규칙과 4,002/4,002 같음, 판정기 바이트 사본 + 합성 출력 26가지 모두 예상대로(RS 잎 두 값만 → PASS, 그 밖 차이 → 보류/FAIL/INCOMPLETE 그대로, 다른 행 손대지 않음), 원본 변이 16개 가운데 15개 잡음(남은 1개는 같은 결과를 내는 변이, a28w 자체 시험이 잡음). RS 블롭: K9-2-1 `a21fd7c0`→`1ab45c03`, K9-2-2…4 `bcf7a777`→`70cca680`. `check`·`check28` Declare와 when만 다름, a28w 자체 시험 24/24.
- 지킨 것: R-old·RJ-G2·RJ-G4 데이터 0, VISSIM·COM·러너·동결·재생·plant 잡·트리 만들기 0, 판정 함수의 실제 출력 호출 0(합성만), GWT8(head `bfd609c0`, status 0줄, K8 `b9734abe`, 원격 추적 없음, 푸시 0)·OUT27(21파일 그대로)·TK·KI·KPA·AD7·AD8·동결본·런 폴더 쓰기 0, SEALED27 없음, 봉인 시드·v3c3-s47 열람 0, 금지 시험 0, `__pycache__` 0, python·VISSIM 0. 쓴 곳: `KB/a28review`, SP 보충 28·`_r1`·`.sha256` 둘, 고정점, 이 LOG. 공개: rv_a28w 첫 실행(`syn_run1`, `out/rv_a28w_run1.json`)은 예외를 "거짓"과 따로 센 검토 도구 셈 방식 차이(40건)로 다시 돌림. C: 38 GB, D: 431 GB.

## 2026-10-20 12:11 +0900 — Rejudge A28: 보충 28 적용 시작 (D0–D5, R6부터 이어 하기)

- 이 항목 덧붙임 전 LOG `8c285fad9bac3d64291733956e2004540c1902ece918de6786436fd2d115e2a1`(116,840 B).
- 근거 [실행 sha]: 보충 28 `9881eb40…345e` = `.sha256`, 고정점 `KB/AMENDMENT28_FIXED.md` `14451cf4…e0e5`(LOG 12:08 항목의 값과 같음). 결정 기록 `2bfe5c56…1a76`. `KB/REJUDGE_A27.md` `0a311a00…e364`, `KB/IMPLEMENT.md` `6709aa3f…3ae5`.
- 구동기 고침은 커밋하지 않는 구동기 `KB/a28decl/rj28.py`(`57e79a78…35a9`)라서 새 커밋이 없고, 다시 고정 = D1(`KB/a28_pins.sha256` 49줄)입니다. 이번 점검 도구·출력 폴더 AI8 = `KB/a28impl`(새로 만듦). python·VISSIM 0(시작 때). C: 38 GB, D: 431 GB.

## 2026-10-20 12:14 +0900 — Rejudge A28: D0 사전 확인 참, D1 다시 고정

- D0 [실행 `a28impl/d0_check.py` `333057e9…9b2f` → `a28impl/out/d0.json` `cd3a37b6…8c50`, 16점검 모두 참]: 보충 28 `9881eb40…` = `.sha256` = 고정점 28(`14451cf4…`), 결정 기록 165줄 = `2bfe5c56…`, 보충 21·24–27·고정점 24–27 등 §0 문서 23개 sha 같음, LOG 앞부분 세 지점 그대로(덧붙임만), `a27_pins` 31/31·자기 sha `a06c78d7…`, §4 49개 바이트 = 기대 파일 `2427e2dd…`(값이 보충 27·28 글에 있음), `OUT27/logs/rj28.log` 없음, SEALED27 없음, GWT8 head `bfd609c0`·브랜치·K8 `b9734abe`·커밋 5개·status 0줄·원격 추적 없음, AD8·판정기 트리에 `__pycache__` 없음, `rj28.py check28 --dest a28decl/dry/rj28_check28_impl.json`(`51a9174e…aa75`) 종료 0·14점검 참·`amendment28` = `9881eb40…`. python·VISSIM 0. 스냅숏 `OK2/snap/s16_a28_D0.json` `9d7a06c8…1221` 대 s02 SAME. C: 37.6 GiB, D: 430.4 GiB.
- D1 [실행]: `KB/a28_pins.sha256` = 기대 파일 복사, `cmp` 같음, sha256 `2427e2ddbcd39bf8f0b0df10ab6a8e6bc4150e690d05507a82bbf168882b28cd`, 49줄, LF, CR 0, `sha256sum -c` 49/49 OK·종료 0(`a28impl/out/pincheck_D1.txt`). 고정 창(D1–D5 끝 대조) 시작.
- [2026-10-20 12:32 +0900] 보충 28 구동기: K9-2-4 관문 끝(rj28.py, 자동 기록): pre4=PASS, trees4=PASS, diff4=PASS, pycompile4=PASS, jb4=PASS, selftest4=PASS, U4=PASS, rold4=PASS. 판정 파일 `D:\VISSIM_runs\20261001_v3c3\reports\k8\k92_b1\a27\gates.json` sha256 `2df93a72f2b75c10514f939dc4c3be0da356811c41195189755907e1fd49012e`.

## 2026-10-20 12:35 +0900 — Rejudge A28: D2 이어 하기 R6·R7 PASS

- 바로잡음: 앞 항목 머리 "12:14"는 실제 12:13입니다(내용 같음).
- 발사 전 대조 49/49 OK·종료 0·목록 sha `2427e2dd…`(`a28impl/out/pincheck_D2.txt`). WMI 발사 12:13:17 `rj28.py gates`(태그 `a28_gates`, ReturnValue 0, cmd PID 25884, BelowNormal, `PYTHONHASHSEED=0`, `python -B`). 12:32:46 끝, 기다림 확인 3번(각 9분 이하). 태그 로그 `OK2/logs/a28_gates.txt` `4175f6ff…ea78`(끝 줄 `RJ28_GATES_DONE`).
- 결과 [실행 `OUT27/gates.json` `2df93a72…012e`]: `resume28` PASS(14점검 참, 보충 28 = `9881eb40…`, `a28_base/` 21개 복사 = §5.2 값), `pre4` PASS(다시 봄, 파일 바이트는 옛 R0 기록과 같음 `85c90118…`), R1–R5 건너뜀(기록 그대로), **`rold4` PASS**(184쌍: 무리 K 162 PASS, 무리 R 22 PASS; `gates/rold4.json` `7ed175aa…feea`), **`after4` PASS**(`after4.json` `800ca115…ce8e`).
- 보충 28 D2 통과 조건 [실행 `a28impl/stage_check.py D2` `d1ae9579…d8a` → `a28impl/out/d2.json` `2b5e0a89…9398`, 16점검 참]: `child_transport.ack_ok` 참, `input_sha256` = `318474fb…`(= §2.4), 명령줄 1,974자, `pairs_sha256` = `63a05d8a…`, 확인 파일 sha 둘 = 입력 sha, R1–R5 기록 18개 바이트 = §5.2 값, `a28_base/` 21개 = §5.2 값, `STOP_*` 없음, SEALED27 없음. 보고만: K 무리 새 비교기 판정 = 기록된 판정 162/162.
- 스냅숏 `OK2/snap/s17_a28_gates.json` `b7b05722…785a` 대 s02 SAME. python·VISSIM 0(끝). C: 38 GB, D: 431 GB.

## 2026-10-20 14:33 +0900 — Rejudge A28: D3 RJ-G2 PASS (9칸, 결과 넷)

- 발사 전 대조 49/49 OK·종료 0·목록 sha `2427e2dd…`(`a28impl/out/pincheck_D3.txt`). WMI 발사 12:35:48 `rj28.py rjg2`(태그 `a28_rjg2`, ReturnValue 0, cmd PID 23204, BelowNormal). 14:31:17 끝, 기다림 확인 11번(각 9분 이하). 태그 로그 `OK2/logs/a28_rjg2.txt` `f40a73b9…9a91`(끝 줄 `RJ28_RJG2_DONE`).
- 트리 9개(`TK/a27/rj_*`) 만듦, 팔 트리 6개 점검 모두 참(뿌리·차이 = 튜닝 ∪ L 10파일·형태 `CCCCCCCCCC`/`AAAAAAAAAA`·RS/SHO/튜닝 = 옛 G-K2 트리) [`OUT27/rjg2_trees.json` `49d823c0…6f16`]. 재생 전 칸 9개 기준 핀·CR 짝·keyed 핀 참, **`a28_items_sha256` = `c0523271…`(= §2.4, 새 트리 keyed로도 같음)** [`OUT27/rjg2_pre.json` `29fff06c…40b5`]. 재생 9개 모두 건강 점검 통과(재생 기록 `exit=2`는 원래 닫힌 고리 기록과의 런처 대조 결과로, 옛 G-K2·탐침과 같은 꼴; 건강 점검 `replay_run.exit_code` 0·`derived`·`action_contract` 참).
- 결과 [실행 `OUT27/gates/rjg2.json` `e4718cb3…dc8b`, 자식 원본 `judge/rjg2.json` `2aa8be0c…5710`]: **9칸 모두 PASS**(결과 넷: HARD SAME, `verdict_full` PASS, 미분류 0). (c) S3 H5 선언 차이 1개(`/metadata/head_discharge_floor_173_p4_301ceabb95f116fa`)는 보충 24 규칙대로. `child_transport.ack_ok` 참, `input_sha256` = `c0523271…`, 명령줄 1,406자.
- D3 통과 조건 [실행 `a28impl/stage_check.py D3` → `a28impl/out/d3.json` `c349996b…966d`, 12점검 참]. `OUT27/gates.json` `51bbc1c0…74e7`. 스냅숏 `OK2/snap/s18_a28_rjg2.json` `35c2e8eb…ec4d` 대 s02 SAME. `TK/a27` 25 GB, OUT27 1.8 GB. python·VISSIM 0(끝). C: 38 GB, D: 411 GB.
- [2026-10-20 14:35 +0900] 보충 28 구동기: 다시 판정 끝(rj28.py, 자동 기록): rjg2=PASS, rjg4=PASS. 판정 파일 `D:\VISSIM_runs\20261001_v3c3\reports\k8\k92_b1\a27\gates.json` sha256 `e57f1b3655b1f046820944cf0e55680a83d2f93b9f7f960f7d9e1acd3b8d2db6`.

## 2026-10-20 14:42 +0900 — Rejudge A28: D4 RJ-G4 PASS, D5 마무리 (보충 28 적용 끝, STOP 없음)

- D4 [실행]: 발사 전 대조 49/49 OK·종료 0(`a28impl/out/pincheck_D4.txt`). WMI 발사 14:33:20 `rj28.py rjg4`(태그 `a28_rjg4`, ReturnValue 0, cmd PID 22404, BelowNormal). 14:35:41 끝, 기다림 확인 1번. 태그 로그 `OK2/logs/a28_rjg4.txt` `4484d066…dae1`(끝 줄 `RJ28_RJG4_DONE`). 봉인 갈래 자식 종료 0, 109.4 s, 표준 출력 `SEALED27/logs/rjg4_20261020_143322.txt`(0 B, 열지 않음; `OUT27/sealed_index.json` `62ddee56…51f9`).
- 결과 [실행 `OUT27/gates/rjg4.json` `4f2f0426…ad90`, 자식 원본 `judge/rjg4.json` `246f28aa…82ec`]: **RJ-G4 PASS, 12행 모두 PASS**. K9-2-2 B1 결정 4행 = K9-2-4 PASS(HARD SAME, 전체 결과 PASS, 미분류 0). plant 4행 = K9-2-4 PASS(`summary.json`·`k92_record.json` 모두 PASS). K9-2-1 W 결정 4행 = K9-2-4 판정 보류(HARD SAME, 숫자 PASS, CR 짝 참, 미분류 = RS 잎 `A_K92 condition false` 1·2·1·2개) → A28-W 11점검 모두 참·`failed` 빈 목록 → PASS. 두 값 `70cca680…`(탐침)·`1ab45c03…`(K9-2-1), 옛 쪽 JSON sha = `K92_PROBE_OUT.json` 핀. 입력 sha `968d17fa…`, `ack_ok` 참, 명령줄 1,551자.
- D4 통과 조건 [실행 `a28impl/out/d4.json` `5f574f42…f4ac`, 11점검 참]: 자식 원본 판정 = `verdicts_k924`(보류 4 + PASS 8), 바뀐 행 = 원본 보류 W 4행뿐, 다른 8행 손대지 않음. 스냅숏 `OK2/snap/s19_a28_rjg4.json` `7d5e40d1…8c3e` 대 s02 SAME.
- D5 [실행]: 끝 대조 49/49 OK·종료 0(`a28impl/out/pincheck_final.txt`, 대조 출력 다섯 개 바이트 같음 `160b172c…0321`). `a28impl/out/d5.json` `f53c3cfe…cf39`: R1–R5 기록 18파일 바이트 = 보충 28 §5.2, `a28_base/` 21개 같음, GWT8 head `bfd609c0`·브랜치·K8 `b9734abe`·커밋 5개·status 0줄·원격 추적 없음. `OUT27/gates.json` 끝 `e57f1b36…2db6`(resume28·pre4·R1–R5·rold4·after4·rjg2·rjg4 모두 PASS). `__pycache__` 0. python·VISSIM·cscript 0.
- 보고: `KB/REJUDGE_A27.md`에 "보충 28 적용" 절 덧붙임(앞 15,191 B = `0a311a00…e364` 그대로; 덧붙인 뒤 `7ddf9d3f62111d3db69df62cb9435c8e6cc4af0442b0764fb71681f764c5681a`, 절 원본 `a28impl/out/rejudge_a28_section.md` `302e4764…b8f9`). `KB/IMPLEMENT.md`에 다섯째 시도 절 덧붙임(앞 36,507 B = `6709aa3f…` 그대로; 뒤 `8b763911…4635`).
- 지킨 것: 새 커밋 0, 푸시 0, VISSIM·COM·러너·동결 0, plant 잡 0, 결정 재생은 RJ-G2 9개뿐, 봉인 시드·v3c3-s47 파일·봉인 로그 내용 열람 0(이름만: 시작 때 `OK2/sealed_s47/` 맨 위, D4 뒤 `SEALED27/logs/`), 금지 시험 0, 내가 끈 프로세스 0. 공개: `REJUDGE_A27.md` 첫 덧붙임 시도는 셸 따옴표 오류로 쓰기 0이었고(sha 그대로 확인) 파일로 써서 덧붙임. C: 38 GB, D: 411 GB.
- 다음(사용자): 독립 검증(A28-W 따로 구현 포함) → k92t → V-B. V-A·푸시는 사용자 결정 뒤에만.

## 2026-10-20 15:32 +0900 — VerifyImpl r2: 구현·보충 27·28 적용 독립 검증 (결함 1건 R2-D1 → STOP, 사용자 결정)
- 보고서: `KB/VERIFY_IMPL_r2.md` (sha256 `24b3c15d3cca7b265f1ea60ce2600d30e3c80745b3a34cb2866b1c07de698a63`), 도구·출력 `KB/vimpl_r2/`(파일별 sha는 보고서 §10).
- 고정점 [실행]: 결정 기록 `2bfe5c56…`, 보충 27 `4ce8b27a…`, 보충 28 `9881eb40…`, `a28_pins` 49/49 OK = 기대 파일. K9-2-4 `bfd609c0` 4파일 블롭·메시지(`23f36116…`)·작성자 = 선언, 런타임 차이 0 B, 푸시 0(`ls-remote` 읽기 한 번).
- 독립 재계산(하네스 import 0) [실행]: G-K2 9칸 모두 PASS(허용 수까지 하네스와 같음). G-K4 결정 B1 4행 PASS, W 4행 보류(1·2·1·2) → 글만 보고 짠 A28-W 11점검 4/4 참 → PASS. plant 4행은 봉인 규칙 때문에 원자료 재계산 안 함(원래 gk4 결과와 바이트 같음 확인). R-old 무리 R 22쌍 모든 칸 하네스와 같음, 무리 K 728파일 K9-2 글자 0.
- 정규화 [실행]: 내 N = 블롭 N(문자열 20,237개 차이 0). 실제 17쌍에서 N이 합친 원문 차이 4,206개 모두 자기 트리 뿌리뿐, 다른 트리·대소문자 0.
- 결함 R2-D1: 판정기 A_K92가 보충 24 :270의 "옛 값 = 옛 쪽 트리 RS sha"를 보지 않음(`k92_compare.py:434`, 판정 함수가 `old_root`를 넘기지 않음). 지금 판정 결과 영향 0(19잎 모두 참). 처리 = 공개 보충 또는 판정기 고침 커밋, 사용자 결정. 관찰 O-1–O-6(시험 빈 곳 4/16, N이 §2.1 글보다 넓게 합치는 꼴 하나, plant 행 재계산과 봉인 규칙 맞섬 등).
- 지킨 것: VISSIM·COM·러너·동결·재생·plant 잡 0, 커밋·푸시 0, GWT8·OUT27·KI·동결본·런 폴더 쓰기 0, 봉인 시드·s47 파일·봉인 뿌리 열람 0. 스크래치 `TK/vimpl_r2`(1.6 MB). 스냅숏 두 번 s02 대비 SAME. python·VISSIM 0. C: 38 GB, D: 411 GB.

## 2026-10-20 15:50 +0900 — Declare A29: 보충 29 작성 시작 (D-K9-53·54·55)

- 근거 [실행 sha]: 결정 기록 `SP/K9_1_J1_NOTES_20261013.md` `abe3cc05…95af`(174줄; 앞 165줄 = `2bfe5c56…1a76` 그대로, D-K9-53~55 :167-174), `KB/VERIFY_IMPL_r2.md` `24b3c15d…8a63`, 보충 24 `d46db6dc…`·25 `4fd7b599…`·26 `8f835616…`·27 `4ce8b27a…`·28 `9881eb40…`(고정점 24–28 sha 기록 값과 같음), `KB/a28_pins.sha256` `2427e2dd…` 49/49 OK. 이 항목 덧붙임 전 LOG `27fa0dd5…017b`(127,673 B).
- 작업 폴더 AD9 = `KB/a29decl`(새로 만듦; 읽기 전용 탐침 `probe/` 둘: 옛 출력의 생성 뿌리·RS sha 앞 8자, A_K92-M 하위 트리 꼴 — 이름·깊이·형만 출력). 보충 29·고정점 29는 아직 없음. GWT8·OUT27·TK의 기존 트리·KI·KPA·AD7·AD8·동결본·런 폴더 쓰기 0으로 진행. 판정 함수의 실제 출력 호출 0.

## 2026-10-20 17:12 +0900 — Declare A29: 보충 29 작성 끝 (D-K9-53·54·55)

- 이 항목 덧붙임 전 LOG `eaf527bdfbdfa5b6b97a1c912b0a09a1c1550224109f77f42938f59d60bc4645`(128,579 B).
- **보충 29 Declare 판** `SP/K8_PREDECLARATION_AMENDMENT_29.md` sha256 `26f46b1557e89cb5b61489922c3379f258c94121f2515b67dc9ab8ac340c046a`(82,256 B, 524줄, CR 0) = `SP/K8_PREDECLARATION_AMENDMENT_29.md.sha256`(sha256sum -c OK). 고정점 `KB/AMENDMENT29_FIXED.md`는 반박 검토가 씀(아직 없음).
- 내용 [실행·읽음]: (1) 판정기 고침 커밋 K9-2-5 후보 7파일(`AD9/cand/repo/SA`: M `k92_compare.py` `4b0f4dd9…`, M `k92_gates.py` `fb79ed57…`, M `k92_a27.py` `d4ab3f3d…`, A `k92_a29.py` `cb816eab…`, M `tests/test_k92_a27.py` `0e39d5f8…`, M `tests/test_k92_harness.py` `752aada0…`, A `tests/test_k92_a29.py` `b30cbb83…`; 차이 `A29_CANDIDATES.diff` `7753af6b…` 1,139줄, `git apply`로 K9-2-4 블롭 사본 → 후보 7/7 같음): A_K92 = 새 값 = 새 뿌리 RS sha + 옛 값 = 옛 뿌리 RS sha(옛 뿌리 필수) + 아는 값; A_K92-M 쪽 배정(:271)·모든 깊이 결정적 마디·옛 쪽 = 옛 뿌리; `judge_g2`·`judge_g4_decision_full`·`judge_hard`·`judge_decisions`(여섯째)·`report_g2e`가 옛 뿌리를 넘김; N 두 줄(묶음 이름 제외를 k92attrib 갈래에도, 묶음 폴더 k92b1·k92attrib는 한 단계 규칙에서도 트리 아님 — 보충 27 §2.1 :84/:104-106 대 :115 충돌에서 "좁힘" 쪽, 표 글자 8개·16짝 바뀜 공개). 메시지 틀 `d275c1c7…`. (2) 기존 출력만 다시 비교: K9-2-5 관문 `rold5`(R-old 184쌍, 비교기 셋 K9-2-0·K9-2-4·K9-2-5, R6 행 재현 + `same29` + K9-2-5 R-old 판정 = 기록), `rc_g2`(9칸, 목록 sha = 보충 28 RJ-G2와 같은 `c0523271…`), `rc_g4`(결정 8행 + A28-W를 `strip29` 행에 + 점검 12 `old_is_root_rs`; plant 4행은 바이트로 이어받음). 판정 변화·`same29` 거짓 = STOP. 옛 뿌리 닫힌 표(무리 K: FRZ_K8b 153·FRZ_K8 9, 무리 R: 기준·탐침 재생 root 22). (3) K9-2-5 관문 P0–P8(pre5·trees5·diff5·pycompile5·jb5·selftest5·U5·mut5·rold5·after5). (4) D-K9-55: k92t 전 plant = 바이트 대조만, k92t 안 J·F 값 고정 뒤 독립 원자료 재계산·기록 판정과 같아야 함. (5) k92t J·V-B VB-I1 = K9-2-5 판정기 + 옛 뿌리 필수(VB-31 FRZ_K8b, VB-43/41/41w FRZ_K8). 새 구동기 `AD9/rj29.py` `a45f894b1b68274d14aa177e4d4b7890169ccfa39df2a4af14e053502710578f`. 기대 고정 목록 `AD9/a29_pins.expected.sha256` `70a70b71c6d5a50a641f62a60bd908b474ffaa8bc88fa490a5216085923bbe29`(90줄 = a28 49줄 + 41줄, 90/90 OK).
- 데이터 없는 확인 [실행]: static ok(git apply 7/7), trees ok(tc24 SA = K9-2-4 39파일), 자체 시험 a27 59/59·a29 62/62, pytest tc24 21 passed·tc29 29 passed·judge_u PASS(새 8), cross(K9-2-4 시험을 K9-2-5 코드에: 정확히 5개 실패 = R2-D1·O-2 꼴), 망가뜨림 40/40(`decl2`; 첫 판 30개 가운데 M09·M13 못 잡아 시험 사례 고침), drivercode ok(명령줄 3,317/1,990/1,889), `rj29.py check29` ok, nscan: 다시 비교 입력 JSON 282개(5.06 GB)·K9-2 글자 10,074개에서 K9-2-4 N 대 K9-2-5 N 다른 글자 0. 무거운 확인 셋(nscan dev4, mut decl·decl2, nscan decl2)은 `AD9/launch_dry.ps1` WMI 분리·BelowNormal. 스냅숏 `OK2/snap/s20_a29decl.json` `615b0779…ffbf0` = s02(SAME).
- 지킨 것: VISSIM·COM·러너·동결·재생·plant 잡 0, 판정 함수의 실제 출력 호출 0(nscan은 `norm_s` 문자열만), 커밋·브랜치·푸시 0(GWT8 head `bfd609c0`, status 0줄, K8 `b9734abe`), GWT8·OUT27·OK2A·OK2C·KI·KPA·AD7·AD8·동결본·런 폴더·k92attrib·TK 기존 트리 쓰기 0(TKD9 `TK/a29decl/tc24`·`tc29`만 새로), `OK2/a29`·`TK/a27/k925` 등 만들지 않음, 봉인 시드·v3c3-s47·봉인 뿌리 열람 0, 금지 시험 0, a28_pins 49/49 OK, 결정 기록 `abe3cc05…` 그대로. 공개: 개발 실행 dev1–dev6·learn1·learn2 보관, `dry/decl`의 구동기 의존 출력 셋은 `ARM_OLD_TREE` 지우기 전 판(보관), Git Bash heredoc 역슬래시 문제로 쓰기 0인 시도 둘, `python -m py_compile` 한 번이 만든 `AD9/__pycache__`는 바로 지움. python·VISSIM 0. C: 38 GB, D: 410 GB.

## 2026-10-20 17:19 +0900 — ReviewDeclare A29: 보충 29 반박 검토 시작

- 이 항목 덧붙임 전 LOG `f91fab77bf2253eb13fe1d4a344fff9405af0906158d3a7f15f2a658f515b95a`(132,793 B).
- 근거 [실행 sha]: 보충 29 Declare 판 `26f46b1557e89cb5b61489922c3379f258c94121f2515b67dc9ab8ac340c046a` = `.sha256`, 결정 기록 `abe3cc058b7369148b28e9ccb9a9cff1a49dfd34bd30e01599ef48f5932395af`, 보충 24–28 sha = 보충 29 §0 값, `AD9/a29_pins.expected.sha256` 90/90 OK.
- 검토 폴더 RV9 = `KB/a29review`(새로 만듦). GWT8 head `bfd609c0`, K8 `b9734abe`, status 0줄 [실행]. python·VISSIM 프로세스 0. C: 38 GB, D: 410 GB.
- 할 일: 판정기 고침을 글에서 따로 짠 작은 구현과 합성 사례로 견줌, N을 경로 조각 해석과 견줌(합침·갈림), 새 망가뜨림으로 시험 빈 곳 점검, 다시 비교가 판정을 조용히 바꿀 수 없는지, 고정·STOP 규칙. 실제 결정 출력에 판정 함수 부르기 0, 재생·VISSIM 0, 커밋 0.

## 2026-10-20 18:05 +0900 — ReviewDeclare A29: 중간 기록 (찾은 것, 고칠 곳)

- 확인 [실행 RV9 도구]: §0·§2.7·§10·§13 sha 125/125 참(`rv_static`), 차이 파일 다시 만들기·`git apply` 7/7 같음; 글에서 따로 짠 A_K92/A_K92-M 작은 구현 대 후보 `compare` 무작위 3,000건 3,000 같음, 판정 함수 다섯이 옛 뿌리를 넘김 429/429(`rv_judge`); N 경로 조각 해석 대 후보 105,574 글자 0 다름, 뿌리 안 글자와 묶음 폴더 글자 만남 0(K9-2-4 N 311), K9-2 글자 없는 64,121 글자 K9-2-0·K9-2-4 N과 같음(`rv_n`).
- 찾은 것: (1) A_K92-M 결정적 마디를 N 전 키로 읽어 보충 21 §6.3a(N 뒤 경로)와 다름 — 대문자 키 `X_SHA256`·`PLAN_ACTION_TOKEN`이 PASS(`rv_edge`), 지금·k92t 데이터에는 닿는 자리 없음(런타임 키가 소문자 고정); (2) 새 망가뜨림 21개 가운데 판정이 느슨해지는 5개(u4·rule_code 아무 글자, `k92_attrib_head_173_p4_seed` 쪽, 두 쪽 다름 규칙, 키 끔 규칙)를 시험이 못 잡음(`rv_mut`), STOP 쪽 4개도 못 잡음; (3) E5 판정 자식이 불러오는 `TK27/k925` 9파일 바이트를 E4 뒤 다시 보지 않음; (4) 글 고칠 곳 몇.
- 고칠 곳: 후보 `k92_compare.py`(A_K92-M을 N 뒤 문서로), `tests/test_k92_a29.py`(단언 더함), `make_mutants29.py`·`mutants29.json`(M09 글자, 새 망가뜨림), `rj29.py` 상수 셋, 차이 파일. 고치기 전 사본 `RV9/r1/`(목록 `RV9/r1_files.sha256`). 커밋·판정 데이터·VISSIM 0.
- 고침(덧붙임): 바로 위 항목 머리의 시각 "18:05"는 잘못 적은 값입니다. 실제로 쓴 시각은 17:45 KST입니다 [실행 `date` 17:46, `RV9/r1_files.sha256` 수정 시각 17:45:10]. 그 뒤 자체 시험 출력 두 개가 시스템 Temp(`%TEMP%/rv_k92_a2{7,9}.json`)에 한 번 쓰였고 바로 지웠습니다.

## 2026-10-20 18:11 +0900 — ReviewDeclare A29: 보충 29 고정 (반박 검토 끝)

- 이 항목 덧붙임 전 LOG `d7458d9905b1cf6537e15c78ae5601a8ea9322ced28c4556b5060ecd7336b072`(135650 B).
- **보충 29 고정판** `SP/K8_PREDECLARATION_AMENDMENT_29.md` sha256 `4bd6dc8de8b0a4a4ab0b8703c07d7a73d244c4a622b81585f06dc69d6d83599d`(104,361 B, 604줄, CR 0) = `.sha256`(sha256sum -c OK). Declare 판 = `SP/K8_PREDECLARATION_AMENDMENT_29_r1.md`(+ `.sha256`, 26f46b15…). **고정점** `KB/AMENDMENT29_FIXED.md` sha256 `3ba1d0bdaab8a0189f903d10fc1024baed770080542cbd841f79d3a56df58e43`(고정 시각 18:10 KST; 고정판 sha만 64자). 구동기 `amendment29_sha()`가 고정판을 받음, `message5()` = K9-2-5 메시지 `a8545b2d279da75234f835d0e7a16ad1dc63d8d614bde1ab42ec581bfb577f77`(1,644 B) [실행, 구동기 함수만 불러옴·OUT29 만들지 않음].
- 고친 곳(§14.1): V1 A_K92-M 결정적 마디를 N 뒤 문서로(후보 `k92_compare.py` 한 줄, `3e2da987…`), V2 시험 빈 곳(`tests/test_k92_a29.py` 단언 25줄, `94a2a69b…`; 망가뜨림 40 → 58, `mutants29.json` `0df323fa…`), V3 `TK27/k925` 판정기 파일 10개 대조(E4 끝·E5 전·E6, `RV9/out/k925_judge_files.expected.sha256` `c2d83ba9…`), V4 고정점에 고정판 sha만, V5·V6 글. 구동기 `rj29.py` = `0779ce4c…`(상수 셋만), 차이 파일 `a3354b7f…`. 고정 목록 기대 파일 `RV9/out/a29_pins.expected.sha256` `6a4a04f1…` 99줄 99/99 OK. E0 기준 `RV9/out/rj29_check29_rv.json` `354cdf19…`.
- 확인 [실행]: 작은 구현 대 후보 3,000/3,000·판정 함수 429/429(Declare 판·고친 판), N 105,574 글자 0 다름·만남 0, 고친 후보 `dry_a29.py --tag rv` static·trees·selftest 59/59·62/62·pytest 21·29·cross 5·drivercode ok·mut 58/58(WMI, 380.6 s), `check29` ok, 스냅숏 앞뒤 s02 대비 SAME.
- 지킨 것: VISSIM·COM·러너·동결·재생·plant 잡 0, 판정 함수의 실제 출력 호출 0, 커밋·브랜치·푸시 0(GWT8 head `bfd609c0`, status 0줄, K8 `b9734abe`), OUT27·OK2A·OK2C·KI·KPA·AD7·AD8·동결본·런 폴더·k92attrib·TK27 쓰기 0, 봉인 시드·s47·봉인 뿌리 열람 0, 금지 시험 0. 쓴 곳: RV9, TKR9(`tm29`), AD9 고친 파일 6개(사본 `RV9/r1/`)·`dry/rv`·`dry/logs/mut_rv.txt`, TKD9 `tc29` 후보 두 파일, SP 보충 29·_r1·.sha256 둘, 고정점, 이 LOG. python·VISSIM 0. C: 38 GB, D: 410 GB.

## 2026-10-20 18:14 +0900 — Apply A29: 보충 29 적용 시작 (E0–E6)

- 이 항목 덧붙임 전 LOG `7211ed401439accc321a030b36a68c429a850082c6a1f2f32933214c81155292`(138,046 B).
- 근거 [실행 sha]: 보충 29 고정판 `4bd6dc8de8b0a4a4ab0b8703c07d7a73d244c4a622b81585f06dc69d6d83599d` = `.sha256`, 고정점 `KB/AMENDMENT29_FIXED.md` `3ba1d0bdaab8a0189f903d10fc1024baed770080542cbd841f79d3a56df58e43`(고정판 sha 64자를 담음), 결정 기록 `abe3cc058b7369148b28e9ccb9a9cff1a49dfd34bd30e01599ef48f5932395af`.
- 시작 상태 [실행]: GWT8 head `bfd609c0`(K9-2-4), K8 `b9734abe`, status 0줄, `OK2/a29`·`TK/a27/k925` 없음. python·VISSIM 0. C: 38 GB, D: 410 GB.
- 이 단계의 점검 도구·출력 폴더 = `KB/a29impl`(AI9, 판정에 쓰지 않음). 할 일: 보충 29 §7 E0–E6 차례대로(커밋 K9-2-5, 관문 P0–P8, 다시 비교 rc_g2·rc_g4). 새 재생·VISSIM·plant 잡 0, 푸시 0.

## 2026-10-20 18:21 +0900 — Apply A29: E0 사전 확인 통과, E1 고정

- E0 [실행 `KB/a29impl/e0_check.py`, WMI 분리 태그 `a29_E0`, 출력 `KB/a29impl/out/e0.json` `a4732f0b9fee7289f3acdbdb8ac68365f424a1039527acffe0b1549344ffcadf`]: `ok` 참. 보충 29 = `.sha256` = 고정점(고정점 자기 sha `3ba1d0bd…8e43`), 결정 기록 174줄 = `abe3cc05…`, §0 문서 31개 sha 같음, LOG 앞부분 넷(127,673·132,793·135,650·138,046 B) 같음(덧붙임만), `a28_pins` 49/49·자기 sha `2427e2dd…`, 기대 파일 `RV9/out/a29_pins.expected.sha256` 99/99 OK·자기 sha `6a4a04f1…`·CR 0·1–49줄 = a28_pins 바이트·50–99줄 값이 보충 29 글 안에 있음, GWT8 head K9-2-4·커밋 5개·status 0줄·원격 추적 없음·K8 `b9734abe`, `OK2/a29`·`TK/a27/{k925,u29_k924,u29_k925,m29_k925}` 없음, `rj29.py check29 --dest AD9/dry/rj29_check29_impl.json` 종료 0·`ok` 참(106.8 s)·`when` 밖 칸 = `RV9/out/rj29_check29_rv.json`(정규 JSON 같음), AD9·TK27 `__pycache__` 0. 출력 `AD9/dry/rj29_check29_impl.json` = `758120771154929a324f3312ca02cf7f06c136d8ea379e5798df2a54f710024f`. python·VISSIM 0(발사 전·끝). C: 37.4 GB, D: 409.6 GB.
- 스냅숏 `OK2/snap/s21_a29_E0.json` `ef2c3f2158a50c86accc83f731fa6d2626137a12303d5cb2a653cd46cd1cbe01` 대 s02: SAME [실행 `KI/k92snap.py diff`].
- **E1 고정** [실행]: `KB/a29_pins.sha256` = 기대 파일 복사, `cmp` 같음, **sha256 `6a4a04f189f5e5a842affffae32b02e56a3425873ee2817d181e9f567073cc43`, 99줄**, CR 0, `sha256sum -c` 99/99 OK·종료 0(`KB/a29impl/out/pincheck_E1.txt`). 구동기 `AD9/rj29.py` = `0779ce4c62cbf6e9de5597efc1d69dd932c570dd8620e3605de5ce00dee489bd`(51줄). 고정 창 시작(E1 → E6 끝 대조).
- [2026-10-20 18:20 +0900] 보충 29 커밋(rj29.py, 자동 기록): K9-2-5 = `e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d`, ok=True, 파일 7개 블롭 = 선언 값 True, 푸시 0.

## 2026-10-20 18:21 +0900 — Apply A29: E2 빈 돌리기, E3 커밋 K9-2-5

- 고침(덧붙임): 바로 위 "E0 … E1 고정" 항목 머리의 시각 "18:21"은 실제로 쓴 시각이 아닙니다. 실제로는 18:19 KST에 썼습니다 [실행 `date` 18:19:51 = 그 직후의 발사 전 대조]. 내용은 그대로입니다.
- E2 [실행 `rj29.py commit --dry-run`, 18:19:40, `OUT29/logs/rj29.log`]: `FRONT_CHECK` 6점검 참·커밋 5개, `EXPECT` 7파일 sha 앞 16자 = 보충 29 §2.7 후보(`3e2da987`·`fb79ed57`·`d4ab3f3d`·`cb816eab`·`0e39d5f8`·`752aada0`·`94a2a69b`), `msg_sha256` = `a8545b2d279da75234f835d0e7a16ad1dc63d8d614bde1ab42ec581bfb577f77`(고정점 값), `DRY RUN: no change`, GWT8 head `bfd609c0`·status 0줄 그대로.
- E3 [실행]: 발사 전 대조 `KB/a29impl/out/pincheck_E3_pre.txt` 99/99 OK·종료 0·목록 sha `6a4a04f1…`. `rj29.py commit`(18:19:58–18:20:04): **K9-2-5 = `e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d`**, 부모 K9-2-4 `bfd609c0`, `OUT29/commit_k925.json` `ok` 참(`3096db9d757dc83e6d5af2bb2caf69c123a638d898a3b8e0b7f1c473b31f5bfa`). 파일 7개 ls-tree 블롭 = 작업 바이트(`hash-object --no-filters`) = 선언 블롭(`2b2b5523`·`79f0790d`·`01bff8a8`·`1e345e86`·`b65acea0`·`1899b60c`·`b1b4605f`). 이름·상태 = M 다섯·A 둘(§3.1-5). 작성자 = 커밋터 = `Ming2you <alsrjsrb1915@snu.ac.kr>`. 메시지 바이트 `OUT29/commit_msg_K9-2-5.txt` = `a8545b2d…`(1,644 B), 끝 줄 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. status 0줄, K8 브랜치 `b9734abe` 그대로, 원격 추적 참조 없음, **푸시 0**. 명시 경로 7개만 `git add -- <경로>`, amend·rebase·force 0.
- [2026-10-20 19:16 +0900] 보충 29 구동기: K9-2-5 관문 끝(rj29.py, 자동 기록): pre5=PASS, trees5=PASS, diff5=PASS, pycompile5=PASS, jb5=PASS, selftest5=PASS, U5=PASS, mut5=PASS, rold5=PASS. 판정 파일 `D:\VISSIM_runs\20261001_v3c3\reports\k8\k92_b1\a29\gates.json` sha256 `d7192982ab8bda8c4af02d052acb2c952076e12f14859107d556d3e0ec843a7f`.

## 2026-10-20 19:18 +0900 — Apply A29: E4 K9-2-5 관문 P0–P8 모두 PASS

- 발사 전 대조 `KB/a29impl/out/pincheck_E4_pre.txt` 99/99 OK·종료 0. WMI 분리 `KI/launch.ps1 -Tag a29_gates -Script ..\a29decl\rj29.py -ArgLine gates`(18:21:00, cmd PID 23176, BelowNormal; python·VISSIM 발사 전 0). 끝 19:16:27, 태그 로그 `OK2/logs/a29_gates.txt` `154cc94013a9e82d82df62c9ea00436ce17f1ad8b47013ed03062713e50f7c6f`.
- 결과 [실행 `OUT29/gates.json` `d7192982ab8bda8c4af02d052acb2c952076e12f14859107d556d3e0ec843a7f`]: pre5·trees5·diff5·pycompile5·jb5·selftest5·U5·mut5·rold5·after5 = **10단계 모두 PASS**, STOP 파일 0. trees5: `TK/a27/k925`·`u29_k924`·`u29_k925`·`m29_k925` 만듦(각 약 47 s), 차이 = 바뀐 5 + 새 2, 판정기 7파일 sha = 후보, 트리 자리 참. jb5: `OUT29/k925_blobs.json`(19개) `3a8f24cd85afab288f55a2e0105a47457a150842a3deaae8c5b5bcedf99e8112`. selftest5: k92_a27 59/59, k92_a29 62/62, 자식 프로세스 0. U5: 바탕 293·새 301, 겹친 293 같음, 새 8 통과, 한쪽에만 0, 두 쪽 같은 옛 실패·건너뜀 10(`known_failures_same`, pytest 종료 1 두 쪽). mut5: 58/58 잡음, 되돌림 참, 끝에 `m29_k925` = `k925`. **rold5: 184쌍 모두 PASS(무리 K 162, R 22)**, 쌍마다 K9-2-5 판정 = 기록 R6 판정 = PASS, 기록 판정 파일 행 = 기록 원본 행, 자식 입력 sha = 선언 `f2029d6e…`·확인 참·명령줄 3,317자·1,816 s, A_K92 항목 101. after5: head = K9-2-5, status 0줄.
- E4 끝 대조 [실행 `KB/a29impl/pincheck.sh E4_end judge`]: 고정 목록 99/99 OK, **판정기 트리 `RV9/out/k925_judge_files.expected.sha256` 10/10 OK**·종료 0. 점검 `KB/a29impl/stage_check.py E4` → `KB/a29impl/out/e4.json` `59ae4773fd71454f783d70f1b4b0c863963e8b1a7ce9b19594ea26bc4e4e1037` `ok` 참.
- 스냅숏 `OK2/snap/s22_a29_gates.json` `a57819dc83cddca14e186fce90389e592a2bb56e7a236ff907bcefd505412e9e` 대 s02: SAME. python·VISSIM 0. C: 37.4 GB, D: 401.4 GB.
- [2026-10-20 19:21 +0900] 보충 29 구동기: 다시 비교 끝(rj29.py, 자동 기록): rc_g2=PASS, rc_g4=PASS. 판정 파일 `D:\VISSIM_runs\20261001_v3c3\reports\k8\k92_b1\a29\gates.json` sha256 `129b642d4a53be61f520b26ac9a07f9d29a4de6ae74bdfc6b92eb498d9083f49`.

## 2026-10-20 19:24 +0900 — Apply A29: E5 다시 비교 rc_g2·rc_g4 PASS

- 발사 전 대조 `KB/a29impl/out/pincheck_E5_pre.txt` 99/99 OK, 판정기 트리 `judgecheck_E5_pre.txt` 10/10 OK, 둘 다 종료 0. WMI 분리 `KI/launch.ps1 -Tag a29_rc -Script ..\a29decl\rj29.py -ArgLine rc`(19:18:17, cmd PID 26664, BelowNormal; python·VISSIM 발사 전 0). 끝 19:21:41, 태그 로그 `OK2/logs/a29_rc.txt` `8abf81d1e5f334c82163dca3c2c5f7565063b6b5ed1decb0abf21237ccfbf545`. 새 재생 0.
- **rc_g2 PASS** [실행 `OUT29/gates/rc_g2.json` `959a4f013c39066709cdacf5ae3b0ecaceb4fa5afa9a3df664022fa48b342ac5`]: 9칸 모두 PASS = 기록 판정 줄(9 PASS); 칸마다 `same29` 참, K9-2-5 판정 = 기록 = PASS, 전체 결과 PASS·미분류 0; A_K92 항목(1·2·1·2·1·2·2·0·2개) 모두 `old_is_root_rs` 참. 입력 점검 `OUT29/rc_g2_pre.json` `0b450cf9…4c94` 참. 자식 입력 sha = 선언 `c0523271…`, 확인 참, 명령줄 1,990자.
- **rc_g4 PASS** [실행 `OUT29/gates/rc_g4.json` `d8c4a3e811bcaed8667a7fa822a2f2059c99642bf50b0db41e8dbd1f19820517`]: 결정 8행 — B1 4행 K9-2-5 판정 PASS = 기록, W 4행 K9-2-5 판정 보류 = 기록 K9-2-4 판정(미분류 1·2·1·2), A28-W 11점검 참 + 점검 12 참(A_K92 항목 1·2·1·2개, `old_is_root_rs` 참) + A28-W 기록 여섯 칸 같음 → 최종 PASS = 기록; 8행 모두 `same29` 참. plant 4행 바이트 이어받음(기록 판정 = 기록 관문 행, `parts` = 원래 gk4, `plant_source_same` 참, jb5 PASS) → PASS. 12행 최종 판정 줄 = 기록(12 PASS), 묶음 판정 PASS = 기록. 입력 점검 `OUT29/rc_g4_pre.json` `3e66c471…15a9` 참. 자식 입력 sha = 선언 `cbbd1edd…`, 확인 참, 명령줄 1,889자. 봉인 뿌리 열람·sha 0.
- `OUT29/gates.json`(P0–P8 + rc 둘) `129b642d4a53be61f520b26ac9a07f9d29a4de6ae74bdfc6b92eb498d9083f49`. 점검 `KB/a29impl/stage_check.py E5` → `KB/a29impl/out/e5.json` `ee1f057ee7c228691f87ec6269223ab9292a88d66f1a69955b622966f09d6354` `ok` 참.
- 스냅숏 `OK2/snap/s23_a29_rc.json` `5e2f363baa899e447d197fdc49f50a30b2a8069bbdccc2829d90838533d8fb87` 대 s02: SAME. python·VISSIM 0.

## 2026-10-20 19:28 +0900 — Apply A29: E6 마무리 (보충 29 적용 끝, STOP 없음)

- 이 항목 덧붙임 전 LOG `4539c08a3ee097465f4ed4f275c25ef2d22ff29801ade5103e934f86e711e548`(147,269 B).
- E6 끝 대조 [실행 `KB/a29impl/pincheck.sh E6_final judge`]: 고정 목록 `KB/a29_pins.sha256` 99/99 OK·종료 0·목록 sha `6a4a04f1…`, 판정기 트리 10/10 OK·종료 0·목록 sha `c2d83ba9…`. 고정 창(E1 → E6) 안의 대조 6번·판정기 트리 3번 모두 OK.
- GWT8 [실행 `KB/a29impl/stage_check.py E6` → `out/e6.json` `d150617190b79a521eb980b65103354e3c37283061918e59386db8b8cd431e1d`]: head = K9-2-5 `e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d`, `b9734abe..HEAD` 커밋 6개, status 0줄, K8 브랜치 `b9734abe` 그대로, 원격 추적 참조·상류 없음, **푸시 0**.
- `KB/IMPLEMENT.md` 여섯째 시도 절 덧붙임(앞 38,400 B = `8b763911…4635` 그대로) → `5bb9e0ce42d187726528ec45edf974e3583a688946d7022a1c81c8d8acfc8c5b`. 보고 `KB/APPLY_A29.md` = `98fe61c3b76a476541419a9ec1e5942e38424abaf79ebf8bddcba099df6fd460`(25,246 B, CR 0).
- 요약: E0–E6 통과 조건 모두 참. K9-2-5 관문 P0–P8 PASS. 다시 비교 판정 = 이전 판정: R-old 184/184 PASS, RJ-G2 9/9 PASS(rc_g2), RJ-G4 12/12 PASS(rc_g4). VISSIM·COM·러너·동결·재생·plant 잡 0, 봉인 시드·v3c3-s47·봉인 뿌리 열람 0, 금지 시험 0, 내가 끈 프로세스 0. 끝에 python·VISSIM 0. C: 38 GB, D: 402 GB.

## 2026-10-20 19:38 +0900 — VerifyImpl r3: 독립 검증 시작 (K9-2-5 커밋·보충 29 다시 비교)

- 이 항목 덧붙임 전 LOG `855c977e85b638bb5f6857ce2748d20c55171d82699998903a5772b3a1d9234d`(148721 B).
- 고정점 [실행 sha256]: 결정 기록 `abe3cc05…95af`, 보충 29 `4bd6dc8d…599d`(고정점 29 표 값과 같음), 보충 24–28 = 기록 값. GWT8 head = K9-2-5 `e27ceac8`, K8 브랜치 `b9734abe`, status 0줄, 원격 추적 k92 0.
- 이 검증의 도구·출력 = `KB/vimpl_r3`(VD3). 스크래치 트리 = `TK/vimpl_r3`(만들 때만). 하네스 import 0. 봉인 시드·v3c3-s47·봉인 뿌리 열람 0. VISSIM·COM·러너·동결·재생 0.

## 2026-10-20 19:52 +0900 — VerifyImpl r3: 내 도구 고정 (다시 비교 전)

- 도구 sha256 [실행]: `*vcmp3.py` 8ce44b493c6389b37f29b643bc4a09b474e9724cd3ad946d5900c015cedb4a65; `*run3.py` 1975acf6383a0dbc333f12b699af0aaeeb05cdc344b4e47c7ab95e4891561a8e; `*launch3.ps1` b2fd086fa29afb075b10082ae6575ce7816b65fc99d74d8aa6f95fb9ee7a8ffd; `*ntable3.py` 43feabe469a34fa3155268a41f0d86abc8ad7aeb5908b04f2d2c6555ac0c9795; 
- 공개: 고정 전에 `tmp/try1.py`로 세 쌍(K_K9-2-1_Da_T000150, K_K9-2-1_Db_T000900, R_K9-2-1_g4_S2_W)을 시험으로 돌렸습니다. 코드는 고치지 않았습니다. N 표 점검 `ntable3.py` 30/30 같음.
- 본 실행: `run3.py`를 `launch3.ps1`(WMI 분리·BelowNormal·PYTHONHASHSEED=0·python -B)로 띄움. 출력 `VD3/out/items.jsonl`.

## 2026-10-20 20:00 +0900 — VerifyImpl r3: 다시 계산 본 실행 끝, N 대조 시작

- 시각 바로잡음: 바로 앞 항목 머리 "19:52"는 잘못 적은 시각입니다. 실제로 쓴 때는 19:46 무렵(발사 19:46:35 직전)입니다 [실행 `date`].
- run3 [실행, WMI PID 20764, 788.1 s]: 193항목(R-old 184, RJ-G2 9; RJ-G4 결정 8행은 R-old 무리 R의 g4 8쌍과 같은 입력). 내 판정 = 기록 판정: R-old 184/184 PASS, RJ-G2 9/9 PASS, RJ-G4 결정 8행 최종 PASS(B1 넷 PASS, W 넷 보류 → A28-W 11점검·점검 12 참). 기록과 다른 칸 0. 옛 뿌리 184+9 모두 출력에서 따로 끌어낸 값 = 목록 값.
- 출력·도구 sha256 [실행]: `*nx3.py` b4424419a8fed4f65e088d5280eb5026f89a9bd5febfdffb4bb92ab5013ef283; `*recchk3.py` e7756668892f3215e5454e58193394fcbf610527f353b4fd37bdedb88cae276f; `*out/items.jsonl` 5d400482f305d45336e1d4951ae4128ad4fbb5becd44de5a0070631bfc8f20b3; `*out/meta.json` 6a6ca440ddedbbdd2d59eacdd7433e046d19e5d1c42b30d65c599d06766c3613; `*out/done.json` 1e3bf6ae7de8c82ec94a78f92d7678a80c5382d8156c8beaee58cebe2673a4da; 
- 다음: `nx3.py`(실제 문자열 N 대조)를 WMI로 띄움.

## 2026-10-20 20:23 +0900 — VerifyImpl r3: 끝 (결함 0, 관찰 넷)

- 이 항목 덧붙임 전 LOG `e20b4799d15573fd7f2a00bd18b2e9b5a446b90863f70c3c4fd7d9fd09521c9f`(151339 B).
- 보고 `KB/VERIFY_IMPL_r3.md` = `c242792fadba4c49e8d39e111325e5c3ecf911dc7135551a0911bc510920fb8d`(29582 B, CR 0).
- N 대조 [실행 `nx3.py`, WMI `vr3_nx3b`]: 결정 JSON 282개·다른 문자열 49,872개에서 내 N = K9-2-5 정규식 N(다름 0), 내 보충 21 N = K9-2-0 정규식 N(다름 0), K9-2-4 = K9-2-5 N(다름 0). K9-2 뿌리를 담은 41파일 모두 자기 생성 트리 하나만 가리킴. 첫 실행(`vr3_nx3`)은 결과 전에 내 코드 칸 이름 오류로 멈춤(공개).
- 시험 [실행 스크래치 `TK/vimpl_r3/t925`]: 29 passed, 자체 시험 59/59·62/62. 내 망가뜨림 15개 중 14개 잡음; X12(증거 값 = 파일 sha, 핀 무시) 못 잡음 → 관찰 O-2. 첫 `mut3`는 pytest 임시 경로 길이 때문에 바탕이 실패한 무효 실행(공개, 보관).
- 합성 사례 [실행 `gap3.py`]: 목록 꼴 `k92_*` 하위 트리가 두 쪽에서 다르면 K9-2-5가 F1·F3로 허용(`k92_compare.py:463` `'/'`만 봄) → 관찰 O-1(런타임이 사전·수로만 써서 지금·k92t·V-B에 닿는 자리 0).
- 스냅숏 `VD3/out/s_vr3_after.json` 대 s02: SAME. 고정 목록 99/99, 판정기 트리 10/10. GWT8 head `e27ceac8`, status 0줄, K8 `b9734abe`, 푸시 0. python·VISSIM 0. C: 38 GB, D: 402 GB.

## 2026-10-20 21:00 +0900 — Gates: 판정 단계 k92t 준비 시작 (보충 24 §5, 보충 25–29가 k92t에 거는 규칙)

- 이 항목 덧붙임 전 LOG sha256 `f8c2b1c5…`가 아니라 아래 줄의 값입니다(덧붙이기 직전 `sha256sum` 출력과 같음).
- 고정점 [실행 `sha256sum`]: 보충 24 `d46db6dc…`·25 `4fd7b599…`·26 `8f835616…`·27 `4ce8b27a…`·28 `9881eb40…`·29 `4bd6dc8d…` = 각 `.sha256`. 고정점 파일 24 `fbc3d59f…`·25 `d1338fbc…`·26 `6edc55ac…`·27 `394ab15f…`·28 `14451cf4…`·29 `3ba1d0bd…`. 결정 기록 174줄 `abe3cc05…`. VerifyImpl r3 = 결함 0.
- 상태 [실행]: GWT8 head `e27ceac8`(K9-2-5), K8 브랜치 `b9734abe`, status 0줄, 원격 k92 참조 0. python·VISSIM 0. `OK2/k92t`·`TK/a27/k92t` 없음. C: 38 GB, D: 402 GB.
- 할 일(이 단계): k92t 구동기·판정기를 새로 짜고 데이터 전에 sha 고정 → 트리 `TK/a27/k92t`(git archive K9-2-5) → k92t 시작 기록·시작 훑기(봉인 sha 대조, 새는 줄, §3.1-3b) → J-0 → J-a(+ J 잡 벽시계 짝) → J-b → F. 커밋 관문(G-K0–G-K5)은 커밋마다 이미 돌았고(K9-2-0…3, 보충 27–29 다시 판정 포함) 다시 돌리지 않습니다. 독립 검증·D-K9-55 plant 원자료 재계산·V-B는 이 단계 밖입니다.
- 바로잡음(덧붙임): 바로 위 항목 첫 줄의 "`f8c2b1c5…`가 아니라 아래 줄의 값" 문장은 잘못 쓴 문장입니다(그런 값은 없음). 덧붙임 전 LOG는 sha256 `c696aa333a00fca03d00ba46e9759bdae9e03ba249799b02a3e3521492faf826`, 152,770 B입니다 [실행].

## 2026-10-20 21:50 +0900 — Gates: k92t 구동기·판정기 고정 (데이터 전, `OK2/k92t` 없음)

- 이 항목 덧붙임 전 LOG sha256 `d8452fcd298779ea3244b65ddc8367529a1acb43263c22c98a6c46ef15f01efa`, 154357 B.
- 새 도구(커밋 안 함) [실행 sha256]: 구동기 `KB/k92t/k92t.py` `b07ffb56789c30c8ef2f60f098ae7212fec52eec8a307b959bf26c44c6f02bec`, 판정기 `KB/k92t/k92t_judge.py` `eb4c113a6b7194cdf00d193d5faf07b426aae61a49ff84ae442bcf29b59fb28e`. 고정 목록 `KB/k92t_pins.sha256` `38a2ce147795bbe7613fa5b6633441b31b814e781d1948e550753db776ed7cdd`(56줄: 구동기·판정기, KI `launch.ps1` bf7a8132·`k92lib.py` ae5de0cc·`k92snap.py` 0dbd7d2c, `run_pytest_bn.py` fe4451e4, pre·tree 기록, `gates_k91t.json` 4e59f61d, `leader_review_k91t.json` ba80564c, V4 `vissim_ref.json` e5e3466f, `k925_blobs.json` 3a8f24cd, P0-4 두 파일, K9-1 BASE 319d07aa, 트리의 하네스·판정 파일 39개(`sa/*.py` 31 + k8common·prep·site 셋·4c 시험 넷)), `sha256sum -c` 56/56 OK.
- 판정 정의 = 보충 24 §5(J-0·J-a·J-b·F), 보충 25–29가 k92t에 거는 규칙. 데이터 전에 정한 조작화(구동기·판정기 머리말 O1–O8, 보고서에 공개): (1) J-0 "R-obs3 61"의 T=1·150은 두 팔이 같은 자리에서 실패(보충 13 G-EB-14 같은 실패 규칙)면 61/61에 "같은 실패"로 셈 — K9-1 기록상 모든 팔이 그 자리에서 실패함, (2) J-a 상태 고르기(열린 곳은 첫 상태: TL3m 900, c11 = C11 변형, "DP 훅 한 결정" = full 2700 hooks 결정)와 결정 항목은 보충 29 §6.1-3대로 k92_compare 결과 넷(옛 뿌리 = k8_gate_trees/k91t), 잡 항목은 summary 숫자 잎(G5 제외 규칙), (3) J 잡 벽시계 짝 = J-a SAF-K91 H3 잡 11개와 같은 라벨 SAF-K92b1 잡을 붙여 돌림, (4) J-b에서 BASE 산출은 k91t 복사, 단 한 코드 트리 안에서 비교되는 BASE 실행(ROBS61 T=1·150 셋 시드, TL3·T9C 2700, full BASE hooks 2700·4950)은 k92t 트리에서 다시 돌림(예외 줄에 트리 경로가 들어가 k91t 사본과는 같은 실패 판정이 성립하지 않음), SAG는 k91t 복사, (5) F를 J-b보다 먼저(보충 24 §5.1은 어느 쪽이 먼저여도 됨), (6) 봉인 뿌리 k92_record.json 훑기는 J·F 값 고정 뒤(보충 29 §5가 그 전 봉인 데이터 파일 열기를 막음; 시작 때는 봉인 파일 sha 전수 대조).
- 데이터 전 개발 점검 [실행, k92t 출력 0]: 트리 `TK/a27/k92t` = git archive e27ceac8(10,569파일, 54.5 s), `TK/a27/k925`와 바이트 같음(다름 0·한쪽 0), 판정기 블롭 19/19, VR `f3fcc574`, CR 짝(k91t `AAAAAA---X` 대 `AAAAAAAAAA`) 참, 기록 `TK/a27/k92t.build.json`. 판정기 점검 `KB/k92t/dev/devtest.py` `5886cd63…` → `devtest_out.json` `6529c07d…`: J-b 자기 비교 45/45 같음, J-0 규칙을 재실행 탐침 포착(v3c3-s31 1,500·2,850, s43 1,050·3,300·4,800; OFF 대 B1)에 대어 모두 PASS(s43 1,050에서 좌회전 묶임 감지), J-a 숫자 잎·결정 자기 비교 PASS, F 둘째 표본 표가 탐침 표와 6지표×3팔 모두 같음. 같은 실패 규칙·짝 계산 합성 시험 참. 시작 훑기 마른 실행 `dev/scans_dry.json` `bee28996…`(1,581.6 s): 봉인 12,538파일 sha 대조 다름 0, 새는 줄 0(29,324파일; 보고만 a27·a29 908파일 0), §3.1-3b 위반 0, 주 표본 산출 이름 0.
- 팔 바이트 미리 확인(메모리 안) [실행]: W 팔 `d179f01d…`, B1 팔 `65cac7ea…` = 탐침 t74 팔.
- 스냅숏 `OK2/snap/s24_k92t_before.json` `4bacbeed…` 대 s02: SAME.
- 다음: `KI/launch.ps1 -Tag k92t_chain -Script ..\k92t\k92t.py -ArgLine chain`(WMI 분리, BelowNormal) — start(시작 기록·훑기) → prep → J-0 → J-a(+짝) → F → J-b → post. 판정이 PASS가 아니면 그 자리에서 STOP.
- [2026-10-20 21:45:53 +0900] k92t 구동기: 판정 단계 시작 기록 `OK2/k92t/k92_judging_stage.json` sha256 `34e63a991451ef8c3f1be0ef6f4765f009abc19745fe7e546ffaeda43fd1aaa5` (보충 24 `d46db6dc…`, 보충 25 `4fd7b599…`, K9-2 head `e27ceac8`; 자동 기록)
- 시각 바로잡음(덧붙임): 바로 위 항목 머리 "21:50"은 미리 적은 시각입니다. 실제 발사는 21:45:53 KST입니다 [실행 `KI/launch.ps1 -Tag k92t_chain`, WMI ReturnValue 0, PID 27432(cmd), BelowNormal, 발사 때 python 0·VISSIM 0]. 표준 출력 `OK2/logs/k92t_chain.txt`. 고정 목록은 발사 전 56/56 OK였습니다.
- [2026-10-20 22:16:40 +0900] k92t 구동기: 시작 훑기 ok=True (봉인 sha 대조 True, 새는 줄 True, §3.1-3b True, 주 표본 산출 없음 True), `OK2/k92t/start/scans.json` sha256 `410fde88da1e97e0434d3df59f292a904ed87c153a17bb209ec918b7a074bfb8` (자동 기록)
- [2026-10-20 22:17:39 +0900] k92t 구동기: 읽기 전용 뿌리 스냅숏 `OK2/snap/s25_k92t_start.json` sha256 `b606745397b92858d101c6aa162d5e2004df435513c9c11046dd8ecb966a1a6b`, s02 대비 SAME (자동 기록)
- [2026-10-20 22:25:47 +0900] k92t 구동기: prep 끝 — 팔 sha = 선언 값(ja SAF-K91·BASE 319d07aa, jb SAF-K92b1 65cac7ea, f_w d179f01d), 닻 표 sha `3cc8297ac947b65d9a0ae3276dee5259725b2c884e57de281387c5dd4233c329` (자동 기록)
- [2026-10-21 00:12:53 +0900] k92t 구동기: J-0 판정 PASS (상태 105, {'PASS': 105, 'FAIL': 0, 'INCOMPLETE': 0}, R-obs3 61 = 초기화 59 + 같은 실패 2), `OK2/k92t/judge/j0.json` sha256 `24ee9d3b66d16618f9c6bc255bcabaecbcbaa2a653c985a9fb0315d68a85aab1` (자동 기록)
- [2026-10-21 03:35:14 +0900] k92t 구동기: J-a 판정 PASS (항목 23, 다름 []), `OK2/k92t/judge/ja.json` sha256 `74806cb0683582bc20eccb68eb086363a0ac0e8d100d2c6c5d48436da14b4d5c`; J 잡 벽시계 짝 PASS (깨끗 11/11, 중앙 0.9800955989161412, 문턱 1.0158), `jwall.json` sha256 `1fb5c60454169b9f10014691a9fae9aa4697ac5bd26323e146149b6600fb615a` (자동 기록)
- [2026-10-21 03:36:16 +0900] k92t 구동기: 읽기 전용 뿌리 스냅숏 `OK2/snap/s26_k92t_after_ja.json` sha256 `b922c86f6176ca6dad9f69968066a13296782bfd7d76c5ef024e731a9bacbe14`, s02 대비 SAME (자동 기록)
- [2026-10-21 07:04:31 +0900] k92t 구동기: STOP — 단계 f, 까닭 persist rc=1 (k92t.py, 자동 기록)

## 2026-10-21 07:09 +0900 — Gates: k92t STOP (F 단계, 보고용 지속성 VR rc=1), 보고서 작성

- 이 항목 덧붙임 전 LOG sha256 `545cbe167eaba0b5dab2be759d2465c34369dfad00f24f7eb0186e730ea07405`, 160460 B.
- 사슬 결과 [실행 `OK2/k92t/driver.log`·`steps.jsonl` 59줄]: start(시작 훑기 PASS, 1,845 s) → s25 SAME → prep(팔 sha = 선언 값) → J-0 PASS(105/105, 61 = 초기화 59 + 같은 실패 2) → J-a PASS(23/23) + J 잡 벽시계 짝 PASS(깨끗 11/11, 중앙 0.98010 ≤ 1.01575, 사분위 0.0304 보고만) → s26 SAME → F: 세 팔 포착·잡 각 38 ok, `f_vref` rc 0, **`f_persist` rc 1** → 구동기 O7대로 `STOP_f.json`(`ebff59c9…`). F 판정기·J-b·사후는 돌지 않음.
- 실패 진단(보충 25 §6.4 k92t 안 예외, 연 것: `OK2/k92t/logs/f_persist.log` 끝 줄 하나, 07:0x): VR이 지속성 보고용 상태 T−450의 첫 상태 T=600에서 창 (600.1, 750.1]을 헤드 1090201 주기로 찾지 못해 SystemExit. 판정 항목 밖(보고만)의 내 설계 결함 [추론: 측정 범위가 900 s 무렵부터].
- 처리: 구동기를 고쳐 이어 가면 데이터 뒤 판정 도구 변경(S-K12)이라 하지 않음. F 판정 값 없음(J·F 값 고정 전) → 봉인 로그·봉인 데이터 파일 계속 닫음. v3c3-s47 결과 값 열람 0.
- 끝 점검 [실행]: 스냅숏 `OK2/snap/s27_k92t_stop_f.json` `fabe7d5e…` 대 s02 SAME. 고정 목록 56/56 OK. GWT8 head `e27ceac8`, 6커밋, status 0줄, K8 `b9734abe`, 원격 k92 0, 푸시 0. python·VISSIM 0. C: 38 GB, D: 396 GB.
- 보고서 `KB/GATES_K92B1.md` = 사본 `OK2/GATES_K92B1.md` sha256 `63dd35e29ced298c9e7538f0aeefe7e48871e6197285b3994fa2e51683a03b60`. 사용자 결정 대기(Q1 이어 가는 방법, Q2 조작화 1·5·7).

## 2026-10-21 07:12 +0900 — VerifyGates: 관문 보고 독립 검증 시작 (GATES_K92B1.md `63dd35e2…`)

- 이 항목 덧붙임 전 LOG sha256 `deacc2f2ba502a3fb84b4f4c092cc6cec1df652172761780a94bae2a24dbe35f`, 162223 B.
- 고정점 [실행 sha256]: 보충 24 `d46db6dc…`·25 `4fd7b599…`·26 `8f835616…`·27 `4ce8b27a…`·28 `9881eb40…`·29 `4bd6dc8d…` = 각 `.sha256`·고정점 표. 결정 기록 `abe3cc05…`. 보고서 `GATES_K92B1.md` `63dd35e2…`. 고정 목록 `k92t_pins.sha256` 56/56 OK.
- 상태 [실행]: GWT8 head `e27ceac8`, K8 `b9734abe`, status 0줄. python·VISSIM 0. C: 37.5 GB, D: 395 GB.
- 이 검증의 도구·출력 = `KB/vgates`(VG). 스크래치 트리 = `D:/VISSIM-merge/k8_gate_trees/k92b1/vgates`(필요할 때만). 하네스 import 0(재실행 잡은 하네스를 자식으로만 부름). 봉인 시드·봉인 로그·봉인 데이터 파일·v3c3-s47 결과 값 열람 0. VISSIM·COM·러너·동결 0.

## 2026-10-21 07:58 +0900 — VerifyGates: 내 도구 고정 (재계산·재실행 데이터 전)

- 이 항목 덧붙임 전 LOG sha256 `afebed86b82b75a3d658f2fa80ec4c80ec015aace980239c9dc549e4b89bf6ab`.
- 도구 sha256 [실행] (`KB/vgates`, 하네스 import 0; 재실행만 하네스를 자식으로 부름): `vglib.py` 1ea9760545a554d1d50109dd8c09939ad982792a0fe19745dc5e0329de56efd4; `vg_rerun.py` 844480ae22df811c04bb2cd4abbb3715a3e73120a7567c695cc17a2c052e2bbb; `vg_cmp.py` 3ec44fc9b5f0601a7376088c0c6970dcb220aa0e2aa0626682a8b31c4dc6c689; `vg_j0.py` 87edb5983ca8fd87cb46b4df901e6ed37b17311ab9a2e137750bb12b809d863f; `vg_ja.py` ffa3d2dc81c1821b1887d60bb523523230bc99e5bf07fd6304e754439836bf70; `vg_scans.py` a93c02656f6e24545db193940edfccd590cf2cbbb9c12734077843a9af71d9b2; `vg_commit.py` 47f75a8f97989b59c38fd39d232f8f5b370616ec183a86325a47347e08291fde; `vg_f.py` c2a0f80b64accc6997e85e7f717c936f878f79f7bc9581cce8cf63d56f0d51e5; `vg_vr600.py` 2bc56d6db8d32150f4cabcc67640191716de38c304209ffa8da601ff15c6a7f7; `vglaunch.ps1` 78c34844badb11eaa513b8e01a8661b17074b441d15cfea258d89aa123ff839b. 목록 `KB/vgates/vg_pins.sha256` aff9d36684896aa9d093aec9335cc955eaa1c9a482e28ee70cec1e7d50e34b6a.
- 고정 전 개발 점검(공개): N 합성 문자열 9/9, 규칙 함수 합성 점검, K9-1 결정 파일(`V4/sa/full/k91t/002700_SAF_hooks`) 자기 비교 차이 0. k92t 산출은 아직 열지 않음(판정 파일 `ja.json`의 항목 이름·허용 분류 개수만 읽음).
- 재실행 둘(블라인드 때문에 s47 주 표본은 고르지 않음): J = jb(SAF-K92b1) `TL3_900_SAF_OBS_H3`(J-b가 판정할 tl3 SAF 잡과 같은 잡), F = f_b1 `TL3_1050_s43_SAF_OBS_H3`(둘째 표본). 출력 뿌리 `OK2/vg2t`(새 폴더, 'k92t'와 같은 글자 수). 비트 동일 규칙은 `vg_cmp.py` 머리말(데이터 전 고정).
- 시각 바로잡음(덧붙임): 바로 위 항목 머리 "07:58"은 잘못 적은 시각입니다. 실제로 쓴 때는 07:28 무렵입니다 [실행 `date` 07:29:34]. 고정 sha는 그대로입니다.
- [2026-10-21 07:32 +0900] VerifyGates: 도구 하나 더 고정(데이터 전) `vg_tree.py` 5a969f7be9b849045be837fd8a21ddb238168b1cd945eb7bf790ad45ba4884fc (k92t 트리 대 커밋 e27ceac8 블롭 전수 대조). 목록 `vg_pins.sha256` 덧붙임 뒤 dc52f7d7f2be9142d13dd84cbd005a68e9ab6a7e42407bd5c446f3b609daa861.
- [2026-10-21 07:36 +0900] VerifyGates: 재실행 둘 끝(`OK2/vg2t`, rc 0 모두, VISSIM 0) → 고정 비교기 `vg_cmp.py` 판정 **DIFFERENT**(J·F 모두; `KB/vgates/out/rerun_cmp.json` 3988be6efb49513282032f12e008ee79e7ddce1bdcb6d5b1dd333becd3184f3f). 판정은 바꾸지 않음. 데이터 뒤 진단 도구 `vg_cmp_diag.py` a384c2c1ea712000d12e0090a4f7c47c331154ea1c01a0a3653dad6f810bfa90를 고정(공개: 비교 결과를 본 뒤 만든 설명용 도구, 판정 도구 아님).
- [2026-10-21 07:37 +0900] VerifyGates: 데이터 뒤 진단 도구 `vg_cmp_diag2.py` 681690a6a4012fb970c2f75413746b291ab45afb02fabe233db0bcee181db711 고정(공개, 설명용). 진단 1 출력 `out/rerun_diag.json` 08c3139aefa62b4c218b692916b15862a56371b04e7798760e98868344a45215.
- [2026-10-21 07:37 +0900] VerifyGates: `vg_cmp_diag2.py` 첫 실행은 내 도구 결함(셸이 백슬래시 하나를 먹어 뿌리 바꿈이 작동 안 함; `obs150_equal_after_swap` 거짓은 무효)로 공개하고 보관. 고친 사본 `vg_cmp_diag2b.py` 3ec7614af485943f2537e38862a42c7cd79ae010ffec2d470c4b3f0638e36a95 고정(설명용, 판정 도구 아님).
- [2026-10-21 08:19 +0900] VerifyGates: 고정 도구 `vg_ja.py` 결과(`out/ja.json` e2dfecf34b11a742a56084c96ed89c598965befa8fd717e7895e6e999a4b6212) = J-a 잡 21 SAME, J 짝 PASS, 결정 2 HOLD(미분류 4 = CAO 2·RS 2). 원인 = 내 도구 결함: 사전 키에 '/'가 든 경로('<root>/evaluation/…')를 문자열로 다시 찾아 값이 None이 됨(`vg_ja.py:113-125`, :250). 데이터 뒤 고친 사본 `vg_ja2.py` eb0dacbc6e037142e5900df9aefe12d9e7b1c1e082cffe95190584b5976c44ae(키 묶음으로 찾기 + 분류별 경로 보고만 더함) 고정. 보충 24 S-K12(독립 검증기 데이터 뒤 변경)에 해당함을 공개하고, 두 결과를 모두 보고합니다(사용자 결정 몫).

## 2026-10-21 08:27 +0900 — VerifyGates: 끝 (k92t STOP 확인, pass 거짓)

- 이 항목 덧붙임 전 LOG sha256 `21e4d19f97861ca1396feb7243564e18c3e84176e79d6fe28b5f99f93c9965f7`.
- 다시 계산 [실행, `KB/vgates`]: 커밋 관문 기록 6개 sha·단계 PASS, G-K5 중앙 0.98999·0.99505 원자료에서 같음; 시작 훑기 같음(봉인 12,538 다름 0, 새는 줄 0, §3.1-3b 0, 주 표본 이름 0, §5.4 파일 시각 참); J-0 103 PASS + 같은 실패 2(조작화 PASS, 글자 그대로 59/61); J-a 잡 21 SAME, 결정 2 PASS(고친 사본 `vg_ja2.py`; 고정 도구 `vg_ja.py`는 내 결함으로 보류, S-K12 공개); J 짝 11/11 중앙 0.9800955989161412 ≤ 1.0157507938976496.
- F STOP 확인: `f_persist` rc 1만, F 판정·J-b·사후 출력 없음. 원인 = U4 측정기 T_FROM 900(창 600.1–750.1 버림). s43 T=600 다시 만들기 rc 1 같은 끝 줄, T=1050 rc 0. O7 인용은 글보다 넓지만 STOP은 보충 24 §6 INCOMPLETE·S-K12로 맞음.
- 대표 잡 다시 돌리기 2개(jb TL3_900 SAF-K92b1, f_b1 TL3_1050_s43): 고정 규칙 DIFFERENT. 차이 = 출력 뿌리 경로에서 나온 해시·시간 값뿐(진단 실행), 결정·잡 결과 파일은 같음.
- 관찰: F 잡 ok 센 방법 LOG에 없음(그 로그에 s47 SA_JOB 목적값 줄이 있음, 보충 25 §6.4 적용 범위 불분명), f_persist 열람 시각 "07:0x", TREE 실행 캐시 90개.
- 끝 점검: 스냅숏 vg2_after SAME, 고정 목록 56/56, GWT8 head e27ceac8·status 0, OUTK·TREE에 내 쓰기 0, python·VISSIM 0.
- 보고서 `KB/VERIFY_GATES_K92B1.md` sha256 `b9e90cd23975cf8234562bac1e601df49d846cb6a7886ea808bc84172db808cc`.

## 2026-10-21 10:38 +0900 — Declare A30: 보충 30 작성 시작 (D-K9-56·D-K9-57, D-K9-55 시점)

- 이 항목 덧붙임 전 LOG sha256 `09656a590ee6c8508bc2b7271066e9aabdb4bcb1fde1ba303bc2231244e14fca`, 169,011 B.
- 고정점 [실행 sha256]: 결정 기록 `K9_1_J1_NOTES_20261013.md` `eae2e6fa…`(182줄). 보충 24 `d46db6dc…`·25 `4fd7b599…`·26 `8f835616…`·27 `4ce8b27a…`·28 `9881eb40…`·29 `4bd6dc8d…` = 각 `.sha256`; 고정점 24 `fbc3d59f…`·25 `d1338fbc…`·26 `6edc55ac…`·27 `394ab15f…`·28 `14451cf4…`·29 `3ba1d0bd…`. 관문 보고 `GATES_K92B1.md` `63dd35e2…`, 검증 `VERIFY_GATES_K92B1.md` `b9e90cd2…`.
- 상태 [실행]: GWT8 head `e27ceac8`, 브랜치 `claude/k92-b1-20261016`, K8 `b9734abe`, status 0줄, 원격 k92 0. python·VISSIM 0. C: 38 GB, D: 396 GB. `OK2/k92t`는 STOP 그대로(`STOP_f.json` `ebff59c9…`, `steps.jsonl` 59줄 `7edd53c9…`, `driver.log` `8140fd2f…`, 판정 파일 j0·ja·jwall = 보고서 값, `f_vref` json `09f9194b…`, `f_persist` 폴더 없음).
- 이 단계에서 할 일: 보충 30 글 + 이어 하기 구동기·판정기 후보(`KB/a30decl`, 커밋 안 함) + 데이터 없는 확인(합성 입력, 읽기 전용 점검, OUTK 파일 목록·sha) + 고정 목록 기대 파일. F 판정 값·J-b·봉인 로그 내용·v3c3-s47 결과 값은 열거나 계산하지 않습니다. VISSIM·COM·러너·동결·커밋·푸시 0.

## 2026-10-21 11:12 +0900 — Declare A30: 보충 30 작성 끝 (D-K9-56·D-K9-57, D-K9-55 시점)

- 이 항목 덧붙임 전 LOG sha256 `74f2ddcc34b092adb2418d81ee989444349b80d7da5ef50e15762656445cd5a2`, 170,431 B.
- 보충 30 Declare 판 `SP/K8_PREDECLARATION_AMENDMENT_30.md` sha256 `304719e19fc7fd0238d5cc9c4203b66b6d228892b8cb56b02b15f5054885f262`(62,957 B, 410줄, LF), `.sha256` 같은 값 [실행 `sha256sum -c` OK].
- 새 도구(커밋 안 함, `KB/a30decl`) [실행 sha256]: 구동기 `k92t30.py` `8f28171e7a3721a73f71216ca2823d179b78914dfbf70ef309a2b70fb5223ec4`, 판정기 `k92t30_judge.py` `a1937942f06cb7d7e0be400dfc367691e9e6575061ed5aa00cee370f697fe7bf`, 확인 `dry_a30.py` `c685b5bad597de6769c29178d737ec1837c18a58c31f51e3a51817e7f792901d`, 차이 `A30_DRIVER.diff` `a9d5087d81d01b50695ecc945bd6eb40579f02fb8dff9dbe5e215b797bbeaaa7`, OUTK 파일 목록 `out/outk_inventory_decl.json` `33101cd1…`(18,019파일), 기대 고정 목록 `a30_pins.expected.sha256` `7afabd03f315c8925c4a8bb1b1566d246cbfb9273470876963df9e7fe4f3d30e`(83줄, `sha256sum -c` 83/83 OK).
- 데이터 없는 확인 [실행 `dry/decl`]: static ok(함수 글 대조: 구동기 같음 17·바뀜 6·뺌 14·새 14, 판정기 같음 32·바뀜 2·새 3 = 선언), synth ok(합성 사례 S1–S8 8/8, 망가뜨림 M1–M7 7/7 잡음), drive ok(`check30 --mode decl` 거짓 0, `seal30 --dry-run` 3/3, 지속성 VR 상태 21개 1,200…7,950). WMI 분리 발사 셋(`a30decl_inv`, `a30decl_drive`, `a30decl_drive2`), BelowNormal, 한 번에 하나. 개발 출력 `dry/dev1`·`dev3`·`decl0` 보관, `dev2`와 `dev1`의 실패한 합성 출력은 지움(합성 값만; 보충 30 §0.1 공개).
- 지킨 것 [실행]: VISSIM·COM·러너·동결·VR 실행 0. OUTK 쓰기 0(파일 18,019 그대로, `steps.jsonl` 59줄), `OK2/a30` 없음, 봉인 뿌리 맨 위 다섯 그대로. F 판정 값·J-b 0. F 잡 로그 셋·`f_vref`·F 잡 폴더·봉인 뿌리 내용 열람 0(바이트 sha만). 봉인 시드·v3c3-s47 결과 값 0. 커밋·브랜치·푸시 0: GWT8 head `e27ceac8`, status 0줄, K8 `b9734abe`. 스냅숏 `s28_a30decl` `c94eb83f…`·`s28b_a30decl_after` `218a54dd…` 모두 s02 대비 SAME. python·VISSIM 0. C: 38 GB, D: 396 GB.
- 알리는 것(보충 30 머리): 지속성 보고 22 → 21상태(T=1,050 측정 불가), 검증 도구 고정 시점의 읽기(보충 24 §3.1-8 글보다 늦음), Gates 단계의 F 잡 로그 걸러 읽기로 v3c3-s47 목적값이 화면에 나왔을 가능성.

## 2026-10-21 11:29 +0900 — ReviewDeclare A30: 보충 30 반박 검토 시작 (Declare 판 `304719e1…`)

- 이 항목 덧붙임 전 LOG sha256 `cfebe3c598abd03f123680aac0fd940c3d9794bb55c40210f472e813dcf00f0b`, 172,925 B.
- 고정점 [실행 sha256]: 결정 기록 `eae2e6fa…`(182줄), 보충 24–29·고정점 24–29 = 보충 30 §0 값, `GATES_K92B1.md` `63dd35e2…`, `VERIFY_GATES_K92B1.md` `b9e90cd2…`, OUTK 이어 받는 기록 11개·`steps.jsonl` 59줄·`driver.log` 3,434 B·F 잡 로그 셋(바이트 sha만) = §0. python·VISSIM 0. C: 38 GB, D: 396 GB.
- 이 검토의 도구·출력 = `KB/a30review`(RV30). 데이터 전 고정 [실행 sha256]: `rv_leak30.py` `3b7ece0e27075a5fb5abc3cb00d074a7144079ff6e4e827c67f4f11426845983`(봉인 뿌리 밖 k92t 출력의 v3c3-s47 목적값 줄 훑기; 보충 25 §6.5-4 정규식 + F 주 표본 라벨 좁은 규칙; 파일 이름·개수만, 줄 내용 0; F 잡 로그 셋·s47 F 잡·포착 폴더·`f_vref`는 열지 않음; 세션 기록은 보고만), `rvlaunch.ps1` `ecbbd276612bebd24cf964b202ef5da1e3f94884100ba7fa7fa7d95c5196de49`(WMI 분리·BelowNormal·`PYTHONHASHSEED=0`·`python -B`, `VG/vglaunch.ps1`의 머리말 두 줄만 바꾼 사본).
- 하지 않는 것: VISSIM·COM·러너·동결·결정 재생·plant 잡·VR 실행 0. OUTK·TREE·봉인 뿌리·GWT8 쓰기 0. F 잡 로그·봉인 로그·s47 F 데이터 폴더·`f_vref` 내용 열람 0. 커밋·푸시 0.
- [2026-10-21 11:35 +0900] ReviewDeclare A30: 스냅숏 `RV30/out/snap_rv30_before.json` `88762891f17c31e3…` s02 대비 SAME. 훑기 `rv_leak30.py`(WMI 분리 `rv30_leak`, 125.6 s) 끝 → `RV30/out/leak30.json` `d844c450bfa30a57e3214a1710ad973373a58aa4248f19ebee5de7d6550bbd75`: 대조 문자열 5/5; OUTK(제외 1,060파일 = F 잡 로그 3 + s47 F 잡·포착 폴더 1,056 + `f_vref` 1) 15,940파일에서 F 주 표본 목적값 줄 0, 보충 25 §6.5-4 규칙 줄 3(`logs/ja_pairs.log` 2·`ja_jobs.log` 1 = J-a TL3_900 s47, K9-1 판정 상태), 주 표본 이름 경로 0; `OK2/logs`·`vg2t`·`OK2/*.md`·KB(96,842)·SP `*.md` 0; 세션 기록(10-21 03:30 뒤 7파일, 보고만) F 주 표본 목적값 줄 0·K92T_JOB 주 표본 줄 0(규칙 줄 30 = 판정기 합성 대조 글 등). 줄 내용 출력 0.
- [2026-10-21 11:36 +0900] ReviewDeclare A30: 도구 둘 더 고정(데이터 전): `rv_cmds30.py` `620b182a79dd83c39c257f792a0bc113f045177fef7a781a597c92b71f349102`(세션 기록에서 F 잡 로그를 건드린 명령 글만 찾고 결과는 길이·s47 있음·규칙 개수만), `rv_c6path.py` `6ccc7a5b9d9f82b43d998c06040a2243939d99043fb2ca116cf6474257e32f75`(launch.ps1 경로로 돌 때 check30 C6 글자 대조).
- [2026-10-21 11:44 +0900] ReviewDeclare A30: `rv_cmds30.py` 결과(세션 기록의 명령 글만; 결과 내용 0) `out/cmds30.txt` `7b06b7eb5d50114a4057f0652464dbb9d547117ac402f36fcfa1a6a0d8812e23`, `out/cmds30_main.txt` `4e93cd2a62e6cb8ed8b5616a9d642df90a53b618b2d54b713c4b13a3175a2a63`: Gates 하위 에이전트가 07:04:42 KST에 `cat STOP_f.json`·`tail -c 1500 logs/f_persist.log`·`tail -c 300 logs/f_vref.log`(실패 진단), 07:05:57 KST에 세 F 잡 로그에 `grep -c '^K92T_JOB'`·`grep '^K92T_JOB' | grep -c 'ok=True'`(개수만 출력, 결과 554자, 's47' 글자 0)을 돌림. 그 밖에 F 잡 로그 내용을 걸러 읽은 명령 0(VerifyGates·Declare는 sha·stat만, 메인 세션 0). 코드만 보는 `rv_static30.py` `d4580322ddcf1882f313fc23469ed7171444b4121b62be747e746dacb02ff35e` → `out/rv_static30.json` `4af9b5357b73c0c6f09c0b78fa5c6825b8a8d8b60a2cb1b4bb46ec626421441f` ok(함수 글 같음·바뀜·뺌·새 목록 = 보충 30 §3.2·§3.3, 지속성 상수 = §2.2).
- [2026-10-21 11:44 +0900] ReviewDeclare A30: 도구 고정(데이터 전) `rv_labels30.py` `a42dd24d17cd98c12dadeca5b87966297d9f7507fcb9391b20f5edab9b3346aa`(OUTK에서 닫힌 F 데이터 목록 밖 파일이 F 주 표본 라벨·태그를 담는지, 값 키 이름이 함께 있는지; 경로·개수만).
- 시각 바로잡음(덧붙임): 바로 위 두 줄 머리의 "11:44"는 잘못 적은 시각입니다. 실제로 쓴 때는 11:37 무렵입니다 [실행 `date` 11:37:22]. 그 위 "11:35"·"11:36" 두 줄도 미리 적은 시각이며 실제는 11:32(훑기 끝)와 11:37 사이입니다. `rv_labels30.py`는 11:37:16 WMI 분리 발사(`rv30_labels`, PID 27620)이고, 고정 sha를 LOG에 적은 뒤입니다.
- [2026-10-21 11:39 +0900] ReviewDeclare A30: `rv_labels30.py`(WMI 분리 `rv30_labels`, 123.0 s) → `out/labels30.json` `d0cb9472b4f2b376dd64c14df051cca9d27ddd42485e0f3667fe174840395bea`: OUTK에서 닫힌 F 데이터 목록·F 잡 로그 셋 밖 16,959파일 가운데 F 주 표본 라벨·태그를 담은 파일 6개 = `logs/f_f_{off,w,b1}_cap_s47.log`(SA_CAPTURE 줄의 출력 경로) + `specs/f_f_{off,w,b1}_jobs.json`(잡 계획 라벨), 값 키 이름 0. 도구 고정(데이터 전) `rv_vr30.py` `11def0feee29c19d179bf5f21db62df6d852e9681cc9ed9c36db5d882f7d77b3`(보충 30 §2.3과 같은 VR·같은 21상태·같은 단계 인자를 v3c3-s43에; 출력 `TK/a30review/vr_s43_21` 새 폴더; rc·초·상태 열쇠·정수 여부만, VISSIM 값 출력 0).
- [2026-10-21 11:45 +0900] ReviewDeclare A30: `rv_vr30.py`(WMI 분리 `rv30_vr`) → `out/vr30.json` `7dd617e75b75b571125160bddf61978ff6061b8c8dc41a8bb9a4a337901ab43f`: 보충 30 §2.3과 같은 VR 호출을 v3c3-s43에 — rc 0, 23.6 s, 21상태 모두 있음, `m1_T450` 모두 정수(값 출력 0, v3c3-s47 0). 다음: 새 구동기 `check30 --mode decl`(읽기만, 출력 `RV30/out/check30_rv.json`)로 OUTK 파일 목록·이어 받는 기록이 검토 뒤에도 같은지 확인, 끝 스냅숏.
- [2026-10-21 11:56 +0900] ReviewDeclare A30: (11:45–11:47 실행) 새 구동기 `check30 --mode decl`(WMI 분리 `rv30_check30_decl`, 읽기만) → `RV30/out/check30_rv.json` `9df7c11f7c510ff9fa614c71d6d632cecc552cba72732ff69a80042b592d03c9`: 37점검 거짓 0, OUTK 18,019파일·4,223,333,998 B = 선언 목록(검토가 OUTK를 바꾸지 않음). 끝 스냅숏 `RV30/out/snap_rv30_after.json` `11060d6b70244fdf90b460802f9f45549b922d5bccef8c76f257181f5ad00d1e` s02 대비 SAME.

## 2026-10-21 11:55 +0900 — ReviewDeclare A30: 보충 30 고정 (반박 검토 끝)

- 이 항목 덧붙임 전 LOG sha256 `35ea2fb49837fe582a0ec7cd9febe0deb04c77cd4c2d5626472a3504a39650e3`, 178,592 B.
- Declare 판 보존: `SP/K8_PREDECLARATION_AMENDMENT_30_r1.md` + `.sha256`(`304719e1…`, Declare 판과 같은 바이트), 사본 `RV30/r1/`.
- **고정판** `SP/K8_PREDECLARATION_AMENDMENT_30.md` sha256 `ba556227a6356b1733bfa8125b334cfef180c1eed97e8d69ae4ba53a3106a56a`(83,288 B, 476줄, LF), `.sha256` 같은 값 [실행 `sha256sum -c` OK]. **고정점** `KB/AMENDMENT30_FIXED.md` sha256 `ad3fafadd59985b3b71f33d5523ceb2324aa8267395d7280039228669cb83e9c`(고정판 sha 64자 + 기대 고정 목록 `KB/a30decl/a30_pins.expected.sha256` `7afabd03f315c8925c4a8bb1b1566d246cbfb9273470876963df9e7fe4f3d30e` 64자; Declare 판 sha는 16자만). 구동기 자신의 `a30_sha()` = `ba556227…`, C6 같은 뜻 참(83줄·틀린 줄 0) [실행 `RV30/rv_fixcheck30.py` `4952b5d3b6a28aacc479e65a39bb4c8621db142eaf58685bb87861758ef706d6`].
- 고친 곳(글만, §13.1 V1–V8): V1 Gates의 F 잡 로그 걸러 읽기 = 07:05:57 KST `grep -c` 한 번(개수만), 세션 기록 7개에 F 주 표본 목적값 줄 0 → "가능성"을 사실로; V2 07:04:42 KST 실패 진단에 `f_vref.log` 끝 300 B도 열림(값 없음); V3 §8 표에 보충 24 §5.4 끝 줄·보충 29 §5 "누가"(검증 도구 고정 시점) 더함; V4 G2 종료 코드 = `steps.jsonl` rc, STOP 파일 없는 SystemExit 끝 → G2 거짓 STOP; V5 S-K41에 `chain30` 밖 쓰는 명령; V6 `capture.json` 셈의 정확한 뜻; V7 봉인 이동 완전성 근거·목록 밖 s47 파일(재생 상태 공개)·봉인 뿌리 맨 위 여섯; V8 v3c3-s43 같은 VR 호출 rc 0·21/21. 새 구동기·판정기·`dry_a30.py`·차이 파일·확인 출력·기대 고정 목록 바이트는 그대로.
- 확인(§13.2): §0 sha 모두 같음; 지속성 좁힘은 보고 전용만 바꿈(판정 칸 줄 = 기반); F 값 계산·열람 0(파일 시각·`judge/` 셋·LOG·세션 기록·`check30` 다시); 이어 하기 가드; J-b 판정 항목 45개 값에 트리·경로 글자 0, 한 트리 안 비교 셋 = 다시 돌림 목록; STOP 규칙 ↔ 코드.
- 지킨 것 [실행]: VISSIM·COM·러너·동결·결정 재생·plant 잡·v3c3-s47 VR 0. OUTK·TREE·봉인 뿌리·GWT8·KI·AD30 쓰기 0. F 잡 로그·봉인 로그·s47 F 데이터 폴더·`f_vref` 내용 열람 0. 봉인 시드·codex 64cf 숫자 0. 커밋·푸시 0(GWT8 head `e27ceac8`, status 0줄, K8 `b9734abe`). python·VISSIM 0. C: 38 GB, D: 396 GB.
- 남은 미해결: 없음. 다음: 보충 30 §6 G0부터(Apply).

## 2026-10-21 11:58 +0900 — Gates A30: 보충 30 적용 시작 (§6 G0–G3)

- 이 항목 덧붙임 전 LOG sha256 `08c977319151fa705c78408250def2b257bc1d145175c9027c1dde3462df327b`, 181,725 B.
- G0 사전 확인 [실행 11:58 KST]: 보충 30 sha256 `ba556227a6356b1733bfa8125b334cfef180c1eed97e8d69ae4ba53a3106a56a` = `.sha256` = 고정점 `KB/AMENDMENT30_FIXED.md`(`ad3fafad…`) 안의 64자(1회), Declare 판 64자는 고정점에 0회. 결정 기록 182줄 sha `eae2e6fa…`(전체 182줄). 보충 24–29·`.sha256`·고정점 24–29 = 보충 30 §0. `KB/k92t_pins.sha256` `38a2ce14…` 56/56 OK. 기대 고정 목록 `KB/a30decl/a30_pins.expected.sha256` `7afabd03f315c8925c4a8bb1b1566d246cbfb9273470876963df9e7fe4f3d30e`(83줄, 14,537 B, CR 0) `sha256sum -c` 83/83 OK·종료 0, 앞 56줄 = `k92t_pins` 바이트. GWT8 head `e27ceac8`, 브랜치 `claude/k92-b1-20261016`, K8 `b9734abe`, status 0줄, `b9734abe..HEAD` 6커밋, 원격 k92 0. python·VISSIM 0. C: 38 GB, D: 396 GB.
- 할 일: G1 고정(기대 목록 → `KB/a30_pins.sha256`), G2 `KI/launch.ps1 -Tag k92t30_chain -Script ..\a30decl\k92t30.py -ArgLine chain30` 하나(WMI 분리), 기다림은 프로세스 유무·`OUTK/stages/*.json`·`STOP_a30_*.json`·`steps.jsonl` 이름·rc 칸만 봄(로그 걸러 읽기 0), G3 끝 대조·보고서. G-K4 plant 원자료 재계산·독립 검증·V-B·V-A는 이 순서 밖(보충 30 §6, 보충 29 §5 "누가 = k92t 독립 검증기").
- [2026-10-21 11:58 +0900] Gates A30 G1 고정: 기대 목록 바이트를 `KB/a30_pins.sha256`에 씀 — `cmp` 같음, sha256 `7afabd03f315c8925c4a8bb1b1566d246cbfb9273470876963df9e7fe4f3d30e`, 83줄, `sha256sum -c` 83/83 OK·종료 0. 이 목록이 고정하는 새 구동기 `KB/a30decl/k92t30.py` `8f28171e7a3721a73f71216ca2823d179b78914dfbf70ef309a2b70fb5223ec4`, 새 판정기 `KB/a30decl/k92t30_judge.py` `a1937942f06cb7d7e0be400dfc367691e9e6575061ed5aa00cee370f697fe7bf`(다시 고정; 보충 30 데이터 전).
- [2026-10-21 11:59 +0900] Gates A30 G2 발사: 발사 전 `sha256sum -c KB/a30_pins.sha256` 83/83 OK·종료 0(11:59:01). `KI/launch.ps1 -Tag k92t30_chain -Script ..\a30decl\k92t30.py -ArgLine chain30` → 11:59:03 ReturnValue 0, PID 9616(cmd.exe; 그 아래 python), BelowNormal(16384), PYTHONHASHSEED=0, `python -B`, 발사 때 python 0·VISSIM 0. 표준 출력 `OK2/logs/k92t30_chain.txt`(새 이름). 기다림은 프로세스 유무·`OUTK/stages/*.json` 이름·`STOP_a30_*.json` 이름·`steps.jsonl`의 name·rc·sec·VISSIM 칸만 봄.
- [2026-10-21 11:59:53 +0900] k92t30 구동기: 이어 하기 점검 ok=True, `OK2/a30/check30.json` sha256 `f5b35a857edc293b733d22b33e52f1aad4ebb5f8feabb9f38427972da90a4df9` (자동 기록)
- [2026-10-21 12:00:49 +0900] k92t30 구동기: 읽기 전용 뿌리 스냅숏 `OK2/snap/s29_a30_check.json` sha256 `4c6a44064bf66379b30309ad0b4a1020da2988106cd75dbad0c3926322ff430f`, s02 대비 SAME (자동 기록)
- [2026-10-21 12:00:49 +0900] k92t30 구동기: D-K9-57 ⑤ 봉인 이동 3파일(F 잡 로그 셋) → `OK2/sealed_s47/k92t/logs/`, 크기·sha 같음 True, 목록 `OK2/a30/sealed_k92t_index.json` sha256 `3946b3fcb2104ac5ca6a52a847e80fd6a04cccdfd7783c8e1f47cde08f47ce0a` (자동 기록)
- [2026-10-21 12:01:47 +0900] k92t30 구동기: 읽기 전용 뿌리 스냅숏 `OK2/snap/s30_a30_seal.json` sha256 `ce9d64ff5a6df725627dafc5efc2ae256327c21a962d65e61c86990cd528763b`, s02 대비 SAME (자동 기록)
- [2026-10-21 12:01:50 +0900] k92t30 구동기: F 잡 정상 수(요약·기록·포착 파일로만 셈) PASS, `OK2/k92t/judge/f_jobs.json` sha256 `26959c474c9cc0ec0b107c4d38aa260cb2f123d0b6b8094ea18ed77d90fb0666` (자동 기록)
- [2026-10-21 12:02:17 +0900] k92t30 구동기: F 판정 PASS (F-1 True, F-2 True, F-3 True, n 22; 지속성 보고 측정 21·측정 불가 ['1050']·완전 True), `OK2/k92t/judge/f.json` sha256 `04cfa2e0a9ac754bd13d5c5ca2d4cd5790acb34fda64fafdce7f7382027ac792` — F 판정 값 고정 (자동 기록)
- [2026-10-21 12:03 +0900] Gates A30 G2 진행(기다림 확인, 이름·rc만): check30 ok(11:59:53), s29 SAME, seal30 끝(`stages/seal30.json`), s30 SAME, f30 끝(`stages/f.json`; fcount PASS, `f_persist30` rc 0 22.1 s, `judge_f` rc 0; 판정 줄은 위 자동 기록). 새 `steps.jsonl` 줄 7개 rc 0·VISSIM 0/0. STOP_a30 0. 다음: s31 → jb(약 12 h). `judge/f.json` 내용은 J·F 값 고정(post30) 뒤에만 읽음(보고서 표 값용).
- [2026-10-21 12:03:16 +0900] k92t30 구동기: 읽기 전용 뿌리 스냅숏 `OK2/snap/s31_a30_after_f.json` sha256 `b1b21c0759a214382007c4d54c0358bf047c97ef50c49d9ad28b82fcce02beec`, s02 대비 SAME (자동 기록)
- [2026-10-21 14:25 +0900] Gates A30 G2 진행: `steps.jsonl`에 `jb_unit` rc=1(107.2 s, 14:21:29 시작). 구동기 `stage_jb`는 이 줄에 `must()`를 쓰지 않음(기반 그대로, "failures are read by sa_gates from the log") — 사슬은 계속 돎. 보충 30 §5.3(O7′) 글 "모든 단계 실행 rc≠0 → STOP"과의 관계를 보려고 실패 진단으로 엶(보충 25 §6.4·보충 30 §4.5 예외; F·봉인 파일 아님): 14:25 `OUTK/jb/sa/unit_k92t.log` 끝 부분(pytest 요약 줄), `V4/sa/unit_k91t.log` 끝 부분(K9-1 같은 시험의 요약, 읽기 전용 뿌리 읽기만). 목적: 실패 시험 이름·개수가 K9-1 기록과 같은 꼴인지.
- [2026-10-21 14:33 +0900] Gates A30 `jb_unit` rc=1 진단 결과(J-b 판정 데이터 전, 판정기 출력 0): [실행 로그 끝 읽음] `OUTK/jb/sa/unit_k92t.log` 요약 "2 failed, 95 passed, 92 subtests passed" — 실패 둘 = `test_stopline_wiring.py::ConfigFlagTests::test_default_output_is_byte_identical`·`::test_arms_add_exactly_the_key`(둘 다 `make_config_n31.build()` 바이트 = TREE `config_n31_v2.json`인지 봄). K9-1 같은 시험 `V4/sa/unit_k91t.log` "97 passed". [실행 sha] TREE·K925·`git show e27ceac8:` 의 `config_n31_v2.json` = `d0f9ef39…`(stopline_approach 있음; K8-7 `dad555ba`가 SAF-K91 바이트로 올림, K8-10 `b9734abe`), k91t 트리(1617ab24) = `319d07aa…`(없음). 그래서 이 실패는 K9-2 커밋이나 이번 실행이 만든 것이 아니라 K8-7 승격 뒤 트리의 구조 차이로 봄 [추론]. [읽음 `sa_gates.py:251-275`, `:321-323`, `:1246`, `:1640-1642`] 판정 단위 항목의 이름 패턴(KeyAbsent·ContiguousWalk·PostService·Tangent·T9b·T9c)에 실패 둘이 걸리지 않음 → J-b 판정 잎에 들어가지 않을 것으로 봄 [추론; J-b 판정기가 정함]. 구동기는 이 줄에 STOP하지 않음(기반 `stage_jb` 그대로). 그러나 보충 30 §5.3 글 "새 구동기의 모든 단계 실행은 rc ≠ 0이면 STOP(INCOMPLETE)"에는 걸림(보충 24 §6 INCOMPLETE 정의 "출력 없음·실행 미완"에는 걸리지 않음). 처리: 고정된 G2 순서(사슬 하나)를 끊지 않고 그대로 두며(끊는 일은 선언 밖, J-b 산출은 봉인·블라인드를 열지 않음), 이 어긋남을 보고서에 STOP 사유 후보로 적어 사용자가 정하게 함. 판정 정의·문턱·구동기 바이트 바꿈 0.
- [2026-10-21 23:33:07 +0900] k92t30 구동기: J-b 판정 PASS (판정 잎 45, 같음 45, 다름 []), `OK2/k92t/judge/jb.json` sha256 `f8a273ef9b6e2f02f539b4193a39d35516959d8799e3cd89a2b060c006faa200`, 새 판정 파일 sha256 `4b0cf22ea96fdd09f57320e3130fea2a3078676015a1008631ad14d82560fdfb` — J 판정 값 고정 (자동 기록)
- [2026-10-21 23:34:08 +0900] k92t30 구동기: 읽기 전용 뿌리 스냅숏 `OK2/snap/s32_a30_after_jb.json` sha256 `61626480e08c37bf07b1fef5cc8497bfa2da036aad4d5226243a87649827208b`, s02 대비 SAME (자동 기록)
- [2026-10-21 23:34:09 +0900] k92t30 구동기: J·F 판정 값 고정 확인(f.json `04cfa2e0a9ac754b…`, jb.json `f8a273ef9b6e2f02…`), 봉인 뿌리 k92_record.json 훑기 ok=False ({'files': 134, 's47': 134, 'bad': 89, 'ran': True}), 봉인 k92t 목록 같음 True, 앞 기록 바이트 같음 True, `OK2/k92t/judge/sealed_records.json` sha256 `517582ad15adc98d936199cc9d4c1e9e9c9cc6bbc3d359722b4d7a06941d6eb5` — 이제 봉인 로그는 보충 25 §6.4대로 열 수 있음(열 때마다 LOG), G-K4 plant 원자료 재계산(보충 29 §5)은 독립 검증기 몫 (자동 기록)
- [2026-10-21 23:34:09 +0900] k92t30 구동기: STOP — 단계 post, 까닭 sealed-root record scan not ok (S-K10) (k92t30.py, 자동 기록)
- [2026-10-21 23:36 +0900] Gates A30 G2 끝: 사슬 프로세스 PID 8248 끝남. `STOP_a30_post.json`(sha256 `8fa7524342517c020715aa26757f38a54473cdcf30cdd1d18d9b5414dcf8e18e`, 까닭 "sealed-root record scan not ok (S-K10)"), `stages/post.json` 없음, `post_sealedscan` rc=3. J·F 값 고정은 이미 됨(f.json `04cfa2e0…`·jb.json `f8a273ef…` sha가 LOG에 있음, 23:33:07). 실패 진단(보충 25 §6.4·보충 30 §4.5; J·F 값 고정 뒤이므로 봉인 열람 허용, 열 때마다 LOG): 23:36 `OUTK/judge/sealed_records.json`(판정기 출력, 경로·까닭 글만) 엶. 목적: 89개 "not blind"가 실제 v3c3-s47 기록인지 판정기 경로 규칙의 문제인지.
- 시각 바로잡음(덧붙임): 바로 위 항목 머리 "23:36"은 미리 적은 시각입니다. 실제로 쓴 때는 23:34:53, `sealed_records.json`을 연 때는 23:35:08입니다 [실행 `date`]. 진단 도구 `KB/a30apply/diag_sealedscan.py` sha256 `bdac6ad09b825d02494e8b376f19667abc686554a353cf5c5baf4c7edafe2cb1`(판정에 쓰지 않음; 값 출력 0). 1단계 결과: 봉인 k92_record.json 134개 모두 "s47"로 셈, bad 89(목록 50 = K9-2-0 17·K9-2-1 33). 판정기 `_seed47_path`(`k92t30_judge.py:303-305`)는 경로 조각이 `_s47`로 끝나면 s47로 보는데, 봉인 뿌리 이름 자체가 `sealed_s47`이라 봉인 뿌리 아래 모든 파일이 s47로 셈될 수 있음 [읽음 코드; 추론].
- [2026-10-21 23:35 +0900] Gates A30 실패 진단 2단계(봉인 열람, J·F 값 고정 뒤): `OK2/sealed_s47/**/k92_record.json` 134개를 메모리에서 읽어 파일마다 `seed` 칸, `vissim` 칸 null 여부, `vissim_reason` 글, 봉인 뿌리 아래 경로에 s47 조각이 있는지만 셈(값 출력 0). 목적: STOP_a30_post(S-K10)의 89개가 실제 v3c3-s47 기록의 블라인드 위반인지, 판정기 경로 규칙이 봉인 뿌리 이름에 걸린 것인지.
- [2026-10-21 23:36 +0900] Gates A30 실패 진단 2단계 결과(값 출력 0) [실행 23:35:21]: 봉인 k92_record.json 134 = `seed` 47 45개(K9-2-0 9·K9-2-1 18·K9-2-2 18; 모두 `vissim` null·`vissim_reason` `k92_blind_s47` = 블라인드 참, 봉인 뿌리 아래 경로에 s47 조각 있음) + `seed` 31 42개·43 47개 = 89개(모두 `vissim` null, `vissim_reason` `k92_vissim_ref`, 봉인 뿌리 아래 경로에 s47 조각 없음). bad 89 = 정확히 v3c3-s31·s43 기록 89개. 판정기 `scan_vissim_blind(sealed=True)`(`k92t30_judge.py:359-371`)가 `_seed47_path(full)`을 봉인 뿌리를 포함한 전체 경로에 적용해 뿌리 이름 `sealed_s47`이 모든 기록을 s47로 만듦 → s31·s43 기록이 "s47 VISSIM 쪽 블라인드 아님"으로 셈. 실제 v3c3-s47 기록의 블라인드 위반 0 [실행·읽음]. 판정기 결함으로 봄 [추론]. 판정기를 데이터 뒤 고치면 S-K12 → 고치지 않음, STOP 그대로, 사용자가 정함.

## 2026-10-21 23:41 +0900 — Gates A30: G3 마무리 (STOP)

- 이 항목 덧붙임 전 LOG sha256 `c13b9ed29be0787c64f1ac8e3f5f55f53ef9789690f2457c1f870b99abc50b78`, 192,913 B.
- 결과: check30 PASS, seal30 PASS, fcount PASS, 지속성 보고 완전(21상태, T=1,050 측정 불가(T_FROM=900)), F PASS(F-1·F-2·F-3 참, n 22), J-b PASS(45/45), post30 **STOP (S-K10)** — 봉인 뿌리 기록 훑기 bad 89 = v3c3-s31·s43 기록 89(판정기 `_seed47_path`가 봉인 뿌리 이름 `sealed_s47`을 s47로 읽음), 실제 s47 기록 45/45 블라인드. 판정기 고침 0(S-K12). 따로: `jb_unit` rc=1(시험 2개, 판정 잎 밖)과 보충 30 §5.3 글의 어긋남 — 사용자 결정.
- 끝 확인 스냅숏(사슬 밖, `KI/launch.ps1 -Tag a30gates_snap_end`, 23:36:08 PID 20780, 51.6 s) `OK2/snap/s34_a30_gates_stop.json` `c3b4c0a3bdf0db87aee54517db5c21968cde32693ecc8d489ee23252c1071ee5`, s02 대비 SAME.
- G3 끝 대조 [실행 23:41]: `KB/a30_pins.sha256` 83/83 OK·종료 0, `KB/k92t_pins.sha256` 56/56 OK, 이어 받은 OUTK 기록 11개 바이트 같음, GWT8 head `e27ceac8`·브랜치 `claude/k92-b1-20261016`·status 0줄·`b9734abe..HEAD` 6커밋·K8 `b9734abe`·원격 k92 0·푸시 0, python·VISSIM 0, C: 40 GB·D: 393 GB.
- 보고서 `KB/GATES_K92B1_A30.md` sha256 `167e9e188c1053b89f814080b258e89238901126f153d2753bcdb0ab271f3556`(159줄, LF), 사본 `OK2/GATES_K92B1_A30.md` 같은 바이트. `KB/GATES_K92B1.md`에 §8 덧붙임(덧붙임 전 `63dd35e2…` → 뒤 `3f3a069a68123f7b273d8ae2dc4c14c6be57b2aa8865d38fc975f10ab8ee7e8b`), 사본 `OK2/GATES_K92B1.md` 같은 바이트로 바꿈.
- 이 단계 도구(판정에 쓰지 않음) `KB/a30apply/`: `poll30.py` `1cd0001a…`, `wait30.sh` `32a0c17a…`, `diag_sealedscan.py` `bdac6ad0…`.
- 하지 않은 것: G-K4 plant 원자료 재계산·독립 검증·V-B·V-A(보충 30 §6 순서 밖), 커밋·푸시, 판정기·구동기 고침, 다시 돌림. 사용자 결정: Q1 post STOP 처리, Q2 `jb_unit` rc=1, Q3 다음 순서(검증·plant 재계산 시점).

## 2026-10-22 00:18 KST — VerifyGates 2 (k92t 독립 검증 r2): 검증 도구 고정 (보충 30 §5.4, D-K9-57 ④)

- 도구 폴더 VG3 = `KB/vgates3` (새 파일. `vg_ja.py`·`vg_ja2.py`·`vglib.py`의 사본 아님·import 0. 하네스 `sa_*`·`k92_*`·`k8b_*`, k92t 구동기·판정기 import 0). 목록 `KB/vgates3/vg3_pins.sha256` sha256 `a864482c66d47b260e17b9200bc7dd79ece8170d10f03687449185c8f7d53313` (17줄).
- 고정한 sha256: `vg3lib.py` 696d00c54ab990b6b143526a61ae235b78353317c690e141d5b7e0eb17767e4e · `vg3_ja.py`(J-a) e025f02d7163b61f34c7d2c2b70cd227bdc6d77bea76800e43553b259940aba1 · `vg3_j0.py` 01494a21d2c450c6a3186acbf027704f1d38566d79b873e133e08291337845af · `vg3_jwall.py` be391951032936a949a2c1306083759865e9d835bb136e2000baa1b8cd7b42fe · `vg3_f.py`(F) 5c50b6019c14dd168e59b487157b201f5f0cab1327f1f896a2b9f8729b103dcc · `vg3_jb.py`(J-b) cf0eeefa12af5b2046de4958ea58344b6aba0f15531e5194cd564baa7d4d4943 · `vg3_jbrepro.py` 157e2748fe0672cec3187d5aa41271ddd075b3313f62b7ec1b1df1bfe7919973 · `vg3_post.py`(사후) 124250eab11992dc1e4ded6a92e3494f31c252268c072ca8e886598f2288de80 · `vg3_gk4.py`(G-K4 plant) 652965d6d23d77aa6fd85fe04318898fe19b2e03c9f77416fd87502649137836 · `vg3_rerun.py` dbed6908482e10f95994f9c4c3909099ac26ea9cac000910620ffdae91a418be · `vg3_rcmp.py`(다시 돌리기 비교 규칙) 6d16eaf5493b1206a4d0c11ff588ac9aeb78f2912471443af0440e259fe89941 · `vg3_static.py` b8aff9224d5bf83faf8a9698dceca35756e258cca4889b8d62b26664db491675 · `vg3_synth.py` d8394904e8fe6c766f0fc02a6c7e55c18b4d68dfd7b6b3e93dc8fd6a19ae9c9f · `vg3_synth2.py` f1a99819df1f43cf474778258a3368facfe8d2ff33ff6a56612f49786bdc8532 · `vg3launch.ps1` 240a259c9369ff389089627af3f912046f34897ee9c8b6b5a4c996a37672b71b · 합성 시험 출력 `dev/synth_out.txt`(75/75) faf474b7… · `dev/synth2_out.txt`(26/26) 9615c64a….
- 고정 전에 한 것(공개): 합성 입력 시험만(J-a 비교 규칙 28사례·N 표 20줄·G5·역추적 서명·스텁 언피클러; 가짜 트리로 각 모듈 main). 실제 자료로는 k92t 산출이 아닌 것만: J-b 원자료 부분집합 식을 V4 K9-1 산출에 돌려 `gates_k91t.json` 7항목과 같음 확인(이 때 V4 `jobs/k91t/TL3_<T>_SAF_OBS_H3/summary.json`의 블록 값도 읽음 — J-a 옛 쪽 파일이지만 J-a 도구는 돌리지 않았음), 스텁 로더를 K9-1 V4·탐침 OK2A 템플릿에, 모형 쪽 교차 확인을 탐침 잡 `k92pB1/TL3_2850`에, FZP 계수기를 v3c3-s31 FZP 앞 60 MB 사본에(사본은 지움). 정적 점검(`vg3_static`, 보충·고정점·핀 목록·문턱 글·GWT8)은 k92t 값 0.
- 고정 전에 본 k92t 쪽 정보(공개): 작업 지시 글 안의 관문 보고 요약(F-1·F-2·F-3 수치, J-b 45/45, 사후 STOP 진단 포함); `OUTK/steps.jsonl`의 단계 이름·rc·초·일부 argv; OUTK·`judge/`·`stages/`의 파일 이름; LOG에서 post30 줄 글자 개수 세기 1회(`grep -c`, 개수만). 판정 파일(`judge/*.json`)·F 잡 파일·봉인 뿌리 파일 내용 열람 0.
- 다음: 스냅숏 → static → J-a(1회) → J-0 → J 벽시계 → (LOG 열람 기록 뒤) F → J-b → J-b 재현 → (LOG) 사후 → (LOG) G-K4 plant → 대표 잡 둘 다시 돌리기 → 비교 → 스냅숏. 무거운 실행은 모두 `vg3launch.ps1`(WMI 분리, BelowNormal, PYTHONHASHSEED=0, python -B), 한 번에 하나.
- [2026-10-22 00:20 +0900] VerifyGates 2: 정정 — 위 도구 고정 항목은 00:17(00:17:20–00:17:54 사이)에 덧붙였음(머리의 00:18은 분 반올림). 고정 뒤 실행: 스냅숏 `vgates3/out/snap_vg3_before.json`(s02 대비 SAME), static ok, J-a(1회) PASS 23/23·기록과 같음, J-0 PASS 105·기록과 같음, J 벽시계 PASS·기록과 같음.
- [2026-10-22 00:20 +0900] VerifyGates 2 열람 기록(보충 30 §4.5·보충 25 §6.4; J·F 값 고정 = LOG에 f.json·jb.json sha 있음은 도구가 기계로 확인): 파일 = `OUTK/f_{off,w,b1}/sa/{jobs,cap}/k92t/`의 v3c3-s47 주 표본 22 + s31·s43 둘째 표본 16(summary.json·k92_record.json·k92_series.npz·capture.json), `OUTK/f_vref/sa/k92_vissim_ref.json`, `OUTK/f_persist30/sa/k92_vissim_ref.json`, `OUTK/judge/f.json`·`f_jobs.json`, `OUTK/steps.jsonl`, NC3 v3c3-s47·s31·s43 FZP(체인 링크 13개 프레임 대수만 셈, 바이트 sha)와 .inpx(바이트 sha·randSeed 값). 목적 = F-1–F-3·잡 정상 수·지속성 보고의 독립 재계산(`vg3_f.py` 5c50b601…). 출력은 합계·참거짓·개수(상태별 값 0). F 잡 로그 셋(봉인)은 열지 않음.
- [2026-10-22 00:25 +0900] VerifyGates 2: F 재계산 `vgates3/out/f.json` — 판정 PASS, 기록 `judge/f.json`·`f_jobs.json`과 모든 대조 항목 같음(값은 보고서). J-b 재계산 `out/jb.json` PASS 45/45·기록과 같음, 원자료 부분집합 7항목 같음. J-b 재현(`OK2/vg3t/jbcopy`, sa_gates 다시) 43/43 같음, unit_T9b·T9c는 선언대로 경로 의존(값의 provenance 뺀 부분 같음).
- [2026-10-22 00:25 +0900] VerifyGates 2 열람 기록(보충 30 §4.5): 파일 = `OK2/sealed_s47/` 아래 모든 파일의 바이트 sha·크기(봉인 목록 대조), `k92_record.json` 134개의 seed·vissim·vissim_reason 칸(메모리 안 비교, 개수만 출력), `OK2/commit/K9-2-*/sealed_s47_index.json`·`OK2/a27/sealed_index.json`·`OK2/a30/sealed_k92t_index.json`, `OUTK/STOP_a30_post.json`·`stages/*.json`·`judge/sealed_records.json`. 목적 = 사후 단계(post30) 독립 재계산과 S-K10 진단 확인(`vg3_post.py` 124250ea…). 봉인 로그 파일 내용(F 잡 로그 셋 포함) 열람 0(sha만).
- [2026-10-22 00:26 +0900] VerifyGates 2: 사후 재계산 `vgates3/out/post.json` — 봉인 뿌리 맨 위 여섯·목록 대조 모두 같음(K9-2-0 3,573 / K9-2-1 4,072 / K9-2-2 4,072 / K9-2-3 821파일 다시 sha, a27, k92t 셋), 기반 기록 11개 바이트 같음. k92_record.json 134개: seed 칸 31=42·43=47·47=45, 선언 규칙(봉인 뿌리 아래 상대 경로·seed 칸) s47 45개 모두 vissim null·k92_blind_s47(나쁨 0), 기반 판정기 글자 규칙은 134/134를 s47로 세어 나쁨 89(= s31 42 + s43 47) — 기록 `judge/sealed_records.json`과 같음.
- [2026-10-22 00:26 +0900] VerifyGates 2 열람 기록(보충 29 §5 D-K9-55, 보충 30 §4.5; post30 LOG 줄 있음): 파일 = `OK2/probe_a25/plant/sa/jobs/k92p{W,B1}/{TL3_1500_SAF_OBS_H3,TL3_1050_s43_SAF_OBS_H3}/{summary.json,k92_record.json}`와 `OK2/sealed_s47/K9-2-{1,2}/plant/new/sa/jobs/k92{1,2}g4{W,B1}/` 같은 잡의 같은 두 파일(v3c3-s31 1,500·v3c3-s43 1,050만, v3c3-s47 0), `OK2/a27/judge/rjg4.json`. 목적 = "D-K9-55 G-K4 plant 원자료 재계산"(`vg3_gk4.py` 652965d6…). 출력은 판정·경로·개수.
- [2026-10-22 00:27 +0900] VerifyGates 2: G-K4 plant 원자료 재계산 `vgates3/out/gk4_plant.json` — 4행 모두 PASS(파일별 summary·k92_record PASS), 기록 `OK2/a27/judge/rjg4.json` plant 행과 모두 같음.
- [2026-10-22 00:27 +0900] VerifyGates 2: 대표 잡 다시 돌리기 첫 발사(00:26:54)는 `vg3_rerun.py`의 첫 가드("`OK2/vg3t` 있음")에서 바로 끝남 — J-b 재현이 같은 `OK2/vg3t`(jbcopy)를 먼저 만들었기 때문(내 도구 설계 충돌, 실행·쓰기·읽기 0). 도구는 고치지 않고, 내 J-b 재현 폴더 `OK2/vg3t` → `OK2/vg3r`로 이름만 바꿈(같은 볼륨, 재현 관문 파일 sha e365d170… 그대로). 다시 발사함.
- [2026-10-22 00:37 +0900] VerifyGates 2: 대표 잡 둘 다시 돌리기(`OK2/vg3t`, 8단계 rc 0·VISSIM 0) — 미리 정한 규칙으로 J(`TL3_2250_SAF_OBS_H3`)·F(`TL3_3300_s43_SAF_OBS_H3`) 모두 REPRO_SAME(`vgates3/out/rerun_cmp.json` 66107450…). TREE .mcode 91 → 91. 끝 스냅숏 `snap_vg3_after.json`(ef7308ab…) s02 대비 SAME, 기록 스냅숏 s29–s32·s34 다시 diff 모두 SAME. 끝 대조: vg3 핀 17/17, a30 핀 83/83, k92t 핀 56/56, GWT8 e27ceac8·status 0줄·6커밋·K8 b9734abe·원격 k92 0. 실패 진단 아닌 확인으로 `OUTK/jb/sa/unit_k92t.log`·`V4/sa/unit_k91t.log`의 pytest 요약·FAILED 줄만 읽음(00:3x).
- [2026-10-22 00:37 +0900] VerifyGates 2 보고서 `KB/VERIFY_GATES_K92B1_r2.md` sha256 `5f7c125614c65457c08e40644f0723e7db84dad669f2f98fcd73728ed64e2442`(사본 `OK2/VERIFY_GATES_K92B1_r2.md` 같은 바이트). 결과 STOP 확인: 다시 낸 J-0·J-a·J 벽시계·F·J-b·잡 수·지속성·봉인 대조·G-K4 plant가 기록과 모두 같음; post30 S-K10은 판정기 글자 규칙으로 다시 만들어짐(134/134/89), 선언 규칙으로는 s47 45/45 블라인드(나쁨 0). 사용자 결정 Q1–Q4.

## 2026-10-22 01:29 +0900 — Declare A31: 보충 31 작성 시작 (D-K9-58·59·60·61)

- 이 항목 덧붙임 전 LOG sha256 `638c97ebd72aed4659f1cb0184138df78f3d1c05e8f1c6a5cfb44b455dd6b3e2`, 203,463 B.
- 고정점 [실행 sha256]: 결정 기록 `K9_1_J1_NOTES_20261013.md` `09974cfc3e1412735ba6cf3228f4a2e4c08ad01294327d534290011b4a8042cc`(193줄, D-K9-58~61 :184-193). 보충 24 `d46db6dc…`·25 `4fd7b599…`·26 `8f835616…`·27 `4ce8b27a…`·28 `9881eb40…`·29 `4bd6dc8d…`·30 `ba556227…` = 각 `.sha256`; 고정점 24 `fbc3d59f…`·25 `d1338fbc…`·26 `6edc55ac…`·27 `394ab15f…`·28 `14451cf4…`·29 `3ba1d0bd…`·30 `ad3fafad…`. 관문 보고 `GATES_K92B1_A30.md` `167e9e18…`, 검증 2차 `VERIFY_GATES_K92B1_r2.md` `5f7c1256…`. `KB/a30_pins.sha256` `7afabd03…`, `KB/k92t_pins.sha256` `38a2ce14…`.
- 상태 [실행]: GWT8 head `e27ceac8`, 브랜치 `claude/k92-b1-20261016`, K8 브랜치 `b9734abe`, status 0줄, `b9734abe..HEAD` 6커밋, 원격 k92 0. python·VISSIM 0. C: 40 GB, D: 389 GB.
- 이 단계에서 할 일: 보충 31 글 + 새 도구(`KB/a31decl`, 커밋 안 함: 판정기 사본 `k92t31_judge.py`(`_seed47_path` 한 함수만 바꿈), 구동기 `k92t31.py`, 단위 시험 비교기, 확인 도구) + 합성 자료로만 확인 + 기대 고정 목록. 봉인 기록 내용·jb_unit 로그 내용·b9734abe 시험 결과는 열거나 만들지 않습니다(임시 작업 트리 만들기 0). VISSIM·COM·러너·동결·커밋·푸시 0.

## 2026-10-22 02:21 +0900 — Declare A31: 보충 31 작성 끝 (D-K9-58·59·60·61)

- 이 항목 덧붙임 전 LOG sha256 `6b8b9e6dd32d337e2157135a07f9bd4216f4defe093f754ea491dc3271620de7`, 204,955 B.
- 보충 31 Declare 판 `SP/K8_PREDECLARATION_AMENDMENT_31.md` sha256 `8a76e210230b69c0c21627f13eb7459e04f044d5ac62feac3cdcb2dd5c3d0cbc`(77,939 B, 506줄, LF, CR 0), `.sha256` 같은 값 [실행 `sha256sum -c` OK]. 고정점 `KB/AMENDMENT31_FIXED.md`는 반박 검토가 만듭니다(아직 없음).
- 새 도구(커밋 안 함, `KB/a31decl`) [실행 sha256]: 구동기 `k92t31.py` `63b5aa229eeaf013f2136a838cf9e5be163a087771fc3a71ea3202b0ad12b53d`, 판정기 `k92t31_judge.py` `9dfc0b208c4f2fbd1abcd1eeb04bc066e29599aef63c5a5d59521a3311ee1d2c`(= 보충 30 판정기 사본에서 `_seed47_path` 한 함수만 바꿈; 차이 `A31_JUDGE.diff` `fc9ce7b6…`), jb_unit 비교기 `k92t31_unit.py` `a1d82bffb71660361b07b19a823c1ff79286d2add90a0a58fdda8376cc03c6e2`, 확인 도구 `dry_a31.py` `15183681dc34316b92ae812ddad0d2c0eb3ae31d545037ed6023351b5678ac39`, 기대 고정 목록 `a31_pins.expected.sha256` `bf1ca001e8c8a4215512582871ddf439971aff04887267a0b797b3496ddc6d4e`(133줄, `sha256sum -c` 133/133 OK; 앞 83줄 = `KB/a30_pins.sha256` 바이트).
- 데이터 없는 확인 [실행 `KB/a31decl/dry/decl`]: static ok(바뀐 함수 = `_seed47_path` 하나, 함수 밖 모듈 글 같음, 비교기 import = 표준 라이브러리만); truth ok(진리표 T1–T22 22/22, 합성 봉인 뿌리 A 새 6/3/0·옛 6/6/3, B 새 6/5/3, 망가뜨림 M1–M8 8/8, 판정기 명령줄 A rc 0·B rc 3); unit ok(합성 pytest 로그 U1–U14 14/14 기대와 같음, 망가뜨림 UM1–UM8 8/8, 명령줄 = 함수 호출); drv ok(구동기 `stage_scan31`·`stage_unit31`을 합성 판정기 사본·합성 git 저장소에: scan A PASS·기대 바꿈 STOP·B STOP, unit 같음 PASS·바뀜 FAIL/STOP, 두 경우 임시 작업 트리 만들고 지움·저장소 상태 그대로); drive ok(`check31 --mode decl` 43점검 거짓 0, 읽기만). 사실 확인: GWT8 대 TREE 바뀜 10(CR만, `TK/cr_only_files.json`의 10개)·한쪽 0; 합성 저장소에서 새 작업 트리 = archive 줄바꿈(CRLF), 커밋한 작업 트리 LF.
- 무거운 일(WMI 분리, BelowNormal, 한 번에 하나): `a31decl_fact_wt`(01:37, 144.1 s), `a31decl_fact_wt2`(01:56, 8.4 s; 첫 출력 파일을 정리 때 지워 다시 냄), `a31decl_snap`(02:00) → `OK2/snap/s34b_a31decl.json` `bb3fe248aea12587fa82faaeedac680d5b3c05d2687e43469143eecbf3d5a111`, s02 대비 SAME.
- 지킨 것 [실행]: VISSIM·COM·러너·동결·결정 재생·plant 잡 0. 실제 저장소 임시 작업 트리 0(합성 저장소에서만), b9734abe 시험 실행 0, 4c 시험 실행 0. OUTK·봉인 뿌리·TREE·GWT8·저장소 `.git`·K8 브랜치·V4 쓰기 0. jb_unit 로그·봉인 기록 내용 열람 0(바이트 sha·이름·크기만). 봉인 시드·codex 64cf 숫자 0. 커밋·브랜치·푸시 0: GWT8 head `e27ceac8`, status 0줄, K8 `b9734abe`, `git worktree list`에 a31 항목 0. 끝에 python·VISSIM 0. C: 40 GB, D: 388 GB.
- 알리는 것(보충 31 머리): 데이터 뒤 판정기 고침(D-K9-58, S-K12 예외 하나, 결과 짐작됨), 보충 30 §5.3을 jb_unit 줄에 한해 바꿈(D-K9-59), 메인 세션 `grep -rl` 공개, 검증 2차 공개 수용(D-K9-61). 다음: ReviewDeclare A31(고정판·고정점) → Apply A31(§4.2 G0–G3).

## 2026-10-22 02:27 +0900 — ReviewDeclare A31: 보충 31 반박 검토 시작 (Declare 판 `8a76e210…`)

- 이 항목 덧붙임 전 LOG sha256 `a534151453e36a9753283151cf7f443e7c8c3a15fdd42a12f70ca9cfca474cab`, 208,366 B.
- 고정점 [실행 sha256]: 결정 기록 `09974cfc…`(193줄, D-K9-58~61 :184-193) = 작업 지시 값. 보충 31 Declare 판 `8a76e210230b69c0…` = `.sha256`. 사본 `KB/a31review/r1/K8_PREDECLARATION_AMENDMENT_31_declare.md`(같은 바이트). python·VISSIM 0. C: 40 GB, D: 388 GB.
- 이 검토의 도구·출력 = `KB/a31review`(RV31). 할 일: 판정기 차이 다시 대조, s47 판별 규칙 적대 경로 시험(합성 경로·합성 봉인 뿌리만), 새 데이터 0 확인(파일 시각), jb_unit 기준 실행 절차 읽기(GWT8·K8 브랜치 보호), G-K4 재계산 순서·고정, V-B 시작 조건.
- 하지 않는 것: VISSIM·COM·러너·동결·결정 재생·plant 잡 0. 실제 저장소 임시 작업 트리 0, b9734abe 시험 실행 0, 4c 시험 실행 0. 봉인 뿌리 파일 내용·jb_unit 로그 내용 열람 0. OUTK·SEALED·TREE·GWT8·저장소 `.git`·K8 브랜치 쓰기 0. 커밋·푸시 0.
- [2026-10-22 02:35 +0900] ReviewDeclare A31: 검토 도구 고정. `rv_s47rule.py` `b39ae21fb58bebd370f1ec3a4b0597ecb3e4661ade98ed04a68ecbc06be4bb96`(합성 경로 24개·진리표 22줄·합성 봉인 뿌리 12기록; 실제 자료 0 — 고정 전에 한 번 돌림, 출력 `out/rv_s47rule.json` `2ebc5153986558f01d38249f1e02ef6210d8fe4626b517f1be5d23602bd68e0b`, ok 참, 합성 트리 `TK/a31review/syn` 만들고 지움). `rv_idx31.py` `83057a00500b449fc7ae074c4e6b94bd8c78096c7b97aae72908b90404aee449`(봉인 뿌리 **밖**의 봉인 목록 `OK2/commit/K9-2-{0..3}/sealed_s47_index.json`·`OK2/a27/sealed_index.json`·`OK2/a30/sealed_k92t_index.json`의 파일 이름에 새·옛 `_seed47_path`를 걸어 개수만 냄; 봉인 뿌리 파일 열기·목록 0, 이름 출력 0). 열람 기록: 위 목록 파일 셋(이름·개수만), 목적 = 보충 31 s47 판별 규칙의 실제 이름 대조(반박 검토).
- [2026-10-22 02:45 +0900] ReviewDeclare A31: `rv_idx31.py` 결과 `out/rv_idx31.json` `e752e800fe02e8970be22a7644748299969b86831b3628b8528255215588a260` — ok 참: 봉인 목록 파일 12,538 가운데 `k92_record.json` 134(26/54/54/0), 새 `_seed47_path` 경로만 45(긴 경로 머리 꼴도 45), 옛 134, 따로 나눈 조각 45, `k92_vissim_ref.json` 0. 이름에 record가 든 다른 파일 212개의 이름을 보려고 `rv_idxnames.py` `e968718b6ced9941347175e4052dc7e93e8a76dc90ec8c9c72071193f0fccd86`(같은 봉인 목록의 이름만, 바닥 이름별 개수 출력)을 sha를 LOG에 적기 **전에** 한 번 돌렸음(공개) → `k91_record.json` 212, `k92_record.json` 134. 또 `OK2/a27/judge/rjg4.json`의 키 이름(값 아님)을 봤음(V1 글의 칸 이름 확인). 메타데이터 `find -newermt`(이름 출력 없음, 개수만)로 OUTK·봉인 뿌리·OUT30의 10-21 23:42 뒤 바뀐 파일을 셈 → 0·0·0.
- [2026-10-22 02:46 +0900] ReviewDeclare A31: 도구 고정 `rv_capman.py` `d74e5e2a1fe4b90009e10fb3eb853ce462c8ebff40ff8d8cf334452e17799596`(J-b 포착 뿌리 `OUTK/jb/sa/cap/k92t`의 파일 이름·크기·바이트 sha 목록을 보충 31 데이터 전에 만듦 — 기준 실행이 포착을 읽기만 했는지 독립 검증 V4가 대조할 기준; 내용 파싱·출력 0, 표준 출력은 개수·목록 sha만). WMI 분리(`KI/launch.ps1 -Tag rv31_capman`), BelowNormal, 한 번.
- [2026-10-22 02:49 +0900] ReviewDeclare A31: `rv_capman.py`(WMI 분리 02:47:06 PID 25812, 29.2 s) → `out/cap_manifest.json` `d6691f48954d07dd2b3bbfe718e468fd59f3f6b7492060a2151d4d02e177e3a9`: CAP 파일 3,944개, 1,690,146,202 B, 목록 sha256 `5340ac03da81742dd864044f9922a75bed1e542147249d4a8699a6432e273038`. 대조 도구 `rv_capx.py` `f34fc326df4a70a25b7951078d1168c4fd77a92194200001f140a50e3bbfb0ed`(쓴 바로 뒤 sha를 LOG에 적기 전에 돌림, 공개; 첫 두 판은 셸 글자 문제로 문법 오류, 실행 0) → `OUTK/jb_copies.json` `caps` 960개와 같음 960·다름 0·없음 0, 포착 시험 입력(TL3/002700 SAF·BASE, T9C/002700 BASE) 있음.

## 2026-10-22 02:55 +0900 — ReviewDeclare A31: 보충 31 고정 (반박 검토 끝)

- 이 항목 덧붙임 전 LOG sha256 `099927fda6841c13881bebf66705054bf06e5f52d2566510dacb5c4d4595b8c1`, 212535 B.
- 고정판 `SP/K8_PREDECLARATION_AMENDMENT_31.md` sha256 `8541ccb7fa6c951b4affcca67d57e25be09b061c3ae3dd006d050c9c6413e304`(98,679 B, 575줄, LF, CR 0), `.sha256` 같은 값 [실행 `sha256sum -c` OK]. Declare 판은 `SP/K8_PREDECLARATION_AMENDMENT_31_r1.md`(`8a76e210…`, `.sha256` 있음)로 남김. 고정점 `KB/AMENDMENT31_FIXED.md` sha256 `605ccbd2cb392ac2ed0a6da1d27c20e93aa68fcac50ec6d99c4393236f98a053`(고정 시각 2026-10-22T02:53+09:00). 기대 고정 목록 `KB/a31decl/a31_pins.expected.sha256` `bf1ca001…` 133/133 그대로; 구동기·판정기·비교기 바이트 그대로.
- 고친 곳(글만, 보충 31 §12.1): R1 판별 규칙 한계와 실제 봉인 뿌리에서 닿지 않는 근거(§2.2), R2 독립 검증 V2에 seed 칸 분포·두 길 어긋남 0(STOP 늘림), R3 첫 읽기 전 고정 목록에 K9-2 jb_unit 로그, R4 CAP 바이트 기준 목록과 V4 대조(STOP 늘림), R5 GWT8·K8 보호 근거, R6 pytest 뿌리 근거, R7 시간 상한 끝의 손자 프로세스 처리·G3 프로세스 개수, R8 `k91_record.json` 212개 공개.
- 확인 [실행]: 판정기 차이 = `_seed47_path` 한 함수; 진리표 22/22·적대 경로 24/24·합성 봉인 뿌리 11/5/3; 실제 이름 134 → 새 45·옛 134; 새 scan 데이터 0(파일 시각); `check31 --mode decl` 43점검 거짓 0; 구동기 `a31_sha()` = `8541ccb7…`, C6 같은 뜻 참(`rv_fixcheck31.py` `233c060f30e95138790302efce90b7ef24772ed69e67c483bb90783df49b8c2e`).
- 지킨 것 [실행]: VISSIM·COM·러너·동결·결정 재생·plant 잡 0. 실제 저장소 임시 작업 트리 0, b9734abe·4c 시험 실행 0. 봉인 뿌리 파일 내용·jb_unit 로그 내용 열람 0. OUTK·봉인 뿌리·TREE·GWT8·저장소 `.git`·K8 브랜치·AD31 쓰기 0. 커밋·브랜치·푸시 0: GWT8 head `e27ceac8`, status 0줄, K8 `b9734abe`, `git worktree list`에 a31 0. 끝에 python·VISSIM 0. C: 42.6 GB, D: 416.6 GB(10^9 B 단위).
- 다음: Apply A31(보충 31 §4.2 G0–G3) → 사슬 PASS면 독립 검증 A31(§4.3 V1–V4) → K92_GATES_PASS면 V-B → VerifyVB. V-A·푸시는 사용자 결정 뒤.

## 2026-10-22 02:57 +0900 — Gates A31: 보충 31 적용 시작 (§4.2 G0–G3)

- 이 항목 덧붙임 전 LOG sha256 `c6a0dd795314189814811725424ecb7cc2e3b7d7e12cc6a4f3648862221f3f5e`, 214,846 B.
- G0 사전 확인 [실행 02:55–02:57 KST]: 보충 31 sha256 `8541ccb7fa6c951b4affcca67d57e25be09b061c3ae3dd006d050c9c6413e304` = `.sha256` = 고정점 `KB/AMENDMENT31_FIXED.md`(`605ccbd2cb392ac2ed0a6da1d27c20e93aa68fcac50ec6d99c4393236f98a053`) 안의 64자(1회); Declare 판 64자(`8a76e210…`)는 고정점에 0회. 결정 기록 앞 193줄(전체 193줄) sha `09974cfc…` 같음. 보충 24–30·`.sha256`·고정점 24–30 = 보충 31 §0 같음. `KB/k92t_pins.sha256` `38a2ce14…` 56/56 OK, `KB/a30_pins.sha256` `7afabd03…` 83/83 OK. 기대 고정 목록 `KB/a31decl/a31_pins.expected.sha256` `bf1ca001e8c8a4215512582871ddf439971aff04887267a0b797b3496ddc6d4e`(133줄, 23,474 B, CR 0; 고정점 안 64자 1회) `sha256sum -c` 133/133 OK·종료 0. GWT8 head `e27ceac8`, 브랜치 `claude/k92-b1-20261016`, K8 `b9734abe`, status 0줄, `b9734abe..HEAD` 6커밋, 원격 k92 0, `git worktree list`에 a31 0. OUT31·`KB/a31_pins.sha256`·WT 자리 없음. python·VISSIM·cscript 0. C: 42.6 GB, D: 416.6 GB.
- 할 일: G1 고정(기대 목록 → `KB/a31_pins.sha256`), G2 `KI/launch.ps1 -Tag k92t31_chain -Script ..\a31decl\k92t31.py -ArgLine chain31` 하나(WMI 분리), 기다림은 프로세스 유무·`OUT31/stages/*.json`·`STOP_a31_*.json`·`steps31.jsonl` 이름·rc 칸만 봄(로그 걸러 읽기 0), G3 끝 대조·보고서. 독립 검증 A31(V1–V4)·V-B·V-A는 이 단계 밖.
- [2026-10-22 02:57 +0900] Gates A31 G1 고정: 기대 목록 바이트를 `KB/a31_pins.sha256`에 씀 — `cmp` 같음, sha256 `bf1ca001e8c8a4215512582871ddf439971aff04887267a0b797b3496ddc6d4e`, 133줄, `sha256sum -c` 133/133 OK·종료 0(02:57:26). 이 목록이 고정하는 새 구동기 `KB/a31decl/k92t31.py` `63b5aa229eeaf013f2136a838cf9e5be163a087771fc3a71ea3202b0ad12b53d`(85줄), 새 판정기 `KB/a31decl/k92t31_judge.py` `9dfc0b208c4f2fbd1abcd1eeb04bc066e29599aef63c5a5d59521a3311ee1d2c`(86줄), jb_unit 비교기 `KB/a31decl/k92t31_unit.py` `a1d82bffb71660361b07b19a823c1ff79286d2add90a0a58fdda8376cc03c6e2`(87줄) — 보충 31 데이터 전(OUT31 없음).
- [2026-10-22 02:58 +0900] Gates A31 기다림 도우미(판정에 쓰지 않음, 이름·rc·프로세스 표만 봄) `KB/a31apply/poll31.py` sha256 `f6e53fd3ba8b2db7150148431d7ae1f8915e0b596adc8e3f4ca90a40af08ac04`.
- [2026-10-22 02:58:24 +0900] k92t31 구동기: 사전 점검 ok=True, `OK2/a31/check31.json` sha256 `007d316f74d93ab25c559528885d9796d4249f54b346d42155b90c981675438f` (자동 기록)
- [2026-10-22 02:58 +0900] Gates A31 G2 발사: 발사 전 `sha256sum -c KB/a31_pins.sha256` 133/133 OK·종료 0(02:58:13). `KI/launch.ps1 -Tag k92t31_chain -Script ..\a31decl\k92t31.py -ArgLine chain31` → 02:58:19 ReturnValue 0, PID 18880(cmd.exe; 그 아래 python), BelowNormal(16384), PYTHONHASHSEED=0, `python -B`, 발사 때 python 0·VISSIM 0. 표준 출력 `OK2/logs/k92t31_chain.txt`(새 이름). 기다림은 `poll31.py`로 프로세스 표·`OUT31/stages`·`STOP_a31_*` 이름·`steps31.jsonl`의 name·rc·sec·VISSIM 칸만 봄.
- [2026-10-22 02:59:22 +0900] k92t31 구동기: 읽기 전용 뿌리 스냅숏 `OK2/snap/s35_a31_check.json` sha256 `12eb59472c21b12419de99c530a7b2c7130fecf180daa68d68bdacbf508b2b14`, s02 대비 SAME (자동 기록)
- [2026-10-22 02:59:22 +0900] k92t31 구동기: 봉인 열람 기록(보충 25 §6.4, 보충 31 §2.4) — 파일 = `OK2/sealed_s47/**/k92_record.json`의 seed·vissim·vissim_reason 칸(판정기 메모리 안), 목적 = 보충 31 봉인 뿌리 기록 훑기(D-K9-58), 출력 = 개수·참거짓·경로만 (자동 기록)
- [2026-10-22 02:59:23 +0900] k92t31 구동기: 보충 31 봉인 뿌리 기록 훑기 PASS (rc 0, ok True, {'files': 134, 's47': 45, 'bad': 0, 'ran': True}, 기대 {'files': 134, 's47': 45, 'bad': 0, 'ran': True}, 보관 파일 그대로 True), `OK2/a31/sealed_records_a31.json` sha256 `47f91364ed00325b40d15ebb9dca464193b2ac093c569c2498b42398b90fa4fa` (자동 기록)
- [2026-10-22 03:00:21 +0900] k92t31 구동기: 읽기 전용 뿌리 스냅숏 `OK2/snap/s36_a31_scan.json` sha256 `1140517122963ebfa773821c391addcc6e7572dcedf0af8830b6b797403dc9a8`, s02 대비 SAME (자동 기록)
- [2026-10-22 03:05:22 +0900] k92t31 구동기: jb_unit 기준 대조(b9734abe 임시 작업 트리, 지움 True) PASS (기준 rc 1, K9-2 rc 1, 공통 97, 다름 0, 기준만 0, K9-2만 0, 통과 아닌 공통 2), `OK2/a31/unit_judge.json` sha256 `b7e9b64901ecd16a0d89a890b850358bae9708eba0e6ef2f392617a7f29cdea5` (자동 기록)
- [2026-10-22 03:06:23 +0900] k92t31 구동기: 읽기 전용 뿌리 스냅숏 `OK2/snap/s37_a31_unit.json` sha256 `23dccfbee7523a36e01ebc90fe69962c26e2a64bba1cc5bef26318106b6dc46b`, s02 대비 SAME (자동 기록)
- [2026-10-22 03:06:23 +0900] k92t31 구동기: 사슬 끝 — check31·scan31·unit31 모두 PASS, `OK2/a31/chain31.json` sha256 `5ca6c42857395650ceaa2613524d3bec24d5eec3b3ed9243972bbb3ee2d8238d` (자동 기록)
- [2026-10-22 03:07 +0900] Gates A31 G2 끝: 사슬 프로세스(cmd PID 18880, python PID 11496) 끝남. `OUT31/chain31.json` 있음, `stages/` = check31·scan31·unit31(모두 `ok` 참), `STOP_a31_*` 0. `steps31.jsonl` 11줄: rc≠0은 `unit31_pytest` rc 1(기준 실행의 pytest 종료 코드, 판정 입력) 하나, VISSIM 전·후 모두 0/0. 기다림은 `poll31.py wait` 세 번(60 s·345 s·60 s). 메모: 구동기 첫 자동 줄(02:58:24)이 위 "G2 발사" 줄보다 앞에 적혔음(내 줄은 발사 몇 초 뒤에 씀).
- [2026-10-22 03:07 +0900] Gates A31 G3 끝 대조 [실행 03:07:18]: `KB/a31_pins.sha256` 133/133 OK·종료 0, `KB/k92t_pins.sha256` 56/56, `KB/a30_pins.sha256` 83/83. GWT8 head `e27ceac8`·브랜치 `claude/k92-b1-20261016`·status 0줄·`b9734abe..HEAD` 6커밋·K8 `b9734abe`·원격 k92 0·지역 브랜치 a31 0·푸시 0. `git worktree list` 23개(a31 0), `repo/.git/worktrees` 22개, `TK/a31_wt_b9734abe`·관리 폴더 없음. 메타데이터 `find -newermt` 개수만: OUTK·SEALED·OUT30(10-21 23:42 뒤) 0·0·0(SEALED는 개수만, 이름 출력 0), TREE·`TK/b9_ref`·V4(10-22 02:57 뒤) 0·0·0; OK2의 OUT31 밖 02:57 뒤 바뀐 이름 = OK2 자신·`a31`·`logs/k92t31_chain.txt`·`snap/s35–s37`. 03:11:39 python·VISSIM·cscript·wscript 0, C: 42.6 GB, D: 416.5 GB.
- [2026-10-22 03:13 +0900] Gates A31 보고 쓰기 전 열람(사슬 끝 뒤): OUT31 기록(`check31.json`·`scan31.json`·`sealed_records_a31.json`·`unit31.json`·`unit31_run.json`·`unit_judge.json`·`chain31.json`·`stages/*`·`driver31.log`·`logs/scan31.log`·`unit31_judge.log`·`unit31_wt_add.log`·`unit_base/unit_b9734abe.meta.txt`)과 `OK2/logs/k92t31_chain.txt`. 목적 = G3 보고서. 두 pytest 로그(`OUT31/unit_base/unit_b9734abe.log`, `OUTK/jb/sa/unit_k92t.log`) 내용 열람 0(sha·크기만). 봉인 뿌리 파일 열람 0(scan31 판정기 자식만, 02:59:22 자동 열람 줄).
- [2026-10-22 03:15 +0900] Gates A31 G3 끝 대조 다시(`GATES_K92B1.md` 덧붙임 직전) [실행 03:15:34]: `KB/a31_pins.sha256` 133/133 OK·종료 0, `KB/GATES_K92B1.md` = 사본 `OK2/GATES_K92B1.md` = `3f3a069a68123f7b273d8ae2dc4c14c6be57b2aa8865d38fc975f10ab8ee7e8b`, GWT8 head `e27ceac8`·status 0줄·K8 `b9734abe`. **고정 창(G1 → G3 끝 대조) 닫힘.** 이 뒤 `KB/GATES_K92B1.md`(고정 목록 127줄)에 §9를 덧붙이므로 그 뒤 `sha256sum -c KB/a31_pins.sha256`은 127줄 하나가 다름(설계된 바꿈, 보충 30 단계 N7과 같은 덧붙임).

## 2026-10-22 03:17 +0900 — Gates A31: G3 마무리 (사슬 PASS)

- 이 항목 덧붙임 전 LOG sha256 `f52de3b40c0be0afca37f289c40385403205de9e1a4b655448bd4ed2565d08c8`, 222448 B.
- 결과: check31 PASS(45점검 거짓 0), scan31 PASS(rc 0, ok 참, 134/45/0, 보관 두 파일 그대로), unit31 PASS(보충 31 §3 규칙 — 보충 30 §5.3을 jb_unit 줄에 한해 대신함; 기준 rc 1·K9-2 rc 1, 공통 97, 다름 0, 한쪽에만 0/0, 해석 INCOMPLETE 0, 통과 아닌 공통 2 = `ConfigFlagTests` 두 실패 두 쪽 같음; WT 대 `TK/b9_ref` 차이 0; WT 만들고 지움, GWT8·K8 그대로), 스냅숏 s35·s36·s37 SAME, STOP 0. K92_GATES_PASS는 아직 아님(독립 검증 A31 V1–V4 PASS 필요, 보충 31 §4.4).
- 보고서 `KB/GATES_K92B1_A31.md` sha256 `e2b301837feb35d652d0db088d634e07449676abd01cb0e8b2dfef6eff232885`(157줄, 28,202 B, LF, CR 0), 사본 `OK2/GATES_K92B1_A31.md` 같은 바이트(`cmp`). `KB/GATES_K92B1.md`에 §9 덧붙임(덧붙임 전 `3f3a069a…` → 뒤 `449b361e96d047156e63f73bcdae905ec61408b9a5f9be047629092d3ab0a792`, 169줄, 25,414 B), 사본 `OK2/GATES_K92B1.md` 같은 바이트로 바꿈(`cmp`).
- 덧붙임 뒤 `sha256sum -c KB/a31_pins.sha256` [실행 03:16:55] = 132 OK, 127줄 `KB/GATES_K92B1.md` 하나만 다름(설계된 바꿈; 고정 창은 03:15:34 133/133 OK로 닫힘). 다음 단계가 이 목록을 다시 대조하면 127줄은 `449b361e…`로 읽어야 함.
- 이 단계 도구(판정에 쓰지 않음) `KB/a31apply/poll31.py` `f6e53fd3ba8b2db7150148431d7ae1f8915e0b596adc8e3f4ca90a40af08ac04`.
- 하지 않은 것: 독립 검증 A31(V1–V4, G-K4 plant 원자료 재계산 포함)·V-B·VerifyVB·V-A, 커밋·브랜치·푸시, 판정기·구동기·비교기 고침, 다시 돌림. 두 pytest 로그 내용 열람 0. 봉인 시드·codex 64cf 숫자 0. 끈 프로세스 0.
- 다음: 독립 검증 A31(보충 31 §4.3; 새 도구 sha를 첫 읽기 전에 LOG에 고정) → K92_GATES_PASS면 V-B → VerifyVB. V-A·푸시는 사용자 결정 뒤.

## 2026-10-22 03:25 +0900 — VerifyGates 3 (독립 검증 A31, D-K9-60): 시작

- 이 항목 덧붙임 전 LOG sha256 `644e141945badb434c84acb07d53106e99dc5b1cb6a9d463a6dc55b990f92f40`, 224473 B.
- 사전 확인 [실행 03:2x KST]: 보충 31 `8541ccb7fa6c951b4affcca67d57e25be09b061c3ae3dd006d050c9c6413e304` = `.sha256` = 고정점 `KB/AMENDMENT31_FIXED.md`(`605ccbd2…`) 안 64자. 결정 기록 `09974cfc…` 같음. GWT8 head `e27ceac8`·브랜치 `claude/k92-b1-20261016`·status 0줄·`b9734abe..HEAD` 6커밋·K8 `b9734abe`·원격 k92 0·`git worktree list`에 a31 0. python·VISSIM·cscript·wscript 0. C: 40 GB·D: 388 GB 여유(df).
- 할 일(보충 31 §4.3): 새 폴더 `KB/vgates4`(VG4)에 새 도구를 짜고, 합성 입력으로만 시험한 뒤, 도구 sha를 이 LOG에 고정하고 나서 처음으로 OUT31 출력·두 pytest 로그·봉인 기록·G-K4 행 원자료·`rjg4.json`·CAP와 `cap_manifest.json`을 읽음. V1 G-K4 plant 원자료 재계산, V2 봉인 훑기 다시 셈, V3 jb_unit 판정 다시 셈, V4 보관 그대로·CAP 바이트. 검증 2차 도구(`vg3_*`)·하네스·k92t 구동기·판정기·`k92t31_unit.py`는 import하지 않음.
- 고정 전에 읽은 것(공개): 보충 31 전문, 보충 29 §5, 보충 27 §2.3·§5, 보충 24 §4.2–4.4, 보충 18 §3.3 G5 글; 출력 꼴을 알려고 코드(`k92t31.py` 상수·scan31·unit31 단계, `k92t31_unit.py` 머리말·결과 꼴, `k92t31_judge.py` 봉인 훑기, `k8b_commit_gates.py:117-120`·`:797-798` 제외 상수와 `compare_g5`, `sa_compare.flatten`, `k92_gates.judge_g4_plant`, `rj27.py` plant 행 꼴, `rv_capman.py`); 검증 2차 보고서 `VERIFY_GATES_K92B1_r2.md`; LOG 끝. 작업 지시 글에 Apply A31 보고 요약(134/45/0, 공통 97·다름 0 등)이 들어 있었음. OUT31 파일·두 pytest 로그·봉인 파일·G-K4 행 파일·`rjg4.json`·CAP·`cap_manifest.json` 내용은 열지 않음.

## 2026-10-22 03:39 +0900 — VerifyGates 3: 도구 고정 (데이터 첫 읽기 전)

- 이 항목 덧붙임 전 LOG sha256 `664fb1eb3830749dd4d22f6ddda607ad462cd7d3cd1851dd9cea8f8945acf32f`, 226394 B.
- 고정 목록 `KB/vgates4/vg4_pins.sha256` sha256 `fb4fa16fb9d711e115e4cd8237ac8b5aafccf845873198e6b088187956a47896` (9줄, `sha256sum -c` 9/9 OK). 아래 64자 sha가 이 LOG에 적힌 뒤에만 구동기 `vg4_run.py`가 데이터를 엽니다(구동기가 시작 때 자기 도구 7개의 sha가 LOG에 있는지 기계로 봄).
  - `vgates4/vg4lib.py` `2e5a9d133b76c22dbace1ce7376cf378f19c637f0215bd713df04a5713d1902b`
  - `vgates4/vg4_scan.py` `bef3d5c78f8a3da7f0dea7d0b541d4281caadc9c4ea6da97ed36b3dbfe485a3c`
  - `vgates4/vg4_unit.py` `eed86ef25f9a212f52c5626f3318a25973dab8c95178b7ce2f08636af53b938e`
  - `vgates4/vg4_gk4.py` `0f81492561ae8dc61fc4a46aad7a07a9037a47224c403c7a13f04770e6434498`
  - `vgates4/vg4_keep.py` `68798acec4613a6ae1542a1874716cdc1e54a74c08c528c1b3ad9f985cb90b8d`
  - `vgates4/vg4_run.py` `56c10d1b0ade22f4567767592ae076c2caf438109330e24c3d4273a58b5612d9`
  - `vgates4/vg4launch.ps1` `2848be71c8d7bee17c496489c049f7a96687067b40820be35394389c721de4f8`
  - `vgates4/vg4_synth.py` `4943ec4d1808b8042e1fa265c5f87ce6034194af12699113206f4e13ae9f910a`
  - `vgates4/out/synth.json` `d6de503131383b1efe8cbd9b6a3e1178ccf7f3f101b9b2d408e1f2ad8da4d603`
- 쓰기만 하고 바꾸지 않는 남의 도구(참고): 스냅숏 `KB/impl/k92snap.py` `0dbd7d2c75f982d867eff46f27b1c2d8fbf34301d39952bdc87ebd7a0c8beeff`(실행만), pytest 발사기 `SP/k8b_impl/run_pytest_bn.py` `fe4451e431a74e7653c5f064e7f2331f17ca9302148da86e51eb4e81c033489e`(합성 시험에서만 실행).
- 고정 전 시험 [실행]: `vg4_synth.py` 합성 입력만 80/80(진리표 T1–T22, 합성 봉인 뿌리 둘, G5 규칙 13사례, CAP 3사례, pytest 합성 트리 8벌 실행·로그 판정 24사례, 가짜 배치 전체 구동 6사례). 실제 OUT31·봉인·G-K4·rjg4·CAP·pytest 로그 읽기 0. 합성 트리 `KB/vgates4/syn`, 출력 꼴 확인용 합성 트리 `KB/vgates4/dev/pyfmt`(실제 값 0).
- 독립성: 새 파일, 표준 라이브러리만. 하네스(`sa_*`·`k92_*`·`k8b_*`), k92t 구동기·판정기(기반·30·31), `k92t31_unit.py`, 검증 2차 `vg3_*`·`vglib`를 import하지 않음. 규칙은 보충 31 §2.2·§3.3·§4.3, 보충 29 §5, 보충 27 §2.3·§5.2, 보충 18 §3.3 글에서 짬(제외 낱말 상수는 보충 27이 줄 번호로 가리킨 `k8b_commit_gates.py:118`·`:797-798` 값).
- 다음: `vg4launch.ps1 -Tag vg4_run -Script vg4_run.py -ArgLine run` 하나(WMI 분리, BelowNormal, `PYTHONHASHSEED=0`, `python -B`). 열람 기록 줄은 구동기가 읽기 직전에 자동으로 씀.
- [2026-10-22 03:40 +0900] 열람 기록: CAP `OK2/k92t/jb/sa/cap/k92t`(파일 목록·크기·바이트 sha256만)과 기준 `KB/a31review/out/cap_manifest.json`, 목적 = 보충 31 독립 검증 V4 (VerifyGates 3 자동 기록)
- [2026-10-22 03:41 +0900] 열람 기록: 파일 = `OK2/sealed_s47/**/k92_record.json`(seed·vissim·vissim_reason 칸, 도구 메모리 안), 목적 = 보충 31 독립 검증 V2 (봉인 훑기 다시 셈); 그리고 `OK2/a31/scan31.json`·`sealed_records_a31.json` (VerifyGates 3 자동 기록)
- [2026-10-22 03:41 +0900] 열람 기록: `OK2/a31/unit_base/unit_b9734abe.log`·`OK2/k92t/jb/sa/unit_k92t.log`(두 pytest 로그 전체)와 `OK2/a31/unit_judge.json`·`unit31_run.json`·`steps31.jsonl`·`OK2/k92t/steps.jsonl`, 목적 = 보충 31 독립 검증 V3 (jb_unit 규칙 다시 셈) (VerifyGates 3 자동 기록)
- [2026-10-22 03:41 +0900] 열람 기록: G-K4 plant 행 원자료 16파일 = `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/probe_a25/plant/sa/jobs/k92pW/TL3_1500_SAF_OBS_H3/summary.json`; `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/probe_a25/plant/sa/jobs/k92pW/TL3_1500_SAF_OBS_H3/k92_record.json`; `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/sealed_s47/K9-2-1/plant/new/sa/jobs/k921g4W/TL3_1500_SAF_OBS_H3/summary.json`; `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/sealed_s47/K9-2-1/plant/new/sa/jobs/k921g4W/TL3_1500_SAF_OBS_H3/k92_record.json`; `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/probe_a25/plant/sa/jobs/k92pW/TL3_1050_s43_SAF_OBS_H3/summary.json`; `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/probe_a25/plant/sa/jobs/k92pW/TL3_1050_s43_SAF_OBS_H3/k92_record.json`; `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/sealed_s47/K9-2-1/plant/new/sa/jobs/k921g4W/TL3_1050_s43_SAF_OBS_H3/summary.json`; `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/sealed_s47/K9-2-1/plant/new/sa/jobs/k921g4W/TL3_1050_s43_SAF_OBS_H3/k92_record.json`; `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/probe_a25/plant/sa/jobs/k92pB1/TL3_1500_SAF_OBS_H3/summary.json`; `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/probe_a25/plant/sa/jobs/k92pB1/TL3_1500_SAF_OBS_H3/k92_record.json`; `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/sealed_s47/K9-2-2/plant/new/sa/jobs/k922g4B1/TL3_1500_SAF_OBS_H3/summary.json`; `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/sealed_s47/K9-2-2/plant/new/sa/jobs/k922g4B1/TL3_1500_SAF_OBS_H3/k92_record.json`; `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/probe_a25/plant/sa/jobs/k92pB1/TL3_1050_s43_SAF_OBS_H3/summary.json`; `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/probe_a25/plant/sa/jobs/k92pB1/TL3_1050_s43_SAF_OBS_H3/k92_record.json`; `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/sealed_s47/K9-2-2/plant/new/sa/jobs/k922g4B1/TL3_1050_s43_SAF_OBS_H3/summary.json`; `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/sealed_s47/K9-2-2/plant/new/sa/jobs/k922g4B1/TL3_1050_s43_SAF_OBS_H3/k92_record.json`, 그리고 `OK2/a27/judge/rjg4.json`, 목적 = 보충 31 독립 검증 V1 (D-K9-55·D-K9-60 G-K4 plant 원자료 재계산; v3c3-s31 1,500·v3c3-s43 1,050만, v3c3-s47 잡 0) (VerifyGates 3 자동 기록)
- [2026-10-22 03:42 +0900] VerifyGates 3 실행 끝: 판정 PASS (V4=True, V2=True, V3=True, V1=True, out31_unchanged=True, snap_before_same=True, snap_after_same=True), 출력 `KB/vgates4/out/vg4_result.json` sha256 `0b7654eca9e1165fad42ebe59b28bde91598d0b183f0cf694a21ba09a398b603` (VerifyGates 3 자동 기록)

## 2026-10-22 04:06 +0900 — VerifyGates 3: 끝 (독립 검증 A31 PASS)

- 이 항목 덧붙임 전 LOG sha256 `855ac0c683ca2b6fcb12cf72adf36b6c9e8af1682d99aaf240d211ff4068c53d`, 232549 B.
- 결과 [실행]: V1 G-K4 plant 4행 PASS(파일별 8/8 PASS) = `OK2/a27/judge/rjg4.json`(`246f28aa…`); V2 봉인 훑기 134/45/0, seed 분포 `{'31': 42, '43': 47, '47': 45}`, 두 길 어긋남 0 = `OUT31/scan31.json`·`sealed_records_a31.json`; V3 jb_unit PASS(공통 97, 다름 0, 0/0, 통과 아닌 공통 2 같음, P1–P10 20/20) = `OUT31/unit_judge.json` 13항목; V4 OUTK 26·OUT30 2·`k92t30_chain.txt` sha 같음, C7·C9 참, WT 없음·GWT8·K8 그대로, CAP 3,944파일·1,690,146,202 B·목록 `5340ac03…` = 기준. OUT31 기록 8파일 sha = 적용 보고 값. 스냅숏 앞·뒤 s02 대비 SAME. `a31_pins` 133줄 가운데 다른 것은 127줄 `GATES_K92B1.md`(`449b361e…`, A31-N2 설계된 바꿈) 하나.
- 보고서 `KB/VERIFY_GATES_K92B1_r3.md` sha256 `6fb66ac5b8de8bbd00df420bc3b1bf5364e5f95148574dd2834204e3df3ac189`(155줄, 22461 B, LF), 사본 `OK2/VERIFY_GATES_K92B1_r3.md` 같은 바이트(`cmp`). 결과 `KB/vgates4/out/vg4_result.json` `0b7654eca9e1165fad42ebe59b28bde91598d0b183f0cf694a21ba09a398b603`. 도구 고정 목록 `KB/vgates4/vg4_pins.sha256` 끝 대조 9/9 OK(고정 뒤 바뀐 도구 0).
- 공개: (1) 고정 전 노출 — 작업 지시 글의 적용 보고 요약, 출력 꼴을 알려고 읽은 코드(`k92t31.py`·`k92t31_unit.py`·`k92t31_judge.py` 봉인 훑기·`k8b_commit_gates.py` 제외 상수와 `compare_g5`·`sa_compare.flatten`·`k92_gates.judge_g4_plant`·`rj27.py`·`rv_capman.py`), OUTK `jb/sa/unit_k92t.meta.txt`와 `steps.jsonl`의 `jb_unit` 줄(이름·rc), OUT31 파일 이름·크기, G-K4 입력 16파일 있음 여부. (2) 넓은 트리(OK2 전체·TK 전체) 메타데이터 개수 세기를 백그라운드로 시작했다가 너무 느려 내가 멈춤(내 `find` 하나, 출력 0); 좁은 자리(OUTK·SEALED·OUT30·OUT31·a27·probe_a25/plant·snap·logs·OK2 맨 위·TREE·V4)만 03:39 뒤 바뀐 파일 0으로 다시 셈(SEALED는 개수만). (3) 해석 선택(경로 문자열 예외 '한쪽이라도 뿌리 품음', bool·null 보고만, 읽지 못하는 s47 기록은 나쁨)은 도구 머리말에 고정 전 선언, 실제 자료에서 결과 차이 없음.
- 지킨 것: VISSIM·COM·러너·동결·재생·실제 pytest 0, 커밋·브랜치·푸시 0, OUTK·OUT31·OUT30·SEALED·TREE·GWT8·K8·V4 쓰기 0, 봉인 시드·codex 64cf 0, s47 G-K4 잡 0. 끝에 python·VISSIM 0. GWT8 head `e27ceac8`·status 0줄·6커밋·K8 `b9734abe`·원격 k92 0·worktree a31 0(04:03).
- 다음: 보충 31 §4.4대로 K92_GATES_PASS 조건의 마지막 칸(독립 검증 A31)이 채워짐 → V-B → VerifyVB. V-A·푸시는 사용자 결정 뒤. 이 검증은 V-B를 하지 않음.

## 2026-10-22 04:19 +0900 — V-B: 사전 점검에서 STOP (사슬 계산 0, V-B 데이터 0)

- 이 항목 덧붙임 전 LOG sha256 `4b81161ae8ddd9272d6d7a79e3f1face726bb8754b7a4a7eabcce5b47376d8a1`, 235406 B.
- 사전 확인 [실행 04:0x–04:18 KST]: 보충 24–31 sha = `.sha256` = 고정점 8개 모두 일치(31 = `8541ccb7…`), 결정 기록 `09974cfc…`. GWT8 head `e27ceac8`, status 0줄. `TK/vb_*`·`OK2/vb*` 없음. C: 40 GB, D: 388 GB. VerifyGates 3 PASS(04:06 항목) → 보충 31 §4.4 K92_GATES_PASS 조건 채움 → V-B 차례.
- 찾은 것 V-B-D1 [읽음·실행]: 어댑터는 직전 행동 파일의 경로·바이트 sha를 출력 잎에 적습니다(sdmpc.py:513-533 `load_prices` 영수증, ADP:11084-11134 `prediction_error.source_action_json`, `lane_plant_runtime.py:650-673` `vsl_cohort_initialization`, ADP:13051-13093 `physical_ramp_recorded_csv`). RR v3c3-s41 기록에서 그 잎을 찾아 K9-2-5 `k92_compare` 규칙 함수(`in_hard`·`d_rule`·`r3_item`·`V`)로 분류: 사슬 앞 출력을 받는 결정에서 반드시 다른 잎 = 무제어 3(HARD 1), 첫 SDMPC 12(HARD 1), SDMPC←SDMPC 16(HARD 3: `/prediction_error/source_action_json`, `/metadata/sdmpc_state/previous_application/{source,receipt_sha256}`). RR 쓰기 금지라 사슬 파일 자리는 OK2 아래이고 N2는 OK2를 `<run>`으로 바꾸지 않음; 영수증은 사슬 CSV 경로를 담아야 `load_prices`가 받음(sdmpc.py:525). → OFF 14결정 중 10결정(T=3,150 ×3, VB-41w T=150–1,050 ×7)은 사슬 기구가 완벽해도 VB-I1 결과 넷 FAIL로 정해짐 → VB_INCOMPLETE(S-K15). 데이터 전에 멈춤.
- 둘째 빈칸 V-B-D2 [읽음]: VB-M5·M6·M8·VB-I5가 쓰는 `k92_record.json`은 plant 잡 기록기(`k92_record.py:1-17`, `sa_worker.py:75`·`:744`·`:1144`)이고 결정 재생은 만들지 않음. 사슬 결정에서 만드는 길이 정의되지 않음.
- 기록 런 사실(사슬 데이터 아님) [실행 `rrflags.py`]: V-B 41결정 시각의 RR 기록 모두 status ok, `head_observation_prior_discarded` 0.0, `snapshot_sec` = T, hold 파일 0; (173, p4) 하한 키 s31r·s43 1개, s41 0개.
- 보고 `KB/k92_vb/VB_PRECHECK_STOP.md` sha256 `e9a0975869def9892b5f3f46b74c467e8856a9e6f6d8fa0fd03ad918bb5113b6`(102줄). 사용자 질문 Q1(VB-I1 고침: 좁은 허용 A_VB / 보고만 / 첫 결정만), Q2(`k92_record` 길: 측정 훅 / 하네스 plant 잡 / "없음"), Q3(보고서 자리 두 곳).
- 개발용 탐침(판정 도구 아님, 고정 대상 아님; RR 기록·GWT8 코드만 읽음, 경로·규칙 이름·계수만 출력, 목적값·예측값 0): `KB/k92_vb/dev/prevleaves.py` `d42343f7acce54801434bf717b4ce3749e145199c6ba877a20acdf756e344e96`, `classify.py` `18a1e4620da26bb361ac16428414804fb149225081d66fbd182e2477aa998f32`, `classify_out.json` `eda96865db22fb67165c5fa4a3569954962934405e9e17af389eeba78e9c1ea6`, `dirleaves.py` `1c4003088ee83e28f7184eee1c924c182328fd36a40b0fbae65641911a964ad0`, `rrflags.py` `a031c6457238c647303b338b71011a2838b6770c9135065c407275a55936bc9c`.
- 하지 않은 것: V-B 트리·구동기·재계산기·고정, 사슬 계산, `OK2/vb/`, VerifyVB, V-A, 커밋·브랜치·푸시, VISSIM·COM·러너·동결, 금지 시험, 봉인 시드·codex 64cf. 끈 프로세스 0. 04:18 python·VISSIM 0.
- 다음: 사용자 결정(Q1–Q3) → 필요하면 보충 32(데이터 전 고정) → V-B 처음부터.

## 2026-10-22 04:29 +0900 — VerifyVB: 도구 고정(실행 전)

- 이 항목 덧붙임 전 LOG sha256 `86e907d80353734a1ff323351e9e116f23c265a9306a5cee8b7bddffcb8c113f`, 238794 B.
- 대상: V-B 보고 = `KB/k92_vb/VB_PRECHECK_STOP.md` `e9a09758…`(V-B는 사전 점검 STOP, 사슬 출력 0개). `VB_REPORT.md`·`K92_VB_REPORT.md`·`OK2/vb`·`TK/vb_*` 없음 [실행].
- 검증 도구(새 파일, 첫 실행 전 고정) `KB/k92_vb/verify/vvb_pins.sha256` `1415cc7f49a3b3836394d2a3fdd0839e86add2283c4a507152b982a319c8de49`:
  - `vvb_a.py` `b3e62b1fa9139916c8a24cf6a88a0b30eefa457a5703bb189d32afd15098b1fa` — 독립 재계산(표준 라이브러리만; GWT8·dev 탐침·하네스 import 0). 보충 21 §6 글로 다시 짠 N·HARD·D 규칙으로 §2.2 잎 분류, 영수증 꼴 사실, §4 기록 표지, VB-I1 결정 수.
  - `vvb_b.py` `ea35262733fbb52269742ca568730554685c1b173fd2a63256832acd13ab8b06` — 판정기 거동 탐침: 선언된 VB-I1 판정기 GWT8 K9-2-5 `k92_compare.compare`(블롭 `2b2b5523…`, sha256 `3e2da987…`)를 import해, RR 기록 사본에서 직전 행동 자리·영수증·JSON sha 잎만 바꾼 합성 출력(ctrl/pathonly/chain/rrsib)을 판정. 어댑터·재생·V-B 데이터 0. 합성 JSON은 비교 뒤 지우고 sha만 남김.
  - `vvb_launch.ps1` `2be8b445f57bd94a6c70c7d44b9790b3e2e78f064b7721fc8925635d79b3a4d1` — WMI 분리·BELOW_NORMAL·PYTHONHASHSEED=0·python -B (vg4launch.ps1 꼴).
- 공개: 고정 전에 읽은 것 = V-B 보고(VB_PRECHECK_STOP.md), LOG 끝, dev 탐침 4개 소스(출력 classify_out.json은 아직 안 읽음), 보충 21 §6·24 §14.1, GWT8 코드(k92_compare·k92_replay·sdmpc·ADP·lane_plant_runtime·k92_record 머리), RR 파일 이름·크기.
- RR 결정 폴더 3개 목록(`ls -l --time-style=full-iso`) sha256 `db86b508…`, 파일 645개씩(실행 전 스냅숏). python·VISSIM 0.

## 2026-10-22 04:39 +0900 — VerifyVB: 끝 (V-B 사전 점검 STOP 보고 r1 재계산; 숫자 다름 0, 결론 그대로)

- 이 항목 덧붙임 전 LOG sha256 `2eae734c0e296fec695f5e091879680194fd13fc6f716d049960d8986b553c3d`, 240671 B.
- 대상: V-B 사슬 출력 0개라 보충 31 §4.4의 VB-I/VB-M 재계산 대상 없음. 대신 `KB/k92_vb/VB_PRECHECK_STOP.md` r1(`e9a09758…`)의 사실·숫자·논리를 고정 도구(04:29 항목, `vvb_pins.sha256` `1415cc7f…`, 끝 대조 3/3 OK)로 다시 냄.
- 결과 [실행]:
  - 독립 재계산 `verify/out/vvb_a_01.json` `618b9592e7753147cbc3cf139d4140cc1a099bc636acf2e151f8c8aeb8323741`(재실행 `vvb_a_02.json` 바이트 같음, 화면 기록 `e235b6f8…` 같음): 사슬 결정 10개 전부(r1은 s41 다섯) 잎 수·반드시 다른 잎·HARD 수 = r1 표(무제어←무제어 3/3/1 ×5, T=900 21/12/1, SDMPC←SDMPC 25/16/3 ×4); dev 다섯 결정과 경로 집합 같음; 사전 키 0; 직전 파일 sha는 .json·.csv·.json.applied만; VB-I1 14·사슬 10·첫 4, VB-I4 55; RR 영수증 4개 3줄 꼴 참; §4 표 41결정 모두 같음(hold 이름 검사 넓혀도 0).
  - 판정기 거동 탐침 `verify/out/vvb_b_01.json` `e0d5537b29de99aadfb3ea6715a7b1d65b91601366cf9b7aa5b89dc08df2700c`(K9-2-5 `k92_compare` `3e2da987…`, 40번): ctrl 10/10 PASS; pathonly·chain 10/10 FAIL(HARD 경로 = r1 표); rrsib(N이 `<run>`으로 맞추는 가상 자리) 무제어·T=900 보류(D2b 1), SDMPC←SDMPC FAIL(영수증 sha HARD) → 자리 고침만으로는 모자람.
  - 코드·문서 자리 [읽음]: §2.1 네 곳 같음(ADP 끝 :13094로 고침). 보충 24 :540의 `sdmpc.py:461-470`은 지금 블롭 `d21fdd49`(74cd495f·b9734abe·e27ceac8 같음)에서 QP 코드, 영수증 규칙은 :513-533; cd06a39a에서는 :455 시작이라 옛 줄 번호로 보임 [추론]. V-B 반환 글의 ":550"은 :540.
- 고친 보고: `KB/k92_vb/VB_PRECHECK_STOP.md` r2 `b96637d9bc35ecf5155817058f53c6421157b24f006ae65ae9bac788a1ad9e86`(160줄, LF), r1 보관 `KB/k92_vb/VB_PRECHECK_STOP_r1.md` `e9a09758…`(바이트 같음). 바뀐 곳 11행(§8): 줄 번호 1, 비용 인용 7–9 h → 8–9 h(보충 24 :577), 범위 넓힘·판정기 탐침 표·설명 다듬음. 결론(STOP, V-B-D1·D2, Q1–Q3) 그대로.
- 공개: (1) `vvb_b.py`는 하네스 판정기 `k92_compare`를 import함 — 보충 31 §4.4 글과 다름; 판정기 거동을 묻는 탐침이라 불가피, 독립 재계산은 import 0인 `vvb_a.py`가 맡고 둘이 같음. (2) 사슬 한 토막 재실행·비트 대조는 하지 않음(사슬 출력 0; 지금 돌리면 보충 32 전 V-B 데이터). (3) 합성 사본 폴더 `verify/syn_b_01`(CSV·진행 기록 사본 60개, 1 MB)은 판정 뒤 지움.
- 지킨 것: RR 결정 폴더 목록 sha 앞·뒤 `db86b508…` 같음, RR 위 새 폴더 0. GWT8 head `e27ceac8`·status 0줄·K8 `b9734abe`. VISSIM·COM·러너·동결·재생·어댑터 0, 커밋·푸시 0, 금지 시험 0, 봉인 시드·봉인 뿌리·codex 64cf 0. 끈 프로세스 0, 끝에 python·VISSIM 0. 출력·기록 파일: `verify/out/logs/vvb_a_01.txt` `e235b6f8…`, `vvb_b_01.txt` `9a61e083…`, `wmi_launch_lines.txt` `e02d8962…`.
- 다음: 사용자 결정 Q1–Q3 → 필요하면 보충 32(데이터 전 고정; 보충 24 :540 줄 번호도) → V-B 처음부터 → VerifyVB. V-A·푸시·GB-7′ 목록 보충은 그 뒤 사용자 결정.

## 2026-10-22 09:45 +0900 — Declare A32: 보충 32 작성 시작 (D-K9-62·63·64)

- 이 항목 덧붙임 전 LOG sha256 `0fc4b2ae6aad47fb63a2df34a6694ae8f427520a37d6b7bdfa607279165d1b2c`, 244,072 B.
- 고정점 [실행 sha256]: 결정 기록 `K9_1_J1_NOTES_20261013.md` `402eaf59aa738bef1dcb27f41d51eba873a8cb6abdbfde7707dfc6b146cfbd3b`(204줄, D-K9-62~64 :195-204) = 작업 지시 값. 보충 24 `d46db6dc…`·25 `4fd7b599…`·26 `8f835616…`·27 `4ce8b27a…`·28 `9881eb40…`·29 `4bd6dc8d…`·30 `ba556227…`·31 `8541ccb7…` = 각 `.sha256`, 각 고정점 안 64자 1회. V-B 사전 점검 보고 `KB/k92_vb/VB_PRECHECK_STOP.md` r2 `b96637d9…`.
- 상태 [실행]: GWT8 head `e27ceac8`, 브랜치 `claude/k92-b1-20261016`, K8 브랜치 `b9734abe`, status 0줄, `b9734abe..HEAD` 6커밋, 원격 k92 0. `OK2/vb*`·`TK/vb*` 없음(V-B 데이터 0). python·VISSIM 0. C: 40 GB, D: 388 GB.
- 이 단계에서 할 일: 보충 32 글 + 새 도구(`KB/a32decl`, 커밋 안 함: 측정 훅 `vbhook/sitecustomize.py`, 후보 고르기 `vb_select.py`, 영수증·닫힌 잎·보고 전용 비교·훅 영향 0 판정 함수 `vb_lib32.py`, 닫힌 잎 목록 JSON과 그 생성기, 확인 도구) + 합성 자료로만 확인 + 기대 고정 목록. 결정 재생·사슬 계산·훅 영향 0 시험 실행 0(그것은 V-B 단계). RR 은 읽기만(영수증 바이트 대조용). VISSIM·COM·러너·동결·커밋·푸시 0.

## 2026-10-22 10:16 +0900 — Declare A32: 보충 32 작성 끝 (D-K9-62·63·64)

- 이 항목 덧붙임 전 LOG sha256 `db649ee98d1e9250957593d03b8f0dce4d874ae26768ca510996e22d8a3f645b`, 245,505 B.
- 보충 32 Declare 판 `SP/K8_PREDECLARATION_AMENDMENT_32.md` sha256 `176ded8997b53206b320b15efb3c92b79de2b256ee8293acbd41c1dabbd36e52`(89,398 B, 532줄, LF, CR 0), `.sha256` 같은 값 [실행 `sha256sum -c` OK]. 고정점 `KB/AMENDMENT32_FIXED.md`는 반박 검토가 만듭니다(아직 없음).
- 내용: VB-I1 판정 = 사슬 첫 결정 4개만(결과 넷 PASS, SDMPC 셋은 A_K92 줄로 D5 뿌리 점검); 사슬 이어받는 OFF 10결정 = 닫힌 잎 목록(NN 3경로/잎 3·HARD 1, SN 9/12·1, SS 13/16·3)을 뺀 보고만, 목록 밖 차이는 표·굵은 문장·보고서 맨 앞 요약; VB-I2–I6 그대로 55결정; 새 VB-I7(훅 무결성) STOP; 측정 훅(`omega_costs` PY_START에서 REC `network_facts`·`collect`·`write`(H 3) 호출, 후보 → `vb_select.py`로 고른 행동과 서명 같은 것 고름) → `VBR/chain/<사슬>_<팔>/rec/t<T6>/k92_record.json`; ZI(55결정 밖: v3c3-s43 T=1,050 OFF·B1, T=750 B1; 같은 준비 폴더·같은 출력 경로로 훅 끔→켬; 규칙 = CSV 같음 + KC 결과 넷 PASS + 진행 기록 같음 + 차이 잎 모두 KC `is_f3` 벽시계; 거짓 → S-K51); 구동기 V0–V10·발사 규칙(`k92_replay.py`와 같음, 직전 경로만 다름)·영수증(VBS :1281-1287 바이트 꼴, `.sdmpc_pending` 있을 때만)·합성 자기 시험(자식 0)·재계산기 독립 요건; 보고서 정본 `KV/K92_VB_REPORT.md` + 같은 바이트 `KB/VB_REPORT.md`; 보충 24 :540 → `sdmpc.py:513-533`; 공개 P1–P11(D-K9-62 = (나) 권장안 아님, D-K9-64 수용); STOP S-K51–S-K55.
- 새 도구(커밋 안 함, `KB/a32decl`) [실행 sha256]: 측정 훅 `vbhook/sitecustomize.py` `4d7e0375116c3f805aa223651da0dc1c0c04b7d3315062e98e21137ba60aa321`, 고르기 `vb_select.py` `33adfd5033c277a3ad640f745a69efb2a929b27c1ff2a88d794dfa69b489e9cc`, 도움 함수 `vb_lib32.py` `504999a196a9e08582f303d4ad38d4cc661fcfc765df62d11bc4cc7c05ddc75f`, 닫힌 목록 생성기 `make_closed32.py` `20f058b7d195c4b898def664567a5ca7c0db5e14545ca39bc8b6d27de3a34802`, 닫힌 잎 목록 `vb_closed_leaves.json` `b800be45ae3e4e5030ed31ecd221e6288d52c2a287bdeaa5efee243e3cc2f426`, 확인 도구 `dry_a32.py` `4215f7f8ed70d148c48ec999962d37068b961e07a715b0557737193a1b155fa3`, 기대 고정 목록 `a32_pins.expected.sha256` `9e4dc5925e36fcc092f1b4ace4c3e86600d8f96422f3720653fe7d72d4514fcb`(51줄, `sha256sum -c` 51/51 OK).
- 데이터 없는 확인 [실행 `dry_a32.py all`, 합성 입력만 + 기록기·비교기 바이트(GWT8, 읽기만) + RR 영수증 다섯 바이트·CSV 크기]: static·closed·hook·select·receipt·reportonly·zi·mutants 모두 참, 요약 `dry/decl/dry_a32_summary.json` `172c15761e06c71cf6a0a7103328524287b72facc75f5fe73e66a2fbd0b8ff23`. 개발 중: 첫 실행은 망가뜨림 M1에서 확인 함수 예외로 끝남(읽기 오류를 거짓으로 세게 고침), 둘째 실행은 M8이 의미 없는 망가뜨림이라 안 잡힘(`collect`는 T0를 안 씀 → `write` T0로 바꿈), 셋째 실행 8/8. 훅·고르기·도움 함수 바이트는 첫 확인 실행 뒤 그대로.
- 스냅숏 `OK2/snap/s37b_a32decl.json` `765c287dacf5ab46f26df6f0031ab37b50b4d46495e2bffbe6a84faefa32b5ab`(WMI `a32decl_snap` 09:59:58 PID 5132, 51.4 s), s02 대비 SAME.
- 열람(공개 P5): RR 영수증 다섯·CSV 크기, RR `decision_budget.json` 벽시계(s41 T=1·150·750·900·1,050·3,000·3,150, s43 750·1,050), RR 결정 폴더 파일 목록 일부, 몫 가르기 `DA/hook/S1_A0h` 목록과 E2 기록(개수·키·첫 기록 행동 녹색), OUTH `gh3`·`gb9` 준비 기록 머리, 세 튜닝의 `phase_price` 절. V-B 데이터 0.
- 지킨 것 [실행 10:11]: VISSIM·COM·러너·동결·결정 재생·어댑터·plant 잡 0, VBT·VBR 없음, 사슬 계산·ZI 0, 커밋·브랜치·푸시 0(GWT8 head `e27ceac8`, status 0줄, K8 `b9734abe`, 6커밋, 원격 k92 0, worktree vb 0), 금지 시험 0, 봉인 뿌리·봉인 시드·v3c3-s47·codex 64cf 0. 끈 프로세스 0. 끝에 python·VISSIM 0. C: 40 GB, D: 388 GB.
- 다음: ReviewDeclare A32(고정판·고정점 `KB/AMENDMENT32_FIXED.md`) → V-B 단계(§4.1 고정 → V0–V10) → VerifyVB. V-A·푸시는 사용자 결정 뒤.

## 2026-10-22 10:17 +0900 — ReviewDeclare A32: 보충 32 반박 검토 시작 (Declare 판 `176ded89…`)

- 이 항목 덧붙임 전 LOG sha256 `28a6622ce061bf34952242624c6c32e333756dd1af18885d980f98f15b7183c6`, 249,863 B.
- 고정점 [실행 sha256]: 결정 기록 `402eaf59…`(204줄, D-K9-62~64 :195-204) = 작업 지시 값. 보충 32 Declare 판 `176ded8997b53206…` = `.sha256`. 사본 `KB/a32review/r1/K8_PREDECLARATION_AMENDMENT_32_declare.md`(같은 바이트). python·VISSIM 0. C: 40 GB, D: 388 GB.
- 이 검토의 도구·출력 = `KB/a32review`(RV32). 할 일: VB-I1 판정 4결정이 구조로 실패할 길(RR 기록 파일·G-K0 허용 대조, 사슬 데이터 계산 0), 닫힌 잎 목록의 완전·정확(VB_PRECHECK_STOP §2.2·`vvb_a_01.json` 대조), 훅이 결정 출력·원천 고정(joint_runtime_source_pins, 보충 25 경로 글자 교훈)을 바꿀 길과 ZI 상태가 55결정 밖인지, V-B 데이터 0(파일 시각), VB-I2–I6 충족 가능(VB-I2 T=150 예외), 고정·STOP 규칙.
- 하지 않는 것: VISSIM·COM·러너·동결·결정 재생·plant 잡·어댑터 실행 0. VBT·VBR 만들기 0, ZI·사슬 계산 0. RR·동결본·GWT8·OUTK·봉인 뿌리 쓰기 0, 봉인 뿌리·봉인 시드·v3c3-s47 열람 0. 커밋·브랜치·푸시 0.
- [2026-10-22 10:52 +0900] ReviewDeclare A32: 검토 도구 고정 `a32review/rv32_nested.py` `aa12297b7ddd215d35b927c707901a5ea8a69db1ff5bdeb5ca46538f518f5f26`(실행 전). 읽는 것 = RR 기록 결정 파일만(J1 v3c3-s31 재실행·s43·s41, 사슬 14결정 시각의 JSON과 그 앞 사슬 결정 파일의 바이트 sha); 사슬 이어받는 10결정에서 바로 앞이 아닌 앞 사슬 결정 파일의 이름·sha를 담은 잎(닫힌 목록이 놓칠 수 있는 꼴)과 현재 결정 자기 출력 이름을 담은 잎을 찾음. 출력은 경로·종류·개수만(값 0). V-B 데이터 아님. WMI 분리(`KI/launch.ps1 -Tag rv32_nested`), BelowNormal, 한 번. 앞서 `py_compile` 한 번(문법 확인; 생긴 `__pycache__`는 지움).
- [2026-10-22 10:30 +0900] ReviewDeclare A32: 바로 위 줄의 시각 "10:52"는 내가 잘못 적은 것입니다(실제 고정·발사 시각 10:29, `date` 확인). `KI/launch.ps1`을 Git Bash의 `powershell -File`로 부르자 실행 정책에 막혀(실행 0) PowerShell 도구로 다시 불렀습니다: `rv32_nested` WMI 10:29:54 PID 8216, BelowNormal, python 0·VISSIM 0에서 시작.
- [2026-10-22 10:45 +0900] ReviewDeclare A32: `rv32_nested` 끝(rc 0) → `a32review/out/rv32_nested.json` (sha는 고정점 32 표). 사슬 이어받는 10결정 모두: 바로 앞이 아닌 앞 사슬 결정 파일의 이름·sha를 담은 잎 0, 자기 출력 이름을 담은 잎 0, 그 밖 결정 폴더 문자열 2(상태 경로 V). 바로 앞 파일 잎 수 = 닫힌 목록 + CSV sha(SS 13+3·9, SN 11+1·9, NN 2+1). 사슬 첫 4결정: 자기 출력 이름 잎 0. 그리고 인라인 대조(도구 파일 없음, 작은 JSON 둘 읽기): `vb_closed_leaves.json` = `vvb_a_01.json`의 "반드시 다름" 잎(경로·HARD·기록 개수) 10/10 같음, CSV sha 제외 목록 10/10 같음. 인라인 읽기(값 출력 0): RR 세 런 `run_provenance` 작업 뿌리·튜닝 sha 앞 16자, `launch_plan.json` 제어 시작 900, RR s41·s43 결정 폴더 파일 이름, 몫 가르기 `DA/hook/S*_A0h` `loaded_*.json`의 argv0, `DA/gates/adiff_S1_A0_vs_S1_A0h.json`의 경로 분류, OUTH `judge/gr2_gh3_result.json`·`judge/hash_result.json`의 허용 개수·F1 경로, OUTH `gb7/A/T000001/replay/replay_run.json`의 root. GWT8 코드 읽기(쓰기 0, `__pycache__` 새 파일 0 확인). Windows PID 재사용 시험: `cmd /c exit` 60번 차례로 → 서로 다른 PID 60(재사용 0).

## 2026-10-22 10:55 +0900 — ReviewDeclare A32: 보충 32 고정 (반박 검토 끝)

- 이 항목 덧붙임 전 LOG sha256 `ee9df4a7dda93cf29d165165a0db0656dbe24469b3f16f2a34ea7662404e92b2`, 253586 B.
- 고정판 `SP/K8_PREDECLARATION_AMENDMENT_32.md` sha256 `7f25c21e72fc2599022c72adb1976257413a8486f4898ffcec61f3c6b01423e7`(110,229 B, 605줄, LF, CR 0), `.sha256` 같은 값 [실행 `sha256sum -c` OK]. Declare 판은 `SP/K8_PREDECLARATION_AMENDMENT_32_r1.md`(`176ded8997b53206…`, `.sha256` 있음)로 남김. 고정점 `KB/AMENDMENT32_FIXED.md` sha256 `b59088ab44683f5990f2a44038c688aec59a21fcb5207e72b0bc7ee5782ddef4`(고정 시각 2026-10-22T10:53+09:00; Declare 판 sha는 앞 16자만). 기대 고정 목록 `KB/a32decl/a32_pins.expected.sha256` `9e4dc592…` 51/51 그대로; 훅·고르기·도움 함수·닫힌 목록·확인 도구 바이트 그대로.
- 고친 곳(글만, 보충 32 §14.1): R1 판정 4결정의 구조 실패 길 확인 근거와 VB-41w T=1 간접 선례(P13), R2 닫힌 목록 완전·정확(앞 사슬 파일 잎 0, `vvb_a` 10/10), R3 ZI (z5)의 F1 가정과 위험(P12), R4 훅이 원천 고정·D5·AD·시간 예산·GC를 건드릴 길 없음의 근거와 PID 겹침(P14), R5 보고 전용 INCOMPLETE 처리(출력 없음만 STOP), R6 표준 출력 파일 이름. 공개 P12–P15, 한계 §11-12·13, §14 검토 절 더함. 판정 정의·문턱·표본·STOP 규칙 바뀜 0.
- 확인 [실행]: V-B 데이터 0(파일 시각; `OK2/vb*`·`TK/vb*`·KV 구동기·재계산기·자기 시험·V-B 고정 목록·보고서 없음), GWT8 head `e27ceac8`·status 0줄·K8 `b9734abe`·`b9734abe..HEAD` 6·원격 k92 0·worktree vb 0, 끝에 python 0·VISSIM 0, C: 40 GB·D: 388 GB.
- 끈 프로세스: 내 파일 시각 `find` 하나(PID 612). 그 밖 0.
- 다음: V-B 단계(보충 32 §4.1 고정 → V0–V10, VBT·VBR 만들기부터) → VerifyVB. V-A·푸시는 사용자 결정 뒤.

## 2026-10-22 11:03 +0900 — V-B (보충 32): 시작

- 이 항목 덧붙임 전 LOG sha256 `3be2668dd3ecb92b5f5b2ba0b5e9754dc6c2bd1adf4cb0177bac6c339c49f993`, 255514 B.
- 고정점 확인 [실행 sha256]: 보충 32 고정판 `7f25c21e72fc2599022c72adb1976257413a8486f4898ffcec61f3c6b01423e7` = `.sha256` = 고정점 `KB/AMENDMENT32_FIXED.md`(`b59088ab44683f5990f2a44038c688aec59a21fcb5207e72b0bc7ee5782ddef4`) 안 64자. 결정 기록 `402eaf59aa738bef1dcb27f41d51eba873a8cb6abdbfde7707dfc6b146cfbd3b`(204줄) = 작업 지시 값(D-K9-62~64). 기대 고정 목록 `AD32/a32_pins.expected.sha256` `sha256sum -c` 51/51 OK. `KB/a31_pins.sha256` 133줄.
- 상태 [실행]: GWT8 head `e27ceac8`, 브랜치 `claude/k92-b1-20261016`, K8 `b9734abe`, status 0줄. `OK2/vb*`·`TK/vb*`·KV 구동기·재계산기 없음(V-B 데이터 0). C: 40 GB, D: 388 GB.
- 할 일(보충 32 §4): 구동기 `KV/vb_chain.py`·재계산기 `KV/vb_recalc.py` 작성 → 합성 자기 시험(자식 0) → `KB/a32_pins.sha256`(= 기대 파일 바이트)·`KV/vb_pins.sha256` 고정과 LOG 항목 → WMI 분리 `vb_chain.py chain`(V0–V10, ZI → OFF 사슬 → OFF 관문 → B1 사슬 → 무결성·지표·재계산 → 끝 대조) → 보고서. VISSIM·COM·러너·동결·커밋·푸시 0.

## 2026-10-22 11:23 +0900 — V-B (보충 32 §4.1): 도구 고정 (사슬 계산·ZI 전, V-B 데이터 0)

- 이 항목 덧붙임 전 LOG sha256 `d2c5e3b73d541f3ac6551ab8f2c94a84cbc4782a1f1efee84a4effc2f8a2d6e3`, 256790 B.
- (1) `KB/a32_pins.sha256` = 기대 파일 `AD32/a32_pins.expected.sha256` 바이트 복사(`cmp` 같음), sha256 `9e4dc5925e36fcc092f1b4ace4c3e86600d8f96422f3720653fe7d72d4514fcb`, 51줄, `sha256sum -c` 51/51 OK [실행].
- (2) 구동기 `KV/vb_chain.py` sha256 `4dc9297df760800ebb20948b05ba94a645d93a8c7e44abb64c511d1be21d6e99`, 재계산기 `KV/vb_recalc.py` sha256 `cab7939df8fd55ff4d7df36b058f8892d045a9aff5610b17c8f81f336d5c3e7c`. 자기 시험(합성, 자식 프로세스 0; 구동기는 `subprocess.Popen/run`을 막은 채 돎) [실행]: `KV/selftest/vb_selftest.json` `0bf303ef77566f7b67e215a7257ab9af30765f38f2659b8f0b0df87b459e8f54`(t1 발사 규칙 = VBT가 담을 `k92_replay.py` 822dd78f를 같은 프로세스에서 돌려 받은 인자·작업 폴더·환경과 같음 5꼴, t2 RR 영수증 5/5 바이트 같음·합성 쓰기 규칙, t3 쓰기 범위 허용 8·거부 27, t4 사슬 계획 55행, t5 VB-I2·I6·I7 27사례, t6 이어 하기 11, t7 AD32 고정 sha로 불러 씀 — 모두 참), `KV/selftest/vb_recalc_selftest.json` `27faab53a04db7bbce41600907b82802a157607f9b39a739d273dacca4a1d84f`(23사례 참: 고르기·VB-M 손 계산·결정 JSON 값/후보 서명/기록 숫자 바꿈 잡음).
- (3) V-B 고정 목록 `KV/vb_pins.sha256` sha256 `6bed354112b93b65d6ffe59bbc8b1472c5e3911683e0d0fcc31964e44514f366`, 4줄(구동기·재계산기·자기 시험 출력 둘), `sha256sum -c` 4/4 OK.
- 선언(실행 전, 데이터 0): ZI 비교 규칙은 보충 32 §3.5 그대로 "G-K0 비교로 같고 벽시계 잎만 다름"(`vb_lib32.zi_judge` + (z1)(z6)(z7)). 구동기가 글을 기계로 옮기며 정한 해석(데이터 전 고정, 보고서 공개): VB-I2의 "그 T 파일" = 출력 폴더에서 이름에 `<T6>`가 든 파일; VB-M7 "PFO 결과 목적값" = `joint_leader_selection.warm_start_objective`(sdmpc.py:990-994, cap 모드에서 held_objective = PFO 시작점), "유지 목적값" = `held_objective`, "고른 행동 목적값" = `selected_objective`; VB-M3 Δp3 = 사슬 안 이웃 결정(T−150, VB-41w T=1→150 포함) 차이, 부호 바뀜은 |Δ| ≥ 0.5인 것만 차례로, 평균 |Δ|는 모든 Δ; VB-M9 첫 다른 결정 = CSV sha가 RR 기록과 다른 첫 T, 벽시계 = 구동기가 잰 어댑터 시간과 `metadata.decision_wall_sec`. STOP을 늘리는 쪽 더함: V0 C2에 고정점 32 파일 sha(`b59088ab…`), V1에 VBT `k92_replay.py`(822dd78f, 자기 시험 대상과 같은 바이트)·`sa_arms.py` sha, 결정마다 VBT RS·SHO·REC·KC와 훅·고르기·도움 함수 바이트 전후 대조.
- 개발 중 공개: 재계산기 자기 시험은 첫 판이 통과한 뒤, "결정 JSON 값 하나를 바꾸면 잡음" 사례가 값 비교 함수만 보던 것을 실제 파일을 바꿔 다시 계산하는 꼴로 강화해 다시 돌렸습니다(둘째 판 출력이 고정 대상). 구동기 자기 시험은 한 번 돌림. 자기 시험의 합성 트리 `KV/selftest/syn`은 고정 목록 밖(남김).
- 다음: WMI 분리 `KI/launch.ps1 -Tag vb_chain -Script ..\k92_vb\vb_chain.py -ArgLine chain` → V0–V10.
- [2026-10-22 11:23 +0900] V-B driver: V0 사전 점검 first 참(C1–C12), `check_v0.json` sha256 `81cb17682cf7c78b14031374c8eaab63c22f294104df9bd207ae49bdfbf8fe5e`, 구동기 `4dc9297df760800ebb20948b05ba94a645d93a8c7e44abb64c511d1be21d6e99`, 재계산기 `cab7939df8fd55ff4d7df36b058f8892d045a9aff5610b17c8f81f336d5c3e7c`
- [2026-10-22 11:24 +0900] V-B driver: 스냅숏 s38_vb_v0.json SAME (s02 대비), sha256 `336951f0e6eb195d5c85bd4d81225659e2f9219ae6adb7dffcd7ad767b5a6316`
- [2026-10-22 11:27 +0900] V-B driver: V1 트리 `TK/vb_e27ceac8` (git archive e27ceac8 + CR 고침, 형태 CCCCCCCCCC, cr_pair 둘 참, RS·SHO·튜닝·REC·KC·k92_replay sha 기대값), 빌드 기록 sha256 `2ace33638b30a4daccb63544d55e668608e2f51e140a6f93706e79c0514bab0e`; GWT8 작업 트리 대비 바이트 다름 0·VBT만 0·GWT8만 1(보고만)
- [2026-10-22 11:27 +0900] V-B driver: V2 팔: SAF-B1 `65cac7ea0b33d8f0b5c8efc458307578bcae7a2e34d1d097ce448a18a65ada28` = 기대값, VB-I3 두 팔 참(차이 두 경로, 증거 sha = VBT 커밋 증거, 파일 sha), C12 참
- [2026-10-22 12:15 +0900] V-B driver: V3 ZI 세 칸 PASS, `VBR/zi/zi.json` sha256 `79c7988361cefa87a79586a93e06cf7207bb1ee853c7d1c1a77f80ccaa6129c5`
- [2026-10-22 12:16 +0900] V-B driver: 스냅숏 s39_vb_zi.json SAME (s02 대비), sha256 `81aaf7c4f0bbff217d62671daa68e8c4af68c6645411c8f7ba7d91f97dbad366`
- [2026-10-22 13:58 +0900] V-B driver: V4 OFF 사슬 14결정 끝(종료 0)
- [2026-10-22 13:59 +0900] V-B driver: STOP V5 (S-K55): OFF gate false (VB-I1 True, VB-I2 True, VB-I7 False)

## 2026-10-22 14:07 +0900 — V-B: STOP (V5, S-K55) — VB-I7 거짓 1/14 (훅 후보 폴더 PID 겹침), B1 사슬 0

- 이 항목 덧붙임 전 LOG sha256 `747a106f1d6e79e9b8e7c3f9637e2b64c8b7473d2ae5818c0a2f6025a4cf542b`, 261658 B.
- 실행 [실행]: `vb_chain.py chain` WMI 11:23:27 PID 14464 → V0 참 → s38 SAME → V1 참(VBT `TK/vb_e27ceac8`, 빌드 기록 `2ace33638b30a4daccb63544d55e668608e2f51e140a6f93706e79c0514bab0e`) → V2 참(SAF-B1 `65cac7ea…`, VB-I3 두 팔 참) → V3 ZI 세 칸 PASS(`VBR/zi/zi.json` `79c7988361cefa87a79586a93e06cf7207bb1ee853c7d1c1a77f80ccaa6129c5`; 훅 켬/끔 벽시계 비 0.991·1.043·1.022) → s39 SAME → V4 OFF 14결정 종료 0 → **V5 13:59:46 STOP S-K55**: VB-I1 4/4 PASS(VB-41w T=1, VB-31·43·41 T=3,000; SDMPC 셋 A_K92 2줄 참), VB-I2 14/14 참, **VB-I7 13/14**(VB-41 T=3,150 고르기 상태 `hook_error`). 구동기 종료 코드 3, 이후 python 0·VISSIM 0.
- 진단(파일 이름·시각만) [실행]: `VBR/chain/vb41_off/hook/t003150/hook_error_26704.txt` `c98097670e66928de549abd885a4e571d422d5dd75e233d56fdd7311809f77c4` = `os.makedirs(c_26704_0001)` FileExistsError(13:57:29). 그 폴더는 13:53:44에 PID 26704(부모 어댑터 5132)가 만들었고, `loaded_26704.json` 시작 시각 13:56:26 = 둘째 프로세스(같은 PID)가 덮어씀. 한 결정 안 Windows PID 재사용 = 보충 32 P14가 적은 STOP 쪽 위험. 고르기 `k92_select.json` `fe8b63197a0b168e091ec443a3f9b8e29bb71abf14a9fbfd286cbc3b904bdc9c`.
- 보고 전용 10결정(판정 아님, D-K9-62): CSV 10/10 기록과 바이트 같음, 목록 밖 HARD 0, 보이지 않은 목록 잎 0; **목록 밖 미분류 = SDMPC 사슬 결정 5개(VB-41w T=900·1,050, VB-31·43·41 T=3,150)에서 결정마다 같은 11경로(모두 D1 `action_token`), 잎 31·29·27·29·31**; NN 5결정 0. `judge/vb_i1.json` `9c1749a9f7bc6331f527026cb53ae83c7ebbdfd7c479695e522e38615fe358e9`, `judge/vb_reportonly.json` `30fcda3ec3e3d8b7c08a476a02b96d47f8c049f6209c4bac3e603f2f983f971c`, `STOP_vb_V5.json` `4127cbf2bfbbd3625bb625e388c29c6191b755e4a774b9f1cbbcacd3490a751c`.
- STOP 뒤 읽기만 확인 [실행]: 스냅숏 `KI/launch.ps1 -Tag vb_stop_snap`(14:01:53 PID 20228) → `VBR/poststop/s40x_vb_stop.json` `415ae03a0e30e5f6fbb100744073a61b6a737ff0326ae1838249e7e4f3b6f646`, s02 대비 SAME. `KB/a32_pins.sha256` 51/51·기대 바이트, `KV/vb_pins.sha256` 4/4, GWT8 head `e27ceac8`·status 0·K8 `b9734abe`·6·원격 k92 0·worktree vb 0, RR 결정 폴더 목록 sha = V0, OK2 vb 밖 목록 = V0, 훅·고르기·도움 함수·VBT RS·SHO·REC·KC 바이트 그대로. C: 42 GB, D: 411 GB.
- 보고서(STOP 판 r1): 정본 `KV/K92_VB_REPORT.md` = 사본 `KB/VB_REPORT.md` = `OK2/vb/K92_VB_REPORT.md` sha256 `d7bf44f3e309aa4ae8e5084b0db238f9baeb2870b6d75b4bea7b6d854427ea00`(257줄, `cmp` 같음). 실행 출력 쪽 사본은 다시 돌릴 때 V10 "OK2 vb 밖" 대조를 깨지 않으려 OK2 맨 위가 아니라 `OK2/vb`에 둠.
- 세션 도우미(판정 도구 아님): `KV/poll_vb.sh` `8f2f7b4aee632cee828a1385d1a922e5aa3d26a1ac5db72018a0b52dbe37634a`(진행 확인, 읽기만), `KV/mk_tables.py` `4351c2ed7b2d825172670fd37e0d98dac39099272ae059e9d9b8673c8e61749e`(표 서식, VB-M 표가 없어 쓰지 않음). 보고서 초안 `KV/rep_static.md`는 보고서에 옮긴 뒤 지움.
- 하지 않은 것: B1 사슬 0/41, V6–V10, VB-M, 재계산. 도구 고침 0. VISSIM·COM·러너·동결·커밋·푸시·금지 시험 0. 봉인 시드·봉인 뿌리·v3c3-s47·codex 64cf 0. 끈 프로세스 0.
- 다음: 사용자 결정(보고서 §6 Q1 훅 PID 겹침 처리, Q2 `action_token` 11경로 처리, Q3 다시 돌림 자리). V-A·푸시는 그 뒤.

## 2026-10-22 14:22 +0900 — Declare A33 (보충 33) 시작: 훅 이름 고침(D-K9-65)·보고 전용 action_token 글(D-K9-66), V-B 데이터 0

- 이 항목 덧붙임 전 LOG sha256 `71b698eea2486fa35b7022b5c130a37910aabfc6e2e2ec4ab9640ef827105bfb`, 265344 B.
- 확인 [실행]: 결정 기록 `SP/K9_1_J1_NOTES_20261013.md` sha256 `187242343570f1fe4e22d644509139e87ff59f76c70458b58160c1cde5387109`(214줄, D-K9-65·66 :206-214) = 작업 지시 값 18724234…; 보충 32 고정판 `7f25c21e…` = `.sha256`, 고정점 32 `b59088ab…`; V-B STOP 보고 r1 `KV/K92_VB_REPORT.md` = `KB/VB_REPORT.md` = `OK2/vb/K92_VB_REPORT.md` = `d7bf44f3…`; 고정 훅 `AD32/vbhook/sitecustomize.py` `4d7e0375…`. GWT8 head `e27ceac8`, 브랜치 `claude/k92-b1-20261016`, K8 `b9734abe`, status 0줄. `KB/a33decl`·`KB/k92_vb2`·`OK2/vb2`·`TK/vb2_e27ceac8` 없음. python·VISSIM 0. C: 40 GB, D: 384 GB.
- 할 일: AD33 = `KB/a33decl`(새 훅·합성 확인 도구·확인 출력·차이 파일·기대 고정 목록), KV2 = `KB/k92_vb2`(새 구동기·재계산기·자기 시험; 옛 `KV/vb_chain.py`·`vb_recalc.py`는 보관, 바꾸지 않음) → 합성 확인만(자식은 합성 프로그램뿐; 결정 재생·어댑터·VISSIM 0) → STOP 판 r1 보관 사본 둘 → 스냅숏 하나 → 보충 33 글.

## 2026-10-22 14:32 +0900 — Declare A33: 도구 sha (합성 확인 실행 전)

- 새 훅 `AD33/vbhook/sitecustomize.py` `691fe8100e38d3222f3508f3f682b84b225535d1d3f7cca57f08a671708e365c`(옛 `4d7e0375…` 대비 이름·배타 생성만 바뀜, 차이 `AD33/diff/hook.diff`).
- 새 구동기 `KV2/vb_chain.py` `57e7749f0eb376303ac873c7467b910d311fb67f60b3fda9c6d715a0c3fc4ae4`, 새 재계산기 `KV2/vb_recalc.py` `6531a5e8eab37201781d4f81c80c7090b1546c2511c128c5db58026f28625d8b`(옛 `KV` 판 4dc9297d·cab7939d의 사본에 자리·고정·보관 점검만 고침).
- 합성 확인 도구 `AD33/dry_a33.py` `d1992a8c244c654b5663f8b14fe8875f9682549a5f7f0b888972b41ed9b027ab`, 우선순위 도우미 `AD33/run_bn.py` `c635e1513d71ad071a788d740d7ae637c22f8c73b12cea132cdfca4e6ff153ee`.
- 다음: `run_bn.py`로 구동기 자기 시험·재계산기 자기 시험(합성, 자식 0) → `dry_a33.py all`(합성 자식만, BelowNormal).

## 2026-10-22 14:37 +0900 — Declare A33: 구동기 한 번 고침(실행 전 sha)

- 첫 합성 확인(14:32–14:34, 구동기 `57e7749f…`·재계산기 `6531a5e8…`·dry `d1992a8c…`, 모두 참) 뒤 구동기의 STOP 규칙 이름만 고침: 보관 자리 점검(V0 C13, V10 보관 목록·바이트)이 거짓일 때 STOP 파일의 규칙 이름을 S-K53 대신 새 S-K57로 적음(cmd_chain V0 멈춤 한 줄, v10 멈춤 한 줄). 판정 조건·나머지 바이트 그대로. 새 구동기 `KV2/vb_chain.py` `87b89ce48b6552b4967cc5416d2e56d5f9f6d20d887d9997385df4f1be521322`. 구동기 자기 시험과 `dry_a33.py all`을 다시 돌려 그 출력이 고정 대상(첫 판 출력은 덮어씀; 기대 고정 목록은 다시 만듦). 재계산기·훅·dry 도구 바이트 그대로.

## 2026-10-22 14:49 +0900 — Declare A33 끝: 보충 33 Declare 판 (새 V-B 데이터 0)

- 이 항목 덧붙임 전 LOG sha256 `a2001c7cc9697a1bfa042cd33dead1762c745ae01e699f4fc11e1042034754e5`, 268382 B.
- 보충 33 Declare 판 `SP/K8_PREDECLARATION_AMENDMENT_33.md` sha256 `b0db6bf5d49e5b989dd09b629bba016b52e45647a24104cfc4a0a5487dd0bdc9`(1,158줄, 109,408 B, LF, CR 0), 같은 값 `.sha256` [실행 `sha256sum -c` OK]. 고정점 `KB/AMENDMENT33_FIXED.md`는 반박 검토가 씀.
- 둘째 확인 판 [실행]: 구동기 자기 시험 `KV2/selftest/vb_selftest.json` `a649aaa5094bf0b94aebe5c4eed9418193cfa032b6ec20c97145744ddd6f8922`(t1–t7 참), 재계산기 자기 시험 `KV2/selftest/vb_recalc_selftest.json` `9e7d864a7eff440c0ad62cecca01d299a0f7ef4135eca647919d14d8d52c6379`(26 참), `dry_a33.py all` 요약 `AD33/dry/decl/dry_a33_summary.json` `de72ea283b2529ac5d3eac868ab70fc33a056725e7bd15e48cb0e4343a98af3b`(static·hook·pidreuse P1–P8·paths·mutants M1–M4 모두 참; P1 = 옛 훅이 같은 PID에서 겹침을 재현, P2–P7 = 새 훅 겹침 0, P5 = 토큰 전체 강제 겹침은 배타 생성이 거절하고 첫 프로세스 파일 그대로).
- 기대 고정 목록 `AD33/a33_pins.expected.sha256` `a1b02027c3238dcb3cb55bae42e163d4d1ce60b0f7c688e44517efcfe9e7ac74`(63줄, `sha256sum -c` 63/63 OK; 만드는 도구 `AD33/make_pins33.sh` `fa59909897ef1759fdbe3e7cf92da1c088a50e9e8b77a7790b2b9af367e83bd9`). 새 훅 `691fe8100e38d3222f3508f3f682b84b225535d1d3f7cca57f08a671708e365c`, 구동기 `87b89ce48b6552b4967cc5416d2e56d5f9f6d20d887d9997385df4f1be521322`, 재계산기 `6531a5e8eab37201781d4f81c80c7090b1546c2511c128c5db58026f28625d8b`.
- STOP 판 r1 보관 사본(메인 세션 처리): `KV/K92_VB_REPORT_stop_r1.md`·`KB/VB_REPORT_stop_r1.md` = `d7bf44f3…`(`cp -p`, `cmp` 같음).
- 스냅숏 `KI/launch.ps1 -Tag a33decl_snap`(14:34:12 PID 27544, 52.7 s) → `OK2/snap/s42_a33decl.json` `4e55240d36e460f33f9c13c5cf5164e2a03ed2653ae65675afcac9d6b6410302`, s02 대비 SAME.
- 끝 상태 [실행]: GWT8 head `e27ceac8`·K8 `b9734abe`·status 0줄, python·VISSIM 0, C: 40 GB·D: 384 GB. VISSIM·COM·러너·동결·결정 재생·어댑터 0, 커밋·푸시 0, 금지 시험 0, 봉인 뿌리·봉인 시드·v3c3-s47 0. 끈 프로세스 0.
- 다음: 반박 검토(ReviewDeclare A33) → 고정점 33 → V-B 단계(보충 33 §6.1: `KB/a33_pins.sha256` 복사·LOG 항목·`KI/launch.ps1 -Tag vb2_chain -Script ..\k92_vb2\vb_chain.py -ArgLine chain`).

## 2026-10-22 14:51 +0900 — ReviewDeclare A33 (보충 33 반박 검토) 시작

- 이 항목 덧붙임 전 LOG sha256 `9a52b396efabcfa4601fbb46f415524c0e93d34e9559d72264dffe62893efb4e`, 270869 B.
- 확인 [실행]: 보충 33 Declare 판 `b0db6bf5d49e5b989dd09b629bba016b52e45647a24104cfc4a0a5487dd0bdc9` = `.sha256`; 결정 기록 `187242343570f1fe4e22d644509139e87ff59f76c70458b58160c1cde5387109`; 보충 32 고정판 `7f25c21e…` = `.sha256`. `OK2/vb2`·`TK/vb2_e27ceac8` 없음, python·VISSIM 0. C: 40 GB, D: 384 GB.
- 할 일: 훅 차이·이름 유일성(PID 재사용·동시 작업자·다시 시도)·고르기·보관·고정·STOP 규칙 반박 검토. 합성 확인만(검토 폴더 `KB/a33review`), 결정 재생·어댑터·VISSIM 0.

## 2026-10-22 15:01 +0900 — ReviewDeclare A33: 검토 합성 시험 도구 sha (실행 전)

- `KB/a33review/rev_a33.py` sha256 `da72c75054234f22f5cca61f7fd332aeba68b6892e35cb855d312a47d462001d` — 합성 입력만(자기 폴더 `KB/a33review/syn`): R1 실제 운영 체제 PID로 작업자 역 120개 차례 실행(새 훅)·R1o 같은 꼴 옛 훅(대조)·R2 같은 PID+같은 time_ns 12개 동시 실행(스레드 4)·R3 한 프로세스 안 훅 두 번 실행(importlib.reload; 새·옛 훅, 작업자·어댑터 역)·R4 토큰 전체 겹침 둘 + 다른 하나. 고르기(AD32 `vb_select.py` 자식)·구동기 `vbi7`·재계산기 `reselect`/`i7_of`를 합성 폴더에 부름. AD33·AD32·KV2는 읽기만(가져오기만), 결정 재생·어댑터·VISSIM 0. BelowNormal, `python -B`, PYTHONHASHSEED=0.
- [2026-10-22 15:03 +0900] 검토 합성 시험 첫 실행 [실행]: R1·R1o·R2·R3 참, R4 거짓 — 원인은 검토 도구 결함(R4의 "첫 프로세스 파일 그대로" 비교를 파일 이름만으로 열쇠 삼아 후보 폴더마다 같은 이름 `cand.json` 등이 겹침), 훅 결함 아님. 첫 출력은 `KB/a33review/out/rev_a33_run1.json` `2ebe01d0fd4da3938e839c5c4dcc47b3943a344b1b9ee37d3e7b80544724a515`로 남김. 고친 도구(열쇠 = 훅 폴더 안 상대 경로) sha256 `10119951615cfa5b07c44fd8bd75946ec69a428eab71f469e55d14de2adb9bc7`, 다시 돌림.
- [2026-10-22 15:07 +0900] 검토 합성 시험 둘째 실행 [실행]: R1–R4 모두 참, 그러나 `below_normal` 거짓 — 검토 도구의 우선순위 함수가 ctypes 기본 int 반환형으로 `GetCurrentProcess()` 가짜 핸들을 32비트로 잘라 `SetPriorityClass`가 ERROR_INVALID_HANDLE(6)로 실패(첫·둘째 실행은 보통 우선순위; 가벼운 합성 자식뿐). **같은 꼴이 `AD33/run_bn.py`에 있음**(검토 발견, 보충 33 공개로 옮김). 둘째 출력 `KB/a33review/out/rev_a33_run2.json` `c1796ee1215a5377e82def50152e4f66204fa66a805737051ae6efe83fe67e09`. 우선순위 함수만 고친 도구 sha256 `a35a286f82560617e692f4b15f307ede4be95eec73faf82817cd41b27a847487`, 셋째 실행.
- [2026-10-22 15:13 +0900] 검토 셋째 실행 끝 [실행]: `KB/a33review/out/rev_a33.json` `9b8694dca6fe08349e91857c0ff56c496a0fae3493b48012a7cecf7560e68f14`, R1–R4 모두 참, BelowNormal 참(15:07:15–15:10:03). R1 실제 PID 재사용 3번(121 프로세스) — 새 훅 겹침 0·오류 0·`selected`; R1o 옛 훅 대조는 재사용 8번에서 `hook_error` 8개(멈춘 실행의 겹침을 실제 운영 체제에서 다시 냄). 끝에 python 0.
- [2026-10-22 15:13 +0900] 검토 보관 목록 도구 sha256 `7b1315f7ec24c3ac81a2080104702d413d30667d1c52ead8443bd35e664cf326` (실행 전): `KB/a33review/rev_a33_archive.py` — 고정된 새 구동기(`87b89ce4…`)를 가져와 `archive_listing()`(TK/vb_e27ceac8 + 빌드 기록)·`archive_bytes()`와 같은 꼴의 `OK2/vb` 목록(이름·크기·수정 시각만, 내용 열람 0)을 냄. 봉인 뿌리 안 들어감.
- [2026-10-22 15:14 +0900] 바로 위 도구는 문법 오류(셸 heredoc이 역슬래시 글자 하나를 먹음)로 시작 전에 멈춤(읽기·출력 0). 그 줄만 `chr(92)`로 고친 도구 sha256 `325871a7e2e72846d2bca48a9bf93a26a94fe5bf8e00a470ec116711707a6a0a`, 실행.

## 2026-10-22 15:24 +0900 — ReviewDeclare A33 끝: 보충 33 고정 (새 V-B 데이터 0)

- 이 항목 덧붙임 전 LOG sha256 `32c610b0b5b6825291feb343985dbba4fa319ec2c1e1c2b99e160ca8fdc47f1a`, 274897 B.
- 보충 33 고정판 `SP/K8_PREDECLARATION_AMENDMENT_33.md` sha256 `76ae084b2b12eb820238a8c2b980c6554c2a988ebeebca877d51fb9714f733ea`(135,275 B, 1,236줄, LF, CR 0) = `.sha256`. Declare 판은 `SP/K8_PREDECLARATION_AMENDMENT_33_r1.md`(+ `.sha256`)와 `KB/a33review/r1/K8_PREDECLARATION_AMENDMENT_33_declare.md`로 남김(같은 바이트).
- **고정점 `KB/AMENDMENT33_FIXED.md` sha256 `9254e2792bad367586c99c05925e649414c01601ea2e8642bcf575ed17f60908`** (15:23). 기대 고정 목록 `AD33/a33_pins.expected.sha256` `a1b02027c3238dcb3cb55bae42e163d4d1ce60b0f7c688e44517efcfe9e7ac74`(63줄, 검토가 바꾸지 않음, 63/63 OK). V0 C2 꼴 대조 [실행]: 고정판 sha가 고정점에 64자로 있음·`.sha256` 같음·Declare 판 64자는 고정점에 없음·기대 목록 sha 있음 — 모두 참.
- 검토가 고친 곳(모두 글; 도구·확인 출력·기대 목록 바이트 그대로) R1–R7: (R1) `AD33/run_bn.py` BelowNormal 설정 조용히 실패 → Declare 자기 시험 둘은 보통 우선순위였음, 공개 P14, V-B에서 안 씀; (R2) 보관 틈(멈춘 실행 → V0) → 검토 때 목록 값 옛 VBT+빌드 `d51f4deefc53b69cdadd9472a6ea2ca9197f694760f26c2380e1a101a1089680`(10,660행)·`OK2/vb` `392d10278514a2206fe9a6b5d22190708931ffabdecaf911037668f5f4ecd583`(1,129파일), VerifyVB 대조·S-K57; (R3) VerifyVB 토큰 짝 점검 넷; (R4) 가정 없는 겹침 상한과 검토 시험 R1–R4; (R5) ZI `hook_on` 인용 바로잡음; (R6) 경로 길이 234/260·약 145/260; (R7) 고르기 자식 작업 폴더 `KV` 공개 P16.
- 검토 시험 결과 [실행 `KB/a33review/out/rev_a33.json` `9b8694dca6fe08349e91857c0ff56c496a0fae3493b48012a7cecf7560e68f14`]: R1 실제 PID 재사용 3번(121 프로세스) 새 훅 겹침 0·오류 0·`selected`; R1o 옛 훅 재사용 8번 → `hook_error` 8; R2 같은 PID·시각 동시 12 겹침 0; R3 한 프로세스 두 번 실림 → 작업자 같은 기록 둘(STOP 아님)·어댑터 VB-I7 거짓(STOP 쪽), 옛 훅은 둘 다 `hook_error`; R4 셋 중 둘 토큰 전체 겹침 → 거절·첫 파일 11개 그대로·STOP 쪽.
- 끝 상태 [실행 15:22]: GWT8 head `e27ceac8`·K8 `b9734abe`·status 0줄·푸시 0, `OK2/vb2`·`TK/vb2_e27ceac8`·`KB/a33_pins.sha256` 없음, 옛 VBR·옛 VBT 안 늦은 파일 0, python·VISSIM 0, C: 40 GB·D: 384 GB. VISSIM·COM·러너·동결·결정 재생·어댑터 0, 커밋·푸시 0, 금지 시험 0, 봉인 뿌리·봉인 시드·v3c3-s47·codex 64cf 0, 끈 프로세스 0.
- 다음: V-B 단계(보충 33 §6.1: 이 고정점 sha를 LOG에서 봄 → `cp AD33/a33_pins.expected.sha256 KB/a33_pins.sha256`·cmp·63/63 → LOG 항목 → `KI/launch.ps1 -Tag vb2_chain -Script ..\k92_vb2\vb_chain.py -ArgLine chain`). 남은 미해결 없음.

## 2026-10-22 15:27 +0900 — V-B 재실행 (보충 33): 시작

- 이 항목 덧붙임 전 LOG sha256 `73156e81341d06c2dc0074bb1a336c31fb5b93eea7c9b5138f84ee1ffa5abf6e`, 277865 B.
- 고정점 확인 [실행 sha256]: 보충 33 고정판 `SP/K8_PREDECLARATION_AMENDMENT_33.md` `76ae084b2b12eb820238a8c2b980c6554c2a988ebeebca877d51fb9714f733ea` = `.sha256` 앞 64자 = 고정점 `KB/AMENDMENT33_FIXED.md` 안 64자. 고정점 33 파일 sha256 `9254e2792bad367586c99c05925e649414c01601ea2e8642bcf575ed17f60908`. 결정 기록 `187242343570f1fe4e22d644509139e87ff59f76c70458b58160c1cde5387109` = 작업 지시 값(D-K9-65·66).
- 상태 [실행]: GWT8 head `e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d`(브랜치 `claude/k92-b1-20261016`), K8 `b9734abe1c83f95c9cec5fca5e42b7b18cd45991`, status 0줄, `b9734abe..HEAD` 6, 원격 k92 0, 이름에 vb 든 worktree 0. `OK2/vb2`·`TK/vb2_e27ceac8`·`KB/a33_pins.sha256` 없음(V-B 데이터 0). python 0·VISSIM 0. C: 40 GB, D: 384 GB.
- 자기 시험(합성, PID 재사용 강제 포함)은 보충 33 §6.1-4대로 **다시 돌리지 않음**: `AD33/dry_a33.py`는 출력 자리를 `AD33/dry/decl`(고정 목록 11–16줄)로 박아 두어 다시 돌리면 고정 파일을 덮어씀(S-K53). 대신 고정 출력을 읽어 확인 [실행]: `dry_a33_summary.json` all_ok 참(static·hook·pidreuse·paths·mutants), `dry_a33_pidreuse.json` P1–P8 참(P1 옛 훅 같은 PID → `hook_error`, P2–P4·P6 새 훅 `selected`, P5 토큰 전체 강제 겹침 → 거절·`hook_error`, P7 결정끼리 독립, P8 강제 방법 통제), 구동기 자기 시험 ok 참, 재계산기 자기 시험 ok 참. 바이트는 아래 고정 63/63에서 봄.
- 할 일(보충 33 §6.1–§6.2): `KB/a33_pins.sha256` 복사·cmp·63/63 → LOG 고정 항목 → `KI/launch.ps1 -Tag vb2_chain -Script ..\k92_vb2\vb_chain.py -ArgLine chain`(WMI 분리, BelowNormal, PYTHONHASHSEED=0, python -B) → V0–V10 → 보고서 r2. VISSIM·COM·러너·동결·커밋·푸시 0.

## 2026-10-22 15:27 +0900 — V-B 재실행 (보충 33 §6.1): 고정 (ZI·사슬 계산 전, V-B 데이터 0)

- 이 항목 덧붙임 전 LOG sha256 `01bf964d7e3c864b8c387cc2f63ef73b52c060d563f9d699f82ea53688d81818`, 279857 B.
- (1) 고정점 33 파일 `KB/AMENDMENT33_FIXED.md` sha256 `9254e2792bad367586c99c05925e649414c01601ea2e8642bcf575ed17f60908`.
- (2) `KB/a33_pins.sha256` = 기대 파일 `AD33/a33_pins.expected.sha256` 바이트 복사(`cmp` 같음), sha256 `a1b02027c3238dcb3cb55bae42e163d4d1ce60b0f7c688e44517efcfe9e7ac74`, 63줄, `sha256sum -c` 63/63 OK [실행].
- (3) 구동기 `KV2/vb_chain.py` sha256 `87b89ce48b6552b4967cc5416d2e56d5f9f6d20d887d9997385df4f1be521322`, 재계산기 `KV2/vb_recalc.py` sha256 `6531a5e8eab37201781d4f81c80c7090b1546c2511c128c5db58026f28625d8b`, 새 훅 `AD33/vbhook/sitecustomize.py` sha256 `691fe8100e38d3222f3508f3f682b84b225535d1d3f7cca57f08a671708e365c`(HOOKDIR 파일 하나), 고르기 `AD32/vb_select.py` `33adfd5033c277a3ad640f745a69efb2a929b27c1ff2a88d794dfa69b489e9cc`, 도움 함수 `AD32/vb_lib32.py` `504999a196a9e08582f303d4ad38d4cc661fcfc765df62d11bc4cc7c05ddc75f`, 닫힌 잎 목록 `AD32/vb_closed_leaves.json` `b800be45ae3e4e5030ed31ecd221e6288d52c2a287bdeaa5efee243e3cc2f426`(모두 고정 목록 1–6줄과 같음). 바뀐 도구는 Declare A33이 만든 것뿐이고 이 단계는 도구를 고치지 않음.
- 다음: WMI 분리 `KI/launch.ps1 -Tag vb2_chain -Script ..\k92_vb2\vb_chain.py -ArgLine chain` → V0–V10.
- [2026-10-22 15:28 +0900] V-B driver: V0 사전 점검 first 참(C1–C13), `check_v0.json` sha256 `d8bc2130d8ebb4fdd7b3e33cf35545b99a95c1025ce46fcde496fe146c1dbad6`, 구동기 `87b89ce48b6552b4967cc5416d2e56d5f9f6d20d887d9997385df4f1be521322`, 재계산기 `6531a5e8eab37201781d4f81c80c7090b1546c2511c128c5db58026f28625d8b`
- [2026-10-22 15:29 +0900] V-B driver: 스냅숏 s43_vb2_v0.json SAME (s02 대비), sha256 `8cc4da7261ad968e3c074d4f475f6cb9cbd5f1b34b2e890ed691d0ab3eaf5752`
- [2026-10-22 15:31 +0900] V-B driver: V1 트리 `TK/vb2_e27ceac8` (git archive e27ceac8 + CR 고침, 형태 CCCCCCCCCC, cr_pair 둘 참, RS·SHO·튜닝·REC·KC·k92_replay sha 기대값), 빌드 기록 sha256 `e2c4ee176a249cbd53e993ec0d680962a75dbb4dd4d75dca00e8ee1fad10fb00`; GWT8 작업 트리 대비 바이트 다름 0·VBT만 0·GWT8만 1(보고만)
- [2026-10-22 15:31 +0900] V-B driver: V2 팔: SAF-B1 `65cac7ea0b33d8f0b5c8efc458307578bcae7a2e34d1d097ce448a18a65ada28` = 기대값, VB-I3 두 팔 참(차이 두 경로, 증거 sha = VBT 커밋 증거, 파일 sha), C12 참

## 2026-10-22 15:35 +0900 — V-B 재실행: 세션 도우미 고정 (판정 도구 아님, V-B 판정 파일 첫 읽기 전)

- 이 항목 덧붙임 전 LOG sha256 `34109301bdc91bf624eea38f2d5f0877a28609daa29a20df0dbdb266adc4a41a`, 282419 B.
- 발사 [실행]: `KI/launch.ps1 -Tag vb2_chain` 15:28:04, ReturnValue 0, PID 6736(cmd.exe), BelowNormal(16384), 발사 때 python 0·VISSIM 0. 진행: 15:28:18 V0 PASS, 15:29:17 s43 스냅숏 PASS, 15:31:57 V1 PASS, 15:31:59 V2 PASS(이름·초만 봄).
- 진행 확인 도우미 `KV2/poll_vb2.sh` sha256 `81b4348b01f6502a11bd011beda41682f2f465b5b134a26c9ac4bb3ff4ef1397`(읽기만: `steps.jsonl` 줄 수, `stages/`·`STOP_vb_*` 이름, `driver_log.txt` 끝 3줄, 발사 로그 끝 2줄, python·VISSIM 개수, 디스크; 한 번에 510 s 이하).
- 보고서 표 도구 `KV2/mk_vb2_tables.py` sha256 `c59cef11b9273191a5c60fbad85b7fb69f7685440e2ab14667bfc3a4c41f0e70`: 구동기가 쓴 단계·ZI·판정·재계산·`done` 파일과 58개 훅 폴더 이름(+ `loaded`의 `pid`·`argv0`, `cand.json`의 `pid`·`seq`·`time_ns`)을 읽어 표만 만듦. 판정 0(PASS·참/거짓은 구동기 파일 그대로 옮김). 스스로 세는 것은 보고만 항목 둘뿐: 보충 33 §8-5·§6.5의 훅 폴더 이름 요약(토큰 수·같은 PID 묶음·time_ns 겹침)과 §9의 r1 11경로 대조(같음·새로 보임·안 보임). 합성 폴더로 한 번 시험(합성 폴더는 지움), 그 뒤 출력 꼴(하한 소수 4자리) 한 곳만 고쳐 이 sha. 실제 V-B 출력에는 V10 뒤 한 번 돌림.
- [2026-10-22 16:20 +0900] V-B driver: V3 ZI 세 칸 PASS, `VBR/zi/zi.json` sha256 `8d1ae5a157e8a708f1195c4e4d2a8a278f3ea962eafab66787b3a85f805112b5`
- [2026-10-22 16:21 +0900] V-B driver: 스냅숏 s44_vb2_zi.json SAME (s02 대비), sha256 `24d977a5cff1866cd3f9c1baed7d526eb9f82fa3056fb72bf4dce13e0a9383d1`
- [2026-10-22 18:02 +0900] V-B driver: V4 OFF 사슬 14결정 끝(종료 0)
- [2026-10-22 18:04 +0900] V-B driver: V5 OFF 관문: VB-I1 판정 4결정 결과 넷 ['PASS', 'PASS', 'PASS', 'PASS'], OFF 14결정 VB-I2·VB-I7 참; 보고 전용 10결정 닫힌 목록 밖 차이 결정 5개에서 모두 55개(판정 아님); `judge/vb_i1.json` `47de078e9c1a6333ca8aa1828b8706dbb2fb33305303a318c1944954fc031815`, `judge/vb_reportonly.json` `9ab57fcfcf0611c815b28e3aa7ae83e467508d979291b2f7578c402b86487bcf`
- [2026-10-22 18:05 +0900] V-B driver: 스냅숏 s45_vb2_off.json SAME (s02 대비), sha256 `59a2c2f23fd611e1b5216d06da11ca3d47cc7854ec533d2ec2358dd9c89695aa`
- [2026-10-23 00:41 +0900] V-B driver: V6 B1 사슬 41결정 끝(종료 0)
- [2026-10-23 00:43 +0900] V-B driver: V7 무결성 55결정: VB-I2·VB-I3·VB-I4·VB-I6·VB-I7 참; SDMPC 결정 고르기 상태 {'selected': 41, 'no_match': 2}; `judge/vb_i.json` `18eb483b006e62aa7becc20d3d402e6bf6a5cd09c0674605dfccce0694093b96`
- [2026-10-23 00:44 +0900] V-B driver: V8 지표 표 `judge/vb_m.json` sha256 `459369834f7c9df5ffb18812494664e5896341596d14315faf13ba39d355dcf4` (결정 줄 96, 사슬 줄 12)
- [2026-10-23 00:48 +0900] V-B driver: V9 재계산 VB-I5 같음(비교 4204칸), `recalc/recalc.json` sha256 `bee4d4622b79bc824425fb7566fb258d156cf890a98e76ef31c2348154866d77`
- [2026-10-23 00:49 +0900] V-B driver: 스냅숏 s46_vb2_end.json SAME (s02 대비), sha256 `583592df84638b5bb31127c6244e67c4523b486ea86e7e55330fd0340b72bef3`
- [2026-10-23 00:49 +0900] V-B driver: V10 끝 대조 OK: a33 고정 63/63, GWT8 head `e27ceac8`·status 0·K8 `b9734abe`·원격 k92 0, RR 목록 sha = V0, OK2 의 vb2 밖(보관 OK2/vb 포함) = V0, 보관 TK/vb_e27ceac8 목록 = V0, 보관 바이트 참

## 2026-10-23 00:56 +0900 — V-B 재실행 (보충 33): 끝 — V0–V10 모두 PASS, 보고서 r2

- 이 항목 덧붙임 전 LOG sha256 `d596bfb73d802fcbe5f6484a42a6965c6327d66dcc561002d803af346ac0884f`, 286044 B.
- 실행 [실행]: `vb_chain.py chain` WMI 2026-10-22 15:28:04 (cmd.exe PID 6736) → 10-23 00:49:14 `VB_CHAIN_DONE`, STOP 파일 0. V0 C1–C13 참(보관 `archive_tree` 10,660행 `d51f4deefc53b69cdadd9472a6ea2ca9197f694760f26c2380e1a101a1089680` = 고정점 33 검토 값) → s43 SAME → V1(VBT `TK/vb2_e27ceac8`, 빌드 기록 `e2c4ee176a249cbd53e993ec0d680962a75dbb4dd4d75dca00e8ee1fad10fb00`) → V2(SAF-B1 `65cac7ea…`, VB-I3 참) → V3 ZI 세 칸 PASS(켬/끔 벽시계 비 1.007·1.011·0.980) → s44 SAME → V4 OFF 14결정 종료 0 → V5 PASS(VB-I1 4/4 PASS, VB-I2·VB-I7 14/14) → s45 SAME → V6 B1 41결정 종료 0 → V7 VB-I2·I3·I4·I6·I7 55결정 참 → V8 `judge/vb_m.json` 96·12줄 → V9 VB-I5 같음(4,204칸, 다름 0) → s46 SAME → V10 끝 대조 참(a33 63/63, GWT8·RR·OK2(옛 VBR 포함)·옛 VBT 목록 = V0, 보관 바이트 참). 이후 python 0·VISSIM 0.
- 고르기 상태(SDMPC 43): `selected` 41, **`no_match` 2(VB-41 B1 T=3,300·4,500; STOP 아님, 그 두 결정 VB-M5·M6·M8 없음)**. 훅 폴더 58개 이름 모두 새 꼴·오류 0; 한 폴더 안 PID 재사용 1번(VB-41 B1 T=4,200, PID 3024 토큰 둘, 겹침 0, time_ns 구간 겹침 0).
- 보고 전용 OFF 10결정: CSV 10/10 기록과 같음, 닫힌 목록 밖 = 결정 5개(VB-41w T=900·1,050, VB-31·43·41 T=3,150)에서 모두 55개(경로; 잎 147), 전부 `action_token` 11경로 = r1과 같은 11경로(새로 보임 0·안 보임 0), 그 밖 0.
- 세션 표 도구 `KV2/mk_vb2_tables.py`(`c59cef11…`, 고정 그대로) 한 번 → `KV2/report/tables.md` `f68e92850f3182591fd82ec6aca0bb37c0be1362d53ffa7d10a012f2f2ab3788`, `tables_summary.json` `c8b7c83651968983f28720ae37f297ca4aae8cd049162c668b329ab5feb83bda`. 조립 도우미 `KV2/report/assemble.py` sha256 `f1ddfd3fbecaaf4323c975aee6210fa1523c15596a94a766414f4c8682fa8260`(서식만, §9 sha는 파일에서 다시 계산).
- **보고서 r2(완료 판)**: STOP 판 r1 보관 사본 셋 `d7bf44f3…` 확인 뒤 정본 `KV/K92_VB_REPORT.md` = `KB/VB_REPORT.md` = `OK2/vb2/K92_VB_REPORT.md` sha256 `79e7cb03c65151fb240d33af3a362cda5b985bd4fac6bc832fc0999983e424a0`(631줄, 85,865 B, LF, `cmp` 같음).
- 공개(보고서 §8): E1 자기 시험은 보충 33 §6.1-4대로 다시 돌리지 않고 고정 출력(63/63, P1–P8 참)을 확인; E3 고정 목록 복사 줄에 잘못 섞인 `cp AD33=1 2>/dev/null`(오류로 끝, 파일 생김 0).
- 끝 상태 [실행]: GWT8 head `e27ceac8`·브랜치 `claude/k92-b1-20261016`·K8 `b9734abe`·status 0줄·`b9734abe..HEAD` 6·원격 k92 0, `KB/a33_pins.sha256` 63/63·바이트 = 기대, 옛 VBR(14:07:20 뒤)·옛 VBT(11:28:38 뒤) 새 파일 0, python 0·VISSIM 0, C: 40 GB·D: 372 GB. VISSIM·COM·러너·동결·커밋·푸시·금지 시험 0, 봉인 시드·봉인 뿌리·v3c3-s47·codex 64cf 0, 끈 프로세스 0.
- 다음: VerifyVB(보충 33 §6.5: 훅 이름 넷·보관 대조 + 보충 32 §4.8). V-A·푸시는 그 뒤 사용자 결정.

## 2026-10-23 01:01 +0900 — VerifyVB 3 (보충 33 V-B 재실행 독립 검증): 시작

- 이 항목 덧붙임 전 LOG sha256 `a17bf33ef1ba2000ca3f8dcf903e6bd1717889fafd18795d68c4eb0033fee6bd`, 289,237 B.
- 확인 [실행 sha256]: 보충 33 고정판 `76ae084b2b12eb820238a8c2b980c6554c2a988ebeebca877d51fb9714f733ea`, 고정점 33 `9254e2792bad367586c99c05925e649414c01601ea2e8642bcf575ed17f60908`, 결정 기록 `187242343570f1fe4e22d644509139e87ff59f76c70458b58160c1cde5387109` — 작업 지시 값과 같음. GWT8 head `e27ceac8`, 브랜치 `claude/k92-b1-20261016`, status 0줄. python 0·VISSIM 0. C: 40 GB, D: 372 GB.
- 공개(도구 고정 전 노출): 작업 지시 글에 V-B 보고 요약 숫자(PASS 수, Ω·OUTW·FEED-4 범위, no_match 2결정, PID 재사용 1번 등)가 들어 있었고, LOG 1106–1143줄(V-B 재실행 고정·구동기 자동 줄: 판정 파일 sha, 고르기 상태 개수, 목록 밖 55개, 재계산 4,204칸)을 읽었습니다. V-B 출력 파일·보고서 r2 본문은 아직 열지 않았습니다.
- 할 일: 보충 24/27/29/31/32/33 글과 코드(구동기·재계산기·고르기·도움 함수·KC·기록기)를 읽어 출력 꼴을 안 뒤, 새 도구를 쓰고 sha를 LOG에 고정 → 그 뒤에만 VBR 출력·보고서 r2를 읽음. 사슬 두 결정 재실행은 따로 자리(WMI 분리, BelowNormal).

## 2026-10-23 01:58 +0900 — VerifyVB 3: 도구 고정 (V-B 출력·보고서 r2 첫 읽기 전)

- 이 항목 덧붙임 전 LOG sha256 `cda66eb1a17fb1705ede3da6869c789182b945effa9a9b8b404995200ec08056`, 290,600 B.
- 고정 목록 `KB/vvb3/vvb3_pins.sha256` sha256 `bbb44a566428634af925d181000452c9aabdb7b7a3010946cd1e7a32be5dc511` (4줄, `sha256sum -c` 4/4 OK):
  - `vvb3_recalc.py` `52d44f5e322a29c90c58c3d293cf340ef32e47aa4968544b62c9a7d5f27b60d8` — 독립 재계산(표준 라이브러리 + numpy만; 구동기·재계산기·훅·AD32 도구·KI·하네스·VBT/GWT8 모듈 import 0). 보충 21 §6·24 §4.2·27 §2.1·29 글로 다시 짠 비교기(N, HARD H1–H5, F1–F3, D1–D5, V, R3, A_K92)로 VB-I1 4결정과 보고 전용 10결정의 목록 밖 집합, VB-I2·I3·I4·I6·I7, 보충 33 §6.5 훅 이름 넷(이름·오류 0·짝·순번)과 보고 항목(같은 PID 묶음·time_ns 겹침), 고르기(§3.4) 다시 하기, ZI (z2)–(z6), VB-M1–M9 표, B1−OFF 같은 상태 차, no_match 결정 사실, 보관 목록 둘(§5 (라) 꼴)·V0 `archive_tree`·STOP r1 사본 셋. 다 낸 뒤에만 구동기 판정 파일을 읽어 견줌(숫자 상대 1e-12, 그 밖 정확히).
  - `vvb3_rerun.py` `c73c246c10b3953702f34e564206218e7e73ef1c22dfc36e9b48ce817951f8bb` — 사슬 두 결정 재실행. **선언(데이터 전)**: VB-41 B1, T1 = 3,300(직전 = V-B 출력 `VBR/chain/vb41_b1/dec/action_003150.json`, 읽기만) → T2 = 3,450(직전 = 재실행 T1 출력 + 보충 32 규칙 영수증). 훅 켬(AD33 훅 읽기만). 트리 `TK/vvb3_e27ceac8` = `git archive e27ceac8` + CR 고침(`TK/cr_only_files.json`), VBT와 캐시 폴더 밖 파일마다 같아야 함. 출력 `OK2/vvb3/chain/vb41_b1/…`. 발사 인자 = V-B 실행 기록 인자(자리 두 개 바꿈 뒤) 같아야 함. **같음 규칙 R-ID**: T1 = CSV 바이트 같음 + 비교기 결과 넷 PASS(VB-I1과 같은 규칙); T2 = CSV 바이트 같음 + 재실행 쪽 `k92_b1/vvb3/`를 `k92_b1/vb2/`로 읽은 뒤 HARD 같음·미분류 0, 이때 더 다를 수 있는 잎은 (a) 영수증 sha 두 잎(옛 값 = V-B T1 영수증 sha, 새 값 = 재실행 T1 영수증 sha), (b) `vsl_cohort_initialization/sha256`(옛 = V-B T1 JSON sha, 새 = 재실행 T1 JSON sha), (c) 이름이 `action_token`으로 끝나는 잎뿐. 그 밖은 "같지 않음" → 보고·STOP(사용자). 보고만: 고르기 상태·후보 수 대조. 지킴: C:·D: 8 GB, VISSIM 0, 읽은 V-B 파일·RR s41 목록 끝에 그대로.
  - `vvb3_launch.ps1` `5992cb26d391ca981aa9f0719cfb45d779495214fa37c94cbac6bde3f7294e00` — WMI 분리, BelowNormal 16384, PYTHONHASHSEED=0, python -B.
  - `out/vvb3_selftest.json` `27ce9efc4c2aa5f8a9427af167818693913a3147cc39fc19599260997395dd48` — 합성 자기 시험 18사례 모두 참(V-B 파일 읽기 0).
- 고정 전에 읽은 것: 보충 21 §6·24 §14.1·27 §2.1·32 §2–§5·33 전문, 고정점 33, 구동기·재계산기 구조·`vb_select.py`·`vb_lib32.py`·닫힌 잎 목록·KC·기록기·훅·`mk_vb2_tables.py`·`gprep.py`·KI `k92lib`/`cglib`/`launch.ps1` 코드, RR 파일 이름, OK2·TK 폴더 이름. V-B 출력 파일 내용·보고서 r2 본문 0.
- 순서: 재계산(WMI 분리) → 끝나면 재실행(WMI 분리) → 보고서 r2 읽기·대조 → 고침(있으면 `_r1` 보관) → `KV/VERIFY_VB.md`.

## 2026-10-23 01:27 +0900 — VerifyVB 3: 재계산 끝, 보충 도구 고정

- 이 항목 덧붙임 전 LOG sha256 `90e60796eb06762e32f36d3666f04575d833250a19126e4590d984a597b79dcf`, 293933 B.
- 바로잡음: 앞 항목 제목의 시각 "01:58"은 잘못 친 것이고 실제로는 01:18쯤입니다(그 뒤 발사 시각 01:18:40, `out/logs/wmi_launch_lines.txt`).
- 재계산 [실행]: WMI 발사 01:18:40(PID 9500, BelowNormal) → 01:22:31 끝(230.7 s). 출력 `KB/vvb3/out/vvb3_recalc.json` sha256 `1f5de72eba86c8a26fd61840132d098250fbf73476e88aff532b260cdb018013`. 구동기 판정 파일과 견준 칸 3,105, 다름 0, 숫자 최대 상대차 0. VB-I1 4/4 PASS, VB-I2·I3·I4·I6·I7 참, 훅 폴더 58 넷 점검 참, 고르기 다시 하기 = 구동기와 같음(43 SDMPC: selected 41, no_match 2), 기록 대 자기 계열 일치 41/41, ZI (z2)–(z6) 세 칸 참, 보관 목록 둘·V0 `archive_tree`·STOP r1 사본 셋 = 고정점 값.
- 보충 도구 `KB/vvb3/vvb3_extra.py` sha256 `9acae625860178261ba7628a4874448ccc184fca93ec440d3ca4d939c7c35e3d` — **공개: 보고서 r2와 재계산 출력을 읽은 뒤에 썼습니다.** 판정 숫자는 다루지 않고 보고 전용 항목만 다시 셈(z1_off 훅 끔 대 RR 기록 = 고정된 `vvb3_recalc.compare_dec` 그대로, ZI 훅 비용·벽시계 경로 수, 사슬 벽시계·중앙값, done 기록의 트리 바이트 전후·영수증 수, 단계·STOP 파일·VBR 크기, 8상태 범위, no_match 두 결정의 후보별 서명 어긋난 자리). 이 항목 뒤에 한 번 돌림(WMI 분리).

## 2026-10-23 01:31 +0900 — VerifyVB 3: 보충 출력, 표 대조 도구 고정, 재실행 발사

- 이 항목 덧붙임 전 LOG sha256 `7ef9c16c0df6346c758a049d620ba22f49f4b5bb4666ba2a1c9c0bdb8d0716ca`, 295501 B.
- 바로잡음: 앞 항목 제목 "01:27"은 실제 01:23쯤입니다(보충 도구 발사 01:23:30).
- 보충 출력 [실행] `KB/vvb3/out/vvb3_extra.json` sha256 `3dcfb679e159360b487906050373ca4044a96ff3e6490e4064e7b95651e6a1e7`(01:23:30 발사, 01:24:5x 끝).
- 재실행 `vvb3_rerun.py`(고정 `c73c246c…`) WMI 발사 01:25:44(PID 8084, BelowNormal). 트리 `TK/vvb3_e27ceac8` = VBT와 캐시 밖 파일 10,569개 모두 같음(278.9 s), T=3,300 준비 참, 발사 인자·환경 = V-B 실행 기록(자리 바꿈 뒤) 같음.
- 표 대조 도구 `KB/vvb3/vvb3_tables.py` sha256 `1e7aaf5088c0ca78a3ed5b2bf138fdac517eece8906379a03392771b3b396f57` — **보고서를 읽은 뒤 씀(공개)**: 내 재계산 출력으로 보고서 §3.4–§3.7·§4.2–§4.5 표 줄을 같은 꼴로 다시 만들어 보고서 글에 있는지 찾음(표시 대조만, 숫자는 고정 재계산). 가벼움(파일 수백 개 읽기), 앞에서 한 번 돌림.

## 2026-10-23 01:48 +0900 — VerifyVB 3: 표 대조·두 결정 재실행 끝

- 이 항목 덧붙임 전 LOG sha256 `3cb7adc4c54842e0d89c6330cf819b86a741abf5bce877ff0d2b61a330c00aa4`, 296668 B.
- 표 대조 [실행] `out/vvb3_tables.json` `e887e9fd22850a0442d616d7434125b371ac5b2c74004378cf06eb1fdd763551`: 내 재계산으로 다시 만든 보고서 표 줄 243개(§3.4 14·§3.5 55·§3.6 58·§3.7 8·§4 결정 96·사슬 12) 모두 보고서 r2 글에 그대로 있음. 보고서 §9 sha 43줄 = 파일 [실행]. 55결정 실행 기록의 튜닝 sha·직전 행동 자리·제어기·훅 켬 모두 규칙대로(도우미 `KB/vvb3/adhoc_run_records_chk.py` `6e18cd2f…`, 읽기만; 처음에 /tmp에 써서 돌린 뒤 이 자리로 옮김 — 공개).
- 재실행 [실행] (WMI 01:25:44, PID 8084, BelowNormal): 트리 `TK/vvb3_e27ceac8` = VBT(캐시 밖 10,569파일 같음, 빌드 기록 `a48a0d7e…`), 발사 인자·환경 = V-B 실행 기록(자리 바꿈 뒤) 두 결정 모두 같음. T=3,300 종료 0(553.4 s), T=3,450 종료 0(423.4 s). **R-ID: T1 CSV 바이트 같음·결과 넷 PASS(HARD 같음, 미분류 0; 허용 V 6·F1 9·F3 16·R3-01 2); T2 CSV 바이트 같음·HARD 같음·미분류 0(선언 잎 (a) 영수증 sha 2·(b) 직전 JSON sha 1·(c) action_token 20만 더 다름, 값 조건 참) → 둘 다 참.** 고르기: T1 `no_match`(후보 3·맞음 0) = V-B와 같음, T2 `selected`(후보 5·맞음 1) = V-B, 고른 기록 blocks·horizon 같음(상대 1e-12). 읽은 V-B·RR 파일 목록 앞뒤 같음. 출력 `OK2/vvb3/rerun.json` `3a6946e9db94c92b09a40f34ea261781a52f81a4f5b9e4950c8dc0e8efc2823f`(403 MB 폴더), 트리 2.1 GB. 끝에 python·VISSIM 0, C: 40 GB, D: 369 GB.
- 다음: 보고서 r2 고침(r3; r2 바이트는 `KV/K92_VB_REPORT_r2.md`·`KB/VB_REPORT_r2.md`·`OK2/vb2/K92_VB_REPORT_r2.md`로 이미 보관, `79e7cb03…`) → `KV/VERIFY_VB.md`.

## 2026-10-23 01:52 +0900 — VerifyVB 3: 끝 (다름 0, 재실행 같음 규칙 참, 보고서 r3)

- 이 항목 덧붙임 전 LOG sha256 `c8423866232ecea30870881335e456f12b2ac173cbbcd36f6f30454e7d36c31a`, 298566 B.
- 보고서 r3(정본 `KV/K92_VB_REPORT.md` = `KB/VB_REPORT.md` = `OK2/vb2/K92_VB_REPORT.md`, `cmp` 같음) sha256 `08bd9238ecce3c001132d6371eab0367a74373f9622457f051474921aefa1241`(646줄). r2 보관 `KV/K92_VB_REPORT_r2.md` = `KB/VB_REPORT_r2.md` = `OK2/vb2/K92_VB_REPORT_r2.md` = `79e7cb03…`. STOP r1 사본 셋 `d7bf44f3…` 그대로. 고친 곳: §3.7 B1 벽시계 합 6.53 → 6.52 h, "어림 안쪽" → "조금 짧음"(9.35 h), 머리 크기 단위 표시(du -h), no_match 두 결정 사실 더함(녹색·오프셋 전체 = 앞 결정, 예측 순서 없음, 고른 목적값 = 유지 목적값); 판정·VB-M 값 바뀜 0. 변경 기록 r3 §10.
- 검증 글 `KV/VERIFY_VB.md` sha256 `c5e0ba587df83029b6b46befa464a09f6dacbf7af266ec384bcf44bc77b40b76`(134줄).
- 끝 상태 [실행]: python 0·VISSIM 0, GWT8 head `e27ceac8`·status 0줄, 커밋·푸시 0, C: 40 GB·D: 369 GB. 봉인 시드·봉인 뿌리·v3c3-s47·codex 64cf 0. 끈 프로세스 0.
- 다음(사용자 결정): V-A 폐루프 3시드 go/no-go, 브랜치 푸시, V-A 동결 때 GB-7′ 목록 보충, no_match 까닭을 더 볼지, 검증 산출물(TK/vvb3_e27ceac8 2.1 GB, OK2/vvb3 403 MB) 정리 시기.
