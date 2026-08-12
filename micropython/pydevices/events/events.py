# SPDX-FileCopyrightText: 2024 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""SDL2/PyGame-style event types and namedtuple event classes.

Import as ``import events`` and use ``events.QUIT``, ``events.Button(...)``.
"""

from collections import namedtuple
import sys

try:
    from micropython import const
except ImportError:

    def const(x):
        return x


QUIT = const(0x100)
KEYDOWN = const(0x300)
KEYUP = const(0x301)
MOUSEMOTION = const(0x400)
MOUSEBUTTONDOWN = const(0x401)
MOUSEBUTTONUP = const(0x402)
MOUSEWHEEL = const(0x403)
JOYAXISMOTION = const(0x600)
JOYBALLMOTION = const(0x601)
JOYHATMOTION = const(0x602)
JOYBUTTONDOWN = const(0x603)
JOYBUTTONUP = const(0x604)
# SDL2 touch-finger events (SDL_FINGERDOWN/UP/MOTION).
FINGERDOWN = const(0x700)
FINGERUP = const(0x701)
FINGERMOTION = const(0x702)
_USER_TYPE_BASE = 0x8000

filter = [  # noqa: A001
    QUIT,
    KEYDOWN,
    KEYUP,
    MOUSEMOTION,
    MOUSEBUTTONDOWN,
    MOUSEBUTTONUP,
    MOUSEWHEEL,
    JOYAXISMOTION,
    JOYBALLMOTION,
    JOYHATMOTION,
    JOYBUTTONDOWN,
    JOYBUTTONUP,
    FINGERDOWN,
    FINGERUP,
    FINGERMOTION,
]

Unknown = namedtuple("Unknown", "type")  # noqa: PYI024
Motion = namedtuple("Motion", "type pos rel buttons touch window")  # noqa: PYI024
Button = namedtuple("Button", "type pos button touch window")  # noqa: PYI024
Wheel = namedtuple("Wheel", "type flipped x y precise_x precise_y touch window")  # noqa: PYI024
Key = namedtuple("Key", "type name key mod scancode window")  # noqa: PYI024
Quit = namedtuple("Quit", "type")  # noqa: PYI024
Any = namedtuple("Any", "type")  # noqa: PYI024
JoyAxisMotion = namedtuple("JoyAxisMotion", "type instance_id axis value")  # noqa: PYI024
JoyButtonUp = namedtuple("JoyButtonUp", "type instance_id button")  # noqa: PYI024
JoyButtonDown = namedtuple("JoyButtonDown", "type instance_id button")  # noqa: PYI024
JoyHatMotion = namedtuple("JoyHatMotion", "type instance_id hat value")  # noqa: PYI024
JoyBallMotion = namedtuple("JoyBallMotion", "type instance_id ball rel")  # noqa: PYI024
Finger = namedtuple("Finger", "type pos finger_id window")  # noqa: PYI024


def _normalize_type_items(types):
    if isinstance(types, dict):
        return types.items()
    if isinstance(types, list):
        return types
    raise ValueError("types must be a dict or list of (name, value) tuples")


def register_event(name=None, value=None, *, fields=None, types=None, classes=None):
    """Register custom event type(s) and optional namedtuple class(es).

    Single type::

        register_event("MINE", 0x801)
        register_event("MINE")  # auto-allocated value

    Bulk types (dict or list of tuples) and classes (dict of field strings)::

        register_event(types=[("FOO", 0x900)], classes={"Foo": "type a b"})
    """
    mod = sys.modules[__name__]
    if types is not None:
        for type_name, type_value in _normalize_type_items(types):
            _register_event_type(mod, type_name, type_value)
    elif name is not None:
        _register_event_type(mod, name, value)

    class_map = classes if classes is not None else {}
    if fields is not None:
        if name is None:
            raise ValueError("fields requires name")
        class_map = {name: fields}

    for event_class_name, event_class_fields in class_map.items():
        event_class_name = event_class_name[0].upper() + event_class_name[1:].lower()
        if hasattr(mod, event_class_name):
            raise ValueError(f"Event class {event_class_name} already exists in events module.")
        event_class_fields = event_class_fields.lower()
        setattr(
            mod,
            event_class_name,
            namedtuple(event_class_name, event_class_fields),  # noqa: PYI024
        )


def _register_event_type(mod, type_name, value):
    type_name = type_name.upper()
    if hasattr(mod, type_name):
        raise ValueError(f"Event type {type_name} already exists in events module.")
    setattr(mod, type_name, value or mod._USER_TYPE_BASE)
    if not value:
        mod._USER_TYPE_BASE += 1
