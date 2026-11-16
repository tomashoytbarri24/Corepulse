; Interfaz propia. El motor Inno conserva validación, rollback y desinstalación.
[Code]
var
  CanvasBack: TBitmapImage;
  Heading, Subheading, CardTitle, StageText, PercentText, InstallPath: TLabel;
  StepOne, StepTwo, StepThree, DesktopText: TLabel;
  NumberOne, NumberTwo, NumberThree, Banner: TLabel;
  PathBox: TNewEdit;
  Primary, Secondary, Browse, DesktopCheck, CloseIcon: TBitmapButton;
  ProgressFill: TPanel;
  DesktopSelected, PreviewDone: Boolean;
  PreviewDir: String;
  LastProgressPercent: Integer;
#ifdef TestBuild
  SelfTestStep, LastCapturedPercent: Integer;
#endif

function CreateRoundRectRgn(X1,Y1,X2,Y2,W,H: Integer): NativeUInt;
  external 'CreateRoundRectRgn@gdi32.dll stdcall';
function SetWindowRgn(Wnd: HWND; Rgn: NativeUInt; Redraw: Boolean): Integer;
  external 'SetWindowRgn@user32.dll stdcall';
function GetDC(Wnd: HWND): NativeUInt;
  external 'GetDC@user32.dll stdcall';
function ReleaseDC(Wnd: HWND; DC: NativeUInt): Integer;
  external 'ReleaseDC@user32.dll stdcall';
function BitBlt(Dest: NativeUInt; X,Y,W,H: Integer; Src: NativeUInt; SX,SY: Integer; Mode: Cardinal): Boolean;
  external 'BitBlt@gdi32.dll stdcall';
function RedrawWindow(Wnd: HWND; Rect,Rgn: NativeUInt; Flags: Cardinal): Boolean;
  external 'RedrawWindow@user32.dll stdcall';
function PostMessage(Wnd: HWND; Msg: Cardinal; WParam: NativeUInt; LParam: NativeInt): Boolean;
  external 'PostMessageW@user32.dll stdcall';
function GetWindowLong(Wnd: HWND; Index: Integer): LongInt;
  external 'GetWindowLongW@user32.dll stdcall';
function SetWindowLong(Wnd: HWND; Index,Value: LongInt): LongInt;
  external 'SetWindowLongW@user32.dll stdcall';
#ifdef TestBuild
function SetTimer(Wnd: HWND; Id: NativeUInt; Delay: Cardinal; Callback: NativeInt): NativeUInt;
  external 'SetTimer@user32.dll stdcall';
function KillTimer(Wnd: HWND; Id: NativeUInt): Boolean;
  external 'KillTimer@user32.dll stdcall';
#endif

function RGB(R,G,B: Integer): TColor;
begin
  Result := R + G*256 + B*65536;
end;

function NewText(X,Y,W,H,Size: Integer; Text: String; Ink: TColor; Bold: Boolean): TLabel;
begin
  Result := TLabel.Create(WizardForm);
  Result.Parent := WizardForm;
  Result.StyleElements := [];
  Result.AutoSize := False;
  Result.SetBounds(ScaleX(X),ScaleY(Y),ScaleX(W),ScaleY(H));
  Result.Transparent := True;
  Result.WordWrap := True;
  Result.ShowAccelChar := False;
  Result.Font.Name := 'Segoe UI';
  Result.Font.Size := Size;
  Result.Font.Color := Ink;
  if Bold then Result.Font.Style := [fsBold];
  Result.Caption := Text;
end;

procedure LoadButton(Button: TBitmapButton; Asset: String);
begin
  Button.PngImage.LoadFromFile(ExpandConstant('{tmp}\cp-' + Asset + '.png'));
end;

function NewButton(X,Y,W,H: Integer; Asset, Text: String; Handler: TNotifyEvent): TBitmapButton;
begin
  Result := TBitmapButton.Create(WizardForm);
  Result.Parent := WizardForm;
  Result.StyleElements := [];
  Result.SetBounds(ScaleX(X),ScaleY(Y),ScaleX(W),ScaleY(H));
  Result.Stretch := True;
  Result.BackColor := RGB(17,24,34);
  Result.Caption := Text;
  Result.Cursor := crHandPoint;
  Result.TabStop := True;
  Result.OnClick := Handler;
  LoadButton(Result,Asset);
