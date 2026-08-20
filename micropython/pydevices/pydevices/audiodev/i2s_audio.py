"""MCU I2S adapter: wrap ``machine.I2S`` as :class:`audiodev.PCMOutput` / :class:`PCMInput`."""

try:
    import asyncio
except ImportError:  # pragma: no cover
    try:
        import uasyncio as asyncio
    except ImportError:
        asyncio = None

import sys

from audiodev import PCMInput, PCMOutput


def _resolve(value):
    return value() if callable(value) else value


def _close_i2s(i2s):
    if i2s is None:
        return
    if hasattr(i2s, "deinit"):
        i2s.deinit()
    elif hasattr(i2s, "close"):
        i2s.close()


class I2SPCMOutput(PCMOutput):
    """Playback through ``machine.I2S`` (or any object with ``write``)."""

    def __init__(self, i2s, format, **kwargs):
        super().__init__(format, **kwargs)
        self._i2s_factory = i2s
        self._i2s = None
        self._async_stream = None

    @property
    def i2s(self):
        return self._i2s

    def _open(self):
        self._i2s = _resolve(self._i2s_factory)
        if hasattr(self._i2s, "open"):
            self._i2s.open()

    def _close(self):
        i2s = self._i2s
        self._i2s = None
        self._async_stream = None
        _close_i2s(i2s)

    def _write(self, buf):
        return self._i2s.write(buf)

    async def _awrite(self, buf):
        if sys.implementation.name == "micropython":
            if self._async_stream is None:
                self._async_stream = asyncio.StreamWriter(self._i2s)
            self._async_stream.write(buf)
            await self._async_stream.drain()
            return len(buf)
        return await super()._awrite(buf)


class I2SPCMInput(PCMInput):
    """Capture through ``machine.I2S`` (or any object with ``readinto``)."""

    def __init__(self, i2s, format, **kwargs):
        super().__init__(format, **kwargs)
        self._i2s_factory = i2s
        self._i2s = None
        self._async_stream = None

    @property
    def i2s(self):
        return self._i2s

    def _open(self):
        self._i2s = _resolve(self._i2s_factory)
        if hasattr(self._i2s, "open"):
            self._i2s.open()

    def _close(self):
        i2s = self._i2s
        self._i2s = None
        self._async_stream = None
        _close_i2s(i2s)

    def _readinto(self, buf):
        return self._i2s.readinto(buf)

    async def _areadinto(self, buf):
        if sys.implementation.name == "micropython":
            if self._async_stream is None:
                self._async_stream = asyncio.StreamReader(self._i2s)
            return await self._async_stream.readinto(buf)
        return await super()._areadinto(buf)


def audio_out(i2s, format, **kwargs):
    """Build an :class:`I2SPCMOutput` around *i2s* (instance or factory)."""
    return I2SPCMOutput(i2s, format, **kwargs)


def audio_in(i2s, format, **kwargs):
    """Build an :class:`I2SPCMInput` around *i2s* (instance or factory)."""
    return I2SPCMInput(i2s, format, **kwargs)
