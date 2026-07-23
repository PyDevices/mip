# SPDX-FileCopyrightText: 2024 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Shared top-lit raised (gradient + rim) face drawing for pdwidgets.

Opt-in visual language matching pydisplay ``roku_graphics._draw_button``:
vertical hi→lo gradient, soft darker rim, pressed lighting invert.

Row recipes (inset + color per scanline) are cached so repeated draws of the
same face geometry skip the circular-inset / lerp work — important when many
raised buttons share a role size or press/release redraws a single key.
"""

_STYLES = ("flat", "raised")

# (w, h, radius, hi, lo, pressed) -> tuple[(inset, color), ...]
_ROW_CACHE = {}
_ROW_CACHE_MAX = 48


def normalize_style(style):
    """Return ``\"flat\"`` or ``\"raised\"``; raise ``ValueError`` if invalid."""
    if style is None:
        return "flat"
    if style not in _STYLES:
        raise ValueError("style must be 'flat' or 'raised'")
    return style


def _channels(c, pal=None):
    if pal is not None:
        return pal.color_rgb(c)
    return (c >> 8) & 0xF8, (c >> 3) & 0xFC, (c << 3) & 0xF8


def _pack(r, g, b, pal=None):
    if pal is not None:
        return pal.color565(r, g, b)
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def shade(c, factor, pal=None):
    """Darken (``factor`` < 1) or lighten (``factor`` > 1) an RGB565 color."""
    r, g, b = _channels(c, pal)
    r = max(0, min(255, int(r * factor)))
    g = max(0, min(255, int(g * factor)))
    b = max(0, min(255, int(b * factor)))
    return _pack(r, g, b, pal)


def lerp(c1, c2, t, pal=None):
    """Linear interpolate between two RGB565 colors; ``t`` in ``[0, 1]``."""
    r1, g1, b1 = _channels(c1, pal)
    r2, g2, b2 = _channels(c2, pal)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return _pack(r, g, b, pal)


def raised_face_colors(bg, bg_hi=None, bg_lo=None, rim=None, pal=None):
    """Derive hi / lo / rim from face mid ``bg`` when optional colors omitted."""
    hi = bg_hi if bg_hi is not None else shade(bg, 1.12, pal)
    lo = bg_lo if bg_lo is not None else shade(bg, 0.78, pal)
    rim_c = rim if rim is not None else shade(bg, 0.55, pal)
    return hi, lo, rim_c


def clear_raised_row_cache():
    """Drop cached raised-face row recipes (tests / theme changes)."""
    _ROW_CACHE.clear()


def _raised_rows(w, h, radius, hi, lo, pressed, pal=None):
    """Return cached ``(inset, color)`` rows for a raised face."""
    r = radius
    if r < 0:
        r = 0
    max_r = min(w, h) // 2
    if r > max_r:
        r = max_r
    key = (w, h, r, hi, lo, bool(pressed))
    rows = _ROW_CACHE.get(key)
    if rows is not None:
        return rows, r

    out = []
    for j in range(h):
        if j < r:
            d = r - j
        elif j >= h - r:
            d = r - (h - 1 - j)
        else:
            d = 0
        if d:
            rr = r * r
            dd = d * d
            s = 0
            while (s + 1) * (s + 1) <= rr - dd:
                s += 1
            inset = r - s
        else:
            inset = 0
        t = j / (h - 1) if h > 1 else 0
        c = lerp(lo, hi, t, pal) if pressed else lerp(hi, lo, t, pal)
        out.append((inset, c))

    if len(_ROW_CACHE) >= _ROW_CACHE_MAX:
        _ROW_CACHE.clear()
    _ROW_CACHE[key] = tuple(out)
    return _ROW_CACHE[key], r


def fill_raised_round_rect(
    fb, x, y, w, h, radius, hi, lo, rim, pressed=False, pal=None
):
    """Fill a top-lit raised round rect; ``pressed`` inverts the gradient."""
    if w <= 0 or h <= 0:
        return
    rows, r = _raised_rows(w, h, radius, hi, lo, pressed, pal=pal)
    for j, (inset, c) in enumerate(rows):
        ww = w - 2 * inset
        if ww > 0:
            fb.fill_rect(x + inset, y + j, ww, 1, c)

    fb.round_rect(x, y, w, h, r, rim, f=False)
