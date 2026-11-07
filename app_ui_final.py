import os
import sys
import shutil
import subprocess
import threading
from tkinter import filedialog, Tk

import webbrowser


def _screen_work_area():
    """Zone utile de l'écran (sans la barre des tâches) sous Windows."""
    try:
        import ctypes
        from ctypes import wintypes
        rect = wintypes.RECT()
        ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
        return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
    except Exception:
        return 0, 0, 1366, 728


# Taille et position de la fenêtre, calculées pour tenir dans l'écran
# (la barre de titre avec Réduire / Agrandir / Fermer reste visible).
from kivy.config import Config
_wa_left, _wa_top, _wa_w, _wa_h = _screen_work_area()
_WIN_W = min(860, _wa_w - 40)
_WIN_H = min(660, _wa_h - 90)
Config.set("graphics", "width", str(_WIN_W))
Config.set("graphics", "height", str(_WIN_H))
Config.set("graphics", "minimum_width", "680")
Config.set("graphics", "minimum_height", str(min(600, _WIN_H)))
Config.set("graphics", "position", "custom")
Config.set("graphics", "left", str(_wa_left + max(0, (_wa_w - _WIN_W) // 2)))
Config.set("graphics", "top", str(_wa_top + max(40, (_wa_h - _WIN_H) // 2)))

# Icône de la fenêtre (barre de titre) : le logo Jessna Convert au lieu de celui de Kivy
_BASE_DIR = getattr(sys, "_MEIPASS", os.path.abspath("."))
_WINDOW_ICON = os.path.join(_BASE_DIR, "logo_jessna_convert_icon.png")
if os.path.exists(_WINDOW_ICON):
    Config.set("kivy", "window_icon", _WINDOW_ICON)

# KivyMD imports (version 1.2.0)
from kivy.lang import Builder
from kivy.clock import mainthread, Clock
from kivy.core.clipboard import Clipboard
from kivy.properties import StringProperty, ListProperty, DictProperty
from kivy.utils import get_color_from_hex
from kivy.metrics import dp
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.list import OneLineListItem  # noqa: F401  (utilisé par le menu)
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton


# --- Palette Jessna Convert (identique au logo) ---
BG = "#0E0E11"
SURFACE = "#17171B"
SURFACE_2 = "#1F1F25"
BORDER = "#2B2B31"
RED = "#E5202E"
SILVER = "#C9CED6"
MUTED = "#8C919B"
WHITE = "#FFFFFF"
GREEN = "#22C55E"
AMBER = "#F59E0B"

APP_VERSION = "1.0"

DEVELOPER = {
    "name": "Chadrack Mbu Jess",
    "role": "Fondateur & CEO de l'écosystème Jessna Tech",
    "title": "Développeur Full Stack",
    "phone": "+243 891 433 419",
    "phone_url": "tel:+243891433419",
    "email": "chadrackmbujess@gmail.com",
    "email_url": "mailto:chadrackmbujess@gmail.com",
    "site": "chadrackmbu.pythonanywhere.com",
    "site_url": "https://chadrackmbu.pythonanywhere.com",
}

STATUS_STYLES = {
    "info": ("information-outline", MUTED),
    "loading": ("progress-download", SILVER),
    "success": ("check-circle", GREEN),
    "warning": ("alert", AMBER),
    "error": ("alert-circle", RED),
}


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
    "Solution simple : écrivez  firefox  dans le champ « Cookies » "
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
    "3. Redémarrez Jessna Convert m3u8.\n\n"
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
KV = """
#:import hex kivy.utils.get_color_from_hex

<FieldLabel@MDLabel>:
    font_style: "Caption"
    theme_text_color: "Custom"
    text_color: hex("#8C919B")
    size_hint_y: None
    height: "18dp"

<JField@MDTextField>:
    mode: "rectangle"
    line_color_normal: hex("#2B2B31")
    line_color_focus: hex("#E5202E")
    hint_text_color_normal: hex("#8C919B")
    hint_text_color_focus: hex("#E5202E")
    text_color_normal: hex("#FFFFFF")
    text_color_focus: hex("#FFFFFF")
    icon_left_color_normal: hex("#8C919B")
    icon_left_color_focus: hex("#E5202E")
    icon_right_color_normal: hex("#8C919B")
    icon_right_color_focus: hex("#E5202E")

<JCard@MDCard>:
    orientation: "vertical"
    size_hint_y: None
    height: self.minimum_height
    padding: "24dp"
    spacing: "12dp"
    radius: [18, 18, 18, 18]
    elevation: 0
    md_bg_color: hex("#17171B")
    line_color: hex("#2B2B31")

<ContactRow@MDCard>:
    icon: ""
    text: ""
    url: ""
    size_hint_y: None
    height: "48dp"
    padding: ["14dp", 0, "14dp", 0]
    spacing: "12dp"
    radius: [12, 12, 12, 12]
    elevation: 0
    md_bg_color: hex("#1F1F25")
    ripple_behavior: True
    on_release: app.open_link(self.url)
    MDIcon:
        icon: root.icon
        theme_text_color: "Custom"
        text_color: hex("#E5202E")
        font_size: "20sp"
        adaptive_size: True
        pos_hint: {"center_y": 0.5}
    MDLabel:
        text: root.text
        theme_text_color: "Custom"
        text_color: hex("#FFFFFF")
    MDIcon:
        icon: "open-in-new"
        theme_text_color: "Custom"
        text_color: hex("#5E626B")
        font_size: "16sp"
        adaptive_size: True
        pos_hint: {"center_y": 0.5}

<EcoChip@MDCard>:
    text: ""
    icon: "circle-medium"
    size_hint_y: None
    height: "44dp"
    padding: ["12dp", 0, "12dp", 0]
    spacing: "8dp"
    radius: [22, 22, 22, 22]
    elevation: 0
    md_bg_color: hex("#1F1F25")
    line_color: hex("#2B2B31")
    MDIcon:
        icon: root.icon
        theme_text_color: "Custom"
        text_color: hex("#E5202E")
        font_size: "18sp"
        adaptive_size: True
        pos_hint: {"center_y": 0.5}
    MDLabel:
        text: root.text
        theme_text_color: "Custom"
        text_color: hex("#C9CED6")
        font_style: "Body2"

MDScreenManager:

    # =====================  PAGE D'ACCUEIL  =====================
    MDScreen:
        name: "home"
        md_bg_color: hex("#0E0E11")

        MDBoxLayout:
            orientation: "vertical"
            padding: ["28dp", "16dp", "28dp", "12dp"]
            spacing: "12dp"

            # ---------- En-tête ----------
            MDBoxLayout:
                size_hint_y: None
                height: "56dp"
                spacing: "14dp"

                Image:
                    source: app.logo_path
                    size_hint: None, None
                    size: "56dp", "56dp"
                    fit_mode: "contain"
                    pos_hint: {"center_y": 0.5}

                MDBoxLayout:
                    orientation: "vertical"
                    spacing: "2dp"
                    padding: [0, "4dp", 0, "4dp"]

                    MDBoxLayout:
                        spacing: "10dp"
                        size_hint_y: None
                        height: "30dp"

                        MDLabel:
                            text: "[b]Jessna[/b] Convert"
                            markup: True
                            font_style: "H5"
                            theme_text_color: "Custom"
                            text_color: hex("#FFFFFF")
                            adaptive_width: True

                        MDCard:
                            size_hint: None, None
                            size: "62dp", "24dp"
                            radius: [6, 6, 6, 6]
                            elevation: 0
                            md_bg_color: hex("#E5202E")
                            pos_hint: {"center_y": 0.5}
                            MDLabel:
                                text: "[b]M3U8[/b]"
                                markup: True
                                halign: "center"
                                font_size: "12sp"
                                theme_text_color: "Custom"
                                text_color: hex("#FFFFFF")

                        Widget:

                    MDLabel:
                        text: "Vos vidéos YouTube en flux m3u8, en un clic."
                        font_style: "Body2"
                        theme_text_color: "Custom"
                        text_color: hex("#8C919B")

                MDIconButton:
                    id: menu_button
                    icon: "dots-vertical"
                    theme_icon_color: "Custom"
                    icon_color: hex("#C9CED6")
                    pos_hint: {"center_y": 0.5}
                    on_release: app.open_main_menu()

            # ---------- Carte : source ----------
            JCard:
                padding: "20dp"
                spacing: "10dp"

                FieldLabel:
                    text: "VIDÉO SOURCE"

                JField:
                    id: video_url
                    hint_text: "Collez le lien YouTube (vidéo ou direct)"
                    icon_left: "youtube"

                MDBoxLayout:
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: "12dp"

                    JField:
                        id: quality
                        hint_text: "Qualité"
                        text: "720p"
                        readonly: True
                        icon_right: "chevron-down"
                        size_hint_x: 0.34
                        on_focus: if self.focus: app.open_quality_menu()

                    JField:
                        id: cookies_path
                        hint_text: "Cookies (fichier .txt ou firefox)"
                        text: "cookies.txt"
                        icon_left: "cookie-outline"
                        size_hint_x: 0.66

                    MDIconButton:
                        icon: "folder-open-outline"
                        theme_icon_color: "Custom"
                        icon_color: hex("#C9CED6")
                        md_bg_color: hex("#1F1F25")
                        pos_hint: {"center_y": 0.5}
                        on_release: app.browse_cookies()

                MDFillRoundFlatIconButton:
                    id: generate_button
                    text: "GÉNÉRER LE LIEN M3U8"
                    icon: "play-circle-outline"
                    size_hint_x: 1
                    font_size: "16sp"
                    padding: ["16dp", "14dp", "16dp", "14dp"]
                    md_bg_color: hex("#E5202E")
                    theme_text_color: "Custom"
                    text_color: hex("#FFFFFF")
                    theme_icon_color: "Custom"
                    icon_color: hex("#FFFFFF")
                    on_release: app.start_link_generation()

            # ---------- Carte : résultat ----------
            JCard:
                padding: "20dp"
                spacing: "10dp"

                FieldLabel:
                    text: "LIEN M3U8"

                MDBoxLayout:
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: "12dp"

                    JField:
                        id: output_link
                        hint_text: "Le lien apparaîtra ici"
                        readonly: True
                        icon_left: "link-variant"

                    MDFillRoundFlatIconButton:
                        text: "COPIER"
                        icon: "content-copy"
                        font_size: "15sp"
                        padding: ["16dp", "12dp", "16dp", "12dp"]
                        pos_hint: {"center_y": 0.5}
                        md_bg_color: hex("#1F1F25")
                        theme_text_color: "Custom"
                        text_color: hex("#FFFFFF")
                        theme_icon_color: "Custom"
                        icon_color: hex("#C9CED6")
                        on_release: app.copy_to_clipboard()

            # ---------- Statut ----------
            MDBoxLayout:
                adaptive_size: True
                spacing: "8dp"
                pos_hint: {"center_x": 0.5}

                MDBoxLayout:
                    id: spinner_box
                    size_hint: None, None
                    size: 0, "22dp"
                    opacity: 0
                    pos_hint: {"center_y": 0.5}
                    MDSpinner:
                        id: spinner
                        size_hint: None, None
                        size: "20dp", "20dp"
                        pos_hint: {"center_y": 0.5}
                        color: hex("#E5202E")
                        line_width: 2
                        active: False

                MDIcon:
                    id: status_icon
                    icon: app.status_icon
                    theme_text_color: "Custom"
                    text_color: app.status_color
                    font_size: "20sp"
                    adaptive_size: True
                    pos_hint: {"center_y": 0.5}

                MDLabel:
                    id: status_label
                    text: "Prêt"
                    theme_text_color: "Custom"
                    text_color: app.status_color
                    adaptive_size: True
                    pos_hint: {"center_y": 0.5}

            Widget:

            MDLabel:
                text: "Jessna Tech  ·  Jessna Convert m3u8"
                halign: "center"
                font_style: "Caption"
                theme_text_color: "Custom"
                text_color: hex("#5E626B")
                size_hint_y: None
                height: "18dp"

    # =====================  PAGE À PROPOS  =====================
    MDScreen:
        name: "about"
        md_bg_color: hex("#0E0E11")

        MDScrollView:
            do_scroll_x: False
            bar_width: "4dp"

            MDBoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                padding: ["28dp", "16dp", "28dp", "20dp"]
                spacing: "16dp"

                # ---------- Barre du haut ----------
                MDBoxLayout:
                    size_hint_y: None
                    height: "48dp"
                    spacing: "8dp"

                    MDIconButton:
                        icon: "arrow-left"
                        theme_icon_color: "Custom"
                        icon_color: hex("#FFFFFF")
                        pos_hint: {"center_y": 0.5}
                        on_release: app.go_home()

                    MDLabel:
                        text: "À propos"
                        font_style: "H6"
                        theme_text_color: "Custom"
                        text_color: hex("#FFFFFF")

                # ---------- L'application ----------
                JCard:
                    spacing: "8dp"

                    Image:
                        source: app.logo_path
                        size_hint: None, None
                        size: "88dp", "88dp"
                        fit_mode: "contain"
                        pos_hint: {"center_x": 0.5}

                    MDLabel:
                        text: "[b]Jessna[/b] Convert m3u8"
                        markup: True
                        font_style: "H5"
                        halign: "center"
                        theme_text_color: "Custom"
                        text_color: hex("#FFFFFF")
                        adaptive_height: True

                    MDLabel:
                        text: "Version " + app.app_version
                        font_style: "Caption"
                        halign: "center"
                        theme_text_color: "Custom"
                        text_color: hex("#8C919B")
                        adaptive_height: True

                    MDLabel:
                        text: "Transformez n'importe quelle vidéo ou direct YouTube en lien m3u8 (HLS) prêt à diffuser sur vos lecteurs, TV et plateformes de streaming."
                        font_style: "Body2"
                        halign: "center"
                        theme_text_color: "Custom"
                        text_color: hex("#C9CED6")
                        adaptive_height: True

                # ---------- Le concepteur ----------
                JCard:
                    FieldLabel:
                        text: "CONÇU ET DÉVELOPPÉ PAR"

                    MDBoxLayout:
                        size_hint_y: None
                        height: "64dp"
                        spacing: "16dp"

                        MDCard:
                            size_hint: None, None
                            size: "60dp", "60dp"
                            radius: [30, 30, 30, 30]
                            elevation: 0
                            md_bg_color: hex("#E5202E")
                            pos_hint: {"center_y": 0.5}
                            MDLabel:
                                text: "[b]CMJ[/b]"
                                markup: True
                                halign: "center"
                                font_size: "18sp"
                                theme_text_color: "Custom"
                                text_color: hex("#FFFFFF")

                        MDBoxLayout:
                            orientation: "vertical"
                            spacing: "2dp"

                            MDLabel:
                                text: "[b]" + app.developer["name"] + "[/b]"
                                markup: True
                                font_style: "H6"
                                theme_text_color: "Custom"
                                text_color: hex("#FFFFFF")

                            MDLabel:
                                text: app.developer["role"]
                                font_style: "Body2"
                                theme_text_color: "Custom"
                                text_color: hex("#FF5A63")

                            MDLabel:
                                text: app.developer["title"]
                                font_style: "Body2"
                                theme_text_color: "Custom"
                                text_color: hex("#8C919B")

                    ContactRow:
                        icon: "phone"
                        text: app.developer["phone"]
                        url: app.developer["phone_url"]

                    ContactRow:
                        icon: "email-outline"
                        text: app.developer["email"]
                        url: app.developer["email_url"]

                    ContactRow:
                        icon: "web"
                        text: app.developer["site"]
                        url: app.developer["site_url"]

                # ---------- L'écosystème ----------
                JCard:
                    FieldLabel:
                        text: "L'ÉCOSYSTÈME JESSNA TECH"

                    MDGridLayout:
                        cols: 2
                        adaptive_height: True
                        spacing: "10dp"

                        EcoChip:
                            icon: "movie-open-play"
                            text: "Jessna CinéHub"

                        EcoChip:
                            icon: "school-outline"
                            text: "Jessna TechLearn"

                        EcoChip:
                            icon: "remote-desktop"
                            text: "Jessna Remote"

                        EcoChip:
                            icon: "swap-horizontal-circle-outline"
                            text: "Jessna Convert m3u8"

                MDLabel:
                    text: "© 2026 Jessna Tech  ·  Tous droits réservés"
                    halign: "center"
                    font_style: "Caption"
                    theme_text_color: "Custom"
                    text_color: hex("#5E626B")
                    size_hint_y: None
                    height: "18dp"
"""


class MainApp(MDApp):
    status_icon = StringProperty("information-outline")
    status_color = ListProperty([0.55, 0.57, 0.61, 1])
    app_version = StringProperty(APP_VERSION)
    developer = DictProperty(DEVELOPER)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.quality_menu = None
        self.main_menu = None
        self.dialog = None
        self.logo_path = resource_path("logo_jessna_convert.png")
        self.icon_path = resource_path("logo_jessna_convert_icon.png")

    def build(self):
        self.title = "Jessna Convert m3u8"
        self.icon = self.icon_path
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Red"
        self.theme_cls.primary_hue = "A700"
        return Builder.load_string(KV)

    def on_start(self):
        # Force le logo dans la barre de titre (au cas où Kivy garde le sien)
        if os.path.exists(self.icon_path):
            Window.set_icon(self.icon_path)
        qualities = ["1080p", "720p", "480p"]
        menu_items = [
            {
                "viewclass": "OneLineListItem",
                "text": quality,
                "height": 52,
                "on_release": lambda x=quality: self.set_quality(x),
            } for quality in qualities
        ]
        self.quality_menu = MDDropdownMenu(
            caller=self.root.ids.quality,
            items=menu_items,
            width_mult=3,
            background_color=get_color_from_hex(SURFACE_2),
        )

    def open_main_menu(self):
        if not self.main_menu:
            self.main_menu = MDDropdownMenu(
                caller=self.root.ids.menu_button,
                items=[
                    {"viewclass": "OneLineListItem", "text": "À propos", "height": 52,
                     "on_release": lambda: self._menu_action("about")},
                    {"viewclass": "OneLineListItem", "text": "Quitter", "height": 52,
                     "on_release": lambda: self._menu_action("quit")},
                ],
                width_mult=3,
                background_color=get_color_from_hex(SURFACE_2),
            )
        self.main_menu.open()

    def _menu_action(self, action):
        self.main_menu.dismiss()
        if action == "about":
            self.root.transition.direction = "left"
            self.root.current = "about"
        elif action == "quit":
            self.stop()

    def go_home(self):
        self.root.transition.direction = "right"
        self.root.current = "home"

    def open_link(self, url):
        if url:
            webbrowser.open(url)

    def open_quality_menu(self):
        self.quality_menu.open()

    def set_quality(self, quality):
        self.root.ids.quality.text = quality
        self.root.ids.quality.focus = False
        self.quality_menu.dismiss()

    def browse_cookies(self):
        if not _tk_root:
            self.show_error_dialog("Erreur", "Impossible d'initialiser l'explorateur de fichiers.")
            return
        file_path = filedialog.askopenfilename(
            title="Sélectionnez le fichier de cookies",
            filetypes=(("Fichiers texte", "*.txt"), ("Tous les fichiers", "*.*"))
        )
        if file_path:
            self.root.ids.cookies_path.text = file_path

    def copy_to_clipboard(self):
        link = self.root.ids.output_link.text
        if link:
            Clipboard.copy(link)
            self.set_status("Lien copié dans le presse-papiers", "success")
        else:
            self.set_status("Rien à copier pour l'instant", "warning")

    def start_link_generation(self):
        thread = threading.Thread(target=self.get_m3u8_link, daemon=True)
        thread.start()

    @mainthread
    def set_status(self, text, kind="info"):
        icon, color = STATUS_STYLES.get(kind, STATUS_STYLES["info"])
        self.status_icon = icon
        self.status_color = get_color_from_hex(color)
        self.root.ids.status_label.text = text

    @mainthread
    def set_output_link(self, text):
        self.root.ids.output_link.text = text

    @mainthread
    def toggle_ui_elements(self, disabled):
        ids = self.root.ids
        ids.generate_button.disabled = disabled
        ids.generate_button.text = "RECHERCHE EN COURS..." if disabled else "GÉNÉRER LE LIEN M3U8"
        ids.video_url.disabled = disabled
        ids.quality.disabled = disabled
        ids.cookies_path.disabled = disabled

        if disabled:
            ids.spinner_box.width = dp(22)
            ids.spinner_box.opacity = 1
            ids.spinner.active = True
            ids.status_icon.opacity = 0
        else:
            ids.spinner.active = False
            ids.spinner_box.width = 0
            ids.spinner_box.opacity = 0
            ids.status_icon.opacity = 1

    @mainthread
    def show_error_dialog(self, title, text):
        if self.dialog:
            self.dialog.dismiss()
        self.dialog = MDDialog(
            title=title,
            text=text,
            md_bg_color=get_color_from_hex(SURFACE),
            buttons=[
                MDFlatButton(
                    text="OK",
                    theme_text_color="Custom",
                    text_color=get_color_from_hex(RED),
                    on_release=lambda *_: self.dialog.dismiss(),
                )
            ],
        )
        self.dialog.open()

    def get_m3u8_link(self):
        video_url = self.root.ids.video_url.text.strip()
        if not video_url:
            self.set_status("Collez d'abord un lien YouTube", "warning")
            self.show_error_dialog("Lien manquant", "Veuillez entrer l'URL d'une vidéo YouTube.")
            return

        self.set_status("Récupération du lien m3u8...", "loading")
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
                self.set_status("Lien m3u8 prêt !", "success")
            else:
                self.set_status("Aucun lien m3u8 trouvé", "error")
                self.show_error_dialog("Aucun lien", "Aucun lien m3u8 trouvé. Vérifiez l'URL et les cookies.")

        except FileNotFoundError:
            self.set_status("yt-dlp introuvable", "error")
            self.show_error_dialog("yt-dlp introuvable", "yt-dlp n'est pas installé ou pas dans le PATH.")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr or ""
            if "not a bot" in stderr or "cookies are no longer valid" in stderr:
                self.set_status("Cookies YouTube à renouveler", "warning")
                self.show_error_dialog("Cookies expirés", COOKIES_HELP)
                return
            if "Requested format is not available" in stderr:
                self.set_status("Pas de flux m3u8 pour cette vidéo", "error")
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
                self.set_status("Moteur JavaScript manquant ou yt-dlp obsolète", "warning")
                self.show_error_dialog("Configuration requise", JS_HELP)
            else:
                self.set_status("Erreur yt-dlp", "error")
                self.show_error_dialog("Erreur yt-dlp", stderr or "Erreur inconnue de yt-dlp.")
        except Exception as e:
            self.set_status("Une erreur inattendue est survenue", "error")
            self.show_error_dialog("Erreur", str(e))
        finally:
            self.toggle_ui_elements(False)


if __name__ == "__main__":
    MainApp().run()
