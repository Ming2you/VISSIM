# 2026-09-13 다른 컴퓨터에서 이어가기

**가장 먼저 읽을 최신 인계 문서다.** 아래 결과는 현재 정본 코드의 실행·검증 범위를 구분한 것이다. 이전 문서의 ACTIVE, N_UF=7200, 4그룹 재고, 차량 소실=완료 등의 서술을 현재 정의로 되돌리지 않는다.

**추가 진단:** 사용자의 낮은 개선율·미터 TTT 의심에 대한 [2026-09-13 성능·미터 진단](../diagnostics/performance_diagnosis_20260913/REPORT.md)을 함께 읽는다. 53개 결정의 탐색 제한, 2400초 동일 상태 미터 반응, native 첨두 악화·후반 회복을 확인했다. E8 미터 g8은 해당 시점의 평균 서비스 모델에서 도착 재고보다 상한이 높아 교통 반응이 정확히 동률이었다. TTT 거주시간 합산·Ω 내 생성항을 포함한 보존식에는 해당 재현에서 오류가 없었다. native g8 A/B는 아직 수행하지 않았으며 정본 모델·controller 소스는 이 추가 진단에서 변경하지 않았다. 원본 LDP의 완전한 byte-prefix로 8741초까지 신호 상태를 보완 확인했지만, 마지막 109초와 전체 런 인증은 미완료다. 아래 원래 인계 결과·실패 기록은 그대로 보존한다.

## 현재 상태와 바로 확인할 결과

- 작업 브랜치: `codex/control-full-review-20260909`. 원격 `https://github.com/Ming2you/VISSIM.git`.
- 이전 로컬 커밋은 `dd13e0810fe4fc5582a863cb19839fe0f2464d9f`이다. 이번 인계 커밋에 그 이후 정본 코드·실행 준비 파일·선별한 검증 근거를 포함한다.
- **이 컴퓨터에서 새 VISSIM 런을 시작하지 않았다.** 2026-09-13 16:29KST 확인 시 중단 런의 cscript37064/native39320은 없었다. 다른 사용자 프로세스를 종료하지 않았다.
- 마지막 런 `codex_fid_cl9000_s13_v3`는 8700초 제어 결정까지 완료했다. 8850초 원시 상태와 FZP는 있으나, 해당 결정의 마지막 진행 기록은168.920초이며 완료 action·9000초 종료 확인서는 없다. 종료 원인에 대한 정상적인 wrapper receipt도 없다. **완료 런으로 승격하지 않는다.**
- 사용자 요청에 따라 이 런은 **관측된 0–8850초 구간만** 같은 seed13 무제어와 비교했다. 이 비교를 위해 전체 런을 다시 돌릴 필요는 없다.

| Ω TTT [veh·h] | 무제어 | 제어 | 제어−무제어 | 감소율 |
|---|---:|---:|---:|---:|
| 0–8850초 | 4155.383750 | 4131.682500 | −23.701250 | **0.5703745%** |
| 900–8850초: 제어 시작 이후 | 3965.121528 | 3941.420278 | −23.701250 | 0.5977433% |

CL FZP는18,551,214행,8850개의1초 프레임, 시간 누락0, tail 외삽0이다. 마지막 FZP1236대에 같은 시각 COM1235대가 모두 포함된다. FZP에만 차량32482가 남아 있으며, 마지막 관측의 차량은 잔여 차량으로 취급하고 TTD에 넣지 않는다. Ω 종료 재고는 NC891/CL908대, 미확인 내부 소실은 NC375/CL348건이다. 소실은 정상 유출로 바꾸지 않았다. 최종 native 신호·오류 검증이 없는 **중단 구간의 관측 비교**이며, GNE·실시간·10% 개선 인증이 아니다.

근거: [비교 JSON](../diagnostics/handoff_20260913/ttt_prefix8850/comparison.json), [CL 구간 회계](../diagnostics/handoff_20260913/ttt_prefix8850/area_metrics.json), [재현 스크립트](../diagnostics/handoff_20260913/compare_ttt_prefix.py). 원시 FZP는 Git 전송 대상과 구분한다.

이 스크립트는 이번 계산 당시의 원래 경로에서 실행한 기록이다. 기존 결과 폴더가 있으면 덮어쓰지 않고 중단하며, state의 manifest 절대경로까지 검사한다. 새 PC에서 raw를 복사한 것만으로 곧바로 재실행되지는 않는다. 재분석 시 새 출력 경로와 원본 SHA를 보존하는 경로 이전 검증이 필요하다. 과거 state/receipt를 일괄 치환하거나 guard를 제거하지 않는다. Git에 포함한 두 시계열 CSV로 위 TTT 차감 자체는 확인할 수 있다.

