# c_port LOG — codex 기구 묶음별 이식(길 C) 작업 기록

- 줄임: SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, CP = `SP/c_port`, W = `CP/w1099`.
- 표시: [실행] 명령·도구로 확인 · [읽음] 파일을 읽어 확인 · [추론] 시험하지 않은 판단 · [계산] 산술.

## 2026-10-27 05:08 KST — w1099 시작 (입력 1099 대기 분해, D-K9-93 ④)
- 근거 결정: D-K9-93 ④ "입구 1099 대기 오프라인 분해(링크 26 위치·차로·시간, 링크 120, 미터 10480·10482, 끝 엮임 10479·10491)" [읽음 `SP/K9_1_J1_NOTES_20261013.md:310`, sha c6c720eb…].
- **데이터 뒤 선언**: B 결과(B_RESULTS r2 152a2f6f…, VERIFY_B f2851f8b…)를 본 뒤 정의하는 새 분석. 규칙과 도구 sha 는 실행 전에 이 LOG 에 적음. COMPARE_RULE_B·PINS_B 는 바꾸지 않음.
- [실행] 디스크 C 28 GB, D 225 GB. PC VISSIM 0, python 0 (05:08). VISSIM 띄움 0.

## 2026-10-27 05:14 KST — readback 시작 (미터 실행 대조, D-K9-93 ③)
- 줄임: RB = `CP/readback`.
- 근거 결정: D-K9-93 ③ "signal_readback.csv 로 미터 신호 대조를 새 선언(데이터 뒤임을 밝힘)으로 실행" [읽음 `SP/K9_1_J1_NOTES_20261013.md:310`].
- **데이터 뒤 선언**: VERIFY_B(f2851f8b…) D5 가 선언 밖으로 이미 readback 을 셌고(810/810 주기), 이 작업자도 규칙을 쓰기 전에 B v3c3-s31 readback 머리 약 40줄·SC 별 행 수·V-A v3c3-s31 머리를 형식 확인으로 봤음. 규칙(RB/RB_RULE.md)과 도구 sha 는 실행 전에 이 LOG 에 적음. COMPARE_RULE_B·PINS_B 는 바꾸지 않음.
- [실행] 디스크 C 27 GB, D 224 GB (05:07). 남의 python 1개(PID 32548, codex td3 native_segments) 무접촉. 같은 폴더 w1099 작업자와 무거운 작업이 겹치지 않게 발사 전 c_port python 검사.

## 2026-10-27 05:16 KST — vsl 시작 (VSL 오프라인, D-K9-92)
- 줄임: VS = `CP/vsl` (도구 `VS/work`, 출력 `VS/out`), 산출 문서 `CP/VSL_OFFLINE.md`.
- 근거 결정: D-K9-92 "A1 의 VSL 100 결정 8개 + codex T=1,800 결정 JSON(+ 64cf-s29 window·off·VSL 단독 팔) 으로 plant 대 VISSIM VSL 반응 대조. VSL 런은 그 뒤" [읽음 `SP/K9_1_J1_NOTES_20261013.md:309`, sha c6c720eb…].
- **데이터 뒤 선언**: B 결과(B_RESULTS r2 152a2f6f…, VERIFY_B f2851f8b…)를 본 뒤 정의하는 새 분석. A1 결정 JSON·codex 원자료 결정 JSON·64cf-s29 FZP 는 앞 단계(RAW_CHECK, A1_RESULT r2, W264_READ r2)가 이미 일부 읽었음. 분석마다 규칙과 도구 sha 를 실행 전에 이 LOG 에 적음. COMPARE_RULE_B·PINS_B 는 바꾸지 않음.
- 범위: VISSIM·COM·폐루프 러너·동결·커밋·푸시 0. 런 폴더·인계 사본·동결 트리·GWT8·Y: 읽기만. 무거운 일은 한 번에 하나(같은 c_port 의 w1099·readback 작업자와도 겹치지 않게 발사 전 python 검사), WMI·BELOW_NORMAL·PYTHONHASHSEED=0·python -B. plant 재생은 scratch 트리 `D:/VISSIM-merge/k8_gate_trees/codexhandoff/vsl_off/` 에서만, env_hsw.
- [실행] 디스크 C 28 GB, D 225 GB (05:11).

## 2026-10-27 05:16 KST — vsl V1 선언 (결정 JSON 의 VSL 기록 읽기) · 데이터 뒤 선언
- 규칙 V1: 아래 결정마다 결정 JSON(읽기만)에서 VSL 축(코드 sdmpc.py:405-415), 쓴 VSL(`vsl`·CSV), secant 기울기 행(`gradient_rows` kind=vsl: own·external·total·stencil·자원 도함수; J(낮춘 값)−J(기준) = total×stencil[0]), 지역 QP 행(`local_rows` FW_E·FW_W 의 VSL 칸 own·ext·price 기울기와 걸음; 걸음 ≤ −0.04545 면 한 칸 아래로 반올림), PFO 행, 시험 행·후보·쌍대 갱신·목적값을 뽑는다. 모형을 돌리지 않는다.
- 결정 목록(지금 고정): A1 = 1650·1800·1950·3000·3450·3600·3750·3900·4050·4200·4350·4500·4650 (VSL 100 결정 8개 + 이웃; 3150·3300 은 유지라 뺌). codex joint = 1650·1800·1950·3450·3900·4350·4500·4650. codex freeway_only = 쓴 VSL 이 110 아닌 결정과 그 바로 앞 결정(CSV 로 찾음).
- 도구 sha256: v1_dec_vsl.py 592cfcd845f457a8877c11fafdf2f145678ca65f9462fbe27a28e102b5e80b44 · vs_launch.ps1 0f85aeeed1fb274b9a855447d795bea6f4df6bf190e58ad1294e72f56aa6c8ca (WMI·BELOW_NORMAL·PYTHONHASHSEED=0·python -B·스레드 1, c_port python 이 돌면 거부). 구조 확인용 probe_keys.py 002cfe350d503239d2a6c7cfcd941f03ba0f00602c33a41287d15199b94f5c68 는 A1 1800 결정의 키 구조만 봤음(분석 숫자로 쓰지 않음).
- 출력: VS/out/v1_dec_vsl.json.

## 2026-10-27 05:17 KST — w1099 규칙·도구 고정 (데이터 뒤 선언, 스캔 출력 보기 전)
- 규칙: W/W1099_RULE.md 4768d2631b831872890ba3b7e4180c1301654a647c697ba48796a582ae99bb35 — 망 배치(망 3de889f0…), 잴 것 M1–M7, 기구 후보 H1–H6 와 받침/반박 꼴을 스캔 전에 적음.
- 도구(읽기만): W/w1099_scan.py 0ed864f29ab3d8b09d1e03734b0590f14593250a06246d7aa6e98a57c9c2281d, 발사 W/w1099_launch.ps1 96f0a6a697d1a10eac619c60f6639ba3d7a6db2c99d88e3c12d958b18cb276c3, 망 탐색 W/net_probe.py 751562ffa483bcb0d1f7982818d570ddfe08b1398818a1d78ae11fb7ac5a1332 · W/net_probe2.py 8cb5e4a9f4c58752abbadf9bb5e68f4dcc55325f38f0ac9fbf2484f2913cfd37 → W/out/net_links.json 66fe3253a82bcea12912fa397f8dc454d24b9c71816f995774d075ef51b8d2d9. 핀 목록 W/PINS_W1099.sha256 8c7003bfcfe4fd0a20df8d874a4bd3489db90a6646934696ebe62b8cf7eb6b65.
- [실행] 시험: w1099_scan.py 를 B v3c3-s41 FZP 앞 300,000 줄 잘라낸 사본(W/test, 시험 뒤 지움)으로 한 번 돌려 출력 꼴 확인(1.3 s). 이 시험 출력은 분석에 쓰지 않음.
- [실행] 밝힘: 망 해시 대조 때 glob 이 NC3 폴더의 다른 시드 망 파일(.inpx, 결과 아님)까지 sha256 를 냈음. 봉인 시드 하나가 그 안에 있음 — 망 입력 파일 해시 한 줄만 화면에 나왔고 내용·결과 자료는 열지 않았으며 이 분석에 쓰지 않음. 이후 시드 목록을 31·41·43 으로 적어서만 씀.
- 디스크 C 28 GB, D 225 GB.

