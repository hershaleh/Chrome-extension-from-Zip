#define MyAppName "ZIP Extension Loader"
#define MyAppVersion "1.0.0"
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
[Files]
Source: "..\publish\ZipExtensionLoader.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\extension\*"; DestDir: "{app}\extension"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\ZIP Extension Loader"; Filename: "{app}\ZipExtensionLoader.exe"
Name: "{autodesktop}\ZIP Extension Loader"; Filename: "{app}\ZipExtensionLoader.exe"
[Run]
Filename: "{app}\ZipExtensionLoader.exe"; Description: "הפעל ZIP Extension Loader"; Flags: postinstall nowait skipifsilent
