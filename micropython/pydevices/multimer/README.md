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
  pydevices-multimer
```

### MicroPython (MIP)

```python
import mip

mip.install("multimer", index="https://PyDevices.github.io/mip")
```

## Quick start

Choose a timer provider explicitly:

```python
import multimer
from multimer import machine as timer


def on_tick(tim):
    print("tick")


tim = timer.Timer(-1)
tim.init(mode=timer.Timer.PERIODIC, period=500, callback=on_tick)

while True:
    timer.sleep_ms(1000)
```

Portable applications may opt into host selection:

```python
from multimer import auto as timer
```

Explicit providers are `machine`, `librt`, `win32`, `sdl2`, `threading`, and
`polling`. Each provider exposes the same surface:

- `Timer` — the provider's `machine.Timer`-compatible class
- `name` — provider name
- `uses_interrupts` — callbacks run without an application pump
- `is_async` — whether `Timer` and `sleep_ms` are asynchronous
- `pump()` — deliver scheduled/provider work; safe when no work is pending
- `sleep_ms(ms)` — provider-aware sleep

Changing between explicit and automatic selection changes only the import:

```python
from multimer import threading as timer
# from multimer import auto as timer
```

## Backend-neutral API

Importing `multimer` does not probe or select a synchronous provider. The root
exports:

- `AsyncTimer`
- `ticks_ms`, `ticks_add`, `ticks_diff`, `ticks_less`, `monotonic`
- `schedule`
- lazy `asyncio` and `loop_running`
- development deadline hooks

Async applications select `AsyncTimer` directly:

```python
from multimer import AsyncTimer, asyncio


async def main():
    tim = AsyncTimer(-1)
    tim.init(mode=AsyncTimer.PERIODIC, period=200, callback=lambda _: print("tick"))
    await asyncio.sleep(2)


asyncio.run(main())
```

## Automatic selection

`multimer.auto` preserves the platform order:

```text
machine → librt → win32 → sdl2 → threading → polling
```

PyScript and Jupyter select `AsyncTimer`. On CPython, SDL2 is skipped when
pygame is available; Win32 is considered only on Windows; Android skips SDL2.

Set `MULTIMER_BACKEND` before importing `multimer.auto` to force one provider.
Accepted values are `machine`, `librt`, `win32`, `sdl2`, `threading`,
`polling`, and `async`. A forced provider that is unknown or unavailable raises
instead of falling back.

Optional application keep-alive loops are available from `pydevices-eventsys`;
LVGL owns its own coordinator.

## Links

- [Documentation — multimer](https://pydevices.github.io/pydevices/multimer.html)
- [Source](https://github.com/PyDevices/pydevices/tree/main/lib/multimer)
- [Issues](https://github.com/PyDevices/pydevices/issues)
- Related: `pydevices-eventsys`

## License

MIT — see [LICENSE](https://github.com/PyDevices/pydevices/blob/main/LICENSE).
