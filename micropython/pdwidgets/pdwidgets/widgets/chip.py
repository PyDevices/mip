# SPDX-FileCopyrightText: 2024 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Chip / Tag — compact selectable filter chip (Badge stays status-only)."""

from eventsys import events

from .._constants import PAD, TEXT_SIZE, TEXT_WIDTH
from ..widget import Widget
from ._raised import fill_raised_round_rect, normalize_style, raised_face_colors


class Chip(Widget):
    """Compact selectable filter chip."""

    def __init__(  # noqa: PLR0913
        self,
        parent: Widget,
        x=0,
        y=0,
        w=None,
        h=None,
        align=None,
        align_to=None,
        fg=None,
        bg=None,
        visible=True,
        value=False,
        padding=None,
        label="",
        text_height=TEXT_SIZE.MEDIUM,
        radius=10,
        style="flat",
        bg_hi=None,
        bg_lo=None,
        rim=None,
    ):
        """Selectable filter chip; ``value`` is selected bool."""
        self.label = label
        self.text_height = text_height
        self.radius = radius
        self._style = normalize_style(style)
        self._bg_hi = bg_hi
        self._bg_lo = bg_lo
        self._rim = rim
        w = w or (len(label) + 2) * TEXT_WIDTH + 2 * PAD
        h = h or text_height + 2 * PAD
        bg = bg if bg is not None else parent.color_theme.chip
        fg = fg if fg is not None else parent.color_theme.on_chip
        super().__init__(
            parent, x, y, w, h, align, align_to, fg, bg, visible, value, padding
        )

    @property
    def style(self):
        """Face style: ``\"flat\"`` or ``\"raised\"``."""
        return self._style

    def _register_callbacks(self):
        self.add_event_cb(events.MOUSEBUTTONDOWN, self._toggle)

    def _toggle(self, data=None, event=None):
        self.value = not self._value

    def draw(self, _=None):
        """Draw the chip background and label."""
        pa = self.padded_area
        selected = bool(self._value)
        fill = self.color_theme.chip_selected if selected else self.color_theme.chip
        ink = (
            self.color_theme.on_chip_selected if selected else self.color_theme.on_chip
        )
        if self._style == "raised":
            pal = self.display.pal
            hi, lo, rim = raised_face_colors(
                fill, self._bg_hi, self._bg_lo, self._rim, pal=pal
            )
            fill_raised_round_rect(
                self.display.framebuf,
                pa.x,
                pa.y,
                pa.w,
                pa.h,
                self.radius,
                hi,
                lo,
                rim,
                pal=pal,
            )
        else:
            self.display.framebuf.round_rect(*pa, self.radius, fill, f=True)
        tw = len(self.label) * TEXT_WIDTH
        tx = pa.x + (pa.w - tw) // 2
        ty = pa.y + (pa.h - self.text_height) // 2
        self.display.framebuf.text(self.label, tx, ty, ink, height=self.text_height)


Tag = Chip
