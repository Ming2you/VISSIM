# K9-2 묶음 1 관문 보고 (Gates, 2026-10-21) — STOP: F 단계의 보고용 지속성 기준 계산에서 멈춤

- 상태: **STOP**. 판정 단계 k92t를 시작했고, 시작 훑기·J-0·J-a·J 잡 벽시계 짝은 모두 PASS입니다. F 단계에서 판정기를 부르기 전에, 보고만 하는 "지속성(persistence)" VISSIM 기준 계산이 rc=1로 끝났습니다. 미리 고정한 구동기 규칙(O7: 단계 안의 실행이 rc≠0이면 STOP)대로 멈췄습니다. F 판정 값·J-b·사후 단계는 계산하지 않았습니다. 사용자 결정이 필요합니다(§5).
- 이 보고는 판정 말을 쓰지 않습니다. 결과는 PASS / FAIL / 보류 / INCOMPLETE / STOP과 숫자로만 적습니다. 교통 성능 판정이 아닙니다.
- 표시: [실행] 이번에 돌리거나 계산함, [읽음] 문서·코드·기록에서 확인, [추론] 시험하지 않은 판단.

## 줄임말 (처음 한 번)

- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`. KB = `SP/k92/bundle1`. KT = `KB/k92t`(이번 구동기·판정기). KI = `KB/impl`.
- OK2 = `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1`. OUTK = `OK2/k92t`(판정 단계 출력 뿌리). V4 = `D:/VISSIM-merge/k8_gates_out_v4`(K9-1 판정 산출, 읽기만).
- GWT8 = `D:/VISSIM-merge/sim3-n31-k8`. TREE = `D:/VISSIM-merge/k8_gate_trees/k92b1/a27/k92t`(git archive K9-2-5 `e27ceac8`).
- k92t = 보충 24 §5의 판정 단계. J = K9-1 판정 상태 불변 관문(J-0 정적, J-a 기준 확인, J-b 판정 잎). F = 충실도 관문(NC = 무제어 런 전용).
- SAF-K91 = K9-1 판정 팔 튜닝(`5f0d0e40…`). SAF-K92b1 = SAF-K91 + 두 키(W·H-b, `65cac7ea…`). BASE = K9-1 BASE 튜닝(`319d07aa…`).
- W = SC109 서측 직진 용량 키(값 5209.8). H-b = (173, p4) 좌회전 헤드 하한 씨앗 키(1045.1612903225805).
- VR = VISSIM 기준 도구 `k92_vissim_ref.py`(`f3fcc574…`). FZP = VISSIM 차량 궤적 파일.

## 보고서 머리에 옮겨 적는 공개 (보충 24 §2.6-6·-10, 보충 27 §8·§13, 보충 28 §9, 보충 29 §11)

1. W 값 5,209.8은 몫 가르기 결과를 본 뒤 고른 값입니다(D-K9-34). 몫 가르기에서 시험하지 않았습니다 [읽음 보충 24 §2.6-10].
2. F-3(좌회전)은 비블라인드 안전 문턱입니다. 설계 단계가 v3c3-s47 좌회전 자료를 읽었습니다 [읽음 보충 24 §2.6-6].
3. G-K2·G-K4는 처음에 HARD만으로 판정했고, 보충 27–29로 결과 넷(PASS = HARD 같음 + 미분류 0)·"모든 차이"로 다시 판정했습니다. 다시 판정은 결과를 짐작하는 상태의 판정입니다 [읽음 보충 27 §8].
4. G-K4 결정 W 4행은 RS 소스 sha 잎 하나만 좁게 허용했습니다(A28-W, D-K9-51) [읽음 보충 28].
5. G-K4 plant 4행의 원자료 재계산은 J·F 값 고정 뒤에 독립 검증기가 합니다(D-K9-55). 아직 하지 않았습니다 [읽음 보충 29 §5].
6. 기존 어댑터는 결정마다 봉인 시드·v3c3-s47 파일의 sha를 계산합니다(D-K9-44, 기록만). 이번 단계에서도 그대로입니다 [읽음 보충 25 §7].

## 한눈에

| 관문 | 정의 (요약) | 값 | 문턱 | 결과 |
|---|---|---|---|---|
| 커밋 관문 K9-2-0…3 (G-K0–G-K5 등) | 보충 24 §4.3–§4.4, 커밋마다 | 커밋별 단계 모두 PASS(§1) | 각 정의 | PASS (기록, 다시 돌리지 않음) |
| 판정기 고침 관문 K9-2-4·K9-2-5 + 다시 비교 | 보충 27–29 | R-old 184/184, RJ-G2 9/9, RJ-G4 12/12, rc_g2·rc_g4 같음 | 각 정의 | PASS (기록) |
| k92t 시작 훑기 | 보충 25 §6.5-3·4·5, 보충 24 §3.1-3b, S-K10 | 봉인 12,538파일 sha 다름 0, 새는 줄 0, s47 VISSIM 값 0, 주 표본 산출 이름 0 | 모두 0 | PASS |
| J-0 정적 | 보충 24 §5.2 | 105/105 상태 PASS, R-obs3 61 = 초기화 59 + 같은 실패 2 | 모든 상태 | PASS |
| J-a 기준 확인 | 보충 24 §5.2 | 23/23 항목 같음(잡 21 숫자 잎 다름 0, 결정 2 결과 넷 PASS) | 모두 같음 | PASS |
| J 잡 벽시계 짝 | 보충 24 §5.2 주, RG-6 | 깨끗한 짝 11/11, 중앙 비 0.98010 | ≤ 1.01575 | PASS (사분위 범위 0.0304, 보고만) |
| F (F-1·F-2·F-3) | 보충 24 §5.3 | 계산 안 함 | F-1·F-2 상대, F-3 ≤ +5대 | **INCOMPLETE (STOP, 판정기 전)** |
| J-b 판정 잎 | 보충 24 §5.2 | 돌리지 않음 | 판정 잎 repr 같음 | 돌리지 않음 |
| 사후(봉인 뿌리 기록 훑기) | 보충 25 §6.4, 보충 29 §5 | 돌리지 않음 | – | 돌리지 않음 |
| 독립 검증·D-K9-55·V-B | 보충 24 §5.4, 보충 29 §5, §14.1 | 이 단계 밖 | – | 하지 않음 |

## 1. 커밋 관문 (이미 끝난 기록, 다시 돌리지 않음) [읽음 판정 파일, 실행 sha256]

보충 24 §4.4는 관문을 커밋마다 정의합니다. 커밋 K9-2-0…3의 관문은 그 커밋 때 돌았고, 판정기 고침(K9-2-4·K9-2-5)과 다시 비교로 G-K2·G-K4를 다시 판정했습니다. 이 Gates 단계에서 다시 돌리지 않았습니다(같은 정의를 같은 바이트로 다시 돌릴 근거가 없음).

| 커밋·단계 | 정의 | 값 | 문턱 | 결과 | 판정 파일 (sha256) |
|---|---|---|---|---|---|
| K9-2-0 `1868b37c` | pre·trees·diff0·pycompile·selftest·J-b 계산기 자체 점검·U·G-K0 plant(P-a 26·P-b 17) | 9단계 모두 PASS | 각 정의 | PASS | `OK2/commit/K9-2-0/gates.json` `04a5f3161a9a77c44ccc8860e96d3c414f9e6909a80428353fa415f0b6374a16` |
| K9-2-1 `7ed49cdf` (W) | U·B(w)·G-K0(결정 79, plant)·G-K1(정적 79, 동적 26)·G-K2 (a)·(e)·G-K4·G-K5 | 12단계 PASS; G-K5 중앙 0.98999(짝 8/8, 사분위 0.0152 보고만) | G-K5 ≤ 1.01575 | PASS | `OK2/commit/K9-2-1/gates.json` `dbf644937010c510a7a2de7336246ae0c1b78219192033e3d548d0a20c98aa24` |
| K9-2-2 `2d5d95f0` (H-b) | 위 + G-K2 (b)(c)·G-K3 | 13단계 PASS; G-K5 중앙 0.99505(짝 8/8, 사분위 0.0096 보고만) | 같음 | PASS | `OK2/commit/K9-2-2/gates.json` `176dd263eb38b132e0b25ac18b86aa9ad73c5c65aa04c7f4f709f4a72f73420e` |
| K9-2-3 `b887f99f` (팔·문서) | G-K0(D-d·P-b)·G-K3·팔 동일성·`--check` | 6단계 PASS | 각 정의 | PASS | `OK2/commit/K9-2-3/gates.json` `064d1b4b62748d648e2379ace9cf89e5a0f210281724b77c01b59eb957906d71` |
| K9-2-4 `bfd609c0` (비교 규칙) | R0–R7(R6 R-old 184쌍) + RJ-G2(G-K2 9칸 다시 재생, 결과 넷) + RJ-G4(G-K4 12행, 모든 차이, A28-W) | 모두 PASS | 결과 넷 PASS | PASS | `OK2/a27/gates.json` `e57f1b3655b1f046820944cf0e55680a83d2f93b9f7f960f7d9e1acd3b8d2db6` |
| K9-2-5 `e27ceac8` (판정기 고침) | P0–P8 + rc_g2(9칸)·rc_g4(12행) 기존 출력 다시 비교 | 모두 PASS, 판정 변화 0 | 판정 = 기록 | PASS | `OK2/a29/gates.json` `129b642d4a53be61f520b26ac9a07f9d29a4de6ae74bdfc6b92eb498d9083f49` |

- G-K2는 D-K9-34로 다시 정의한 꼴(기준 팔 CWf·X1f, 값 5209.8)입니다. 5,700.6 대 몫 가르기 CW 동일성은 (e) 보고(Wu 4/4·Xu 같음)입니다 [읽음 LOG 2026-10-19·20 항목].
- 독립 검증 r1–r3이 이 기록들을 다시 냈고, r3은 결함 0입니다 [읽음 `KB/VERIFY_IMPL_r3.md` `c242792f…`].

## 2. 판정 단계 k92t [실행]

- 구동기 `KT/k92t.py` `b07ffb56789c30c8ef2f60f098ae7212fec52eec8a307b959bf26c44c6f02bec`, 판정기 `KT/k92t_judge.py` `eb4c113a6b7194cdf00d193d5faf07b426aae61a49ff84ae442bcf29b59fb28e`. 고정 목록 `KB/k92t_pins.sha256` `38a2ce147795bbe7613fa5b6633441b31b814e781d1948e550753db776ed7cdd`(56줄). 모두 첫 k92t 데이터 전에 LOG에 고정했고(LOG 2026-10-20 21:50 항목, 실제 발사 21:45:53), STOP 뒤에도 56/56 OK입니다.
- 트리 TREE = git archive `e27ceac8`, 10,569파일. K9-2-5 판정기 트리 `TK/a27/k925`와 바이트 같음(다름 0, 한쪽 0), 판정기 블롭 19/19(`OUT29/k925_blobs.json`), VR `f3fcc574…`, CR 짝 참(k91t `AAAAAA---X` 대 `AAAAAAAAAA`). 기록 `TK/a27/k92t.build.json`.
- 시작 기록 `OUTK/k92_judging_stage.json` `34e63a991451ef8c3f1be0ef6f4765f009abc19745fe7e546ffaeda43fd1aaa5`(2026-10-20 21:45:53, 보충 24·25…29 sha, head `e27ceac8`).
- 실행: WMI 분리 `KI/launch.ps1 -Tag k92t_chain`(PID 27432, BelowNormal, PYTHONHASHSEED=0, `python -B`), 한 번에 자식 하나. 단계마다 VISSIM 개수 0(전·후). 단계 기록 `OUTK/steps.jsonl` `7edd53c9…`(59줄), `OUTK/driver.log` `8140fd2f…`.

| 단계 | 정의 (요약) | 값 | 문턱 | 결과 | 경로 (sha256) |
|---|---|---|---|---|---|
| 시작 훑기 | 봉인 파일 sha 전수 대조(보충 25 §6.5-3·5), 새는 줄(§6.5-4 정규식), §3.1-3b(s47 K9-2 VISSIM 값), S-K10(주 표본 산출) | 봉인 K9-2-0 3,573·K9-2-1 4,072·K9-2-2 4,072·K9-2-3 821파일 = 목록, 다름·빠짐·더함 0, 실행 수 = 목록(5·9·9·3), a27 1파일; 새는 줄 0(선언 뿌리 29,325파일; 보고만 a27·a29 908파일 0); s47 VISSIM 값 0(JSON 29,988개, k92_vissim_ref.json 2개 모두 s47 없음); 주 표본 이름 0(1,204,993개) | 모두 0 | PASS | `OUTK/start/scans.json` `410fde88da1e97e0434d3df59f292a904ed87c153a17bb209ec918b7a074bfb8` (1,845 s) |
| J-0 정적 | TL3m 27 + DP 17 + R-obs3 61 포착, SAF-K91 대 SAF-K92b1: K8b·K9 메타 7개 같음, SA 초기 상태 같음, 용량 차이 = G-K1 정적 조건, G-EB-14 초기화 61/61 | 105/105 PASS; 61 = 초기화 59 + T=1·150 같은 실패 2; 좌회전 씨앗 묶임 7상태(ROBS61 300·450·600·750, TL3m s43 900, s47 900·1,200); 그 밖 capture.json 다른 잎 0; 한쪽 메타 = K9-2 키 셋뿐(103상태) | 모든 상태 | PASS | `OUTK/judge/j0.json` `24ee9d3b66d16618f9c6bc255bcabaecbcbaa2a653c985a9fb0315d68a85aab1` |
| J-a 기준 확인 | SAF-K91 TL3 s31 GRID9 H3 9잡 + 잡 종류×팔(SAF-K91·BASE) 한 상태씩 대 `V4/sa/jobs/k91t` | 잡 21개 숫자 잎 다름 0·한쪽 0(공통 7,730–142,350개), 결정 2개(full 2700 hooks SAF·BASE) 결과 넷 PASS(HARD 같음, 미분류 0; A_K92 2·R3-08 2 등), run.json objective·held_objective·CSV 같음 | 모두 같음 | PASS | `OUTK/judge/ja.json` `74806cb0683582bc20eccb68eb086363a0ac0e8d100d2c6c5d48436da14b4d5c` |
| J 잡 벽시계 짝 | J-a의 SAF-K91 H3 잡 11개 대 같은 라벨 SAF-K92b1 잡(바로 이어 돌림), 깨끗한 짝(VISSIM 개수 넷 0)만 | 깨끗한 짝 11/11, 중앙 비 0.9800955989161412, 사분위 범위 0.030372(보고만), 짝 비 0.948–1.035 | ≤ 1.05 / 1.033718118959995 = 1.01575 | PASS | `OUTK/judge/jwall.json` `1fb5c60454169b9f10014691a9fae9aa4697ac5bd26323e146149b6600fb615a` |
| F | 주 표본 v3c3-s47 22상태 × {OFF, W, B1}, H3 OBS; F-1 MAE_B1(M1) ≤ MAE_OFF, F-2 \|편향_B1(M2)\| ≤ \|편향_OFF\|, F-3 편향_B1(M3) − 편향_OFF ≤ +5대 | 포착 114/114·잡 114/114 ok(팔마다 38 = 22 + 둘째 표본 16), VR 주·둘째 표본 끝(sha만 봄), **보고용 지속성 VR rc=1** → 판정기 부르기 전 STOP | 22상태, 위 문턱 | **INCOMPLETE (STOP)** | `OUTK/STOP_f.json` `ebff59c96596baca6039647e3902b88881a45fe6227b7da438e99afe420d3f17` |
| J-b | `gates_k91t.json`의 G-EB-2…8·13·14 판정 잎(pass_ null 아님) 45개를 SAF-K92b1로 다시 계산해 repr 같음 | 돌리지 않음 | 45/45 같음 | – | – |
| 사후 | J·F 값 고정 뒤 봉인 뿌리 k92_record.json 훑기 | 돌리지 않음 | – | – | – |

- 스냅숏(읽기 전용 뿌리, 이름·크기·시각만): s24 `4bacbeed…`(시작 전), s25 `k92t_start`, s26 `k92t_after_ja`, s27 `k92t_stop_f` `fabe7d5ea11fabd6f65266d7d9365f480c8612d5b0ea08504523f4406a39ee73` — 모두 s02 대비 SAME [실행].
- 팔 바이트 [실행 `OUTK/stages/prep.json` `9ef3a7ed…`]: ja SAF `5f0d0e40…`·BASE `319d07aa…`, jb SAF `65cac7ea…`·BASE `319d07aa…`, f_off `5f0d0e40…`, f_w `d179f01d…`, f_b1 `65cac7ea…` = 선언 값. S3 닻 표 `s3_table_e27ceac86c01.json` `3cc8297a…`(rows 31, moved 26, searched 0 = K9-1 꼴).

## 3. STOP 내용 (F 단계)

- 무엇 [실행 `OUTK/logs/f_persist.log` 끝 줄, 실패 진단으로 엶 — 보충 25 §6.4 "k92t 안의 실패 진단 예외"]: `k92_vissim_ref.py --states 47:<T−450 22개>`가 첫 상태 T=600에서 `K92 VISSIM ref s47 T=600: window (600.1, 750.1) found 0 times for 1090201`로 SystemExit(rc=1). 파일 `OUTK/f_persist/sa/k92_vissim_ref.json`은 생기지 않았습니다.
- 이 계산의 자리: 보충 24 §5.3 "보고만" 항목인 M1 지속성 MAE(VISSIM의 T 시점 사슬 재고로 T+450을 예측)를 내려고, 구동기가 VR에 상태 T−450을 넣어 그 m1_T450(= 프레임 T+0.1)을 쓰게 했습니다(구동기 O5). 판정 항목 F-1·F-2·F-3에는 쓰이지 않습니다.
- 원인 [추론]: VR이 창 (T+0.1, T+150.1]을 U4 측정기(`k8b/u4` 사본)의 헤드 주기로 찾는데, T=600 창이 측정 범위에 없음(NC FZP 기록 시작 또는 측정기 주기 범위가 900 s 무렵부터일 가능성). 주 표본(1,050…8,400)·둘째 표본은 같은 도구로 끝났습니다(`f_vref` rc 0). 측정기 코드는 더 따지지 않았습니다.
- 처리: 미리 고정한 규칙 O7("단계 안의 실행이 rc≠0이면 STOP_<단계>.json, 다음 단계 없음, 다시 돌리지 않음")대로 멈췄습니다. 구동기를 고쳐 이어 가면 데이터 뒤 판정 도구 변경(S-K12)이므로 하지 않았습니다. F 판정기(`k92t_judge.py f`)도 부르지 않았습니다. 그래서 F 판정 값은 없고, J·F 값 고정 전 상태입니다(봉인 로그·봉인 데이터 파일은 그대로 닫혀 있음).
- 있는 F 데이터 [실행, 이름·개수·sha만]: `OUTK/f_off|f_w|f_b1/sa/jobs/k92t/` 각 38잡(summary ok 38/38, 구동기 줄로만 셈), 포착 각 38(실패 0), `OUTK/f_vref/sa/k92_vissim_ref.json` `09f9194b308703db4d1da87cc10e458fca85872fd1189ef5fda7b2bc8f3b601a`(내용은 열지 않음). 망 동일성 원래 sha 앞 16자는 VR 줄에 s47 `1895ca30542cd505`, s31 `3de889f0257d998b`, s43 `51478c397b3a2570`(보충 25 §3.3-9 기대 값과 같음).

## 4. 데이터 전에 정한 조작화 (구동기·판정기 머리말, 공개)

1. **J-0 "R-obs3 61/61 오류 0"**: K9-1 기록상 모든 팔이 ROBS61 T=1·150에서 같은 자리에서 실패합니다. 그래서 두 팔이 같은 실패(예외 줄 + 런타임 프레임 서명 같음, 보충 13 G-EB-14 규칙)면 "같은 실패"로 61에 셉니다. 실제 값 = 초기화 59 + 같은 실패 2. 글자 그대로 읽으면 어느 팔이든 반드시 FAIL인 자리입니다.
2. **J-0 SA 초기 상태**: install_check(구성원)·stopline_approach_initial(통과 뒤 차량 수 포함)·probes.sa·ports·records·provenance['127']·occupancy['SC1001_W_out']의 바이트 같음.
3. **J-a 상태 고르기**(선택이 열린 곳은 첫 상태): TL3m = s43·s47의 900, c11 = C11 변형 900, tan = 900, 장기 = 2700 H42·4950 H27(OBS), "DP 훅 한 결정" = full 2700 hooks 결정. 결정 항목은 보충 29 §6.1-3대로 `k92_compare` 결과 넷(옛 뿌리 = `k8_gate_trees/k91t`), 잡 항목은 summary 숫자 잎(G5 제외 규칙).
4. **J 잡 벽시계 짝**: J-a SAF-K91 H3 잡 11개와 같은 라벨 SAF-K92b1 잡을 바로 이어 돌림(짝 사이 시간 차를 줄이려고).
5. **J-b(아직 안 돎)**: BASE 산출은 k91t 복사, 단 한 코드 트리 안에서 비교되는 BASE 실행(ROBS61 T=1·150 셋 시드, TL3·T9C 2700, full BASE hooks 2700·4950)은 TREE에서 다시 돌림. 예외 줄에 코드 트리 경로가 들어가 k91t 사본과는 같은 실패 판정이 성립하지 않기 때문입니다 [실행 V4 기록 확인]. SAG는 k91t 복사.
6. **F를 J-b보다 먼저**: 보충 24 §5.1은 어느 쪽이 먼저여도 됩니다.
7. **봉인 뿌리 k92_record.json 훑기는 J·F 값 고정 뒤**: 보충 25 §8.2는 시작 훑기에 넣었지만, 보충 29 §5가 그 전에 봉인 데이터 파일을 여는 일을 막습니다. 시작 때는 봉인 파일 sha 전수 대조로 바이트가 커밋 관문 때와 같음을 보였습니다.
8. **VISSIM 쪽 입력**(vissim_ref.json, fzp, opt1v2, R-obs 유효성)은 V4의 K9-1 입력 바이트 사본.
9. **지속성 보고(이번 STOP 자리)**: VR 상태 T−450으로 VISSIM M1(T)를 얻음 — T=600 같은 이른 상태에서 VR이 창을 못 찾는 경우를 미리 보지 못했습니다(내 설계 결함, 데이터 전 시험에서 빠짐).

## 5. 사용자 결정이 필요한 것

- Q1 이어 가는 방법(선택지; 어느 것이든 새 보충으로 선언·고정한 뒤):
  - (가) **지속성 보고를 바꾸고 F 판정부터 이어 하기**: 지속성 VR을 T−450 ≥ 900인 상태만으로 좁히거나(또는 보고에서 빼고) 그 실행 실패를 STOP 아닌 보고로 바꾼 구동기를 다시 고정 → 이미 있는 F 데이터(잡 114, `f_vref`)로 F 판정기 → J-b → 사후. F 판정 정의·문턱·표본은 바꾸지 않음. 비용: J-b 약 12시간 + F 판정 수 분.
  - (나) (가)와 같되 F 단계를 처음부터 다시 돌림(데이터 재사용 없음). 비용 +약 3.5시간.
  - (다) 지속성 보고를 VR 대신 FZP 프레임 T+0.1 링크 대수만 세는 새 도구로 냄(새 도구 고정 필요).
- Q2 이번 조작화 1·5·7(§4)을 받아들일지: 데이터 전에 정해 공개했지만 보충 글자와 다르게 읽은 자리입니다.

## 6. 지킨 것 [실행]

- VISSIM·COM·러너·동결 0. 단계마다 VISSIM 개수 0. 커밋·브랜치·푸시 0: GWT8 head `e27ceac8`, `b9734abe..HEAD` 6커밋, status 0줄, K8 브랜치 `b9734abe`, 원격 k92 참조 0.
- 봉인 시드 37/59/61/67 열지 않음. codex 64cf 숫자 0. 봉인 로그·봉인 데이터 파일 열지 않음(sha만). v3c3-s47 결과 값(F 잡 summary·k92_record·`f_vref` 내용)은 열지 않았습니다. 실패 진단으로 `f_persist.log` 끝 줄 하나만 읽었습니다.
- 읽기 전용 뿌리(동결본, RR, RO, NC3, k92attrib, DA, V4, OUTH) 쓰기 0: 스냅숏 s24–s27 모두 s02 대비 SAME. `k8_gate_trees/k91t`는 BASE 튜닝 사본·CR 형태·옛 뿌리로 읽기만 했습니다.
- 금지 시험 0. 이번에 시험을 돌리지 않았습니다(4c 단위 시험은 J-b 안이라 아직 안 돎).
- 내 PID만 썼고 끈 프로세스 0. 끝에 python·VISSIM 0. C: 38 GB, D: 396 GB.
- 고정 목록 `KB/k92t_pins.sha256` 56/56 OK(STOP 뒤 다시 확인).

## 7. 파일

| 파일 | sha256 |
|---|---|
| `KT/k92t.py` | `b07ffb56789c30c8ef2f60f098ae7212fec52eec8a307b959bf26c44c6f02bec` |
| `KT/k92t_judge.py` | `eb4c113a6b7194cdf00d193d5faf07b426aae61a49ff84ae442bcf29b59fb28e` |
| `KB/k92t_pins.sha256` | `38a2ce147795bbe7613fa5b6633441b31b814e781d1948e550753db776ed7cdd` |
| `KT/out/pre.json`·`tree.json`, `TK/a27/k92t.build.json` | 고정 목록에 있음 |
| `KT/dev/devtest.py` / `devtest_out.json` / `scans_dry.json` (데이터 전 점검) | `5886cd63…` / `6529c07d…` / `bee28996…` |
| `OUTK/k92_judging_stage.json` | `34e63a991451ef8c3f1be0ef6f4765f009abc19745fe7e546ffaeda43fd1aaa5` |
| `OUTK/start/scans.json` | `410fde88da1e97e0434d3df59f292a904ed87c153a17bb209ec918b7a074bfb8` |
| `OUTK/judge/j0.json` | `24ee9d3b66d16618f9c6bc255bcabaecbcbaa2a653c985a9fb0315d68a85aab1` |
| `OUTK/judge/ja.json` | `74806cb0683582bc20eccb68eb086363a0ac0e8d100d2c6c5d48436da14b4d5c` |
| `OUTK/judge/jwall.json` | `1fb5c60454169b9f10014691a9fae9aa4697ac5bd26323e146149b6600fb615a` |
| `OUTK/STOP_f.json` | `ebff59c96596baca6039647e3902b88881a45fe6227b7da438e99afe420d3f17` |
| `OUTK/f_vref/sa/k92_vissim_ref.json` (열지 않음) | `09f9194b308703db4d1da87cc10e458fca85872fd1189ef5fda7b2bc8f3b601a` |
| `OUTK/stages/{start,prep,j0,ja}.json` | `f3ed1dce…` / `9ef3a7ed…` / `3845def6…` / `b40593bb…` |
| `OK2/snap/s27_k92t_stop_f.json` | `fabe7d5ea11fabd6f65266d7d9365f480c8612d5b0ea08504523f4406a39ee73` |
| 이 보고서 사본 | `OK2/GATES_K92B1.md` (같은 바이트) |

## 8. 덧붙임 (2026-10-21 23:4x KST, Gates A30): 보충 30으로 이어 한 결과 — STOP (사후 단계 S-K10)

- 이 절 덧붙임 전 이 파일 sha256 `63dd35e29ced298c9e7538f0aeefe7e48871e6197285b3994fa2e51683a03b60`(보충 30 §0 값). 위 §1–§7은 바꾸지 않았습니다. 자세한 보고는 `KB/GATES_K92B1_A30.md` sha256 `167e9e188c1053b89f814080b258e89238901126f153d2753bcdb0ab271f3556`(사본 `OK2/GATES_K92B1_A30.md` 같은 바이트)입니다.
- 사용자 결정 D-K9-56·57(결정 기록 `eae2e6fa…`)과 보충 30 고정판(`ba556227…`, 고정점 `ad3fafad…`)대로, 새 구동기 `KB/a30decl/k92t30.py`(`8f28171e…`)·새 판정기 `k92t30_judge.py`(`a1937942…`)를 `KB/a30_pins.sha256`(`7afabd03…`, 83/83 OK)로 다시 고정한 뒤 `chain30` 하나를 WMI 분리로 돌렸습니다(10-21 11:59:03 – 23:34:09) [실행].

| 단계 | 값 | 결과 |
|---|---|---|
| check30 (C1–C15, 39점검) | 거짓 0, OUTK 18,019파일 다름 0 | PASS |
| seal30 (F 잡 로그 셋 → `OK2/sealed_s47/k92t/logs/`) | 크기·sha 같음 3/3, 원래 자리 없음 | PASS |
| F 잡 정상 셈 (요약·기록·포착 파일) | 3팔 × {s47 22, s31 8, s43 8} 모든 칸 = 계획 수 | PASS |
| 지속성 보고 (보고 전용) | 21상태 측정, T=1,050 측정 불가(T_FROM=900), MAE 〔가림: 봉인·블라인드 시드 값〕, 겹침 15/15, `complete` 참 | 보고 (완전) |
| F (F-1·F-2·F-3, n 22) | MAE_B1(M1) 〔가림: 봉인·블라인드 시드 값〕 ≤ MAE_OFF 〔가림: 봉인·블라인드 시드 값〕; \|편향_B1(M2)\| 〔가림: 봉인·블라인드 시드 값〕 ≤ 〔가림: 봉인·블라인드 시드 값〕; 편향_B1(M3) − 편향_OFF = 〔가림: 봉인·블라인드 시드 값〕 ≤ +5 | PASS (`judge/f.json` `04cfa2e0…`) |
| J-b (판정 잎 45) | 같음 45, 다름 0 | PASS (`judge/jb.json` `f8a273ef…`) |
| `jb_unit` (J-b 안 단위 시험) | rc=1, 2 failed / 95 passed (ConfigFlagTests 둘; 판정 단위 항목 밖; 원인은 K8-7 뒤 `config_n31_v2.json` = `d0f9ef39…` 대 k91t `319d07aa…`) | 보충 30 §5.3 글과 어긋남 — 사용자 결정 필요 |
| post30 봉인 뿌리 기록 훑기 | 기록 134, s47로 셈 134, bad 89 | **STOP (S-K10)** (`STOP_a30_post.json` `8fa75243…`) |

- STOP 진단(J·F 값 고정 뒤, 값 출력 0) [실행·읽음]: bad 89는 정확히 v3c3-s31(42)·s43(47) 기록입니다. 판정기 `_seed47_path`가 봉인 뿌리 이름 `sealed_s47`을 s47 조각으로 읽어(`k92t30_judge.py:303-305`, `:359-371`) 봉인 아래 모든 기록을 s47로 셌습니다. 실제 v3c3-s47 기록 45개는 모두 `vissim` null·`k92_blind_s47`입니다. 판정기를 데이터 뒤 고치면 S-K12이므로 고치지 않았습니다.
- 스냅숏 s29–s32·끝 확인 s34 모두 s02 대비 SAME. GWT8 head `e27ceac8`, status 0줄, 6커밋, 푸시 0. G-K4 plant 원자료 재계산·독립 검증·V-B·V-A는 하지 않았습니다(보충 30 §6 순서 밖).
- 사용자 결정 필요: Q1 post STOP 처리(새 보충으로 훑기 규칙을 바로 적고 그 훑기만 다시 / 진단을 공개 기록으로 받아들임 / 그 밖), Q2 `jb_unit` rc=1을 보충 30 §5.3 글대로 STOP으로 볼지, Q3 독립 검증·G-K4 plant 재계산 시점(post30이 STOP으로 끝남).

## 9. 덧붙임 (2026-10-22 03:16 KST, Gates A31): 보충 31로 이어 한 결과 — 사슬 PASS (scan31·unit31)

- 이 절 덧붙임 전 이 파일 sha256 `3f3a069a68123f7b273d8ae2dc4c14c6be57b2aa8865d38fc975f10ab8ee7e8b`(보충 31 §0 값, `KB/a31_pins.sha256` 127줄). 위 §1–§8은 바꾸지 않았습니다. 자세한 보고는 `KB/GATES_K92B1_A31.md` sha256 `e2b301837feb35d652d0db088d634e07449676abd01cb0e8b2dfef6eff232885`(사본 `OK2/GATES_K92B1_A31.md` 같은 바이트)입니다.
- 사용자 결정 D-K9-58·59(결정 기록 `09974cfc…`)와 보충 31 고정판(`8541ccb7…`, 고정점 `605ccbd2…`)대로, 새 구동기 `KB/a31decl/k92t31.py`(`63b5aa22…`)·새 판정기 `k92t31_judge.py`(`9dfc0b20…`; 보충 30 판정기에서 `_seed47_path` 한 함수만 바꿈, 데이터 뒤 고침 — 사용자 결정)·jb_unit 비교기 `k92t31_unit.py`(`a1d82bff…`)를 `KB/a31_pins.sha256`(`bf1ca001…`, 133/133 OK)로 고정한 뒤 `chain31` 하나를 WMI 분리로 돌렸습니다(10-22 02:58:19 – 03:06:23) [실행].

| 단계 | 값 | 결과 |
|---|---|---|
| check31 (C1–C14, apply 45점검) | 거짓 0 | PASS |
| scan31 (봉인 뿌리 기록 훑기, 고친 s47 규칙) | 자식 rc 0, ok 참, 기록 134, s47 45, 나쁨 0, 보관 `STOP_a30_post.json`·`judge/sealed_records.json` 그대로 | PASS (`OK2/a31/sealed_records_a31.json` `47f91364…`) |
| unit31 (jb_unit 줄; 보충 31 §3 규칙, 보충 30 §5.3을 이 줄에 한해 대신함) | b9734abe 임시 분리 작업 트리(만들고 지움; WT 대 `TK/b9_ref` 차이 0)에서 4c 시험 넷 rc 1(128.3 s); 공통 97, 다름 0, 한쪽에만 0/0, 해석 INCOMPLETE 0; 통과 아닌 공통 2 = `ConfigFlagTests` 두 실패(두 쪽 같음) | PASS (`OK2/a31/unit_judge.json` `b7e9b649…`) |
| 스냅숏 s35·s36·s37 | s02 대비 | SAME |
| G3 끝 대조 | `a31_pins` 133/133 OK(03:07:18, 03:15:34), GWT8 head `e27ceac8`·status 0줄·6커밋·K8 `b9734abe`·원격 k92 0·푸시 0, 작업 트리 없음, python·VISSIM 0 | PASS |

- post30의 봉인 뿌리 훑기 STOP(S-K10)은 보충 31 §4.4대로 scan31 PASS로 대신합니다. jb_unit rc=1은 보충 31 §3 규칙으로 PASS입니다(같은 두 실패가 K8 머리 b9734abe에도 있음). 설정 정합(`make_config_n31.py`·`config_n31_v2.json`)은 묶음 2 목록입니다.
- 아직 아닌 것: K92_GATES_PASS는 독립 검증 A31(보충 31 §4.3 V1–V4; G-K4 plant 원자료 재계산 포함, 새 도구를 첫 읽기 전에 고정) PASS 뒤입니다. 그 뒤 V-B → VerifyVB. V-A·푸시는 사용자 결정 뒤.
- 이 절 덧붙임으로 이 파일 sha가 바뀌어 `KB/a31_pins.sha256` 127줄이 다르게 나옵니다. 고정 창(G1 → G3 끝 대조, 03:15:34 133/133 OK) 뒤의 설계된 바꿈입니다(`GATES_K92B1_A31.md` A31-N2).
