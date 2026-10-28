# 승격 단계 (Promote) — K9-2-6, K9-2-7 (2026-10-23 08:00–08:10 KST)

- **결과: 두 커밋을 만들었습니다. 보충 34가 정한 점검은 모두 참입니다. 작업 트리는 깨끗하고, 푸시는 하지 않았습니다.**
  - K9-2-6 = `11d99c2a4790f2bed1a610054e322ffff0253bc1` (승격: 묶음 1 팔 바이트 → 배포 튜닝)
  - K9-2-7 = `c20aff1d7bf0c432cb4f20e2922bd406d857aa5d` (GB-7′ 목록 R2-12, 목록 sha `a8148f3849fb5e26f09d8f0a095d442aa56da051d888df0b2f657dba089e7af1`)
- 근거 규칙: 보충 34 §3.1(K9-2-6), §3.2(K9-2-7), §9.2 S-A34-1·2·12. 사용자 결정 D-K9-67·D-K9-72.
- 다음 단계: 보충 34 §3.3 **VerifyPromote**(독립 검증, `pass = true`)가 푸시 전에 꼭 있어야 합니다(S-A34-13). 이 단계는 푸시·동결·관문·VISSIM을 하지 않았습니다.
- 표시: [실행] 이번에 돌려서 확인 · [읽음] 문서·코드에서 확인 · [추론] 시험하지 않은 판단.

## 줄임말 (처음 한 번만 풉니다)

- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`. VA = `SP/k92/va`. PR = `VA/promote`(이 단계 출력 폴더). REPVA = `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_va`(사본 자리).
- GWT8 = `D:/VISSIM-merge/sim3-n31-k8`, 브랜치 `claude/k92-b1-20261016`. K8 가지 = `claude/k8-sc1001eb-defects-20261004`(`b9734abe…`, 건드리지 않음).
- CFG = `diagnostics/sdmpc_n31_20260924/config_n31_v2.json`(배포 튜닝). CFG-B1 = `diagnostics/sdmpc_n31_20260924/config_n31_v2_k92b1.json`(묶음 1 팔, K9-2-3에서 만듦).
- GB7 = `diagnostics/sdmpc_n31_20260924/k8_gates/gb7_allowed.py`(GB-7′ 허용 차이 경로 목록).
- W = SC109 서측 직진 용량 키 `urban.sc109w_through_saturation`. H-b = (173, p4) 좌회전 헤드 하한 씨앗 키 `urban.capacity.head_floor_seed`. B1 = W + H-b.
- blob = git 객체 해시(`git hash-object --no-filters`로 작업 파일과 비교; `core.autocrlf=true`라 필터 없이 셈).

## 1. 시작 점검 [실행 08:00]

| 항목 | 값 | 참? |
|---|---|---|
| 고정점 `VA/AMENDMENT34_FIXED.md` sha256 | `fef58eca53240e6026a78e19729a699be5fa7e965a2d1648f185e551afc3c167` (= LOG 07:59:34 줄) | 참 |
| 보충 34 `SP/K8_PREDECLARATION_AMENDMENT_34.md` sha256 | `a05592d48512a515fc254d70b8173360d448b0aa17afb3f63c98b52ef713205e` (= 고정점 표 `AMENDMENT34_FIXED.md:7`, = `.sha256`) | 참 |
| 고정 목록 `VA/a34_pins.sha256` | sha256 `4e44741657dc483f2cbe5dd99a83fe9b477f5bdeffd5eadd534f87cb6cac0403`(= 고정점 `:8`), 83줄, `sha256sum -c` 83/83 OK | 참 |
| 결정 기록 `SP/K9_1_J1_NOTES_20261013.md` | `6b76cc09cc0bc0ea568f219dce16900799e3b1095b0d850ecc1d442720e6af88` | 참 |
| 재개 점검 | LOG에 Promote 줄 없음, `PROMOTE.md` 없음, HEAD `e27ceac8`, 앞 시도 흔적 없음 → 처음부터 | — |
| 디스크·프로세스 | C: 39.5 GB, D: 368.9 GB. python·VISSIM·cscript 0개 | 참 |
| §3.1 브랜치 앞 확인 | HEAD `e27ceac86c01…`, K8 가지 `b9734abe…`(로컬·원격 같음), `status --porcelain` 0줄, `git log --format=%s b9734abe..HEAD` = K9-2-5 … K9-2-0 6개 이 순서, 원격 `claude/k92*` 0개(`git ls-remote`) | 참 |

## 2. K9-2-6 승격 (보충 34 §3.1, D-K9-72 순서)

| 순서 | 점검 (보충 34 `:129`–`:138`) | 결과 [실행] | 참? |
|---|---|---|---|
| 1 전 | HEAD `e27ceac8`, status 0줄, 작업 CFG blob = HEAD blob, CFG-B1 sha | 작업 CFG `268ae47132443a4a97e87ffa51ca7f7f0c878586` = HEAD blob; CFG sha `d0f9ef39…aec6` 278,142 B; CFG-B1 sha `c8e3ee2c…1866` 278,607 B, blob `b6ccd50d…`; 셋 다 `i/lf w/lf attr/-text` | 참 |
| 1 | 편집 **전** `python -B …/make_config_n31.py --k92b1 --check` (깨끗한 K9-2-5 트리) | exit 0. 표준 출력 한 줄 `CONFIG_N31_K92B1_OK family=single_value sha256=c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866`. 파일 `PR/pre_edit_mkcfg_k92b1_check.out.txt` sha `41a9020a…0963` = 첫 Declare 출력 `VA/work/pre_mkcfg_k92b1_check.out.txt`와 **바이트 같음**. 오류 출력 0 B. 뒤 status 0줄, `.pyc` 11→11 차이 0, CFG·CFG-B1 바이트 그대로 | 참 |
| 2 | 바이트 복사 CFG-B1 → CFG | 08:02:49 `[System.IO.File]::Copy(…, $true)`. 줄 끝 변환 없음 | — |
| 3 | `python -B scripts/build_obs150_detectors.py --tuning …/config_n31_v2.json --check` | exit 0. 출력 한 줄 `OBS150_DETECTORS_OK rows=294 sha256=108debbb4b021796b195927ba2140dafab571e1d976734190f5d8f5bd255cfbc …`. 파일 `PR/post_copy_obs150_check.out.txt` sha `7e6191ad…45e4` = 첫 Declare `pre_obs150_arm_check.out.txt`와 바이트 같음. 오류 0 B. 뒤 status = CFG 한 줄, `.pyc` 차이 0 | 참 |
| 4 | blob·sha·크기·바이트 | 작업 CFG `hash-object --no-filters` = `b6ccd50d96321e293f6ad9cf020e53ce1a8fbf5c`, sha `c8e3ee2c…1866`, 278,607 B, CFG-B1과 `cmp`·`fc /b` 같음 | 참 |
| 5 | JSON 값 차이 (작업 CFG 대 `e27ceac8:CFG`) | `PR/p5_json_diff.py`(실행 전 LOG 고정) exit 0 `P5_ALL_OK`: 차이 = `/urban/capacity/head_floor_seed`, `/urban/sc109w_through_saturation` 두 경로뿐, 둘 다 새 쪽에만. 값 = `{evidence, evidence_sha256}` 둘. `evidence_sha256` `b9fa1d01…20ee`·`b4b7294d…1712` = 증거 파일 바이트 sha. `runtime.decision_error_policy` = `hold_previous_on_exception` (옛·새 둘 다) | 참 |
| 6 | diff 범위 | `git diff --name-status` = `M CFG` 한 줄, `git diff e27ceac8 -- evaluation vendor plant scripts` 0줄, 추적 안 된 파일 0 | 참 |
| 커밋 | 경로 하나, 작성자·커미터 Ming2you | `git add -- CFG` 하나. `git -c user.name=Ming2you -c user.email=alsrjsrb1915@snu.ac.kr commit -F PR/msg_k926.txt`. 커밋 **`11d99c2a4790f2bed1a610054e322ffff0253bc1`** 08:04:46, 부모 `e27ceac8`. 첫 줄 = 보충 34 `:136` 글 그대로, 끝 줄 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` | 참 |
| 커밋 뒤 | ls-tree blob = 작업 blob, 바뀐 경로 하나 | `git ls-tree 11d99c2a CFG` = `b6ccd50d…` = 작업 `hash-object --no-filters`. `cat-file` 바이트 sha `c8e3ee2c…1866`. `git diff --name-status e27ceac8 11d99c2a` = `M CFG` 한 줄. status 0줄 | 참 |

