# multimer

Cross-platform `machine.Timer`-style providers, `AsyncTimer`, millisecond ticks,
and scheduling helpers for MicroPython, CircuitPython, and CPython.

Canonical source: [pydevices/lib/multimer](https://github.com/PyDevices/pydevices/tree/main/lib/multimer).

## Install

### CPython (TestPyPI)

```bash
pip install \
  -i https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  pydevices
```

`pydevices` is one distribution covering the whole core `lib/` tree. MIP
publishes each component separately: `mip.install("multimer", …)`.

### MicroPython (MIP)

```python
import mip

mip.install("multimer", index="https://PyDevices.github.io/mip")
```

## Quick start

Choose a timer provider explicitly:

```python
from multimer import machine as timer

tim = timer.Timer(-1)
tim.init(mode=timer.Timer.PERIODIC, period=500, callback=lambda t: print("tick"))

while True:
    timer.sleep_ms(1000)
```

Or let the host decide — the only change is the import:

```python
from multimer import auto as timer
```

Explicit providers are `machine`, `librt`, `win32`, `sdl2`, `threading`, and
`polling`; each exposes the same surface. Importing `multimer` itself probes
nothing and gives you `AsyncTimer`, the `ticks_*` helpers, and `schedule`.

**Everything else — the provider-selection order, the runtime matrix, async
timers, `pump()` / `sleep_ms()`, hard versus soft delivery, and the
`MULTIMER_BACKEND` override — is in
[docs/multimer.md](https://github.com/PyDevices/pydevices/blob/main/docs/multimer.md).**

## Links

- [Documentation — multimer](https://github.com/PyDevices/pydevices/blob/main/docs/multimer.md)
- [Source](https://github.com/PyDevices/pydevices/tree/main/lib/multimer)
- [Issues](https://github.com/PyDevices/pydevices/issues)
- Related: `pydevices-pygraphics`, `pydevices-desktop`

## License

MIT — see [LICENSE](https://github.com/PyDevices/pydevices/blob/main/LICENSE).
