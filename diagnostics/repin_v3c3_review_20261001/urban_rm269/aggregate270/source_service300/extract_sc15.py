"""One closed-run SC15/SC101 positional cache, reusing the verified291 reader.

This is diagnostic future evidence only, never a predictor input or a fitted rate.
The already cached291 links do not include this source/destination corridor.
"""
import ctypes
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
A=HERE.parent
ROOT=HERE.parents[4]
OUT=Path('E:/VISSIM_analysis/20261010_sc15_source300')


def read(p): return json.loads(Path(p).read_bytes())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert not (OUT/'extract_intent.json').exists(), 'No duplicate source scan'
    old=read('E:/VISSIM_analysis/20261010_gatearrival291/completion.json')
    assert old['status']=='complete_thin_closed_corridor_cache'
    closure=read('E:/VISSIM_analysis/20261010_urbanrm269_cityonly289/runtime_closure.json')
    assert closure['all_owned_processes_closed'] and closure['normal_sim_done_sec']==2850
    reader=A/'gatearrival291/extract_closed.py'
    assert sha(reader)==old['script_sha256']
    spec=importlib.util.spec_from_file_location('closed_reader291',reader)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    geometry=read(A/'sc101_clock299/source_geometry.json')
    network=Path(geometry['network_path'])
    assert sha(network)==geometry['network_sha256']
    xml=ET.parse(network).getroot()
    links={341,343,1220008501,1220008502,1220008401,1220008402,1220011503,1220006903}
    for node in xml.findall('./links/link'):
        ends=[e.get('lane','').split()[0] for e in node if e.tag in ('fromLinkEndPt','toLinkEndPt')]
        if len(ends)==2 and any(int(e) in links for e in ends):
            # The source roads and their immediate connectors are enough to
            # retain a lower-bound crossing witness without scanning all lanes.
            links.add(int(node.get('no')))
    kernel=ctypes.WinDLL('kernel32')
    kernel.GetCurrentProcess.restype=ctypes.c_void_p
    kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    OUT.mkdir(parents=True,exist_ok=True)
    intent=dict(status='started_no_automatic_retry',max_passes=2,window=[2395.1,2845.1],
        reason='Existing291 cache excludes SC15 source roads. Separate source flow from receiver head capacity.',
        links=sorted(links),source_pins={str(reader):sha(reader),str(network):sha(network),str(Path(__file__)):sha(__file__)},
        future_truth_usage='diagnosis only',new_forecasts=0,new_native_runs=0,new_fits=0)
    (OUT/'extract_intent.json').write_text(json.dumps(intent,indent=2)+'\n',encoding='utf8')
    records={}
    for arm in ('hold','city'):
        source=Path(old['arms'][arm]['source'])
        result=module.extract(source,links)
        assert result['source_sha256']==old['arms'][arm]['source_sha256']
        target=OUT/(arm+'.json.gz')
        assert not target.exists()
        target.write_bytes(gzip.compress(json.dumps(result,allow_nan=False).encode('utf8')))
        records[arm]={k:result[k] for k in ('source','source_sha256','source_size_bytes','rows_retained')}
        records[arm].update(cache=str(target),cache_sha256=sha(target),frames=len(result['frames']))
        print(arm,records[arm],flush=True)
    report=dict(status='complete_sc15_sc101_source_cache',arms=records,source_passes=2,physical_links=sorted(links),
        new_native_runs=0,new_forecasts=0,new_fits=0,source_pins=intent['source_pins'])
    (OUT/'completion.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')


if __name__=='__main__': main()
