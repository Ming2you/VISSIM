# K8 관문 도구 (진단 전용)

K8(공유 결함 수정 + SC1001 EB 안 1 v2)의 활성 점검·관문 계산에 쓰는 도구입니다. 런타임 코드가 아니며, 배포 경로는 이 폴더를 import하지 않습니다.

- 원본: K8 스크래치 하네스 `k8/tools/`, `k8/site/sitecustomize.py`, `k8/opt1v2/tools/` (2026-10-04, DEFECTS.md §1). 이식하면서 바꾼 것은 경로 처리뿐입니다(아래 "이식 메모").
- 규칙: VISSIM·cscript 실행 없음. 무거운 작업(아래 ●)은 한 번에 하나, `python -B`, `PYTHONHASHSEED=0`, BELOW_NORMAL(도구가 스스로 낮춤).

## 루트와 출력

| 항목 | 인자 / 환경변수 | 기본값 |
|---|---|---|
| 코드 루트 | `--root` / `K8G_ROOT` | 이 워크트리(`k8_gates/../../..`) |
| 출력 루트 | `--out` / `K8G_OUT` | `k8common.DEFAULT_OUT`(세션 스크래치 `k8/gates_out`). **저장소 안이면 거부** |
| R-obs 런 | `--robs` / `K8G_ROBS` | `D:/VISSIM_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s31` (읽기만) |
| NC 런 묶음 | `--nc3` / `K8G_NC3` | `D:/VISSIM_runs/20261001_v3c3` (읽기만, opt1v2 FZP·INPX) |
| 파이썬 / sdmpc 의존성 | `K8G_PY` / `K8G_DEPS` | 실행 중인 인터프리터 / `.review-deps` |

출력 루트 아래 배치는 스크래치 폴더와 같습니다. 그래서 `--root <k8>/r --out <k8>`이면 스크래치 하네스를 그대로 가리킵니다.

```
replays/<T>/                      prep.py
out/<T>/cap_<variant>/            capture.py
out/<T>/jobs/<label>/             jobs.py (+ hook/)
out/<T>/full_<label>/             full.py (+ hook/)
out/an_*.json, out/<T>/an_*.json  an_*.py
opt1v2/data/, opt1v2/out/         opt1v2/*.py
tuning/                           capture.py lgk 가 만든 튜닝
tmp/                              자식 프로세스 TEMP
```

## 도구

| 도구 | 입력 | 출력 |
|---|---|---|
| `k8common.py` | – | 공용 경로·환경. `--print-config`(경로 점검, 쓰기 없음), `--print-out` |
| `prep.py <T…>` | R-obs `decisions_*` | `replays/<T>/` (사본만, `make_replay_state_v2.prepare`) |
| ● `capture.py <variant> <T…>` + `cap_child.py` | `replays/<T>`, 코드 루트 어댑터 | `out/<T>/cap_<v>/{template.pickle, capture.json, capture_log.txt}`. variant `base·s5·s9·s59`(투영 패치, 메모리에만 컴파일) · `lgk`(튜닝에 `lane_group_kinds` 4종) |
| ● `jobs.py <T> <cap> <label> <mode> <action> <patches>` + `worker.py` | `cap_<cap>/template.pickle` | `out/<T>/jobs/<label>/{result.pickle, brief.json, log.txt, hook/}`. 패치 `s1·s3·s3f`, 행동 `REF·M2ALL·M2E·M2W·M5ALL` |
| ● `full.py <T> <label>` | `replays/<T>` | `out/<T>/full_<label>/{action_T.*, run.json, hook/}` (배포 결정 + 수동 훅) |
| `an_jobs.py <T…>` | `jobs/*` | `out/an_jobs.json` (S1·S3·S5·S9 짝 차) |
| `an_proj.py <T>` | `cap_{base,s5,s9,s59}` | `out/<T>/an_proj.json` |
| `an_fid.py <T…>` | `jobs/REF_*`, `cap_base`(T+150) | `out/an_fid.json` (한 스텝 큐·저장 충실도) |
| `an_ramps.py <T…>` / `an_s9split.py <T…>` / `an_lgk.py <T>` | `cap_base`(·`cap_s9`·`cap_lgk`) | `out/an_ramps.json` / `out/an_s9split.json` / `out/<T>/an_lgk.json` |
| `s6_scan.py` | 런 폴더 `runlog_*.txt` (봉인 시드 경로 제외) | 표준출력 |
| `s7_links.py` | 코드 루트 geometry, R-obs `obs150/err_*.jsonl` | 표준출력 |
| `roots.py` / `pinlen.py` | 코드 루트 config·plant·reference JSON | 표준출력 (사본에 필요한 하위 트리 / 259자 넘는 경로) |
| ● `chain1-4.sh` | – | DEFECTS 측정 순서 기록(위 도구 호출). 로그는 `"$OUT/out/chainN.log"`로 받음 |
| `site/sitecustomize.py` | `K8_LONGPATH=1`, `K8_HOOK_DIR` | 장경로 shim, 수동 계수 훅 → `hook/hook_<pid>.json` |
| ● `opt1v2/x2_extract.py <seed…>` | NC FZP (31·41·43·47·53만) | `opt1v2/data/e_s<seed>_{v1,ext}.parquet` |
| `opt1v2/g2_inpx.py` | NC INPX 5시드 | `opt1v2/out/g2_inpx_v3c3.json` |
| ● `opt1v2/a1v2_visit.py` | `e_s*_ext.parquet` | `opt1v2/out/a1v2_visit.json`, `a1v2_cycles.csv` |
| ● `opt1v2/a1_v1rule_v3c3.py` | `e_s*_v1.parquet` | `opt1v2/out/a1_v1rule_v3c3.json`, `a1_v1rule_cycles_v3c3.csv` |
| `opt1v2/s2_lanefull.py` / `opt1v2/p4c_states_grid9_v3c3.py` | `e_s*_ext` / `e_s*_v1` parquet | `opt1v2/out/s2_lanefull.json` / `p4_states_grid9_v3c3.json` |

