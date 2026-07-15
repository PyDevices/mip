# SPDX-FileCopyrightText: 2024 Brad Barnett
# SPDX-FileCopyrightText: 2020-2023 Russ Hughes
# SPDX-FileCopyrightText: 2019 Ivan Belokobylskiy
#
# SPDX-License-Identifier: MIT
"""
Proportional bitmap-font renderer for Label (and widgets built on it).

Private module: apps normally pass a font module to ``Label(..., font=...)``;
they do not import this file. Keep it underscored so it stays off the public
``pdwidgets`` API.

Font modules
------------
Generate glyph modules with Russ Hughes's
`write_font_converter.py <https://github.com/russhughes/st7789py_mpy/blob/master/utils/write_font_converter.py>`_
(expects ``MAP``, ``HEIGHT``, ``MAX_WIDTH``, ``WIDTHS``, ``OFFSETS``,
``OFFSET_WIDTH``, ``BITMAPS``). Example output lives in pydisplay's
``src/examples/chango/`` (``chango_16.py``, etc.).

See also pydisplay docs:

- `Drawing and fonts <https://pydevices.github.io/pydisplay/concepts/drawing-and-fonts/>`_
- `TFT GUI / font tools <https://pydevices.github.io/pydisplay/guis/tft-gui/>`_

History
-------
Vendored from pydisplay ``add_ons/tft_write.py`` (same Russhughes
``st7789_mpy`` / ``st7789py_mpy`` lineage) so pdwidgets does not depend on that
add-on at import time.
"""

from graphics import Area
from micropython import const

WHITE = const(0xFFFF)
BLACK = const(0x0000)


def write(canvas, font, string, x, y, fg=WHITE, bg=BLACK):
    """
    Write a string using a converted true-type font on the display starting
    at the specified column and row

    Args:
        font (font): The module containing the converted true-type font
        string (str): The string to write
        x (int): column to start writing
        y (int): row to start writing
        fg (int): foreground color, optional, defaults to WHITE
        bg (int): background color, optional, defaults to BLACK
    """
    buffer_len = font.HEIGHT * font.MAX_WIDTH * 2
    buffer = bytearray(buffer_len)
    fg_hi = fg & 0xFF
    fg_lo = fg >> 8

    bg_hi = bg & 0xFF
    bg_lo = bg >> 8

    x_pos = x
    for character in string:
        try:
            char_index = font.MAP.index(character)
            offset = char_index * font.OFFSET_WIDTH
            bs_bit = font.OFFSETS[offset]
            if font.OFFSET_WIDTH > 1:
                bs_bit = (bs_bit << 8) + font.OFFSETS[offset + 1]

            if font.OFFSET_WIDTH > 2:
                bs_bit = (bs_bit << 8) + font.OFFSETS[offset + 2]

            char_width = font.WIDTHS[char_index]
            buffer_needed = char_width * font.HEIGHT * 2

            for i in range(0, buffer_needed, 2):
                if font.BITMAPS[bs_bit // 8] & 1 << (7 - (bs_bit % 8)) > 0:
                    buffer[i] = fg_hi
                    buffer[i + 1] = fg_lo
                else:
                    buffer[i] = bg_hi
                    buffer[i + 1] = bg_lo

                bs_bit += 1

            to_col = x_pos + char_width - 1
            to_row = y + font.HEIGHT - 1
            if canvas.width > to_col and canvas.height > to_row:
                canvas.blit_rect(buffer[:buffer_needed], x_pos, y, char_width, font.HEIGHT)

            x_pos += char_width

        except ValueError:
            pass
    return Area(x, y, x_pos - x, font.HEIGHT)


def write_width(font, string):
    """
    Returns the width in pixels of the string if it was written with the
    specified font

    Args:
        font (font): The module containing the converted true-type font
        string (string): The string to measure

    Returns:
        (int): The width of the string in pixels

    """
    width = 0
    for character in string:
        try:
            char_index = font.MAP.index(character)
            width += font.WIDTHS[char_index]
        except ValueError:
            pass

    return width
