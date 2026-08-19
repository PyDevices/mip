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
            parent (Widget): Parent widget or screen.
            x (int): Relative x-coordinate.
            y (int): Relative y-coordinate.
            w (int): Width in pixels (defaults to parent width).
            h (int): Height in pixels (defaults from ``text_height``).
            align (int): Alignment constant from :data:`~pdwidgets.ALIGN`.
            align_to (Widget): Widget to align against (default parent).
            fg (int): Foreground / text color.
            bg (int): Background / field fill color.
            visible (bool): Initial visibility (default ``True``).
            value (str): Initial password string (default empty).
            padding (tuple): ``(left, right, top, bottom)`` inset.
            hint (str): Placeholder text when the value is empty.
            text_height (int): Romfont height (``TEXT_SIZE`` member).
            radius (int): Corner radius of the field border.
            max_length (int): Optional maximum character count.
            mask (str): Single character used to mask each glyph (default ``"*"``).
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
