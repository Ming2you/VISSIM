# 6056c94 two-branch FD 독립 검토

검토 대상: `6056c94770bb45c19e0a32b90416444db2bce2d1`, `n21i_i1_20260909.json`, 실제 `wu-link` 경로. 작성자는 production 코드/설정 및 VISSIM을 변경하지 않았다. `systematic-debugging`과 `karpathy-guidelines`에 따라 배선 추적 후 작은 오프라인 재현을 수행했다.

**판정: two-branch 활성화 배선은 실제로 동작한다. 그러나 셀별 속도·임계밀도·국소 램프수용력의 정의가 서로 다르고, 적합한 혼잡가지를 실행 모델이 보존하지 않는다. i1을 '적합을 마친 VSL capacity-drop 회피 모델'로 해석하면 안 된다.**

## 축별 의심 → 근거 → 판정

| 의심 | 근거 | 판정 | 조치 |
|---|---|---|---|
| two-branch 키가 다시 미배선인가 | installer `vissim_stackelberg_adapter.py:8635-8654`, main 설치 `:12250`, 실행 metadata와 pickle 왕복 확인 | 설계 의도: 배선 동작 | 유지. 다만 enabled일 때 누락/비정상 임계값을 명시적으로 거부할 것 |
| 낮은 제한속도가 항상 자유류 목표속도를 낮추는가 | active two-branch가 `min(vsl, cell_v_free)` 없이 vsl 자체를 반환: `metanet.py:33-39,88-92`; 셀별 vf는 adapter `:8793`에서 교체 | **실재 오류**: 저속 합류셀에서 120→100 명령이 오히려 목표속도를 높임 | VSL cap과 cell 자유속도의 관계를 단일 함수로 정의하고 단조성 검증 |
| 원하는 속도와 capacity-drop 임계가 같은 FD를 쓰는가 | adapter `:8791-8798`은 cell vf, `metanet.py:68`은 network vf=120 | **실재 오류**: active VSL에서 셀별 접점과 판정 임계가 다름 | cell vf/jam/nominal critical 및 inactive cap을 공유하는 critical 함수로 통일 |
| anticipation capacity drop도 VSL critical을 읽는가 | adapter `:8800-8807`은 p.rho_crit=25/28만 사용하고 vsl을 무시 | **실재 오류**이나 i1에서 해당 게이트는 꺼짐 | two-branch 활성 경로에서 동일 cell critical 사용; off 때 비트 동일 |
| global/local 램프 receiving이 정합한가 | global `metanet.py:289-294`은 shifted critical, LIVE local `wu_faithful_follower.py:1971-1973`은 고정 27 | **실재 오류**: 모델 경로 차이. 현재 저밀도 램프에서는 대부분 ramp cap이 가림 | global/local 공통 산식 또는 adapter rebind, 높은 밀도 합성 대조 포함 |
| 42셀의 qcap/vf 유사성이 scalar critical의 실증 검증인가 | 기존 exponential capacity 식에서 vf가 소거됨; D-lit shape가 차로급 2개로 공통 | 설계 의도인 차로급 풀링. **실증 주장에는 근거 부족** | 계산상 용량 보존 근사라고 표현하고 3차로의 약 2.6% 차이를 보고 |
| 무제어 혼잡가지 적합이 실행 FD를 정했는가 | 적합기는 두 자유계수 w,jam을 추정하고 jam만 풀링, 실행은 w를 qcap/vf 앵커로 다시 생성 | **실재 방법론 불일치** | 고정 capacity 조건의 jam 1차원 적합 또는 capacity와 w를 공동 적합한 연속 FD로 재검증 |
| 171.4를 얻었으니 180의 타당성이 확인됐는가 | scalar 180은 `vendor/.../src/config/default.yaml:30`에서 온 값. raw max128보다 크고 pooled 추정에 근접 | 확정 불가: 안전한 표현 범위와 calibration은 별개 | 관측 재현/시드 보류/붕괴 전후 잔차 비교 필요 |
| i1이 two-branch와 capacity drop을 짝으로 평가하는가 | 실효 `capacity_drop_discharge_phi=1.0`, `capacity_drop_anticipation=False` | **그 주장은 틀림**. i1은 FD 교체 팔 | 두 게이트를 섞기 전에 모델 검증, 그 뒤 별도 ablation |

행 번호는 검토 기준 커밋 기준이다. root의 후속 수정으로 이동할 수 있다.

## 1. 실제 배선과 살아 있는 경로

`scripts/resolve_live_controller.py --tuning evaluation/configs/n21i_i1_20260909.json --controller wu-link` 실행 결과:

