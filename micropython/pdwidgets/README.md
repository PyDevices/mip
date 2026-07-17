# pdwidgets

Cross-platform widget toolkit for [pydisplay](https://github.com/PyDevices/pydisplay) — buttons, lists, themes, navigation, and more on MicroPython, CircuitPython, and CPython.

## Install

### CPython (TestPyPI)

```bash
pip install \
  -i https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  pdwidgets displaysys pydisplay-graphics eventsys multimer palettes
```

Requires a pydisplay `board_config` and display stack.

### MicroPython (MIP)

```python
import mip
mip.install("pdwidgets", index="https://PyDevices.github.io/micropython-lib/mip/PyDevices")
```

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

## What you get

- Screens, themes, and a growing widget set (buttons, lists, navigation, …)
- Works with pydisplay `displaysys` + `eventsys.Runtime`
- Importable icon modules under `pdwidgets.icons` (no binary MIP assets)

## Links

- [Documentation](https://pdwidgets.readthedocs.io)
- [Source](https://github.com/PyDevices/pdwidgets)
- [Issues](https://github.com/PyDevices/pdwidgets/issues)
- [PyScript demos](https://pydevices.github.io/pydisplay/pyscript/)
- Related: [pydisplay](https://github.com/PyDevices/pydisplay), [palettes](https://github.com/PyDevices/palettes)

## License

MIT — see [LICENSE](LICENSE).

---

## Icon assets (maintainers)

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
