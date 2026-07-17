# palettes

Color palette toolkit for [pydisplay](https://github.com/PyDevices/pydisplay) — `wheel`, `cube`, `material_design`, and named Windows-16 colors on MicroPython, CircuitPython, and CPython.

## Install

### CPython (TestPyPI)

```bash
pip install \
  -i https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  palettes
```

### MicroPython (MIP)

```python
import mip
mip.install("palettes", index="https://PyDevices.github.io/micropython-lib/mip/PyDevices")
```

## Quick start

```python
from palettes import get_palette

palette = get_palette(name="wheel", length=256, saturation=1.0)
color = palette[42]
name = palette.color_name(42)
```

Named palette variants:

```python
cube = get_palette(name="cube", size=5, color_depth=16)
material = get_palette(name="material_design", color_depth=16)
```

## What you get

- `get_palette(...)` factory for wheel, cube, material_design, and named palettes
- Indexing and `color_name()` helpers
- Works on MicroPython, CircuitPython, and CPython (no native extension)

## Links

- [Documentation](https://palettes.readthedocs.io)
- [Source](https://github.com/PyDevices/palettes)
- [Issues](https://github.com/PyDevices/palettes/issues)
- [PyScript demos](https://pydevices.github.io/pydisplay/pyscript/) (`palettes_demo.py`)
- Related: [pydisplay](https://github.com/PyDevices/pydisplay), [pdwidgets](https://github.com/PyDevices/pdwidgets)

## License

MIT — see [LICENSE](LICENSE).