- `PricedWuLinkStackelbergController`, `LinkAgentWuFollower`, 2링크 × 21셀. **주의: resolver가 출력한 `segment_agents=False`는 하드코딩된 설명이라 실제 객체 상태가 아니다.** n7/i1은 `metering_in_gne=true`로 `segment_agents=True`가 된다. 하지만 `LinkAgentWuFollower._solve_freeway_segment_agents` override(`priced_wu_link_controller.py:149-167`)가 `_solve_freeway_agent_metered`→`_solve_freeway_agent_local`로 넘기므로 여전히 링크 단위 국소 롤아웃이다. base의 점유 동결 segment 경로를 탄다는 뜻이 아니다.
- `scripts/whose_code.py _local_ramp_release ... --controller wu-link`: WuFaithfulFollower의 정의와 호출 LIVE 3건, F1 정의 DEAD 1건.
- 실제 installer를 순서대로 호출해 `two_branch_fd_enabled=1`, `two_branch_rho_crit=15.164` 확인.
- network scalar critical은 cap120/100/80에서 각각 15.164000/17.895284/21.826614.
- cfg pickle 왕복 후에도 `rho_crit_two_branch=15.164` 보존. 모듈 패치는 worker installer `vissim_stackelberg_adapter.py:4737`에서 재설치한다. 이번 검토는 실제 process-spawn 가격 동등성까지는 실행하지 않았다.

`vsl_active = vsl < max(vsl_set)-0.5`가 `metanet.py:610`, `local_freeway_plant.py:295`에 있다. 따라서 **120은 무제어 표식**이고 FD가 cell vf로 복귀한다. 'two-branch가 120을 모든 셀 목표속도로 강제한다'는 비판은 틀리다. 문제는 active인 100/80에서 발생한다.

현재 installer는 docstring의 'rho_crit_two_branch를 반드시 같이 줘라'를 강제하지 않는다(`:8641-8644`). `enabled:true`만 있으면 27로 fallback되어 잘못된 용량을 만들 수 있다. i1은 15.164를 명시했으므로 이번 팔의 직접 오류는 아니다.

## 2. 실제 함수 재현: 낮은 cap이 가속을 유도하고 critical 정의가 갈림

전체 i1 config를 로드한 후 실제 adapter의 segment/two-branch installer를 실행했다. `ControlAction.vsl['FW_E__seg{i}']`를 바꾸고 실제 `segment_vsl`, `effective_desired_speed_kmh`, `effective_rho_crit`를 호출했다. 아래 속도는 rho=5에서의 목표속도이고, 'FD 접점'은 원하는 속도 함수가 실제 사용하는 cell vf로 직접 계산한 값이다.

| 셀, cell vf | cap | 목표속도 | 실제 FD 접점 | global effective critical |
|---|---:|---:|---:|---:|
| E8, 118.29 | 120 | 118.29 | 15.164 | 15.164 |
| E8 | 100 | 100.00 | 17.665 | 17.895 |
| E8 | 80 | 80.00 | 21.553 | 21.827 |
| E9, 91.31 | 120 | 91.31 | 15.164 | 15.164 |
| E9 | 100 | **100.00** | **13.948** | **17.895** |
| E9 | 80 | 80.00 | 17.104 | 21.827 |
| E14, 78.10 | 120 | 78.10 | 15.164 | 15.164 |
| E14 | 100 | **100.00** | 12.066 | 17.895 |
| E14 | 80 | **80.00** | 14.834 | 21.827 |
| E15, 75.96 | 120 | 75.96 | 15.164 | 15.164 |
| E15 | 100 | **100.00** | 11.757 | 17.895 |
| E15 | 80 | **80.00** | 14.460 | 21.827 |

E15는 i1의 고정 하류 구역이라 이 후보가 실제 채택되지는 않는다. E9/E14는 가변 구역이므로 활성 오류다. E9 cap100은 lower cap에도 임계가 **15.164→13.948로 하락**하는데, 리더/flow 제약은 **15.164→17.895 상승**이라고 읽는다. 단순 numerical tolerance 문제가 아니다.

명령이 cell vf를 넘으면 비활성 cap처럼 취급하거나 `min(cell_vf, cap)`을 사용해야 물리적인 상한 의미가 유지된다. desired speed와 critical 양쪽에 같은 규칙이 필요하다. critical만 바꾸면 두 함수는 여전히 어긋난다.

anticipation 분기는 별도 합성 조건으로만 켰다(`nu_cong=90`, 기존 nu=30). E8 rho20에서는 cap120/100/80 모두30, rho26에서는 모두90이었다. 실제 VSL critical은 cap에 따라 달라지지만 wrapper는 rho25 기준만 본다. i1 게이트가 false라 이 결과를 현재 실행 손실이라고 세면 안 된다.

