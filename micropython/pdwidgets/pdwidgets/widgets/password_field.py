# SPDX-FileCopyrightText: 2024 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""PasswordField — TextInput that masks glyphs."""

from .._constants import TEXT_SIZE
from ..widget import Widget
from .text_input import TextInput


class PasswordField(TextInput):
    """Single-line password entry; drawn text is replaced with ``*`` masks."""

    def __init__(
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
        hint="",
        text_height=TEXT_SIZE.LARGE,
        radius=6,
        max_length=None,
        mask="*",
    ):
        """Initialize a password field that masks displayed glyphs.

        Args:
            parent: Parent widget or screen.
            x: Relative x-coordinate.
            y: Relative y-coordinate.
            w: Width in pixels (defaults to parent width).
            h: Height in pixels (defaults from ``text_height``).
            align: Alignment constant from :data:`~pdwidgets.ALIGN`.
            align_to: Widget to align against (default parent).
            fg: Foreground / text color.
            bg: Background / field fill color.
            visible: Initial visibility (default ``True``).
            value: Initial password string (default empty).
            padding: ``(left, right, top, bottom)`` inset.
            hint: Placeholder text when the value is empty.
            text_height: Romfont height (``TEXT_SIZE`` member).
            radius: Corner radius of the field border.
            max_length: Optional maximum character count.
            mask: Single character used to mask each glyph (default ``"*"``).
        """
        self.mask = mask
        super().__init__(
            parent,
            x,
            y,
            w,
            h,
            align,
            align_to,
            fg,
            bg,
            visible,
            value,
            padding,
            hint,
            text_height,
            radius,
            max_length,
        )

    def _display_text(self):
        n = len(self._value or "")
        return self.mask * n if n else ""
