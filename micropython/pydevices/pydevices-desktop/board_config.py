"""Universal non-MCU board configuration (desktop / Jupyter / PyScript)."""

import sys

from displaydev import env_bool, env_float, env_int
from displaydev.auto import AutoDisplay

_width = env_int("PYDEVICES_WIDTH", 320)
_height = env_int("PYDEVICES_HEIGHT", 480)
_rotation = env_int("PYDEVICES_ROTATION", 0)
_scale = env_float("PYDEVICES_SCALE", 2.0)

display_drv = AutoDisplay(
    width=_width,
    height=_height,
    rotation=_rotation,
    scale=_scale,
    title="{} on {}".format(sys.implementation.name, sys.platform),
)

host_read = display_drv.get_events
timer_async = env_bool("PYDEVICES_TIMER_ASYNC", display_drv.requires_async_timer)

display_drv.fill(0)

from board_peripherals import PERIPHERALS, load_peripherals

load_peripherals(globals())
