# k92 — K9-2 묶음 1: SC109 서측 직진 용량(W)과 좌회전 헤드 하한 씨앗(H-b)

근거: 보충 24 고정판 `K8_PREDECLARATION_AMENDMENT_24.md`(sha256 `d46db6dc3959b19525f0fce77ead5432682e3de0ef8060cdc3da09661559aadc`),
결정 기록 D-K9-30…38. 커밋 K9-2-1(W), K9-2-2(H-b), K9-2-3(팔·문서). 하네스는 K9-2-0(`../k8_gates/sa/`).

줄임말: W = SC109 서측 직진 용량 키, H-b = (173, p4) 좌회전 헤드 하한의 씨앗(아래 끝), CFG = `config_n31_v2.json`,
SAF-K91 = `config_n31_v2_stopline_observed_full_k91.json`, U4 = 헤드 포화 측정 표(sha `22384c00…`), R-obs = v3c3 무제어
결정 런(`sdmpc31_v3c3_nc_s{31,43,47}`).

## 두 키

| 키 | 하는 일 | 증거 파일(이 폴더) | 값 |
|---|---|---|---|
| `urban.sc109w_through_saturation` | movement `SC109_W_SC108_to_E` 한 키의 용량을 증거 값으로 바꿈(K9-1 W1 훅 바로 뒤, `runtime_setup.install_sc109w_through_saturation`). 메타 `k92_w` | `sc109w_through_saturation_v3b_u4_20261016.json` (sha256 `b4b7294d…71712`) | 5209.8 veh/h-녹색(3차로; U4 `173\|p3` F2 1736.6 × 3을 0.1로 반올림, repr `5209.8`) |
| `urban.capacity.head_floor_seed` | (173, p4) 좌회전 헤드 하한 = max(지금 규칙 값, 씨앗). 학습은 그대로(`signal_head_observation.configure_head_floor_seed` + `install`의 두 자리). 메타 `k92_hb`, `k92_hb_seed_binding` | `head_floor_seed_v3c3_robs_20261016.json` (sha256 `b9fa1d01…f20ee`) | 1045.1612903225805(R-obs 세 런 두 창 지지값의 중앙값, repr 고정) |

- 키 값은 `{"evidence": <저장소 상대 경로>, "evidence_sha256": <파일 바이트 sha256>}` 꼴입니다. 경로·sha·schema가 다르면 ValueError입니다.
- 키가 없으면 런타임은 b9734abe와 같은 길입니다.
- 묶기(D-K9-31): 씨앗 키만 있고 W 키가 없으면 런타임 ValueError, 하네스는 포착·잡 전에 거부합니다.

## 팔 파일

- `../config_n31_v2_k92b1.json` = CFG + 두 키(다른 곳 0). `python -B diagnostics/sdmpc_n31_20260924/make_config_n31.py --k92b1 [--check]`가 커밋된 CFG 바이트 위에 만듭니다.
- SAF-K91 계열 팔은 `python -B diagnostics/sdmpc_n31_20260924/k8_gates/sa/sa_arms.py --k92b1 --out <폴더>`가 `<폴더>/sa/tuning/config_n31_v2_stopline_observed_full_k91_k92b1.json`으로 씁니다.
- 배포 튜닝 CFG에는 키를 넣지 않았습니다. 승격은 V-A(폐루프) 사용자 결정 때 따로 정합니다(보충 24 §2.0-5).

## 증거 다시 만들기·점검

```
python -B diagnostics/sdmpc_n31_20260924/k92/build_k92_evidence.py w --check
python -B diagnostics/sdmpc_n31_20260924/k92/build_k92_evidence.py hb --check --root <git archive b9734abe 트리>
```

- `--check`는 다시 계산한 `values`가 커밋된 증거의 `values`와 정규 JSON으로 같은지만 봅니다.
- `hb`는 규칙 코드 SHO 바이트(sha `d9bd5392…`, b9734abe)를 고정해 둡니다. K9-2-2 뒤 작업 트리의 SHO는 바뀐 파일이라, 규칙 코드를 담은 트리를 `--root`로 줍니다.
- `inputs/u4_row_173_p3_v3b.json`은 U4 표 `groups[27]` 행을 그대로 옮긴 입력입니다.

## 알려진 한계 (보충 24 §2.6 요약)

1. W 값은 v3b 무제어(U4)에서 쟀습니다. v3c3에서는 이 머리가 비포화라 다시 잴 수 없습니다.
2. 5209.8은 몫 가르기 결과를 본 뒤 고른 값이고(D-K9-34), 몫 가르기(5700.6)에서 시험하지 않았습니다.
3. 씨앗 1045.16은 몫 가르기에서 시험하지 않은 값입니다. 씨앗을 만든 R-obs 런에 판정 주 표본(v3c3-s47)이 들어 있어 F-3은 비블라인드 안전 문턱입니다.
4. 씨앗이 있으면 연쇄·폐루프의 T=150 결정에서 `head_observation_prior_discarded`가 1.0이 됩니다(계산 영향 0, 계수만 다름).
5. 서측 직진을 Ω 밖 `SC109_E_out`으로 더 내보내도 목적함수는 그 대기를 세지 않습니다(D-K9-32).
