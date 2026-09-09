# -*- coding: utf-8 -*-
"""매핑 생성기를 세그먼트 수에 대해 자유롭게 만든다 — A단계 (2026-09-07).

무엇이 막고 있었나. `build_segments` 가 **설치 매니페스트를 `model_segment_index` 로 묶어** 세그먼트를
만들었다. 그래서 (a) 세그먼트 수가 매니페스트에 매여 N 을 못 바꾸고, (b) Ver2 처럼 망을 분할해 VISSIM 이
DSD 를 다른 링크로 옮긴 뒤에는 매니페스트의 link/pos 가 낡아 엉뚱한 셀에 붙는다. 실제로 지금 매핑의
FW_W S3~S7 은 "링크 26, pos 4041~9430 m" 를 주장하는데 **Ver2 링크 26 은 3818.55 m 뿐**이고, 그 DSD 들은
망에서 이미 링크 120 pos 222~5611 로 옮겨져 있다(생성기는 WARN 만 찍고 지나간다).

이 패치 뒤로 매니페스트는 **어느 DSD 가 설치본인지(번호 집합)만** 제공하고, 위치는 언제나 망에서 읽는다.
세그먼트는 체인 기하에서 N 개를 만들고 DSD 를 사슬 위치로 붙인다. DSD 가 없는 셀이 생기는 것은 정상이다 —
`segment_vsl` 이 `{link}__seg{i}` → `{link}` 로 폴백하고 살아있는 팔(wu-link)은 링크당 VSL 1개다.

세그먼트 수: 환경변수 `RW_FREEWAY_SEGMENTS_PER_LINK` (없으면 8, 비트 동일).
사용: python apply_gen_nseg_patch_20260907.py <generator_path>
"""
import io
import sys

