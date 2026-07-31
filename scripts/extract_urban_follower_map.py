# Urban-Follower.xlsx(사용자 검증 매핑표)를 추적 가능한 CSV로 기계 추출한다.
"""Urban Follower ID ↔ VISSIM SC/SG/Signal Head 매핑 추출기.

배경: 2026-07-28 분산 플레이어 생성기는 사용자가 표시한 15개 코어를 사람이 눈으로
해석해 SC 번호로 박아넣었고(`CORE15_SC_NUMBERS` 원본 주석 "Manual interpretation"),
그 결과 **Urban Follower ID를 VISSIM SC 번호로 착각**하는 버그가 생겼다.
UF ID 1~19와 SC 번호는 전혀 다른 체계다(예: UF1 → SC1004, UF8 → SC1).

이 스크립트는 사용자 검증 원본(Urban-Follower.xlsx)에서 매핑을 기계적으로 뽑아
버전 관리되는 CSV 두 개로 고정한다 — 이후 수동 해석이 끼어들 여지를 없앤다.

출력:
  - urban_follower_sc_map.csv    : UF ID → SC (1행 1팔로워, 요약)
  - urban_follower_signal_map.csv: UF ID → SC/SG/Signal Head (1행 1헤드, 상세)

상세본은 outputs/real_world_distributed_signal_todo_20260731.md가 요구한
"사용자 검증 player↔SC/SG 매핑 표(player_id, sc_no, sg_no, signal_head_no)"에 해당한다.

실행:
    python scripts/extract_urban_follower_map.py
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_XLSX = ROOT / "Urban-Follower.xlsx"
DEFAULT_OUT_DIR = ROOT / "evaluation/real_world_modi_inventory"

# 'No.' 열은 " 3: NBL" 형태 — 앞의 정수가 SG(phase) 번호, 뒤가 movement 이름.
SG_PATTERN = re.compile(r"^\s*(\d+)\s*:\s*(.+?)\s*$")


def parse_sg(raw: object) -> tuple[int, str]:
    text = "" if raw is None else str(raw)
    match = SG_PATTERN.match(text)
    if not match:
        raise ValueError(f"'No.' 열 형식을 해석할 수 없다: {text!r}")
    return int(match.group(1)), match.group(2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xlsx", default=str(DEFAULT_XLSX))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()

    try:
        import openpyxl
    except ImportError as exc:  # pragma: no cover - 환경 의존
        raise SystemExit("openpyxl이 필요하다: pip install openpyxl") from exc

    xlsx_path = Path(args.xlsx)
    if not xlsx_path.exists():
        raise SystemExit(f"매핑 원본을 찾을 수 없다: {xlsx_path}")

    workbook = openpyxl.load_workbook(xlsx_path, data_only=True)
    sheet = workbook.worksheets[0]
    rows = list(sheet.iter_rows(values_only=True))
    header = [str(c).strip() if c is not None else "" for c in rows[0]]
    expected = ["Urban Follower ID", "SC", "No.", "Signal Head"]
    if header[: len(expected)] != expected:
        raise SystemExit(f"예상과 다른 헤더: {header} (기대: {expected})")

    detail: list[dict[str, object]] = []
    uf_to_sc: "OrderedDict[int, set[int]]" = OrderedDict()
    for raw in rows[1:]:
        if raw[0] is None:
            continue
        uf_id, sc_no = int(raw[0]), int(raw[1])
        sg_no, movement = parse_sg(raw[2])
        detail.append({
            "urban_follower_id": uf_id,
            "sc_no": sc_no,
            "sg_no": sg_no,
            "movement": movement,
            "signal_head_no": int(raw[3]),
        })
        uf_to_sc.setdefault(uf_id, set()).add(sc_no)

    # UF 하나가 SC 여러 개에 걸치면 플레이어↔SC 1:1 전제가 깨진다 — 조용히 넘기지 않는다.
    ambiguous = {uf: sorted(scs) for uf, scs in uf_to_sc.items() if len(scs) != 1}
    if ambiguous:
        raise SystemExit(f"UF가 복수 SC에 매핑됐다(1:1 전제 위반): {ambiguous}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_path = out_dir / "urban_follower_sc_map.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["urban_follower_id", "sc_no", "sg_count", "signal_head_count"])
        for uf_id in sorted(uf_to_sc):
            heads = [d for d in detail if d["urban_follower_id"] == uf_id]
            writer.writerow([
                uf_id,
                sorted(uf_to_sc[uf_id])[0],
                len({d["sg_no"] for d in heads}),
                len(heads),
            ])

    detail_path = out_dir / "urban_follower_signal_map.csv"
    with detail_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["urban_follower_id", "sc_no", "sg_no", "movement", "signal_head_no"]
        )
        writer.writeheader()
        writer.writerows(sorted(detail, key=lambda d: (d["urban_follower_id"], d["sg_no"], d["signal_head_no"])))

    print(f"UF {len(uf_to_sc)}개, signal head {len(detail)}개")
    print(f"  {summary_path.relative_to(ROOT)}")
    print(f"  {detail_path.relative_to(ROOT)}")
    print("UF -> SC: " + ", ".join(f"{uf}->{sorted(uf_to_sc[uf])[0]}" for uf in sorted(uf_to_sc)))


if __name__ == "__main__":
    main()