## 지금까지 완료한 작업과 한계

1. **모델·실제 경로 교정.** SC1005의403L1→10565→58 무신호 통과와403L2/3→10570→61의 SG7 경로를 분리했다. 실제 경로 결정 자격, 이미 선택된 경로, 8개 진출 분기의 서로 다른 본선 위치를 보존한다. 같은900–1350초 명령에서 진출 분기 MAE48.407→25.956대, 본선 말단 MAE83.318→16.545대로 줄었다. 전체 TTD 오차와 램프별 합류 오차가 모두 좋아진 것은 아니다.
2. **계산 시간 개선.** 같은 모델·가격·32회 논리 평가·17회 실제 endpoint의 ABBA에서 game 평균53.915→34.083초(36.8% 감소), 명령·물리 응답·가격·trace·gap 일치를 확인했다. 전체 controller 시간의36.8% 감소가 아니다. 실제 긴 런의 결정은 약240–270초로150초 주기를 초과한다. 별도120초 예산 실험의111.466초 반환은 최종 gap 미완료 상태였다.
3. **혼잡 구간 실제 폐루프.** seed13,80/50,제어 시작2400초,2850초 종료의 NC/CL 비교를 완료했다. 제어 이전4,475,808개 FZP 데이터 행과 필요한 head 이력이 일치했다. LDP·신호/VSL 실행·213행 명령 결합 검증을 통과했다. 2400–2850초 TTT304.176667→303.143750(0.340% 감소), TTD2019→2010, 종료 재고2508→2529였다. 도시부 일부 신호·offset이 바뀌었고 일부 도로는 악화됐다.
4. **장시간·다른 seed 검증은 미완료.** 정본 NC seed13의9000초는 완료했고, CL은 위8850초 중단 자료까지 있다. seed17의 정본 NC/CL 짝 비교와 최종 전체 검증은 아직 수행하지 않았다.

정본 NC9000의 Ω TTT4192.123194veh·h, TTD29436건, 종료865대, 미확인 소실380건이다. native 제거194건 중 Ω 내부162건은 소실과 겹칠 수 있으므로 합산하지 않는다. E7→E6→E5→E4→E3의 저속 발생 시각은2220/2580/3030/3240/3870초였고, 마지막 구간에는 본선 정지는 해소됐지만 도시부325/326 등에 잔여 대기가 있었다. 이를 CL의 회복 결과로 오인하지 않는다.

상세 결과는 [계산·모델·실제 실행 보고서](../reports/20260911_decision_runtime/TIME_UNLIMITED_AND_MODEL_NATIVE_20260912.md)를 읽는다. 그 안의 날짜별 ACTIVE 표시는 역사적 진행 일지다.

## 장시간 실행에서 수정한 두 오류

- **3150초 경로 초기화:** 이미 목표 분기를 지나친 실제 STATIC 경로 차량을 잘못 재배분하거나 NULL로 만들지 않는다. 차량12602의 뒤에 놓인10682 목표를 유지하고, 확인되지 않은 마지막 운명은 정상 TTD로 바꾸지 않는 보수적 검열을 적용했다. 관련84검사·기록 결정·V2/V3 실제3150초 결정이 통과했다. 모든 모델 회계 잔차가0이라는 뜻은 아니다.
- **6300초 context guard:** native 실패의 세부 원인은 완전히 재현하지 못했다. 별도 합성 실험에서 내용이 같은 set의 순서 변경과 cfg↔runtime 참조 분리로 raw pickle이 달라지는 현상은 재현했다. 바뀌지 않은 child 객체를 보존하도록 복원을 수정했고, 실제 cfg/state 변경을 되돌려 가리지 않는다. 전체 raw SHA guard를 유지하며 재발 시 최초 전후 pickle을 실패 기록으로 남긴다. 관련63검사와 기록6300초 결정이 통과했다. 수정 전후 기록 결정의213행 실제 명령은 byte 일치했지만 탐색 작업량은 달라 전체 속도비로 쓰지 않는다.
- V3 실제6300초도244.243초에 완료했고213행 결합, 소스 변경0, 실패0, worker 종료를 확인했다. 이후8700초까지 진행했다. 원 native6300 실패의 정확한 원인 확정과 이번 재발 없음은 구분한다.

