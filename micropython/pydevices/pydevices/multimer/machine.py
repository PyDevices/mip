"""Native ``machine.Timer`` provider."""

from machine import Timer

from . import _provider_pump, _provider_sleep_ms

name = "machine"
uses_interrupts = True
is_async = False
_defer_sync_arm = False


def pump():
    _provider_pump()


def sleep_ms(ms):
    _provider_sleep_ms(ms, uses_interrupts=True)


__all__ = ["Timer", "is_async", "name", "pump", "sleep_ms", "uses_interrupts"]
