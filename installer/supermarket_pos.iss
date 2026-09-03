; ============================================================
; Inno Setup Script for Supermarket POS
; Builds: dist_installer\Supermarket_POS_Setup.exe
; ============================================================

#define MyAppName "Supermarket POS"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Supermarket POS"
#define MyAppExeName "supermarket_pos.exe"

[Setup]
; Unique application GUID for Supermarket POS
AppId={{C7892310-84E1-4BE5-A2B0-04DE6BD34871}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=..\dist_installer
OutputBaseFilename=Supermarket_POS_Setup
Compression=lzma2/ultra64
SolidCompression=yes
; Per-user install: avoids requiring Administrator privileges and prevents permission issues
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Copy all compiled files from PyInstaller's onedir dist directory
Source: "..\supermarket_pos\dist\supermarket_pos\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