opt1v2 도구는 `--data DIR`로 parquet 폴더를 바꿀 수 있습니다(기본 `<out>/opt1v2/data`).

## 점검(가벼움)

```
python -B k8common.py --print-config
python -B capture.py --dry-run base 2700        # 어댑터 명령줄만 출력
python -B jobs.py --dry-run 2700 base REF_scalar scalar REF -
python -B <tool>.py --help
```

## 이식 메모

- 바꾼 것: 하드코딩 경로(스크래치 루트 `k8/r`, `k8/out`, `k8/replays`, `k8/opt1v2`, FRZ_K7, R-obs·NC 경로)를 위 인자로 바꿈. `worker.py`는 `K8G_ROOT`(jobs.py가 넘김)를 씀. `--help`·`--dry-run` 추가. 계산 줄은 그대로입니다.
- 선언 docstring은 바이트 그대로라 선언 sha16이 같습니다: `a1v2_visit` 211a48c6b3e3f450, `s2_lanefull` 5864d5b1d518c34e, `a1_v1rule_v3c3` 77304deded2de68a. 파일 sha는 경로 처리 때문에 원본과 다릅니다.
- `lgk` 튜닝은 코드 루트 `config_n31_v2.json`에서 만들어 `tuning/`에 씁니다(indent 2, CRLF). bd39205 config에서는 스크래치 `config_n31_v2_k8lgk.json`과 바이트가 같습니다. config 안 상대 경로는 어댑터 작업 루트 기준이라 튜닝 위치와 무관합니다.
- `cap_child.py` s5는 127 포함 모든 contiguous·stopped_instant 링크에 적용합니다(K8_REVIEW B7: K8-4도 127 포함).
- 자식 환경은 R-obs provenance의 `RW_*`를 그대로 씁니다(`RW_OBS150_DETECTORS`는 FRZ_K7 경로, sha 고정). numba 캐시와 탄젠트 캐시는 코드 루트 안 `__pycache__`·`__tangentcache__`(gitignore, 동결 제외)에 생깁니다.
- 옮기지 않은 것: `fixdoc.py`(DEFECTS.md 문구 수정용 일회성), 스크래치 결과물.
- 원본 sha256 앞 16자: k8common a33664b0c7ece912, prep 5ffaeba95ee3b31d, capture 552a5a2a005e96d0, cap_child 9b75189b4e5c06b3, jobs c35994c041e0f997, worker 0c1eba192b123474, full 0386f830e74f2ef8, an_fid 57d26b8fca38201f, an_jobs 0d4762138644dbe1, an_lgk f7ed23c783c5a2f8, an_proj af08156c3575733e, an_ramps c2fdbedfa4deb1f2, an_s9split 82b437417c9e3385, s6_scan 61a48c9cb15ca99c, s7_links 84fd3cd5207ae198, roots 90e577d163dc4c3a, pinlen 8707a2d54407345c, chain1-4 5cf134777aacf32c·7b992550f0da60c4·648cd3420ae7dcb2·1cc60c757adda69d, sitecustomize 8b02b81182b7030e, x2_extract 4474bcbb5750b2a9, g2_inpx b1615bae0f0d8263, p4c_states_grid9_v3c3 3a7ba0f016ff20d9, s2_lanefull 749d451277a4dd02, a1v2_visit ef650b91960cf061, a1_v1rule_v3c3 1460516b3eb91d22.

