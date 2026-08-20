# SPDX-FileCopyrightText: 2026 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Device adapters and input mappers for appdev."""

import events
import keys

try:
    from micropython import const
except ImportError:

    def const(x):
        return x


HOST = const(0x01)
POINTER = const(0x02)
ENCODER = const(0x03)
KEYPAD = const(0x04)
JOYSTICK = const(0x05)

_DEFAULT_TOUCH_ROTATION_TABLE = (0b000, 0b101, 0b110, 0b011)

SWAP_XY = const(0b001)
REVERSE_X = const(0b010)
REVERSE_Y = const(0b100)


def _key_name(key):
    """Human-readable name for a key code (never assume chr-safe)."""
    name = keys.keyname(key)
    if name != "Unknown":
        return name
    if isinstance(key, int) and 32 <= key <= 126:
        return chr(key)
    return "0x%x" % key if isinstance(key, int) else str(key)


def _normalize_points(sample):
    """Coerce a touch_read sample to a tuple of (x, y[, ...]) points."""
    if not sample:
        return ()
    first = sample[0]
    if isinstance(first, int):
        return (tuple(sample),)
    return tuple(tuple(p) for p in sample)


class Device:
    """Base class for hardware input device adapters."""

    type = 0

    def __init__(self):
        self.app = None
        self.user_data = None
        self._callbacks = []

    def subscribe(self, callback, event_types=None):
        if not callable(callback):
            raise ValueError("callback must be callable")
        item = (callback, event_types)
        if item not in self._callbacks:
            self._callbacks.append(item)

    def unsubscribe(self, callback, event_types=None):
        self._callbacks = [item for item in self._callbacks if item[0] is not callback]

    def _notify_callbacks(self, eventlist, *args):
        if not self._callbacks or not eventlist:
            return
        for event in eventlist:
            for cb, event_types in tuple(self._callbacks):
                if event_types is None or event.type in event_types:
                    cb(event, *args)


