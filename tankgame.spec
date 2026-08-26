# -*- mode: python ; coding: utf-8 -*-
# Build with: pyinstaller tankgame.spec
import os

repo_root = os.path.abspath('.')
tankgame_dir = os.path.join(repo_root, 'tankgame')

a = Analysis(
    ['tankgame/__main__.py'],
    pathex=[repo_root, tankgame_dir],
    binaries=[
        ('tankgame/utils/line_intersection.cp312-win_amd64.pyd', 'utils'),
    ],
    datas=[
        ('tankgame/map_files', 'tankgame/map_files'),
        ('tankgame/misc_images', 'tankgame/misc_images'),
        ('tankgame/sound_effects', 'tankgame/sound_effects'),
        ('tankgame/units', 'tankgame/units'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TankGame',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