end;

procedure ClickPrimary(Sender: TObject);
begin
  if (WizardForm.CurPageID=wpInstalling) or not WizardForm.NextButton.Enabled then Exit;
  if WizardForm.CurPageID=wpFinished then
    if WizardForm.RunList.Items.Count > 0 then WizardForm.RunList.Checked[0] := True;
  WizardForm.NextButton.OnClick(WizardForm.NextButton);
end;

procedure ClickSecondary(Sender: TObject);
begin
  if WizardForm.CurPageID=wpFinished then begin
    if WizardForm.RunList.Items.Count > 0 then WizardForm.RunList.Checked[0] := False;
    WizardForm.NextButton.OnClick(WizardForm.NextButton);
  end else WizardForm.CancelButton.OnClick(WizardForm.CancelButton);
end;

procedure ClickClose(Sender: TObject);
begin
  if WizardForm.CurPageID=wpFinished then ClickSecondary(nil)
  else PostMessage(WizardForm.Handle,$0010,0,0);
end;

#ifdef TestBuild
procedure WizardSelfTestTick(Wnd: HWND; Message: Cardinal; Id: NativeUInt; Ticks: Cardinal);
begin
  KillTimer(Wnd,Id);
  if (WizardForm.CurPageID=wpSelectDir) and (SelfTestStep=0) then begin
    SelfTestStep:=1;
    ClickPrimary(nil);
  end else if (WizardForm.CurPageID=wpFinished) and (SelfTestStep=1) then begin
    SelfTestStep:=2;
    ClickSecondary(nil);
  end;
end;
#endif

procedure ClickBrowse(Sender: TObject);
var Directory: String;
begin
  Directory := PathBox.Text;
  if BrowseForFolder('Dónde quieres instalar CorePulse',Directory,True) then PathBox.Text := Directory;
end;

procedure ClickDesktop(Sender: TObject);
begin
  DesktopSelected := not DesktopSelected;
  if DesktopSelected then LoadButton(DesktopCheck,'check_on')
  else LoadButton(DesktopCheck,'check_off');
end;

procedure KeyDown(Sender: TObject; var Key: Word; Shift: TShiftState);
begin
  if Key=13 then begin
    if WizardForm.ActiveControl=Secondary then ClickSecondary(nil)
    else if WizardForm.ActiveControl=Browse then ClickBrowse(nil)
    else if WizardForm.ActiveControl=DesktopCheck then ClickDesktop(nil)
    else if WizardForm.ActiveControl=CloseIcon then ClickClose(nil)
    else ClickPrimary(nil);
    Key:=0;
  end;
  if Key=27 then begin ClickClose(nil); Key:=0; end;
end;

