icons from https://github.com/google/material-design-icons/tree/master/png

Runtime set for ``pdwidgets.icon_theme``: importable ``.py`` modules
(``WIDTH`` / ``HEIGHT`` / ``FORMAT`` / ``BITMAP``). No binary ``.pbm``/``.bmp``
are shipped.

Regenerate (from repo root)::

    # binaries into icons/ (optional when re-pulling Material sources)
    .venv/bin/python scripts/assets_generate_pdwidgets_icons.py
    .venv/bin/python scripts/assets_make_color_icons.py
    # convert → .py and remove binaries
    .venv/bin/python scripts/assets_icons_to_py.py --delete-binaries