## 2026-10-27 05:18 KST — vsl V1 끝 · V2a 선언 (FZP FW_E 스캔) · 데이터 뒤 선언
- [실행] V1 PID 47928, 39결정 읽음, 오류 0, 44.8 s. 출력 VS/out/v1_dec_vsl.json c52791bd28efd36729e5b23dc2ed327c5c1c9c5c6be902dfe7ab69c813b23653. freeway_only 결정은 축 48개(고속도로 레버만).
- 규칙 V2a: 기존 고정 스캐너 rmcause/phys/fwe_scan.py(sha 0619e9fc…, 바꾸지 않음; 100 m × 60 s FW_E 체인 칸, 차로 칸 3,800–8,000 m, 검지선 통과, 램프 합류·대기)를 64cf-s29 FZP 다섯에 한 번에 하나씩: codex joint·window·off·freeway_only(원자료 사본, 읽기만), A1. NC·VSL 단독은 기존 스캔(rmcause/phys/scan/cf_s29_none.json, rmcause/o1o4/scan/vsl_s29.json)을 그대로 씀.
- 도구: work/v2_scan_chain.py f063630eb88d413627509450a81a63e8427b323e88f36c7a63acd69bf406d1b5 (스캐너 sha 확인 뒤 차례로, BELOW_NORMAL). 출력 VS/out/scan/<tag>.json.
- 05:19 V1b 선언: work/v1_summary.py 2c1cf037245e53fd99c449adbdb7f61df03d4b1520b05a72e69b2044a9d9ac45 — V1 출력만 표로(결정마다 쓴 VSL, 첫 호출 secant 행, 양수 행, 한 칸 아래로 반올림되는 지역 걸음, 가격 칸, 목적값). 가벼움(수 초), 세션 안에서 실행.

## 2026-10-27 05:21 KST — readback 규칙·도구 고정 (런 자료로 돌리기 전)
- 규칙 `RB/RB_RULE.md` sha256 6a27a1bf777edd5f23f7bb1129ce587870387b4622eb4bbe766782723bd6c255 (데이터 뒤 선언).
- 도구 sha256 (`RB/PINS_RB.sha256` 8c0b034ea9f7b89a2b151e4be89ee88c7b2a00b8a3f53ec82c276881e01b1411):
  - 6a27a1bf777edd5f23f7bb1129ce587870387b4622eb4bbe766782723bd6c255 *RB_RULE.md
  - 25ea55076e35bc36551560dd4e397472125a678faef5fe57c9609b7dcfab2234 *tools/rb_inpx.py
  - cee5f2629b8accc602655cbcbf2dc706796f57b97a69f66ee25966ac550a96cb *tools/rb_readback.py
  - 3687d3c8609786f09045e1c50975b8e2c7c7dc2c91408b3e537ea31fdc7aec84 *tools/rb_fzp_scan.py
  - ea156a9184cfc0bbaa282d3433107cff5b72ca95595782c8cce43e50f7d8f05f *tools/rb_scan_chain.py
  - 4c385da965298b49e445ba599cdf0314f719184bee900ae78b309f9ecd4303e9 *tools/rb_discharge.py
  - 0733647ac068b80f498f00185e8886dbd7893343119386f26323c0fd66f1b5d8 *tools/rb_launch.ps1
  - c0674b39d368ff9d9ccd42662c48166a0669ae0e073c351a5ddc169502ab347e *tools/rb_selftest.py
- 모형 표 출처 FRZ_B1 `diagnostics/b0_v3c3/config_b0_v3c3.json` sha256 729640af754a90c8d7fbe8f81577b27bae02b86f1d504e18333c0fc99717f983 (:7528-7538, 우리 c20aff1d CFG:7524-7534 와 같은 값 [읽음 git show]).
- [실행] 합성 자기 시험(`rb_selftest.py`, 런 자료 0): 주입한 9 s 녹색 주기 1개를 K3 가 잡음, 헤드 통과 9 + 헤드 뒤 첫 기록 1 = 이탈 10.
- 05:20 V1b 결과 출력 out/v1_summary.json 368eff25724ba23e031fc71b908c00c4715b6b8072176bbf7eddb64ca5b58b54, .txt 2e1706ef5cf1f006428be994aa416fa61bc34d74b684b720c6608fe5c7b29288. V1c 선언: work/v1c_plan.py 30d1683aaa2ccbd0e54f14e6a23386d66f20c0f6c60bb50e990a32cbe814922a — V1 과 같은 21결정(A1·joint)에서 original_held_candidate·미터 이웃 검사 기준/선택·3블록 계획 VSL(블록 0 = 쓴 값, 1–2 = diagnostics.sdmpc_prediction_sequence.future) 읽기. 구조 확인 probe_seq.py a50810936ecd20ba6e2f7ed2d55f79aad3e2818b892440018d5ab25ba210c3ee 는 joint 4500 의 future 구조만 봄. JSON 21개(각 50–60 MB)라 WMI 로 띄움.

## 2026-10-27 05:22 KST — w1099 스캔 끝, 표 도구 고정
- [실행] 05:17:56 WMI 발사 PID 39248 (BELOW_NORMAL, env_hsw, python -B, 한 번에 하나) → out/scan.log ALL_DONE, FZP 9개 각 27–31 s. 우리 프로세스는 끝남(남은 것 0).
- 표 도구(스캔 출력 보기 전 작성, 실행 전 고정): W/w1099_report.py a3bf9b0c3865a9b1c350886a8ba5711a2074fade239d79e2137e41e3e8e4356d (핀 목록에 더함). 가벼움(JSON 9개 + 명령 CSV 6개 읽기)이라 세션에서 직접 돌림.

## 2026-10-27 05:22 KST — readback 실행 (K0–K6) 과 FZP 스캔 발사
- [실행] `rb_inpx.py` 6개 inpx(B·V-A × v3c3-s31·s41·s43): 모두 sha 3de889f0257d998b…(같은 망), 미터 헤드 위치 N34 표와 차 0, 헤드 뒤 저장 10490 16.0 · 10484 27.5 · 10681 24.5 · 10639 15.6 대(N34 와 같음). 출력 `RB/out/inpx_<run>.json`.
- [실행] `rb_readback.py` 6런 앞에서(가벼움, 25 s): `RB/out/readback.json`, `RB/out/cycles_<run>.csv`. 첫 줄 결과 K3 6,480/6,480 주기(런마다), K0 488/488.
- [실행] 05:22 `rb_launch.ps1` → `rb_scan_chain.py` WMI 분리 PID 35440 (BELOW_NORMAL, python -B, PYTHONHASHSEED=0, env_hsw, 스레드 1). 발사 전 w1099 의 스캔 PID 33032 가 끝나기를 기다림(한 번에 하나).
- 05:25 [실행] V2a 발사 PID 8444 (vs_launch.ps1, WMI·BELOW_NORMAL). 발사 전 c_port python 0 확인(w1099 스캔 끝남, readback 스캔 PID 35440 은 이미 끝남).