class Touch(Device):
    """Touchscreen adapter mapped to MOUSEMOTION and MOUSEBUTTONDOWN/UP events."""

    type = POINTER

    def __init__(self, read, display=None, rotation_table=None):
        super().__init__()
        if not callable(read):
            raise TypeError("read must be callable")
        if display is None:
            raise ValueError("Touch requires display=")
        self._read = read
        self._display = display
        self._rotation_table = rotation_table or _DEFAULT_TOUCH_ROTATION_TABLE
        if len(self._rotation_table) != 4:
            raise ValueError("rotation_table must have exactly 4 items")
        self._state = None
        self.rotation = getattr(display, "rotation", 0)
        display.touch_device = self
        self._inject_q = []
        self.points = ()

    @property
    def rotation(self):
        return self._rotation

    @rotation.setter
    def rotation(self, value):
        self._rotation = value % 360
        self._mask = self._rotation_table[self._rotation // 90]

    def inject_clear(self):
        """Drop pending synthetic samples."""
        self._inject_q.clear()

    def inject_point(self, xy):
        """Queue one sample: (x, y) display coords, or None for release."""
        self._inject_q.append(xy)

    def inject_tap(self, x, y, hold_frames=1):
        """Queue a press and release at display coordinates."""
        pt = (int(x), int(y))
        self._inject_q.append(pt)
        for _ in range(max(1, int(hold_frames)) - 1):
            self._inject_q.append(pt)
        self._inject_q.append(None)

    def _map_point(self, point):
        x = int(point[0])
        y = int(point[1])
        if self._mask & SWAP_XY:
            x, y = y, x
        if self._mask & REVERSE_X:
            x = self._display.width - x - 1
        if self._mask & REVERSE_Y:
            y = self._display.height - y - 1
        if len(point) > 2:
            return (x, y) + tuple(point[2:])
        return (x, y)

    def _emit_primary(self, x, y):
        last_pos = self._state
        self._state = (x, y)
        if last_pos is not None:
            last_x, last_y = last_pos
            return events.Motion(
                events.MOUSEMOTION,
                self._state,
                (x - last_x, y - last_y),
                (1, 0, 0),
                False,
                None,
            )
        return events.Button(events.MOUSEBUTTONDOWN, self._state, 1, False, None)

    def _emit_up(self):
        if self._state is not None:
            last_pos = self._state
            self._state = None
            return events.Button(events.MOUSEBUTTONUP, last_pos, 1, False, None)
        return None

    def poll(self, *args):
        if self._inject_q:
            sample = self._inject_q.pop(0)
            if sample is not None:
                x, y = int(sample[0]), int(sample[1])
                self.points = ((x, y),)
                ev = self._emit_primary(x, y)
                evs = [ev] if ev else []
                self._notify_callbacks(evs, *args)
                return evs
            self.points = ()
            ev = self._emit_up()
            evs = [ev] if ev else []
            self._notify_callbacks(evs, *args)
            return evs

        try:
            raw = self._read()
        except OSError:
            return []
        mapped = tuple(self._map_point(p) for p in _normalize_points(raw))
        self.points = mapped
        if mapped:
            ev = self._emit_primary(int(mapped[0][0]), int(mapped[0][1]))
            evs = [ev] if ev else []
            self._notify_callbacks(evs, *args)
            return evs
        ev = self._emit_up()
        evs = [ev] if ev else []
        self._notify_callbacks(evs, *args)
        return evs


class Keypad(Device):
    """Keypad/keyboard adapter mapped to KEYDOWN and KEYUP events."""

    type = KEYPAD

    def __init__(self, read):
        super().__init__()
        if not callable(read):
            raise TypeError("read must be callable")
        self._read = read
        self._state = set()

    def poll(self, *args):
        pressed_keys = set(self._read() or ())
        eventlist = []
        released = self._state - pressed_keys
        if released:
            for key in released:
                self._state.remove(key)
                eventlist.append(events.Key(events.KEYUP, _key_name(key), key, 0, 0, None))
        pressed = pressed_keys - self._state
        if pressed:
            for key in pressed:
                self._state.add(key)
                eventlist.append(events.Key(events.KEYDOWN, _key_name(key), key, 0, 0, None))
        self._notify_callbacks(eventlist, *args)
        return eventlist


class Encoder(Device):
    """Rotary encoder and button adapter mapped to MOUSEWHEEL and MOUSEBUTTON* events."""

    type = ENCODER

    def __init__(self, read, *, button_read=None, button=2):
        super().__init__()
        if not callable(read):
            raise TypeError("read must be callable")
        if button_read is not None and not callable(button_read):
            raise TypeError("button_read must be callable")
        self._read = read
        self._button_read = button_read
        self._button = button
        self._last_pos = 0
        self._last_pressed = False
        try:
            self._last_pos = self._read() or 0
        except Exception:
            pass

    def poll(self, *args):
        eventlist = []
        if self._button_read is not None:
            pressed = bool(self._button_read())
            if pressed != self._last_pressed:
                self._last_pressed = pressed
                eventlist.append(
                    events.Button(
                        events.MOUSEBUTTONDOWN if pressed else events.MOUSEBUTTONUP,
                        (0, 0),
                        self._button,
                        False,
                        None,
                    )
                )

        try:
            pos = self._read()
        except Exception:
            pos = self._last_pos
        if pos is not None and pos != self._last_pos:
            steps = pos - self._last_pos
            self._last_pos = pos
            if self._button % 2 == 0:
                eventlist.append(
                    events.Wheel(events.MOUSEWHEEL, False, 0, steps, 0, steps, False, None)
                )
            else:
                eventlist.append(
                    events.Wheel(events.MOUSEWHEEL, False, steps, 0, steps, 0, False, None)
                )
        self._notify_callbacks(eventlist, *args)
        return eventlist


class Joystick(Device):
    """Joystick adapter mapped to SDL Joy* events."""

    type = JOYSTICK

    def __init__(self, joystick_driver, *, emulate_digital=None, digital_threshold=0.5):
        super().__init__()
        self.driver = joystick_driver
        self.emulate_digital = emulate_digital
        self.digital_threshold = float(digital_threshold)
        self._state = [
            [0] * self.driver.get_numaxes(),
            [False] * self.driver.get_numbuttons(),
            [(0, 0)] * self.driver.get_numhats(),
            [(0, 0)] * self.driver.get_numballs(),
        ]
        if self.emulate_digital:
            self._state.append([(0, 0)] * len(self.emulate_digital))

    def _emulate(self, value):
        return (
            -1 if value < -self.digital_threshold else 1 if value > self.digital_threshold else 0
        )

    def poll(self, *args):
        eventlist = []
        new_state = [
            [self.driver.get_axis(i) for i in range(self.driver.get_numaxes())],
            [self.driver.get_button(i) for i in range(self.driver.get_numbuttons())],
            [self.driver.get_hat(i) for i in range(self.driver.get_numhats())],
            [self.driver.get_ball(i) for i in range(self.driver.get_numballs())],
        ]
        instance_id = self.driver.get_instance_id()

        for i, (old, new) in enumerate(zip(self._state[0], new_state[0])):
            if old != new:
                eventlist.append(events.JoyAxisMotion(events.JOYAXISMOTION, instance_id, i, new))

        for i, (old, new) in enumerate(zip(self._state[1], new_state[1])):
            if old != new:
                eventlist.append(
                    events.JoyButtonDown(events.JOYBUTTONDOWN, instance_id, i)
                    if new
                    else events.JoyButtonUp(events.JOYBUTTONUP, instance_id, i)
                )

        for i, (old, new) in enumerate(zip(self._state[2], new_state[2])):
            if old != new:
                eventlist.append(events.JoyHatMotion(events.JOYHATMOTION, instance_id, i, new))

        for i, (old, new) in enumerate(zip(self._state[3], new_state[3])):
            if old != new:
                eventlist.append(events.JoyBallMotion(events.JOYBALLMOTION, instance_id, i, new))

        if self.emulate_digital:
            axes = new_state[0]
            emulated = [
                (self._emulate(axes[x]), self._emulate(axes[y])) for x, y in self.emulate_digital
            ]
            new_state.append(emulated)
            for i, (old, new) in enumerate(zip(self._state[4], emulated)):
                if old != new:
                    eventlist.append(
                        events.JoyHatMotion(
                            events.JOYHATMOTION,
                            instance_id,
                            i + self.driver.get_numhats(),
                            new,
                        )
                    )

        self._state = new_state
        self._notify_callbacks(eventlist, *args)
        return eventlist


class HostEvents(Device):
    """Host event pump adapter for SDL2/PyGame and OS events."""

    type = HOST

    def __init__(self, host_read, display=None, event_filter=None):
        super().__init__()
        if not callable(host_read):
            raise TypeError("host_read must be callable")
        self._read = host_read
        self._display = display
        self._filter = event_filter or events.filter
        self.scale = getattr(display, "touch_scale", 1) if display is not None else 1
        self._quit_chord_ok = hasattr(display, "quit_chord")

    def _touch_scale_for(self, window_id):
        panel = self._display
        if window_id is not None and self.app is not None:
            for candidate in self.app.displays:
                if getattr(candidate, "_window_id", None) == window_id:
                    panel = candidate
                    break
        scale = getattr(panel, "touch_scale", None) if panel is not None else None
        if scale is None:
            return self.scale
        self.scale = scale
        return scale

    def poll(self, *args):
        raw = self._read()
        if not raw:
            return []
        eventlist = []
        quit_chord = getattr(self._display, "quit_chord", None) if self._quit_chord_ok else None
        chord_key = quit_chord[0] if quit_chord else None

        for event in raw:
            if event.type == events.KEYDOWN:
                if keys.chord_matches(quit_chord, event.key, event.mod):
                    event = events.Quit(events.QUIT)
            elif event.type == events.KEYUP and quit_chord and event.key == chord_key:
                continue

            if event.type in self._filter:
                if event.type in (
                    events.MOUSEMOTION,
                    events.MOUSEBUTTONDOWN,
                    events.MOUSEBUTTONUP,
                ):
                    scale = self._touch_scale_for(getattr(event, "window", None))
                    if scale and scale != 1:
                        pos = (int(event.pos[0] // scale), int(event.pos[1] // scale))
                        if event.type == events.MOUSEMOTION:
                            rel = (int(event.rel[0] // scale), int(event.rel[1] // scale))
                            event = events.Motion(
                                event.type,
                                pos,
                                rel,
                                event.buttons,
                                event.touch,
                                event.window,
                            )
                        else:
                            event = events.Button(
                                event.type,
                                pos,
                                event.button,
                                event.touch,
                                event.window,
                            )
                eventlist.append(event)
        self._notify_callbacks(eventlist, *args)
        return eventlist


class TouchGrid:
    """Maps a screen rectangle into a grid of app key IDs."""

    def __init__(
        self,
        app,
        x,
        y,
        w,
        h,
        cols=3,
        rows=3,
        keys=None,
        translate=None,
        on_press=None,
        on_release=None,
    ):
        self._app = app
        self._keys = keys if keys else list(range(cols * rows))
        self._on_press = on_press
        self._on_release = on_release
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.cols = cols
        self.rows = rows
        self.key_width = w / cols
        self.key_height = h / rows
        self._translate = translate or (lambda point: point)
        self._state = dict.fromkeys(self._keys, False)
        self._clicks = []
        self._app.on(
            [events.MOUSEBUTTONDOWN, events.MOUSEBUTTONUP, events.KEYDOWN, events.KEYUP],
            self._handle_event,
        )

    def _handle_event(self, event):
        if event.type in (events.MOUSEBUTTONDOWN, events.MOUSEBUTTONUP) and getattr(event, "button", 0) == 1:
            x, y = self._translate(event.pos)
            if x < self.x or x > self.x + self.w or y < self.y or y > self.y + self.h:
                return
            col = int((x - self.x) / self.key_width)
            row = int((y - self.y) / self.key_height)
            try:
                key = self._keys[row * self.cols + col]
                pressed = event.type == events.MOUSEBUTTONDOWN
                if pressed:
                    self._clicks.append(key)
                self._state[key] = pressed
                cb = self._on_press if pressed else self._on_release
                if cb is not None:
                    cb(key)
            except IndexError:
                return

        elif event.type in (events.KEYDOWN, events.KEYUP):
            key = event.key
            if key in self._keys:
                pressed = event.type == events.KEYDOWN
                if pressed:
                    self._clicks.append(key)
                self._state[key] = pressed
                cb = self._on_press if pressed else self._on_release
                if cb is not None:
                    cb(key)

    def read(self):
        """Return keys pressed since the last read (edge triggered)."""
        if not self._clicks:
            return None
        clicks = self._clicks
        self._clicks = []
        return clicks

    def read_held(self):
        """Return keys currently held down (level triggered)."""
        return [k for k, v in self._state.items() if v]


class JoyMap:
    """Maps joystick hat directions and buttons onto held key codes."""

    def __init__(self, app, joymap):
        self._app = app
        self._joymap = joymap
        self._state = {}
        for j in joymap.values():
            for h in j.get("hats", {}).values():
                for key in h:
                    self._state[key] = False
            for b in j.get("buttons", {}).values():
                self._state[b] = False
        self._app.on(
            [events.JOYHATMOTION, events.JOYBUTTONDOWN, events.JOYBUTTONUP],
            self._handle_event,
        )

    def _handle_event(self, event):
        if (
            event.type == events.JOYHATMOTION
            and (j := self._joymap.get(event.instance_id))
            and (h := j.get("hats", {}).get(event.hat))
        ):
            x, y = event.value
            self._state[h[0]] = x == -1
            self._state[h[1]] = x == 1
            self._state[h[2]] = y == -1
            self._state[h[3]] = y == 1
            return
        if (
            event.type in (events.JOYBUTTONDOWN, events.JOYBUTTONUP)
            and (j := self._joymap.get(event.instance_id))
            and (b := j.get("buttons", {}).get(event.button))
        ):
            self._state[b] = event.type == events.JOYBUTTONDOWN

    def read(self):
        """Return key codes currently held according to joymap."""
        return [k for k, v in self._state.items() if v]