- 이 커밋 뒤로는 `make_config_n31.py --k92b1 --check`를 돌리지 않았습니다. 설계상 `ValueError`입니다(생성기가 CFG를 바탕으로 읽음, 보충 34 §2.2·§9.1-7) [읽음].

## 3. K9-2-7 GB-7′ 목록 보충 (보충 34 §3.2 = 보충 24 §14.3)

| 순서 | 점검 (보충 34 `:142`–`:155`) | 결과 [실행] | 참? |
|---|---|---|---|
| 편집 전 | HEAD = K9-2-6, status 0줄, 작업 GB7 blob = K9-2-6 ls-tree blob | HEAD `11d99c2a`, status 0줄, GB7 `9fd7d5194081a089298444351072a2d058af5aef` = ls-tree blob, sha `c6f9ca1c…94c8`, CR 0 | 참 |
| 편집 | 바이트, LF만 | `PR/p7_edit.py`(실행 전 LOG 고정)가 보충 24(sha `d46db6dc…aadc`)의 `:591` 정규식·`:592` 이유·`:593` docstring 글자를 따옴표 안에서 뽑아 넣음. 마른 실행 뒤 `--write` 1회. 넣은 것 = docstring 줄 `:19` 뒤 한 줄(`- ` + `:593` 글자 + `.`), R2-11 튜플 끝 뒤 R2-12 튜플 두 줄. 새 파일 sha `61c70c222cf3bed2a0a299b539aa3fccad288c059b72be678cceda2c3dc6f319`, 11,780 B, CR 0 | — |
| 3 | `python -B …/k8_gates/gb7_allowed.py` 출력 | exit 0. 한 줄 `GB7_ALLOWED schema=k8-gb7-allowed/v1 V=7 A_K8=35 R1=16 R2=12 R3=7 list_sha256=a8148f3849fb5e26f09d8f0a095d442aa56da051d888df0b2f657dba089e7af1` = 보충 34 `:150` 기대 줄 = 검토 `rev_a34.json` `print_line`. 오류 0 B, `.pyc` 차이 0 | 참 |
| 4 | 판정 표 6행 (보충 24 §14.3) | `PR/p7_checks.py`(실행 전 LOG 고정) `P7_CHECKS_ALL_OK`: `len_SC1001_W_out` → R2-12, `length_fallback` → R2-12, `req_last_SC1001_W_out` → 밖, `u_on_last` → 밖, `len_SC1001_W_out/x` → 밖, `injected_RM_C10484` → R2-11. R2-12 하나, R2-11 바로 뒤. V 7, A_K8 35(R1 16·R2 12·R3 7) | 참 |
| 5 | 바이트 범위 | `git diff 11d99c2a c20aff1d -- GB7`: 지운 줄 0, 더한 줄 3(docstring 1 + 튜플 2). docstring 줄 = 검토 `rev_a34.json` `docline.a34` 글자 그대로. 이유 문자열 117자, UTF-8 sha256 `7a51c150f6bc3cc4…` = 보충 24 `:592`. CR 0. `git ls-files --eol` = `i/lf w/lf attr/-text` | 참 |
| 6 | E_K92 경로 넷이 A 밖 | `/metadata/k92_w`, `/metadata/k92_hb`, `/metadata/k92_hb_seed_binding`, `/metadata/head_discharge_floor_173_p4_e36d6761cfeac634` 모두 `which` = None | 참 |
| 커밋 | 경로 하나 | `git add -- GB7` 하나, `commit -F PR/msg_k927.txt`. 커밋 **`c20aff1d7bf0c432cb4f20e2922bd406d857aa5d`** 08:07:52, 부모 `11d99c2a`. 첫 줄 = 보충 34 `:154` 글 그대로. 본문에 새 목록 sha·파일 sha·blob, "결과를 본 뒤의 목록 보충(D-K9-38 ④)", D-K9-12 예외 다시 쓰지 않음. 끝 줄 Co-Authored-By | 참 |
| 1 | `git diff --name-status K9-2-6..K9-2-7` | `M GB7` 한 줄 | 참 |
| 2 | `git diff K9-2-6 K9-2-7 -- evaluation vendor plant scripts` | 0줄 | 참 |
| 커밋 뒤 | ls-tree blob = 작업 blob | GB7 ls-tree `1ca72d81f6e63736fa835cd408c9c9d6b7563ffa` = 작업 `hash-object --no-filters`, `cat-file` 바이트 sha `61c70c22…f319` | 참 |