## 2026-10-27 05:36 KST — readback 결과 1차 (K0–K9) 와 비교 열 추가 선언
- [실행] 스캔 사슬 끝(05:24:41, 6 FZP 각 22–26 s, header_ok 모두 True; V-A v3c3-s31 FZP sha d3a440af… = N34 스캔과 같음). `rb_discharge.py` 앞에서 1.6 s → `RB/out/discharge.json`.
- [실행] 검산: V-A 10681 차로 2 g10 1차 1블록 888·2차 5블록 888·정지대기 B 아님 32 — N34_FLOWS.md:224 와 같음(독립 재구현 일치).
- **데이터 뒤 추가** `RB/RB_RULE_ADD1.md` sha256 8eabd151d139ccc38f7e18c70cc22c0221d4a770e84a19274f9a71a954844611: K0b 에서 B FW_E 미터 4개 group_rate_vph ≠ 표×차로 를 보고, B 설정의 머리 서비스 곡선(config_b0_v3c3.json:8161-8202, lane_plant_runtime.py:616-620)을 K7 비교 열로 더함. 도구 `tools/rb_headcurve.py` sha256 1466ff35839d494c858637f47ea392df5963c983426fd03772956c04a1f3b56b (실행 전 고정). 다른 정의는 그대로.
- 출력 sha 목록 `RB/out/OUT_SHA_1.txt`.

## 2026-10-27 05:28 KST — 덧붙임 1 고정 (SC1001 둘레, 데이터 뒤 선언 두 겹)
- [실행 05:22] 표 도구 1판 실행 → out/report_tables.md 1e5527c9ed5a60d2105fe9fc772297425d414db2e756cfe71a0683b07af41f79, out/report.json b7aa26efd30a0cdf4dc1c53761aca7e4bb886ef4384f8345d6ac67a1c21d83d6. 점검: S_1099 9런 vb_scan 과 소수 셋째 자리까지 같음, 링크 26 총량 link26.json 4런과 같음. T8 상관은 마지막 구간 프레임 0개로 NaN(도구 결함, 2판에서 빈 구간 뺌).
- 1판 표를 본 뒤(링크 127 느림·SC1001 SG2 명령 차·129/10491 느림) 덧붙임 규칙을 씀: W/W1099_RULE_ADD1.md fd70dfdefd37c02a1bf219f0aab2a9fdde736d253042d1ebb778cae531aa20b5 (H3b·H3c·H3d 예측, T13 문턱 — 문턱은 1판 T8 s31 앞 10줄만 보고 정함, 밝힘).
- 도구: w1099_scan2.py e33c080765381f55cde77fca26751f0209d1a81f48b3a3c1b6a45c1ca1778461, w1099_launch2.ps1 4b0aba7c5ccb9f0d442c5b2f75fae18ae568de8596aae296faf9accf162aa081, w1099_sc_readback.py c31227d7161a4ad306ea5aa307f456c00b19c20977789e9f69d7757d8da60168, w1099_report2.py 19be1098a6304eb5b4d072a0528d02d90bebd8dd294b17bd75fe3f9fb635a146, w1099_report2_add.py 065bdfb63896c521c1a886176c0f1df3d219e88094c1d1dc01fb064ccf81ecd5. 핀 목록에 더함.
- 05:29 [실행] V2a 끝(CHAIN_DONE, 다섯 스캔 각 40–45 s, 종료 0). 행 수 joint 6,151,818 · window 6,240,760 · off 6,226,669 · A1 6,140,911 · freeway_only 6,752,032 (joint·A1 은 A1_RESULT 와 같음). 출력 sha: a1_s29.json 5f996c93076b439e… cx_fwonly_s29.json f01c1f65eb5c650c… cx_joint_s29.json c2d2b8dc7a36315d… cx_off_s29.json d13da72e196fb270… cx_window_s29.json a7d8a926f6af6794… 

## 2026-10-27 05:29 KST — vsl V2b 선언 (VISSIM FW_E 반응 비교) · 데이터 뒤 선언
- 규칙 V2b: fwe_scan 격자(읽기만)에서 칸별 지표. 구역(체인 m): U 0–4,200 · B1 4,200–5,300 · M1 5,300–6,300 · VSa 6,300–6,800(표지 6,341.7 m ~ 차로 감소 6,841.7 m) · VSb 6,800–8,100(B2, 다음 DSD 8,090.8 m) · D 8,100–10,800. 지표: 구역 평균속도(ΣV/ΣN), 구역 veh·h(5 s 프레임), 검지선 3,700·4,600·5,300·6,300·6,800·7,300·7,700·8,500 m 통과율, 램프 합류율(10681·10490·10484·10639)·램프 대기 veh·h(속도<15), 링크 74 삽입률, VSL 구간 6,300–8,000 m 차로별 평균속도, 500 m 칸 평균속도(3,000–9,000 m), B1 번짐 분(<4,500 m)·M 번짐 분(<6,800 m; 고정 tails.py cb6c0bd4… 그대로).
- 창: 0–900, 900–1,800, 1,800–2,700, 2,700–3,600, 3,600–4,500, 4,500–5,700, 5,700–8,100, 900–8,100, 1,800–5,700, 900–1,350, 1,350–1,800, 1,800–2,250, 2,250–2,700, 5,700–6,150, 1,800–1,950, 1,950–2,100, 3,450–4,500, 4,500–4,650.
- 짝: VSL 단독 − NC(vsl_repro_s29, 900–9,000 s DSD 63–66 = 90, 미터 없음·도시 native), window − off(codex RM+TSC, window 는 seg13 90 @1,800–5,700), joint − off(VSL 출력 둘 다 110), A1 − joint(A1 VSL 100 결정 8개, 궤적은 1,350 s 부터 이미 다름), 참고 freeway_only − NC. 모두 64cf-s29 한 시드, v3c3 와 다른 망.
- 도구: work/v2_vissim_vsl.py 754719f610a40ef446e59fe096e438626e5a3d9b8c17ab376b6da624cb409cee (가벼움, 세션 안). 출력 VS/out/v2b.json·.txt.
- 05:31 [실행] V2b 끝(세션 안, 종료 0). 출력 out/v2b.json e1745813d3aaeb0d1b0f4dcf1d99f3af958716cff4bb0ec940e79df5546b7d3e, out/v2b.txt 1204774274ecd9b35cce1f7406de8943c6ac971eb54733ade6ea9d263dfbc2f9.

