import ctypes
import sys
from ctypes import wintypes

if sys.platform != "win32":
    pass

WM_SETICON = 0x0080
ICON_SMALL = 0
GCLP_HICONSM = -34

_transparent_hicon = None

def hide_titlebar_icon(hwnd: int) -> None:
    if sys.platform != "win32":
        return

    global _transparent_hicon
    user32 = ctypes.windll.user32

    # Set up 64-bit safe signatures
    user32.SendMessageW.restype = ctypes.c_void_p
    user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    
    user32.SetClassLongPtrW.restype = ctypes.c_void_p
    user32.SetClassLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]

    if _transparent_hicon is None:
        and_mask = (ctypes.c_byte * 32)()
        ctypes.memset(and_mask, 0xFF, 32)
        xor_mask = (ctypes.c_byte * 32)()
        ctypes.memset(xor_mask, 0x00, 32)
        _transparent_hicon = user32.CreateIcon(None, 16, 16, 1, 1, and_mask, xor_mask)

    user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, _transparent_hicon)
    user32.SetClassLongPtrW(hwnd, GCLP_HICONSM, _transparent_hicon)
