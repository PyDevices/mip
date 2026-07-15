# SPDX-FileCopyrightText: 2024 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Color palette toolkit for pydisplay.

Provides named color sets, RGB/HSV wheels, RGB cubes, and Material Design
swatches. Palettes map integer indices to display-ready color values at
several bit depths (4, 8, 16, or 24).

Example:
    >>> from palettes import get_palette
    >>> palette = get_palette(name="wheel", length=256, saturation=1.0)
    >>> palette[0]
    >>> palette.color_name(0)

Attributes:
    WIN16: Mapping of ``0xRRGGBB`` values to Windows 16-color names. Used as
        the default name table for :class:`Palette` and
        :class:`~palettes.wheel.WheelPalette`.
"""

WIN16 = {
    0x000000: "Black",
    0x000080: "Navy",
    0x0000FF: "Blue",
    0x008000: "Green",
    0x008080: "Teal",
    0x00FF00: "Lime",
    0x00FFFF: "Cyan",
    0x800000: "Maroon",
    0x800080: "Purple",
    0x808000: "Olive",
    0x808080: "Grey",
    0xC0C0C0: "Silver",
    0xFF0000: "Red",
    0xFF00FF: "Magenta",
    0xFFFF00: "Yellow",
    0xFFFFFF: "White",
}


def get_palette(name="default", **kwargs):
    """Construct a palette by logical name.

    Args:
        name: Palette type. One of ``"default"`` (Windows 16-color),
            ``"wheel"``, ``"cube"``, or ``"material_design"``. Unknown names
            fall back to :class:`Palette`.
        **kwargs: Forwarded to the palette constructor (for example
            ``color_depth``, ``length``, ``size``, ``saturation``).

    Returns:
        A :class:`Palette` subclass instance.

    Example:
        >>> get_palette(name="cube", size=3, color_depth=16)
    """
    if name == "wheel":
        from .wheel import WheelPalette as MyPalette
    elif name == "material_design":
        from .material_design import MDPalette as MyPalette
    elif name == "cube":
        from .cube import CubePalette as MyPalette
    else:
        MyPalette = Palette
    return MyPalette(name, **kwargs)


class Palette:
    """Indexed color palette with optional named color attributes.

    Subclasses override :meth:`_get_rgb` to define how each index maps to
    red, green, and blue components. :meth:`__getitem__` converts those
    components to the configured ``color_depth``.

    Named colors from the palette's name table (for example ``palette.RED``)
    are attached as attributes during initialization.

    Args:
        name: Optional label stored in :attr:`name`.
        color_depth: Output format for :meth:`__getitem__`: ``4`` (24-bit
            index), ``8`` (RGB332), ``16`` (RGB565), or ``24`` (``0xRRGGBB``).
        swapped: If ``True``, byte-swap 16-bit colors (little-endian displays).
        cached: If ``True``, memoize computed index colors in an internal dict.
    """

    def __init__(self, name="", color_depth=16, swapped=False, cached=False):
        self._name = name
        self._color_depth = color_depth
        self._swapped = swapped
        self._cache = {} if cached else None

        if not hasattr(self, "_names"):
            self._names = WIN16
        if not hasattr(self, "_length"):
            self._length = len(self._names)

        self._define_named_colors()

    def _define_named_colors(self):
        for color, name in self._names.items():
            if self._color_depth == 16:
                color = self.color565(color)
            elif self._color_depth == 8:
                color = self.color332(color)
            elif self._color_depth == 4:
                color = list(self._names.keys()).index(color)
            setattr(self, name.replace(" ", "_").upper(), color)

    @property
    def name(self):
        """Human-readable palette label."""
        return self._name

    def __iter__(self):
        """Yield each palette entry in index order."""
        for i in range(len(self)):
            yield self[i]

    def __len__(self):
        """Number of colors in the palette."""
        return self._length

    def __getitem__(self, index):
        """Return the color at ``index`` in the configured bit depth.

        Negative indices and indices beyond the palette length wrap around.

        Args:
            index: Color index (supports negative and out-of-range values).

        Returns:
            Color value as an integer (format depends on ``color_depth``).

        Raises:
            ValueError: If ``color_depth`` is not 4, 8, 16, or 24.
        """
        index = self._normalize(index)

        if self._cache is not None and index in self._cache:
            return self._cache[index]

        r, g, b = self._get_rgb(index)
        if self._color_depth == 24 or self._color_depth == 4:
            return r << 16 | g << 8 | b
        elif self._color_depth == 16:
            return self.color565(r, g, b)
        elif self._color_depth == 8:
            return self.color332(r, g, b)
        raise ValueError("Invalid color depth")

    def _normalize(self, index):
        while index < 0:
            index += len(self)
        if index >= len(self):
            index %= len(self)
        return index

    def color565(self, r, g=None, b=None):
        """Convert RGB to a 16-bit RGB565 value.

        Args:
            r: Red component (0–255), a 24-bit ``0xRRGGBB`` integer, or an
                ``(r, g, b)`` sequence.
            g: Green component when ``r`` is passed separately.
            b: Blue component when ``r`` is passed separately.

        Returns:
            16-bit color, optionally byte-swapped when ``swapped`` is ``True``.
        """
        if isinstance(r, (tuple, list)):
            # r is a tuple or list
            r, g, b = r
        elif g is None:
            # r is a 24-bit color
            r, g, b = r >> 16 & 0xFF, r >> 8 & 0xFF, r & 0xFF

        color = (r & 0xF8) << 8 | (g & 0xFC) << 3 | b >> 3
        if self._swapped:
            return (color & 0xFF) << 8 | (color & 0xFF00) >> 8
        else:
            return color

    def color332(self, r, g=None, b=None):
        """Convert RGB to an 8-bit RGB332 value.

        Args:
            r: Red component (0–255), a 24-bit ``0xRRGGBB`` integer, or an
                ``(r, g, b)`` sequence.
            g: Green component when ``r`` is passed separately.
            b: Blue component when ``r`` is passed separately.

        Returns:
            8-bit RGB332 color.
        """
        # Convert r, g, b to 8-bit
        if isinstance(r, (tuple, list)):
            # r is a tuple or list
            r, g, b = r
        elif g is None:
            # r is a 24-bit color
            r, g, b = r >> 16 & 0xFF, r >> 8 & 0xFF, r & 0xFF

        color = (r & 0xE0) | (g & 0xE0) >> 3 | (b & 0xC0) >> 6
        return color

    def color_rgb(self, color):
        """Expand a packed color to an ``(r, g, b)`` tuple.

        Args:
            color: A 16-bit integer, or a 2- or 3-byte sequence in display
                byte order.

        Returns:
            ``(red, green, blue)`` with each component in ``0``–``255``.
        """
        if isinstance(color, int):
            # convert 16-bit int color to 2 bytes
            color = (color & 0xFF, color >> 8)
        if len(color) == 2:
            r = color[1] & 0xF8 | (color[1] >> 5) & 0x7  # 5 bit to 8 bit red
            g = color[1] << 5 & 0xE0 | (color[0] >> 3) & 0x1F  # 6 bit to 8 bit green
            b = color[0] << 3 & 0xF8 | (color[0] >> 2) & 0x7  # 5 bit to 8 bit blue
        else:
            r, g, b = color
        return (r, g, b)

    def color_name(self, index):
        """Return the name of the color at ``index``.

        Args:
            index: Palette index (supports wrapping).

        Returns:
            A name from the palette name table, or a ``"#RRGGBB"`` hex string
            when no name matches.
        """
        return self.rgb_name(self._get_rgb(self._normalize(index)))

    def rgb_name(self, r, g=None, b=None):
        """Look up a color name from RGB components.

        Args:
            r: Red (0–255), a 24-bit integer, or an ``(r, g, b)`` sequence.
            g: Green when ``r`` is passed separately.
            b: Blue when ``r`` is passed separately.

        Returns:
            Matching name from :attr:`_names`, or ``"#RRGGBB"`` if unknown.
        """
        if isinstance(r, (tuple, list)):
            r, g, b = r
        return self._names.get(r << 16 | g << 8 | b, f"#{r:02X}{g:02X}{b:02X}")

    def luminance(self, index):
        """Perceived brightness of the color at ``index`` (ITU-R BT.601).

        Args:
            index: Palette index.

        Returns:
            Luminance in ``0.0``–``255.0``.
        """
        r, g, b = self._get_rgb(index)
        return 0.299 * r + 0.587 * g + 0.114 * b

    def brightness(self, index):
        """Average channel brightness of the color at ``index``.

        Args:
            index: Palette index.

        Returns:
            Normalized brightness in ``0.0``–``1.0``.
        """
        r, g, b = self._get_rgb(index)
        return (r + g + b) / 3 / 255

    def _get_rgb(self, index):
        color = list(self._names.keys())[index]
        return color >> 16 & 0xFF, color >> 8 & 0xFF, color & 0xFF


class MappedPalette(Palette):
    """Palette backed by a flat RGB byte map.

    Each color occupies three consecutive bytes ``(r, g, b)`` in
    ``color_map``. Subclasses such as :class:`~palettes.material_design.MDPalette`
    supply a pre-built map and named-color attributes.

    Args:
        name: Optional label stored in :attr:`name`.
        color_depth: Output format for :meth:`Palette.__getitem__`.
        swapped: Byte-swap 16-bit colors when ``True``.
        color_map: ``bytes`` or buffer of RGB triplets, length ``3 * n_colors``.
    """

    def __init__(self, name, color_depth, swapped, color_map):
        self._color_map = color_map
        self._length = len(color_map) // 3
        super().__init__(name, color_depth, swapped)

    def _get_rgb(self, index):
        r, g, b = self._color_map[index * 3 : index * 3 + 3]
        return r, g, b