근거는 `diagnostics/control_improvement/decision_common_anchor_20260911/ramp8_physical_v1/`의 `route3150_missed_target_fix_v1.md`, `guard6300_scope_fix_v1.md`, `fidelity_recorded6300_scope_comparison_v1.md`에 있다. 실패한 V1/V2/V3 원본을 덮어쓰지 않는다.

## 유지해야 할 사용자 합의

- Ω는 **고속도로+도시 protected network**. TTT는 Ω 내부 체류시간이다. TTD는 살아서 Ω 밖으로 나가는 사건과 검증 가능한 말단 유출이다. 내부 이동·비정상 삭제·미확인 소실·끝 잔여는 제외한다.
- N_P는17개 도시 제어 주체의450초 **도시 경계 유입+off-ramp 방출−도시 경계 유출−on-ramp 방향 방출**이다. Ω 전체 재고나 TTD로 바꾸지 않는다.
- N_UF는 **8개 램프의 예측된 실제 본선 수용 합류량 합**이다. 각 결정의 실제 유지 명령으로 목표를 정한 뒤 후보 간 고정하며 현재 허용오차는±40veh/h=450초±5대다. 과거7200veh/h 서비스율 합을 사용하지 않는다.
- 8개 미터는 물리 재고·접근 권역·녹색을 각각 관리한다.10초 cycle, RED/GREEN만 사용(미터 황색0), 직전 실제 녹색 대비 최대±2초. 도시 신호 황색3초·전적색0 규약은 유지했다.
- green·offset·VSL·metering은 같은 follower game의 전략변수다. 현재19개 owner는 도시17개와 동·서 freeway owner2개다. 미터8개를4개 재고로 합친다는 뜻이 아니다.
- 예측450초, 제어150초, 현재 β=0은 TTT 진단 조건이다. TTT−TTD의 최종 가중치는 아직 선택되지 않았다.
- 시작 후 실제 simulation 진행이300초 동안 없을 때 해당 런의 소유 프로세스만 정리한다. 제어 계산 중의 의도된 정지와 UI 응답없음을 구분한다. 다른 사용자 프로세스 일괄 종료 금지.
- 제어 입력으로 쓰는1초 head/차량 관측은 유지한다. 신호·미터는 전환 시 쓰고, VSL은 새 명령 적용 시 쓰고 readback한다. 일반 반복 실험에서 매초 전체 readback을 다시 켜지 않는다.
- 사용자가 **native LDP를 실행 검증 대체 기준으로 허용**했다. LSA의 COM 전환 누락은 독립 실패 항목으로 남긴다. CSV만으로 실제 적용 성공을 선언하지 않는다.
- 수요·망·기준 신호는 비교 중 고정한다.80% freeway/50% urban,seed13,9000초 조건에서4500초 시작 마지막 수요 구간을 끝까지 유지한다. 수요0의 배출 시험이 아니다.

## 다음 진단에서 꼭 확인할 것

- queue·예측 도착·실제 명령 trust region으로 빠른 N_P 초기값을 만들되, 한 극단 명령의 성능을 전 영역의 불가능 증명으로 사용하지 않는다. 유효한 전 영역 하한이 없으면 가능성 미확인으로 두고 짧은 후보 예산 후 다음 후보로 넘어간다.
- 출발 지연은 첫차 반응과 뒤쪽 차량의 출발 전파를 구분한다. 기존 실측 방출률에 포함된 손실을 다시 차감하지 않는다. 현재 자료는 첫차 지연이 queue 길이에 선형 비례한다는 계수를 지지하지 않는다.
- g10 완전 개방의 모델 상한1512veh/h는 **1차로 기준**이며 현재 RG0 포화 실험으로 검증된 용량이 아니다. 현재 모형은10초 RG 펄스 대신 평균 서비스 상한을 쓴다. 실제 상한이 예측 방출을 제한했는지 먼저 확인한다.
- g10 anchor의 고정±2초 범위는g8/g9/g10이다. follower는 동률 명령을 중립적으로 채택하지 않고450초 동안 후보를 유지하므로 미래g10→g8→g6을 미리 평가하지 않는다. 다만 outer seed와 VSL×meter 결합 후보가 있으므로 실제 plateau/영구 OPEN을 증명한 것은 아니다.
- 동·서 FD/MFD 그림은 방향별 초기 탐색 범위의 근거로 사용할 수 있으나 two-branch 및 VSL capacity gain을 실제로 검증한 것으로 쓰지 않는다.
- 개선율만 보지 말고 병목 위치·전파·spillback·실제 방출·platoon과 green/offset의 관계, 제거/미삽입을 함께 본다. 목표10%는 미달이다. 최종 정본 확정 전 대규모 adapter 삭제·리팩터링은 보류한다.

