import ctypes
from ctypes import wintypes

def errcheck_bool(result, func, args):
	if not result:
		raise ctypes.WinError(ctypes.get_last_error())
	return args
	
user32 = ctypes.WinDLL('user32', use_last_error=True)
user32.LoadStringW.errcheck = errcheck_bool
user32.LoadStringW.argtypes = (wintypes.HINSTANCE,
							   wintypes.UINT,
							   wintypes.LPWSTR,
							   ctypes.c_int)
							   
PWCHAR = ctypes.POINTER(wintypes.WCHAR)

LoadLibrary = ctypes.windll.kernel32.LoadLibraryExW
FreeLibrary = ctypes.windll.kernel32.FreeLibrary
FindResource = ctypes.windll.kernel32.FindResourceA

LoadResource = ctypes.windll.kernel32.LoadResource
FreeResource = ctypes.windll.kernel32.FreeResource
SizeofResource = ctypes.windll.kernel32.SizeofResource
LockResource = ctypes.windll.kernel32.LockResource

GetLastError = ctypes.windll.kernel32.GetLastError
BeginUpdateResource = ctypes.windll.kernel32.BeginUpdateResourceA
EndUpdateResource = ctypes.windll.kernel32.EndUpdateResourceA
UpdateResource = ctypes.windll.kernel32.UpdateResourceA
EnumResourceNames = ctypes.windll.kernel32.EnumResourceNamesA
EnumResourceNameCallback = ctypes.WINFUNCTYPE(
	ctypes.wintypes.BOOL,
	ctypes.wintypes.HMODULE, ctypes.wintypes.LONG,
	ctypes.wintypes.LONG, ctypes.wintypes.LONG,
)

LOAD_LIBRARY_AS_IMAGE_RESOURCE = 0x20
LOAD_LIBRARY_AS_DATAFILE_EXCLUSIVE = 0x40
LOAD_WITH_ALTERED_SEARCH_PATH = 0x8

LOCAL_EN_US = 1033
