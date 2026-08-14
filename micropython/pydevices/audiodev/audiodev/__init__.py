"""Portable PCM and tone device contracts for MicroPython and CPython.

Backends subclass :class:`PCMOutput`, :class:`PCMInput`, and
:class:`ToneOutput`. Optional host selection lives in :mod:`audiodev.auto`
and is never imported from here.
"""

try:
    import asyncio
except ImportError:  # pragma: no cover - uasyncio name on older firmware
    try:
        import uasyncio as asyncio
    except ImportError:
        asyncio = None

# Latency profiles, shared vocabulary for every backend's ``audio_out`` /
# ``audio_in``. Backends translate a profile into their own block and queue
# sizes -- the names live here so all of them spell it the same way, and so a
# caller can ask for a profile without knowing which backend it will get.
#
# ``None``      backend default: buffered for throughput, which is what a
#               producer that can write faster than realtime wants (a TTS pump
#               with whole utterances ready, file playback).
# ``"low"``     interactive: shortest block and queue the backend supports, for
#               a producer that writes at realtime with a small look-ahead (a
#               synth responding to key presses). A buffered profile turns
#               directly into note-to-sound delay for those callers.
# ``"buffered"``the default, named explicitly.
LATENCIES = (None, "low", "buffered")


def check_latency(latency):
    """Validate a latency profile name, returning it unchanged.

    Raises rather than falling back, so a typo is a visible error instead of
    silently buffered audio in an app that asked for low latency.
    """
    if latency not in LATENCIES:
        raise ValueError(
            "unknown latency profile {!r}; expected one of {}".format(latency, LATENCIES)
        )
    return latency


# Queue depth for the "low" profile, in milliseconds of audio.
LOW_LATENCY_QUEUE_MS = 100


def queue_bytes(fmt, latency=None, queue_ms=None, default=None, minimum=0):
    """Bytes of buffering for a latency profile, e.g. ``machine.I2S(ibuf=...)``.

    MCU drivers size their ring buffer in bytes, which depends on the format, so
    the profile is expressed in milliseconds and converted here. ``default`` is
    returned untouched for the buffered profile: a board's own value is usually
    tuned against its codec and should not be recomputed from a round number.
    ``minimum`` is the smallest size the driver can work with (for I2S, a few DMA
    buffers), so a caller asking for an unusable depth gets a working device.
    """
    check_latency(latency)
    if queue_ms is None:
        if latency != "low":
            return default
        queue_ms = LOW_LATENCY_QUEUE_MS
    wanted = fmt.rate * fmt.frame_size * int(queue_ms) // 1000
    return max(minimum, fmt.frame_size, wanted)


async def _asleep(seconds=0):
    if seconds and hasattr(asyncio, "sleep_ms"):
        await asyncio.sleep_ms(int(seconds * 1000) if seconds >= 0.001 else 0)
        return
    if hasattr(asyncio, "sleep_ms") and not seconds:
        await asyncio.sleep_ms(0)
        return
    await asyncio.sleep(seconds)


class AudioFormat:  # noqa: PLW1641 - mutable value object is intentionally unhashable
    """Description of raw, interleaved PCM frames."""

    def __init__(self, rate, channels, bits, signed=True, byteorder="little"):
        if rate <= 0:
            raise ValueError("rate must be positive")
        if channels <= 0:
            raise ValueError("channels must be positive")
        if bits not in (8, 16, 32):
            raise ValueError("bits must be 8, 16, or 32")
        if byteorder not in ("little", "big"):
            raise ValueError("byteorder must be 'little' or 'big'")
        self.rate = int(rate)
        self.channels = int(channels)
        self.bits = int(bits)
        self.signed = bool(signed)
        self.byteorder = byteorder
        self.frame_size = self.channels * self.bits // 8

    def __repr__(self):
        return "AudioFormat(rate=%d, channels=%d, bits=%d, signed=%r, byteorder=%r)" % (
            self.rate,
            self.channels,
            self.bits,
            self.signed,
            self.byteorder,
        )

    def __eq__(self, other):
        return isinstance(other, AudioFormat) and (
            self.rate,
            self.channels,
            self.bits,
            self.signed,
            self.byteorder,
        ) == (
            other.rate,
            other.channels,
            other.bits,
            other.signed,
            other.byteorder,
        )


