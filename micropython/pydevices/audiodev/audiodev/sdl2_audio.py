"""SDL2 audio backend for :mod:`audiodev` (pure Python, queued audio only).

Playback pushes PCM with ``SDL_QueueAudio`` and never installs an audio
callback: SDL's audio thread is not registered with the Python/MicroPython
runtime, so calling back into the interpreter from it is unsafe (it segfaults
under MicroPython and fights the GIL under CPython/LVGL).

Four behaviors keep queued playback smooth, all established by measurement on
WSLg/PulseAudio rather than by preference:

* small writes are coalesced (``coalesce_ms``, 100ms by default) before being
  handed to SDL;
* the device stays paused until ``PREBUFFER_MS`` is queued, because starting on
  a nearly empty queue and then starving it makes PulseAudio stop asking for
  data;
* if the device falls far behind realtime, it is reopened and the unplayed PCM is
  re-queued (see ``STALL_WINDOW_MS``);
* that reopen runs on a worker thread, because closing a wedged device blocks for
  over a second and the caller is usually driving a UI.

Before simplifying any of this
------------------------------

Each rule below replaced an obvious, simpler version that measurably failed. The
failure is named so it can be re-tested instead of rediscovered:

* Detect stalls by **consumption rate over a window**, never by watching queue
  depth. A caller that tops the queue up replaces every consumed period before
  the next check sees it, so depth does not fall even when the sink has died.
* Gate the prebuffer on :meth:`SDLPCMOutput._hw_queued`, never on
  :meth:`SDLPCMOutput.queued_size`. Counting bytes still sitting in the
  software buffer let the device start on ~40ms of audio, underrun, and wedge
  again immediately after every recovery.
* Keep the reopen off the caller's thread, and keep ``RECOVER_SETTLE_MS``
  between close and open. A synchronous rebuild stalled the caller's tick for
  ~1.8s; reopening with no gap handed back the same wedged sink and re-stalled
  within seconds, in pairs.
* Size ``_shadow`` to cover everything SDL may still hold. Anything smaller
  silently drops audio during recovery.
* Do not let "the device is unpaused" mean playing in
  :meth:`SDLPCMOutput.is_active` -- it stays unpaused for the life of the
  device, so callers would wait forever for playback that already finished.

The ``recycles``, ``lost_bytes`` and ``requeued_bytes`` counters exist to keep
those claims checkable: a healthy long run recycles rarely and loses nothing.
``README.md`` in this directory has the full account, including how to measure a
change before making it.

This module also runs on MicroPython (unix and ``micropython.exe``) and
CircuitPython, so it avoids CPython-only APIs -- notably it consumes buffers with
``buf[:n] = b""`` rather than ``del buf[:n]``, which those runtimes reject at
runtime, not at import. See "Portability" in ``README.md``; verify changes by
running ``examples/audio_out_test.py`` under all three interpreters.
"""

try:
    import asyncio
except ImportError:  # pragma: no cover
    import uasyncio as asyncio

import sys
import time

from audiodev import AudioFormat, PCMInput, PCMOutput, check_latency
import usdl2 as sdl

try:
    import threading
except ImportError:  # pragma: no cover
    threading = None


# SDL device period (``SDL_AudioSpec.samples``) for playback. Queued audio does
# not care about device latency, so this is chosen for stall detection: the
# queue legitimately holds steady for up to one period between SDL's pulls.
DEFAULT_PLAY_SAMPLES = 4096

# Playback cushion held in SDL's queue. Speech synthesis is bursty, so a couple
# of seconds keeps the device fed while the next sentence is still being made.
DEFAULT_PLAY_QUEUE_MS = 2000

# PCM to accumulate in the *software* buffer before handing a piece to SDL.
# Batching keeps a caller's small writes from becoming one SDL_QueueAudio call
# each, but a realtime producer waits this long before its first sound.
DEFAULT_COALESCE_MS = 100

