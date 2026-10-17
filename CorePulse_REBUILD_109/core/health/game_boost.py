"""Game Boost por proceso, reversible y condicionado a una sesión de juego.

Solo modifica el juego identificado por el detector de CorePulse y el valor de
Game Mode del usuario. Cada cambio se respalda antes de aplicarse y se restaura
al terminar el juego, desactivar Game Boost o cerrar la aplicación.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import time
from concurrent.futures import ThreadPoolExecutor
import ctypes
from ctypes import wintypes

import psutil
from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot


def _state_root() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    return base / "CorePulse" / "rebuild"


PROCESS_SET_INFORMATION = 0x0200
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_POWER_THROTTLING = 4
PROCESS_POWER_THROTTLING_CURRENT_VERSION = 1
PROCESS_POWER_THROTTLING_EXECUTION_SPEED = 0x1


class _ProcessPowerThrottlingState(ctypes.Structure):
    _fields_ = [("Version", wintypes.ULONG), ("ControlMask", wintypes.ULONG), ("StateMask", wintypes.ULONG)]


class GameBoost(QObject):
    changed = Signal()

    def __init__(self, performance, parent=None):
        super().__init__(parent)
        self.performance = performance
        self._settings_path = _state_root() / "game_boost_settings.json"
        self._backup_path = _state_root() / "game_boost_backup.json"
        self._enabled = self._read_enabled()
        self._purge_standby = self._read_purge_standby()
        self._power_throttling = self._read_power_throttling()
        self._tracked: dict[int, dict] = {}
        self._message = "Game Boost está desactivado."
        self._active_name = "N/A"
        self._status = "DESACTIVADO"
        self._session_active = False
        self._purge_attempted = False
        self._purge_message = ""
        self._purge_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="corepulse-game-ram")
        self._purge_future = None
        self._purge_timer = QTimer(self)
        self._purge_timer.setInterval(120)
        self._purge_timer.timeout.connect(self._poll_purge)
        self._recover_process_backup()
        self._recover_game_mode_backup()
        self.performance.changed.connect(self._sync)
        self._sync()

    def _read_enabled(self):
        try:
            value = json.loads(self._settings_path.read_text(encoding="utf-8"))
            return value.get("enabled") is True if isinstance(value, dict) else False
        except (OSError, ValueError, TypeError):
            return False

    def _read_purge_standby(self):
        try:
            value = json.loads(self._settings_path.read_text(encoding="utf-8"))
            return value.get("clean_standby_memory") is not False if isinstance(value, dict) else True
        except (OSError, ValueError, TypeError):
            return True

    def _read_power_throttling(self):
        try:
            value = json.loads(self._settings_path.read_text(encoding="utf-8"))
            return value.get("disable_power_throttling") is not False if isinstance(value, dict) else True
        except (OSError, ValueError, TypeError):
            return True

    def _save_settings(self):
        self._write_json(self._settings_path, {
            "enabled": self._enabled,
            "clean_standby_memory": self._purge_standby,
            "disable_power_throttling": self._power_throttling,
        })

    def _write_json(self, path: Path, value: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, path)

    @Property(bool, notify=changed)
    def enabled(self):
        return self._enabled

    @Property(str, notify=changed)
    def status(self):
        return self._status

    @Property(bool, notify=changed)
    def purgeStandby(self):
        return self._purge_standby

    @Property(bool, notify=changed)
    def powerThrottling(self):
        return self._power_throttling

    @Property(str, notify=changed)
    def message(self):
        return self._message

    @Property(str, notify=changed)
    def activeGame(self):
        return self._active_name

    @Slot(bool)
    def setEnabled(self, enabled):
        self._enabled = bool(enabled)
        try:
            self._save_settings()
        except OSError as error:
            self._enabled = False
            self._status = "ERROR"
            self._message = f"No se guardó la configuración: {error}"
        if self._enabled:
            self._message = "Game Boost listo; solo actuará cuando se detecte un juego compatible."
            self._sync()
        else:
            self._session_active = False
            self._purge_attempted = False
            self._restore_all()
            self._status = "DESACTIVADO"
            self._active_name = "N/A"
            self._message = "Game Boost desactivado; se restauraron los cambios que seguían bajo control de CorePulse."
        self.changed.emit()

    @Slot(bool)
    def setPurgeStandby(self, enabled):
        self._purge_standby = bool(enabled)
        try:
            self._save_settings()
            self._message = ("La purga standby se aplicará al inicio de la próxima sesión de juego."
                             if self._purge_standby else "La purga standby automática está desactivada.")
        except OSError as error:
            self._purge_standby = not self._purge_standby
            self._message = f"No se guardó la opción: {error}"
        self.changed.emit()

    @Slot(bool)
    def setPowerThrottling(self, enabled):
        previous = self._power_throttling
        self._power_throttling = bool(enabled)
        try:
            self._save_settings()
            self._message = ("HighQoS se aplicará a los procesos detectados al entrar en un juego."
                             if self._power_throttling else "HighQoS automático está desactivado.")
            if previous and not self._power_throttling:
                for pid in list(self._tracked):
                    if not self._restore_power_throttling(pid):
                        self._message = "Power Throttling conserva un rollback pendiente; CorePulse reintentará al terminar el juego."
        except OSError as error:
            self._power_throttling = previous
            self._message = f"No se guardó la opción: {error}"
        self.changed.emit()

    def _start_standby_purge(self):
        if not self._purge_standby or self._purge_attempted or self._purge_future is not None:
            return
        self._purge_attempted = True
        self._purge_message = "Solicitando a Windows una purga standby al inicio de la sesión…"

        def purge():
            from core.maintenance.cleanup import purge_standby
            return purge_standby()

        self._purge_future = self._purge_pool.submit(purge)
        self._purge_timer.start()

    def _poll_purge(self):
        future = self._purge_future
        if future is None or not future.done():
            return
        self._purge_future = None
        self._purge_timer.stop()
        try:
            result = future.result()
            delta = int(result.get("delta") or 0)
            amount = f"{abs(delta) / (1024 * 1024):.1f} MiB"
            self._purge_message = (f"RAM standby solicitada; variación observada: "
                                   f"{'+' if delta >= 0 else '-'}{amount} (no atribuible solo a CorePulse).")
        except Exception as error:
            self._purge_message = f"Purga standby no disponible: {type(error).__name__}."
        self._message = " · ".join(part for part in (self._message, self._purge_message) if part)
        self.changed.emit()

    def _games(self):
        data = getattr(self.performance, "data", {}) or {}
        rows = data.get("probableGames") if isinstance(data, dict) else None
        games = []
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            try:
                if int(row.get("pid") or 0) > 0:
                    games.append(dict(row))
            except (TypeError, ValueError):
                continue
        return games

    def _sync(self, *_args):
        if not self._enabled:
            return
        games = self._games()
        current = {int(game["pid"]): game for game in games}
        for pid in list(self._tracked):
            if pid not in current:
                self._restore_process(pid)
        if not games:
            self._session_active = False
            self._purge_attempted = False
            self._restore_game_mode()
            self._active_name = "N/A"
            self._status = "ESPERANDO JUEGO"
            self._message = "No hay un proceso de juego compatible activo."
        else:
            if not self._session_active:
                self._session_active = True
                self._purge_attempted = False
                self._purge_message = ""
                self._start_standby_purge()
            self._active_name = str(games[0].get("name") or games[0].get("exe") or f"PID {games[0]['pid']}")
            process_results = []
            qos_results = []
            for game in games:
                process_results.append(self._boost_process(game))
                if self._power_throttling:
                    qos_results.append(self._set_high_qos(game))
            mode_result = self._apply_game_mode()
            all_results = process_results + qos_results + [mode_result]
            success = any(result.get("success") for result in all_results)
            self._status = "ACTIVO" if success else "PARCIAL"
            messages = list(dict.fromkeys(result["message"] for result in all_results if result.get("message")))
            if self._purge_message:
                messages.append(self._purge_message)
            self._message = " · ".join(messages)
        self.changed.emit()

    def _boost_process(self, game):
        pid = int(game.get("pid") or 0)
        try:
            process = psutil.Process(pid)
            created = float(process.create_time())
            current = process.nice()
            state = self._tracked.get(pid)
            if state and abs(state.get("created", -1.0) - created) > .01:
                self._tracked.pop(pid, None)
                state = None
            if state is None:
                target = getattr(psutil, "HIGH_PRIORITY_CLASS", 128)
                state = {"pid": pid, "created": created, "original": int(current), "applied": int(target)}
                self._tracked[pid] = state
                if not self._persist_process_backup():
                    self._tracked.pop(pid, None)
                    return {"success": False, "message": "No se modificó la prioridad porque no se pudo guardar el rollback."}
            target = int(state["applied"])
            if int(current) != target:
                process.nice(target)
            return {"success": True, "message": "Prioridad alta aplicada al juego detectado."}
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError, ValueError) as error:
            return {"success": False, "message": f"Prioridad del juego no disponible ({type(error).__name__})."}

    @staticmethod
    def _kernel32():
        if os.name != "nt":
            raise OSError("HighQoS solo está disponible en Windows.")
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        kernel.GetProcessInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        kernel.GetProcessInformation.restype = wintypes.BOOL
        kernel.SetProcessInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        kernel.SetProcessInformation.restype = wintypes.BOOL
        return kernel

    def _set_high_qos(self, game):
        if not self._power_throttling:
            return {"success": True, "message": "HighQoS desactivado por configuración."}
        if os.name != "nt":
            return {"success": False, "message": "HighQoS solo está disponible en Windows."}
        pid = int(game.get("pid") or 0)
        state = self._tracked.get(pid)
        if not pid or state is None:
            return {"success": False, "message": "HighQoS omitido: falta un respaldo de proceso."}
        if state.get("power_throttling_changed"):
            return {"success": True, "message": "Power Throttling ya está desactivado (HighQoS)."}
        handle = None
        try:
            process = psutil.Process(pid)
            if abs(float(process.create_time()) - float(state.get("created", -1))) > .01:
                return {"success": False, "message": "HighQoS omitido: el PID cambió de proceso."}
            kernel = self._kernel32()
            handle = kernel.OpenProcess(PROCESS_SET_INFORMATION | PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return {"success": False, "message": f"HighQoS no disponible (WinError {ctypes.get_last_error()})."}
            original = _ProcessPowerThrottlingState()
            original.Version = PROCESS_POWER_THROTTLING_CURRENT_VERSION
            if not kernel.GetProcessInformation(handle, PROCESS_POWER_THROTTLING,
                                                ctypes.byref(original), ctypes.sizeof(original)):
                return {"success": False, "message": f"No se pudo leer HighQoS (WinError {ctypes.get_last_error()})."}
            target = _ProcessPowerThrottlingState()
            target.Version = PROCESS_POWER_THROTTLING_CURRENT_VERSION
            target.ControlMask = int(original.ControlMask) | PROCESS_POWER_THROTTLING_EXECUTION_SPEED
            target.StateMask = int(original.StateMask) & ~PROCESS_POWER_THROTTLING_EXECUTION_SPEED
            if (int(original.ControlMask), int(original.StateMask)) == (int(target.ControlMask), int(target.StateMask)):
                return {"success": True, "message": "Power Throttling ya estaba desactivado."}

            state["power_throttling_original"] = {
                "version": int(original.Version), "control_mask": int(original.ControlMask),
                "state_mask": int(original.StateMask),
            }
            state["power_throttling_applied"] = {
                "version": int(target.Version), "control_mask": int(target.ControlMask),
                "state_mask": int(target.StateMask),
            }
            state["power_throttling_changed"] = True
            if not self._persist_process_backup():
                state.pop("power_throttling_original", None)
                state.pop("power_throttling_applied", None)
                state.pop("power_throttling_changed", None)
                return {"success": False, "message": "No se aplicó HighQoS porque falló el respaldo."}
            if not kernel.SetProcessInformation(handle, PROCESS_POWER_THROTTLING,
                                                ctypes.byref(target), ctypes.sizeof(target)):
                state.pop("power_throttling_original", None)
                state.pop("power_throttling_applied", None)
                state.pop("power_throttling_changed", None)
                self._persist_process_backup()
                return {"success": False, "message": f"Windows rechazó HighQoS (WinError {ctypes.get_last_error()})."}
            return {"success": True, "message": "Power Throttling desactivado (HighQoS)."}
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError, ValueError) as error:
            return {"success": False, "message": f"HighQoS no disponible ({type(error).__name__})."}
        finally:
            if handle:
                try:
                    self._kernel32().CloseHandle(handle)
                except Exception:
                    pass

    def _restore_power_throttling(self, pid):
        state = self._tracked.get(int(pid))
        if not state or not state.get("power_throttling_changed"):
            return True
        original = state.get("power_throttling_original") or {}
        applied = state.get("power_throttling_applied") or {}
        handle = None
        try:
            if not psutil.pid_exists(int(pid)):
                state.pop("power_throttling_original", None)
                state.pop("power_throttling_applied", None)
                state.pop("power_throttling_changed", None)
                self._persist_process_backup()
                return True
            process = psutil.Process(int(pid))
            if abs(float(process.create_time()) - float(state.get("created", -1))) > .01:
                state.pop("power_throttling_original", None)
                state.pop("power_throttling_applied", None)
                state.pop("power_throttling_changed", None)
                self._persist_process_backup()
                return True
            kernel = self._kernel32()
            handle = kernel.OpenProcess(PROCESS_SET_INFORMATION | PROCESS_QUERY_LIMITED_INFORMATION,
                                        False, int(pid))
            if not handle:
                return False
            current = _ProcessPowerThrottlingState()
            current.Version = PROCESS_POWER_THROTTLING_CURRENT_VERSION
            if not kernel.GetProcessInformation(handle, PROCESS_POWER_THROTTLING,
                                                ctypes.byref(current), ctypes.sizeof(current)):
                return False
            current_pair = (int(current.ControlMask), int(current.StateMask))
            applied_pair = (int(applied.get("control_mask", -1)), int(applied.get("state_mask", -1)))
            original_pair = (int(original.get("control_mask", -1)), int(original.get("state_mask", -1)))
            if current_pair == applied_pair:
                restore = _ProcessPowerThrottlingState()
                restore.Version = int(original.get("version") or PROCESS_POWER_THROTTLING_CURRENT_VERSION)
                restore.ControlMask = original_pair[0]
                restore.StateMask = original_pair[1]
                if not kernel.SetProcessInformation(handle, PROCESS_POWER_THROTTLING,
                                                    ctypes.byref(restore), ctypes.sizeof(restore)):
                    return False
            elif current_pair != original_pair:
                self._message = "HighQoS cambió fuera de CorePulse; no se sobrescribió ese estado."
            state.pop("power_throttling_original", None)
            state.pop("power_throttling_applied", None)
            state.pop("power_throttling_changed", None)
            self._persist_process_backup()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError, ValueError):
            return False
        finally:
            if handle:
                try:
                    self._kernel32().CloseHandle(handle)
                except Exception:
                    pass

    def _persist_process_backup(self):
        try:
            self._write_json(self._backup_path, {"processes": list(self._tracked.values())})
            return True
        except OSError:
            self._message = "No se pudo persistir el respaldo; no se aplicarán más cambios de prioridad."
            return False

    def _restore_process(self, pid):
        state = self._tracked.get(int(pid))
        if not state:
            return
        if not self._restore_power_throttling(pid):
            self._message = "HighQoS no se pudo restaurar; se conserva el rollback para reintentarlo."
            return
        try:
            process = psutil.Process(int(pid))
            if abs(float(process.create_time()) - float(state["created"])) <= .01:
                current = int(process.nice())
                if current == int(state["applied"]):
                    process.nice(int(state["original"]))
                elif current != int(state["original"]):
                    self._message = "Prioridad modificada por otra aplicación; CorePulse no la sobrescribió."
        except psutil.NoSuchProcess:
            pass
        except (psutil.AccessDenied, OSError, ValueError):
            self._message = "Windows no permitió restaurar una prioridad; se conserva el rollback para reintentarlo."
            return
        self._tracked.pop(int(pid), None)
        self._persist_process_backup()

    def _recover_process_backup(self):
        try:
            payload = json.loads(self._backup_path.read_text(encoding="utf-8"))
            self._tracked = {int(row["pid"]): row for row in payload.get("processes", []) if isinstance(row, dict)}
        except (OSError, ValueError, TypeError, KeyError):
            self._tracked = {}
        # A restarted app has no active session context: restore only its own
        # still-running PIDs, then clear stale records.
        for pid in list(self._tracked):
            self._restore_process(pid)

    def _apply_game_mode(self):
        if os.name != "nt":
            return {"success": False, "message": "Windows Game Mode solo está disponible en Windows."}
        backup_path = self._backup_path.with_name("game_mode_backup.json")
        if backup_path.exists():
            return {"success": False, "message": "Hay un rollback anterior de Game Mode pendiente; no se sobrescribirá."}
        try:
            import winreg
            key_path = r"Software\Microsoft\GameBar"
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE) as key:
                try:
                    original, kind = winreg.QueryValueEx(key, "AutoGameModeEnabled")
                    existed = True
                except FileNotFoundError:
                    original, kind, existed = None, winreg.REG_DWORD, False
                self._write_json(backup_path,
                                 {"existed": existed, "value": original, "kind": int(kind), "applied": 1})
                if not existed or int(original) != 1:
                    winreg.SetValueEx(key, "AutoGameModeEnabled", 0, winreg.REG_DWORD, 1)
            return {"success": True, "message": "Windows Game Mode activado con respaldo reversible."}
        except (OSError, ValueError, TypeError) as error:
            return {"success": False, "message": f"Windows Game Mode no se pudo activar ({type(error).__name__})."}

    def _recover_game_mode_backup(self):
        self._restore_game_mode()

    def _restore_game_mode(self):
        path = self._backup_path.with_name("game_mode_backup.json")
        if os.name != "nt" or not path.is_file():
            return
        try:
            import winreg
            data = json.loads(path.read_text(encoding="utf-8"))
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\GameBar", 0,
                                    winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE) as key:
                try:
                    current, _ = winreg.QueryValueEx(key, "AutoGameModeEnabled")
                except FileNotFoundError:
                    current = None
                if current is not None and int(current) == int(data.get("applied", 1)):
                    if data.get("existed"):
                        winreg.SetValueEx(key, "AutoGameModeEnabled", 0, int(data["kind"]), data.get("value"))
                    else:
                        winreg.DeleteValue(key, "AutoGameModeEnabled")
                elif data.get("existed") and current == data.get("value"):
                    pass  # Ya se restauró; no hace falta cambiarlo.
                elif not data.get("existed") and current is None:
                    pass  # El estado original era que el valor no existiera.
                else:
                    self._message = "Game Mode cambió fuera de CorePulse; se conserva el rollback para no sobrescribirlo."
                    return
            path.unlink(missing_ok=True)
        except (OSError, ValueError, TypeError, KeyError):
            self._message = "Game Mode conserva un rollback pendiente; Windows cambió el valor o no permitió restaurarlo."

    def _restore_all(self):
        for pid in list(self._tracked):
            self._restore_process(pid)
        self._restore_game_mode()

    @Slot()
    def close(self):
        self._enabled = False
        self._purge_timer.stop()
        self._restore_all()
        self._purge_pool.shutdown(wait=False, cancel_futures=True)
        try:
            self.performance.changed.disconnect(self._sync)
        except (RuntimeError, TypeError):
            pass
