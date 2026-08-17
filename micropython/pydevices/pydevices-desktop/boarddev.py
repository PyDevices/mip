# SPDX-FileCopyrightText: 2026 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Lazy end-device binding for board_peripherals -> board_config.

``board_peripherals.load_peripherals(globals())`` typically calls
``bind_lazy(ns, this_module)``. Apps never import ``boarddev`` directly;
they use ``board_config.PERIPHERALS`` and attribute access.
"""


def bind_lazy(ns, peripherals_mod):
    """Install module ``__getattr__`` / ``__dir__`` on *ns* for lazy roles.

    Each name in ``peripherals_mod.PERIPHERALS`` maps to a zero-arg factory
    ``peripherals_mod.<name>()``. First access constructs, caches into
    ``ns[name]``, and returns the object. Further access hits the module
    dict (no ``__getattr__``).
    """
    roles = peripherals_mod.PERIPHERALS

    def __getattr__(name):
        if name not in roles:
            raise AttributeError("module has no attribute {!r}".format(name))
        factory = getattr(peripherals_mod, name)
        obj = factory()
        ns[name] = obj
        return obj

    def __dir__():
        names = list(ns.keys())
        for role in roles:
            if role not in ns:
                names.append(role)
        return sorted(names)

    ns["__getattr__"] = __getattr__
    ns["__dir__"] = __dir__
