"""Limpieza de temporales y RAM de Windows con mediciones verificables.
La operación manual profunda puede recortar conjuntos de trabajo de procesos.
"""
from __future__ import annotations

import ctypes
import gc
from contextlib import contextmanager
import os
import subprocess
from pathlib import Path
import tempfile
import time
from concurrent.futures.thread import ThreadPoolExecutor

import psutil
from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot
from .storage_cleanup import delete_scanned_candidates, scan_duplicates, scan_safe_storage_cleanup


MAX_FILES = 120000
MIN_AGE_SECONDS = 24 * 3600


def user_temp_root() -> Path:
    """Solamente directorio temporal de usuario, nunca el directorio Temp del sistema."""
    candidate = Path(tempfile.gettempdir()).resolve()
    user = Path.home().resolve()
    # Temp suele estar bajo AppData\Local\Temp; impedir rutas arbitrarias.
    if os.name != "nt" or str(candidate) == candidate.anchor or candidate == user:
        raise OSError("Ruta de temporales no compatible")
    local = os.environ.get("LOCALAPPDATA", "")
    if not local or not candidate.is_relative_to(Path(local).resolve()):
        raise OSError("La carpeta temporal no pertenece al perfil local del usuario")
    return candidate


def scan_temps(root: Path, *, now=None):
    """Lista limitada de archivos antiguos sin atravesar enlaces a otras carpetas."""
    now = time.time() if now is None else now
    root = root.resolve()
    found = []
    count = 0
    for folder, dirs, filenames in os.walk(root, topdown=True, followlinks=False):
        dirs[:] = [d for d in dirs if not (Path(folder)/d).is_symlink()]
        for name in filenames:
            count += 1
            if count > MAX_FILES:
                raise RuntimeError("Demasiados archivos; se canceló la exploración para evitar un análisis incompleto")
            path = Path(folder)/name
            try:
                if path.is_symlink() or not path.resolve().is_relative_to(root):
                    continue
                stat = path.stat()
                if stat.st_mtime > now - MIN_AGE_SECONDS:
                    continue
                found.append((path, stat.st_size, stat.st_mtime))
            except OSError:
                continue
    return found


def clean_temps(root: Path):
    """Revalida edad/ruta/tamaño al eliminar; archivos bloqueados se omiten."""
    root = root.resolve()
    candidates = scan_temps(root)
    removed = 0
    bytes_removed = 0
    skipped = 0
    for path, size, original_mtime in candidates:
        try:
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                skipped += 1; continue
            stat = path.stat()
            if stat.st_mtime != original_mtime or stat.st_size != size or stat.st_mtime > time.time()-MIN_AGE_SECONDS:
                skipped += 1; continue
            path.unlink()
            removed += 1
            bytes_removed += size
        except OSError:
            skipped += 1
    remaining = scan_temps(root)
    return {"removed": removed, "bytes": bytes_removed, "skipped": skipped,
            "remaining": len(remaining), "remaining_bytes": sum(item[1] for item in remaining)}


# Únicamente cachés regenerables del perfil actual. No navegar Descargas,
# perfiles de navegador, ni datos personales o instalaciones del sistema.
def user_cache_locations():
    if os.name != "nt":
        raise OSError("Limpieza de caché disponible solo en Windows")
    raw = os.environ.get("LOCALAPPDATA", "")
    if not raw:
        raise OSError("Windows no informó LOCALAPPDATA")
    local = Path(raw).resolve()
    if local == Path(local.anchor) or local == Path.home().resolve():
        raise OSError("Carpeta de caché insegura")
    return [
        (local / "D3DSCache", None),
        (local / "NVIDIA" / "DXCache", None),
        (local / "NVIDIA" / "GLCache", None),
        (local / "AMD" / "DxCache", None),
        (local / "Microsoft" / "Windows" / "Explorer", "thumbcache_"),
    ]


def scan_user_cache(locations=None):
    """Inventario real de caché de shaders/miniaturas sin seguir enlaces.

    Devuelve (ruta, bytes, mtime_ns, raíz) para poder revalidar en limpieza.
    """
    locations = user_cache_locations() if locations is None else locations
    found = []
    inspected = 0
    for location, prefix in locations:
        root = Path(location)
        if not root.exists() or root.is_symlink() or (hasattr(root, 'is_junction') and root.is_junction()):
            continue
        root = root.resolve()
        if not root.is_dir():
            continue
        for folder, dirs, filenames in os.walk(root, topdown=True, followlinks=False):
            dirs[:] = [d for d in dirs if not ((Path(folder) / d).is_symlink() or
                       (hasattr(Path(folder) / d, 'is_junction') and (Path(folder) / d).is_junction()))]
            for name in filenames:
                inspected += 1
                if inspected > MAX_FILES:
                    raise RuntimeError("Caché demasiado grande: análisis interrumpido, no se ha borrado nada")
                if prefix is not None and not name.lower().startswith(prefix):
                    continue
                path = Path(folder) / name
                try:
                    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
                        continue
                    stat = path.stat()
                    found.append((path, stat.st_size, stat.st_mtime_ns, root))
                except OSError:
                    continue
    return found


