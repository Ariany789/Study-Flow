#define AppName "StudyFlow"
#ifndef AppVersion
#define AppVersion "1.0.0"
#endif
#define AppPublisher "StudyFlow"

[Setup]
AppId={{2F28F66D-2BC8-4D54-86EA-6D3EB6411F03}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\StudyFlow
DefaultGroupName=StudyFlow
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist-installer
OutputBaseFilename=StudyFlow-Setup
SetupIconFile=studyflow.ico
UninstallDisplayIcon={app}\StudyFlow.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
Uninstallable=yes

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Files]
Source: "..\dist\StudyFlow.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\StudyFlow"; Filename: "{app}\StudyFlow.exe"
Name: "{autodesktop}\StudyFlow"; Filename: "{app}\StudyFlow.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\StudyFlow.exe"; Description: "Abrir o StudyFlow"; Flags: nowait postinstall skipifsilent
