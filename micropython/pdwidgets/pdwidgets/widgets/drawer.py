# SPDX-FileCopyrightText: 2024 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Drawer — side panel + scrim."""

from eventsys import events

from .._constants import ALIGN
from .._util import _root_screen
from ..widget import Widget
from .card import Card


class Drawer(Widget):
    """Modal side panel that slides in from the left or right."""
    def __init__(  # noqa: PLR0913
        self,
        parent: Widget,
        title=None,
        w=None,
        side="left",
        fg=None,
        bg=None,
        scrim=None,
        on_dismiss=None,
    ):
        """Modal side panel (``side`` is ``\"left\"`` or ``\"right\"``)."""
        screen = _root_screen(parent)
        display = parent.display
        self.scrim = scrim if scrim is not None else parent.color_theme.sheet_scrim
        self.on_dismiss = on_dismiss
        self.side = side
        bg = bg if bg is not None else parent.color_theme.surface
        fg = fg if fg is not None else parent.color_theme.on_surface
        super().__init__(
            screen, 0, 0, display.width, display.height, None, None, fg, None, False
        )
        panel_w = w or display.width // 2
        align = ALIGN.LEFT if side != "right" else ALIGN.RIGHT
        self.panel = Card(
            self,
            w=panel_w,
            h=display.height,
            align=align,
            fg=fg,
            bg=bg,
            title=title,
            shadow=4,
        )
        self.add_event_cb(events.MOUSEBUTTONDOWN, self._scrim_tap)

    @property
    def content(self):
        """The :class:`Card` panel; add child widgets here."""
        return self.panel

    def _scrim_tap(self, data=None, event=None):
        pt = self.display.translate_point(event.pos)
        if not self.panel.area.contains(*pt):
            self.hide_drawer()

    def show(self):
        """Show the drawer, grab modal capture, and redraw."""
        self.visible = True
        self.set_modal(True)
        self.invalidate()

    def hide_drawer(self):
        """Hide the drawer, release modal capture, and call ``on_dismiss``."""
        self.set_modal(False)
        self.visible = False
        if self.on_dismiss:
            self.on_dismiss()

    def draw(self, area=None):
        """Fill the scrim behind the side panel."""
        area = area or self.area
        self.display.framebuf.fill_rect(*area, self.scrim)
