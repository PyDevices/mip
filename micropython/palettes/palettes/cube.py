# SPDX-FileCopyrightText: 2024 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""RGB color-cube palettes.

Samples the RGB cube at evenly spaced points. Supported cube sizes are
2, 3, 4, and 5 (8, 27, 64, or 125 colors). Each size uses a built-in
name table for :meth:`~palettes.Palette.color_name`.

Example:
    >>> from palettes import get_palette
    >>> palette = get_palette(name="cube", size=5, color_depth=16)
    >>> len(palette)
    125
"""

from . import Palette as _Palette


class CubePalette(_Palette):
    """Evenly spaced RGB cube palette.

    Indices traverse the cube in ``x``, then ``y``, then ``z`` order. Channel
    values are spaced from ``0`` to ``255`` inclusive.

    Args:
        name: Prefix for :attr:`~palettes.Palette.name` (length suffix is added).
        color_depth: Output format; see :class:`~palettes.Palette`.
        swapped: Byte-swap 16-bit colors when ``True``.
        cached: Memoize index lookups when ``True`` (default).
        size: Cube edge length. Must be ``2``, ``3``, ``4``, or ``5``.
    """

    def __init__(self, name="", color_depth=16, swapped=False, cached=True, size=5):
        self._size = size
        self._length = size**3
        self._values = [round(i * (255 / (size - 1)) + 0.25) for i in range(size)]

        if self._size == 2:
            from ._cube8 import CUBE8 as NAMES
        elif self._size == 3:
            from ._cube27 import CUBE27 as NAMES
        elif self._size == 4:
            from ._cube64 import CUBE64 as NAMES
        else:
            from ._cube125 import CUBE125 as NAMES
        self._names = NAMES
        super().__init__(name + str(self._length), color_depth, swapped, cached)

    def _get_rgb(self, index):
        z = index % self._size
        index //= self._size
        y = index % self._size
        index //= self._size
        x = index % self._size
        return self._values[x], self._values[y], self._values[z]
