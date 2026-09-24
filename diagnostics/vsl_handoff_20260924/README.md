# VSL 이득 재현 및 다른 컴퓨터 실행 인계 — 2026-09-24

**Seed29의 실제 VSL 이득과 학습 구간의 METANET 이득 예측을 재현하는 패키지다. 다른 seed에서도 순이득을 맞추는 모델이 완성됐다는 뜻은 아니다.** Seed43에서 확인된 실제 손해와 예측 실패를 함께 보존했다. 기본 controller·SDMPC에 이 후보를 승격하지 않았다.

이 폴더가 이번 실행 인계의 진입점이다. 이전 [VSL 실험 설명](../../docs/vsl_bottleneck90_reproduction_20260924/README.md)에 더해 실제 INPX·42개 SIG, 휴대 가능한 예측 입력, 기존 runner를 호출하는 준비 도구를 포함한다. 원래 C:/D: 자료 경로는 일부 증거 파일의 출처 표기이며 실행에 필요하지 않다. 대용량 FZP는 Git에 추가하지 않았다.

## 무엇이 확인됐나

| 비교 | 실측 변화 | 예측/판정 |
|---|---:|---|
| Seed29, VSL90을 900초부터, 9000초 동측 국소 TTT | −6.153% | 실제 VISSIM 결과 |
| 같은 런, 전체 망 내부+미삽입 외부 대기 | −78.7637 차량·시간 (−0.2721%) | 작은 전역 순이득 |
| Seed43, 같은 9000초 정책, 전체 망 내부+외부 대기 | +67.6357 차량·시간 (+0.2358%) | 손해; 일반화 성공 아님 |
| Seed29, 공통 2220.1초 상태에서 450초, 2250초부터 VSL90 | −0.3250 차량·시간 | 이 패키지 후보 −0.269119; **학습 자료 재현** |
| Seed43, 같은 450초 개입 | +0.791667 차량·시간 | 후속 prior/local-FD 후보 −0.147650/−0.138854; 방향 실패 |

9000초 동측 국소 범위는 본선+진입/진출 커넥터+직접 진입 접근 링크다. 450초 예측 범위는 **동측31셀+진입4/진출4 커넥터**, 30초 재고 적분이며 도시 접근부·망 외부 대기를 포함하지 않는다. 둘을 같은 지표로 비교하지 않는다. Seed43의 마지막 행은 이 패키지의 순수 A0.5_E4와 다른 후속 후보이며, 후보별 구분은 [결과와 원본 증거](evidence/RESULTS.md)에 있다.

## 1. VISSIM 없이 예측 재현

저장소 루트에서 Python 3.12와 NumPy로 실행한다. 검증 환경은 Python 3.12.14, NumPy 2.3.5다. 그래프 후처리에는 Matplotlib도 필요하다.

```powershell
git clone --branch codex/control-full-review-20260909 https://github.com/Ming2you/VISSIM.git
cd VISSIM
python -m venv .venv
$py = (Resolve-Path .venv/Scripts/python.exe).Path
& $py -m pip install numpy==2.3.5 matplotlib==3.11.1
& $py -B diagnostics/vsl_handoff_20260924/reproduce.py offline --output results/vsl_offline_s29
```

이미 clone한 경우에는 현재 변경을 보존한 뒤 이 브랜치 최신 커밋을 가져온다. 출력 폴더는 매번 새 경로여야 한다. 성공 시 다음을 검사한다.

- 소스·입력 SHA256 manifest 일치.
- NC와 VSL 각각 cells/flows/ports/ramps 배열이 저장 결과와 정확히 일치.
- 차량 보존 잔차 < 1e−7대, 재고 유한·비음수.
- 예측 TTT: NC 140.690656672765, VSL 140.421537434149 차량·시간.
- 예측 차이 −0.269119238616, 같은 범위 실측 차이 −0.325000.

`case_29.json.gz`는 실제 예측 호출에 사용된 공통 초기 상태·과거 기반 경계 예측·실행 명령을 저장한 fixture다. 실측 미래 재고는 점수 계산에만 쓰고 rollout에 넣지 않는다. 내보내기 전에 미래 자료를 잘라도 입력 창이 같음을 재확인했다. 실제 모델은 기존 `canonical_harness.py`와 유일한 adapter를 사용한다. fixture는 새 VISSIM 결과를 자동 보정하거나 새로운 상태를 생성하는 기능은 아니다.

## 2. 실제 VISSIM에서 NC/VSL 재실행

Windows, 라이선스가 있는 **VISSIM 2020 COM**이 필요하다. 원본 버전은 2020.00-14 [95957]이다. 다른 버전에서는 같은 seed여도 궤적이 동일하다고 보장하지 않는다. 고속도로 동·서80%, 도시90%, 진입 DSD110, 수정된 기하·경로·native 신호를 정확한 원본 INPX로 보존했다.

```powershell
# 경로는 해당 컴퓨터의 여유 있는 드라이브로 지정한다.
& $py -B diagnostics/vsl_handoff_20260924/native.py prepare --output D:/VISSIM_runs/vsl_repro_s29 --seed 29
powershell -NoProfile -ExecutionPolicy Bypass -File D:/VISSIM_runs/vsl_repro_s29/run_commands.ps1 -Python $py
```

