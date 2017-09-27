import ctypes
import struct

from ctypes import wintypes
from collections import OrderedDict


def errcheck_bool(result, func, args):
    if not result:
        raise ctypes.WinError(ctypes.get_last_error())
    return args

user32 = ctypes.WinDLL('user32', use_last_error=True)
user32.LoadStringW.errcheck = errcheck_bool
user32.LoadStringW.argtypes = (
    wintypes.HINSTANCE,
    wintypes.UINT,
    wintypes.LPWSTR,
    ctypes.c_int,
)

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
    ctypes.wintypes.HMODULE,
    ctypes.wintypes.LONG,
    ctypes.wintypes.LONG,
    ctypes.wintypes.LONG,
)

LOAD_LIBRARY_AS_IMAGE_RESOURCE = 0x20
LOAD_LIBRARY_AS_DATAFILE_EXCLUSIVE = 0x40
LOAD_WITH_ALTERED_SEARCH_PATH = 0x8

LOCAL_EN_US = 1033


def VS_FIXEDFILEINFO(maj, min, sub, build):
    return struct.pack(
        'lllllllllllll',
        -17890115, 
        0x00010000, 
        (maj << 16) | min,	  # dwFileVersionMS
        (sub << 16) | build,  # dwFileVersionLS
        (maj << 16) | min,	  # dwProductVersionMS
        (sub << 16) | build,
        0x0000003f, 0x00000000, 
        0x00040004, 0x00000001, 0x00000000, 0x00000000,
        0x00000000,
    )

NULL_TERM = '\x00'.encode('utf-16')[3:]


def addlen(s, modificator=3):
    return struct.pack('h', len(s) + modificator) + s


def nullterm(s):
    try:
        s = s.decode('utf-16')
    except:
        pass
    
    s = s.encode('utf-16')[2:]
    # get raw bytes for a NULL terminated unicode string.
    return s + NULL_TERM


def pad32(s, extra=1):
    # extra is normally 2 to deal with wLength
    l = 4 - ((len(s) + extra) & 3)
    if l < 4:
        return s + (NULL_TERM * l)
    return s


def _len(value):
    return int((len(value)) / 2) + 1


def String(key, value):
    key = nullterm(key)
    
    if value:
        print(value, len(value), _len(value))        
        result = struct.pack('hh', len(value) + 1, 1)   # wValueLength, wType
        result = result + key
        result = pad32(result, 2) + nullterm(value)
        mod = 3
    else:
        result = struct.pack('hh', 0, 1)   # wValueLength, wType
        result = result + key
        result = pad32(result, 2)
        mod = 2
    
    return addlen(result, mod)


def Var(key, value):
    key = nullterm(key)    
    print(value, len(value))

    result = struct.pack('hh', _len(value) + 1, 0) # wValueLength, wType
    result = result + key
    result = pad32(result, 2) + value
    return addlen(result, 2)


def StringTable(key, data):
    key = key.encode('utf-16')[2:]

    result = struct.pack('hh', 0, 1)  # wValueLength, wType
    result = result + nullterm(key)
    #result = pad32(result, 2)
    
    for k, v in data.items():
        result = pad32(result, 2)
        result = result + String(k, v)
    
    result = pad32(result, 2)
    print(len(result))
        
    return addlen(result, 2)


def StringFileInfo(data):
    result = struct.pack('hh', 0, 1)  # wValueLength, wType
    result = result + nullterm('StringFileInfo')
    result = pad32(result, 2) + StringTable('040904b0', data)
    #  result = pad32(result) + StringTable('040904E4', data)
    return addlen(result, 2)


def VarFileInfo(data):
    result = struct.pack('hh', 0, 1)  # wValueLength, wType
    result = result + nullterm('VarFileInfo')
    result = pad32(result, 2)
    for k, v in data.items():
        result = result + Var(k, v)
    return addlen(result, 2)


def VS_VERSION_INFO():
    sdata = OrderedDict()
    sdata['Comments'] = ''
    sdata['CompanyName'] = 'Microsoft Corporation'
    sdata['FileDescription'] = 'Freelancer Resources'
    sdata['FileVersion'] = '1, 0, 0, 0'
    sdata['InternalName'] = ''
    sdata['LegalCopyright'] = '© 2003 Microsoft Corporation. All rights reserved'
    sdata['LegalTrademarks'] = ''
    sdata['OriginalFilename'] = ''
    sdata['PrivateBuild'] = ''
    sdata['ProductName'] = 'Freelancer'
    sdata['ProductVersion'] = '1, 0, 0, 0'
    sdata['SpecialBuild'] = ''

    vdata = {
        'Translation' : struct.pack('hh', 0x0409, 0x04B0),
    }
    
    ffi = VS_FIXEDFILEINFO(1, 0, 0, 41)

    result = struct.pack('hh', len(ffi), 0)
    result = result + nullterm('VS_VERSION_INFO')
    result = pad32(result, 2) + ffi
    result = pad32(result, 2) + StringFileInfo(sdata) + VarFileInfo(vdata)
    return addlen(result, 2)

