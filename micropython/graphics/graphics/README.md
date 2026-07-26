# graphics-py

Pure-Python `graphics` package — `FrameBuffer`, `Draw`, fonts, shapes, and image
loaders. Import as `graphics`.

> **Pip name:** `graphics-py` · **Import:** `import graphics`

On desktop/Android when a native wheel is available, prefer
[`graphics-cmod`](https://test.pypi.org/project/graphics-cmod/) (same import
name, C implementation). Both products are published from this repo and share
the same release tag / version.

## Install

### CPython (TestPyPI)

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

## Quick start

```python
import graphics

fb = graphics.FrameBuffer(
    bytearray(160 * 128 * 2), 160, 128, graphics.RGB565
)
fb.fill(0)
fb.fill_rect(10, 10, 40, 40, 0xF800)
print(graphics.implementation())  # graphics_python
```

## Links

- [API reference (native)](https://pydevices.github.io/graphics/api/)
- [Source](https://github.com/PyDevices/graphics)
- Related: [graphics-cmod](https://test.pypi.org/project/graphics-cmod/), [pydisplay](https://github.com/PyDevices/pydisplay)

## License

MIT — see [LICENSE](https://github.com/PyDevices/graphics/blob/main/LICENSE).
