# 고속도로 70%·80%·90% FD 비교 — 도시 50% 고정

요청한 80%·90%를 기존 빠른 무제어 러너로 각각 실제 5400초 실행했다. 두 런 모두 exit0, 완료 기록 및 소유 VISSIM 프로세스의 자연 종료를 확인했다. 70%는 직전 검증 완료 결과를 재사용했다. 새 controller 계산이나 수요 추가 탐색은 수행하지 않았다.

**80%부터 양방향의 혼잡 분포가 나타나고, 동행은 종료까지 회복되지 않는다. 90%는 동행 정체가 한때 최상류 E0까지 확장된다.** 따라서 이 조건들은 혼잡이 부족한 상태로 보기는 어렵다. 특히 90%를 정상 회복하는 제어 실험의 기준으로 바로 채택할 근거는 없다.

## FD

![70·80·90% FD 비교](C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.worktrees/control-full-review/reports/20260911_fd_fw070_080_090/freeway_fd_70_80_90.png)

위쪽은 동행, 아래쪽은 서행이다. 가로는 밀도 [veh/km/lane], 세로는 공간 평균 유량 [veh/h/lane]이며 모든 패널이 동일한 축을 쓴다. 색은 시뮬레이션 시간이다. 점 하나는 **약 513m 구간 × 60초 평균**, 방향별·조건별 1,890점이다.

- 동행은 70%에도 E8 주변의 국소 혼잡이 있었으나, 80%·90%에서는 고밀도·저유량 상태가 더 많은 구간과 시간에 걸쳐 지속된다.
- 서행은 70%에서 거의 자유류 분포였고, 80%·90%에서 밀도 증가에 따라 유량이 낮아지는 관측 분포가 드러난다.
- 관측 유량 최대값은 구간별 수요·속도 조건이 섞인 값이다. 이 그림을 capacity 추정치나 제어에 따른 capacity drop 실험 결과로 읽으면 안 된다. 곡선 적합은 하지 않았다.

## 혼잡 발생·전파·회복

![시공간 속도 비교](C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.worktrees/control-full-review/reports/20260911_fd_fw070_080_090/freeway_speed_70_80_90.png)

구간 번호 0이 상류, 20이 하류다. 회색은 평균 차량 수 5대 미만이다. 다음 표의 저속 기준은 **60초 평균 속도 <30 km/h, 평균 차량 수 ≥5대**다. 구간·분은 해당 1분 창의 구간 수를 합한 것으로, 실제 혼잡 지속 시간 하나나 차량 지체시간과 다르다.

| 고속도로 / 도시 | 동행 저속 구간·분 | 서행 저속 구간·분 | 종료 전 60초 동행 저속 구간 | 종료 전 60초 서행 저속 구간 |
|---|---:|---:|---|---|
| 70 / 50 | 105 | 0 | 없음 | 없음 |
| 80 / 50 | 294 | 11 | E4–E8, 5개 | 없음 |
| 90 / 50 | 482 | 59 | E1–E8 및 E12–E13, 10개 | 없음 |

80% 동행은 E3까지, 90%는 E0까지 상류로 확장된 저속 구간이 관측된다. 90%에는 후반 E12–E13의 별도 저속 영역도 남는다. 서행은 80%에서 W3–W4, 90%에서 W0–W4에 저속 구간이 나타나지만 종료 전 60초에는 위의 저속 기준을 벗어난다. 이는 서행 모든 차량이 자유류로 복귀했다는 뜻은 아니다.

본선 link2의 **마지막 900초 정상 방출 수지**도 다르다. 70%는 차량 수 366→65, 정상 유출−유입 +301대, 삭제·실종 0으로 감소했다. 80%는 690→617, 정상 수지 +71대와 삭제 2대이며 종료 시 정지 차량 166대가 남았다. 90%는 685→726, 정상 수지 −42대와 삭제 1대이며 정지 차량 218대가 남았다. 고밀도 상태가 단순히 그림의 축 때문에 보이는 현상은 아니다.

도시 연결도로 link127의 종료 차량/정지 차량도 **109/65 → 144/98 → 171/126**으로 증가했다. 고속도로 원점 수요를 높이면 원래 route 비율을 따라 off-ramp행 희망 수요도 함께 커지므로, 이 비교를 본선 통과 수요만 늘린 실험이라고 부르지 않는다.

## 수요·실행 조건과 결과

- 같은 네트워크 `diagnostics/fixed_beta300v3_network_arms_flat_v1/baseline.inpx`, SHA `085a10c71874e897083c97097af8fa3f1f08da1ef7416fef2f7cfbedabdfc317`, seed13, 5400초, SimRes1.
- 고속도로 입력 **1098·1099만** 기존 profile 적용 후 기준 수요의 70/80/90%로 설정했다. 도시 입력 32곳 × 6구간 = **192개 설정값은 모두 50%로 동일**하다. 34개 입력 × 6구간의 전체 204개 수요 설정·readback을 확인했다.
- 확률적 생성 및 공유 난수열 때문에 실제 도시 차량 생성 수·차량 ID까지 같다는 의미는 아니다. 설정 희망 수요 보존과 실제 표본 수는 구분한다.
- native route·도시 신호·66개 VSL120·8개 미터 GREEN 조건은 동일하다. 첫 native step 이후 기존 NC 명령을 적용하고 연속 실행했다. 1초 FZP, LSA, 오류 기록을 보존했다.
- 80% 실행 2026-09-11 10:56:51.929–11:00:25.987 KST, **214.06초**. 90% 11:00:52.123–11:05:00.950 KST, **248.83초**. 로딩·설정·종료를 포함한 러너 경과시간이다. 분석 시간과 합치지 않았다.

