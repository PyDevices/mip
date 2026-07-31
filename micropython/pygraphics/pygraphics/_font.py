# SPDX-FileCopyrightText: Tony DiCola, 2024 Brad Barnett
#
# SPDX-License-Identifier: MIT

"""
`pygraphics._font`
====================================================

A module to draw text to a canvas using fonts from
https://github.com/spacerace/romfont
"""

import os
import struct

from ._area import Area

sep = os.sep if hasattr(os, "sep") else "/"  # PyScipt doesn't have os.sep

try:  # MicroPython-WASM (PyScript) does not define FileNotFoundError.
    _FileNotFoundError = FileNotFoundError
except NameError:
    _FileNotFoundError = OSError

# Default embedded romfont data (https://github.com/spacerace/romfont).
# Loaded lazily so importing text helpers does not pull all three fonts at once.
_FONT_MODULES = {
    8: "_font_8x8",
    14: "_font_8x14",
    16: "_font_8x16",
}
_FONTS = {}


def _font_blob(height):
    blob = _FONTS.get(height)
    if blob is not None:
        return blob
    mod_name = _FONT_MODULES.get(height)
    if mod_name is None:
        mod_name = _FONT_MODULES[8]
        height = 8
    mod = __import__(__name__.rsplit(".", 1)[0] + "." + mod_name, None, None, ("FONT",))
    blob = mod.FONT
    _FONTS[height] = blob
    return blob


_DEFAULT_FONT_HEIGHT = 8


def text(*args, height=8, **kwargs):
    """
    Selector to call the correct text function based on the height of the font.
    See text8, text14, and text16 for more information.

    Args:
        height (int): The height of the font to use.  Default is 8.
    """
    if height == 8:
        return text8(*args, **kwargs)
    if height == 14:
        return text14(*args, **kwargs)
    if height == 16:
        return text16(*args, **kwargs)
    raise ValueError("Unsupported font height: %d" % height)


def text8(canvas, s, x, y, c=1, scale=1, inverted=False, font_data=None):
    """
    Draw a single line of text with the built-in 8-pixel font.

    This helper is used throughout pydisplay examples for labels, status text,
    and scrolling captions. The text is written into the given canvas at
    ``(x, y)`` and returns the region that was updated so that it can be used
    as a dirty rectangle.

    Args:
        canvas (Canvas): The display driver, framebuffer, or other canvas-like object to draw on.
        s (str): The text to draw.
        x (int): The x position to start drawing the text.
        y (int): The y position to start drawing the text.
        c (int): The color to draw the text in. Default is ``1``.
        scale (int): The scale factor to draw the text at. Default is ``1``.
        inverted (bool): If ``True``, draw the text inverted. Default is ``False``.
        font_data (str | byterray): Path to a font file or memoryview. Default is ``None``.

    Returns:
        Area: The area that was drawn to.
    """
    height = 8
    if (
        not hasattr(Font, "_text8font")
        or (font_data is not None and Font._text8font.font_data != font_data)
        or (height is not None and Font._text8font.height != height)
    ):
        # load the font!
        Font._text8font = Font(font_data, height)

    return Font._text8font.text(canvas, s, x, y, c, scale, inverted)


def text14(canvas, s, x, y, c=1, scale=1, inverted=False, font_data=None):
    """
    Place text on the canvas with a 14 pixel high font.
    Breaks on \n to next line.  Does not break on line going off canvas.

    Args:
        canvas (Canvas): The DisplayDriver, FrameBuffer, or other canvas-like object to draw on.
        s (str): The text to draw.
        x (int): The x position to start drawing the text.
        y (int): The y position to start drawing the text.
        c (int): The color to draw the text in.  Default is 1.
        scale (int): The scale factor to draw the text at.  Default is 1.
        inverted (bool): If True, draw the text inverted.  Default is False.
        font_data (str | byterray): The path to the font .bin file or memoryview.  Default is None.

    Returns:
        Area: The area that was drawn to.
    """
    height = 14
    if (
        not hasattr(Font, "_text14font")
        or (font_data is not None and Font._text14font.font_data != font_data)
        or (height is not None and Font._text14font.height != height)
    ):
        # load the font!
        Font._text14font = Font(font_data, height)

    return Font._text14font.text(canvas, s, x, y, c, scale, inverted)


