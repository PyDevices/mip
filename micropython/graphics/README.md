# graphics

Native and pure-Python **graphics** for MicroPython, CircuitPython, and CPython.
Import as `graphics`.

| Product | Pip / MIP | Role |
|---------|-----------|------|
| **graphics-cmod** | TestPyPI `graphics-cmod` | All-C extension (prefer on desktop/Android when available) |
| **graphics-py** | TestPyPI `graphics-py`, MIP `graphics` | Pure-Python package (same public API) |

One release tag `vX.Y.Z` publishes both products at that version.

## Install

### Native (TestPyPI)

```bash
pip install \
  -i https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  graphics-cmod
```

### Pure Python (TestPyPI)

```bash
pip install \
  -i https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  graphics-py
```

### MicroPython (MIP)

```python
import mip
mip.install("graphics", index="https://PyDevices.github.io/micropython-lib/mip/PyDevices")
```

### Quick start

```python
import graphics
from graphics import FrameBuffer, RGB565

fb = FrameBuffer(bytearray(160 * 128 * 2), 160, 128, RGB565)
fb.fill(0)
fb.fill_rect(10, 10, 40, 40, 0xF800)
print(graphics.implementation())  # native_cmod or graphics_python
```

## What you get

- `Area` — rectangle geometry helper
- `FrameBuffer` — framebuf-compatible drawing surface (returns `Area` bounds)
- Format constants: `MONO_VLSB`, `MONO_HLSB`, `MONO_HMSB`, `RGB565`, `GS2_HMSB`, `GS4_HMSB`, `GS8`, `RGB888`
- `framebuf_backend()`, `capabilities()`, `implementation()`

## Links

- [Source-linked API reference](https://pydevices.github.io/graphics/api/)
- [Source](https://github.com/PyDevices/graphics)
- [Issues](https://github.com/PyDevices/graphics/issues)
- Related: [pydisplay](https://github.com/PyDevices/pydisplay)

## License

MIT (framebuf algorithms derived from MicroPython `extmod/modframebuf.c`, Damien P. George).

---

## Build from source

### Layout

```
graphics/
  micropython.mk / micropython.cmake / circuitpython.mk / setup.py
  include/                 # C headers (gfx_*.h, font_8x*.h, qstrs)
  src/                     # C sources (core + MP/CP/CPython bindings)
  lib/graphics/            # pure-Python package (import graphics)
  tests/                   # native smoke / parity tests
  docs/ scripts/ web/
```

### CPython native (editable)

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python tests/test_area.py
.venv/bin/python tests/test_graphics.py
.venv/bin/python tests/test_subclass.py
```

### Pure Python (no extension)

```bash
PYTHONPATH=lib python3 -c "import graphics; print(graphics.implementation())"
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

When this cmod is installed or linked, `graphics.framebuf_backend()` reports
`native` and `graphics.implementation()` reports `native_cmod`. Otherwise the
pure-Python package reports `graphics_python`.
