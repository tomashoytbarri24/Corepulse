"""Arranque automático y robusto del runtime local de CorePulse AI.

V399 hace resistente el primer arranque en un PC limpio y conserva el autoarranque desde ``main.py``: prioriza el ejecutable
servidor dedicado de llama.cpp, prueba rutas alternativas si una termina al inicio y
usa como último fallback el mismo BAT manual del proyecto. Sólo después de confirmar
127.0.0.1:8766 levanta CorePulse AI Server en 8765.

La telemetría y las decisiones técnicas siguen fuera de este módulo. Aquí sólo se
administran procesos locales de IA. REAL_OR_NA permanece bajo autoridad de CorePulse.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import zipfile
from typing import Any

from core.runtime_paths import data_path, is_frozen, log_path, resource_root

MODEL_PORT = 8766
SERVER_PORT = 8765
MODEL_ENDPOINT = f"http://127.0.0.1:{MODEL_PORT}/v1/models"
SERVER_STATUS_ENDPOINT = f"http://127.0.0.1:{SERVER_PORT}/v1/status"
MODEL_NAME = "Qwen/Qwen3-4B-GGUF:Q4_K_M"
LLAMA_GITHUB_RELEASES_API = "https://api.github.com/repos/ggml-org/llama.cpp/releases?per_page=12"

_MODEL_READY_TIMEOUT_SECONDS = 15 * 60
_SERVER_READY_TIMEOUT_SECONDS = 90
_HTTP_STATUS_TIMEOUT = 2.5
_MODEL_QUICK_EXIT_GRACE_SECONDS = 18
_MODEL_LOG_NAME = "corepulse_ai_model.log"
_MODEL_BAT_LOG_NAME = "corepulse_ai_model_bat.log"


def _creation_flags() -> int:
    if os.name != "nt":
        return 0
    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0))


def _http_json(url: str, *, timeout: float = _HTTP_STATUS_TIMEOUT) -> dict[str, Any] | None:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "CorePulse-AutoStart/2"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
        data = json.loads(raw) if raw else {}
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _endpoint_ready(url: str, *, timeout: float = _HTTP_STATUS_TIMEOUT) -> bool:
    return _http_json(url, timeout=timeout) is not None


class LocalAIRuntimeManager:
    """Administra el runtime local iniciado junto con CorePulse.

    Si llama.cpp o CorePulse AI Server ya estaban ejecutándose, se reutilizan.
    Los procesos arrancados por esta instancia sí se detienen durante el cierre.
    """

    def __init__(self, root: str | os.PathLike | None = None):
        self.root = Path(root or resource_root()).resolve()
        self.server_dir = self.root / "CorePulse_AI_Server"
        self.model_dir = self.root / "CorePulse_AI_Model_Host"
        self.runtime_dir = Path(data_path("ai_runtime")).resolve()
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        # V399: runtime portable propio en AppData. En un PC nuevo CorePulse puede
        # preparar llama.cpp sin depender de que ya exista en PATH/WinGet.
        self.portable_llama_dir = self.runtime_dir / "llama_cpp_portable"

        # V396: primero reutiliza el .venv del servidor que usa el BAT manual.
        # Esto evita crear un segundo entorno distinto al que el usuario ya probó.
        self.project_venv_dir = self.server_dir / ".venv"
        self.fallback_venv_dir = self.runtime_dir / "server_venv"
        self.venv_dir = self._select_initial_venv_dir()
        self.venv_python = self._venv_python_for(self.venv_dir)
        self.deps_marker = self.venv_dir / ".corepulse_ai_requirements.sha256"

        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._owned_processes: dict[str, subprocess.Popen] = {}
        self._log_handles: list[Any] = []
        self._embedded_server = None
        self._embedded_server_thread: threading.Thread | None = None
        self._state: dict[str, Any] = {
            "state": "IDLE",
            "stage": "Esperando inicio",
            "detail": "CorePulse AI todavía no inició su runtime local.",
            "server_ready": False,
            "model_ready": False,
            "started_by_corepulse": False,
            "error": None,
            "updated_at": time.time(),
        }

    @staticmethod
    def _venv_python_for(directory: Path) -> Path:
        return directory / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

    def _select_initial_venv_dir(self) -> Path:
        project_python = self._venv_python_for(self.project_venv_dir)
        if project_python.is_file():
            return self.project_venv_dir
        fallback_python = self._venv_python_for(self.fallback_venv_dir)
        if fallback_python.is_file():
            return self.fallback_venv_dir
        # En modo fuente la carpeta del proyecto suele ser escribible y coincide
        # con Iniciar_Todo_CorePulse_AI.bat. En un bundle de sólo lectura se hará
        # fallback automático a AppData si la creación falla.
        return self.project_venv_dir

    def status(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._state)

    def _publish(self, state: str, stage: str, detail: str, **extra: Any) -> None:
        with self._lock:
            self._state.update({
                "state": str(state),
                "stage": str(stage),
                "detail": str(detail),
                "updated_at": time.time(),
                **extra,
            })
        try:
            self._append_runtime_log(f"{state} | {stage} | {detail}")
        except Exception:
            pass

    def _append_runtime_log(self, line: str) -> None:
        path = Path(log_path("corepulse_ai_autostart.log"))
        path.parent.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with path.open("a", encoding="utf-8", errors="replace") as handle:
            handle.write(f"[{stamp}] {line}\n")

    def start_async(self) -> bool:
        """Inicia una única preparación en background; nunca bloquea Tk."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return False
            if self._state.get("state") == "READY":
                return False
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._worker, daemon=True, name="CorePulse-AI-AutoStart")
            self._thread.start()
            return True

    def _requirements_signature(self) -> str:
        path = self.server_dir / "requirements.txt"
        if not path.is_file():
            return ""
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _run(self, args: list[str], *, cwd: Path | None = None, timeout: float | None = None) -> subprocess.CompletedProcess:
        kwargs: dict[str, Any] = {
            "cwd": str(cwd) if cwd else None,
            "capture_output": True,
            "text": True,
            "errors": "replace",
            "creationflags": _creation_flags(),
            "timeout": timeout,
        }
        return subprocess.run(args, **kwargs)

    def _python_candidates(self) -> list[str]:
        candidates: list[str] = []
        if sys.executable:
            candidates.append(sys.executable)
        if os.name == "nt":
            py = shutil.which("py")
            if py:
                candidates.append(py)
        python = shutil.which("python")
        if python:
            candidates.append(python)
        out: list[str] = []
        seen: set[str] = set()
        for value in candidates:
            key = os.path.normcase(os.path.abspath(value)) if os.path.exists(value) else value.casefold()
            if key not in seen:
                seen.add(key)
                out.append(value)
        return out

    def _create_venv(self, directory: Path) -> bool:
        directory.parent.mkdir(parents=True, exist_ok=True)
        for python_exe in self._python_candidates():
            command = [python_exe]
            if Path(python_exe).name.lower() in {"py", "py.exe"}:
                command += ["-3"]
            command += ["-m", "venv", str(directory)]
            try:
                result = self._run(command, timeout=180)
            except Exception:
                continue
            vpy = self._venv_python_for(directory)
            if result.returncode == 0 and vpy.is_file():
                self.venv_dir = directory
                self.venv_python = vpy
                self.deps_marker = directory / ".corepulse_ai_requirements.sha256"
                return True
        return False

    def _server_dependencies_ready(self) -> bool:
        if not self.venv_python.is_file():
            return False
        try:
            result = self._run([
                str(self.venv_python), "-c",
                "import fastapi,uvicorn,pydantic,dotenv; print('COREPULSE_AI_DEPS_OK')",
            ], timeout=20)
            return result.returncode == 0 and "COREPULSE_AI_DEPS_OK" in (result.stdout or "")
        except Exception:
            return False

    def _ensure_server_runtime(self) -> bool:
        requirements = self.server_dir / "requirements.txt"
        if not requirements.is_file():
            self._publish("ERROR", "Servidor IA no disponible", "Falta CorePulse_AI_Server/requirements.txt.", error="SERVER_FILES_MISSING")
            return False

        if not self.venv_python.is_file():
            self._publish("PREPARING", "Preparando CorePulse AI", "Creando el entorno local del servidor de IA…")
            if not self._create_venv(self.venv_dir):
                if self.venv_dir != self.fallback_venv_dir:
                    self._publish("PREPARING", "Preparando CorePulse AI", "La carpeta del proyecto no admite el entorno; usando AppData…")
                    if not self._create_venv(self.fallback_venv_dir):
                        self._publish("ERROR", "No se pudo preparar CorePulse AI", "No fue posible crear un entorno Python para el servidor local.", error="VENV_CREATE_FAILED")
                        return False
                else:
                    self._publish("ERROR", "No se pudo preparar CorePulse AI", "No fue posible crear un entorno Python para el servidor local.", error="VENV_CREATE_FAILED")
                    return False

        # Si el entorno que ya dejó preparado el BAT manual funciona, se reutiliza
        # sin reinstalar nada ni depender de un marker distinto.
        if self._server_dependencies_ready():
            return True

        signature = self._requirements_signature()
        self._publish("PREPARING", "Preparando CorePulse AI", "Instalando dependencias del servidor local…")
        try:
            result = self._run([
                str(self.venv_python), "-m", "pip", "install", "--disable-pip-version-check",
                "-r", str(requirements),
            ], cwd=self.server_dir, timeout=600)
        except Exception as exc:
            self._publish("ERROR", "Dependencias de IA no disponibles", f"{type(exc).__name__}: {exc}", error="SERVER_DEPS_FAILED")
            return False
        if result.returncode != 0 or not self._server_dependencies_ready():
            detail = (result.stderr or result.stdout or "No se pudieron instalar las dependencias.")[-900:]
            self._publish("ERROR", "Dependencias de IA no disponibles", detail, error="SERVER_DEPS_FAILED")
            return False
        try:
            self.deps_marker.write_text(signature, encoding="utf-8")
        except Exception:
            pass
        return True

    def _open_log(self, name: str):
        path = Path(log_path(name))
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = path.open("a", encoding="utf-8", errors="replace")
        self._log_handles.append(handle)
        return handle

    def _spawn(self, key: str, args: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.Popen | None:
        try:
            if self._stop_event.is_set():
                return None
            log = self._open_log(f"{key}.log")
            self._append_runtime_log(f"SPAWN {key}: {' '.join(map(str, args))}")
            process = subprocess.Popen(
                args,
                cwd=str(cwd),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=_creation_flags(),
            )
            # Una desactivación durante el inicio no puede dejar un modelo
            # pesado ejecutándose por una carrera entre spawn y stop.
            with self._lock:
                if self._stop_event.is_set():
                    try:
                        process.terminate()
                    except Exception:
                        pass
                    return None
                self._owned_processes[key] = process
            return process
        except Exception as exc:
            self._publish("ERROR", "No se pudo iniciar CorePulse AI", f"{type(exc).__name__}: {exc}", error=f"SPAWN_{key.upper()}_FAILED")
            return None

    def _winget_candidates(self) -> list[Path]:
        """Localiza WinGet incluso cuando App Execution Aliases no están en PATH."""
        candidates: list[Path] = []
        found = shutil.which("winget")
        if found:
            candidates.append(Path(found))

        local = os.environ.get("LOCALAPPDATA")
        if local:
            candidates.append(Path(local) / "Microsoft" / "WindowsApps" / "winget.exe")

        # Get-Command cubre instalaciones de App Installer que Python no ve todavía.
        if os.name == "nt":
            powershell = shutil.which("powershell") or shutil.which("powershell.exe")
            if powershell:
                try:
                    result = self._run([
                        powershell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                        "-Command", "(Get-Command winget.exe -ErrorAction SilentlyContinue).Source",
                    ], timeout=20)
                    for line in (result.stdout or "").splitlines():
                        if line.strip():
                            candidates.append(Path(line.strip().strip('"')))
                except Exception:
                    pass

        out: list[Path] = []
        seen: set[str] = set()
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except Exception:
                resolved = candidate
            key = str(resolved).casefold()
            if key in seen:
                continue
            try:
                if resolved.is_file():
                    seen.add(key)
                    out.append(resolved)
            except Exception:
                pass
        return out

    def _refresh_process_path(self) -> None:
        """Refresca PATH del proceso tras una instalación portable de WinGet."""
        if os.name != "nt":
            return
        values: list[str] = []
        try:
            import winreg  # type: ignore
            for hive, subkey in (
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
                (winreg.HKEY_CURRENT_USER, r"Environment"),
            ):
                try:
                    with winreg.OpenKey(hive, subkey) as key:
                        raw, _ = winreg.QueryValueEx(key, "Path")
                        if raw:
                            values.append(str(raw))
                except Exception:
                    pass
        except Exception:
            pass
        current = str(os.environ.get("PATH") or "")
        if current:
            values.append(current)
        local = os.environ.get("LOCALAPPDATA")
        if local:
            values.append(str(Path(local) / "Microsoft" / "WinGet" / "Links"))
            values.append(str(Path(local) / "Microsoft" / "WindowsApps"))
        merged: list[str] = []
        seen: set[str] = set()
        for block in values:
            for item in block.split(os.pathsep):
                item = item.strip().strip('"')
                if not item:
                    continue
                key = os.path.normcase(os.path.abspath(os.path.expandvars(item)))
                if key in seen:
                    continue
                seen.add(key)
                merged.append(os.path.expandvars(item))
        if merged:
            os.environ["PATH"] = os.pathsep.join(merged)

    def _portable_llama_candidates(self) -> list[Path]:
        if not self.portable_llama_dir.is_dir():
            return []
        candidates: list[Path] = []
        try:
            candidates.extend(self.portable_llama_dir.glob("**/llama-server.exe"))
            candidates.extend(self.portable_llama_dir.glob("**/llama.exe"))
        except Exception:
            pass
        return candidates

    @staticmethod
    def _safe_extract_zip(archive: Path, destination: Path) -> None:
        destination = destination.resolve()
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                target = (destination / info.filename).resolve()
                if destination not in target.parents and target != destination:
                    raise ValueError("Unsafe archive path")
            zf.extractall(destination)

    def _download_portable_llama(self) -> bool:
        """Fallback de primer inicio: descarga el binario oficial CPU x64 a AppData.

        No modifica Windows ni el proyecto. Se usa sólo si no hay llama.cpp local y
        WinGet no pudo dejarlo disponible. El modelo se descarga después por llama.cpp.
        """
        if os.name != "nt":
            return False
        self._publish(
            "PREPARING", "Preparando motor local",
            "No se encontró llama.cpp instalado. CorePulse está descargando su runtime portable oficial…",
        )
        try:
            req = urllib.request.Request(
                LLAMA_GITHUB_RELEASES_API,
                headers={"Accept": "application/vnd.github+json", "User-Agent": "CorePulse-AI-Bootstrap/1"},
            )
            with urllib.request.urlopen(req, timeout=25) as response:
                releases = json.loads(response.read().decode("utf-8", errors="replace"))
            if not isinstance(releases, list):
                raise RuntimeError("GitHub releases response invalid")

            asset_url = None
            asset_name = None
            # Preferimos CPU x64: es la variante más portable para un PC Windows limpio.
            pattern = re.compile(r"^llama-.*-bin-win-cpu-x64\.zip$", re.IGNORECASE)
            for release in releases:
                if not isinstance(release, dict):
                    continue
                for asset in release.get("assets") or []:
                    if not isinstance(asset, dict):
                        continue
                    name = str(asset.get("name") or "")
                    url = str(asset.get("browser_download_url") or "")
                    if pattern.match(name) and url.startswith("https://github.com/"):
                        asset_name, asset_url = name, url
                        break
                if asset_url:
                    break
            if not asset_url:
                raise RuntimeError("No Windows x64 CPU release asset found")

            self.portable_llama_dir.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="corepulse_llama_", dir=str(self.runtime_dir)) as tmp:
                tmp_path = Path(tmp)
                archive = tmp_path / (asset_name or "llama-win-x64.zip")
                req = urllib.request.Request(asset_url, headers={"User-Agent": "CorePulse-AI-Bootstrap/1"})
                with urllib.request.urlopen(req, timeout=90) as response, archive.open("wb") as handle:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        handle.write(chunk)
                extracted = tmp_path / "extracted"
                extracted.mkdir(parents=True, exist_ok=True)
                self._safe_extract_zip(archive, extracted)
                if not any(extracted.glob("**/llama-server.exe")):
                    raise RuntimeError("Downloaded archive does not contain llama-server.exe")
                staged = tmp_path / "runtime"
                shutil.copytree(extracted, staged)
                if self.portable_llama_dir.exists():
                    shutil.rmtree(self.portable_llama_dir, ignore_errors=True)
                shutil.move(str(staged), str(self.portable_llama_dir))

            candidates = self._portable_llama_candidates()
            if candidates:
                self._append_runtime_log(f"PORTABLE LLAMA READY: {candidates[0]}")
                return True
            raise RuntimeError("Portable llama.cpp was extracted but not located")
        except Exception as exc:
            self._append_runtime_log(f"PORTABLE LLAMA FAILED: {type(exc).__name__}: {exc}")
            return False

    def _llama_direct_candidates(self) -> list[Path]:
        """Devuelve candidatos de llama.cpp priorizando el servidor dedicado.

        En algunas versiones de WinGet coexisten ``llama.exe`` y
        ``llama-server.exe``. Para CorePulse necesitamos un endpoint OpenAI-compatible,
        por lo que ``llama-server`` es la primera opción y el frontend unificado queda
        como fallback.
        """
        self._refresh_process_path()
        candidates: list[Path] = []
        candidates.extend(self._portable_llama_candidates())
        for name in ("llama-server.exe", "llama.exe", "llama-server", "llama"):
            found = shutil.which(name)
            if found:
                candidates.append(Path(found))

        local = os.environ.get("LOCALAPPDATA")
        if local:
            links = Path(local) / "Microsoft" / "WinGet" / "Links"
            candidates += [links / "llama-server.exe", links / "llama.exe"]
            packages = Path(local) / "Microsoft" / "WinGet" / "Packages"
            if packages.is_dir():
                try:
                    candidates.extend(packages.glob("**/llama-server.exe"))
                    candidates.extend(packages.glob("**/llama.exe"))
                except Exception:
                    pass

        program_files = os.environ.get("ProgramFiles")
        if program_files:
            packages = Path(program_files) / "WinGet" / "Packages"
            if packages.is_dir():
                try:
                    candidates.extend(packages.glob("**/llama-server.exe"))
                    candidates.extend(packages.glob("**/llama.exe"))
                except Exception:
                    pass
        return candidates

    @staticmethod
    def _candidate_priority(path: Path) -> int:
        name = path.name.lower()
        # sort() es estable: dentro de cada tipo conserva el orden PATH -> Links -> Packages.
        return 0 if name in {"llama-server.exe", "llama-server"} else 1

    def _all_llama_candidates(self) -> list[Path]:
        found: list[Path] = []
        seen: set[str] = set()
        for candidate in self._llama_direct_candidates():
            try:
                resolved = candidate.resolve()
            except Exception:
                resolved = candidate
            key = str(resolved).casefold()
            if key in seen:
                continue
            try:
                valid_name = resolved.name.lower() in {"llama.exe", "llama-server.exe", "llama", "llama-server"}
                if resolved.is_file() and valid_name:
                    seen.add(key)
                    found.append(resolved)
            except Exception:
                pass

        # El BAT de V357 sigue siendo una fuente válida para instalaciones WinGet
        # que no estén visibles en PATH.
        locator = self.model_dir / "Localizar_Llama_Host.bat"
        if os.name == "nt" and locator.is_file():
            try:
                command = f'call "{locator}"'
                result = self._run(["cmd.exe", "/d", "/c", command], cwd=self.model_dir, timeout=45)
                for line in (result.stdout or "").splitlines():
                    candidate = Path(line.strip().strip('"'))
                    if not candidate.is_file():
                        continue
                    try:
                        resolved = candidate.resolve()
                    except Exception:
                        resolved = candidate
                    key = str(resolved).casefold()
                    if key not in seen and resolved.name.lower() in {"llama.exe", "llama-server.exe"}:
                        seen.add(key)
                        found.append(resolved)
            except Exception:
                pass
        found.sort(key=self._candidate_priority)
        return found

    def _locate_llama(self) -> Path | None:
        candidates = self._all_llama_candidates()
        return candidates[0] if candidates else None

    @staticmethod
    def _model_command_for(executable: Path) -> list[str]:
        name = executable.name.lower()
        args = [str(executable)]
        if name in {"llama.exe", "llama"}:
            args.append("serve")
        args += ["-hf", MODEL_NAME, "--host", "127.0.0.1", "--port", str(MODEL_PORT)]
        return args

    def _log_tail(self, name: str, *, max_chars: int = 1200) -> str:
        try:
            path = Path(log_path(name))
            if not path.is_file():
                return ""
            text = path.read_text(encoding="utf-8", errors="replace")
            return text[-max_chars:].strip()
        except Exception:
            return ""

    def _wait_for_model_attempt(self, process: subprocess.Popen | None, *, long_wait: bool = True) -> tuple[bool, str]:
        """Espera un intento sin convertir el primer fallo en error terminal.

        Si el ejecutable termina rápido, devolvemos control para probar el siguiente
        candidato. Si sigue vivo, puede estar descargando/cargando el modelo y se le
        concede el timeout completo de la primera ejecución.
        """
        started = time.monotonic()
        deadline = started + (_MODEL_READY_TIMEOUT_SECONDS if long_wait else _MODEL_QUICK_EXIT_GRACE_SECONDS)
        while not self._stop_event.is_set() and time.monotonic() < deadline:
            if _endpoint_ready(MODEL_ENDPOINT):
                return True, "READY"
            if process is not None and process.poll() is not None:
                return False, f"EXIT_{process.returncode}"
            # Tras el periodo de gracia, un proceso que sigue vivo probablemente está
            # descargando o cargando el modelo; continuamos con el timeout largo.
            if not long_wait and time.monotonic() - started >= _MODEL_QUICK_EXIT_GRACE_SECONDS:
                return False, "STILL_RUNNING"
            time.sleep(1.0)
        if self._stop_event.is_set():
            return False, "STOPPED"
        if not long_wait and process is not None and process.poll() is None:
            return False, "STILL_RUNNING"
        return False, "TIMEOUT"

    def _start_portable_model_fallback(self, attempted: list[str]) -> bool:
        """Prueba el runtime CPU x64 portable cuando la instalación del sistema falla."""
        existing_portable = self._portable_llama_candidates()
        if existing_portable:
            # Ya fue incluido entre los candidatos normales; no repetimos el mismo fallo.
            return False
        if not self._download_portable_llama():
            return False
        for executable in self._portable_llama_candidates():
            if self._stop_event.is_set():
                return False
            attempted.append(str(executable))
            self._publish(
                "MODEL_LOADING", "Cargando IA local",
                "Usando el runtime portable CPU de CorePulse AI. La primera vez puede descargar varios GB del modelo…",
                server_ready=False, model_ready=False,
            )
            model_env = os.environ.copy()
            model_env.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
            process = self._spawn(
                "corepulse_ai_model_portable", self._model_command_for(executable),
                cwd=self.model_dir, env=model_env,
            )
            if process is None:
                continue
            quick_ok, quick_reason = self._wait_for_model_attempt(process, long_wait=False)
            self._append_runtime_log(f"PORTABLE MODEL CANDIDATE {executable}: {quick_reason}")
            if quick_ok:
                return True
            if quick_reason == "STILL_RUNNING":
                ready, reason = self._wait_for_model_attempt(process, long_wait=True)
                self._append_runtime_log(f"PORTABLE MODEL LONG WAIT {executable}: {reason}")
                if ready:
                    return True
        return False

    def _start_model_via_bat(self) -> bool:
        bat = self.model_dir / "Iniciar_Modelo_CorePulse_AI.bat"
        if os.name != "nt" or not bat.is_file():
            return False
        env = os.environ.copy()
        env["COREPULSE_AI_AUTOSTART"] = "1"
        self._publish(
            "MODEL_LOADING", "Reintentando IA local",
            "Usando el iniciador compatible de CorePulse AI para completar el arranque del modelo…",
            model_ready=False, server_ready=False,
        )
        process = self._spawn(
            "corepulse_ai_model_bat",
            ["cmd.exe", "/d", "/s", "/c", f'call "{bat}"'],
            cwd=self.model_dir, env=env,
        )
        if process is None:
            return False
        ok, reason = self._wait_for_model_attempt(process, long_wait=True)
        self._append_runtime_log(f"MODEL BAT RESULT: {reason}")
        return ok

    def _install_llama(self) -> bool:
        """Prepara llama.cpp automáticamente en un Windows nuevo.

        Orden: WinGet (incluye dependencias de Windows) -> runtime portable oficial
        en AppData. Nunca exige que el usuario ejecute un BAT antes de main.py.
        """
        if os.name != "nt":
            return False

        wingets = self._winget_candidates()
        if wingets:
            self._publish(
                "PREPARING", "Preparando motor local",
                "llama.cpp no estaba instalado; CorePulse lo está preparando automáticamente…",
            )
            for winget in wingets:
                commands = [
                    [str(winget), "install", "--id", "ggml.llamacpp", "-e", "--source", "winget",
                     "--accept-package-agreements", "--accept-source-agreements", "--disable-interactivity", "--silent"],
                    [str(winget), "install", "llama.cpp", "--accept-package-agreements",
                     "--accept-source-agreements", "--disable-interactivity", "--silent"],
                ]
                for command in commands:
                    try:
                        result = self._run(command, timeout=900)
                        self._append_runtime_log(
                            f"WINGET LLAMA RESULT {result.returncode}: "
                            + ((result.stdout or result.stderr or "")[-900:]).replace("\n", " ")
                        )
                    except Exception as exc:
                        self._append_runtime_log(f"WINGET LLAMA ERROR: {type(exc).__name__}: {exc}")
                        continue
                    self._refresh_process_path()
                    # WinGet portable puede tardar unos segundos en crear Links.
                    for _ in range(12):
                        if self._locate_llama() is not None:
                            return True
                        time.sleep(1.0)

        # En un desktop limpio puede no existir WinGet/App Installer. No dejamos que
        # eso convierta el autoarranque en una configuración manual obligatoria.
        if self._download_portable_llama() and self._locate_llama() is not None:
            return True

        if not wingets:
            detail = "No se encontró WinGet y tampoco se pudo descargar el runtime portable oficial de llama.cpp."
        else:
            detail = "WinGet no dejó llama.cpp disponible y el fallback portable oficial también falló."
        self._publish("ERROR", "No se pudo preparar llama.cpp", detail, error="LLAMA_INSTALL_FAILED")
        return False

    def _start_model_if_needed(self) -> bool:
        if _endpoint_ready(MODEL_ENDPOINT):
            self._publish("STARTING", "Modelo local detectado", "Motor generativo local disponible.", model_ready=True)
            return True

        candidates = self._all_llama_candidates()
        if not candidates:
            if not self._install_llama():
                return False
            candidates = self._all_llama_candidates()

        attempted: list[str] = []
        for index, executable in enumerate(candidates):
            if self._stop_event.is_set():
                return False
            command = self._model_command_for(executable)
            attempted.append(str(executable))
            self._publish(
                "MODEL_LOADING", "Cargando IA local",
                f"Iniciando {executable.name}. La primera vez puede descargar varios GB; CorePulse seguirá funcionando mientras termina.",
                server_ready=False, model_ready=False,
            )
            model_env = os.environ.copy()
            model_env.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
            process = self._spawn("corepulse_ai_model", command, cwd=self.model_dir, env=model_env)
            if process is None:
                continue

            # Un candidato que permanece vivo se considera válido y se espera con el
            # timeout completo. Los que cierran enseguida permiten probar el siguiente.
            quick_ok, quick_reason = self._wait_for_model_attempt(process, long_wait=False)
            self._append_runtime_log(f"MODEL CANDIDATE {executable}: {quick_reason}")
            if quick_ok:
                self._publish(
                    "STARTING", "Modelo local conectado", "El motor generativo está listo; iniciando CorePulse AI Server…",
                    model_ready=True,
                )
                return True
            if quick_reason == "STILL_RUNNING":
                ready, reason = self._wait_for_model_attempt(process, long_wait=True)
                self._append_runtime_log(f"MODEL CANDIDATE LONG WAIT {executable}: {reason}")
                if ready:
                    self._publish(
                        "STARTING", "Modelo local conectado", "El motor generativo está listo; iniciando CorePulse AI Server…",
                        model_ready=True,
                    )
                    return True
                if reason in {"TIMEOUT", "STOPPED"}:
                    break

        # Si el binario instalado existe pero no puede arrancar en este hardware,
        # probamos una variante oficial CPU x64 aislada en AppData antes del BAT.
        if not self._stop_event.is_set() and self._start_portable_model_fallback(attempted):
            self._publish(
                "STARTING", "Modelo local conectado",
                "El runtime portable quedó listo; iniciando CorePulse AI Server…",
                model_ready=True,
            )
            return True

        # Último fallback: ejecutar exactamente el BAT manual del proyecto. Esto evita
        # que una diferencia entre Popen y el shell de Windows deje la IA sin iniciar.
        if not self._stop_event.is_set() and self._start_model_via_bat():
            self._publish(
                "STARTING", "Modelo local conectado", "El motor generativo está listo; iniciando CorePulse AI Server…",
                model_ready=True,
            )
            return True

        tail = self._log_tail(_MODEL_LOG_NAME, max_chars=700) or self._log_tail(_MODEL_BAT_LOG_NAME, max_chars=700)
        self._append_runtime_log("MODEL START FAILED. Candidates: " + " | ".join(attempted))
        if tail:
            compact = " ".join(tail.split())[-520:]
            detail = f"llama.cpp se cerró durante el inicio. Último detalle: {compact}"
        else:
            detail = "llama.cpp se cerró durante el inicio. Revisa corepulse_ai_model.log y corepulse_ai_autostart.log."
        self._publish("ERROR", "El modelo local se cerró", detail, error="MODEL_EXITED", model_ready=False)
        return False

    @staticmethod
    def _embedded_server_dependencies_ready() -> bool:
        try:
            import fastapi  # noqa: F401
            import uvicorn  # noqa: F401
            import pydantic  # noqa: F401
            return True
        except Exception:
            return False

    def _start_embedded_server(self) -> bool:
        """Levanta CorePulse AI Server dentro del EXE/Proceso actual.

        En un build PyInstaller no debe exigirse una instalación externa de Python
        para crear un venv. FastAPI/Uvicorn viajan dentro de CorePulse y el servidor
        se ejecuta en un hilo daemon, manteniendo el mismo endpoint 127.0.0.1:8765.
        """
        if _endpoint_ready(SERVER_STATUS_ENDPOINT):
            return True
        try:
            os.environ["COREPULSE_MODEL_BASE_URL"] = f"http://127.0.0.1:{MODEL_PORT}/v1"
            os.environ["COREPULSE_MODEL_NAME"] = MODEL_NAME
            os.environ["COREPULSE_AI_DATA_DIR"] = str(Path(data_path("ai_server")).resolve())
            import uvicorn
            from CorePulse_AI_Server.app.main import app as ai_app

            config = uvicorn.Config(
                ai_app,
                host="127.0.0.1",
                port=SERVER_PORT,
                log_level="warning",
                access_log=False,
            )
            server = uvicorn.Server(config)
            self._embedded_server = server

            def run_server():
                try:
                    server.run()
                except Exception as exc:
                    self._append_runtime_log(f"EMBEDDED SERVER ERROR: {type(exc).__name__}: {exc}")

            thread = threading.Thread(target=run_server, daemon=True, name="CorePulse-AI-Embedded-Server")
            self._embedded_server_thread = thread
            thread.start()

            deadline = time.monotonic() + _SERVER_READY_TIMEOUT_SECONDS
            while not self._stop_event.is_set() and time.monotonic() < deadline:
                status = _http_json(SERVER_STATUS_ENDPOINT)
                if status and status.get("ok"):
                    self._publish(
                        "STARTING", "Servidor CorePulse AI conectado",
                        "Servidor IA integrado disponible; verificando estado final…",
                        server_ready=True, model_ready=bool(status.get("model_ready")), started_by_corepulse=True,
                    )
                    return True
                if not thread.is_alive():
                    break
                time.sleep(0.5)
            self._publish(
                "ERROR", "CorePulse AI Server integrado no respondió",
                "El servidor interno no quedó disponible en 127.0.0.1:8765.",
                error="EMBEDDED_SERVER_FAILED",
            )
            return False
        except Exception as exc:
            self._publish(
                "ERROR", "CorePulse AI Server integrado no disponible",
                f"{type(exc).__name__}: {exc}", error="EMBEDDED_SERVER_IMPORT_FAILED",
            )
            return False

    def _start_server_if_needed(self) -> bool:
        status = _http_json(SERVER_STATUS_ENDPOINT)
        if status and status.get("ok"):
            self._publish(
                "STARTING", "Servidor CorePulse AI disponible", "Verificando conexión con el modelo local…",
                server_ready=True, model_ready=bool(status.get("model_ready")),
            )
            return True

        # En el EXE distribuido el backend viaja embebido: no requerimos Python
        # ni pip en el PC del usuario. En modo fuente también preferimos el servidor
        # embebido cuando las dependencias ya forman parte del runtime principal.
        if is_frozen() or self._embedded_server_dependencies_ready():
            return self._start_embedded_server()

        if not self._ensure_server_runtime():
            return False
        self._publish("STARTING", "Iniciando CorePulse AI Server", "Levantando la API local en 127.0.0.1:8765…", model_ready=True)
        env = os.environ.copy()
        env["COREPULSE_MODEL_BASE_URL"] = f"http://127.0.0.1:{MODEL_PORT}/v1"
        env["COREPULSE_MODEL_NAME"] = MODEL_NAME
        env["COREPULSE_AI_DATA_DIR"] = str(Path(data_path("ai_server")).resolve())
        process = self._spawn(
            "corepulse_ai_server",
            [str(self.venv_python), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(SERVER_PORT)],
            cwd=self.server_dir,
            env=env,
        )
        if process is None:
            return False

        deadline = time.monotonic() + _SERVER_READY_TIMEOUT_SECONDS
        while not self._stop_event.is_set() and time.monotonic() < deadline:
            status = _http_json(SERVER_STATUS_ENDPOINT)
            if status and status.get("ok"):
                self._publish(
                    "STARTING", "Servidor CorePulse AI conectado", "Verificando estado final de CorePulse AI…",
                    server_ready=True, model_ready=bool(status.get("model_ready")), started_by_corepulse=True,
                )
                return True
            if process.poll() is not None:
                self._publish("ERROR", "CorePulse AI Server se cerró", "Revisa el log corepulse_ai_server.log.", error="SERVER_EXITED")
                return False
            time.sleep(0.8)
        if self._stop_event.is_set():
            return False
        self._publish("ERROR", "CorePulse AI Server no respondió", "El puerto local 8765 no quedó disponible dentro del tiempo esperado.", error="SERVER_TIMEOUT")
        return False

    def _confirm_ready(self) -> bool:
        deadline = time.monotonic() + 30
        while not self._stop_event.is_set() and time.monotonic() < deadline:
            status = _http_json(SERVER_STATUS_ENDPOINT)
            if status and status.get("ok") and bool(status.get("model_ready")):
                self._publish(
                    "READY", "CorePulse AI lista", "IA local conectada automáticamente al iniciar CorePulse.",
                    server_ready=True, model_ready=True,
                )
                return True
            time.sleep(1.0)
        if self._stop_event.is_set():
            return False
        status = _http_json(SERVER_STATUS_ENDPOINT)
        if status and status.get("ok"):
            self._publish(
                "DEGRADED", "Servidor conectado; modelo no confirmado",
                "CorePulse AI Server responde, pero todavía no confirma el modelo local.",
                server_ready=True, model_ready=False, error="MODEL_NOT_CONFIRMED",
            )
        else:
            self._publish("ERROR", "CorePulse AI no quedó disponible", "El servicio local dejó de responder durante el arranque.", error="AI_STARTUP_FAILED")
        return False

    def _worker(self) -> None:
        if os.name != "nt":
            self._publish("UNSUPPORTED", "Autoarranque local sólo en Windows", "CorePulse AI puede iniciarse manualmente en este entorno.", error="NON_WINDOWS")
            return

        self._publish("STARTING", "Iniciando CorePulse AI", "Conectando automáticamente el motor local…")
        existing = _http_json(SERVER_STATUS_ENDPOINT)
        if existing and existing.get("ok") and bool(existing.get("model_ready")):
            self._publish("READY", "CorePulse AI lista", "IA local ya estaba conectada.", server_ready=True, model_ready=True)
            return

        # V397: modelo robusto primero; servidor CorePulse AI sólo después de confirmar 8766.
        if not self._start_model_if_needed():
            return
        if self._stop_event.is_set():
            return
        if not self._start_server_if_needed():
            return
        self._confirm_ready()

    def stop(self) -> None:
        """Detiene sólo procesos que esta instancia inició."""
        self._stop_event.set()
        # Detener sólo los procesos propios; nunca finalizar por PID o nombre
        # un servidor llama.cpp que el usuario inició fuera de CorePulse.
        with self._lock:
            owned = list(self._owned_processes.items())[::-1]
            self._owned_processes.clear()
        for _key, process in owned:
            try:
                if process.poll() is None:
                    # El fallback BAT mantiene a llama.cpp como proceso hijo de
                    # cmd.exe. Terminar sólo cmd puede dejar el modelo en RAM.
                    # /T limita taskkill al árbol de ESTE PID propio, jamás a
                    # procesos llama ajenos detectados por nombre o puerto.
                    if os.name == "nt" and _key == "corepulse_ai_model_bat":
                        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       creationflags=_creation_flags(), timeout=8, check=False)
                    if process.poll() is None:
                        process.terminate()
                    try:
                        process.wait(timeout=3.0)
                    except Exception:
                        process.kill()
            except Exception:
                pass
        try:
            if self._embedded_server is not None:
                self._embedded_server.should_exit = True
        except Exception:
            pass
        self._embedded_server = None
        thread = self._embedded_server_thread
        self._embedded_server_thread = None
        if thread is not None and thread is not threading.current_thread() and thread.is_alive():
            thread.join(timeout=2.0)
        for handle in list(self._log_handles):
            try:
                handle.close()
            except Exception:
                pass
        self._log_handles.clear()
        with self._lock:
            self._state.update({"state": "STOPPED", "stage": "CorePulse AI desactivada",
                                "detail": "Los procesos iniciados por CorePulse se detuvieron.",
                                "server_ready": False, "model_ready": False,
                                "started_by_corepulse": False, "updated_at": time.time()})


__all__ = ["LocalAIRuntimeManager", "MODEL_NAME", "MODEL_ENDPOINT", "SERVER_STATUS_ENDPOINT"]
