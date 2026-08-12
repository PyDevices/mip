# SPDX-FileCopyrightText: 2026 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Small compatibility helpers for Python hosts without ``micropython``."""

try:
    from micropython import const
except ImportError:

    def const(value):
        return value