NEW_BUILD = '''def build_segments(
    manifest_rows: list[dict[str, str]],
    network: dict[str, Any],
    geometry: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """세그먼트 = 체인 기하가 정본(N 개). DSD 는 **망의 실제 위치**로 붙인다.

    2026-09-07 재작성. 매니페스트는 이제 '어느 DSD 가 설치본인가'(번호 집합)만 제공한다 — 위치는 망에서
    읽는다. 종전처럼 매니페스트의 model_segment_index 로 묶으면 세그먼트 수가 매니페스트에 매이고,
    망 분할로 DSD 가 다른 링크로 옮겨간 뒤에는 낡은 link/pos 가 엉뚱한 셀에 붙는다.
    DSD 가 하나도 없는 셀이 생기는 것은 정상이다(VSL 은 링크 키로 폴백한다).
    """
    installed_dsd_nos: set[int] = set()
    default_speed = 120.0
    for row in manifest_rows:
        if row.get("category") != "segment_start_vsl":
            continue
        no = int(clean_float(row.get("no"), 0.0))
        if no:
            installed_dsd_nos.add(no)
        default_speed = clean_float(row.get("default_speed_kph"), default_speed)

    link_index = chain_link_index(geometry)
    segments: list[dict[str, Any]] = []
    for model_link in sorted(geometry):
        geom = geometry[model_link]
        bounds = geom["segment_bounds_m"]
        offsets = list(geom["chain_offsets_m"])
        members = list(geom["chain_links"])
        lanes_profile = geom.get("segment_lanes") or []
        for idx in range(len(bounds) - 1):
            start_m, end_m = float(bounds[idx]), float(bounds[idx + 1])
            mid = 0.5 * (start_m + end_m)
            member_i = max(j for j in range(len(offsets)) if float(offsets[j]) <= mid)
            segments.append(
                {
                    "segment_id": "RW_%s_S%d" % (model_link, idx),
                    "model_link": model_link,
                    "model_segment_index": idx,
                    "link": int(members[member_i]),
                    "chain_links": [int(v) for v in members],
                    "direction": str(geom.get("direction", "")),
                    "segment_start_m": round3(start_m),
                    "segment_end_m": round3(end_m),
                    "dsd_chain_pos_m": None,
                    "dsd_snap_offset_m": None,
                    "length_km": round((end_m - start_m) / 1000.0, 6),
                    "lanes": int(lanes_profile[idx]) if idx < len(lanes_profile) else int(geom["lanes"]),
                    "dsd_by_lane": {},
                    "extra_dsd_controls": [],
                    "dsds": [],
                    "default_speed_kph": default_speed,
                }
            )

    lookup = {(s["model_link"], s["model_segment_index"]): s for s in segments}
    for dsd in network["dsds"]:
        dsd_no = dsd.get("no")
        if not isinstance(dsd_no, int):
            continue
        physical_link = dsd.get("link")
        model_link, chain_pos = chain_position(link_index, physical_link, float(dsd.get("pos_m", 0.0)))
        if model_link is None or chain_pos is None:
            continue
        idx = segment_index(chain_pos, geometry[model_link]["segment_bounds_m"])
        segment = lookup.get((model_link, idx))
        if not segment:
            continue
        lane = dsd.get("lane")
        if dsd_no in installed_dsd_nos:
            rec = {
                "dsd_no": dsd_no,
                "lane": lane,
                "pos_m": round3(float(dsd.get("pos_m", 0.0))),
                "source": "installed_real_world_segment_start",
                "name": dsd.get("name", ""),
            }
            segment["dsd_by_lane"][str(lane)] = dict(rec)
            segment["dsds"].append(dict(rec))
        else:
            rec = {
                "dsd_no": dsd_no,
                "lane": lane,
                "link": physical_link,
                "pos_m": round3(float(dsd.get("pos_m", 0.0))),
                "chain_pos_m": round3(chain_pos),
                "source": "existing_freeway_mainline_dsd",
                "name": dsd.get("name", ""),
            }
            segment["extra_dsd_controls"].append(dict(rec))
            segment["dsds"].append(dict(rec))

    for segment in segments:
        installed = [d for d in segment["dsds"] if d.get("source") == "installed_real_world_segment_start"]
        if not installed:
            continue
        _, chain_pos = chain_position(link_index, segment["link"], float(installed[0]["pos_m"]))
        if chain_pos is None:
            continue
        segment["dsd_chain_pos_m"] = round3(chain_pos)
        segment["dsd_snap_offset_m"] = round3(chain_pos - float(segment["segment_start_m"]))

    n_with = sum(1 for s in segments if s["dsd_by_lane"])
    print(
        "NOTE=SEGMENTS_FROM_GEOMETRY count=%d with_installed_dsd=%d without=%d "
        "(DSD 없는 셀은 VSL 이 링크 키로 폴백한다)" % (len(segments), n_with, len(segments) - n_with)
    )
    return segments
'''


def main():
    path = sys.argv[1]
    s = io.open(path, encoding="utf-8").read()
    if "NOTE=SEGMENTS_FROM_GEOMETRY" in s:
        print("already patched:", path)
        return

    old_const = "FREEWAY_SEGMENTS_PER_LINK = 8"
    new_const = ('# 2026-09-07: 세그먼트 수는 env 로 연다(없으면 8, 비트 동일). N=21 이 "셀당 on<=1 off<=1" 을\n'
                 '# 만족하는 가장 성긴 균등 분할이다(N=8~20 은 전부 위반, 전수 탐색 2026-09-07).\n'
                 'FREEWAY_SEGMENTS_PER_LINK = int(os.environ.get("RW_FREEWAY_SEGMENTS_PER_LINK", "8"))')
    assert s.count(old_const) == 1, ("const", s.count(old_const))
    s = s.replace(old_const, new_const)

    head = "def build_segments(\n    manifest_rows: list[dict[str, str]],\n    network: dict[str, Any],\n    geometry: dict[str, dict[str, Any]],\n) -> list[dict[str, Any]]:"
    assert s.count(head) == 1, ("build_segments head", s.count(head))
    start = s.index(head)
    tail_anchor = "\n\ndef "
    end = s.index(tail_anchor, start + len(head))
    s = s[:start] + NEW_BUILD.rstrip("\n") + s[end:]

    io.open(path, "w", encoding="utf-8", newline="").write(s)
    print("gen nseg patch applied to", path)


if __name__ == "__main__":
    main()
