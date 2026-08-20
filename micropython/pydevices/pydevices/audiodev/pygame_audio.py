"""pygame-ce playback and capture backend for the portable :mod:`audiodev` contract.

Uses **pygame's own SDL** only (never ``usdl2`` / system libSDL2):

- **Playback:** ``SDL_QueueAudio`` via ctypes against pygame-ce's bundled
  ``libSDL2`` — no ``pygame.mixer``, no Python audio callback (avoids the
  GIL+pause deadlock that freezes the UI under WSLg).
- **Capture:** ``pygame._sdl2.AudioDevice`` (callback), with async close.

Mixing SDL libraries is the one thing that must not change: pygame-ce links its
own ``libSDL2``, and driving pygame's devices through ``usdl2``'s copy means two
SDL states in one process. Load the bundled library (:func:`_pygame_sdl`) or use
``sdl2_audio`` instead — never both against the same device.

Before simplifying playback
---------------------------

:class:`PygamePCMOutput` deliberately mirrors ``sdl2_audio.SDLPCMOutput``
mechanism for mechanism: rate-based stall detection, a hardware-only prebuffer
gate, an off-thread rebuild with a settle gap, and a shadow buffer for lossless
recovery. Each exists because the simpler version measurably failed. That module's
docstring records what each one prevents, and ``README.md`` in this directory has
the full account.

Keep the two in step. When a fix lands in one backend it belongs in the other,
because the failure they work around is in the host's audio sink, not in either
library.
"""

import asyncio
import collections
import os
import sys
import threading
import time
from pathlib import Path

from audiodev import AudioFormat, PCMInput, PCMOutput, check_latency

try:
    import ctypes
    from ctypes import c_char_p, c_int, c_uint8, c_uint16, c_uint32, c_void_p
except ImportError:  # MicroPython
    ctypes = None


def _sleep_ms(milliseconds):
    time.sleep(milliseconds / 1000)


async def _asleep_ms(milliseconds):
    await asyncio.sleep(milliseconds / 1000)


def _ensure_pygame():
    import pygame

    if not pygame.get_init():
        pygame.init()
    # This backend drives SDL audio directly, so ``pygame.mixer`` would hold a
    # second, unused output device open. Under WSLg two concurrent streams make
    # the PulseAudio RDP sink stop consuming after ~30s (playback wedges), so
    # release the mixer device we never use.
    try:
        if pygame.mixer.get_init():
            pygame.mixer.quit()
    except Exception:
        pass
    return pygame


def _pygame_audio_format(fmt):
    """Map :class:`AudioFormat` to a ``pygame._sdl2.audio`` format constant."""
    from pygame._sdl2 import audio as sdl_audio

    if fmt.bits == 8:
        return sdl_audio.AUDIO_S8 if fmt.signed else sdl_audio.AUDIO_U8
    if fmt.bits == 16:
        if fmt.byteorder == "little":
            return sdl_audio.AUDIO_S16LSB if fmt.signed else sdl_audio.AUDIO_U16LSB
        return sdl_audio.AUDIO_S16MSB if fmt.signed else sdl_audio.AUDIO_U16MSB
    if fmt.bits == 32:
        if fmt.byteorder == "little":
            return sdl_audio.AUDIO_S32LSB if fmt.signed else sdl_audio.AUDIO_U32LSB
        return sdl_audio.AUDIO_S32MSB if fmt.signed else sdl_audio.AUDIO_U32MSB
    raise ValueError("unsupported pygame audio format %r" % (fmt,))


# SDL_AudioFormat integers (match pygame._sdl2 / SDL2 headers).
_AUDIO_U8 = 0x0008
_AUDIO_S8 = 0x8008
_AUDIO_U16LSB = 0x0010
_AUDIO_S16LSB = 0x8010
_AUDIO_U16MSB = 0x1010
_AUDIO_S16MSB = 0x9010
_AUDIO_S32LSB = 0x8020
_AUDIO_S32MSB = 0x9020

_SDL = None

# SDL device period (``SDL_AudioSpec.samples``) for playback. Writes are queued
# rather than callback driven, so device latency is not important.
DEFAULT_PLAY_SAMPLES = 4096

# Playback cushion held in SDL's queue.
DEFAULT_PLAY_QUEUE_MS = 2000

