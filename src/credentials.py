"""OpenAI API key storage in Windows Credential Manager.

Windows encrypts saved credentials with the user's login, so the key can't be read from config.json, backups
or another account. It is listed under Credential Manager > Windows Credentials as "CrewChief Assistant".
"""
import ctypes
import os
from ctypes import wintypes

TARGET = "CrewChief Assistant"
available = os.name == "nt"

_CRED_TYPE_GENERIC = 1
_CRED_PERSIST_LOCAL_MACHINE = 2  # this PC only, never roamed to other machines
_ERROR_NOT_FOUND = 1168


class _Credential(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


if available:
    _advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    _advapi32.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                    ctypes.POINTER(ctypes.POINTER(_Credential))]
    _advapi32.CredReadW.restype = wintypes.BOOL
    _advapi32.CredWriteW.argtypes = [ctypes.POINTER(_Credential), wintypes.DWORD]
    _advapi32.CredWriteW.restype = wintypes.BOOL
    _advapi32.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    _advapi32.CredDeleteW.restype = wintypes.BOOL
    _advapi32.CredFree.argtypes = [ctypes.c_void_p]
    _advapi32.CredFree.restype = None


def read_api_key():
    """Return the stored key, or "" if there is none or it can't be read."""
    if not available:
        return ""
    credential = ctypes.POINTER(_Credential)()
    if not _advapi32.CredReadW(TARGET, _CRED_TYPE_GENERIC, 0, ctypes.byref(credential)):
        return ""
    try:
        blob = ctypes.string_at(credential.contents.CredentialBlob, credential.contents.CredentialBlobSize)
        return blob.decode("utf-8")
    finally:
        _advapi32.CredFree(credential)


def write_api_key(key):
    """Store the key, replacing any existing one. Raises OSError if Windows refuses."""
    blob = key.encode("utf-8")
    buffer = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
    credential = _Credential()
    credential.Type = _CRED_TYPE_GENERIC
    credential.TargetName = TARGET
    credential.UserName = "OpenAI API key"
    credential.CredentialBlobSize = len(blob)
    credential.CredentialBlob = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))
    credential.Persist = _CRED_PERSIST_LOCAL_MACHINE
    if not _advapi32.CredWriteW(ctypes.byref(credential), 0):
        raise ctypes.WinError(ctypes.get_last_error())


def delete_api_key():
    """Remove the stored key, if there is one."""
    if not available:
        return
    if not _advapi32.CredDeleteW(TARGET, _CRED_TYPE_GENERIC, 0):
        error = ctypes.get_last_error()
        if error != _ERROR_NOT_FOUND:
            raise ctypes.WinError(error)
