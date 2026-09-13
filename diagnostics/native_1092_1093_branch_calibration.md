# Native input1092/1093의 관측 분기 — seed13 보정 근거

**1092는 관측80대 모두 동향 SC12 방향, 1093은 관측67대 모두 서향 SC11 방향이었다.** Native static route decision이 없다는 이유로 1:1 분할하면 이 기준 궤적과 어긋난다. 생산 분율을 바꾸지 않았으며, 이것은 명시적인 seed13 offline calibration 자료다.

| 입력/source | 첫 branch | 전체 관측 ID | connector 직접 관측 | connector 건너뛴 고유 target | 반대 branch | 검열/미해소 |
|---|---|---:|---:|---:|---:|---:|
| 1092 / 217 | 10350 → 1210012103 (SC12 방향) | 80 | 80 | 0 | 0 | 0 |
| 1093 / 225 | 10359 → 1220012001 (SC11 방향) | 67 | 38 | 29 | 0 | 0 |

고정 Ver2 XML에서 source217/225는 incoming connector0·해당 native input1개·static decision0이다. 두 출구는 모두 source lane1에서 시작한다. 모든147개 ID가 network에 처음 나타난 link도 해당 source였으며, source 재진입/중복 timestamp ID/관측 gap은0이다. source를 처음 본 시각 이후 최초 다른 link가 실제 connector인지,1초 사이 connector를 지난 고유 직접 하류 road인지 구별했다. 후자를 직접 connector 관측으로 표기하지 않았다.

| Source 최초 관측 창 (시작 제외, 끝 포함) | 1092:10350 | 1093:10359 | 반대 방향/검열 |
|---|---:|---:|---:|
| (0, 900]초 | 11 | 17 | 0 / 0 |
| (900, 1800]초 | 14 | 14 | 0 / 0 |
| (1800, 2700]초 | 17 | 15 | 0 / 0 |
| (2700, 3600]초 | 18 | 11 | 0 / 0 |
| (3600, 4500]초 | 13 | 6 | 0 / 0 |
| (4500, 5400]초 | 7 | 4 | 0 / 0 |

두 관측 선택은 source에서 더 먼저 만나는 connector와 일치한다:217의10350 시작18.385578m <10349의18.462590m;225의10359 시작29.961442m <10360의30.459113m. 이는 가능한 기하 설명이며, 이 자료로 VISSIM의 모든 no-route 선택 규칙이나 다른 seed의 확정 분기를 증명하지 않는다. 각 branch의 target lane/position 및 실제 geometry 길이를 JSON topology에 보존했다.

분율의 분모는 실제 source에서 관측한 고유 ID다. Native 수요가 모두 주입되었다고 가정하지 않으며, 요청 volume을 관측 admission으로 바꾸어 쓰지 않는다. source에서1초도 관측되지 않은 차량이 있다면 이 cohort에 들어오지 않는다. 이번 두 source는 관측 cohort 내부의 검열이0이므로 resolved 분율과 전체 관측 분율이 같다. JSON에는 일반적으로 이 두 분모를 별도로 유지한다.

**검증 분리:** 전체0~5400초 seed13 자료로 얻은 보정치를 같은 실행의 이른 시점 예측 검증에 쓰면 미래 정보가 유입된다. 향후 생산에서 명시적으로 고정한 offline prior로 사용할 경우에도 seed14 또는 따로 보존한 prospective run에서 검증해야 한다. 본 산출물에는 seed14 검증이나 생산 승인이 없다. 900초별 표는 같은 seed 내부의 기술 통계이며 독립 holdout이 아니다.

전체1초 FZP 5400프레임·26,693,633행을 한 번 읽었다. CSV는147개 ID별 source 최초/마지막 위치, 출발 관측구간, 최초 다른link, 분기 해소 방식과 검열 상태를 보존한다. 입력 FZP·network·run manifest·producer의 SHA와 전후 source 변경 검사는 JSON에 있다.

재현: `python -X utf8 -m diagnostics.calibrate_native_1092_1093`. 집중 회귀: `python -m unittest diagnostics.test_native_branch_calibration -v`.
