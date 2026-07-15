# pdwidgets

Cross-platform widget toolkit for [pydisplay](https://github.com/PyDevices/pydisplay) — buttons, lists, themes, navigation, and more on MicroPython, CircuitPython, and CPython.

## Install

### MicroPython (MIP, precompiled)

```python
import mip
mip.install("pdwidgets", index="https://PyDevices.github.io/micropython-lib/mip/PyDevices")
```

### CPython (TestPyPI)

```bash
pip install \
  -i https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  pdwidgets displaysys pydisplay-graphics eventsys multimer palettes
```

Requires a pydisplay `board_config` and display stack. See [documentation](https://pdwidgets.readthedocs.io).

## Quick start

```python
import board_config
import pdwidgets as pd

display = pd.Display(board_config.display_drv, board_config.runtime)
screen = pd.Screen(display)
pd.Button(screen, x=10, y=10, w=120, h=40, label="Hello")
board_config.runtime.run_forever()
```

Lean imports (MCU-friendly):

```python
from pdwidgets.widgets.button import Button
```

## Documentation

- [pdwidgets.readthedocs.io](https://pdwidgets.readthedocs.io)
- [PyScript demos](https://pydevices.github.io/pydisplay/pyscript/) (widget examples install `pdwidgets` via MIP)

## Icon assets

Runtime icons are **importable Python modules** under [`src/pdwidgets/icons/`](src/pdwidgets/icons/)
(no binary mip). Authoring:

```bash
# 1) Optional: regenerate mono .pbm / color .bmp from Material Design
.venv/bin/python scripts/assets_generate_pdwidgets_icons.py
.venv/bin/python scripts/assets_make_color_icons.py
# 2) Convert binaries → .py modules (BITMAP = bytearray; uses sibling or TestPyPI graphics)
.venv/bin/python scripts/assets_icons_to_py.py --delete-binaries
# Optional bulk dump into assets/icons/
.venv/bin/python scripts/assets_convert_md_png_to_pbm.py
# PNG smoke probe (pydisplay display stack + material-design-icons png/)
SDL_VIDEODRIVER=dummy ../pydisplay/.venv/bin/python tools/png_test.py
```

## Related

- [pydisplay](https://github.com/PyDevices/pydisplay) — display, events, graphics backend
- [micropython-lib](https://github.com/PyDevices/micropython-lib) — MIP package index

## License

MIT — see [LICENSE](LICENSE).