def text16(canvas, s, x, y, c=1, scale=1, inverted=False, font_data=None):
    """
    Place text on the canvas with a 16 pixel high font.
    Breaks on \n to next line.  Does not break on line going off canvas.

    Args:
        canvas (Canvas): The DisplayDriver, FrameBuffer, or other canvas-like object to draw on.
        s (str): The text to draw.
        x (int): The x position to start drawing the text.
        y (int): The y position to start drawing the text.
        c (int): The color to draw the text in.  Default is 1.
        scale (int): The scale factor to draw the text at.  Default is 1.
        inverted (bool): If True, draw the text inverted.  Default is False.
        font_data (str | byterray): The path to the font .bin file or memoryview.  Default is None.

    Returns:
        Area: The area that was drawn to.
    """
    height = 16
    if (
        not hasattr(Font, "_text16font")
        or (font_data is not None and Font._text16font.font_data != font_data)
        or (height is not None and Font._text16font.height != height)
    ):
        # load the font!
        Font._text16font = Font(font_data, height)

    return Font._text16font.text(canvas, s, x, y, c, scale, inverted)


class Font:
    """
    Load a bundled romfont and reuse it for multiple text draws.

    `Font` is useful when the same UI needs to draw several labels, scores, or
    status strings with the same glyph set. It can load either an embedded font
    or a custom ``.bin`` file from disk or from memory.

    Args:
        font_data (str | byterray): Path to a font file or memoryview. Default is ``None``.
        height (int): The height of the font. Default is ``None``.
        cached (bool): If ``True`` (default), read the font into memory on init.
            If ``False``, read it from disk each time it is needed.
    """

    def __init__(self, font_data=None, height=None, cached=True):
        """Load a romfont from a path, ``memoryview``, or embedded default.

        Binary font layout: 256 glyphs in ASCII order, one byte per pixel row
        per glyph (fonts up to 8 pixels wide). If ``height`` is omitted and
        ``font_data`` is a path like ``font_8x14.bin``, height is taken from the
        name; for a ``memoryview``, height is ``len(data) // 256``.

        Args:
            font_data (str | memoryview): Path to a ``.bin`` font file, or a
                ``memoryview`` of glyph bytes. Default uses the embedded font
                for ``height`` (or 8×8).
            height (int): Glyph height in pixels. Overrides height inferred from
                the file name when both are set.
            cached (bool): If True (default), read the whole file into memory.
                If False, seek the open file for each glyph row.

        Raises:
            FileNotFoundError: If ``font_data`` is a path that cannot be opened.
            RuntimeError: If the file size does not match the expected font size.
        """
        # Optionally specify font_data to override the font data to use (default
        # is _font_8x8.FONT).  font_data may be a memoryview or a string path to a
        # font file.  The font format is a binary file with the following
        # format:
        # - bytes: font data, in ASCII order covering all 256 characters.
        #          Each character should have a byte for each pixel row of
        #          data (i.e. an 8x14 font has 14 bytes per character).
        # If height is not specified, the height of the font will be determined from
        # the memoryview or font file name.  For example a font file named font_8x14.bin
        # will have a height of 14 pixels.  If height is specified it will override
        # the height in the font file name.
        self.font_data = font_data or _font_blob(height if height is not None else _DEFAULT_FONT_HEIGHT)

        # Note that only fonts up to 8 pixels wide are currently supported.
        self._font_width = 8
        if isinstance(self.font_data, memoryview):
            self.font_name = "memoryview"
            self._font_height = len(self.font_data) // 256
            self._cache = self.font_data
            return

        # font_data is a string, so it should be a path to a font file.
        self.font_name = self.font_data.split(sep)[-1].split(".")[0]
        self._font_height = height or int(self.font_name.split("x")[-1])

        # Open the font file.
        try:
            font_path = self.font_data
            self._font = open(font_path, "rb")  # noqa: SIM115  # kept open for random access
            # simple font file validation check based on expected file size
            filesize = os.stat(font_path)[6]
            if filesize != 256 * self.height and filesize != 128 * self.height:
                raise RuntimeError(
                    f"Invalid font file: {self.font_data} is {filesize} bytes, expected {256 * self.height}"
                )
        except OSError as err:
            raise _FileNotFoundError(f"Could not find font file: {self.font_data}") from err
        except OverflowError:
            # os.stat can throw this on boards without long int support
            # just hope the font file is valid and press on
            pass

        if cached:
            self._cache = self._font.read()
            self._font.close()
        else:
            self._cache = None

    @property
    def width(self):
        """Return the width of the font in pixels."""
        return self._font_width

    @property
    def height(self):
        """Return the height of the font in pixels."""
        return self._font_height

    def deinit(self):
        """Close the font file as cleanup."""
        if not self._cache:
            self._font.close()

    def __enter__(self):
        """Initialize/open the font file"""
        self.__init__()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """cleanup on exit"""
        self.deinit()

    def draw_char(self, char, x, y, canvas, color, scale=1, inverted=False):
        """
        Draw one character at position (x,y).

        Args:
            char (str): The character to draw.
            x (int): The x position to draw the character.
            y (int): The y position to draw the character.
            canvas (Canvas): The DisplayDriver, FrameBuffer, or other canvas-like object to draw on.
            color (int): The color to draw the character in.
            scale (int): The scale factor to draw the character at.  Default is 1.
            inverted (bool): If True, draw the character inverted.  Default is False.

        Returns:
            (Area): The area that was drawn to.
        """
        scale = max(scale, 1)
        # Go through each row of the character; coalesce horizontal runs of set bits.
        for char_y in range(self._font_height):
            if not (line := self._read_line(char, char_y)):
                continue
            char_x = 0
            while char_x < self.width:
                if (line >> (self.width - char_x - 1)) & 0x1:
                    run = 1
                    while char_x + run < self.width and (
                        (line >> (self.width - (char_x + run) - 1)) & 0x1
                    ):
                        run += 1
                    if inverted:
                        px = x + (self._font_width - char_x - run) * scale
                        py = y + (self._font_height - char_y - 1) * scale
                    else:
                        px = x + char_x * scale
                        py = y + char_y * scale
                    canvas.fill_rect(px, py, run * scale, scale, color)
                    char_x += run
                else:
                    char_x += 1
        return Area(x, y, self._font_width * scale, self._font_height * scale)

    def text(self, canvas, string, x, y, color, scale=1, inverted=False):
        """
        Draw text to the canvas.

        Args:
            canvas (Canvas): The DisplayDriver, FrameBuffer, or other canvas-like object to draw on.
            string (str): The text to draw.
            x (int): The x position to start drawing the text.
            y (int): The y position to start drawing the text.
            color (int): The color to draw the text in.
            scale (int): The scale factor to draw the text at.  Default is 1.
            inverted (bool): If True, draw the text inverted.  Default is False.

        Returns:
            (Area): The area that was drawn to.
        """
        if inverted:
            string = "".join(reversed(string))

        char_y = y
        largest_x = 0  # the last x position reached on the longest line
        for chunk in string.split("\n"):
            last_x = x  # the last x position reached on the current line
            for i, char in enumerate(chunk):
                char_x = x + (i * self.width * scale)
                if (
                    (char_x < canvas.width if hasattr(canvas, "width") else True)
                    and (char_y < canvas.height if hasattr(canvas, "height") else True)
                    and char_x + (self.width * scale) > 0
                    and char_y + (self.height * scale) > 0
                ):
                    self.draw_char(
                        char,
                        char_x,
                        char_y,
                        canvas,
                        color,
                        scale=scale,
                        inverted=inverted,
                    )
                    last_x = char_x + (self.width * scale)
            largest_x = max([largest_x, last_x])  # update the largest x position
            char_y += self.height * scale
        return Area(x, y, largest_x - x, char_y - y)

    def text_width(self, text, scale=1):
        """
        Return the pixel width of the specified text message.
        Takes into account the scale factor, but not any newlines.

        Args:
            text (str): The text to measure.
            scale (int): The scale factor to measure the text at.  Default is 1.

        Returns:
            int: Width in pixels.
        """
        return len(text) * self._font_width * scale

    def _read_line(self, char, line):
        """Read a line of font data for a character."""
        # ROM fonts cover 256 code points (0..255). Skip anything outside that
        # range instead of indexing off the end of the cache / file.
        code = ord(char)
        if code > 255:
            return None
        offset = (code * self.height) + line
        if self._cache:
            if offset >= len(self._cache):
                return None
            return self._cache[offset]

        self._font.seek(offset)
        try:
            return struct.unpack("B", self._font.read(1))[0]
        except RuntimeError:  # maybe character isnt there? go to next
            return None

    def export(self, filename):
        """
        Export the font data in self._cache to a .py file that can be imported.
        The format is a single bytes object named _FONT.  There are 256 lines, one for each character.
        The last line is `FONT = memoryview(_FONT)`.

        Args:
            filename (str): The path to save the file to.
        """
        if not self._cache:
            raise RuntimeError("Font data not cached, cannot export")
        mv = memoryview(self._cache)
        with open(filename, "w") as f:
            f.write("_FONT =\\\n")
            for i in range(256):
                f.write("b'")
                for j in range(self.height):
                    f.write(f"\\x{mv[(i * self.height) + j]:02x}")
                f.write("'\\\n")
            f.write("\nFONT = memoryview(_FONT)\n")
