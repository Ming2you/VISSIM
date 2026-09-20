The first audit stopped before emitting results because its hand-written
spatial locator rejected native terminal overshoot at a1s simulation step.
The canonical Observer assigns these positions to the last cell. The failed
source is preserved as source_failed.py.txt. v2 retains that stock convention,
checks overshoot against the existing speed/terminal tolerance and excludes
positions past the physical end from small-bin crowding. No native result,
geometry or canonical Observer was changed.
