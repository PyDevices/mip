# SPDX-FileCopyrightText: 2024 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Display framebuffer, rendering, and runtime integration."""

from random import getrandbits

try:
    from time import ticks_ms
except ImportError:
    from multimer import ticks_ms

import events
from pygraphics import RGB565, Area, FrameBuffer

from ._constants import ALIGN
from ._focus import FocusManager
from ._themes import ColorTheme, get_palette
from ._util import (
    _POINTER_EVENTS,
    _WIDGET_EVENTS,
    _cond_pointer,
    _display_drv_get_attrs,
    _display_drv_set_attrs,
    _log,
)
from .task import Task
from .widget import Widget


def _mark_updates_enabled():
    import sys

    mod = sys.modules.get("pdwidgets")
    return bool(mod is not None and getattr(mod, "MARK_UPDATES", False))


class Display(Widget):
    """Root display surface that owns the framebuffer, event loop, and widget tree.

    Create one :class:`Display` per hardware panel and attach it to the app's
    shared :mod:`appdev` coordinator. The display becomes the root of the widget
    hierarchy, and its render loop is driven by the app's timer callback so
    widgets redraw without a separate timer of their own.

    Typical setup:

    - build a :class:`Screen` for the active page
    - add child widgets with relative geometry and alignment
    - call :meth:`app.run() <appdev.App.run>` after
      construction to start input handling and rendering
    """
    displays = []
    timer = None  # pdwidgets owns no timer; kept as None for API/back-compat.
    tick_period = 10  # Render tick period (ms) for the app every() subscription.

    def __init__(self, display_drv, app, tfa=0, bfa=0, format=RGB565):
        """Initialize a display root from the board's display driver and app coordinator.

        Args:
            display_drv (DisplayDriver): The hardware driver that exposes the
                framebuffer dimensions, color depth, and any scroll regions.
            app (App): The shared application coordinator that will dispatch input
                and drive periodic redraws.
            tfa (int): Top fixed area used for split displays or status bars.
            bfa (int): Bottom fixed area used for split displays or status bars.
            format (int): Framebuffer color format; defaults to :data:`RGB565`.

        Example:
            import board_config
            import appdev

            app = appdev.App(board_config)
            display = Display(board_config.display_drv, app)
            screen = Screen(display)
            Label(screen, value="Hello")
        """
        self.display_drv = display_drv
        super().__init__(
            None,
            0,
            0,
            display_drv.width,
            display_drv.height,
            None,
            None,
            -1,
            0,
            True,
            None,
            None,
            (0, 0, 0, 0),
        )
        display_drv.set_vscroll(tfa, bfa)
        display_drv.vscroll = 0
        self.app = app
        self.runtime = app
        self._buffer = memoryview(
            bytearray(display_drv.width * display_drv.height * display_drv.color_depth // 8)
        )
        self.framebuf = FrameBuffer(self._buffer, display_drv.width, display_drv.height, format)
        self._framebuf_real = self.framebuf
        self._clip_stack = []
        self._dirty_areas = []
        self._tasks = []
        self._tick_busy = False
        self._modals = []  # modal-capture stack (see Widget.set_modal)
        self.focus_manager = FocusManager()
        if display_drv.requires_byteswap:
            self.needs_swap = display_drv.disable_auto_byteswap(True)
        else:
            self.needs_swap = False
        self.pal = get_palette(
            "material_design", swapped=self.needs_swap, color_depth=display_drv.color_depth
        )
        self._color_theme = ColorTheme(self.pal)
        self._tick_sub = None
        self._refresh_claim = None
        Display.displays.append(self)
        self._attach_to_app()

    def _attach_to_app(self):
        """Wire input dispatch and frame rendering into the shared app coordinator."""
        app = self.app
        if app is None:
            return
        if hasattr(app, "on"):
            app.on(list(_WIDGET_EVENTS), self.handle_event)
        elif hasattr(app, "subscribe"):
            app.subscribe(self.handle_event, event_types=list(_WIDGET_EVENTS))

        if hasattr(app, "every"):
            self._tick_sub = app.every(Display.tick_period, self._render_tick)
        elif hasattr(app, "on_tick"):
            self._tick_sub = app.on_tick(
                self._render_tick,
                period=Display.tick_period,
                async_=getattr(app, "timer_async", False),
            )

        if hasattr(app, "pause_refresh"):
            try:
                self._refresh_claim = app.pause_refresh()
            except Exception:
                pass

    def _render_tick(self, _=None):
        """Shared-timer callback: render one widget frame."""
        self.tick()

    @property
    def parent(self):
        """Always ``None``; the display is the root."""
        return None

    @parent.setter
    def parent(self, parent):
        """Raise :exc:`ValueError` if a parent is assigned."""
        if parent is not None:
            raise ValueError("Display object cannot have a parent.")

    @property
    def x(self):
        """Display x offset (always 0)."""
        return self._x

    @property
    def y(self):
        """Display y offset (always 0)."""
        return self._y

    @property
    def width(self):
        """Framebuffer width in pixels."""
        return self._w

    @property
    def height(self):
        """Framebuffer height in pixels."""
        return self._h

    @property
    def display(self):
        """Return ``self``."""
        return self

    @property
    def color_theme(self):
        """Semantic color theme for this display."""
        return self._color_theme

    @property
    def visible(self):
        """Always ``True``."""
        return True

    @visible.setter
    def visible(self, visible):
        """Raise :exc:`ValueError`; the display cannot be hidden."""
        raise ValueError("Cannot set visibility of Display object.")

    def clip_push(self, area: Area):
        """Push an integer clip rectangle for nested draw/render (MCU-safe, no alpha)."""
        if self._clip_stack:
            area = area.clip(self._clip_stack[-1])
        self._clip_stack.append(area)
        from pygraphics import ClippedCanvas

        self.framebuf = ClippedCanvas(self._framebuf_real, area)

    def clip_pop(self):
        """Pop the current clip rectangle and restore the previous draw target."""
        if not self._clip_stack:
            return
        self._clip_stack.pop()
        if self._clip_stack:
            from pygraphics import ClippedCanvas

            self.framebuf = ClippedCanvas(self._framebuf_real, self._clip_stack[-1])
        else:
            self.framebuf = self._framebuf_real

    @property
    def _modal(self):
        """The widget currently holding modal pointer capture, or None."""
        return self._modals[-1] if self._modals else None

    def handle_event(self, event, condition=None, point=None):
        """
        Dispatch an event, honoring modal pointer capture and focus keys.

        Focus keys (Tab / Shift-Tab / arrows) are handled by
        :attr:`focus_manager` before the widget tree walk. Pointer modality
        (see :meth:`Widget.set_modal`) only affects mouse/touch — key focus is
        independent so sheets/dialogs can still host TextInput fields.
        """
        if event.type == events.KEYDOWN and self.focus_manager.handle_key(event):
            return
        modal = self._modal
        if modal is not None and modal.visible and event.type in _POINTER_EVENTS:
            point = self.translate_point(event.pos)
            for callback, data in modal._event_callbacks.get(event.type, {}).items():
                callback(data, event)
            modal.handle_event(event, _cond_pointer, point)
            return
        super().handle_event(event, condition, point)

    @property
    def active_screen(self):
        """The currently attached :class:`Screen`, if any."""
        if self.children:
            return self.children[0]
        return None

    @active_screen.setter
    def active_screen(self, screen):
        """Replace the active screen (removes any previous screen)."""
        for child in self.children:
            self.remove_child(child)
        super().add_child(screen)

    def add_child(self, screen):
        """Set :attr:`active_screen` to ``screen``."""
        self.active_screen = screen

    def set_position(self, *args, **kwargs):
        """Reset geometry to the full display size."""
        self._x = 0
        self._y = 0
        self._w = self.display_drv.width
        self._h = self.display_drv.height
        self._align = ALIGN.TOP_LEFT
        self._align_to = None

    def add_task(self, callback, delay) -> Task:
        """
        Schedule a repeating task run from :meth:`tick`.

        Args:
            callback (callable): Zero-argument callable to run.
            delay (int): Interval between runs, in milliseconds.

        Returns:
            Task: The created task (pass to :meth:`remove_task` to cancel).
        """
        new_task = Task(callback, delay)
        self._tasks.append(new_task)
        return new_task

    def refresh(self, area: Area):
        """
        Copy a dirty region from the internal framebuffer to the physical display.

        Args:
            area: ``Area`` or ``(x, y, w, h)`` rectangle to flush.
        """
        area = area.clip(self.area)
        _log("Refreshing", area)
        x, y, w, h = area
        for row in range(y, y + h):
            buffer_begin = (row * self.width + x) * 2
            buffer_end = buffer_begin + w * 2
            self.display_drv.blit_rect(self._buffer[buffer_begin:buffer_end], x, row, w, 1)
        if _mark_updates_enabled():
            c = getrandbits(16)
            self.display_drv.fill_rect(x, y, w, 2, c)
            self.display_drv.fill_rect(x, y + h - 2, w, 2, c)
            self.display_drv.fill_rect(x, y, 2, h, c)
            self.display_drv.fill_rect(x + w - 2, y, 2, h, c)
        self.display_drv.show()

    def remove_task(self, task):
        """
        Cancel a scheduled task.

        Args:
            task (Task): A task previously returned by :meth:`add_task`.
        """
        self._tasks.remove(task)

    def quit(self):
        """Remove this display from the active list (called on QUIT)."""
        if self in Display.displays:
            Display.displays.remove(self)

    def tick(self):
        """
        Render one widget frame.

        Flushes dirty areas to the display, otherwise runs scheduled tasks and
        re-renders invalidated widgets. Driven automatically by the runtime's
        shared timer (see :meth:`_attach_to_runtime`); may also be called
        manually (e.g. :func:`tick`) to force a frame.
        """
        if self._tick_busy:
            return
        self._tick_busy = True

        if self._dirty_areas:
            # Coalesce touching/overlapping dirty rectangles before flushing.
            # Take ownership of the pending list up front so we never mutate a
            # list while iterating it, and merge transitively (a freshly merged
            # area may now touch one merged earlier).
            pending = self._dirty_areas
            self._dirty_areas = []
            merged = []
            for area in pending:
                i = 0
                while i < len(merged):
                    if area.touches_or_intersects(merged[i]):
                        area += merged.pop(i)
                        i = 0
                    else:
                        i += 1
                merged.append(area)

            for dirty in merged:
                self.refresh(dirty)
        else:
            t = ticks_ms()
            for task in self._tasks:
                if t >= task.next_run:
                    task.run(t)

            self.render_dirty_widgets()
        self._tick_busy = False

    @staticmethod
    def _dirty_children_z_order(widget):
        """Dirty direct children in paint order (``children`` index = z-order).

        ``dirty_widgets`` / ``dirty_descendants`` are sets, so iterating them
        directly is unordered on MicroPython and can paint a later sibling
        under an earlier one (e.g. D-pad disc Card over Up/Left keys, while
        labels — next BFS level — still appear on top).
        """
        dirty = widget.dirty_widgets | widget.dirty_descendants
        if not dirty:
            return []
        return [c for c in widget.children if c in dirty]

    def render_dirty_widgets(self):
        """Redraw all invalidated widgets, breadth-first, without recursion."""
        # Non-recursive redraw; enqueue with reversed() so stack.pop() paints
        # earlier children first (painter's algorithm).
        stack = list(reversed(self._dirty_children_z_order(self)))
        if not stack and self.dirty_descendants:
            # Fallback when dirt is not under ``children`` (should be rare).
            stack = list(self.dirty_descendants)

        while stack:
            # Collect all widgets at the current level
            current_level = []
            while stack:
                widget = stack.pop()
                if widget.invalidated and widget.visible:
                    widget.render()
                    self._dirty_areas.append(widget.area)
                current_level.append(widget)

            # Next level: dirty children in z-order (not set iteration order).
            for widget in current_level:
                stack.extend(reversed(self._dirty_children_z_order(widget)))

    def __getattr__(self, name):
        """Forward unknown attributes to the underlying ``display_drv``.

        Args:
            name: Attribute name to look up on ``display_drv``.

        Returns:
            The value from ``display_drv``.

        Raises:
            AttributeError: If neither this object nor ``display_drv`` has
                ``name``.
        """
        if name in _display_drv_get_attrs:
            return getattr(self.display_drv, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        """Forward known driver attributes to ``display_drv``, else set locally.

        Args:
            name: Attribute name.
            value: Value to assign.
        """
        if name in _display_drv_set_attrs:
            return setattr(self.display_drv, name, value)
        super().__setattr__(name, value)


def tick(_=None):
    """
    Call the ``tick`` method of every registered :class:`Display`.

    Args:
        _ (Any): Ignored positional argument so this may also be used as a
            timer/``on_tick`` callback signature.
    """
    for display in Display.displays:
        display.tick()
