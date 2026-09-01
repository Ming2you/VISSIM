# _archive

## Purpose

이 디렉터리는 network topology setting 의 **현재 최종본에는 사용되지 않지만**, 개발 과정 및
과거 작업 추적을 위해 보존한 파일들을 저장한다. 2026-08-19 에 프로젝트 전체를 훑어 분류한 결과다.

## Important

**`_archive/` 내부 파일은 현재 production / final workflow 에서 사용하지 않는다.**
과거 구현, 실험, 설정 또는 중간 결과를 확인해야 할 때만 참고한다.
여기서 파일을 꺼내 최종본 경로에 되돌리지 마라 — 그것이 지금까지 두 번 롤백을 만든 경로다.
현재 최종본이 무엇인지는 저장소 루트의 `CLAUDE.md` 를 봐라.

## Structure

| 폴더 | 파일 | 용량 | 내용 |
| --- | --- | --- | --- |
| `debug/` | 21개 | 0.1 MB | 디버깅 산출 — 예측오차 분해, 상태 비교, 라우팅 감사, 일회성 수정 스크립트 |
| `experiments/` | 82개 | 0.8 MB | 실험·탐색 — forced response, FD 재적합, VSL 프로브, 파라미터 스윕, A/B 비교 |
| `intermediate_results/` | 65개 | 118.1 MB | 중간 산출물 — 옛 세대 canonical topology, 저류/배정 아티팩트, 분석 CSV |
| `legacy_code/` | 20개 | 0.2 MB | 이전 세대 코드 — 8구간 하네스, 옛 워치독/설치 VBS, 승격 전 검증 스크립트 |
| `misc/` | 10개 | 2.8 MB | 위 어디에도 안 들어가는 나머지 |
| `old_configs/` | 18개 | 0.1 MB | 과거 설정 — 옛 세대 tuning/calibration/demand profile |
| `old_docs/` | 20개 | 0.1 MB | 과거 문서 — 인수인계 노트, 리뷰 diff, 초안, 작업 메모 |

각 bucket 아래에는 **원래 디렉터리 구조를 그대로 유지**했다.
예: `outputs/canonical_topology_evaluserfix_20260814b.json` 은
`_archive/intermediate_results/outputs/canonical_topology_evaluserfix_20260814b.json` 에 있다.

## Restore

`manifest.csv` 에 파일마다 `archived_path` · `original_path` · `bucket` · `bytes` · `reason` 이
들어 있다. 되돌리려면 `original_path` 로 옮기면 된다.
되돌리기 전에 그 파일이 무엇으로 대체됐는지 `CLAUDE.md` 의 정본표를 먼저 확인해라.

## 어떻게 골랐나

1. 프로젝트 전체를 7개 영역(scripts .py / 러너·테스트 / evaluation / outputs / plant·tests /
   문서 / network)으로 나눠 훑고 **707개 파일**을 ACTIVE / ARCHIVE_CANDIDATE /
   REVIEW_REQUIRED 로 분류했다.
2. 후보 **343개** 각각에 대해 저장소 전수 검색으로 참조를 확인했다. 파일명 어간이 어디서든
   언급되면 — import, 상대경로, f-string 조립, glob, 문서 언급 무엇이든 — 이동하지 않았다.
3. 참조 0건인 **236개**만 옮겼다. 파일명이 old/test/v2 로 보여도 참조가 있으면 남겼다.

### 옮기지 않은 것

- **참조가 걸린 후보 80개.** 예: 루트의 `review-*.diff` 는
  `.superpowers/sdd/IMPLEMENTATION_PLAN/*.md` 가 이름을 들고 있다.
- **REVIEW_REQUIRED 125개.**
  사용 여부가 불명확해 판단을 보류했다.
- **보호 구역 27개** — `network/` 의 .inpx/.sig 원본과 `reports/`.
  원본 덮어쓰기 금지 대상이라 손대지 않았다.
- **pedovrx / pedfold / jam168 / userfix_20260814e 세대.** 이름은 옛 세대처럼 보이지만
  **살아 있다.** `scripts/build_preflight_manifest.py` 의 `DEFAULT_PATHS` 와
  `plant/src/vissim_strict/run_evidence.py` 의 표가 이 경로들을 못 박고, 그 표가 곧
  `scripts/approve_physical_stock_topology.py` 의 `is_production` 판정이다. 옮기면 승인이
  통과하되 아무것도 증명하지 않는 약한 경로로 조용히 떨어진다. 어댑터도 네 경로를 매 결정
  해시해 `execution_fingerprint_sha256` 에 넣는다 — 없어도 예외가 안 나고 지문만 바뀐다.
- **정본 러너가 provenance 로 해시하는 `*_20260805.json` 3개.**
- **`scripts/run_real_world_single_watchdog_distributed_core15n41*.ps1`** —
  `tests/test_action_csv_contract.py` 가 glob 으로 잡아 존재를 단언한다.

## 이동 후 확인

- 정본 파이프라인 3종 재실행 정상 (`derive_pn_boundary_turns` · `build_urban_input_gate_map_legs4b`
  · `build_pn_boundary_map`), 수치 불변.
- `tests/test_action_csv_contract.py` 는 이동 **전부터** 실패하고 있었다.
  HEAD 워크트리에서 7 실패 / 13 통과, 이동 후 6 실패 / 13 통과. 원인은
  `outputs/signal_group_actuation_plan_v3.json` 과 생성 `*_sgplan.vbs` 의 sha256 불일치이고,
  그 파일들은 이번에 건드리지 않았다.
- `.gitignore` 에 `_archive/**/canonical_topology_*.json` 등을 추가했다. 원 패턴은 `*` 가
  슬래시를 넘지 않아 하위 폴더로 옮기면 무시가 풀리고 118MB 가 추적 대상이 된다.
