# Urban Follower ID ↔ VISSIM SC 매핑 오류 정정 (2026-08-01)

## 요약

분산 urban follower 구성(`19sc`, `15core`)이 **Urban Follower ID를 VISSIM SC 번호로 착각**한 채
생성돼 있었다. 두 체계는 완전히 다르다. 그 결과 19sc는 19개 중 14개, 15core는 15개 중 8개가
엉뚱한 신호기를 제어하고 있었다.

## 근본 원인

`scripts/generate_real_world_distributed_players.py`의 구 정의에 자백이 남아 있다.

```python
# Manual interpretation of the user's 2026-07-28 marked-up 15-player core.
CORE15_SC_NUMBERS = [1, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 107, 108]
```

`primary19`도 같은 착각으로 `1 <= no <= 19`(SC 번호 1~19)를 그대로 썼다.

사용자가 표시한 번호는 **Urban Follower ID**였고, 실제 VISSIM SC 번호는 별개다.
추적되지 않는 자료(마크업 이미지)를 사람이 눈으로 해석해 코드에 상수로 박은 것이 원인이다.

## 정확한 매핑 (Urban-Follower.xlsx 기계 추출)

| UF | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **SC** | 1004 | 1005 | 107 | 108 | 109 | 1003 | 105 | 1 | 11 | 12 | 106 | 1001 | 1002 | 101 | 5 | 6 | 104 | 102 | 103 |

### 독립 검증

xlsx의 SC별 신호헤드 수와 네트워크 인벤토리(`modi.inpx` 파싱)의 `signal_head_count`를 대조 —
**19개 중 16개 정확히 일치**. 불일치 3건은 xlsx가 부분집합인 경우다.

| UF | SC | xlsx 헤드 | 인벤토리 헤드 | 해석 |
|---|---|---|---|---|
| 4 | 108 | 14 | 16 | 2개 제외 |
| 15 | 5 | 16 | 31 | 도곡역, SG 24개 대형 교차로 — 절반 이하만 선택 |
| 18 | 102 | 16 | 23 | 한티역, SG 16개 — 7개 제외 |

부분집합은 오류가 아니라 "해당 팔로워가 제어할 헤드만 고른" 것으로 보인다. UF→SC는 전부
1:1이며(추출기가 1:N을 오류로 차단), 이 3건은 pending dual-ring 투영 작업과 직결된다.

## 대조표

**15core** (= UF 1~16 중 11 제외)

| | SC 집합 |
|---|---|
| 정정 후 | `1, 5, 6, 11, 12, 101, 105, 107, 108, 109, 1001, 1002, 1003, 1004, 1005` |
| 구 구현 | `1, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 107, 108` |

- 우연히 맞은 것 **7개**: `1, 5, 6, 11, 12, 107, 108`
- 틀리게 제어 중 **8개**: `4, 7, 9, 10, 13, 14, 15, 16` (urban follower가 아닌 신호기)
- 누락 **8개**: `101, 105, 109, 1001, 1002, 1003, 1004, 1005`

**19sc** (= UF 1~19 전체)

| | SC 집합 |
|---|---|
| 정정 후 | `1, 5, 6, 11, 12, 101, 102, 103, 104, 105, 106, 107, 108, 109, 1001~1005` |
| 구 구현 | `SC1 ~ SC19` |

- 우연히 맞은 것 **5개**: `1, 5, 6, 11, 12`

## 변경 내용

| 파일 | 내용 |
|---|---|
| `scripts/extract_urban_follower_map.py` | 신규. Urban-Follower.xlsx → 추적 CSV 기계 추출 |
| `evaluation/real_world_modi_inventory/urban_follower_sc_map.csv` | 신규. UF→SC 요약(19행) |
| `evaluation/real_world_modi_inventory/urban_follower_signal_map.csv` | 신규. UF→SC/SG/헤드 상세(275행) |
| `scripts/generate_real_world_distributed_players.py` | `CORE15_SC_NUMBERS` 제거 → `CORE15_URBAN_FOLLOWER_IDS`(UF ID) + CSV 조회. `primary19`도 매핑 기반으로 정정 |

상세 CSV는 `outputs/real_world_distributed_signal_todo_20260731.md`가 다음 단계로 요구한
"사용자 검증 player↔SC/SG 매핑 표(player_id, sc_no, sg_no, signal_head_no)"에 해당한다.

### 재발 방지 가드 2종

같은 부류의 **침묵 실패**를 막기 위해 생성기가 이제 다음 경우에 중단한다.

1. 선택된 SC가 인벤토리에 없거나 비활성 → 인벤토리 재생성 명령 안내
2. 선택된 SC가 eval 네트워크에 없음 → movement가 빈 채로 생성되던 경로. 네트워크 재빌드 순서 안내

## 남은 작업 — eval 네트워크 재빌드

SC 1001~1005는 사용자가 수정한 `modi.inpx`에 새로 추가된 신호기다. 파이프라인 진행 상황:

| 단계 | 산출물 | 상태 |
|---|---|---|
| 1. 인벤토리 재생성 | `evaluation/real_world_modi_inventory/*` | ✅ 완료 (SC 1001~1005 반영 확인) |
| 2. sanitize | `modi_eval_sanitized.inpx` | ✅ 완료 (SC 1001~1005 전파 확인) |
| 3. freeway 제어층 설치 | `modi_eval_rw_control.inpx` | ⛔ **VISSIM COM 필요** |
| 4. base control mapping | `evaluation/real_world_modi_control/*` | 3번 대기 |
| 5. 분산 플레이어 재생성 | `*_distributed_{19sc,15core}_*` | 3~4번 대기 |

3번 명령 (PowerShell에서 실행, CodeMeter 서비스 확인 필요).

```bash
cscript //nologo scripts\install_real_world_freeway_controls.vbs network\real_world_gaepo_modi\modi_eval_sanitized.inpx network\real_world_gaepo_modi\modi_eval_sanitized.layx network\real_world_gaepo_modi\modi_eval_rw_control.inpx network\real_world_gaepo_modi\modi_eval_rw_control.layx evaluation\real_world_modi_control\freeway_control_manifest.csv
```

이후 4~5번.

```bash
python scripts/generate_real_world_control_mapping.py
python scripts/generate_real_world_distributed_players.py --selector primary19
python scripts/generate_real_world_distributed_players.py --selector core15
```

## 주의 사항

- **기존 15core/19sc 실행 결과는 전부 폐기 대상**이다. `evaluation/runs/rw_15core_sc108_4500_20260728` 등
  잘못된 SC 집합에서 나온 것이므로 증거로 쓸 수 없다.
  (`outputs/real_world_distributed_signal_todo_20260731.md`의 경고가 이 원인으로 확정됐다.)
- `Urban-Follower.xlsx`와 `Urban Follower ID.png`는 현재 **git 미추적**이다. 이제 파이프라인이 이
  매핑에 의존하므로 커밋을 권장한다 — 추적되지 않는 원본이 이 버그의 근본 원인이었다.
- `core15`의 `include_sc1_coupling = False`(SC1 approach-only) 설정은 그대로 두었다. SC1(=UF8)은
  정정 후에도 15core에 포함되지만, 이 결합 해제가 여전히 의도한 바인지는 확인이 필요하다.
- 이번 정정은 `pstack-flagship` 컨트롤러 이식(브랜치 `pstack-flagship-controller`)과 무관하다.
  해당 작업은 분산 경로를 명시적으로 제외했다.
