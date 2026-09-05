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
AppPublisherURL=https://preeminent-truffle-0ea26e.netlify.app/
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=..\dist_installer
OutputBaseFilename=Supermarket_POS_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
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
; Detached updater helper; this executable is built separately and never touches AppData
Source: "..\supermarket_pos\dist\updater.exe"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Dirs]
; Persistent application configuration and database directories.
; They are outside {app} so upgrades cannot replace customer data.
Name: "{userappdata}\MySupermarketPOS"; Permissions: users-full
Name: "{userappdata}\MySupermarketPOS\Data"; Permissions: users-full

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]

var
  StorePage: TInputQueryWizardPage;

function JsonEscape(Value: String): String;
begin
  Result := Value;
  StringChange(Result, '\', '\\');
  StringChange(Result, '"', '\"');
  StringChange(Result, #13, '\r');
  StringChange(Result, #10, '\n');
end;

procedure InitializeWizard;
begin
  StorePage := CreateInputQueryPage(
    wpWelcome,
    'بيانات السوبرماركت',
    'تخصيص اسم السوبرماركت / الفرع',
    'يرجى إدخال اسم السوبرماركت أو الفرع ليتم تخصيص الواجهة والطباعة به.'
  );
  StorePage.Add('اسم السوبرماركت:', False);
  StorePage.Values[0] := 'سوبرماركت الخير';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigDirectory: String;
  ConfigFile: String;
  StoreName: String;
  JsonContent: String;
begin
  if CurStep = ssPostInstall then
  begin
    StoreName := Trim(StorePage.Values[0]);
    if StoreName = '' then
      StoreName := 'سوبرماركت الخير';

    ConfigDirectory := ExpandConstant('{userappdata}\MySupermarketPOS');
    ConfigFile := ConfigDirectory + '\config.json';
    ForceDirectories(ConfigDirectory);

    JsonContent :=
      '{"store_name": "' + JsonEscape(StoreName) + '"}';
    SaveStringToFile(ConfigFile, UTF8Encode(JsonContent), False);
  end;
end;
