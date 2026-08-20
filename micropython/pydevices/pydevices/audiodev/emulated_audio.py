"""CI / no-hardware PCM: WAV files, waveform generator, in-memory loopback.

Never selected by :mod:`audiodev.auto`. Import this module explicitly.
"""

import math

from audiodev import AudioFormat, PCMInput, PCMOutput, queue_bytes

_WAVES = ("sine", "square", "noise", "silence")


def _u16(value):
    return int(value).to_bytes(2, "little")


def _u32(value):
    return int(value).to_bytes(4, "little")


def wav_header(fmt, data_length):
    """Build a 44-byte PCM RIFF/WAVE header for *fmt* and *data_length* bytes."""
    byte_rate = fmt.rate * fmt.frame_size
    block_align = fmt.frame_size
    return (
        b"RIFF"
        + _u32(36 + data_length)
        + b"WAVEfmt "
        + _u32(16)
        + _u16(1)
        + _u16(fmt.channels)
        + _u32(fmt.rate)
        + _u32(byte_rate)
        + _u16(block_align)
        + _u16(fmt.bits)
        + b"data"
        + _u32(data_length)
    )


def parse_pcm_wav(data):
    """Return ``(AudioFormat, pcm_bytes)`` from a PCM WAV buffer."""
    if len(data) < 44 or data[0:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("Expected RIFF/WAVE data")

    pos = 12
    total = len(data)
    channels = None
    rate = None
    bits = None
    fmt_tag = None
    payload = None

    while pos + 8 <= total:
        chunk_id = data[pos : pos + 4]
        chunk_len = int.from_bytes(data[pos + 4 : pos + 8], "little")
        pos += 8
        end = pos + chunk_len
        if end > total:
            end = total

        if chunk_id == b"fmt ":
            chunk = data[pos:end]
            if len(chunk) < 16:
                raise ValueError("WAV fmt chunk is too short")
            fmt_tag = int.from_bytes(chunk[0:2], "little")
            channels = int.from_bytes(chunk[2:4], "little")
            rate = int.from_bytes(chunk[4:8], "little")
            bits = int.from_bytes(chunk[14:16], "little")
        elif chunk_id == b"data":
            payload = data[pos:end]
            break

        pos = end + (chunk_len % 2)

    if payload is None:
        raise ValueError("WAV data chunk not found")
    if fmt_tag != 1:
        raise ValueError("Only PCM WAV is supported")
    if channels is None or rate is None or bits is None:
        raise ValueError("WAV fmt metadata is incomplete")

    signed = bits != 8
    return AudioFormat(rate, channels, bits, signed=signed), bytes(payload)


class WavPCMOutput(PCMOutput):
    """Write interleaved PCM into a WAV file; finalize sizes on close."""

    def __init__(self, path, format):
        if not isinstance(format, AudioFormat):
            raise TypeError("format must be an AudioFormat")
        super().__init__(format)
        self.path = path
        self._file = None
        self._data_length = 0

    def _open(self):
        if self._file is not None:
            return
        self._file = open(self.path, "wb")
        self._file.write(wav_header(self.format, 0))
        self._data_length = 0

    def _write(self, buf):
        view = memoryview(buf)
        self._file.write(view)
        self._data_length += len(view)
        return len(view)

    def _drain(self):
        if self._file is not None:
            self._file.flush()

    def _close(self):
        if self._file is None:
            return
        try:
            self._file.seek(0)
            self._file.write(wav_header(self.format, self._data_length))
            self._file.flush()
        finally:
            self._file.close()
            self._file = None


class WavPCMInput(PCMInput):
    """Read interleaved PCM from a WAV file; ``readinto`` returns 0 at EOF."""

    def __init__(self, path):
        with open(path, "rb") as handle:
            data = handle.read()
        fmt, _pcm = parse_pcm_wav(data)
        super().__init__(fmt)
        self.path = path
        self._pcm = b""
        self._offset = 0

    def _open(self):
        with open(self.path, "rb") as handle:
            data = handle.read()
        _fmt, self._pcm = parse_pcm_wav(data)
        self._offset = 0

    def _readinto(self, buf):
        remaining = len(self._pcm) - self._offset
        if remaining <= 0:
            return 0
        count = min(len(buf), remaining)
        buf[:count] = self._pcm[self._offset : self._offset + count]
        self._offset += count
        return count

    def _close(self):
        self._pcm = b""
        self._offset = 0


class NullPCMOutput(PCMOutput):
    """Discard PCM (write-path tests that must not touch a host sink)."""

    def __init__(self, format):
        super().__init__(format)
        self.written = 0

    def _write(self, buf):
        n = len(buf)
        self.written += n
        return n


class LoopbackBuffer:
    """Shared in-memory PCM queue for a loopback pair."""

    def __init__(self, format, *, queue_ms=None):
        if not isinstance(format, AudioFormat):
            raise TypeError("format must be an AudioFormat")
        self.format = format
        limit = queue_bytes(format, None, queue_ms, default=format.rate * format.frame_size)
        self.limit = max(format.frame_size, int(limit))
        self._pending = bytearray()

    def write(self, buf):
        view = memoryview(buf)
        self._pending.extend(view)
        overflow = len(self._pending) - self.limit
        if overflow > 0:
            drop = overflow - (overflow % self.format.frame_size)
            if drop > 0:
                self._pending[:drop] = b""
        return len(view)

    def readinto(self, buf):
        count = min(len(buf), len(self._pending))
        count -= count % self.format.frame_size
        if count <= 0:
            return 0
        buf[:count] = self._pending[:count]
        self._pending[:count] = b""
        return count

    def queued_size(self):
        return len(self._pending)

    def clear(self):
        self._pending = bytearray()


class LoopbackPCMOutput(PCMOutput):
    """Enqueue PCM into a :class:`LoopbackBuffer`."""

    def __init__(self, buffer):
        super().__init__(buffer.format)
        self._buffer = buffer

    def _write(self, buf):
        return self._buffer.write(buf)

    def queued_size(self):
        return self._buffer.queued_size()

    def is_active(self):
        return self._buffer.queued_size() > 0

    def clear(self):
        self._buffer.clear()


class LoopbackPCMInput(PCMInput):
    """Dequeue PCM from a :class:`LoopbackBuffer` (0 when empty)."""

    def __init__(self, buffer):
        super().__init__(buffer.format)
        self._buffer = buffer

    def _readinto(self, buf):
        return self._buffer.readinto(buf)

    def queued_size(self):
        return self._buffer.queued_size()

    def is_active(self):
        return self._buffer.queued_size() > 0

    def clear(self):
        self._buffer.clear()


def loopback_pair(format, *, queue_ms=None):
    """Return ``(LoopbackPCMOutput, LoopbackPCMInput)`` sharing one buffer."""
    buffer = LoopbackBuffer(format, queue_ms=queue_ms)
    return LoopbackPCMOutput(buffer), LoopbackPCMInput(buffer)


def _sample_value(wave, phase, amplitude, bits, signed):
    if wave == "silence":
        unit = 0.0
    elif wave == "square":
        unit = 1.0 if phase < 0.5 else -1.0
    elif wave == "noise":
        # xorshift-ish from phase so tests are deterministic per frame index.
        raw = int(phase * 65536.0) & 0xFFFF
        raw ^= (raw << 7) & 0xFFFF
        raw ^= raw >> 9
        unit = (raw / 32768.0) - 1.0
    else:
        unit = math.sin(2.0 * math.pi * phase)
    peak = (1 << (bits - 1)) - 1 if signed else (1 << bits) - 1
    midpoint = 0 if signed else 1 << (bits - 1)
    scaled = int(unit * amplitude * peak / 100.0)
    if signed:
        return scaled
    return midpoint + scaled


class GeneratorPCMInput(PCMInput):
    """Endless or timed waveform as a :class:`PCMInput` (no microphone)."""

    def __init__(
        self,
        format,
        *,
        wave="sine",
        frequency=440,
        duration_ms=None,
        amplitude=100,
    ):
        if wave not in _WAVES:
            raise ValueError("unknown wave {!r}; expected one of {}".format(wave, _WAVES))
        super().__init__(format)
        self.wave = wave
        self.frequency = float(frequency)
        self.amplitude = int(amplitude)
        self.duration_ms = duration_ms
        self._frame = 0
        self._remaining = None

    def _open(self):
        self._frame = 0
        if self.duration_ms is None:
            self._remaining = None
        else:
            self._remaining = self.format.rate * int(self.duration_ms) // 1000

    def _close(self):
        self._remaining = None

    def _readinto(self, buf):
        fmt = self.format
        frames = len(buf) // fmt.frame_size
        if self._remaining is not None:
            if self._remaining <= 0:
                return 0
            if frames > self._remaining:
                frames = self._remaining
        width = fmt.bits // 8
        inv_rate = 1.0 / float(fmt.rate)
        offset = 0
        for _ in range(frames):
            phase = (self._frame * self.frequency * inv_rate) % 1.0
            value = _sample_value(
                self.wave, phase, self.amplitude, fmt.bits, fmt.signed
            )
            sample = (value % (1 << fmt.bits)).to_bytes(width, fmt.byteorder)
            for _ch in range(fmt.channels):
                buf[offset : offset + width] = sample
                offset += width
            self._frame += 1
        if self._remaining is not None:
            self._remaining -= frames
        return frames * fmt.frame_size


def audio_out(format=None, *, path=None, loopback=None, discard=False, queue_ms=None):
    """Standalone emulated playback: WAV path, loopback buffer, or discard."""
    if discard:
        fmt = format or AudioFormat(16000, 1, 16)
        return NullPCMOutput(fmt)
    if loopback is not None:
        if format is not None and format != loopback.format:
            raise ValueError("loopback format mismatch")
        return LoopbackPCMOutput(loopback)
    if path is not None:
        if format is None:
            raise TypeError("WAV audio_out requires format")
        return WavPCMOutput(path, format)
    raise ValueError("emulated audio_out needs path, loopback, or discard=True")


def audio_in(
    format=None,
    *,
    path=None,
    loopback=None,
    wave=None,
    frequency=440,
    duration_ms=None,
    amplitude=100,
):
    """Standalone emulated capture: WAV path, loopback buffer, or generator."""
    if path is not None:
        return WavPCMInput(path)
    if loopback is not None:
        if format is not None and format != loopback.format:
            raise ValueError("loopback format mismatch")
        return LoopbackPCMInput(loopback)
    if wave is not None:
        fmt = format or AudioFormat(16000, 1, 16)
        return GeneratorPCMInput(
            fmt,
            wave=wave,
            frequency=frequency,
            duration_ms=duration_ms,
            amplitude=amplitude,
        )
    raise ValueError("emulated audio_in needs path, loopback, or wave")
