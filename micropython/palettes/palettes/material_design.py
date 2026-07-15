# SPDX-FileCopyrightText: 2024 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Material Design color palette.

256 swatches from the Material Design spec, exposed as indexed colors and
named attributes. Each hue family includes shades ``S50``–``S900``; most
families also provide accent colors ``A100``, ``A200``, ``A400``, and
``A700``.

Example:
    >>> from palettes import get_palette
    >>> palette = get_palette(name="material_design", color_depth=16)
    >>> palette.RED
    >>> palette.RED_S900
    >>> palette[127]
"""

from . import MappedPalette
from ._material_design import COLORS, FAMILIES, LENGTHS


class MDPalette(MappedPalette):
    """Material Design swatch palette.

    Colors are stored in a flat RGB map. During initialization, named
    attributes are created for each family and shade (for example
    ``RED``, ``RED_S500``, ``RED_A700``). The unsuffixed name always
    refers to the ``S500`` primary shade.

    Args:
        name: Label for :attr:`~palettes.Palette.name`; defaults to
            ``"MaterialDesign"`` when empty.
        color_depth: Output format; see :class:`~palettes.Palette`.
        swapped: Byte-swap 16-bit colors when ``True``.
        color_map: RGB byte map; defaults to the built-in Material Design table.
    """

    _shades = [
        "S50",
        "S100",
        "S200",
        "S300",
        "S400",
        "S500",
        "S600",
        "S700",
        "S800",
        "S900",
    ]

    _accents = ["A100", "A200", "A400", "A700"]

    def __init__(self, name="", color_depth=16, swapped=False, color_map=COLORS):
        super().__init__(name, color_depth, swapped, color_map)
        self._name = name if name else "MaterialDesign"

    def _define_named_colors(self):
        # The colors are already available as pal[0], pal[1], etc.
        # Now we want to add pal.BLACK = pal[0], pal.WHITE = pal[1], etc.
        color_index = 0
        if len(FAMILIES) != len(LENGTHS):
            raise ValueError("FAMILIES and LENGTHS must have the same length")
        for i, name in enumerate(FAMILIES):
            length = LENGTHS[i]
            if length == 1:  # black or white
                setattr(self, name.upper(), self[color_index])
                color_index += 1
            else:
                for shade in self._shades:
                    setattr(self, f"{name}_{shade}".upper(), self[color_index])
                    # S500 is the default shade for each family, so add it to the palette
                    # without the _S500 suffix
                    if shade == "S500":
                        setattr(self, name.upper(), self[color_index])
                    color_index += 1
                if length == 14:
                    for accent in self._accents:
                        setattr(self, f"{name}_{accent}".upper(), self[color_index])
                        color_index += 1
