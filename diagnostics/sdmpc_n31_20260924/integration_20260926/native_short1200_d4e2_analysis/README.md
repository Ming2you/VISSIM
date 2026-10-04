# δ4/E2 SDMPC1200 연결 확인 — 2026-09-28

짧은 native 연결 검증은 통과했다. 혼잡 구간의 순이득 검증은 아직 완료되지 않았다. 같은 동결본으로 SDMPC9000 런을 시작했다.

- 실행: `D:/VISSIM_runs/20260928_sd31_d4e2_short1200`, seed29, 선택한 80–90 DSD110 망. 네트워크 SHA256 `64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc`.
- 1200초 정상 도달, watchdog 종료 코드0, 소유 PID 4개 종료 확인. 일회성 작업은 종료 확인 후 해제했고 결과는 보존했다. 근거: `process_closure.json`, `task_cleanup.json`.
- `execution.json`: native LDP의 전체 대상 SG/초기 상태/전환과 적용 시 VSL readback 통과. LSA COM 누락은 계속 실패로 남겨 두었으며, 사용자가 허용한 LDP 대체 기준으로 실행을 판정했다.
- `summary.json`: 제어 전 895.1초까지 FZP 데이터 431,233행이 완료된 matched NC9000과 정확히 일치. 비교는 5초 기록의 실제 위상을 유지했다.
- `observation_history.json`: 제어 계산에 사용된8개 관측 시점의 원본·derived·프레임 해시와 VSL 과거 이력/재고 보존 정합 통과. 미래 실측 입력이나 재보정은 없다.
- 900·1050초 결정은 모델의 NP/NUF 제약과 scored-action→CSV binding을 통과했고, 실제 적용은 위 native 증거로 별도 확인했다. 두 첫 명령은 RM g10/VSL110 유지이며 도시 신호가 변경됐다. 이 시점만으로 혼잡 시 RM/VSL 선택 능력을 판정하지 않는다.

| 결정 시각 | own-cost PFO 상한/실행/수락 | SDMPC 상한/실행/수락 | 수렴 |
|---|---|---|---|
| 900초 | 2/2/2 | 2/2/2 | 둘 다 미수렴 |
| 1050초 | 2/2/1 | 2/1/0 | 둘 다 미수렴 |

`decisions.json`의 겹치는450초 예측 이득은 실제 누적 이득으로 합산하지 않는다. 실행 가능한 두 결정의 검증이며 Nash 수렴 증명도 아니다.

runner는 종료 시점1200초에서도 다음 명령을 계산한 후 닫혔다. 그 계산은 이 런의 후속 교통에 쓰이지 않았으므로 위 두 제어 구간 및 교통 효과 집계에서 제외했다. 총 경과1321초에는 이 마지막 계산이 포함된다. 실행 중 동결 코드를 변경하거나 유효한 계산을 중단하지 않았다.

재현 명령(완료 결과를 덮어쓰지 않도록 새 출력 폴더 필요):

```text
python -B diagnostics/sdmpc_n31_20260924/integration_20260926/native_pair1200/analyze_pair.py --short-connection --runs-root D:/VISSIM_runs/20260928_sd31_d4e2_short1200 --nc-run-dir D:/VISSIM_runs/20260927_sd31_wiring9000/nc --output-dir <new-output> --status-json D:/VISSIM_runs/20260928_sd31_d4e2_short1200/status.json
```

다음9000 런: `D:/VISSIM_runs/20260928_sd31_d4e2_9000`. 동결본은 `D:/VISSIM_runs/20260928_sd31_d4e2_runtime/frozen/sdmpc31_886a014a_202609280537`이며 수정하지 않는다. 완료된 NC `D:/VISSIM_runs/20260927_sd31_wiring9000/nc`와 종료 후 비교한다. 전체 Ω TTT·TTD, 외부 체류·미삽입 대기, 삭제, 혼잡 전파와 실제 레버 선택을 확인해야 한다. 목표ACTIVE, 성능 미검증, push 없음.
