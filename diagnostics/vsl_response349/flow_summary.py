"""Read saved forecasts and native detector counts; no simulation or fitting."""
import argparse,csv,gzip,hashlib,json,math
from collections import defaultdict
from pathlib import Path
read=lambda p:json.loads(Path(p).read_bytes())

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    assert not (a.out/'flow_comparison.json').exists()
    assessment=read(a.out/'assessment.json');start=assessment['at_sec'];arm=assessment['arm']
    folder=Path(f'E:/VISSIM_runs/20261008_coupling268_{arm}_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
    native=[read(folder/f'state_{t:06}.json')['obs150'] for t in range(start+150,start+451,150)]
    dc=native[0]['detector_config'];data=Path(dc['path']).read_bytes()
    assert hashlib.sha256(data).hexdigest()==dc['sha256']
    detectors=list(csv.DictReader(data.decode('utf-8-sig').splitlines()))
    refs=defaultdict(list)
    for row in detectors:
        if row['role'] in ('off_entry','chain_end'):refs[row['boundary_ref']].append(row['dcm_no'])
    observed={ref:[sum(obs['detectors'][key] for key in keys) for obs in native] for ref,keys in refs.items()}
    model={}
    for case in ('recorded','vsl110','vsl90'):
        response=json.loads(gzip.decompress((a.out/(case+'_response.json.gz')).read_bytes()))
        values={ref:[0.,0.,0.] for ref in refs}
        for tr in response['transfers']:
            if tr['source'] not in ('freeway:FW_E','freeway:FW_W'):continue
            target=tr['target'];ref=None
            if target.startswith('transit:exchange:off:'):ref='off_entry:'+target.split(':')[-1]
            elif target.startswith('external:terminal:'):ref='chain_end:'+target.split(':')[-1]
            if ref is None:continue
            block=int((tr['end_sec']-start-1e-7)//150)
            assert 0<=block<3 and tr['start_sec']>=start+150*block-1e-7
            values[ref][block]+=tr['vehicles']
        model[case]=values
    report=dict(scope='Conditional recorded command forecast and model-only VSL contrast; legacy urban recipe. Native detector1m and model cell port can differ in position.',
        at_sec=start,new_forecasts=0,new_native_runs=0,
        rows=[dict(ref=ref,native150=observed[ref],predicted150=model['recorded'][ref],
            total_error=sum(model['recorded'][ref])-sum(observed[ref]),
            vsl90_minus110_150=[x-y for x,y in zip(model['vsl90'][ref],model['vsl110'][ref])]) for ref in refs])
    (a.out/'flow_comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps([r for r in report['rows'] if r['ref'] in ('off_entry:10481','off_entry:10483','off_entry:10643','off_entry:10682','chain_end:FW_E')],indent=2))

if __name__=='__main__':main()
