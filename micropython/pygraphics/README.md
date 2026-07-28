# pygraphics

Native and pure-Python **pygraphics** for MicroPython, CircuitPython, and CPython.
Import as `pygraphics`.

| Product | Pip / MIP | Role |
|---------|-----------|------|
| **pygraphics-cmod** | TestPyPI `pygraphics-cmod` | All-C extension (prefer on desktop/Android/Pyodide when available) |
| **pygraphics** | TestPyPI `pygraphics`, MIP `pygraphics` | Pure-Python package (same public API) |

One release tag `vX.Y.Z` publishes both products at that version.

## Install

### Native (TestPyPI)

```bash
pip install \
  -i https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  pygraphics-cmod
```

### Pure Python (TestPyPI)

```bash
pip install \
  -i https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  pygraphics
```

### MicroPython (MIP)

```python
import mip
mip.install("pygraphics", index="https://PyDevices.github.io/micropython-lib/mip/PyDevices")
```

### Quick start

```python
import pygraphics
from pygraphics import FrameBuffer, RGB565

fb = FrameBuffer(bytearray(160 * 128 * 2), 160, 128, RGB565)
fb.fill(0)
fb.fill_rect(10, 10, 40, 40, 0xF800)
print(pygraphics.implementation())  # native_cmod or pygraphics_python
```

## What you get

- `Area` — rectangle geometry helper
- `FrameBuffer` — framebuf-compatible drawing surface (returns `Area` bounds)
- Format constants: `MONO_VLSB`, `MONO_HLSB`, `MONO_HMSB`, `RGB565`, `GS2_HMSB`, `GS4_HMSB`, `GS8`, `RGB888`
- `framebuf_backend()`, `capabilities()`, `implementation()`

## Links

- [Documentation](https://pygraphics.readthedocs.io)
- [Source-linked API reference](https://pydevices.github.io/pygraphics/api/)
- [Source](https://github.com/PyDevices/pygraphics)
- [Issues](https://github.com/PyDevices/pygraphics/issues)
- Related: [pydisplay](https://github.com/PyDevices/pydisplay)

## License

MIT (framebuf algorithms derived from MicroPython `extmod/modframebuf.c`, Damien P. George).

---

## Build from source

### Layout

```
pygraphics/
  micropython.mk / micropython.cmake / circuitpython.mk / setup.py
  src/                     # C sources + headers (gfx_*.h, font_8x*.h, qstrs)
  lib/pygraphics/            # pure-Python package (import pygraphics)
  tests/                   # native smoke / parity tests
  tools/                   # developer benchmarks / helpers
  docs/ scripts/ web/
```

### CPython native (editable)

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python tests/test_area.py
.venv/bin/python tests/test_pygraphics.py
.venv/bin/python tests/test_subclass.py
```

### Pure Python (no extension)

```bash
PYTHONPATH=lib python3 -c "import pygraphics; print(pygraphics.implementation())"
```

### MicroPython

Clone as a sibling of `micropython/`:

```
workspace/
  graphics/       ← this repo
  micropython/
```

```bash
cd micropython/ports/unix
make submodules
make USER_C_MODULES=../../..
cd ../../..
./micropython/ports/unix/build-standard/micropython graphics/tests/test_area.py
```

([cmods](https://github.com/PyDevices/cmods) is an optional convenience workspace with `./build_mp.sh`; it is not required.)

### pydisplay integration

When this cmod is installed or linked, `pygraphics.framebuf_backend()` reports
`native` and `pygraphics.implementation()` reports `native_cmod`. Otherwise the
pure-Python package reports `pygraphics_python`.
