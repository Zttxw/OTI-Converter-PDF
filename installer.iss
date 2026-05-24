[Setup]
AppName=OTI Converter
AppVersion=1.0.0
AppPublisher=Zttxw
DefaultDirName={autopf}\OTI Converter
DefaultGroupName=OTI Converter
OutputBaseFilename=OTI_Converter_Setup_v1.0.0
SetupIconFile=assets\logo.ico
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
MinVersion=10.0
PrivilegesRequired=admin

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\OTI-Converter\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\OTI Converter"; Filename: "{app}\OTI-Converter.exe"; IconFilename: "{app}\_internal\assets\logo.ico"; Tasks: desktopicon
Name: "{group}\OTI Converter"; Filename: "{app}\OTI-Converter.exe"; IconFilename: "{app}\_internal\assets\logo.ico"
Name: "{group}\Desinstalar OTI Converter"; Filename: "{uninstallexe}"

[Registry]
Root: HKLM; Subkey: "Software\OTI-Converter"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey

[Code]
var
  OfficeInstalled: Boolean;

function InitializeSetup(): Boolean;
var
  VersionCode: Integer;
begin
  Result := True;
  
  // Validar Windows 10 64-bit mínimo (esto también se cubre con ArchitecturesInstallIn64BitMode y MinVersion, pero podemos añadir lógica extra)
  if not IsWin64 then
  begin
    MsgBox('OTI Converter requiere una versión de Windows de 64 bits.', mbError, MB_OK);
    Result := False;
    Exit;
  end;

  // Verificación básica de Office (Word/Excel) vía Registro
  OfficeInstalled := RegKeyExists(HKEY_LOCAL_MACHINE, 'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\excel.exe') or 
                     RegKeyExists(HKEY_LOCAL_MACHINE, 'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\WINWORD.EXE');
  
  if not OfficeInstalled then
  begin
    if MsgBox('No se ha detectado Microsoft Office en este equipo.' + #13#10 + 
              'Funciones como la conversión de Word/Excel a PDF podrían no estar disponibles o dependerán de LibreOffice.' + #13#10#13#10 +
              '¿Desea continuar con la instalación?', mbConfirmation, MB_YESNO) = IDNO then
    begin
      Result := False;
      Exit;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  UserDataDir: String;
begin
  if CurStep = ssPostInstall then
  begin
    // Crear la carpeta LocalAppData
    UserDataDir := ExpandConstant('{localappdata}\OTI-Converter');
    if not DirExists(UserDataDir) then
    begin
      CreateDir(UserDataDir);
    end;
  end;
end;

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\OTI-Converter\logs"
Type: filesandordirs; Name: "{localappdata}\OTI-Converter"
Type: filesandordirs; Name: "{app}\temp*"
Type: files; Name: "{autodesktop}\OTI Converter.lnk"
Type: files; Name: "{group}\OTI Converter.lnk"