# Playback settings per ``audiodev`` latency profile. Only the values a caller
# left unset are taken from here.
#
# "low" is what this backend defaulted to before queued playback grew stall
# recovery, and it is chosen for note-to-sound delay rather than throughput:
#
# * a 512-sample period is ~21ms at 24kHz instead of ~170ms, so playback starts
#   and stops on a musical timescale;
# * queue_ms also shrinks the prebuffer, since ``_prebuffer_bytes`` is capped at
#   a quarter of the queue -- 250ms of queue means ~62ms of priming, not 500ms;
# * a 20ms coalesce window is under one 40ms synth chunk, so each chunk reaches
#   SDL as it is rendered.
#
# Measured end to end with a realtime writer: ~59ms of latency against ~416ms
# for the buffered profile. The tradeoff is real -- a short queue leaves less
# room to recover from a host sink stall -- so it is opt-in, not the default.
_PLAY_PROFILES = {
    None: (DEFAULT_PLAY_SAMPLES, DEFAULT_PLAY_QUEUE_MS, DEFAULT_COALESCE_MS),
    "buffered": (DEFAULT_PLAY_SAMPLES, DEFAULT_PLAY_QUEUE_MS, DEFAULT_COALESCE_MS),
    "low": (512, 250, 20),
}

# Capture profiles. Recording has no prebuffer or coalescing, so only the period
# and queue matter.
_CAPTURE_PROFILES = {
    None: (512, 250),
    "buffered": (512, 250),
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


def _android_session():
    """Attach Android media focus/FGS session on first PCM open (lazy).

    Non-Android hosts get ``session=None`` (unchanged PCMOutput behavior).
    On Android the module must be present; acquire/release stay lazy until
    ``open()`` / ``write()`` via :class:`SDLPCMOutput`.
    """
    if sys.platform != "android":
        return None
    from audiodev.android_audio import get_session

    return get_session()


def _sleep_ms(milliseconds):
    if hasattr(time, "sleep_ms"):
        time.sleep_ms(milliseconds)
    else:
        time.sleep(milliseconds / 1000)


async def _asleep_ms(milliseconds):
    if hasattr(asyncio, "sleep_ms"):
        await asyncio.sleep_ms(milliseconds)
    else:
        await asyncio.sleep(milliseconds / 1000)


def _monotonic_ms():
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms()
    return int(time.time() * 1000)


def _elapsed_ms(since):
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(_monotonic_ms(), since)
    return _monotonic_ms() - since


def _diff_ms(later, earlier):
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(later, earlier)
    return later - earlier


def _deadline_ms(milliseconds):
    """A future timestamp comparable with :func:`_elapsed_ms` (ticks-safe)."""
    if hasattr(time, "ticks_add"):
        return time.ticks_add(_monotonic_ms(), milliseconds)
    return _monotonic_ms() + milliseconds


def _sdl_format(fmt):
    if fmt.bits == 8:
        return sdl.AUDIO_S8 if fmt.signed else sdl.AUDIO_U8
    suffix = "LSB" if fmt.byteorder == "little" else "MSB"
    name = "AUDIO_%s%d%s" % ("S" if fmt.signed else "U", fmt.bits, suffix)
    value = getattr(sdl, name, None)
    if value is None:
        raise ValueError("SDL does not support %r" % fmt)
    return value


def list_audio_devices(capture=False):
    """Return SDL playback or capture device names."""
    count = sdl.SDL_GetNumAudioDevices(bool(capture))
    if count < 0:
        raise OSError(sdl.SDL_GetError())
    return tuple(sdl.SDL_GetAudioDeviceName(index, bool(capture)) for index in range(count))


class SDLPCMOutput(PCMOutput):
    """SDL playback via ``SDL_QueueAudio`` (no audio callback, no mixer).

    PCM travels through two buffers: writes land in ``_coalesce`` (software) and
    are handed to SDL in ``coalesce_ms`` pieces up to ``_queue_limit`` (hardware).
    :meth:`queued_size` reports both, so a caller can treat "queued_size() == 0"
    as end of playback without knowing which buffer holds what.

    Callers must call :meth:`service` from their tick. Without it, a partial
    write can sit in ``_coalesce`` unqueued and a wedged device is never noticed.
    """

    def __init__(
        self,
        fmt,
        *,
        device=None,
        samples=512,
        queue_ms=250,
        poll_ms=2,
        coalesce_ms=DEFAULT_COALESCE_MS,
        session=None,
    ):
        super().__init__(fmt, session=session)
        self.device_name = device
        self.samples = int(samples)
        self.queue_ms = int(queue_ms)
        self.poll_ms = int(poll_ms)
        self.device = 0
        self._bytes_per_second = fmt.rate * fmt.frame_size
        self._queue_limit = max(fmt.frame_size, self._bytes_per_second * queue_ms // 1000)
        # SDL pulls a whole period at a time, so the queue must comfortably hold
        # several of them no matter what ``queue_ms`` a caller asked for.
        period_bytes = self.samples * fmt.frame_size
        self._queue_limit = max(self._queue_limit, 3 * period_bytes)
        self._coalesce = bytearray()
        self.coalesce_ms = int(coalesce_ms)
        self._coalesce_bytes = max(
            fmt.frame_size,
            self._bytes_per_second * self.coalesce_ms // 1000,
        )
        # Kept under the caller's fill watermark so a pump that stops writing at
        # the watermark cannot leave us paused forever.
        self._prebuffer_bytes = min(
            self._queue_limit // 4,
            max(fmt.frame_size, self._bytes_per_second * PREBUFFER_MS // 1000),
        )
        period_ms = 1000 * self.samples // max(1, fmt.rate)
        # Long enough that period quantization cannot look like a slow sink: a
        # healthy device delivers whole periods, so a short window can read well
        # under realtime purely from where the period boundaries fall.
        self._stall_window_ms = max(STALL_WINDOW_MS, 6 * period_ms)
        self._min_rate = int(self._bytes_per_second * STALL_RATIO)
        # Below this the queue may simply be running dry, which says nothing
        # about the device.
        self._min_depth_bytes = 2 * period_bytes
        # Backstop for callers that ignore ``queued_size()`` backpressure: a
        # rebuild only needs a couple of seconds of headroom here.
        self._max_pending = 4 * self._queue_limit
        # Must cover every byte SDL can still hold, or a rebuild cannot restore
        # the whole unplayed queue.
        self._shadow_limit = self._queue_limit + self._coalesce_bytes
        self._prime_pause = True
        self._lock = threading.Lock() if threading is not None else None
        # True while a worker thread is closing/reopening the device.
        self._recycling = False
        # Cumulative bytes handed to SDL. Progress is measured as
        # ``_queued_total - queued``, not as a drop in queue depth: a caller that
        # tops the queue up replaces each consumed period before the next check
        # sees it, so depth alone never falls while playback is healthy.
        self._queued_total = 0
        # Trailing (timestamp, consumed) samples spanning ``_stall_window_ms``.
        self._samples = []
        self._grace_until = None
        # Copy of the most recently queued PCM (never more than one full queue).
        # A recycle discards whatever SDL still held, so the unplayed tail is
        # re-queued from here instead of being dropped.
        self._shadow = bytearray()
        self.recycles = 0
        self.lost_bytes = 0
        self.requeued_bytes = 0
        self.channel = None  # no mixer; kept for callers that probe for one
        self.mode = "queue"

    # -- device ---------------------------------------------------------------

    def _open(self):
        self._open_device()

    def _open_device(self):
        """Open the SDL device **paused** and reset progress accounting.

        Opening paused is not an optimization: the device must not start on the
        first small chunk of a flush (see :meth:`_unpause_if_primed`). Progress
        state is per-device, so ``_queued_total`` and the rate samples reset here
        -- carrying them across a reopen would read as a huge instant stall.
        """
        if self.device:
            return self
        if sdl.SDL_InitSubSystem(sdl.SDL_INIT_AUDIO) != 0:
            raise OSError(sdl.SDL_GetError())
        spec = sdl.SDL_AudioSpec(
            self.format.rate,
            _sdl_format(self.format),
            self.format.channels,
            self.samples,
        )
        self.device = sdl.SDL_OpenAudioDevice(self.device_name, False, spec, None, 0)
        if not self.device:
            raise OSError(sdl.SDL_GetError())
        # Stay paused until primed; see PREBUFFER_MS.
        self._prime_pause = True
        self._queued_total = 0
        del self._samples[:]
        sdl.SDL_PauseAudioDevice(self.device, 1)
        return self

    def _close_device(self):
        """Tear the SDL device down, leaving the software buffers alone."""
        if self.device:
            sdl.SDL_PauseAudioDevice(self.device, 1)
            sdl.SDL_ClearQueuedAudio(self.device)
            sdl.SDL_CloseAudioDevice(self.device)
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

    def _wait_rebuild(self, timeout_ms=3000):
        """Wait out an in-flight rebuild before touching the device."""
        waited = 0
        while self._recycling and waited < timeout_ms:
            _sleep_ms(self.poll_ms)
            waited += self.poll_ms
        return not self._recycling

    # -- queue accounting -----------------------------------------------------

    def _hw_queued(self):
        """Bytes SDL still holds. The only trustworthy measure of playback."""
        if not self.device:
            return 0
        return int(sdl.SDL_GetQueuedAudioSize(self.device))

    def queued_size(self):
        """Bytes still waiting to play, including what has not been handed to SDL.

        Both buffers count, so audio parked in ``_coalesce`` during a rebuild is
        not mistaken for silence. Use :meth:`_hw_queued` instead when the
        question is what the *device* is doing.
        """
        return self._hw_queued() + len(self._coalesce)

    def is_active(self):
        """True while PCM is still queued anywhere.

        Deliberately ignores pause state: the device stays unpaused for its whole
        life, so testing that instead would report playback as active forever and
        hang callers that wait for idle.
        """
        return self.queued_size() > 0

    # -- writing --------------------------------------------------------------

    def _unpause_if_primed(self, force=False):
        """Start playback once ``_prebuffer_bytes`` are queued.

        ``force`` starts on whatever is queued -- used when the caller has said
        no more PCM is coming (short sounds, flush, drain), so a 40ms beep plays.

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
        data = bytes(buf)
        if self._lock is not None:
            self._lock.acquire()
        try:
            if not self.device:
                self._open_device()
            rc = sdl.SDL_QueueAudio(self.device, data, len(data))
            if rc == 0:
                self._queued_total += len(data)
                self._shadow.extend(data)
                if len(self._shadow) > self._shadow_limit:
                    # Slice assignment: MP/CP bytearrays cannot ``del``.
                    self._shadow[: len(self._shadow) - self._shadow_limit] = b""
        finally:
            if self._lock is not None:
                self._lock.release()
        if rc != 0:
            raise OSError(sdl.SDL_GetError())

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

    def clear(self):
        """Drop queued PCM now (abort); keep the device and re-prime on next write."""
        self._coalesce = bytearray()
        if not self.device:
            return
        sdl.SDL_PauseAudioDevice(self.device, 1)
        sdl.SDL_ClearQueuedAudio(self.device)
        self._prime_pause = True
        self._shadow = bytearray()
        self._queued_total = 0
        del self._samples[:]

    # -- stall recovery -------------------------------------------------------

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
        # Failsafe: a pump parked at the fill watermark must not leave us paused.
        self._unpause_if_primed()
        self._check_stall()

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
        if self._grace_until is not None and _elapsed_ms(self._grace_until) < 0:
            del self._samples[:]
            return
        hw = self._hw_queued()
        consumed = self._queued_total - hw
        if hw < self._min_depth_bytes:
            del self._samples[:]
            return
        now = _monotonic_ms()
        samples = self._samples
        if not samples or _diff_ms(now, samples[-1][0]) >= STALL_SAMPLE_MS:
            samples.append((now, consumed))
        while len(samples) > 1 and _diff_ms(now, samples[1][0]) >= self._stall_window_ms:
            del samples[0]
        span = _diff_ms(now, samples[0][0])
        if span < self._stall_window_ms:
            return
        rate = (consumed - samples[0][1]) * 1000 // span
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
        if self._lock is None:
            self._rebuild_device()
        else:
            threading.Thread(target=self._rebuild_device, daemon=True).start()

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
            print("[sdl2_audio] reopen after stall failed: %s" % (error,))
        finally:
            self._grace_until = _deadline_ms(RECOVER_GRACE_MS)
            self._recycling = False

    # -- draining -------------------------------------------------------------

    def _drain_timeout_ms(self):
        """Real-time playout of what is queued, plus slack.

        Never wait forever: a device that stopped consuming would otherwise hang
        the caller instead of reporting the stall.
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
        self._unpause_if_primed(force=True)
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
        self._unpause_if_primed(force=True)
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


class SDLPCMInput(PCMInput):
    def __init__(self, fmt, *, device=None, samples=512, queue_ms=250, poll_ms=2):
        super().__init__(fmt)
        self.device_name = device
        self.samples = int(samples)
        self.queue_ms = int(queue_ms)
        self.poll_ms = int(poll_ms)
        self.device = 0

    def _open(self):
        if self.device:
            return
        if sdl.SDL_InitSubSystem(sdl.SDL_INIT_AUDIO) != 0:
            raise OSError(sdl.SDL_GetError())
        spec = sdl.SDL_AudioSpec(
            self.format.rate,
            _sdl_format(self.format),
            self.format.channels,
            self.samples,
        )
        self.device = sdl.SDL_OpenAudioDevice(
            self.device_name,
            True,
            spec,
            None,
            0,
        )
        if not self.device:
            raise OSError(sdl.SDL_GetError())
        sdl.SDL_PauseAudioDevice(self.device, 0)

    def _close(self):
        if self.device:
            sdl.SDL_CloseAudioDevice(self.device)
            self.device = 0

    def _readinto(self, buf):
        needed = len(buf)
        while sdl.SDL_GetQueuedAudioSize(self.device) < self.format.frame_size:
            _sleep_ms(self.poll_ms)
        available = min(needed, sdl.SDL_GetQueuedAudioSize(self.device))
        available -= available % self.format.frame_size
        return sdl.SDL_DequeueAudio(self.device, buf, available)

    async def _areadinto(self, buf):
        needed = len(buf)
        while sdl.SDL_GetQueuedAudioSize(self.device) < self.format.frame_size:
            await _asleep_ms(self.poll_ms)
        available = min(needed, sdl.SDL_GetQueuedAudioSize(self.device))
        available -= available % self.format.frame_size
        return sdl.SDL_DequeueAudio(self.device, buf, available)


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
    """Create an SDL-backed :class:`PCMOutput`.

    ``latency`` picks a profile (see :data:`audiodev.LATENCIES`); pass
    ``"low"`` for interactive callers such as a synth. Any of ``samples``,
    ``queue_ms`` and ``coalesce_ms`` given explicitly override the profile.
    """
    check_latency(latency)
    default_samples, default_queue_ms, default_coalesce_ms = _PLAY_PROFILES[latency]
    fmt = format or AudioFormat(16000, 2, 16)
    return SDLPCMOutput(
        fmt,
        device=device,
        samples=default_samples if samples is None else samples,
        queue_ms=default_queue_ms if queue_ms is None else queue_ms,
        coalesce_ms=default_coalesce_ms if coalesce_ms is None else coalesce_ms,
        poll_ms=poll_ms,
        session=_android_session(),
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
    """Create an SDL-backed :class:`PCMInput` using real host capture.

    ``latency`` picks a profile as in :func:`audio_out`; ``samples`` and
    ``queue_ms`` given explicitly override it.
    """
    check_latency(latency)
    default_samples, default_queue_ms = _CAPTURE_PROFILES[latency]
    fmt = format or AudioFormat(16000, 1, 16)
    return SDLPCMInput(
        fmt,
        device=device,
        samples=default_samples if samples is None else samples,
        queue_ms=default_queue_ms if queue_ms is None else queue_ms,
        poll_ms=poll_ms,
    )


