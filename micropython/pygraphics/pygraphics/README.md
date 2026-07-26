# pygraphics

Pure-Python `pygraphics` package — `FrameBuffer`, `Draw`, fonts, shapes, and image
loaders. Import as `pygraphics`.

> **Pip name:** `pygraphics` · **Import:** `import pygraphics`

On desktop/Android when a native wheel is available, prefer
[`pygraphics-cmod`](https://test.pypi.org/project/pygraphics-cmod/) (same import
name, C implementation). Both products are published from this repo and share
the same release tag / version.

## Install

### CPython (TestPyPI)

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

## Quick start

```python
import pygraphics

fb = pygraphics.FrameBuffer(
    bytearray(160 * 128 * 2), 160, 128, pygraphics.RGB565
)
fb.fill(0)
fb.fill_rect(10, 10, 40, 40, 0xF800)
print(pygraphics.implementation())  # pygraphics_python
```

## Links

- [API reference (native)](https://pydevices.github.io/pygraphics/api/)
- [Source](https://github.com/PyDevices/pygraphics)
- Related: [pygraphics-cmod](https://test.pypi.org/project/pygraphics-cmod/), [pydisplay](https://github.com/PyDevices/pydisplay)

## License

MIT — see [LICENSE](https://github.com/PyDevices/pygraphics/blob/main/LICENSE).
