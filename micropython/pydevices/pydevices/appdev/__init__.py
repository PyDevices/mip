# SPDX-FileCopyrightText: 2026 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""appdev — application coordinator and event loop for *Python.

Quick start::

    import board_config
    import appdev
    import events

    app = appdev.App(board_config)

    @app.on(events.KEYDOWN)
    def on_key(e):
        print("Key pressed:", e.key)

    @app.every(1000)
    def heartbeat(timer=None):
        print("Heartbeat")

    app.run()
"""

from .app import (
    DEFAULT_REFRESH_MS,
    App,
)
from .devices import (
    ENCODER,
    HOST,
    JOYSTICK,
    KEYPAD,
    POINTER,
    Device,
    Encoder,
    HostEvents,
    Joystick,
    JoyMap,
    Keypad,
    Touch,
    TouchGrid,
)

__version__ = "0.1.3"

__all__ = [
    "DEFAULT_REFRESH_MS",
    "ENCODER",
    "HOST",
    "JOYSTICK",
    "KEYPAD",
    "POINTER",
    "App",
    "Device",
    "Encoder",
    "HostEvents",
    "JoyMap",
    "Joystick",
    "Keypad",
    "Touch",
    "TouchGrid",
    "__version__",
]