| 고속도로 / 도시 | Ω TTT [veh·h] | Ω TTD [유출 사건] | 종료 Ω 차량 | native 삭제 | Ω 미해결 disappearance | native 미삽입 차량 |
|---|---:|---:|---:|---:|---:|---:|
| 70 / 50 | 2,278.26 | 18,684 | 1,065 | 127 | 206 | 0 |
| 80 / 50 | 3,021.85 | 19,414 | 1,911 | 115 | 213 | 0 |
| 90 / 50 | 3,722.48 | 20,063 | 2,917 | 119 | 235 | 0 |

TTT는 기존 Ω 내부 체류시간, TTD는 기존 정상 외향 사건 집계를 유지했다. 내부 이동·삭제·미해결 실종·종료 잔여 차량을 TTD로 새로 합산하지 않았다. 삭제와 미해결 disappearance 열은 서로 배타적인 합계가 아니다. 서로 다른 수요이므로 TTD 증가를 controller 개선으로 해석하지 않는다.

## 검증 범위

1. native 완료, FZP 전체 1–5400초, 프레임 내 중복 ID(읽기 청크 경계 포함), Ω 차량 수의 기존 집계와 일치를 확인했다. 80% FZP 13,397,700행, 90% 15,931,304행이다.
2. 70%에서 검토한 동일 FD 집계식을 재사용했다. 실제 링크 차로 수 × 구간 겹침 길이로 lane-km를 구하고 1초 표본을 사다리꼴 적분했다. 본선 공간 경계 밖 음수 입력 위치·종단 초과 기록은 FD에서만 제외한다. 모든 링크의 실제 Ω 기록은 보존했다.
3. 204개 수요 ID/시간 구간과 준비표 join, 264개 VSL ID/차종 조합의 적용·종료 readback, 미터8개의 적용·종료 GREEN readback이 모두 일치했다.
4. 세 조건의 native LSA event payload SHA가 정확히 같다. **단, 미터는 LSA에 t=1 OFF만 기록되고 COM GREEN 전환은 기록되지 않는다.** 미터의 native 전환 검증은 여전히 불완전하며, SG ID가 있다는 이유만으로 GREEN 실행 증거로 쓰지 않았다. GREEN은 적용·종료 readback에서 확인한 범위다.
5. 실패·누락 기록을 정상 결과로 바꾸지 않았다. 세 런 모두 `unfinished_inputs=[]`이며 native 미삽입 기록은0대다. 삭제·경로 문제는 원본 오류 파일과 summary에 유지돼 있다. 최종 정본이나 깨끗한 용량 보정 자료로 승격하지 않았다.

## 파일과 재현

- 그림: `freeway_fd_70_80_90.png/.svg/.pdf`, `freeway_speed_70_80_90.png/.svg/.pdf`.
- 집계: `fd_points_60s_comparison.csv`, `comparison_metrics.csv`, `desired_demand_comparison.csv`.
- 80%·90%의 개별 FD·MFD 및 집계는 `fw080/`, `fw090/`에 있다.
- 런: `evaluation/runs/fast_nc_fw080_urban050_s13_v1`, `evaluation/runs/fast_nc_fw090_urban050_s13_v1`.
- 원본 준비/오류/경계 집계: `diagnostics/demand_sweep/fw080_urban050`, `diagnostics/demand_sweep/fw090_urban050`.
- `prepare_cases.py`는 두 수요 조건을 기존 준비 코드로 생성한다. `plot_comparison.py`는 완료 결과만 읽는다. `validation.json`에 source SHA와 기록 검증을 남겼다.
- 기존 `build_figures.py`에는 수요 조건·출력 경로·제목 인자만 추가했고 수치 집계는 그대로다. 최초70% 분석 코드의 정확한 사본은 `build_figures_before_multicase.py.txt`로 보존했다. 기존70% 그림·CSV는 덮어쓰지 않았다.

실제 사용한 PowerShell 런 명령(작업 디렉터리 `.worktrees/control-full-review`):

```powershell
& 'C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe' -NoProfile -ExecutionPolicy Bypass -File 'diagnostics/fast_nc_run.ps1' -Prepared 'diagnostics/demand_sweep/fw080_urban050/prepared' -Output 'evaluation/runs/fast_nc_fw080_urban050_s13_v1' -Seed 13 -Execute
& 'C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe' -NoProfile -ExecutionPolicy Bypass -File 'diagnostics/fast_nc_run.ps1' -Prepared 'diagnostics/demand_sweep/fw090_urban050/prepared' -Output 'evaluation/runs/fast_nc_fw090_urban050_s13_v1' -Seed 13 -Execute
```

기존 결과를 보호하기 위해 같은 출력 폴더로 재실행하면 러너가 거부한다. 그림만 재생성하려면 아래 명령을 사용한다.

```powershell
& 'C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B -X utf8 'reports/20260911_fd_fw070_080_090/plot_comparison.py'
```
