"""WASAPI queued PCM backend for Windows CPython (via ``uwin32``).

Playback and capture use shared-mode ``IAudioClient`` with
``AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM``. There is no Python audio-thread
callback. Import fails unless ``uwin32`` loads.
"""

try:
    import asyncio
except ImportError:  # pragma: no cover
    try:
        import uasyncio as asyncio
    except ImportError:
        asyncio = None

import time

from audiodev import AudioFormat, PCMInput, PCMOutput, check_latency
import uwin32 as win

DEFAULT_PLAY_SAMPLES = 4096
DEFAULT_PLAY_QUEUE_MS = 2000
DEFAULT_COALESCE_MS = 100
PREBUFFER_MS = 100

_PLAY_PROFILES = {
    None: (DEFAULT_PLAY_SAMPLES, DEFAULT_PLAY_QUEUE_MS, DEFAULT_COALESCE_MS),
    "buffered": (DEFAULT_PLAY_SAMPLES, DEFAULT_PLAY_QUEUE_MS, DEFAULT_COALESCE_MS),
    "low": (512, 250, 20),
}

_CAPTURE_PROFILES = {
    None: (512, 500),
    "buffered": (512, 500),
    "low": (256, 100),
}


def _sleep_ms(milliseconds):
    try:
        from multimer import sleep_ms

        sleep_ms(milliseconds)
    except Exception:
        time.sleep(milliseconds / 1000)


async def _asleep_ms(milliseconds):
    await asyncio.sleep(milliseconds / 1000)


def _wave_format(fmt):
    return win.WAVEFORMATEX_pcm(fmt.rate, fmt.channels, fmt.bits)


