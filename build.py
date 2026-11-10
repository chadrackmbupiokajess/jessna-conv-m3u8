"""
Build de Jessna Convert m3u8 en UN SEUL .exe autonome.

L'exe contient tout ce qu'il faut pour fonctionner sur un autre PC Windows,
sans rien installer :
  - Python, Kivy, KivyMD (et leurs DLL SDL2 / GLEW / ANGLE)
  - yt-dlp.exe  (version officielle, avec le solveur EJS intégré)
  - deno.exe    (moteur JavaScript exigé par YouTube)
  - le logo, l'icône et l'écran de démarrage

Utilisation :  python build.py
"""
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

# --- Configuration ---
APP_NAME = "Jessna_Conv_m3u8"
MAIN_SCRIPT = "app_ui.py"
ICON_FILE = "logo_jessna_convert.ico"
LOGO_FILE = "logo_jessna_convert.png"
WINDOW_ICON_FILE = "logo_jessna_convert_icon.png"
SPLASH_FILE = "splash_jessna_convert.png"

BIN_DIR = "bin"  # outils externes embarqués dans l'exe
YTDLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
DENO_URL = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip"


def download(url, dest):
    print(f"    téléchargement : {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "JessnaConvert-build"})
    with urllib.request.urlopen(req) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)


def installed_tool(name, min_size_mb):
    """
    Renvoie le chemin d'un outil déjà installé sur ce PC s'il est AUTONOME.
    Un yt-dlp installé avec pip n'est qu'un petit lanceur (~100 Ko) qui a besoin
    de Python : il ne marcherait pas sur un autre PC, on l'ignore.
    """
    path = shutil.which(name)
    if path and os.path.getsize(path) >= min_size_mb * 1024 * 1024:
        return path
    return None


def prepare_tools(force_update):
    """
    Met yt-dlp.exe et deno.exe dans bin/ pour les embarquer dans l'exe.
    1. Réutilise ceux déjà installés sur ce PC (s'ils sont autonomes),
    2. sinon les télécharge (une seule fois).
    --update : force le téléchargement des dernières versions.
    """
    os.makedirs(BIN_DIR, exist_ok=True)

    ytdlp = os.path.join(BIN_DIR, "yt-dlp.exe")
    if force_update or not os.path.exists(ytdlp):
        print("--- yt-dlp.exe ---")
        local = None if force_update else installed_tool("yt-dlp", 5)
        if local:
            print(f"    copie de la version installée : {local}")
            shutil.copy2(local, ytdlp)
        else:
            download(YTDLP_URL, ytdlp)
    else:
        print("--- yt-dlp.exe déjà dans bin/ (python build.py --update pour le mettre à jour) ---")

    deno = os.path.join(BIN_DIR, "deno.exe")
    if force_update or not os.path.exists(deno):
        print("--- deno.exe ---")
        local = None if force_update else installed_tool("deno", 20)
        if local:
            print(f"    copie de la version installée : {local}")
            shutil.copy2(local, deno)
        else:
            zip_path = os.path.join(BIN_DIR, "deno.zip")
            download(DENO_URL, zip_path)
            with zipfile.ZipFile(zip_path) as z:
                z.extract("deno.exe", BIN_DIR)
            os.remove(zip_path)
    else:
        print("--- deno.exe déjà dans bin/ ---")

    # Vérification rapide
    for exe, arg in ((ytdlp, "--version"), (deno, "--version")):
        out = subprocess.run([exe, arg], capture_output=True, text=True).stdout.strip().splitlines()
        print(f"    {os.path.basename(exe)} : {out[0] if out else '???'}")


def check_files():
    missing = [f for f in (MAIN_SCRIPT, ICON_FILE, LOGO_FILE, WINDOW_ICON_FILE, SPLASH_FILE) if not os.path.exists(f)]
    if missing:
        sys.exit(f"Fichiers manquants : {', '.join(missing)}")


SPEC_TEMPLATE = """# -*- mode: python ; coding: utf-8 -*-
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
    ['{main}'],
    pathex=[],
    binaries=[
        ('{bin}/yt-dlp.exe', '.'),   # yt-dlp embarqué
        ('{bin}/deno.exe', '.'),     # moteur JavaScript embarqué
    ],
    datas=[
        ('{logo}', '.'),
        ('{icon}', '.'),
        ('{win_icon}', '.'),
        ('{splash}', '.'),
    ] + kivymd_datas,
    hiddenimports=kivy_deps['hiddenimports'] + kivy_providers + kivymd_modules
                  + ['kivymd.icon_definitions.md_icons'],
    hookspath=hookspath(),
    runtime_hooks=runtime_hooks(),
    excludes=kivy_deps['excludes'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

# Écran de démarrage avec texte : pendant l'extraction, il affiche le fichier en cours,
# puis l'appli y écrit « Veuillez patienter » + la progression (voir app_ui.py).
splash = Splash(
    '{splash}',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=(62, 385),
    text_size=10,
    text_color='#C9CED6',
    text_default='Veuillez patienter... préparation de Jessna Convert m3u8',
    always_on_top=True,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    splash,
    splash.binaries,
    *[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins + angle.dep_bins)],
    name='{name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    icon='{icon}',
)
"""


def main():
    force_update = "--update" in sys.argv
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    check_files()
    prepare_tools(force_update)

    print("--- Nettoyage des anciens builds ---")
    shutil.rmtree("build", ignore_errors=True)
    shutil.rmtree("dist", ignore_errors=True)

    spec = SPEC_TEMPLATE.format(
        main=MAIN_SCRIPT, bin=BIN_DIR, logo=LOGO_FILE, icon=ICON_FILE,
        win_icon=WINDOW_ICON_FILE, splash=SPLASH_FILE, name=APP_NAME,
    )
    with open(f"{APP_NAME}.spec", "w", encoding="utf-8") as f:
        f.write(spec)
    print(f"--- {APP_NAME}.spec généré ---")

    print("--- PyInstaller (quelques minutes)... ---")
    code = subprocess.call([sys.executable, "-m", "PyInstaller", "--noconfirm", f"{APP_NAME}.spec"])
    if code != 0:
        sys.exit("Le build a échoué : lisez les messages ci-dessus.")

    exe_path = os.path.join("dist", f"{APP_NAME}.exe")
    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"--- Terminé ! {exe_path} ({size_mb:.0f} Mo) — prêt à copier sur n'importe quel PC Windows ---")


if __name__ == "__main__":
    main()