## 2026-10-27 05:31 KST — vsl V3 선언 (plant 오프라인 탐침, VISSIM 0) · 데이터 뒤 선언
- 규칙 V3: 기록 상태 넷(A1 T=1,800 = A1 이 100 을 쓴 결정·secant 양수; A1 T=3,600 = 기준 명령이 이미 100; codex joint T=1,800 = seg13 블록 1 secant +0.10 이지만 110; codex joint T=4,500 = 가격 걸음 사례)에서 codex 어댑터를 VBS 명령줄 그대로 돌리되 sdmpc.solve 만 탐침으로 바꿈: sdmpc.py:791-874 와 같은 결정 문맥(held 기준·운영 한계·공유 질의·좌표·저장 보호 운영 seed)을 만들고, 최적화·도함수 없이 plant 점수만 냄(질의는 프로세스 안, parallel_workers 0). 변형: seed 그대로, FW_E seg13 세 블록 모두 110·100·90, seg13 블록 0 만 100(A1 3,600 은 110), seg5 세 블록 100. 각 변형에서 FW_E 정제 셀별 밀도·속도·흐름(plant 걸음마다, PhysicalLaneGroups.advance 뒤), plant 가 셀마다 쓴 VSL(segment_vsl), Ω 소유자별 비용, 입구 대기를 기록. 행동 파일은 쓰지 않고 프로세스를 끝냄.
- 점검: seed 목적값 대 기록된 pfo_warm_start.initial_omega_objective(같은 seed 의 plant 점수) 차를 보고만 함(비트 같음 요구 아님).
- 읽기(V3b): 기준 = v110_all. Δ 목적값·Δ 소유자 비용·셀별 시간평균 Δ속도·Δ밀도·Δ흐름·구역(U/B1/M1/VSa/VSb/D, 셀 중앙 체인 위치)별 Δ속도(|Δ|<0.5 km/h 는 ~0)·Δveh·h·150 s 블록별 Δ구역속도·Δ입구 대기. VISSIM 대조는 방향만: V2b 의 V−NC 900–1,350·1,350–1,800·1,800–2,700, window−off 1,800–2,250 구역 Δ속도 부호와 같음/반대/plant ~0 으로 적음(상태가 달라 크기 비교 아님).
- 입력 준비(가벼움, 복사만): work/v3_build_inputs.py 2c3745172fa65a3ea34904fef27a27ef0669c98cefec27d0dc3aed881862d1de (고정 A0 빌더 s4_build_inputs.py 72f7a5ac… 와 같은 규칙, 원천 둘로 일반화; **도구 sha 를 이 줄에 실행 직후 적음** — 05:31 에 네 상태 입력 트리를 먼저 만들었음, 출력은 복사·경로 바꾸기뿐: a1_T001800 132파일, a1_T003600 204, cx_T001800 132, cx_T004500 240, 안 바뀐 경로 0). 코드 트리: a0/code 를 vsl_off/code 로 robocopy(8,016파일·470.52 MB; sdmpc.py 5c1ba251…·physical_lane_groups.py abfa7f9c…·adapter a615d8ca…·freeway_fd.py 3c0c5892…·튜닝 c9088262… 같음).
- 도구 sha256: work/v3_plant_probe.py 398d30ba506c9f45e7237c26924f170764089f6c6b78311675c183911f18e663 · work/v3_run_probes.ps1 0698eeedf8c3628c73e2b31adf819918422a0b9e4378694910f30c3adcf162a2 (A0 재생 스크립트 run_replay2.ps1 119bbd38… 의 env 그대로 + env_hsw, BelowNormal, 한 번에 한 상태) · work/vs_launch_ps.ps1 6abb33f6af769f6c6c9b36808a4224b9fb1ddb736d81d0a05d97e3a2ff33b714 (WMI 분리) · work/v3_analyze.py cb0e885f4e6bb4f7888fecb37efb214a3d1afd34c0fdfdca67f9fa2d226b2f72.
- 순서: a1_T001800 하나를 먼저 돌려 탐침이 도는지 보고(실패면 도구 고침을 새 sha 로 적음), 나머지 셋을 차례로.

## 2026-10-27 05:45 KST — readback 마감
- 보고 `CP/READBACK_METER.md` sha256 2fd9863934f93d09341e84df45f7c67cc404e0c4e97dcb85ed1ec465bbd7f980.
- `RB/PINS_RB.sha256` sha256 9402d9eee25697877c2280902ce8447eed47db2dd58faf96d0632acde708fa6b (규칙·ADD1·도구 10개, 실행 뒤 `sha256sum -c` 10/10 OK). 출력 sha 목록 `RB/out/OUT_SHA_2.txt` 56a88b1ca804318b71186fa34c7bbbfbdf41ddad3257b4a54ae5b7fac61b3f23.
- [실행] 요지: B v3c3-s31·s41·s43 각 미터 8 × 810 주기 = 6,480 주기 녹색 초 = 명령(어긋남 0), 행 17,370/17,081/18,089 모두 요청=읽음=기대, 쓰기 8,458/8,306/8,817 모두 post_step 재확인. V-A 3런 488행 모두 GREEN=명령. 녹색별 차로 방류(1차 블록) = 모형 표의 1.20–1.48배(14칸 중 13칸), codex 머리 곡선의 0.89–1.09배(FW_E 13칸 중 12칸). g2 = 주기당 1대(10639 74블록 모두).
- [실행] VISSIM·COM·러너·재생·커밋·푸시·kill 0. 런 폴더·FRZ·GWT8 쓰기 0. 디스크 C 27 GB, D 225 GB.
- 05:33 [실행] V3 시험 발사(a1_T001800 만) PID 51024 (vs_launch_ps.ps1, WMI·BELOW_NORMAL). 발사 전 w1099 의 두 번째 스캔(PID 50972)이 끝나기를 기다림.