`prepare`는 VISSIM을 실행하지 않는다. 이후 PowerShell 명령은 기존 `fast_nc_run.ps1`로 NC→VSL 두 런을 순서대로 실행한다. 기존 VISSIM 창이 있으면 실행을 거부하며 다른 창을 종료하지 않는다. 초기300초 실제 진행 없음 watchdog은 해당 런 소유 프로세스에만 적용한다.

원본 수요·신호·경로를 그대로 두고, **동측 DSD63–66만 900초에 분포110→90**으로 변경하여 9000초까지 유지한다. 다른 DSD와 RM은 기존 무제어 조건이다. 분포 ID90은 모든 차량의 속도를90에 고정한다는 뜻이 아니다. 분포 곡선은 INPX 안에 있다. SimRes10, FZP5초, LDP·명령 적용 readback·오류 기록·native 전체 망 내부 체류/외부 미삽입 대기 측정을 유지한다. 큰 배경 JPG는 저장소의 기존 파일을 SHA 검사 후 복사한다.

별도 seed 재검증은 새 출력 폴더에 `--seed 43` 등으로 준비한다. Seed만 바꾸고 원본으로 되돌리면 바이트가 정확히 같음을 준비 단계에서 검사한다. 이미 생성된 출력에 덮어쓰기·자동 재시도하지 않는다.

450초 예측 개입과 맞는 짧은 native 재현은 다음과 같다. 최초2250초까지 같은 상태로 진행하므로 전체3000초 런이다.

```powershell
& $py -B diagnostics/vsl_handoff_20260924/native.py prepare --output D:/VISSIM_runs/vsl_response2250_s29 --seed 29 --start 2250 --end 3000
```

이 짧은 런과 900초부터 제한하는 9000초 런은 서로 다른 실험이다. 짧은 런의 출력으로 아래9000초 전용 분석을 실행하지 않는다.

## 3. 9000초 두 런이 모두 끝난 뒤 비교

```powershell
& $py -B diagnostics/vsl_handoff_20260924/analyze.py --native-root D:/VISSIM_runs/vsl_repro_s29 --output results/vsl_native_s29
```

완료·소유 프로세스 종료·실제 실행 검증 파일을 확인한 뒤 기존 후처리로 FZP를 한 번씩 읽는다. Ω TTT, Ω 외부 이동 사건(TTD), 정상 종료·삭제·미삽입, 동·서 본선 히트맵과 **native 전체 망 내부+외부 대기 합**을 출력한다. 분석의 `TTT_FW_E`는 동측 본선만이며 위 표의 접근부 포함 −6.153%와 범위가 다르다. 살아서 non-control area로 나간 차량은 Ω TTD에 포함하며 내부 이동·삭제·종료 잔여는 정상 유출로 세지 않는다.

LSA만으로 COM 신호 실행을 판정하지 않는다. 사용자 승인대로 native LDP와 적용 readback을 검사하며, 누락·불일치는 실패로 남긴다. 원래 자료의 native 계측 결과와 5초 FZP 적분은 서로 다른 계측이므로 마지막 몇 초까지 정확히 같다고 가정하지 않는다.

## 변경한 모델과 다음 작업

이 후보는 이전에 보정한 **1초 모델 적분**을 그대로 재현한다. native FZP 기록은5초이고 비교 출력은30초다. 이관 중 적분을5초로 바꾸어 같은 보정값이라고 주장하지 않았다.

이번 후보는 기존 METANET의 제한속도별 FD(A=0.5, E=4), 차량이 받은 VSL 분포를 보존 유량으로 수송하는 재고, 국소 자유속도·anticipation 보정을 사용한다. 실제 합류 유량에 따른 감속, 진출부 재고·배수와 램프 대기 비용은 유지했다. 선택 값은 `candidate.json`, `parameters.json`, `segment_params.json`에 고정했다. FD 변화는 이론상 용량에도 영향을 주며, 실측으로 확인한 보편적 용량 보너스는 아니다. 90 외 명령으로 외삽해 이득을 주장하지 않는다.

다음 컴퓨터에서는 먼저 위 두 재현을 확인하고, 후보를 동결한 별도 seed에서 혼잡 시작·회복·방출·램프 대기를 함께 비교해야 한다. 우선 해결할 것은 seed43의 VSL 손해 방향 실패와 RM 순이득 누락이다. RM은 head 이후 재고·차로별 합류 시점, 이어서 본선/진출부 추가 방출을 분리해 검사한다. 성공 label이나 임의 보상항을 추가해 순이득을 만들지 않는다. full follower/GNE/SDMPC 연결은 이 단계의 검증 대상이 아니다.

## 이관 검증

실행 파일만 복사한 폴더와 **Git index에서 새로 checkout한 폴더**에서 같은450초 배열 재현을 통과했다. 새 checkout에서도9000초 native 두 조건 준비가 통과했다. 900/9000 및2250/3000 native 준비 profile은 완료된 원본 profile과 정확히 같고, 28개 기존 writer/FD 단위 검사가 통과했다. 기존 Ω 경계 ledger가 CRLF 바이트를 요구하는6개 파일은 Git 속성으로 같은 줄바꿈을 복원한다. 나머지 외부 소스의 manifest 비교는 LF/CRLF만 정규화하며, native 망·SIG·증거는 원본 바이트를 보존한다. 이번 이관 작업에서 새 VISSIM 런은 시작하지 않았다. [`verification.json`](verification.json), [`manifest.json`](manifest.json), [`evidence/index.json`](evidence/index.json)을 함께 확인한다.
