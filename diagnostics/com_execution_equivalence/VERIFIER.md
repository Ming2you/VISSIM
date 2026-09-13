# 완료된 old/fast pair 검증

`verify_pair.py`는 정본 run 폴더 두 개만 읽는 후처리 CLI다. 실행기나 설정 DSL은 없다. 아직 실제 pair를 읽거나 실행하지 않았다. `test_verify_pair.py`의 3초짜리 합성 파일이 검토용 fixture다.

```powershell
& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -X utf8 `
  diagnostics/com_execution_equivalence/verify_pair.py `
  --left evaluation/runs/<old-name> --right evaluation/runs/<fast-name> `
  --left-receipt-sha256 <actual-old-completion-receipt-sha256> `
  --right-receipt-sha256 <actual-fast-completion-receipt-sha256> `
  --out diagnostics/com_execution_equivalence/<new-pair-result>.json
```

왼쪽은 write-on-change=0/readback=1, 오른쪽은 1/0이어야 한다. 두 arm 모두 같은 새 정본 VBS와 VSL logger, 같은 config/network/demand/SIG/source 및 RW_PERF 등 나머지 환경을 사용해야 한다. 기존 `selected_control_completion.py`의 `selected-control-completion/v1` receipt를 사용한다. 외부 watchdog 종료 0을 cscript 종료 0으로 바꾸지 않는다. 실제 receipt SHA, run ID/경로, provenance SHA, 종료 마커·실패 카운터·끝 state CSV를 확인한 뒤 payload를 읽는다. 미완료는 FZP를 열기 전에 실패한다.

정본 폴더 규칙으로 유일 FZP/LSA, `decisions_<name>/signal_readback.csv`, `vsl_readback.csv`, 모든 `action_<sec>.csv/.json` 및 `state_<sec>.json`을 찾는다. 결정 시각은 정확히 `{1} ∪ {control_interval, …, end}`여야 한다. 양쪽에서 같은 중간 결정을 빠뜨려도 실패한다. head-OFF event 모드는 지원 범위 밖이다.

state의 `run_provenance.manifest_path`와 action의 정본 v2 `run_provenance.inputs`는 서로 다른 스키마다. state는 자기 run ID·manifest 경로를, action은 schema_version=2·자기 run ID·`run_manifest_json`과 바로 그 시각 `state_json`의 path/SHA/exists를 완료 receipt 및 읽은 state bytes와 대조한다. action에 state의 간단한 identity만 넣는 fallback은 허용하지 않는다. 최초 실제 signal pair v1의 `KeyError: manifest_path` 실패 결과는 보존했으며, 수정 후 작은 JSON/CSV만 읽은 9개 결정 비교는 `signal_head_inputs_schema_v2.json`에 남겼다. 이 작은 검사는 FZP·LSA·readback 재검증 결과를 대신하지 않는다.

| 별도 판정 | 비교 범위 |
|---|---|
| 완료·출처 | 기록된 모든 file/source/SIG SHA 및 입력 경로 exact. 예외는 위의 두 RW 환경값뿐. 출력 경로·run ID·생성 시각·Git/workspace 메타데이터는 물리 입력 동치로 쓰지 않는다. 현재 checkout을 전수 재해시하지 않는다. |
| 명령·상태 | 같은 시각의 ordered CSV actuator 열, 7개 최종 control JSON 필드. CSV metadata 및 JSON metadata/prediction/diagnostics 제외 목록·SHA를 별도 보고한다. state는 실제 r02 raw의 19개 물리·수요·관측·history 키 전체를 exact 비교하며, 확인한 run_provenance만 제외한다. |
| FZP | 해당 pair의 파일 각각 1회 streaming. pre-data metadata·빈 줄·CR/LF만 제외하고 모든 ordered data bytes 및 header를 비교한다. 첫 차이의 행/시각/원문, 다른 행 수, 양쪽 전체 행 수·SHA·범위를 남긴다. 다른 과거 전체 FZP는 읽지 않는다. |
| SG readback | 실제 CSV의 requested/readback/ok 검증. 명령 CSV에서 제어 SC와 최초 적용 시각을 얻고, receipt.preparation_checks에 pin된 generated `_sgplan.vbs`의 `RW_SIGNAL_SG_EXPECTED` 및 실제 `RW_MAINLINE_SG_ONLY` 필터로 소유 SG 전체를 도출한다. 따라서 명령의 비영 창 122개 외 RED-only 14개도 포함하며 이 그룹은 RED만 허용한다. 관측 CSV에서 미지 그룹을 추측하지 않는다. 같은 주소의 반복 hold만 제거하며 전이 시각·post_step/immediate·전역 순서는 유지한다. old에는 매초 immediate[start,end), post_step(start,end] 누락 검사가 있다. 양쪽 모두 최초/변경 immediate 다음 1초의 같은 요청값 post와 소유 중 제어 경계 post를 요구한다. 같은 시각의 마지막 요청값이 기준이며 terminal 새 쓰기는 다음 step이 없다는 예외를 명시한다. fast의 희소 hold를 연속 관측으로 인증하지 않는다. |
| VSL readback | `sim_sec,dsd_no,veh_class_no,requested_kph,readback_distribution_no,ok,stage`. 실제 command마다 10/20/30/70의 네 setter-immediate 행을 요구한다. 정본 setter가 요청 정수를 분포 No로 쓰는 계약으로 예상 mapping을 명령에서 만들고 대조한다. 분포 참조값은 관측 차량 속도가 아니며 네 행은 동시 snapshot이 아니다. |
| 독립 명령 시계 | 각 arm의 실제 ordered CSV batches를 별도 `CommandClock`에 전달한다. provenance에 pin된 정본 VBS/생성 config의 10초 meter cycle·1초 meter amber·3초 urban amber 및 meter capacity를 확인한다. **모든** SG 행은 immediate t의 최신 명령/시계 또는 post-step t−1의 최신 명령/시계와 대조한다. 다른 SG가 GREEN일 때 AMBER 억제, RED-only, meter 정수 green 양자화를 기존 정본 oracle에서 재사용한다. VSL도 해당 DSD·실제 적용 시각의 CSV 값과 직접 대조하므로 다른 시각에 허용됐던 값으로 대체하면 실패한다. |
| native LSA | 실제 SG readback의 초기 상태·전이에 대응하는 같은 시각/SG/state native event가 있는지 별도로 검사한다. 명령이나 의도 clock을 LSA 대신 쓰지 않는다. 누락 COM coverage는 **FAIL**이며 실제 readback/FZP 통과를 숨기지 않는다. LSA 자체에는 pre/post 단계가 없어 단계 동치 증명이 아니다. |

최종 `passed`는 모든 판정이 통과해야 참이다. `actual_execution_equivalent`와 `native_lsa_com_coverage_passed`를 따로 읽어야 한다. LSA가 COM 전이를 기록하지 않는 현재 알려진 한계라면 전자는 참, 후자는 거짓일 수 있다. exit code는 이 경우에도 1이며 JSON은 보존된다. 기존 출력 파일에는 쓰지 않는다.

현재 r02의 provenance `files` 17개는 모두 exists=true다. 존재하지 않는 optional 항목은 `detector_mapping`이라는 명시 키에서만 exists=false/빈 SHA/양쪽 동일 경로를 허용하고 결과에 적는다. network/config/demand/정본 소스 등의 누락은 계속 실패한다. SG plan의 현재 파일을 역사적 pin으로 간주하지 않으며, 두 arm의 실제 preparation checks에 해당 sibling 파일 SHA가 있어야 한다.

기존 `audit_observed_nc_trajectory`의 SHA helper와 ordered payload 정의를 재사용했다. 기존 LSA producer는 5400초 고정 또는 malformed 행을 건너뛰므로 이 짧은 엄격 coverage 검사에 그대로 호출하지 않았다. 이 파일의 작은 9열 parser는 같은 native 형식을 검증한다. 새 clock/모델/COM/FZP 분석 프레임워크는 없다.

`command_clock.py`는 `live_beta0_first_interval_audit.expected_signal/expected_ramp`와 `signal_timing_oracle.decisions_from_action_rows`를 재사용한다. 이벤트 기반 continuous 모드에 t−1 규칙을 적용하지 않는다. 전체 `verify` 경로는 이 실제 checker를 반드시 구성한다. 순수 coverage 반례 중 두 개만 명시적인 테스트 callback으로 pending/terminal 규칙을 따로 검사하며, 실제 pair 경로에는 검사 생략 옵션이 없다. `command_clock_left/right` 성공과 각 readback의 `independent_command_clock_rows_checked`가 결과에 남는다.

고정 명령 pair 통과는 폐루프 제어 동치나 속도 향상을 자동 입증하지 않는다. 별도 wu-link pair에서도 같은 관측과 모든 최종 제어를 확인해야 한다. 양쪽 모두 새 VSL logger와 중복 summary-read 제거를 공유하므로 이 비교로 그 이전 2회 read 제거의 절감 시간을 측정했다고 주장하지 않는다.

합성 회귀 실행:

```powershell
& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -X utf8 -m unittest diagnostics.com_execution_equivalence.test_verify_pair diagnostics.com_execution_equivalence.test_command_clock -v
```