## 2026-10-27 05:35 KST — 2판 표 실행·덧붙임 2 고정
- [실행 05:29:02] scan2 WMI 발사 PID 31092 (BELOW_NORMAL, env_hsw, 한 번에 하나) → out/scan2.log ALL_DONE (9개 각 24–27 s). sc_readback 세션 실행(가벼움, SC1001·1002 readback 줄 어긋남 0). report2 → out/report2_tables.md f24249dde2af2a56885f275492f0133ecabc138768848f2e91e6056c4b71e3b8, out/report2.json 416a4e1b805965a0bf9cc467c9f32269e01e577b1aa2d4bd392aa3af2b0c73fa, out/sc_readback.json b7dc33515e659d629d2fa21b990007bb448c74b37447499060c414569602e1c1.
- 2판을 보고(s43 보존 점검이 안 맞음) 덧붙임 2 를 씀: W/W1099_RULE_ADD2.md 80bb7e05e8d24f4ae843f98221e8b83efd389b345943a8e227be45effbc79eb7, 도구 W/w1099_add2.py 8b9394ad71b68077b23a3793499fd943fe39ac39aa5fc4c4ffe27ba65b4d8f59 (out/*.json 만 읽음).
- 05:36 [실행] V3 시험(a1_T001800) 끝: 종료 0, 138 s(준비 63 s, 변형당 약 15 s). 목적값은 나왔으나 셀 기록 0행: FW_E 는 PhysicalLaneGroups 가 아니라 LaneFreewayRuntime 의 집계 경로(5 s 다중속도)로 걸음 → 갈고리 자리가 틀림. seed 목적값 521.476932 대 기록 PFO 초기값 521.471395(차 +0.0055). 시험 출력은 out/v3_a1_T001800_smoke1.json af0b155c303a628fddd51e3d0450b54801c69ab7df35042d15fc9df01cb5adba 로 보관(결과로 쓰지 않음, 목적값 비교 참고만).
- 도구 고침(실행 전 기록): 갈고리를 lane_freeway_runtime.LaneFreewayRuntime.advance 뒤로 옮김(state.freeway_density/speed, 유효 차로, 셀 길이 = area_freeway_accounting.cell_lengths_km, 걸음 전후 시각, 램프 방출·진출 용량, 입구 대기, 부품 설정 덤프). 새 sha: work/v3_plant_probe.py 7307f8a5a12ac9b1c694b7d2af2ebb706a0e7e6f7315f7086746e89aead3cf39, work/v3_analyze.py 7f123b89eea7fc0697e38e6b4dc472058b20f5da14bb487020f13e7c19fadbd6(행 형식 맞춤: 시간 가중 평균, 흐름 = k×v×차로, 재고 = Σk×L×차로). 규칙은 바꾸지 않음. 이제 네 상태를 차례로 돌림.
- 05:38 도구 고침(실행 전): v3_analyze.py 에 '캐시 적중 변형(같은 행동 토큰)은 앞 변형의 걸음 기록을 씀' 추가 — v110_all 이 seed 와 같은 토큰이라 걸음 기록이 0행이었음. 새 sha daea1d53a501b6226946f3daa2e83f87d140028ab574effed4bd69c776d52a12.

## 2026-10-27 05:43 KST — w1099 마감 (INPUT1099)
- **산출: SP/c_port/INPUT1099.md 1548316a36b5647ee2a0132af9814d91c5c25d0be1d489a170170b65c3e31285** (+ INPUT1099.md.sha256).
- 출력 sha 목록 W/OUT_W1099.sha256 a4f171f206041ec5a6070527e91df99104c4c92df9b3e349dbc22f2afa8a2de0 (스캔 JSON 18개·표·readback·add2). 핀 W/PINS_W1099.sha256 13e947fe0389015e5d4c14411e763c8e885660a293295b78438fb393b3722ddb — sha256sum -c 모두 OK(규칙 3·도구 11·net_links).
- [실행] 요지: 넣기는 멈추지 않음(0 프레임 ≤ 19, 최장 15 s), 2,700–4,500 s 넣기 B − NC3 −10.4/−15.2/−2.8 %. ④b 1099 +490.0/+468.4/+84.0 의 84/86/51 % 가 4,500 s 뒤 이월. 사슬 SC1001 SG2 녹색(900–2,700 s B 406/409/512 대 NC3 576 대 V-A 578/638/680 s) → 127 시작 7/4/6 km/h → 129·10491 느림 → 26 차로 1 끝 → 입구(시작 순서 3/3, 보존 s31·s41). 반박: 미터 10480(124 체류 B=NC3, 합류 B≥NC3), 10490(상관 0.18/−0.12/0.16), 링크 120(느림 0), 10479·125(느림 0), SC1002(링크 30 앞 느림 0), 링크 2 유입(같음). s43 은 잡음 크기 안(넣기 차 109 대 대 72).
- 고칠 글 제안(파일은 안 바꿈): VERIFY_B D4·B_RESULTS §1.7·§2.1-3 의 RM_C10480 합류 "3,525 m" → 3,625.8 m.
- 시각 고침: 이 LOG 의 w1099 항목 머리 시각을 어림(05:35·05:58·06:25·06:52)에서 파일 시각(05:17·05:22·05:28·05:35)으로 고침. 규칙 파일 머리의 고정 시각 글은 핀 때문에 그대로(실제 05:15:29·05:27:32·05:35:32, 모두 실행 전).
- VISSIM·COM·러너·재생·동결·커밋·푸시·kill 0. GWT8·런 폴더·codex 원자료·동결 트리·Y: 쓰기 0. sealed/·봉인 시드 자료 0, 금지 시험 0. 디스크 C 27 GB, D 223 GB.
- 05:45 도구 고침(실행 전): v3_analyze.py 걸음 길이를 '다음 걸음 시작 − 이 걸음 시작'(마지막은 시작+450 s)으로 셈 — 갈고리 안에서 state.time_sec 가 바뀌지 않아 t_after−t 가 0 이었음(1.25·1.667·2.5 s 부분 걸음). 새 sha c973fe58cb0f684b920442639b3e58d8a4d019bd8f3b696ab27087aa4c2541b6. [실행] V3 네 상태 끝(각 121–126 s, 종료 0): out/v3_a1_T001800.json 780bded1…, v3_a1_T003600.json 4c2dc334…, v3_cx_T001800.json 6cda6c77…, v3_cx_T004500.json 77be2d58….
- 05:48 [실행] V1c 끝(PID 34704, 21결정, 종료 0). 출력 out/v1c_plan.json 90b34b2d30b18abe2ddd6fafd1c0e8cee5a0949842f988e0e8710f73e9bbb6a3. V3b 끝(세션 안): out/v3b.json 7f828f1abdb5658e3b86e1917fd36d04e1cd5d5013c45d3af3e095341a7ce6f1, out/v3b.txt f8e747905d04a5dd3f059d9b0cf58886e35193af1454bc5b23fb58a0d9641745.

## 2026-10-27 05:50 KST — vsl V4 선언 (짝마다 Ω701·④·Ω 밖, ④b 첫 관측 차분) · 데이터 뒤 선언
- 까닭: 보고서에서 Ω 를 ④·Ω 밖과 함께 적고 ④b 는 첫 관측 차분을 주 값으로 쓰기 위함.
- 규칙 V4: 0–8,100 s. window−off·joint−off 의 Ω701·④a 는 RAW_CHECK final_table.json(c2da1c54…, codex 사다리꼴 꼴) 값. VSL 단독−NC 의 Ω701·④a 는 W264_READ linkbin(lb_vsl_s29·lb_nc_s29, 사각형 꼴, 150 s 칸 0–53) 과 Ω701 소속(D:/VISSIM_handoff/20261024/derived/omega_membership_exact.json inside_links). ④b = 첫 관측 차분(vhr_unins.py 식: U_a−U_b = S(b)−S(a), S = Σ(8,100−첫 관측 시각)), 첫 관측 자료는 vhr scan_out 의 first_window·first_off·first_joint·first_nc_raw(이미 있음) + 새 first_vsl. 입력별(링크 74 = 1098, 26 = 1099, 그 밖)도 냄. ④ = ④a + ④b, Ω 밖 (a) = ④ − Ω701, (b) = ④a − Ω701.
- 도구: work/v4_firstseen.py c93d2fc3a551ab01f386150261669ee75b891f124a805eab9d7c142a7bb85a28 (고정 vhr_firstseen.py 42e17585… 와 같은 셈, VSL 단독 FZP 하나, WMI) · work/v4_omega.py 4a43deb46e50c3f73572b1aaf5fe1f2ff06518da7b366e3670a519798ec50601 (가벼움, 세션 안).
- 05:51 [실행] V4a 끝(PID 53412, first_vsl 67,666대, 8.9 s), V4b 끝(세션 안). 출력 out/first_vsl.json ceb5f188fd41090e8288d5d07dcd89d1050cc38c5afc6459229f9b670a91bc77, out/v4_omega.json de854edb731614f9f76504fb19cc83d1ad9e61021c2c9f31c02c74d8879d0bd0.
- 05:51 V1d 선언: work/v1d_window_axes.py 8a9040c15568eddf6539d67a85ced943328088ce43f227749e17683688659435 — codex window·off T=1,800 결정 JSON 의 좌표 종류·fixed_vsl·쓴 seg13 값·VSL 기울기 행 수만 셈(세션 안, 두 파일).

## 2026-10-27 06:00 KST — vsl 끝: VSL_OFFLINE.md r1
- [실행] V3b 첫 실행은 걸음 길이 0 으로 ZeroDivisionError(05:45) → 고친 sha c973fe58… 를 적고 다시 돌림. V1d(window·off 1,800 s 좌표: VSL 축 0, fixed_vsl 일정 확인) 출력 out/v1d_window_axes.txt 615c2209….
- **산출: CP/VSL_OFFLINE.md 6cca0baa715f4d0bb870bd5f7e2c2c05279bc168048961c106f95b430ba9debf** (+ .sha256). 도구·출력·스캔 55개 목록 vsl/SHA256SUMS_VSL.txt 0e8d9d1fe5691fc624858430d882a13902c945c1581319633461d1cdc70bafbe.
- 핵심 [실행]: A1 VSL 100 8결정 = secant 양수 2개(1,800·3,450, dJ −0.160·−0.127) + 기준 100 유지 6개(AD 는 110 쪽, 양자화·공통 선탐색으로 남음). codex 1,800 b1 +0.1017(dJ −0.009) → 110, 4,500 가격 걸음 후보 438.59·438.84 > held 437.20 → 110. plant 탐침(4상태, 450 s): 100 Δ −0.121 / +0.066 / +0.250 / +0.478, 90 +0.223 / +0.467 / +0.906 / +1.236 veh·h. VISSIM(64cf-s29 한 시드, 다른 망) VSL 단독−NC Ω701 −165.2 / ④ −77.6 / Ω 밖 (a) +87.6(④b 첫 관측 +79.6), window−off +25.7 / −101.6 / −127.3, joint−off −100.3 / −133.6 / −33.3.
- 지킨 것: VISSIM 띄움 0, kill 0, 커밋·푸시 0, GWT8·동결·인계 사본·런 폴더·Y: 쓰기 0, sealed/ 0, 봉인 시드 자료 0, 금지 시험 0. 끝에 이 작업 프로세스 0, PC VISSIM 0. 디스크 C 27 GB, D 223 GB.

## 2026-10-27 06:17 KST — c1 설계 초안 시작 (C1_DESIGN_DRAFT.md, D-K9-91 첫 묶음)
- 근거 결정: D-K9-91(길 C, 첫 묶음 후보 = 목적 경계 Ω701 접근로 + 미터 결정 묶음, ③④ 뒤 확정), D-K9-92, D-K9-93 [읽음 `SP/K9_1_J1_NOTES_20261013.md:308-310`, sha c6c720eb…].
- 입력: `CP/READBACK_METER.md` 2fd98639…, `CP/INPUT1099.md` 1548316a…, `CP/VSL_OFFLINE.md` 6cca0baa…, `CH/R_MECH.md` 2fc879d6…, `CH/TAKEOVER_PLAN.md` r2 b75ad041…, `CH/b0/B0.md` r2 11fa7578…, `RC/METER_CAUSE.md` r2 0b4036c6…, `N/METER_NEXT2.md` r2 acebbe73…, `N/K9_3_DESIGN_DRAFT.md` r2 549f20e2…, `KB/K9_2_DESIGN.md` r2 1100f7af…, `CH/B_RESULTS.md` r2 152a2f6f…, `CH/VERIFY_B.md` f2851f8b….
- 이 작업은 **설계 문서만** 씁니다. 코드 변경·커밋·푸시·동결·재생·VISSIM·COM·러너 0. 런 자료(FZP·결정 JSON·readback) 새 분석 0 — 숫자는 위 문서에서 옮김.
- [실행] 05:5x–06:16 읽기만 한 것(밝힘): (1) `git -C GWT8 show c20aff1d:` 로 sdmpc.py·physical_ramp_branches.py·lane_plant_runtime.py·runtime_setup.py·control_area_objective.py·sdmpc_sequence.py·lane_ramp_runtime.py·config_n31_v2.json 을 `CP/c1d/ou_*` 로 복사(읽기 사본, GWT8 쓰기 0, 체크아웃 0), `git grep`. (2) codex 쪽은 `D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff` 와 FRZ_B1 를 읽기만(sdmpc.py·PRB·LPR·USG sha 가 두 트리에서 같음 확인). (3) 설정 파일(FRZ_B1 `config_b0_v3c3.json` 729640af…, Ω701 membership 9bb740b3…, `B0_REPIN_RECEIPT.json`)을 python 한 줄로 읽어 키·링크 집합만 셈 — 런 결과 자료가 아니라 설정·증거 파일이라 규칙 고정 없이 셈(밝힘). (4) `diff --strip-trailing-cr` 우리/codex sdmpc.py → `CP/c1d/diff_sdmpc.txt`. (5) `du -sh` B·V-A v3c3-s31 런 폴더 크기(읽기만).
- [실행] 디스크 C 27 GB, D 223 GB. PC VISSIM 0, python 0 (06:16).

## 2026-10-27 06:32 KST — c1 설계 초안 마감 (C1_DESIGN_DRAFT.md r0)
- 줄임(06:17 항목 보충): CH = `SP/codex_handoff`, RC = `SP/rmcause`, N = `RC/r2c_n`, KB = `SP/k92/bundle1`.
- **산출: `CP/C1_DESIGN_DRAFT.md` sha256 c7108585b69122ca6d92352fb7e73c8c65c3d2a27ca978f311786a4afc76861a** (+ `C1_DESIGN_DRAFT.md.sha256`).
- 읽기 사본 `CP/c1d/` sha256: ou_sdmpc.py 352701a0… · ou_physical_ramp_branches.py 08cb370d… · ou_lane_plant_runtime.py 493a5bf2… · ou_runtime_setup.py 70cca680… · ou_control_area_objective.py 2c21cd8c… · ou_sdmpc_sequence.py d96a611c… · ou_lane_ramp_runtime.py 9fb59951… · ou_config_n31_v2.json c8e3ee2c… · diff_sdmpc.txt 2858d1a4….
- 요지: 묶음 1 = Ω701(66링크) + 이웃 검사·조합 + cap 3 + 녹색 0 금지 + 저장 보호 0.9(+ 운영 seed·held 유지) + FW_E 4미터 머리 표. 1099 항은 미터 기구에서 오지 않았으므로(INPUT1099) FW_W 입구 장치 대신 SG2 오프라인 대조·폐루프 사슬 줄을 권함(⟨Q2⟩·⟨Q3⟩). 충돌 하나 확인: codex 머리 표 g9 = g10 이 우리 K3 정규화(OU PRB:75-77)에서 ValueError → ⟨Q4⟩. 키 켬 재생은 정책 토큰 때문에 T=900 단일 + 연쇄 재생만(OU SD:527-528). 결정 거리 ⟨Q1⟩–⟨Q19⟩.
- 데이터 뒤 선언: 설계 전체. 실행할 새 분석 없음(규칙·도구 sha 고정은 보충 C1 단계에서).
- 지킨 것: 코드 변경·커밋·푸시·동결·재생·plant 잡·VISSIM·COM·러너 0, kill 0, GWT8·런 폴더·동결 트리·인계 사본·Y: 쓰기 0(GWT8 은 `git show`/`git grep` 읽기만), sealed/·봉인 시드 자료 0, codex 64cf-s59/s61/s67 숫자 0, 금지 시험 0. COMPARE_RULE_B·PINS_B 그대로. 끝에 PC VISSIM 0, python 0 (06:32). 디스크 C 27 GB, D 223 GB.

## 2026-10-27 06:35 KST — C 준비 결과 종합 시작 (C_PREP_RESULTS.md)
- 무엇: READBACK_METER.md(2fd9863934f93d09341e84df45f7c67cc404e0c4e97dcb85ed1ec465bbd7f980)·INPUT1099.md(1548316a36b5647ee2a0132af9814d91c5c25d0be1d489a170170b65c3e31285)·VSL_OFFLINE.md(6cca0baa715f4d0bb870bd5f7e2c2c05279bc168048961c106f95b430ba9debf)·C1_DESIGN_DRAFT.md(c7108585b69122ca6d92352fb7e73c8c65c3d2a27ca978f311786a4afc76861a) 네 문서를 읽어 한국어 종합 C_PREP_RESULTS.md 를 씀 [실행 sha256sum].
- 이 작업은 **새 분석 없음**(문서 종합만). 숫자는 네 문서에서 file:line 으로 옮김. 런 자료(FZP·결정 JSON·readback)·재생·plant 잡·VISSIM·COM·러너·동결·커밋·푸시 0. 그래서 새 규칙·도구 sha 고정 없음. 종합 자체가 B 결과를 본 뒤의 일이라 '데이터 뒤 종합' 으로 밝힘.
- 디스크 C 27 GB, D 223 GB (8 GB 문턱 위) [실행 df].

## 2026-10-27 06:39 KST — C 준비 결과 종합 마감 (C_PREP_RESULTS.md r0)
- **산출: `CP/C_PREP_RESULTS.md` sha256 c51fe7f77b42a6ebe1d52e6c49c9842c15ee801cc4c41678caa8a5bbdf77102e** (+ `C_PREP_RESULTS.md.sha256`).
- 요지: (1) readback — B 세 시드 미터 8 × 810 주기 녹색 초 = 명령(어긋남 0), g2 방류 1대/주기/차로, VISSIM ÷ 우리 표 1.20–1.48(13/14칸), ÷ codex 머리 곡선 0.89–1.09(12/13칸). (2) 1099 — 미터 아닌 SC1001 EBT 녹색 단축 사슬(v3c3-s31·s41 받침, s43 잡음 크기). (3) VSL — plant(64cf-s29 기록, 다른 망, 한 시드)는 100·90 에 대체로 비용 증가, 붕괴·방류 감소 없음, 풀이기 비대칭. (4) C 묶음 1 = Ω701 + 미터 결정 묶음(초안 그대로).
- 결정 목록: 초안 ⟨Q1⟩–⟨Q19⟩ + 새 ⟨Q20⟩(B 저장 보호 10639 읽기) ⟨Q21⟩(B SG2 단축 까닭 읽기·NC3 노랑) ⟨Q22⟩(plant 사슬 표현 읽기) ⟨Q23⟩(VSL O1·O2 먼저, R1 따로) ⟨Q24⟩(3,625.8 m 정정 메모) ⟨Q25⟩(입구 처리량 → 망 묶음) ⟨Q26⟩(머리 곡선 출처). 새 것은 모두 데이터 뒤, 돌리기 전 규칙·도구 sha 고정.
- 새 분석 0(덧셈·개수 세기 두 칸만 [계산]). VISSIM·COM·러너·재생·plant 잡·동결·커밋·푸시·kill 0. GWT8·런 폴더·동결 트리·인계 사본·Y: 쓰기 0. sealed/·봉인 시드 자료 0, codex 64cf 다른 시드 숫자 0, 금지 시험 0. COMPARE_RULE_B·PINS_B 그대로.

## 2026-10-27 06:58 KST — 독립 재검 시작·규칙·도구 고정 (VERIFY_C_PREP, 데이터 뒤 선언)
- 무엇: C_PREP_RESULTS(c51fe7f7…)·READBACK_METER(2fd98639…)·INPUT1099(1548316a…)·VSL_OFFLINE(6cca0baa…)·C1_DESIGN_DRAFT(c7108585…) 를 새 도구로 다시 셈(저자 도구 재사용 0). 줄임 VC = `CP/verify_c`.
- **데이터 뒤 선언**: B 결과와 다섯 문서를 읽은 뒤 정함. 규칙 쓰기 전 본 것(밝힘): B v3c3-s41 readback·명령 CSV 머리와 SC1001 줄, B v3c3-s41 `.lsa` 머리·SC1001·9105 줄, B v3c3-s43 FZP 머리·시각 소수부 분포(awk, 모두 .10), NC3 SC1001 `.sig` prog 1, A1 1,800 s 결정 JSON 키 이름 구조(값 아님, vc_probe_keys*.py 세션 안), 코드·설정 인용 줄 일부. COMPARE_RULE_B·PINS_B 그대로.
- 규칙 `VC/VC_RULE.md` 9c5df55769344b362af0fd69530ff8ca4a28f8061ff355db71bb4ff39ef7c5c0.
- 도구 sha256 (`VC/PINS_VC.sha256` e7574b653278ad7ce1bdbd697de518b03e94a9b97fb0167d4d6760a7640cf81f):
  - 89f7845741ef309b79646c26b34444f4332e1d111f35e0cba7b09e885fcbac99 vc_readback.py (V1·V2, 가벼움, 세션 안)
  - 05a4127c57e987a65972e4be59896e70ef6de127784280acd28672759b4fd199 vc_fzp1099.py (V3 FZP 여섯, WMI)
  - 22e3adce1278bca6786597b9038ff2a9199d3c5288aa58051efd2e987c5eae2c vc_report1099.py (V3 표, 가벼움)
  - f1e61e79d67de21b51322c031dd63b94cb141ee240f64cf6da539c66bbd39606 vc_vsl_json.py (V4, WMI)
  - e52fa195e5c513143bcaa4e034801041133c6b5f68f6a34b0c5e4fb04e1d3714 vc_refs.py (V5, 가벼움)
  - 108521d06615ff732d761c6e34e8c236300058da47a7f12b0c00b4a752ce9197 vc_launch.ps1 (WMI·BELOW_NORMAL·env_hsw·PYTHONHASHSEED=0·python -B·스레드 1, c_port python 이 돌면 거부)
  - 구조 확인만: vc_probe_keys.py 49c942e5… · vc_probe_keys2.py 292f1a0c… · vc_probe_keys3.py 668960ca… · vc_probe_keys4.py 8af325ef… (분석 숫자로 쓰지 않음)
- [실행] 디스크 C 27 GB, D 223 GB. PC python·VISSIM 0 (06:50 확인).

## 2026-10-27 07:06 KST — 재검 덧붙임 V6 고정 (미터 머리 방류 재셈, 데이터 뒤 두 겹)
- 까닭: V1–V5 결과(readback·1099·VSL·코드 참조)를 본 뒤, M5(머리 서비스 표) 근거인 READBACK K7 "g2 = 주기당 1대" 와 10681 차로 2 녹색별 방류를 다른 정의로 한 번 더 봄. **데이터 뒤 선언(두 겹)**.
- 규칙 V6: B v3c3-s43 FZP 한 개. 150 s 결정 구간(900–9,000 s, 54개)마다 미터 커넥터 10639·10681(차로 1·2)·10484·10490·10480 의 머리(inpx signalHead pos) 넘음 수를 차로별로 셈(직전 프레임 머리 앞 → 지금 머리 뒤 또는 커넥터 떠남). 내 대기 표지: 구간 30 프레임 모두 머리 앞 30 m 안에 5 km/h 미만 차가 있음. 막힘 표지: 머리 뒤 30 m 안 5 km/h 미만 차가 한 프레임이라도 있음. "대기·막힘 없음" 구간의 넘음 수를 녹색별로 냄. N34 정의와 다르므로 비교는 꼴(주기당 대수)만.
- 도구 verify_c/tools/vc_meterhead.py 0776446d3c338f20b9c969d87f88e9a31b14d0e3d5d0a34c452cc6ecc897de9a (WMI, vc_launch.ps1 그대로).

## 2026-10-27 07:11 KST — 독립 재검 마감 (VERIFY_C_PREP.md r0)
- **산출: `CP/VERIFY_C_PREP.md` sha256 c83130bb4200f417e236be9799f1bb8ece68bacd61c666b58ad9d7306a44a004** (+ `.sha256`). 출력 sha 목록 `VC/OUT_VC.sha256` f6b4c4849e68511507f967894a33de82ccb5103edc0573b3f70bf5f3d092b1a3, 핀 마감판 `VC/PINS_VC.sha256` 90f87d8be23ca7f9fcfa808bb32223cfa8367aa4b8502d4ce92f7d9440d7c15d (`sha256sum -c` 12/12 OK).
- [실행] 요지: readback(B v3c3-s43 주, s31·s41 덤) 6,480/6,480 주기·행·쓰기·분포 모두 같음. 1099 사슬 숫자(v3c3-s31·s43 × B·NC3·V-A) 모두 다시 나옴(④b 1099 +490.05 / +84.03 등). VSL 결정 JSON 숫자 모두 같음. 설계 초안 file:line 74곳 맞음, Ω701 66 = 35 + 31.
- 틀림: NC3 SC1001 녹색이 노랑 포함 꼴(SG2 576·SG5 324·전체 2,592) — 같은 GREEN 만 꼴은 540·288·2,430 (B v3c3-s41 .lsa 로 노랑 45–48 s 확인). "1/45" → 약 1/4.5. 작은 부정확 셋(팩 문서 8개 sha, adapter 차이 다섯, "이웃 검사만"). 하중 걸린 결론·권고는 바뀌지 않음.
- 시각 밝힘: 06:58 항목 머리와 VC_RULE 머리의 "06:58" 은 어림, 실제 고정 06:56:06(규칙)·첫 발사 06:56:39. 07:06 항목은 실제 07:05:14–07:05:28 고정, 07:05:35 발사. 모든 고정이 실행보다 앞섬.
- 지킨 것: VISSIM·COM·러너·재생·plant 잡·동결·커밋·푸시·kill 0. 런 폴더·CX·FRZ·GWT8(읽기만)·인계 사본·Y: 쓰기 0. sealed/·봉인 시드 자료 0, codex 64cf 다른 시드 숫자 0, 금지 시험 0. COMPARE_RULE_B·PINS_B 그대로. 끝에 우리 python 0. 디스크 C 27 GB, D 223 GB.

## 2026-10-27 07:16 KST — C 준비 문서 마감 시작 (VERIFY_C_PREP 고칠 글 반영)
- 무엇: `CP/VERIFY_C_PREP.md`(c83130bb4200f417e236be9799f1bb8ece68bacd61c666b58ad9d7306a44a004) §8 고칠 글 표와 본문 §1–§7 의 보완을 C_PREP_RESULTS(c51fe7f7…)·INPUT1099(1548316a…)·VSL_OFFLINE(6cca0baa…)·C1_DESIGN_DRAFT(c7108585…)에 넣음. READBACK_METER(2fd98639…)는 재검이 고칠 글을 내지 않아 그대로 둠.
- 앞 판은 `<이름>_r1.md` 사본으로 남김("직전 판 = _r1" 관례, K9_3_DESIGN_DRAFT r2 와 같음). 새 판 머리는 r2.
- **새 분석 0**: 고친 값은 모두 VERIFY_C_PREP 의 [실행]·[계산] 값을 옮김. 새 규칙·도구 sha 고정 없음(실행할 것이 없음). COMPARE_RULE_B·PINS_B·W1099_RULE*(핀 sha) 그대로 — W1099_RULE_ADD1 망 줄의 노랑 위치는 INPUT1099 r2 와 변경 기록에서 고침.
- 줄 번호: INPUT1099·VSL_OFFLINE·C1_DESIGN_DRAFT 는 본문 줄 수를 바꾸지 않고(줄 안에서만 고침) 변경 기록만 끝에 더함 → C_PREP_RESULTS·VERIFY_C_PREP 의 file:line 인용이 그대로 맞게 함.
- [실행] 디스크 C 27 GB, D 223 GB (8 GB 문턱 위).

## 2026-10-27 07:24 KST — C 준비 문서 마감 (r2: VERIFY_C_PREP 고칠 글 반영)
- **산출 (r2)**: `CP/C_PREP_RESULTS.md` 4b58fb4e09a72a826c86975bccfcdb5ed2f67848b3e5c2556c64c6179c51c3ca · `CP/INPUT1099.md` c89011d8d1d7b3a45fea46f2622d87930e6f0e361969e4dae219e418b6d54274 · `CP/VSL_OFFLINE.md` a8ff255ecf5b20717c16b7c6bbb45e388810fa3d8bef47ef23e686a759a5d0ba · `CP/C1_DESIGN_DRAFT.md`(초안 r2) c32e1006a2a2c4084af9f77b615739dc51a6fb8a7768207f40bf461f742c2816 (+ 각 `.sha256`). READBACK_METER 는 그대로 2fd98639….
- **앞 판 사본**: `C_PREP_RESULTS_r1.md` c51fe7f7… · `INPUT1099_r1.md` 1548316a… · `VSL_OFFLINE_r1.md` 6cca0baa… · `C1_DESIGN_DRAFT_r1.md` c7108585… (+ `.sha256`).
- 반영(VC §8 전부 + 보완): NC3 SC1001 GREEN 만 꼴(SG2 540·SG5 288·900–9,000 s 2,430, B − NC3 SG2 −134 / −131 / −28 s, SG5 +130 / +200 / +194 s, V-A − NC3 SG2 +38 / +98 / +140 s), 노랑 위치(SG2 45–48 s·SG5 72–75 s) 답, "+0.1017 = 문턱 약 1/4.5", 팩 문서 7개 이름·1개 옛 소속 4863f5ee…, adapter 차이 다섯, "이웃 검사만" 표현, 0 넣기 프레임 창 ±1, v3c3-s43 출발점 근거 약함, 이웃 후보 10개는 저장 보호 안 걸린 상태만(G-K2 (a) 조건), 머리 비 g2 만 독립 근거, A1 3,600 부호 가정, VSL 기울기 행 수 꼴(8,100 s 뺌). 틀린 값은 본문에 남기지 않고 변경 기록 표에만 적음.
- 핀 파일 그대로: `w1099/W1099_RULE_ADD1.md` fd70dfde…(망 줄 노랑 위치는 INPUT1099 r2:44 가 고침), COMPARE_RULE_B·PINS_B·PINS_W1099·PINS_VC. w1099 출력 `sc_readback.json` `/nc3_sig/1001` 등 NC3 노랑 포함 값도 바꾸지 않음(INPUT1099 r2:146, :238 에 밝힘).
- 줄 번호: IN 238·VS 291·CD 561 본문 줄 수 유지 확인(sed 로 인용 줄 34곳 대조), 변경 기록만 끝에 더함.
- 사본: `D:/VISSIM_runs/20261001_v3c3/reports/k8/c_port/` 에 c_port 트리 전체(226파일 + LOG) 복사, LOG 뺀 226파일 sha256 대조 모두 OK [실행 sha256sum -c].
- 새 분석·새 규칙·새 도구 0, VISSIM·COM·러너·재생·plant 잡·동결·커밋·푸시·kill 0. 런 폴더·CX·FRZ·GWT8·인계 사본·Y: 쓰기 0(D: 쓰기는 reports/k8/c_port 뿐). sealed/·봉인 시드 자료 0, codex 64cf 다른 시드 숫자 0, 금지 시험 0. 디스크 C 26 GB, D 223 GB.
