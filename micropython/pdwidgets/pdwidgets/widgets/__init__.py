# SPDX-FileCopyrightText: 2024 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Concrete pdwidgets UI widgets (one module per class).

Lean onboard: importing this package does **not** load every widget. Names
resolve via ``__getattr__`` on first access. Prefer::

    from pdwidgets.widgets.button import Button
"""

__all__ = [
    "Accordion",
    "AppBar",
    "Badge",
    "BottomSheet",
    "Button",
    "Card",
    "Chart",
    "CheckBox",
    "Chip",
    "ColorPicker",
    "Column",
    "DatePicker",
    "Dialog",
    "DigitalClock",
    "Divider",
    "Drawer",
    "Dropdown",
    "Form",
    "FormRow",
    "Gauge",
    "Grid",
    "Icon",
    "IconButton",
    "Image",
    "Keyboard",
    "Label",
    "ListView",
    "Menu",
    "Navigator",
    "NumberStepper",
    "Page",
    "PasswordField",
    "PinPad",
    "ProgressBar",
    "RadioButton",
    "RadioGroup",
    "Row",
    "ScrollBar",
    "ScrollView",
    "SegmentedControl",
    "Slider",
    "Spinner",
    "Switch",
    "TabView",
    "TextBox",
    "TextInput",
    "Toast",
    "Toggle",
    "ToggleButton",
]

# name -> (submodule, attribute)
_LAZY = {
    "Accordion": ("accordion", "Accordion"),
    "AppBar": ("app_bar", "AppBar"),
    "Badge": ("badge", "Badge"),
    "BottomSheet": ("bottom_sheet", "BottomSheet"),
    "Button": ("button", "Button"),
    "Card": ("card", "Card"),
    "Chart": ("chart", "Chart"),
    "CheckBox": ("check_box", "CheckBox"),
    "Chip": ("chip", "Chip"),
    "ColorPicker": ("color_picker", "ColorPicker"),
    "Column": ("column", "Column"),
    "DatePicker": ("date_picker", "DatePicker"),
    "Dialog": ("dialog", "Dialog"),
    "DigitalClock": ("digital_clock", "DigitalClock"),
    "Divider": ("divider", "Divider"),
    "Drawer": ("drawer", "Drawer"),
    "Dropdown": ("dropdown", "Dropdown"),
    "Form": ("form", "Form"),
    "FormRow": ("form_row", "FormRow"),
    "Gauge": ("gauge", "Gauge"),
    "Grid": ("grid", "Grid"),
    "Icon": ("icon", "Icon"),
    "IconButton": ("icon_button", "IconButton"),
    "Image": ("image", "Image"),
    "Keyboard": ("keyboard", "Keyboard"),
    "Label": ("label", "Label"),
    "ListView": ("list_view", "ListView"),
    "Menu": ("menu", "Menu"),
    "Navigator": ("navigator", "Navigator"),
    "NumberStepper": ("number_stepper", "NumberStepper"),
    "Page": ("page", "Page"),
    "PasswordField": ("password_field", "PasswordField"),
    "PinPad": ("pin_pad", "PinPad"),
    "ProgressBar": ("progress_bar", "ProgressBar"),
    "RadioButton": ("radio_button", "RadioButton"),
    "RadioGroup": ("radio_group", "RadioGroup"),
    "Row": ("row", "Row"),
    "ScrollBar": ("scroll_bar", "ScrollBar"),
    "ScrollView": ("scroll_view", "ScrollView"),
    "SegmentedControl": ("segmented_control", "SegmentedControl"),
    "Slider": ("slider", "Slider"),
    "Spinner": ("spinner", "Spinner"),
    "Switch": ("switch", "Switch"),
    "TabView": ("tab_view", "TabView"),
    "TextBox": ("text_box", "TextBox"),
    "TextInput": ("text_input", "TextInput"),
    "Toast": ("toast", "Toast"),
    "Toggle": ("toggle", "Toggle"),
    "ToggleButton": ("toggle_button", "ToggleButton"),
}


def __getattr__(name):
    spec = _LAZY.get(name)
    if spec is None:
        raise AttributeError(f"module 'pdwidgets.widgets' has no attribute {name!r}")
    mod_name, attr = spec
    mod = __import__(f"pdwidgets.widgets.{mod_name}", None, None, [attr])
    val = getattr(mod, attr)
    globals()[name] = val
    return val


def __dir__():
    return sorted(set(__all__) | set(globals().keys()))
