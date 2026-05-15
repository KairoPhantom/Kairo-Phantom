; KairoSetup.iss — Kairo Phantom One-Click Windows Installer (P0-B1)
; Compile with Inno Setup 6: iscc installer\KairoSetup.iss
; Prerequisites: Build phantom-core first: cd phantom-core && cargo build --release

#define MyAppName "Kairo Phantom"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Kairo Phantom"
#define MyAppURL "https://github.com/Kartik24Hulmukh/Kairo-Phantom"
#define MyAppExeName "kairo-phantom.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\KairoPhantom
DefaultGroupName={#MyAppName}
OutputDir=Output
OutputBaseFilename=KairoSetup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
MinVersion=10.0.17763
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startup"; Description: "Launch Kairo Phantom automatically when Windows starts"; GroupDescription: "Startup:"

[Files]
; Main binary (built from cargo build --release)
Source: "..\phantom-core\target\release\kairo-phantom.exe"; DestDir: "{app}"; Flags: ignoreversion
; Default config
Source: "config-template.toml"; DestDir: "{app}"; DestName: "config.toml"; Flags: ignoreversion onlyifdoesntexist
; Skills directory
Source: "..\skills\*"; DestDir: "{app}\skills"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: DirExists('..\skills')

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Registry]
; Auto-start on Windows login (optional task)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "KairoPhantom"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
; First-run: launch with onboarding flag
Filename: "{app}\{#MyAppExeName}"; Parameters: "--first-run"; Description: "Launch {#MyAppName} now"; Flags: nowait postinstall skipifsilent

[Code]
function OllamaInstalled: Boolean;
begin
  Result := FileExists(ExpandConstant('{localappdata}\Programs\Ollama\ollama.exe')) or
            FileExists('C:\Program Files\Ollama\ollama.exe') or
            FileExists(ExpandConstant('{localappdata}\Ollama\ollama.exe'));
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // Create Kairo data directories
    ForceDirectories(ExpandConstant('{localappdata}\.kairo-phantom'));
    ForceDirectories(ExpandConstant('{localappdata}\.kairo-phantom\logs'));
    ForceDirectories(ExpandConstant('{localappdata}\.kairo-phantom\plugins'));
    ForceDirectories(ExpandConstant('{localappdata}\.kairo-phantom\compliance'));

    if not OllamaInstalled then
    begin
      if MsgBox(
        'Ollama (local AI engine) was not found on your system.' + #13#10 +
        #13#10 +
        'Kairo Phantom runs 100% offline using Ollama.' + #13#10 +
        'Would you like to open the Ollama download page now?',
        mbConfirmation, MB_YESNO
      ) = IDYES then
      begin
        ShellExec('open', 'https://ollama.com/download/windows', '', '', SW_SHOW, ewNoWait, ResultCode);
      end;
    end;
  end;
end;
