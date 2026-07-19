# -*- mode: python ; coding: utf-8 -*-

# Full res data includes res/themes/3.5inchTheme2-zh-CN.
SMOKE_DATAS = [
    ('res', 'res'),
    ('locales', 'locales'),
    ('config.yaml', '.'),
    ('external', 'external'),
    ('configure.py', '.'),
    ('theme-editor.py', '.'),
]

smoke_a = Analysis(
    ['tools/frozen_smoke.py'],
    pathex=[],
    binaries=[],
    datas=SMOKE_DATAS,
    hiddenimports=['PIL', 'PIL._imagingtk', 'PIL._tkinter_finder'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
smoke_pyz = PYZ(smoke_a.pure)

smoke_exe = EXE(
    smoke_pyz,
    smoke_a.scripts,
    [],
    exclude_binaries=True,
    name='frozen-smoke',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory='.',
)

smoke_coll = COLLECT(
    smoke_exe,
    smoke_a.binaries,
    smoke_a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='frozen-smoke',
)
