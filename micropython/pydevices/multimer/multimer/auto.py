# SPDX-FileCopyrightText: 2024 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Optional host timer-provider selection.

Importing :mod:`multimer` alone performs no backend probing. Applications that
want the former platform-selection behavior opt in explicitly::

    from multimer import auto as timer

Set ``MULTIMER_BACKEND`` before importing this module to force one provider.
Explicit provider imports never fall back.
"""

import sys

from . import AsyncTimer, _async_only_runtime, _async_sleep_ms, _provider_pump

_AUTO_BACKENDS = ("machine", "librt", "win32", "sdl2", "threading", "polling")
_BACKENDS = _AUTO_BACKENDS + ("async",)
_ENV_OVERRIDE = "MULTIMER_BACKEND"


class _AsyncProvider:
    Timer = AsyncTimer
    name = "async"
    uses_interrupts = False
    is_async = True
    _defer_sync_arm = False
    sleep_ms = staticmethod(_async_sleep_ms)

    @staticmethod
    def pump():
        _provider_pump()


def _load_backend(backend_name):
    """Import one provider without fallback."""
    if backend_name == "machine":
        from . import machine as provider
    elif backend_name == "librt":
        from . import librt as provider
    elif backend_name == "win32":
        from . import win32 as provider
    elif backend_name == "sdl2":
        from . import sdl2 as provider
    elif backend_name == "threading":
        from . import threading as provider
    elif backend_name == "polling":
        from . import polling as provider
    elif backend_name == "async":
        provider = _AsyncProvider
    else:
        raise ValueError(
            f"unknown multimer backend {backend_name!r}; expected one of {_BACKENDS}"
        )
    return provider


def _forced_backend():
    import os

    getenv = getattr(os, "getenv", None)
    if getenv is None:
        return None
    try:
        value = getenv(_ENV_OVERRIDE)
    except Exception:
        return None
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _pygame_available():
    try:
        import pygame  # noqa: F401

        return True
    except ImportError:
        return False


def _auto_backends():
    """Return the unchanged host-specific provider order."""
    impl = getattr(sys.implementation, "name", "")
    skip_sdl2 = (impl == "cpython" and _pygame_available()) or sys.platform == "android"
    out = []
    for backend_name in _AUTO_BACKENDS:
        if backend_name == "win32" and sys.platform != "win32":
            continue
        if backend_name == "sdl2" and skip_sdl2:
            continue
        out.append(backend_name)
    return out


def _select_backend():
    forced = _forced_backend()
    if forced is not None:
        return _load_backend(forced)
    if _async_only_runtime():
        return _AsyncProvider

    tried = _auto_backends()
    for backend_name in tried:
        try:
            return _load_backend(backend_name)
        except ImportError:
            pass
    raise ImportError(
        f"multimer.auto: no timer backend available (tried {', '.join(tried)})"
    )


_provider = _select_backend()

Timer = _provider.Timer
name = _provider.name
uses_interrupts = _provider.uses_interrupts
is_async = _provider.is_async
sleep_ms = _provider.sleep_ms
pump = _provider.pump
_defer_sync_arm = _provider._defer_sync_arm

__all__ = ["Timer", "is_async", "name", "pump", "sleep_ms", "uses_interrupts"]
