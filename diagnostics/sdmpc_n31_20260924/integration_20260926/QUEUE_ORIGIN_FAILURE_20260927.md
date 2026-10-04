# 3600초 실행 중단: 접근로 큐 연결 수정

추가 METANET 계수 보정은 하지 않는다. 세부 속도·궤적의 정확한 일치보다 제어 후보의 의미 있는 이득/손해 방향, 대기 비용, 실제 실행을 판단한다. 거의 같은 비용의 후보를 재보정하지 않는다.

## 완료된 실행과 실패

`D:/VISSIM_runs/20260927_sd31_wiring9000/nc`는 9000초 완료. 같은 큐의 SDMPC는 3450초 명령 적용 후 3600초 예측에서 종료됐다. session61765 exit1. 두 결과와 원래 동결본은 보존하며 실패한 제어 런을 완료 결과로 사용하지 않는다.

실패: `MembershipError: unresolved destination of movement:SC5_S_to_N_SC102: (None, None)`.
실측 `state_003600.json`, `action_003600.error.txt`, 직전 실제 `action_003450.json.applied`가 근거다. 고정 명령 450초 일반 예측에서도 같은 오류를 재현했으므로 미분 전용 오류가 아니다.

## 원인과 수정 범위

물리 링크1220011103은 SC11_to_SC5 접근로다. 기존 교차로 단위 detector 목록이 그곳의 큐3대를 반대 접근로와 실제 연결이 없는 `SC5_S_to_N_SC102` 등에도 분할했다. 해당 가상 경로에 0.428571대가 배정돼 차량 보존 장부에서 목적지를 찾지 못했다. 앞서 의심한256번 링크는 직접 원인이 아니며, 기존 native input1097의 저장공간 투영은 이미 연결돼 있었다.

기존 `_queue_origin_filter_enabled`와 물리 origin 필터는 구현돼 있었지만 `install_config_switches`에 연결이 빠져 항상 꺼졌다. 정본 adapter에 설정 연결 한 줄을 추가하고 선택 config에 `urban.queue.origin_filter=true`를 명시했다. 기존 false/미지정 동작은 유지한다. 새 경로 확률, 가짜 목적지, 오류 무시, capacity 변경은 추가하지 않았다.

변경 전 config는 `executed_sources/config_n31_v2_before_queue_origin_d258ba71047b.json`에 바이트 그대로 보존했다. 네트워크·수요·액추에이터·METANET 계수는 불변이다.

## 검증

- 작은 재현 테스트: 수정 전 3개 중2개 실패, 수정 후3개 통과. 반대·가상 접근로 배정 제거, 총 큐와 저장량 보존, 미지정 옵션의 기존 동작 유지.
- 실제 실패 상태의 고정450초 예측: `closedloop_recorded3600_lever450_origin/summary.json`, session77860 exit0. 3개 제어 블록과8램프 보존 검사를 통과했다. 이전 SC5 가상 큐는0이다.
- 잔여 `SC7_E_SC16_to_N_SC11`의 초기큐6.5대는 beta0인 비활성 이동류이며 이번 실패 원인과 구분한다. 전체 도시 경로 모델이 완전하다는 뜻은 아니다.
- 실제 SDMPC 한 결정: `closedloop_recorded3600_select_origin/summary.json`, session15887 exit0,354.57초. 예측·237축 미분·선택·명령 binding 통과. Ω 예측 비용541.237718→539.287239대·시간(−0.3604%). N_P/N_UF 수량 제약 feasible, 유한 반복 수렴 인증은 없고 실측 이득도 아니다. 미세한 비용 차이 추가 보정 없이 실제 실행으로 넘어간다.

다음은 완료된 NC9000의 provenance를 재사용하고, 오류 수정이 검증된 SDMPC만 새 폴더에서 실행하는 것이다. 기존 분석기에 선택적 `--nc-run-dir`만 추가해 데이터 복사·무제어 재런 없이 두 완료 결과를 비교한다. 같은 seed·망·기간·제어 전 궤적 일치를 다시 확인하며, 전체 비용에서 불리하면 그대로 보고한다.

## 수정 후 실제 런

새 고정본 SHA `8d7fab32ae7f862d0bc61ab616d9f8ee3c91264267cd23339464f71067da143b`, preflight session69232 exit0. 제어9000만 session77249로 시작했다. 소스/설정은 실행 중 변경하지 않으며 추가 계산·대형 분석을 병행하지 않는다. `closedloop9000_queue_origin_launch.json`과 상태파일이 정본 실행 포인터다.

완료 후 기존 분석 명령(아직 실행하지 않음):

```powershell
python -B diagnostics/sdmpc_n31_20260924/integration_20260926/native_pair1200/analyze_pair.py --closed-loop-9000 --runs-root D:/VISSIM_runs/20260927_sd31_queue_origin9000 --nc-run-dir D:/VISSIM_runs/20260927_sd31_wiring9000/nc --output-dir diagnostics/sdmpc_n31_20260924/integration_20260926/closedloop9000_queue_origin_analysis --status-json diagnostics/sdmpc_n31_20260924/integration_20260926/closedloop9000_queue_origin_status.json
```

이후 동일 명령에 `--cached-diagnostics`를 붙여 저장된 집계에서 공간/선택 진단을 만든다. 두 런의 동결본이 다름을 유지하고, 제어 전 FZP 행의 정확한 일치와 명령 실행 근거를 확인한다. 제어 전 일치는 모델 예측이 실제 궤적과 정확히 같아야 한다는 요구와 구분한다.
