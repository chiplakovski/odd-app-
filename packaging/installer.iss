; Inno Setup script for the ODD Inspection Report Generator.
; Build the app first (from the repo root):
;   pyinstaller packaging\build.spec --noconfirm
; Then compile this script with Inno Setup (https://jrsoftware.org/isinfo.php):
;   iscc packaging\installer.iss
; The finished installer is written to packaging\Output\.

#define MyAppName "ODD Inspection Report Generator"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ODD"
#define MyAppExeName "ODD Inspection Report Generator.exe"

[Setup]
AppId={{268E2707-1979-4D2B-8509-208E42458019}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=ODD_Inspection_Report_Generator_Setup
SetupIconFile=..\app\assets\app_icon.ico
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: checkedonce

[Files]
Source: "..\dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent unchecked
