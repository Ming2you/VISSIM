# COM 실행 비용 축소 검증 — 2026-09-10

2026-09-11 갱신: [일반 실행 연결 검증](selected_native_record_v1/README.md)을 실제 original70/30·1050초에서 완료했다. `execution.native_signal_record=true`이면 기존 selected 실행기가 기록 전용 망 사본·변경 시 쓰기·종료 후 LDP/실제 readback 검사를 사용한다. 아래의 과거 LSA 실패 기록은 유지한다. 새 실행 판정은 native LDP와 실제 초기/변경 readback에 근거하며 LSA 자체를 PASS로 바꾸지 않는다. 기존 r03과 전체866,523행 궤적이 같고 wrapper wall은561.820→503.125초였다. 이 차이는 실행시간이며 TTT 개선이 아니다.

**고정 signal·ramp 및 1050초 폐루프 시험의 실제 실행 동치는 모두 통과했지만, native LSA 검증 실패로 종합 판정은 FAIL이다.** Selected trial의 기본 실행 설정 채택은 보류한다. 폐루프 검증은 이번 seed13·1050초 범위에 한정하며, 최신 사용자 지시에 따라 추가 5400초 시험은 진행하지 않는다.

기존 정본 VBS·watchdog에 변경을 적용했다. 동일 상태의 SG 반복 쓰기를 생략하고 변경 직후·다음 step·제어 경계의 확인을 유지하며, 필수 1초 head 관측은 그대로 둔다. 적용된 VBS SHA는 `961d61d0…`, watchdog은 `619066df…`이다. [적용 receipt](canonical_edit_receipt.json)의 당시 `pending`은 적용 시점의 기록이며, 후속 판정은 아래 완료 결과를 따른다.

고정 signal의 두 arm은 같은 수정 소스·망·FW70/도시40 수요·seed13·1200초·고정 신호 프로필·head ON을 사용했다. 900초까지 NC, 이후 같은 green/offset 명령을 적용했다. 양쪽 `RW_PERF=1`이며 old는 readback=1/write-on-change=0, new는 0/1이다. VSL sidecar와 이미 제거한 중복 VSL summary read는 양쪽 공통이므로 그 절감 효과를 별도로 측정한 비교는 아니다.

| 완료 signal pair 판정 | 결과 |
|---|---|
| Old | `codex_com_signal_head_old_s13_1200_r02` — 성공 종료 |
| New | `codex_com_signal_head_new_s13_1200_r01` — 성공 종료 |
| 실제 실행 동치 | `actual_execution_equivalent=true` |
| Native LSA COM 기록 포괄성 | `native_lsa_com_coverage_passed=false` |
| 종합 gate | `passed=false` — native 증빙 조건 미충족 |

[Signal pair v2](signal_head_pair_v2.json)는 완료·기록 provenance, 명령/상태, ordered FZP, 실제 SG/VSL readback과 전환을 대조한 결과다. 관측된 실행 동치를 sparse readback 사이의 모든 순간이나 적응형 제어 전체의 동치로 확대하지 않는다.

| 계측값 | Old | New | 변화 |
|---|---:|---:|---:|
| 계측 지점 COM 호출 수 | 452944 | 286834 | −166110 |
| Wrapper 전체 경과시간 (초) | 461.835 | 302.331 | −159.504 |
| 수요 설정 전체 (초) | 105.188 | 2.219 | −102.969 |
| 수요 setter 후 검증 읽기 (초) | 101.477 | 0.883 | −100.594 |
| 실제 수요 setter·오류 처리204회 (초) | 1.555 | 0.906 | −0.648 |
| 실제 simulation 호출 합계 (초) | 20.570 | 21.773 | +1.203 |
| Python controller9회 (초) | 10.555 | 10.961 | +0.406 |
| SG setter / apply-read (각각 회) | 50608 | 876 | −49732 |
| SG persistence read (회) | 50392 | 1186 | −49206 |
| 필수 head 직접 SigState read (회) | 104700 | 135857 | **+31157** |
| Head capture (초) | 152.711 | 181.328 | +28.617 |

