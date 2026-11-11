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
Source: "..\dist\MicrosoftEdgeWebView2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Code]
function WebView2InstalledAt(RootKey: Integer; SubKey: String): Boolean;
var
  Version: String;
begin
  Result := RegQueryStringValue(RootKey, SubKey, 'pv', Version)
    and (Version <> '') and (Version <> '0.0.0.0');
end;

function WebView2RuntimeInstalled: Boolean;
const
  WebView2ClientKey = 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
begin
  Result := WebView2InstalledAt(HKLM32, WebView2ClientKey)
    or WebView2InstalledAt(HKLM64, WebView2ClientKey)
    or WebView2InstalledAt(HKCU, WebView2ClientKey);
end;

[Icons]
Name: "{autoprograms}\StudyFlow"; Filename: "{app}\StudyFlow.exe"
Name: "{autodesktop}\StudyFlow"; Filename: "{app}\StudyFlow.exe"; Tasks: desktopicon

[Run]
Filename: "{tmp}\MicrosoftEdgeWebView2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Preparando o componente de interface do StudyFlow..."; Flags: waituntilterminated; Check: not WebView2RuntimeInstalled
Filename: "{app}\StudyFlow.exe"; Description: "Abrir o StudyFlow"; Flags: nowait postinstall skipifsilent
