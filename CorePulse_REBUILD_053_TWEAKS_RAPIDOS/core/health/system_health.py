"""Estado general de salud: consolidación de lecturas REALES, sin puntuaciones inventadas.

La cobertura es n/N de indicadores verificables y no representa un porcentaje de salud.
Los límites térmicos/de ocupación son umbrales preventivos de interfaz; no
son diagnósticos del fabricante. Cada fuente conserva su trazabilidad.
"""
from __future__ import annotations

import math

from PySide6.QtCore import QObject, Property, Signal, Slot


def valid_number(value, lower=0, upper=100):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    num = float(value)
    return num if math.isfinite(num) and lower <= num <= upper else None


def build_health_summary(metrics, battery, storage, windows, recovery):
    """Función pura: sin llamadas a Windows ni estimaciones ocultas."""
    metrics = metrics if isinstance(metrics, dict) else {}
    battery = battery if isinstance(battery, dict) else {}
    storage = storage if isinstance(storage, dict) else {}
    windows = windows if isinstance(windows, dict) else {}
    recovery = recovery if isinstance(recovery, dict) else {}
    checks = []

    def add(key, title, value, state, detail, route, source):
        checks.append({'key': key, 'title': title, 'value': value, 'state': state,
                       'detail': detail, 'route': route, 'source': source})

    temp = valid_number(metrics.get('cpuTemp'), 1, 115)
    add('cpu', 'Temperatura CPU', f'{temp:.1f} °C' if temp is not None else 'N/A',
        'critical' if temp is not None and temp >= 95 else 'attention' if temp is not None and temp >= 85 else 'ok' if temp is not None else 'na',
        'Umbrales orientativos: revisar desde 85 °C; prioritario desde 95 °C.' if temp is not None else 'Sensor CPU no disponible o lectura sin confirmar.',
        'cpu', metrics.get('cpuTempSource') or 'N/A')

    temp = valid_number(metrics.get('gpuTemp'), 1, 125)
    add('gpu', 'Temperatura GPU', f'{temp:.1f} °C' if temp is not None else 'N/A',
        'critical' if temp is not None and temp >= 90 else 'attention' if temp is not None and temp >= 80 else 'ok' if temp is not None else 'na',
        'Umbrales orientativos: revisar desde 80 °C; prioritario desde 90 °C.' if temp is not None else 'Lectura térmica de GPU no disponible.',
        'gpu', 'Telemetría de CorePulse / GPU')

    used = valid_number(metrics.get('ramPercent'))
    add('ram', 'Uso de memoria RAM', f'{used:.1f} %' if used is not None else 'N/A',
        'attention' if used is not None and used >= 90 else 'ok' if used is not None else 'na',
        'Uso de memoria elevado; no equivale a un fallo físico.' if used is not None and used >= 90 else 'Porcentaje de RAM ocupada en esta lectura.' if used is not None else 'No hay lectura válida de memoria RAM.',
        'ram', 'psutil / memoria física de Windows')

    disks = storage.get('physical')
    disks = disks if isinstance(disks, list) else []
    known = [d for d in disks if isinstance(d, dict) and d.get('healthKnown') is True and d.get('health') in ('Correcto', 'Advertencia', 'Crítico')]
    all_known = bool(disks) and len(known) == len(disks)
    disk_state = ('critical' if any(d['health'] == 'Crítico' for d in known) else
                  'attention' if any(d['health'] == 'Advertencia' for d in known) else
                  'ok' if all_known else 'na')
    add('disks', 'Estado físico de discos',
        f'{len(known)}/{len(disks)} verificados' if disks else 'N/A', disk_state,
        'Windows informa al menos una unidad con incidencia.' if disk_state in ('critical', 'attention') else
        'Windows Storage confirma el estado de todas las unidades detectadas.' if all_known else
        'No se pudo comprobar el estado físico de todas las unidades.',
        'storage', 'MSFT_PhysicalDisk / Windows Storage')

    volumes = storage.get('volumes')
    volumes = volumes if isinstance(volumes, list) else []
    occupancies = [valid_number(v.get('usedPct')) for v in volumes if isinstance(v, dict)]
    occupancies = [v for v in occupancies if v is not None]
    complete = bool(volumes) and len(occupancies) == len(volumes)
    most_used = max(occupancies) if occupancies else None
    add('space', 'Espacio en unidades', f'{most_used:.1f} % máx.' if most_used is not None else 'N/A',
        'attention' if most_used is not None and most_used >= 90 else 'ok' if complete else 'na',
        'Al menos una unidad supera el 90 % de ocupación.' if most_used is not None and most_used >= 90 else
        'Mayor ocupación entre las unidades locales consultadas.' if complete else
        'No se pudo leer el espacio de todas las unidades.',
        'storage', 'psutil / unidades locales de Windows')

    # La batería no se evalúa en una torre confirmada sin batería.
    if battery.get('hasBattery') is True:
        health = valid_number(battery.get('healthPct'), 0, 150)
        add('battery', 'Salud de batería', f'{health:.1f} %' if health is not None else 'N/A',
            'critical' if health is not None and health < 50 else 'attention' if health is not None and health < 70 else 'ok' if health is not None else 'na',
            'Comparación entre capacidades reales de diseño y carga máxima.' if health is not None else
            'Windows aún no ha proporcionado ambas capacidades.',
            'battery', battery.get('source') or 'Windows / informe de batería')

    drivers = windows.get('drivers')
    drivers = drivers if isinstance(drivers, dict) else {}
    code = drivers.get('metric')
    driver_count = int(code) if drivers.get('available') is True and isinstance(code, str) and code.isdecimal() else None
    add('drivers', 'Dispositivos con problemas', str(driver_count) if driver_count is not None else 'N/A',
        'attention' if driver_count is not None and driver_count > 0 else 'ok' if driver_count == 0 else 'na',
        'Códigos de error PnP, no actualizaciones de drivers pendientes.' if driver_count is not None else
        'Consulta de dispositivos pendiente o no disponible.',
        'windows_health', 'Win32_PnPEntity / CIM')

    winre = recovery.get('recoveryEnv')
    winre_key = str(winre or '').strip().casefold()
    if winre_key in ('activa', 'activo', 'enabled', 'habilitada', 'habilitado'):
        winre_label, status = 'Activo', 'ok'
    elif winre_key in ('desactivada', 'desactivado', 'inactivo', 'inactiva', 'disabled', 'deshabilitada', 'deshabilitado'):
        winre_label, status = 'Inactivo', 'attention'
    else:
        winre_label, status = 'N/A', 'na'
    add('recovery', 'Entorno de recuperación', winre_label, status,
        'Disponibilidad de Windows RE; no indica que exista un respaldo.' if status != 'na' else
        'Windows no confirmó el estado del entorno de recuperación.',
        'restore', 'reagentc /info')

    verified = sum(check['state'] != 'na' for check in checks)
    unknown = len(checks) - verified
    critical = sum(check['state'] == 'critical' for check in checks)
    attention = sum(check['state'] == 'attention' for check in checks)
    if critical:
        headline, state = 'Atención prioritaria', 'critical'
    elif attention:
        headline, state = 'Revisión recomendada', 'attention'
    elif unknown:
        headline, state = 'Sin alertas en lecturas disponibles' if verified else 'Información insuficiente', 'partial'
    else:
        headline, state = 'Sin incidencias detectadas', 'ok'
    return {'headline': headline, 'state': state, 'verified': verified,
            'total': len(checks), 'unknown': unknown, 'critical': critical,
            'attention': attention, 'coverage': f'{verified}/{len(checks)}',
            'checks': checks, 'note': 'Cobertura = lecturas comprobadas; no es un porcentaje de salud. Umbrales preventivos, no diagnósticos oficiales.'}


