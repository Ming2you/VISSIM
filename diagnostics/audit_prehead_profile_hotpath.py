"""Read a fixed completed worker subset; never execute a model candidate."""
import hashlib
import json
from pathlib import Path
import pstats

ROOT=Path(__file__).resolve().parents[1]
PROFILE=ROOT/'diagnostics/area_production_preflight/wu-link_t900_beta300_20260910T032525335593Z/profile'
PIDS=(13804,16020,19296,20020,21828,22840,23648,23888,25112,26256)


def main():
    files=[];aggregate={}
    for pid in PIDS:
        path=PROFILE/f'process_{pid}.pstats';meta_path=path.with_suffix('.json')
        data=path.read_bytes();meta_bytes=meta_path.read_bytes();meta=json.loads(meta_bytes)
        if not meta.get('completed'):raise ValueError('Worker profile is not complete: '+str(path))
        files.append({'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(data).hexdigest(),
            'metadata_sha256':hashlib.sha256(meta_bytes).hexdigest(),'pid':pid,'parent_pid':meta['parent_pid'],
            'completed':True,'wall_sec':meta['finish_perf_sec']-meta['start_perf_sec']})
        for (filename,line,function),(primitive,calls,self_sec,inclusive_sec,callers) in pstats.Stats(str(path)).stats.items():
            if not filename.replace('\\','/').endswith('/native_input_prehead.py'):continue
            key=f'{line}:{function}'
            row=aggregate.setdefault(key,{'line':line,'function':function,'primitive_calls':0,'calls':0,'self_sec':0.,'inclusive_sec':0.,'callers':{}})
            for k,v in (('primitive_calls',primitive),('calls',calls),('self_sec',self_sec),('inclusive_sec',inclusive_sec)):row[k]+=v
            for (source,caller_line,caller),values in callers.items():
                name=f'{Path(source).name}:{caller_line}:{caller}'
                r=row['callers'].setdefault(name,{'primitive_calls':0,'calls':0,'self_sec':0.,'inclusive_sec':0.})
                for k,v in zip(('primitive_calls','calls','self_sec','inclusive_sec'),values):r[k]+=v
        if path.read_bytes()!=data or meta_path.read_bytes()!=meta_bytes:raise ValueError('Profile changed during read')
    output={'schema':'prehead-partial-profile-audit/v1','source_commit':'dd13e08','workers':files,
        'scope':'Fixed ten completed workers selected lexically when first inspected; neither the parent process nor a full decision. Profile inclusive times overlap and must not be summed. No full-wall percentage is inferred.',
        'functions':sorted(aggregate.values(),key=lambda x:x['self_sec'],reverse=True)}
    (ROOT/'diagnostics/prehead_partial_profile_audit.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