global/local 램프 receiving은 rho160, cap100, qcap6937 합성조건에서 각각 약855.87/906.80 veh/h로 갈린다. i1 관측 merge rho가 훨씬 낮다면 둘 모두 1800 ramp cap에 가려진다. 코드 결함의 존재와 현재 손실 크기를 구분해야 한다.

## 3. 적합기의 결과와 실행하는 혼잡가지가 다름

`fit_two_branch_fd_ver2_20260909.py:66-80`은 `q=a+b*rho`에서 **절편과 기울기 두 개를 자유롭게 적합**한다. `:123-130`에서 jam과 w를 보관하지만 `:139-148`에서 jam 중앙값만 채택한다. 실행 `metanet.py:37,47`은 `w=vf*tb/(jam-tb)`로 w를 다시 만든다. 이는 원래 적합한 straight line을 재현하는 절차가 아니다.

| 셀 | 적합 w | 실행 w(jam180/tb15.164) | 기존 qcap | 적합 straight line을 nominal critical까지 외삽한 q |
|---|---:|---:|---:|---:|
| E0 | 2.096 | 7.909 | 1303.6 | 950.5 |
| E5 | 9.953 | 11.035 | 1818.8 | 1554.7 |
| **E8 병목** | **6.873** | **10.882** | **1793.7** | **1244.3** |
| E9 | 12.763 | 8.400 | 1384.6 | 775.8 |
| W5 | 1.947 | 10.889 | 1842.4 | 1610.2 |

E8에서 published fitted line과 실제 채택 FD의 q_lane을 비교하면:

| rho | published fit | 실행 FD | 차이 |
|---:|---:|---:|---:|
| 20 | 1211.1 | 1741.1 | +43.8% |
| 40 | 1073.6 | 1523.5 | +41.9% |
| 80 | 798.7 | 1088.2 | +36.2% |
| 120 | 523.8 | 652.9 | +24.7% |

이것은 **원시 관측 오차율이 아니라, 적합기가 낸 straight line과 실행 FD 간 불일치**다. 이 checkout과 원 작업 디렉터리에서 참조 무제어 raw run이 없어서 표본별 residual/보류검증은 수행할 수 없었다. 출력 JSON은 읽고 계산할 수 있었다.

capacity를 선행 D-lit 값으로 고정하려면 그 제약을 만족하는 `q(rho;jam)=qcap*(jam-rho)/(jam-tb)`를 직접 적합해야 한다. 반대로 자유 적합 w를 보존하려면 nominal critical/capacity와 접점이 달라져야 한다. 이 충돌은 구조적 capacity drop 또는 서로 다른 regime을 자료가 포함한다는 신호일 수도 있으므로, 사후에 median으로 숨기면 안 된다.

## 4. 표본 선택·풀링·스칼라 근거

- **속도 기준만으로 branch를 정할 수 없다.** `:112`의 `v<0.75*vf`는 혼잡가지뿐 아니라 저밀도 합류 마찰/과도응답/느린 차량도 고른다. 출력 E10은 최대rho14.60인데 congested 표본8개로 분류되어 결국 positive slope로 기각된다. nominal tb15.164보다 최대rho 자체가 낮다. 42셀 중 유효15, positive slope 무효10, 표본부족17이다.
- 시공간 표본이 상관되어 있고 한 seed에서 얻은 궤적이므로 셀당6개는 식별성의 증거가 아니다. rho 범위, regression 잔차, 기울기 신뢰구간, jam profile/부트스트랩 안정성과 보류 seed 검증이 필요하다.
- **median은 outlier에 강한 선택 자체로는 합리적이다.** jam468.65/842.57 두 값을 제외해도 중앙값171.37→169.55(약1.1%)만 바뀐다. 따라서 두 outlier가 median을 폭발시켰다는 비판은 맞지 않는다. 다만 이 셀들은 slope가 약해 jam이 약하게 식별된다는 증거이며, 모든 셀 jam이 공통이라는 증거가 생기는 것은 아니다. E9 jam75.95와 E8 jam196.21처럼 병목/합류 차이도 남아 있다.
- **42개의 tb가 두 값에 몰리는 것은 산술이다.** D-lit의 `qcap=vf*rho_crit*exp(-1/a)`이므로 `qcap/vf=rho_crit*exp(-1/a)`이고 cell vf가 소거된다. 출력42셀을 대조한 최대차는 rounding 수준0.000678. 4차로 shape(25,2)는15.1633, 3차로 shape(28,1.70295)는15.5646이다. scalar15.164 사용은 3차로 nominal capacity를 약2.6% 낮추는 근사이며, 관측42셀을 독립적으로 적합해서 얻은 일치가 아니다.
- scalar tb 자체가 cell vf 편차와 수학적으로 충돌하지는 않는다. vf에 비례해 용량이 바뀌는 일관된 family를 만들 수 있다. **실제 충돌은 desired speed는 cell vf를 쓰고 다른 critical 소비처는 global vf를 쓴다는 것**이다.
- '셀별 tb는 줄 수 없다'는 현재 loader의 whitelist와 wrapper 전달 형식의 제약이다(`adapter:8206-8207,8798`). 모델 이론이나 network dataclass가 cell runtime context를 통한 전달까지 금지하는 것은 아니다. 다만 셀별 자유도가 실증적으로 필요한지 먼저 판단해야 한다.

