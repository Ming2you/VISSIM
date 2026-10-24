"""Three existing native frames around the198 overlap, not a full FZP scan.

The failed fitted experiment is unchanged. POSLAT and desired speed were
recorded natively but omitted from176's compact cache; verify them at source.
"""
import hashlib
import time
from pathlib import Path

from diagnostics.repin_v3c3_review_20261001.blocking176.analyze import seek_time
from diagnostics.repin_v3c3_review_20261001.spacing_braking198.check import read, save, HERE, R


def main():
    assert not (HERE/'geometry_context.json').exists()
    started=time.perf_counter()
    cache=read(R/'blocking176/hold_frames.json.gz'); source=cache['source']
    p=Path(source['path']); stat=p.stat()
    assert stat.st_size==source['bytes'] and stat.st_mtime_ns==source['mtime_ns']
    ids={'20743','22188','13662','20776'}
    wanted=['SIMSEC','NO','LANE\\LINK\\NO','LANE\\INDEX','POS','POSLAT','SPEED',
            'DESSPEED','LENGTH','NEXTLINK\\NO','DESTLANE','LNCHG',
            'INTERACTSTATE','INTERACTTARGTYPE','INTERACTTARGNO','ACCELERATION']
    records=[]; digest=hashlib.sha256(); read_rows=0; cached_checks=0
    ix={s:i for i,s in enumerate(cache['fields'])}
    with p.open('rb') as stream:
        for line in stream:
            if line.startswith(b'$VEHICLE:'):
                names=line.split(b':',1)[1].strip().decode().split(';')
                ci={name:i for i,name in enumerate(names)}; body=stream.tell(); break
        else: raise AssertionError('Missing header')
        assert all(s in ci for s in wanted)
        byte_start=seek_time(stream,2775.1,body,stat.st_size)
        for line in stream:
            z=line.rstrip(b'\r\n').split(b';'); t=float(z[ci['SIMSEC']])
            if t<2775.1-1e-6: continue
            if t>2785.1+1e-6: break
            digest.update(line); read_rows+=1
            vid=z[ci['NO']].decode(); link=int(z[ci['LANE\\LINK\\NO']]); pos=float(z[ci['POS']])
            if vid not in ids and not (link==119 and 345<=pos<=385): continue
            record={s:z[ci[s]].decode() for s in wanted}
            prior=cache['frames'][str(t)].get(vid)
            assert prior is not None
            for old,new in [('speed','SPEED'),('pos','POS'),('lane','LANE\\INDEX'),
                            ('link','LANE\\LINK\\NO'),('accel','ACCELERATION')]:
                assert float(prior[ix[old]])==float(record[new])
                cached_checks+=1
            records.append(record)
        byte_end=stream.tell()
    assert p.stat().st_size==stat.st_size and p.stat().st_mtime_ns==stat.st_mtime_ns
    save(HERE/'geometry_context.json',dict(status='complete_source_context',
        source=str(p),source_size=stat.st_size,source_mtime_ns=stat.st_mtime_ns,
        read_window_sec=[2775.1,2785.1],read_byte_start=byte_start,read_byte_end=byte_end,
        header_bytes=body,window_sha256=digest.hexdigest(),all_window_rows=read_rows,
        cached_field_checks=cached_checks,records=records,seconds=time.perf_counter()-started,
        fits=0,forecasts=0,native_runs=0,
        limitations='Only three frames; lateral offsets show projection support, not causal shares or a continuous lane-change trajectory. Original198 fit/score unchanged.'))
    print(dict(rows=read_rows,bytes=byte_end-byte_start,cached_field_checks=cached_checks))


if __name__=='__main__':main()
