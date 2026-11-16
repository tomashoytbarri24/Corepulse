param([string]$Python='python')
$ErrorActionPreference='Stop'
$env:COREPULSE_ASSET_DIR=$PSScriptRoot
@'
from pathlib import Path
import os
from PySide6.QtCore import Qt,QRectF
from PySide6.QtGui import QImage,QPainter,QGuiApplication,QColor,QFont
from PySide6.QtSvg import QSvgRenderer
app=QGuiApplication([])
root=Path(os.environ['COREPULSE_ASSET_DIR']); out=root/'assets'; out.mkdir(exist_ok=True)
def render(svg,path,w,h):
    image=QImage(w*2,h*2,QImage.Format_RGB32); image.fill(0xff111822)
    p=QPainter(image); QSvgRenderer(svg).render(p); p.end()
    if not image.save(str(path),'PNG'): raise RuntimeError(path)
render((root/'WizardBackdrop.svg').read_bytes(),out/'cp-backdrop.png',900,560)
for name,label,bg,ink in (
 ('install','Instalar CorePulse  →','#24b8ed','#071725'),
 ('open','Abrir CorePulse  →','#24b8ed','#071725'),
 ('cancel','Cancelar','#1c2936','#b8c9d8'),
 ('finish','Terminar','#1c2936','#b8c9d8'),
 ('browse','Cambiar…','#243645','#bee8f5'),
 ('close','×','#1c2936','#b8c9d8'),
 ('check_on','✓','#3bcdbc','#092722'),
 ('check_off','','#182a37','#b8c9d8')):
    w,h=(236,52) if name in ('install','open') else (106,40) if name=='browse' else (32,32) if name=='close' else (22,22) if name.startswith('check') else (124,52)
    size=13 if name=='browse' else 19 if name in ('close','check_on') else 15
    image=QImage(w*2,h*2,QImage.Format_RGB32); image.fill(QColor('#151f2a' if name=='browse' else '#111822'))
    painter=QPainter(image); painter.scale(2,2)
    painter.setRenderHint(QPainter.Antialiasing); painter.setRenderHint(QPainter.TextAntialiasing)
    painter.setPen(Qt.NoPen); painter.setBrush(QColor(bg))
    painter.drawRoundedRect(QRectF(.5,.5,w-1,h-1),min(14,h//3),min(14,h//3))
    font=QFont('Segoe UI'); font.setPixelSize(size); font.setWeight(QFont.DemiBold)
    painter.setFont(font); painter.setPen(QColor(ink))
    painter.drawText(QRectF(0,0,w,h),Qt.AlignCenter,label); painter.end()
    image.save(str(out/('cp-'+name+'.png')),'PNG')
print('Installer assets rendered at 2x')
'@ | & $Python -
if($LASTEXITCODE -ne 0){throw 'Asset generation failed'}
