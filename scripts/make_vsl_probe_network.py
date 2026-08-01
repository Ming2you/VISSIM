# VSL 채널 실집행 검증용 프로브 네트워크와 채널 설정 CSV를 만드는 생성기.
"""16개 VSL 채널에 서로 구분되는 '지문' 희망속도 분포를 심는다.

왜 새 분포가 필요한가.
  네트워크 기본 희망속도 분포(25/30/40/70/100/120/130 ...)는 지지집합이 5~170 km/h를
  연속으로 덮는다. 기존 분포를 채널 지문으로 쓰면 "이 차량이 어느 DSD를 통과했는가"를
  DesSpeed 값만으로 되짚을 수 없다. 그래서 폭 0.01 km/h짜리 초협대역 분포 16개를
  9001~9016 번으로 새로 넣고, 각 채널에 하나씩 배정한다. 값이 정수가 아니고(.37)
  폭이 0.01이라 기본 분포에서 우연히 같은 값이 뽑힐 확률은 무시할 수 있다.

기하/DSD 위치/세그먼트 격자는 손대지 않는다. 추가되는 것은 분포 정의 16개뿐이고
DSD의 vehClassDesSpeedDistr 배정은 런타임에 프로브 vbs가 COM으로 바꾼다.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# 지문 대역. 채널 k -> 88.37 + 2k (km/h), 폭 0.01. FW_E는 짝수 k, FW_W는 홀수 k.
BASE_SPEED_KMH = 88.37
SPEED_STEP_KMH = 2.0
BAND_WIDTH_KMH = 0.01
DISTR_NO_BASE = 9001


def build_channels(mapping: dict, include_extra: bool) -> list[dict]:
    """include_extra=True 가 실제 운영 배선이다.

    어댑터(evaluation/controllers/vissim_stackelberg_adapter.py 의
    _segment_dsd_controls)는 segments[*].dsd_by_lane 뿐 아니라
    segments[*].extra_dsd_controls 에 실린 기존 네트워크 DSD(36~42)에도 같은 VSL
    값을 실어 보낸다. 그래서 운영 채널 수는 64가 아니라 71개 DSD다. False로 두면
    RW_VSL_* 64개만 구동하는 변형이 되고, 그 차이가 곧 레거시 DSD의 기여분이다.
    """
    channels = []
    for seg in mapping["segments"]:
        link_model = seg["model_link"]
        idx = int(seg["model_segment_index"])
        k = 2 * idx + (0 if link_model == "FW_E" else 1)
        dsd = seg["dsd_by_lane"]
        nos = [dsd[key]["dsd_no"] for key in sorted(dsd, key=int)]
        extras = seg.get("extra_dsd_controls", []) if include_extra else []
        nos.extend(int(e["dsd_no"]) for e in extras)
        channels.append(
            {
                "channel_index": k,
                "segment_id": seg["segment_id"],
                "model_link": link_model,
                "segment_index": idx,
                "segment_start_m": float(seg["segment_start_m"]),
                "segment_end_m": float(seg["segment_end_m"]),
                "host_link": int(seg["link"]),
                "dsd_pos_m": float(dsd["1"]["pos_m"]),
                "dsd_chain_pos_m": float(seg["dsd_chain_pos_m"]),
                "dsd_snap_offset_m": float(seg["dsd_snap_offset_m"]),
                "dsd_nos": ";".join(str(n) for n in nos),
                "distr_no": DISTR_NO_BASE + k,
                "distr_speed_kmh": round(BASE_SPEED_KMH + SPEED_STEP_KMH * k, 3),
            }
        )
    channels.sort(key=lambda c: c["channel_index"])
    return channels


def inject_distributions(src_inpx: Path, out_inpx: Path, channels: list[dict]) -> list[int]:
    tree = ET.parse(src_inpx)
    root = tree.getroot()
    container = root.find(".//desSpeedDistributions")
    if container is None:
        raise SystemExit("ERROR: <desSpeedDistributions> not found in " + str(src_inpx))
    existing = {int(e.get("no")) for e in container.findall("desSpeedDistribution")}
    added = []
    for ch in channels:
        no = int(ch["distr_no"])
        if no in existing:
            raise SystemExit(f"ERROR: desSpeedDistribution no={no} already exists")
        lo = float(ch["distr_speed_kmh"])
        hi = lo + BAND_WIDTH_KMH
        node = ET.SubElement(container, "desSpeedDistribution")
        node.set("name", f"VSLPROBE_CH{ch['channel_index']:02d}_{ch['segment_id']}")
        node.set("no", str(no))
        pts = ET.SubElement(node, "speedDistrDatPts")
        for fx, x in ((0, lo), (1, hi)):
            p = ET.SubElement(pts, "speedDistributionDataPoint")
            p.set("fx", str(fx))
            p.set("x", f"{x:.4f}")
        added.append(no)
    out_inpx.parent.mkdir(parents=True, exist_ok=True)
    tree.write(out_inpx, encoding="utf-8", xml_declaration=True)
    return added


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mapping", default=str(REPO / "evaluation/real_world_modi_control/control_mapping.json"))
    ap.add_argument("--src-inpx", default=str(REPO / "network/real_world_gaepo_modi/modi_eval_rw_control.inpx"))
    ap.add_argument("--src-layx", default=str(REPO / "network/real_world_gaepo_modi/modi_eval_rw_control.layx"))
    ap.add_argument("--out-inpx", default=str(REPO / "network/real_world_gaepo_modi/modi_eval_rw_control_vslprobe.inpx"))
    ap.add_argument("--run-dir", default=str(REPO / "evaluation/runs/vsl_channel_com_smoke_20260801"))
    ap.add_argument("--rw-dsd-only", action="store_true",
                    help="RW_VSL_* 64개만 구동한다(운영 배선이 아니라 레거시 DSD 기여분 분리용).")
    ap.add_argument("--skip-net", action="store_true", help="프로브 네트워크 재생성을 건너뛴다.")
    args = ap.parse_args()

    mapping = json.loads(Path(args.mapping).read_text(encoding="utf-8"))
    channels = build_channels(mapping, include_extra=not args.rw_dsd_only)
    if len(channels) != 16:
        raise SystemExit(f"ERROR: expected 16 segments, got {len(channels)}")

    out_inpx = Path(args.out_inpx)
    if args.skip_net:
        added = []
    else:
        added = inject_distributions(Path(args.src_inpx), out_inpx, channels)
        layx = Path(args.src_layx)
        if layx.exists():
            shutil.copy2(layx, out_inpx.with_suffix(".layx"))

    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    ch_csv = run_dir / "vsl_probe_channels.csv"
    with ch_csv.open("w", newline="", encoding="ascii") as fh:
        w = csv.DictWriter(fh, fieldnames=list(channels[0].keys()))
        w.writeheader()
        for ch in channels:
            w.writerow(ch)

    chain_csv = run_dir / "vsl_probe_chain.csv"
    with chain_csv.open("w", newline="", encoding="ascii") as fh:
        w = csv.writer(fh)
        w.writerow(["model_link", "chain_links", "chain_offsets_m", "segment_bounds_m", "lanes"])
        for key, info in mapping["freeway_model_links"].items():
            w.writerow(
                [
                    key,
                    ";".join(str(x) for x in info["chain_links"]),
                    ";".join(f"{x:.6f}" for x in info["chain_offsets_m"]),
                    ";".join(f"{x:.6f}" for x in info["segment_bounds_m"]),
                    int(info["lanes"]),
                ]
            )

    print("PROBE_NET=" + str(out_inpx))
    print("ADDED_DISTRIBUTIONS=" + ",".join(str(n) for n in added))
    print("CHANNELS_CSV=" + str(ch_csv))
    print("CHAIN_CSV=" + str(chain_csv))
    for ch in channels:
        print(
            "CHANNEL k=%02d %s link=%s seg=%d dsd=[%s] host_link=%s pos=%.3f distr=%d speed=%.2f"
            % (
                ch["channel_index"],
                ch["segment_id"],
                ch["model_link"],
                ch["segment_index"],
                ch["dsd_nos"],
                ch["host_link"],
                ch["dsd_pos_m"],
                ch["distr_no"],
                ch["distr_speed_kmh"],
            )
        )


if __name__ == "__main__":
    main()
