완료된 signal old r02와 new r01의 전체 경과시간은 **461.835→302.331초**, 159.504초 감소했다. 그러나 old의 수요 설정 readback 지연이 크게 섞여 있어 이를 SG 최적화 효과로 그대로 발표하면 안 된다.

| 구간 | Old 초 | New 초 | New−old 초 |
|---|---:|---:|---:|
| LoadNet | 8.234 | 7.633 | −0.602 |
| 수요 설정 전체 | 105.188 | 2.219 | −102.969 |
| └ setter 전 검증 읽기204회 | 0.516 | 0.055 | −0.461 |
| └ setter 및 오류 처리204회 | 1.555 | 0.906 | −0.648 |
| └ setter 후 검증 읽기204회 | 101.477 | 0.883 | −100.594 |
| 실제 simulation 호출 합계 | 20.570 | 21.773 | +1.203 |
| Python controller9회 | 10.555 | 10.961 | +0.406 |
| Runtime urban signal | 52.523 | 5.672 | −46.852 |
| Runtime ramp meter | 8.805 | 0.070 | −8.734 |
| Post-step persistence 확인 | 35.648 | 1.055 | −34.594 |
| Head capture | 152.711 | 181.328 | +28.617 |

old의 큰 지연은 **input1082, interval1-4 DONE(log189행)→1-5 BEGIN(190행), 101.68초** 구간이다. 이 구간에는 직전 after-read, 집계 작업, 다음 before-read가 포함된다. 단일 getter에 101.68초가 걸렸다고 확정할 수는 없지만, 별도 PERF가 after-read 전체101.476563초를 직접 계측한다. 실제 setter 전체는1.554688초였다.

양쪽 wall에서 각자의 after-read만 빼면 **360.359→301.448초(−58.911초)**, 전체 수요 설정을 빼면 **356.648→300.112초(−56.536초)**다. LoadNet와 수요 설정 전체를 모두 빼면348.413→292.479초(−55.934초). 이 값들도 초기화·정리·폴링·기타 작업이 남는 산술적 잔여이므로 순수 SG 실행시간이나 반복 실험의 안정적 speedup은 아니다. Wall은 wrapper 시작부터 종료 확인까지이며 startup·cleanup을 포함한다.

계측된 SG setter와 apply-read는 각각 **50608→876회**, persistence read는50392→1186회로 감소했다. 반면 head 직접 SigState read는104700→135857회 증가했고, head owner read는186436→137839회 감소했다. `CaptureHeadSignalStates`는 같은 초의 `obsActual` 캐시가 없을 때 직접 읽으므로, persistence 확인을 줄이면 관측이 그 결과를 재사용하는 기회도 줄어든다. Head signal capture79.508→108.031초 증가는 이 비용 이동과 부합한다. 이는 관측을 끈 결과가 아니다: 양쪽 head capture/history/seal 각1200회, physical bulk 반환4800회, route bulk 반환36회가 같다.

VSL setter/read는 양쪽 각각2376회로 같다. 두 arm 모두 같은 수정 소스·VSL sidecar·RW_PERF=1이며 차이는 `RW_SIGNAL_READBACK_SEC` 1→0과 `RW_SIGNAL_WRITE_ON_CHANGE` 0→1뿐이다. 따라서 이번 비교는 SG 반복 쓰기·확인 감소를 주로 측정하고, 공통 소스에서 이미 제거한 두 VSL summary read 비용을 별도로 측정하지 않는다.

**중첩 계측을 합산하지 않는다.** 수요 전체는 세 하위 구간을, decision.total은 state.json/Python/action.apply를 포함한다. Head capture는 vehicle scan/signal capture를, head seal도 signal capture를 포함한다. COM `sec=0`은 미계측 count 표기이며 실제 latency0이 아니다. 카운트는 이름 붙은 계측 지점만 포괄하고 GetAll·객체 열거/해결·일부 소유권/Count/SimSec getter 및 오류 경로를 제외한다. 별도 postprocessing 시간은 없다.

사용한 작은 도구는 `compare_timing.py`다. 실패한 old r01은 제외하고, 명시한 성공 완료 receipt의 wrapper/provenance/runlog만 읽는다. 완료·외부 exit0·owned native 종료·SHA·terminal marker·실패 카운터0을 확인한 뒤, 기존 `verify_pair.provenance_comparison`으로 기록 source/config/env124필드를 대조했다. 두 arm 합8개 작은 파일은 재확인 시 변경0이었다. FZP/LSA/ERR/state payload, 모델, COM, 실행기는 호출하지 않았다. Native trajectory/명령/관측 동치는 별도 pair verifier의 결과이며 timing helper는 이를 PASS로 만들지 않는다.

`test_compare_timing.py`의8개 합성 시험 PASS. CP949 로그의 ASCII marker, 중복/비유한 PERF, 실패·미완료 receipt, 소유 프로세스·SHA, 날짜 경계 Timer, 누락 bucket을0으로 만들지 않는 동작, 입력 변조 거부를 확인했다. 상세 기록은 `timing_validation.json` 및 `signal_head_timing_v1.json/.md`에 있다.

다음 완료 pair에는 같은 호출만 재사용하면 된다. 기존 결과를 덮지 않도록 새 `--out` 이름을 지정한다.

```powershell
& $Python -I -B -X utf8 diagnostics/com_execution_equivalence/compare_timing.py `
  --old-receipt <completed-old-run>/completion_receipt.json `
  --new-receipt <completed-new-run>/completion_receipt.json `
  --out diagnostics/com_execution_equivalence/<new-report-stem>
```
