# SPDX-FileCopyrightText: 2026 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Windows waitable-timer backend (CPython + ``uwin32``).

APCs run on the main thread during an alertable wait. ``_backend_sleep_ms``
uses ``SleepEx`` so ``uses_interrupts`` is true (librt analogue).
"""

import uwin32 as win

from . import _provider_pump, _provider_sleep_ms
from ._core import _TimerCore

name = "win32"
uses_interrupts = True
is_async = False
_defer_sync_arm = False


def _backend_sleep_ms(ms):
    win.SleepEx(ms, True)


def pump():
    _provider_pump()


def sleep_ms(ms):
    _provider_sleep_ms(ms, backend_sleep=_backend_sleep_ms, uses_interrupts=True)


__all__ = ["Timer", "is_async", "name", "pump", "sleep_ms", "uses_interrupts"]


class Timer(_TimerCore):
    """Timer backed by ``CreateWaitableTimer`` / ``SetWaitableTimer``."""

    def __init__(self, id=-1, **kwargs):
        self._handle = None
        self._apc = None
        super().__init__(id, **kwargs)

    def _arm(self):
        self._handle = win.CreateWaitableTimerExW()
        self._apc = win.TIMERAPCROUTINE(self._on_apc)
        period = self._period_ms if self._mode == self.PERIODIC else 0
        win.SetWaitableTimer(self._handle, self._period_ms, period, self._apc, None)

    def _disarm(self):
        handle = self._handle
        self._handle = None
        self._apc = None
        if handle:
            try:
                win.CancelWaitableTimer(handle)
            except Exception:
                pass
            try:
                win.CloseHandle(handle)
            except Exception:
                pass

    def _on_apc(self, _arg, _low, _high):
        if self._mode is None:
            return
        self._deliver()
