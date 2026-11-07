import os
import sys
import shutil
import subprocess
import threading
from tkinter import filedialog, Tk

# KivyMD imports
from kivymd.icon_definitions import md_icons
from kivy.lang import Builder
from kivy.clock import mainthread
from kivy.core.clipboard import Clipboard
from kivymd.app import MDApp
from kivymd.uix.list import OneLineListItem
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.screen import MDScreen


# --- ✅ Fonction universelle pour accéder aux fichiers intégrés ---
def resource_path(relative_path):
    """
    Récupère le chemin absolu vers le fichier,
    que l'application soit lancée depuis un script .py ou un .exe PyInstaller.
    """
    try:
        base_path = sys._MEIPASS  # dossier temporaire PyInstaller
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def app_dir():
    """Dossier où se trouve l'application (.exe installé ou script .py)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def find_tool(name):
    """
    Cherche un exécutable (yt-dlp, deno, node...) :
    1. à côté de l'application (ex. livré avec l'installeur),
    2. dans les ressources intégrées PyInstaller,
    3. dans le PATH Windows.
    """
    exe_name = name + (".exe" if os.name == "nt" else "")
    for folder in (app_dir(), resource_path(".")):
        candidate = os.path.join(folder, exe_name)
        if os.path.isfile(candidate):
            return candidate
    return shutil.which(name)


def build_js_runtime_args():
    """
    Depuis fin 2025, YouTube impose un « challenge » JavaScript (paramètre n / signature).
    yt-dlp doit l'exécuter avec un runtime JS externe (Deno recommandé, Node accepté)
    et le script de résolution EJS. Sans ça : « n challenge solving failed »
    puis « No video formats found ».
    """
    args = []
    for runtime in ("deno", "node", "quickjs", "bun"):
        path = find_tool(runtime)
        if path:
            args.extend(["--js-runtimes", f"{runtime}:{path}"])
    # Télécharge automatiquement le script de résolution EJS à jour depuis GitHub
    # si la version locale manque ou est trop ancienne.
    args.extend(["--remote-components", "ejs:github"])
    return args


def has_js_runtime():
    return any(find_tool(r) for r in ("deno", "node", "quickjs", "bun"))


BROWSERS = ("firefox", "chrome", "edge", "brave", "opera", "vivaldi", "chromium")

COOKIES_HELP = (
    "YouTube demande de prouver que vous n'êtes pas un robot, "
    "et le fichier cookies.txt n'est plus valide (YouTube l'a renouvelé).\n\n"
    "Solution simple : écrivez  firefox  dans le champ « Fichier de cookies » "
    "(Firefox doit être connecté à YouTube et fermé).\n\n"
    "Ou ré-exportez cookies.txt :\n"
    "1. Ouvrez une fenêtre de navigation privée et connectez-vous à YouTube.\n"
    "2. Dans le même onglet, allez sur youtube.com/robots.txt.\n"
    "3. Exportez les cookies (extension « Get cookies.txt LOCALLY »).\n"
    "4. Fermez la fenêtre privée sans revenir sur YouTube."
)


JS_HELP = (
    "YouTube exige maintenant un moteur JavaScript pour déchiffrer les vidéos.\n\n"
    "1. Installez Deno : ouvrez PowerShell et tapez\n"
    "   winget install DenoLand.Deno\n"
    "   (ou installez Node.js depuis nodejs.org)\n"
    "2. Mettez yt-dlp à jour :\n"
    "   yt-dlp -U   (version .exe)\n"
    "   ou pip install -U \"yt-dlp[default]\"   (version pip)\n"
    "3. Redémarrez Jessna Conv m3u8.\n\n"
    "Astuce : vous pouvez aussi placer deno.exe et yt-dlp.exe "
    "dans le dossier de l'application."
)


# Masquer la fenêtre Tkinter
try:
    _tk_root = Tk()
    _tk_root.withdraw()
except Exception:
    _tk_root = None


# --- KV Layout ---
KV = '''
<CustomSpinner@MDSpinner>:
    size_hint: None, None
    size: "46dp", "46dp"
    pos_hint: {'center_x': 0.5}
    active: False

MDScreen:
    MDBoxLayout:
        orientation: 'vertical'
        padding: "30dp"
        spacing: "15dp"

        Image:
            source: app.logo_path
            size_hint_y: None
            height: "100dp"
            allow_stretch: True
            keep_ratio: True
            pos_hint: {'center_x': 0.5}

        MDLabel:
            text: "Jessna Conv m3u8"
            halign: 'center'
            font_style: 'H5'
            size_hint_y: None
            height: self.texture_size[1]
            padding_y: "10dp"

        MDTextField:
            id: video_url
            hint_text: "URL de la vidéo YouTube"
            mode: "rectangle"
            icon_right: "youtube"

        MDBoxLayout:
            size_hint_y: None
            height: "50dp"
            spacing: "20dp"

            MDTextField:
                id: quality
                hint_text: "Qualité"
                mode: "rectangle"
                readonly: True
                text: "720p"
                on_focus: if self.focus: app.open_quality_menu()

            MDTextField:
                id: cookies_path
                hint_text: "Fichier de cookies"
                mode: "rectangle"
                text: "cookies.txt"

            MDRaisedButton:
                text: "Parcourir..."
                on_release: app.browse_cookies()
                size_hint_x: 0.4
                pos_hint: {"center_y": 0.5}
                md_bg_color: 1, 1, 1, 1
                theme_text_color: "Custom"
                text_color: 0, 0, 0, 1

        MDRaisedButton:
            id: generate_button
            text: "Générer le lien"
            on_release: app.start_link_generation()
            pos_hint: {'center_x': 0.5}
            size_hint_x: 1
            font_style: "H6"
            padding: "12dp"
            md_bg_color: 1, 1, 1, 1
            theme_text_color: "Custom"
            text_color: 0, 0, 0, 1

        MDBoxLayout:
            id: spinner_box
            size_hint_y: None
            height: 0
            opacity: 0
            CustomSpinner:
                id: spinner

        MDTextField:
            id: output_link
            hint_text: "Lien m3u8 généré"
            mode: "rectangle"
            readonly: True

        MDRaisedButton:
            text: "Copier le lien"
            on_release: app.copy_to_clipboard()
            pos_hint: {'center_x': 0.5}
            size_hint_x: 1
            md_bg_color: 1, 1, 1, 1
            theme_text_color: "Custom"
            text_color: 0, 0, 0, 1

        MDLabel:
            id: status_label
            text: "Prêt"
            halign: 'center'
            size_hint_y: None
            height: self.texture_size[1]
            theme_text_color: "Secondary"
'''


class MainApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.quality_menu = None
        self.dialog = None
        # --- 🔥 Charger les ressources intégrées ---
        self.logo_path = resource_path("logo_jessna_convert.png")
        self.icon_path = resource_path("logo_jessna_convert.ico")

    def build(self):
        self.title = "Jessna Conv m3u8"
        self.icon = self.icon_path
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Purple"
        return Builder.load_string(KV)

    def on_start(self):
        qualities = ["1080p", "720p", "480p"]
        menu_items = [
            {
                "viewclass": "OneLineListItem",
                "text": quality,
                "height": 56,
                "on_release": lambda x=quality: self.set_quality(x),
            } for quality in qualities
        ]
        self.quality_menu = MDDropdownMenu(
            caller=self.root.ids.quality,
            items=menu_items,
            width_mult=4,
        )

    def open_quality_menu(self):
        self.quality_menu.open()

    def set_quality(self, quality):
        self.root.ids.quality.text = quality
        self.quality_menu.dismiss()

    def browse_cookies(self):
        if not _tk_root:
            self.show_error_dialog("Erreur", "Impossible d'initialiser l'explorateur de fichiers.")
            return
        file_path = filedialog.askopenfilename(
            title="Sélectionnez cookies.txt",
            filetypes=(("Fichiers texte", "*.txt"), ("Tous les fichiers", "*.*"))
        )
        if file_path:
            self.root.ids.cookies_path.text = file_path

    def copy_to_clipboard(self):
        link = self.root.ids.output_link.text
        if link:
            Clipboard.copy(link)
            self.set_status("Lien copié dans le presse-papiers !")
        else:
            self.set_status("Rien à copier.")

    def start_link_generation(self):
        thread = threading.Thread(target=self.get_m3u8_link, daemon=True)
        thread.start()

    @mainthread
    def set_status(self, text):
        self.root.ids.status_label.text = text

    @mainthread
    def set_output_link(self, text):
        self.root.ids.output_link.text = text

    @mainthread
    def toggle_ui_elements(self, disabled):
        self.root.ids.generate_button.disabled = disabled
        self.root.ids.video_url.disabled = disabled
        self.root.ids.quality.disabled = disabled
        self.root.ids.cookies_path.disabled = disabled

        spinner_box = self.root.ids.spinner_box
        spinner = self.root.ids.spinner
        if disabled:
            spinner_box.height = "46dp"
            spinner_box.opacity = 1
            spinner.active = True
        else:
            spinner.active = False
            spinner_box.height = 0
            spinner_box.opacity = 0

    @mainthread
    def show_error_dialog(self, title, text):
        if not self.dialog:
            self.dialog = MDDialog(
                title=f"[color=ff0000]{title}[/color]",
                text=text,
            )
        else:
            self.dialog.title = f"[color=ff0000]{title}[/color]"
            self.dialog.text = text
        self.dialog.open()

    def get_m3u8_link(self):
        video_url = self.root.ids.video_url.text
        if not video_url:
            self.show_error_dialog("Erreur", "Veuillez entrer une URL de vidéo YouTube.")
            return

        self.set_status("🔍 Récupération du lien m3u8...")
        self.set_output_link("")
        self.toggle_ui_elements(True)

        # Uniquement des flux HLS (m3u8) : un seul lien, vidéo + son ensemble.
        # Si la qualité demandée n'existe pas en m3u8, on prend la meilleure m3u8 dispo.
        height = self.root.ids.quality.text.replace("p", "") or "720"
        if not height.isdigit():
            height = "720"
        format_id = f"best[protocol^=m3u8][height<={height}]/best[protocol^=m3u8]"
        cookies_path = self.root.ids.cookies_path.text

        try:
            yt_dlp_path = find_tool("yt-dlp")
            if not yt_dlp_path:
                raise FileNotFoundError("yt-dlp")

            command = [yt_dlp_path, "-f", format_id, "--get-url", "--no-playlist"]
            command.extend(build_js_runtime_args())
            # Les clients "tv" et "ios" de YouTube fournissent les flux HLS (m3u8)
            command.extend(["--extractor-args", "youtube:player_client=default,tv,ios"])
            browser = cookies_path.strip().lower()
            if browser in BROWSERS:
                # Lit les cookies directement dans le navigateur (toujours à jour)
                command.extend(["--cookies-from-browser", browser])
            elif os.path.exists(cookies_path):
                command.extend(["--cookies", cookies_path])
            command.append(video_url)

            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            result = subprocess.run(command, capture_output=True, text=True, check=True, creationflags=creationflags)

            m3u8_url = result.stdout.strip().split('\n')[0]
            if m3u8_url and ("m3u8" in m3u8_url or "hls" in m3u8_url):
                self.set_output_link(m3u8_url)
                self.set_status("✅ Lien trouvé !")
            else:
                self.set_status("❌ Aucun lien trouvé.")
                self.show_error_dialog("Erreur", "Aucun lien m3u8 trouvé. Vérifiez l'URL et le fichier cookies.")


        except FileNotFoundError:
            self.set_status("🚨 Erreur : yt-dlp introuvable.")
            self.show_error_dialog("Erreur", "yt-dlp n'est pas installé ou pas dans le PATH.")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr or ""
            if "not a bot" in stderr or "cookies are no longer valid" in stderr:
                self.set_status("🔒 Cookies YouTube à renouveler.")
                self.show_error_dialog("Cookies expirés", COOKIES_HELP)
                return
            if "Requested format is not available" in stderr:
                self.set_status("❌ Pas de flux m3u8 pour cette vidéo.")
                self.show_error_dialog(
                    "Pas de m3u8",
                    "YouTube ne propose pas de flux m3u8 (HLS) pour cette vidéo.\n\n"
                    "Les directs (lives) en ont toujours ; certaines vidéos normales non.\n"
                    "Essayez sans fichier cookies, ou mettez yt-dlp à jour (yt-dlp -U).",
                )
                return
            js_problem = (
                "challenge solving failed" in stderr
                or "JavaScript runtime" in stderr
                or "No video formats found" in stderr
                or not has_js_runtime()
            )
            if js_problem:
                self.set_status("⚠️ Moteur JavaScript manquant ou yt-dlp obsolète.")
                self.show_error_dialog("Configuration requise", JS_HELP)
            else:
                self.set_status("⚠️ Erreur yt-dlp.")
                self.show_error_dialog("Erreur yt-dlp", stderr or "Erreur inconnue de yt-dlp.")
        except Exception as e:
            self.set_status("🚨 Une erreur inattendue est survenue.")
            self.show_error_dialog("Erreur", str(e))
        finally:
            self.toggle_ui_elements(False)


if __name__ == "__main__":
    MainApp().run()
