# SPDX-FileCopyrightText: 2026 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Cooperative polling Timer (last-resort backend)."""

from . import _provider_pump, _provider_sleep_ms
from ._core import _TimerCore
from ._ticks import ticks_add, ticks_diff, ticks_ms

_active = []
name = "polling"
uses_interrupts = False
is_async = False
_defer_sync_arm = True


class Timer(_TimerCore):
    def _arm(self):
        self._next = ticks_add(ticks_ms(), self._period_ms)
        if self not in _active:
            _active.append(self)

    def _disarm(self):
        try:
            _active.remove(self)
        except ValueError:
            pass


def _tick(max_items=None):
    """Advance due polling timers (internal). Returns callbacks dispatched."""
    if not _active:
        return 0

    now = ticks_ms()
    fired = 0
    for timer in tuple(_active):
        if max_items is not None and fired >= max_items:
            break
        if timer not in _active:
            continue
        if ticks_diff(timer._next, now) > 0:
            continue

        fired += 1
        # ``_deliver`` owns hard/soft coalesce; do not call ``_invoke_callback``
        # directly (that skipped soft gap / ``hard``).
        timer._deliver()

        if timer._mode == timer.ONE_SHOT or not timer._armed:
            break

        timer._next = ticks_add(timer._next, timer._period_ms)
        while ticks_diff(timer._next, now) <= 0:
            timer._next = ticks_add(timer._next, timer._period_ms)

    return fired


def _backend_drain():
    _tick()


def _backend_sleep_ms(ms):
    """Sleep while pumping due polling timers (CircuitPython / no-thread hosts)."""
    import time

    end = ticks_add(ticks_ms(), max(0, int(ms)))
    while ticks_diff(end, ticks_ms()) > 0:
        _tick()
        # coarse yield; supervisor.delay or time.sleep
        try:
            import supervisor

            supervisor.delay(1)
        except Exception:
            time.sleep(0.001)


def pump():
    _provider_pump(_backend_drain)


def sleep_ms(ms):
    _provider_sleep_ms(ms, backend_sleep=_backend_sleep_ms, drain=_backend_drain)


__all__ = ["Timer", "is_async", "name", "pump", "sleep_ms", "uses_interrupts"]
