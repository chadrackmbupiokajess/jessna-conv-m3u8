; =====================================================================
;  Installeur de Jessna Convert m3u8 — Jessna Tech
;  À ouvrir avec Inno Setup APRÈS avoir lancé :  python build.py
;  Tous les chemins sont relatifs au dossier de ce script.
; =====================================================================

#define MyAppName "Jessna Convert m3u8"
#define MyAppVersion "1.0"
#define MyAppPublisher "Jessna Tech"
#define MyAppURL "https://www.jessnatechlearn.com/"
#define MyAppExeName "Jessna_Conv_m3u8.exe"

[Setup]
; Même AppId que l'ancien installeur : la nouvelle version remplace l'ancienne proprement.
AppId={{2719CDD4-5CE7-40AC-A9FA-2BD0E11AAFB5}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppCopyright=© 2026 Jessna Tech
DefaultDirName={autopf}\Jessna Tech\{#MyAppName}
DefaultGroupName=Jessna Tech\{#MyAppName}
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
AllowNoIcons=yes
LicenseFile=license.txt
InfoBeforeFile=info_avant.txt
InfoAfterFile=info_apres.txt
SetupIconFile=logo_jessna_convert.ico
OutputDir=installer
OutputBaseFilename=Jessna_Convert_m3u8_Setup_{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; L'exe autonome produit par build.py (contient Python, Kivy, yt-dlp et Deno)
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\{cm:ProgramOnTheWeb,{#MyAppName}}"; Filename: "{#MyAppURL}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