procedure SetDesign(Stage: Integer);
begin
  PathBox.Visible := Stage=0;
  Browse.Visible := Stage=0;
  DesktopCheck.Visible := Stage=0;
  DesktopText.Visible := Stage=0;
  PercentText.Visible := Stage<>0;
  InstallPath.Visible := Stage<>0;
  if Stage<>0 then begin
    InstallPath.Caption := MinimizePathName(WizardDirValue,InstallPath.Font,InstallPath.Width);
    InstallPath.Hint := WizardDirValue;
  end;
  CardTitle.Visible := Stage=0;
  Primary.Visible := Stage<>1;
  StepOne.Font.Color := RGB(90,115,133);
  StepTwo.Font.Color := RGB(90,115,133);
  StepThree.Font.Color := RGB(90,115,133);
  NumberOne.Font.Color := RGB(90,115,133);
  NumberTwo.Font.Color := RGB(90,115,133);
  NumberThree.Font.Color := RGB(90,115,133);
  if Stage=0 then begin
    Heading.Caption := 'Tu equipo,' + #13#10 + 'bajo tu control.';
    Subheading.Caption := 'Monitoreo, diagnóstico y rendimiento en un solo lugar.';
    StageText.Caption := 'Instalación local · Tus datos permanecen en tu equipo.';
    StepOne.Font.Color := RGB(66,204,219);
    NumberOne.Font.Color := RGB(66,204,219);
    Banner.Caption := 'BIENVENIDO A COREPULSE';
    LoadButton(Primary,'install'); Primary.Caption := 'Instalar CorePulse';
    LoadButton(Secondary,'cancel'); Secondary.Caption := 'Cancelar';
    ProgressFill.Width := 0;
  end;
  if Stage=1 then begin
    LastProgressPercent := -1;
    ProgressFill.Width := 0;
    Heading.Caption := 'Preparando' + #13#10 + 'tu CorePulse.';
    Subheading.Caption := 'Estamos instalando los componentes de la aplicación.';
    StageText.Caption := 'Copiando la aplicación y preparando sus componentes…';
    PercentText.Caption := '0 %';
    StepTwo.Font.Color := RGB(66,204,219);
    NumberTwo.Font.Color := RGB(66,204,219);
    Banner.Caption := 'INSTALACIÓN EN CURSO';
  end;
  if Stage=2 then begin
    Heading.Caption := 'Todo listo.';
    Subheading.Caption := 'CorePulse ya forma parte de tu equipo.';
    StageText.Caption := 'Puedes abrirlo ahora o encontrarlo después en Inicio.';
    PercentText.Caption := 'Instalación completada';
    PercentText.Font.Color := RGB(61,211,189);
    StepThree.Font.Color := RGB(66,204,219);
    NumberThree.Font.Color := RGB(66,204,219);
    Banner.Caption := 'TU COREPULSE ESTÁ LISTO';
    LoadButton(Primary,'open'); Primary.Caption := 'Abrir CorePulse';
    LoadButton(Secondary,'finish'); Secondary.Caption := 'Terminar';
    ProgressFill.Width := ScaleX(512);
  end;
end;

procedure SavePreview(Directory,Name: String);
var Bitmap: TBitmap; DC: NativeUInt;
begin
  WizardForm.Refresh;
  RedrawWindow(WizardForm.Handle,0,0,$0185);
  Bitmap := TBitmap.Create;
  try
    Bitmap.Width := WizardForm.ClientWidth;
    Bitmap.Height := WizardForm.ClientHeight;
    DC := GetDC(WizardForm.Handle);
    try
      BitBlt(Bitmap.Canvas.Handle,0,0,Bitmap.Width,Bitmap.Height,DC,0,0,$00CC0020);
    finally ReleaseDC(WizardForm.Handle,DC); end;
    Bitmap.SaveToFile(AddBackslash(Directory)+Name+'.bmp');
  finally Bitmap.Free; end;
end;

procedure PreviewShown(Sender: TObject);
begin
  if PreviewDone or (PreviewDir='') then Exit;
  PreviewDone := True;
  ForceDirectories(PreviewDir);
  SetDesign(0); SavePreview(PreviewDir,'01-inicio');
  SetDesign(1); PercentText.Caption := '65 %'; ProgressFill.Width := ScaleX(333);
  SavePreview(PreviewDir,'02-instalando');
  SetDesign(2); SavePreview(PreviewDir,'03-listo');
  PostMessage(WizardForm.Handle,$0010,0,0);
end;

