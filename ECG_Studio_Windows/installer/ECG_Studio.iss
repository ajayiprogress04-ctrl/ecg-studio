#define AppName "ECG Studio"
#define AppVersion "1.1.0"
#define AppPublisher "Progress Ajayi"
#define AppExe "ECG_Studio.exe"

[Setup]
AppId={{B48F9439-41F0-4D7C-BAA5-7759E03570F3}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoVersion=1.1.0.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=ECG Studio Windows Setup
VersionInfoProductName={#AppName}
DefaultDirName={localappdata}\Programs\ECG Studio
DefaultGroupName=ECG Studio
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist\installer
OutputBaseFilename=ECG_Studio_Setup_{#AppVersion}
SetupIconFile=..\frontend\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=no
RestartApplications=no
AppMutex=ECGStudioDesktopRunning
UninstallDisplayName=ECG Studio

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\ECG_Studio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\ECG Studio"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"
Name: "{autodesktop}\ECG Studio"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Open ECG Studio"; Flags: nowait postinstall skipifsilent
