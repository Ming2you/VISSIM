# K9-2 V-A VerifyGates: 오프라인 관문 독립 검증 — 결과

- 작성 2026-10-23 11:3x KST. 검증 실행 11:08 ~ 11:35 KST.
- 검증 대상: `VA/K92_OFFLINE_GATES.md` = `VA/K92_VA_OFFLINE_GATES.md`(같은 바이트, sha256 `f5812e453099cfdadda9066ae873461d092c26f0ec6e1adeafcafc99a589b079`, 과제 글 값과 같음) [실행 `sha256sum`, `cmp`].
- **결론: pass = true.** 관문 판정을 원자료에서 모두 다시 계산했습니다. 일곱 판정(guard·FG·GB-7′·해시 A/B·GB-9′·S·G-H5′ 세 시드)이 모두 PASS(guard는 참)이고, 관문 판정과 모두 같습니다. 선언 목록 A만의 조건 7(0/61)과 A ∪ E_K92 판 조건 7(61/61)도 61행 모두 같습니다. 재실행 셋(GB-7′ 2개, 해시 A/B 1개)은 관문 출력과 비트 단위로 같습니다. 문턱은 보충 34 글과 같고, GB-7′ 목록 커밋은 첫 재생 출력보다 앞섭니다. [실행]
- 이 검증 결과는 판정 말이 아닙니다. 관문 결과는 PASS/FAIL과 숫자로만 적습니다.
- 표시: **[실행]** 이번에 직접 돌리거나 파일을 읽어 확인 · **[읽음]** 문서·코드·하네스 기록에서 확인 · **[추론]** 시험하지 않은 판단.
- 줄임말 (처음 한 번 풀어 씀)
  - SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`. VA = `SP/k92/va`. VG = 이번 검증 도구 폴더 `VA/vgates/`.
  - REPVA = `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_va`. OUTVA = 관문 출력 `REPVA/offline_gates`. VGO = 이번 검증 출력 `REPVA/verify_gates`(새 폴더, OUTVA 밖).
  - FRZ_K92 = 새 동결본(얼린 사본) `D:/VISSIM-merge/frozen/sdmpc31_c20aff1d_202610230833`, `FREEZE.json` sha256 `011f5be253fd31a5fb8342859b2b571375e49b4bbbbb42ea8f3ca93657b68476`, head `c20aff1d7bf0c432cb4f20e2922bd406d857aa5d`(K9-2-7). FRZ_K8b = 앞 동결본 `…/sdmpc31_b9734abe_202610141821`. OUTH = FRZ_K8b 관문 출력(이미 보고·검증된 자료, 자기 시험에만 씀).
  - GWT8 = 작업 트리 `D:/VISSIM-merge/sim3-n31-k8`. R-obs3 = 무제어 기록 런 v3c3-s31(61결정). RVA = V-A 런 자리 `D:/VISSIM_runs/20261023_sdmpc31_k92`.
  - A = GB-7′ 허용 차이 목록(V ∪ A_K8, R2-12 포함, 목록 sha `a8148f38…7af1`). E_K92 = 보충 34 §5.2의 K9-2 선언 차이 네 경로(E1 `k92_w`, E2 `k92_hb`, E3 `k92_hb_seed_binding`, E4 (173, p4) 하한 키).
  - S = 상시 관문(어댑터 exit 0, `*.error.txt` 0, `DECISION_FAILED` 0). WMI = 세션과 떼어 띄우기(`Invoke-CimMethod Win32_Process Create`).
- **블라인드**: 목적값·예측값은 열지도, 출력하지도 않았습니다. 이 보고의 숫자는 벽시계·개수·sha·종료 코드뿐입니다. V-A 성능 숫자는 아직 없고, J1 성능 숫자도 열지 않았습니다.

---

## 0. 판정 대조표

| 관문 | 관문 단계 판정 | 내 재계산 | 같음? | 근거 (`VGO/judge/v_judge_new.json` 안 경로) |
|---|---|---|---|---|
| 시작 조준·목록 (guard) | 참 | 참: FRZ_K92 `FREEZE.json` sha·head·가지·status 0, GWT8 HEAD = `c20aff1d…`, GWT8 status(캐시 뺌) 0줄, GWT8 바이트 대 FRZ_K92 표 0/0/0(제가 전체 해시), 목록 파일 sha `61c70c22…` = K9-2-7 blob 바이트, 목록 sha `a8148f38…7af1`(파일 안 함수와 제 정규 JSON 재계산 둘 다), A_K8 35, V 7, 재생 도구 sha = FRZ_K8b = 고정값, E_K92 함수 파일 sha `d15e9cc0…` | 예 | `/guard` |
| FG 동결·커밋 정합 | PASS | PASS: FG-1 {M CFG, M `gb7_allowed.py`}, FG-2 exit 0·0 B, FG-3 12/21/0 = git M/A/D(그 밖 0), 33경로 FRZ 바이트의 git blob sha(제가 계산) = ls-tree blob, sha256 = 표, FG-4 도구 sha | 예 | `/FG` |
| GB-7′ 61결정 (A ∪ E_K92) | PASS 61/61 | PASS 61/61: 조건 1–8 각 61, 제어 7필드 61 | 예 (61행 모두) | `/gb7` |
| └ 선언 목록 A만의 조건 7 (보고) | 0/61 | 0/61. A 밖 = 정확히 E1–E4 넷, A ∪ E_K92 밖 0 | 예 (61행 모두) | `/gb7/c7_declared_A_count`, `/gb7/outside_A_union` |
| 해시 A/B 9회 | PASS | PASS 9/9, 짝 6/6(V 밖 차이 0, CSV 같음) | 예 (9행·6짝) | `/hash` |
| GB-9′ 4결정 | PASS 4/4 | PASS 4/4. 벽시계 (가)/(나) s: 900 722.8/710.485, 2700 752.1/738.452, 4950 701.4/687.623, 6300 684.3/671.06 | 예 (값까지) | `/gb9` |
| 상시 관문 S | PASS 74/74 | PASS 74/74 | 예 | `/S` |
| G-H5′ s31·s41·s43 | PASS (조건 1–8) | PASS 세 시드 모두 조건 1–8 참 | 예 | `/GH5` |
| 단계 기록 `stages.json` | FG·GB-7′·해시·GB-9′·S·G-H5′ PASS | 같음, STOP 파일 0 | 예 | `/agreement/stages_equal` |

- 전체 대조: `/agreement/all_agree` = true. 행 불일치 0(GB-7′ 61, 해시 9행 + 6짝, GB-9′ 4, G-H5′ 3). 항목별 적중 수(경로 수)도 관문 `hits_by_item`과 같음 [실행].
- 재실행 셋(§4): 3/3 비트 같음 [실행 `VGO/rerun/rerun_result.json` `/all_bit_identical`].
- 문턱·순서·지금 상태(§2·§3.7): 모두 참 [실행 `/thresholds/ok`, `/order_pins/ok`, `/state_now/ok`].

---

## 1. 검증 방법 [실행]

### 1.1 하네스 비의존

- 관문 하네스(`VA/gates/*.py`)와 E_K92 판정 함수 `gb7_k92decl.py`는 import하지도, 실행하지도 않았습니다. 도구는 선언 글만 보고 새로 썼습니다(보충 34 §5.0 `:224`).
  - `VG/v_lib.py`: deep diff(K7 `gb_common.deep_diff` 꼴, `D:/VISSIM_runs/20261001_v3c3/reports/gb/gb_common.py:120-136`), 목록 A 읽기, **E_K92 다시 짬**(보충 34 §5.2-3 `:245-254` 글 그대로: 네 경로 정확히, `presence`·재생 쪽에만, E1 증거 sha 고정값 = Root 파일 sha·u4 sha·`after` float repr `5209.8`, E2 증거 sha 둘·rule sha, E3 float 0.0/1.0, E4 이름 정확히·float repr `1045.1612903225805`·그 결정 묶임 float 1.0).
  - `VG/v_judge.py`: guard·FG·GB-7′ 조건 1–8·해시 A/B·GB-9′·S·G-H5′ 조건 1–8·문턱·순서·지금 상태, 그리고 마지막에 관문 판정 JSON과 대조.
  - 목록 A만은 정의 그 자체라 FRZ_K92 `gb7_allowed.py` 바이트를 새 이름공간에 `exec`했습니다(import 아님, `__pycache__` 0). 파일 sha와 목록 sha를 먼저 확인했고, 목록 sha는 정규 JSON으로 제가 다시 셌습니다. 경로 판정은 제 정규식 맞춤과 파일의 `which()`를 모든 경로에서 둘 다 돌려 다른 경우 0을 확인했습니다(`/gb7/which_disagree_total` = 0).
- **원자료만 씀**: 판정은 재생 묶음(매니페스트·복사본·상태·원본/재생 action JSON·CSV·`replay_run.json`·어댑터 출력·`replay_compare*.json`), ps1·prepare·compare 글 파일, R-obs3 원본, `FREEZE.json` 표, git 객체, 사전점검 출력·plan·provenance, K7 GB-9 r1 원자료, 보충 34 글에서 계산했습니다.
  - 하네스 기록(`*.summary.json`)에만 있는 값 두 가지는 [읽음]으로 다뤘습니다. (1) ps1 종료 코드: ps1 글에서 다시 추론했습니다(거부 → 3, 어댑터 exit ≠ 0 → 1, compare 다름 → 2, 그 밖 0; `replay_decision_n31.ps1:19`, `:31`, `:141-146`). 추론은 하네스 기록과 74/74 같았습니다. (2) 해시 A/B 자식 환경의 `PYTHONHASHSEED`: 하네스 기록에서 9/9 의도대로였습니다. 미설정 팔 하나(T=9000)는 제가 미설정으로 다시 돌려 비트 같음을 봤습니다(§4).
  - 관문 판정 JSON(`OUTVA/judge/*.json`)은 제 판정이 끝난 뒤 대조에만 읽었습니다.
- 덧붙인 엄격 점검(선언 조건보다 강함, 모두 참): 복사본마다 하드 링크 아님(`st_nlink` 1), 복사 원천이 R-obs3 결정 폴더, 앞 결정 번호(`replay_manifest.previous_sec`), ps1 compare 파일에 튜닝 계약 칸이 있고 둘째 compare 파일에는 없음(두 파일이 바뀌지 않았음), 원본 action JSON = R-obs3 파일(61/61), 앞 결정 인자 61/61, 컨트롤러 no-control, GB-9′ 앞 결정 = R-obs3 `action_<T−150>`, GB-9′ 코드 바이트(재생 provenance의 GWT8 아래 입력·모듈 45개 sha = FRZ_K92 표, 4/4 불일치 0).

### 1.2 도구 고정 (관문 출력 읽기 전)

- 11:25:44 KST에 7개 도구 sha를 `VG/v_pins.sha256`과 LOG에 고정했습니다. 고정 전에는 V-A 관문 출력(OUTVA)을 열지 않았습니다. 형식은 OUTH(이미 보고된 K8b 출력)와 하네스 소스 글에서 익혔습니다.
- **도구 결함 하나(고침, V-A 자료 전)**: 첫 자기 시험(11:25:51)이 K8b 재현에서 T=150 조건 1을 거짓으로 냈습니다. 원인은 제 덧붙임 점검의 기대값이었습니다(T=150의 앞 결정을 T=0으로 둠; 실제는 T=1, `n31_common.py:168-172`). OUTVA를 열기 전에 `prev_sec(T)`로 고치고, 자기 시험에 앞 결정 점검 하나를 더해 11:28:01에 다시 고정했습니다(`v_pins.sha256` `23bcc198…7c01`). 첫 출력은 `VGO/selftest_run1_toolbug/`에, 옛 고정 목록은 `VG/v_pins_r1.sha256`(`059d91bb…`)에 남겼습니다. 옛 두 파일 바이트는 제자리 수정이라 sha만 LOG에 있습니다.
- 끝난 뒤 `sha256sum -c v_pins.sha256` 7/7 OK. 고정 뒤 도구를 고친 일은 없습니다.

| 도구 | sha256 |
|---|---|
| `v_lib.py` | `4033f6dc279e3396fb6520e9b943a21392ea7ff506e18d8b98ee2cc6bd6fae17` |
| `v_judge.py` | `375af56baf82de267d04db8d8bc55922faf19ff19cfc8390ddbe04f4db5fa1ca` |
| `v_selftest.py` | `da6cd24c37db2224947e5aae8440b51e588588dec4bd91d230a722944c141346` |
| `v_rerun.py` | `afd8c0d4f8ffc0b9a9a3cc4b6ad27245643e146da41d43019228764f3bfc1696` |
| `v_snap.py` | `bc1278bc890b49a8dfb4410607ce570941c3deb8e9a589235451827a314183db` |
| `v_copydiff.py` | `ee5bbffa79afa21872ecb831d237acf8d7729b74a1bddd54e46381b7424ab938` |
| `v_launch.ps1` | `3f3c2687115940687f256c3f1f91e7d94b0af2676cf61a1cf454fb894223eabe` |

### 1.3 자기 시험 (관문 출력 읽기 전) — 58/58 ALL_OK [실행 `VGO/selftest/v_selftest.json` `bfb0cf9d…`]

- 기대는 실행 전에 `v_selftest.py` 머리 글에 적었습니다.
- (a) deep diff 합성 7개, 그리고 K8b 실제 세 짝(T=1, 900, 9000)에서 제 경로 순서 = K7 `deep_diff` 경로 순서(314/373/366개).
- (b) E_K92 합성 24사례: 참 4(네 경로 재생 쪽에만, 하한 키 양쪽 같고 묶임 0.0, V·R2-12만, E 넷 + R2-02), 거짓 20(증거·u4·rule sha, `after` 1 ulp, Root 증거 1바이트, 양쪽 있음, 묶임 2.0·정수 1·bool, 하한 키 해시16, s + 1 ulp, 묶임 0.0, 묶임 키 없음, 원본 쪽에만, 새 `k92_other`, 형 틀림). 거짓은 모두 기대한 조건에서 났습니다.
- (c) V-B 마른 점검(VB-41w OFF 대 B1, T = 1…750, Root = V-B 트리, 하한 키 `…301ceabb95f116fa`): 보충 34 §5.2-6 `:264` 글의 기대와 6/6 같음(E1–E3 6/6, E4 T=1·150 안, T=300…750은 `binding_float_1`만 거짓, 남는 사슬 경로 4·5개 정확히 같음; FRZ_K92 이름 `e36d…`로 보면 B1 하한 키 6/6 밖).
- (d) K8b 재현(제 판정기를 K8b 프로필로 OUTH에): GB-7′ 60/61, T=1 조건 7만 거짓, A 밖 = `/diagnostics/leg_ramp_split_len_SC1001_W_out`, 61행 모두 K8b 행과 같음, 항목별 적중 같음, ps1 종료 코드 추론 74/74 = 하네스 기록, 해시 PASS(짝 6/6), GB-9′ PASS(벽시계 = K8b 값, 코드 바이트 45/45), S 74/74, 앞 결정 인자 61/61. = K8b 판정(`SP/j1/fix/VERIFY_GATES_K8b.md` §0).

### 1.4 실행 위생

- 무거운 Python은 한 번에 하나였습니다. 자기 시험·전체 판정·재실행은 WMI로 떼어 띄웠습니다(BelowNormal 16384, `PYTHONHASHSEED=0`, `python -B`, `PYTHONDONTWRITEBYTECODE=1`). 발사 기록 `VG/wmi_launch_lines.txt`: v_selftest_1 11:25:51 PID 23704, v_selftest_2 11:28:04 PID 26968, v_judge_new_1 11:29:09 PID 7220, v_rerun_1 11:30:59 PID 24036. 모두 RV 0, 그때 VISSIM 0·python 0. 모두 스스로 끝났습니다.
- 짧은 도구(스냅숏·사본 차이)는 `start /belownormal /b /wait`로 돌렸습니다.
- 재실행 자식(ps1·어댑터)의 우선순위 6(= BelowNormal)을 프로세스 목록에서 확인했습니다 [실행]. `v_rerun.log` 첫 줄의 `priority=0x0`은 제 스크립트의 되읽기 호출(ctypes 핸들 인자)이 실패한 것입니다. 실제 우선순위는 WMI 발사 설정으로 이미 BelowNormal이었습니다.
- 확인 간격은 9분 이하였습니다. 긴 목록을 명령 줄로 넘긴 일은 없습니다. 임시 이름은 PID만으로 정하지 않았습니다(재개 이동 이름에 시각 + ns).

---

## 2. 선언·문턱·순서 [실행]

### 2.1 근거 문서 sha

| 문서 | sha256 | 기대 |
|---|---|---|
| 보충 34 | `a05592d48512a515fc254d70b8173360d448b0aa17afb3f63c98b52ef713205e` | 고정점 `VA/AMENDMENT34_FIXED.md`(`fef58eca…c167`) 값과 같음 |
| 고정 목록 `VA/a34_pins.sha256` | `4e44741657dc483f2cbe5dd99a83fe9b477f5bdeffd5eadd534f87cb6cac0403` | 같음, `sha256sum -c` 83/83 OK (시작 때) |
| 결정 기록 | `6b76cc09cc0bc0ea568f219dce16900799e3b1095b0d850ecc1d442720e6af88` | 과제 글 값과 같음 |
| OG_METHOD / 보충 21 | `8edf8673…475d` / `ca369954…d176` | 보충 34 §0 값과 같음 |
| 관문 판정기 고정 목록 `VA/gates/va_gates_pins.sha256` | `6af36e7bd77dcc122886e56d30f0dae5ff76f75c72a74d2f6d9c33efeadfb669` | LOG 09:00:25 줄 값과 같음, 31/31 지금 바이트와 같음 |
| E_K92 판정 함수 `VA/gates/gb7_k92decl.py` | `d15e9cc08a600a60edb29b945bdab407e4e4631f5b0e44bc2d7ac080dc11fb11` | 보충 34 고정값과 같음(S-A34-11 해당 없음) |
| 자기 시험 (iii) 표준 출력 `VA/gates/gb7_k92decl_selftest_gates.out.txt` | `666cbac34ace9b76025c66fc655468e733935a7e69e2fc93519c62a20f3c1110` | Declare 고정 출력과 같음 |

### 2.2 문턱이 보충 34 글과 같음 [`/thresholds`]

- 보충 34 §5.1 3행(`:233`) 글에서 뽑은 문턱: (가) 1,005.0 / 859.95 / 996.0 / 974.4 s, (나) 985.6443465 / 841.0834455 / 975.7478355 / 955.3794375 s.
- K7 GB-9 r1 원자료(`reports/gb/gb9/B/T<T>_r1/replay/replay_run.json` `wall_sec`, action `metadata.decision_wall_sec`) × 1.5 = 위 값(4/4, 차 ≤ 1e-6). OG_METHOD §4 표(`:81-86`)와도 같음. 관문 판정기 상수 `K7_WALL`(소스 글을 정규식으로 읽음)과 `wa <= 1.5 * ka`·`wb <= 1.5 * kb` 비교도 같음.
- 개수 문턱: GB-7′ 61/61 + 제어 7필드 61(`:231`, R4 항목 3 `:218`), 해시 9회 + 짝(`:232`), GB-9′ 4/4(`:233`), S 74/74(`:234`), G-H5′ 조건 1–8(`:235`). 제 판정기도 이 개수로 셉니다 [읽음 `v_judge.py` `judge_gb7`·`judge_hash`·`judge_gb9`·`judge_s`·`gh5`].

### 2.3 GB-7′ 목록 커밋이 첫 재생 출력보다 앞섬 [`/order_pins`]

| 사건 | 시각 (KST) |
|---|---|
| K9-2-7 커밋 `c20aff1d`(`gb7_allowed.py`를 마지막으로 바꾼 커밋, 부모 = K9-2-6 `11d99c2a`, 작성자·커미터 Ming2you) | 08:07:52 |
| FRZ_K92 `FREEZE.json` `created_at` | 08:38:01 |
| 관문 판정기 고정 목록 파일 수정 시각(고정된 31개 파일 모두 이보다 늦지 않음) | 09:00:10 |
| 구동기 발사 / 첫 GB-7′ 출력(`OUTVA/gb7` 생성 시각, `g_driver.log` `STAGE_A start`) | 09:01:28 / 09:02:01 |

- 순서가 위 표와 같습니다. 그리고 61결정 모두 Root = FRZ_K92(조건 4)이고, FRZ_K92의 `gb7_allowed.py` 바이트 = K9-2-7 blob입니다. 그래서 GB-7′은 커밋된 목록(R2-12 포함)으로 판정됐습니다.

---

## 3. 관문별 재계산 세부 [실행]

### 3.1 guard·FG [`/guard`, `/FG`]

- guard: 위 §0 줄. GWT8 대 FRZ_K92 표는 제가 GWT8 전체를 다시 해시했습니다(10,569파일, 18.9 s).
- FG-1 `git diff --name-status --no-renames e27ceac8 c20aff1d` = `M …/config_n31_v2.json`, `M …/k8_gates/gb7_allowed.py`. FG-2 `git diff e27ceac8 c20aff1d -- evaluation vendor plant scripts` exit 0, 0 B. FG-3 FRZ_K92 대 FRZ_K8b 표 바뀜·더함·없음 12/21/0 = `git diff b9734abe c20aff1d` M 12·A 21·D 0, 그 밖 0. 33경로 FRZ 바이트의 git blob sha(제가 `sha1("blob <n>\0" + 바이트)`로 셈) = `ls-tree c20aff1d` blob, sha256 = 두 표 값. FG-4 `make_replay_state_v2.py` `4adf41cf…`, `replay_decision_n31.ps1` `5d34109f…` = FRZ_K8b 사본 = 고정값.

### 3.2 GB-7′ 61결정 [`/gb7`]

- 조건별 참(61 중): 1 준비 61(모든 사본 복사·sha 일치·하드 링크 아님, F17b 이력 바이트 = R-obs3, 상태의 `obs150.directory` = 묶음), 2 ps1·compare 61(추론 exit 0, ps1 compare `IDENTICAL`·`action_contract.ok`, `--tuning` 없는 compare `IDENTICAL`), 3 `FREEZE_VERIFIED path=FRZ_K92 sha256=011f5be2… head=c20aff1d…` 1줄 61, 4 루트 61(root FRZ_K92·run_root FRZ_K7·rebased·`REBASE FRZ_K7 -> FRZ_K92` 줄·`workspace_root` FRZ_K92), 5 튜닝 61(인자 = FRZ_K92 CFG, 지금 sha `c8e3ee2c…`, provenance sha 같음), 6 S 61, **7 A ∪ E_K92 61**, 8 CSV 바이트 61. 제어 7필드 같음 61.
- 선언 목록 A만의 조건 7: 0/61. A 밖 경로는 정확히 넷이고 모두 `presence`(재생 쪽에만)입니다: `/metadata/k92_w`(E1, 61결정), `/metadata/k92_hb`(E2, 61), `/metadata/k92_hb_seed_binding`(E3, 61), `/metadata/head_discharge_floor_173_p4_e36d6761cfeac634`(E4, T = 1, 150, 300, 450, 600, 750의 6결정). E 조건 거짓 0. **A ∪ E_K92 밖 0.** T ≥ 900에서는 하한 키가 차이로 나오지 않았습니다(§5.2-3 `:256` 예상과 같음).
- 항목별 적중(경로/결정): V 427/61, R1-01 427/61, R1-02…R1-08 각 61/61, R1-09 732/61, R1-10 305/61, R1-12 305/61, R1-13 976/61, R2-02 9,508/61, R2-03 830/60, R2-05 114/60, R2-07 2,068/61, R2-10 8/8, R2-11 393/61, R2-12 1/1(T=1), R3-01 122/61, R3-02 3,660/61, R3-03 366/61, R3-04 244/61, R3-05 1,830/61, R3-06 122/61, E1–E3 각 61/61, E4 6/6. 관문 `hits_by_item`과 같음.
- 어댑터 벽시계 27.3–34.4 s(보고와 같음).

### 3.3 해시 A/B 9회 [`/hash`]

- 9회 모두 조건 1–8 참(조건 7 = A ∪ E_K92, 같은 Root·같은 이름), 제어 7필드 같음, E 적중 E1·E2·E3(T ≥ 900), 선언 A만 조건 7 거짓 9/9(보고).
- 짝(미설정 대 0, 미설정 대 2; T = 4,050·4,500·9,000): V 밖 차이 0, V 안 7경로, CSV 같음 — 6/6.
- 환경 `PYTHONHASHSEED`(하네스 기록 [읽음]): 키 없음 / 0 / 2 = 의도대로 9/9.

### 3.4 GB-9′ 4결정 [`/gb9`]

- S 4/4: 준비 참, 어댑터 exit 0, `*.error.txt` 0, `DECISION_FAILED` 0, ps1 추론 2(= 하네스 기록, 허용 0·2).
- 유효성 4/4: `replay_run.controller` wu-link, `sdmpc_active` 참, 튜닝 인자 = GWT8 CFG이고 지금 sha `c8e3ee2c…`, provenance 튜닝 sha 같음, `workspace_root` = GWT8, `workspace_git_commit` = `c20aff1d…`, 재생 root = GWT8, 앞 결정 = R-obs3 `action_<T−150>`.
- 덧붙인 확인: 재생 provenance가 적은 GWT8 아래 입력·모듈 파일 45개의 sha가 FRZ_K92 표와 모두 같음(4/4). 그래서 GB-9′가 쓴 GWT8 코드 바이트 = FRZ_K92 바이트입니다.

| T | (가) `replay_run.json wall_sec` / 문턱 / 비 | (나) `metadata.decision_wall_sec` / 문턱 / 비 |
|---|---|---|
| 900 | 722.8 / 1,005.0 / 1.079 | 710.485 / 985.644 / 1.081 |
| 2,700 | 752.1 / 859.95 / 1.312 | 738.452 / 841.083 / 1.317 |
| 4,950 | 701.4 / 996.0 / 1.056 | 687.623 / 975.748 / 1.057 |
| 6,300 | 684.3 / 974.4 / 1.053 | 671.060 / 955.379 / 1.054 |

- 보고만: 네 상태 모두 `k92_w`·`k92_hb` 있음, `k92_hb_seed_binding` = 0.0, (173, p4) 하한 키 1개이고 이름 = R-obs3 이름(`e36d…`). 보고서 §3.4와 같음.

### 3.5 상시 관문 S [`/S`]

- 74/74(GB-7′ 61 + 해시 9 + GB-9′ 4), 실패 0.

### 3.6 G-H5′ 세 시드 [`/GH5`]

- 시드마다 사전점검 출력(`OUTVA/gh5/gh5_preflight_k92va_s<S>.out`, 각 22줄)과 plan·provenance 파일에서 셈: 1 `FREEZE_VERIFIED … sha256=011f5be2… head=c20aff1d…` 1줄, 2 `LAUNCH_PLAN_DETAIL … network_sha=3de889f0 … controller=wu-link sim_period=9000 seed=<S>` 1줄 + plan `tuning.sha256` `c8e3ee2c…` + `warnings []` + 줄의 plan sha = plan 파일 sha, 3 `NETWORK_COPY_OK`·`NETWORK_OK` sha `3de889f0…`, 4 `PROVENANCE_OK … freeze=011f5be2…` 1줄, 5 provenance `env.RW_DECISION_ERROR_POLICY` = plan `expected_env` = `hold_previous_on_exception`, 6 WD 정책 줄 정확히 1개, 7 `PREFLIGHT_ONLY done; no VISSIM started`·`EXIT sdmpc31_v3c3_k92va_s<S> code=0`, 8 RVA에 런 이름 폴더 없음(지금 다시 봄). 세 시드 모두 1–8 참.
- 보고: plan sha s31 `0ccd5613…d6cb`, s41 `35b7d437…e1c9`, s43 `cda87fae…90dc`; 출력 sha s31 `6588cb5d…5cc5`, s41 `9349f549…fdaa`, s43 `2ce82b34…aab7`(보고서 §3.6과 같음). `-Freeze` 줄 0, `REFUSED` 0, provenance 튜닝 sha `c8e3ee2c…`, `LAUNCH` 줄의 튜닝 경로 = FRZ_K92 CFG [실행 s31 출력 읽음]. `RVA\_preflight` 아래 런 이름마다 폴더 하나(`…_s31_20261023_105836`, `…_s41_20261023_105910`, `…_s43_20261023_105943`).

### 3.7 지금 상태 [`/state_now`]

- FRZ_K92 바이트 = `FREEZE.json` 표(제가 전체 해시, 0/0/0), FRZ_K92 캐시 파일 0. `frozen/` 36항목, PushFreeze 전 목록(`VA/freeze/frozen_top_before.txt`) 대비 더함 = FRZ_K92 폴더와 그 robocopy 로그 둘, 없어짐 0. RVA 최상위 `_preflight` 하나, 런 이름 폴더 0. `OUTVA/SHA256SUMS_gates.txt`(`40e9e58a…edae`) 4,441/4,441 OK.

---

## 4. 재실행 셋 (비트 같음) [실행 `VGO/rerun/rerun_result.json` `9bed31e2…`]

- 고른 것(실행 전 `v_rerun.py` 머리 글에 고정): A1 = GB-7′ T=1(앞 결정 없음, R2-12 길이 키와 E1–E4가 함께 나오는 결정), A750 = GB-7′ T=750(E4가 나오는 마지막 예열 결정, 이력 4창), H9000 = 해시 A/B T=9000 `PYTHONHASHSEED` 미설정(이력 59창). 한도(GB-7′ 2, 해시 1) 안입니다.
- 방법: FRZ_K92 재생 도구를 그대로 썼습니다(`make_replay_state_v2.prepare` 복사 전용 + F17b 이력 복사 + `replay_decision_n31.ps1 -ReplayDir <묶음> -Root FRZ_K92` + `--tuning` 없는 둘째 compare). 자식 환경은 관문 규칙과 같습니다(RW_* 등 뺌, 스레드 1, `NUMBA_CACHE_DIR = VGO/numba_cache`). 출력은 VGO 아래입니다.
- "비트 같음" 기준(실행 전 고정): 재생 CSV 바이트 같음, 재생 action JSON 차이가 V 경로뿐, `derived_<T>.json` 차이가 `/inputs/raw_sha256` 하나뿐(이 값은 묶음 폴더 이름을 담은 상태의 해시라 폴더가 다르면 반드시 다름 — K8b 해시 짝 두 묶음에서 실행 전에 확인), ps1·어댑터 종료 코드와 두 compare 판정·검사 플래그 같음, `replay_run` 인자(묶음 경로 뺌)·환경 같음, 제 행 판정 같음.

| 재실행 | 결과 | 관문 묶음과 비교 |
|---|---|---|
| A1 `VGO/rerun/gb7A/T000001` | ps1 0, compare 0, 어댑터 0, 25.3 s (관문 28.4 s) | **비트 같음**: CSV 같음, JSON 차이 V만(밖 0), derived 차이 `/inputs/raw_sha256`만, 행 판정·E 적중 같음 |
| A750 `VGO/rerun/gb7A/T000750` | ps1 0, compare 0, 어댑터 0, 28.3 s (관문 32.3 s) | **비트 같음** (같은 항목) |
| H9000 `VGO/rerun/gb7H/T009000_hunset_r1` (`PYTHONHASHSEED` 없음) | ps1 0, compare 0, 어댑터 0, 29.3 s (관문 30.3 s) | **비트 같음** (같은 항목) |

- ps1 종료 코드: 실제 0 = 제 추론 0 = 관문 묶음 추론 0 (세 경우 모두).

---

## 5. 보고서 주장·공개 점검

| `K92_OFFLINE_GATES.md` 주장·공개 | 점검 |
|---|---|
| 판정표 §0·관문별 §3 숫자(개수·벽시계·sha) | 제 재계산과 모두 같음 [실행]. 판정 JSON 9개 sha 64자리 = 보고서 §6 값 [실행 `sha256sum`] |
| §1.1 판정기 첫 재생 전 고정, 고정 뒤 수정 없음 | 고정 목록 파일 시각 09:00:10 < 구동기 09:01:28 < 첫 출력 09:02:01. 31/31 지금 바이트와 같음. 고정 뒤 바뀐 파일 = 출력(`*.out.txt`·`*.err.txt`·`wmi_launch_lines.txt`)뿐 [실행 `VGO/judge/copy_diffs/v_copydiff.json` `d8518adf…`] |
| §1.2 사본 차이 = R4 닫힌 목록 | K8b 원본 9개 sha = K8b 고정값(`SP/j1/fix/gates/gates_files_before_run.sha256`, `gates_files_later.sha256`) = `k8b_orig/` 사본. 제가 따로 만든 diff(`VGO/judge/copy_diffs/*.diff`)를 읽음: `gprep.py`·`greplay.py` 차이 0; `gcommon.py` 기대값·K8b 프로필 상수·`load_allowed` 인자화·안 쓰는 상수 뺌(항목 1·5·7), `gjudge.py` 조건 7 연결·제어 7필드·D-K9-12 분기 뺌·G-H2 뺌·프로필(항목 1·2·3·4·5·7), `g_driver.py` 문서 sha·단계 guard→FG→A→H→B→S→GH5→after·감시 대상(항목 1·5·6), `gh5_check.py`·`gh5_launch.ps1`·`launch.ps1`·`gb7_report.py` 기대값(항목 1, `gh5_launch`는 항목 5). 그 밖 차이 없음. `gh1*`·`gr`·`gtree`·`cmp21`·`gh4_confirm` 사본 없음 [실행] |
| §1.3 자기 시험 (iii) 출력 = `666cbac3…` | 같음 [실행 sha] |
| §2-2 `gh5_launch.ps1` 9번째 사본 | 차이 = 기대값(FRZ_K92·RVA·이름·시드·출력)과 발사 줄 한 줄 더 적기뿐, 발사 명령 글 = §5.1 `:235` [실행 diff 읽음] |
| §2-3 G-H5′ 조건 8을 구동기가 판정 | 제 재계산은 조건 8을 RVA에서 직접 봄. 세 시드 모두 런 폴더 없음 [실행] |
| §2-7 `gb7_report.json` 최대 |Δ| 칸 미열람 | 저도 열지 않았습니다(블라인드) |
| §2-10 FRZ_K8b `__pycache__` 229파일 | 제 스냅숏 FRZ_K8b 10,778파일 = 표 10,549 + 캐시 229. 검증 앞뒤 변화 0 [실행] |
| §2-11 GWT8 탄젠트 캐시 3개 옮김 | 지금 GWT8 탄젠트 캐시 135개, GWT8 바이트 대 표 0/0/0 [실행] |
| §2-12 RVA `_preflight` 새 폴더 셋 | 같음 [실행] |
| §3.7 읽기 전용 감시 8회 변화 0 | `g_driver.log` `SNAP_CHECK` 8줄 모두 `bad=[]`, `STOP`·`Traceback`·`error` 0줄 [실행 grep] |
| 사본 `REPVA/offline_gates_report/` | `SHA256SUMS_OFFLINE_GATES.txt`(`d36e72db…01ba`) `sha256sum -c` 59/59 OK [실행] |

---

## 6. 발견과 단서

1. **판정에 영향을 주는 결함은 찾지 못했습니다.** 판정·개수·벽시계·sha가 제 재계산과 모두 같습니다.
2. **보고서 글자 하나 틀림(판정 무관)**: `K92_OFFLINE_GATES.md:220`의 `va_gates_pins.sha256` `6af36e7b…b33f`는 끝 넉 자가 틀립니다. 실제 sha는 `6af36e7b…b669`입니다(같은 보고서 `:49`의 64자리와 LOG 09:00:25 줄은 맞음) [실행]. 판정과 무관한 줄임 표기 실수입니다.
3. **제 도구 결함 하나(고침, V-A 자료 전)**: §1.2. 제가 덧붙인 앞 결정 점검의 기대값 실수였고, OUTVA를 읽기 전에 고치고 다시 고정했습니다.
4. **제 보고 전용 칸 하나는 쓸모없었음**: G-H5′ 출력에서 `TUNING` 줄을 찾는 칸(`/GH5/seeds/*/report/tuning_line_under_frz`)이 거짓입니다. `-Freeze` 없는 사전점검에는 그 줄이 없고, 튜닝 경로는 `LAUNCH` 줄에 있습니다. 그 줄의 경로는 FRZ_K92 CFG이고 provenance 튜닝 sha도 `c8e3ee2c…`입니다 [실행]. 판정 조건이 아닙니다.
5. **하네스 기록에만 있는 값**: ps1 종료 코드와 해시 A/B 환경 `PYTHONHASHSEED`는 하네스 요약에만 있습니다 [읽음]. ps1 종료 코드는 글에서 다시 추론해 74/74 같았고, 미설정 팔 하나는 재실행으로 확인했습니다.
6. 재생 도구는 직전 행동을 R-obs3 폴더에서 제자리로 읽습니다(`replay_decision_n31.ps1:71-82`). 관문과 같은 방식입니다. 읽기만 했고 앞뒤 스냅숏에서 R-obs3 변화 0입니다.

---

## 7. 읽기 전용·위생 [실행]

- 앞(11:28:51)·뒤(11:34) 스냅숏(경로·크기·mtime, 캐시 포함): FRZ_K92(10,570, 캐시 0), FRZ_K8b, R-obs3, RVA 전체, OUTVA 전체(4,442), `VA/gates`, J1 런 폴더 넷, `frozen/` 최상위 36, RR 최상위, GWT8 HEAD·`status --porcelain --ignored`·탄젠트 캐시 135, K8 가지 — **변화 0** (`VGO/logs/v_snap_cmp.txt` `bad=[]`).
- GWT8: HEAD = 원격 = `c20aff1d…`, `status --porcelain` 0줄. K8 가지 로컬·원격 `b9734abe…` 그대로. 원격 `claude/k92-b1-20261016` = `c20aff1d…`.
- `VG/__pycache__` 0. python·VISSIM·cscript 끝에 0개. 드라이브 여유 C: 39.5 GB, D: 365.8 GB(8 GB 위).

## 8. 하지 않은 일

- 커밋·푸시·동결 0. GWT8 추적 파일·`frozen/*`·J1 런·R-obs3·OUTVA 쓰기 0(재실행 준비는 복사, 출력은 VGO).
- VISSIM 시작·종료 0. 발사 0. 내가 띄우지 않은 프로세스 끔 0. 이름으로 끈 일 0.
- 시험(test) 실행 0(금지 시험 포함). 봉인 시드 37·59·61·67 자료 0, codex 64cf 숫자 0, v3c3-s47 자료 0.
- 선언 정의·문턱·목록·E_K92·판정기 변경 0. 목적값·예측값·성능 숫자 열람 0.
- 튜닝·증거 파일 쓰기 0.

## 9. 산출물

- 이 보고서: `VA/VERIFY_GATES.md` = `VA/VERIFY_GATES_VA.md`(보충 34 §5.1 `:239`·§6.1 `:280` 이름; 같은 바이트, sha256은 LOG와 `REPVA/verify_gates_report/SHA256SUMS_VERIFY_GATES.txt`). 사본 `REPVA/verify_gates_report/`(보고서 두 이름 + `vgates/` 도구).
- 판정 출력 VGO (sha256 앞 16자리): `judge/v_judge_new.json` `2c25569eed5b98a1`(64자리 `2c25569eed5b98a160238c2845747333df042671314b8ede48dc3bb25e5f0f20`), `rerun/rerun_result.json` `9bed31e243679acc`(64자리 `9bed31e243679acc4c7486bde2a9079232999e1f9551f07bff051b5c7bc17a75`), `selftest/v_selftest.json` `bfb0cf9d17d2adfd`, `selftest/k8b_judge.json` `4e33c339679ad642`, `judge/copy_diffs/v_copydiff.json` `d8518adf1f577534`, `snap/before.json` `d36f13db1323e539`, `snap/after.json` `6ec4a78aace0080b`. 첫 자기 시험(도구 결함) 출력 `selftest_run1_toolbug/`.
- 로그: `VGO/logs/v_selftest_{1,2}.txt`, `v_judge_new_1.txt` `0523ff013ae465c7`, `v_rerun_1.txt` `571a103124f159ce`, `v_rerun.log`, `v_copydiff.txt`, `v_snap_{before,after,cmp}.txt`. 전체 목록 `VGO/SHA256SUMS_verify.txt`.
- 도구 `VG/`: §1.2 표, 고정 목록 `v_pins.sha256` `23bcc198f55a3ecdd189d24fdffbefac4077bdbe839054e04e8112eb33c37c01`(옛 `v_pins_r1.sha256` `059d91bb…`), 발사 기록 `wmi_launch_lines.txt`.
- 기록: `VA/LOG.md` "[VerifyGates]" 줄들.

## 10. 다음

- 보충 34 §6.1 발사 전제 (3)(`:280`)의 "독립 검증 `VA/VERIFY_GATES_VA.md` pass = true"는 이 보고로 섰습니다.
- 발사 전에 남은 전제: (4) 분석 도구·`ANALYSIS_METHOD_VA.md`·검증 도구 sha 고정, (5) `va_monitor.py`·`va_health.py`·`k92va_s43_watcher.ps1`(드라이런 8건) 고정, (6) C:·D: 8 GB 이상·K8 가지 `b9734abe…`. (1)(2)는 앞 단계 기록으로 참입니다 [읽음 LOG].
