# SPDX-FileCopyrightText: 2024 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Base widget class and geometry/event primitives."""

from pygraphics import Area

from ._constants import ALIGN, DEFAULT_PADDING, POSITION
from ._themes import ColorTheme
from ._util import _POINTER_EVENTS, _cond_always, _cond_pointer, _log


class Widget:
    """Base class for pdwidgets UI elements and simple container layouts.

    Subclass :class:`Widget` to build a custom control, or use it directly as a
    lightweight layout container. Each widget has a local geometry, an optional
    parent/child tree, a semantic value, and a small event model. The default
    implementation draws a solid background and leaves the interesting visuals to
    subclasses, while the base class handles hit-testing, invalidation, and
    child propagation.

    In practice, most applications compose a tree of widgets with
    :class:`Screen` and :class:`Display`, then use alignment and padding to
    arrange content rather than manually calculating absolute coordinates.
    """
    next_instance_id = 0

    def __init__(
        self,
        parent,
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
    ):
        """Create a widget in a parent tree with optional geometry and styling.

        Args:
            parent (Widget): Parent widget that owns this child. The root display
                is the only widget that may have no parent.
            x (int): Relative x offset from the parent or alignment anchor.
            y (int): Relative y offset from the parent or alignment anchor.
            w (int): Width in pixels; defaults to the parent's width.
            h (int): Height in pixels; defaults to the parent's height.
            align (int): Alignment constant from :data:`ALIGN`.
            align_to (Widget): Widget used as the alignment anchor.
            fg (int): Foreground color; falls back to the parent color.
            bg (int): Background color; falls back to the parent color.
            visible (bool): Whether the widget is shown immediately.
            value (Any): Widget value such as text, numeric state, or a model object.
            padding (tuple): Padding applied to the widget's content area.
            radius (int): Corner radius stored on the widget; subclasses may use
                it when drawing rounded surfaces.

        Example:
            screen = Screen(display)
            title = Label(screen, x=8, y=8, value="Hello")
        """
        self.id = Widget.next_instance_id  # Currently only used in debugging
        Widget.next_instance_id += 1

        self._parent: Widget = None
        self.fg = fg if fg is not None else parent.fg if parent else -1
        self.bg = bg if bg is not None else parent.bg if parent else 0
        self._visible = visible
        self._value = value  # Value of the widget (e.g., text of a label)
        self.padding = padding if padding is not None else DEFAULT_PADDING
        self.radius = radius

        self.children: list[Widget] = []
        self.dirty_widgets = set()
        self.dirty_descendants = set()
        self.invalidated = False
        self._event_callbacks = {}
        self._change_callback = None

        self._x = self._y = self._w = self._h = self._align = self._align_to = None
        # When True, this widget's padded_area clips descendant drawing (ScrollView / ListView).
        self.clip_content = False
        self.set_position(
            x,
            y,
            w or parent.width,
            h or parent.height,
            align if align is not None else ALIGN.TOP_LEFT,
            align_to or parent,
        )
        self.parent: Widget = parent
        self._register_callbacks()

    def __str__(self):
        """Return a short ``ID <n> <ClassName>`` label for debugging."""
        return f"ID {self.id} {self.__class__.__name__}"

    def __format__(self, format_spec):
        """Format like :meth:`__str__`, applying ``format_spec`` to the class name.

        Args:
            format_spec: Format specifier applied to the class name portion.
        """
        return f"ID {self.id} {self.__class__.__name__:{format_spec}}"

    def _register_callbacks(self):
        """
        Register event callbacks for the widget.  Subclasses should override this method to register event callbacks.
        """

    def add_event_cb(self, event_type, callback, data=None):
        """Register an event handler for this widget.

        Args:
            event_type (int): ``events`` constant such as
                ``events.MOUSEBUTTONDOWN`` or ``events.KEYDOWN``.
            callback (callable): Callable invoked as ``callback(data_or_sender, event)``.
            data (Any): User data passed as the first callback argument; defaults to
                the widget itself.

        This is the primary way to react to pointer and keyboard input without
        overriding :meth:`handle_event` in every subclass.
        """
        # Each item's key is the callback and value is the optional data.  If the event_type is not found,
        # add it to the dictionary with the callback and data.
        data = data or self
        if event_type not in self._event_callbacks:
            self._event_callbacks[event_type] = {}
        self._event_callbacks[event_type][callback] = data

    def remove_event_cb(self, event_type: int, callback: callable):
        """
        Remove a previously registered event callback.

        Args:
            event_type (int): ``events`` constant the callback was
                registered for.
            callback (callable): The callback to remove. No error if absent.
        """
        if event_type in self._event_callbacks:
            self._event_callbacks[event_type].pop(callback, None)

    def handle_event(self, event, condition=None, point=None):
        """Dispatch an event through the widget tree.

        The default implementation walks the children in order, checks whether
        each child should receive the event, and invokes any registered callbacks
        for that event type. Pointer events are translated to display
        coordinates once per dispatch so child widgets can reason about screen
        positions consistently.

        Args:
            event (Event): The event to handle.
            condition (callable): ``condition(child, event, point)`` returning
                ``True`` when the event should reach ``child``. The default
                uses pointer hit-testing for mouse/touch events and falls back to
                unconditional delivery for keyboard and other events.
            point (tuple): Pre-translated pointer position shared across the
                recursive walk.
        """
        if condition is None:
            if event.type in _POINTER_EVENTS:
                condition = _cond_pointer
                point = self.display.translate_point(event.pos)
            else:
                condition = _cond_always
        # Snapshot: click handlers often rebuild the tree (remove_child) mid-walk.
        for child in list(self.children):
            if child.parent is not self:
                continue
            if child.visible:
                if condition(child, event, point):
                    for callback, data in child._event_callbacks.get(event.type, {}).items():
                        callback(data, event)
                if child.parent is not self:
                    continue
                child.handle_event(event, condition, point)

    @property
    def parent(self):
        """Parent widget that contains this widget."""
        return self._parent

    @parent.setter
    def parent(self, parent):
        """
        Reparent this widget.

        Args:
            parent (Widget): New parent, or ``None`` to detach.
        """
        if parent != self._parent:
            if self._parent:
                self._parent.remove_child(self)
            self._parent = parent
            if self._parent:
                self._parent.add_child(self)
                if self.align_to is None:
                    self.set_position(align_to=parent)

    @property
    def area(self) -> Area:
        """
        Absolute bounding box of the widget on screen.

        Returns:
            Area: ``(x, y, width, height)`` in display coordinates.
        """
        return Area(self.x, self.y, self.width, self.height)

    @property
    def padded_area(self):
        """Bounding box inset by :attr:`padding`."""
        return self.area.inset(*self.padding)

    @property
    def x(self):
        """Calculate the absolute x-coordinate of the widget based on align"""
        align = self.align
        align_to = self.align_to or self.display

        x = align_to.x + int(self._x)

        if align & POSITION.LEFT:
            if align & POSITION.OUTER:
                x -= self.width
        elif align & POSITION.RIGHT:
            x += align_to.width
            if not align & POSITION.OUTER:
                x -= self.width
        else:
            x += (align_to.width - self.width) // 2

        return x

    @x.setter
    def x(self, x):
        """Set the relative x-coordinate (triggers relayout)."""
        self.set_position(x=x)

    @property
    def y(self):
        """Calculate the absolute y-coordinate of the widget based on align"""
        align = self.align
        align_to = self.align_to or self.display

        y = align_to.y + int(self._y)

        if align & POSITION.TOP:
            if align & POSITION.OUTER:
                y -= self.height
        elif align & POSITION.BOTTOM:
            y += align_to.height
            if not align & POSITION.OUTER:
                y -= self.height
        else:
            y += (align_to.height - self.height) // 2

        return y

    @y.setter
    def y(self, y):
        """Set the relative y-coordinate (triggers relayout)."""
        self.set_position(y=y)

    @property
    def width(self):
        """Widget width in pixels."""
        return int(self._w)

    @width.setter
    def width(self, w):
        """Set widget width in pixels."""
        self.set_position(w=w)

    @property
    def height(self):
        """Widget height in pixels."""
        return int(self._h)

    @height.setter
    def height(self, h):
        """Set widget height in pixels."""
        self.set_position(h=h)

    @property
    def align(self):
        """Alignment constant from :data:`ALIGN`."""
        return self._align

    @align.setter
    def align(self, align):
        """Set alignment relative to :attr:`align_to`."""
        self.set_position(align=align)

    @property
    def align_to(self):
        """Widget used as the alignment anchor."""
        return self._align_to

    @align_to.setter
    def align_to(self, align_to):
        """Set the alignment anchor widget."""
        self.set_position(align_to=align_to)

    @property
    def display(self):
        """Root :class:`Display` for this widget subtree."""
        return self.parent.display

    @property
    def color_theme(self) -> ColorTheme:
        """Semantic color palette from the display."""
        return self.display.color_theme

    @property
    def visible(self):
        """Get widget visibility.

        Detached widgets (``parent is None``) are not visible. The root
        :class:`~pdwidgets.display.Display` overrides this.
        """
        if not self._visible:
            return False
        parent = self._parent
        return parent is not None and parent.visible

    @visible.setter
    def visible(self, visible):
        """Set widget visibility."""
        if visible != self._visible:
            if not self.visible:
                self._visible = True
                self.invalidate()
            else:
                self._visible = False
                if self._parent is not None:
                    self._parent.invalidate()

    @property
    def value(self):
        """Widget value (text, number, bool, etc.)."""
        return self._value

    @value.setter
    def value(self, value):
        """Set the value and call :meth:`changed` when it differs."""
        if value != self._value:
            self._value = value
            self.changed()

    def add_child(self, child):
        """Adds a child widget to the current widget."""
        _log("Adding", child, "to", self)
        self.children.append(child)
        child.invalidate()

    def changed(self):
        """Called when the value of the widget changes.  May be overridden in subclasses.
        If overridden, the subclass should call this method to trigger the on_change_callback and invalidate.
        """
        if self.visible:
            if self._change_callback:
                self._change_callback(self)
            self.invalidate()

    def draw(self, area=None):
        """
        Draw the widget on the screen.  Subclasses should override this method to draw the widget unless the widget is
        a container widget (like a screen) that contains other widgets.  Subclasses may call this method to draw the
        background of the widget before drawing other elements.
        """
        if self.bg is not None:
            area = self.area if area is None else area
            self.display.framebuf.fill_rect(*area, self.bg)

    def hide(self, hide=True):
        """
        Show or hide the widget.

        Args:
            hide (bool): ``True`` to hide, ``False`` to show.
        """
        self.visible = not hide

    def invalidate(self):
        """Mark this widget (and its descendants) as needing a redraw."""
        if not self.invalidated:
            self.invalidated = True
            if self.parent:
                self.parent.add_dirty_widget(self)
            for child in self.children:
                child.invalidate()

    def remove(self):
        """Detach this widget from its parent (no-op if already detached)."""
        parent = self._parent
        if parent is not None:
            parent.remove_child(self)

    def clear(self):
        """Remove all child widgets via :meth:`remove_child`."""
        for child in list(self.children):
            self.remove_child(child)

    def remove_child(self, widget):
        """Removes a child widget from the current widget.

        Detaches the child so it cannot paint again via leftover dirty-set
        entries (page swaps that leave empty regions would otherwise ghost).
        """
        self.children.remove(widget)
        self.dirty_widgets.discard(widget)
        self.dirty_descendants.discard(widget)
        if widget._parent is self:
            widget._parent = None
        self.invalidate()

    def set_change_cb(self, callback):
        """
        Set the callback invoked when the widget's value changes.

        Args:
            callback (callable): Called as ``callback(widget)`` on change.
        """
        self._change_callback = callback

    def set_position(self, x=None, y=None, w=None, h=None, align=None, align_to=None):
        """Update a subset of the widget's geometry and relayout state.

        Only the arguments that are not ``None`` are changed. Geometry changes
        invalidate the parent so the affected area is redrawn on the next tick.
        This is the preferred way to reposition or resize widgets after they
        have already been created.

        Args:
            x (int): New relative x-coordinate.
            y (int): New relative y-coordinate.
            w (int): New width in pixels.
            h (int): New height in pixels.
            align (int): New ``ALIGN`` constant.
            align_to (Widget): New widget to align against.
        """
        changed = False
        if x is not None:
            self._x = x
            changed = True
        if y is not None:
            self._y = y
            changed = True
        if w is not None:
            self._w = w
            changed = True
        if h is not None:
            self._h = h
            changed = True
        if align is not None:
            self._align = align
            changed = True
        if align_to is not None:
            self._align_to = align_to
            changed = True
        if changed and self.parent is not None:
            self.parent.invalidate()

    def add_dirty_widget(self, child):
        """Mark a direct child as dirty for rendering."""
        self.dirty_widgets.add(child)
        self.dirty_descendants.add(child)
        if self.parent:
            self.parent.add_dirty_descendant(self)

    def add_dirty_descendant(self, branch):
        """Bubble a dirty descendant up the tree."""
        self.dirty_descendants.add(branch)
        if self.parent:
            self.parent.add_dirty_descendant(self)

    def _clip_from_ancestors(self):
        """Intersect padded areas of ancestors with ``clip_content`` set."""
        clip = None
        node = self.parent
        while node is not None:
            if getattr(node, "clip_content", False):
                area = node.padded_area
                clip = area if clip is None else clip.clip(area)
            node = node.parent
        if clip is not None and (clip.w <= 0 or clip.h <= 0):
            return None
        return clip

    def render(self):
        """Redraw this widget if invalidated, then clear its dirty flags."""
        if self.invalidated:
            _log("Drawing", self, "on", self.parent, "at", self.area)
            clip = self._clip_from_ancestors()
            if clip is not None:
                self.display.clip_push(clip)
            try:
                self.draw()
            finally:
                if clip is not None:
                    self.display.clip_pop()
            self.invalidated = False
            if self.parent:
                self.parent.remove_dirty_widget(self)

    def remove_dirty_widget(self, child):
        """Clear a child from the dirty set."""
        self.dirty_widgets.discard(child)
        if not self.dirty_widgets and not self.dirty_descendants and self.parent:
            self.parent.remove_dirty_descendant(self)

    def remove_dirty_descendant(self, branch):
        """Clear a descendant branch from the dirty set."""
        self.dirty_descendants.discard(branch)

    def set_value(self, value) -> None:
        """
        Set the widget's value (equivalent to assigning ``widget.value``).

        Args:
            value (Any): The new value; triggers ``changed`` when it differs.
        """
        self.value = value

    def set_modal(self, modal=True):
        """
        Grab or release modal pointer capture for this widget.

        While a widget is modal, the :class:`Display` routes all pointer events
        (mouse/touch) through this widget's branch only, so widgets elsewhere in
        the tree do not receive them. Non-pointer events (e.g. key events) are
        unaffected. This is used by :class:`Dialog` and :class:`Dropdown` to
        implement modal overlays without a separate event layer. Modality nests:
        the most recently grabbed widget wins, and releasing restores the
        previous one.

        Args:
            modal (bool): ``True`` to grab modal capture, ``False`` to release.
        """
        modals = self.display._modals
        if modal:
            if self not in modals:
                modals.append(self)
        elif self in modals:
            modals.remove(self)
