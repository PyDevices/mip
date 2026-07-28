# SPDX-FileCopyrightText: 2026 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Blit helpers for display-driver fast paths and clipping."""

from ._area import Area

_RGB565_BPP = 2


def canvas_bytes_per_pixel(canvas):
    """Contiguous bytes/pixel for blit_rect (0 = bit-packed / unsupported).

    Uses ``canvas.format`` when present; otherwise ``color_depth // 8``, then RGB565.
    """
    fmt = getattr(canvas, "format", None)
    if fmt is not None:
        from ._framebuf_plus import GS8, RGB565, RGB888

        if fmt == RGB888:
            return 3
        if fmt == RGB565:
            return 2
        if fmt == GS8:
            return 1
        return 0
    depth = getattr(canvas, "color_depth", None)
    if depth is not None and depth >= 8:
        return depth // 8
    return _RGB565_BPP


def key_to_bytes(key, bpp):
    """Pack a color key into buffer byte order for ``blit_transparent``.

    RGB888 buffers store R,G,B; other contiguous formats use little-endian.
    """
    if bpp == 3:
        return bytes(((key >> 16) & 0xFF, (key >> 8) & 0xFF, key & 0xFF))
    return (key & ((1 << (bpp * 8)) - 1)).to_bytes(bpp, "little")


def clip_blit_bounds(canvas, source, x, y):
    """Return clipped destination/source origin as ``(x0, y0, w, h, src_x, src_y)``.

    Returns ``None`` when the blit is fully outside the canvas.
    """
    if (
        (-x >= source.width)
        or (-y >= source.height)
        or (x >= canvas.width)
        or (y >= canvas.height)
    ):
        return None

    x0 = max(0, x)
    y0 = max(0, y)
    src_x = max(0, -x)
    src_y = max(0, -y)
    w = min(canvas.width, x + source.width) - x0
    h = min(canvas.height, y + source.height) - y0
    return x0, y0, w, h, src_x, src_y


def canvas_accepts_blit_rect(canvas):
    """True when ``canvas.blit_rect`` is a display-style fast path (not RAM copy)."""
    if not callable(getattr(canvas, "blit_rect", None)):
        return False
    from ._framebuf_plus import FrameBuffer

    return not isinstance(canvas, FrameBuffer)


def canvas_accepts_blit_transparent(canvas):
    """True when ``canvas.blit_transparent`` is implemented by the display driver."""
    if not callable(getattr(canvas, "blit_transparent", None)):
        return False
    from ._framebuf_plus import FrameBuffer

    return not isinstance(canvas, FrameBuffer)


def crop_buffer(buf, src_w, src_x, src_y, crop_w, crop_h, bpp):
    """Extract a sub-rectangle from a top-down packed buffer."""
    row_bytes = crop_w * bpp
    out = bytearray(row_bytes * crop_h)
    for row in range(crop_h):
        src_start = ((src_y + row) * src_w + src_x) * bpp
        dst_start = row * row_bytes
        out[dst_start : dst_start + row_bytes] = buf[src_start : src_start + row_bytes]
    return out


def _framebuffer_base_blit(canvas, source, x, y, key=-1, palette=None):
    """Call ``framebuf.FrameBuffer.blit`` without re-entering graphics overrides."""
    base = type(canvas).__mro__[1]
    base.blit(canvas, source, x, y, key, palette)


def _extract_rows(source, src_x, src_y, w, h, bpp):
    return crop_buffer(source.buffer, source.width, src_x, src_y, w, h, bpp)


def blit_rect_to_buffer(canvas, buf, x, y, w, h, *, bpp=None):
    """Copy a packed rectangle into ``canvas.buffer``."""
    if bpp is None:
        bpp = canvas_bytes_per_pixel(canvas)
        if bpp <= 0:
            bpp = _RGB565_BPP
    if x < 0 or y < 0 or x + w > canvas.width or y + h > canvas.height:
        raise ValueError("The provided x, y, w, h values are out of range")

    expected = w * h * bpp
    if len(buf) != expected:
        raise ValueError(
            f"The source buffer is not the correct size (got {len(buf)} bytes, expected {expected})"
        )

    for row in range(h):
        source_begin = row * w * bpp
        source_end = source_begin + w * bpp
        dest_begin = ((y + row) * canvas.width + x) * bpp
        dest_end = dest_begin + w * bpp
        canvas.buffer[dest_begin:dest_end] = buf[source_begin:source_end]


def blit_rect_dispatch(canvas, buf, x, y, w, h):
    """Blit a raw packed buffer, using a canvas hook when available."""
    if canvas_accepts_blit_rect(canvas):
        canvas.blit_rect(buf, x, y, w, h)
    else:
        blit_rect_to_buffer(canvas, buf, x, y, w, h)
    return Area(x, y, w, h)


def try_fast_framebuffer_blit(canvas, source, x, y, key=-1, palette=None):
    """Use framebuffer or display fast paths when available.

    Returns an :class:`Area` on success, or ``None`` to use the pixel loop.
    """
    clipped = clip_blit_bounds(canvas, source, x, y)
    if clipped is None:
        return None

    x0, y0, w, h, src_x, src_y = clipped

    from ._framebuf_plus import FrameBuffer

    if isinstance(canvas, FrameBuffer) and isinstance(source, FrameBuffer):
        _framebuffer_base_blit(canvas, source, x, y, key, palette)
        return Area(x0, y0, w, h)

    if key != -1 or palette is not None:
        return None

    if not hasattr(source, "buffer"):
        return None

    src_bpp = canvas_bytes_per_pixel(source)
    dst_bpp = canvas_bytes_per_pixel(canvas)
    if src_bpp <= 0 or src_bpp != dst_bpp:
        return None

    data = _extract_rows(source, src_x, src_y, w, h, src_bpp)
    blit_rect_dispatch(canvas, data, x0, y0, w, h)
    return Area(x0, y0, w, h)
