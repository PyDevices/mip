# SPDX-FileCopyrightText: 2024 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Full-screen widget container."""

from graphics import Area

from .display import Display
from .widget import Widget


class Screen(Widget):
    """Full-screen container for a page of widgets."""
    def __init__(self, parent: Display | Widget, fg=None, bg=None, visible=True):
        """
        Initialize a Screen object to contain widgets.

        Args:
            parent (Display): The display object that contains the screen.
            fg (int): The foreground color of the screen.
            bg (int): The background color of the screen.
            visible (bool): The visibility of the screen.

        Usage:
            screen = Screen(display)
        """
        super().__init__(
            parent,
            0,
            0,
            parent.width,
            parent.height,
            None,
            None,
            fg,
            bg,
            visible,
            None,
            (0, 0, 0, 0),
        )
        self.partitioned = self.display.tfa > 0 or self.display.bfa > 0

        if self.partitioned:
            tfa = Area(self.display.tfa_area)
            self.top = Widget(
                self,
                tfa.x,
                tfa.y,
                tfa.w,
                tfa.h,
                None,
                None,
                parent.color_theme.on_primary,
                parent.color_theme.primary,
            )
            vsa = Area(self.display.vsa_area)
            self.main = Widget(self, vsa.x, vsa.y, vsa.w, vsa.h)
            bfa = Area(self.display.bfa_area)
            self.bottom = Widget(
                self,
                bfa.x,
                bfa.y,
                bfa.w,
                bfa.h,
                None,
                None,
                parent.color_theme.on_primary,
                parent.color_theme.primary,
            )
