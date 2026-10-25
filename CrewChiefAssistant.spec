# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

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
)
