# 모델 수정 및 native 관측·시각 검증 인계

`codex/control-full-review-20260909`, `1f378f3` 이후 증분이다. 누적 모델 수정은 이 브랜치의 이전 커밋들과 `docs/HANDOFF_20260921_gain_prediction.md`에 포함되어 있다. **RM/VSL 순이득 보정은 NOT_QUALIFIED이며, 이번 전달은 보정 완료나 새 성능 정본의 선언이 아니다.**

## 이번에 포함한 변경

- 기존 `evaluate_response.online_data()`의 관측 시각 검사: 소수 초를 버리기 전에 유한성·비음수·미래 여부·정수 초 정렬을 검사한다. 150.1초를 150초 관측으로 받아들이던 오류를 재현했다. 현재 고해상도 기록의 1.1/2.1초 위상을 정수 시각으로 바꾸지 않는다.
- 기존 `fast_nc_runner.vbs`: VISSIM 2020의 `VehRecResolution`은 simulation step 단위이므로, 1초 출력을 위해 현재 `SimRes`만큼 설정하고 readback을 남긴다. 기본 SimRes1의 값은 계속 1이다.
- 기존 `prepare_vehicle_lengths.py`와 `fast_fixed_profile.py`: 차체 앞뒤 좌표·가속도 기록과 명시적인 NC 전용 SimRes1/10 비교를 지원한다. 제어 명령이 있으면 해상도 진단 옵션을 거부한다. 기준 네트워크와 수요는 바꾸지 않았다.
- 기존 `fast_nc_run.ps1`: 선택적 `-MinimumFreeGiB` 시작 전 공간 검사와 실행 중 최소 공간 보호를 추가했다. 기본 0은 기존 동작을 유지한다. 다음 native 진단은 10으로 실행한다.
- 차체 좌표 분석, 해상도별 종료 자료 비교, 관측 시각 테스트와 수정 전 소스·실패 증거를 보존했다. 새 adapter나 controller 실행 경로는 만들지 않았다.

`H = diagnostics/demand_sweep/ramp_dsd_20260916_v2`, `K = H/cohort_dynamics_20260920`.

## 완료한 검증과 미완료 실험

| 항목 | 확인 결과와 한계 |
|---|---|
| NC seed23, SimRes1, 좌표 추가, 3000초 | 완료. 원래 FZP 20열 11,788,963행 정확 일치. 864개 초기/최종 주소 및 LDP 검증 PASS |
| NC SimRes10 첫 시도 | 잘못된 0.1초 기록 간격으로 실패. 소유 프로세스만 종료, 실패 원본 보존 |
| NC SimRes10 재시도 | 1초 기록 간격 확인. 1516.1초에서 디스크가 차서 실패. 전체 3000초 비교 미완료 |
| 종료된 재시도의 1500.1초까지 | 닫힌 앞부분만 분석. link24 겹침은 줄지만 속도·차량 수·혼잡 노출도 달라 같은 교통의 개선으로 해석할 수 없음 |
| 관측 시각 검사 | 6개 테스트 PASS. 합성 정수 입력의 150/300초 두 주기 상태·증거·캐시 바이트가 수정 전과 같음. 실제 폐루프 동등성은 별도 미검증 |
| 고정 명령 프로파일 | 관련 8개 테스트 PASS, 기존 NC/RM/VSL 명령표·초기값·증거 기본값 일치 |
| 실행 보호 | PowerShell 문법과 시작 전 공간 부족 거부 확인. 실행 중 128MiB 중단 경로는 코드 검토만 수행 |

기존 광범위한 15개 검사 중 정적 문자열 검사 1개는 수정 전부터 MPC 전용 차량 조회까지 금지하여 실패한다. 이를 성공으로 감추지 않았으며 `body_geometry_native_v1/preexisting_static_test_failure.txt`에 근거가 있다.

실제 좌표의 평면 직사각형 겹침은 native 충돌 사건이 아니다. 이번 관측 시각 오류가 과거 정수 초 제어의 이득 예측 실패 원인이었다는 증거도 없다. 고해상도의 교통 차이는 RM/VSL 효과가 아니다. 자세한 근거는 `K/BODY_GEOMETRY_AND_NATIVE_RESOLUTION.md`, `K/NATIVE_OBSERVATION_TIME_CONTRACT.md`를 따른다.

## 다음 컴퓨터에서 재개

1. 이전 `handoff_20260921_ordered/README.md`까지의 복원 순서를 먼저 수행한다. 이번 압축 자료는 그 위에 추가한다.
2. 아래 저장 결과 검사와 관측 테스트를 실행한다. VISSIM 실행은 필요 없다.
3. 최신 확인 시 C: 여유 공간이 약 12MB로, 새 native 실행은 중단된 상태다. 실패한 원시 기록을 삭제하거나 미완료 런을 완료로 취급하지 않는다. 충분한 공간을 확보하고 소유 실행 상태를 다시 확인한다.
4. 해상도 10의 기록 위상과 제어 관측 시각을 짧게 검증한 뒤, 새 출력 폴더에서 3000초 해상도 비교를 완료한다. 분수 시각을 반올림하는 우회는 금지한다.
5. 이후 동일 초기 상태의 RM/VSL 변경에 대해 본선·on-ramp·off-ramp 구성 비용, 순이득, 선택 순위를 검증한다. 실패한 평균밀도·IDM·기억 계수 sweep을 반복하지 않는다. seed13/23/33/43은 이미 개발에 사용했다. 미사용 holdout과 전체 Ω/full GNE는 별도 미완료다.

```powershell
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260921_native_clock --restore --verify
python -B -X utf8 diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/verify_resolution_prefix.py
python -B -X utf8 -m unittest diagnostics.test_fast_fixed_profile diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.test_online_native_clock
```

`evidence_manifest.json`은 복원 경로·크기·SHA256을, `direct_files.json`은 직접 전달한 소스·문서를 기록한다. 수정 전 소스는 과거 결과의 해시 확인에만 사용한다. 기존 pin을 새 코드의 해시로 덮어쓰지 않는다. 공간 제약 때문에 패키지 검증은 압축 객체와 현재 파일의 바이트 대조로 수행하며, 별도 빈 폴더 전체 복원 여부는 검증 기록에 구분한다.

대형 원시 FZP/LDP/DB와 배경 지도 JPG는 Git 증분에 넣지 않고 원위치에 보존했다. 제외 목록은 manifest에 남긴다. 분석 프레임·집계·실행 receipt·readback·설정·테스트용 작은 FZP는 포함한다. 원시 재추출이나 native 재실행에 필요한 제외 파일은 별도로 전달해야 한다. 과거 문서의 '로컬·미푸시' 및 프로세스 상태는 작성 당시의 기록이며 이 인계의 완료/실패 구분이 우선한다.
