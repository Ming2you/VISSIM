# 완료 제어 런의 native LSA 기록 범위

**현재 설정의 native LSA는 COM 신호 실행 증빙을 대신할 수 없다.** 완료된 `codex_area_sources_beta0_s13_20260910`의 LSA에는 제어 시작 900초 이후 아래 144개 SG의 전환이 없지만, 실제 COM readback에는 901–1050초 사이 도시 신호 348회·미터 88회의 상태변화가 있다. 명령 CSV로 누락된 LSA를 보충하지 않았다.

| 범위 | 실제 readback SG 수 | 901–1050 연속 1초 readback 간 상태변화 | 해당 SG의 900초 이후 LSA event |
|---|---:|---:|---:|
| 도시 | 136 | 348 | 0 |
| 미터 9101–9108 | 8 | 88 | 0 |

각 SG는 이 구간에 post_step 150개·서로 다른 시각 150개가 있으며 actual=requested, ok=1이다. 전환 수는 901초부터 인접 post_step 샘플을 비교한 값으로, 901초 진입 전환과 초 미만 시각은 포함하지 않는다. 전체 제어 런의 모든 전환 수라고 일반화하지 않는다.

- SC1004/SG5: LSA 마지막 행은 900초 RED. 실제 readback은 968초 GREEN, 992초 AMBER, 995초 RED로 변한다. LSA에는 세 전환이 모두 없다.
- 미터 SC9103/SG1: LSA에는 1초 OFF 한 행뿐이다. 실제 1초 immediate readback은 GREEN이고, 904초 AMBER·905초 RED·911초 GREEN 등 반복 전환이 기록되어 있다. 다른 7개 미터도 LSA는 초기 OFF 한 행뿐이다.
- action900의 도시 `signal_sg` 주소는 122개다. 런타임 readback에는 14개가 더 있다: 7:{2,3,5,6}, 16:{1,5}, 107:{4,8}, 108:{3,7}, 109:{1,3,4,8}. 이 14개는 LSA 전체에도 없다. 명령 행 수와 런타임 검사 대상 수를 구분하며, 추가 SG에 실제 signal head가 있다는 뜻으로 해석하지 않는다.

완료 증빙은 run_id `329913b3a1a747948d4b5196242254c5`, watchdog OK, SIM_DONE, 최종 SIM_SEC=5400, 5개 실패 counter=0이다. native LSA 1,631,388 bytes 전체에서 19,773 event·291 SG·1–5400초·모든 mode `Fixed Time`을 확인했다. 42.97 MB readback은 최초 1051초 행까지 1,912,770 bytes만 읽었고 그 prefix SHA와 원본 파일 크기/mtime을 보존했다. FZP·COM·모델 실행은 없었다.

## 현재 설정과 문서 범위

원 INPX의 `sigChgs.writeFile=false`는 런타임 VBS `ConfigureEvaluationOutput`에서 `SigChangesWriteFile=True`로 설정된다. 이 완료 런의 로그도 `NATIVE_EVAL=1 ... sigChanges=1 ... resolution=1`이다. 출력 스위치를 켜지 않아서 생긴 전체 파일 부재가 아니다. 도시 SC는 FIXEDTIME/VISSIG_Controller.dll/native SIG를 사용하며 미터 9101–9108에는 공급 SIG 파일이 없다.

설치된 PTV 2020 `Doc/Eng/attribute.xlsx`의 SignalGroup.SigState/ContrByCOM 및 Evaluation.SigChangesWriteFile/Database를 확인했다. SigState를 쓰면 ContrByCOM이 true가 되어 정상 신호 제어를 무시한다는 계약이 있다. 확인한 SignalGroup 전체 속성과 SigChanges 두 속성에는 COM 전환을 LSA에 별도로 포함시키는 스위치가 없다. 다른 API의 부재까지 증명한 것은 아니다. COM CHM은 찾았으나 제한된 추출 시도에서 읽을 파일이 나오지 않아 전체 CHM 검토로 표시하지 않는다.

[PTV의 신호 변경 평가 문서](https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/11_Auswertungen/AuswertungLSAUmschaltungen.htm)는 일반 신호 변경의 행 기록을 설명하며 COM 직접 쓰기의 포함 여부는 명시하지 않는다. 현장의 누락 증거를 문서의 일반 표현으로 무효화할 수 없다.

## COM 비용 축소에 필요한 최소 계약

현재 VBS의 `SetSignalGroupState`는 실제 setter 뒤 SigState를 읽고 immediate 행을 쓴다. `ValidateRuntimeSignalPersistence`는 기록된 requested SG를 다시 읽어 post_step을 남긴다. `RW_SIGNAL_WRITE_ON_CHANGE=1`의 동일 요청 생략 경로는 COM 쓰기와 읽기를 모두 생략한다. 따라서 변경 시 setter+immediate readback, 초기 미터 및 도시 인계 시각 readback, 변경 직후 첫 post_step readback, 결정 경계·종료 검사를 유지하는 것이 작은 축소 후보이다. **이는 미관측 매초의 상태 지속을 증명하지 않는다.** 1초 전 구간 증빙을 요구하면 동일 주기의 실제 읽기가 필요하며, 배치 읽기로 줄이는 별도 방안은 실제 API/런 검증 뒤 판단해야 한다.

`RecordSignalReadback`은 파일 기록 전에 `ObservationSignalReadback`도 호출한다. 읽기 주기 축소가 head 관측의 실제 GREEN 노출 분모를 바꾸지 않도록 독립적으로 보존해야 한다. VBS 3614–3634/4505–4520 부근의 native LSA가 지속 readback을 대신한다는 주석은 이번 증거와 맞지 않으며 차기 수선 때 정정 대상이다. 생산 파일은 수정하지 않았다.

상세 값·파일 SHA·SG별 증거는 [coverage JSON](<C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.worktrees/control-full-review/diagnostics/controlled_native_lsa_coverage.json>), 문서 속성의 행 번호와 SHA는 [documentation JSON](<C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.worktrees/control-full-review/diagnostics/controlled_native_lsa_documentation.json>)에 있다. 재현기는 [audit_controlled_lsa_coverage.py](<C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.worktrees/control-full-review/diagnostics/audit_controlled_lsa_coverage.py>)이며 한 완료 런의 작은 파일·제한 prefix만 소비한다.
