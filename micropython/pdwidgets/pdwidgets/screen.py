# SPDX-FileCopyrightText: 2024 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Full-screen widget container."""

from pygraphics import Area

from .display import Display
from .widget import Widget


class Screen(Widget):
    """Full-screen page container for grouping a coherent UI view.

    A :class:`Screen` is the usual root for a page or modal surface inside a
    :class:`Display`. It fills the display area and can expose helper children
    such as ``top``, ``main``, and ``bottom`` when the display has split
    regions. Applications commonly create one screen per page and swap the
    active screen to navigate between views.
    """
    def __init__(self, parent: Display | Widget, fg=None, bg=None, visible=True):
        """Create a full-screen container for a page of widgets.

        Args:
            parent (Display): The display that owns this screen.
            fg (int): Default foreground color for child widgets.
            bg (int): Default background color for the screen itself.
            visible (bool): Whether the page is shown immediately.

        Example:
            display = Display(display_drv, runtime)
            screen = Screen(display, bg=theme.background)
            Label(screen, value="Home")
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
