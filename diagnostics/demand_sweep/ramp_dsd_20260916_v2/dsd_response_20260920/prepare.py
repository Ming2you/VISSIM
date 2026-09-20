"""Repeat one fixed VSL case with one extra native observation, no traffic edit."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.fast_fixed_profile import prepare
import hashlib
import json
import re
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
H=HERE.parent


def main():
    out=HERE/'native_v2';out.mkdir(exist_ok=False)
    source=H/'response_late_s23_v1/prepared_vsl/network/baseline.inpx'
    data=source.read_bytes();root=ET.fromstring(data)
    attr=root.find('./evaluation/vehRec/attributes')
    if attr is None:raise ValueError('Missing native vehicle recording attributes')
    assert len(attr)==9
    # Text insertion preserves every existing byte and every physical setting.
    pattern=rb'(<vehRec\b[^>]*>\s*<attributes>)(.*?)(</attributes>)'
    changed,n=re.subn(pattern,lambda m:m[1]+m[2]+b'<attributeSelection attributeID="DESSPEED" decimals="3" format="DEFAULT" showUnits="false"/>\r\n\t\t\t'+m[3],data,flags=re.S)
    assert n==1
    edited=ET.fromstring(changed);attributes=edited.find('./evaluation/vehRec/attributes')
    added=attributes[-1];assert added.get('attributeID')=='DESSPEED'
    attributes.remove(added)
    # Compare XML elements ignoring whitespace-only tails introduced by recording.
    def normalized(node):return (node.tag,dict(node.attrib),(node.text or '').strip(),[normalized(c) for c in node])
    assert normalized(edited)==normalized(root),'Unexpected traffic-setting change'
    target=out/'source';target.mkdir();network=target/'baseline.inpx';network.write_bytes(changed)
    assets=set(v[6:] for node in root.iter() for v in node.attrib.values() if v.startswith('#data#'))
    for name in assets:
        assert Path(name).name==name
        (target/name).write_bytes((source.parent/name).read_bytes())
    profile=json.loads((H/'response_late_s23_v1/vsl.json').read_text())
    profile['network_sha256']=hashlib.sha256(changed).hexdigest();profile['terminal_sec']=3000
    profile['vsl_commands']=[r for r in profile['vsl_commands'] if r['time_s']<3000]
    path=out/'profile.json';path.write_text(json.dumps(profile,indent=2),encoding='utf-8')
    prepare(network,path,out/'prepared')
    (out/'protocol.json').write_text(json.dumps({'seed':23,'start_s':2400,'end_s':3000,
        'source':str(source),'source_sha256':hashlib.sha256(data).hexdigest(),
        'only_network_edit':'Append native FZP DESSPEED,3decimals; all existing fields and traffic settings retained',
        'purpose':'Observe actual desired speed and DSD passage/cohort timing; not a new performance replicate',
        'reference':str(H/'response_late_s23_v1/run_vsl'),
        'required_gate':'All original nine FZP columns exactly match the existing VSL run through3000, plus native LDP and VSL readback',
        'controller_calls':0,'per_second_COM_vehicle_queries':0,'startup_no_progress_watchdog_sec':300},indent=2),encoding='utf-8')
    print(out)


if __name__=='__main__':main()