class WinPCMOutput(PCMOutput):
    def __init__(
        self,
        fmt,
        *,
        device=None,
        samples=DEFAULT_PLAY_SAMPLES,
        queue_ms=DEFAULT_PLAY_QUEUE_MS,
        poll_ms=2,
        coalesce_ms=DEFAULT_COALESCE_MS,
        session=None,
    ):
        super().__init__(fmt, session=session)
        self.device_name = device
        self.samples = int(samples)
        self.queue_ms = int(queue_ms)
        self.poll_ms = int(poll_ms)
        self.coalesce_ms = int(coalesce_ms)
        self._bytes_per_second = fmt.rate * fmt.frame_size
        self._queue_limit = max(fmt.frame_size, self._bytes_per_second * self.queue_ms // 1000)
        self._coalesce_bytes = max(
            fmt.frame_size,
            self._bytes_per_second * self.coalesce_ms // 1000,
        )
        self._prebuffer_bytes = min(
            self._queue_limit // 4,
            max(fmt.frame_size, self._bytes_per_second * PREBUFFER_MS // 1000),
        )
        self._max_pending = 4 * self._queue_limit
        self._coalesce = bytearray()
        self._enumerator = None
        self._endpoint = None
        self._client = None
        self._render = None
        self._buffer_frames = 0
        self._started = False

    def _hw_queued(self):
        if not self._client:
            return 0
        return int(win.IAudioClient_GetCurrentPadding(self._client)) * self.format.frame_size

    def queued_size(self):
        return self._hw_queued() + len(self._coalesce)

    def is_active(self):
        return self.queued_size() > 0

    def clear(self):
        self._coalesce = bytearray()
        if self._client and self._started:
            try:
                win.IAudioClient_Stop(self._client)
                win.IAudioClient_Reset(self._client)
            except OSError:
                pass
            self._started = False

    def _open(self):
        win.CoInitializeEx()
        self._enumerator = win.MMDeviceEnumerator_Create()
        self._endpoint = win.IMMDeviceEnumerator_GetDefaultAudioEndpoint(
            self._enumerator, win.eRender
        )
        self._client = win.IMMDevice_Activate_IAudioClient(self._endpoint)
        wfx = _wave_format(self.format)
        win.IAudioClient_Initialize_shared_pcm(self._client, wfx, self.queue_ms)
        self._buffer_frames = win.IAudioClient_GetBufferSize(self._client)
        self._render = win.IAudioClient_GetService(self._client, win.IID_IAudioRenderClient)
        self._started = False

    def _close(self):
        if self._client and self._started:
            try:
                win.IAudioClient_Stop(self._client)
            except OSError:
                pass
        for punk in (self._render, self._client, self._endpoint, self._enumerator):
            if punk:
                win.IUnknown_Release(punk)
        self._render = self._client = self._endpoint = self._enumerator = None
        self._started = False
        self._coalesce = bytearray()

    def _available_frames(self):
        if not self._client:
            return 0
        padding = win.IAudioClient_GetCurrentPadding(self._client)
        return max(0, self._buffer_frames - padding)

    def _push_frames(self, data):
        frame = self.format.frame_size
        nbytes = len(data) - (len(data) % frame)
        if nbytes <= 0 or not self._render:
            return 0
        frames = nbytes // frame
        room = self._available_frames()
        if room <= 0:
            return 0
        frames = min(frames, room)
        ptr = win.IAudioRenderClient_GetBuffer(self._render, frames)
        win.memmove(ptr, data[: frames * frame], frames * frame)
        win.IAudioRenderClient_ReleaseBuffer(self._render, frames)
        return frames * frame

    def _start_if_primed(self, force=False):
        if self._started or not self._client:
            return
        queued = self._hw_queued()
        if queued <= 0:
            return
        if not force and queued < self._prebuffer_bytes:
            return
        win.IAudioClient_Start(self._client)
        self._started = True

    def _flush_coalesce(self, force=False):
        frame = max(1, self.format.frame_size)
        while self._coalesce:
            pending = len(self._coalesce)
            if not force and pending < self._coalesce_bytes:
                break
            take = pending if force else self._coalesce_bytes
            take -= take % frame
            if take <= 0:
                break
            if not force and self._hw_queued() + take > self._queue_limit:
                break
            written = self._push_frames(bytes(self._coalesce[:take]))
            if written <= 0:
                break
            self._coalesce[:written] = b""
        self._start_if_primed(force=force)

    def _write(self, buf):
        if not buf:
            return 0
        waited = 0
        while len(self._coalesce) >= self._max_pending and waited < 500:
            self._flush_coalesce(force=False)
            _sleep_ms(self.poll_ms)
            waited += self.poll_ms
        self._coalesce.extend(buf)
        self._flush_coalesce(force=False)
        return len(buf)

    def service(self):
        self._flush_coalesce(force=False)
        return self.queued_size()

    def _drain(self):
        self._flush_coalesce(force=True)
        waited = 0
        timeout_ms = 10000
        while self.queued_size() > 0 and waited < timeout_ms:
            self._flush_coalesce(force=True)
            _sleep_ms(self.poll_ms)
            waited += self.poll_ms
        return self.queued_size() == 0

    async def _awrite(self, buf):
        await _asleep_ms(0)
        while self._hw_queued() >= self._queue_limit:
            await _asleep_ms(self.poll_ms)
        return self._write(buf)

    async def _adrain(self):
        self._flush_coalesce(force=True)
        waited = 0
        timeout_ms = 10000
        while self.queued_size() > 0 and waited < timeout_ms:
            self._flush_coalesce(force=True)
            await _asleep_ms(self.poll_ms)
            waited += self.poll_ms
        return self.queued_size() == 0


class WinPCMInput(PCMInput):
    def __init__(
        self,
        fmt,
        *,
        device=None,
        samples=512,
        queue_ms=500,
        poll_ms=2,
        session=None,
    ):
        super().__init__(fmt, session=session)
        self.device_name = device
        self.samples = int(samples)
        self.queue_ms = int(queue_ms)
        self.poll_ms = int(poll_ms)
        self._enumerator = None
        self._endpoint = None
        self._client = None
        self._capture = None
        self._pending = bytearray()

    def queued_size(self):
        return len(self._pending)

    def _open(self):
        win.CoInitializeEx()
        self._enumerator = win.MMDeviceEnumerator_Create()
        self._endpoint = win.IMMDeviceEnumerator_GetDefaultAudioEndpoint(
            self._enumerator, win.eCapture
        )
        self._client = win.IMMDevice_Activate_IAudioClient(self._endpoint)
        wfx = _wave_format(self.format)
        win.IAudioClient_Initialize_shared_pcm(self._client, wfx, self.queue_ms)
        self._capture = win.IAudioClient_GetService(self._client, win.IID_IAudioCaptureClient)
        win.IAudioClient_Start(self._client)

    def _close(self):
        if self._client:
            try:
                win.IAudioClient_Stop(self._client)
            except OSError:
                pass
        for punk in (self._capture, self._client, self._endpoint, self._enumerator):
            if punk:
                win.IUnknown_Release(punk)
        self._capture = self._client = self._endpoint = self._enumerator = None
        self._pending = bytearray()

    def _pull(self):
        if not self._capture:
            return
        while True:
            packet = win.IAudioCaptureClient_GetNextPacketSize(self._capture)
            if packet <= 0:
                return
            ptr, frames, _flags = win.IAudioCaptureClient_GetBuffer(self._capture)
            nbytes = frames * self.format.frame_size
            if ptr and nbytes:
                self._pending.extend(win.string_at(ptr, nbytes))
            win.IAudioCaptureClient_ReleaseBuffer(self._capture, frames)

    def _readinto(self, buf):
        needed = len(buf)
        while len(self._pending) < self.format.frame_size:
            self._pull()
            if len(self._pending) < self.format.frame_size:
                _sleep_ms(self.poll_ms)
        self._pull()
        take = min(needed, len(self._pending))
        take -= take % self.format.frame_size
        view = memoryview(buf)
        view[:take] = self._pending[:take]
        self._pending[:take] = b""
        return take

    async def _areadinto(self, buf):
        needed = len(buf)
        while len(self._pending) < self.format.frame_size:
            self._pull()
            if len(self._pending) < self.format.frame_size:
                await _asleep_ms(self.poll_ms)
        self._pull()
        take = min(needed, len(self._pending))
        take -= take % self.format.frame_size
        view = memoryview(buf)
        view[:take] = self._pending[:take]
        self._pending[:take] = b""
        return take


def audio_out(
    format=None,
    *,
    device=None,
    latency=None,
    samples=None,
    queue_ms=None,
    coalesce_ms=None,
    poll_ms=2,
):
    """Create a WASAPI-backed :class:`PCMOutput`."""
    check_latency(latency)
    default_samples, default_queue_ms, default_coalesce_ms = _PLAY_PROFILES[latency]
    fmt = format or AudioFormat(16000, 2, 16)
    return WinPCMOutput(
        fmt,
        device=device,
        samples=default_samples if samples is None else samples,
        queue_ms=default_queue_ms if queue_ms is None else queue_ms,
        coalesce_ms=default_coalesce_ms if coalesce_ms is None else coalesce_ms,
        poll_ms=poll_ms,
    )


def audio_in(
    format=None,
    *,
    device=None,
    latency=None,
    samples=None,
    queue_ms=None,
    poll_ms=2,
):
    """Create a WASAPI-backed :class:`PCMInput`."""
    check_latency(latency)
    default_samples, default_queue_ms = _CAPTURE_PROFILES[latency]
    fmt = format or AudioFormat(16000, 1, 16)
    return WinPCMInput(
        fmt,
        device=device,
        samples=default_samples if samples is None else samples,
        queue_ms=default_queue_ms if queue_ms is None else queue_ms,
        poll_ms=poll_ms,
    )