def clean_user_cache(locations=None):
    """Borra solo archivos del inventario regenerable; revalida para evitar TOCTOU.

    No elimina carpetas, enlaces, perfiles del navegador ni archivos bloqueados.
    """
    candidates = scan_user_cache(locations)
    removed = skipped = bytes_removed = 0
    for path, size, mtime_ns, root in candidates:
        try:
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                skipped += 1
                continue
            stat = path.stat()
            if not path.is_file() or stat.st_size != size or stat.st_mtime_ns != mtime_ns:
                skipped += 1
                continue
            path.unlink()
            removed += 1
            bytes_removed += size
        except OSError:
            skipped += 1
    remaining = scan_user_cache(locations)
    return {"removed": removed, "bytes": bytes_removed, "skipped": skipped,
            "remaining": len(remaining), "remaining_bytes": sum(r[1] for r in remaining)}


def recycle_bin_info():
    """Consulta tamaño y cantidad REAL de elementos de Papelera (Shell32)."""
    if os.name != 'nt':
        raise OSError("Papelera disponible solo en Windows")
    from ctypes import wintypes

    class SHQUERYRBINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("i64Size", ctypes.c_longlong),
                    ("i64NumItems", ctypes.c_longlong)]

    shell = ctypes.WinDLL('shell32', use_last_error=True)
    query = shell.SHQueryRecycleBinW
    query.argtypes = (wintypes.LPCWSTR, ctypes.POINTER(SHQUERYRBINFO))
    query.restype = ctypes.c_long
    info = SHQUERYRBINFO()
    info.cbSize = ctypes.sizeof(info)
    hresult = ctypes.c_uint32(query(None, ctypes.byref(info))).value
    if hresult:
        raise OSError(f"Windows no pudo consultar la Papelera (HRESULT 0x{hresult:08X})")
    return {"count": int(info.i64NumItems), "bytes": int(info.i64Size)}


def empty_recycle_bin():
    """Vacía la Papelera solamente tras confirmación explícita de la interfaz."""
    before = recycle_bin_info()
    if before['count'] == 0:
        return {"before": before, "after": before, "emptied": 0}
    from ctypes import wintypes
    shell = ctypes.WinDLL('shell32', use_last_error=True)
    empty = shell.SHEmptyRecycleBinW
    empty.argtypes = (wintypes.HWND, wintypes.LPCWSTR, wintypes.DWORD)
    empty.restype = ctypes.c_long
    # El diálogo de la app ya solicitó consentimiento; sin popup Shell adicional.
    flags = 0x00000001 | 0x00000002 | 0x00000004
    hresult = ctypes.c_uint32(empty(None, None, flags)).value
    if hresult:
        raise OSError(f"Windows rechazó vaciar la Papelera (HRESULT 0x{hresult:08X})")
    after = recycle_bin_info()
    return {"before": before, "after": after,
            "emptied": max(0, before['count'] - after['count'])}


def flush_dns_cache():
    """Solicita a ipconfig vaciar la caché DNS; sin cifras ficticias en MB."""
    if os.name != 'nt':
        raise OSError("Caché DNS disponible solo en Windows")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    result = subprocess.run(["ipconfig", "/flushdns"], capture_output=True,
                            text=True, errors="replace", timeout=20,
                            creationflags=flags)
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "sin detalle del sistema").strip()
        raise RuntimeError(f"Windows rechazó la limpieza DNS: {message[:240]}")
    return {"accepted": True}  # Windows confirmó la solicitud, no un número de MB.


