# SPDX-FileCopyrightText: 2024 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Button widget with optional icon and label."""

from eventsys import events

from .._constants import ALIGN, ICON_SIZE, PAD, TEXT_SIZE, TEXT_WIDTH
from ..widget import Widget
from ._raised import fill_raised_round_rect, normalize_style, raised_face_colors
from .icon import Icon
from .label import Label


class Button(Widget):
    """Clickable control with optional icon and text label."""

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
        radius=0,
        pressed_offset=2,
        pressed=False,
        label=None,
        text_color=None,
        text_height=TEXT_SIZE.LARGE,
        scale=1,
        icon_file=None,
        icon_color=None,
        shadow=0,
        style="flat",
        bg_hi=None,
        bg_lo=None,
        rim=None,
        backdrop=None,
    ):
        """
        Initialize a Button widget to display an icon and/or text.

        Args:
            parent (Widget): The parent widget or screen that contains this widget.
            x (int): The x-coordinate of the widget.
            y (int): The y-coordinate of the widget.
            w (int): The width of the widget.
            h (int): The height of the widget.
            align (int): The alignment of the widget.
            align_to (Widget): The widget to align to.
            fg (int): The foreground color of the widget.
            bg (int): The background color of the widget.
            visible (bool): The visibility of the widget (default is True).
            value (Any): User-assigned value of the widget.
            padding (tuple): The padding on each side of the widget.
            radius (int): The corner radius of the widget (default is 0).
            pressed_offset (int): The offset of the widget when pressed (default is 2).
            pressed (bool): The state of the widget (default is False).
            label (str): The text label of the widget.
            text_color (int): The color of the text label.
            text_height (int): The height of the text label (default is TEXT_SIZE.LARGE).
            scale (int): Romfont scale factor passed to the label (default is 1).
            icon_file (str): The icon file to display on the widget.
            icon_color (int): The color of the icon.
            shadow (int): Fake drop-shadow offset in pixels drawn behind the
                button in ``color_theme.shadow`` (0 disables; the default).
            style (str): ``\"flat\"`` (default solid fill + outline press) or
                ``\"raised\"`` (top-lit gradient + rim; press inverts lighting).
            bg_hi (int): Optional raised highlight color; default shade of ``bg``.
            bg_lo (int): Optional raised shade color; default shade of ``bg``.
            rim (int): Optional raised rim stroke; default shade of ``bg``.
            backdrop (int | None): When set, fill this button's axis-aligned
                ``area`` with ``backdrop`` before painting the face instead of
                calling ``parent.draw(self.area)``. Use for raised round keys
                that sit on a painted disc/chassis that is not the parent (same
                role as filling a scratch buffer with the disc color before
                blitting a circular key).
        """
        self.radius = radius
        self.pressed_offset = pressed_offset
        self.shadow = shadow
        self._style = normalize_style(style)
        self._bg_hi = bg_hi
        self._bg_lo = bg_lo
        self._rim = rim
        self._backdrop = backdrop
        self._pressed = pressed
        if w is None and label:
            w = (len(label) + 1) * TEXT_WIDTH * scale + 2 * PAD
        w = w or ICON_SIZE.LARGE + 2 * PAD
        h = h or ICON_SIZE.LARGE + 2 * PAD
        bg = bg if bg is not None else parent.color_theme.primary_variant
        fg = fg if fg is not None else parent.color_theme.on_primary
        super().__init__(
            parent, x, y, w, h, align, align_to, fg, bg, visible, value, padding
        )
        face_bg = parent.color_theme.transparent if self._style == "raised" else self.bg
        if icon_file:
            icon_align = ALIGN.CENTER if not label else ALIGN.LEFT
            icon_color = (
                icon_color if icon_color is not None else parent.color_theme.on_primary
            )
            self.icon = Icon(
                self,
                0,
                0,
                None,
                None,
                icon_align,
                None,
                icon_color,
                face_bg,
                True,
                icon_file,
            )
        if label:
            if text_height not in TEXT_SIZE:
                raise ValueError("Text height must be 8, 14 or 16 pixels.")
            label_align = ALIGN.CENTER if not icon_file else ALIGN.OUTER_RIGHT
            label_align_to = self.icon if icon_file else self
            text_color = (
                text_color if text_color is not None else parent.color_theme.on_primary
            )
            self.label = Label(
                self,
                0,
                0,
                None,
                None,
                label_align,
                label_align_to,
                text_color,
                face_bg,
                True,
                label,
                None,
                text_height,
                scale,
            )
        else:
            self.label = None

    @property
    def style(self):
        """Face style: ``\"flat\"`` or ``\"raised\"``."""
        return self._style

    def _register_callbacks(self):
        self.add_event_cb(events.MOUSEBUTTONDOWN, self.press)
        self.add_event_cb(events.MOUSEBUTTONUP, self.release)

    def _draw_face(self, pressed=False):
        pa = self.padded_area
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
                pressed=pressed,
                pal=pal,
            )
            return
        self.display.framebuf.round_rect(*pa, self.radius, self.bg, f=True)

    def _redraw_content(self):
        """Repaint face and visible children into the framebuffer (no flush)."""
        self.draw()
        for child in self.children:
            if child.visible:
                child.draw()

    @property
    def backdrop(self):
        """Clear color under the face, or ``None`` to erase via the parent."""
        return self._backdrop

    @backdrop.setter
    def backdrop(self, value):
        self._backdrop = value
        self.invalidate()

    def draw(self, _=None):
        """
        Draw the button background and shape (with an optional drop shadow).
        """
        if self._backdrop is not None:
            # Match offscreen "fill then circle" (roku_graphics): corners of the
            # AABB keep the disc/chassis color instead of the parent's fill.
            self.display.framebuf.fill_rect(*self.area, self._backdrop)
        else:
            self.parent.draw(self.area)
        pa = self.padded_area
        if self.shadow:
            # Cheap fake drop shadow: a shape-colored round_rect offset behind
            # the button. Two fills, no alpha blending.
            self.display.framebuf.round_rect(
                pa.x + self.shadow,
                pa.y + self.shadow,
                pa.w,
                pa.h,
                self.radius,
                self.color_theme.shadow,
                f=True,
            )
        self._draw_face(pressed=self._pressed and self._style == "raised")

    def press(self, data=None, event=None):
        """Mark pressed and dirty; flush via the display tick (not inline I80)."""
        # Synchronous ``display.refresh`` from the input/service tick nested
        # I80 blits under the soft timer and panicked the ESP32-S3 (HARD_RESET
        # = ESP_RST_PANIC) when tapping raised roku_widgets keys.
        self._pressed = True
        self.invalidate()

    def release(self, data=None, event=None):
        """Clear pressed and dirty; flush via the display tick."""
        self._pressed = False
        self.invalidate()
