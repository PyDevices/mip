"""
Combination board configuration for desktop, pyscript and jupyter notebook platforms.
If you are running pydisplay on a microcontroller, you will need to get or create a
board_config.py file that is specific to your hardware from:

https://github.com/PyDevices/micropython-hardware/tree/main/board_configs

Desktop size / timer overrides (process env or ``displaysys.env_set`` before import)::

    PYDISPLAY_WIDTH / PYDISPLAY_HEIGHT / PYDISPLAY_SCALE — integer panel size / scale
    PYDISPLAY_ROTATION — rotation degrees
    PYDISPLAY_TIMER_ASYNC — truthy/falsey timer mode overlay on requires_async_timer
"""

import sys

from displaysys import AutoDisplay, env_bool, env_float, env_int
import eventsys

_DESKTOP_PLATFORMS = frozenset(("linux", "darwin", "win32", "unix", "webassembly", "emscripten"))


def _warn_embedded_default_board():
    impl = sys.implementation.name
    if impl in ("micropython", "circuitpython") and sys.platform not in _DESKTOP_PLATFORMS:
        print(
            "board_config: default board_config.py from lib/ is for desktop "
            "displaysys only.\n"
            "On a microcontroller, copy a board_config.py for your hardware "
            "into the current working directory (the parent of lib/).\n"
            "Download board configs from:\n"
            "  https://github.com/PyDevices/micropython-hardware/tree/main/board_configs"
        )


_warn_embedded_default_board()

display_drv = AutoDisplay(
    width=env_int("PYDISPLAY_WIDTH", 320),
    height=env_int("PYDISPLAY_HEIGHT", 480),
    rotation=env_int("PYDISPLAY_ROTATION", 0),
    scale=env_float("PYDISPLAY_SCALE", 2.0),
    title="{} on {}".format(sys.implementation.name, sys.platform),
)

runtime = eventsys.Runtime(
    displays=[display_drv],
    host_read=display_drv.get_events,
    timer_async=env_bool("PYDISPLAY_TIMER_ASYNC", display_drv.requires_async_timer),
)

display_drv.fill(0)