@contextmanager
def standby_privilege():
    """Activa temporalmente SeProfileSingleProcessPrivilege en el token actual.

    AdjustTokenPrivileges NO concede un derecho inexistente: se comprueba
    ERROR_NOT_ALL_ASSIGNED y se restaura exactamente el estado anterior.
    """
    if os.name != "nt":
        raise OSError("Solo Windows")
    from ctypes import wintypes

    TOKEN_ADJUST_PRIVILEGES = 0x0020
    TOKEN_QUERY = 0x0008
    SE_PRIVILEGE_ENABLED = 0x00000002
    ERROR_NOT_ALL_ASSIGNED = 1300

    class LUID(ctypes.Structure):
        _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]

    class LUID_AND_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("Luid", LUID), ("Attributes", wintypes.DWORD)]

    class TOKEN_PRIVILEGES(ctypes.Structure):
        _fields_ = [("PrivilegeCount", wintypes.DWORD), ("Privileges", LUID_AND_ATTRIBUTES * 1)]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    get_process = kernel32.GetCurrentProcess
    get_process.restype = wintypes.HANDLE
    open_token = advapi.OpenProcessToken
    open_token.argtypes = (wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE))
    open_token.restype = wintypes.BOOL
    lookup = advapi.LookupPrivilegeValueW
    lookup.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.POINTER(LUID))
    lookup.restype = wintypes.BOOL
    adjust = advapi.AdjustTokenPrivileges
    adjust.argtypes = (wintypes.HANDLE, wintypes.BOOL, ctypes.POINTER(TOKEN_PRIVILEGES),
                       wintypes.DWORD, ctypes.POINTER(TOKEN_PRIVILEGES), ctypes.POINTER(wintypes.DWORD))
    adjust.restype = wintypes.BOOL
    close = kernel32.CloseHandle
    close.argtypes = (wintypes.HANDLE,)
    close.restype = wintypes.BOOL

    token = wintypes.HANDLE()
    if not open_token(get_process(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, ctypes.byref(token)):
        raise PermissionError(f"No se pudo abrir el token de Windows (WinError {ctypes.get_last_error()})")
    previous = TOKEN_PRIVILEGES()
    try:
        luid = LUID()
        if not lookup(None, "SeProfileSingleProcessPrivilege", ctypes.byref(luid)):
            raise PermissionError(f"No se encontró el privilegio de perfilado (WinError {ctypes.get_last_error()})")
        desired = TOKEN_PRIVILEGES()
        desired.PrivilegeCount = 1
        desired.Privileges[0] = LUID_AND_ATTRIBUTES(luid, SE_PRIVILEGE_ENABLED)
        returned = wintypes.DWORD()
        ctypes.set_last_error(0)
        if not adjust(token, False, ctypes.byref(desired), ctypes.sizeof(previous),
                      ctypes.byref(previous), ctypes.byref(returned)):
            raise PermissionError(f"No se pudo habilitar el privilegio (WinError {ctypes.get_last_error()})")
        if ctypes.get_last_error() == ERROR_NOT_ALL_ASSIGNED:
            raise PermissionError("Windows no asignó SeProfileSingleProcessPrivilege a este proceso; "
                                  "comprueba la elevación y la directiva de seguridad")
        try:
            yield
        finally:
            if returned.value:
                if not adjust(token, False, ctypes.byref(previous), 0, None, None):
                    raise PermissionError(f"No se pudo restaurar el privilegio original (WinError {ctypes.get_last_error()})")
    finally:
        close(token)


def purge_standby():
    """NtSetSystemInformation(SystemMemoryListInformation, MemoryPurgeStandbyList).

    El kernel decide qué páginas recuperables liberar. No vacía RAM activa ni
    garantiza un porcentaje de liberación. Exige privilegios de Windows.
    """
    if os.name != "nt":
        raise OSError("Solo Windows")
    before = psutil.virtual_memory()
    ntdll = ctypes.WinDLL("ntdll")
    fn = ntdll.NtSetSystemInformation
    fn.argtypes = [ctypes.c_ulong, ctypes.c_void_p, ctypes.c_ulong]
    fn.restype = ctypes.c_long
    operation = ctypes.c_int(4)  # MemoryPurgeStandbyList
    with standby_privilege():
        status = fn(80, ctypes.byref(operation), ctypes.sizeof(operation))
    if status != 0:
        code = ctypes.c_uint32(status).value
        raise PermissionError(f"Windows rechazó la purga standby (NTSTATUS 0x{code:08X}); el token puede carecer de permisos o una política puede bloquearlo")
    time.sleep(0.5)
    after = psutil.virtual_memory()
    return {"before": int(before.available), "after": int(after.available),
            "delta": int(after.available-before.available), "total": int(after.total)}



def optimize_ram_deep():
    """Acción manual intensiva del motor V485: trim externo y listas de Windows.

    Todas las operaciones se registran individualmente. Una reducción observada
    de RAM disponible no es una cifra causal atribuible a la operación.
    """
    if os.name != "nt":
        raise OSError("La limpieza profunda está disponible únicamente en Windows")
    if not ctypes.windll.shell32.IsUserAnAdmin():
        raise PermissionError("La limpieza profunda requiere ejecutar CorePulse como administrador")
    from ctypes import wintypes
    before = psutil.virtual_memory()
    results = {}
    gc.collect()
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    psapi.EmptyWorkingSet.argtypes = (wintypes.HANDLE,)
    psapi.EmptyWorkingSet.restype = wintypes.BOOL
    trimmed = failed = 0
    for proc in psutil.process_iter(['pid']):
        pid = int(proc.info.get('pid') or 0)
        if pid in (0, 4):
            continue
        handle = kernel.OpenProcess(0x0400 | 0x0100, False, pid)
        if not handle:
            failed += 1
            continue
        try:
            if psapi.EmptyWorkingSet(handle):
                trimmed += 1
            else:
                failed += 1
        finally:
            kernel.CloseHandle(handle)
    results['working_sets'] = {'ok': trimmed > 0, 'trimmed': trimmed, 'skipped': failed}
    ntdll = ctypes.WinDLL('ntdll')
    fn = ntdll.NtSetSystemInformation
    fn.argtypes = (ctypes.c_ulong, ctypes.c_void_p, ctypes.c_ulong)
    fn.restype = ctypes.c_long
    for key, cmd in [('system_working_sets', 2), ('modified_pages', 3),
                     ('low_priority_standby', 5), ('standby', 4)]:
        try:
            with standby_privilege():
                operation = ctypes.c_int(cmd)
                status = ctypes.c_uint32(fn(80, ctypes.byref(operation), ctypes.sizeof(operation))).value
            results[key] = {'ok': status == 0, 'ntstatus': f'0x{status:08X}'}
        except (OSError, PermissionError) as exc:
            results[key] = {'ok': False, 'error': str(exc)}
    # La caché de archivos es otra operación independiente; no alterar los
    # límites persistentes de caché. Si falta el derecho, informar el fallo.
    try:
        with windows_privilege('SeIncreaseQuotaPrivilege'):
            flush = kernel.SetSystemFileCacheSize
            flush.argtypes = (ctypes.c_size_t, ctypes.c_size_t, wintypes.DWORD)
            flush.restype = wintypes.BOOL
            max_size = ctypes.c_size_t(-1).value
            ok = bool(flush(max_size, max_size, 0))
            results['file_cache'] = {'ok': ok, 'winerror': ctypes.get_last_error() if not ok else 0}
    except (OSError, PermissionError) as exc:
        results['file_cache'] = {'ok': False, 'error': str(exc)}
    time.sleep(0.75)
    after = psutil.virtual_memory()
    return {'before': int(before.available), 'after': int(after.available),
            'delta': int(after.available-before.available), 'results': results,
            'completed': sum(bool(v['ok']) for v in results.values()),
            'attempted': len(results), 'trimmed': trimmed, 'skipped': failed}


@contextmanager
def windows_privilege(name):
    """Habilita un privilegio existente y restaura sus atributos originales."""
    if os.name != 'nt':
        raise OSError('Solo Windows')
    from ctypes import wintypes
    class LUID(ctypes.Structure):
        _fields_ = [('LowPart', wintypes.DWORD), ('HighPart', wintypes.LONG)]
    class ENTRY(ctypes.Structure):
        _fields_ = [('Luid', LUID), ('Attributes', wintypes.DWORD)]
    class PRIVS(ctypes.Structure):
        _fields_ = [('PrivilegeCount', wintypes.DWORD), ('Privileges', ENTRY*1)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    advapi.OpenProcessToken.argtypes = (wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE))
    advapi.OpenProcessToken.restype = wintypes.BOOL
    advapi.LookupPrivilegeValueW.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.POINTER(LUID))
    advapi.LookupPrivilegeValueW.restype = wintypes.BOOL
    advapi.AdjustTokenPrivileges.argtypes = (wintypes.HANDLE,wintypes.BOOL,ctypes.POINTER(PRIVS),wintypes.DWORD,ctypes.POINTER(PRIVS),ctypes.POINTER(wintypes.DWORD))
    advapi.AdjustTokenPrivileges.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    token = wintypes.HANDLE()
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 0x28, ctypes.byref(token)):
        raise PermissionError(f'OpenProcessToken: {ctypes.get_last_error()}')
    previous=PRIVS(); previous_size=wintypes.DWORD()
    try:
        luid=LUID()
        if not advapi.LookupPrivilegeValueW(None, name, ctypes.byref(luid)):
            raise PermissionError(f'{name} no encontrado')
        desired=PRIVS(1,(ENTRY*1)(ENTRY(luid, 2)))
        ctypes.set_last_error(0)
        if not advapi.AdjustTokenPrivileges(token,False,ctypes.byref(desired),ctypes.sizeof(previous),ctypes.byref(previous),ctypes.byref(previous_size)) or ctypes.get_last_error()==1300:
            raise PermissionError(f'{name} no concedido por Windows')
        try:
            yield
        finally:
            if previous_size.value:
                if not advapi.AdjustTokenPrivileges(token,False,ctypes.byref(previous),0,None,None):
                    raise PermissionError(f'No se pudo restaurar {name}')
    finally:
        kernel.CloseHandle(token)

