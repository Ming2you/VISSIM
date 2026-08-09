# PTV Vissim eval 산출물(.rsr 차량 기록, Queue/Travel Time .att 표)을 레코드로 읽는 파서

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple, Sequence


# .rsr 는 고정 열 구성이라 머리글을 그대로 대조한다.
RSR_COLUMNS = ("Time", "No.", "Veh", "VehType", "Trav.", "Delay.", "Dist")

QUEUE_COLUMNS = (
    "SIMRUN",
    "TIMEINT",
    "QUEUECOUNTER",
    "QLEN",
    "QLENMAX",
    "QSTOPS",
)

TRAVEL_TIME_COLUMNS = (
    "SIMRUN",
    "TIMEINT",
    "VEHICLETRAVELTIMEMEASUREMENT",
    "VEHS(ALL)",
    "TRAVTM(ALL)",
    "DISTTRAV(ALL)",
)


class RsrRecord(NamedTuple):
    time_sec: float
    measurement_no: int
    veh_no: int
    veh_type: int
    trav_sec: float
    delay_sec: float
    dist_m: float


class QueueRecord(NamedTuple):
    simrun: int
    timeint: str
    queue_counter: int
    qlen_m: float
    qlenmax_m: float
    qstops: int


class TravelTimeRecord(NamedTuple):
    simrun: int
    timeint: str
    measurement: int
    vehs: int
    travtm_s: float | None
    dist_m: float | None


def _read_lines(path: Path | str) -> list[str]:
    """헤더에 CP949 한글 경로가 박혀 있어 UTF-8 로는 못 읽는 파일이 있다.

    데이터 행은 항상 ASCII 이므로 헤더 디코딩이 실패해도 파싱은 계속되어야 한다.
    """
    raw = Path(path).read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("cp949", errors="replace")
    return text.splitlines()


def _cells(line: str) -> list[str]:
    return [field.strip() for field in line.split(";")]


def _drop_trailing_blank(cells: list[str]) -> list[str]:
    # .rsr 은 모든 행이 세미콜론으로 끝나서 빈 꼬리 열이 하나 생긴다.
    return cells[:-1] if cells and cells[-1] == "" else cells


def _optional_float(value: str) -> float | None:
    # 통과 차량이 0 대인 측정은 TravTm/DistTrav 셀이 비어 있다.
    return float(value) if value else None


def parse_rsr(path: Path | str) -> list[RsrRecord]:
    lines = _read_lines(path)

    header = None
    for index, line in enumerate(lines):
        if tuple(_drop_trailing_blank(_cells(line))) == RSR_COLUMNS:
            header = index
            break
    if header is None:
        raise ValueError(f"{path}: .rsr 열 머리글 {';'.join(RSR_COLUMNS)} 을 찾지 못했다")

    records = []
    for number, line in enumerate(lines[header + 1 :], start=header + 2):
        if not line.strip():
            continue
        cells = _drop_trailing_blank(_cells(line))
        if len(cells) != len(RSR_COLUMNS):
            raise ValueError(
                f"{path}:{number}: 열이 {len(RSR_COLUMNS)}개여야 하는데 "
                f"{len(cells)}개다 -> {line!r}"
            )
        records.append(
            RsrRecord(
                time_sec=float(cells[0]),
                measurement_no=int(cells[1]),
                veh_no=int(cells[2]),
                veh_type=int(cells[3]),
                trav_sec=float(cells[4]),
                delay_sec=float(cells[5]),
                dist_m=float(cells[6]),
            )
        )
    return records


def _read_att_table(
    path: Path | str, required: Sequence[str]
) -> tuple[dict[str, int], list[list[str]]]:
    """`$TABLE:COL;COL;...` 머리글을 찾아 열 이름 -> 위치 사상과 데이터 행을 돌려준다."""
    lines = _read_lines(path)

    header = None
    for index, line in enumerate(lines):
        if line.startswith("$") and ":" in line:
            header = index
            break
    if header is None:
        raise ValueError(f"{path}: .att 표 머리글($TABLE:COL;...) 을 찾지 못했다")

    names = [name.strip().upper() for name in lines[header].split(":", 1)[1].split(";")]
    missing = [name for name in required if name not in names]
    if missing:
        raise ValueError(f"{path}: 필요한 열 {missing} 이 없다. 실제 열 {names}")
    column = {name: names.index(name) for name in required}

    rows = []
    for number, line in enumerate(lines[header + 1 :], start=header + 2):
        if not line.strip():
            continue
        cells = _cells(line)
        if len(cells) != len(names):
            raise ValueError(
                f"{path}:{number}: 열이 {len(names)}개여야 하는데 "
                f"{len(cells)}개다 -> {line!r}"
            )
        rows.append(cells)
    return column, rows


def parse_queue_att(path: Path | str) -> list[QueueRecord]:
    column, rows = _read_att_table(path, QUEUE_COLUMNS)
    return [
        QueueRecord(
            simrun=int(cells[column["SIMRUN"]]),
            timeint=cells[column["TIMEINT"]],
            queue_counter=int(cells[column["QUEUECOUNTER"]]),
            qlen_m=float(cells[column["QLEN"]]),
            qlenmax_m=float(cells[column["QLENMAX"]]),
            qstops=int(cells[column["QSTOPS"]]),
        )
        for cells in rows
    ]


def parse_travel_time_att(path: Path | str) -> list[TravelTimeRecord]:
    column, rows = _read_att_table(path, TRAVEL_TIME_COLUMNS)
    return [
        TravelTimeRecord(
            simrun=int(cells[column["SIMRUN"]]),
            timeint=cells[column["TIMEINT"]],
            measurement=int(cells[column["VEHICLETRAVELTIMEMEASUREMENT"]]),
            vehs=int(cells[column["VEHS(ALL)"]]),
            travtm_s=_optional_float(cells[column["TRAVTM(ALL)"]]),
            dist_m=_optional_float(cells[column["DISTTRAV(ALL)"]]),
        )
        for cells in rows
    ]