두 미터 검토 메모: [OPEN 서비스 상한](../diagnostics/control_improvement/decision_common_anchor_20260911/meter_open_service_bound_review_v1.md), [동률 후보와 시간 규약](../diagnostics/control_improvement/decision_common_anchor_20260911/meter_plateau_scope_review_v1.md).

## 새 Windows 컴퓨터에서 준비

1. 이 브랜치를 clone/pull한다. Windows 긴 경로 문제를 피하도록 `C:\VISSIM` 같은 짧은 위치를 권장한다. 로컬 절대경로와 이전 실행의 PID/session ID는 재사용하지 않는다. 새 컴퓨터에서 실제 런을 수행할 때 다른 컴퓨터의 동시 런이 없는지 조율한다.
2. 라이선스가 있는 VISSIM2020과64비트 `Vissim.Vissim` COM, Windows PowerShell/cscript가 필요하다. 코드 검증 환경은 Python3.12.14 AMD64·NumPy2.3.5였다. vendored `vendor/NumSim-mine` 및 `plant/src`를 유지한다. 사후 분석용 pandas는 별도다.
3. 새 Python 경로를 `-Python`에 명시한다. runner의 이전 PC 기본 경로에 의존하지 않는다.
4. 고정 망은 `diagnostics/fixed_beta300v3_network_arms_flat_v1/baseline.inpx`와 참조하는42SIG·1JPG다. 원본 SHA는 `085a10c71874e897083c97097af8fa3f1f08da1ef7416fef2f7cfbedabdfc317`. recording 설정만 적용한 실행 망 SHA는 `25acf56cbdc475479094a20903dc190557d0ccd278094f0a3c6121a3ff23fdd2`였다.
5. 기존 `prepared.json`에는 이전 PC 절대경로가 있다. **새 준비 폴더를 생성**한다. `fast_nc_prepare.py`에는 source ACTION 경로 옵션이 없으므로 인계에 포함한 기존 위치의74행 `action_000001.csv`가 필요하다. prepared terminal은5400으로 두고 실제 runner 기간을9000으로 지정한다.

저장소 루트의 PowerShell에서:

```powershell
$py = (Get-Command python).Source
$d = 'diagnostics/control_improvement/decision_common_anchor_20260911/ramp8_physical_v1'
& $py -B -X utf8 scripts/verify_parameters.py "$d/joint_config_fidelity_v3_portable.json"
& $py -B -X utf8 diagnostics/fast_nc_prepare.py --demand-overrides diagnostics/demand_sweep/fw080_urban050/input_override.csv --output diagnostics/demand_sweep/fw080_urban050/prepared_transfer
```

새 PC 선택 설정은 **`joint_config_fidelity_v3_portable.json`**이다. 원래 `joint_config_fidelity_v3.json`의 다섯 절대경로만 저장소 상대경로로 옮겼고, 참조 파일 SHA와 나머지 모든 설정값은 동일하다. [경로 이전 증명](../diagnostics/handoff_20260913/portable_config_proof.json)을 확인한다. 원본 설정과 이전 실행 receipt는 보존했다. `v4`는120초 예산 진단 설정으로 실제 비교 설정이 아니다. 다음은 실제 VISSIM을 시작하지 않는 준비 점검이다:

```powershell
& .\diagnostics\run_selected_control_trial.ps1 -SelectedPrepared diagnostics/demand_sweep/fw080_urban050/prepared_transfer -Tuning "$d/joint_config_fidelity_v3_portable.json" -Name transfer_cl_s13 -Controller wu-link -SimPeriod 9000 -ControlStartSec 900 -Seed 13 -Python $py
```

실제 실행은 필요한 점검 후 같은 명령에 `-Execute`를 붙인다. 출력이 존재하면 새 `-Name`을 쓴다. 신호·수요·recording 증명·profile/config는 기존 wrapper가 새 경로에서 생성한다. 과거 receipt/proof의 경로와 SHA를 일괄 치환해 이전 실행 증거인 것처럼 사용하지 않는다. 기본 초기 검증은1050초 등 짧은 런으로 할 수 있다.

## 남은 순서