Old의 큰 시작 지연은 input1082의 interval1-4 DONE→1-5 BEGIN 사이101.68초에 위치한다. 이 구간은 after-read·집계·다음 before-read를 포함하므로 단일 getter 시간을 뜻하지 않는다. 별도 PERF가 after-read 전체101.477초를 확인한다. **전체159.504초 감소를 SG 최적화 효과로 그대로 주장할 수 없다.**

각 arm의 after-read를 빼면 잔여 경과시간은360.359→301.448초(−58.911초), 수요 설정 전체를 빼면356.648→300.112초(−56.536초)다. 초기화·폴링·정리가 남아 있는 산술 비교이며 순수 SG speedup이나 반복 실험의 안정적 성능 추정은 아니다. 실제 simulation 호출이 빨라진 결과도 아니다.

직접 계측된 urban runtime52.523→5.672초, ramp runtime8.805→0.070초, persistence35.648→1.055초는 줄었다. 반면 head 관측은 줄어든 persistence read 결과를 덜 재사용하여 직접 읽기가 늘었다. Head capture/history/seal은 양쪽 각1200회, physical bulk 반환4800회·route bulk 반환36회·VSL setter/read 각2376회가 같다. 필요한 관측을 생략해 얻은 절감으로 설명하지 않는다.

시간 bucket은 중첩되어 합산할 수 없다. Wall에는 startup·cleanup이 포함되고, `com.* sec=0`은 시간 미계측 count 표기다. COM 수는 계측 지점만 포괄하며 객체 열거/GetAll·일부 getter·오류 경로 등을 제외한다. 상세 값과 범위는 [타이밍 v1](signal_head_timing_v1.json), [짧은 해석](timing_handoff.md)에 있다.

실패한 old r01은 실제1158초 signal readback 이후 멈춰 watchdog이 종료했다. 초기 수요 설정 실패나 실행 중 MPC로 분류하지 않으며, 정확히 막힌 COM API는 미확정이다. 원자료와 [실패 평가](../../evaluation/runs/codex_com_signal_head_old_s13_1200_r01/failure_assessment.json)를 보존하고 성능 비교에서 제외했다.

Native LSA는 출력 설정이 켜져 있어도 COM 소유 SG의 실제 전환·적용 후 초기 상태를 충분히 기록하지 않는다. [기존 실측 포괄성](../controlled_native_lsa_coverage.md)과 [설정 재확인](../controlled_native_lsa_setting_followup.md)에 근거와 한계를 보존했다. 명령 CSV나 요청 상태로 빠진 native 행을 채워 PASS 처리하지 않는다.

기록된 native LSA 행 자체도 old/new 간 정확히 같다(signal6170행, ramp6910행, 폐루프5681행). [기록 행 대조](recorded_native_lsa_pair_equality.json)는 누락된 COM 전환을 보완하지 않으므로 native 포괄성 FAIL을 바꾸지 않는다.

Ramp old/new `codex_com_ramp_head_{old,new}_s13_1200_r01`도 성공 종료했다. [Ramp pair v1](ramp_head_pair_v1.json)은 실제 실행 동치=true, native LSA=false, 종합=false다. Ordered FZP 1226653행의 데이터 SHA는 `c012422d529f99e56613ce6e901b5fcc6a3a000dc494040a9ab8bf6330f497fd`로 동일하다.

Ramp의 세 핵심 계측은 **COM312736→286040회**, **전체303.217→304.112초**, **simulation21.703→21.313초**다. 호출은26696회 줄었지만 이 한 쌍의 전체시간은0.896초 늘어, wall 절감은 입증하지 못했다. 수요 설정을 뺀 잔여도301.092→301.323초이며 head 직접 읽기는 양쪽136800회로 같다. [Ramp timing v1](ramp_head_timing_v1.json)에 완료 증거와 중첩 계측 범위를 보존했다.

