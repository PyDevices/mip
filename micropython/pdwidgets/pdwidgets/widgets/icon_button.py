# SPDX-FileCopyrightText: 2024 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Icon-only button."""

from .._constants import ALIGN
from ..widget import Widget
from ._raised import normalize_style
from .button import Button
from .icon import Icon


class IconButton(Button):
    """Button whose content is a centered icon."""

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
        icon_file=None,
        radius=0,
        shadow=0,
        style="flat",
        bg_hi=None,
        bg_lo=None,
        rim=None,
        backdrop=None,
    ):
        """
        Initialize an IconButton widget to display an icon on a button.

        Args:
            parent (Widget): The parent widget or screen that contains this icon button.
            x (int): The x-coordinate of the icon button.
            y (int): The y-coordinate of the icon button.
            w (int): The width of the icon button.
            h (int): The height of the icon button.
            align (int): The alignment of the icon button.
            align_to (Widget): The widget to align to.
            fg (int): The color of the icon button.
            bg (int): The background color of the icon button.
            visible (bool): The visibility of the icon button.
            value (str): The user-assigned value of the icon button.
            padding (tuple): The padding on each side of the icon button.
            icon_file (str): The icon file to display.
            radius (int): Corner radius (default 0).
            shadow (int): Fake drop-shadow offset in pixels (0 disables).
            style (str): ``\"flat\"`` or ``\"raised\"`` (see :class:`Button`).
            bg_hi (int): Optional raised highlight color.
            bg_lo (int): Optional raised shade color.
            rim (int): Optional raised rim stroke.
            backdrop (int | None): Optional clear color under the face
                (see :class:`Button`).

        Usage:
            icon_button = IconButton(screen, icon_file="pdwidgets.icons.home_filled_36dp")
        """
        fg = fg if fg is not None else parent.fg
        bg = bg if bg is not None else parent.bg
        style = normalize_style(style)
        face_bg = parent.color_theme.transparent if style == "raised" else bg
        self.icon = Icon(
            None, 0, 0, None, None, ALIGN.CENTER, None, fg, face_bg, True, icon_file
        )
        w = w or self.icon.width
        h = h or self.icon.height
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
            radius=radius,
            shadow=shadow,
            style=style,
            bg_hi=bg_hi,
            bg_lo=bg_lo,
            rim=rim,
            backdrop=backdrop,
        )
        self.icon.parent = self
