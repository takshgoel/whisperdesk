; ============================================================
;  installer.iss — Inno Setup script for WhisperDesk
;
;  Prerequisites:
;    1. Run build.bat first to produce dist\WhisperDesk\
;    2. Install Inno Setup 6 from https://jrsoftware.org/isdl.php
;    3. Open this file in Inno Setup and press Ctrl+F9 (or Build > Compile)
;
;  Output: dist\WhisperDesk_Setup_v1.0.0.exe
; ============================================================

#define AppName      "WhisperDesk"
#define AppVersion   "1.0.0"
#define AppPublisher "WhisperDesk"
#define AppURL       "https://github.com/yourusername/whisperdesk"
#define AppExeName   "WhisperDesk.exe"
#define SourceDir    "dist\WhisperDesk"

[Setup]
; ── Identity ─────────────────────────────────────────────────────────────────
AppId={{A7F2C3D4-E5B6-47A8-9C0D-E1F2A3B4C5D6}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases

; ── Install location ─────────────────────────────────────────────────────────
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes

; ── Output ───────────────────────────────────────────────────────────────────
OutputDir=dist
OutputBaseFilename=WhisperDesk_Setup_v{#AppVersion}
; Compress well — the torch binaries squish nicely
Compression=lzma2/ultra64
SolidCompression=yes
LZMANumBlockThreads=4

; ── Windows requirements ─────────────────────────────────────────────────────
MinVersion=10.0
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible

; ── Appearance ───────────────────────────────────────────────────────────────
WizardStyle=modern
SetupIconFile=
; UninstallDisplayIcon={app}\{#AppExeName}
; WizardImageFile=assets\installer_banner.bmp   ; 164x314 px (optional)
; WizardSmallImageFile=assets\installer_icon.bmp ; 55x58 px  (optional)

; ── Privileges ───────────────────────────────────────────────────────────────
; "lowest" lets users install without admin rights
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Desktop shortcut — offered but not ticked by default
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; \
  GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; ── Main application folder (everything PyInstaller produced) ─────────────────
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; ── Readme ───────────────────────────────────────────────────────────────────
Source: "README.md";   DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE";  DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion

[Icons]
; Start Menu shortcut
Name: "{group}\{#AppName}";          Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
; Desktop shortcut (only if task selected)
Name: "{autodesktop}\{#AppName}";    Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Offer to launch the app at the end of installation
Filename: "{app}\{#AppExeName}"; \
  Description: "{cm:LaunchProgram,{#StringChange(AppName,'&','&&')}}"; \
  Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove the temp folder the app creates at runtime
Type: filesandordirs; Name: "{app}\temp"
; Remove the log file
Type: files;          Name: "{app}\whisperdesk.log"

[Code]
// Show a warning if less than 3 GB free disk space
// (Whisper base model downloads ~140 MB on first run)
function InitializeSetup(): Boolean;
var
  FreeBytes: Int64;
begin
  Result := True;
  if GetSpaceOnDisk(ExpandConstant('{autopf}'), True, FreeBytes, FreeBytes) then
  begin
    if FreeBytes < 3221225472 then   // 3 GB
    begin
      if MsgBox(
        'WhisperDesk requires at least 3 GB of free disk space.' + #13#10 +
        '(The app is ~1.5 GB; the Whisper model downloads ~140 MB on first use.)' + #13#10#13#10 +
        'You currently have less than 3 GB free. Continue anyway?',
        mbConfirmation, MB_YESNO
      ) = IDNO then
        Result := False;
    end;
  end;
end;
