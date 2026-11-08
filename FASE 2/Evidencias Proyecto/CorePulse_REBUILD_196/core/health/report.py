"""Generación local de informes CorePulse con diseño común para todos los PDF."""
from __future__ import annotations

from datetime import datetime
import math
import os
from pathlib import Path
import re

from PySide6.QtCore import QObject, Property, Signal, Slot, Qt, QUrl, QMarginsF, QRectF, QPointF
from PySide6.QtGui import QColor, QDesktopServices, QFont, QFontMetrics, QPainter, QPageLayout, QPageSize, QPdfWriter


INK = "#17263A"
MUTED = "#617186"
NAVY = "#10233A"
BLUE = "#168FC2"
TEAL = "#159A91"
LINE = "#D7E0E9"
PALE = "#F3F7FA"
WHITE = "#FFFFFF"


def _output_dir():
    local = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    return local / "CorePulse" / "reportes"


def _number(value, suffix="", digits=1):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        return "N/A"
    formatted = f"{float(value):,.{digits}f}"
    formatted = formatted.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{formatted}{suffix}"


def _text(value, fallback="N/A", limit=500):
    if value is None:
        return fallback
    if isinstance(value, bool):
        return "Sí" if value else "No"
    result = " ".join(str(value).replace("\x00", " ").split())
    return result[:limit] or fallback


def _display_time(value):
    raw = str(value or "")
    if not raw:
        return "N/A"
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed.astimezone().strftime("%d/%m/%Y %H:%M:%S")
    except (TypeError, ValueError, OverflowError):
        return raw[:40]


def _state_label(value):
    """Estados legibles; una lectura ausente nunca se presenta como correcta."""
    return {"ok": "Correcto", "attention": "Revisar", "critical": "Crítico",
            "partial": "Parcial", "unknown": "Sin datos", "na": "Sin datos"}.get(
                str(value or "").strip().lower(), "Sin datos")



def _plain_check(row):
    """Explica la lectura sin cambiar su valor, estado ni origen."""
    explanations = {
        'cpu': 'Temperatura del procesador en esta lectura.',
        'gpu': 'Temperatura de la tarjeta gráfica en esta lectura.',
        'ram': 'Memoria ocupada por Windows y las aplicaciones; no mide daño físico.',
        'disks': 'Estado que informan los discos; es distinto del espacio libre.',
        'space': 'Porcentaje ocupado en la unidad con menos espacio proporcional.',
        'battery': 'Capacidad máxima actual frente a la original; no es la carga de hoy.',
        'drivers': 'Cantidad de dispositivos con un error detectado por Windows; no son actualizaciones pendientes.',
        'recovery': 'Herramientas de Windows para recuperarse de un problema. No son una copia de tus archivos.',
    }
    state = str(row.get('state') or '').lower()
    if state not in ('ok', 'attention', 'critical'):
        explanation = 'No se pudo comprobar esta lectura. Esto, por sí solo, no confirma una avería.'
    else:
        explanation = explanations.get(row.get('key'), _text(row.get('detail'), '', 250))
    return _text(row.get('value')) + ' · ' + _state_label(state) + (' · ' + explanation if explanation else '')


def _write_next_steps(doc, checks):
    actions = {
        'cpu': 'Revisa la ventilación y las aplicaciones que están exigiendo al procesador. Repite la lectura con el equipo en reposo.',
        'gpu': 'Revisa la ventilación y la carga gráfica. Repite la lectura después de cerrar el juego o programa exigente.',
        'ram': 'Cierra las aplicaciones que no estés usando y vuelve a comprobar el uso de memoria.',
        'disks': 'Guarda una copia de tus archivos importantes y revisa la unidad indicada en Almacenamiento.',
        'space': 'Revisa qué ocupa espacio y elimina solo archivos que reconozcas y no necesites.',
        'battery': 'La batería conserva menos capacidad que al principio. Comprueba su autonomía y valora una revisión si ya no cubre tus necesidades.',
        'drivers': 'Abre la información de dispositivos de Windows y revisa los elementos que presentan un error.',
        'recovery': 'Abre Recuperación y comprueba el estado de las herramientas de Windows. Conserva también una copia de tus archivos.',
    }
    pending = [row for row in checks if row.get('state') in ('attention', 'critical')]
    doc.section('Qué conviene revisar', minimum_content=65)
    if pending:
        for row in sorted(pending, key=lambda item: item.get('state') != 'critical'):
            doc.paragraph(_text(row.get('title'), 'Comprobación') + ': ' + _text(row.get('value')), size=10, bold=True, gap=3)
            doc.paragraph(actions.get(row.get('key'), _text(row.get('detail'), 'Revisa este resultado en CorePulse.')), size=9, color=MUTED, gap=7)
    else:
        doc.paragraph('No hay avisos en las comprobaciones disponibles.' if checks else 'Todavía no hay comprobaciones suficientes para orientar una revisión.', size=9)
    unknown = sum(row.get('state') not in ('ok', 'attention', 'critical') for row in checks)
    if unknown:
        label = 'comprobación sin datos' if unknown == 1 else 'comprobaciones sin datos'
        doc.paragraph(f'{unknown} {label}. El resultado solo describe lo que se pudo medir.', size=9, color=MUTED)