# PCM to accumulate in the *software* buffer before handing a piece to SDL.
DEFAULT_COALESCE_MS = 100

# Playback settings per ``audiodev`` latency profile; see the matching table in
# sdl2_audio.py for why "low" uses these numbers. Only values a caller left unset
# are taken from here.
_PLAY_PROFILES = {
    None: (DEFAULT_PLAY_SAMPLES, DEFAULT_PLAY_QUEUE_MS, DEFAULT_COALESCE_MS),
    "buffered": (DEFAULT_PLAY_SAMPLES, DEFAULT_PLAY_QUEUE_MS, DEFAULT_COALESCE_MS),
    "low": (512, 250, 20),
}

# Capture profiles: period and queue only.
_CAPTURE_PROFILES = {
    None: (512, 500),
    "buffered": (512, 500),
    "low": (256, 100),
}

# PCM to accumulate in the *device* queue before unpausing a freshly primed
# device. Lowering this trades startup latency for the risk that the sink stops
# asking for data; it is capped per stream so it can never exceed the caller's
# fill watermark (see ``_prebuffer_bytes``).
PREBUFFER_MS = 500

# Window over which playback progress is measured, and the fraction of realtime
# below which the device counts as wedged.
#
# WSLg's PulseAudio RDP sink degrades after roughly a minute of continuous
# playback: it keeps taking data, but at 5-30% of realtime, while SDL still
# reports the device as playing. It is not specific to this backend (plain
# ``paplay`` of a 150s file stalls the same way while a 60s file completes) and
# closing and reopening the device is the only thing that restores realtime
# playback -- pausing and unpausing the same device does not. Because the sink
# trickles rather than freezing, the test has to be a rate over a window; "no
# progress at all for N ms" almost never becomes true. Remove this recovery once
# hosts can sustain long playback.
#
# Both values are a compromise between false positives and slow recovery, so
# move them only with rate measurements in hand: a shorter window or a higher
# ratio starts firing on healthy playback (period quantization alone can read
# well under realtime over a short span), while a longer window or lower ratio
# leaves audible slow-motion audio before recovery kicks in.
STALL_WINDOW_MS = 1500
STALL_RATIO = 0.5

# Spacing of the progress samples that make up the window.
STALL_SAMPLE_MS = 100

# Skip one window after a reopen so the measurement starts on steady state
# rather than on the device's ramp-up.
RECOVER_GRACE_MS = 1500

# Gap between closing and reopening during recovery. Reopening immediately gets
# the same wedged sink back -- measurably so: those opens return in ~3ms and
# re-wedge within seconds, while opens that follow a settled close take ~1.3s
# (the host building a new sink) and then run normally. The rebuild is off the
# caller's thread, so this delay costs only silence, not responsiveness.
RECOVER_SETTLE_MS = 800


def _sdl_format_int(fmt):
    """Map :class:`AudioFormat` to an ``SDL_AudioFormat`` integer.

    Raises for combinations SDL2 has no format for, rather than substituting the
    nearest one: a silently wrong format is decoded as noise at the wrong speed,
    which is far harder to recognize than an exception at open time.
    """
    if fmt.bits == 8:
        return _AUDIO_S8 if fmt.signed else _AUDIO_U8
    if fmt.bits == 16:
        if fmt.byteorder == "little":
            return _AUDIO_S16LSB if fmt.signed else _AUDIO_U16LSB
        return _AUDIO_S16MSB if fmt.signed else _AUDIO_U16MSB
    if fmt.bits == 32:
        # SDL2 defines only S32 and F32 at 32 bits -- there is no AUDIO_U32.
        if not fmt.signed:
            raise ValueError("SDL2 has no unsigned 32-bit format: %r" % (fmt,))
        return _AUDIO_S32LSB if fmt.byteorder == "little" else _AUDIO_S32MSB
    raise ValueError("unsupported pygame audio format %r" % (fmt,))


