# SPDX-FileCopyrightText: 2024 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Load icon / image assets into ``FrameBuffer`` instances."""

from graphics import FrameBuffer


def _from_module(mod):
    """Prefer ``FrameBuffer.from_module``; fall back for native cmod builds."""
    from_module = getattr(FrameBuffer, "from_module", None)
    if from_module is not None:
        return from_module(mod)
    buf = mod.BITMAP
    if not isinstance(buf, bytearray):
        buf = bytearray(buf)
    return FrameBuffer(buf, mod.WIDTH, mod.HEIGHT, mod.FORMAT)


def load_framebuffer(value):
    """Load a framebuffer from a package module name or filesystem path.

    Package icons are plain Python modules under ``pdwidgets.icons`` (e.g.
    ``pdwidgets.icons.home_filled_36dp``) with ``WIDTH``, ``HEIGHT``,
    ``FORMAT``, and ``BITMAP`` (prefer a writable ``bytearray``). Filesystem
    ``.pbm`` / ``.bmp`` / ``.pgm`` paths still use ``FrameBuffer.from_file``.
    """
    if not isinstance(value, str):
        raise TypeError("icon value must be a module name or file path string")

    # Dotted import path (no path separators) — preferred for shipped icons.
    if "/" not in value and "\\" not in value and "." in value and not value.endswith(
        (".pbm", ".bmp", ".pgm", ".py")
    ):
        mod = __import__(value, None, None, ("BITMAP", "WIDTH", "HEIGHT", "FORMAT"))
        return _from_module(mod)

    if value.endswith(".py"):
        # Filesystem .py module (authoring / absolute path).
        try:
            import importlib.util
        except ImportError as exc:  # pragma: no cover — CPython authoring helper
            raise ValueError(f"Cannot load .py icon on this runtime: {value}") from exc
        stem = value.rsplit("/", 1)[-1].rsplit("\\", 1)[-1][:-3]
        spec = importlib.util.spec_from_file_location(stem, value)
        if spec is None or spec.loader is None:
            raise ValueError(f"Cannot load icon module {value!r}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return _from_module(mod)

    return FrameBuffer.from_file(value)