def human_bytes(n):
    return f"{n / 1024**2:,.1f} MB" if abs(n) < 1024**3 else f"{n / 1024**3:,.2f} GB"


def ram_usage_snapshot():
    """Una sola lectura real de RAM física para total, disponible y ocupada.

    Ocupada = total - disponible, incluyendo memoria no recuperable al instante.
    Vaciar standby NO garantiza reducir esta cifra; otras aplicaciones también
    pueden cambiarla mientras se ejecuta la limpieza.
    """
    reading = psutil.virtual_memory()
    total, available = int(reading.total), int(reading.available)
    if total <= 0 or available < 0 or available > total:
        raise ValueError("Lectura física de RAM no válida")
    used = total - available
    return {"total": total, "available": available, "used": used,
            "percent": round(used * 100.0 / total, 1)}


class CleanupManager(QObject):
    changed = Signal()
    trayNotification = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = {"busy": False, "status": "Listo para analizar", "found": 0,
                      "size": "N/A", "ramBefore": "N/A", "ramAfter": "N/A", "ramChange": "N/A", "deepBefore": "N/A", "deepAfter": "N/A", "deepChange": "N/A", "deepDetail": "Sin ejecutar", "lastRamKind": "", "resultSequence": 0, "resultSuccess": False, "resultPartial": False, "resultKind": "",
                      "ramMeterActive": False, "ramUiFeedback": True, "ramMeterValid": False,
                      "ramMeterUsed": "N/A", "ramMeterStart": "N/A", "ramMeterTotal": "N/A",
                      "ramMeterAvailable": "N/A", "ramMeterDelta": "N/A", "ramMeterPercent": None,
                      "ramMeterSamples": 0,
                      "cacheFound": 0, "cacheSize": "Sin analizar", "cacheAnalyzed": False,
                      "cacheStatus": "Caché sin analizar",
                      "recycleFound": 0, "recycleSize": "Sin consultar", "recycleAnalyzed": False,
                      "recycleStatus": "Papelera sin consultar",
                      "dnsStatus": "Listo para vaciar DNS",
                      "storageFound": 0, "storageSize": "Sin analizar",
                      "storageAnalyzed": False, "storageStatus": "Almacenamiento sin analizar",
                      "duplicateFolder": "", "duplicateFiles": 0, "duplicateGroups": 0,
                      "duplicateWasted": "Sin analizar", "duplicateStatus": "Selecciona una carpeta",
                      "duplicatePreview": ""}
        self._meter_first_used = None
        self._meter_last_read = 0.0
        self._active_kind = ""
        self._tray_operation = False
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="corepulse-cleanup")
        self._future = None
        self._storage_scan = None
        self._duplicate_scan = None
        self._timer = QTimer(self)
        self._timer.setInterval(140)
        self._timer.timeout.connect(self._check)

    @Property('QVariantMap', notify=changed)
    def data(self):
        return dict(self._data)

    def _sample_ram_meter(self, *, force=False):
        """Lectura periódica en hilo Qt; N/A si Windows no ofrece datos válidos.

        Un QTimer ya existente sondea un Future en segundo plano. No se fabrica
        una progresión ni un porcentaje de limpieza, solo uso RAM observado.
        """
        if self._active_kind not in ("ram", "ram_deep", "ram_safe"):
            return
        now = time.monotonic()
        if not force and now - self._meter_last_read < 0.28:
            return
        self._meter_last_read = now
        try:
            sample = ram_usage_snapshot()
        except Exception:
            # Fallo de telemetría independiente de la operación de limpieza.
            self._data.update(ramMeterValid=False, ramMeterUsed="N/A",
                              ramMeterAvailable="N/A", ramMeterPercent=None,
                              ramMeterDelta="N/A")
            self.changed.emit()
            return
        if self._meter_first_used is None:
            self._meter_first_used = sample["used"]
        difference = self._meter_first_used - sample["used"]
        self._data.update(ramMeterValid=True, ramMeterPercent=sample["percent"],
                          ramMeterUsed=human_bytes(sample["used"]),
                          ramMeterTotal=human_bytes(sample["total"]),
                          ramMeterAvailable=human_bytes(sample["available"]),
                          ramMeterStart=human_bytes(self._meter_first_used),
                          ramMeterDelta=("+" if difference >= 0 else "") + human_bytes(difference),
                          ramMeterSamples=self._data["ramMeterSamples"] + 1)
        self.changed.emit()

    def _start(self, label, fn, *, kind="", ram_ui_feedback=True, tray_operation=False):
        if self._future is not None:
            return False
        self._active_kind = kind
        self._tray_operation = bool(tray_operation)
        self._meter_first_used = None
        self._meter_last_read = 0.0
        self._data.update(busy=True, status=label,
                          ramMeterActive=(kind in ("ram", "ram_deep", "ram_safe") and ram_ui_feedback),
                          ramUiFeedback=bool(ram_ui_feedback),
                          ramMeterValid=False, ramMeterPercent=None,
                          ramMeterUsed="N/A", ramMeterStart="N/A", ramMeterTotal="N/A",
                          ramMeterAvailable="N/A", ramMeterDelta="N/A", ramMeterSamples=0)
        if self._data["ramMeterActive"]:
            self._sample_ram_meter(force=True)
        self.changed.emit()
        self._future = self._pool.submit(fn)
        self._timer.start()
        return True

    def _check(self):
        if not self._future:
            return
        if not self._future.done():
            self._sample_ram_meter()
            return
        self._sample_ram_meter(force=True)
        future = self._future
        self._future = None
        self._timer.stop()
        # Conservar la clase de operación incluso si Future.result() lanza.
        # Sin esto, una limpieza fallida cerraba el medidor sin mostrar error.
        kind = self._active_kind
        succeeded = False
        partially_completed = False
        try:
            kind, result = future.result()
            if kind == 'scan':
                self._data.update(found=len(result), size=human_bytes(sum(item[1] for item in result)),
                                  status=f"Análisis terminado: {len(result)} archivos temporales antiguos")
            elif kind == 'clean':
                self._data.update(found=result['remaining'], size=human_bytes(result['remaining_bytes']), status=(
                    f"Eliminados {result['removed']} archivos ({human_bytes(result['bytes'])}). "
                    f"Omitidos: {result['skipped']}."))
            elif kind == 'cache_scan':
                self._data.update(cacheFound=len(result), cacheSize=human_bytes(sum(i[1] for i in result)),
                                  cacheAnalyzed=True, cacheStatus=f"Caché analizada: {len(result)} archivos")
            elif kind == 'cache_clean':
                self._data.update(cacheFound=result['remaining'], cacheSize=human_bytes(result['remaining_bytes']),
                                  cacheAnalyzed=True, cacheStatus=(
                                      f"Eliminados {result['removed']} · Omitidos {result['skipped']}"))
            elif kind == 'recycle_scan':
                self._data.update(recycleFound=result['count'], recycleSize=human_bytes(result['bytes']),
                                  recycleAnalyzed=True, recycleStatus=f"{result['count']} elementos encontrados")
            elif kind == 'recycle_empty':
                remaining = result['after']
                self._data.update(recycleFound=remaining['count'], recycleSize=human_bytes(remaining['bytes']),
                                  recycleAnalyzed=True, recycleStatus=f"Vaciados {result['emptied']} elementos; restantes {remaining['count']}")
            elif kind == 'storage_scan':
                self._storage_scan = result
                categories = [row for row in result.get('categories', []) if int(row.get('bytes') or 0) > 0]
                category_text = ' · '.join(str(row.get('label') or '') for row in categories[:3])
                self._data.update(storageFound=int(result.get('total_files') or 0),
                                  storageSize=human_bytes(int(result.get('total_bytes') or 0)),
                                  storageAnalyzed=True,
                                  storageStatus=(f"{int(result.get('units_scanned') or 0)} unidades · "
                                                 f"{int(result.get('total_files') or 0)} archivos elegibles"
                                                 + (f" · {category_text}" if category_text else " · Nada que limpiar")))
            elif kind == 'storage_clean':
                self._storage_scan = result.get('after') or None
                deleted = int(result.get('deleted_files') or 0)
                skipped = int(result.get('skipped') or 0)
                bytes_deleted = int(result.get('deleted_bytes') or 0)
                delta = result.get('free_space_delta_bytes')
                measure = (f"Espacio libre medido: {human_bytes(int(delta))}" if delta is not None
                           else "Espacio libre final: N/A")
                self._data.update(storageFound=int((self._storage_scan or {}).get('total_files') or 0),
                                  storageSize=human_bytes(int((self._storage_scan or {}).get('total_bytes') or 0)),
                                  storageAnalyzed=True,
                                  storageStatus=(f"Eliminados {deleted} archivos ({human_bytes(bytes_deleted)}); "
                                                 f"omitidos {skipped}. {measure}"))
                succeeded = deleted > 0 or skipped == 0
            elif kind == 'duplicates_scan':
                self._duplicate_scan = result
                preview = []
                for index, group in enumerate(result.get('groups', [])[:10], 1):
                    files = group.get('files') or []
                    preview.append(f"Grupo {index} · {human_bytes(int(group.get('size') or 0))} × {len(files)}")
                    preview.extend(f"  {path}" for path in files[:2])
                    if len(files) > 2:
                        preview.append(f"  y {len(files) - 2} más")
                self._data.update(duplicateFolder=str(result.get('folder') or ""),
                                  duplicateFiles=int(result.get('duplicate_files') or 0),
                                  duplicateGroups=len(result.get('groups') or []),
                                  duplicateWasted=human_bytes(int(result.get('wasted_bytes') or 0)),
                                  duplicateStatus=(f"{int(result.get('scanned_files') or 0)} archivos comprobados "
                                                   f"por SHA-256 · {int(result.get('errors') or 0)} omitidos"),
                                  duplicatePreview="\n".join(preview) if preview else "No se encontraron copias idénticas.")
            elif kind == 'dns_flush':
                self._data['dnsStatus'] = 'Caché DNS vaciada · Windows confirmó la operación'
            elif kind == 'ram_deep':
                succeeded = result['attempted'] > 0 and result['completed'] == result['attempted']
                partially_completed = 0 < result['completed'] < result['attempted']
                if succeeded or partially_completed:
                    self._data["lastRamKind"] = "ram_deep"
                detail = ', '.join(f'{name}: {"OK" if value["ok"] else "no disponible"}' for name,value in result['results'].items())
                self._data.update(deepBefore=human_bytes(result['before']), deepAfter=human_bytes(result['after']),
                                  deepChange=('+' if result['delta']>=0 else '') + human_bytes(result['delta']),
                                  deepDetail=f'{result["completed"]}/{result["attempted"]} operaciones; {result["trimmed"]} procesos recortados; {result["skipped"]} omitidos',
                                  status=f'Limpieza profunda: {detail}. Cambio medido: {human_bytes(result["delta"])} (no atribuible exclusivamente).')
            elif kind == 'ram_safe':
                succeeded = True
                self._data["lastRamKind"] = "ram_safe"
                self._data.update(ramBefore=human_bytes(result['before']), ramAfter=human_bytes(result['after']),
                                  ramChange=(('+' if result['delta'] >= 0 else '') + human_bytes(result['delta'])),
                                  status=(f"Optimización normal completada; {result['collected']} objetos de CorePulse recogidos. "
                                          "El cambio de RAM es una lectura, no una cifra atribuible."))
            elif kind == 'ram':
                succeeded = True
                self._data["lastRamKind"] = "ram"
                self._data.update(ramBefore=human_bytes(result['before']), ramAfter=human_bytes(result['after']),
                                  ramChange=(('+' if result['delta']>=0 else '')+human_bytes(result['delta'])),
                                  status="Purga standby completada; la memoria disponible se midió realmente")
        except Exception as error:
            message = f"No se pudo completar: {error}"
            self._data['status'] = message
            if kind in ('cache_scan', 'cache_clean'):
                self._data['cacheStatus'] = message
            elif kind in ('recycle_scan', 'recycle_empty'):
                self._data['recycleStatus'] = message
            elif kind == 'dns_flush':
                self._data['dnsStatus'] = message
            elif kind in ('storage_scan', 'storage_clean'):
                self._data['storageStatus'] = message
                if kind == 'storage_clean':
                    self._storage_scan = None
            elif kind == 'duplicates_scan':
                self._data['duplicateStatus'] = message
        finally:
            tray_operation = self._tray_operation
            self._data['resultSequence'] += 1
            self._data['resultSuccess'] = succeeded
            self._data['resultPartial'] = partially_completed
            self._data['resultKind'] = kind
            self._data['busy'] = False
            self._data['ramMeterActive'] = False
            self._active_kind = ""
            self._tray_operation = False
            self.changed.emit()
            if tray_operation:
                title = "Limpieza RAM completada" if succeeded else "Limpieza RAM con incidencias"
                self.trayNotification.emit(title, str(self._data.get('status') or 'Operación finalizada')[:220])

    @Slot()
    def analyze(self):
        self._start("Analizando temporales del usuario…", lambda: ('scan', scan_temps(user_temp_root())))

    @Slot()
    def clean(self):
        self._start("Eliminando temporales antiguos…", lambda: ('clean', clean_temps(user_temp_root())))

    @Slot()
    def analyzeCache(self):
        self._start("Analizando cachés regenerables…", lambda: ('cache_scan', scan_user_cache()), kind="cache_scan")

    @Slot()
    def cleanCache(self):
        self._start("Limpiando cachés regenerables…", lambda: ('cache_clean', clean_user_cache()), kind="cache_clean")

    @Slot()
    def analyzeRecycleBin(self):
        self._start("Consultando Papelera…", lambda: ('recycle_scan', recycle_bin_info()), kind="recycle_scan")

    @Slot()
    def emptyRecycleBin(self):
        self._start("Vaciando Papelera…", lambda: ('recycle_empty', empty_recycle_bin()), kind="recycle_empty")

    @Slot()
    def analyzeStorage(self):
        self._start("Analizando archivos eliminables permitidos…",
                    lambda: ('storage_scan', scan_safe_storage_cleanup()), kind="storage_scan")

    @Slot()
    def cleanStorage(self):
        if not self._storage_scan or not self._storage_scan.get('candidates'):
            self._data['storageStatus'] = "Analiza primero; no hay una selección segura pendiente."
            self.changed.emit()
            return
        snapshot = self._storage_scan
        self._start("Eliminando solo candidatos revisados…",
                    lambda: ('storage_clean', delete_scanned_candidates(snapshot)), kind="storage_clean")

    @Slot()
    def analyzeDuplicates(self):
        if self._future is not None:
            return
        try:
            from PySide6.QtWidgets import QFileDialog
            folder = QFileDialog.getExistingDirectory(None, "Selecciona una carpeta para analizar duplicados")
        except Exception as error:
            self._data['duplicateStatus'] = f"No se pudo abrir el selector: {error}"
            self.changed.emit()
            return
        if not folder:
            return
        self._duplicate_scan = None
        self._data.update(duplicateFolder=folder, duplicateFiles=0, duplicateGroups=0,
                          duplicateWasted="Analizando…", duplicateStatus="Calculando hashes SHA-256…",
                          duplicatePreview="")
        self._start("Comparando archivos por tamaño y SHA-256…",
                    lambda: ('duplicates_scan', scan_duplicates(folder)), kind="duplicates_scan")

    @Slot()
    def flushDns(self):
        self._start("Vaciando caché DNS…", lambda: ('dns_flush', flush_dns_cache()), kind="dns_flush")

    @Slot()
    def cleanRam(self):
        self._start("Solicitando a Windows liberar la lista standby…", lambda: ('ram', purge_standby()), kind="ram")

    @Slot()
    def cleanRamSafely(self):
        def optimize():
            before = [int(psutil.virtual_memory().available) for _ in range(3)]
            collected = int(gc.collect())
            time.sleep(0.35)
            after = [int(psutil.virtual_memory().available) for _ in range(3)]
            before_value = sorted(before)[len(before) // 2]
            after_value = sorted(after)[len(after) // 2]
            return ("ram_safe", {"before": before_value, "after": after_value,
                                 "delta": after_value - before_value, "collected": collected})
        self._start("Ejecutando optimización normal de memoria…", optimize, kind="ram_safe")

    @Slot()
    def cleanRamDeep(self):
        self._start("Ejecutando limpieza profunda de Windows…", lambda: ('ram_deep', optimize_ram_deep()), kind="ram_deep")

    @Slot(result=bool)
    def cleanRamDeepFromTray(self):
        """La acción explícita del menú ejecuta en segundo plano sin diálogos QML."""
        return self._start("Ejecutando limpieza profunda de Windows desde la bandeja…",
                           lambda: ('ram_deep', optimize_ram_deep()),
                           kind="ram_deep", ram_ui_feedback=False, tray_operation=True)

    def close(self):
        self._timer.stop()
        self._pool.shutdown(wait=False, cancel_futures=True)