## K8-0b (S3 계수 훅·K8-2 관문 도구, 보충 1 §D)

K8-2 관문 전에 넣는 도구 커밋입니다. 런타임 코드는 0줄입니다.

| 도구 | 내용 |
|---|---|
| `s3site/sitecustomize.py` | S3 31곳 수동 LINE 훅. 스크래치 `amend1/s3/site/sitecustomize.py`(sha16 69c3665e29f716cf)의 이식. 바뀐 것은 머리 주석, 위치 표 두 벌(`SITES_K81` = 원본 행 바이트 그대로, `SITES_K82` = DEFECTS §4 여섯 행을 K8-2 커밋의 줄·문구로 옮김), 환경변수 `K8_S3_ANCHORS`(k81 기본·k82)로 고르기, `EXTRA['anchors']` 기록뿐입니다. 위치 id는 K7 줄 번호를 그대로 써서 두 표를 행끼리 비교합니다 |
| `s3run.py` | `job`(스칼라·대리 AD·비대리 AD)과 `full`(배포 결정 전체). `jobs.py`·`full.py`와 같은 워커·어댑터·환경이고, PYTHONPATH 첫 칸만 `s3site`로 바꿉니다. `--anchors`는 필수. 스크래치 `amend1/s3/tools/run_s3.py`(sha16 cb288a34b0ef3233)의 이식 |
| `an_s3.py` | 런 폴더 하나의 훅 파일 집계 + 정방향 스윕 검증. 스크래치 `an_s3.py`(sha16 6369c050539c79a6)와 docstring만 다릅니다 |
| `table_s3.py` | 4런 표(JSON·markdown). 스크래치 `table_s3.py`(sha16 e9e46d4ee6744cc7)와 같은 칸, 런 목록·출력은 인자 |
| `k82_gate.py` | K8-2 판정기(읽기만). 선언값(보충 1 r2 §2 K8-2 (a)–(f))은 코드 상수입니다 |
| `worker.py` | mode `ad_full`(비대리 역방향 AD: 스칼라 증인 + 탄젠트 + 전체 `state_error`; 진단 전용 옵션 `central_multiplier`·`prediction_hotpath`만 그 프로세스에서 끔, S1_OWNER §5 방식). 결과에 `max_primal_state_error`·`complete_primal_state_match`·`trace` 등을 더하고, `area_leader_objective.shared_urban_quantities`의 소유자별 `accepted_event_count`·`net_inflow_veh` 원시값을 수동 기록(`kind_service`) |
| `capture.py` / `jobs.py` | `--cap-label`(여러 코드 루트를 한 출력 루트에 포착) / mode `ad_full` 허용 |

- K8-2 관문 배치(출력 루트 하나: replay 경로가 모든 팔에서 같도록)
  - `out/<T>/cap_k81base`, `cap_k82` : K8-1 런타임(기준)·K8-2 후보 포착
  - `out/<T>/jobs/k81_<A>_<mode>`, `k82_<A>_<mode>` : `s3run.py --anchors k81|k82 job`
  - `out/2700/full_k81`, `full_ctrl`, `full_k82` : 배포 결정. ctrl = 기준 + 고친 네 파일 끝에 주석 한 줄(줄 번호 불변, 원천 해시만 바뀜)로, 원천 해시에서 나오는 실행 출처 경로를 판정 전에 실측합니다
  - `k81_table_s3.json`, `k82_table_s3.json` : `table_s3.py`(2700 REF ad, 2700 M2ALL ad, 4950 REF ad, 2700 full)
- 판정: `python -B k82_gate.py --out <출력 루트> --k7 <스크래치 k8> --unit-log <pytest 로그> --json <판정.json>`
