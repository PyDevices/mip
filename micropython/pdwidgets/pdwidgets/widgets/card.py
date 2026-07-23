# SPDX-FileCopyrightText: 2024 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Card container widget."""

from .._constants import ALIGN, PAD
from ..widget import Widget
from ._raised import fill_raised_round_rect, normalize_style, raised_face_colors
from .label import Label


class Card(Widget):
    """Rounded container with optional title and drop shadow."""

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
        value=None,
        padding=None,
        radius=8,
        shadow=2,
        title=None,
        font=None,
        style="flat",
        bg_hi=None,
        bg_lo=None,
        rim=None,
    ):
        """
        Initialize a Card: a rounded, optionally-shadowed container for grouping
        other widgets.

        The card paints a rounded ``surface`` rectangle (with a cheap fake drop
        shadow) and, optionally, a title along its top. Add child widgets to it
        exactly like any other container.

        Args:
            parent (Widget): The parent widget or screen that contains this card.
            x (int): The x-coordinate of the card.
            y (int): The y-coordinate of the card.
            w (int): The width of the card.
            h (int): The height of the card.
            align (int): The alignment of the card.
            align_to (Widget): The widget to align to.
            fg (int): The foreground (text) color; defaults to ``on_surface``.
            bg (int): The card surface color; defaults to ``surface``.
            visible (bool): The visibility of the card.
            value (Any): User-assigned value of the card.
            padding (tuple): The padding on each side of the card.
            radius (int): The corner radius of the card (default is 8).
            shadow (int): Fake drop-shadow offset in pixels (0 disables).
            title (str): Optional title drawn along the top of the card.
            font (module): Optional proportional font module for the title.
            style (str): ``\"flat\"`` (default) or ``\"raised\"`` gradient face.
            bg_hi (int): Optional raised highlight color.
            bg_lo (int): Optional raised shade color.
            rim (int): Optional raised rim stroke.

        Usage:
            card = Card(screen, w=200, h=120, title="Settings")
            Switch(card, align=pd.ALIGN.CENTER)
        """
        bg = bg if bg is not None else parent.color_theme.surface
        fg = fg if fg is not None else parent.color_theme.on_surface
        self.radius = radius
        self.shadow = shadow
        self._style = normalize_style(style)
        self._bg_hi = bg_hi
        self._bg_lo = bg_lo
        self._rim = rim
        super().__init__(
            parent, x, y, w, h, align, align_to, fg, bg, visible, value, padding
        )
        self.title_label = None
        if title:
            title_bg = parent.color_theme.transparent if self._style == "raised" else bg
            self.title_label = Label(
                self,
                value=title,
                x=radius,
                y=PAD,
                align=ALIGN.TOP_LEFT,
                fg=fg,
                bg=title_bg,
                font=font,
            )

    @property
    def style(self):
        """Face style: ``\"flat\"`` or ``\"raised\"``."""
        return self._style

    def _draw_face(self):
        pa = self.padded_area
        if self.shadow:
            self.display.framebuf.round_rect(
                pa.x + self.shadow,
                pa.y + self.shadow,
                pa.w,
                pa.h,
                self.radius,
                self.color_theme.shadow,
                f=True,
            )
        if self._style == "raised":
            pal = self.display.pal
            hi, lo, rim = raised_face_colors(
                self.bg, self._bg_hi, self._bg_lo, self._rim, pal=pal
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
            return
        self.display.framebuf.round_rect(*pa, self.radius, self.bg, f=True)

    def draw(self, area=None):
        """
        Draw the card's shadow and rounded surface.

        When a child asks the card to repaint just its sub-area (via
        ``parent.draw(child.area)``), only that region is refilled with the card
        color so sibling widgets are not erased; a full (``area is None``) draw
        repaints the shadow and rounded surface.

        Raised cards always repaint the full gradient face (partial solid fills
        would punch holes in the lighting).
        """
        if area is not None:
            if self._style == "raised":
                self._draw_face()
                return
            self.display.framebuf.fill_rect(*area, self.bg)
            return
        self.parent.draw(self.area)
        self._draw_face()
