"""Five-second launch-lifetime check; no simulation or input-data reads."""
import time
print('PROBE_STARTED', flush=True)
time.sleep(5)
print('PROBE_COMPLETED', flush=True)
