#define MyAppName "ZIP Extension Loader"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "hershaleh"

[Setup]
AppId={{7B6F9C13-4F26-4B55-A8EA-1B4C3F8D9A21}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\ZIP Extension Loader
DefaultGroupName={#MyAppName}
OutputDir=..\dist
OutputBaseFilename=ZipExtensionLoader-Setup
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#MyAppName}
CloseApplications=force
RestartApplications=no

[Files]
Source: "..\publish\ZipExtensionLoader.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\update.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\extension\*"; DestDir: "{app}\extension"; Flags: ignoreversion recursesubdirs createallsubdirs

[Registry]
Root: HKCU; Subkey: "Software\Classes\ziploader"; ValueType: string; ValueName: ""; ValueData: "URL:ZIP Extension Loader"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\ziploader"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\ziploader\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\ZipExtensionLoader.exe"" ""%1"""; Flags: uninsdeletekey

[Icons]
Name: "{group}\ZIP Extension Loader"; Filename: "{app}\ZipExtensionLoader.exe"
Name: "{autodesktop}\ZIP Extension Loader"; Filename: "{app}\ZipExtensionLoader.exe"

[Run]
Filename: "{app}\ZipExtensionLoader.exe"; Description: "הפעל ZIP Extension Loader"; Flags: postinstall nowait skipifsilent
