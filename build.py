import os
import shutil
from pathlib import Path

# --- Configuration ---
APP_NAME = "Jessna_Conv_m3u8"
MAIN_SCRIPT = "app_ui.py"
ICON_FILE = "logo_jessna_convert.ico"
LOGO_FILE = "logo_jessna_convert.png"
SPLASH_FILE = "splash_jessna_convert.png"  # ton image d’écran de chargement (tu peux la créer)

# --- Nettoyage des anciens builds ---
print("--- Nettoyage des anciens builds ---")
shutil.rmtree("build", ignore_errors=True)
shutil.rmtree("dist", ignore_errors=True)
if os.path.exists(f"{APP_NAME}.spec"):
    os.remove(f"{APP_NAME}.spec")

# --- Création du contenu du fichier SPEC ---
spec_content = f"""# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

# Inclure tous les fichiers nécessaires de KivyMD
kivymd_datas = collect_data_files('kivymd')

a = Analysis(
    ['{MAIN_SCRIPT}'],
    pathex=[],
    binaries=[],
    datas=[
        ('{LOGO_FILE}', '.'),   # Logo intégré
        ('{ICON_FILE}', '.'),   # Icône intégrée
        ('logo_jessna_convert_icon.png', '.'),  # Icône de la fenêtre
        ('{SPLASH_FILE}', '.'), # Splash intégré
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
    name='{APP_NAME}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,
    icon='{ICON_FILE}',
    splash='{SPLASH_FILE}'  # <-- Splash screen intégré
)
"""

# --- Écrire le fichier .spec ---
with open(f"{APP_NAME}.spec", "w", encoding="utf-8") as f:
    f.write(spec_content)
print(f"--- Fichier {APP_NAME}.spec créé avec succès ---")

# --- Lancer PyInstaller ---
print("--- Lancement de PyInstaller... ---")
os.system(f'pyinstaller --noconfirm {APP_NAME}.spec')

print("--- Build terminé ! L'exécutable se trouve dans le dossier 'dist' ---")