class AudioSession:
    """Coordinate devices which share a codec or peripheral."""

    def __init__(self, codec_factory=None, duplex=False):
        self.codec_factory = codec_factory
        self.duplex = bool(duplex)
        self.codec = None
        self._owners = []

    def get_codec(self):
        """Return the shared codec, constructing it on first access."""
        if self.codec is None and self.codec_factory is not None:
            self.codec = self.codec_factory()
        return self.codec

    def acquire(self, owner, direction):
        if owner in self._owners:
            return self.codec
        if self._owners and not self.duplex:
            raise OSError("audio session is already active")
        self.get_codec()
        self._owners.append(owner)
        return self.codec

    def release(self, owner):
        if owner in self._owners:
            self._owners.remove(owner)


def _clamp_percent(value):
    value = int(value)
    if value < 0:
        return 0
    if value > 100:
        return 100
    return value


def _scale_pcm(source, target, fmt, percent):
    """Scale PCM into target without allocating per sample."""
    src = memoryview(source)
    dst = memoryview(target)
    length = len(src)
    if len(dst) < length:
        raise ValueError("target is too small")
    if percent == 100:
        dst[:length] = src
        return length
    if percent == 0:
        dst[:length] = bytes(length)
        return length

    width = fmt.bits // 8
    order = fmt.byteorder
    signed = fmt.signed
    midpoint = 0 if signed else 1 << (fmt.bits - 1)
    sign_bit = 1 << (fmt.bits - 1)
    modulus = 1 << fmt.bits
    for offset in range(0, length, width):
        sample = int.from_bytes(src[offset : offset + width], order)
        if signed and sample & sign_bit:
            sample -= modulus
        if signed:
            sample = sample * percent // 100
        else:
            sample = midpoint + (sample - midpoint) * percent // 100
        dst[offset : offset + width] = (sample % modulus).to_bytes(width, order)
    return length


class _Device:
    """Shared open/close, session, and no-op queue housekeeping."""

    direction = None

    def __init__(self, *, session=None):
        self.session = session
        self.is_open = False
        self._codec = None

    @property
    def codec(self):
        if self._codec is None and self.session is not None:
            return self.session.get_codec()
        return self._codec

    @codec.setter
    def codec(self, value):
        self._codec = value

    def _open(self):
        """Open the transport. Subclasses override."""
        pass

    def _close(self):
        """Close the transport. Subclasses override."""
        pass

    def open(self):
        if self.is_open:
            return self
        if self.session is not None:
            self.session.acquire(self, self.direction)
        try:
            self._open()
            self.is_open = True
        except Exception:
            if self.session is not None:
                self.session.release(self)
            raise
        return self

    def close(self):
        if not self.is_open:
            return
        try:
            self._close()
        finally:
            self.is_open = False
            if self.session is not None:
                self.session.release(self)

    deinit = close

    def service(self):
        """Per-tick housekeeping. Queued hosts override; default is a no-op."""
        return None

    def queued_size(self):
        """Bytes still waiting to play or capture. Default 0."""
        return 0

    def is_active(self):
        """True while PCM remains queued. Default False."""
        return False

    def clear(self):
        """Drop queued PCM now. Default no-op."""
        return None

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc, traceback):
        self.close()


