# SPDX-FileCopyrightText: 2026 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""
Pure-Python Win32 subset for CPython on Windows.

Used by ``displaydev.windisplay``, ``multimer``'s win32 timer backend, and
``audiodev.win_audio``. Import raises ``ImportError`` unless this is CPython
on ``win32`` with working ``ctypes.windll``.

Exports real Win32 / WASAPI names (plus a few thin COM helpers that wrap
vtable calls). Policy (eventsys mapping, PCM coalesce, timer ``_deliver``)
stays in the consumers.
"""

import sys

if sys.platform != "win32":
    raise ImportError("uwin32 requires Windows")
if getattr(sys.implementation, "name", "") != "cpython":
    raise ImportError("uwin32 requires CPython ctypes")

try:
    import ctypes
    from ctypes import POINTER, byref, c_void_p, sizeof, windll, wintypes
except Exception as exc:
    raise ImportError("uwin32 requires ctypes.windll") from exc

try:
    user32 = windll.user32
    gdi32 = windll.gdi32
    kernel32 = windll.kernel32
    ole32 = windll.ole32
except Exception as exc:
    raise ImportError("uwin32 could not load Win32 DLLs") from exc

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

BOOL = wintypes.BOOL
DWORD = wintypes.DWORD
WORD = wintypes.WORD
LONG = wintypes.LONG
ULONG = wintypes.ULONG
HWND = wintypes.HWND
HDC = wintypes.HDC
HINSTANCE = wintypes.HINSTANCE
HMENU = wintypes.HMENU
HICON = wintypes.HICON
HCURSOR = wintypes.HCURSOR
HBRUSH = wintypes.HBRUSH
HBITMAP = wintypes.HBITMAP
HANDLE = wintypes.HANDLE
LPARAM = wintypes.LPARAM
WPARAM = wintypes.WPARAM
UINT = wintypes.UINT
LPCWSTR = wintypes.LPCWSTR
LPWSTR = wintypes.LPWSTR
ATOM = wintypes.ATOM
BYTE = wintypes.BYTE
WCHAR = wintypes.WCHAR
HRESULT = ctypes.c_long
INT = ctypes.c_int
UINT32 = ctypes.c_uint32
INT64 = ctypes.c_int64
UINT64 = ctypes.c_uint64
LRESULT = ctypes.c_ssize_t
LPVOID = c_void_p
LPCVOID = c_void_p

WNDPROC = ctypes.WINFUNCTYPE(LRESULT, HWND, UINT, WPARAM, LPARAM)
TIMERAPCROUTINE = ctypes.WINFUNCTYPE(None, c_void_p, DWORD, DWORD)


class POINT(ctypes.Structure):
    _fields_ = [("x", LONG), ("y", LONG)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", LONG),
        ("top", LONG),
        ("right", LONG),
        ("bottom", LONG),
    ]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", HWND),
        ("message", UINT),
        ("wParam", WPARAM),
        ("lParam", LPARAM),
        ("time", DWORD),
        ("pt", POINT),
    ]


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", UINT),
        ("style", UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", INT),
        ("cbWndExtra", INT),
        ("hInstance", HINSTANCE),
        ("hIcon", HICON),
        ("hCursor", HCURSOR),
        ("hbrBackground", HBRUSH),
        ("lpszMenuName", LPCWSTR),
        ("lpszClassName", LPCWSTR),
        ("hIconSm", HICON),
    ]


class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [
        ("hdc", HDC),
        ("fErase", BOOL),
        ("rcPaint", RECT),
        ("fRestore", BOOL),
        ("fIncUpdate", BOOL),
        ("rgbReserved", BYTE * 32),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", DWORD),
        ("biWidth", LONG),
        ("biHeight", LONG),
        ("biPlanes", WORD),
        ("biBitCount", WORD),
        ("biCompression", DWORD),
        ("biSizeImage", DWORD),
        ("biXPelsPerMeter", LONG),
        ("biYPelsPerMeter", LONG),
        ("biClrUsed", DWORD),
        ("biClrImportant", DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", DWORD * 3),
    ]


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", DWORD),
        ("Data2", WORD),
        ("Data3", WORD),
        ("Data4", BYTE * 8),
    ]


class WAVEFORMATEX(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("wFormatTag", WORD),
        ("nChannels", WORD),
        ("nSamplesPerSec", DWORD),
        ("nAvgBytesPerSec", DWORD),
        ("nBlockAlign", WORD),
        ("wBitsPerSample", WORD),
        ("cbSize", WORD),
    ]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CS_HREDRAW = 0x0002
CS_VREDRAW = 0x0001
CW_USEDEFAULT = -2147483648
IDC_ARROW = 32512
COLOR_WINDOW = 5
SW_SHOW = 5
SW_HIDE = 0
PM_REMOVE = 0x0001
ERROR_CLASS_ALREADY_EXISTS = 1410

WS_OVERLAPPED = 0x00000000
WS_CAPTION = 0x00C00000
WS_SYSMENU = 0x00080000
WS_MINIMIZEBOX = 0x00020000
WS_VISIBLE = 0x10000000
WS_CLIPCHILDREN = 0x02000000
WS_CLIPSIBLINGS = 0x04000000
WS_DISPLAY = (
    WS_OVERLAPPED
    | WS_CAPTION
    | WS_SYSMENU
    | WS_MINIMIZEBOX
    | WS_VISIBLE
    | WS_CLIPCHILDREN
    | WS_CLIPSIBLINGS
)

WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_QUIT = 0x0012
WM_PAINT = 0x000F
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_MOUSEWHEEL = 0x020A
WM_MOUSEHWHEEL = 0x020E

MK_LBUTTON = 0x0001
MK_RBUTTON = 0x0002
MK_MBUTTON = 0x0010
WHEEL_DELTA = 120

VK_BACK = 0x08
VK_TAB = 0x09
VK_RETURN = 0x0D
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_PRIOR = 0x21
VK_NEXT = 0x22
VK_END = 0x23
VK_HOME = 0x24
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_INSERT = 0x2D
VK_DELETE = 0x2E
VK_LSHIFT = 0xA0
VK_RSHIFT = 0xA1
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_LMENU = 0xA4
VK_RMENU = 0xA5
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_F1 = 0x70

BI_RGB = 0
DIB_RGB_COLORS = 0
SRCCOPY = 0x00CC0020
SPI_GETWORKAREA = 0x0030

INFINITE = 0xFFFFFFFF
CREATE_WAITABLE_TIMER_HIGH_RESOLUTION = 0x00000002
TIMER_ALL_ACCESS = 0x1F0003
WT_EXECUTEDEFAULT = 0x00000000

COINIT_MULTITHREADED = 0x0
COINIT_APARTMENTTHREADED = 0x2
CLSCTX_ALL = 0x17
S_OK = 0
S_FALSE = 1
RPC_E_CHANGED_MODE = 0x80010106

eRender = 0
eCapture = 1
eConsole = 0
AUDCLNT_SHAREMODE_SHARED = 0
AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM = 0x80000000
AUDCLNT_STREAMFLAGS_SRC_DEFAULT_QUALITY = 0x08000000
WAVE_FORMAT_PCM = 1

# SDL-style keycodes used by keys.py
_SDLK_SCANCODE_MASK = 1 << 30
KMOD_LSHIFT = 0x0001
KMOD_RSHIFT = 0x0002
KMOD_LCTRL = 0x0040
KMOD_RCTRL = 0x0080
KMOD_LALT = 0x0100
KMOD_RALT = 0x0200
KMOD_LGUI = 0x0400
KMOD_RGUI = 0x0800


def _guid(d1, d2, d3, d4):
    g = GUID()
    g.Data1 = d1
    g.Data2 = d2
    g.Data3 = d3
    g.Data4[:] = d4
    return g


CLSID_MMDeviceEnumerator = _guid(
    0xBCDE0395, 0xE52F, 0x467C, (0x8E, 0x3D, 0xC4, 0x57, 0x92, 0x91, 0x69, 0x2E)
)
IID_IMMDeviceEnumerator = _guid(
    0xA95664D2, 0x9614, 0x4F35, (0xA7, 0x46, 0xDE, 0x8D, 0xB6, 0x36, 0x17, 0xE6)
)
IID_IAudioClient = _guid(
    0x1CB9AD4C, 0xDBFA, 0x4C32, (0xB1, 0x78, 0xC2, 0xF5, 0x68, 0xA7, 0x03, 0xB2)
)
IID_IAudioRenderClient = _guid(
    0xF294ACFC, 0x3146, 0x4483, (0xA7, 0xBF, 0xAD, 0xDC, 0xA7, 0xC2, 0x60, 0xE2)
)
IID_IAudioCaptureClient = _guid(
    0xC8ADBD64, 0xE71E, 0x48A0, (0xA4, 0xDE, 0x18, 0x5C, 0x39, 0x5C, 0xD3, 0x17)
)


# ---------------------------------------------------------------------------
# Prototypes
# ---------------------------------------------------------------------------

user32.DefWindowProcW.argtypes = [HWND, UINT, WPARAM, LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.RegisterClassExW.argtypes = [POINTER(WNDCLASSEXW)]
user32.RegisterClassExW.restype = ATOM
user32.CreateWindowExW.argtypes = [
    DWORD,
    LPCWSTR,
    LPCWSTR,
    DWORD,
    INT,
    INT,
    INT,
    INT,
    HWND,
    HMENU,
    HINSTANCE,
    LPVOID,
]
user32.CreateWindowExW.restype = HWND
user32.DestroyWindow.argtypes = [HWND]
user32.DestroyWindow.restype = BOOL
user32.ShowWindow.argtypes = [HWND, INT]
user32.ShowWindow.restype = BOOL
user32.UpdateWindow.argtypes = [HWND]
user32.UpdateWindow.restype = BOOL
user32.GetClientRect.argtypes = [HWND, POINTER(RECT)]
user32.GetClientRect.restype = BOOL
user32.GetWindowRect.argtypes = [HWND, POINTER(RECT)]
user32.GetWindowRect.restype = BOOL
user32.AdjustWindowRectEx.argtypes = [POINTER(RECT), DWORD, BOOL, DWORD]
user32.AdjustWindowRectEx.restype = BOOL
user32.SetWindowPos.argtypes = [HWND, HWND, INT, INT, INT, INT, UINT]
user32.SetWindowPos.restype = BOOL
user32.GetDC.argtypes = [HWND]
user32.GetDC.restype = HDC
user32.ReleaseDC.argtypes = [HWND, HDC]
user32.ReleaseDC.restype = INT
user32.BeginPaint.argtypes = [HWND, POINTER(PAINTSTRUCT)]
user32.BeginPaint.restype = HDC
user32.EndPaint.argtypes = [HWND, POINTER(PAINTSTRUCT)]
user32.EndPaint.restype = BOOL
user32.InvalidateRect.argtypes = [HWND, POINTER(RECT), BOOL]
user32.InvalidateRect.restype = BOOL
user32.ValidateRect.argtypes = [HWND, POINTER(RECT)]
user32.ValidateRect.restype = BOOL
user32.PeekMessageW.argtypes = [POINTER(MSG), HWND, UINT, UINT, UINT]
user32.PeekMessageW.restype = BOOL
user32.TranslateMessage.argtypes = [POINTER(MSG)]
user32.TranslateMessage.restype = BOOL
user32.DispatchMessageW.argtypes = [POINTER(MSG)]
user32.DispatchMessageW.restype = LRESULT
user32.PostQuitMessage.argtypes = [INT]
user32.PostQuitMessage.restype = None
user32.PostMessageW.argtypes = [HWND, UINT, WPARAM, LPARAM]
user32.PostMessageW.restype = BOOL
user32.GetMessageW.argtypes = [POINTER(MSG), HWND, UINT, UINT]
user32.GetMessageW.restype = BOOL
user32.LoadCursorW.argtypes = [HINSTANCE, LPCWSTR]
user32.LoadCursorW.restype = HCURSOR
user32.GetSystemMetrics.argtypes = [INT]
user32.GetSystemMetrics.restype = INT
user32.SystemParametersInfoW.argtypes = [UINT, UINT, LPVOID, UINT]
user32.SystemParametersInfoW.restype = BOOL
user32.ScreenToClient.argtypes = [HWND, POINTER(POINT)]
user32.ScreenToClient.restype = BOOL
user32.GetAsyncKeyState.argtypes = [INT]
user32.GetAsyncKeyState.restype = wintypes.SHORT
user32.MapVirtualKeyW.argtypes = [UINT, UINT]
user32.MapVirtualKeyW.restype = UINT
user32.GetKeyNameTextW.argtypes = [LONG, LPWSTR, INT]
user32.GetKeyNameTextW.restype = INT
user32.SetWindowTextW.argtypes = [HWND, LPCWSTR]
user32.SetWindowTextW.restype = BOOL
user32.GetWindowLongPtrW.argtypes = [HWND, INT]
user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.SetWindowLongPtrW.argtypes = [HWND, INT, ctypes.c_ssize_t]
user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t

gdi32.StretchDIBits.argtypes = [
    HDC,
    INT,
    INT,
    INT,
    INT,
    INT,
    INT,
    INT,
    INT,
    LPCVOID,
    POINTER(BITMAPINFO),
    UINT,
    DWORD,
]
gdi32.StretchDIBits.restype = INT
gdi32.SetDIBitsToDevice.argtypes = [
    HDC,
    INT,
    INT,
    DWORD,
    DWORD,
    INT,
    INT,
    UINT,
    UINT,
    LPCVOID,
    POINTER(BITMAPINFO),
    UINT,
]
gdi32.SetDIBitsToDevice.restype = INT

kernel32.GetModuleHandleW.argtypes = [LPCWSTR]
kernel32.GetModuleHandleW.restype = HINSTANCE
kernel32.GetLastError.argtypes = []
kernel32.GetLastError.restype = DWORD
kernel32.CloseHandle.argtypes = [HANDLE]
kernel32.CloseHandle.restype = BOOL
kernel32.SleepEx.argtypes = [DWORD, BOOL]
kernel32.SleepEx.restype = DWORD
kernel32.WaitForSingleObjectEx.argtypes = [HANDLE, DWORD, BOOL]
kernel32.WaitForSingleObjectEx.restype = DWORD
kernel32.CreateWaitableTimerExW.argtypes = [LPVOID, LPCWSTR, DWORD, DWORD]
kernel32.CreateWaitableTimerExW.restype = HANDLE
kernel32.CreateWaitableTimerW.argtypes = [LPVOID, BOOL, LPCWSTR]
kernel32.CreateWaitableTimerW.restype = HANDLE
kernel32.SetWaitableTimer.argtypes = [
    HANDLE,
    POINTER(INT64),
    LONG,
    TIMERAPCROUTINE,
    LPVOID,
    BOOL,
]
kernel32.SetWaitableTimer.restype = BOOL
kernel32.CancelWaitableTimer.argtypes = [HANDLE]
kernel32.CancelWaitableTimer.restype = BOOL

ole32.CoInitializeEx.argtypes = [LPVOID, DWORD]
ole32.CoInitializeEx.restype = HRESULT
ole32.CoUninitialize.argtypes = []
ole32.CoUninitialize.restype = None
ole32.CoCreateInstance.argtypes = [
    POINTER(GUID),
    LPVOID,
    DWORD,
    POINTER(GUID),
    POINTER(c_void_p),
]
ole32.CoCreateInstance.restype = HRESULT
ole32.CoTaskMemFree.argtypes = [LPVOID]
ole32.CoTaskMemFree.restype = None


# ---------------------------------------------------------------------------
# Thin helpers
# ---------------------------------------------------------------------------

def GET_X_LPARAM(lparam):
    return ctypes.c_int16(lparam & 0xFFFF).value


def GET_Y_LPARAM(lparam):
    return ctypes.c_int16((lparam >> 16) & 0xFFFF).value


def GET_WHEEL_DELTA_WPARAM(wparam):
    return ctypes.c_int16((wparam >> 16) & 0xFFFF).value


def MAKEINTRESOURCE(value):
    return ctypes.cast(value, LPCWSTR)


def hwnd_int(hwnd):
    if not hwnd:
        return 0
    return int(hwnd) if not isinstance(hwnd, int) else hwnd


def GetLastError():
    return int(kernel32.GetLastError())


def DefWindowProcW(hwnd, msg, wparam, lparam):
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


def GetModuleHandleW(name=None):
    return kernel32.GetModuleHandleW(name)


def LoadCursorW(instance, cursor):
    if isinstance(cursor, int):
        cursor = MAKEINTRESOURCE(cursor)
    return user32.LoadCursorW(instance, cursor)


def RegisterClassExW(cls):
    atom = user32.RegisterClassExW(byref(cls))
    if not atom and GetLastError() != ERROR_CLASS_ALREADY_EXISTS:
        raise OSError("RegisterClassExW failed (%s)" % GetLastError())
    return atom


def CreateWindowExW(
    ex_style,
    class_name,
    window_name,
    style,
    x,
    y,
    width,
    height,
    parent=None,
    menu=None,
    instance=None,
    param=None,
):
    hwnd = user32.CreateWindowExW(
        ex_style,
        class_name,
        window_name,
        style,
        x,
        y,
        width,
        height,
        parent,
        menu,
        instance or GetModuleHandleW(),
        param,
    )
    if not hwnd:
        raise OSError("CreateWindowExW failed (%s)" % GetLastError())
    return hwnd


def DestroyWindow(hwnd):
    return bool(user32.DestroyWindow(hwnd))


def ShowWindow(hwnd, cmd=SW_SHOW):
    return bool(user32.ShowWindow(hwnd, cmd))


def UpdateWindow(hwnd):
    return bool(user32.UpdateWindow(hwnd))


def GetClientRect(hwnd):
    rect = RECT()
    if not user32.GetClientRect(hwnd, byref(rect)):
        return 0, 0, 0, 0
    return int(rect.left), int(rect.top), int(rect.right), int(rect.bottom)


def AdjustWindowRectEx(width, height, style, ex_style=0):
    rect = RECT(0, 0, int(width), int(height))
    if not user32.AdjustWindowRectEx(byref(rect), style, False, ex_style):
        return width, height
    return int(rect.right - rect.left), int(rect.bottom - rect.top)


SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010


def SetWindowPos(hwnd, x, y, width, height, flags=SWP_NOZORDER | SWP_NOACTIVATE):
    return bool(user32.SetWindowPos(hwnd, None, x, y, width, height, flags))


def GetDC(hwnd):
    return user32.GetDC(hwnd)


def ReleaseDC(hwnd, hdc):
    return user32.ReleaseDC(hwnd, hdc)


def BeginPaint(hwnd):
    ps = PAINTSTRUCT()
    hdc = user32.BeginPaint(hwnd, byref(ps))
    return hdc, ps


def EndPaint(hwnd, ps):
    return bool(user32.EndPaint(hwnd, byref(ps)))


def InvalidateRect(hwnd, erase=False):
    return bool(user32.InvalidateRect(hwnd, None, bool(erase)))


def PeekMessageW(hwnd=None, remove=True):
    msg = MSG()
    got = user32.PeekMessageW(byref(msg), hwnd, 0, 0, PM_REMOVE if remove else 0)
    if not got:
        return None
    return msg


def TranslateMessage(msg):
    return bool(user32.TranslateMessage(byref(msg)))


def DispatchMessageW(msg):
    return user32.DispatchMessageW(byref(msg))


def PostQuitMessage(code=0):
    user32.PostQuitMessage(int(code))


def ScreenToClient(hwnd, x, y):
    pt = POINT(int(x), int(y))
    user32.ScreenToClient(hwnd, byref(pt))
    return int(pt.x), int(pt.y)


def GetAsyncKeyState(vk):
    return int(user32.GetAsyncKeyState(int(vk)))


def SystemParametersInfoW_GETWORKAREA():
    rect = RECT()
    if not user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, byref(rect), 0):
        return 0, 0, 0, 0
    w = int(rect.right - rect.left)
    h = int(rect.bottom - rect.top)
    if w <= 0 or h <= 0:
        return 0, 0, 0, 0
    return int(rect.left), int(rect.top), w, h


def bmi_bgra(width, height):
    """32-bit top-down BI_RGB BITMAPINFO for BGRA pixels."""
    info = BITMAPINFO()
    info.bmiHeader.biSize = sizeof(BITMAPINFOHEADER)
    info.bmiHeader.biWidth = int(width)
    info.bmiHeader.biHeight = -int(height)
    info.bmiHeader.biPlanes = 1
    info.bmiHeader.biBitCount = 32
    info.bmiHeader.biCompression = BI_RGB
    info.bmiHeader.biSizeImage = int(width) * int(height) * 4
    return info


def StretchDIBits(hdc, dest_w, dest_h, src_w, src_h, bits, bmi):
    return int(
        gdi32.StretchDIBits(
            hdc,
            0,
            0,
            int(dest_w),
            int(dest_h),
            0,
            0,
            int(src_w),
            int(src_h),
            bits,
            byref(bmi),
            DIB_RGB_COLORS,
            SRCCOPY,
        )
    )


def GetKeyNameTextW(lparam):
    buf = ctypes.create_unicode_buffer(64)
    n = user32.GetKeyNameTextW(int(lparam), buf, 64)
    return buf.value if n else ""


def modifier_mask():
    """SDL-style KMOD mask from GetAsyncKeyState."""
    mod = 0
    if GetAsyncKeyState(VK_LSHIFT) & 0x8000:
        mod |= KMOD_LSHIFT
    if GetAsyncKeyState(VK_RSHIFT) & 0x8000:
        mod |= KMOD_RSHIFT
    if GetAsyncKeyState(VK_LCONTROL) & 0x8000:
        mod |= KMOD_LCTRL
    if GetAsyncKeyState(VK_RCONTROL) & 0x8000:
        mod |= KMOD_RCTRL
    if GetAsyncKeyState(VK_LMENU) & 0x8000:
        mod |= KMOD_LALT
    if GetAsyncKeyState(VK_RMENU) & 0x8000:
        mod |= KMOD_RALT
    if GetAsyncKeyState(VK_LWIN) & 0x8000:
        mod |= KMOD_LGUI
    if GetAsyncKeyState(VK_RWIN) & 0x8000:
        mod |= KMOD_RGUI
    if not (mod & (KMOD_LSHIFT | KMOD_RSHIFT)) and GetAsyncKeyState(VK_SHIFT) & 0x8000:
        mod |= KMOD_LSHIFT
    if not (mod & (KMOD_LCTRL | KMOD_RCTRL)) and GetAsyncKeyState(VK_CONTROL) & 0x8000:
        mod |= KMOD_LCTRL
    if not (mod & (KMOD_LALT | KMOD_RALT)) and GetAsyncKeyState(VK_MENU) & 0x8000:
        mod |= KMOD_LALT
    return mod


_VK_SPECIAL = {
    VK_BACK: 8,
    VK_TAB: 9,
    VK_RETURN: 13,
    VK_ESCAPE: 27,
    VK_SPACE: 32,
    VK_DELETE: 127,
    VK_LEFT: 1073741904,
    VK_RIGHT: 1073741903,
    VK_UP: 1073741906,
    VK_DOWN: 1073741905,
    VK_HOME: 1073741898,
    VK_END: 1073741901,
    VK_PRIOR: 1073741899,
    VK_NEXT: 1073741902,
    VK_INSERT: 1073741897,
}


def virtual_key_to_sdl(vk):
    """Map a Win32 virtual-key code to an eventsys / SDL keycode."""
    vk = int(vk) & 0xFF
    if 0x41 <= vk <= 0x5A:
        return vk + 32  # 'A'..'Z' → 'a'..'z'
    if 0x30 <= vk <= 0x39:
        return vk  # '0'..'9'
    if VK_F1 <= vk <= VK_F1 + 11:
        return 1073741882 + (vk - VK_F1)
    if vk in _VK_SPECIAL:
        return _VK_SPECIAL[vk]
    return vk


# ---------------------------------------------------------------------------
# Timers
# ---------------------------------------------------------------------------

def CreateWaitableTimerExW(manual_reset=False, high_resolution=False):
    # High-resolution timers reject APC completion routines (ERROR_INVALID_PARAMETER).
    # Auto-reset + APC is the librt analogue we need for multimer.
    flags = 0
    if manual_reset:
        flags |= 0x00000001  # CREATE_WAITABLE_TIMER_MANUAL_RESET
    if high_resolution:
        flags |= CREATE_WAITABLE_TIMER_HIGH_RESOLUTION
    handle = kernel32.CreateWaitableTimerExW(None, None, flags, TIMER_ALL_ACCESS)
    if handle:
        return handle
    handle = kernel32.CreateWaitableTimerW(None, bool(manual_reset), None)
    if not handle:
        raise OSError("CreateWaitableTimer failed (%s)" % GetLastError())
    return handle


def SetWaitableTimer(handle, due_ms, period_ms, apc, arg=None):
    due = INT64(int(-max(1, int(due_ms)) * 10000))
    cb = apc if apc is not None else TIMERAPCROUTINE()
    ok = kernel32.SetWaitableTimer(
        handle,
        byref(due),
        int(period_ms),
        cb,
        arg,
        False,
    )
    if not ok:
        raise OSError("SetWaitableTimer failed (%s)" % GetLastError())
    return ok


def CancelWaitableTimer(handle):
    return bool(kernel32.CancelWaitableTimer(handle))


def CloseHandle(handle):
    return bool(kernel32.CloseHandle(handle))


def SleepEx(ms, alertable=True):
    return int(kernel32.SleepEx(max(0, int(ms)), bool(alertable)))


def WaitForSingleObjectEx(handle, ms, alertable=True):
    return int(kernel32.WaitForSingleObjectEx(handle, int(ms), bool(alertable)))


# ---------------------------------------------------------------------------
# COM / WASAPI
# ---------------------------------------------------------------------------

def _vtbl(punk):
    p = ctypes.cast(c_void_p(punk), POINTER(c_void_p))
    return ctypes.cast(p[0], POINTER(c_void_p))


def _vcall(punk, index, restype, argtypes, *args):
    proto = ctypes.WINFUNCTYPE(restype, c_void_p, *argtypes)
    fn = proto(_vtbl(punk)[index])
    return fn(punk, *args)


def SUCCEEDED(hr):
    return int(hr) >= 0


def _check(hr, what):
    hr = int(hr)
    if hr < 0:
        raise OSError("%s failed (hr=0x%08X)" % (what, hr & 0xFFFFFFFF))
    return hr


def IUnknown_AddRef(punk):
    return int(_vcall(punk, 1, ULONG, ()))


def IUnknown_Release(punk):
    if not punk:
        return 0
    return int(_vcall(punk, 2, ULONG, ()))


def CoInitializeEx(flags=COINIT_APARTMENTTHREADED):
    hr = int(ole32.CoInitializeEx(None, int(flags)))
    if hr in (S_OK, S_FALSE):
        return hr
    if hr & 0xFFFFFFFF == RPC_E_CHANGED_MODE:
        return hr
    _check(hr, "CoInitializeEx")
    return hr


def CoUninitialize():
    ole32.CoUninitialize()


def CoCreateInstance(clsid, iid):
    obj = c_void_p()
    _check(
        ole32.CoCreateInstance(byref(clsid), None, CLSCTX_ALL, byref(iid), byref(obj)),
        "CoCreateInstance",
    )
    return obj.value


def MMDeviceEnumerator_Create():
    return CoCreateInstance(CLSID_MMDeviceEnumerator, IID_IMMDeviceEnumerator)


def IMMDeviceEnumerator_GetDefaultAudioEndpoint(enumerator, data_flow, role=eConsole):
    device = c_void_p()
    _check(
        _vcall(
            enumerator,
            4,
            HRESULT,
            (INT, INT, POINTER(c_void_p)),
            int(data_flow),
            int(role),
            byref(device),
        ),
        "GetDefaultAudioEndpoint",
    )
    return device.value


def IMMDevice_Activate_IAudioClient(device):
    client = c_void_p()
    _check(
        _vcall(
            device,
            3,
            HRESULT,
            (POINTER(GUID), DWORD, LPVOID, POINTER(c_void_p)),
            byref(IID_IAudioClient),
            CLSCTX_ALL,
            None,
            byref(client),
        ),
        "IMMDevice.Activate",
    )
    return client.value


def WAVEFORMATEX_pcm(rate, channels, bits):
    fmt = WAVEFORMATEX()
    fmt.wFormatTag = WAVE_FORMAT_PCM
    fmt.nChannels = int(channels)
    fmt.nSamplesPerSec = int(rate)
    fmt.wBitsPerSample = int(bits)
    fmt.nBlockAlign = int(channels) * (int(bits) // 8)
    fmt.nAvgBytesPerSec = int(rate) * fmt.nBlockAlign
    fmt.cbSize = 0
    return fmt


def IAudioClient_Initialize_shared_pcm(client, fmt, buffer_ms):
    hns = max(10000, int(buffer_ms) * 10000)
    flags = AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM | AUDCLNT_STREAMFLAGS_SRC_DEFAULT_QUALITY
    _check(
        _vcall(
            client,
            3,
            HRESULT,
            (INT, DWORD, INT64, INT64, POINTER(WAVEFORMATEX), LPVOID),
            AUDCLNT_SHAREMODE_SHARED,
            flags,
            hns,
            0,
            byref(fmt),
            None,
        ),
        "IAudioClient.Initialize",
    )


def IAudioClient_GetBufferSize(client):
    frames = UINT32()
    _check(
        _vcall(client, 4, HRESULT, (POINTER(UINT32),), byref(frames)),
        "IAudioClient.GetBufferSize",
    )
    return int(frames.value)


def IAudioClient_GetCurrentPadding(client):
    frames = UINT32()
    _check(
        _vcall(client, 6, HRESULT, (POINTER(UINT32),), byref(frames)),
        "IAudioClient.GetCurrentPadding",
    )
    return int(frames.value)


def IAudioClient_Start(client):
    _check(_vcall(client, 10, HRESULT, ()), "IAudioClient.Start")


def IAudioClient_Stop(client):
    hr = int(_vcall(client, 11, HRESULT, ()))
    if hr < 0:
        raise OSError("IAudioClient.Stop failed (hr=0x%08X)" % (hr & 0xFFFFFFFF))


def IAudioClient_Reset(client):
    _vcall(client, 12, HRESULT, ())


def IAudioClient_GetService(client, iid):
    svc = c_void_p()
    _check(
        _vcall(
            client,
            14,
            HRESULT,
            (POINTER(GUID), POINTER(c_void_p)),
            byref(iid),
            byref(svc),
        ),
        "IAudioClient.GetService",
    )
    return svc.value


def IAudioRenderClient_GetBuffer(render, frames):
    data = c_void_p()
    _check(
        _vcall(
            render,
            3,
            HRESULT,
            (UINT32, POINTER(c_void_p)),
            UINT32(int(frames)),
            byref(data),
        ),
        "IAudioRenderClient.GetBuffer",
    )
    return data.value


def IAudioRenderClient_ReleaseBuffer(render, frames, flags=0):
    _check(
        _vcall(render, 4, HRESULT, (UINT32, DWORD), UINT32(int(frames)), DWORD(int(flags))),
        "IAudioRenderClient.ReleaseBuffer",
    )


def IAudioCaptureClient_GetNextPacketSize(capture):
    frames = UINT32()
    _check(
        _vcall(capture, 5, HRESULT, (POINTER(UINT32),), byref(frames)),
        "IAudioCaptureClient.GetNextPacketSize",
    )
    return int(frames.value)


def IAudioCaptureClient_GetBuffer(capture):
    data = c_void_p()
    frames = UINT32()
    flags = DWORD()
    _check(
        _vcall(
            capture,
            3,
            HRESULT,
            (POINTER(c_void_p), POINTER(UINT32), POINTER(DWORD), LPVOID, LPVOID),
            byref(data),
            byref(frames),
            byref(flags),
            None,
            None,
        ),
        "IAudioCaptureClient.GetBuffer",
    )
    return data.value, int(frames.value), int(flags.value)


def IAudioCaptureClient_ReleaseBuffer(capture, frames):
    _check(
        _vcall(capture, 4, HRESULT, (UINT32,), UINT32(int(frames))),
        "IAudioCaptureClient.ReleaseBuffer",
    )
