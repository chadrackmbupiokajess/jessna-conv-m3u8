# -*- mode: python ; coding: utf-8 -*-
# Fichier généré par build.py — ne pas modifier à la main.
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
from kivy_deps import sdl2, glew, angle
from kivy.tools.packaging.pyinstaller_hooks import get_deps_all, hookspath, runtime_hooks

kivymd_datas = collect_data_files('kivymd')
kivymd_modules = collect_submodules('kivymd')

# Kivy charge ses « providers » (images, presse-papiers, texte, fenêtre...) par leur nom
# pendant l'exécution : PyInstaller ne les voit pas tout seul, on les ajoute nous-mêmes.
kivy_deps = get_deps_all()
kivy_providers = [
    'kivy.core.window.window_sdl2',
    'kivy.core.text.text_sdl2', 'kivy.core.text.text_pil',
    'kivy.core.image.img_tex', 'kivy.core.image.img_dds',
    'kivy.core.image.img_sdl2', 'kivy.core.image.img_pil',
    'kivy.core.clipboard.clipboard_winctypes', 'kivy.core.clipboard.clipboard_sdl2',
    'kivy.core.clipboard.clipboard_dummy',
    'kivy.core.audio.audio_sdl2',
    'kivy.core.spelling.spelling_enchant',
    'win32timezone',
]

a = Analysis(
    ['app_ui.py'],
    pathex=[],
    binaries=[
        ('bin/yt-dlp.exe', '.'),   # yt-dlp embarqué
        ('bin/deno.exe', '.'),     # moteur JavaScript embarqué
    ],
    datas=[
        ('logo_jessna_convert.png', '.'),
        ('logo_jessna_convert.ico', '.'),
        ('logo_jessna_convert_icon.png', '.'),
        ('splash_jessna_convert.png', '.'),
    ] + kivymd_datas,
    hiddenimports=kivy_deps['hiddenimports'] + kivy_providers + kivymd_modules
                  + ['kivymd.icon_definitions.md_icons'],
    hookspath=hookspath(),
    runtime_hooks=runtime_hooks(),
    excludes=kivy_deps['excludes'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

splash = Splash(
    'splash_jessna_convert.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    splash,
    splash.binaries,
    *[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins + angle.dep_bins)],
    name='Jessna_Conv_m3u8',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    icon='logo_jessna_convert.ico',
)
