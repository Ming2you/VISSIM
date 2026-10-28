"""Wait (at most MAX seconds, default 530) until a JSON state file says status/stage done; print a one-line status."""
import io, json, os, sys, time

path = sys.argv[1]
key = sys.argv[2] if len(sys.argv) > 2 else 'status'
MAX = int(sys.argv[3]) if len(sys.argv) > 3 else 530
t0 = time.time()
last = None
while True:
    try:
        with io.open(path, encoding='utf-8-sig') as f:
            last = json.load(f)
    except Exception as e:  # file mid-write
        last = {'read_error': str(e)}
    if last.get(key) == 'done':
        print('DONE', json.dumps(last, ensure_ascii=False)[:1500])
        break
    if time.time() - t0 > MAX:
        print('WAITING', time.strftime('%H:%M:%S'), json.dumps(last, ensure_ascii=False)[:600])
        break
    time.sleep(20)