## 5. 프롬프트의 물리 해석에 대한 수정

**two-branch만으로 diverge single-lane queue 병목이 생기지는 않는다.** 현재 FD는 cell 평균 density-speed 관계이고 off-ramp/직진 차량의 차로별 대기·방류·FIFO를 분리하지 않는다. nominal critical을 옮기고 cap에 따른 speed-density 형상을 바꾸는 것과, 커넥터10682의 처리량 및 차로1 정체를 표현하는 것은 다른 문제다. downstream 처리량/저장고/차로별 mixing 검증이 필요하다.

**i1은 capacity-drop 회피 팔이 아니다.** runtime값은 discharge_phi1, anticipation false. 따라서 i1의 결과가 좋아져도 'two-branch와 drop의 결합을 검증했다'고 할 수 없다. 반대로 i1이 져도 모든 VSL 물리기구가 기각된 것은 아니다.

**'exponential cap의 capacity 권한0'을 'VSL 권한0'으로 확대하면 틀린다.** 정적 최대유량이 같아도 낮은 밀도의 속도/흐름은 cap에 반응한다. E8 rho10에서 exponential 목표속도109.195이고 cap80이면80으로 낮아진다. 다른 speed 항을0으로 둔 10초 relaxation(τ18초)만으로 속도92.976, 4차로 rho*v는4367.8→3719.0 veh/h가 된다. 이는 실제 rollout/plant 이득의 증명이 아니라, **과도 유입 조절 가능성0이라는 보편 주장에 대한 반례**다. 병목까지의 운행시간, 저장공간, rate 변화, VSL 존 경계가 작동점을 결정한다.

**dynamics 블록의 provenance와 배선을 구분해야 한다.** segment loader는 JSON `segments` whitelist만 읽고 파일 최상위 `dynamics`는 읽지 않는다(`:8203-8213`). τ18,ν30,κ40,δ0.3의 실효 출처는 i1 `config_overrides.network:7435-7439`; φ3은 `freeway:7898`이다. 거절된 팔과 동일한 값을 복사했다는 calibration 비판은 유효하지만, '그 파일 dynamics 블록이 runtime에 먹는다'는 dataflow 설명은 부정확하다.

τ18에서 순수 relaxation 잔차는 30초 뒤 `(1-10/18)^3≈0.0878`이므로 초기−22km/h가 약−1.93km/h로 줄어드는 계산은 맞다. 그러나 full METANET의 convection/anticipation/merge/lane-drop 항과 density가 계속 바뀌므로 이것만으로 '모든 전조가30초 뒤 사라진다'고 확정할 수는 없다. 특히 two-branch 도입 후에는 기존τ calibration의 식별성과 표본외오차를 다시 확인해야 한다.

## 6. 우선 수선과 판별 실험