def _pygame_sdl():
    """Load the libSDL2 that pygame-ce already linked (not system usdl2)."""
    global _SDL
    if _SDL is not None:
        return _SDL
    if ctypes is None:
        raise OSError("pygame_audio QueueAudio needs ctypes (CPython)")
    _ensure_pygame()
    import pygame

    root = Path(pygame.__file__).resolve().parent
    libs = root.parent / "pygame_ce.libs"
    candidates = sorted(libs.glob("libSDL2-*.so*")) if libs.is_dir() else []
    if not candidates:
        # Windows / alternate layout
        candidates = sorted(root.glob("**/libSDL2*.dll")) + sorted(
            (root.parent / "pygame_ce.libs").glob("SDL2*.dll")
            if (root.parent / "pygame_ce.libs").is_dir()
            else []
        )
    if not candidates:
        raise OSError("could not find pygame-ce bundled libSDL2")
    lib = ctypes.CDLL(str(candidates[0]))

    class SDL_AudioSpec(ctypes.Structure):
        _fields_ = [
            ("freq", c_int),
            ("format", c_uint16),
            ("channels", c_uint8),
            ("silence", c_uint8),
            ("samples", c_uint16),
            ("padding", c_uint16),
            ("size", c_uint32),
            ("callback", c_void_p),
            ("userdata", c_void_p),
        ]

    lib.SDL_InitSubSystem.argtypes = [c_uint32]
    lib.SDL_InitSubSystem.restype = c_int
    lib.SDL_OpenAudioDevice.argtypes = [
        c_char_p,
        c_int,
        ctypes.POINTER(SDL_AudioSpec),
        ctypes.POINTER(SDL_AudioSpec),
        c_int,
    ]
    lib.SDL_OpenAudioDevice.restype = c_uint32
    lib.SDL_CloseAudioDevice.argtypes = [c_uint32]
    lib.SDL_CloseAudioDevice.restype = None
    lib.SDL_PauseAudioDevice.argtypes = [c_uint32, c_int]
    lib.SDL_PauseAudioDevice.restype = None
    lib.SDL_QueueAudio.argtypes = [c_uint32, c_void_p, c_uint32]
    lib.SDL_QueueAudio.restype = c_int
    lib.SDL_GetQueuedAudioSize.argtypes = [c_uint32]
    lib.SDL_GetQueuedAudioSize.restype = c_uint32
    lib.SDL_ClearQueuedAudio.argtypes = [c_uint32]
    lib.SDL_ClearQueuedAudio.restype = None
    lib.SDL_GetError.argtypes = []
    lib.SDL_GetError.restype = c_char_p

    lib.SDL_AudioSpec = SDL_AudioSpec
    lib.SDL_INIT_AUDIO = 0x00000010
    _SDL = lib
    return lib


def _close_audiodevice_async(dev):
    """``AudioDevice.close`` may futex-deadlock — pause sync, close on a daemon.

    Do not make this synchronous. The pause takes effect immediately, which is
    all a caller actually needs (capture stops), while ``close`` itself can block
    indefinitely inside SDL waiting on its callback thread. The daemon thread
    means a stuck close cannot keep the process alive either.
    """
    if dev is None:
        return
    try:
        dev.pause(1)
    except Exception:
        pass

    def _close_native():
        try:
            dev.close()
        except Exception:
            pass

    threading.Thread(
        target=_close_native, name="pygame-audiodevice-close", daemon=True
    ).start()