class _PdfDocument:
    """Plantilla A4 reutilizada por informes de sistema y de benchmark."""

    def __init__(self, path: Path, title: str, subtitle: str):
        self.writer = QPdfWriter(str(path))
        self.writer.setResolution(96)
        self.writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        self.writer.setPageMargins(QMarginsF(14, 13, 14, 14), QPageLayout.Unit.Millimeter)
        self.writer.setTitle(title)
        self.writer.setCreator("CorePulse")
        self.painter = QPainter(self.writer)
        if not self.painter.isActive():
            raise OSError("Qt no pudo iniciar el escritor PDF")
        self.rect = self.writer.pageLayout().paintRectPixels(self.writer.resolution())
        # QPdfWriter's painter origin is the top-left of the paintable area.
        # paintRectPixels already accounts for margins, so only its dimensions
        # belong in painter coordinates; applying rect.x()/rect.y() again doubles
        # the leading margins and pushes the content toward the lower-right.
        self.left = 0
        self.top = 0
        self.width = int(self.rect.width())
        self.bottom = int(self.rect.height())
        self.page = 1
        self.generated = datetime.now().astimezone().strftime("%d/%m/%Y %H:%M")
        self.title = title
        self.subtitle = subtitle
        self.body_bottom = self.bottom - 30
        self.y = self.top
        self._header(first=True)

    def _set_font(self, size=10, *, bold=False):
        font = QFont("Segoe UI", size, QFont.Weight.DemiBold if bold else QFont.Weight.Normal)
        self.painter.setFont(font)
        return QFontMetrics(font, self.painter.device())

    def _header(self, *, first=False):
        p = self.painter
        band_height = 102 if first else 40
        p.fillRect(self.left, self.top, self.width, band_height, QColor(NAVY))
        p.fillRect(self.left, self.top, 5, band_height, QColor(BLUE))
        p.setPen(QColor(WHITE))
        metrics = self._set_font(13 if first else 10, bold=True)
        logo_x = self.left + 19
        baseline = self.top + (28 if first else 26)
        p.drawText(logo_x, baseline, "Core")
        logo_width = metrics.horizontalAdvance("Core")
        p.setPen(QColor("#56C8F0"))
        p.drawText(logo_x + logo_width, baseline, "Pulse")
        if first:
            p.setPen(QColor("#AFC2D5"))
            self._set_font(8)
            p.drawText(logo_x, self.top + 48, "INFORME LOCAL · DATOS VERIFICABLES")
            p.setPen(QColor(WHITE))
            self._set_font(21, bold=True)
            p.drawText(logo_x, self.top + 76, self.title[:72])
            p.setPen(QColor("#D1DEEA"))
            self._set_font(9)
            p.drawText(logo_x, self.top + 94, self.subtitle[:110])
            p.setPen(QColor("#B7C7D8"))
            self._set_font(8)
            stamp = "Generado " + self.generated
            p.drawText(self.left + self.width - self._set_font(8).horizontalAdvance(stamp) - 17,
                       self.top + 26, stamp)
            self.y = self.top + band_height + 19
        else:
            p.setPen(QColor("#D1DEEA"))
            self._set_font(9)
            p.drawText(self.left + self.width - 220, self.top + 26, self.title[:48])
            self.y = self.top + band_height + 16

    @staticmethod
    def _wrapped(text, metrics, width):
        lines = []
        for raw_line in str(text or "").splitlines() or [""]:
            current = ""
            for word in raw_line.split() or [""]:
                candidate = word if not current else current + " " + word
                if metrics.horizontalAdvance(candidate) <= width:
                    current = candidate
                    continue
                if current:
                    lines.append(current)
                    current = ""
                if metrics.horizontalAdvance(word) <= width:
                    current = word
                    continue
                piece = ""
                for char in word:
                    if piece and metrics.horizontalAdvance(piece + char) > width:
                        lines.append(piece)
                        piece = char
                    else:
                        piece += char
                current = piece
            lines.append(current)
        return lines or [""]

    def _new_page(self):
        self._footer()
        if not self.writer.newPage():
            raise OSError("Qt no pudo crear una página nueva")
        self.page += 1
        self._header(first=False)

    def _footer(self):
        p = self.painter
        y = self.bottom - 20
        p.setPen(QColor(LINE))
        p.drawLine(self.left, y - 8, self.left + self.width, y - 8)
        p.setPen(QColor(MUTED))
        metrics = self._set_font(8)
        p.drawText(self.left, y, "CorePulse · Informe generado localmente")
        page_text = f"Página {self.page}"
        p.drawText(self.left + self.width - metrics.horizontalAdvance(page_text), y, page_text)

    def paragraph(self, text, *, size=10, color=INK, bold=False, indent=0, gap=5):
        metrics = self._set_font(size, bold=bold)
        lines = self._wrapped(text, metrics, self.width - indent)
        line_height = max(11, metrics.height() + 2)
        for line in lines:
            if self.y + line_height > self.body_bottom:
                self._new_page()
                metrics = self._set_font(size, bold=bold)
                line_height = max(11, metrics.height() + 2)
            self.painter.setPen(QColor(color))
            self.painter.drawText(self.left + indent, self.y + metrics.ascent(), line)
            self.y += line_height
        self.y += gap

    def section(self, title, *, minimum_content=40):
        height = 29
        # El título y las primeras líneas deben aparecer en la misma página.
        if self.y + height + minimum_content > self.body_bottom:
            self._new_page()
        self.painter.setPen(Qt.PenStyle.NoPen)
        self.painter.setBrush(QColor(PALE))
        self.painter.drawRoundedRect(QRectF(self.left, self.y, self.width, height), 5, 5)
        self.painter.fillRect(self.left, self.y + 4, 3, height - 8, QColor(TEAL))
        self.painter.setPen(QColor(INK))
        metrics = self._set_font(10, bold=True)
        self.painter.drawText(self.left + 12, self.y + (height + metrics.ascent() - metrics.descent()) // 2, str(title).upper())
        self.y += height + 9

    def table(self, rows, *, label_width_ratio=0.31):
        label_font = self._set_font(9)
        label_width = int(self.width * label_width_ratio)
        label_text_width = label_width - 18
        value_font = self._set_font(9, bold=True)
        value_width = self.width - label_width - 23
        for index, pair in enumerate(rows):
            label, value = pair
            label = _text(label, "", 100)
            value = _text(value, "N/A", 420)
            label_lines = self._wrapped(label, label_font, label_text_width)
            lines = self._wrapped(value, value_font, value_width)
            line_height = max(12, value_font.height() + 1)
            row_height = max(29, max(len(lines), len(label_lines)) * line_height + 10)
            if self.y + row_height > self.body_bottom:
                self._new_page()
            background = WHITE if index % 2 == 0 else PALE
            self.painter.fillRect(self.left, self.y, self.width, row_height, QColor(background))
            self.painter.setPen(QColor(LINE))
            self.painter.drawLine(self.left, self.y + row_height, self.left + self.width, self.y + row_height)
            self.painter.setPen(QColor(MUTED))
            self.painter.setFont(QFont("Segoe UI", 9))
            label_baseline = self.y + (row_height - len(label_lines) * line_height) // 2 + label_font.ascent()
            for line in label_lines:
                self.painter.drawText(self.left + 10, label_baseline, line)
                label_baseline += line_height
            self.painter.setPen(QColor(INK))
            self.painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            baseline = self.y + (row_height - len(lines) * line_height) // 2 + value_font.ascent()
            for line in lines:
                self.painter.drawText(self.left + label_width + 9, baseline, line)
                baseline += line_height
            self.y += row_height
        self.y += 5

    def cards(self, cards):
        cards = list(cards or [])
        if not cards:
            return
        if self.y + 75 > self.body_bottom:
            self._new_page()
        count = min(4, len(cards))
        gap = 8
        card_width = (self.width - gap * (count - 1)) / count
        for index, card in enumerate(cards[:count]):
            x = self.left + index * (card_width + gap)
            self.painter.setPen(QColor(LINE))
            self.painter.setBrush(QColor(PALE))
            self.painter.drawRoundedRect(QRectF(x, self.y, card_width, 68), 7, 7)
            self.painter.fillRect(int(x), self.y + 8, 3, 52, QColor(BLUE if index % 2 == 0 else TEAL))
            self.painter.setPen(QColor(MUTED))
            label_metrics = self._set_font(8)
            self.painter.drawText(int(x + 11), self.y + 20, _text(card[0], "", 28))
            self.painter.setPen(QColor(INK))
            value_metrics = self._set_font(14, bold=True)
            value = _text(card[1], "N/A", 25)
            while value and value_metrics.horizontalAdvance(value) > card_width - 22:
                value = value[:-2] + "…"
                value_metrics = self._set_font(14, bold=True)
            self.painter.drawText(int(x + 11), self.y + 43, value)
            self.painter.setPen(QColor(MUTED))
            caption_metrics = self._set_font(8)
            caption = _text(card[2] if len(card) > 2 else "", "", 80)
            caption = caption_metrics.elidedText(caption, Qt.ElideRight, max(1, int(card_width - 22)))
            self.painter.drawText(int(x + 11), self.y + 59, caption)
        self.y += 77

    def line_chart(self, rows, *, marker=0, marker_label='Marcador', height=165):
        """Frametime con ejes reales; el resumen conserva máximos por bloque."""
        from core.health.game_capture import peak_series
        rows = peak_series(rows)
        height = max(110, height)
        if self.y + height > self.body_bottom:
            self._new_page()
        if not rows:
            self.paragraph('Frametime N/A: no se recibieron intervalos ETW verificables.', size=9)
            return
        p = self.painter
        x, top, width, plot = self.left+40, self.y+13, self.width-60, height-42
        ceiling = max(50, max(r['ms'] for r in rows))
        start, end = rows[0]['time'], rows[-1]['time']
        span = max(.001, end-start)
        self._set_font(8)
        p.fillRect(QRectF(x, top, width, plot), QColor(PALE))
        for value in (16.667, 33.333, ceiling):
            y = top+plot-value/ceiling*plot
            p.setPen(QColor(LINE))
            p.drawLine(QPointF(x, y), QPointF(x+width, y))
            p.setPen(QColor(MUTED))
            p.drawText(QPointF(self.left, y+3), f'{value:.1f}')
        p.setPen(QColor(BLUE))
        for a, b in zip(rows, rows[1:]):
            p.drawLine(QPointF(x+(a['time']-start)/span*width, top+plot-a['ms']/ceiling*plot),
                       QPointF(x+(b['time']-start)/span*width, top+plot-b['ms']/ceiling*plot))
        if start <= marker <= end:
            mx = x+(marker-start)/span*width
            p.setPen(QColor('#B67B20'))
            p.drawLine(QPointF(mx, top), QPointF(mx, top+plot))
            p.drawText(QPointF(min(mx+4, x+width-QFontMetrics(p.font(), p.device()).horizontalAdvance(marker_label)), top+12), marker_label)
        p.setPen(QColor(MUTED))
        p.drawText(QPointF(x, top+plot+16), f'{start:.1f} s')
        p.drawText(QPointF(x+width-40, top+plot+16), f'{end:.1f} s')
        p.drawText(QPointF(self.left, self.y+5), 'ms')
        self.y += height

    def bar_chart(self, title, rows, *, suffix=" FPS"):
        values = [(str(label), value) for label, value in (rows or [])
                  if isinstance(value, (int, float)) and not isinstance(value, bool)
                  and math.isfinite(float(value)) and float(value) >= 0]
        if not values:
            return
        title_metrics = self._set_font(9, bold=True)
        row_height = 26
        height = 22 + len(values) * row_height + 5
        if self.y + height > self.body_bottom:
            self._new_page()
        self.painter.setPen(QColor(INK))
        self.painter.drawText(self.left, self.y + title_metrics.ascent(), _text(title, "", 100))
        label_width = int(self.width * 0.28)
        value_width = 58
        bar_x = self.left + label_width
        bar_width = max(80, self.width - label_width - value_width - 22)
        maximum = max((float(value) for _label, value in values), default=0.0)
        maximum = maximum or 1.0
        metrics = self._set_font(8)
        for index, (label, value) in enumerate(values):
            top = self.y + 20 + index * row_height
            self.painter.setPen(QColor(MUTED))
            label_text = metrics.elidedText(label, Qt.TextElideMode.ElideRight, label_width - 12)
            self.painter.setFont(QFont("Segoe UI", 8))
            self.painter.drawText(self.left + 2, top + 15, label_text)
            self.painter.setPen(Qt.PenStyle.NoPen)
            self.painter.setBrush(QColor(PALE))
            self.painter.drawRoundedRect(QRectF(bar_x, top + 5, bar_width, 12), 6, 6)
            fill_width = max(3, bar_width * float(value) / maximum) if value else 0
            self.painter.setBrush(QColor(BLUE if index % 2 == 0 else TEAL))
            if fill_width:
                self.painter.drawRoundedRect(QRectF(bar_x, top + 5, fill_width, 12), 6, 6)
            self.painter.setPen(QColor(INK))
            self.painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
            display = _number(value, suffix, 1)
            self.painter.drawText(bar_x + bar_width + 8, top + 15, display)
        self.y += height + 5

    def note(self, text):
        metrics = self._set_font(8)
        lines = self._wrapped(text, metrics, self.width - 34)
        line_height = max(11, metrics.height() + 2)
        height = max(42, len(lines) * line_height + 17)
        if self.y + height > self.body_bottom:
            self._new_page()
            metrics = self._set_font(8)
        self.painter.setPen(QColor("#B8D9E2"))
        self.painter.setBrush(QColor("#F0F8FA"))
        self.painter.drawRoundedRect(QRectF(self.left, self.y, self.width, height), 6, 6)
        self.painter.fillRect(self.left, self.y + 6, 3, height - 12, QColor(TEAL))
        self.painter.setPen(QColor(MUTED))
        baseline = self.y + 8 + metrics.ascent()
        for line in lines:
            self.painter.drawText(self.left + 12, baseline, line)
            baseline += line_height
        self.y += height + 7

    def finish(self):
        self._footer()
        if self.painter.isActive():
            self.painter.end()


class ReportExporter(QObject):
    changed = Signal()

    def __init__(self, telemetry, system_health, insights, windows_health=None, parent=None,
                 ai_controller=None, benchmark_controller=None):
        super().__init__(parent)
        self.telemetry = telemetry
        self.system_health = system_health
        self.insights = insights
        self.windows_health = windows_health
        self.ai_controller = ai_controller
        self.benchmark_controller = benchmark_controller
        self._data = {"busy": False, "status": "Listo para generar un informe.", "path": "", "kind": "",
                      "diagnosticBusy": False, "diagnosticStatus": "", "diagnosticPath": "", "diagnosticRunId": 0}
        self._last_diagnostic_run_id = 0
        try:
            self.system_health.diagnosticChanged.connect(self._on_diagnostic_changed)
        except (AttributeError, RuntimeError):
            pass

    @Property("QVariantMap", notify=changed)
    def data(self):
        return self._data

    def _set(self, **values):
        self._data = {**self._data, **values}
        self.changed.emit()

    def _on_diagnostic_changed(self):
        diagnostic = dict(getattr(self.system_health, "diagnostic", {}) or {})
        run_id = int(diagnostic.get("runId") or 0)
        if diagnostic.get("status") in ("complete", "partial") and run_id > self._last_diagnostic_run_id:
            self.generateDiagnostic()

    def _write(self, filename, title, subtitle, builder):
        folder = _output_dir()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / filename
        document = None
        try:
            document = _PdfDocument(path, title, subtitle)
            builder(document)
            document.finish()
            document = None
            if not path.is_file() or path.stat().st_size < 1200:
                raise OSError("El PDF generado está vacío o incompleto")
            return path
        except Exception:
            if document is not None:
                try:
                    if document.painter.isActive():
                        document.painter.end()
                except Exception:
                    pass
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def _benchmark_data(self):
        return dict(getattr(self.benchmark_controller, "data", {}) or {})

    @staticmethod
    def _gpu_summary(result):
        scenes = [row for row in (result.get("scenes") or [])
                  if isinstance(row, dict) and row.get("status") == "OK"]
        fps = [row.get("frames_per_s") for row in scenes if isinstance(row.get("frames_per_s"), (int, float))]
        lows = [row.get("one_percent_low_fps") for row in scenes if isinstance(row.get("one_percent_low_fps"), (int, float))]
        return scenes, (sum(fps) / len(fps) if fps else result.get("frames_per_s", result.get("value"))), (sum(lows) / len(lows) if lows else result.get("one_percent_low_fps"))

    @staticmethod
    def _scene_label(key):
        labels = {"avenue": "Avenida de neón", "district": "Distrito financiero",
                  "skyline": "Horizonte nocturno", "megacity": "Megaciudad"}
        return labels.get(str(key or ""), str(key or "Escena"))

    def _append_benchmarks(self, doc, data, *, include_history=True):
        cpu = data.get('result') if isinstance(data.get('result'), dict) else {}
        gpu = data.get('gpuResult') if isinstance(data.get('gpuResult'), dict) else {}
        cpu_ok = cpu.get('status') == 'complete'
        gpu_ok = gpu.get('status') in ('OK', 'PARTIAL') and gpu.get('benchmark_method')
        history = [row for row in (data.get('history') or []) if isinstance(row, dict)]
        doc.note('Cómo leer esta prueba: CPU es el procesador y GPU la tarjeta gráfica. FPS son imágenes por segundo; el 1 % Low resume los momentos más lentos de cada escena. MiB/s expresa datos transferidos por segundo. Para comparar, usa el mismo método, equipo y configuración.')
        if not cpu_ok and not gpu_ok:
            doc.paragraph('No hay una prueba completada disponible para mostrar resultados detallados.', color=MUTED)
        cpu_row = cpu.get('cpu') if isinstance(cpu.get('cpu'), dict) else {}
        ram_row = cpu.get('ram') if isinstance(cpu.get('ram'), dict) else {}
        disk_row = cpu.get('ssd') if isinstance(cpu.get('ssd'), dict) else {}
        scenes, fps, low = self._gpu_summary(gpu)
        if cpu_ok:
            doc.section('Procesador, memoria y disco')
            doc.cards([
                ('Procesador', _number(cpu_row.get('operationsPerSecond'), '', 0), 'cálculos por segundo'),
                ('Memoria RAM', _number(ram_row.get('mibPerSecond'), ' MiB/s', 1), 'datos copiados por segundo'),
                ('Lectura del disco', _number(disk_row.get('readMiBPerSecond'), ' MiB/s', 1), 'datos leídos por segundo'),
                ('Escritura del disco', _number(disk_row.get('writeMiBPerSecond'), ' MiB/s', 1), 'datos escritos por segundo'),
            ])
            doc.paragraph('En estas mediciones, más operaciones o datos por segundo significan más rendimiento bajo las mismas condiciones. No son una puntuación universal de calidad.', size=9, color=MUTED)
            doc.table([('Prueba realizada', _display_time(cpu.get('completedAt'))),
                       ('Verificación de los datos del disco', 'Correcta' if disk_row.get('integrity') == 'PASS' else _text(disk_row.get('integrity')))])
        if gpu_ok:
            doc.section('Tarjeta gráfica')
            doc.cards([
                ('FPS promedio', _number(fps, ' FPS', 1), 'fluidez media de las escenas'),
                ('1 % Low', _number(low, ' FPS', 1), 'rendimiento en momentos lentos'),
                ('Resolución', _text(gpu.get('render_resolution') or gpu.get('resolution'), 'N/A', 25), 'tamaño de la imagen'),
                ('Estado', 'Completo' if gpu.get('status') == 'OK' else 'Parcial', 'escenas disponibles'),
            ])
            doc.paragraph('Un promedio alto puede esconder tirones. Por eso se muestra también el 1 % Low. Aquí ambos valores son el promedio de las escenas que terminaron correctamente.', size=9, color=MUTED)
            doc.table([('Tarjeta utilizada', _text(gpu.get('renderer'), 'N/A', 180))])
            if scenes:
                doc.bar_chart('Fluidez por escena (FPS)', [(self._scene_label(row.get('key')), row.get('frames_per_s')) for row in scenes[:8]])
        if cpu_ok or gpu_ok:
            doc._new_page()
            doc.section('Detalles técnicos - para soporte')
            doc.paragraph('Esta sección permite repetir y comparar la prueba. Puedes consultar primero el resumen de la página anterior.', size=9, color=MUTED)
            if cpu_ok:
                doc.table([
                    ('Método del procesador', _text(cpu_row.get('method'), 'Cálculos enteros por bloques', 240)),
                    ('Método de memoria', _text(ram_row.get('method'), 'Copias verificadas; influido por cachés', 240)),
                    ('Método de disco', _text(disk_row.get('method'), 'Archivo temporal y lectura verificada', 240)),
                ])
            if gpu_ok:
                session = gpu.get('session') if isinstance(gpu.get('session'), dict) else {}
                doc.table([
                    ('Perfil y motor gráfico', _text(gpu.get('profile') or data.get('gpuProfile'), 'N/A').title() + ' · ' + _text(gpu.get('api'), 'DirectX 11')),
                    ('Nivel de compatibilidad', _text(gpu.get('feature_level'))),
                    ('Modo de pantalla', _text(gpu.get('window_mode'))),
                    ('Selección de gráfica', _text(gpu.get('adapter_selection_reason') or gpu.get('adapter_selection'), 'N/A', 250)),
                    ('Temperatura máxima', _number(session.get('gpu_temp_max_c'), ' °C', 0)),
                    ('Frecuencia media', _number(session.get('gpu_clock_avg_mhz'), ' MHz', 0)),
                    ('Consumo medio', _number(session.get('gpu_power_avg_w'), ' W', 1)),
                    ('Estabilidad observada', _text(session.get('stability'))),
                    ('Duración', _number(gpu.get('duration_s'), ' s', 1)),
                    ('Fecha', _display_time(gpu.get('completedAt') or gpu.get('startedAt'))),
                ])
                if scenes:
                    doc.section('Tiempos de cada escena')
                    doc.paragraph('Frametime es lo que tarda una imagen en mostrarse: menos milisegundos significa más fluidez. p95 es el tiempo por debajo del cual quedó el 95 % de las imágenes medidas.', size=8, color=MUTED)
                    doc.table([(self._scene_label(row.get('key')), _number(row.get('frames_per_s'), ' FPS', 1) + ' de media · ' + _number(row.get('one_percent_low_fps'), ' FPS', 1) + ' 1 % Low · ' + _number(row.get('frametime_avg_ms'), ' ms', 2) + ' por imagen · p95 ' + _number(row.get('frametime_p95_ms'), ' ms', 2)) for row in scenes[:8]])
                if session.get('warnings'):
                    doc.section('Condiciones observadas')
                    for warning in list(session.get('warnings') or [])[:5]:
                        doc.paragraph(_text(warning, '', 300), size=8, color=MUTED)
        if include_history and history:
            doc.section('Pruebas guardadas recientes')
            rows=[]
            for row in history[:12]:
                summary = row.get('summary') if isinstance(row.get('summary'), dict) else {}
                label = 'Gráfica' if row.get('kind') == 'GPU' else 'Procesador, memoria y disco'
                value = _number(summary.get('gpu_fps'), ' FPS', 1) if row.get('kind') == 'GPU' else _number(summary.get('cpu_ops_s'), ' cálculos/s', 0)
                rows.append((_display_time(row.get('timestamp')), label + ' · ' + value))
            doc.table(rows, label_width_ratio=0.28)
        doc.note('N/A significa que la prueba no entregó esa lectura; no equivale a cero. Los resultados describen esta ejecución y pueden cambiar por la temperatura, las aplicaciones abiertas, Windows y sus cachés.')

    def _build_system_report(self, doc):
        metrics = dict(getattr(self.telemetry, 'metrics', {}) or {})
        health = dict(getattr(self.system_health, 'data', {}) or {})
        diagnostic = dict(getattr(self.system_health, 'diagnostic', {}) or {})
        if diagnostic.get('status') in ('complete', 'partial') and isinstance(diagnostic.get('summary'), dict) and diagnostic['summary']:
            health = diagnostic['summary']
        checks = [row for row in (health.get('checks') or []) if isinstance(row, dict)]
        doc.cards([('Resultado', _state_label(health.get('state')), 'Estado de las lecturas revisadas'),
                   ('Lecturas disponibles', _text(health.get('coverage'), 'N/A', 24), 'Comprobaciones con información')])
        doc.paragraph(_text(health.get('headline'), 'Información insuficiente', 180), size=10, bold=True)
        doc.paragraph('Este informe explica lo que se pudo comprobar. No sustituye una revisión técnica ni garantiza que no existan otros problemas.', size=9, color=MUTED)
        _write_next_steps(doc, checks)
        doc.section('Cómo está el equipo ahora')
        doc.cards([
            ('Uso del procesador', _number(metrics.get('cpuPercent'), '%', 0), _number(metrics.get('cpuTemp'), ' °C', 0)),
            ('Uso de la gráfica', _number(metrics.get('gpuPercent'), '%', 0), _number(metrics.get('gpuTemp'), ' °C', 0)),
            ('Memoria en uso', _number(metrics.get('ramUsed'), ' GiB', 1), 'de ' + _number(metrics.get('ramTotal'), ' GiB', 1)),
            ('Espacio ocupado', _number(metrics.get('diskPercent'), '%', 0), _text(metrics.get('diskLabel'), 'Unidad N/A', 24)),
        ])
        doc.paragraph('Los porcentajes de uso cambian al abrir y cerrar programas: no son porcentajes de salud. GiB es una unidad de capacidad de memoria.', size=8, color=MUTED)
        if checks:
            doc.section('Comprobaciones, explicadas')
            doc.table([(_text(row.get('title'), 'Indicador', 85), _plain_check(row)) for row in checks], label_width_ratio=0.29)
        doc.section('Tu equipo')
        doc.table([
            ('Equipo', _text(metrics.get('computer'))),
            ('Procesador', _text(metrics.get('cpuName'), 'N/A', 180)),
            ('Tarjeta gráfica', _text(metrics.get('gpuName'), 'N/A', 180)),
            ('Memoria RAM total', _number(metrics.get('ramTotal'), ' GiB', 1)),
            ('Encendido desde hace', _text(metrics.get('uptime'))),
        ])
        windows = dict(getattr(self.windows_health, 'data', {}) or {})
        doc.section('Información adicional de Windows', minimum_content=90)
        labels = [('startup', 'Programas que se abren al iniciar'), ('services', 'Servicios de Windows'),
                  ('events', 'Eventos registrados'), ('drivers', 'Dispositivos con errores')]
        for key, label in labels:
            section = windows.get(key) if isinstance(windows.get(key), dict) else {}
            doc.paragraph(label + ': ' + _text(section.get('metric')), size=9, bold=True, gap=3)
            if key == 'events':
                doc.paragraph('Los registros de Windows ayudan a investigar problemas. Su cantidad no equivale a averías confirmadas.', size=8, color=MUTED)
            elif key == 'services':
                doc.paragraph('Un servicio detenido puede ser normal: muchos se activan solo cuando hacen falta.', size=8, color=MUTED)
            names = [_text(item.get('primary'), '', 160) for item in (section.get('items') or [])[:3] if isinstance(item, dict)]
            if names:
                doc.paragraph('Ejemplos: ' + '; '.join(names), size=8, color=MUTED)
        try:
            from core.maintenance.audio_test import evidence_rows, recent_audio_result
            audio = recent_audio_result()
            rows = evidence_rows(audio)
        except Exception:
            audio, rows = {}, []
        doc.section('Prueba de sonido')
        if str(audio.get('status') or 'NO EVALUADO') == 'NO EVALUADO':
            doc.paragraph('No se realizó una prueba de sonido. Esto no indica que exista un problema de audio.', size=9, color=MUTED)
        else:
            doc.table(rows[:8])
        data = self._benchmark_data()
        cpu = data.get('result') if isinstance(data.get('result'), dict) else {}
        gpu = data.get('gpuResult') if isinstance(data.get('gpuResult'), dict) else {}
        doc.section('Pruebas de rendimiento guardadas')
        doc.paragraph('Estos resultados pueden pertenecer a otra fecha. Para métodos, escenas y detalles, genera el informe desde Benchmark.', size=9, color=MUTED)
        saved = []
        if cpu.get('status') == 'complete':
            saved.append(('Procesador, memoria y disco', 'Prueba completada · ' + _display_time(cpu.get('completedAt'))))
        if gpu.get('status') in ('OK', 'PARTIAL') and gpu.get('benchmark_method'):
            scenes, fps, low = self._gpu_summary(gpu)
            saved.append(('Tarjeta gráfica', _number(fps, ' FPS', 1) + ' de media · ' + _number(low, ' FPS', 1) + ' en los fotogramas más lentos (1 % Low)'))
        if saved:
            doc.table(saved)
            doc.paragraph('FPS significa imágenes por segundo. El 1 % Low resume los momentos más lentos de la prueba; aquí se promedian las escenas disponibles.', size=8, color=MUTED)
        else:
            doc.paragraph('No hay pruebas de rendimiento guardadas disponibles.', size=9, color=MUTED)
        ai_state = dict(getattr(self.ai_controller, 'state', {}) or {})
        ai = ai_state.get('diagnostic') if isinstance(ai_state.get('diagnostic'), dict) else {}
        if diagnostic.get('status') in ('complete', 'partial') and int(ai.get('runId') or 0) == int(diagnostic.get('runId') or 0) and ai.get('text'):
            doc.section('Análisis solicitado a CorePulse AI')
            doc.paragraph(_text(ai.get('text'), '', 6000), size=9, color=MUTED)
        doc.note('N/A significa que no se obtuvo un dato verificable: no equivale a cero ni confirma un fallo. Las lecturas de salud corresponden a la última comprobación disponible; las cifras de uso reflejan el momento de creación del informe.')

    @Slot()
    def generate(self):
        if self._data.get("busy"):
            return
        self._set(busy=True, status="Generando informe del equipo…", path="", kind="system")
        try:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            path = self._write(f"CorePulse_Informe_{stamp}.pdf", "Informe del equipo",
                               "Qué se pudo comprobar y qué conviene revisar", self._build_system_report)
            self._set(busy=False, status="Informe del equipo generado.", path=str(path), kind="system")
        except Exception as error:
            self._set(busy=False, status=f"No se generó el informe ({type(error).__name__}: {error}).", path="", kind="system")

    @Slot()
    def generateBenchmark(self):
        if self._data.get("busy"):
            return
        data = self._benchmark_data()
        cpu = data.get("result") if isinstance(data.get("result"), dict) else {}
        gpu = data.get("gpuResult") if isinstance(data.get("gpuResult"), dict) else {}
        history = data.get("history") or []
        if cpu.get("status") != "complete" and gpu.get("status") not in ("OK", "PARTIAL") and not history:
            self._set(status="Ejecuta un benchmark para generar su informe.", path="", kind="benchmark")
            return
        self._set(busy=True, status="Preparando informe de benchmark…", path="", kind="benchmark")

        def build(doc):
            metrics = dict(getattr(self.telemetry, "metrics", {}) or {})
            doc.paragraph("Equipo: " + _text(metrics.get("computer")) + " · CPU: " + _text(metrics.get("cpuName"), "N/A", 100), size=9, color=MUTED)
            doc.paragraph("GPU detectada: " + _text(metrics.get("gpuName"), "N/A", 130), size=9, color=MUTED, gap=9)
            self._append_benchmarks(doc, data)

        try:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            path = self._write(f"CorePulse_Benchmark_{stamp}.pdf", "Informe de benchmark",
                               "CPU, memoria, almacenamiento y GPU · mediciones locales", build)
            self._set(busy=False, status="Informe de benchmark generado.", path=str(path), kind="benchmark")
        except Exception as error:
            self._set(busy=False, status=f"No se generó el informe ({type(error).__name__}: {error}).", path="", kind="benchmark")

    def _build_diagnostic_report(self, doc, diagnostic):
        metrics = dict(getattr(self.telemetry, "metrics", {}) or {})
        summary = diagnostic.get("summary") if isinstance(diagnostic.get("summary"), dict) else {}
        checks = [row for row in (summary.get("checks") or []) if isinstance(row, dict)]
        state = str(summary.get("state") or "partial")
        doc.paragraph("Equipo: " + _text(metrics.get("computer")) + " · Procesador: " + _text(metrics.get("cpuName"), "N/A", 110), size=9, color=MUTED)
        doc.paragraph("GPU: " + _text(metrics.get("gpuName"), "N/A", 130) + " · Diagnóstico local, sin puntuaciones de benchmark.", size=9, color=MUTED, gap=8)
        doc.cards([
            ("Resultado", _state_label(state), "Estado del equipo"),
            ("Lecturas disponibles", _text(summary.get("coverage"), "N/A", 20), "con datos"),
            ("Críticas", _text(summary.get("critical", 0), "0", 12), "requieren atención"),
            ("Por revisar", _text(summary.get("attention", 0), "0", 12), "observaciones")
        ])
        _write_next_steps(doc, checks)
        doc.section("Resumen del diagnóstico")
        doc.table([
            ("Estado de ejecución", "Completo" if diagnostic.get("status") == "complete" else "Parcial"),
            ("Finalizado", _display_time(diagnostic.get("completedAt"))),
            ("Resultado de salud", _text(summary.get("headline"), "Información insuficiente", 120)),
            ("Nota", _text(summary.get("note"), "Las lecturas dependen de las fuentes disponibles en Windows.", 350))
        ])
        doc.section("Indicadores evaluados")
        if checks:
            rows = []
            for row in checks:
                label = _text(row.get("title"), "Indicador", 100)
                value = _text(row.get("value"), "N/A", 100)
                status = _state_label(row.get("state"))
                rows.append((label, _plain_check(row)))
            doc.table(rows, label_width_ratio=0.30)
        else:
            doc.paragraph("La ejecución no recibió indicadores verificables. Los campos ausentes se conservan como N/A.", size=9, color=MUTED)
        ai_state = dict(getattr(self.ai_controller, "state", {}) or {})
        ai_report = ai_state.get("diagnostic") if isinstance(ai_state.get("diagnostic"), dict) else {}
        if int(ai_report.get("runId") or 0) == int(diagnostic.get("runId") or 0):
            if ai_report.get("text"):
                doc.section("Análisis CorePulse AI")
                doc.paragraph(_text(ai_report.get("text"), "", 6000), size=8, color=MUTED, gap=5)
            elif ai_report.get("statusText"):
                doc.section("Estado del análisis con IA")
                doc.paragraph(_text(ai_report.get("statusText"), "", 400), size=8, color=MUTED)
        doc.note("Informe independiente del benchmark. Presenta únicamente las lecturas y comprobaciones disponibles durante esta ejecución. N/A significa que Windows o el dispositivo no proporcionó un dato verificable.")

    @Slot()
    def generateDiagnostic(self):
        if self._data.get("busy"):
            self._set(diagnosticStatus="Hay otro informe en preparación; inténtalo de nuevo en un momento.")
            return
        diagnostic = dict(getattr(self.system_health, "diagnostic", {}) or {})
        if diagnostic.get("status") not in ("complete", "partial"):
            self._set(diagnosticStatus="Ejecuta y termina un diagnóstico antes de generar su informe.", diagnosticPath="")
            return
        run_id = int(diagnostic.get("runId") or 0)
        self._set(busy=True, diagnosticBusy=True, diagnosticStatus="Preparando PDF del diagnóstico…", diagnosticPath="")
        try:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            path = self._write(f"CorePulse_Diagnostico_{stamp}.pdf", "Informe de diagnóstico",
                               "Comprobaciones del equipo y pasos recomendados",
                               lambda doc: self._build_diagnostic_report(doc, diagnostic))
            self._last_diagnostic_run_id = max(self._last_diagnostic_run_id, run_id)
            self._set(busy=False, diagnosticBusy=False, diagnosticStatus="Informe de diagnóstico generado.",
                      diagnosticPath=str(path), diagnosticRunId=run_id)
        except Exception as error:
            self._set(busy=False, diagnosticBusy=False, diagnosticStatus=f"No se generó el PDF del diagnóstico ({type(error).__name__}: {error}).",
                      diagnosticPath="", diagnosticRunId=run_id)

    @Slot()
    def openDiagnostic(self):
        path = str(self._data.get("diagnosticPath") or "")
        if path and Path(path).is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    @Slot()
    def openReportsFolder(self):
        folder = _output_dir()
        try:
            folder.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        except OSError as error:
            self._set(status=f"No se pudo abrir la carpeta de reportes ({type(error).__name__}: {error}).")

    @Slot()
    def openLast(self):
        path = str(self._data.get("path") or "")
        if path and Path(path).is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