1. 이번8850초 TTT 비교를 읽고 해석한다. 원시 FZP만으로 중단 지점의 VISSIM 내부 상태를 복원할 수 있다고 가정하지 않는다. 현재 검증된 runner는 fresh LoadNet 실행이다.
2. 필요하면 완전한 seed13 CL9000을 새 이름으로 수행한다. 이미 얻은8850초 TTT 수치를 얻기 위해 반복할 필요는 없다. 완료 기록이 있는9000초 native 인증은 별도 미완료 범위다.
3. 같은 망·수요·fidelity_v3로 seed17 정본 NC/CL을 짝지어 비교한다. `-Controller no-control`과`wu-link`를 바꾸고 `-Seed 17`, 같은9000초·제어 시작900초를 쓴다. 각각 새 이름을 사용한다.
4. 완료한 런에만 기존 `qualify_fast_np_closedloop.py`와`diagnostics/summarize_fast_nc.py --completion-receipt ...`를 적용한다. 중단 V3에 가짜 completion receipt를 만들지 않는다. seed별 개선율·TTD·재고·소실·제거·미삽입과 공간 전파를 함께 보고한다.

**fast NC를 정본 기준으로 재사용하지 않는다.** 전체9000초 대조에서448초 차량1256 위치가 최초로 달랐다. 같은 총계라는 이유로 동일 실행으로 인정하지 않았다. seed17도 현재 정본 wrapper의 NC를 사용한다.

사후 계산 규약은 [전체 비교 계약](../diagnostics/control_improvement/decision_common_anchor_20260911/ramp8_physical_v1/full_pair_report_contract_v1.md)과 [두 seed 확인표](../diagnostics/control_improvement/decision_common_anchor_20260911/ramp8_physical_v1/final_two_seed_review_checklist_v1.md)에 있다. 9000초 마지막 명령은 실제 노출0초이며, 상세450초 차량 분석을 전체9000초 실행 증명으로 확대하지 않는다.

## Git에 포함한 것과 원시 자료

이번 인계는 정본 코드, 필요한 준비 입력·망·신호 파일, 작은 검증/요약 결과, 그림과 보고서를 포함한다. `.plot-deps`, 캐시, 전체 per-decision 데이터, GB 단위 native FZP는 일반 Git 소스에 넣지 않는다. 원시 자료가 필요한 분석은 원래 컴퓨터의 다음 폴더를 별도로 보존/전송한다:

- `evaluation/runs/codex_phys8_fidelity_fw080_u050_nc9000_s13_v1/`: 완료 NC9000 및 native FZP.
- `evaluation/runs/codex_fid_cl9000_s13_v3/`: 중단 CL,0–8850초 FZP/LSA/LDP/관측/명령.
- `evaluation/runs/codex_phys8_fidelity_fw080_u050_nc2850_s13_v1/`, `...cl2850_s13_v1/`: 완료 혼잡 구간 대조.
- `evaluation/runs/codex_fid_cl9000_s13_v2/` 및 최초3150 실패 런: 실패 원인 추적용 원본.
- 해당 런의 `diagnostics/selected_control_demand/<name>/`: 생성 config/profile/recording 증명.

Git에 포함되는 경로와 파일 SHA는 `diagnostics/handoff_20260913/transfer_manifest.json`으로 확인한다. 문서의 역사적 근거 링크 일부는 위 로컬 원시 자료를 필요로 한다. **요약을 clone한 것과 원시 실행 자료를 옮긴 것은 다르다.**

인계 직전 확인: context/owner 관련63검사, 선택 수요·완료 확인서28검사, fidelity_v3 파라미터 검사가 통과했다. 필수404파일을 별도의 폴더에 복사한 뒤 새 prepared 폴더와 portable 설정으로 wrapper 계획 생성을 통과했다. 계획에 이전 worktree 경로가 남지 않는지도 확인했다. 이는 새 PC의 COM·라이선스 및 실제 native 실행 검증을 대신하지 않는다.

Git index에서 별도 폴더로 내보낸 선별1537파일은 당시 manifest의 SHA와 모두 일치했다. 별도 폴더에서도 context/owner63검사와 completion23검사, 총86검사가 통과했다. 과거 `SelectedDemand` 클래스의5검사는7030/7040/8050 prepared 및 joint_config_v2의 이전 절대경로를 사용하므로 새 PC에서 실행하려면 테스트용 준비 파일을 새 경로로 재생성해야 한다. 원본 prepared와 작은 baseline ZIP·수요 override도 보존했다. 이5검사의 원래 PC 통과와 새 PC 이식 검증은 구분한다. 실제 재개 설정은 위 portable v3다.
