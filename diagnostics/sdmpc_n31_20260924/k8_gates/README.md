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
