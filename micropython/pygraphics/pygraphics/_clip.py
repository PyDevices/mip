# SPDX-FileCopyrightText: 2026 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Clip-region wrapper for draw targets."""

from ._area import Area
from ._blit_hooks import blit_rect_dispatch, canvas_bytes_per_pixel, crop_buffer


def intersect_rect(x, y, w, h, clip):
    """Intersect a rectangle with a clip ``Area``. Returns ``Area`` or ``None``."""
    if w <= 0 or h <= 0:
        return None
    hit = Area(x, y, w, h).clip(clip)
    if hit.w <= 0 or hit.h <= 0:
        return None
    return hit


def crop_rgb565_buffer(buf, src_w, src_x, src_y, crop_w, crop_h):
    """Extract a sub-rectangle from a top-down RGB565 buffer."""
    return crop_buffer(buf, src_w, src_x, src_y, crop_w, crop_h, 2)


class ClippedCanvas:
    """Proxy that restricts drawing on ``canvas`` to ``clip``.

    Drawing methods that intersect the clip region are forwarded to the
    underlying canvas; pixels outside the clip are ignored. Unknown attributes
    fall through to ``canvas`` via ``__getattr__``.
    """

    def __init__(self, canvas, clip):
        """Wrap ``canvas`` so drawing is limited to ``clip``.

        Args:
            canvas: Framebuf-compatible draw target.
            clip (Area): Inclusive rectangle in canvas coordinates.
        """
        self._canvas = canvas
        self._clip = clip
        self._graphics_clip = clip

    def __getattr__(self, name):
        return getattr(self._canvas, name)

    @property
    def width(self):
        """Underlying canvas width in pixels."""
        return self._canvas.width

    @property
    def height(self):
        """Underlying canvas height in pixels."""
        return self._canvas.height

    def pixel(self, x, y, c=None):
        """Get or set a pixel if ``(x, y)`` is inside the clip.

        Args:
            x: X coordinate.
            y: Y coordinate.
            c: Color to set. If ``None``, read the existing pixel color.

        Returns:
            On set: ``Area`` of the pixel, or ``None`` if outside the clip.
            On get: pixel color, or ``None`` if outside the clip.
        """
        if not self._clip.contains(x, y):
            return None
        if c is None:
            return self._canvas.pixel(x, y)
        self._canvas.pixel(x, y, c)
        return Area(x, y, 1, 1)

    def fill(self, c):
        """Fill the entire clip rectangle with color ``c``.

        Args:
            c: Fill color.

        Returns:
            ``Area`` of the filled clip, or ``None`` if empty.
        """
        return self.fill_rect(self._clip.x, self._clip.y, self._clip.w, self._clip.h, c)

    def fill_rect(self, x, y, w, h, c):
        """Fill the intersection of the given rectangle with the clip.

        Args:
            x: Left edge.
            y: Top edge.
            w: Width.
            h: Height.
            c: Fill color.

        Returns:
            Clipped ``Area`` that was filled, or ``None`` if no overlap.
        """
        hit = intersect_rect(x, y, w, h, self._clip)
        if hit is None:
            return None
        if hasattr(self._canvas, "fill_rect"):
            self._canvas.fill_rect(hit.x, hit.y, hit.w, hit.h, c)
        else:
            for row in range(hit.y, hit.y + hit.h):
                for col in range(hit.x, hit.x + hit.w):
                    self._canvas.pixel(col, row, c)
        return hit

    def hline(self, x, y, w, c):
        """Draw a horizontal line clipped to this region.

        Args:
            x: Start x.
            y: Y coordinate.
            w: Width in pixels.
            c: Color.

        Returns:
            Clipped ``Area``, or ``None`` if no overlap.
        """
        return self.fill_rect(x, y, w, 1, c)

    def vline(self, x, y, h, c):
        """Draw a vertical line clipped to this region.

        Args:
            x: X coordinate.
            y: Start y.
            h: Height in pixels.
            c: Color.

        Returns:
            Clipped ``Area``, or ``None`` if no overlap.
        """
        return self.fill_rect(x, y, 1, h, c)

    def blit_rect(self, buf, x, y, w, h):
        """Blit a packed buffer, cropping to the clip region.

        Args:
            buf: Source bytes for a ``w`` x ``h`` rectangle (canvas bpp).
            x: Destination x.
            y: Destination y.
            w: Source width.
            h: Source height.

        Returns:
            Clipped destination ``Area``, or ``None`` if no overlap.
        """
        hit = intersect_rect(x, y, w, h, self._clip)
        if hit is None:
            return None
        dx = hit.x - x
        dy = hit.y - y
        if dx or dy or hit.w != w or hit.h != h:
            bpp = canvas_bytes_per_pixel(self._canvas)
            if bpp <= 0:
                bpp = 2
            buf = crop_buffer(buf, w, dx, dy, hit.w, hit.h, bpp)
        blit_rect_dispatch(self._canvas, buf, hit.x, hit.y, hit.w, hit.h)
        return hit

    def blit_transparent(self, buf, x, y, w, h, key):
        """Blit a packed buffer with transparency, cropped to the clip.

        Args:
            buf: Source bytes for a ``w`` x ``h`` rectangle (canvas bpp).
            x: Destination x.
            y: Destination y.
            w: Source width.
            h: Source height.
            key: Transparent color key.

        Returns:
            Clipped destination ``Area``, or ``None`` if no overlap.
        """
        from ._shapes import blit_transparent

        hit = intersect_rect(x, y, w, h, self._clip)
        if hit is None:
            return None
        dx = hit.x - x
        dy = hit.y - y
        if dx or dy or hit.w != w or hit.h != h:
            bpp = canvas_bytes_per_pixel(self._canvas)
            if bpp <= 0:
                bpp = 2
            buf = crop_buffer(buf, w, dx, dy, hit.w, hit.h, bpp)
        return blit_transparent(self._canvas, buf, hit.x, hit.y, hit.w, hit.h, key)

    def text(self, s, x, y, c=1, scale=1, inverted=False, font_data=None, height=8):
        """Draw romfont text clipped to this region.

        Glyphs are rendered via :meth:`fill_rect` on ``self``, so pixels
        outside the clip are discarded (unlike falling through to the
        underlying canvas ``text``, which draws unclipped).

        Args:
            s: Text to draw.
            x: Left edge.
            y: Top edge.
            c: Foreground color.
            scale: Glyph scale factor.
            inverted: Mirror glyphs when True.
            font_data: Optional romfont bytes / path.
            height: Romfont height (8, 14, or 16).

        Returns:
            Unclipped text ``Area`` (same contract as ``FrameBuffer.text``).
        """
        from . import _font

        return _font.text(
            self,
            s,
            x,
            y,
            c,
            scale=scale,
            inverted=inverted,
            font_data=font_data,
            height=height,
        )

    def text8(self, s, x, y, c=1, scale=1, inverted=False, font_data=None):
        """Draw 8px-high romfont text clipped to this region."""
        from . import _font

        return _font.text8(
            self, s, x, y, c, scale=scale, inverted=inverted, font_data=font_data
        )

    def text14(self, s, x, y, c=1, scale=1, inverted=False, font_data=None):
        """Draw 14px-high romfont text clipped to this region."""
        from . import _font

        return _font.text14(
            self, s, x, y, c, scale=scale, inverted=inverted, font_data=font_data
        )

    def text16(self, s, x, y, c=1, scale=1, inverted=False, font_data=None):
        """Draw 16px-high romfont text clipped to this region."""
        from . import _font

        return _font.text16(
            self, s, x, y, c, scale=scale, inverted=inverted, font_data=font_data
        )


class ClipContext:
    """Context manager that pushes a clip rectangle onto a :class:`Draw` stack.

    Entering returns the effective (intersected) clip ``Area``. Nested
    ``with draw.clip(...)`` blocks intersect.
    """

    def __init__(self, draw, area):
        """Bind this context to ``draw`` and the clip ``area``.

        Args:
            draw (Draw): Draw instance whose clip stack is updated.
            area (Area): Clip rectangle to push on enter.
        """
        self._draw = draw
        self._area = area

    def __enter__(self):
        """Push the clip and return the effective clip ``Area``."""
        self._draw._clip_stack.append(self._area)
        return self._draw._effective_clip()

    def __exit__(self, exc_type, exc, tb):
        """Pop the clip rectangle from the draw stack."""
        self._clip_stack_pop()

    def _clip_stack_pop(self):
        self._draw._clip_stack.pop()