class PCMOutput(_Device):
    """Raw PCM playback with normalized volume and async support.

    Subclasses implement :meth:`_write` (and optionally :meth:`_drain`,
    :meth:`_awrite`, :meth:`_adrain`, :meth:`service`).
    """

    kind = "pcm"
    direction = "out"

    def __init__(
        self,
        format,
        *,
        session=None,
        codec=None,
        amplifier=None,
        set_hardware_volume=None,
        set_hardware_mute=None,
        power=None,
    ):
        super().__init__(session=session)
        self.format = format
        self.codec = codec
        self.amplifier = amplifier
        self._set_hardware_volume = set_hardware_volume
        self._set_hardware_mute = set_hardware_mute
        self._power = power
        self._volume = 100
        self._muted = False
        self._scratch = bytearray()
        capabilities = {"pcm", "playback", "volume", "mute"}
        capabilities.add("hardware-volume" if set_hardware_volume else "software-volume")
        self.capabilities = frozenset(capabilities)

    @property
    def volume(self):
        return self._volume

    @property
    def muted(self):
        return self._muted

    def open(self):
        if self.is_open:
            return self
        super().open()
        if self.session is not None and self.codec is None:
            self.codec = self.session.codec
        if self._power is not None:
            self._power(True)
        if self._set_hardware_volume is not None:
            self._set_hardware_volume(self._volume)
        if self._set_hardware_mute is not None:
            self._set_hardware_mute(self._muted)
        return self

    def set_volume(self, percent):
        self._volume = _clamp_percent(percent)
        if self.is_open and self._set_hardware_volume is not None:
            self._set_hardware_volume(self._volume)
        return self._volume

    def mute(self, value=True):
        self._muted = bool(value)
        if self.is_open and self._set_hardware_mute is not None:
            self._set_hardware_mute(self._muted)
        return self._muted

    def _prepare(self, buf):
        view = memoryview(buf)
        if len(view) % self.format.frame_size:
            raise ValueError("PCM buffer must contain complete frames")
        if self._set_hardware_volume is not None and not (
            self._muted and self._set_hardware_mute is None
        ):
            return view
        percent = 0 if self._muted else self._volume
        if percent == 100:
            return view
        if len(self._scratch) < len(view):
            self._scratch = bytearray(len(view))
        target = memoryview(self._scratch)[: len(view)]
        _scale_pcm(view, target, self.format, percent)
        return target

    def _write(self, buf):
        raise NotImplementedError("PCMOutput subclasses must implement _write")

    def _drain(self):
        return None

    async def _awrite(self, buf):
        count = self._write(buf)
        await _asleep(0)
        return count

    async def _adrain(self):
        result = self._drain()
        await _asleep(0)
        return result

    def write(self, buf):
        self.open()
        source = self._prepare(buf)
        written = 0
        while written < len(source):
            count = self._write(source[written:])
            if count is None:
                count = len(source) - written
            if count <= 0:
                raise OSError("audio stream made no write progress")
            written += count
        return len(buf)

    def drain(self):
        self.open()
        return self._drain()

    async def awrite(self, buf):
        self.open()
        source = self._prepare(buf)
        written = 0
        while written < len(source):
            count = await self._awrite(source[written:])
            if count is None:
                count = len(source) - written
            if count <= 0:
                raise OSError("audio stream made no write progress")
            written += count
        return len(buf)

    async def adrain(self):
        self.open()
        return await self._adrain()

    def close(self):
        if not self.is_open:
            return
        try:
            if self._set_hardware_mute is not None:
                self._set_hardware_mute(True)
            if self._power is not None:
                self._power(False)
        finally:
            super().close()


