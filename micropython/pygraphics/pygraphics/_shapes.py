# SPDX-FileCopyrightText: 2018 Kattni Rembor for Adafruit Industries, 2024 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""
`pygraphics._shapes`
====================================================
Graphics primitives for drawing on a canvas.

Heavily modified from gfx.py at:
https://github.com/adafruit/Adafruit_CircuitPython_GFX
* Author(s): Kattni Rembor, Tony DiCola, Jonah Yolles-Murphy, based on code by Phil Burgess

Implementation Notes
--------------------
.pixel(), .fill_rect(), .fill() and .blit_rect() will be called from the canvas object if the canvas
object has these methods.

``blit_rect`` / ``gradient_rect`` follow ``canvas.format``: RGB565, RGB888, and GS8
(contiguous), plus greyscale/mono scalar gradients. Bit-packed formats have no
raw ``blit_rect`` row path.

"""

from ._area import Area
from ._blit_hooks import (
    blit_rect_dispatch,
    canvas_accepts_blit_transparent,
    canvas_bytes_per_pixel,
    key_to_bytes,
    try_fast_framebuffer_blit,
)
from ._trig import _DEG_TO_U, rotate_q15, sin_cos_rad, sin_cos_u

try:
    import micropython as _mp

    _native_deco = getattr(_mp, "native", None)
except ImportError:  # bare CPython
    _native_deco = None


def _mp_native(f):
    """Apply ``@micropython.native`` when the port provides it."""
    return _native_deco(f) if _native_deco is not None else f


@_mp_native
def _set_pixel(canvas, x, y, c):
    """Set a pixel without allocating an :class:`Area` (hot-path helper)."""
    put = getattr(canvas, "pixel", None)
    if put is not None:
        put(x, y, c)
        return
    rgb565_color = (c & 0xFFFF).to_bytes(2, "little")
    canvas.buffer[(y * canvas.width + x) * 2 : (y * canvas.width + x) * 2 + 2] = rgb565_color


def _do_fill_rect(canvas, x, y, w, h, c):
    """Fill a rectangle without allocating an :class:`Area`."""
    fill_m = getattr(canvas, "fill_rect", None)
    if fill_m is not None:
        fill_m(x, y, w, h, c)
        return
    put = getattr(canvas, "pixel", None)
    if put is not None:
        for j in range(y, y + h):
            for i in range(x, x + w):
                put(i, j, c)
        return
    for j in range(y, y + h):
        for i in range(x, x + w):
            _set_pixel(canvas, i, j, c)


def _do_fill(canvas, c):
    fill_m = getattr(canvas, "fill", None)
    if fill_m is not None:
        fill_m(c)
        return
    _do_fill_rect(canvas, 0, 0, canvas.width, canvas.height, c)


def arc(canvas, x, y, r, a0, a1, c):
    """
    Arc drawing function.  Will draw a single pixel wide arc with a radius r
    centered at x, y from a0 to a1.

    Args:
        x (int): X-coordinate of the arc's center.
        y (int): Y-coordinate of the arc's center.
        r (int): Radius of the arc.
        a0 (float): Starting angle in degrees.
        a1 (float): Ending angle in degrees.
        c (int): color.

    Returns:
        (Area): The bounding box of the arc.
    """
    # 256-unit turn (Q15 LUT); ~1.4° per step — same algorithm in C gfx_shapes_arc.
    u0 = int(a0 * _DEG_TO_U)
    u1 = int(a1 * _DEG_TO_U)
    s0, c0 = sin_cos_u(u0)
    x0 = x + ((r * c0) >> 15)
    y0 = y + ((r * s0) >> 15)
    step = 1 if u1 > u0 else -1
    x_min = x_max = x0
    y_min = y_max = y0
    u = u0
    while (step > 0 and u < u1) or (step < 0 and u > u1):
        u += step
        s1, c1 = sin_cos_u(u)
        x1 = x + ((r * c1) >> 15)
        y1 = y + ((r * s1) >> 15)
        line(canvas, x0, y0, x1, y1, c)
        if x0 < x_min:
            x_min = x0
        if x1 < x_min:
            x_min = x1
        if x0 > x_max:
            x_max = x0
        if x1 > x_max:
            x_max = x1
        if y0 < y_min:
            y_min = y0
        if y1 < y_min:
            y_min = y1
        if y0 > y_max:
            y_max = y0
        if y1 > y_max:
            y_max = y1
        x0 = x1
        y0 = y1
    return Area(x_min, y_min, x_max - x_min, y_max - y_min)


def blit(canvas, source, x, y, key=-1, palette=None):
    """
    Copy a source buffer or sprite onto a canvas.

    This is useful for compositing an off-screen frame into the live display,
    for scrolling text and sprite animations, and for drawing pre-rendered tiles
    or bitmaps. The returned area is the region that was written so that it can
    be treated as a dirty rectangle.

    Args:
        source (FrameBuffer): Source framebuffer or canvas-like object.
        x (int): X-coordinate to blit to.
        y (int): Y-coordinate to blit to.
        key (int): Key value for transparency (default: -1).
        palette (Palette): Palette object for color translation (default: None).

    Returns:
        Area: The bounding box of the blitted area.
    """
    fast = try_fast_framebuffer_blit(canvas, source, x, y, key, palette)
    if fast is not None:
        return fast

    from ._blit_hooks import clip_blit_bounds

    clipped = clip_blit_bounds(canvas, source, x, y)
    if clipped is None:
        return None

    x0, y0, w, h, src_x, src_y = clipped
    x0end = x0 + w
    y0end = y0 + h

    for cy0 in range(y0, y0end):
        cx1 = src_x + (cy0 - y0)
        src_row = src_y + (cy0 - y0)
        for cx0 in range(x0, x0end):
            col = source.pixel(cx1, src_row)
            if palette:
                col = palette.pixel(col, 0)
            if col != key:
                _set_pixel(canvas, cx0, cy0, col)
            cx1 += 1
    return Area(x0, y0, w, h)


def blit_rect(canvas, buf, x, y, w, h):
    """
    Blit a rectangular area from a buffer to the canvas.  Uses the canvas's blit_rect method if available,
    otherwise writes directly to the buffer.

    Args:
        buf (memoryview): Buffer to blit. Must already be byte-swapped if necessary.
        x (int): X-coordinate to blit to.
        y (int): Y-coordinate to blit to.
        w (int): Width of the area to blit.
        h (int): Height of the area to blit.

    Returns:
        (Area): The bounding box of the blitted area.
    """
    return blit_rect_dispatch(canvas, buf, x, y, w, h)


def blit_transparent(canvas, buf, x, y, w, h, key):
    """
    Blit a buffer with transparency.

    Args:
        buf (memoryview): Buffer to blit.
        x (int): X-coordinate to blit to.
        y (int): Y-coordinate to blit to.
        w (int): Width of the area to blit.
        h (int): Height of the area to blit.
        key (int): Key value for transparency.

    Returns:
        (Area): The bounding box of the blitted area.
    """
    if canvas_accepts_blit_transparent(canvas):
        canvas.blit_transparent(buf, x, y, w, h, key)
        return Area(x, y, w, h)

    BPP = canvas_bytes_per_pixel(canvas)
    if BPP <= 0:
        BPP = getattr(canvas, "color_depth", 16) // 8 or 2
    key_bytes = key_to_bytes(key, BPP)
    stride = w * BPP
    for j in range(h):
        rowstart = j * stride
        colstart = 0
        # iterate over each pixel looking for the first non-key pixel
        while colstart < stride:
            startoffset = rowstart + colstart
            if buf[startoffset : startoffset + BPP] != key_bytes:
                # found a non-key pixel
                # then iterate over each pixel looking for the next key pixel
                colend = colstart
                while colend < stride:
                    endoffset = rowstart + colend
                    if buf[endoffset : endoffset + BPP] == key_bytes:
                        break
                    colend += BPP
                # blit the non-key pixels
                blit_rect(
                    canvas,
                    buf[rowstart + colstart : rowstart + colend],
                    x + colstart // BPP,
                    y + j,
                    (colend - colstart) // BPP,
                    1,
                )
                colstart = colend
            else:
                colstart += BPP
    return Area(x, y, w, h)


def circle(canvas, x0, y0, r, c, f=False):
    """
    Draw a circle or filled disk centered at ``(x0, y0)``.

    This is a common primitive for buttons, status indicators, animated balls,
    and other UI ornaments. Pass ``f=True`` for a filled circle.

    Args:
        x0 (int): Center x coordinate.
        y0 (int): Center y coordinate.
        r (int): Radius.
        c (int): Color.
        f (bool): Fill the circle (default: ``False``).

    Returns:
        Area: The bounding box of the circle.
    """
    if f:
        return _fill_circle_helper(canvas, x0, y0, r, c, 0, 0)

    _circle_helper(canvas, x0, y0, r, c, 0, 0)
    return Area(x0 - r, y0 - r, 2 * r, 2 * r)


def _circle_helper(canvas, x0, y0, r, c, x_offset, y_offset):
    """
    Circle helper function.  Draws the 4 quadrants of a circle with center at x0, y0 and the specified r
    separated by the specified x_offset and y_offset.  Draws a circle if offsets are 0.  Draws the 4 corners of
    a round_rect if an offset is greater than 0.
    """
    f = 1 - r
    ddF_x = 1
    ddF_y = -2 * r
    x = 0
    y = r
    while x < y:
        if f >= 0:
            y -= 1
            ddF_y += 2
            f += ddF_y
        x += 1
        ddF_x += 2
        f += ddF_x
        offset_x = x + x_offset
        offset_y = y + y_offset
        _set_pixel(canvas, x0 + offset_x - 1, y0 - offset_y, c)  # 90 to 45
        _set_pixel(canvas, x0 - offset_x, y0 - offset_y, c)  # 90 to 135
        _set_pixel(canvas, x0 + offset_x - 1, y0 + offset_y - 1, c)  # 270 to 315
        _set_pixel(canvas, x0 - offset_x, y0 + offset_y - 1, c)  # 270 to 225
        offset_x = y + x_offset
        offset_y = x + y_offset
        _set_pixel(canvas, x0 + offset_x - 1, y0 + offset_y - 1, c)  # 0 to 315
        _set_pixel(canvas, x0 - offset_x, y0 + offset_y - 1, c)  # 180 to 225
        _set_pixel(canvas, x0 + offset_x - 1, y0 - offset_y, c)  # 0 to 45
        _set_pixel(canvas, x0 - offset_x, y0 - offset_y, c)  # 180 to 135


def _fill_circle_helper(canvas, x0, y0, r, c, x_offset, y_offset):
    """
    Fill circle helper function.  Draws the 4 quadrants of a filled circle with center at x0, y0 and the
    specified r separated by the specified x_offset and y_offset.  Fills a circle if offsets are 0.  Fills the
    4 corners of a filled round_rect if an offset is greater than 0.
    """
    # vline(canvas, x0, y0 - r, 2 * r + 1, c)
    f = 1 - r
    ddF_x = 1
    ddF_y = -2 * r
    x = 0
    y = r
    while x < y:
        if f >= 0:
            y -= 1
            ddF_y += 2
            f += ddF_y
        x += 1
        ddF_x += 2
        f += ddF_x
        offset_x = x + x_offset
        offset_y = y + y_offset
        vline(canvas, x0 - offset_x, y0 - offset_y, 2 * offset_y, c)
        vline(canvas, x0 + offset_x - 1, y0 - offset_y, 2 * offset_y, c)
        offset_x = y + x_offset
        offset_y = x + y_offset
        vline(canvas, x0 - offset_x, y0 - offset_y, 2 * offset_y, c)
        vline(canvas, x0 + offset_x - 1, y0 - offset_y, 2 * offset_y, c)

    return Area(x0 - r, y0 - r, 2 * r, 2 * r)


def ellipse(canvas, x0, y0, r1, r2, c, f=False, m=0b1111, w=None, h=None):
    """
    Midpoint ellipse algorithm
    Draw an ellipse at the given location. Radii r1 and r2 define the geometry; equal values cause a
    circle to be drawn. The c parameter defines the color.

    The optional f parameter can be set to True to fill the ellipse. Otherwise just a one pixel outline
    is drawn.

    The optional m parameter enables drawing to be restricted to certain quadrants of the ellipse.
    The LS four bits determine which quadrants are to be drawn, with bit 0 specifying Q1, b1 Q2,
    b2 Q3 and b3 Q4. Quadrants are numbered counterclockwise with Q1 being top right.

    Args:
        x0 (int): Center x coordinate
        y0 (int): Center y coordinate
        r1 (int): x radius
        r2 (int): y radius
        c (int): color
        f (bool): Fill the ellipse (default: False)
        m (int): Bitmask to determine which quadrants to draw (default: 0b1111)
        w (int): Width of the ellipse (default: None)
        h (int): Height of the ellipse (default: None)

    Returns:
        (Area): The bounding box of the ellipse.
    """
    if r1 < 1 or r2 < 1:
        return

    x_side = w - 2 * r1 if w else 0
    y_side = h - 2 * r2 if h else 0
    x_offset = x_side // 2 if w else 0
    y_offset = y_side // 2 if h else 0

    if f:
        if y_offset > 0:
            fill_rect(canvas, x0 - w // 2, y0 - y_offset, w, y_side, c)
        if x_offset > 0:
            fill_rect(canvas, x0 - x_offset, y0 - h // 2, x_side, r1, c)
            fill_rect(canvas, x0 - x_offset, y0 + h // 2 - r1, x_side, r1, c)

    if x_offset > 0:
        hline(canvas, x0 - x_offset, y0 - h // 2, x_side, c)
        hline(canvas, x0 - x_offset, y0 + h // 2, x_side, c)
    if y_offset > 0:
        vline(canvas, x0 - w // 2, y0 - y_offset, y_side, c)
        vline(canvas, x0 + w // 2, y0 - y_offset, y_side, c)

    a2 = r1 * r1
    b2 = r2 * r2
    fa2 = 4 * a2
    fb2 = 4 * b2

    x1 = r1
    y1 = 0
    sigma = 2 * a2 + b2 * (1 - 2 * r1)
    while a2 * y1 <= b2 * x1:
        if f:
            if m & 0x1:
                hline(canvas, x0 + x_offset, y0 - y1 - y_offset, x1, c)
            if m & 0x2:
                hline(canvas, x0 - x1 - x_offset, y0 - y1 - y_offset, x1, c)
            if m & 0x4:
                hline(canvas, x0 - x1 - x_offset, y0 + y1 + y_offset, x1, c)
            if m & 0x8:
                hline(canvas, x0 + x_offset, y0 + y1 + y_offset, x1, c)
        else:
            if m & 0x1:
                _set_pixel(canvas, x0 + x1 + x_offset, y0 - y1 - y_offset, c)
            if m & 0x2:
                _set_pixel(canvas, x0 - x1 - x_offset, y0 - y1 - y_offset, c)
            if m & 0x4:
                _set_pixel(canvas, x0 - x1 - x_offset, y0 + y1 + y_offset, c)
            if m & 0x8:
                _set_pixel(canvas, x0 + x1 + x_offset, y0 + y1 + y_offset, c)
        if sigma >= 0:
            sigma += fb2 * (1 - x1)
            x1 -= 1
        sigma += a2 * ((4 * y1) + 6)
        y1 += 1

    x1 = 0
    y1 = r2
    sigma = 2 * b2 + a2 * (1 - 2 * r2)
    while b2 * x1 <= a2 * y1:
        if f:
            if m & 0x1:
                hline(canvas, x0 + x_offset, y0 - y1 - y_offset, x1, c)
            if m & 0x2:
                hline(canvas, x0 - x1 - x_offset, y0 - y1 - y_offset, x1, c)
            if m & 0x4:
                hline(canvas, x0 - x1 - x_offset, y0 + y1 + y_offset, x1, c)
            if m & 0x8:
                hline(canvas, x0 + x_offset, y0 + y1 + y_offset, x1, c)
        else:
            if m & 0x1:
                _set_pixel(canvas, x0 + x1 + x_offset, y0 - y1 - y_offset, c)
            if m & 0x2:
                _set_pixel(canvas, x0 - x1 - x_offset, y0 - y1 - y_offset, c)
            if m & 0x4:
                _set_pixel(canvas, x0 - x1 - x_offset, y0 + y1 + y_offset, c)
            if m & 0x8:
                _set_pixel(canvas, x0 + x1 + x_offset, y0 + y1 + y_offset, c)
        if sigma >= 0:
            sigma += fa2 * (1 - y1)
            y1 -= 1
        sigma += b2 * ((4 * x1) + 6)
        x1 += 1
    return Area(x0 - r1 - x_offset, y0 - r2 - y_offset, 2 * (r1 + x_offset), 2 * (r2 + y_offset))


def fill(canvas, c):
    """
    Fill the entire canvas with a solid color.

    This is the typical first step for each frame: clear the previous scene,
    then draw the next frame on top of it.

    Args:
        c (int): Color.

    Returns:
        Area: The bounding box of the filled area.
    """
    _do_fill(canvas, c)
    return Area(0, 0, canvas.width, canvas.height)


def fill_rect(canvas, x, y, w, h, c):
    """
    Draw a filled rectangle.

    Use this for backgrounds, panels, status bars, and other simple UI blocks.
    It is also the workhorse for clipping and partial redraw operations.

    Args:
        x (int): X-coordinate of the top-left corner.
        y (int): Y-coordinate of the top-left corner.
        w (int): Width of the rectangle.
        h (int): Height of the rectangle.
        c (int): Color.

    Returns:
        Area: The bounding box of the filled area.
    """
    if y < -h or y > canvas.height or x < -w or x > canvas.width:
        return
    _do_fill_rect(canvas, x, y, w, h, c)
    return Area(x, y, w, h)


def _format_grey_max(fmt):
    from ._framebuf_plus import GS2_HMSB, GS4_HMSB, GS8, MONO_HLSB, MONO_HMSB, MONO_VLSB

    if fmt in (MONO_VLSB, MONO_HLSB, MONO_HMSB):
        return 1
    if fmt == GS2_HMSB:
        return 3
    if fmt == GS4_HMSB:
        return 15
    if fmt == GS8:
        return 255
    return -1


def _gradient_lerp_color(fmt, c1, c2, t, span):
    grey_max = _format_grey_max(fmt)
    if grey_max >= 0:
        v = c1 + (c2 - c1) * t // span
        if v < 0:
            v = 0
        elif v > grey_max:
            v = grey_max
        return v
    from ._framebuf_plus import RGB888

    if fmt == RGB888:
        r1, g1, b1 = (c1 >> 16) & 0xFF, (c1 >> 8) & 0xFF, c1 & 0xFF
        r2, g2, b2 = (c2 >> 16) & 0xFF, (c2 >> 8) & 0xFF, c2 & 0xFF
        r = r1 + (r2 - r1) * t // span
        g = g1 + (g2 - g1) * t // span
        b = b1 + (b2 - b1) * t // span
        return (r & 0xFF) << 16 | (g & 0xFF) << 8 | (b & 0xFF)
    r1, g1, b1 = (c1 >> 8) & 0xF8, (c1 >> 3) & 0xFC, (c1 << 3) & 0xF8
    r2, g2, b2 = (c2 >> 8) & 0xF8, (c2 >> 3) & 0xFC, (c2 << 3) & 0xF8
    r = r1 + (r2 - r1) * t // span
    g = g1 + (g2 - g1) * t // span
    b = b1 + (b2 - b1) * t // span
    return (r & 0xF8) << 8 | (g & 0xFC) << 3 | (b & 0xF8) >> 3


def gradient_rect(canvas, x, y, w, h, c1, c2=None, vertical=True):
    """
    Fill a rectangle with a vertical or horizontal color ramp.

    This is useful for scenery, backgrounds, and other effects where a smooth
    transition looks better than a flat fill. The pydevices-examples applications use it for
    animated skies and other stylized backdrops.

    Args:
        x (int): X-coordinate of the top-left corner.
        y (int): Y-coordinate of the top-left corner.
        w (int): Width of the rectangle.
        h (int): Height of the rectangle.
        c1 (int): Color for the top or left edge (format-native).
        c2 (int): Color for the bottom or right edge. If omitted or equal to
            ``c1``, the helper falls back to :func:`fill_rect`.
        vertical (bool): If ``True``, draw a vertical gradient; otherwise a horizontal one.

    Returns:
        Area: The bounding box of the filled area.
    """
    if c2 is None or c1 == c2:
        return fill_rect(canvas, x, y, w, h, c1)
    from ._framebuf_plus import RGB565

    fmt = getattr(canvas, "format", RGB565)
    if vertical:
        for j in range(h):
            c = _gradient_lerp_color(fmt, c1, c2, j, h)
            _do_fill_rect(canvas, x, y + j, w, 1, c)
    else:
        for i in range(w):
            c = _gradient_lerp_color(fmt, c1, c2, i, w)
            _do_fill_rect(canvas, x + i, y, 1, h, c)
    return Area(x, y, w, h)


def hline(canvas, x0, y0, w, c):
    """
    Horizontal line drawing function.  Will draw a single pixel wide line.

    Args:
        x0 (int): X-coordinate of the start of the line.
        y0 (int): Y-coordinate of the start of the line.
        w (int): Width of the line.
        c (int): color.

    Returns:
        (Area): The bounding box of the line.
    """
    if y0 < 0 or y0 > canvas.height or x0 < -w or x0 > canvas.width:
        return
    _do_fill_rect(canvas, x0, y0, w, 1, c)
    return Area(x0, y0, w, 1)


def line(canvas, x0, y0, x1, y1, c):
    """
    Draw a single-pixel line from ``(x0, y0)`` to ``(x1, y1)``.

    Use this for outlines, rulers, charts, and small UI connectors where a solid
    stroke is more appropriate than a filled shape.

    Args:
        x0 (int): X-coordinate of the start of the line.
        y0 (int): Y-coordinate of the start of the line.
        x1 (int): X-coordinate of the end of the line.
        y1 (int): Y-coordinate of the end of the line.
        c (int): Color.

    Returns:
        Area: The bounding box of the line.
    """
    bx0, by0, bx1, by1 = x0, y0, x1, y1
    if x0 == x1:
        y = y0 if y0 < y1 else y1
        return vline(canvas, x0, y, abs(y1 - y0) + 1, c)
    if y0 == y1:
        x = x0 if x0 < x1 else x1
        return hline(canvas, x, y0, abs(x1 - x0) + 1, c)

    steep = abs(y1 - y0) > abs(x1 - x0)
    if steep:
        x0, y0 = y0, x0
        x1, y1 = y1, x1
    if x0 > x1:
        x0, x1 = x1, x0
        y0, y1 = y1, y0
    dx = x1 - x0
    dy = abs(y1 - y0)
    err = dx // 2
    ystep = 1 if y0 < y1 else -1
    put = getattr(canvas, "pixel", None)
    while x0 <= x1:
        if steep:
            if put is not None:
                put(y0, x0, c)
            else:
                _set_pixel(canvas, y0, x0, c)
        elif put is not None:
            put(x0, y0, c)
        else:
            _set_pixel(canvas, x0, y0, c)
        err -= dy
        if err < 0:
            y0 += ystep
            err += dx
        x0 += 1
    left = bx0 if bx0 < bx1 else bx1
    top = by0 if by0 < by1 else by1
    return Area(left, top, abs(bx1 - bx0), abs(by1 - by0))


def pixel(canvas, x, y, c):
    """
    Draw a single pixel at the specified x, y location.  Uses the canvas's pixel method if available,
    otherwise writes directly to the buffer.

    Args:
        x (int): X-coordinate of the pixel.
        y (int): Y-coordinate of the pixel.
        c (int): color.

    Returns:
        (Area): The bounding box of the pixel.
    """
    _set_pixel(canvas, x, y, c)
    return Area(x, y, 1, 1)


def _poly_xy_lists(coords):
    """Normalize ``coords`` to parallel ``xs``/``ys`` int lists (relative verts)."""
    if isinstance(coords, (list, tuple)) and coords and isinstance(coords[0], (list, tuple)):
        xs = [int(p[0]) for p in coords]
        ys = [int(p[1]) for p in coords]
        return xs, ys
    if len(coords) % 2 != 0:
        raise ValueError("coords must have an even number of elements")
    xs = [int(coords[i]) for i in range(0, len(coords), 2)]
    ys = [int(coords[i + 1]) for i in range(0, len(coords), 2)]
    return xs, ys


def _div_trunc(a, b):
    """C-like integer division (truncate toward zero)."""
    return int(a / b) if b else 0


def poly(canvas, x, y, coords, c, f=False):
    """
    Given a list of coordinates, draw an arbitrary (convex or concave) closed polygon at the given x, y location
    using the given color.

    The coords must be specified as an array of integers, e.g. array('h', [x0, y0, x1, y1, ... xn, yn]) or a
    list or tuple of points, e.g. [(x0, y0), (x1, y1), ... (xn, yn)].

    The optional f parameter can be set to True to fill the polygon. Otherwise, just a one-pixel outline is drawn.

    Args:
        x (int): X-coordinate of the polygon's position.
        y (int): Y-coordinate of the polygon's position.
        coords (list): List of coordinates.
        c (int): color.
        f (bool): Fill the polygon (default: False).

    Returns:
        (Area): The bounding box of the polygon.
    """
    xs, ys = _poly_xy_lists(coords)
    n = len(xs)
    if n < 3:
        raise ValueError("polygon must have at least 3 vertices")

    left = right = xs[0]
    top = bottom = ys[0]
    for i in range(1, n):
        if xs[i] < left:
            left = xs[i]
        if xs[i] > right:
            right = xs[i]
        if ys[i] < top:
            top = ys[i]
        if ys[i] > bottom:
            bottom = ys[i]

    if f:
        # Integer scanline fill — same node formula as gfx_shapes_poly (C).
        for row in range(top, bottom + 1):
            nodes = []
            for j in range(n):
                j2 = (j + 1) % n
                px1, py1 = xs[j], ys[j]
                px2, py2 = xs[j2], ys[j2]
                if py1 != py2 and ((py1 > row and py2 <= row) or (py1 <= row and py2 > row)):
                    node = _div_trunc(
                        32 * px1
                        + _div_trunc(32 * (px2 - px1) * (row - py1), py2 - py1)
                        + 16,
                        32,
                    )
                    nodes.append(node)
                elif row == (py1 if py1 > py2 else py2):
                    if py1 < py2:
                        _set_pixel(canvas, x + px2, y + py2, c)
                    elif py2 < py1:
                        _set_pixel(canvas, x + px1, y + py1, c)
                    else:
                        line(canvas, x + px1, y + py1, x + px2, y + py2, c)
            if not nodes:
                continue
            nodes.sort()
            for k in range(0, len(nodes) - 1, 2):
                _do_fill_rect(
                    canvas, x + nodes[k], y + row, (nodes[k + 1] - nodes[k]) + 1, 1, c
                )
    else:
        for i in range(n):
            i2 = (i + 1) % n
            line(canvas, x + xs[i], y + ys[i], x + xs[i2], y + ys[i2], c)

    return Area(x + left, y + top, right - left, bottom - top)


def polygon(canvas, points, x, y, color, angle=0, center_x=0, center_y=0):
    """
    Draw a polygon on the canvas.

    Args:
        points (list): List of points to draw.
        x (int): X-coordinate of the polygon's position.
        y (int): Y-coordinate of the polygon's position.
        color (int): color.
        angle (float): Rotation angle in radians (default: 0).
        center_x (int): X-coordinate of the rotation center (default: 0).
        center_y (int): Y-coordinate of the rotation center (default: 0).

    Raises:
        ValueError: If the polygon has less than 3 points.

    Returns:
        (Area): The bounding box of the polygon.
    """
    # MIT License
    # Copyright (c) 2024 Brad Barnett
    # Copyright (c) 2020-2023 Russ Hughes
    # Copyright (c) 2019 Ivan Belokobylskiy
    if len(points) < 3:
        raise ValueError("Polygon must have at least 3 points.")

    if angle:
        sin_a, cos_a = sin_cos_rad(angle)
        rx0, ry0 = rotate_q15(points[0][0], points[0][1], center_x, center_y, sin_a, cos_a)
        prev_x = x + rx0
        prev_y = y + ry0
    else:
        prev_x = x + int(points[0][0])
        prev_y = y + int(points[0][1])
    left = right = prev_x
    top = bottom = prev_y

    for i in range(1, len(points)):
        if angle:
            rx, ry = rotate_q15(points[i][0], points[i][1], center_x, center_y, sin_a, cos_a)
            cur_x = x + rx
            cur_y = y + ry
        else:
            cur_x = x + int(points[i][0])
            cur_y = y + int(points[i][1])
        line(canvas, prev_x, prev_y, cur_x, cur_y, color)
        if cur_x < left:
            left = cur_x
        if cur_x > right:
            right = cur_x
        if cur_y < top:
            top = cur_y
        if cur_y > bottom:
            bottom = cur_y
        prev_x = cur_x
        prev_y = cur_y
    return Area(left, top, right - left, bottom - top)


def rect(canvas, x0, y0, w, h, c, f=False):
    """
    Rectangle drawing function.  Will draw a single pixel wide rectangle starting at
    x0, y0 and extending w, h pixels.

    Args:
        x0 (int): X-coordinate of the top-left corner of the rectangle.
        y0 (int): Y-coordinate of the top-left corner of the rectangle.
        w (int): Width of the rectangle.
        h (int): Height of the rectangle.
        c (int): color.
        f (bool): Fill the rectangle (default: False).

    Returns:
        (Area): The bounding box of the rectangle.
    """
    if f:
        return fill_rect(canvas, x0, y0, w, h, c)
    if y0 < -h or y0 > canvas.height or x0 < -w or x0 > canvas.width:
        return
    hline(canvas, x0, y0, w, c)
    hline(canvas, x0, y0 + h - 1, w, c)
    vline(canvas, x0, y0, h, c)
    vline(canvas, x0 + w - 1, y0, h, c)
    return Area(x0, y0, w, h)


def round_rect(canvas, x0, y0, w, h, r, c, f=False):
    """
    Rounded rectangle drawing function.  Will draw a single pixel wide rounded rectangle starting at
    x0, y0 and extending w, h pixels with the specified radius.

    Args:
        x0 (int): X-coordinate of the top-left corner of the rectangle.
        y0 (int): Y-coordinate of the top-left corner of the rectangle.
        w (int): Width of the rectangle.
        h (int): Height of the rectangle.
        r (int): Radius of the corners.
        c (int): color.
        f (bool): Fill the rectangle (default: False).

    Returns:
        (Area): The bounding box of the rectangle.
    """
    # If the radius is 0, just draw a rectangle
    if r == 0:
        return rect(canvas, x0, y0, w, h, c, f)

    # If filled, draw the rounded rectangle using the _fill_round_rect function
    if f:
        return _fill_round_rect(canvas, x0, y0, w, h, r, c)

    # ensure that the r will only ever half of the shortest side or less
    r = int(min(r, w / 2, h / 2))

    hline(canvas, x0 + r, y0, w - 2 * r, c)  # top
    hline(canvas, x0 + r, y0 + h - 1, w - 2 * r, c)  # bottom
    vline(canvas, x0, y0 + r, h - 2 * r, c)  # left
    vline(canvas, x0 + w - 1, y0 + r, h - 2 * r, c)  # right
    _circle_helper(canvas, x0 + w // 2, y0 + h // 2, r, c, w // 2 - r, h // 2 - r)
    return Area(x0, y0, w, h)


def _fill_round_rect(canvas, x0, y0, w, h, r, c):
    """
    Filled rounded rectangle drawing function.  Will draw a filled rounded rectangle starting at
    x0, y0 and extending w, h pixels with the specified radius.
    """

    # ensure that the r will only ever be half of the shortest side or less
    r = int(min(r, w / 2, h / 2))
    fill_rect(canvas, x0 + r, y0, w - 2 * r, h, c)  # center
    _fill_circle_helper(canvas, x0 + w // 2, y0 + h // 2, r, c, w // 2 - r, h // 2 - r)
    return Area(x0, y0, w, h)


def triangle(canvas, x0, y0, x1, y1, x2, y2, c, f=False):
    # pylint: disable=too-many-arguments
    """
    Triangle drawing function.  Draws a single pixel wide triangle with vertices at
    (x0, y0), (x1, y1), and (x2, y2).

    Args:
        x0 (int): X-coordinate of the first vertex.
        y0 (int): Y-coordinate of the first vertex.
        x1 (int): X-coordinate of the second vertex.
        y1 (int): Y-coordinate of the second vertex.
        x2 (int): X-coordinate of the third vertex.
        y2 (int): Y-coordinate of the third vertex.
        c (int): color.
        f (bool): Fill the triangle (default: False).

    Returns:
        (Area): The bounding box of the triangle.
    """
    if f:
        return _fill_triangle(canvas, x0, y0, x1, y1, x2, y2, c)
    line(canvas, x0, y0, x1, y1, c)
    line(canvas, x1, y1, x2, y2, c)
    line(canvas, x2, y2, x0, y0, c)
    left = min(x0, x1, x2)
    top = min(y0, y1, y2)
    right = max(x0, x1, x2)
    bottom = max(y0, y1, y2)
    return Area(left, top, right - left, bottom - top)


def _fill_triangle(canvas, x0, y0, x1, y1, x2, y2, c):
    # pylint: disable=too-many-arguments
    """
    Filled triangle drawing function.  Will draw a filled triangle with vertices at
    (x0, y0), (x1, y1), and (x2, y2).
    """
    if y0 > y1:
        y0, y1 = y1, y0
        x0, x1 = x1, x0
    if y1 > y2:
        y2, y1 = y1, y2
        x2, x1 = x1, x2
    if y0 > y1:
        y0, y1 = y1, y0
        x0, x1 = x1, x0
    a = 0
    b = 0
    last = 0
    if y0 == y2:
        a = x0
        b = x0
        if x1 < a:
            a = x1
        elif x1 > b:
            b = x1
        if x2 < a:
            a = x2
        elif x2 > b:
            b = x2
        hline(canvas, a, y0, b - a + 1, c)
        return
    dx01 = x1 - x0
    dy01 = y1 - y0
    dx02 = x2 - x0
    dy02 = y2 - y0
    dx12 = x2 - x1
    dy12 = y2 - y1
    if dy01 == 0:
        dy01 = 1
    if dy02 == 0:
        dy02 = 1
    if dy12 == 0:
        dy12 = 1
    sa = 0
    sb = 0
    y = y0
    last = y1 - 1 if y0 == y1 else y1
    while y <= last:
        a = x0 + sa // dy01
        b = x0 + sb // dy02
        sa += dx01
        sb += dx02
        if a > b:
            a, b = b, a
        hline(canvas, a, y, b - a + 1, c)
        y += 1
    sa = dx12 * (y - y1)
    sb = dx02 * (y - y0)
    while y <= y2:
        a = x1 + sa // dy12
        b = x0 + sb // dy02
        sa += dx12
        sb += dx02
        if a > b:
            a, b = b, a
        hline(canvas, a, y, b - a + 1, c)
        y += 1
    left = min(x0, x1, x2)
    top = min(y0, y1, y2)
    right = max(x0, x1, x2)
    bottom = max(y0, y1, y2)
    return Area(left, top, right - left, bottom - top)


def vline(canvas, x0, y0, h, c):
    """
    Horizontal line drawing function.  Will draw a single pixel wide line.

    Args:
        x0 (int): X-coordinate of the start of the line.
        y0 (int): Y-coordinate of the start of the line.
        h (int): Height of the line.
        c (int): color.

    Returns:
        (Area): The bounding box of the line.
    """
    if y0 < -h or y0 > canvas.height or x0 < 0 or x0 > canvas.width:
        return
    _do_fill_rect(canvas, x0, y0, 1, h, c)
    return Area(x0, y0, 1, h)
