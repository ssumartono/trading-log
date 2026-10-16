"""Local AI configuration encrypted for the current Windows user using DPAPI."""
import ctypes,json,os,tempfile
from ctypes import wintypes
from pathlib import Path

class Blob(ctypes.Structure):
    _fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]

def crypt(value,decrypt=False):
    if os.name!='nt':raise ValueError('Penyimpanan key terenkripsi memerlukan Windows.')
    buffer=ctypes.create_string_buffer(value);source=Blob(len(value),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)));target=Blob()
    library=ctypes.WinDLL('crypt32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    function=library.CryptUnprotectData if decrypt else library.CryptProtectData
    function.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    function.restype=wintypes.BOOL
    kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree.restype=ctypes.c_void_p
    if not function(ctypes.byref(source),None,None,None,None,1,ctypes.byref(target)):
        raise ValueError('Konfigurasi AI tidak dapat '+('dibuka' if decrypt else 'dienkripsi')+' oleh akun Windows ini.')
    try:return ctypes.string_at(target.data,target.size)
    finally:kernel.LocalFree(target.data)

def write(path,config,key):
    encrypted=crypt(json.dumps({'config':config,'key':key},ensure_ascii=False).encode())
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    descriptor,temporary=tempfile.mkstemp(prefix='ai-settings-',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(descriptor,'wb') as stream:
            stream.write(encrypted);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)

def read(path):
    path=Path(path)
    return json.loads(crypt(path.read_bytes(),True).decode()) if path.exists() else None