1. **실재 wiring/model 일관성 오류부터 격리한다.** two-branch가 켜진 경우에만 cap을 cell 자유속도와 정합하게 하고, desired speed·critical·anticipation·global/local receiving을 같은 정의로 맞춘다. vendor를 변경하지 말고 단일 adapter에서 runtime patch. two-branch off baseline 비트 동일과120→100→80의 목표속도 단조성을 확인한다.
2. **enabled 설정 검증을 추가한다.** finite `0<tb<jam`을 요구하고 누락tb를 허용하지 않는다. step metadata에 셀별 effective critical의 min/max와 inactive cap 의미를 기록한다.
3. **기존 데이터가 돌아오면 FD 재현검증을 먼저 한다.** 무제어 관측상태를 동일하게 시작해서 E5–E10의10/30/150초 예측을 single-branch 대 consistent two-branch로 비교한다. 붕괴 전/후를 나눠 density·speed·discharge·off-ramp blocked flow를 보고, fitting에 사용하지 않은 시간/seed로 확인한다.
4. **적합 방법을 비교한다.** (A) 현행 scalar jam180, (B) 고정qcap를 지키는 jam 제약적합, (C) 식별되는 셀/차로급에서 capacity와 backward wave 공동적합. held-out 오차와 physical range를 함께 비교한다. fitting 자료로만 더 좋아진다는 이유로 채택하지 않는다.
5. **VSL 이득은 원인별로 구분한다.** n7 일관성 수정팔→two-branch→그 후 필요시 drop 별도팔 순으로 같은 시드 비교. 모든 팔의 동일 actuator 주소와 실제 명령/속도 반응을 확인한다. i1 기존 결과는 위 불일치가 섞인 FD 교체 결과로 표시한다.

이번 검토만으로 two-branch를 채택/폐기하거나 capacity-drop phi를 켤 근거는 부족하다. 확실한 것은 배선이 살아 있다는 것, 활성 cap의 비단조성·정의 불일치를 먼저 고쳐야 한다는 것, 그리고 현재 적합 출력은 실행 FD의 관측충실도를 증명하지 못한다는 것이다.

## 7. 후속 구현 준비 및 검증

root 요청으로 신규 `evaluation/controllers/freeway_fd.py`와 `diagnostics/test_freeway_fd.py`를 작성했다. 기존 adapter/vendor 및 숫자 적합은 수정하지 않았다. **이 시점에는 실런 경로에 아직 연결하지 않았다.**

설치 인터페이스는 `install_freeway_fd_runtime(a, w, cfg, tuning=None)`이다. `a`는 canonical adapter module, `w`는 `src.controllers.wu_faithful_follower` module이다. 기존 two-branch 값 설치와 zone/segment runtime 설치 **뒤**에 부모에서 호출하고, price worker에서 zone/segment runtime **뒤**에 `tuning=None`으로 다시 호출해야 한다.

새 FD는 adapter의 `_FW_SEG_CTX`를 읽지 않는다. `segment_vsl`이 반환하는 수치(float subclass)에 그 호출의 cell FD snapshot을 싣고 speed/critical/nu가 직접 읽는다. 덕분에 다른 셀의 호출을 사이에 끼우거나 legacy context를 일부러 오염시켜도 기존 token의 FD가 바뀌지 않는다. local ramp receiving도 동일 함수를 사용한다. FD 비활성 cfg는 installer 무변경이고, 이미 wrapper를 설치한 프로세스에서도 off 경로는 기존 함수를 호출한다.

회귀검사 **11개 PASS** (`python diagnostics/test_freeway_fd.py`, 약0.7초):

- actual controller가 `segment_agents=True`, `metering_in_gne=True`인 Link override 경로인지 확인.
- cell E8/E9/E14의 cap120/100/80 단조성·접점 연속성·desired/critical 일치.
- nu branch가 같은 cell critical을 사용.
- 음수/0/임계/혼잡/jam/초과 density에서 bounded finite speed.
- global/local ramp release가 rho0~200, cap120/100/80에서 정확히 일치.
- global/local 4substep density/speed/lane 결과가 정확히 일치. 이 검사는 독립적으로 진단된 phi context 오류를 섞지 않으려고 **phi0**으로 격리했고 두 capacity-drop gate는 활성화했다.
- two-branch off 4substep 결과가 설치 전/후 정확히 동일.
- cfg 파라미터 누락·0·negative·jam 이상·NaN·Inf 기각.
- 후보/셀 interleave 시 legacy context 무관성.
- 반복 zone/segment/FD installer 후 올바른 cell 정보 보존과 pickle/JSON 동작.
- Windows `spawn` 새 프로세스에서 worker 순서로 installer를 호출해 부모와 E9 speed/critical 정확히 일치.

반복 installer 검사가 한 번 실패하며 추가 함정을 드러냈다. 기존 segment wrapper가 안쪽 zone wrapper의 marker를 가려, zone installer를 다시 부르면 원래 cell9를 head5로 먼저 바꾼 다음 FD token을 만들 수 있었다. 신규 wrapper는 두 기존 installer marker를 보존하여 이 이중 wrapping을 막는다. 실런에 연결할 때 설치 순서는 위 규약을 따라야 한다.

이 검사는 모형/코드 일관성 검증이다. 가격 전체 벡터 또는 VISSIM TTT 개선을 입증한 결과는 아니다. 원시 관측 기반 FD 재적합·보류검증은 여전히 별도 작업이다.
