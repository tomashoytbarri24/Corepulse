#ifndef PayloadDir
  #define PayloadDir "..\dist\CorePulse"
#endif
#ifndef ReleaseDir
  #define ReleaseDir "..\release"
#endif
[Setup]
#ifdef TestBuild
AppId={{1AE0EE84-6C40-4B1C-BE9E-0EA8B4D76176}
#else
AppId={{B23A7DBA-5F60-43DD-ADAB-53C0E24454DF}
#endif
AppName=CorePulse
AppVersion=0.177.0
AppVerName=CorePulse · Rebuild 177
AppPublisher=CorePulse
AppPublisherURL=https://corepulse.cl
AppSupportURL=https://corepulse.cl
DefaultDirName={localappdata}\Programs\CorePulse
DefaultGroupName=CorePulse
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.19041
OutputDir={#ReleaseDir}
#ifdef TestBuild
OutputBaseFilename=CorePulse_Setup_177_test
#else
OutputBaseFilename=CorePulse_Setup_177_x64
#endif
SetupIconFile=CorePulse.ico
UninstallDisplayIcon={app}\CorePulse.exe
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern dark
DisableWelcomePage=yes
DisableDirPage=no
DisableReadyPage=yes
DisableFinishedPage=no
CloseApplications=yes
CloseApplicationsFilter=CorePulse.exe,CorePulseWorker.exe,CorePulseOverlayHost.exe
RestartApplications=no
SetupLogging=yes
VersionInfoVersion=0.177.0.0
VersionInfoProductName=CorePulse
VersionInfoDescription=Instalador de CorePulse

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
Source: "assets\*.png"; Flags: dontcopy
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
#ifdef TestBuild
Name: "{app}\CorePulse-test"; Filename: "{app}\CorePulse.exe"; WorkingDir: "{app}"
#else
Name: "{autoprograms}\CorePulse"; Filename: "{app}\CorePulse.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\CorePulse"; Filename: "{app}\CorePulse.exe"; WorkingDir: "{app}"; Tasks: desktopicon
#endif

[Run]
Filename: "{app}\CorePulse.exe"; Description: "Abrir CorePulse"; Flags: nowait postinstall skipifsilent

; Los historiales, informes y ajustes viven fuera de {app}; se conservan al desinstalar.
#include "CorePulseWizard.iss"