폐루프 `codex_com_closed_loop_head_{old,new}_s13_1050_r01`은 같은 기존 r02 config/profile·head ON·wu-link를 사용해 성공 종료했다. [폐루프 pair v1](closed_loop_head_pair_v1.json)의 실제 실행 동치=true, native LSA=false, 종합=false다. 세 pair 모두 실제 CSV 명령·최종 제어7필드·head 이력을 포함한 물리/이력19필드·ordered FZP가 대조 범위에서 동일하다. Run provenance 등 명시된 메타데이터 제외를 전체 JSON 바이트 동치로 확대하지 않는다.

폐루프의 **COM344096→250372회**, **전체563.374→522.400초(−40.974초)**, **simulation19.797→19.336초**를 확인했다. Python controller8회는275.828→274.242초로 알고리즘 계산을 크게 줄인 결과가 아니다. 수요 설정2.203→2.250초여서 signal의101초 시작 지연은 재현되지 않았고, 수요 설정 제외 잔여는561.171→520.150초다. 필수 head 직접 읽기는103650→119169회(+15519)로 늘었다. [폐루프 timing v1](closed_loop_head_timing_v1.json)은 이 비용 이동과 단일 pair의 한계를 보존한다.

실행 후 별도 verifier 명령은 signal **4.957초**, ramp **4.200초**, 폐루프 **3.9443518초**였다. Python 시작과 파일 검증을 포함하며 위 wrapper 실행시간에 포함되지 않는다. [후처리 시간 기록](post_analysis_timing.json)의 `valid_analysis=true`는 검증 명령이 완료됐다는 뜻이며 native LSA 종합 FAIL을 뒤집지 않는다.

| 최종 검증 항목 | 결과 |
|---|---|
| 고정 signal·head ON, 1200초 old/new | **실제 실행 동치 PASS / native LSA FAIL** — 시작 지연을 분리한 시간 해석 필요 |
| Ramp 고정 프로필: 8개 meter 5G/10초·VSL80, 1200초 old/new | **실제 실행 동치 PASS / native LSA FAIL** — wall 절감 미입증 |
| Head ON wu-link 폐루프, 동일 r02 config/profile, 1050초 old/new | **실제 실행 동치 PASS / native LSA FAIL** — 한 pair에서 wall40.974초 감소 |
| Native LSA 요구 충족 / 기본 설정 채택 | **미해결 / 보류** |


## 후속60초 native LDP 판별시험

[별도망사본 검증](../native_signal_record_s13_60_v2/verification.json)에서 COM도시SG1개·미터SG1개·native대조SG1개의 LDP180행이 실제after-step readback과모두일치했다.14개COM전환은 다음프레임에14/14기록됐지만LSA는0/14로여전히FAIL이다. 적용직후초기상태는readback으로별도확인해야하며 LDP는1초뒤프레임에반영됐다. 이는2020의native상태기록 대안에관한작은실측이며 기존pair/전체SG의포괄성PASS나기본설정채택으로확대하지않는다. 전체21.219초, 실제simulation60초, 소유VISSIM종료확인. 풀런추가없음.

## 전체 SG의 짧은 native 기록 검증 — 2026-09-11

[300초 old/new 결과](native_all_sg_300_v1/RESULTS.md)에서 실제 제어 대상은 RED-only14개를 포함한 **144 SG**임을 확인했다. 두 arm 모두 실제300초를 완료하고 소유 native 프로세스가 종료됐다. FZP136,243행·실제명령·VSLreadback이 일치했고, LDP144×300샘플이 양 arm에서 정확히 같았다. t2..300의43,056샘플은 기존 post-step 명령 시계와 일치했다. 전체wall161.480→101.273초, 계측COM218,790→74,782회였으며 계산·관측 비용은 별도 분리했다. LSA는 여전히 COM전환872개 중867개 누락으로 FAIL이다. 이번엔 추가5400초 런을 하지 않았다.
