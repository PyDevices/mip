# Audio drivers

PCM playback and capture for [pydevices](https://github.com/PyDevices/pydevices)
board configs. The `audiodev` package owns the portable bases; each backend is a
standalone submodule that subclasses them. `audiodev.auto` is an optional
selector only — backends never import it.

| Module | Host | Role |
|--------|------|------|
| `audiodev` | all | `AudioFormat`, `PCMOutput` / `PCMInput` / `ToneOutput` bases, latency helpers |
| `audiodev.sdl2_audio` | desktop MicroPython, CircuitPython, CPython, Jupyter | SDL2 queued PCM through `usdl2` |
| `audiodev.pygame_audio` | CPython desktop with pygame-ce installed | Queued PCM on pygame-ce's bundled SDL |
| `audiodev.win_audio` | Windows CPython | WASAPI shared-mode queued PCM through `uwin32` |
| `audiodev.web_audio` | PyScript / browser | Web Audio playback, `getUserMedia` capture |
| `audiodev.i2s_audio` | MCU | `machine.I2S` adapter |
| `audiodev.pwm_tone` | MCU | PWM / buzzer adapter |
| `audiodev.emulated_audio` | CI / no hardware | WAV, generator, loopback, discard |
| `audiodev.android_audio` | Android | Media focus + foreground service |
| `audiodev.auto` | host convenience | Probe-based `audio_out` / `audio_in` |

Apps typically use `board_config.audio_out`. Board configs may import a concrete
backend or `audiodev.auto`. Desktop `board_peripherals` uses auto (DirectSound env
only when the selected backend is `pygame_audio`). `audiodev.auto` prefers
`win_audio` on Windows CPython when `uwin32` imports, before pygame/SDL.

This package does not import `displaydev`, `multimer`, or `eventsys`.

Family invariants (template for later displaydev / multimer):

1. Package owns base + standalone backend modules; each backend is complete without `Auto*`.
2. `Auto*` is optional; dependency arrow is `auto → backends`, never reverse.
3. Optional behavior is real methods with defaults (`service`, `queued_size`, `is_active`, `clear`), not `getattr` discovery.
4. Platform defects stay documented with “do not simplify” tests, inside the owning subclass.

## Buffering options

Because a board forwards its keyword arguments to whichever backend it picks,
the backends have to spell the same concept the same way. These names are the
contract; do not add a fourth spelling for one of them.

| Keyword | Meaning | Backends |
|---------|---------|----------|
| `latency` | Profile name: `None`/`"buffered"` or `"low"` (see `audiodev.LATENCIES`) | host PCM backends |
| `samples` | Device block size in frames (SDL's `AudioSpec.samples`, Web Audio's `ScriptProcessorNode` size) | host PCM (capture only for `web_audio`) |
| `queue_ms` | Playable audio the queue may hold | `sdl2_audio`, `pygame_audio`, `win_audio`, `emulated_audio` loopback |
| `coalesce_ms` | How much PCM to batch in software before handing a piece to the device | `sdl2_audio`, `pygame_audio`, `win_audio` |
| `poll_ms` | Sleep between polls while blocked | host PCM backends |
| `device` | Host device name | `sdl2_audio`, `pygame_audio` (capture) |

A backend accepts a name only where the concept exists, rather than accepting
and ignoring it: `web_audio` playback has no queue or coalesce window at all,
because it schedules each buffer onto the `AudioContext` timeline as it arrives.

The same rule reaches the MCU board configs that build PCM devices directly from
`machine.I2S` (ESP32-P4, both M5Stack Tab5 variants). There `latency` and
`queue_ms` size the I2S ring buffer — `audiodev.queue_bytes()` converts a profile
into the byte count `ibuf` wants — and nothing else is accepted, since those
boards have no software coalescing stage and no host device to name. Their
buffered default is the board's own bring-up value, returned untouched rather
than recomputed from a round number, and the shortened buffer has a floor so a
caller cannot starve the DMA. Boards whose `audio_out` is a PWM
`audiodev.pwm_tone.PWMToneOutput` take no audio keywords at all.

`latency` is the one knob every backend takes, so it is what portable code
should use. The default profile is buffered, tuned for a producer that can write
faster than realtime — speech synthesis with whole utterances ready, or file
playback — where depth costs nothing and protects against a starved sink.

`latency="low"` is for the opposite producer: a synth writing at realtime with a
small look-ahead, where every buffered millisecond is note-to-sound delay.
Measured on `micropython.exe` with a 40ms-per-40ms writer:

| Profile | First sound | Steady latency |
|---------|-------------|----------------|
| default | 486 ms | 418 ms |
| `"low"` | 42 ms | 52 ms |

The tradeoff is real — a short queue leaves less slack to recover from a host
sink stall (see [The WSLg / PulseAudio sink defect](#the-wslg--pulseaudio-sink-defect))
— so it is opt-in. Explicit
`samples` / `queue_ms` / `coalesce_ms` override whatever the profile chose. An
unknown profile name raises rather than falling back, so a typo cannot quietly
leave an interactive app buffered.

## The device contract

Backends subclass `PCMOutput` / `PCMInput` / `ToneOutput`. The object the app
holds *is* the backend. Bases provide session, volume/gain, write-all looping,
and async defaults that yield. Subclasses implement `_write` / `_readinto` /
`_play` (and `_open` / `_close`).

Queued hosts override these methods on the device itself (safe no-ops on MCU):

| Method | Purpose |
|--------|---------|
| `queued_size()` | Bytes still waiting to play, software plus hardware buffers |
| `is_active()` | True while any PCM remains queued |
| `service()` | Per-tick housekeeping; **required** for `sdl2_audio`, `pygame_audio`, and `win_audio` |
| `clear()` | Abort playback now, discarding queued PCM |

`service()` is not optional decoration for the two SDL backends: partial writes
are flushed there, and stall recovery only runs from `service()` and `drain()`.
An app that never ticks will eventually hear PCM stop with data still buffered.

Async overrides must await, including when there is nothing to wait for. An
`_awrite` that never awaits starves the event loop: a task looping on it never
yields, so timers never fire and even its own `cancel()` is never delivered.

## Portability

`audiodev/__init__.py` and `sdl2_audio.py` run on CPython, MicroPython (unix *and*
`micropython.exe`), and CircuitPython, so they are limited to APIs all three
provide. CPython-only idioms here do not fail at import — they raise at runtime
on the first write, which is why they survive review.

| Instead of | Write | Why |
|------------|-------|-----|
| `del buf[:n]` | `buf[:n] = b""` | MicroPython and CircuitPython bytearrays support no item deletion at all (`TypeError`). Slice assignment behaves identically on all four runtimes, including `[:]`, `n == len`, and `n > len`. |
| `os.environ` | `displaydev.env_get` / `env_set` | Only CPython has `os.environ`; the others have `getenv`/`putenv` only. `env_set` walks `os.environ` → `os.putenv` → a process-local override. |
| `time.monotonic()` | the module's `_monotonic_ms()` / `_elapsed_ms()` | MicroPython measures time with `ticks_ms`, which wraps; comparisons need `ticks_diff`. |
| assuming `threading` | the guarded `threading is not None` paths | Bare MicroPython and CircuitPython have no `threading`, so `_lock` is `None` and the async rebuild degrades to a synchronous one. |

Lists are unaffected — `del self._samples[:]` is fine everywhere; only
`bytearray` (`_coalesce`, `_shadow`, `_pending`) has the restriction.

`pygame_audio.py` and `web_audio.py` cannot run on MicroPython or CircuitPython at
all (they need pygame-ce and Pyodide's `js` module), so a CPython-only idiom is
not a bug there. `pygame_audio.py` still uses the portable forms, because it
mirrors `sdl2_audio.py` closely enough to diff — see "Keep it in step with
`sdl2_audio.py`" below. `web_audio.py` shares nothing with them and stays as it is.

Verify with the real interpreters rather than by inspection — CPython accepts
everything above:

```bash
cd pydevices-examples/src
for rt in micropython micropython.exe circuitpython; do $rt examples/audio_out_test.py; done
```

## `audiodev/__init__.py`

Portable bases, no host dependencies:

- **`AudioFormat(rate, channels, bits, signed=True, byteorder="little")`** —
  validates its arguments and precomputes `frame_size`. Compares by value.
- **`PCMOutput` / `PCMInput`** — subclassable bases: volume/gain, session,
  write-all looping, async surface. `write()` loops until the whole buffer is
  consumed and raises if a transport makes no progress.
- **`ToneOutput`** — subclassable frequency/duty base.
- **`AudioSession`** — coordinates devices sharing a codec or peripheral;
  `acquire()` refuses a second owner unless the session is `duplex`.

WAV / generator / loopback live in `audiodev.emulated_audio`, not here.

## `sdl2_audio.py`

SDL2 backend built on `usdl2` (pure Python ctypes/FFI bindings — no C
extension). Runs on MicroPython, CircuitPython and CPython, and attaches the
Android media session lazily when `sys.platform == "android"`.

Playback pushes PCM with `SDL_QueueAudio` and **never installs an audio
callback**. SDL's audio thread is not registered with the Python or MicroPython
runtime, so calling into the interpreter from it segfaults under MicroPython and
fights the GIL under CPython with LVGL.

### How playback works

PCM passes through two buffers. `write()` appends to a software `_coalesce`
buffer; pieces of roughly 100 ms are handed to SDL until its queue reaches
`_queue_limit` (`queue_ms`, default 2 s). `queued_size()` reports both, so
"`queued_size() == 0`" means playback finished no matter which buffer held what.

Four behaviors keep that smooth, each measured on WSLg/PulseAudio:

1. **Coalescing** — many small writes become few `SDL_QueueAudio` calls.
2. **Prebuffer** — the device opens paused and starts only once `PREBUFFER_MS`
   is in *SDL's* queue. Starting on a nearly empty queue and then starving it
   makes PulseAudio stop asking for data.
3. **Stall recovery** — if consumption falls below `STALL_RATIO` of realtime over
   `STALL_WINDOW_MS`, the device is closed and reopened and the unplayed tail is
   re-queued from a shadow copy.
4. **Off-thread rebuild** — that close/reopen runs on a worker thread, because
   closing a wedged device blocks for over a second and the caller is usually
   driving a UI.

### Do not simplify these

Every rule below replaced an obvious, simpler version that measurably failed.
The failure is named so it can be re-tested rather than rediscovered:

- **Detect stalls by consumption rate, not queue depth.** Progress is
  `_queued_total - _hw_queued()`, a monotonic total. "Has queue depth stopped
  falling?" never becomes true: the pump replaces each consumed period before
  the next check, so depth is flat during healthy playback *and* during a total
  stall.
- **Gate the prebuffer on `_hw_queued()`, never `queued_size()`.** Counting
  software bytes lets a rebuild's re-queued tail satisfy the threshold instantly,
  so the device starts on ~40 ms of audio, underruns, and wedges again — the
  exact failure the prebuffer exists to prevent.
- **Keep the rebuild off the caller's thread.** A synchronous rebuild stalled the
  caller's tick for up to 1.8 s. Off-thread, the worst tick gap measured 48 ms.
- **Keep `RECOVER_SETTLE_MS` between close and open.** Reopening immediately
  returns in ~3 ms and re-wedges within seconds; an open after a settled close
  takes ~1.3 s (the host building a new sink) and then runs normally. Without the
  gap, recycles arrive in pairs and audio degrades further each time.
- **Size `_shadow` to cover everything SDL may still hold**
  (`_queue_limit + _coalesce_bytes`). Anything smaller silently drops audio
  during recovery.
- **Do not treat "unpaused" as playing in `is_active()`.** The device stays
  unpaused for its whole life, so callers waiting for idle would wait forever.
- **`_flush_coalesce()` unpauses once, at the end.** Per-piece unpausing starts
  the device on the first chunk of a large flush.
- **Backpressure must not block.** Without `force`, flushing stops at the queue
  limit and leaves the rest buffered; the caller may be the UI thread.
  `_queue_bytes()` never waits for room at all — waiting there would block
  whichever thread or event loop happened to be flushing.
- **`awrite()` awaits; it is not `write()` in a coroutine.** It yields once even
  when there is room, because a task looping on `awrite` is otherwise the only
  thing the event loop ever runs.
- **The rebuild worker never raises.** A reopen can fail while the sink is busy,
  and an escaped exception leaves no device — at which point `service()` does
  nothing, buffered PCM can never play, and `is_active()` stays true forever. It
  retries, and if it must give up it drops that audio into `lost_bytes` so
  callers stop waiting.

### Tuning and evidence

| Constant | Default | Meaning |
|----------|---------|---------|
| `DEFAULT_PLAY_SAMPLES` | 4096 | SDL device period. Sets `_min_depth_bytes` and the stall window floor |
| `DEFAULT_PLAY_QUEUE_MS` | 2000 | Hardware cushion. Bursty synth needs seconds, not milliseconds |
| `PREBUFFER_MS` | 500 | Device-queue depth required before playback starts |
| `STALL_WINDOW_MS` | 1500 | Measurement window (raised to at least 6 device periods) |
| `STALL_RATIO` | 0.5 | Fraction of realtime below which the device counts as wedged |
| `STALL_SAMPLE_MS` | 100 | Spacing of progress samples |
| `RECOVER_GRACE_MS` | 1500 | Detector pause after a reopen, to skip ramp-up |
| `RECOVER_SETTLE_MS` | 800 | Gap between close and open during recovery |

`STALL_WINDOW_MS` and `STALL_RATIO` trade false positives against slow recovery,
so move them only with rate measurements in hand. A shorter window or higher
ratio fires on healthy playback, because period quantization alone can read well
under realtime over a short span; a longer window or lower ratio leaves audible
slow-motion audio before recovery starts.

`SDLPCMOutput` counts its own recoveries so claims stay checkable:

```python
device.recycles                  # rebuilds so far
device.lost_bytes                # PCM dropped by recovery; must stay 0
device.requeued_bytes            # PCM replayed after a rebuild
```

A healthy long run recycles rarely and loses nothing: 208 s of speech across
four utterances produced one recycle and zero lost bytes.

Keyword arguments are the shared set in [Buffering options](#buffering-options).
Leave the playback defaults alone unless you have measured a reason — an earlier
board config passed `queue_ms=150`, which left too little cushion for
sentence-at-a-time synthesis. A caller that needs less delay should ask for
`latency="low"` rather than trimming the default profile, so speech playback
keeps the depth it was tuned for.
The `queue_ms=150` that `board_peripherals.audio_in()` still passes is unrelated and
intentional: capture wants low latency.

## `win_audio.py`

WASAPI shared-mode backend for Windows CPython, through `uwin32`. Import fails
unless `uwin32` loads.

Playback and capture are queued/pull (`GetBuffer` / `ReleaseBuffer`) with
`AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM`. There is no Python audio-thread callback.
`audiodev.auto` selects this before pygame when `uwin32` is importable.

Keyword arguments are the shared set in [Buffering options](#buffering-options).

## `pygame_audio.py`

Backend for CPython hosts with pygame-ce installed. It uses **pygame's own SDL**,
never `usdl2` or the system libSDL2:

- **Playback** — `SDL_QueueAudio` through ctypes against the bundled `libSDL2`
  that `_pygame_sdl()` locates. No `pygame.mixer`, no Python audio callback.
- **Capture** — `pygame._sdl2.AudioDevice` with a callback into a bounded deque.

Mixing SDL libraries is the one thing that must not change. Driving pygame's
devices through another copy of SDL means two SDL states in one process; use the
bundled library or use `sdl2_audio`, never both against one device.

`_ensure_pygame()` deliberately calls `pygame.mixer.quit()`. This backend drives
SDL audio directly, so the mixer would hold a second, unused output device open,
and two concurrent streams make the WSLg PulseAudio sink stop consuming after
about 30 s.

Capture close is asynchronous on purpose. `AudioDevice.close()` can futex-deadlock
inside SDL waiting on its callback thread, so `_close_audiodevice_async()` pauses
synchronously — which is what callers actually need — and closes on a daemon
thread. Do not make it synchronous.

### Keep it in step with `sdl2_audio.py`

`PygamePCMOutput` mirrors `SDLPCMOutput` mechanism for mechanism: rate-based
stall detection, the hardware-only prebuffer gate, the off-thread rebuild with a
settle gap, the shadow buffer, and the same `recycles` / `lost_bytes` /
`requeued_bytes` counters. Every "do not simplify" rule in the `sdl2_audio.py`
section above applies here unchanged, and the constants carry the same names and
values.

When a fix lands in one backend it belongs in the other, because the failure they
work around is in the host's audio sink, not in either library.

### Windows: only this backend wants DirectSound

`board_peripherals` forces `SDL_AUDIODRIVER=directsound` on Windows for
`pygame_audio` alone. SDL2's default WASAPI backend glitches with pygame's
small-chunk playback, but `sdl2_audio` queues whole buffers and never hit that,
and DirectSound keeps a deeper buffer: measured on `micropython.exe` at
`latency="low"`, DirectSound sits at 185 ms against WASAPI's 55 ms. Forcing it
for every backend spent that on callers who gained nothing. An explicit
`SDL_AUDIODRIVER` in the environment still wins in either case.

## `web_audio.py`

PyScript backend. `WebPCMOutput` converts each write into an `AudioBuffer`
and schedules `AudioBufferSourceNode`s back to back against `currentTime`;
`WebPCMInput` captures through `getUserMedia` and a `ScriptProcessorNode`.

Browser autoplay policy is the thing to know here. A fresh `AudioContext` starts
`suspended`, and while suspended `currentTime` never advances — a naive wait for
playout would spin forever. The module resumes best-effort, arms a one-shot
pointer/key handler to resume on the next gesture, prints a hint telling the user
to click the page, and keeps already-scheduled buffers alive for their wall-clock
duration so a later gesture can still play them.

There is no host device to wedge here, so none of the SDL stall machinery exists.

## `emulated_audio.py`

CI / no-hardware provider. Never selected by `audiodev.auto`.

- `WavPCMOutput` / `WavPCMInput` — PCM WAV files
- `GeneratorPCMInput` — sine / square / noise / silence
- `loopback_pair` — in-memory out→in queue (TTS→STT style)
- `NullPCMOutput` — discard writes

```python
from audiodev import AudioFormat
from audiodev.emulated_audio import audio_in, audio_out, loopback_pair

fmt = AudioFormat(24000, 1, 16)
out = audio_out(fmt, path="/sd/prompt.wav")
out.write(pcm_bytes)
out.close()
mic = audio_in(path="/sd/prompt.wav")
```

## `android_audio.py`

`AndroidMediaSession` is a duck-typed `audiodev.AudioSession`. The first
`open()` / `write()` acquires audio focus and starts a `mediaPlayback` foreground
service; the last `close()` releases both, so Android does not throttle or kill
playback in the background. It is `duplex`, so several `PCMOutput` instances can
share one session — focus and the service stay up while any owner is open.

`get_session()` returns a process-wide instance, created once.
`sdl2_audio.audio_out()` attaches it automatically on Android and passes
`session=None` everywhere else, so acquire and release stay lazy.

Needs pyjnius and a python-for-android service named `mediaplayback` declared
with `:foreground:foregroundServiceType=mediaPlayback` — see
[pydevices-android-template](https://github.com/PyDevices/pydevices-android-template). Off Android
the import is a no-op.

## Tests

`tests/test_audiodev.py`, `tests/test_sdl2_audio.py`, `tests/test_pygame_audio.py`,
`tests/test_win_audio.py`, `tests/test_emulated_audio.py` and `tests/test_auto.py`
cover these modules
against SDL's `dummy` driver, and `tests/test_audiodev_latency.py` covers the
profile vocabulary on its own:

```bash
python -m unittest discover -s tests -q
```

The whole suite finishes in a few seconds. A test that instead runs for minutes is
a real failure, not a slow machine: it means a stream is blocking where it should
await, so a `cancel()` or timer never gets delivered.

Do not run them while another process is playing audio. Two clients on one sink
makes `SDL_OpenAudioDevice` fail with "Could not connect PulseAudio stream",
which looks like a driver bug and is not one.

`tests/test_contract_proof.py` relies on a sibling test importing `tests/_env.py`
first, so run it through `discover` rather than on its own.

`tests/test_portability.py` covers the constraints above. It rejects
`del` on any bytearray buffer and any `os.environ` use in the portable modules —
statically, so it still guards CI, where no MicroPython build exists — and then
runs `tests/portability_probe.py` under each of `micropython`,
`micropython.exe`, and `circuitpython` found on `PATH`, skipping when none are.
The probe selects a backend, exercises the environment helpers, and writes PCM on
both latency profiles, since these idioms import cleanly everywhere and only
raise on first use. Run it by hand against one interpreter with:

```bash
micropython tests/portability_probe.py
```

`tests/test_esp32_p4_audio.py` and `tests/test_tab5_audio.py` simulate the MCU
boards that build I2S devices directly, with fake `machine`, I2C and codecs, so
the profile-to-`ibuf` mapping is checked without hardware. When editing those
board configs, clear `__pycache__` before trusting a re-run: WSL mtimes are
coarse enough that an edit in the same second as the previous run can leave stale
bytecode in place and a real failure looking green.

## ⚠️ Troubleshooting

| Symptom | Likely cause |
|---------|--------------|
| Audio turns to slow motion or silence after ~60 s | The host sink degraded. Check `device.recycles` — if it is not increasing, `service()` is not being called |
| PCM stops with data still buffered | No `service()` tick; partial writes never reach SDL |
| Callers hang waiting for playback to finish | Something is reporting activity from pause state instead of `queued_size()` |
| UI freezes for a second or more during playback | A device close/open is running on the caller's thread |
| Clipped or missing audio right after a recovery | `device.lost_bytes` is above 0; the shadow buffer is too small for the queue |
| `reopen after stall failed` on stderr, then silence | Another process holds the sink. `lost_bytes` records what could not be played; the next write reopens |
| An asyncio app stops ticking during playback | Something on the async path is blocking rather than awaiting — check `awrite` |
| Playback wedges within ~30 s under pygame-ce | A second output device is open — most likely `pygame.mixer` was reinitialized |
| First sound never plays under PyScript | The `AudioContext` is still suspended, awaiting a user gesture |

## The WSLg / PulseAudio sink defect

The recovery machinery in both SDL backends exists for one host bug. WSLg's
PulseAudio RDP sink degrades after roughly a minute of continuous playback: it
keeps accepting data, but consumes it at 5–30 % of realtime while SDL still
reports the device as playing.

It is not specific to these backends — `paplay` of a 150 s file stalls the same
way, while a 60 s file completes — and closing and reopening the device is the
only thing that restores realtime playback. Pausing and unpausing the same device
does not. Because the sink trickles instead of freezing, detection has to be a
rate over a window; "no progress at all for N ms" almost never becomes true.

Delete this machinery when hosts can sustain long playback, not before. The
counters make that easy to check: run several minutes of continuous audio and see
whether `recycles` stays at zero.