procedure InitializeWizard;
var Caption: TLabel; I: Integer; Assets: TArrayOfString;
begin
  PreviewDir := ExpandConstant('{param:PREVIEWDIR|}');
  WizardForm.BorderStyle := bsNone;
  WizardForm.StyleElements := [];
  WizardForm.ClientWidth := ScaleX(900);
  WizardForm.ClientHeight := ScaleY(560);
  WizardForm.Position := poScreenCenter;
  WizardForm.Color := RGB(17,24,34);
  { Componer los controles en memoria sin borrar toda la ventana en cada % . }
  SetWindowLong(WizardForm.Handle,-20,GetWindowLong(WizardForm.Handle,-20) or $02000000);
  WizardForm.KeyPreview := True;
  WizardForm.OnKeyDown := @KeyDown;
  WizardForm.OuterNotebook.Visible := False;
  WizardForm.Bevel.Visible := False;
  WizardForm.BackButton.Visible := False;
  WizardForm.NextButton.SetBounds(-ScaleX(2000),0,1,1);
  WizardForm.CancelButton.SetBounds(-ScaleX(2000),0,1,1);
  WizardForm.NextButton.TabStop := False;
  WizardForm.CancelButton.TabStop := False;
  SetWindowRgn(WizardForm.Handle,CreateRoundRectRgn(0,0,WizardForm.Width,WizardForm.Height,ScaleX(24),ScaleY(24)),True);
  Assets := ['backdrop','install','open','cancel','finish','browse','close','check_on','check_off'];
  for I:=0 to GetArrayLength(Assets)-1 do ExtractTemporaryFile('cp-'+Assets[I]+'.png');
  CanvasBack := TBitmapImage.Create(WizardForm);
  CanvasBack.Parent := WizardForm;
  CanvasBack.SetBounds(0,0,WizardForm.ClientWidth,WizardForm.ClientHeight);
  CanvasBack.Stretch := True;
  CanvasBack.PngImage.LoadFromFile(ExpandConstant('{tmp}\cp-backdrop.png'));
  Caption := NewText(44,37,80,40,23,'Core',RGB(242,248,253),True);
  Caption := NewText(103,37,120,40,23,'Pulse',RGB(36,184,237),True);
  Caption := NewText(44,208,230,82,22,'Conoce tu equipo.'+#13#10+'Toma el control.',RGB(232,243,250),True);
  Caption := NewText(44,302,212,38,10,'Lecturas reales. Decisiones claras.',RGB(140,170,187),False);
  NumberOne := NewText(49,356,16,24,10,'1',RGB(100,216,229),True); NumberOne.Alignment:=taCenter;
  NumberTwo := NewText(49,396,16,24,10,'2',RGB(100,151,171),True); NumberTwo.Alignment:=taCenter;
  NumberThree := NewText(49,436,16,24,10,'3',RGB(100,151,171),True); NumberThree.Alignment:=taCenter;
  StepOne := NewText(82,356,180,26,11,'Ubicación',RGB(66,204,219),True);
  StepTwo := NewText(82,396,180,26,11,'Instalación',RGB(90,115,133),True);
  StepThree := NewText(82,436,180,26,11,'Listo para usar',RGB(90,115,133),True);
  Caption := NewText(44,514,230,22,9,'WINDOWS 10/11 · 64 BITS',RGB(92,121,139),False);
  Banner := NewText(344,70,460,24,9,'BIENVENIDO A COREPULSE',RGB(58,194,217),True);
  Heading := NewText(344,109,512,86,27,'',RGB(240,246,251),True);
  Subheading := NewText(344,202,512,43,11,'',RGB(159,180,195),False);
  CardTitle := NewText(366,264,350,24,9,'CARPETA DE INSTALACIÓN',RGB(99,142,164),True);
  PathBox := TNewEdit.Create(WizardForm);
  PathBox.Parent := WizardForm;
  PathBox.StyleElements := [];
  PathBox.SetBounds(ScaleX(366),ScaleY(304),ScaleX(363),ScaleY(28));
  PathBox.BorderStyle := bsNone;
  PathBox.Color := RGB(21,31,42);
  PathBox.Font.Name := 'Segoe UI'; PathBox.Font.Size := 10;
  PathBox.Font.Color := RGB(219,232,241);
  PathBox.Text := WizardForm.DirEdit.Text;
  Browse := NewButton(738,279,106,40,'browse','Cambiar carpeta',@ClickBrowse);
  PercentText := NewText(366,264,470,47,22,'0 %',RGB(227,241,250),True);
  InstallPath := NewText(366,318,470,22,9,'',RGB(159,180,195),False);
  InstallPath.ShowHint := True;
  InstallPath.WordWrap := False;
  ProgressFill := TPanel.Create(WizardForm);
  ProgressFill.Parent := WizardForm;
  ProgressFill.StyleElements := [];
  ProgressFill.BevelOuter := bvNone; ProgressFill.Color := RGB(61,211,189);
  ProgressFill.SetBounds(ScaleX(344),ScaleY(378),0,ScaleY(4));
  DesktopCheck := NewButton(344,402,22,22,'check_off','Acceso directo al escritorio',@ClickDesktop);
  DesktopText := NewText(378,403,470,25,10,'Crear un acceso directo en el escritorio',RGB(169,190,204),False);
  DesktopText.OnClick := @ClickDesktop; DesktopText.Cursor := crHandPoint;
  StageText := NewText(344,432,512,24,9,'',RGB(108,138,157),False);
  Primary := NewButton(620,482,236,52,'install','Instalar CorePulse',@ClickPrimary);
  Secondary := NewButton(344,482,124,52,'cancel','Cancelar',@ClickSecondary);
  CloseIcon := NewButton(842,22,32,32,'close','Cerrar instalador',@ClickClose);
  DesktopSelected := WizardIsTaskSelected('desktopicon');
  if DesktopSelected then LoadButton(DesktopCheck,'check_on');
  SetDesign(0);
  if PreviewDir<>'' then WizardForm.OnActivate := @PreviewShown;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (PageID<>wpSelectDir) and (PageID<>wpInstalling) and (PageID<>wpFinished);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  if (CurPageID=wpSelectDir) and not WizardSilent then begin
    WizardForm.DirEdit.Text := PathBox.Text;
    if DesktopSelected then WizardSelectTasks('desktopicon') else WizardSelectTasks('');
  end;
  Result := True;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  WizardForm.BackButton.Visible := False;
  { Mantener la visibilidad semántica: el motor la consulta al navegar/cerrar. }
  WizardForm.NextButton.Visible := CurPageID<>wpInstalling;
  WizardForm.CancelButton.Visible := CurPageID<>wpFinished;
  WizardForm.NextButton.Left := -ScaleX(2000);
  WizardForm.CancelButton.Left := -ScaleX(2000);
  if CurPageID=wpInstalling then SetDesign(1)
  else if CurPageID=wpFinished then SetDesign(2)
  else SetDesign(0);
  if CurPageID=wpPreparing then begin
    Heading.Caption := 'Comprobando' + #13#10 + 'la instalación.';
    if WizardForm.PreparingMemo.Text<>'' then StageText.Caption := WizardForm.PreparingMemo.Text;
  end;
#ifdef TestBuild
  if (ExpandConstant('{param:AUTOTEST|0}')='1') and
     (((CurPageID=wpSelectDir) and (SelfTestStep=0)) or
      ((CurPageID=wpFinished) and (SelfTestStep=1))) then
    SetTimer(0,0,350,CreateCallback(@WizardSelfTestTick));
#endif
end;

procedure CurInstallProgressChanged(CurProgress,MaxProgress: Integer);
var Percent: Integer;
#ifdef TestBuild
  ProgressDir: String;
#endif
begin
  if MaxProgress<=0 then Exit;
  if CurProgress<0 then CurProgress:=0;
  if CurProgress>MaxProgress then CurProgress:=MaxProgress;
  { Pascal Script divide enteros antes de Round: usar MulDiv evita 0 -> 100
    y su cálculo intermedio de 64 bits evita desbordar paquetes grandes. }
  Percent := MulDiv(CurProgress,100,MaxProgress);
  if Percent=LastProgressPercent then Exit;
  LastProgressPercent:=Percent;
  PercentText.Caption := IntToStr(Percent)+' %';
  ProgressFill.Width := MulDiv(CurProgress,ScaleX(512),MaxProgress);
  if Percent<15 then StageText.Caption := 'Preparando los archivos de CorePulse…'
  else if Percent<90 then StageText.Caption := 'Instalando la aplicación y sus componentes…'
  else StageText.Caption := 'Terminando la instalación…';
  PercentText.Update;
  ProgressFill.Update;
  StageText.Update;
#ifdef TestBuild
  Log(Format('CorePulseProgress current=%d maximum=%d percent=%d width=%d visible=%d page=%d', [CurProgress,MaxProgress,Percent,ProgressFill.Width,Ord(PercentText.Visible),WizardForm.CurPageID]));
  if Percent=0 then Log(Format('CorePulseInstallPath=%s Buffered=%d', [WizardDirValue,Ord((GetWindowLong(WizardForm.Handle,-20) and $02000000)<>0)]));
  ProgressDir:=ExpandConstant('{param:PROGRESSDIR|}');
  if (ProgressDir<>'') and (Percent<100) and (Percent>=LastCapturedPercent+25) then begin
    LastCapturedPercent:=Percent;
    ForceDirectories(ProgressDir);
    SavePreview(ProgressDir,'avance-'+IntToStr(Percent));
  end;
#endif
end;

procedure CancelButtonClick(CurPageID: Integer; var Cancel,Confirm: Boolean);
begin
  if PreviewDir<>'' then begin Cancel:=True; Confirm:=False; end;
end;
