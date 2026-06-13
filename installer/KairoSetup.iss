; KairoSetup.iss — Kairo Phantom One-Click Windows Installer
; Compile with Inno Setup 6: iscc installer\KairoSetup.iss

#define MyAppName "Kairo Phantom"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "Kairo Phantom"
#define MyAppURL "https://github.com/KairoPhantom/Kairo-Phantom"
#define MyAppExeName "kairo-phantom.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={localappdata}\Kairo
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
; Default config deployed to %APPDATA%\Kairo
Source: "config-template.toml"; DestDir: "{userappdata}\Kairo"; DestName: "config.toml"; Flags: ignoreversion onlyifdoesntexist
; Skills directory
Source: "..\skills\*"; DestDir: "{app}\skills"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: DirExists('..\skills')
; Python sidecar directory
Source: "..\kairo-sidecar\*"; DestDir: "{app}\kairo-sidecar"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Registry]
; Auto-start on Windows login (optional task)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "KairoPhantom"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
; Silent download and install of Ollama if missing
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""& { if (!(Get-Command ollama -ErrorAction SilentlyContinue)) { Write-Host 'Downloading Ollama...'; Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile '$env:TEMP\OllamaSetup.exe'; Start-Process '$env:TEMP\OllamaSetup.exe' -ArgumentList '/silent' -NoNewWindow -Wait; Start-Sleep -Seconds 5 } }"""; Flags: runhidden
; Warmup background endpoints (pull qwen2.5:3b and qwen2.5:7b)
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""& { Start-Process ollama -ArgumentList 'serve' -NoNewWindow; Start-Sleep -Seconds 3; Start-Process ollama -ArgumentList 'pull qwen2.5:3b' -NoNewWindow -Wait; Start-Process ollama -ArgumentList 'pull qwen2.5:7b' -NoNewWindow -Wait }"""; Flags: runhidden
; Bootstrap Python virtual environment and dependencies
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""& { cd '{app}\kairo-sidecar'; python -m venv .venv; .venv\Scripts\python -m pip install --upgrade pip; .venv\Scripts\pip install -r requirements.txt }"""; Flags: runhidden
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
begin
  if CurStep = ssPostInstall then
  begin
    // Create Kairo data directories in %LOCALAPPDATA%
    ForceDirectories(ExpandConstant('{localappdata}\.kairo-phantom'));
    ForceDirectories(ExpandConstant('{localappdata}\.kairo-phantom\logs'));
    ForceDirectories(ExpandConstant('{localappdata}\.kairo-phantom\plugins'));
    ForceDirectories(ExpandConstant('{localappdata}\.kairo-phantom\compliance'));
    // Create AppData directory
    ForceDirectories(ExpandConstant('{userappdata}\Kairo'));
  end;
end;
