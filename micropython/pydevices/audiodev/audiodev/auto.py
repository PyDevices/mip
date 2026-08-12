"""Optional host backend selection. Backends never import this module."""

import sys


def host_kind():
    try:
        import pyscript  # noqa: F401

        return "pyscript"
    except Exception:
        pass
    try:
        get_ipython()  # noqa: F821
        return "jupyter"
    except Exception:
        return "desktop"


def _pygame_available():
    try:
        import pygame  # noqa: F401

        return True
    except Exception:
        return False


def _uwin32_available():
    if sys.platform != "win32":
        return False
    try:
        import uwin32  # noqa: F401

        return True
    except Exception:
        return False


def select_backend():
    """Return ``web_audio``, ``win_audio``, ``pygame_audio``, or ``sdl2_audio``."""
    kind = host_kind()
    if kind == "pyscript":
        return "web_audio"
    if kind == "jupyter":
        return "sdl2_audio"
    if _uwin32_available():
        return "win_audio"
    if _pygame_available():
        return "pygame_audio"
    return "sdl2_audio"


def _impl(name, direction):
    if name == "web_audio":
        from audiodev import web_audio as mod
    elif name == "win_audio":
        from audiodev import win_audio as mod
    elif name == "pygame_audio":
        from audiodev import pygame_audio as mod
    else:
        from audiodev import sdl2_audio as mod
    return getattr(mod, direction)


def audio_out(format=None, **kwargs):
    """Construct playback via :func:`select_backend`. Forward kwargs unchanged."""
    return _impl(select_backend(), "audio_out")(format, **kwargs)


def audio_in(format=None, **kwargs):
    """Construct capture via :func:`select_backend`. Forward kwargs unchanged."""
    return _impl(select_backend(), "audio_in")(format, **kwargs)


def AutoAudio(format=None, **kwargs):
    """Convenience alias for :func:`audio_out`."""
    return audio_out(format, **kwargs)