## 4. 끝 상태 [실행 08:08–08:09]

- GWT8 HEAD = `c20aff1d7bf0c432cb4f20e2922bd406d857aa5d`(브랜치 `claude/k92-b1-20261016`). `git status --porcelain --untracked-files=all` 0줄.
- `git log b9734abe..HEAD` = 8개, 순서 K9-2-7, K9-2-6, K9-2-5 … K9-2-0. 작성자·커미터 모두 `Ming2you <alsrjsrb1915@snu.ac.kr>`.
- `git diff --name-status e27ceac8 c20aff1d` = `M CFG`, `M GB7` 두 줄. `git diff e27ceac8 c20aff1d -- evaluation vendor plant scripts` 0줄.
- K9-2-7 트리의 CFG blob `b6ccd50d…`(sha `c8e3ee2c…1866`), GB7 blob `1ca72d81…`(sha `61c70c22…f319`, 목록 sha `a8148f38…7af1`). 두 파일 모두 `i/lf w/lf attr/-text`.
- K8 가지 `b9734abe1c83f95c9cec5fca5e42b7b18cd45991` 그대로(로컬·원격).
- **푸시 0.** 원격 `claude/k92*` 0개(`git ls-remote`). 로컬 원격 추적 ref에도 k92 없음.
- 동결·관문·재생·VISSIM·COM·러너·시험 0. `D:/VISSIM-merge/frozen/` 쓰기 0. python·VISSIM·cscript 0개(끝에). C: 39.5 GB, D: 368.9 GB.
- 봉인 시드(37/59/61/67) 자료·codex 64cf 숫자·v3c3-s47 자료 열기 0.

## 5. 알릴 것 (판정에 영향 없음)

1. **순서 1을 두 번 돌렸습니다.** 1차(08:01:49)는 PowerShell 5.1의 `>` 리다이렉션이 출력 앞에 UTF-8 BOM(`ef bb bf`)을 붙였습니다. 글은 같았습니다(BOM을 빼면 `41a9020a…` 파일과 바이트 같음) [실행]. 원본 바이트를 남기려고 같은 읽기 전용 점검을 `cmd.exe` 리다이렉션으로 한 번 더 돌렸습니다(08:02:24). 1차 파일은 `PR/try1_psredir_*`로 이름만 바꿔 남겼습니다. 두 번 모두 exit 0·쓰기 0입니다. 이 점검은 쓰기가 없어 다시 돌려도 상태가 바뀌지 않습니다 [추론, 실행 전후 status·`.pyc`·CFG sha로 확인].
2. **우선순위**: python을 직접 BELOW_NORMAL로 띄우지 않고, 부모 PowerShell을 BelowNormal로 내린 뒤 띄웠습니다. Windows는 부모가 BELOW_NORMAL이면 자식이 그 등급을 물려받습니다 [읽음 CreateProcess 문서; 자식 등급은 직접 재지 않음]. 환경: `PYTHONHASHSEED=0`, `PYTHONDONTWRITEBYTECODE=1`, `python -B`, CurrentDirectory = GWT8. `PR/p7_edit.py`·`PR/p7_checks.py`에만 `PYTHONIOENCODING=utf-8`을 더했습니다(GB7 `__main__` 점검 3에는 안 씀).
3. **`.pyc` 점검 방법**: GWT8 아래 `*.pyc` 전체(이미 있던 11개)의 경로·수정 시각을 실행 전후로 비교했습니다. 매번 차이 0.
4. **"추적 안 된 파일 0"**은 `git ls-files --others --exclude-standard` 기준입니다. 무시 목록에 걸린 항목(152개, 이 단계 전부터 있던 것으로 봄 [추론; 단계 전 목록은 찍지 않음])은 세지 않았습니다.
5. **편집 방법**: GB7 편집은 손 타이핑 대신 `PR/p7_edit.py`가 보충 24 원문 줄에서 글자를 바이트로 뽑아 넣었습니다(앞 sha가 `c6f9ca1c…`가 아니거나 원문 줄 꼴이 다르면 쓰지 않고 멈추게 짬). 소스에서는 R2-12를 두 줄(튜플 머리+정규식 / 이유 문자열 하나)로 썼습니다(보충 34 `:152` "튜플 줄(1–3줄)" 범위, `:145` 이어 붙인 값 = 글자 그대로). 두 커밋의 첫 줄은 보충 34 `:136`·`:154` 고정 글과 글자 같음 [실행 비교].
6. **`PR/p7_worktree_diff.txt`**는 PowerShell `Out-File`로 저장해 다시 인코딩된 참고용입니다. 원본 바이트 diff는 `PR/k927_commit_diff.patch`(git이 직접 씀)입니다.
7. **LOG 시각 정정**: LOG의 Promote 줄 몇 개(08:03:10·08:08:30·08:10:30·08:12:00·08:14:30)는 시계를 읽지 않고 어림해 실제보다 늦게 적었습니다. 08:09:16 줄에 파일 수정 시각·커밋 시각으로 실제 시각 범위를 정정했습니다. 내용·sha·순서(고정 줄 → 첫 실행)는 그대로입니다. 이 문서의 시각은 파일·커밋 시각입니다.

