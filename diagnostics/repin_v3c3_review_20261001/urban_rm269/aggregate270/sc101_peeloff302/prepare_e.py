"""Preserve pre-forecast ENOSPC failure; direct repaired attempt output to E."""
import hashlib,json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=Path("E:/VISSIM_analysis/20261010_sc101_peeloff302/forecast2400")
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert not OUT.exists() and not (HERE/"run_e.py").exists()
    log=(HERE/"run.log").read_text(encoding="utf8")
    assert "No space left on device" in log and "SC101_PEELOFF302" not in log
    assert not (HERE/"forecast2400/summary.json").exists()
    code=(HERE/"run.py").read_text(encoding="utf8")
    assert code.count("OUT=HERE/'forecast2400'")==1
    code=code.replace("OUT=HERE/'forecast2400'","OUT=Path('"+OUT.as_posix()+"')")
    code=code.replace("HERE/'preflight.json'","HERE/'preflight_e.json'")
    compile(code,str(HERE/"run_e.py"),"exec")
    (HERE/"run_e.py").write_text(code,encoding="utf8")
    files=[HERE/"run.py",HERE/"run_e.py",HERE/"run.log",HERE/"preflight.json",Path(__file__)]
    evidence=dict(status="prepared_output_relocation_after_enospc",output=str(OUT),
        failed_attempt=str(HERE/"forecast2400"),failed_forecasts=0,maximum_new_forecasts=2,
        current_native_untouched=True,source_pins={str(p):sha(p) for p in files})
    (HERE/"preflight_e.json").write_text(json.dumps(evidence,indent=2)+"\n",encoding="utf8")
    print("REPAIRED OUTPUT",OUT,"prior setup failure preserved; no completed prediction repeated")


if __name__=="__main__":main()

