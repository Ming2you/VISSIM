# 고속도로 70%·도시 50% — 관측 FD / MFD

완료된 무제어 `fast_nc_fw070_urban050_s13_v1`, seed 13, 0–5400초의 native 1초 FZP로 작성했다. 새 VISSIM 런이나 controller 변경은 하지 않았다. 색은 시뮬레이션 시간이며 보라색이 초기, 노란색이 후반이다.

## 고속도로 FD

![고속도로 FD](C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.worktrees/control-full-review/reports/20260911_fd_mfd_fw070_urban050/freeway_fd.png)

점 하나는 **본선 약 513m 구간 × 60초 평균**이다. 동행·서행 각각 21개 구간, 방향별 1,890점이다. 축은 밀도 [veh/km/lane]와 공간 평균 유량 [veh/h/lane]이다. 램프는 제외했다. 서로 다른 구간을 함께 표시한 관측 산점도이므로 하나의 균질 도로 FD나 적합된 capacity 곡선으로 읽으면 안 된다.

- **동행:** 최대 관측 밀도 86.86 veh/km/lane, 최저 구간 평균 속도 9.51 km/h. 높은 밀도에서 낮은 유량이 관측되는 혼잡 분포가 뚜렷하다.
- **서행:** 최대 관측 밀도 26.55 veh/km/lane, 최저 구간 평균 속도 57.52 km/h. 이 조건에서는 심한 혼잡의 하강 분기가 충분히 관측되지 않았다.
- 60초 평균의 최대 관측 유량은 동행 1,404, 서행 1,863 veh/h/lane이다. **이 값은 용량 추정치가 아니다.** 구간별 속도 조건, 수요, 병목 영향이 섞여 있다.

![고속도로 시공간 속도](C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.worktrees/control-full-review/reports/20260911_fd_mfd_fw070_urban050/freeway_speed_time.png)

평균 속도 30 km/h 미만의 연속된 60초 창은 E8에서 39–86분, E7에서 45–82분, E6에서 55–72분이다. **E8 주변 혼잡이 상류 E7·E6까지 확장되는 공간·시간 패턴**이 보인다. 이것만으로 진출 분기·차로 변경·유입 수요 중 하나를 단독 원인으로 확정하지 않는다. 서행에는 30 km/h 미만의 60초 집계점이 없다. 속도도 색상 범위는 0–120 km/h이며 그보다 높은 관측 속도는 상단 색으로 표시했다.

## 도시부 MFD

![도시부 MFD](C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.worktrees/control-full-review/reports/20260911_fd_mfd_fw070_urban050/urban_mfd.png)

가로축은 평균 차량 수 n [veh], 세로축은 **주행 생산량 P [1,000 veh·km/h]**다. 생산량은 영역 내 차량 속도의 합을 시간 평균한 값이며, 사용자가 정의한 **TTD(영역 밖 유출 차량 사건 수)와 다르다.** 회색 점은 30초 평균, 큰 색 점과 연결선은 150초 평균과 시간 순서다. 두 패널의 축 범위는 독립이다.

| 범위 | 물리 요소 수 | 도로 길이 | 차로·길이 | 최대 평균 차량 수 | 최대 관측 생산량 |
|---|---:|---:|---:|---:|---:|
| 정지선 경계 protected network | 581 | 46.498 km | 130.033 lane-km | 738.81대 | 17,693.73 veh·km/h |
| Ω 도시부, IC 접근·연결도로 포함 | 611 | 53.359 km | 150.789 lane-km | 1,013.56대 | 22,543.74 veh·km/h |

물리 요소는 도로 링크와 connector를 합한 수다. 두 범위 모두 본선과 진입·진출 램프 connector를 제외한다. 두 최대값의 발생 시각은 반드시 같지는 않다.

**차량 수가 비슷해도 후반부 생산량이 더 낮다.** PN에서 35–37.5분은 n=640.10대, P=17,131.61 veh·km/h인데, 70–72.5분은 n=640.22대, P=13,541.62 veh·km/h다. 약 21% 낮은 후반 경로가 나타나 단일 곡선보다 이력에 따른 차이가 크다. 이는 제어 개선율이 아니며, 대기 위치·수요 구성·신호 영향 등을 분리한 인과 효과도 아니다.

