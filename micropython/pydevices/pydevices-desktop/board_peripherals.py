"""Lazy constructors for desktop non-UI devices. PERIPHERALS = lazy roles only."""

import sys

import boarddev

_FORMAT = None
_BACKEND = None

PERIPHERALS = frozenset({"audio_out", "audio_in"})


def _select_backend():
    global _BACKEND
    if _BACKEND is not None:
        return _BACKEND
    from audiodev.auto import select_backend

    _BACKEND = select_backend()
    if _BACKEND == "pygame_audio" and sys.platform == "win32":
        # See board_config.py for the full rationale: SDL2's default Windows
        # WASAPI backend glitches with pygame's small-chunk playback, and
        # DirectSound does not. Duplicated here because an app can init
        # board_peripherals without ever importing board_config (e.g.
        # examples/audio_out_test.py), and must land before the first SDL audio
        # init either way.
        #
        # Only pygame_audio. sdl2_audio queues whole buffers with
        # SDL_QueueAudio and never hit the glitch, and DirectSound keeps a
        # deeper buffer: measured on micropython.exe at latency="low", it holds
        # 185ms against WASAPI's 55ms, which is the difference between playable
        # and not for an interactive caller.
        from displaydev import env_get, env_set

        # Only when unset, so an explicit user choice still wins.
        if env_get("SDL_AUDIODRIVER") is None:
            env_set("SDL_AUDIODRIVER", "directsound")
    return _BACKEND


def _audio_format():
    global _FORMAT
    if _FORMAT is None:
        from audiodev import AudioFormat

        _FORMAT = AudioFormat(24000, 1, 16)
    return _FORMAT


def load_peripherals(ns):
    boarddev.bind_lazy(ns, sys.modules[__name__])


def audio_out(**kwargs):
    """Build the playback device. ``board_config.audio_out`` passes nothing.

    Keyword arguments go straight to the selected backend, which is why the
    three of them agree on names (``latency``, ``samples``, ``queue_ms``,
    ``coalesce_ms``, ``poll_ms``). An interactive caller asks for
    ``latency="low"``; the default stays buffered for throughput.
    """
    fmt = _audio_format()
    _select_backend()
    from audiodev.auto import audio_out as _audio_out

    return _audio_out(fmt, **kwargs)


def audio_in(**kwargs):
    """Build the capture device; see :func:`audio_out` for the keyword contract."""
    fmt = _audio_format()
    backend = _select_backend()
    from audiodev.auto import audio_in as _audio_in

    if backend == "sdl2_audio":
        # Shorter than the backend default: capture is consumed live here, so a
        # long queue only adds lag to whatever is listening.
        kwargs.setdefault("queue_ms", 150)
    return _audio_in(fmt, **kwargs)