class PygamePCMOutput(PCMOutput):
    """PCM playback via pygame's SDL ``QueueAudio`` (no mixer, no py callback).

    PCM travels through two buffers: writes land in ``_coalesce`` (software) and
    are handed to SDL in ~100ms pieces up to ``_queue_limit`` (hardware).
    :meth:`queued_size` reports both, so a caller can treat "queued_size() == 0"
    as end of playback without knowing which buffer holds what.

    Callers must call :meth:`service` from their tick. Without it, a partial
    write can sit in ``_coalesce`` unqueued and a wedged device is never noticed.
    """

    def __init__(
        self,
        fmt,
        *,
        samples=DEFAULT_PLAY_SAMPLES,
        poll_ms=2,
        queue_ms=DEFAULT_PLAY_QUEUE_MS,
        coalesce_ms=DEFAULT_COALESCE_MS,
    ):
        super().__init__(fmt)
        # ~2s HW QueueAudio cushion: moonshine sentence synth often exceeds
        # the old 400ms limit, which underruns to silence between utterances.
        self.samples = int(samples)
        self.poll_ms = int(poll_ms)
        self._bytes_per_second = fmt.rate * fmt.frame_size
        self._queue_limit = max(
            fmt.frame_size,
            self._bytes_per_second * int(queue_ms) // 1000,
        )
        self._coalesce = bytearray()
        self.coalesce_ms = int(coalesce_ms)
        self._coalesce_bytes = max(
            fmt.frame_size,
            self._bytes_per_second * self.coalesce_ms // 1000,
        )
        # Do not start the device on a nearly empty queue: starting on ~40ms and
        # then starving it makes PulseAudio's RDP sink stop asking for data.
        # Kept well under the caller's fill watermark so the pump cannot block
        # while we are still paused.
        self._prebuffer_bytes = min(
            self._queue_limit // 4,
            max(fmt.frame_size, self._bytes_per_second * PREBUFFER_MS // 1000),
        )
        self.device = 0
        self._prime_pause = True
        self.channel = None  # debug probes
        self.mode = "queue"
        period_bytes = self.samples * fmt.frame_size
        period_ms = 1000 * self.samples // max(1, fmt.rate)
        # Long enough that period quantization cannot look like a slow sink: a
        # healthy device delivers whole periods, so a short window can read well
        # under realtime purely from where the period boundaries fall.
        self._stall_window_ms = max(STALL_WINDOW_MS, 6 * period_ms)
        self._min_rate = int(self._bytes_per_second * STALL_RATIO)
        # Below this the queue may simply be running dry, which says nothing
        # about the device.
        self._min_depth_bytes = 2 * period_bytes
        # Backstop for callers that ignore ``queued_size()`` backpressure.
        self._max_pending = 4 * self._queue_limit
        # Must cover every byte SDL can still hold, or a rebuild cannot restore
        # the whole unplayed queue.
        self._shadow_limit = self._queue_limit + self._coalesce_bytes
        self._lock = threading.Lock()
        self._recycling = False
        # Cumulative bytes handed to SDL. Progress is measured as
        # ``_queued_total - queued``, not as a drop in queue depth: a caller that
        # tops the queue up replaces each consumed period before the next check
        # sees it, so depth alone never falls while playback is healthy.
        self._queued_total = 0
        # Trailing (timestamp, consumed) samples spanning ``_stall_window_ms``.
        self._samples = []
        self._grace_until = 0.0
        # Copy of the most recently queued PCM (never more than one full device
        # queue). A recycle discards whatever SDL still held, so the unplayed
        # tail is re-queued from here instead of being dropped.
        self._shadow = bytearray()
        self.recycles = 0
        self.lost_bytes = 0
        self.requeued_bytes = 0

    def _open(self):
        self._open_device()

    def _open_device(self):
        """Open the device **paused** and reset progress accounting.

        Opening paused is not an optimization: the device must not start on the
        first small chunk of a flush (see :meth:`_unpause_if_primed`). Progress
        state is per-device, so ``_queued_total`` and the rate samples reset here
        -- carrying them across a reopen would read as a huge instant stall.
        """
        if self.device:
            return self
        sdl = _pygame_sdl()
        if sdl.SDL_InitSubSystem(sdl.SDL_INIT_AUDIO) != 0:
            err = sdl.SDL_GetError()
            raise OSError(err.decode() if err else "SDL_InitSubSystem AUDIO failed")
        spec = sdl.SDL_AudioSpec(
            self.format.rate,
            _sdl_format_int(self.format),
            self.format.channels,
            0,
            max(64, int(self.samples)),
            0,
            0,
            None,  # NULL callback → QueueAudio mode
            None,
        )
        obtained = sdl.SDL_AudioSpec()
        self.device = sdl.SDL_OpenAudioDevice(
            None,
            0,
            ctypes.byref(spec),
            ctypes.byref(obtained),
            0,  # allowed_changes=0 — pin format
        )
        if not self.device:
            err = sdl.SDL_GetError()
            raise OSError(err.decode() if err else "SDL_OpenAudioDevice failed")
        self._prime_pause = True
        self._queued_total = 0
        del self._samples[:]
        sdl.SDL_PauseAudioDevice(self.device, 1)
        return self

    def _hw_queued(self):
        """Bytes SDL still holds. The only trustworthy measure of playback."""
        if not self.device:
            return 0
        return int(_pygame_sdl().SDL_GetQueuedAudioSize(self.device))

    def queued_size(self):
        """Bytes still waiting to play, including what has not been handed to SDL.

        Both buffers count, so audio parked in ``_coalesce`` during a rebuild is
        not mistaken for silence. Use :meth:`_hw_queued` instead when the
        question is what the *device* is doing.
        """
        return self._hw_queued() + len(self._coalesce)

    def is_active(self):
        """True while PCM is still queued anywhere.

        Deliberately ignores pause state. After the first unpause
        ``_prime_pause`` stays False for the life of the device, so reading it as
        "playing" pinned this True forever and hung callers waiting for idle.
        """
        return self.queued_size() > 0

    def _unpause_if_primed(self, force=False):
        """Start playback once ``_prebuffer_bytes`` are queued.

        ``force`` starts on whatever is queued — used when the caller has said
        there is no more PCM coming (short sounds, flush, drain), so a 40ms beep
        still plays.

        The gate is ``_hw_queued()``, not ``queued_size()``. Counting software
        bytes here is the single easiest way to reintroduce the wedge this whole
        module works around: after a rebuild the re-queued tail satisfies the
        threshold instantly, so the device starts nearly empty and dies again.
        """
        if not self.device or not self._prime_pause:
            return
        # Only what SDL holds counts: starting on a nearly empty device queue
        # starves it immediately, which is the very thing PREBUFFER_MS avoids.
        queued = self._hw_queued()
        if queued <= 0:
            return
        if not force and queued < self._prebuffer_bytes:
            return
        sdl = _pygame_sdl()
        sdl.SDL_PauseAudioDevice(self.device, 0)
        self._prime_pause = False
        del self._samples[:]

    def _queue_bytes(self, buf):
        """Hand ``buf`` to SDL, remembering it so a recycle can re-queue it.

        The copy kept in ``_shadow`` is what makes recovery lossless: SDL discards
        its queue on close, so the unplayed tail can only come from here.

        Never waits for room. Backpressure belongs to the callers that can afford
        it -- :meth:`_flush_coalesce` simply stops early, and :meth:`awrite` awaits
        instead of sleeping. A wait here would block whichever thread or event
        loop happened to be flushing.
        """
        sdl = _pygame_sdl()
        data = bytes(buf)
        with self._lock:
            if not self.device:
                self._open_device()
            rc = sdl.SDL_QueueAudio(self.device, data, len(data))
            if rc == 0:
                self._queued_total += len(data)
                self._shadow.extend(data)
                if len(self._shadow) > self._shadow_limit:
                    # Slice assignment: MP/CP bytearrays cannot ``del``.
                    self._shadow[: len(self._shadow) - self._shadow_limit] = b""
        if rc != 0:
            err = sdl.SDL_GetError()
            raise OSError(err.decode() if err else "SDL_QueueAudio failed")

    def _flush_coalesce(self, force=False):
        """Move buffered PCM into SDL in period-sized pieces.

        ``force`` means the caller has no more PCM: queue everything and start it
        now, regardless of the prebuffer threshold.

        Without ``force`` this never blocks and never overfills: it stops at
        ``_queue_limit`` and leaves the rest buffered, because the caller may be
        a UI thread. :meth:`_unpause_if_primed` is called once at the end rather
        than per piece, so a large flush cannot start the device on its first
        chunk.
        """
        frame = max(1, self.format.frame_size)
        while self._coalesce and not self._recycling:
            pending = len(self._coalesce)
            if not force and pending < self._coalesce_bytes:
                break
            take = pending if force else self._coalesce_bytes
            take -= take % frame
            if take <= 0:
                break
            if not force and self._hw_queued() + take > self._queue_limit:
                # Full: keep the rest buffered rather than blocking the caller,
                # which may be the UI thread.
                break
            piece = bytes(self._coalesce[:take])
            # Slice assignment: MP/CP bytearrays cannot ``del``.
            self._coalesce[:take] = b""
            self._queue_bytes(piece)
        # Start (or not) once, after everything that fits has been queued, so the
        # device never begins on the first small chunk of a large flush.
        self._unpause_if_primed(force=force)

    def _write(self, buf):
        """Accept PCM, queueing as much as fits. Always consumes all of ``buf``.

        Safe to call during a rebuild -- the data is buffered and queued in order
        behind the re-queued tail once the device is back, so a caller does not
        have to know a recovery is in progress. ``_max_pending`` is only a
        backstop against callers that ignore :meth:`queued_size` entirely.
        """
        if not self._recycling:
            self._open_device()
        if not buf:
            return 0
        waited = 0
        while len(self._coalesce) >= self._max_pending and waited < 500:
            _sleep_ms(self.poll_ms)
            waited += self.poll_ms
        # While the device is being rebuilt the PCM just accumulates here; the
        # next service tick queues it in order behind the re-queued tail.
        self._coalesce.extend(buf)
        if self._recycling:
            return len(buf)
        self._flush_coalesce(force=False)
        return len(buf)

    async def _awrite(self, buf):
        """Async :meth:`write`: awaits backpressure instead of sleeping through it.

        Yields once up front even when there is room. :meth:`write`'s bounded
        sleeps would otherwise stall the whole event loop, and a task looping on
        ``awrite`` alone would never give the loop a chance to run anything else
        -- including its own cancellation.
        """
        if not buf:
            return 0
        await _asleep_ms(0)
        if not self._recycling:
            self._open_device()
        waited = 0
        while len(self._coalesce) >= self._max_pending and waited < 500:
            await _asleep_ms(self.poll_ms)
            waited += self.poll_ms
        self._coalesce.extend(buf)
        if not self._recycling:
            self._flush_coalesce(force=False)
        return len(buf)

    def _check_stall(self):
        """Recycle the device when it plays back well below realtime.

        Measures bytes actually consumed per second over ``_stall_window_ms``,
        and only while the queue is deep enough that a slow rate can only be the
        device rather than a caller that stopped writing.

        Consumption is ``_queued_total - _hw_queued()``, a monotonic total. The
        tempting version -- "has the queue depth stopped falling?" -- does not
        work: the pump refills each consumed period before the next check, so
        depth stays flat during healthy playback and during a total stall alike.
        """
        if not self.device or self._prime_pause:
            return
        now = time.time()
        if now < self._grace_until:
            del self._samples[:]
            return
        hw = self._hw_queued()
        consumed = self._queued_total - hw
        if hw < self._min_depth_bytes:
            del self._samples[:]
            return
        samples = self._samples
        if not samples or (now - samples[-1][0]) * 1000 >= STALL_SAMPLE_MS:
            samples.append((now, consumed))
        while len(samples) > 1 and (now - samples[1][0]) * 1000 >= self._stall_window_ms:
            del samples[0]
        span = now - samples[0][0]
        if span * 1000 < self._stall_window_ms:
            return
        rate = int((consumed - samples[0][1]) / span)
        if rate >= self._min_rate:
            return
        del samples[:]
        self._recycle_device(stalled_bytes=hw, rate=rate)

    def _recycle_device(self, stalled_bytes=0, rate=None):
        """Rebuild the device, keeping the audio SDL had not played yet.

        Closing and reopening blocks for over a second on some hosts, so it runs
        on a worker thread: the caller may be driving a UI. The unplayed tail is
        pushed back to the front of the coalesce buffer, which keeps it ahead of
        anything written during the rebuild and keeps it visible to
        ``queued_size()`` so callers do not mistake the gap for end of playback.
        """
        if self._recycling:
            return
        stuck = min(int(stalled_bytes), len(self._shadow))
        tail = bytes(self._shadow[-stuck:]) if stuck else b""
        self.lost_bytes += int(stalled_bytes) - len(tail)
        self.requeued_bytes += len(tail)
        self.recycles += 1
        self._recycling = True
        del self._samples[:]
        if tail:
            self._coalesce[:0] = tail
        threading.Thread(
            target=self._rebuild_device, name="pygame-audio-rebuild", daemon=True
        ).start()

    def _rebuild_device(self, attempts=3):
        """Close, settle, reopen. Runs on the recycle worker thread.

        The ``RECOVER_SETTLE_MS`` gap is the point of this function: without it
        the host hands back the same wedged sink. Reopening can still fail while
        the sink is busy, so it retries.

        Never raises. Nothing is waiting to catch this, and a half-finished
        rebuild is worse than a reported failure: with no device, :meth:`service`
        does nothing, so any PCM left buffered would keep :meth:`is_active` true
        forever and hang callers waiting for playback to end. If no device can be
        had, that audio is dropped and counted.
        """
        error = None
        try:
            self._close_device()
            for _ in range(attempts):
                _sleep_ms(RECOVER_SETTLE_MS)
                try:
                    self._open_device()
                    return
                except Exception as exc:
                    error = exc
            self.lost_bytes += len(self._coalesce)
            self._coalesce[:] = b""
            self._shadow = bytearray()
            print("[pygame_audio] reopen after stall failed: %s" % (error,))
        finally:
            self._grace_until = time.time() + RECOVER_GRACE_MS / 1000.0
            self._recycling = False

    def service(self):
        """Call from the app's tick: flush partial writes and watch for stalls.

        Required, not optional -- stall recovery only happens here and in
        :meth:`drain`. A no-op during a rebuild, since the worker owns the device
        and the pending PCM is queued on the next tick.
        """
        if self._recycling or not self.device:
            return
        if self._coalesce:
            self._flush_coalesce(force=False)
        # Failsafe: pump may be blocked at the HW watermark while still paused.
        self._unpause_if_primed()
        self._check_stall()

    def _wait_rebuild(self, timeout_ms=3000):
        """Wait out an in-flight rebuild before touching the device."""
        waited = 0
        while self._recycling and waited < timeout_ms:
            _sleep_ms(self.poll_ms)
            waited += self.poll_ms
        return not self._recycling

    def _drain_timeout_ms(self):
        """Real-time playout of what is queued, plus slack.

        Never wait forever: a stalled sink (WSLg RDP sink stops consuming) used
        to hang the caller indefinitely instead of reporting the stall.
        """
        queued_ms = self.queued_size() * 1000 // max(1, self._bytes_per_second)
        return 2 * queued_ms + 500

    def drain(self, timeout_ms=None):
        """Block until queued PCM has played out. False if it timed out.

        Keeps servicing the stall detector while it waits, and grants a fresh
        playout budget whenever a recycle happens, so recovering mid-drain does
        not truncate the tail it just re-queued.
        """
        self.open()
        self._wait_rebuild()
        self._open_device()
        self._flush_coalesce(force=True)
        if timeout_ms is None:
            timeout_ms = self._drain_timeout_ms()
        waited = 0
        seen = self.recycles
        while self.queued_size() > 0 and waited < timeout_ms:
            _sleep_ms(self.poll_ms)
            waited += self.poll_ms
            self._check_stall()
            self._flush_coalesce(force=True)
            if self.recycles != seen:
                # A rebuild re-queued audio: allow it its own playout time.
                seen = self.recycles
                timeout_ms = waited + self._drain_timeout_ms()
        return self.queued_size() == 0

    async def adrain(self, timeout_ms=None):
        """Async :meth:`drain`; identical rules, yields instead of sleeping."""
        self.open()
        self._wait_rebuild()
        self._open_device()
        self._flush_coalesce(force=True)
        if timeout_ms is None:
            timeout_ms = self._drain_timeout_ms()
        waited = 0
        seen = self.recycles
        while self.queued_size() > 0 and waited < timeout_ms:
            await _asleep_ms(self.poll_ms)
            waited += self.poll_ms
            self._check_stall()
            self._flush_coalesce(force=True)
            if self.recycles != seen:
                seen = self.recycles
                timeout_ms = waited + self._drain_timeout_ms()
        return self.queued_size() == 0

    def clear(self):
        """Drop queued PCM now (abort); keep the device and re-prime on next write."""
        self._coalesce = bytearray()
        if not self.device:
            return
        sdl = _pygame_sdl()
        sdl.SDL_PauseAudioDevice(self.device, 1)
        sdl.SDL_ClearQueuedAudio(self.device)
        self._prime_pause = True
        self._shadow = bytearray()
        self._queued_total = 0
        del self._samples[:]

    def _close_device(self):
        """Tear the SDL device down, leaving the software buffers alone."""
        if not self.device:
            return
        sdl = _pygame_sdl()
        try:
            sdl.SDL_PauseAudioDevice(self.device, 1)
            sdl.SDL_ClearQueuedAudio(self.device)
            sdl.SDL_CloseAudioDevice(self.device)
        except Exception:
            pass
        self.device = 0

    def _close(self):
        """Close for good, discarding anything still queued.

        Waits out an in-flight rebuild first: that worker owns the device handle
        and would otherwise reopen it moments after this returns.
        """
        self._wait_rebuild()
        self._close_device()
        self._coalesce = bytearray()
        self._shadow = bytearray()
        self._queued_total = 0
        del self._samples[:]
        self._prime_pause = True


class PygamePCMInput(PCMInput):
    """Microphone capture via ``pygame._sdl2.AudioDevice``."""

    def __init__(self, fmt, *, device=None, samples=512, poll_ms=2, queue_ms=500):
        super().__init__(fmt)
        self.device_name = device
        self.samples = int(samples)
        self.poll_ms = int(poll_ms)
        self._queue_limit = max(
            fmt.frame_size,
            fmt.rate * fmt.frame_size * int(queue_ms) // 1000,
        )
        self._device = None
        self._lock = threading.Lock()
        self._chunks = collections.deque()
        self._pending = bytearray()

    def _callback(self, audiodevice, audiomemoryview):
        chunk = bytes(audiomemoryview)
        with self._lock:
            self._chunks.append(chunk)
            total = sum(len(item) for item in self._chunks) + len(self._pending)
            while total > self._queue_limit and self._chunks:
                dropped = self._chunks.popleft()
                total -= len(dropped)

    def _open(self):
        if self._device is not None:
            return
        _ensure_pygame()
        from pygame._sdl2 import audio as sdl_audio

        names = sdl_audio.get_audio_device_names(True)
        if self.device_name is None and not names:
            raise OSError("no pygame capture devices available")
        self._device = sdl_audio.AudioDevice(
            devicename=self.device_name,
            iscapture=True,
            frequency=self.format.rate,
            audioformat=_pygame_audio_format(self.format),
            numchannels=self.format.channels,
            chunksize=self.samples,
            allowed_changes=0,
            callback=self._callback,
        )
        self._device.pause(0)

    def _take(self, needed):
        with self._lock:
            while len(self._pending) < needed and self._chunks:
                self._pending.extend(self._chunks.popleft())
            count = min(needed, len(self._pending))
            count -= count % self.format.frame_size
            if count <= 0:
                return b""
            data = bytes(self._pending[:count])
            # Slice assignment: MP/CP bytearrays cannot ``del``.
            self._pending[:count] = b""
            return data

    def _readinto(self, buf):
        needed = len(buf)
        while True:
            data = self._take(needed)
            if data:
                buf[: len(data)] = data
                return len(data)
            _sleep_ms(self.poll_ms)

    async def _areadinto(self, buf):
        needed = len(buf)
        while True:
            data = self._take(needed)
            if data:
                buf[: len(data)] = data
                return len(data)
            await _asleep_ms(self.poll_ms)

    def _close(self):
        dev = self._device
        self._device = None
        with self._lock:
            self._chunks.clear()
            self._pending = bytearray()
        _close_audiodevice_async(dev)


def audio_out(
    format=None,
    *,
    latency=None,
    samples=None,
    poll_ms=2,
    queue_ms=None,
    coalesce_ms=None,
):
    """Create a pygame-ce-backed PCM playback device (QueueAudio on pygame SDL).

    ``latency`` picks a profile (see :data:`audiodev.LATENCIES`); ``samples``,
    ``queue_ms`` and ``coalesce_ms`` given explicitly override it.
    """
    check_latency(latency)
    default_samples, default_queue_ms, default_coalesce_ms = _PLAY_PROFILES[latency]
    fmt = format or AudioFormat(16000, 2, 16)
    return PygamePCMOutput(
        fmt,
        samples=default_samples if samples is None else samples,
        poll_ms=poll_ms,
        queue_ms=default_queue_ms if queue_ms is None else queue_ms,
        coalesce_ms=default_coalesce_ms if coalesce_ms is None else coalesce_ms,
    )


def audio_in(format=None, *, device=None, latency=None, samples=None, poll_ms=2, queue_ms=None):
    """Create a pygame-ce-backed PCM capture device via ``_sdl2.AudioDevice``.

    ``latency`` picks a profile as in :func:`audio_out`; ``samples`` and
    ``queue_ms`` given explicitly override it.
    """
    check_latency(latency)
    default_samples, default_queue_ms = _CAPTURE_PROFILES[latency]
    fmt = format or AudioFormat(16000, 1, 16)
    return PygamePCMInput(
        fmt,
        device=device,
        samples=default_samples if samples is None else samples,
        poll_ms=poll_ms,
        queue_ms=default_queue_ms if queue_ms is None else queue_ms,
    )
