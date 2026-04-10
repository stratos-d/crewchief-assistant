# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# Collect all data/binaries for problematic packages
keyboard_datas, keyboard_binaries, keyboard_hiddenimports = collect_all('keyboard')
vgamepad_datas, vgamepad_binaries, vgamepad_hiddenimports = collect_all('vgamepad')
src_hiddenimports = collect_submodules('src')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=keyboard_binaries + vgamepad_binaries,
    datas=[
        ('resources', 'resources'),
    ] + keyboard_datas + vgamepad_datas,
    hiddenimports=src_hiddenimports + [
        'keyboard',
        'keyboard._winkeyboard',
        'keyboard._keyboard_event',
        'vgamepad',
        'vgamepad.win',
        'vgamepad.win.vigem_client',
        'sounddevice',
        'pygame',
        'pygame.mixer',
        'scipy',
        'scipy.io',
        'scipy.io.wavfile',
        'numpy',
        'openai',
        'httpx',
        'dotenv',
        'python-dotenv',
        'tkinter',
    ] + keyboard_hiddenimports + vgamepad_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'notebook', 'jupyter', 'IPython',
        'pandas', 'PIL', 'Pillow',
        'lib2to3', 'test',
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
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
