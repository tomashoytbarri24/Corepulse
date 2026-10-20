"""Generación local de informes CorePulse con diseño común para todos los PDF."""
from __future__ import annotations

from datetime import datetime
import math
import os
from pathlib import Path
import re
from urllib.parse import quote_plus

from PySide6.QtCore import QObject, Property, Signal, Slot, Qt, QUrl, QMarginsF, QRectF
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

    def section(self, title):
        height = 29
        if self.y + height > self.body_bottom:
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
            self._set_font(8)
            self.painter.drawText(int(x + 11), self.y + 59, _text(card[2] if len(card) > 2 else "", "", 34))
        self.y += 77

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
        cpu = data.get("result") if isinstance(data.get("result"), dict) else {}
        gpu = data.get("gpuResult") if isinstance(data.get("gpuResult"), dict) else {}
        cpu_ok = cpu.get("status") == "complete"
        gpu_ok = gpu.get("status") in ("OK", "PARTIAL") and gpu.get("benchmark_method")
        history = [row for row in (data.get("history") or []) if isinstance(row, dict)]
        if not cpu_ok and not gpu_ok and not (include_history and history):
            doc.paragraph("Aún no hay un benchmark completado guardado en este equipo.", color=MUTED)
            return

        if cpu_ok:
            doc.section("Benchmark CPU · RAM · SSD")
            cpu_row = cpu.get("cpu") if isinstance(cpu.get("cpu"), dict) else {}
            ram_row = cpu.get("ram") if isinstance(cpu.get("ram"), dict) else {}
            disk_row = cpu.get("ssd") if isinstance(cpu.get("ssd"), dict) else {}
            doc.cards([
                ("CPU · iter/s", _number(cpu_row.get("operationsPerSecond"), "", 0), "cálculo entero"),
                ("RAM · MiB/s", _number(ram_row.get("mibPerSecond"), "", 1), "copias verificadas"),
                ("SSD lectura", _number(disk_row.get("readMiBPerSecond"), " MiB/s", 1), "archivo temporal"),
                ("SSD escritura", _number(disk_row.get("writeMiBPerSecond"), " MiB/s", 1), "flush + fsync")
            ])
            doc.table([
                ("Estado y fecha", _text(cpu.get("status"), "N/A") + " · " + _display_time(cpu.get("completedAt"))),
                ("Método CPU", _text(cpu_row.get("method"), "Bucle entero determinista", 240)),
                ("Método RAM", _text(ram_row.get("method"), "Copias verificadas; influido por cachés", 240)),
                ("Método SSD", _text(disk_row.get("method"), "Archivo temporal y lectura verificada", 240)),
                ("Integridad SSD", _text(disk_row.get("integrity"), "N/A"))
            ])

        if gpu_ok:
            doc.section("Benchmark GPU · DirectX 11")
            scenes, average_fps, average_low = self._gpu_summary(gpu)
            session = gpu.get("session") if isinstance(gpu.get("session"), dict) else {}
            doc.cards([
                ("FPS promedio", _number(average_fps, " FPS", 1), "escenas completadas"),
                ("1 % Low", _number(average_low, " FPS", 1), "promedio de escenas"),
                ("Resolución", _text(gpu.get("render_resolution") or gpu.get("resolution"), "N/A", 25), "render fijo"),
                ("Estado", "Completo" if gpu.get("status") == "OK" else "Parcial", _number(gpu.get("duration_s"), " s", 1))
            ])
            profile = _text(gpu.get("profile") or data.get("gpuProfile"), "N/A")
            doc.table([
                ("Adaptador", _text(gpu.get("renderer"), "N/A", 180)),
                ("Perfil y API", profile.title() + " · " + _text(gpu.get("api"), "DirectX 11")),
                ("Feature level", _text(gpu.get("feature_level"), "N/A")),
                ("Modo de pantalla", _text(gpu.get("window_mode"), "N/A")),
                ("Selección de adaptador", _text(gpu.get("adapter_selection_reason") or gpu.get("adapter_selection"), "N/A", 250)),
                ("Temperatura GPU máxima", _number(session.get("gpu_temp_max_c"), " °C", 0)),
                ("Reloj GPU promedio", _number(session.get("gpu_clock_avg_mhz"), " MHz", 0)),
                ("Consumo GPU promedio", _number(session.get("gpu_power_avg_w"), " W", 1)),
                ("Estabilidad observada", _text(session.get("stability"), "N/A")),
                ("Fecha de referencia", _display_time(gpu.get("completedAt") or gpu.get("startedAt")))
            ])
            if scenes:
                doc.bar_chart("FPS promedio por escena", [
                    (self._scene_label(row.get("key")), row.get("frames_per_s"))
                    for row in scenes[:8]
                ])
                doc.paragraph("Resultados detallados por escena", size=9, bold=True, color=INK, gap=4)
                scene_rows = []
                for row in scenes[:8]:
                    details = (
                        _number(row.get("frames_per_s"), " FPS", 1) + " promedio · " +
                        _number(row.get("one_percent_low_fps"), " FPS", 1) + " 1 % Low · " +
                        _number(row.get("frametime_avg_ms"), " ms", 2) + " frametime medio · p95 " +
                        _number(row.get("frametime_p95_ms"), " ms", 2)
                    )
                    scene_rows.append((self._scene_label(row.get("key")), details))
                doc.table(scene_rows, label_width_ratio=0.28)
            if session.get("warnings"):
                doc.paragraph("Condiciones observadas", size=9, bold=True, color=INK, gap=3)
                for warning in list(session.get("warnings") or [])[:5]:
                    doc.paragraph("• " + _text(warning, "", 300), size=8, color=MUTED, indent=8, gap=2)
            if not scenes:
                doc.paragraph("El resultado contiene un resumen válido, pero no conserva detalle por escena.", size=8, color=MUTED)

        if include_history and history:
            doc.section("Sesiones recientes")
            history_rows = []
            for row in history[:12]:
                summary = row.get("summary") if isinstance(row.get("summary"), dict) else {}
                if row.get("kind") == "GPU":
                    description = "GPU · " + _text(row.get("renderer"), "Adaptador N/A", 70) + " · " + _number(summary.get("gpu_fps"), " FPS", 1)
                else:
                    description = "CPU/RAM/SSD · CPU " + _number(summary.get("cpu_ops_s"), " iter/s", 0) + " · RAM " + _number(summary.get("ram_mib_s"), " MiB/s", 1)
                history_rows.append((_display_time(row.get("timestamp")), description + " · " + _text(row.get("status"), "N/A")))
            doc.table(history_rows, label_width_ratio=0.28)
            if len(history) > 12:
                doc.paragraph(f"Se muestran las 12 sesiones más recientes de {len(history)} disponibles.", size=8, color=MUTED)

        doc.note("Los resultados son locales y describen esta ejecución; no son una puntuación universal. Compara GPU solo con el mismo método, perfil, resolución y adaptador. Las tasas de RAM/SSD incluyen los efectos de Windows y la caché.")

    def _build_system_report(self, doc):
        metrics = dict(getattr(self.telemetry, "metrics", {}) or {})
        health = dict(getattr(self.system_health, "data", {}) or {})
        diagnostic = dict(getattr(self.system_health, "diagnostic", {}) or {})
        summary = diagnostic.get("summary") if isinstance(diagnostic.get("summary"), dict) else {}
        if diagnostic.get("status") in ("complete", "partial") and summary:
            health = summary
        windows = dict(getattr(self.windows_health, "data", {}) or {})
        insight = dict(getattr(self.insights, "data", {}) or {})
        doc.paragraph("Instantánea del equipo", size=10, color=MUTED, gap=7)
        doc.cards([
            ("CPU", _number(metrics.get("cpuPercent"), "%", 0), _number(metrics.get("cpuTemp"), " °C", 0)),
            ("GPU", _number(metrics.get("gpuPercent"), "%", 0), _number(metrics.get("gpuTemp"), " °C", 0)),
            ("RAM", _number(metrics.get("ramUsed"), " GiB", 1), "de " + _number(metrics.get("ramTotal"), " GiB", 1)),
            ("Almacenamiento", _number(metrics.get("diskPercent"), "%", 0), _text(metrics.get("diskLabel"), "Unidad N/A", 24))
        ])
        doc.section("Identidad y lecturas actuales")
        doc.table([
            ("Equipo", _text(metrics.get("computer"))),
            ("Procesador", _text(metrics.get("cpuName"), "N/A", 180)),
            ("Frecuencia CPU", _number(metrics.get("cpuGHz"), " GHz", 2)),
            ("Tarjeta gráfica", _text(metrics.get("gpuName"), "N/A", 180)),
            ("VRAM usada / total", _number(metrics.get("gpuVramUsed"), " GiB", 1) + " / " + _number(metrics.get("gpuVramTotal"), " GiB", 1)),
            ("Memoria RAM usada / total", _number(metrics.get("ramUsed"), " GiB", 1) + " / " + _number(metrics.get("ramTotal"), " GiB", 1)),
            ("Unidad de sistema", _text(metrics.get("diskLabel"))),
            ("Tiempo desde inicio", _text(metrics.get("uptime")))
        ])
        doc.section("Estado del sistema")
        doc.cards([("Resultado", _text(health.get("headline"), "Sin evaluar", 24), "Estado del Centro de salud"),
                   ("Cobertura", _text(health.get("coverage"), "N/A", 24), "indicadores verificados")])
        doc.paragraph(_text(health.get("note"), "Los indicadores ausentes se presentan como N/A; una cobertura parcial no confirma un fallo.", 700), size=9, color=MUTED)
        checks = [row for row in (health.get("checks") or []) if isinstance(row, dict)]
        if checks:
            check_rows = []
            for row in checks:
                state = _text(row.get("state"), "N/A").replace("critical", "Crítico").replace("attention", "Revisar").replace("ok", "Correcto")
                check_rows.append((_text(row.get("title"), "Indicador", 85), _text(row.get("value"), "N/A", 180) + " · " + state + " · " + _text(row.get("detail"), "", 180)))
            doc.table(check_rows, label_width_ratio=0.29)

        doc.section("Consultas de Windows")
        doc.paragraph("Actualizado: " + _text(windows.get("lastUpdate")) + ". Los datos dependen de las fuentes disponibles en Windows.", size=8, color=MUTED)
        doc.paragraph("Resumen: hasta cuatro entradas por categoría.", size=8, color=MUTED, gap=4)
        for key, label in (("startup", "Inicio"), ("services", "Servicios"), ("events", "Eventos"), ("drivers", "Dispositivos")):
            section = windows.get(key) if isinstance(windows.get(key), dict) else {}
            doc.paragraph(label + " · " + _text(section.get("metric"), "N/A") + " · " + _text(section.get("caption"), "Consulta no disponible.", 200), size=9, bold=True, gap=3)
            for item in [x for x in (section.get("items") or []) if isinstance(x, dict)][:4]:
                doc.paragraph("• " + _text(item.get("primary"), "N/A", 120) + " — " + _text(item.get("secondary"), "N/A", 180), size=8, color=MUTED, indent=8, gap=2)

        if diagnostic.get("status") in ("complete", "partial"):
            doc.section("Diagnóstico")
            doc.table([("Estado", _text(diagnostic.get("stage"), "Diagnóstico local finalizado.")),
                       ("Fecha", _display_time(diagnostic.get("completedAt")))])
            ai_state = dict(getattr(self.ai_controller, "state", {}) or {})
            ai_report = ai_state.get("diagnostic") if isinstance(ai_state.get("diagnostic"), dict) else {}
            if ai_report.get("text"):
                doc.paragraph("Análisis CorePulse AI autorizado", size=9, bold=True, gap=3)
                doc.paragraph(_text(ai_report.get("text"), "", 6000), size=8, color=MUTED, gap=5)
            elif ai_report.get("statusText"):
                doc.paragraph("CorePulse AI: " + _text(ai_report.get("statusText"), ""), size=8, color=MUTED)
            checks_for_tutorial = [row for row in checks if row.get("state") in ("critical", "attention")]
            if checks_for_tutorial:
                doc.paragraph("Consultas de referencia", size=9, bold=True, gap=3)
                storage_controller = getattr(self.system_health, "storage", None)
                storage_data = dict(getattr(storage_controller, "data", {}) or {})
                selected_volume = storage_data.get("selectedVolume", {})
                selected_physical = storage_data.get("selectedPhysical", {})
                component_names = {
                    "cpu": metrics.get("cpuName") or "CPU",
                    "gpu": metrics.get("gpuName") or "GPU",
                    "ram": "Memoria RAM del equipo",
                    "disks": selected_physical.get("name") or metrics.get("diskName") or "Disco",
                    "space": str(selected_volume.get("mount") or metrics.get("diskLabel") or "Unidad"),
                }
                for row in checks_for_tutorial[:5]:
                    key = str(row.get("key") or "")
                    model = _text(component_names.get(key, row.get("title") or "equipo"), "equipo", 120)
                    if key == "space":
                        match = re.search(r"[A-Z]:\\", str(row.get("value") or row.get("detail") or ""), re.IGNORECASE)
                        if match:
                            model = match.group(0)
                    elif key == "disks":
                        detail = str(row.get("detail") or "")
                        prefix = "Windows informa incidencia en: "
                        if detail.startswith(prefix):
                            model = detail[len(prefix):].split(",", 1)[0].rstrip(".")
                    query = quote_plus(f"{model} {row.get('title') or ''} {row.get('detail') or ''} solucionar")
                    doc.paragraph("• " + model + " · https://www.youtube.com/results?search_query=" + query, size=8, color=BLUE, gap=2)

        try:
            from core.maintenance.audio_test import evidence_rows, recent_audio_result
            audio_result = recent_audio_result()
            audio_evidence = evidence_rows(audio_result)
        except Exception:
            audio_result, audio_evidence = {"status": "NO EVALUADO"}, []
        doc.section("Prueba local de audio")
        doc.paragraph("Estado reciente: " + _text(audio_result.get("status"), "NO EVALUADO") + ". La captura de micrófono no se adjunta al informe.", size=8, color=MUTED)
        if audio_evidence:
            doc.table([(label, value) for label, value in audio_evidence[:8]])
        else:
            doc.paragraph("No hay evidencia reciente disponible.", size=8, color=MUTED)

        samples = insight.get("samples") or []
        doc.section("Tendencias y benchmarks")
        doc.paragraph(f"Muestras locales recientes: {len(samples)}. Se almacenan en este equipo y no se envían con el informe.", size=8, color=MUTED)
        self._append_benchmarks(doc, self._benchmark_data())
        doc.note("Fuentes: telemetría local de CorePulse, estado de Windows y resultados guardados de benchmark. N/A significa que una fuente no proporcionó una lectura verificable; no equivale a cero ni confirma una avería.")

    @Slot()
    def generate(self):
        if self._data.get("busy"):
            return
        self._set(busy=True, status="Preparando informe profesional…", path="", kind="system")
        try:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            path = self._write(f"CorePulse_Informe_{stamp}.pdf", "Informe del equipo",
                               "Resumen de hardware, salud, Windows y resultados locales", self._build_system_report)
            self._set(busy=False, status="Informe profesional generado.", path=str(path), kind="system")
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
        state_names = {"ok": "Correcto", "attention": "Revisar", "critical": "Crítico", "partial": "Parcial", "unknown": "Sin datos"}
        state = str(summary.get("state") or "partial")
        doc.paragraph("Equipo: " + _text(metrics.get("computer")) + " · Procesador: " + _text(metrics.get("cpuName"), "N/A", 110), size=9, color=MUTED)
        doc.paragraph("GPU: " + _text(metrics.get("gpuName"), "N/A", 130) + " · Diagnóstico local, sin puntuaciones de benchmark.", size=9, color=MUTED, gap=8)
        doc.cards([
            ("Resultado", state_names.get(state, _text(summary.get("headline"), "Parcial", 24)), "Estado del equipo"),
            ("Cobertura", _text(summary.get("coverage"), "N/A", 20), "indicadores revisados"),
            ("Críticas", _text(summary.get("critical", 0), "0", 12), "requieren atención"),
            ("Por revisar", _text(summary.get("attention", 0), "0", 12), "observaciones")
        ])
        doc.section("Resumen del diagnóstico")
        doc.table([
            ("Estado de ejecución", "Completo" if diagnostic.get("status") == "complete" else "Parcial"),
            ("Finalizado", _display_time(diagnostic.get("completedAt"))),
            ("Resultado de salud", _text(summary.get("headline"), "Información insuficiente", 120)),
            ("Cobertura verificada", _text(summary.get("coverage"), "N/A", 50)),
            ("CPU", _text(metrics.get("cpuName"), "N/A", 150)),
            ("GPU", _text(metrics.get("gpuName"), "N/A", 150)),
            ("Temperatura CPU", _number(metrics.get("cpuTemp"), " °C", 1)),
            ("Temperatura GPU", _number(metrics.get("gpuTemp"), " °C", 1)),
            ("Tiempo activo", _text(metrics.get("uptime"), "N/A", 50)),
            ("Nota", _text(summary.get("note"), "Las lecturas dependen de las fuentes disponibles en Windows.", 350))
        ])
        doc.section("Indicadores evaluados")
        if checks:
            rows = []
            for row in checks:
                label = _text(row.get("title"), "Indicador", 100)
                value = _text(row.get("value"), "N/A", 100)
                status = state_names.get(str(row.get("state") or ""), _text(row.get("state"), "Sin datos", 24))
                detail = _text(row.get("detail"), "", 220)
                rows.append((label, value + " · " + status + (" · " + detail if detail else "")))
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
                               "Estado local del equipo · indicadores y cobertura verificable",
                               lambda doc: self._build_diagnostic_report(doc, diagnostic))
            self._last_diagnostic_run_id = max(self._last_diagnostic_run_id, run_id)
            self._set(busy=False, diagnosticBusy=False, diagnosticStatus="PDF propio del diagnóstico generado.",
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
