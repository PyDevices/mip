# SPDX-FileCopyrightText: 2024 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Backend-neutral timing primitives for MicroPython and Python hosts.

Importing :mod:`multimer` never selects a synchronous timer backend. Choose a
provider explicitly, or opt into host selection through :mod:`multimer.auto`::

    import multimer
    from multimer import auto as timer

    tim = timer.Timer(-1)
    tim.init(period=100, callback=on_tick)
    timer.sleep_ms(10)

Backend-neutral clock, scheduling, and asyncio helpers remain available from
this package root.
"""

import sys

from ._async_timer import AsyncTimer
from ._asyncio_loader import load_asyncio, loop_running
from ._schedule import _run_pending, schedule
from ._ticks import (
    _raw_sleep_ms,
    monotonic,
    run_deadline_hook,
    set_deadline_hook,
    ticks_add,
    ticks_diff,
    ticks_less,
    ticks_ms,
)

_PROVIDER_MODULES = (
    "auto",
    "librt",
    "machine",
    "polling",
    "sdl2",
    "threading",
    "win32",
)


def _provider_pump(drain=None):
    """Drain scheduled work and an optional provider event queue."""
    _run_pending()
    if drain is not None:
        drain()


def _provider_sleep_ms(ms, *, backend_sleep=None, drain=None, uses_interrupts=False):
    """Sleep using one provider's unchanged signal/pump behavior."""
    run_deadline_hook()
    if not uses_interrupts:
        _provider_pump(drain)
    if backend_sleep is not None:
        backend_sleep(ms)
    else:
        _raw_sleep_ms(ms)
    run_deadline_hook()
    if not uses_interrupts:
        _provider_pump(drain)


async def _async_sleep_ms(ms):
    """Yield for *ms* through the selected asyncio implementation."""
    aio = load_asyncio()
    if aio is None:
        raise ImportError("async sleep requires asyncio, uasyncio, or _asyncio")
    sleep = getattr(aio, "sleep_ms", None)
    if sleep is not None:
        await sleep(ms)
    else:
        await aio.sleep(ms / 1000)
    run_deadline_hook()


def _async_only_runtime():
    """True on hosts whose application lifecycle is owned by an async loop."""
    if sys.platform in ("emscripten", "webassembly"):
        return True
    try:
        import pyscript  # noqa: F401

        return True
    except Exception:
        pass
    try:
        get_ipython()  # noqa: F821
        return True
    except Exception:
        return False


__all__ = [
    "AsyncTimer",
    "asyncio",
    "loop_running",
    "monotonic",
    "run_deadline_hook",
    "schedule",
    "set_deadline_hook",
    "ticks_add",
    "ticks_diff",
    "ticks_less",
    "ticks_ms",
]


def __getattr__(name):
    if name == "asyncio":
        return load_asyncio()
    # MicroPython resolves ``from multimer import polling`` through package
    # ``__getattr__`` and does not perform CPython's automatic submodule
    # fallback afterward. Import only the explicitly requested provider here;
    # a plain ``import multimer`` still loads none of them.
    if name in _PROVIDER_MODULES:
        module = __import__(f"{__name__}.{name}", None, None, (name,))
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