## 6. 이 단계 파일 (`VA/promote/`, sha256 [실행])

| 파일 | sha256 | 뜻 |
|---|---|---|
| `pre_edit_mkcfg_k92b1_check.out.txt` / `.err.txt` | `41a9020a20696886ced1355cb3a3ed3b4276ed99390f183aa18ea6ae91b00963` / `e3b0c442…b855`(0 B) | 순서 1 (2차, 원본 바이트) |
| `try1_psredir_pre_edit_mkcfg_k92b1_check.out.txt` / `.err.txt` / `try1_step1_pyc_before.txt` | `ad13edcc5d26d1caedca93ebca1d1c282c366415d664e3bd372bf34c175a0a3f` / `e3b0c442…`(0 B) / `b8a07454…e65c` | 순서 1 1차(BOM), 보관 |
| `post_copy_obs150_check.out.txt` / `.err.txt` | `7e6191adb9868ad906b89bce23c026bb2ffa7f1020fa265225a3eee0cb3345e4` / `e3b0c442…`(0 B) | 순서 3 |
| `p5_json_diff.py` / `.out.txt` / `.err.txt` | `d775d360342aab6011204fa14b1b6c2f595a4ae91d3fb0e6ea42bd12074b9396` / `a88ff8d1c44e2480214aa9e5c954de2d79f5ae9c2d81749094fb6c22c1677a95` / 0 B | 순서 5 |
| `msg_k926.txt` | `304ec976abd758247f83924ce1481d5027955e4f4d46073cbaaad2c72e119e03` | K9-2-6 메시지 |
| `k926_commit_stat.txt` | `94ea2e0414e0e8a0d89eeb02ebe2b05ec13d49ec4e28e7e65922bc80dfe5082f` | K9-2-6 diff stat |
| `p7_edit.py` / `p7_edit_dry.out.txt` / `p7_edit_write.out.txt` (두 err 0 B) | `455910988aa270343165da86a3570eefec4a403060dcf02d4451ed32f4f1db3c` / `8e351d5c…2c15` / `9b55029d…6698` | K9-2-7 편집 |
| `p7_worktree_diff.txt` | `be3d055b…f259b` | 참고용(재인코딩) |
| `p7_check3_gb7_main.out.txt` / `.err.txt` | `c9d6b76c5d2463965757b598384a48b159a8709f026904f9684f6e777338f39b` / 0 B | 점검 3 |
| `p7_checks.py` / `p7_checks.out.txt` / `.err.txt` | `cdb0dfe33ee991efe5d4643e07e49eabb7084515b52a71591e5a4c984f2934f2` / `f33a2404b5e6bcde19cbc44f9dd9eed3833122109ab351306a6e9c17a52370ea` / 0 B | 점검 4·6 |
| `msg_k927.txt` | `03f03ee8ba57e8948b8236423935a9dadf68ba8323bb1fb7485f0e1942039e70` | K9-2-7 메시지 |
| `k927_commit_diff.patch` | `595f1ca7ca69894a31b540a2c2c2ee4f7d34b89015b5754348297d0e1deefda3` | K9-2-7 커밋 diff(원본 바이트) |

- 사본: `REPVA/promote/`(이 파일 + `VA/promote/` 전체, `SHA256SUMS_PROMOTE.txt`).

pass = true