class PCMInput(_Device):
    """Raw PCM capture with normalized gain and async support.

    Subclasses implement :meth:`_readinto` (and optionally :meth:`_areadinto`).
    """

    kind = "pcm"
    direction = "in"

    def __init__(
        self,
        format,
        *,
        session=None,
        codec=None,
        set_hardware_gain=None,
        set_hardware_mute=None,
        power=None,
    ):
        super().__init__(session=session)
        self.format = format
        self.codec = codec
        self._set_hardware_gain = set_hardware_gain
        self._set_hardware_mute = set_hardware_mute
        self._power = power
        self._gain = 100
        self._muted = False
        capabilities = {"pcm", "capture", "gain", "mute"}
        capabilities.add("hardware-gain" if set_hardware_gain else "software-gain")
        self.capabilities = frozenset(capabilities)

    @property
    def gain(self):
        return self._gain

    @property
    def muted(self):
        return self._muted

    def open(self):
        if self.is_open:
            return self
        super().open()
        if self.session is not None and self.codec is None:
            self.codec = self.session.codec
        if self._power is not None:
            self._power(True)
        if self._set_hardware_gain is not None:
            self._set_hardware_gain(self._gain)
        if self._set_hardware_mute is not None:
            self._set_hardware_mute(self._muted)
        return self

    def set_gain(self, percent):
        self._gain = _clamp_percent(percent)
        if self.is_open and self._set_hardware_gain is not None:
            self._set_hardware_gain(self._gain)
        return self._gain

    def mute(self, value=True):
        self._muted = bool(value)
        if self.is_open and self._set_hardware_mute is not None:
            self._set_hardware_mute(self._muted)
        return self._muted

    def _finish_read(self, buf, count):
        count -= count % self.format.frame_size
        view = memoryview(buf)[:count]
        if self._muted:
            view[:] = bytes(count)
        elif self._set_hardware_gain is None and self._gain != 100:
            _scale_pcm(view, view, self.format, self._gain)
        return count

    def _readinto(self, buf):
        raise NotImplementedError("PCMInput subclasses must implement _readinto")

    async def _areadinto(self, buf):
        count = self._readinto(buf)
        await _asleep(0)
        return count

    def readinto(self, buf):
        self.open()
        if len(buf) % self.format.frame_size:
            raise ValueError("PCM buffer must hold complete frames")
        return self._finish_read(buf, self._readinto(buf))

    async def areadinto(self, buf):
        self.open()
        if len(buf) % self.format.frame_size:
            raise ValueError("PCM buffer must hold complete frames")
        return self._finish_read(buf, await self._areadinto(buf))

    def close(self):
        if not self.is_open:
            return
        try:
            if self._set_hardware_mute is not None:
                self._set_hardware_mute(True)
            if self._power is not None:
                self._power(False)
        finally:
            super().close()


class ToneOutput(_Device):
    """Frequency/duty output for PWM speakers and buzzers.

    Subclasses implement :meth:`_play` and :meth:`_stop`.
    """

    kind = "tone"
    direction = "out"

    def __init__(self, *, session=None, power=None):
        super().__init__(session=session)
        self._power = power
        self.capabilities = frozenset({"tone", "playback", "volume", "mute"})
        self._volume = 100
        self._muted = False

    def open(self):
        if self.is_open:
            return self
        super().open()
        if self._power is not None:
            self._power(True)
        return self

    @property
    def volume(self):
        return self._volume

    @property
    def muted(self):
        return self._muted

    def set_volume(self, percent):
        self._volume = _clamp_percent(percent)
        return self._volume

    def mute(self, value=True):
        self._muted = bool(value)
        if self._muted and self.is_open:
            self.stop()
        return self._muted

    def _play(self, frequency, level):
        raise NotImplementedError("ToneOutput subclasses must implement _play")

    def _stop(self):
        raise NotImplementedError("ToneOutput subclasses must implement _stop")

    def play(self, frequency, *, volume=None):
        self.open()
        level = self._volume if volume is None else _clamp_percent(volume)
        if self._muted:
            level = 0
        self._play(frequency, level)

    def stop(self):
        if not self.is_open:
            return
        self._stop()

    async def aplay(self, frequency, duration_ms):
        self.play(frequency)
        try:
            if hasattr(asyncio, "sleep_ms"):
                await asyncio.sleep_ms(duration_ms)
            else:
                await asyncio.sleep(duration_ms / 1000)
        finally:
            self.stop()

    def close(self):
        if self.is_open:
            self.stop()
            if self._power is not None:
                self._power(False)
        super().close()


__all__ = (
    "LATENCIES",
    "LOW_LATENCY_QUEUE_MS",
    "AudioFormat",
    "AudioSession",
    "PCMInput",
    "PCMOutput",
    "ToneOutput",
    "check_latency",
    "queue_bytes",
)