종료 전 150초의 PN 평균 차량 수는 536.15대, 평균 속도는 21.28 km/h다. IC 연결도로를 포함하면 725.90대, 19.20 km/h다. 차량 수가 줄어도 초기와 같은 자유로운 방출 상태로 바로 돌아가는 모습은 아니다. 이번 단일 런에서 도시 망 전체의 임계 차량 수나 명확한 capacity drop 크기를 적합·확정하지 않았다.

## 집계·검증

- 각 1초의 차량 수 N(t), 속도 합 S(t)를 집계하고 1초 사다리꼴 적분을 사용했다. 빈 t=0에서 시작하며 비중첩 시간창으로 평균한다. 빈 구간의 N·S는 0이고 속도는 미정이다.
- FD: k = 시간 평균 N / 구간 lane-km, q = 시간 평균 S / 구간 lane-km. **1초 위치·속도 표본에 기반한 공간·시간 근사**이며, 단면 검지기 통과량이나 연속 궤적을 정확히 적분한 값은 아니다.
- 본선 구간 경계·chain offset은 해당 런의 ver2n21 VBS와 같게 두었다. lane-km는 각 구간과 실제 물리 링크가 겹치는 길이 × XML 차로 수로 계산했다. 동행의 4→3차로, 서행의 3→4차로 변화를 반영했다.
- FD의 고정 공간 밖 기록 57 vehicle-second(입력 위치 <0), 6,026 vehicle-second(종단 초과)는 FD 집계에서만 제외했다. 종단 초과는 기존 native 기록 단계 차이 사례와 일치하는 현상이며 도로를 연장해서 처리하지 않았다. Ω 및 도시 MFD 차량 수는 원래 링크 소속 정의를 유지했다.
- PN은 기존 `pn_internal_links`에 canonical turn의 internal/inflow connector 포함·나머지 제외 규칙을 적용하고, 현재 Ω와 교집합한 후 본선·램프를 제외했다. IC 접근부까지 포함하는 Ω 도시부와 분리했다. 모델의 player 소유권을 다시 유도하거나 변경하지 않았다.
- 도시 정규화 CSV의 길이는 XML 3D 중심선이다. 본선에서는 3D와 2D 길이가 같다. 도시의 주 그림인 n–P에는 길이 정규화가 사용되지 않는다.
- FZP SHA 확인, 10,687,229행과 1–5400초 전체 확인, 프레임별 차량 ID 중복 검사(읽기 청크 경계 포함), 기존 Ω 차량 수 5,400개 시점 정확한 일치를 확인했다. Ω TTT는 기존과 같은 2,278.25680556 veh·h다.
- 기존 30초 순간값 7,560개도 기존 clamp 규칙을 별도로 적용한 검증 집계에서 재현했다. 새 FD에는 그 순간값을 시간 평균으로 잘못 사용하지 않았다.
- 원본 런에는 native 차량 삭제 127건, Ω 내부 미해결 disappearance 206건이 기록돼 있다(서로 배타적인 합계가 아님). 이를 정상 유출로 새로 분류하거나 지우지 않았다. **이 그림은 해당 오류까지 포함한 실제 런의 관측이며, 깨끗한 용량 보정 실험이라는 뜻은 아니다.**

## 파일과 재현

- `freeway_fd.png/.svg/.pdf`, `urban_mfd.png/.svg/.pdf`, `freeway_speed_time.png/.svg/.pdf`
- `freeway_fd_points.csv`: 30·60·150초 창의 본선 FD 집계점.
- `urban_mfd_points.csv`: 30·150초 창의 n, P 및 길이 정규화 k, q. `scope` 필드로 PN·Ω 도시부·램프·본선·Ω를 구분한다.
- `geometry_and_scope.json`, `freeway_geometry.csv`: 링크 범위와 분모.
- `aggregates_1s.npz`: 그림을 다시 그릴 수 있는 1초 집계.
- `validation.json`: 원본 SHA, 수치 검증, 공간 제외 기록.

PowerShell에서 작업 디렉터리를 `.worktrees/control-full-review`로 두고 실행한다.

```powershell
& 'C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B -X utf8 'reports/20260911_fd_mfd_fw070_urban050/build_figures.py'
```

`--render-only`를 붙이면 저장된 집계 CSV에서 그림만 다시 만든다. VISSIM이나 controller를 호출하지 않는다.
