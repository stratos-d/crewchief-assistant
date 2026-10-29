# -*- mode: python ; coding: utf-8 -*-
import os
import re

from PyInstaller.utils.hooks import collect_all, collect_submodules
from PyInstaller.utils.win32 import versioninfo as vi

block_cipher = None


def app_version():
    """(major, minor, patch, 0) from the release tag stamped into src/version.py, else from pyproject.toml."""
    for name, pattern in (('src/version.py', r'^VERSION = "v?(\d+)\.(\d+)\.(\d+)"'),
                          ('pyproject.toml', r'^version = "(\d+)\.(\d+)\.(\d+)"')):
        with open(os.path.join(SPECPATH, name), encoding='utf-8') as f:
            match = re.search(pattern, f.read(), re.M)
        if match:
            return tuple(int(n) for n in match.groups()) + (0,)
    return (0, 0, 0, 0)


# Windows file properties. Exes without them score worse with antivirus machine-learning models.
version = app_version()
version_text = '.'.join(map(str, version[:3]))
version_info = vi.VSVersionInfo(
    ffi=vi.FixedFileInfo(filevers=version, prodvers=version),
    kids=[
        vi.StringFileInfo([vi.StringTable('040904B0', [
            vi.StringStruct('CompanyName', 'stratos-d'),
            vi.StringStruct('FileDescription', 'CrewChief Assistant'),
            vi.StringStruct('FileVersion', version_text),
            vi.StringStruct('InternalName', 'CrewChiefAssistant'),
            vi.StringStruct('LegalCopyright', 'Copyright (c) 2025 Julius'),
            vi.StringStruct('OriginalFilename', 'CrewChiefAssistant.exe'),
            vi.StringStruct('ProductName', 'CrewChief Assistant'),
            vi.StringStruct('ProductVersion', version_text),
        ])]),
        vi.VarFileInfo([vi.VarStruct('Translation', [1033, 1200])]),
    ],
)

# Collect all data/binaries for problematic packages
keyboard_datas, keyboard_binaries, keyboard_hiddenimports = collect_all('keyboard')
pyvjoy_datas, pyvjoy_binaries, pyvjoy_hiddenimports = collect_all('pyvjoy')
ctk_datas, ctk_binaries, ctk_hiddenimports = collect_all('customtkinter')  # themes, fonts and icons
src_hiddenimports = collect_submodules('src')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=keyboard_binaries + pyvjoy_binaries + ctk_binaries,
    datas=[
        ('resources', 'resources'),
    ] + keyboard_datas + pyvjoy_datas + ctk_datas,
    hiddenimports=src_hiddenimports + [
        'keyboard',
        'keyboard._winkeyboard',
        'keyboard._keyboard_event',
        'pyvjoy',
        'sounddevice',
        'openai',
        'httpx',
        'dotenv',
        'tkinter',
        'customtkinter',
        'darkdetect',
    ] + keyboard_hiddenimports + pyvjoy_hiddenimports + ctk_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'notebook', 'jupyter', 'IPython',
        'pandas', 'PIL', 'Pillow',
        'lib2to3', 'test',
        # Audio uses raw byte streams; sounddevice only needs numpy for its array APIs
        'numpy',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CrewChiefAssistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX-packed exes trigger antivirus false positives, especially with a global keyboard hook
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/app.ico',
    version=version_info,
)
