"""Single stock/geometry validation pair; preserve source pins until closed."""
import hashlib
import json
from pathlib import Path
import run_upgrade_pair as runner
HERE=Path(__file__).resolve().parent
runner.OUT=HERE/'hot_validation'
def check(pins):
    for name,expected in pins.items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==expected,name
if __name__=='__main__':
    pins=json.loads((runner.OUT/'prepared.json').read_bytes())['source_pins']
    check(pins)
    code=runner.main()
    check(pins)
    raise SystemExit(code)
