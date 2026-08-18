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
; Installs for the current user only, so no admin/UAC elevation is required.
; {autopf}/{autodesktop}/{group} below already resolve to the per-user
; equivalents (LocalAppData\Programs, user Desktop, user Start Menu) when
; PrivilegesRequired is "lowest".
PrivilegesRequired=lowest
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
Name: "oddprint"; Description: "Install the ""oddprint"" virtual PDF printer (needs administrator approval - lets you print from any program straight into {#MyAppName})"; GroupDescription: "Optional components:"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs
Source: "vendor\clawPDF_setup.msi"; DestDir: "{tmp}"; Tasks: oddprint; Flags: deleteafterinstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent unchecked

[Code]
// The main install above is deliberately non-admin (PrivilegesRequired=lowest, see [Setup]).
// clawPDF is a genuine Windows printer driver, and installing a printer driver always
// needs administrator rights regardless of how it's packaged - that's a Windows
// restriction on the driver store, not something this script controls. ShellExec's
// "runas" verb elevates just these two steps (prompting for admin credentials) while
// leaving the rest of the install unelevated. If no admin is available to approve the
// prompt, each step fails gracefully with instructions to finish it later by hand -
// the app itself installs and works fully either way.
procedure InstallOddprintPrinter;
var
  ResultCode: Integer;
  ClawPdfDir, MsiPath, InboxDir, Msg: String;
begin
  MsiPath := ExpandConstant('{tmp}\clawPDF_setup.msi');
  ClawPdfDir := ExpandConstant('{commonpf}\clawPDF');
  InboxDir := ExpandConstant('{localappdata}\{#MyAppName}\PrintInbox');

  if not ShellExec('runas', 'msiexec.exe', '/i "' + MsiPath + '" /quiet /norestart', '',
     SW_SHOWNORMAL, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
  begin
    MsgBox('The oddprint printer needs administrator approval to install, which was not given (or the install failed).' + #13#10#13#10 +
      'You can install it later by running this file as an administrator:' + #13#10 + MsiPath +
      #13#10#13#10 + '(it will be deleted from this temp location after Setup closes - copy it somewhere first if you plan to run it later)',
      mbInformation, MB_OK);
    exit;
  end;

  if not ShellExec('runas', ClawPdfDir + '\SetupHelper.exe', '/Printer=Add /Name=oddprint', '',
     SW_SHOWNORMAL, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
  begin
    MsgBox('clawPDF installed, but creating the "oddprint" printer queue also needs administrator approval.' + #13#10#13#10 +
      'Finish it by running as administrator:' + #13#10 + ClawPdfDir + '\SetupHelper.exe /Printer=Add /Name=oddprint',
      mbInformation, MB_OK);
    exit;
  end;

  Msg := 'The "oddprint" printer is installed. One manual step to finish (about 20 seconds):' + #13#10#13#10 +
    '1. Open Windows Settings -> Bluetooth & devices -> Printers & scanners -> oddprint -> Printing preferences' + #13#10 +
    '2. Go to the Save tab and switch to Automatic' + #13#10 +
    '3. Set the save folder to:' + #13#10 + InboxDir + #13#10 +
    '4. Uncheck "Show progress" and "Open viewer after saving"' + #13#10#13#10 +
    'After that, printing to "oddprint" from any program loads straight into {#MyAppName} automatically - it watches that folder itself.';
  MsgBox(Msg, mbInformation, MB_OK);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and IsTaskSelected('oddprint') then
    InstallOddprintPrinter;
end;
