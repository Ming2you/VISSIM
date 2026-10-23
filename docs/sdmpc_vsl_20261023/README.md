# S-DMPC / VSL / 셀별 보정 전달 — 2026-10-23

10월13일 게시한 **도시부·고속도로부 전체 채택355 플랜트와 공동/영역별 S-DMPC**를 유지하면서 이후 작업을 추가했다. 이 전달은 새 native 실행이나 플랜트 보정의 완료 선언이 아니다.

## 현재 사용할 코드

- 기존 공동제어 window/optimized/off와 자기 정보만 사용하는 freeway_only/urban_only는 [10월13일 안내](../sdmpc_plant_20261013/README.md)를 따른다. 영역별 정보 격리 코드를 이전 개발 스냅샷으로 덮어쓰지 않았다.
- `evaluation/controllers/vsl_schedule_neighbors.py`와 `sdmpc.py`는 `sdmpc_vsl_schedule_audit=true`일 때만 유한 VSL 스케줄을 추가 검사한다. 단일 구역90을2/3블록 유지, 인접 구역/방향전체/양방향3블록을 표준8구역에서 최대25개 검사한다. 개별 후보의 손익과 무관하게 결합 후보를 평가하며, 동일 비용·NP/NUF cap·물리/액추에이터 제약을 쓴다. 강제 활성화 보상이나 모델 계수 변경은 없다.
- 별도 실험 설정은 `diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/vsl_schedules_20261015/config.json`이다. 기존5개 운영 설정에는 이 옵션을 켜지 않았다. 영역별 모드와 새 탐색의 조합은 새로 native 검증한 조합이 아니다.
- 정본 pair runner/analyzer는 검증된 제어 prefix와 기존 baseline의 재사용, 명시적 이전 명령 유지/사용자 중단 증거를 구분한다. 명령표·회복 기록만으로 실제 실행을 통과시키지 않고 native readback/LDP·prefix·소유 종료 확인을 유지한다.

## 저장 방식

`tools/sdmpc31/runtime_package.py prepare`로 실제 config/protocol과 명시적 추가 입력을 선택하고 해시를 기록한다. `freeze_worktree.ps1`에는 **InputManifest가 필수**다. 필요한 입력만 드라이브별 SHA256 공유 저장소에 한 번 보관하고, 동결본은 읽기 전용 하드링크로 참조한다. 편집 가능한 소스는 독립 파일이다. 실행 중 수정하는 INPX/SIG는 runner가 결과 폴더에 별도로 복사하여 쓰기 가능하게 한다.

공유 저장소와 동결본은 같은 볼륨이어야 한다. 같은 네트워크는 재사용하고 내용이 달라진 버전은 다른 해시로 보존한다. 외부 의존 자료는 해시를 검증하되 자동으로 복제하지 않는다. `_archive`와 과거 결과/분할 자료는 실행 입력에 자동 포함하지 않는다. 기존 큐 스크립트가 InputManifest 없이 freezer를 호출한다면 그대로 재개할 수 없다. 기록된 실행 영수증/STOP을 보존하고 새 준비 단계에 명시적 manifest를 연결해야 한다.

```powershell
# 사전 확인만: VISSIM 또는 최적화를 시작하지 않는다.
python -B tools/sdmpc31/verify_publication.py
python -B scripts/verify_parameters.py diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/vsl_schedules_20261015/config.json
```

## VSL 및 셀별 보정의 실제 상태

| 검사 | 확인한 결과 | 채택 상태 |
|---|---|---|
| 저장 상태 유한 VSL 탐색 | 54개450초 예측과 전체 선택1회. 새25후보는 feasible이나 예측 이득이 없어서110 유지. 전체 선택395.413초 중 추가 검사38.55초 | 탐색 기능만 opt-in. native 개선/수렴 증명 아님 |
| 동일 도시/RM 조건의 두 구역90 실험 | 수정된 명령의2700초 종료·prefix·실행 검증. 2250–2700 조건부 반응 비교 | 전체8100 정책 이득과 다름 |
| 셀16–18 개별 계수, 최대25% 갱신 | 결합450초 학습 오차29.9% 악화 | 기각 |
| 같은15개 민감도, 최대5% 갱신 | 학습 종합오차3.53% 감소, seed29 VSL 통과량 변화는 실제+31대/기존−28.87대/후보−29.35대 | 미채택 |
| 계수 고정 후 seed67·71 검사 | 재고·속도 종합오차0.89% 악화. seed67의 실제+33대에 대한 예측은+8.14→+1.92대 | 미채택, 검증 seed에 재적합하지 않음 |
| 동서62셀 관측범위 | 기존900–8100초49시각의 자유류/정체/회복 범위 집계 | 계수 식별 완료나 전 셀 보정 완료 아님 |

3.53%와0.89%는 정규화한 재고·속도 오차의 변화이며 TTT 개선율이 아니다. 5초 조건부 적합과450초 자율 예측도 구분한다. 작은 VSL 이득의 부호를 강제로 맞추는 계수/보상을 넣지 않았다. 다음 과제는 셀별 자료 범위와 식별 가능성을 고려한 에피소드 단위 보정이며, 보정 목표는 미완료다.

## 보존한 기록과 재현 범위

`diagnostics/_archive/vsl_multiblock_20261015/`에는 탐색·native 비교·CDF/공간분할 후보·셀별 추정 스크립트, 실패와 채택 판단, 작은 요약을 보존했다. 최신 결과는 `cellwise_independent_20261020/README.md`, `assessment.json`, `cellwise_coverage_20261020/coverage.json`에 있다. 경계 관측 위치 차이, LSA 누락/LDP 대체, 정상 유출과 종료 잔여, 도시·램프·외부 대기는 각 원 결과의 한계를 유지한다.

`diagnostics/_archive/storage_layout_20261019/`는 완료한 공유 저장소 이전의 코드와 검증 요약이다. **과거 실행·이전 스크립트를 일괄 실행하지 않는다.** 역사적 로컬 경로·PID·hash는 감사 기록이다. 삭제/중복 제거를 이 게시 작업에서 다시 수행하지 않았다.

원래의 FZP·피클·관측 캐시·실행 패키지·지도·네트워크 중복 사본과 거대한 반복 JSON은 이 증분에 포함하지 않았다. 보관한 연구 스크립트는 기록된 외부 입력과 원 소스 환경이 있어야 재현되며 새 checkout만으로 모든 과거 실험을 재실행할 수 있다는 주장이 아니다. `source_provenance.json`은 추가 파일의 출처를, `source_manifest.json`은 기존 전달 위에 적용할 해시를 기록한다. 원10월13일 manifest/검증 영수증은 보존했다. 이번 빠른 회귀 검증은 별도 `publication_validation.json`에 기록한다.
