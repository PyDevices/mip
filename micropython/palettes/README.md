# palettes

Color palette toolkit for [pydisplay](https://github.com/PyDevices/pydisplay) — `wheel`, `cube`, `material_design`, and named Windows-16 colors on MicroPython, CircuitPython, and CPython.

## Install

### MicroPython (MIP, precompiled)

```python
import mip
mip.install("palettes", index="https://PyDevices.github.io/micropython-lib/mip/PyDevices")
```

### CPython (TestPyPI)

```bash
pip install \
  -i https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  pydevices-palettes
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

## Documentation

- [palettes.readthedocs.io](https://palettes.readthedocs.io)
- [PyScript demos](https://pydevices.github.io/pydisplay/pyscript/) (`palettes_demo.py` installs `palettes` via MIP)

## Related

- [pydisplay](https://github.com/PyDevices/pydisplay) — display, events, graphics backend
- [pdwidgets](https://github.com/PyDevices/pdwidgets) — widget toolkit (depends on `palettes`)
- [micropython-lib](https://github.com/PyDevices/micropython-lib) — MIP package index

## License

MIT — see [LICENSE](LICENSE).