class SystemHealth(QObject):
    changed = Signal()

    def __init__(self, telemetry, battery, storage, windows, recovery, parent=None):
        super().__init__(parent)
        self.telemetry = telemetry
        self.battery = battery
        self.storage = storage
        self.windows = windows
        self.recovery = recovery
        self._data = build_health_summary(telemetry.metrics, battery.data, storage.data,
                                          windows.data, recovery.data)
        telemetry.metricsChanged.connect(self._rebuild)
        battery.changed.connect(self._rebuild)
        storage.changed.connect(self._rebuild)
        windows.changed.connect(self._rebuild)
        recovery.changed.connect(self._rebuild)

    @Property('QVariantMap', notify=changed)
    def data(self):
        return self._data

    @Slot()
    def _rebuild(self):
        data = build_health_summary(self.telemetry.metrics, self.battery.data,
                                    self.storage.data, self.windows.data, self.recovery.data)
        if data != self._data:
            self._data = data
            self.changed.emit()

    @Slot()
    def refresh(self):
        # Las llamadas a Windows se realizan con trabajadores ya existentes.
        # No se ejecutan reparaciones, cambios del registro ni limpieza.
        self.battery.refresh()
        self.storage.refresh()
        if not self.windows.data.get('busy'):
            self.windows.refresh()
        if not self.recovery.data.get('busy'):
            self.recovery.refresh()
        self._rebuild()

    @Slot()
    def close(self):
        for signal in (self.telemetry.metricsChanged, self.battery.changed,
                       self.storage.changed, self.windows.changed, self.recovery.changed):
            try:
                signal.disconnect(self._rebuild)
            except (RuntimeError, TypeError):
                pass
