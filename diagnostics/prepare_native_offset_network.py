"""Prepare isolated native-program offset arms without rewriting source XML.

The output INPX must be a new sibling of the source so every untouched relative
asset retains its meaning. Only selected supplyFile2 values change in that copy;
only program offset attributes change in the new SIG copies. Treatment starts
at simulation time zero, unlike a COM arm applied at ControlStartSec=900.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from plant.src.vissim_strict.signal_program import parse_sig_programs

SC_TAG = re.compile(rb"<signalController\b[^>]*>")
PROG_TAG = re.compile(rb"<prog\b[^>]*>")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise FileExistsError(f"refusing to replace a different prepared artifact: {path}")
    else:
        path.write_bytes(data)


def shift_sig_bytes(payload, shift_sec, *, zero=False):
    if not math.isfinite(shift_sec) or abs(shift_sec * 1000 - round(shift_sec * 1000)) > 1e-7:
        raise ValueError("native offset shift must be finite integer milliseconds")
    rows = []

    def replace(match):
        tag = match.group(0)
        attrs = ET.fromstring(tag[:-1] + b" />").attrib
        cycle, before = int(attrs["cycletime"]), int(attrs["offset"])
        after = 0 if zero else (before + round(shift_sec * 1000)) % cycle
        updated = re.sub(rb'\boffset="[0-9]+"', f'offset="{after}"'.encode(), tag, count=1)
        if not re.search(rb'\boffset="[0-9]+"', tag):
            raise ValueError("program has no offset attribute")
        rows.append({"prog_no": int(attrs["id"]), "cycle_sec": cycle / 1000,
                     "before_offset_sec": before / 1000, "after_offset_sec": after / 1000})
        return updated

    result = PROG_TAG.sub(replace, payload)
    if not rows:
        raise ValueError("no native programs to transform")
    # Ignoring the sole allowed attribute must recover byte identity.
    strip = lambda data: re.sub(rb'\boffset="[0-9]+"', b'offset="_"', data)
    if strip(result) != strip(payload):
        raise AssertionError("SIG transformation changed more than offsets")
    return result, rows


def prepare(network, output_network, recipe):
    network, output_network = Path(network).resolve(), Path(output_network).resolve()
    if output_network == network or output_network.parent != network.parent:
        raise ValueError("output must be a new sibling INPX; source is never overwritten")
    arm = recipe["name"]
    if re.fullmatch(r"[a-z0-9_]+", arm) is None:
        raise ValueError("arm name must use lowercase letters, numbers and underscores")
    wanted = {str(int(key.removeprefix("SC"))): float(value)
              for key, value in recipe["relative_native_offset_sec"].items()}
    if not wanted:
        raise ValueError("select at least one controller")
    original = network.read_bytes()
    hashes, rows, seen = {network: sha(original)}, [], set()

    def replace(match):
        tag = match.group(0)
        attrs = ET.fromstring(tag[:-1] + b" />").attrib
        sc = attrs["no"]
        if sc not in wanted:
            return tag
        if attrs.get("active", "true").lower() != "true":
            raise ValueError(f"selected native controller is inactive: {sc}")
        raw = attrs["supplyFile2"]
        relative = raw[6:] if raw.lower().startswith("#data#") else raw
        source = (network.parent / relative).resolve()
        payload = source.read_bytes()
        hashes[source] = sha(payload)
        shifted, programs = shift_sig_bytes(payload, wanted[sc], zero=recipe.get("zero_selected", False))
        target = network.parent / "_diagnostic_native_offsets" / arm / f"SC{sc}.sig"
        write_new(target, shifted)
        old_programs, new_programs = parse_sig_programs(source), parse_sig_programs(target)
        checks = 0
        for item in programs:
            before, after = old_programs[item["prog_no"]], new_programs[item["prog_no"]]
            if before.sg_timelines != after.sg_timelines:
                raise AssertionError("native cycle, SG windows or colors changed")
            delta = after.program_offset_sec - before.program_offset_sec
            for sec in range(int(math.ceil(2 * before.cycle_length_sec))):
                if after.state_at(sec) != before.state_at(sec - delta):
                    raise AssertionError("native SG clock shift mismatch")
                checks += len(before.sg_timelines)
        supply = ("#data#" + str(target.relative_to(network.parent))).encode("utf-8")
        updated = re.sub(rb'(\bsupplyFile2=")[^"]*(")', lambda m: m[1] + supply + m[2], tag, count=1)
        rows.append({"sc": int(sc), "source_sig": str(source), "source_sha256": sha(payload),
                     "output_sig": str(target), "output_sha256": sha(shifted),
                     "programs": programs, "native_clock_state_checks": checks})
        seen.add(sc)
        return updated

    result = SC_TAG.sub(replace, original)
    if seen != set(wanted):
        raise ValueError(f"selected controllers missing: {sorted(set(wanted) - seen)}")
    strip = lambda data: re.sub(rb'\bsupplyFile2="[^"]*"', b'supplyFile2="_"', data)
    if strip(result) != strip(original):
        raise AssertionError("INPX transformation changed more than program references")
    write_new(output_network, result)
    if any(sha(path.read_bytes()) != digest for path, digest in hashes.items()):
        raise AssertionError("a source file changed during preparation")
    return {"status": "PREPARED_OFFLINE", "treatment_start_sec": 0,
            "source_network": str(network), "source_sha256": sha(original),
            "output_network": str(output_network), "output_sha256": sha(result),
            "native_unchanged_except_selected_offsets": True, "recipe": recipe, "controllers": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe", type=Path)
    parser.add_argument("--network", type=Path, default=ROOT / "network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx")
    parser.add_argument("--out-network", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    report = prepare(args.network, args.out_network, json.loads(args.recipe.read_text(encoding="utf-8")))
    write_new(args.manifest, (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"status": report["status"], "controllers": len(report["controllers"]),
                      "source_unchanged": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
