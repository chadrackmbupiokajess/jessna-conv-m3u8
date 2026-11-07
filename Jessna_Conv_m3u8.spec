# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

# Inclure tous les fichiers nécessaires de KivyMD
kivymd_datas = collect_data_files('kivymd')

a = Analysis(
    ['app_ui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('logo_jessna_convert.png', '.'),   # Logo intégré
        ('logo_jessna_convert.ico', '.'),   # Icône intégrée
        ('logo_jessna_convert_icon.png', '.'),  # Icône de la fenêtre
        ('splash_jessna_convert.png', '.'), # Splash intégré
    ] + kivymd_datas,
    hiddenimports=[
        'kivymd.icon_definitions.md_icons',  # module souvent manquant
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,  # Les fichiers sont inclus directement
    [],
    name='Jessna_Conv_m3u8',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,
    icon='logo_jessna_convert.ico',
    splash='splash_jessna_convert.png'  # <-- Splash screen intégré
)
