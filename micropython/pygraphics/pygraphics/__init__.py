"""
pygraphics — cross-platform 2D drawing for *Python.

Extends MicroPython's ``framebuf`` with shape helpers, fonts, image loaders, and
``Area`` bounding boxes for partial updates.  On CPython and CircuitPython the
built-in pure-Python ``framebuf`` fallback is used automatically.

Framebuffer format constants (``FrameBuffer`` ``format`` argument):

* ``MONO_VLSB``, ``MONO_HLSB``, ``MONO_HMSB`` — 1-bit monochrome
* ``GS2_HMSB``, ``GS4_HMSB``, ``GS8`` — 2-, 4-, and 8-bit greyscale
* ``RGB565`` — 16-bit color (MicroPython ``framebuf``)
* ``RGB888`` — 24-bit color (pygraphics extension)

Quick start::

    import pygraphics

    fb = pygraphics.FrameBuffer(bytearray(16 * 16 * 2), 16, 16, pygraphics.RGB565)
    fb.fill(0)
    area = fb.fill_rect(1, 1, 6, 6, 0xFFFF)
    pygraphics.text8(fb, "Hi", 0, 0, 0xFFFF)
"""

from ._area import Area
from ._font import Font, text, text8, text14, text16
from ._framebuf_plus import (
    GS2_HMSB,
    GS4_HMSB,
    GS8,
    MONO_HLSB,
    MONO_HMSB,
    MONO_VLSB,
    RGB565,
    RGB888,
    FrameBuffer,
)
from ._shapes import (
    arc,
    blit,
    blit_rect,
    blit_transparent,
    circle,
    ellipse,
    fill,
    fill_rect,
    gradient_rect,
    hline,
    line,
    pixel,
    poly,
    polygon,
    rect,
    round_rect,
    triangle,
    vline,
)

# Optional / heavier helpers are loaded on first attribute access (MCU import cost).
_LAZY = {
    "BMP565": ("_bmp565", "BMP565"),
    "ClipContext": ("_clip", "ClipContext"),
    "ClippedCanvas": ("_clip", "ClippedCanvas"),
    "Draw": ("_draw", "Draw"),
    "bmp_to_framebuffer": ("_files", "bmp_to_framebuffer"),
    "export_framebuffer": ("_files", "export_framebuffer"),
    "load_image": ("_files", "load_image"),
    "pbm_to_framebuffer": ("_files", "pbm_to_framebuffer"),
    "pgm_to_framebuffer": ("_files", "pgm_to_framebuffer"),
    "save_image": ("_files", "save_image"),
}


def __getattr__(name):
    spec = _LAZY.get(name)
    if spec is None:
        raise AttributeError("module 'pygraphics' has no attribute {!r}".format(name))
    mod_name, attr = spec
    mod = __import__(__name__ + "." + mod_name, None, None, (attr,))
    value = getattr(mod, attr)
    globals()[name] = value
    return value


def implementation():
    """Return ``pygraphics_python`` (this package) vs ``native_cmod`` for the C module."""
    return "pygraphics_python"


__all__ = [
    "BMP565",
    "GS2_HMSB",
    "GS4_HMSB",
    "GS8",
    "MONO_HLSB",
    "MONO_HMSB",
    "MONO_VLSB",
    "RGB565",
    "RGB888",
    "Area",
    "ClipContext",
    "ClippedCanvas",
    "Draw",
    "Font",
    "FrameBuffer",
    "arc",
    "blit",
    "blit_rect",
    "blit_transparent",
    "bmp_to_framebuffer",
    "circle",
    "ellipse",
    "export_framebuffer",
    "fill",
    "fill_rect",
    "gradient_rect",
    "hline",
    "implementation",
    "line",
    "load_image",
    "pbm_to_framebuffer",
    "pgm_to_framebuffer",
    "pixel",
    "poly",
    "polygon",
    "rect",
    "round_rect",
    "save_image",
    "text",
    "text8",
    "text14",
    "text16",
    "triangle",
    "vline",
]
