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

## Related

- [pydisplay](https://github.com/PyDevices/pydisplay) — display, events, graphics backend
- [micropython-lib](https://github.com/PyDevices/micropython-lib) — MIP package index

## License

MIT — see [LICENSE](LICENSE).
