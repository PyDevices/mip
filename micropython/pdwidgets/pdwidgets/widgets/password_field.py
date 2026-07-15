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
